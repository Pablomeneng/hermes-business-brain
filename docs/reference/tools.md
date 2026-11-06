# Reference — Tools (hermes-business-brain v0.1)

This is the dictionary of the 13 plugin tools. Every argument name, type and
required/optional status below is taken from `schemas.py`, and every engine
backing from `tools.py`; example invocations show the JSON argument object the
model passes and the vendored-engine command that results. If a detail here
disagrees with a tool's actual schema, the schema (and, behind it, the
upstream CLI the schema mirrors) wins.

## How a tool runs

Every tool is a handler in `tools.py` that executes one vendored engine script
as a subprocess — no shell, no network, no implicit paths — and returns a JSON
string with this envelope:

```json
{
  "tool": "brain_query",
  "script": "cerebro.py",
  "stdout": "...",
  "stderr": "...",
  "exit_code": 0,
  "timed_out": false,
  "summary": "cerebro.py completed successfully (exit 0)...."
}
```

`summary` is always English. `exit_code` is the engine process exit code (or
`-1` with `timed_out: true` after 120 seconds). Handlers never raise: engine
failure is returned inside the JSON, not thrown.

## Conventions

- Argument names mirror the upstream CLI flags (`--vault` becomes `vault`,
  `--reference-id` becomes `reference_id`) so the mapping is mechanical.
- Paths are always user-provided absolute paths. The engine touches nothing
  outside them except the Codex/Obsidian registry files, whose locations are
  overridable (`registro`/`nativo`).
- Boolean arguments are flags: present (`true`) means the flag is emitted.
- Repeatable arguments (`fuente`, `refs`-adjacent lists) are emitted once per
  item.

## Overview

| Tool | Backing engine command | Purpose (one line) |
| --- | --- | --- |
| `brain_doctor` | `cerebro.py doctor` | Read-only environment preflight (Python, deps, Obsidian); never installs or writes. |
| `brain_create_vault` | `cerebro.py crear` | Create a new empty vault from the bundled template; fails if the destination exists. |
| `brain_validate_vault` | `validar_boveda.py` | Structural integrity check (ids, wikilinks, transfers) — never business truth. |
| `brain_status` | `cerebro.py estado` | Structural company summary (counts, editorial state, templates, sources). |
| `brain_register_vault` | `registrar_boveda_codex.py` | Register an open vault in the Codex selector registry (needs Obsidian's native id). |
| `brain_resolve_vault` | `resolver_boveda_codex.py` | Resolve the vault registered for a Codex project/selector, verified against Obsidian's native registry. |
| `brain_query` | `cerebro.py consulta-contextual` | Candidate note blocks by literal text + topic/scope/date filters; no semantic generation. |
| `brain_capture` | `cerebro.py capturar` | Save preliminary findings as a draft capture note — not approved knowledge. |
| `brain_knowledge_map` | `cerebro.py mapa-conocimiento` | Read-only knowledge-map preview (Markdown/Canvas). |
| `brain_relations` | `cerebro.py relaciones` | Query typed relations and their real state (proposals, confirmations). |
| `brain_references` | `plugin_references.py` (wrapper of `referencias_externas.py`) | Local versioned external-reference registry: metadata only, no content import, no network. |
| `brain_naming` | `nombres_legibles.py` | Plan (default) or apply readable filename changes from a spec JSON. |
| `brain_transcript_cycle` | `transcripciones.py` | One step of the transcript custody→analysis pipeline. |

---

## brain_doctor

Read-only environment preflight: reports Python, PyYAML/jsonschema
availability, Obsidian installation candidates, and optionally whether a
vault's company config exists. Never installs anything and never writes.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | no | Absolute path to a vault to include in the preflight report. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand `doctor`,
dispatched to `doctor_preflight.diagnose`).

```text
brain_doctor({"vault": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py doctor --vault /Users/alice/vaults/empresa
```

## brain_create_vault

Create a new empty business vault from the bundled Obsidian template. Never
overwrites: fails if the destination already exists.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Company id, 2–64 chars: letters, digits, dash or underscore. |
| `nombre` | string | yes | Display name for the company (no newlines). |
| `dest` | string | yes | Absolute path where the new vault directory will be created; must not exist. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand `crear`,
dispatched to `crear_instancia.create`).

