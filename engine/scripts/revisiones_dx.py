"""Revisiones seguras de documentos D/X: preparar, aplicar y restaurar.

NO certifica consentimiento ni aprueba afirmaciones. La autorización se obtiene
fuera del programa; las referencias ingresadas aquí sólo registran esa declaración.
No ejecuta acciones en servicios externos ni escribe información empresarial en Git.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import difflib
import hashlib
import json
import os
import re
import stat

from documentos import _read_input, _is_symlinked
from lib_ce import (
    BLOCK_RE, make_note, notes_in_vault, resolve_link,
    split_frontmatter, target_index, wiki_targets,
)
from operacion import ROOT, local_sources, safe_vault, utcnow
from validar_boveda import validate
from platform_fs import private_directory

DOC_RE = re.compile(r"^(?:D0[1-7]|X0[1-7]-[A-Za-z0-9][A-Za-z0-9_-]{2,63})$")
ITEM_RE = re.compile(r"^(?:PRDX|REVDX)-[A-F0-9]{12}$")
REV_RE = re.compile(r"^(\d{1,5})\.(\d{1,5})$")
PROPOSALS = Path("90_Sistema") / "Propuestas_DX"
HISTORY = Path("90_Sistema") / "Historial_DX"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_sha(links: list[str]) -> str:
    """Huella estable del conjunto de fuentes visible para la autorización."""
    return _hash(json.dumps(sorted(set(links)), ensure_ascii=False, separators=(",", ":")).encode("utf8"))


def _validate_vault(vault: Path) -> None:
    errors = validate(vault)["errores"]
    if errors:
        raise ValueError("Bóveda con errores previos; no se escribe: " + "; ".join(errors[:3]))


def _document(vault: Path, doc_id: str) -> tuple[Path, dict, str, bytes]:
    if not DOC_RE.fullmatch(doc_id):
        raise ValueError("doc_id D/X incorrecto")
    found = []
    for path in notes_in_vault(vault):
        meta, body = split_frontmatter(path.read_text(encoding="utf8"))
        if meta.get("tipo") == "documento" and meta.get("doc_id") == doc_id:
            found.append((path, meta, body))
    if len(found) != 1:
        raise ValueError("Se requiere exactamente un documento existente con doc_id " + doc_id)
    path, meta, body = found[0]
    if path.parent != vault / "10_Conocimiento" or _is_symlinked(path):
        raise ValueError("Documento fuera de la carpeta canónica o enlace simbólico")
    if meta.get("estado_editorial") not in {"borrador", "en_revision"}:
        raise ValueError("Sólo se pueden actualizar borradores o documentos en revisión; aprobados necesitan flujo de gobierno posterior")
    if not REV_RE.fullmatch(str(meta.get("revision") or "")):
        raise ValueError("Revisión previa faltante o no compatible; no improvisar migración")
    return path, meta, body, path.read_bytes()


def _next_revision(previous: str) -> str:
    match = REV_RE.fullmatch(str(previous))
    if not match:
        raise ValueError("Versión original no admitida")
    major, minor = int(match.group(1)), int(match.group(2))
    if minor >= 99999:
        raise ValueError("Límite de revisión; requiere migración planificada")
    return f"{major}.{minor + 1}"


def _check_body(vault: Path, target: Path, previous: str, candidate: str, *, allow_block_removal: bool = False) -> dict:
    if not candidate.lstrip().startswith("# ") or len(candidate.strip()) < 90:
        raise ValueError("El borrador debe incluir título y contenido sustantivo")
    if candidate.startswith("---\n"):
        raise ValueError("El cuerpo candidato no puede declarar YAML; los metadatos se administran por separado")
    if any(s in candidate for s in ("-----BEGIN PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----")):
        raise ValueError("Marcador de credencial detectado")
    if candidate == previous:
        raise ValueError("Sin cambios; no crear otra revisión")
    old_ids = BLOCK_RE.findall(previous)
    new_ids = BLOCK_RE.findall(candidate)
    if len(new_ids) != len(set(new_ids)):
        raise ValueError("ID de bloque duplicado en el documento candidato")
    missing = set(old_ids) - set(new_ids)
    if missing and not allow_block_removal:
        raise ValueError("No se permite retirar IDs de bloque sin un procedimiento de migración: " + ", ".join(sorted(missing)))
    known = set()
    for other in notes_in_vault(vault):
        if other == target:
            continue
        known.update(BLOCK_RE.findall(other.read_text(encoding="utf8")))
    if set(new_ids) & known:
        raise ValueError("IDs de bloque ya utilizados en otro documento")
    paths, names = target_index(vault, include_assets=True)
    bad = [link for link in wiki_targets(candidate) if resolve_link(link, paths, names) is None]
    if bad:
        raise ValueError("Enlace wiki no resuelto: " + ", ".join(sorted(set(bad))[:4]))
    diff = list(difflib.unified_diff(previous.splitlines(),candidate.splitlines(),
                                    fromfile="actual",tofile="propuesta",lineterm=""))
    return {"lineas_diferentes":len(diff),
            "resumen_diff":"\n".join(diff[:45])[:6500],
            "bloques_preservados":len(old_ids),
            "bloques_nuevos":len(set(new_ids)-set(old_ids))}


def _context(vault_path: Path, doc_id: str) -> tuple[Path, Path, dict, str, bytes]:
    vault, _ = safe_vault(vault_path)
    _validate_vault(vault)
    path, meta, body, raw = _document(vault,doc_id)
    return vault,path,meta,body,raw


def previsualizar(vault_path: Path, doc_id: str, input_file: Path,
                 *, sources: list[str] | None = None) -> dict:
    """Sólo lectura: documento actual, borrador externo y diferencia localizada."""
    vault,path,meta,body,raw = _context(vault_path,doc_id)
    candidate,candidate_sha = _read_input(input_file,vault)
    diff = _check_body(vault,path,body,candidate)
    source_ids=sorted(set(sources or []))
    added=local_sources(vault,source_ids)
    current=meta.get("fuentes") or []
    if not isinstance(current,list):
        raise ValueError("Propiedad fuentes del documento no es una lista")
    resulting=sorted(set(current+added))
    return {"doc_id":doc_id,"ruta":str(path),"revision_actual":str(meta["revision"]),
            "revision_propuesta":_next_revision(str(meta["revision"])),
            "sha_original":_hash(raw),"sha_candidato":candidate_sha,
            "fuentes_adicionales":source_ids,"fuentes_resultantes":resulting,
            "sha_fuentes":_source_sha(resulting),
            "estado_editorial":meta["estado_editorial"],**diff,
            "aprobado":False,"operacion":"SOLO_LECTURA"}


def preparar(vault_path: Path, doc_id: str, input_file: Path,
             *, sources: list[str] | None = None) -> dict:
    """Registra propuesta y borrador sin tocar el documento actual."""
    preview=previsualizar(vault_path,doc_id,input_file,sources=sources)
    vault,_=safe_vault(vault_path)
    candidate=input_file.expanduser().resolve().read_bytes()
    if _hash(candidate)!=preview["sha_candidato"]:
        raise ValueError("Borrador cambió durante la preparación")
    pid="PRDX-"+uuid4().hex[:12].upper()
    base=vault/PROPOSALS
    private_directory(base)
    directory=base/pid
    directory.mkdir(mode=0o700,exist_ok=False)
    try:
        (directory/"candidato.snapshot").write_bytes(candidate)
        packet={**preview,"propuesta_id":pid,"creada_en":utcnow(),
                "tipo":"propuesta_revision_documental",
                "estado":"pendiente_autorizacion"}
        (directory/"propuesta.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf8", newline='\n')
    except Exception:
        for item in directory.iterdir(): item.unlink()
        directory.rmdir()
        raise
    return {"propuesta_id":pid,"doc_id":doc_id,"ruta_propuesta":str(directory),
            "sha_original":preview["sha_original"],"sha_candidato":preview["sha_candidato"],
            "fuentes_adicionales":preview["fuentes_adicionales"],
            "fuentes_resultantes":preview["fuentes_resultantes"],
            "sha_fuentes":preview["sha_fuentes"],
            "revision_propuesta":preview["revision_propuesta"],
            "estado":"pendiente_autorizacion","documento_modificado":False}


def _proposal(vault: Path, pid: str) -> tuple[dict, bytes]:
    if not ITEM_RE.fullmatch(pid) or not pid.startswith("PRDX-"):
        raise ValueError("ID de propuesta inválido")
    directory=vault/PROPOSALS/pid
    if _is_symlinked(directory) or not directory.is_dir():
        raise ValueError("Propuesta inexistente o enlazada")
    data=json.loads((directory/"propuesta.json").read_text(encoding="utf8"))
    candidate_path=directory/"candidato.snapshot"
    if _is_symlinked(candidate_path):
        raise ValueError("Candidato enlazado")
    candidate=candidate_path.read_bytes()
    if data.get("propuesta_id")!=pid or _hash(candidate)!=data.get("sha_candidato"):
        raise ValueError("La propuesta fue alterada")
    return data,candidate


def _authorization(responsable: str, referencia: str, esperado: str) -> None:
    if not responsable.strip() or not referencia.strip() or len(referencia)>350:
        raise ValueError("Se necesita responsable y referencia de autorización explícita, obtenida fuera de la CLI")
    if not re.fullmatch(r"[0-9a-f]{64}",esperado):
        raise ValueError("Se necesita SHA-256 exacto para confirmar la versión que se autoriza")


def _backup_root(vault: Path, backup_dir: Path) -> Path:
    raw=backup_dir.expanduser()
    if not raw.is_absolute() or raw.is_symlink():
        raise ValueError("El directorio de respaldo debe ser absoluto y sin enlaces simbólicos")
    root=raw.resolve()
    if root==vault or vault in root.parents or root==ROOT or ROOT in root.parents:
        raise ValueError("El respaldo debe ubicarse fuera de la bóveda y fuera del repositorio maestro")
    return root


def _write_atomic(path: Path, contents: bytes) -> None:
    if os.name == 'nt':
        from windows_fs import atomic_write
        atomic_write(path.parent, path.name, contents, immutable=False, preserve_acl=True)
        return
    temp=path.with_name("."+path.name+".tmp-"+uuid4().hex[:8])
    try:
        mode=stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
        with os.fdopen(fd,"wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp,mode)
        os.replace(temp,path)
    finally:
        if temp.exists(): temp.unlink()


def _publish(vault: Path, path: Path, meta: dict, content: str, *,
             expected_sha: str, responsable: str, referencia: str,
             backup_dir: Path, origen: dict, editorial_status: str = "en_revision",
             reviewed_by: str = "por_validar") -> dict:
    """Bloqueo local + SHA, copia externa/interna y restauración ante fallo."""
    lock_folder=vault/"90_Sistema"/".locks"
    lock_folder.mkdir(parents=True,exist_ok=True)
    lock=lock_folder/(str(meta["doc_id"])+".lock")
    try:
        with lock.open("x",encoding="utf8", newline='\n') as handle:
            handle.write("Operación en curso: "+utcnow()+"\n")
    except FileExistsError as exc:
        raise ValueError("Documento bloqueado por otra revisión; no borrar lock sin comprobar procesos") from exc
    try:
        before=path.read_bytes()
        if _hash(before)!=expected_sha:
            raise ValueError("Documento cambió desde la revisión; no sobrescribir")
        nextrev=_next_revision(str(meta["revision"]))
        entry="REVDX-"+uuid4().hex[:12].upper()
        backroot=_backup_root(vault,backup_dir)
        private_directory(backroot)
        history_root=vault/HISTORY
        private_directory(history_root)
        history=history_root/str(meta["doc_id"])/entry
        history.mkdir(mode=0o700,parents=True,exist_ok=False)
        external=backroot/str(meta["doc_id"])/entry
        external.mkdir(mode=0o700,parents=True,exist_ok=False)
        (history/"anterior.snapshot").write_bytes(before)
        (external/"anterior.snapshot").write_bytes(before)
        if editorial_status not in {"en_revision","aprobado"}:
            raise ValueError("Estado editorial solicitado no permitido")
        if editorial_status=="aprobado" and (not reviewed_by or reviewed_by=="por_validar"):
            raise ValueError("La aprobación editorial requiere revisor explícito")
        newmeta=dict(meta)
        newmeta.update({"revision":nextrev,
                        "estado_editorial":editorial_status,
                        "revisado_por":reviewed_by,
                        "revision_registrada_en":utcnow(),
                        "revision_contenido_sha256":_hash(content.encode("utf8")),
                        "ultima_revision_id":entry})
        out=make_note(newmeta,content).encode("utf8")
        packet={"id":entry,"doc_id":meta["doc_id"],
                "revision_previa":meta["revision"],"revision_nueva":nextrev,
                "sha_previo":_hash(before),"sha_nuevo":_hash(out),
                "solicitante_de_cambio":responsable,
                "referencia_autorizacion":referencia,
                "registrado_en":utcnow(),"operacion":origen,
                "estado":"snapshot_creado",
                "nota":"El script registra una declaración, no verifica identidad/consentimiento."}
        prepared=json.dumps(packet,ensure_ascii=False,indent=2).encode("utf8")+b"\n"
        for location in (history,external):
            _write_atomic(location/"manifest.json",prepared)
        if _hash(path.read_bytes())!=expected_sha:
            raise ValueError("Documento cambió durante la preparación del respaldo")
        try:
            _write_atomic(path,out)
            errors=validate(vault)["errores"]
            if errors:
                raise ValueError("Validación posterior falló: "+"; ".join(errors[:3]))
            if _hash(path.read_bytes())!=_hash(out):
                raise ValueError("No coincide la huella posterior")
            packet["estado"]="aplicado"
            completed=json.dumps(packet,ensure_ascii=False,indent=2).encode("utf8")+b"\n"
            for location in (history,external):
                _write_atomic(location/"manifest.json",completed)
        except Exception:
            _write_atomic(path,before)
            if path.read_bytes()!=before:
                raise RuntimeError("RESTAURACIÓN FALLÓ: requiere recuperación manual del snapshot externo")
            packet["estado"]="restaurado_por_fallo"
            restored=json.dumps(packet,ensure_ascii=False,indent=2).encode("utf8")+b"\n"
            for location in (history,external):
                try:
                    _write_atomic(location/"manifest.json",restored)
                except OSError:
                    pass  # Respaldo original conservado; revisar log y manifiesto.
            raise
        return {"doc_id":meta["doc_id"],"revision":nextrev,
                "ruta":str(path),"historial_id":entry,
                "historial":str(history),"respaldo_externo":str(external),
                "sha_original":_hash(before),"sha_nuevo":_hash(out),
                "estado_editorial":editorial_status,"aprobado":editorial_status=="aprobado",
                "limite":"No certifica aprobación empresarial ni calidad G1–G7"}
    finally:
        if lock.exists(): lock.unlink()


def aplicar(vault_path: Path, proposal_id: str, *,
           expected_sha: str, candidate_sha: str, source_sha: str | None = None,
           responsable: str, referencia_autorizacion: str,
           backup_dir: Path) -> dict:
    """Aplica propuesta EXISTENTE: nunca autoriza/declara aprobado el contenido."""
    _authorization(responsable,referencia_autorizacion,expected_sha)
    vault,_=safe_vault(vault_path)
    plan,raw_candidate=_proposal(vault,proposal_id)
    if plan.get("estado")!="pendiente_autorizacion":
        raise ValueError("Propuesta ya procesada o no autorizable")
    if plan.get("sha_original")!=expected_sha or plan.get("sha_candidato")!=candidate_sha:
        raise ValueError("Huella confirmada no coincide con la propuesta")
    vault,path,meta,body,current=_context(vault,plan["doc_id"])
    if _hash(current)!=expected_sha:
        raise ValueError("Cambio concurrente: documento actual ya no coincide")
    additional=plan.get("fuentes_adicionales") or []
    if not isinstance(additional,list) or not all(isinstance(s,str) for s in additional):
        raise ValueError("Fuentes propuestas inválidas")
    if additional:
        if not source_sha or source_sha!=plan.get("sha_fuentes"):
            raise ValueError("Huella de fuentes confirmada no coincide con la propuesta")
        existing=meta.get("fuentes") or []
        if not isinstance(existing,list):
            raise ValueError("Propiedad fuentes del documento no es una lista")
        resulting=sorted(set(existing+local_sources(vault,additional)))
        if resulting!=plan.get("fuentes_resultantes") or _source_sha(resulting)!=source_sha:
            raise ValueError("Fuentes cambiaron desde la preparación; no aplicar")
        meta=dict(meta)
        meta["fuentes"]=resulting
    candidate=raw_candidate.decode("utf8")
    _check_body(vault,path,body,candidate)
    result=_publish(vault,path,meta,candidate,expected_sha=expected_sha,
                    responsable=responsable,referencia=referencia_autorizacion,
                    backup_dir=backup_dir,origen={"propuesta_id":proposal_id})
    plan["estado"]="aplicada"
    plan["resultado_historial_id"]=result["historial_id"]
    plan_path=vault/PROPOSALS/proposal_id/"propuesta.json"
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf8", newline='\n')
    return result


def restaurar(vault_path: Path, doc_id: str, history_id: str, *,
             expected_sha: str, responsable: str,
             referencia_autorizacion: str, backup_dir: Path) -> dict:
    """Restauración como NUEVA revisión (no destruye la historia)."""
    _authorization(responsable,referencia_autorizacion,expected_sha)
    vault,path,meta,body,current=_context(vault_path,doc_id)
    if _hash(current)!=expected_sha:
        raise ValueError("Documento cambió; no restaurar versión distinta de la confirmada")
    if not ITEM_RE.fullmatch(history_id) or not history_id.startswith("REVDX-"):
        raise ValueError("ID de historial inválido")
    source=vault/HISTORY/doc_id/history_id
    if _is_symlinked(source) or not source.is_dir():
        raise ValueError("Historial inexistente o enlazado")
    packet=json.loads((source/"manifest.json").read_text(encoding="utf8"))
    snapshot_file=source/"anterior.snapshot"
    if _is_symlinked(snapshot_file):
        raise ValueError("Snapshot enlazado")
    original=snapshot_file.read_bytes()
    if packet.get("estado")!="aplicado" or packet.get("doc_id")!=doc_id or _hash(original)!=packet.get("sha_previo"):
        raise ValueError("Snapshot alterado o corresponde a otro documento")
    previous_meta,previous_body=split_frontmatter(original.decode("utf8"))
    if previous_meta.get("doc_id")!=doc_id or previous_meta.get("tipo")!="documento":
        raise ValueError("Snapshot no es documento D/X compatible")
    if previous_body==body:
        raise ValueError("Restauración sin cambio sustantivo")
    _check_body(vault,path,body,previous_body,allow_block_removal=True)
    # Conservar atributos históricos de la versión elegida, y registrar nueva revisión.
    restored_meta=dict(previous_meta)
    restored_meta["revision"]=str(meta["revision"])
    restored_meta["estado_editorial"]="en_revision"
    restored_meta["revisado_por"]="por_validar"
    result=_publish(vault,path,restored_meta,previous_body,expected_sha=expected_sha,
                    responsable=responsable,referencia=referencia_autorizacion,
                    backup_dir=backup_dir,origen={"restauracion_desde":history_id})
    return result
