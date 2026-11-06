#!/usr/bin/env python3
"""Registrar una bóveda ya abierta en Obsidian para el router local de Codex.

No crea ni modifica la bóveda ni el registro nativo de Obsidian. Requiere que
Obsidian ya haya asignado un ID a la ruta; sólo actualiza el selector de Codex.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from platform_fs import is_link_or_reparse


REGISTRY = Path.home() / ".codex" / "obsidian" / "vaults.json"
def native_registry_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/obsidian/obsidian.json"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming") / "obsidian/obsidian.json"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "obsidian/obsidian.json"


NATIVE = native_registry_path()
FORMAT = "codex-obsidian-vaults/1"


def canonical(value: str | Path) -> Path:
    path = Path(os.path.abspath(os.path.expanduser(str(value))))
    if sys.platform == "darwin":
        for alias in ("/tmp", "/var"):
            if path == Path(alias) or Path(alias) in path.parents:
                path = Path("/private") / path.relative_to("/")
                break
    for item in (path, *path.parents):
        if is_link_or_reparse(item):
            raise ValueError(f"Ruta con enlace simbólico: {item}")
    return path


def read_json(path: Path) -> dict:
    path = canonical(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"JSON inexistente o inseguro: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON no es objeto: {path}")
    return value


def safe_relative(value: str) -> str:
    part = Path(value)
    if not value or part.is_absolute() or PureWindowsPath(value).drive or ".." in part.parts or "\\" in value:
        raise ValueError(f"Ruta relativa insegura: {value}")
    return value


def write_registry(registry_path: Path, registry: dict, original: bytes | None) -> dict:
    output = (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if original is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = registry_path.with_name(f"{registry_path.name}.{stamp}.bak")
        with backup.open("xb") as stream:
            stream.write(original)
    else:
        backup = None
    with tempfile.NamedTemporaryFile(dir=registry_path.parent, prefix=".vaults-",
                                     delete=False) as stream:
        temp_path = Path(stream.name)
        os.chmod(temp_path, 0o600)
        stream.write(output)
    try:
        current = registry_path.read_bytes() if registry_path.exists() else None
        if current != original:
            raise ValueError("El registro de Codex cambió durante la operación; no se sobrescribió")
        os.replace(temp_path, registry_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return {"sha256_registro": hashlib.sha256(output).hexdigest(),
            "respaldo": str(backup) if backup else None}


def check_project_collision(entries: list, project: Path, own_entry: dict | None) -> None:
    for entry in entries:
        if entry is own_entry:
            continue
        projects = entry.get("projects", [])
        if not isinstance(projects, list) or not all(isinstance(item, str) for item in projects):
            raise ValueError("Asociaciones de proyecto inválidas en el registro")
        for item in projects:
            other = canonical(item)
            if project == other or project in other.parents or other in project.parents:
                raise ValueError("El proyecto colisiona con la asociación de otra bóveda")


def register(vault: Path, name: str, alias: str, registry_path: Path,
             native_path: Path, instructions: str, entrypoint: str,
             project: Path | None = None) -> dict:
    vault = canonical(vault)
    if not vault.is_dir():
        raise ValueError(f"Bóveda inexistente: {vault}")
    if not name.strip() or not alias.strip():
        raise ValueError("Nombre y alias no pueden estar vacíos")
    if project is not None:
        project = canonical(project)
        if not project.is_dir():
            raise ValueError(f"Proyecto inexistente: {project}")

    native = read_json(native_path)
    native_vaults = native.get("vaults")
    if not isinstance(native_vaults, dict):
        raise ValueError("Registro nativo de Obsidian inválido")
    matches = [ident for ident, entry in native_vaults.items()
               if isinstance(entry, dict) and isinstance(entry.get("path"), str)
               and Path(entry["path"]).is_absolute() and canonical(entry["path"]) == vault]
    if len(matches) != 1:
        raise ValueError("Abre primero la carpeta como bóveda en Obsidian; se requiere un único ID nativo")
    ident = matches[0]

    for relative in (instructions, entrypoint):
        target = canonical(vault / safe_relative(relative))
        if not target.is_relative_to(vault) or not target.is_file():
            raise ValueError(f"Falta archivo de la instancia: {relative}")

    registry_path = canonical(registry_path)
    if registry_path.is_symlink():
        raise ValueError("Registro de Codex con enlace simbólico")
    original = registry_path.read_bytes() if registry_path.exists() else None
    if original is not None:
        registry = read_json(registry_path)
        if registry.get("format") != FORMAT or not isinstance(registry.get("vaults"), list):
            raise ValueError("Formato del registro de Codex desconocido")
    else:
        registry = {"format": FORMAT, "vaults": []}

    entries = registry["vaults"]
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Entrada inválida en el registro de Codex")
        if entry.get("path") == str(vault) and entry.get("id") == ident:
            if (entry.get("name") == name and alias in entry.get("aliases", [])
                    and entry.get("instructions") == instructions
                    and entry.get("entrypoint") == entrypoint):
                if project is not None:
                    projects = entry.get("projects", [])
                    if not isinstance(projects, list) or not all(isinstance(item, str) for item in projects):
                        raise ValueError("Asociaciones de proyecto inválidas en el registro")
                    check_project_collision(entries, project, entry)
                    if project not in [canonical(item) for item in projects]:
                        entry["projects"] = [*projects, str(project)]
                        return {"status": "proyecto_asociado", "vault": str(vault),
                                "id": ident, "proyecto": str(project),
                                **write_registry(registry_path, registry, original)}
                return {"status": "ya_registrada", "vault": str(vault), "id": ident}
            raise ValueError("La bóveda ya está registrada con otros datos; revisar antes de modificar")
        existing_tokens = [entry.get("name"), entry.get("id"), entry.get("path"),
                           *entry.get("aliases", [])]
        new_tokens = [name, alias, ident, str(vault)]
        if any(isinstance(a, str) and isinstance(b, str) and a.casefold() == b.casefold()
               for a in existing_tokens for b in new_tokens):
            raise ValueError("Nombre, alias, ruta o ID colisiona con otra bóveda")

    if project is not None:
        check_project_collision(entries, project, None)
    entries.append({"name": name, "id": ident, "aliases": [alias],
                    "path": str(vault), "instructions": instructions,
                    "entrypoint": entrypoint,
                    "projects": [str(project)] if project is not None else []})
    return {"status": "registrada", "vault": str(vault), "id": ident,
            **write_registry(registry_path, registry, original)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--alias", required=True, help="ID empresarial, por ejemplo EMPRESA-001")
    parser.add_argument("--registro", type=Path, default=REGISTRY)
    parser.add_argument("--nativo", type=Path, default=NATIVE)
    parser.add_argument("--instrucciones", default="90_Sistema/Como_usar.md")
    parser.add_argument("--inicio", default="Inicio.md")
    parser.add_argument("--proyecto", type=Path,
                        help="Directorio del proyecto Codex que debe resolver esta bóveda")
    args = parser.parse_args()
    try:
        result = register(args.vault, args.nombre, args.alias, args.registro,
                          args.nativo, args.instrucciones, args.inicio, args.proyecto)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        result = {"status": "error", "error": str(exc)}
        code = 2
    else:
        code = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
