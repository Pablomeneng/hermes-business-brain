"""Mapa navegable y Canvas DERIVADOS de notas y aristas ya existentes.

Obsidian Bases es una vista sobre notas; este mapa no es una fuente de autoridad.
Previsualización read-only. Publicación opcional exige SHA, confirmación literal,
respaldo externo y validación posterior, sin modificar notas empresariales.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import re
import stat

from documentos import _is_symlinked
from lib_ce import notes_in_vault, split_frontmatter
from platform_fs import private_directory
from operacion import safe_vault, utcnow
from relaciones import query as query_relations
from revisiones_dx import _backup_root, _write_atomic
from validar_boveda import validate

MAP_MD = Path("00_Mapas/Mapa_Derivado_Conocimiento.md")
MAP_CANVAS = Path("00_Mapas/Mapa_Derivado_Conocimiento.canvas")
MAP_ID = "SYS-MAPA-DERIVADO"
MARKER = "<!-- cerebro-empresarial: mapa-conocimiento-generado v1 -->"
MAX_CANVAS_NODES = 100
EXCLUDE = {"mapa","sistema","control","continuidad","registro_descubrimiento",
           "propuesta_de_cambio"}
EXTENSIONS = {".md", ".canvas"}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digests(contents: dict[str,bytes]) -> str:
    return _sha(("|".join(k+":"+_sha(contents[k]) for k in sorted(contents))).encode("ascii"))


def _same_projection(name: str, existing: bytes, proposed: bytes) -> bool:
    """Obsidian may serialize Canvas and add edge sides when it opens a map.

    Those anchors change its layout, not the generated notes or relations. Keep
    hashing the actual bytes for concurrency checks, but do not ask to republish
    a map whose only differences are native Canvas serialization and anchors.
    """
    if existing == proposed:
        return True
    if name != MAP_CANVAS.as_posix():
        return False
    try:
        current, expected = json.loads(existing), json.loads(proposed)
        if not isinstance(current,dict) or not isinstance(expected,dict):
            return False
        current = json.loads(json.dumps(current))
        for edge in current.get("edges",[]):
            if not isinstance(edge,dict):
                return False
            for key in ("fromSide","toSide"):
                if key in edge:
                    if edge[key] not in {"top","bottom","left","right"}:
                        return False
                    del edge[key]
        return current == expected
    except (UnicodeDecodeError,json.JSONDecodeError,TypeError):
        return False


def _title(text: str, fallback: str) -> str:
    m=re.search(r"(?m)^# +(.+)$",text)
    return (m.group(1).strip() if m else fallback).replace("|", " - ").replace("]", "")[:150]


def _wiki(node: dict) -> str:
    return "[["+str(Path(node["ruta"]).with_suffix("")).replace("\\","/")+"|"+str(node["titulo"]).replace("|"," - ").replace("]","")+"]]"


def _catalog(vault: Path) -> dict:
    result=validate(vault)
    if result["errores"]:
        raise ValueError("Bóveda con errores estructurales: "+"; ".join(result["errores"][:3]))
    nodes, skipped=[],0
    for file in notes_in_vault(vault):
        fm,body=split_frontmatter(file.read_text(encoding="utf8"))
        typ=str(fm.get("tipo") or "")
        if typ in EXCLUDE or not typ:
            continue
        if fm.get("sensibilidad","interno")!="interno":
            skipped+=1
            continue
        ident=str(fm["id"])
        tags=fm.get("tags") or []
        if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags):
            tags=[]
        nodes.append({
            "id":ident,"tipo":typ,"clase":str(fm.get("clase") or ""),
            "ruta":file.relative_to(vault).as_posix(),
            "titulo":_title(body,file.stem),
            "etiquetas":sorted(set(tags)),
            "estado_editorial":str(fm.get("estado_editorial") or "sin_registrar"),
            "vigencia":str(fm.get("vigencia") or "sin_verificar"),
        })
    nodes.sort(key=lambda n:(n["tipo"],n["titulo"].casefold(),n["id"]))
    by_id={n["id"]:n for n in nodes}
    relationships=[]
    omitted=0
    for edge in query_relations(vault)["relaciones"]:
        if edge["origen_id"] not in by_id or edge["destino_id"] not in by_id:
            omitted+=1
            continue
        relationships.append({
            "id":edge["id"],"origen":edge["origen_id"],"destino":edge["destino_id"],
            "predicado":edge["predicado"],"ambito":edge["ambito"],
            "estado":edge["estado_efectivo"],"fuentes":edge["fuentes"],
        })
    relationships.sort(key=lambda e:(e["origen"],e["predicado"],e["destino"],e["id"]))
    return {"nodos":nodes,"aristas":relationships,"notas_omitidas_restringidas":skipped,
            "relaciones_omitidas_por_alcance":omitted}


def _render_markdown(report: dict) -> bytes:
    nodes=report["nodos"]
    by_id={n["id"]:n for n in nodes}
    result=[
        "---","id: "+MAP_ID,"tipo: mapa","estado_editorial: borrador",
        "sensibilidad: interno","---",
        MARKER,"# Mapa de conocimiento empresarial","",
        "> Proyección DERIVADA para navegar Obsidian. NO crea ni aprueba afirmaciones,",
        "> decisiones, contratos, precios o relaciones. Las notas originales y sus",
        "> fuentes mantienen autoridad y vigencia propias.","",
        "## Notas por tipo","",
    ]
    by_type=defaultdict(list)
    for n in nodes:by_type[n["tipo"]].append(n)
    for typ in sorted(by_type):
        result.extend(["### "+typ.replace("_"," ").title(),""])
        for n in by_type[typ]:
            tags=(", ".join(n["etiquetas"]) if n["etiquetas"] else "sin etiqueta")
            result.append("- "+_wiki(n)+" — "+n["id"]+" · "+n["estado_editorial"]+
                          " · "+n["vigencia"]+" · temas: "+tags)
        result.append("")
    if not nodes:result.append("_La empresa todavía no tiene notas empresariales registradas._")
    by_tag=defaultdict(list)
    for n in nodes:
        for tag in n["etiquetas"]:by_tag[tag].append(n)
    result.extend(["","## Temas y etiquetas",""])
    if not by_tag:result.append("_Sin etiquetas temáticas registradas todavía._")
    for tag in sorted(by_tag):
        result.append("- "+tag+" ("+str(len(by_tag[tag]))+"): "+
                      ", ".join(_wiki(n) for n in by_tag[tag]))
    result.extend(["","## Relaciones tipadas declaradas","",
                   "Una relación propuesta NO equivale a una relación confirmada. La",
                   "confirmación declarada por revisor tampoco autentica su identidad.",""])
    if not report["aristas"]:
        result.append("_No hay relaciones tipadas registradas entre notas de este mapa._")
    for edge in report["aristas"]:
        src,dst=by_id[edge["origen"]],by_id[edge["destino"]]
        result.append("- "+_wiki(src)+" → "+_wiki(dst)+" · "+edge["predicado"]+
                      " · estado: "+edge["estado"]+" · ámbito: "+str(edge["ambito"]).replace("\n"," "))
    result.extend(["","## Alcance","",
        "- Notas restringidas omitidas: "+str(report["notas_omitidas_restringidas"]),
        "- Relaciones omitidas por sensibilidad o alcance: "+str(report["relaciones_omitidas_por_alcance"]),
        "- Los vínculos de navegación y las etiquetas no confirman autoridad ni acuerdos.",
        "- No se editan las notas, sus propiedades ni sus fuentes.",
        "",
        MARKER,""])
    return "\n".join(result).encode("utf8")


def _render_canvas(report: dict) -> bytes:
    """Canvas nativo con nodos-file y flechas entre notas relacionadas."""
    nodes=list(report["nodos"])
    outgoing={e["origen"] for e in report["aristas"]}
    incoming={e["destino"] for e in report["aristas"]}
    selected=sorted(nodes,key=lambda n:(
        0 if n["id"] in outgoing or n["id"] in incoming else 1,
        n["tipo"],n["titulo"].casefold(),n["id"]))[:MAX_CANVAS_NODES]
    ids={n["id"] for n in selected}
    canvas_nodes=[{"id":"nota-sistema-mapa","type":"text",
                   "text":"MAPA DERIVADO — NO ES FUENTE DE AUTORIDAD. "
                          "Las relaciones son declaraciones, no acuerdos verificados.",
                   "x":-440,"y":0,"width":350,"height":190}]
    for i,node in enumerate(selected):
        col=i%5
        row=i//5
        canvas_nodes.append({"id":"nota-"+node["id"],"type":"file",
             "file":node["ruta"],"x":col*400,"y":row*280,
             "width":340,"height":215})
    edges=[]
    for e in report["aristas"]:
        if e["origen"] not in ids or e["destino"] not in ids:
            continue
        state="revisión" if e["estado"]=="validada_por_revisor" else "propuesta"
        edges.append({"id":"arista-"+e["id"],"fromNode":"nota-"+e["origen"],
                      "toNode":"nota-"+e["destino"],
                      "label":e["predicado"]+" ("+state+")","toEnd":"arrow"})
    return (json.dumps({"nodes":canvas_nodes,"edges":edges},
                       ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8")


def _proposal(vault: Path) -> tuple[dict,dict[str,bytes],dict[str,bytes]]:
    rep=_catalog(vault)
    intended={MAP_MD.as_posix():_render_markdown(rep),
              MAP_CANVAS.as_posix():_render_canvas(rep)}
    existing={}
    for name in intended:
        file=vault/name
        if _is_symlinked(file):
            raise ValueError("Mapa apuntado por enlace simbólico: "+name)
        if file.exists():
            if not file.is_file():
                raise ValueError("Ruta reservada del mapa no es archivo: "+name)
            data=file.read_bytes()
            if name.endswith(".md") and MARKER.encode("utf8") not in data:
                raise ValueError("Mapa ya existe con modificaciones no generadas; no sobrescribir")
            if name.endswith(".canvas"):
                obj=json.loads(data.decode("utf8"))
                if not isinstance(obj,dict) or not isinstance(obj.get("nodes"),list) or not isinstance(obj.get("edges"),list):
                    raise ValueError("Canvas ajeno o inválido; no sobrescribir")
                if not any(x.get("id")=="nota-sistema-mapa" and
                           x.get("type")=="text" and
                           str(x.get("text") or "").startswith("MAPA DERIVADO")
                           for x in obj["nodes"]):
                    raise ValueError("Canvas existente no es generado por el producto")
                if not all(isinstance(x.get("id"),str) and
                           x["id"].startswith(("nota-","arista-"))
                           for x in obj["nodes"]+obj["edges"]):
                    raise ValueError("Canvas existente no corresponde a la proyección generada")
            existing[name]=data
    if existing and len(existing)!=len(intended):
        raise ValueError("Mapa parcialmente existente: revisión manual antes de regenerar")
    return rep,intended,existing


def previsualizar(vault_path:Path) -> dict:
    vault,cfg=safe_vault(vault_path)
    report,new,old=_proposal(vault)
    preview=new[MAP_MD.as_posix()].decode("utf8")
    canvas=json.loads(new[MAP_CANVAS.as_posix()].decode("utf8"))
    proposed=_digests(new)
    original=_digests(old) if old else "NUEVO"
    return {
        "empresa_id":cfg["company_id"],"modo":"SOLO_LECTURA",
        "rutas_generadas":list(new),"sha_actual":original,
        "sha_propuesto":proposed,
        "confirmacion_requerida":"PUBLICAR MAPA "+proposed[:12],
        "sin_cambios":bool(old) and all(_same_projection(n,old[n],new[n]) for n in new),
        "notas_en_mapa":len(report["nodos"]),
        "relaciones_tipadas":len(report["aristas"]),
        "canvas_nodos":len(canvas["nodes"])-1,"canvas_aristas":len(canvas["edges"]),
        "canvas_parcial":len(canvas["nodes"])-1<len(report["nodos"]),
        "notas_restringidas_omitidas":report["notas_omitidas_restringidas"],
        "vista_previa":preview[:3200],
        "limite":"Notas y flechas derivadas; revisar fuentes originales. No modifica la bóveda ni aprueba contenido.",
    }


def publicar(vault_path:Path,*,sha_actual:str,sha_propuesto:str,
             confirmacion:str,backup_dir:Path) -> dict:
    vault,_=safe_vault(vault_path)
    if not re.fullmatch(r"[0-9a-f]{64}",sha_propuesto):
        raise ValueError("SHA propuesto debe tener 64 caracteres hexadecimales")
    if confirmacion!="PUBLICAR MAPA "+sha_propuesto[:12]:
        raise ValueError("Falta confirmación literal del contenido propuesto")
    if sha_actual!="NUEVO" and not re.fullmatch(r"[0-9a-f]{64}",sha_actual):
        raise ValueError("SHA original inválido")
    locks=vault/"90_Sistema"/".locks"
    locks.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock=locks/"mapa_conocimiento.lock"
    if _is_symlinked(lock) or _is_symlinked(locks):
        raise ValueError("Bloqueo enlazado: operación rechazada")
    try:
        with lock.open("x",encoding="utf8", newline='\n') as handle:
            handle.write("Generación de mapa: "+utcnow()+"\n")
    except FileExistsError as exc:
        raise ValueError("Otra generación de mapa sigue en curso") from exc
    try:
        report,new,old=_proposal(vault)
        observed=_digests(old) if old else "NUEVO"
        if observed!=sha_actual or _digests(new)!=sha_propuesto:
            raise ValueError("Mapa o notas cambiaron; volver a previsualizar")
        if old and all(_same_projection(n,old[n],new[n]) for n in new):
            return {"resultado":"SIN_CAMBIOS","nodos":len(report["nodos"])}
        root=_backup_root(vault,backup_dir)
        private_directory(root)
        dest=root/("mapa-"+uuid4().hex[:12])
        dest.mkdir(mode=0o700,parents=True,exist_ok=False)
        for name,content in old.items():
            (dest/(Path(name).name+".anterior.snapshot")).write_bytes(content)
        manifest={"tipo":"copia_mapa_derivado","estado":"respaldo_preparado",
                  "rutas":list(new),"sha_original":observed,
                  "sha_nuevo":sha_propuesto,"registrado_en":utcnow()}
        (dest/"manifest.json").write_text(
            json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8", newline='\n')
        changed=[]
        try:
            for name,data in new.items():
                file=vault/name
                current=file.read_bytes() if file.exists() else None
                if current!=old.get(name):
                    raise ValueError("Cambio concurrente de mapa: "+name)
                _write_atomic(file,data)
                changed.append(name)
            errs=validate(vault)["errores"]
            if errs:
                raise ValueError("Mapa produce errores estructurales: "+"; ".join(errs[:3]))
            for name,data in new.items():
                if (vault/name).read_bytes()!=data:
                    raise ValueError("Huella posterior no coincide: "+name)
            manifest["estado"]="aplicado"
            (dest/"manifest.json").write_text(
                json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8", newline='\n')
        except Exception:
            failures=[]
            for name in reversed(changed):
                try:
                    file=vault/name
                    if name in old:
                        _write_atomic(file,old[name])
                    elif file.exists():
                        file.unlink()
                except OSError as err:
                    failures.append(name+": "+str(err))
            if failures:
                raise RuntimeError("Restauración de mapa falló; usar respaldos: "+"; ".join(failures))
            raise
        return {"resultado":"APLICADO","mapas":list(new),"nodos":len(report["nodos"]),
                "aristas":len(report["aristas"]),"respaldo":str(dest),
                "editorial":"DERIVADO_NO_APROBADO"}
    finally:
        if lock.exists():
            lock.unlink()
