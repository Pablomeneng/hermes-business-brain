# How to use the bundled skills

**Use this when**: you want the plugin's *methodology* — not just its tools.
The tools (`brain_*`) execute operations; the bundled skills tell the agent
*how* to think about a business vault: when to capture vs. approve, how to
check sources, how to run transcripts through custody, and when to mark
something `NO VERIFICADO`.

## What ships with the plugin

Every `skills/<name>/SKILL.md` folder in the plugin is registered at load
time by the plugin's `__init__.py` (`ctx.register_skill(...)`), so the
skills surface in Hermes as **plugin skills** under the
`hermes-business-brain:` namespace — the same convention as the tools.

There are 20 skill folders, grouped as:

| Group | Skills (18 `ce-*`) | When the family activates |
| --- | --- | --- |
| Installation & continuity | `ce-instalacion`, `ce-continuidad` | First set-up of a vault; resuming daily work on an existing one |
| Consultation | `ce-consulta`, `ce-evaluar-recuperacion`, `ce-evaluar-recurso`, `ce-revisar-antecedentes` | Queries, drafts, decisions, pilots, fidelity failures, new sources |
| Knowledge architecture | `ce-arquitectura-conocimiento`, `ce-taxonomia-conocimiento`, `ce-modelo-relaciones`, `ce-calidad-repositorio`, `ce-cambios`, `ce-documentacion`, `ce-investigacion`, `ce-descubrimiento` | Designing notes before drafting, taxonomy, relations, research, D/X documents, corrections |
| Transcripts | `ce-banco-transcripciones`, `ce-analizar-transcripcion`, `ce-extraer-meetgeek` | New conversations/transcripts (custody first), analysis, MeetGeek extraction |
| Company development | `ce-desarrollo-empresa` | Orchestrating the whole second-brain lifecycle |

…plus two companions:

- `obsidian-router` — resolves the private vault through explicit local
  registration and native Obsidian identity *before any access*. The
  `ce-instalacion`, `ce-consulta` and `ce-continuidad` skills all route
  through it (`brain_register_vault` / `brain_resolve_vault`).
- `documentation-writer` — a third-party import (tracked in the repo's
  `skills-lock.json`, sourced from `github/awesome-copilot`), not a
  business-brain workflow skill. The repo's "19 bundled skills" figure counts
  the business-brain set: the 18 `ce-*` plus `obsidian-router`.

## How they surface and activate

1. **Automatic activation (recommended).** Hermes loads a skill when your
   task matches its description. For example:
   - "install the Business Brain for the first time" →
     [`ce-instalacion`](../../skills/ce-instalacion/SKILL.md) (its description
     says: *activate when a person asks to install, start, configure or
     continue the first installation*);
   - "answer a question from the company vault" →
     [`ce-consulta`](../../skills/ce-consulta/SKILL.md) (*queries, drafting,
     commercial preparation, execution, decisions, contracts, prices,
     projects or history*);
   - "here is a transcript of the meeting" →
     [`ce-banco-transcripciones`](../../skills/ce-banco-transcripciones/SKILL.md)
     (*preserve and drive the complete cycle of a new conversation/transcript
     … Custody is the first step*).
2. **Explicit loading.** List them and open one:

   ```text
   skills_list
   skill_view(name='hermes-business-brain:ce-consulta')
   ```

   The raw files also live in the plugin at
   `~/.hermes/plugins/hermes-business-brain/skills/<name>/SKILL.md`.

Load them *before* running business-brain tools for a task — the skills
constrain how the tools are used (for example `ce-consulta` insists on
resolving the vault before any read inside it).

## What they are — and their honest limits

**What they are:** workflow guidance with hard invariants. Examples baked in:

- Never create or reinstall a vault that exists
  ([`ce-instalacion`](../../skills/ce-instalacion/SKILL.md),
  [`ce-continuidad`](../../skills/ce-continuidad/SKILL.md)).
- Captures are drafts; `aprobado: false` until editorial process says
  otherwise; corrections create versions, never replacements.
- Anything unproven is reported `NO VERIFICADO`, and "an empty result doesn't
  prove absence" ([`ce-consulta`](../../skills/ce-consulta/SKILL.md)).

**Honest limits:**

- **Skills are not tools.** A skill can *reference* an upstream `cerebro.py`
  subcommand that is **not** exposed as a plugin tool in v0.1. The plugin
  exposes exactly 13 `brain_*` tools (see the
  [README](../../README.md)); upstream-only subcommands include `ficha`,
  `proponer`, `fuente`, `documento`, `continuidad`, `buscar`, `autoridad`,
  and the `relacion-*` writers (verified against `schemas.py`). They run via
  the vendored CLI instead:

  ```bash
  python ~/.hermes/plugins/hermes-business-brain/engine/run_script.py cerebro.py ficha --help
  ```

  In a development checkout the same launcher is `engine/run_script.py`.
  So when a skill says "use `ficha`", expect an invocation like the above,
  not a `brain_*` tool.
- **Skills are read-only guidance.** They don't change engine behaviour; and
  because they are authored with the upstream, their bodies are in Spanish
  (the tool outputs and schemas likewise). The English documentation in this
  repo translates the key invariants — see
  [continue an existing vault](continue-existing-vault.md) and
  [work with transcripts](work-transcripts.md).
- **The set is a starting map, not a flowchart.** Several skills route to each
  other by *topic* (correction → `ce-revisar-antecedentes`, knowledge change
  → `ce-cambios`, new matter → `ce-arquitectura-conocimiento`). The
  descriptions quoted above are the activation triggers; when in doubt about
  which one applies, open the skill each candidate names.

## Verification

The folder inventory, registration mechanism, and the upstream-only
subcommand list above were verified against this repository
(`__init__.py`, `schemas.py`, `skills/`) and Hermes v0.23.0; see
[`../../_verify/docs-experience.md`](../../_verify/docs-experience.md).