```text
brain_create_vault({"id": "EMPRESA-001", "nombre": "Mi Empresa SAS", "dest": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py crear --id EMPRESA-001 --nombre "Mi Empresa SAS" --dest /Users/alice/vaults/empresa
```

## brain_validate_vault

Validate the structural integrity of a business vault: note ids, wikilinks,
transfers, frontmatter. Integrity only — never business truth.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory to validate. |
| `json` | boolean | no (default `true`) | Emit the full JSON report instead of the condensed summary. |

The `--json` flag is emitted unless `json` is explicitly `false`. On success
the English summary reports integrity-error and warning counts.

Backing engine script: `engine/scripts/validar_boveda.py`.

```text
brain_validate_vault({"vault": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py validar_boveda.py --vault /Users/alice/vaults/empresa --json
```

## brain_status

Structural summary of a company vault: company id/name, note counts by type,
editorial state, installed templates and bases, source summary. Read-only; a
count, not validated truth.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand `estado`,
dispatched to `operacion.summary`).

```text
brain_status({"vault": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py estado --vault /Users/alice/vaults/empresa
```

## brain_register_vault

Register an already-open Obsidian vault in the Codex local router so Codex
can resolve it. Updates the Codex selector registry only; requires the vault
to already have an id in Obsidian's native registry. May read/write the
user's Codex and Obsidian registry files under the home directory — override
with `registro`/`nativo`.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault already opened in Obsidian. |
| `nombre` | string | yes | Human-readable name for the vault entry. |
| `alias` | string | yes | Business id used as an alias, e.g. `EMPRESA-001`. |
| `registro` | string | no | Absolute path to the Codex vaults registry JSON (default `~/.codex/obsidian/vaults.json`). |
| `nativo` | string | no | Absolute path to the Obsidian native registry JSON (platform default). |
| `instrucciones` | string | no | Vault-relative instructions file (default `90_Sistema/Como_usar.md`). |
| `inicio` | string | no | Vault-relative entrypoint note (default `Inicio.md`). |
| `proyecto` | string | no | Absolute path of the Codex project directory that should resolve this vault. |

Backing engine script: `engine/scripts/registrar_boveda_codex.py`.

```text
brain_register_vault({"vault": "/Users/alice/vaults/empresa", "nombre": "Empresa", "alias": "EMPRESA-001"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py registrar_boveda_codex.py --vault /Users/alice/vaults/empresa --nombre "Empresa" --alias EMPRESA-001
```

## brain_resolve_vault

Resolve which registered vault a Codex project (or a selector string) maps
to, verifying it against Obsidian's native registry. Read-only for the
registries. Use before operating on a vault to confirm identity.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `selector` | string | exactly one of `selector`/`project` | Selector matching a registered id, name, alias, or absolute vault path. |
| `project` | string | exactly one of `selector`/`project` | Absolute path of the Codex project whose registered vault should be resolved. |
| `registro` | string | no | Absolute path to the Codex vaults registry JSON (default `~/.codex/obsidian/vaults.json`). |
| `nativo` | string | no | Absolute path to the Obsidian native registry JSON (platform default). |

Backing engine script: `engine/scripts/resolver_boveda_codex.py`.

```text
brain_resolve_vault({"selector": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py resolver_boveda_codex.py --selector /Users/alice/vaults/empresa
```

## brain_query

Contextual consultation over a vault: candidate note blocks matched by
literal text, with topic/scope/date filters and an optional limit; set
`orientar` to order candidates by the terms of a natural request. Returns
candidates only — never a generated semantic answer.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |
| `texto` | string | yes | Literal text to match against note blocks. |
| `tema` | string | no | Optional topic filter. |
| `ambito` | string | no | Optional scope filter. |
| `fecha` | string | no | Optional date filter (`YYYY-MM-DD`). |
| `limite` | integer | no (default `10`) | Maximum number of candidates. |
| `orientar` | boolean | no (default `false`) | Order candidates by terms from a natural request instead of raw match strength. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand
`consulta-contextual`, dispatched to `consulta_contextual.consulta`).

```text
brain_query({"vault": "/Users/alice/vaults/empresa", "texto": "margen bruto", "orientar": true, "limite": 5})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py consulta-contextual --vault /Users/alice/vaults/empresa --texto "margen bruto" --orientar --limite 5
```

## brain_capture

