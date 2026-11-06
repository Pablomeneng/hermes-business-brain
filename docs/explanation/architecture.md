# Explanation — Architecture: a native shell around a vendored engine

This page explains how `hermes-business-brain` is put together and why it is
shaped that way. For exact arguments and names, see the
[Reference](../reference/tools.md) pages; this page is about how the pieces
fit.

## The big picture

The plugin is a **native Hermes plugin wrapping a vendored upstream engine**.
There are two layers:

1. **The native layer** — `plugin.yaml`, `__init__.py`, `schemas.py`,
   `tools.py`, `engine/run_script.py`, and the bundled skills. Written for
   Hermes, in English, MIT-licensed. This is what Hermes loads.
2. **The vendored engine** — `engine/scripts/` (38 upstream Python scripts:
   35 byte-identical to upstream, 3 differing only by the disclosed
   detection-literal split; plus `plugin_references.py`, which is
   plugin-original) and the `data/` directory (schemas, baseline resources,
   the vault template — shipped verbatim) the scripts read through symlinks.
   This is upstream
   [Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
   (MIT), unmodified in behavior, with its Spanish runtime messages intact.

`plugin.yaml` declares the manifest (v2, api version 1), the two Python
dependencies (`PyYAML==6.0.3`, `jsonschema>=4.23,<5`), and the 13 provided
tools. At load, `register(ctx)` in `__init__.py` registers each tool
(schema from `schemas.py`, handler from `tools.py`, description from the
schema) and then registers every `skills/<dir>/SKILL.md` as a plugin skill
under `hermes-business-brain:<name>`.

## The tool execution path

Every tool handler in `tools.py` runs exactly one vendored script as a
subprocess. The pattern is uniform:

- **argv-list call, no shell**: `subprocess.run([sys.executable, run_script.py,
  script, *argv], ...)` — never a shell string, so arguments cannot be
  interpreted by a shell.
- **Working directory = the engine directory** (`cwd=engine`), so the
  scripts' relative sibling imports and `__file__`-relative data lookups
  behave exactly as upstream.
- **Dependencies re-injected**: the host Hermes process records its own
  activated `site-packages` directories and passes them to the child via
  `BB_SITE_PACKAGES`; `run_script.py` re-inserts them into `sys.path` before
  running the target with `runpy`. The same PyYAML/jsonschema available to
  Hermes is therefore available to the engine.
- **~120s timeout**: `DEFAULT_TIMEOUT = 120`. A timeout is not an exception —
  the handler returns `timed_out: true` with whatever output the process
  produced and an English summary.
- **Output captured**: `stdout` and `stderr` are captured (utf-8,
  `errors="replace"`), never streamed to the user's terminal.
- **English exit-code summary**: every result carries a `summary` field in
  English derived from the exit code and output — success messages name the
  script; failure messages carry the exit code and the first error line. The
  engine's own output stays in its original language; only the wrapper's
  summary is English.
- **Handlers never raise**: engine failure is returned as JSON
  (`{"stdout", "stderr", "exit_code", "timed_out", "summary", ...}`), so one
  failing call cannot take down the agent.

`run_script.py` itself is a small shim: it bootstraps `sys.path` (inherited
site-packages, then `engine/scripts/`), sets `sys.argv` to
`[target] + user_args`, and executes the target via `runpy.run_path(..., run_name="__main__")`
— which keeps `__file__` correct for the scripts' data-directory logic.

## Data is shipped read-only

All model data lives under `data/` and is bundled verbatim:

- `data/modelo/` — the canonical document classes
  (`clases_documentales.json`), entity types (`tipos_entidad.json`), start
  routes (`rutas_de_inicio.json`), and 19 transcript schemas under
  `transcripciones/`.
- `data/recursos/` — baseline mirrors (`bases_baseline.json` with per-file
  SHA-256, `registro_plugins.json`).
- `data/plantilla_boveda/` — the complete Obsidian vault template
  (`Inicio.md`, `00_Mapas/`, `90_Sistema/` with the D01–D07/X01–X07 and Ficha
  templates, `.base` views, `config_empresa.yaml`).

The engine directory exposes `modelo`, `recursos` and `plantilla_boveda` as
symlinks back to `data/` (the upstream layout expects them at the repository
root), so the scripts resolve their data with their original relative-path
logic. The plugin ships this tree as data: the native layer never writes into
`data/`, and engine writes go only to user-provided vault and bank paths.
Nothing here is real business data — everything is synthetic by design.

## No network access

The native layer has no network code at all. The only network-adjacent import
in the whole engine is `urllib.parse.urlparse` in `referencias_externas.py`,
used purely to **parse and catalog URL locators without connecting** (the
script's own docstring: "URLs se catalogan sin acceder a la red"). There are
no HTTP/socket clients, no `requests`/`urllib.request` usage, no call-out
anywhere. The plugin is fully offline by construction.

## How the bundled skills interact with the tools

The 19 bundled skills (`hermes-business-brain:ce-*`, `obsidian-router`) are
procedures that tell the agent *when and how* to call the tools. Their
interaction pattern:

- Skills prescribe **tool sequences with discipline** — e.g. `obsidian-router`
  requires `brain_resolve_vault` (exit 0, `status: selected`,
  `native_registry_verified: true`) before any vault read; `ce-instalacion`
  chains `brain_doctor` → `brain_create_vault` → `brain_validate_vault` →
  `brain_register_vault` → `brain_resolve_vault`.
- Skills pass the tools' **schema arguments** (`--vault`, `--archivo`,
  `--fuente`, …) by name, so the schemas in `schemas.py` are the interface
  contract the skills program against.
- Where a needed upstream subcommand is **not exposed** as a tool in v0.1
  (22 of cerebro.py's 29 subcommands), skills call it explicitly through the
  vendored launcher and label it "not exposed as a standalone plugin tool in
  v0.1" — see [upstream-cli.md](../reference/upstream-cli.md). That keeps the
  skill layer honest: it never pretends an unexposed subcommand is a tool.

## Why wrap instead of rewrite

The engine was not ported, translated or rewritten for three reasons:

- **MIT and behavioral fidelity**: upstream is MIT-licensed, so vendoring is
  legal, and wrapping preserves upstream behavior exactly — every flag,
  every JSON key, every error path — instead of risking semantic drift in a
  rewrite. The plugin's promise is "the upstream toolkit, reachable from
  Hermes", and only a wrapper keeps that promise verifiable.
- **Upgrade path**: a future upstream version can be re-vendored by copying
  the scripts and re-running the disclosed detection-literal split, instead
  of re-doing a translation. The wrapper surface (`schemas.py`, `tools.py`)
  is small and stable.
- **Attribution clarity**: keeping the layers separate makes the license
  split crisp — MIT plugin wrapper + MIT upstream engine, credited in
  [`NOTICE/THIRD_PARTY_NOTICES.md`](../../NOTICE/THIRD_PARTY_NOTICES.md).

What *was* rewritten is only the layer Hermes touches: tool schemas, handler
code, the launcher shim, and the skills — the latter translated from the
upstream Codex-oriented procedures into English Hermes procedures (see
[upstream-origin.md](upstream-origin.md)).
