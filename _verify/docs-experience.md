# Experience docs — verification evidence

Diátaxis "experience" documentation (tutorial + how-to guides) for
hermes-business-brain, added on 2026-11-06.

## Files written

| File | Type | Purpose |
| --- | --- | --- |
| `docs/tutorials/quickstart-vault.md` | Tutorial | First vault: doctor → create → validate → status → capture → query |
| `docs/how-to/install.md` | How-to | Catalog + symlink install paths, enable, restart, confirm, unsupported local path |
| `docs/how-to/continue-existing-vault.md` | How-to | Resolve-first workflow, invariants from ce-instalacion / ce-continuidad |
| `docs/how-to/work-transcripts.md` | How-to | brain_transcript_cycle custody→analysis pipeline, cards = future work |
| `docs/how-to/use-bundled-skills.md` | How-to | Skill surfaces, families, activation triggers, honest limits |
| `_verify/docs-tutorial.sh` | Script | Reproducible end-to-end verification (run with `bash _verify/docs-tutorial.sh`) |
| `_verify/docs-tutorial.log` | Evidence | Full real output of every verified command |

Nothing under `engine/` or `skills/` was modified. All command snippets in the
docs were executed with the vendored engine launcher
(`engine/run_script.py`, dev checkout) or the `hermes` CLI, not guessed.

## Verification commands (all with exit codes)

Environment: macOS 26.5.1 (arm64), Hermes Agent v0.23.0, Python 3.14.7 venv at
`.venv/` with `PyYAML` + `jsonschema` installed.

| # | Command | Exit |
| --- | --- | --- |
| 1 | `.venv/bin/python engine/run_script.py cerebro.py doctor` | 0 |
| 2 | `.venv/bin/python engine/run_script.py cerebro.py crear --id EMPRESA-001 --nombre "Acme Consultores" --dest <mktemp>/vault` | 0 |
| 3 | same `crear` again (destination exists) | 2 (fail-safe, expected) |
| 4 | `crear --id "MI EMPRESA"` (invalid id pattern) | 2 (expected) |
| 5 | `.venv/bin/python engine/run_script.py validar_boveda.py --vault <vault> --json` | 0 |
| 6 | `.venv/bin/python engine/run_script.py cerebro.py estado --vault <vault>` | 0 |
| 7 | `.venv/bin/python engine/run_script.py cerebro.py capturar --vault <vault> --titulo "Weekly review meetings requested" --archivo <tmp>/hallazgo.md` | 0 |
| 8 | `.venv/bin/python engine/run_script.py cerebro.py consulta-contextual --vault <vault> --texto "weekly review meetings"` | 0 (0 candidates — by design, see below) |
| 9 | same query with `--orientar` | 0 |
| 10 | `.venv/bin/python engine/run_script.py resolver_boveda_codex.py --selector EMPRESA-001 --registro <tmp>/codex.json --nativo <tmp>/nativo.json` (synthetic registries) | 0, `native_registry_verified: true` |
| 11 | `.venv/bin/python engine/run_script.py registrar_boveda_codex.py --vault <vault> --nombre … --alias EMPRESA-001 --nativo <empty-native.json>` | 2 (authorization gate refusal, expected) |
| 12 | `.venv/bin/python engine/run_script.py transcripciones.py estado --bank <tmp>/bank --profile … --purpose local_analysis` | 0 (empty bank, transcriptions: 0) |
| 13 | same with `--purpose publication` (not in allowed_purposes) | 2, `PURPOSE_DENIED` (expected) |
| 14 | `.venv/bin/python engine/run_script.py transcripciones.py ingresar … --commit --archivo …` (synthetic transcript) | 0 (`DONE_WITH_CONCERNS`, `DELIVERY_INCOMPLETE`, receipts + hashes emitted) |
| 15 | `estado` again after commit | 0 (transcriptions: 1, integrity verificada, analysis pendiente) |
| 16 | `.venv/bin/python -m pytest tests/ -q` | 0 (11 passed) |
| 17 | `hermes plugins doctor . --ci` | 0 (registrations: 13 tool(s), 0 hook(s)) |
| 18 | `hermes plugins list` | 0 (plugin not installed — see unverified) |
| 19 | `hermes plugins install --help` / `hermes plugins enable --help` | 0 (CLI surface) |
| 20 | `.venv/bin/python engine/run_script.py cerebro.py ficha --help` | 0 (upstream-only subcommand runs via vendored CLI) |
| 21 | `hermes plugins search hermes-business-brain` | 0 — "No catalog entries matched" (not yet published) |

## Tutorial proof (key outputs, verbatim)

Vault creation, temp path under `/private/var/folders/…/tmp.f7RVmJ7MIA`
(realpath-resolved; engine rejects symlinked paths):

