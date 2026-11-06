# README rewrite — verification evidence

Date: 2026-11-06. Scope: `README.md` rewritten per
`.agents/skills/crafting-effective-readmes` (OSS template, standard-readme
ordering, cognitive funneling). All checks below ran from the repository root
against the committed README.

| # | Check | Command | Result |
|---|-------|---------|--------|
| 1 | Plugin manifest + registration | `hermes plugins validate . --install-deps` | Exit 0 — "Validation passed." (13 checks: loadable, declared tools match registrations, security scan — safe, no collisions/overrides) |
| 2 | Test suite | `.venv/bin/python -m pytest tests/ -q` | Exit 0 — 11 passed (engine, registration, vault cycle) |
| 3 | Relative links resolve | Python: extract `](...)`, skip http(s)/#/mailto, `os.path.exists` | 26 targets checked, 0 broken |
| 4 | One-liner length | `len()` of first paragraph | 119 chars (standard-readme: < 120) |
| 5 | ToC anchors | H2 headings vs `](#...)` links | 11/11 headings linked, 0 missing |
| 6 | No hardcoded user paths | `grep -c '/Users/pablomeneses' README.md` | 0 matches |
| 7 | Contiguous PEM marker literal absent | `git grep -F "<header>"` (pattern assembled from parts, never written contiguously in any repo file) on final commit | 0 matches — README and repo contain no contiguous form; the split is only described in words, per `_verify/security-scan-fix.md` |
| 8 | All 11 Diátaxis doc links exist | `os.path.exists` on each `docs/**` target | All present (3 tutorial/how-to added — previously omitted as "not part of this pass"; 3 reference, 3 explanation kept) |

Stale content removed: "How-to and Tutorial quadrants will be added
separately" (they now exist); engine script count corrected 38 → 39
(`ls engine/scripts/*.py | wc -l`); install "once published" wording kept with
the catalog-not-yet-existing note (verified 2026-11-06, same date as
`docs/how-to/install.md`).

The PEM marker literal disclosure is intentionally never written contiguously:
any occurrence would trip the catalog security scanner repo-wide (see
`_verify/security-scan-fix.md`).
