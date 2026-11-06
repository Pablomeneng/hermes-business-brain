# skills-group1 verification

English-adapted Hermes skill bundle, group 1 (9 skills + 3 references). Written under `hermes_business_brain/skills/` following the `ctx.register_skill` layout (one dir per skill, `SKILL.md` with frontmatter `name:` identical to source, optional `references/`).

## Per-skill status

| Skill | Translated | Commands rewritten | Unresolved local links | Leftover Spanish in prose | Redirected to upstream |
|---|---|---|---|---|---|
| ce-instalacion | ok | ok (`brain_doctor`, `brain_create_vault`, `brain_validate_vault`, `brain_register_vault --vault/--nombre/--alias`, `brain_resolve_vault --selector`) | 0 | 0 | guia/ACEPTACION_REAL_CODEX_INSTANCIA_EXISTENTE.md, guia/PRIMERA_EMPRESA_CON_CODEX.md |
| ce-descubrimiento | ok | ok (`brain_capture`, `brain_status`, `brain_validate_vault`; `plan-conocimiento` → labeled upstream CLI subcommand) | 0 | 0 | guia/PRIMERA_EMPRESA_CON_CODEX.md, docs/RECONSTRUCCION_EDITORIAL_Y_FUENTES.md, docs/SINTESIS_EMPRESARIAL_CONSTRUCTIVA.md, docs/CAPTURA_PROGRESIVA.md, scripts/cerebro.py |
| ce-desarrollo-empresa | ok | ok (`brain_create_vault`, `brain_status`, `brain_validate_vault`) | 0 | 0 | docs/FLUJO_EMPRESA_COMPLETA.md, docs/MARKETING_EMPRESARIAL.md, docs/CRITERIOS_DE_ACEPTACION.md |
| ce-consulta | ok | ok (`brain_query --orientar/--texto`, `brain_resolve_vault`, `brain_status`, `brain_validate_vault`; `buscar`/`autoridad --tema/--ambito/--fecha` → labeled upstream CLI subcommands) | 0 | 0 | scripts/cerebro.py |
| ce-continuidad | ok | ok (`brain_status`, `brain_validate_vault`, `brain_resolve_vault`; `continuidad --vault/--resumen/--siguiente/--revisado-por` → labeled upstream CLI subcommand) | 0 | 0 | guia/ACEPTACION_REAL_CODEX_INSTANCIA_EXISTENTE.md, scripts/cerebro.py |
| ce-arquitectura-conocimiento | ok | ok (`brain_knowledge_map`; `plan-conocimiento --vault/--archivo`, `ficha --archivo/--etiqueta`, `documento --etiqueta`, `previsualizar-dx`, `publicar-mapa` → labeled upstream CLI subcommands) | 0 | 0 | docs/ARQUITECTURA_CONOCIMIENTO_ANTES_DE_REDACTAR.md, ejemplos/planes_conocimiento/plan_empresa_sintetica.json, scripts/cerebro.py |
| ce-taxonomia-conocimiento | ok | ok (no mapped commands in source) | 0 | 0 | none (antecedentes → relative: sibling bundled) |
| ce-banco-transcripciones | ok | ok (`brain_transcript_cycle` for pipeline; flags/contracts preserved) | 0 | 0 | none |
| ce-banco-transcripciones/references/flujo-predeterminado.md | ok | ok (`brain_resolve_vault --selector/--project`, `brain_register_vault`, `brain_transcript_cycle`; upstream `transcripciones_*.py` APIs labeled as upstream, not claimed as Hermes tools) | 0 | 0 | none (sibling refs relative: obsidian-router, ce-revisar-antecedentes bundled) |
| ce-banco-transcripciones/references/destino-privado.md | ok | ok (`brain_resolve_vault`) | 0 | 0 | none |
| ce-banco-transcripciones/references/contrato-comun.md | ok | ok (`brain_resolve_vault`, `brain_transcript_cycle`) | 0 | 0 | none |
| ce-analizar-transcripcion | ok | ok (no mapped commands in source) | 0 | 0 | none |

