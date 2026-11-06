#!/usr/bin/env python3
"""Vendored-engine launcher for the hermes-business-brain plugin.

Runs a vendored upstream script (from ``./scripts``) as a subprocess with its
relative imports intact. The upstream scripts assume their working directory is
the repository root and import siblings directly (``from lib_ce import ...``);
this shim makes that true by putting ``./scripts`` first on ``sys.path`` before
executing the target file with ``runpy`` (which also keeps ``__file__`` correct
so scripts can compute their engine-relative data directories).

Dependency note: the scripts need ``PyYAML`` and ``jsonschema``. The Hermes
process that spawns this subprocess records its own activated dependency
``site-packages`` directories and passes them via the ``BB_SITE_PACKAGES``
environment variable (``os.pathsep``-separated); the shim re-injects them so the
same environment is used. When the variable is absent (development runs, CI),
the interpreter's own ``sys.path`` is used unchanged.

Usage: run_script.py <script-name.py> [args...]
"""
from __future__ import annotations

import os
import runpy
import sys


def _bootstrap() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(here, "scripts")

    # 1. Dependency site-packages inherited from the host Hermes process.
    inherited = os.environ.get("BB_SITE_PACKAGES", "")
    for entry in inherited.split(os.pathsep):
        if entry and os.path.isdir(entry) and entry not in sys.path:
            sys.path.insert(0, entry)

    # 2. The vendored scripts directory, so relative sibling imports resolve.
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_script.py <script-name.py> [args...]", file=sys.stderr)
        return 2
    _bootstrap()
    name = sys.argv[1]
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", name)
    if not os.path.isfile(target):
        print(f"run_script: unknown vendored script: {name}", file=sys.stderr)
        return 2
    sys.argv = [target] + sys.argv[2:]
    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
