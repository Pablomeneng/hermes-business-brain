"""Test-suite bootstrap: put the plugin root on sys.path.

The plugin root carries Hermes' registration ``__init__.py`` (a package only
*inside* Hermes' loader), so it must never be imported as a package by pytest.
This conftest lives inside ``tests/`` (a plain directory, no ``__init__.py``),
so pytest imports it standalone and the plugin module files (``schemas.py``,
``tools.py``) become importable by name.
"""
from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
