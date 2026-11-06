"""Synthetic vault lifecycle test: create -> validate -> status on a temp dir.

Also smoke-tests the transcript pipeline wrapper (read-only ``estado`` step) on
a private bank under a temp dir. Templates and demo data are synthetic by
design — no real business data is ever created.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PLUGIN_ROOT / "engine"
RUN_SCRIPT = ENGINE_DIR / "run_script.py"
PYTHON = sys.executable

COMPANY_ID = "TBI-001"
COMPANY_NAME = "Synthetic Test Company"


def shim(script: str, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(RUN_SCRIPT), script, *argv],
        cwd=str(ENGINE_DIR),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def test_create_validate_status_cycle(tmp_path):
    vault = tmp_path / "vault"

    # brain_create_vault <- cerebro crear
    created = shim("cerebro.py", "crear", "--id", COMPANY_ID,
                   "--nombre", COMPANY_NAME, "--dest", str(vault))
    assert created.returncode == 0, created.stderr
    payload = json.loads(created.stdout)
    assert payload["estado"] == "infraestructura_sin_conocimiento"
    resolved = Path(payload["creada"])
    assert resolved.is_dir() and (resolved / "Inicio.md").is_file()
    assert (resolved / "90_Sistema" / "config_empresa.yaml").is_file()

    # brain_validate_vault <- validar_boveda --json
    checked = shim("validar_boveda.py", "--vault", str(vault), "--json")
    assert checked.returncode == 0, checked.stderr
    validation = json.loads(checked.stdout)
    assert validation["errores"] == []
    assert validation["notas"] >= 7

    # brain_status <- cerebro estado
    status = shim("cerebro.py", "estado", "--vault", str(vault))
    assert status.returncode == 0, status.stderr
    summary = json.loads(status.stdout)
    assert summary["empresa"] == COMPANY_NAME
    assert summary["id_empresa"] == COMPANY_ID
    assert summary["total_notas"] >= 7
    assert summary["plantillas_instaladas"] > 0


def test_handlers_drive_the_same_cycle(tmp_path):
    """Exercise the actual plugin handlers (same args the model would send)."""
    sys.path.insert(0, str(PLUGIN_ROOT))
    try:
        import tools
    finally:
        sys.path.remove(str(PLUGIN_ROOT))

    vault = tmp_path / "vault2"

    result = json.loads(tools.brain_create_vault(
        {"id": COMPANY_ID, "nombre": COMPANY_NAME, "dest": str(vault)}))
    assert result["exit_code"] == 0, result["stderr"]
    assert "Vault created" in result["summary"]

    result = json.loads(tools.brain_validate_vault({"vault": str(vault)}))
    assert result["exit_code"] == 0, result["stderr"]
    assert "0 integrity errors" in result["summary"]

    result = json.loads(tools.brain_status({"vault": str(vault)}))
    assert result["exit_code"] == 0, result["stderr"]
    summary = json.loads(result["stdout"])
    assert summary["empresa"] == COMPANY_NAME and summary["id_empresa"] == COMPANY_ID


def test_transcript_cycle_estado_step(tmp_path):
    """A private custody bank outside vault/Git works for read-only pipeline steps."""
    bank = tmp_path / "bank"
    bank.mkdir(parents=True)
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps({"company_id": "synthetic", "allowed_purposes": ["custody"]}),
        encoding="utf-8",
    )

    proc = shim("transcripciones.py", "estado", "--bank", str(bank),
                "--profile", str(profile), "--request-id", "test-1",
                "--purpose", "custody")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "DONE"
    assert payload["evidence"]["transcriptions"] == 0
    assert payload["operation"] == "estado"

    # Preview only: nothing was written beyond the (empty) bank dir itself.
    assert not list(bank.rglob("*.json"))
