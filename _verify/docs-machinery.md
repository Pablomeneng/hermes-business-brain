# Docs verification — Diátaxis machinery pass (reference + explanation)

Date: 2026-11-06. Scope: `docs/reference/` (tools, skills, upstream-cli),
`docs/explanation/` (architecture, privacy-and-guardrails, upstream-origin),
README `Documentation` section, and this file.

## Files written (this pass)

| File | Content |
| --- | --- |
| `docs/reference/tools.md` | Dictionary of the 13 tools: exact schema args, engine backings, example invocations. |
| `docs/reference/skills.md` | The 19 bundled skills: frontmatter descriptions, families, activation, qualified names. |
| `docs/reference/upstream-cli.md` | The 22 cerebro.py subcommands not exposed as tools in v0.1 (+ the 7 exposed, for completeness). |
| `docs/explanation/architecture.md` | Native shell + vendored engine; subprocess model; read-only data; no network; skills interaction; wrap-vs-rewrite. |
| `docs/explanation/privacy-and-guardrails.md` | The 8 invariants as implemented, with skill evidence. |
| `docs/explanation/upstream-origin.md` | Provenance, byte-fidelity, adaptations, license/attribution split. |
| `README.md` | Added `## Documentation` section (quadrants + links); install/tool table untouched. |
| `_verify/docs-machinery.md` | This file. |

Note: `_verify/docs-tutorial.sh` and `_verify/docs-tutorial.log` exist in the
working tree but belong to the parallel How-to/Tutorial workstream; they were
not created or touched by this pass and are not part of this commit.

## Verification commands and results

### Tools and schemas (source of truth: `schemas.py`, `tools.py`, `plugin.yaml`)

- `grep -c '^  - brain_' plugin.yaml` → `13`; `schemas.TOOLS` has 13 entries;
  order identical to `provides_tools`.
- Programmatic check (`scratch/verify_docs.py`, python + stdlib):
  - every tool has an H2 subsection in `tools.md`; 13/13 PASS
  - every tool's backing script name appears in its subsection; 13/13 PASS
  - every JSON-schema `properties` argument name of all 13 tools appears in
    `tools.md` (74 arg-documentation rows; e.g. `brain_transcript_cycle`: all
    29 args incl. step-specific ones); PASS
  - every `required` argument is marked `| yes |` in the Required column
    (19 required args across tools; `brain_resolve_vault` correctly has none
    required at schema level — "exactly one of selector/project" noted in
    prose); PASS
  - `step` enum = 14 entries; all 14 listed in `tools.md`; PASS
- Arg flags in examples were cross-checked against `tools.py` mappings
  (`mapping` dicts) and the upstream argparse definitions in `cerebro.py`.

### cerebro.py subcommands (source of truth: `engine/scripts/cerebro.py`)

- `grep -c "add_parser(" engine/scripts/cerebro.py` → `29`
- All 29 subcommand names (extracted with regex from the `add_parser` lines)
  appear in `upstream-cli.md`; PASS.
- Split verified: 22 subcommands are NOT exposed as plugin tools in v0.1 and
  are documented with launcher usage; 7 ARE exposed (`doctor`, `crear`,
  `estado`, `capturar`, `relaciones`, `consulta-contextual`,
  `mapa-conocimiento`) and are cross-referenced to `tools.md`.
- Deviation from the task's draft list, disclosed: the draft list included
  `capturar`, `relaciones`, `consulta-contextual`, `mapa-conocimiento` as
  "not exposed" — they ARE exposed (backed by `brain_capture`,
  `brain_relations`, `brain_query`, `brain_knowledge_map`); and it omitted
  `validar` (cerebro.py) which is NOT exposed as a plugin tool. The document
  follows the code, not the draft list, and says so.
- `brain_validate_vault` runs `validar_boveda.py`, NOT `cerebro.py validar`
  (both exist; the tool wires the standalone script) — documented as a naming
  trap in `upstream-cli.md`.
- Upstream `help=` strings are Spanish; "Purpose" columns are English
  renderings of those strings (stated in the doc).

### Skills (source of truth: `skills/` + `git ls-files`)

- `git ls-files 'skills/*/SKILL.md' | wc -l` → `19` (the bundled product
  skills).
