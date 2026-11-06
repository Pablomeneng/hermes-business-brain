# Skills Group 2 — translation & adaptation verification

Scope: 10 skills (11 files incl. `references/recepcion-v1.md`) translated from Spanish to English and adapted to the Hermes plugin's tool set. Source: `.agents/skills/` of the upstream repo (read-only). All new content is English; Spanish remains only as verbatim identifiers (skill names, CLI flags, JSON keys, path dir names, error/status tokens, product name).

## Per-skill status

| Skill | Translated | Commands rewritten | Unresolved local links | Spanish in prose | Redirected to upstream |
|---|---|---|---|---|---|
| ce-extraer-meetgeek | ok | ok (no runtime commands; tool-less operations contract) | 0 | 0 | `docs/plans/CONTRATO_RECEPCION_V1.md` (via references/recepcion-v1.md → repo root; file is frozen/original-workspace only, not in public repo) |
| ce-extraer-meetgeek/references/recepcion-v1.md | ok | ok | 0 | 0 | `docs/plans/CONTRATO_RECEPCION_V1.md` → repo root pointer; kept literal path components `recepcion/`, `meetgeek/`, `_inventario/` and `banco-transcripciones`, `cerebro-empresarial/` as verbatim contract identifiers |
| ce-evaluar-recurso | ok | ok (none needed) | 0 | 0 | none (technical ref only: `obsmd-projects/obsidian-projects`) |
| ce-evaluar-recuperacion | ok | ok (none needed) | 0 | 0 | none (kept `fork_turns="none"`, `NO_VERIFICADO`, error codes, gate IDs T14/T15/T17–T20/T24/T26–T28) |
| ce-documentacion | ok | ok | 0 | 0 | `metodologia/vNext-1.0R/Catalogo_Documentos_Canonicos_vNext_1_0R.md`, `metodologia/vNext-1.0R/Biblioteca_Prompts_vNext_1_0R.md`, `plantilla_boveda/90_Sistema/Plantillas/`, `docs/RECONSTRUCCION_EDITORIAL_Y_FUENTES.md`, `docs/SINTESIS_EMPRESARIAL_CONSTRUCTIVA.md`, `metodologia/vNext-1.0R/Contrato_Traspaso_Obsidian_Agentes_vNext.md` (all verified to exist upstream on `main`); `plan-conocimiento` → upstream repo pointer (read-only, not bundled) |
| ce-cambios | ok | ok (`python scripts/cerebro.py proponer …` → `brain_create_vault` + verbatim upstream command in parentheses; `validar` → `brain_validate_vault` flow in step 6; `--help` kept) | 0 | 0 | none (upstream `proponer` command shown verbatim as reference) |
| ce-investigacion | ok | ok (none needed) | 0 | 0 | none (kept entity type `investigacion`, `X07`) |
| ce-modelo-relaciones | ok | ok (`python scripts/cerebro.py ficha …` → `brain_create_vault` + verbatim upstream; `validar` → `brain_validate_vault`; `grafo` → Obsidian Graph view) | 0 | 0 | `modelo/tipos_entidad.json`, `metodologia/vNext-1.0R/Contrato_Traspaso_Obsidian_Agentes_vNext.md`, `plan-conocimiento` → upstream repo pointer |
| ce-revisar-antecedentes | ok | ok (none needed) | 0 | 0 | none (kept `TR-ID`, `FTS`, error codes, `D/X`) |
| ce-calidad-repositorio | ok | ok (none needed) | 0 | 0 | `guia/EVOLUCION_PARA_CODEX.md` (verified upstream) |
| obsidian-router | ok (already English) | ok (`scripts/resolver_boveda_codex.py` → `brain_resolve_vault`; `scripts/registrar_boveda_codex.py` → `brain_register_vault`; upstream CLI commands + flags shown verbatim as reference) | 0 | 0 | none (registry/native paths kept verbatim; `--nativo`/`--proyecto` kept as upstream flags) |

## Kept relative cross-links (resolve inside bundled `skills/`; targets verified in source `.agents/skills/`)

- `../ce-banco-transcripciones/references/contrato-comun.md` — ce-extraer-meetgeek, ce-evaluar-recuperacion, ce-revisar-antecedentes
- `../ce-analizar-transcripcion/SKILL.md` — ce-documentacion
- `../ce-revisar-antecedentes/SKILL.md` — ce-cambios, ce-investigacion
- `../ce-cambios/SKILL.md` — ce-revisar-antecedentes
- `references/recepcion-v1.md` — ce-extraer-meetgeek (bundled in the same skill dir)

## Frontmatter

`name:` kept identical for all 10 skills. `description:` translated to English (only prose element of frontmatter that changed).

## Operational invariants preserved (translated, not weakened)

- ce-extraer-meetgeek / recepcion-v1: credentials never in brief nor stored; empty copy = error; inaccessible ≠ downloaded; hash proves bytes, not completeness; single UI/clipboard operator; extractor never promotes originals; no paying/activating services; bank rejection rules (Git tree, vault, symlink escape); atomic-rename sealing manifest.
- ce-evaluar-recuperacion: `NO_VERIFICADO` gate instead of self-evaluation; zero inventions/zero permission violations; critical failure blocks promotion; eval/training separation; private evidence out of Git.
- ce-documentacion: no summary-for-original substitution; sensitivity never lowered to publish; block-ID discipline (`kb:id`), no invented content/blocks; source-over-summary cotejo both directions; gates G1–G7 block promotion only.
- ce-cambios: proposal ≠ decision; no merge engine; reuse of write authorization ≠ editorial ratification; no overwrite for green tests.
- ce-investigacion: hypotheses ≠ facts; rejected content not rehabilitated by websites/summaries; owner opinions ≠ market voice.
- ce-modelo-relaciones: mention ≠ note; generic `related` not authority; graph shows navigation, not truth.
- ce-revisar-antecedentes: no-result search ≠ non-existence; coincidence ≠ causality; contradiction stays open; rejected wording not reintroduced from summaries/web/circular citations.
- ce-calidad-repositorio: no private data in tests without approval; migrations need dry-run/backup/rollback; no dropping/rewriting vNext.

## Notes

- No skill had an explicit "Prohibido" section header; prohibition language was translated inline (per-source) rather than restructured.
- `plan-conocimiento` is not a bundled tool; rendered as upstream product flow used read-only, with an upstream repo pointer in ce-documentacion and ce-modelo-relaciones.
- All upstream blob/tree pointers verified: repo `unsulabs/Obsidian-Bussines-Brain`, branch `main`, paths confirmed by direct fetch of the repo copy and a raw file GET.
- `docs/plans/CONTRATO_RECEPCION_V1.md` does not exist in the public repo (original-workspace contract); pointer goes to the repo root, path kept verbatim.