Save preliminary findings as a draft capture note in the vault without
declaring them approved knowledge. The synthesis markdown must be prepared in
a file outside the vault and Git; sources, if any, must already be registered
with `brain_references`.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |
| `titulo` | string | yes | Title of the capture note. |
| `archivo` | string | yes | Absolute path to the authorized synthesis markdown file outside the vault and Git. |
| `fuente` | array of string | no | Source ids (`F-...`) already registered; repeatable. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand `capturar`,
dispatched to `registro_descubrimiento.capture_discovery`).

```text
brain_capture({"vault": "/Users/alice/vaults/empresa", "titulo": "Hallazgos Q3", "archivo": "/Users/alice/tmp/hallazgos.md", "fuente": ["F-0001", "F-0002"]})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py capturar --vault /Users/alice/vaults/empresa --titulo "Hallazgos Q3" --archivo /Users/alice/tmp/hallazgos.md --fuente F-0001 --fuente F-0002
```

## brain_knowledge_map

Preview the knowledge map (Markdown/Canvas renderings) derived from the
vault's notes and relations. Read-only: writes nothing to the vault.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand
`mapa-conocimiento`, dispatched to `mapa_conocimiento.previsualizar`).

```text
brain_knowledge_map({"vault": "/Users/alice/vaults/empresa"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py mapa-conocimiento --vault /Users/alice/vaults/empresa
```

## brain_relations

Query typed relations stored in a vault and their real state (proposals,
confirmations). Read-only.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |
| `id` | string | no | Filter: relation originates from or targets this note id. |

Backing engine script: `engine/scripts/cerebro.py` (subcommand `relaciones`,
dispatched to `relaciones.query`).

```text
brain_relations({"vault": "/Users/alice/vaults/empresa", "id": "EMP-0001"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py relaciones --vault /Users/alice/vaults/empresa --id EMP-0001
```

## brain_references

Local versioned external-reference registry over a private bank directory
(custody area outside any vault and any Git worktree). Registers metadata
only — never imports content, never touches the network. Records are prepared
as JSON files outside the vault, then committed here.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `action` | string | yes | Operation: `register` (add a metadata record), `read` (fetch one record), `decisions` (list the permission chain), `verify` (transitive closure check). |
| `bank` | string | yes | Absolute path to the private custody bank directory (must not be inside a vault or Git worktree). |
| `commit` | boolean | no (default `false`) | Apply the custody mutation; default is a preview that validates without writing. |
| `metadata` | string | for `register` | Absolute path to the JSON reference record (`referencia-externa.v1`) prepared outside the vault. |
| `reference_id` | string | for `read` | Id of the registered reference. |
| `version_id` | string | for `read` | Version id (`EV-...`) of the registered reference. |
| `refs` | string | for `verify` | Absolute path to a JSON array of reference descriptors to verify transitively. |
| `company` | string | for `verify` | Company id scope. |
| `audience` | string | for `verify` | Audience scope. |
| `purpose` | string | for `verify` | Purpose scope (e.g. `local_analysis`, `custody`). |
| `require_read` | boolean | for `verify` (default `true`) | Require reading evidence for external references; pass `false` to emit `--no-require-read`. |
| `require_internal` | boolean | for `verify` (default `false`) | Require `interno` sensitivity for external references. |

Backing engine script: `engine/scripts/plugin_references.py` (plugin-original
wrapper over `referencias_externas.py`).

```text
brain_references({"action": "register", "bank": "/Users/alice/banco", "metadata": "/Users/alice/tmp/ref.json", "commit": true})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py plugin_references.py register --bank /Users/alice/banco --metadata /Users/alice/tmp/ref.json --commit
```

## brain_naming

Plan (or apply) readable filename changes for a vault from a spec JSON
prepared outside the vault and Git. Default is a read-only plan; pass
`apply: true` to execute, which requires a backup directory.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `vault` | string | yes | Absolute path to the vault directory. |
| `spec` | string | yes | Absolute path to the naming spec JSON prepared outside the vault. |
| `apply` | boolean | no (default `false`) | Apply the rename plan instead of only previewing it. |
| `sha_plan` | string | no | Expected SHA-256 of the plan file; rejects mismatches when applying. |
| `backup_dir` | string | no (required when applying) | Absolute path of the backup directory. |

Backing engine script: `engine/scripts/nombres_legibles.py`.