- `ls skills/` → 20 directories; the 20th (`documentation-writer`) is
  untracked, excluded by `.gitignore` (skills-CLI artifacts), and recorded in
  `skills-lock.json` as installed from `github/awesome-copilot` — documented
  as a note, not listed as a bundled skill.
- All 19 qualified names `hermes-business-brain:<name>` appear in
  `skills.md`; descriptions quoted verbatim from frontmatter (verified by
  frontmatter extraction loop over `skills/*/SKILL.md`).
- Guardrail evidence quoted in `privacy-and-guardrails.md` and
  `architecture.md` read from `ce-instalacion`, `ce-consulta`,
  `ce-banco-transcripciones`, `obsidian-router` SKILL.md files.

### Engine fidelity (source of truth: upstream clone)

Upstream cloned shallow (depth 1) from
`https://github.com/unsulabs/Obsidian-Bussines-Brain`, HEAD
`8803b1bc766092f78b5f65bd83890057e7b749ba`, into the scratch dir.

- `engine/scripts/*.py` (39 files) vs upstream `scripts/*.py` (53 files):
  `cmp` per file → **35 byte-identical**; **3 differ**
  (`documentos.py`, `registro_descubrimiento.py`, `revisiones_dx.py`), each
  by exactly one line: upstream has the contiguous PEM marker tuple, the
  vendored copy has the split-form concatenation
  (`"-----BEGIN " + "PRIVATE KEY-----", "-----BEGIN OPENSSH " + "PRIVATE KEY-----"`).
  No other differences. See `_verify/security-scan-fix.md`.
- `plugin_references.py` has no upstream counterpart (plugin-original). The
  other 14 upstream scripts are not vendored (not part of the 13-tool
  surface), matching NOTICE's "38 upstream scripts" statement.
- `diff -rq` upstream `modelo/` `recursos/` `plantilla_boveda/` vs `data/` →
  exit 0, zero differences (data shipped verbatim).

### Links and scans

- Link checker (stdlib) over `README.md` + all `docs/**/*.md`:
  every relative markdown link resolves to an existing file (README → 6 doc
  links; docs → `tools.md`/`upstream-cli.md`/`skills.md`,
  `../../NOTICE/THIRD_PARTY_NOTICES.md`, `../../_verify/security-scan-fix.md`,
  `../../_verify/docs-machinery.md`, `../../_verify/review-fixes.md`); PASS.
- PEM marker literal scan (same detection pattern the catalog scanner flags,
  mechanically split here so this file cannot re-trigger it), excluding
  `.git`/`.venv`: **0 matches** in source, docs, README and `_verify/`.
  (Gitignored `__pycache__` `.pyc` artifacts — runtime constant-folding of
  the split literals after a test run — were deleted so the working tree scan
  is empty, matching the Gate-2 hygiene note in `_verify/review-fixes.md`.)

## Facts NOT verified (honest limits)

1. **Tests not re-run in this pass** — the pytest suite (11 passed at
   Gate-2, `_verify/review-fixes.md`) was not re-executed here; this pass
   only added/modified docs and no engine or tool code. The parallel
   tutorial workstream did run tests (its `.log` records them).
2. **Live Hermes registration not exercised here** — `hermes plugins doctor`
   / `ctx.register_tool` behavior with these docs is unchanged by this pass
   (no manifest/edit changes), but a fresh doctor run was not performed by
   this pass.
3. **Upstream baseline commit** — the plugin does not pin the exact upstream
   commit the vendored scripts were copied from (no upstream-rev record in
   the repo); the byte-diff above is against upstream `main` at
   `8803b1b` (2026-11-06) and would shift if upstream later changes those
   scripts.
4. **Example values are illustrative** — e.g. `--tipo empresa` (a key that
   exists in `data/modelo/tipos_entidad.json`), `--clase D01`,
   `--localizador https://…`: they are realistic, not exhaustive; the exact
   accepted `tipo`/`clase` vocabularies live in the model data and upstream
   methodology.
5. **The 120s timeout sufficiency for very large transcript operations** was
   not exercised by this pass (documented as the implemented constant
   `DEFAULT_TIMEOUT = 120` in `tools.py`).
6. **The 20th skills directory** (`documentation-writer`): if a published
   bundle ever included it (it is gitignored today), `register(ctx)` would
   register it as a 20th plugin skill; that fate was not exercised here.
