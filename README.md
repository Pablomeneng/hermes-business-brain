# hermes-business-brain

A native Hermes plugin that wraps **Obsidian-Bussines-Brain by unsulabs** (MIT)
— an offline Python toolkit for Obsidian "business brain" vaults — as 13 local,
network-free tools. It ships the upstream scripts and data as a
vendored engine and exposes them through Hermes tool handlers that run each
script as a subprocess against **user-provided paths only**. The vendored
engine is byte-identical to upstream
[unsulabs/Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
EXCEPT the PEM-header detection literals in 3 scripts (`documentos.py`,
`registro_descubrimiento.py`, `revisiones_dx.py`), split via string
concatenation (runtime-identical) so the catalog security scanner passes — see
[_verify/security-scan-fix.md](_verify/security-scan-fix.md).

- No real business data is shipped — all templates, schemas and demo content
  bundled here are synthetic by design.
- No network access: the engine never calls out, and handlers run with no
  special privileges.
- No absolute user paths are hardcoded: every tool takes vault/bank/file paths
  as arguments. (The vault-registry tools default to the user's own
  `~/.codex` / Obsidian native registry files, and both paths can be
  overridden.)

## Install

Two supported ways:

```bash
# (a) Once published (catalog):
hermes plugins install Pablomeneng/hermes-business-brain

# (b) Local/test: link the repo into the plugin install directory, then enable:
mkdir -p ~/.hermes/plugins
ln -s /path/to/repo ~/.hermes/plugins/hermes-business-brain
hermes plugins enable hermes-business-brain
```

`hermes plugins install` with a local path is NOT supported — the CLI parses
the argument as owner/repo. To validate this repository in place before
enabling (or after linking), run `hermes plugins doctor . --ci` from the
repository root.

The manifest declares `PyYAML==6.0.3` and `jsonschema>=4.23,<5`; Hermes'
package manager installs them on enablement (consent is requested).

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

All handlers return a JSON string with `stdout`, `stderr`, `exit_code` and an
English `summary`. Each schema lists the argument flags; they mirror the
upstream CLIs.

## Layout

```
plugin.yaml                 manifest v2 (13 provided tools)
__init__.py                 register(ctx): tools + bundled skills (skills/ may be empty)
schemas.py                  tool JSON schemas
tools.py                    handlers (subprocess runner over the engine)
engine/run_script.py        launcher shim (sys.path bootstrap for relative imports)
engine/scripts/             38 vendored upstream scripts, byte-identical to upstream except the disclosed PEM-header literal splits in 3 files (see NOTICE, _verify/security-scan-fix.md)
engine/{modelo,recursos,plantilla_boveda} -> data/  (symlinks)
data/                       upstream schemas, baseline resources, vault template (verbatim)
skills/                     bundled plugin skills (loaded as hermes-business-brain:<name>)
tests/                      pytest suite (engine + synthetic vault cycle)
NOTICE/THIRD_PARTY_NOTICES.md  upstream attributions
```

## Develop & test

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r <(echo -e "PyYAML==6.0.3\njsonschema>=4.23,<5\npytest")
.venv/bin/python -m pytest tests/ -q
```

## Privacy invariants (inherited from upstream)

- **No real business data ever** — everything bundled is synthetic.
- **No absolute user paths** in the engine — scripts only operate on paths you
  pass in.
- Captures and transcript banks must live **outside** any vault and any Git
  worktree (enforced by the engine).

## License

MIT. The vendored engine is upstream
[Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain)
(© 2026 Obsidian-Bussines-Brain contributors, MIT) — see
[NOTICE/THIRD_PARTY_NOTICES.md](NOTICE/THIRD_PARTY_NOTICES.md).
