#!/usr/bin/env python3
"""Plan y migración acotada de nombres visibles, sin cambiar identidad editorial.

La entrada privada contiene {"notas": [{"id": "...", "nombre": "Asunto legible"}]}.
Sólo reescribe destinos de enlaces wiki y rutas de Canvas; respalda los bytes
originales fuera de Git/bóveda. No crea conocimiento ni toca Bases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from lib_ce import WIKI_RE, notes_in_vault, resolve_link, target_index, visible_filename
from operacion import ROOT, index_ids, safe_vault
from validar_boveda import validate


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_spec(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding='utf8'))
    rows = obj.get('notas') if isinstance(obj, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError('Se requiere una lista no vacía de notas')
    if any(not isinstance(x, dict) or not isinstance(x.get('id'), str)
           or not isinstance(x.get('nombre'), str) for x in rows):
        raise ValueError('Cada nota requiere id y nombre legible')
    if len({x['id'] for x in rows}) != len(rows):
        raise ValueError('ID repetido en el plan')
    return rows


def _rewrite_wiki(text: str, vault: Path, renames: dict[Path, Path],
                  paths: dict, names: dict) -> tuple[str, int]:
    count = 0
    def replace(match: re.Match) -> str:
        nonlocal count
        inner = match.group(1)
        target = inner.split('|', 1)[0]
        base, mark, anchor = target.partition('#')
        had_ext = base.endswith('.md')
        resolved = resolve_link(base, paths, names)
        if resolved not in renames:
            return match.group(0)
        new = renames[resolved].relative_to(vault).with_suffix('').as_posix()
        remainder = inner[len(target):]
        count += 1
        prefix = '!' if match.group(0).startswith('!') else ''
        return prefix + '[[' + new + ('.md' if had_ext else '') + (mark + anchor if mark else '') + remainder + ']]'
    return WIKI_RE.sub(replace, text), count


def _build(vault_path: Path, spec_path: Path) -> tuple[dict, dict[Path, bytes], dict[Path, Path]]:
    vault, _ = safe_vault(vault_path)
    if spec_path.resolve().is_relative_to(vault) or spec_path.resolve().is_relative_to(ROOT):
        raise ValueError('El plan privado debe estar fuera de Git y de la bóveda')
    prior = validate(vault)
    if prior['errores']:
        raise ValueError('Bóveda con errores previos: ' + '; '.join(prior['errores'][:3]))
    ids = index_ids(vault)
    renames: dict[Path, Path] = {}
    rows = []
    for row in _read_spec(spec_path):
        old = ids.get(row['id'])
        if old is None or old.is_symlink():
            raise ValueError('ID ausente o simbólico: ' + row['id'])
        new = old.with_name(visible_filename(row['nombre']))
        if new != old:
            renames[old] = new
        rows.append({'id': row['id'], 'anterior': old.relative_to(vault).as_posix(),
                     'propuesta': new.relative_to(vault).as_posix(),
                     'sha_anterior': _sha(old.read_bytes())})
    all_notes = notes_in_vault(vault)
    destinations = [renames.get(p, p).relative_to(vault).as_posix().casefold() for p in all_notes]
    if len(set(destinations)) != len(destinations):
        raise ValueError('Colisión de nombres visibles con otra nota')
    # os.replace sobrescribe destinos existentes: bloquear también intercambios
    # A -> B y B -> A, aunque el conjunto final no tenga duplicados.
    occupied = set(all_notes)
    for old, new in renames.items():
        if new in occupied and new != old:
            raise ValueError('Destino ocupado por otra nota; migrar en etapas sin sobrescribir: '
                             + str(new.relative_to(vault)))
    paths, names = target_index(vault)
    changes: dict[Path, bytes] = {}
    affected = []
    for p in all_notes:
        if p.is_symlink():
            raise ValueError('Nota simbólica no migrable: ' + str(p.relative_to(vault)))
        before = p.read_bytes()
        rewritten, count = _rewrite_wiki(before.decode('utf8'), vault, renames, paths, names)
        after = rewritten.encode('utf8')
        if after != before or p in renames:
            changes[p] = after
            affected.append({'ruta': p.relative_to(vault).as_posix(),
                             'sha_anterior': _sha(before), 'sha_propuesto': _sha(after),
                             'enlaces_actualizados': count})
    # Canvas son vistas derivadas con rutas de archivo; su contenido no es autoridad.
    for p in vault.rglob('*.canvas'):
        if p.is_symlink(): raise ValueError('Canvas simbólico: ' + str(p))
        original = p.read_bytes()
        obj = json.loads(original)
        count = 0
        def visit(value):
            nonlocal count
            if isinstance(value, dict):
                for k, v in value.items():
                    if k == 'file' and isinstance(v, str):
                        old = vault / v
                        if old in renames:
                            value[k] = renames[old].relative_to(vault).as_posix()
                            count += 1
                    else: visit(v)
            elif isinstance(value, list):
                for item in value: visit(item)
        visit(obj)
        if count:
            updated = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()
            changes[p] = updated
            affected.append({'ruta': p.relative_to(vault).as_posix(),
                             'sha_anterior': _sha(original), 'sha_propuesto': _sha(updated),
                             'enlaces_actualizados': count})
    # Otros formatos con rutas exactas requieren un migrador específico.
    old_paths = [p.relative_to(vault).as_posix() for p in renames]
    # Un enlace Markdown normal no debe quedar apuntando a una ruta que cambia.
    # Se bloquea para que el operador lo trate explícitamente con su sintaxis
    # de URL/fragmento, en vez de dejar una referencia rota silenciosa.
    for p in all_notes:
        content = p.read_text(encoding='utf8')
        if any(re.search(r'\]\([^)]*' + re.escape(old) + r'[^)]*\)', content)
               for old in old_paths):
            raise ValueError('Enlace Markdown a ruta antigua no migrable: ' + str(p.relative_to(vault)))
    for p in vault.rglob('*'):
        if not p.is_file() or p.suffix not in {'.base', '.json', '.yaml', '.yml'}:
            continue
        if p.name == 'workspace.json' or '.obsidian' in p.parts:
            continue
        content = p.read_text(encoding='utf8')
        if any(old in content for old in old_paths):
            raise ValueError('Referencia a ruta antigua en formato no migrable: ' + str(p.relative_to(vault)))
    fingerprint = _sha(json.dumps({'notas': rows, 'afectados': affected},
                                  sort_keys=True, ensure_ascii=True).encode())
    report = {'sha_plan': fingerprint, 'notas': rows, 'afectados': affected,
              'renombradas': len(renames), 'archivos_afectados': len(changes),
              'errores_previos': len(prior['errores'])}
    return report, changes, renames


def plan(vault: Path, spec: Path) -> dict:
    return _build(vault, spec)[0]


def apply(vault_path: Path, spec: Path, backup_dir: Path, expected_sha: str) -> dict:
    report, changes, renames = _build(vault_path, spec)
    vault, _ = safe_vault(vault_path)
    backup = backup_dir.expanduser().absolute()
    if report['sha_plan'] != expected_sha:
        raise ValueError('sha_plan obsoleto; regenerar el plan')
    if (backup.exists() or backup == ROOT or backup.is_relative_to(ROOT)
        or backup == vault or backup.is_relative_to(vault) or backup.is_symlink()):
        raise ValueError('Respaldo debe ser ruta privada nueva fuera de Git y bóveda')
    old_bytes = {p: p.read_bytes() for p in changes}
    for item in report['afectados']:
        p = vault / item['ruta']
        if _sha(old_bytes[p]) != item['sha_anterior']:
            raise ValueError('Cambio concurrente: ' + item['ruta'])
    backup.mkdir(parents=True, mode=0o700)
    try:
        for p, data in old_bytes.items():
            dest = backup / p.relative_to(vault)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (backup / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
        for p, data in old_bytes.items():
            if p.read_bytes() != data:
                raise ValueError('Cambio concurrente antes de aplicar: '+str(p.relative_to(vault)))
        for old, new in renames.items():
            os.replace(old, new)
        for old, data in changes.items():
            target = renames.get(old, old)
            temp = target.with_name('.'+target.name+'.tmp-'+uuid4().hex[:8])
            temp.write_bytes(data)
            os.replace(temp, target)
        result = validate(vault)
        if result['errores']:
            raise ValueError('Validación posterior: '+'; '.join(result['errores'][:3]))
    except Exception:
        for old, new in renames.items():
            if new.exists(): new.unlink()
        for p, data in old_bytes.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        raise
    return {**report, 'respaldo': str(backup), 'validacion': 'PASS',
            'reversion': 'Restaurar únicamente archivos del manifiesto tras verificar huellas actuales; no usar git reset.'}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vault', required=True, type=Path)
    ap.add_argument('--spec', required=True, type=Path)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--sha-plan')
    ap.add_argument('--backup-dir', type=Path)
    args = ap.parse_args()
    if args.apply:
        if not args.sha_plan or not args.backup_dir:
            ap.error('--apply requiere --sha-plan y --backup-dir')
        report = apply(args.vault, args.spec, args.backup_dir, args.sha_plan)
    else:
        report = plan(args.vault, args.spec)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
