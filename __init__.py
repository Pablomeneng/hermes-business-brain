"""hermes-business-brain — Hermes plugin registration entry point.

Wires the 13 canonical tools (schemas -> handlers) and registers any bundled
skills found under ``skills/`` as read-only plugin skills
(``hermes-business-brain:<name>``). The skills directory may be empty or
partially populated while parallel build steps are still writing to it; missing
or malformed skill entries are skipped with a log line and never fail loading.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TOOLSET = "business_brain"

# name -> (handler, schema); order follows the canonical tool list.
_TOOL_SPECS = [
    ("brain_doctor", "brain_doctor", "BRAIN_DOCTOR"),
    ("brain_create_vault", "brain_create_vault", "BRAIN_CREATE_VAULT"),
    ("brain_validate_vault", "brain_validate_vault", "BRAIN_VALIDATE_VAULT"),
    ("brain_status", "brain_status", "BRAIN_STATUS"),
    ("brain_register_vault", "brain_register_vault", "BRAIN_REGISTER_VAULT"),
    ("brain_resolve_vault", "brain_resolve_vault", "BRAIN_RESOLVE_VAULT"),
    ("brain_query", "brain_query", "BRAIN_QUERY"),
    ("brain_capture", "brain_capture", "BRAIN_CAPTURE"),
    ("brain_knowledge_map", "brain_knowledge_map", "BRAIN_KNOWLEDGE_MAP"),
    ("brain_relations", "brain_relations", "BRAIN_RELATIONS"),
    ("brain_references", "brain_references", "BRAIN_REFERENCES"),
    ("brain_naming", "brain_naming", "BRAIN_NAMING"),
    ("brain_transcript_cycle", "brain_transcript_cycle", "BRAIN_TRANSCRIPT_CYCLE"),
]


def register(ctx):
    """Register tools and bundled skills. Runs once at plugin load."""
    # Deferred import: the plugin directory is only a package inside Hermes'
    # loader namespace. When this module is imported standalone (dev runs,
    # pytest), fall back to a top-level import of the sibling modules.
    try:
        from . import schemas, tools
    except ImportError:
        import schemas  # type: ignore
        import tools  # type: ignore

    for name, handler_name, schema_name in _TOOL_SPECS:
        handler = getattr(tools, handler_name)
        schema = getattr(schemas, schema_name)
        try:
            ctx.register_tool(
                name=name,
                toolset=TOOLSET,
                schema=schema,
                handler=handler,
                description=schema.get("description", ""),
            )
        except Exception as exc:  # never let one tool break the whole plugin
            logger.error("hermes-business-brain: failed to register tool %s: %s", name, exc)
    _register_skills(ctx)


def _register_skills(ctx) -> None:
    """Register every ``skills/<dir>/SKILL.md`` as a plugin skill.

    Tolerates an empty or partially populated skills directory: entries that
    are missing, unreadable, or fail registration are skipped with a log line.
    """
    skills_dir = Path(__file__).resolve().parent / "skills"
    if not skills_dir.is_dir():
        logger.info("hermes-business-brain: no skills directory; skipping skill registration")
        return
    found = 0
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            logger.info("hermes-business-brain: skills/%s has no SKILL.md; skipping", child.name)
            continue
        try:
            ctx.register_skill(child.name, skill_md, description=_skill_description(skill_md))
            found += 1
        except Exception as exc:
            logger.warning("hermes-business-brain: could not register skill %s: %s", child.name, exc)
    logger.info("hermes-business-brain: registered %d bundled skill(s)", found)


def _skill_description(skill_md: Path) -> str:
    """Best-effort English description from the SKILL.md YAML frontmatter."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        if text.lstrip().startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                for line in text[3:end].splitlines():
                    if line.startswith("description:"):
                        return line.split(":", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""
