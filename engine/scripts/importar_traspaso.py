#!/usr/bin/env python3
"""Importa un paquete vNext-0.9 VALIDADO: sin fuentes en bruto ni escritura externa."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import os
import tempfile
import shutil
from pathlib import Path
import yaml

from lib_ce import make_note, split_frontmatter, visible_filename
from lib_canvas import canvas_from_manifest

REPO = Path(__file__).resolve().parent.parent
VALIDATOR = REPO / 'contratos' / 'vNext-0.9' / 'Validador_de_Traspaso.py'


def validator_check(manifest: Path) -> dict:
    spec = importlib.util.spec_from_file_location('ce_contract_validator', VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    errors, obj = mod.check(manifest)
    if errors:
        raise ValueError('Traspaso rechazado; errores del contrato:\n- ' + '\n- '.join(errors))
    return obj


def heading_link(block: dict, docs: dict) -> str:
    doc_id = block['doc_id']
    path = docs[doc_id]['_relative'].removesuffix('.md')
    heading = block.get('heading_path') or []
    if heading:
        # El título es para navegación humana, no garantiza identidad de bloque precisa.
        path += '#' + heading[-1].replace('|', '-')
    return f'[[{path}]] (`{block["block_id"]}`)'


def esc_cell(val) -> str:
    return str(val or '').replace('|', '\\|').replace('\n', ' ')


def control_document(sys_id: str, title: str, body: str) -> str:
    return make_note({'id': sys_id, 'tipo': 'control', 'estado_editorial': 'borrador', 'sensibilidad': 'interno'}, f'# {title}\n\n{body.rstrip()}\n')


def collect_changes(manifest: Path, vault: Path, allow_real: bool = False) -> tuple[dict[Path, bytes], dict]:
    manifest = manifest.expanduser().resolve()
    vault = vault.expanduser().resolve()
    if not vault.is_dir(): raise ValueError('Bóveda inexistente; ejecutar primero crear_instancia.py')
    config_path = vault / '90_Sistema' / 'config_empresa.yaml'
    if not config_path.is_file(): raise ValueError('Bóveda no reconocida: falta config_empresa.yaml')
    company = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    obj = validator_check(manifest)
    cid = obj['company']['id']
    if company.get('company_id') != cid:
        raise ValueError(f'Empresa incorrecta: la bóveda es {company.get("company_id")}, el paquete es {cid}')
    if not obj['company']['synthetic'] and not allow_real:
        raise ValueError('Paquete real: se requiere --permitir-real y autorización previa de fuentes')
    # No hay aislamiento por usuario dentro de Obsidian; importar solo material interno compartible.
    protected = [(kind, item.get('doc_id') or item.get('source_id') or item.get('block_id') or item.get('id'))
                 for kind in ('documents', 'sources', 'blocks', 'restrictions')
                 for item in obj.get(kind, []) if item.get('access', 'interno') != 'interno']
    if protected:
        raise ValueError('Rechazado: la bóveda prototipo no tiene ACL. Material protegido: ' + str(protected))
    trans_dir = vault / '90_Sistema' / 'Traspasos' / cid
    if trans_dir.exists():
        raise FileExistsError('Este paquete ya tiene un registro de traspaso; no sobrescribir: ' + str(trans_dir))
    docs = {d['doc_id']: dict(d) for d in obj['documents']}
    locations = {}
    for doc_id, doc in docs.items():
        original = (manifest.parent / doc['path']).read_text(encoding='utf8')
        match = re.search(r'(?m)^# +(.+)$', original)
        label = match.group(1).strip() if match else 'Documento ' + doc['doc_type']
        label = re.sub(r'^(?:D\d{2}|X\d{2}[-_A-Za-z0-9]+)\s*[—:-]\s*', '', label)
        doc['_relative'] = '10_Conocimiento/' + visible_filename(label)
        locations[doc_id] = doc['_relative']
    for source in obj['sources']:
        sid = source['source_id']
        label = source.get('title') or ('Fuente de ' + source['kind'] + ' - ' + sid)
        locations[sid] = '50_Fuentes/' + visible_filename(label)
    if len({p.casefold() for p in locations.values()}) != len(locations):
        raise ValueError('Títulos duplicados en el traspaso; distinguir asuntos antes de importar')
    blocks = {b['block_id']: b for b in obj['blocks']}
    rels_by_doc = {id: {} for id in docs}
    for rel in obj.get('relationships', []):
        a = blocks[rel['subject_id']]['doc_id']
        b = blocks[rel['object_id']]['doc_id']
        if a == b: continue
        pred = re.sub('[^a-z0-9_]', '_', rel['predicate'].lower())
        rels_by_doc[a].setdefault('rel_' + pred, set()).add(f'[[{locations[b].removesuffix(".md")}]]')
    changes = {}
    for doc_id, doc in docs.items():
        path = (manifest.parent / doc['path']).resolve()
        original = path.read_text(encoding='utf-8')
        existing, body = split_frontmatter(original)
        sources = sorted(set(s for b in obj['blocks'] if b['doc_id'] == doc_id for s in b.get('source_ids', [])) |
                         set(s for q in doc.get('coverage_by_question', []) for s in q.get('source_ids', [])))
        # No asumir que todos los bloques tienen el mismo estado de conocimiento o vigencia.
        fm = dict(existing)
        fm.update({'id': doc_id, 'doc_id': doc_id, 'tipo': 'documento', 'clase': doc['doc_type'],
                   'estado_editorial': doc['editorial_status'], 'fecha_corte': str(doc.get('as_of', '')),
                   'revision': str(doc.get('revision', '')), 'sensibilidad': doc['access'],
                   'huella_original_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'fuentes': [f'[[{locations[sid].removesuffix(".md")}]]' for sid in sources]})
        for key, values in sorted(rels_by_doc[doc_id].items()):
            fm[key] = sorted(values)
        # Navegación explícita para el lector; los hechos del documento original no se duplican.
        navigation = ['## Navegación vinculada (vista derivada del traspaso)', '',
                      '> Esta sección es un índice de enlaces, no constituye autoridad o contenido empresarial nuevo.', '']
        for key, values in sorted(rels_by_doc[doc_id].items()):
            navigation.append(f'- **{key[4:]}:** ' + ', '.join(sorted(values)))
        if sources:
            navigation.append('- **Fuentes registradas:** ' + ', '.join(f'[[{locations[sid].removesuffix(".md")}]]' for sid in sources))
        if not sources and not rels_by_doc[doc_id]:
            navigation.append('- No hay vínculos adicionales declarados en este traspaso.')
        body = body.rstrip() + '\n\n' + '\n'.join(navigation) + '\n'
        changes[vault / locations[doc_id]] = make_note(fm, body).encode('utf-8')
    for source in obj['sources']:
        sid = source['source_id']
        fm = {'id': sid, 'tipo': 'fuente', 'clase_fuente': source['kind'], 'lectura': source['read_status'],
              'sensibilidad': source['access']}
        if source.get('event_date'): fm['fecha_evento'] = str(source['event_date'])
        body = f'# {Path(locations[sid]).stem}\n\n- **Localizador original:** `{source["locator"]}`\n- **Capturada:** {source["captured_at"]}\n- **Usos permitidos declarados:** {", ".join(source.get("permitted_uses", []))}\n\n> Se conserva una **ficha**, no el contenido fuente. Verificar permisos, contexto y disponibilidad en el sistema original.\n'
        changes[vault / locations[sid]] = make_note(fm, body).encode('utf-8')
    lines = ['| Origen (bloque) | Predicado | Destino (bloque) | Estado | Fuentes |', '|---|---|---|---|---|']
    for r in obj['relationships']:
        left, right = blocks[r['subject_id']], blocks[r['object_id']]
        fuentes = ', '.join(f'[[{locations[s].removesuffix(".md")}]]' for s in r.get('source_ids', []))
        lines.append(f'| {heading_link(left, docs)} | `{esc_cell(r["predicate"])}` | {heading_link(right, docs)} | {esc_cell(r["status"])} | {fuentes} |')
    mapa = make_note({'id': 'SYS-MAPA-RELACIONES', 'tipo': 'mapa', 'estado_editorial': 'borrador', 'sensibilidad': 'interno'}, '# Relaciones de conocimiento\n\nConexiones **tipadas** del contrato; el enlace a sección no reemplaza la identidad de bloque `kb:id`.\n\n' + '\n'.join(lines) + '\n\nVolver a [[Inicio]].\n')
    changes[vault / '00_Mapas' / 'Relaciones_de_conocimiento.md'] = mapa.encode('utf-8')
    lines = ['| Asunto | Ámbito | Bloque autoridad | Vigencia | Desde | Hasta |', '|---|---|---|---|---|---|']
    for a in obj.get('authorities', []):
        lines.append(f'| {esc_cell(a["topic_key"])} | {esc_cell(a["scope"])} | {heading_link(blocks[a["block_id"]], docs)} | {esc_cell(a["temporal_status"])} | {esc_cell(a.get("valid_from"))} | {esc_cell(a.get("valid_to"))} |')
    changes[vault / '90_Sistema' / 'Autoridades.md'] = control_document('SYS-AUTORIDADES', 'Autoridades explícitas del paquete', '\n'.join(lines) + '\n\n**No es resolución automática de autoridad para cualquier pregunta:** aplicar contexto, acceso y evidencia.').encode('utf-8')
    lines = ['| Pendiente | Pregunta | Prioridad | Documentos afectados |', '|---|---|---|---|']
    for p in obj.get('pending', []):
        refs = ', '.join(f'[[{locations[d].removesuffix(".md")}]]' for d in p['affected_doc_ids'])
        lines.append(f'| {esc_cell(p["id"])} | {esc_cell(p["question"])} | {esc_cell(p["priority"])} | {refs} |')
    changes[vault / '90_Sistema' / 'Pendientes.md'] = control_document('SYS-PENDIENTES', 'Pendientes del traspaso', '\n'.join(lines) + '\n\nEstos vacíos no se consideran aprobados.').encode('utf-8')
    lines = ['| Prueba | Pregunta | Bloques esperados | Estado reportado |', '|---|---|---|---|']
    for t in obj['retrieval_tests']:
        links = ', '.join(heading_link(blocks[b], docs) for b in t['expected_block_ids'])
        lines.append(f'| {esc_cell(t["test_id"])} | {esc_cell(t["question"])} | {links} | **{esc_cell(t["result"])}** |')
    changes[vault / '90_Sistema' / 'Pruebas_de_recuperacion.md'] = control_document('SYS-PRUEBAS', 'Pruebas de recuperación semántica', '\n'.join(lines) + '\n\nNO se han ejecutado aquí pruebas de consulta en Obsidian ni con un agente.').encode('utf-8')
    lines = ['| Bloque | Conocimiento | Editorial | Cobertura | Vigencia | Soporte | Desde | Fuentes |', '|---|---|---|---|---|---|---|---|']
    for b in obj['blocks']:
        fuentes = ', '.join(f'[[{locations[s].removesuffix(".md")}]]' for s in b.get('source_ids', []))
        lines.append('| ' + ' | '.join(esc_cell(v) for v in [heading_link(b, docs), b['knowledge_state'], b['editorial_status'], b['coverage_state'], b['temporal_status'], b['support_class'], b.get('valid_from') or '', fuentes]) + ' |')
    changes[vault / '90_Sistema' / 'Estados_de_bloques.md'] = control_document('SYS-BLOQUES', 'Estados por bloque (cuatro ejes separados)', '\n'.join(lines)).encode('utf-8')
    changes[vault / '00_Mapas' / 'Mapa_de_relaciones.canvas'] = canvas_from_manifest(obj, locations).encode('utf-8')
    manifest_bytes = manifest.read_bytes()
    changes[trans_dir / 'manifest.json'] = manifest_bytes
    audit = f'# Registro de importación estructural\n\n- **Paquete:** `{cid}`\n- **Contrato:** {obj["contract_version"]}\n- **Manifiesto SHA-256:** `{hashlib.sha256(manifest_bytes).hexdigest()}`\n- **Documentos:** {len(docs)}\n- **Bloques:** {len(blocks)}\n- **Fuentes como referencia, sin copia:** {len(obj["sources"])}\n- **Aristas tipadas:** {len(obj["relationships"])}\n- **Pruebas de recuperación pendientes:** {sum(t["result"] != "aprobada_humana" for t in obj["retrieval_tests"])}\n\nEl importador verifica estructura por el validador 0.9. **No valida el significado ni los derechos reales de uso.** No se han leído ni copiado las fuentes en bruto.\n'
    changes[trans_dir / 'Reporte.md'] = control_document('SYS-IMPORT-' + cid, 'Registro de importación', audit.replace('# Registro de importación estructural\n\n', '', 1)).encode('utf-8')
    return changes, obj


# Texto exacto de la plantilla previa. Nunca aceptar una nota editada por coincidir
# parcialmente con una frase dentro de ella.
LEGACY_RELATION_PLACEHOLDER = "---\nid: SYS-MAPA-RELACIONES\ntipo: mapa\nestado_editorial: borrador\nsensibilidad: interno\n---\n# Relaciones del conocimiento\n\nEl importador del contrato vNext genera aquí un mapa de relaciones tipadas desde los bloques del manifiesto. Si no se ha importado material, aún no hay relaciones.\n\nVolver a [[Inicio]].\n"


def _intact_relation_placeholder(original: str) -> bool:
    template=Path(__file__).resolve().parent.parent / "plantilla_boveda" / "00_Mapas" / "Relaciones_de_conocimiento.md"
    return original in (LEGACY_RELATION_PLACEHOLDER, template.read_text(encoding="utf8"))


def import_package(manifest: Path, vault: Path, allow_real: bool = False) -> dict:
    changes, obj = collect_changes(manifest, vault, allow_real)
    root = vault.resolve()
    placeholders = {'00_Mapas/Relaciones_de_conocimiento.md', '90_Sistema/Autoridades.md',
                    '90_Sistema/Pendientes.md', '90_Sistema/Pruebas_de_recuperacion.md'}
    for p in changes:
        if root not in p.parents: raise ValueError('Ruta fuera de la bóveda')
        if p.exists():
            rel = p.relative_to(root).as_posix()
            if rel not in placeholders: raise FileExistsError('No sobrescribir destino ya existente: ' + str(p))
            old = p.read_text(encoding='utf-8')
            if rel == '00_Mapas/Relaciones_de_conocimiento.md':
                if not _intact_relation_placeholder(old): raise FileExistsError('Mapa ya editado: ' + str(p))
            elif rel == '90_Sistema/Autoridades.md':
                if 'No se ha importado aún' not in old: raise FileExistsError('Autoridades ya editadas')
            elif rel == '90_Sistema/Pendientes.md':
                if 'El sistema conserva vacíos' not in old: raise FileExistsError('Pendientes ya editados')
            elif rel == '90_Sistema/Pruebas_de_recuperacion.md':
                if 'PENDIENTE: probar con un agente real' not in old: raise FileExistsError('Pruebas ya editadas')
    # Aplicación transaccional en la medida de lo posible: preflight de todo el lote,
    # stage de bytes, commit y rollback al fallar. No proporciona bloqueo de concurrencia.
    for p in changes:
        if any(parent.is_symlink() for parent in [p, *p.parents] if root == parent or root in parent.parents):
            raise ValueError('Ruta de destino con enlace simbólico: ' + str(p))
    original = {p: p.read_bytes() if p.exists() else None for p in changes}
    committed = []
    with tempfile.TemporaryDirectory(prefix='.ce-stage-', dir=root) as work:
        staging = Path(work)
        for i, (p, data) in enumerate(changes.items()):
            (staging / str(i)).write_bytes(data)
        try:
            for i, p in enumerate(changes):
                p.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / str(i), p)
                committed.append(p)
        except Exception:
            for p in reversed(committed):
                prev = original[p]
                if prev is None:
                    p.unlink(missing_ok=True)
                else:
                    p.write_bytes(prev)
            raise
    return {'empresa': obj['company']['id'], 'documentos': len(obj['documents']), 'bloques': len(obj['blocks']),
            'fuentes_referenciadas': len(obj['sources']), 'relaciones': len(obj['relationships']),
            'pruebas_semanticas_pendientes': sum(t['result'] != 'aprobada_humana' for t in obj['retrieval_tests'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--vault', type=Path, required=True)
    ap.add_argument('--permitir-real', action='store_true', help='Solo documentos internos, después de autorización y revisión externa')
    a = ap.parse_args()
    try: print('IMPORTACIÓN:', json.dumps(import_package(a.manifest, a.vault, a.permitir_real), ensure_ascii=False))
    except (ValueError, FileExistsError, KeyError) as exc: ap.error(str(exc))

if __name__ == '__main__': main()
