"""Registration contract: 13 canonical tools registered, skills tolerated."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class FakeCtx:
    """Minimal stand-in for Hermes' plugin context."""

    def __init__(self):
        self.tools = []
        self.skills = []

    def register_tool(self, name, toolset, schema, handler, description="", **kwargs):
        assert toolset == "business_brain"
        assert callable(handler)
        assert isinstance(schema, dict) and schema.get("description")
        self.tools.append(name)

    def register_skill(self, name, path, description="", **kwargs):
        assert Path(path).is_file()
        self.skills.append(name)


def _load_plugin():
    spec = importlib.util.spec_from_file_location("bb_plugin_under_test", PLUGIN_ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANONICAL_TOOLS = [
    "brain_doctor", "brain_create_vault", "brain_validate_vault", "brain_status",
    "brain_register_vault", "brain_resolve_vault", "brain_query", "brain_capture",
    "brain_knowledge_map", "brain_relations", "brain_references", "brain_naming",
    "brain_transcript_cycle",
]


def test_registers_exactly_the_13_canonical_tools():
    plugin = _load_plugin()
    ctx = FakeCtx()
    plugin.register(ctx)
    assert sorted(ctx.tools) == sorted(CANONICAL_TOOLS)


def test_registers_every_skill_dir_with_skil_md():
    plugin = _load_plugin()
    ctx = FakeCtx()
    plugin.register(ctx)
    present = sorted(p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
    assert set(ctx.skills) == set(present)


def test_missing_skills_dir_is_tolerated(tmp_path, monkeypatch):
    monkeypatch.chdir(PLUGIN_ROOT)
    # Point the loader at a non-existent skills dir by faking __file__ location:
    # simplest: temporarily rename the real skills dir.
    real = PLUGIN_ROOT / "skills"
    moved = tmp_path / "skills-moved"
    real.rename(moved)
    try:
        plugin = _load_plugin()
        ctx = FakeCtx()
        plugin.register(ctx)  # must not raise
        assert len(ctx.tools) == 13
        assert ctx.skills == []
    finally:
        moved.rename(real)
