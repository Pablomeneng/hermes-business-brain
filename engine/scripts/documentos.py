"""Registrar un documento D/X ya redactado, sin aprobar su contenido.

No sustituye validación humana, gobernanza de revisiones ni contrato de bloques.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import hashlib
import json
import os
import re
import sys
from uuid import uuid4

from lib_ce import make_note, notes_in_vault, split_frontmatter, validate_tags, visible_filename
from operacion import ROOT, local_sources, safe_vault, unique_path, utcnow, valid_title
from validar_boveda import validate


X_ID = re.compile(r"^X\d{2}-[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")


# Excepciones cerradas para las dos raíces de sistema de macOS.
# Las rutas dentro de /tmp o /var no reciben excepción propia.
_MACOS_SYSTEM_ALIASES = {
    Path("/var"): ("private/var", "/private/var", Path("/private/var")),
    Path("/tmp"): ("private/tmp", "/private/tmp", Path("/private/tmp")),
}


def _trusted_macos_system_alias(part: Path) -> bool:
    """Acepta SOLO /var y /tmp si el enlace pertenece al SO de macOS.

    Verifica ruta exacta, destino de readlink y destino físico. No se permite
    cualquier otra ruta simbólica, ni un enlace creado por el usuario bajo
    esas raíces. En Linux no se concede ninguna excepción.
    """
    if sys.platform != "darwin":
        return False
    rule = _MACOS_SYSTEM_ALIASES.get(part)
    if rule is None:
        return False
    relative_target, absolute_target, physical_target = rule
    try:
        return (os.readlink(part) in (relative_target, absolute_target)
                and part.resolve(strict=True) == physical_target)
    except (OSError, RuntimeError):
        return False


def _is_symlinked(path: Path) -> bool:
    """Bloquea symlinks arbitrarios; admite sólo aliases fijos del SO."""
    item = path.expanduser().absolute()
    from platform_fs import is_link_or_reparse
    for part in (item, *item.parents):
        if is_link_or_reparse(part) and not _trusted_macos_system_alias(part):
            return True
    return False


def _read_input(file_path: Path, vault: Path) -> tuple[str, str]:
    if _is_symlinked(file_path):
        raise ValueError("Archivo de entrada enlazado simbólicamente; no se utiliza")
    source = file_path.expanduser().resolve()
    if source == ROOT or ROOT in source.parents:
        raise ValueError("No guardar documentos empresariales privados dentro del repositorio maestro")
    if source == vault or vault in source.parents:
        raise ValueError("El borrador de entrada debe estar fuera de la bóveda para evitar sobrescritura")
    if not source.is_file() or source.stat().st_size > 120000:
        raise ValueError("Borrador inexistente o excesivo (>120 kB)")
    original = source.read_bytes()
    text = original.decode("utf-8")
    if len(text.strip()) < 90 or not text.lstrip().startswith("# "):
        raise ValueError("Se requiere un documento Markdown desarrollado con un título y contenido")
    if text.startswith("---\n"):
        raise ValueError("El documento de entrada debe estar sin YAML; el sistema administra sus propiedades")
    if any(marker in text for marker in ("-----BEGIN PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----")):
        raise ValueError("El borrador parece contener una clave privada")
    return text, hashlib.sha256(original).hexdigest()


def _classes() -> set[str]:
    data = json.loads((ROOT / "modelo" / "clases_documentales.json").read_text(encoding="utf-8"))
    return {item["id"] for item in data["clases"]}


def _existing_doc_ids(vault: Path) -> set[str]:
    out = set()
    for path in notes_in_vault(vault):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("tipo") == "documento" and meta.get("doc_id"):
            out.add(str(meta["doc_id"]))
    return out


def create_document(
    vault_path: Path,
    class_id: str,
    title: str,
    content_file: Path,
    *,
    doc_id: str | None = None,
    sources: list[str] | None = None,
    editorial: str = "borrador",
    coverage: str | None = None,
    as_of: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Crea un archivo nuevo en 10_Conocimiento/ con estado nunca aprobado.

    D01–D07: un doc_id estable por familia. X01–X07: identidad propia Xnn-...
    No importa legados; los contenidos deben haber sido obtenidos/autorizados por Codex.
    """
    vault, cfg = safe_vault(vault_path)
    if class_id not in _classes():
        raise ValueError("Clase documental desconocida; usar D01–D07 o X01–X07")
    title = valid_title(title)
    labels = validate_tags(tags)
    if editorial not in {"borrador", "en_revision"}:
        raise ValueError("La creación sólo permite borrador o en_revision, nunca aprobado")
    if coverage is not None and coverage not in {"sin_fuente", "parcial", "suficiente_para_tarea", "no_aplica"}:
        raise ValueError("Cobertura documental desconocida")
    if as_of is None:
        as_of = date.today().isoformat()
    else:
        as_of = date.fromisoformat(as_of).isoformat()
    if class_id.startswith("D"):
        if doc_id is not None and doc_id != class_id:
            raise ValueError("La familia documental D mantiene su doc_id estable, igual a su clase")
        doc_id = class_id
    elif doc_id is None:
        doc_id = class_id + "-" + uuid4().hex[:12].upper()
    if class_id.startswith("X") and (not X_ID.fullmatch(doc_id) or not doc_id.startswith(class_id + "-")):
        raise ValueError("El doc_id de expediente debe ser Xnn-ID y coincidir con su clase")

    # Todo el preflight ocurre antes de escribir, incluidos los links a fuentes.
    pre = validate(vault)
    if pre["errores"]:
        raise ValueError("La bóveda ya contiene errores estructurales; no escribir: " + "; ".join(pre["errores"][:3]))
    if doc_id in _existing_doc_ids(vault):
        raise FileExistsError("El documento ya existe por doc_id; revisar y proponer cambios, no duplicarlo: " + doc_id)
    source_links = local_sources(vault, sources or [])
    if coverage is None:
        coverage = "parcial" if source_links else "sin_fuente"
    body, original_hash = _read_input(content_file, vault)
    target = vault / "10_Conocimiento" / visible_filename(title)
    unique_path(vault, target)

    metadata = {
        "id": doc_id,
        "doc_id": doc_id,
        "tipo": "documento",
        "clase": class_id,
        "empresa_id": cfg["company_id"],
        "schema_version": "0.9",
        "revision": "0.1",
        "estado_editorial": editorial,
        "cobertura": coverage,
        "vigencia": "sin_verificar",
        "sensibilidad": "interno",
        "registrado_en": utcnow(),
        "fecha_corte": as_of,
        "fuentes": source_links,
        **({"tags": labels} if labels else {}),
        "revisado_por": "por_validar",
        "insumo_sha256": original_hash,
    }
    # No interpretar el texto de entrada como un estado ya aprobado.
    new_content = make_note(metadata, body)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline='\n') as handle:
        handle.write(new_content)
    try:
        post = validate(vault)
        if post["errores"]:
            raise ValueError("El documento nuevo no pasó validación estructural: " + "; ".join(post["errores"][:3]))
    except Exception:
        # Sólo este archivo nuevo fue creado; los archivos existentes permanecen.
        target.unlink()
        raise
    return {
        "doc_id": doc_id,
        "ruta": str(target),
        "clase": class_id,
        "revision": "0.1",
        "estado_editorial": editorial,
        "aprobado": False,
        "fuentes": sources or [],
        "insumo_sha256": original_hash,
        "bloques_vnext_con_contrato": "pendiente_validacion",
        "limite": "Crea nota en revisión; NO aprueba contenido, autoridad, relaciones ni gates G1–G7",
    }