Totals: 12 files written; 0 unresolved local links; 0 Spanish residue in prose.

## Notes / decisions

- **Verbatim tokens kept** (per instructions: identifiers, enums, JSON keys, flag names, links): frontmatter `name:` values; skill dir names; `--vault`, `--nombre`, `--alias`, `--selector`, `--project`, `--orientar`, `--texto`, `--archivo`, `--etiqueta`, `--tema`, `--ambito`, `--fecha`, `--resumen`, `--siguiente`, `--revisado-por`; status enums (`pendiente`/`verificada`/`corrupta`, `borrador`/`propuesta`/`en_revision`/`ratificado`/`rechazado`, `desconocido`/`permitido`/`denegado`/`revocado`, `DONE`/`DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED`, `PENDIENTE_IMPLEMENTACION`, `NO VERIFICADO`, `sin_archivo_generado`, `leida_completa`); sensitivity enums `interno`/`confidencial`/`restringido`; JSON keys `responsable`/`referencia`, `company_id`, `allowed_purposes`, `bank`, `vault`, `destination_profile`, `local_analysis`, `internal_query`, `processed=true`; error codes (`ENTITY_COLLISION`, `AMBIGUOUS_ALIAS`, `TAXONOMY_CYCLE`, `BASE_VERSION_STALE`, `SOURCE_CHANGED`, `OFFSET_INVALID`, `COVERAGE_GAP`, `UNSUPPORTED_ENCODING`, `ANALYSIS_INCOMPLETE`, `CONTEXT_STALE`, `INPUT_EMPTY`, `UNSAFE_PATH`, `IDENTITY_AMBIGUOUS`, `PART_MISSING`, `HASH_MISMATCH`, `PURPOSE_DENIED`); vault paths (`90_Sistema/…`, `Inicio.md`, `Como_usar`, `.base`, `CONTROL`, `CAP`, `TR-ID`, K1–K4, D01–D07/X01–X07, `B18`, `SES`, `ID_EMPRESARIAL`, `job_id`, `aceptación_integracion_local`).
- **Product name kept**: first mention in ce-instalacion renders "Business Brain (Cerebro Empresarial)" (upstream product name retained).
- 'Codex' as runtime agent replaced by "the Hermes agent"/Hermes tools everywhere; "Codex" remains only inside upstream file/path names (e.g. `.agents/skills/obsidian-router`, `guia/…_CON_CODEX…`).
- **Sibling skills linked relatively** (`../ce-revisar-antecedentes/SKILL.md`, `../ce-cambios/SKILL.md`, `../ce-documentacion/SKILL.md`, `../ce-extraer-meetgeek/SKILL.md`, `../obsidian-router/SKILL.md`, `../../…` from references/) because those dirs exist in the bundled plugin `skills/` (written by other groups); verified to resolve.
- **Non-bundled content redirected to upstream** `https://github.com/unsulabs/Obsidian-Bussines-Brain` keeping the relative path (16 distinct paths: guia/×3, docs/×6, ejemplos/×1, scripts/cerebro.py×4 target mentions as links, and the upstream test-command references `python -m unittest discover -s tests …`, `test_transcripciones_destino.py` kept as-is).
- **Unmapped cerebro.py subcommands** (`plan-conocimiento`, `buscar`, `autoridad`, `ficha`, `documento`, `previsualizar-dx`, `publicar-mapa`, `continuidad`) have no `brain_*` counterpart in the canonical tool list, so they are labeled "upstream `scripts/cerebro.py` subcommand" with a repo link — never claimed as Hermes tool capabilities (preserves the "don't claim pending CLI capabilities" invariant).
- **Invariants preserved**: privacy/authorization gates, `NO VERIFICADO` discipline, source-over-summary, ID resolution before any vault read, rejected-legacy rules, provenance/immutability, financial-record claim rules, two-attempts block rule, single consolidator/fencing, constructive-development outputs, Forbidden checklist translated from "Prohibido".
- Anchor in ce-instalacion → `../ce-banco-transcripciones/references/flujo-predeterminado.md#instance-and-dependency-preparation` matches the translated heading in the reference file.
