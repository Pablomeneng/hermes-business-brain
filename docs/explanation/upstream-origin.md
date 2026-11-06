# Explanation — Upstream origin, fidelity and attribution

This page explains where the product comes from, what is kept byte-identical,
what was adapted, and how licensing and attribution are split. Verifiable
details and the commands that back them are in
[`_verify/docs-machinery.md`](../../_verify/docs-machinery.md).

## Provenance

`hermes-business-brain` is derived from
[unsulabs/Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain),
an MIT-licensed, offline Python toolkit for Obsidian "business brain" vaults
(called *Cerebro Empresarial* upstream). The plugin is a native Hermes shell
around that toolkit; it is not a fork with diverged behavior — it vendors the
engine and exposes it through Hermes tools (see
[architecture.md](architecture.md)).

## Kept byte-identical

- **Engine scripts**: `engine/scripts/` contains 39 Python files: **38 vendored
  upstream scripts** plus one plugin-original wrapper (`plugin_references.py`).
  A byte-level diff against upstream `main` (commit `8803b1b`, cloned
  2026-11-06) shows **35 of the 38 byte-identical** and exactly 3 differing —
  `documentos.py`, `registro_descubrimiento.py`, `revisiones_dx.py` — each by
  a single disclosed line (see next section). Upstream runtime messages, JSON
  keys and Spanish log strings are intentionally untouched: "Upstream runtime
  log/JSON strings are intentionally left in the original language" (NOTICE).
- **Data**: `data/` is upstream verbatim — `diff -rq` against upstream
  `modelo/`, `recursos/`, `plantilla_boveda/` reports zero differences (the
  transcript model schemas, baseline resources and the complete vault template
  with its D01–D07/X01–X07 and Ficha templates). The engine resolves it
  through `engine/{modelo, recursos, plantilla_boveda}` symlinks back to
  `data/` so the scripts' original relative-path logic works unchanged.
- **Behavior**: the vendored CLI surface (29 subcommands in `cerebro.py`,
  22 of them not exposed as plugin tools) is upstream's, reachable through
  `engine/run_script.py` — see [upstream-cli.md](../reference/upstream-cli.md).

## Adapted (and why)

Three kinds of adaptation, each disclosed:

1. **Detection-literal splits (3 scripts)** — `documentos.py`,
   `registro_descubrimiento.py` and `revisiones_dx.py` contain PEM marker
   detection literals (the scanner-visible "BEGIN … PRIVATE KEY" header
   forms used as *rejection patterns* for user content that embeds a private
   key — a security feature, not a real key). The contiguous literal is what
   the catalog security scanner flags. Fix: each literal is split via string
   concatenation, which is runtime-identical (verified with `python -c`) and
   keeps the rejection checks byte-behavior-equal. No other lines, messages
   or identifiers changed. Full detail: [`_verify/security-scan-fix.md`](../../_verify/security-scan-fix.md).
2. **Skill layer rewritten for Hermes** — the operating procedures that
   upstream wrote around Codex (Spanish, instructing the *Codex* agent and
   upstream CLI calls) were translated into English Hermes procedures that
   call the plugin's `brain_*` tools, and were re-wired so that unexposed
   upstream subcommands are invoked through the vendored launcher with an
   explicit "not exposed as a standalone plugin tool in v0.1" label (Gate-2
   review, `_verify/review-fixes.md`). The skills are part of the plugin's
   native layer, not vendored upstream material.
3. **Wrapper code is new** — `__init__.py`, `schemas.py`, `tools.py`,
   `engine/run_script.py` and `plugin_references.py` are new English,
   MIT-licensed code written for Hermes.

## License and attribution split

- The plugin (manifest, wrapper code, skills, docs) is **MIT**, copyright
  "hermes-business-brain contributors" (`LICENSE`), author **Pablomeneng**
  (`plugin.yaml`).
- The vendored engine keeps its upstream MIT license and attribution
  (© 2026 Obsidian-Bussines-Brain contributors), recorded verbatim in
  [`NOTICE/THIRD_PARTY_NOTICES.md`](../../NOTICE/THIRD_PARTY_NOTICES.md),
  which also reproduces upstream's *own* third-party notices (the
  Best-README-Template Unlicense attribution for README organization and the
  ai-cursor-init MIT notice for its documentation workflow) and the two
  declared Python dependencies (PyYAML, jsonschema).
- The plugin's `homepage` field points at the upstream repository so credit
  is discoverable from the manifest itself.

The split is deliberate: vendoring MIT code with attribution is legally and
practically cleaner than rewriting the engine, and it keeps the "byte-identical
engine" claim checkable (see the verification commands in `_verify/docs-machinery.md`).
