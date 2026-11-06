"""Engine-level tests: vendored engine imports directly and brain_doctor works."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PLUGIN_ROOT / "engine"
SCRIPTS_DIR = ENGINE_DIR / "scripts"
RUN_SCRIPT = ENGINE_DIR / "run_script.py"

PYTHON = sys.executable


@pytest.fixture(scope="module", autouse=True)
def scripts_on_path():
    """Make the vendored scripts importable as plain modules (their sibling
    imports resolve because the scripts dir is first on sys.path)."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    yield
    if str(SCRIPTS_DIR) in sys.path:
        sys.path.remove(str(SCRIPTS_DIR))


def run_shim(script: str, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(RUN_SCRIPT), script, *argv],
        cwd=str(ENGINE_DIR),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def test_vendored_scripts_copied_intact():
    """All 38 upstream scripts plus the references wrapper are present."""
    expected = {
        "cerebro.py", "lib_ce.py", "platform_fs.py", "operacion.py", "crear_instancia.py",
        "validar_boveda.py", "consulta_contextual.py", "registro_descubrimiento.py",
        "mapa_conocimiento.py", "documentos.py", "relaciones.py", "referencias_externas.py",
        "nombres_legibles.py", "resolver_boveda_codex.py", "registrar_boveda_codex.py",
        "doctor_preflight.py", "windows_fs.py", "transcripciones.py",
        "importar_traspaso.py", "exportar_grafo.py", "plan_conocimiento.py",
        "revision_editorial.py", "aceptacion_piloto.py", "lib_canvas.py",
        "revisiones_dx.py", "transcripciones_analisis.py", "transcripciones_antecedentes.py",
        "transcripciones_contexto.py", "transcripciones_custodia.py", "transcripciones_indice.py",
        "transcripciones_ingreso.py", "transcripciones_inventario.py",
        "transcripciones_lectura.py", "transcripciones_modelo.py",
        "transcripciones_permisos.py", "transcripciones_pipeline.py",
        "transcripciones_segmentacion.py", "transcripciones_taxonomia.py",
        "plugin_references.py",
    }
    present = {p.name for p in SCRIPTS_DIR.glob("*.py")}
    assert expected <= present


def test_engine_data_layout():
    """Engine-relative data dirs (modelo, recursos, plantilla_boveda) resolve."""
    for name in ("modelo", "recursos", "plantilla_boveda"):
        target = ENGINE_DIR / name
        assert target.is_dir(), f"missing engine/{name}"
        # The scripts compute ROOT = engine/.. and read these paths.
        for probe in (ENGINE_DIR / "modelo" / "tipos_entidad.json",
                      ENGINE_DIR / "recursos" / "bases_baseline.json",
                      ENGINE_DIR / "plantilla_boveda" / "Inicio.md"):
            assert probe.is_file(), f"missing data file {probe}"


def test_doctor_preflight_imports_directly():
    """brain_doctor's engine module imports and runs standalone."""
    import doctor_preflight

    report = doctor_preflight.diagnose(vault=None)
    assert report["producto"]
    assert "dependencias_python" in report and "yaml" in report["dependencias_python"]
    assert "python" in report and "so" in report


def test_doctor_via_shim():
    """The script launcher runs cerebro doctor and emits the JSON report."""
    proc = run_shim("cerebro.py", "doctor")
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["producto"]
    assert report["dependencias_python"]["yaml"] == "LOCALIZADO"


def test_brain_doctor_handler():
    """The registered handler shape: stdout/stderr/exit_code + English summary."""
    import tools

    result = json.loads(tools.brain_doctor({"vault": None}))
    assert result["exit_code"] == 0
    assert "summary" in result and "completed successfully" in result["summary"]
    payload = json.loads(result["stdout"])
    assert "producto" in payload