```
$ engine/run_script.py cerebro.py crear --id EMPRESA-001 --nombre "Acme Consultores" --dest .../vault
{"creada": ".../vault", "estado": "infraestructura_sin_conocimiento",
 "nota": "Abrir y verificar manualmente en Obsidian"}                  [exit 0]

repeat crear on same dest → "ERROR: Fallo seguro: el destino ya existe: ..." [exit 2]
crear --id "MI EMPRESA" → "ERROR: El ID debe tener 2–64 caracteres: letras, dígitos, guion o guion bajo" [exit 2]

$ engine/run_script.py validar_boveda.py --vault .../vault --json
{"notas": 7, "ids": 7, "bloques": 0, "traspasos": 0, "errores": [], "advertencias": []}   [exit 0]

$ engine/run_script.py cerebro.py estado --vault .../vault
{"empresa": "Acme Consultores", "id_empresa": "EMPRESA-001", "total_notas": 7,
 "capas": {"infraestructura": 7, "fuentes": 0, "trabajo_provisional": 0,
           "documentos_dx": 0, "entidades_operativas": 0},
 "plantillas_instaladas": 47, "advertencia": "Recuento estructural, NO cobertura suficiente ni verdad validada"}   [exit 0]

$ engine/run_script.py cerebro.py capturar --vault .../vault --titulo "Weekly review meetings requested" --archivo .../hallazgo.md
{"id": "CAP-2471F90F241C", "ruta": ".../vault/90_Sistema/Descubrimiento/Weekly review meetings requested.md",
 "estado": "borrador_no_autoritativo", "fuentes": [], "aprobado": false, "importado_como_conocimiento": false}  [exit 0]

$ engine/run_script.py cerebro.py consulta-contextual --vault .../vault --texto "weekly review meetings"
{"empresa_id": "EMPRESA-001", "consulta_literal": "weekly review meetings",
 "total_coincidencias": 0, "candidatos": [], "respuesta_semantica_generada": false}   [exit 0]
```

## Facts verified but notable

- **Empty query on a fresh vault is by design.** Consulted the engine source:
  `consulta_contextual.py` builds candidates only from notes whose `tipo` is
  in `modelo/tipos_entidad.json` (+ `documento`) and whose path is **not**
  under `90_Sistema`/`Plantillas`. A fresh vault contains only `mapa` /
  `control` / `sistema` notes (7), and captures land in
  `90_Sistema/Descubrimiento/` — so 0 candidates is the correct, honest
  result, and the tutorial teaches it explicitly (empty ≠ absence).
- **Transcript pipeline gates** (from `transcripciones.py` +
  `tools.py`): profile must contain non-empty `company_id` and
  `allowed_purposes` (`PROFILE_INVALID` otherwise); `purpose` must be allowed
  (`PURPOSE_DENIED`); bank must pre-exist and be symlink-free (`UNSAFE_PATH`
  on macOS `/var`); `buscar` requires `--output`; `audience` is required for
  `segmentar/analizar/cobertura/indexar/revisar-antecedentes`; `request_id`
  is handler-generated. Missing bank dir returns `BLOCKED/UNSAFE_PATH` via
  the CLI; profile `bank` must equal CLI `--bank` (`BANK_PROFILE_MISMATCH`
  otherwise).
- **Resolver gates** (`resolver_boveda_codex.py`): exactly one match
  required, native Obsidian id must equal the registered id, and
  instructions/entrypoint files must exist in the vault — confirmed by
  synthetic-registry runs.
- **Registrar gate** (`registrar_boveda_codex.py`): refuses to write without
  a native Obsidian id ("Abre primero la carpeta como bóveda en Obsidian…").
- 20 skill folders ship in `skills/` (18 `ce-*` + `obsidian-router` +
  `documentation-writer`); `skills-lock.json` tracks only
  `documentation-writer`. The repo's "19 bundled skills" count = 18 `ce-*` +
  `obsidian-router`; the docs state both numbers and the discrepancy.

## Facts I could NOT verify (honest)

1. **Catalog install / real enablement.** The plugin is not in the catalog yet
   (`hermes plugins search` → no match), so `hermes plugins install
   Pablomeneng/hermes-business-brain --enable` was not executed; the doc marks
   it "once published". The local-symlink + `enable` flow was likewise not
   executed end-to-end: enabling would mutate this machine's Hermes
   environment (install PyYAML/jsonschema into Hermes' PM venv, start the
   plugin). Verified instead: `install --help`/`enable --help` CLI surface,
   `--enable`/`--yes-deps` flags exist, and `hermes plugins doctor . --ci`
   passes against the repo (13 tools registered).
2. **Restart behaviour after enablement.** The "restart Hermes" note is the
   doctor's own wording ("run hermes pm repair, then restart Hermes"); the
   actual load of tools/skills in a running Hermes session was not observed
   here.
3. **`brain_register_vault` success path.** Requires an Obsidian-native id
   from the real Obsidian app; only the refusal gate was exercised. The
   resolver success path was exercised with synthetic registries.
4. **Obsidian GUI facts.** `brain_doctor` reported candidates but
   `obsidian_version`/`obsidian_gui` as `NO VERIFICADO` — the docs repeat
   that verbatim rather than asserting Obsidian works.
5. **Skill surfacing naming.** The `hermes-business-brain:<name>` addressing
   follows the plugin's `register_skill` mechanism and the repo convention;
   a live `skills_list` output from an enabled plugin was not captured
   (plugin never enabled in this environment).
6. **Installed-plugin launcher path.** Tutorial commands show
   `~/.hermes/plugins/hermes-business-brain/engine/run_script.py`; the actual
   verification used the equivalent dev-checkout launcher
   (`engine/run_script.py`), since the plugin is not installed here. The
   launcher's usage is identical for both (dependency bootstrap is
   environment-driven).
7. **`skills-lock.json` is not committed.** The lockfile exists in the
   working tree and was read for the skill-roster facts, but an uncommitted
   `.gitignore` edit (leftover work-in-progress from an earlier session)
   ignores `skills/` and `skills-lock.json`, and the lockfile was never
   added to the index. A fresh clone will lack it; `docs/how-to/use-bundled-skills.md`
   therefore *mentions* it (prose, not a link) as the source record of the
   `documentation-writer` import. The `skills/*.md` files themselves are
   tracked (23 files), so all skill links in the docs resolve in-repo.
