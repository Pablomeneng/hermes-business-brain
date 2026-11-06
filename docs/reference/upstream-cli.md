# Reference — Upstream cerebro.py CLI (subcommands not exposed as tools in v0.1)

`engine/scripts/cerebro.py` is the vendored upstream CLI — 29 subcommands
registered via `add_parser` (verified: `grep -c "add_parser(" cerebro.py` →
29). Seven of them back plugin tools exposed in v0.1 (`doctor`, `crear`,
`estado`, `capturar`, `relaciones`, `consulta-contextual`,
`mapa-conocimiento`) — see [`tools.md`](tools.md). The other **22** are not
exposed as plugin tools in v0.1: they exist in the engine and are reachable
only through the vendored launcher.

> Note on the upstream help text: `cerebro.py`'s `help=` strings are in
> Spanish (upstream language). The "Purpose" column below is an English
> rendering of that help text, not a paraphrase from elsewhere.

## The vendored launcher

```bash
python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py SUBCOMMAND --vault /absolute/path ... 
```

`run_script.py` is the plugin's launcher shim: it boots the vendored scripts'
`sys.path` (dependencies via `BB_SITE_PACKAGES`, sibling scripts under
`engine/scripts/`) and runs the target with `runpy`, so behavior matches the
upstream CLI. Without a vault open yet — e.g. `tipos` — the `--vault` flag is
simply omitted. In a development checkout the same command works from the
repository:

```bash
python /path/to/repo/engine/run_script.py cerebro.py SUBCOMMAND ...
```

