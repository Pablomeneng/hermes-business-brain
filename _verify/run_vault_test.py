#!/usr/bin/env python3
"""Verification driver: exercise the real plugin handlers end to end.

Creates a synthetic vault, validates it, and prints its status via the exact
handler code paths the model would use. Output is appended to _verify logs.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

import tools  # noqa: E402

LOG = Path(__file__).resolve().parents[1] / "_verify" / "vault_test.log"


def main() -> int:
    lines = []
    tmp = tempfile.mkdtemp(prefix="bb-verify-")
    vault = Path(tmp) / "vault"
    lines.append("Synthetic vault test run (real plugin handlers)")
    lines.append(f"temp root : {tmp}")
    lines.append(f"vault     : {vault}")
    lines.append(f"python    : {sys.executable}")
    lines.append("=" * 72)

    r = json.loads(tools.brain_create_vault(
        {"id": "VERIFY-001", "nombre": "Verify Test Company", "dest": str(vault)}))
    lines.append(f"[1] brain_create_vault exited={r['exit_code']} timed_out={r['timed_out']}")
    lines.append(f"    summary: {r['summary']}")
    lines.append(f"    stdout : {r['stdout'].strip()[:300]}")

    r = json.loads(tools.brain_validate_vault({"vault": str(vault)}))
    lines.append(f"[2] brain_validate_vault exited={r['exit_code']}")
    lines.append(f"    summary: {r['summary']}")
    v = json.loads(r["stdout"])
    lines.append(f"    errores={len(v['errores'])} advertencias={len(v['advertencias'])} "
                 f"notas={v['notas']} bloques={v['bloques']} traspasos={v['traspasos']}")

    r = json.loads(tools.brain_status({"vault": str(vault)}))
    lines.append(f"[3] brain_status exited={r['exit_code']}")
    lines.append(f"    summary: {r['summary']}")
    s = json.loads(r["stdout"])
    lines.append(f"    empresa={s['empresa']!r} id={s['id_empresa']!r} "
                 f"total_notas={s['total_notas']} plantillas={s['plantillas_instaladas']}")

    text = "\n".join(lines) + "\n"
    LOG.write_text(text, encoding="utf-8")
    print(text)
    return 0 if (r["exit_code"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
