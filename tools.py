"""Tool handlers for hermes-business-brain.

Every handler runs one vendored engine script as a subprocess with the working
directory set to the engine directory (so the scripts resolve their bundled data
and sibling imports), passes user-supplied arguments through ``argv``, and
returns a JSON string with ``stdout``, ``stderr``, ``exit_code`` and an English
``summary``. Handlers never raise: engine failures are returned as JSON.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent / "engine"
_RUN_SCRIPT = _ENGINE_DIR / "run_script.py"
_SCRIPTS_DIR = _ENGINE_DIR / "scripts"

DEFAULT_TIMEOUT = 120  # seconds

# Dependency site-packages active in the host Hermes process (its PM venv),
# re-injected into the subprocess so the vendored scripts see PyYAML/jsonschema.
_SITE_PACKAGES = sorted(
    {
        p
        for p in sys.path
        if p and os.path.isdir(p) and os.path.basename(p.rstrip("/\\")) == "site-packages"
    }
)


def _run(script: str, argv: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run one vendored script and shape the result for the model."""
    env = dict(os.environ)
    if _SITE_PACKAGES:
        env["BB_SITE_PACKAGES"] = os.pathsep.join(_SITE_PACKAGES)
    timed_out = False
    stdout = stderr = ""
    exit_code = -1
    try:
        proc = subprocess.run(
            [sys.executable, str(_RUN_SCRIPT), script, *argv],
            cwd=str(_ENGINE_DIR),
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[tool timeout after {timeout}s]"
    return {
        "tool": _TOOL_FOR_SCRIPT.get(script, script),
        "script": script,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "summary": _summary(script, stdout, stderr, exit_code, timed_out),
    }


def _head(lines_text: str, n: int = 3) -> str:
    return " | ".join(line.strip() for line in lines_text.splitlines() if line.strip())[:400]


def _summary(script: str, stdout: str, stderr: str, exit_code: int, timed_out: bool) -> str:
    """English, human-readable outcome derived from the engine result."""
    if timed_out:
        return f"{script} timed out after {DEFAULT_TIMEOUT}s; no result produced."
    if exit_code == 0:
        extra = ""
        if script == "cerebro.py" and "creada" in stdout:
            try:
                data = json.loads(stdout)
                extra = f" Vault created at {data.get('creada', '?')}."
            except (ValueError, TypeError):
                pass
        elif script == "validar_boveda.py":
            try:
                data = json.loads(stdout)
                errs = data.get("errores", [])
                warns = data.get("advertencias", [])
                extra = (
                    f" {len(errs)} integrity errors, {len(warns)} warnings "
                    f"({data.get('notas', '?')} notes)."
                )
            except (ValueError, TypeError):
                extra = ""
        elif script == "transcripciones.py":
            try:
                data = json.loads(stdout)
                status = data.get("status", "DONE")
                ev = data.get("evidence", {})
                extra = f" Pipeline status: {status}; evidence keys: {', '.join(sorted(ev)) or 'none'}."
            except (ValueError, TypeError):
                extra = ""
        return f"{script} completed successfully (exit 0).{extra}"
    if stderr.strip():
        first = stderr.strip().splitlines()[0]
        return f"{script} failed (exit {exit_code}): {first}"
    if stdout.strip():
        return f"{script} failed (exit {exit_code}). Output: {_head(stdout)}"
    return f"{script} failed (exit {exit_code}) with no output."


def _flags(args: dict, mapping: dict) -> list[str]:
    """Build an argv list from args according to {arg_key: (flag, kind)}."""
    argv: list[str] = []
    for key, (flag, kind) in mapping.items():
        if key not in args or args[key] in (None, "", False):
            continue
        value = args[key]
        if kind == "bool":
            argv.append(flag)
        elif kind == "repeat":
            for item in value:
                argv.extend([flag, str(item)])
        else:
            argv.extend([flag, str(value)])
    return argv


# ---------------------------------------------------------------------------
# cerebro.py subcommands
# ---------------------------------------------------------------------------

def _cerebro(subcommand: str, args: dict, mapping: dict) -> dict:
    argv = [subcommand] + _flags(args, mapping)
    return _run("cerebro.py", argv)


def brain_doctor(args: dict, **kwargs) -> str:
    argv = []
    if args.get("vault"):
        argv = ["--vault", str(args["vault"])]
    return json.dumps(_run("cerebro.py", ["doctor", *argv]))


def brain_create_vault(args: dict, **kwargs) -> str:
    argv = [
        "--id", str(args["id"]),
        "--nombre", str(args["nombre"]),
        "--dest", str(args["dest"]),
    ]
    return json.dumps(_run("cerebro.py", ["crear", *argv]))


def brain_validate_vault(args: dict, **kwargs) -> str:
    argv = ["--vault", str(args["vault"])]
    if args.get("json", True):
        argv.append("--json")
    return json.dumps(_run("validar_boveda.py", argv))


def brain_status(args: dict, **kwargs) -> str:
    return json.dumps(_run("cerebro.py", ["estado", "--vault", str(args["vault"])]))


def brain_query(args: dict, **kwargs) -> str:
    mapping = {
        "vault": ("--vault", "str"),
        "texto": ("--texto", "str"),
        "tema": ("--tema", "str"),
        "ambito": ("--ambito", "str"),
        "fecha": ("--fecha", "str"),
        "limite": ("--limite", "str"),
        "orientar": ("--orientar", "bool"),
    }
    return json.dumps(_cerebro("consulta-contextual", args, mapping))


def brain_capture(args: dict, **kwargs) -> str:
    mapping = {
        "vault": ("--vault", "str"),
        "titulo": ("--titulo", "str"),
        "archivo": ("--archivo", "str"),
        "fuente": ("--fuente", "repeat"),
    }
    return json.dumps(_cerebro("capturar", args, mapping))


def brain_knowledge_map(args: dict, **kwargs) -> str:
    return json.dumps(_run("cerebro.py", ["mapa-conocimiento", "--vault", str(args["vault"])]))


def brain_relations(args: dict, **kwargs) -> str:
    mapping = {"vault": ("--vault", "str"), "id": ("--id", "str")}
    return json.dumps(_cerebro("relaciones", args, mapping))


# ---------------------------------------------------------------------------
# standalone engine scripts
# ---------------------------------------------------------------------------

def brain_register_vault(args: dict, **kwargs) -> str:
    mapping = {
        "vault": ("--vault", "str"),
        "nombre": ("--nombre", "str"),
        "alias": ("--alias", "str"),
        "registro": ("--registro", "str"),
        "nativo": ("--nativo", "str"),
        "instrucciones": ("--instrucciones", "str"),
        "inicio": ("--inicio", "str"),
        "proyecto": ("--proyecto", "str"),
    }
    return json.dumps(_run("registrar_boveda_codex.py", _flags(args, mapping)))


def brain_resolve_vault(args: dict, **kwargs) -> str:
    mapping = {
        "selector": ("--selector", "str"),
        "project": ("--project", "str"),
        "registro": ("--registro", "str"),
        "nativo": ("--nativo", "str"),
    }
    return json.dumps(_run("resolver_boveda_codex.py", _flags(args, mapping)))


def brain_references(args: dict, **kwargs) -> str:
    mapping = {
        "bank": ("--bank", "str"),
        "commit": ("--commit", "bool"),
        "metadata": ("--metadata", "str"),
        "reference_id": ("--reference-id", "str"),
        "version_id": ("--version-id", "str"),
        "refs": ("--refs", "str"),
        "company": ("--company", "str"),
        "audience": ("--audience", "str"),
        "purpose": ("--purpose", "str"),
        "require_internal": ("--require-internal", "bool"),
    }
    argv = [args["action"]] + _flags(args, mapping)
    if args.get("require_read") is False:
        argv.append("--no-require-read")
    return json.dumps(_run("plugin_references.py", argv))


def brain_naming(args: dict, **kwargs) -> str:
    mapping = {
        "vault": ("--vault", "str"),
        "spec": ("--spec", "str"),
        "apply": ("--apply", "bool"),
        "sha_plan": ("--sha-plan", "str"),
        "backup_dir": ("--backup-dir", "str"),
    }
    return json.dumps(_run("nombres_legibles.py", _flags(args, mapping)))


# ---------------------------------------------------------------------------
# transcript pipeline
# ---------------------------------------------------------------------------

_TRANSCRIPT_STEP_FLAGS: dict[str, dict] = {
    "ingresar": {
        "archivo": ("--archivo", "str"),
        "parts_manifest": ("--parts-manifest", "str"),
        "source_id": ("--source-id", "str"),
        "account_id": ("--account-id", "str"),
        "attempt_id": ("--attempt-id", "str"),
        "closed": ("--closed", "bool"),
        "expected_parts": ("--expected-parts", "str"),
    },
    "registrar": {"capture_manifest": ("--capture-manifest", "str")},
    "segmentar": {
        "tr_id": ("--tr-id", "str"),
        "version": ("--version", "str"),
        "policy": ("--policy", "str"),
        "max_core_bytes": ("--max-core-bytes", "str"),
        "context_bytes": ("--context-bytes", "str"),
    },
    "analizar": {"input": ("--input", "str")},
    "cobertura": {"tr_id": ("--tr-id", "str"), "run": ("--run", "str")},
    "indexar": {"snapshot": ("--snapshot", "str")},
    "revisar-antecedentes": {
        "event": ("--event", "str"),
        "snapshot": ("--snapshot", "str"),
        "results": ("--results", "str"),
        "previous": ("--previous", "str"),
        "taxonomy_version": ("--taxonomy-version", "str"),
    },
    "taxonomia": {"input": ("--input", "str"), "event": ("--event", "str")},
    "permiso": {"input": ("--input", "str")},
    "estado": {},
    "verificar": {},
    "inventario-validar": {"snapshot": ("--snapshot", "str")},
    "conciliar": {"snapshot": ("--snapshot", "str")},
    "buscar": {"request": ("--request", "str")},
}

# Steps that require an audience per the upstream CLI.
_AUDIENCE_REQUIRED = {"segmentar", "analizar", "cobertura", "indexar", "revisar-antecedentes"}


def brain_transcript_cycle(args: dict, **kwargs) -> str:
    step = args["step"]
    argv = [step, "--bank", str(args["bank"]), "--profile", str(args["profile"]),
            "--purpose", str(args["purpose"])]
    if args.get("request_id"):
        argv += ["--request-id", str(args["request_id"])]
    else:
        argv += ["--request-id", f"hermes-brain-{int(time.time())}-{uuid.uuid4().hex[:8]}"]
    if args.get("commit"):
        argv.append("--commit")
    if args.get("audience"):
        argv += ["--audience", str(args["audience"])]
    if args.get("output"):
        argv += ["--output", str(args["output"])]
    argv += _flags(args, _TRANSCRIPT_STEP_FLAGS.get(step, {}))
    return json.dumps(_run("transcripciones.py", argv))


_TOOL_FOR_SCRIPT = {
    "cerebro.py": "brain_* (cerebro)",
    "validar_boveda.py": "brain_validate_vault",
    "registrar_boveda_codex.py": "brain_register_vault",
    "resolver_boveda_codex.py": "brain_resolve_vault",
    "nombres_legibles.py": "brain_naming",
    "plugin_references.py": "brain_references",
    "transcripciones.py": "brain_transcript_cycle",
}

HANDLERS = {
    "brain_doctor": brain_doctor,
    "brain_create_vault": brain_create_vault,
    "brain_validate_vault": brain_validate_vault,
    "brain_status": brain_status,
    "brain_register_vault": brain_register_vault,
    "brain_resolve_vault": brain_resolve_vault,
    "brain_query": brain_query,
    "brain_capture": brain_capture,
    "brain_knowledge_map": brain_knowledge_map,
    "brain_relations": brain_relations,
    "brain_references": brain_references,
    "brain_naming": brain_naming,
    "brain_transcript_cycle": brain_transcript_cycle,
}