**Status:** these are upstream CLI subcommands, not plugin tools. Their
behavior, flags and messages are upstream's. Bundled skills may reference
them exactly as subcommands of the vendored launcher (labeled "not exposed as
a standalone plugin tool in v0.1") when no `brain_*` tool covers the
operation — this is the documented, supported way to reach them inside the
plugin.

## Subcommands not exposed as plugin tools (22)

| Subcommand | Purpose (English, from upstream help) | Key flags (verified in cerebro.py) | Launcher example (illustrative) |
| --- | --- | --- | --- |
| `ficha` | Create a draft record card (ficha) from a specific type; never invent data. | `--vault --tipo --titulo [--resumen --archivo --fuente … --etiqueta …]` | `python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py ficha --vault /abs/vault --tipo empresa --titulo "Ficha de ejemplo" --resumen "..."` |
| `fuente` | Register a reference to a source without copying the original document. | `--vault --id --titulo --localizador --clase [--lectura --fecha-evento]` | `... cerebro.py fuente --vault /abs/vault --id F-0001 --titulo "Contrato" --localizador "https://example.com/doc" --clase D01 --lectura no_verificada` |
| `proponer` | Register a suggested change in the tray; does NOT touch the original note. | `--vault --id --motivo --archivo` | `... cerebro.py proponer --vault /abs/vault --id NOTA-001 --motivo "Precisar cifras" --archivo /tmp/candidato.md` |
| `plan-conocimiento` | Audit the note map, tags and relations BEFORE drafting; read-only. | `--vault --archivo` | `... cerebro.py plan-conocimiento --vault /abs/vault --archivo /tmp/plan.json` |
| `documento` | Register a developed D01–D07 / X01–X07 document without approving it. | `--vault --clase --titulo --archivo [--doc-id --estado --cobertura --fecha-corte --fuente … --etiqueta …]` | `... cerebro.py documento --vault /abs/vault --clase D01 --titulo "Modelo de negocio" --archivo /tmp/doc.md --estado en_revision` |
| `previsualizar-dx` | Simulate a D/X modification without writing. | `--vault --doc-id --archivo [--fuente …]` | `... cerebro.py previsualizar-dx --vault /abs/vault --doc-id D01 --archivo /tmp/candidato.md` |
| `preparar-dx` | Save a D/X proposal without modifying the current document. | `--vault --doc-id --archivo [--fuente …]` | `... cerebro.py preparar-dx --vault /abs/vault --doc-id D01 --archivo /tmp/candidato.md` |
| `aplicar-dx` | Apply a D/X proposal after specific authorization and backup. | `--vault --propuesta --sha-original --sha-candidato [--sha-fuentes] --responsable --referencia-autorizacion --respaldo` | `... cerebro.py aplicar-dx --vault /abs/vault --propuesta /tmp/propuesta.md --sha-original 9f86… --sha-candidato 0a08… --responsable "Alice" --referencia-autorizacion AUT-001 --respaldo /tmp/respaldo` |
| `restaurar-dx` | Restore a D/X version as a new revision after authorization. | `--vault --doc-id --historial --sha-actual --responsable --referencia-autorizacion --respaldo` | `... cerebro.py restaurar-dx --vault /abs/vault --doc-id D01 --historial 5 --sha-actual 9f86… --responsable "Alice" --referencia-autorizacion AUT-002 --respaldo /tmp/respaldo` |
| `evaluar-dx` | Record an editorial evaluation (G1–G7) without modifying the D/X. | `--vault --doc-id --acta --sha-actual` | `... cerebro.py evaluar-dx --vault /abs/vault --doc-id D02 --acta /tmp/revision.json --sha-actual 9f86…` |
| `aprobar-dx` | Full editorial promotion with evaluation, authorization and backup. | `--vault --evaluacion --sha-actual --responsable --referencia-autorizacion --respaldo --confirmacion` | `... cerebro.py aprobar-dx --vault /abs/vault --evaluacion /tmp/evaluacion.json --sha-actual 9f86… --responsable "Alice" --referencia-autorizacion AUT-003 --respaldo /tmp/respaldo --confirmacion "APROBAR D02 9f86d081…"` |
| `relacion-proponer` | Create a typed-edge proposal; never approve it. | `--vault --origen --destino --predicado --fuente … --ambito --motivo` | `... cerebro.py relacion-proponer --vault /abs/vault --origen NOTA-1 --destino NOTA-2 --predicado responde_a --fuente F-0001 --ambito EMPRESA-001 --motivo "Soporta la respuesta"` |
| `relacion-confirmar` | Record human ratification of a relation. | `--vault --relacion-id --sha-relacion --revisor --referencia-autorizacion --confirmacion` | `... cerebro.py relacion-confirmar --vault /abs/vault --relacion-id REL-001 --sha-relacion 9f86… --revisor "Alice" --referencia-autorizacion AUT-004 --confirmacion "CONFIRMAR REL-001 9f86d081…"` |
| `aceptacion` | Pilot preflight: structural read, not human approval. | `--vault` | `... cerebro.py aceptacion --vault /abs/vault` |
| `continuidad` | Record a session close to recover context later. | `--vault --resumen --siguiente [--revisado-por]` | `... cerebro.py continuidad --vault /abs/vault --resumen "Avance Q3" --siguiente "Revisar D07" --revisado-por por_validar` |
| `validar` | Validate integrity of notes, ids, links and transfers — NOT business truth. | `--vault` | `... cerebro.py validar --vault /abs/vault` |
| `buscar` | Textual search with sources, without inferences. | `--vault --texto [--limite]` | `... cerebro.py buscar --vault /abs/vault --texto "margen bruto" --limite 12` |
| `autoridad` | Strict query by topic/scope/date declared in an imported contract. | `--vault --tema --ambito [--fecha]` | `... cerebro.py autoridad --vault /abs/vault --tema precios --ambito EMPRESA-001 --fecha 2026-11-06` |
| `importar` | Import a vNext-0.9 manifest; non-destructive. | `--vault --manifest [--permitir-real]` | `... cerebro.py importar --vault /abs/vault --manifest /tmp/traspaso.json` |
| `publicar-mapa` | Publish only the derived map, with exact SHA and external backup. | `--vault --sha-actual --sha-propuesto --confirmacion --respaldo` | `... cerebro.py publicar-mapa --vault /abs/vault --sha-actual 9f86… --sha-propuesto 0a08… --confirmacion "PUBLICAR MAPA …" --respaldo /tmp/respaldo` |
| `grafo` | Export typed internal relations and hyperlinks (writes `90_Sistema/grafo.json` inside the vault by default). | `--vault [--output]` | `... cerebro.py grafo --vault /abs/vault` |
| `tipos` | Show the candidate model's available types and distinctions. | `[--tipo]` | `... cerebro.py tipos` |

## Subcommands that ARE exposed as plugin tools (7)

| Subcommand | Plugin tool |
| --- | --- |
| `doctor` | `brain_doctor` |
| `crear` | `brain_create_vault` |
| `estado` | `brain_status` |
| `capturar` | `brain_capture` |
| `consulta-contextual` | `brain_query` |
| `relaciones` | `brain_relations` |
| `mapa-conocimiento` | `brain_knowledge_map` |

## Two naming traps

- **`validar` (cerebro) vs `validar_boveda.py`**: `brain_validate_vault` does
  NOT run `cerebro.py validar` — it runs the standalone
  `engine/scripts/validar_boveda.py`. Both check integrity; the tool's backing
  script is the standalone one.
- **`buscar` appears twice**: `cerebro.py buscar` (above, not exposed) is a
  text search over a vault; `transcripciones.py buscar` is a `brain_transcript_cycle`
  step that assembles a query context package. They are different commands in
  different scripts.
