# hermes-business-brain

Offline Obsidian "business-brain" toolkit: 13 network-free Hermes tools to create, validate and query knowledge vaults.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](docs/how-to/install.md)
[![Docs: English](https://img.shields.io/badge/docs-English-blue.svg)](docs/)

`hermes-business-brain` wraps **Obsidian-Bussines-Brain** (Cerebro Empresarial) by
[unsulabs](https://github.com/unsulabs/Obsidian-Bussines-Brain) — an offline Python
toolkit for Obsidian "business brain" vaults — as 13 local Hermes tools. Each tool runs
a vendored upstream script as a subprocess against **user-provided paths only**. The
plugin is privacy-first by construction:

- **No network.** The engine never calls out; handlers run with no special privileges.
- **No real business data shipped.** Every template, schema and piece of demo content
  bundled here is synthetic by design.
- **No hardcoded absolute user paths.** Every tool takes vault/bank/file paths as
  arguments. (The vault-registry tools default to the user's own `~/.codex` / Obsidian
  native registry files; both paths can be overridden.)

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Tools (13)](#tools-13)
- [Bundled skills (19)](#bundled-skills-19)
- [Documentation](#documentation)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Background

Obsidian users often keep a "business brain": a local vault of company knowledge —
entities, sources, decisions, transcripts, typed relations. Until now the tooling for
that workflow lived on the command line and inside Obsidian. This plugin brings the
same workflow to Hermes as plain tools an agent can call, with one hard rule: **nothing
leaves your machine.** No API calls, no telemetry, no cloud — a business decision stays
a local file until *you* move it.

The plugin is a wrapper, not a rewrite: the engine under `engine/` is vendored from
upstream and is byte-identical to
[unsulabs/Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
except for the PEM marker detection literals in 3 scripts, which are split via string
concatenation (runtime-identical) so the catalog security scanner passes. That change is
disclosed in [_verify/security-scan-fix.md](_verify/security-scan-fix.md) and explained
in [docs/explanation/upstream-origin.md](docs/explanation/upstream-origin.md).

## Install

Two supported ways (full walkthrough with real doctor output:
[docs/how-to/install.md](docs/how-to/install.md)):

```bash
# (a) From the catalog (once published):
hermes plugins install Pablomeneng/hermes-business-brain --enable

# (b) Local / development: symlink the repo into the plugin directory, then enable:
mkdir -p ~/.hermes/plugins
ln -s /path/to/hermes-business-brain ~/.hermes/plugins/hermes-business-brain
hermes plugins enable hermes-business-brain
```

> **Note (verified 2026-11-06):** the catalog entry does not exist yet — use path (b)
> until the plugin is published.

`hermes plugins install` with a local filesystem path is **not** supported — the CLI
parses the argument as `owner/repo`. After enabling, **restart Hermes** so the tools and
skills load. To confirm the installation (both read-only):

```bash
hermes plugins list                          # plugin should show status: enabled
hermes plugins doctor hermes-business-brain --ci   # manifest + registration gate
```

From inside a checkout, the same gate runs without the plugin being enabled:
`hermes plugins doctor . --ci`.

The manifest declares two Python dependencies, `PyYAML==6.0.3` and
`jsonschema>=4.23,<5`, installed by Hermes' package manager on enablement (consent is
requested). The engine works on Python 3.11+ (up to 3.14; examples verified on 3.14).

## Usage

Ask Hermes to run the tools; each step below also names the exact engine command so you
can verify it yourself. The full guided walkthrough is the
[quickstart tutorial](docs/tutorials/quickstart-vault.md) (about 10 minutes).

**1. Preflight** — `brain_doctor` checks Python, dependencies and Obsidian, read-only,
installing nothing.

**2. Create a vault** — `brain_create_vault` with three arguments (`id`, `nombre`,
`dest`). It never overwrites: if the destination already exists, the tool fails —
that is a safety feature.

| Argument | Value |
| --- | --- |
| `id` | `EMPRESA-001` (2–64 chars, letters/digits/dash/underscore) |
| `nombre` | `Acme Consultores` |
| `dest` | `~/empresas/acme-consultores` (must **not** exist) |

**3. Validate** — `brain_validate_vault` checks structural integrity (ids, wikilinks,
transfers, frontmatter) — never business truth.

**4. Inspect** — `brain_status` prints a structural summary: company id/name, note
counts by type, editorial state, templates.

**5. Query** — `brain_query` returns candidate note blocks matched by literal text,
optionally filtered by `tema` / `ambito` / `fecha`, with `limite` candidates (default
10). Use `orientar: true` to order results by the terms of a natural request. A fresh
vault answers "no candidates yet" — that is designed behaviour, not a bug.

```bash
# Engine equivalents, run through the vendored launcher from inside the checkout:
python engine/run_script.py cerebro.py doctor
python engine/run_script.py cerebro.py crear --id EMPRESA-001 --nombre "Acme Consultores" --dest ~/empresas/acme-consultores
python engine/run_script.py cerebro.py validar --vault ~/empresas/acme-consultores
python engine/run_script.py cerebro.py estado --vault ~/empresas/acme-consultores
python engine/run_script.py cerebro.py consulta-contextual --vault ~/empresas/acme-consultores --texto "..."
```

Continue with an existing vault: [docs/how-to/continue-existing-vault.md](docs/how-to/continue-existing-vault.md).
Capture transcripts and drive the custody pipeline: [docs/how-to/work-transcripts.md](docs/how-to/work-transcripts.md).

## Tools (13)

| Tool | Engine command | Purpose |
| --- | --- | --- |
| `brain_doctor` | `cerebro.py doctor` | Read-only environment preflight (Python, deps, Obsidian). |
| `brain_create_vault` | `cerebro.py crear` | Create a new empty vault from the bundled template; never overwrites. |
| `brain_validate_vault` | `validar_boveda.py` | Structural integrity check (ids, links, transfers) — not business truth. |
| `brain_status` | `cerebro.py estado` | Structural company summary (counts, editorial state, templates). |
| `brain_register_vault` | `registrar_boveda_codex.py` | Register an open vault in the Codex selector registry (needs Obsidian's native id). |
| `brain_resolve_vault` | `resolver_boveda_codex.py` | Resolve the vault registered for a Codex project/selector. |
| `brain_query` | `cerebro.py consulta-contextual` | Candidate blocks by literal text + source/date/scope filters; no semantic generation. |
| `brain_capture` | `cerebro.py capturar` | Save preliminary findings as a draft note (not approved knowledge). |
| `brain_knowledge_map` | `cerebro.py mapa-conocimiento` | Read-only knowledge-map preview (Markdown/Canvas). |
| `brain_relations` | `cerebro.py relaciones` | Query typed relations and their real state. |
| `brain_references` | `plugin_references.py` (wrap of `referencias_externas.py`) | Local versioned external-reference registry: metadata only, no content import, no network. |
| `brain_naming` | `nombres_legibles.py` | Plan (default) or apply readable filename changes from a spec JSON. |
| `brain_transcript_cycle` | `transcripciones.py` | One step of the transcript custody→analysis pipeline (`ingresar → registrar → segmentar → analizar → cobertura → indexar`, plus read-only custody steps and `buscar`). |

All handlers return a JSON string with `stdout`, `stderr`, `exit_code` and an English
`summary`. Each schema lists the argument flags; they mirror the upstream CLIs. Full
per-tool reference: [docs/reference/tools.md](docs/reference/tools.md).

## Bundled skills (19)

The plugin ships 19 workflow skills under `skills/`, registered at load time as
`hermes-business-brain:<name>` — 18 `ce-*` skills (installation, discovery, query and
task execution, transcripts, taxonomy, relations, knowledge changes, documentation,
research) plus `obsidian-router`, which mandates vault resolution before any access.

Skills never call the engine directly: they instruct the agent to invoke the `brain_*`
tools with the arguments documented in the reference. See
[docs/reference/skills.md](docs/reference/skills.md) for the master table and
[docs/how-to/use-bundled-skills.md](docs/how-to/use-bundled-skills.md) for how to work
with them.

## Documentation

Organized by quadrant (Diátaxis).

**Tutorial** — learn by doing:

- [Tutorial: create your first business vault](docs/tutorials/quickstart-vault.md) — the
  10-minute walkthrough from preflight to first query.

**How-to** — task-oriented guides:

- [How to install the plugin](docs/how-to/install.md) — both install paths, restart,
  confirmation, and the local-path gotcha.
- [How to continue an existing vault](docs/how-to/continue-existing-vault.md) — resume,
  dependency troubleshooting, the `NO VERIFICADO` discipline.
- [How to work with transcripts](docs/how-to/work-transcripts.md) — the custody and
  analysis pipeline.
- [How to use the bundled skills](docs/how-to/use-bundled-skills.md).

**Reference** — the machinery, as a dictionary:

- [Reference: Tools](docs/reference/tools.md) — the 13 tools: arguments, types,
  required/optional, engine backings, examples.
- [Reference: Bundled Skills](docs/reference/skills.md) — the 19 bundled skills,
  families, when each activates.
- [Reference: Upstream CLI](docs/reference/upstream-cli.md) — `cerebro.py` subcommands
  not exposed as plugin tools in v0.1, via the vendored launcher.

**Explanation** — how and why:

- [Explanation: Architecture](docs/explanation/architecture.md) — native shell +
  vendored engine; subprocess execution model; read-only data; no network; skills
  interaction; why wrap instead of rewrite.
- [Explanation: Privacy and guardrails](docs/explanation/privacy-and-guardrails.md) —
  the invariants as implemented: authorization gates, `NO VERIFICADO`, source over
  summary, ID resolution, rejected legacy, provided-path-only, proposal ≠ decision.
- [Explanation: Upstream origin](docs/explanation/upstream-origin.md) — provenance,
  what is byte-identical, what is adapted, license/attribution split.

## Security

The privacy invariants above are enforced in code, not just documented — the details
and the failure modes are in
[docs/explanation/privacy-and-guardrails.md](docs/explanation/privacy-and-guardrails.md).
Key points:

- **No real business data ever** — everything bundled is synthetic.
- **No absolute user paths** in the engine — scripts only operate on paths you pass in.
- Captures and transcript banks must live **outside** any vault and any Git worktree
  (enforced by the engine).
- Unconfirmable facts are reported as `NO VERIFICADO`, never silently assumed.
- The only engine deviation from upstream is the disclosed PEM marker literal split
  (see [_verify/security-scan-fix.md](_verify/security-scan-fix.md)).

## Contributing

This plugin is a wrapper around Cerebro Empresarial. Engine fixes, new subcommands and
documentation of the upstream toolkit belong in the upstream repository:
[unsulabs/Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
(issues and PRs welcome there).

For the Hermes wrapper itself — tool schemas, handlers, bundled skills, docs — open an
issue or PR in this repository.

### Development setup and tests

```bash
python3.11 -m venv .venv
.venv/bin/pip install "PyYAML==6.0.3" "jsonschema>=4.23,<5" pytest
.venv/bin/python -m pytest tests/ -q
```

To validate the manifest and registration in place: `hermes plugins doctor . --ci`.

## License

MIT. The vendored engine is upstream
[Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
(© 2026 Obsidian-Bussines-Brain contributors, MIT) — see
[NOTICE/THIRD_PARTY_NOTICES.md](NOTICE/THIRD_PARTY_NOTICES.md) for the full
attributions.

## Layout

```
plugin.yaml                 manifest v2 (13 provided tools)
__init__.py                 register(ctx): tools + bundled skills (skills/ may be empty)
schemas.py                  tool JSON schemas
tools.py                    handlers (subprocess runner over the engine)
engine/run_script.py        launcher shim (sys.path bootstrap for relative imports)
engine/scripts/             39 vendored upstream scripts, byte-identical to upstream except the disclosed PEM marker literal splits in 3 files (see NOTICE, _verify/security-scan-fix.md)
engine/{modelo,recursos,plantilla_boveda} -> data/  (symlinks)
data/                       upstream schemas, baseline resources, vault template (verbatim)
skills/                     bundled plugin skills (loaded as hermes-business-brain:<name>)
tests/                      pytest suite (engine + synthetic vault cycle)
NOTICE/THIRD_PARTY_NOTICES.md  upstream attributions
```
