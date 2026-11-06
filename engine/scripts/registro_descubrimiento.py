"""Captura provisional de descubrimiento; nunca conocimiento aprobado."""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4

from lib_ce import make_note, visible_filename
from operacion import ROOT, index_ids, local_sources, safe_vault, unique_path, utcnow, valid_title


def capture_discovery(vault_path: Path, title: str, content_file: Path,
                      *, sources: list[str] | None = None) -> dict:
    vault, cfg = safe_vault(vault_path)
    title = valid_title(title)
    raw = content_file.expanduser()
    if raw.is_symlink():
        raise ValueError("El archivo de entrada no puede ser enlace simbólico")
    source = raw.resolve()
    if source == ROOT or ROOT in source.parents:
        raise ValueError("No prepares contenido privado dentro del repositorio Git")
    if source == vault or vault in source.parents:
        raise ValueError("Prepara la captura fuera de la bóveda para evitar duplicación")
    if not source.is_file() or source.stat().st_size > 24000:
        raise ValueError("Insumo inexistente o excesivo; utilizar síntesis breve")
    text = source.read_text(encoding="utf8").strip()
    if len(text) < 20 or "\x00" in text:
        raise ValueError("Captura vacía o inválida")
    if any(x in text for x in ("-----BEGIN PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----")):
        raise ValueError("Captura contiene una credencial: no guardar")
    refs = local_sources(vault, sources or [])
    nid = "CAP-" + uuid4().hex[:12].upper()
    if nid in index_ids(vault):
        raise ValueError("Colisión de ID")
    target = vault / "90_Sistema" / "Descubrimiento" / visible_filename(title)
    unique_path(vault, target)
    front = {
        "id": nid, "tipo": "registro_descubrimiento", "clase": "control",
        "empresa_id": cfg["company_id"], "estado_editorial": "borrador",
        "estado_conocimiento": "pendiente", "vigencia": "sin_verificar",
        "sensibilidad": "interno", "registrado_en": utcnow(),
        "fuentes": refs, "autoridad": "ninguna", "revisado_por": "por_validar",
    }
    body = (
        "# " + title + "\n\n"
        "> **CAPTURA PROVISIONAL.** No es documento empresarial aprobado, "
        "contrato, venta ni prueba automática de participación de la empresa.\n\n"
        "## Hallazgos para contrastar\n\n" + text + "\n\n"
        "## Validación pendiente\n\n"
        "- [ ] Separar observaciones, interpretaciones y atribuciones empresariales.\n"
        "- [ ] Contrastar fuentes originales autorizadas y vigencia.\n"
        "- [ ] Revisar con el propietario antes de integrar como D/X o entidad.\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf8", newline='\n') as handle:
        handle.write(make_note(front, body))
    return {"id": nid, "ruta": str(target), "estado": "borrador_no_autoritativo",
            "fuentes": sources or [], "aprobado": False,
            "importado_como_conocimiento": False}