```text
brain_naming({"vault": "/Users/alice/vaults/empresa", "spec": "/Users/alice/tmp/spec.json", "sha_plan": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "backup_dir": "/Users/alice/backups"})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py nombres_legibles.py --vault /Users/alice/vaults/empresa --spec /Users/alice/tmp/spec.json --sha-plan 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 --backup-dir /Users/alice/backups
```

## brain_transcript_cycle

Drive one step of the transcript custody and analysis pipeline over a private
bank (custody area outside any vault and Git worktree). The full cycle is
`ingresar → registrar → segmentar → analizar → cobertura → indexar`, plus
read-only custody steps (`estado`, `verificar`, `inventario-validar`,
`conciliar`) and `buscar`. Profile JSON must contain `company_id` and
`allowed_purposes` and live outside the vault.

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `step` | string | yes | One of: `ingresar`, `registrar`, `segmentar`, `analizar`, `cobertura`, `indexar`, `revisar-antecedentes`, `taxonomia`, `permiso`, `estado`, `verificar`, `inventario-validar`, `conciliar`, `buscar`. |
| `bank` | string | yes | Absolute path to the private custody bank (must not be inside a vault or Git worktree). |
| `profile` | string | yes | Absolute path to the profile JSON: `{company_id, allowed_purposes:[...], optional bank/vault}`. |
| `purpose` | string | yes | Purpose scope that must be allowed by the profile (e.g. `custody`, `local_analysis`). |
| `request_id` | string | no | Caller-supplied request id for the custody ledger (default: generated). |
| `commit` | boolean | no (default `false`) | Apply the local custody mutation; default is a read-only preview. |
| `audience` | string | no | Audience scope; required for `segmentar`/`analizar`/`cobertura`/`indexar`/`revisar-antecedentes`, optional for `estado`. |
| `archivo` | string | for `ingresar` | Absolute path to the transcript file to import. |
| `parts_manifest` | string | for `ingresar` | Absolute path to a JSON parts manifest instead of a single file. |
| `source_id` | string | for `ingresar` | Transcript source id. |
| `account_id` | string | for `ingresar` | Account id. |
| `attempt_id` | string | for `ingresar` | Attempt id. |
| `closed` | boolean | for `ingresar` | Mark the capture closed (complete). |
| `expected_parts` | integer | for `ingresar` | Expected part count for closed captures. |
| `capture_manifest` | string | for `registrar` | Absolute path to the capture receipt JSON produced by `ingresar`. |
| `tr_id` | string | for `segmentar`/`cobertura` | Transcript id. |
| `version` | string | for `segmentar` | Version id to segment. |
| `policy` | string | for `segmentar` | Segmentation policy id. |
| `max_core_bytes` | integer | for `segmentar` (default `4096`) | Max bytes for a core segment. |
| `context_bytes` | integer | for `segmentar` (default `256`) | Context bytes around a segment. |
| `run` | string | for `cobertura` | Analysis run id. |
| `input` | string | for `analizar`/`permiso`/`taxonomia` | Absolute path to the JSON input payload prepared outside the vault. |
| `event` | string | for `revisar-antecedentes`/`taxonomia` | Absolute path to the event JSON. |
| `snapshot` | string | for `revisar-antecedentes`/`inventario-validar`/`conciliar`/`indexar` | Snapshot JSON path, or `current` for the live watermark. |
| `results` | string | for `revisar-antecedentes` | Optional agent-authored results JSON array path. |
| `previous` | string | for `revisar-antecedentes` | Prior review bundle path relative to the bank. |
| `taxonomy_version` | string | for `revisar-antecedentes` | Exact stored taxonomy version for claim resolution. |
| `request` | string | for `buscar` | Absolute path to the query request JSON `{query, company, audience, purpose, ...}`. |
| `output` | string | no | Optional absolute path for an immutable JSON report; must not already exist. |

Backing engine script: `engine/scripts/transcripciones.py`.

```text
brain_transcript_cycle({"step": "ingresar", "bank": "/Users/alice/banco", "profile": "/Users/alice/tmp/perfil.json", "purpose": "custody", "archivo": "/Users/alice/tmp/transcripcion.vtt", "commit": true})
→  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py transcripciones.py ingresar --bank /Users/alice/banco --profile /Users/alice/tmp/perfil.json --purpose custody --request-id hermes-brain-<timestamp>-<hex8> --commit --archivo /Users/alice/tmp/transcripcion.vtt
```
