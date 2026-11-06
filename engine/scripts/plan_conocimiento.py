"""Auditoría de arquitectura del conocimiento antes de redactar o crear notas.

No extrae significado por sí mismo: Codex clasifica unidades desde originales
autorizados y esta herramienta revisa IDENTIDADES, cobertura, fuentes y vínculos.
No modifica bóvedas ni archivos de empresa, no crea notas y no aprueba contenido.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import unicodedata
import json
import re

from documentos import _is_symlinked
from operacion import ROOT, index_ids, load_registry, safe_vault
from lib_ce import split_frontmatter
from relaciones import PREDICATES

KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{2,55}$")
TAG_RE = re.compile(r"^[a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*){0,2}$")
SOURCE_RE = re.compile(r"^F-[A-Za-z0-9_-]{2,60}$")
DOC_RE = re.compile(r"^(?:D0[1-7]|X0[1-7])$")
ACTIONS = {"crear", "revisar", "referenciar", "no_crear"}


def _text(value: object, name: str, minimum: int=12, maximum: int=1200) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{name} debe contener una explicación concreta de {minimum} a {maximum} caracteres")
    return value.strip()


def _read_plan(plan_path: Path, vault: Path) -> dict:
    if _is_symlinked(plan_path):
        raise ValueError("Plan externo con enlace simbólico, no se lee")
    source = plan_path.expanduser().resolve()
    if source == vault or vault in source.parents or source == ROOT or ROOT in source.parents:
        raise ValueError("El plan se prepara fuera de la bóveda privada y fuera de Git")
    if not source.is_file() or source.stat().st_size > 90000:
        raise ValueError("Plan ausente o mayor a 90 kB")
    raw = source.read_bytes()
    if b"PRIVATE KEY" in raw or b"BEGIN OPENSSH" in raw:
        raise ValueError("Posible clave privada en el plan")
    doc = json.loads(raw.decode("utf8"))
    if not isinstance(doc, dict):
        raise ValueError("El plan debe ser un objeto JSON")
    return doc


def _items(obj: dict, name: str, limit: int=30) -> list:
    val = obj.get(name)
    if not isinstance(val, list) or not 1 <= len(val) <= limit:
        raise ValueError(f"{name} requiere entre 1 y {limit} elementos")
    return val


def _sources(val: object, label: str) -> list[str]:
    if not isinstance(val, list) or not val or any(not isinstance(s, str) or not SOURCE_RE.fullmatch(s) for s in val):
        raise ValueError(f"{label}: indicar al menos un ID de fuente F-...")
    if len(set(val)) != len(val):
        raise ValueError(f"{label}: fuente duplicada")
    return val


def _tags(val: object, label: str) -> list[str]:
    if not isinstance(val, list) or not 1 <= len(val) <= 5:
        raise ValueError(f"{label}: usar entre 1 y 5 etiquetas temáticas")
    if len(set(val)) != len(val) or any(not isinstance(t, str) or not TAG_RE.fullmatch(t) for t in val):
        raise ValueError(f"{label}: etiquetas deben ser únicas, breves y sin datos personales")
    return val


def planificar(vault_path: Path, plan_path: Path) -> dict:
    """Auditoría de plan previamente RAZONADO por Codex. Estrictamente solo lectura."""
    vault, cfg = safe_vault(vault_path)
    plan = _read_plan(plan_path, vault)
    purpose = _text(plan.get("pregunta"), "pregunta empresarial", 15, 650)
    subjects = _items(plan, "asuntos")
    units = _items(plan, "unidades")
    registered = index_ids(vault)
    note_meta = {}
    note_titles = {}
    classes = {}
    for registered_id, note_path in registered.items():
        fm, body = split_frontmatter(note_path.read_text(encoding="utf8"))
        note_meta[registered_id] = fm
        title_match = re.search(r"(?m)^# (.+)$", body)
        note_titles[registered_id] = title_match.group(1).strip() if title_match else note_path.stem
        if fm.get("tipo") == "documento":
            classes.setdefault(str(fm.get("clase") or ""), set()).add(registered_id)
    registry = load_registry()
    subject_ids, unit_ids = set(), set()
    source_pending = set()
    warnings = []
    recommendations = []
    potential_duplicates = []
    mapped_subjects = Counter()
    declared_sources = set()

    def normalize_title(value: str) -> str:
        value = unicodedata.normalize("NFKD",value).casefold()
        value = "".join(c for c in value if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    for s in subjects:
        if not isinstance(s, dict):
            raise ValueError("Cada asunto debe ser un objeto")
        key = s.get("clave")
        if not isinstance(key, str) or not KEY_RE.fullmatch(key) or key in subject_ids:
            raise ValueError("Asunto con clave repetida o inválida")
        subject_ids.add(key)
        _text(s.get("criterio"), "Criterio del asunto "+key, 25, 1300)
        ids = _sources(s.get("fuentes"), "asunto "+key)
        declared_sources.update(ids)
        _text(s.get("por_que_importa"), "Importancia de "+key, 20, 950)

    summaries = []
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("Cada unidad propuesta debe ser un objeto")
        key, action = unit.get("clave"), unit.get("accion")
        if not isinstance(key, str) or not KEY_RE.fullmatch(key) or key in unit_ids:
            raise ValueError("Unidad sin clave estable o repetida")
        unit_ids.add(key)
        if action not in ACTIONS:
            raise ValueError(f"{key}: acción no reconocida: {action}")
        title = _text(unit.get("titulo"), f"{key}.titulo", 5, 180)
        reason = _text(unit.get("razon_identidad"), f"{key}.razon_identidad", 35, 1400)
        assigned = unit.get("asuntos")
        if not isinstance(assigned, list) or not assigned or len(assigned) != len(set(assigned)):
            raise ValueError(f"{key}: cada unidad tiene que asumir asuntos únicos")
        for a in assigned:
            if a not in subject_ids:
                raise ValueError(f"{key}: asunto no declarado: {a}")
            mapped_subjects[a] += 1
        uid = unit.get("id_existente")
        typ = unit.get("tipo")
        path = None
        if action == "no_crear":
            if uid is not None:
                raise ValueError(f"{key}: no_crear no admite ID existente")
            if typ not in (None, "no_aplica"):
                raise ValueError(f"{key}: no_crear no debe crear un tipo de entidad")
            tags = []
        else:
            tags = _tags(unit.get("etiquetas"),key)
            if typ != "documento" and typ not in registry:
                raise ValueError(f"{key}: usar documento o uno de los tipos reales del modelo")
            if typ == "fuente":
                raise ValueError(f"{key}: la fuente se registra por procedencia, no como una ficha de idea")
            doc_class = unit.get("clase")
            if typ == "documento" and (not isinstance(doc_class,str) or not DOC_RE.fullmatch(doc_class)):
                raise ValueError(f"{key}: clase documental debe ser D01–D07 / X01–X07; el ID X01-... es de expediente, no clase")
            if action in ("revisar","referenciar"):
                if not isinstance(uid,str) or uid not in registered:
                    raise ValueError(f"{key}: ID existente no encontrado; recuperar nota antes de inventar otra")
                original_path = registered[uid]
                meta, _ = split_frontmatter(original_path.read_text(encoding="utf8"))
                if meta.get("tipo") != typ:
                    raise ValueError(f"{key}: tipo existente no coincide con el plan")
                if typ == "documento" and meta.get("clase") != doc_class:
                    raise ValueError(f"{key}: clase documental difiere de la nota existente")
                if meta.get("sensibilidad") not in (None, "interno"):
                    raise ValueError(f"{key}: acceso superior a interno; no diseñar operación sin ACL")
                path = str(original_path.relative_to(vault))
            elif action == "crear":
                if uid is not None:
                    raise ValueError(f"{key}: crear no acepta ID existente; usar revisar/referenciar")
                if typ == "documento" and doc_class.startswith("D") and classes.get(doc_class):
                    ids = ", ".join(sorted(classes[doc_class]))
                    raise ValueError(f"{key}: {doc_class} ya existe (ID {ids}); enlazar y revisar, no duplicar")
                if typ != "documento":
                    normalized = normalize_title(title)
                    matches = sorted(nid for nid, existing in note_titles.items()
                        if note_meta[nid].get("tipo") == typ
                        and normalize_title(existing) == normalized)
                    if matches:
                        potential_duplicates.append({"unidad":key,"tipo":typ,
                                                     "titulo":title,"ids_existentes":matches})
                        warnings.append("POSIBLE_DUPLICADO_ENTIDAD: "+key+" -> "+", ".join(matches))
                path = ("10_Conocimiento/" if typ == "documento" else registry[typ]["carpeta"]+"/") + "(ID pendiente)"
        summaries.append({
            "clave":key,"titulo":title,"accion":action,"tipo":typ,
            "id_existente":uid,"ruta_destino":path,"asuntos":assigned,
            "etiquetas":tags,"razon_identidad":reason,
        })

    missed = subject_ids - set(mapped_subjects)
    duplicated = {k:n for k,n in mapped_subjects.items() if n > 1}
    if missed:
        raise ValueError("Asuntos sin destino: "+", ".join(sorted(missed)))
    if duplicated:
        raise ValueError("Asuntos con dos dueños canónicos (duplicación): "+str(duplicated))

    rels = plan.get("relaciones")
    if not isinstance(rels, list):
        raise ValueError("relaciones debe ser una lista (aun cuando sea vacía)")
    checked_rels, pairs = [], set()
    for r in rels:
        if not isinstance(r, dict):
            raise ValueError("Relación inválida")
        a,b,verb=r.get("origen"),r.get("destino"),r.get("predicado")
        if a not in unit_ids or b not in unit_ids or a==b:
            raise ValueError("Relación con extremos inexistentes o idénticos")
        actions_by_key = {x["clave"]:x["accion"] for x in summaries}
        if "no_crear" in (actions_by_key[a], actions_by_key[b]):
            raise ValueError("No se puede enlazar una unidad que no tendrá nota; enlazar la fuente o una existente")
        if verb not in PREDICATES:
            raise ValueError("Usar predicado tipado del modelo, no relacionado genérico")
        if (a,b,verb) in pairs:
            raise ValueError("Relación repetida")
        pairs.add((a,b,verb))
        why = _text(r.get("fundamento"),"relación "+a+" -> "+b,20,1300)
        scope = _text(r.get("ambito"),"ámbito de relación",6,250)
        checked_rels.append({"origen":a,"destino":b,"predicado":verb,
                             "ambito":scope,"fundamento":why,
                             "estado":"propuesta_no_verificada"})
    for sid in declared_sources:
        p = registered.get(sid)
        if p is None:
            source_pending.add(sid)
        else:
            fm,_=split_frontmatter(p.read_text(encoding="utf8"))
            if fm.get("tipo")!="fuente":
                raise ValueError("ID F- usado para algo distinto a fuente: "+sid)
            if fm.get("sensibilidad")!="interno":
                warnings.append("Fuente con acceso no apto para el MVP: "+sid)

    active=[u["clave"] for u in summaries if u["accion"] in ("crear","revisar")]
    if len(active)>1 and not checked_rels:
        explanation = plan.get("justificacion_sin_relaciones")
        if not isinstance(explanation,str) or len(explanation.strip())<50:
            warnings.append("VARIAS_UNIDADES_SIN_VINCULOS: proponer relaciones o justificar por qué son independientes")
        else:
            recommendations.append("Unidades sin enlaces porque se justificó su independencia")
    if len(active)==1:
        sole_active=next(u for u in summaries if u["clave"]==active[0])
        if sole_active["tipo"]=="documento" and len(sole_active["asuntos"])>=3:
            warnings.append("POSIBLE_MONOLITO_DX: varios asuntos sólo desarrollados en un D/X; comprobar identidades autónomas")
    if source_pending:
        warnings.append("FUENTES_PENDIENTES: registrar o vincular originales autorizados: "+", ".join(sorted(source_pending)))
    if not any(u["accion"]=="no_crear" for u in summaries):
        recommendations.append("No hay elementos no_crear; revisar si hubo menciones incidentales, sin obligar a inventarlas")
    return {
        "empresa_id":cfg["company_id"],"pregunta":purpose,
        "asuntos_detectados":len(subjects),"unidades_propuestas":summaries,
        "relaciones_candidatas":checked_rels,"fuentes_pendientes":sorted(source_pending),
        "advertencias":warnings,"recomendaciones":recommendations,
        "posibles_duplicados":potential_duplicates,"plan_consistente":not warnings,
        "documentos_modificados":False,"modo":"SOLO_LECTURA",
        "limite":"La consistencia formal no garantiza criterio, valor ni fidelidad; el propietario revisa y autoriza cada escritura.",
        "siguiente_paso":"Mostrar primero el mapa al propietario; después redactar o proponer cambios por nota con su autorización.",
    }
