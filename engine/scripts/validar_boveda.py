#!/usr/bin/env python3
"""Valida propiedades, enlaces wiki y referencias del último manifest importado."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from lib_ce import (BLOCK_RE, EDITORIAL, TEMPORAL, SENSITIVITY,
                    KNOWLEDGE, COVERAGE, notes_in_vault, resolve_link,
                    split_frontmatter, target_index, wiki_targets)


def validate(vault: Path) -> dict:
    vault = vault.resolve()
    if not vault.is_dir():
        return {'notas': 0, 'ids': 0, 'bloques': 0, 'traspasos': 0,
                'errores': [f'Bóveda inexistente o no es directorio: {vault}'],
                'advertencias': [], 'tipos': {}}
    errors = []
    warnings = []
    id_to_file = {}
    doc_id_to_file = {}
    paths, names = target_index(vault, include_assets=True)
    block_to_file = {}
    for p in notes_in_vault(vault):
        try:
            text = p.read_text(encoding='utf-8')
            fm, _ = split_frontmatter(text)
        except (UnicodeError, ValueError) as e:
            errors.append(f'{p.relative_to(vault)}: {e}')
            continue
        if not fm:
            errors.append(f'{p.relative_to(vault)}: falta frontmatter')
        note_id = fm.get('id')
        if not note_id:
            errors.append(f'{p.relative_to(vault)}: falta id')
        elif note_id in id_to_file:
            errors.append(f'ID duplicado {note_id}: {p} y {id_to_file[note_id]}')
        else:
            id_to_file[note_id] = p
        if fm.get('estado_editorial') and fm['estado_editorial'] not in EDITORIAL:
            errors.append(f'{p.relative_to(vault)}: editorial no permitido: {fm["estado_editorial"]}')
        if fm.get('vigencia') and fm['vigencia'] not in TEMPORAL:
            errors.append(f'{p.relative_to(vault)}: vigencia no permitida: {fm["vigencia"]}')
        if fm.get('estado_conocimiento') and fm['estado_conocimiento'] not in KNOWLEDGE:
            errors.append(f'{p.relative_to(vault)}: conocimiento no permitido')
        if fm.get('cobertura') and fm['cobertura'] not in COVERAGE:
            errors.append(f'{p.relative_to(vault)}: cobertura no permitida')
        if fm.get('sensibilidad') and fm['sensibilidad'] not in SENSITIVITY:
            errors.append(f'{p.relative_to(vault)}: sensibilidad no permitida')
        if fm.get('tipo') == 'documento' and not fm.get('doc_id'):
            errors.append(f'{p.relative_to(vault)}: documento sin doc_id')
        if fm.get('tipo') == 'documento' and fm.get('doc_id'):
            did = str(fm['doc_id'])
            if did in doc_id_to_file:
                errors.append(f'Doc_id duplicado {did}: {p} y {doc_id_to_file[did]}')
            else:
                doc_id_to_file[did] = p
        for target in wiki_targets(text):
            if not resolve_link(target, paths, names):
                errors.append(f'{p.relative_to(vault)}: enlace roto o ambiguo [[{target}]]')
        for bid in BLOCK_RE.findall(text):
            if bid in block_to_file:
                errors.append(f'Bloque duplicado {bid}')
            else: block_to_file[bid] = p
    # Las aristas locales tienen contrato y validación referencial propios.
    try:
        from relaciones import validate_relations
        errors.extend(validate_relations(vault))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append("Registro de relaciones locales inválido: "+str(exc))
    manifests = sorted((vault / '90_Sistema' / 'Traspasos').glob('*/manifest.json'))
    for m in manifests:
        try: obj = json.loads(m.read_text(encoding='utf-8'))
        except Exception as exc:
            errors.append(f'{m}: JSON ilegible: {exc}')
            continue
        for d in obj.get('documents', []):
            expected = id_to_file.get(d['doc_id'])
            if expected is None or expected.parent != vault / '10_Conocimiento':
                errors.append(f'{m}: falta documento {d["doc_id"]}')
        for s in obj.get('sources', []):
            expected = id_to_file.get(s['source_id'])
            if expected is None or expected.parent != vault / '50_Fuentes':
                errors.append(f'{m}: falta ficha de fuente {s["source_id"]}')
        for b in obj.get('blocks', []):
            actual = block_to_file.get(b['block_id'])
            expected = id_to_file.get(b['doc_id'])
            if actual != expected:
                errors.append(f'{m}: bloque {b["block_id"]} ausente o en documento equivocado')
        for r in obj.get('relationships', []):
            if r['subject_id'] not in block_to_file or r['object_id'] not in block_to_file:
                errors.append(f'{m}: arista con bloque ausente: {r["subject_id"]} -> {r["object_id"]}')
        num_semantic = sum(t.get('result') != 'aprobada_humana' for t in obj.get('retrieval_tests', []))
        if num_semantic:
            warnings.append(f'{m.relative_to(vault)}: {num_semantic} prueba(s) semántica(s) no aprobada(s) humanamente')
    return {'notas': len(notes_in_vault(vault)), 'ids': len(id_to_file), 'bloques': len(block_to_file),
            'traspasos': len(manifests), 'errores': errors, 'advertencias': warnings,
            'tipos': dict(Counter((split_frontmatter(p.read_text(encoding='utf-8'))[0].get('tipo') or 'sin_tipo') for p in notes_in_vault(vault)))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vault', type=Path, required=True)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    res = validate(a.vault)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f'{"PASS" if not res["errores"] else "FAIL"}: {res["notas"]} notas, {res["bloques"]} bloques, {res["traspasos"]} traspasos')
        for e in res['errores']: print('ERROR:', e)
        for w in res['advertencias']: print('AVISO:', w)
        print('ALCANCE: integridad, NO verdad empresarial ni respuesta semántica')
    if res['errores']: raise SystemExit(1)

if __name__ == '__main__': main()
