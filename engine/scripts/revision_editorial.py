"""Evaluación humana trazable de documentos D/X, sin evaluación semántica automática.

Los registros de evaluación son evidencia declarada (NO firma ni control de identidad).
Una promoción editorial requiere acto específico y respaldo versionado. Nunca
implica vigencia comercial, legal, financiera ni suficiencia para otra tarea.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import hashlib
import json
import re
import stat

from documentos import _is_symlinked
from lib_ce import BLOCK_RE
from platform_fs import private_directory
from operacion import safe_vault, utcnow
from revisiones_dx import (
    _context, _hash, _publish, _authorization, _backup_root,
)

GATES={f"G{i}" for i in range(1,8)}
DECISIONS={"requiere_cambios","recomendar_parcial","recomendar_integral"}
STATES={"cumple","no_cumple","no_aplica"}
ID_RE=re.compile(r"^EVALDX-[A-F0-9]{12}$")
ALLOWED_PREFIX="90_Sistema/Evaluaciones_DX"


def _read_act(path: Path, vault: Path) -> tuple[dict, str]:
    raw=path.expanduser()
    if _is_symlinked(raw):
        raise ValueError("Acta enlazada; no se admite")
    source=raw.resolve()
    if source==vault or vault in source.parents:
        raise ValueError("Acta debe prepararse fuera de la bóveda")
    from operacion import ROOT
    if source==ROOT or ROOT in source.parents:
        raise ValueError("El acta empresarial privada no se admite en Git")
    if not source.is_file() or source.stat().st_size>24000:
        raise ValueError("Acta ausente o excesiva")
    payload=source.read_bytes()
    if b"PRIVATE KEY" in payload or b"BEGIN OPENSSH" in payload:
        raise ValueError("Posible credencial en acta")
    obj=json.loads(payload.decode("utf8"))
    if not isinstance(obj,dict):
        raise ValueError("Acta JSON debe ser objeto")
    return obj,_hash(payload)


def _validate_act(act:dict, doc_id:str, doc_sha:str, body:str, coverage:str) -> dict:
    if act.get("doc_id")!=doc_id or act.get("sha_documento")!=doc_sha:
        raise ValueError("El acta no corresponde a este documento y huella")
    decision=act.get("decision")
    if decision not in DECISIONS:
        raise ValueError("Decisión del acta inválida")
    reviewer=act.get("revisor")
    ref=act.get("referencia_decision")
    if not isinstance(reviewer,str) or len(reviewer.strip())<3 or len(reviewer)>160:
        raise ValueError("Acta sin revisor identificado")
    if not isinstance(ref,str) or len(ref.strip())<8 or len(ref)>350:
        raise ValueError("Acta sin referencia de decisión verificable por el operador")
    if "revision" in act and not isinstance(act["revision"],str):
        raise ValueError("Revisión no válida")
    blocks=set(BLOCK_RE.findall(body))
    scope=act.get("alcance_bloques")
    if not isinstance(scope,list) or not scope or any(not isinstance(x,str) for x in scope):
        raise ValueError("Se requiere alcance explícito por ID de bloque")
    if len(set(scope))!=len(scope) or not set(scope).issubset(blocks):
        raise ValueError("Alcance duplicado o incluye bloques que no existen")
    gates=act.get("gates")
    if not isinstance(gates,dict) or set(gates)!=GATES:
        raise ValueError("La evaluación debe incluir exactamente G1–G7")
    failures=[]
    for gid,check in gates.items():
        if not isinstance(check,dict) or check.get("estado") not in STATES:
            raise ValueError("Estado inválido en "+gid)
        why=check.get("fundamento")
        if not isinstance(why,str) or len(why.strip())<12 or len(why)>1500:
            raise ValueError("Falta fundamento específico en "+gid)
        if check["estado"]=="no_cumple":
            failures.append(gid)
        if gid in {"G2","G6"} and check["estado"]=="no_aplica":
            failures.append(gid)
    if decision.startswith("recomendar") and failures:
        raise ValueError("No se puede recomendar aprobación con gates críticos incumplidos: "+", ".join(sorted(failures)))
    if decision=="recomendar_integral":
        if scope!=list(dict.fromkeys(BLOCK_RE.findall(body))):
            raise ValueError("Aprobación integral exige TODOS los bloques en orden")
        if coverage!="suficiente_para_tarea":
            raise ValueError("No recomendar aprobación integral si la cobertura sigue parcial")
    return {"decision":decision,"revisor":reviewer.strip(),
            "referencia_decision":ref.strip(),"alcance_bloques":scope,
            "gates":gates,"fallos":sorted(failures)}


def registrar_evaluacion(vault_path:Path, doc_id:str, act_path:Path, *,
                         expected_sha:str) -> dict:
    """Registrar una evaluación, sin modificar el documento revisado."""
    vault,doc,meta,body,raw=_context(vault_path,doc_id)
    if expected_sha!=_hash(raw):
        raise ValueError("Documento cambió; rehacer la evaluación")
    act,act_sha=_read_act(act_path,vault)
    checked=_validate_act(act,doc_id,expected_sha,body,str(meta.get("cobertura","parcial")))
    root=vault/ALLOWED_PREFIX
    private_directory(root)
    folder=root/doc_id
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    eid="EVALDX-"+uuid4().hex[:12].upper()
    record={"id":eid,"tipo":"evaluacion_editorial",
            "doc_id":doc_id,"revision":str(meta["revision"]),
            "sha_documento":expected_sha,
            "fecha_registro":utcnow(),"acta_sha256":act_sha,
            "fuentes_documento":meta.get("fuentes") or [], **checked,
            "documento_modificado":False,
            "limite":"Declaración humana registrada, no identidad autenticada ni comprobación autónoma de G1–G7"}
    target=folder/(eid+".json")
    with target.open("x",encoding="utf8", newline='\n') as f:
        f.write(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    return {"evaluacion_id":eid,"ruta":str(target),"doc_id":doc_id,
            "decision":checked["decision"],"documento_modificado":False}


def _load_eval(vault:Path, evaluation_id:str) -> dict:
    if not ID_RE.fullmatch(evaluation_id):
        raise ValueError("ID de evaluación inválido")
    root=vault/ALLOWED_PREFIX
    found=list(root.glob("*/"+evaluation_id+".json"))
    if len(found)!=1 or _is_symlinked(found[0]):
        raise ValueError("Evaluación inexistente o ambigua")
    record=json.loads(found[0].read_text(encoding="utf8"))
    if record.get("id")!=evaluation_id or record.get("doc_id")!=found[0].parent.name:
        raise ValueError("Evaluación mal formada")
    return record


def aprobar_documento(vault_path:Path,evaluation_id:str,*,expected_sha:str,
                       responsable:str,referencia_autorizacion:str,
                       backup_dir:Path,confirmacion:str) -> dict:
    """Promoción EDITORIAL integral, sólo para documento cubierto y revisado.

    Esta operación no prueba identidad humana ni vigencia temporal. El agente
    debe obtener la autorización del propietario antes de invocar la CLI.
    """
    _authorization(responsable,referencia_autorizacion,expected_sha)
    vault,_=safe_vault(vault_path)
    record=_load_eval(vault,evaluation_id)
    doc_id=record["doc_id"]
    if confirmacion!=f"APROBAR {doc_id} {expected_sha[:12]}":
        raise ValueError("Falta confirmación exacta y específica del documento")
    if record["decision"]!="recomendar_integral" or record.get("sha_documento")!=expected_sha:
        raise ValueError("No existe recomendación integral para esta huella")
    vault,path,meta,body,raw=_context(vault,doc_id)
    if _hash(raw)!=expected_sha or str(meta.get("revision"))!=record.get("revision"):
        raise ValueError("La evaluación no corresponde a la revisión actual")
    if str(meta.get("cobertura"))!="suficiente_para_tarea":
        raise ValueError("Cobertura parcial; la revisión editorial debe seguir por bloques")
    checked=_validate_act(record,doc_id,expected_sha,body,str(meta.get("cobertura")))
    if checked["decision"]!="recomendar_integral":
        raise ValueError("Gates no permiten promoción")
    if not meta.get("fuentes"):
        raise ValueError("Un documento sin referencias no puede promocionarse automáticamente")
    _backup_root(vault,backup_dir)
    # No se altera el cuerpo: sólo el estado editorial y la revisión versionada.
    result=_publish(vault,path,meta,body,expected_sha=expected_sha,
                    responsable=responsable,referencia=referencia_autorizacion,
                    backup_dir=backup_dir,
                    origen={"evaluacion_id":evaluation_id,"tipo":"promocion_editorial_integral"},
                    editorial_status="aprobado",reviewed_by=checked["revisor"])
    result["aprobacion_editorial"]=True
    result["aprobacion_semantica_automatica"]=False
    result["aprobacion_evaluacion_id"]=evaluation_id
    result["advertencia"]="No equivale a vigencia contractual, legal, comercial o financiera"
    return result
