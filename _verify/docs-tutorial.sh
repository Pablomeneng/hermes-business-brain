#!/usr/bin/env bash
# End-to-end verification of the Diátaxis experience docs (docs/tutorials and
# docs/how-to). Runs every documented command against a fresh temp vault/bank,
# appending real outputs to _verify/docs-tutorial.log. Read-only for the repo;
# all writes happen under the temp dir.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
LAUNCH="$ROOT/engine/run_script.py"
TMP="$(mktemp -d)"
# Resolve macOS symlinks (/var -> /private/var): the engine rejects symlinked
# bank/vault paths (UNSAFE_PATH) as an anti-tamper measure.
TMP="$("$PY" -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$TMP")"
VAULT="$TMP/vault"
BANK="$TMP/bank"
LOG="$ROOT/_verify/docs-tutorial.log"

: > "$LOG"

say() { echo "=== $*" >> "$LOG"; }

run() {
  echo "--- COMMAND: $*" >> "$LOG"
  out="$("$@" 2>&1)"
  code=$?
  echo "--- EXIT: $code" >> "$LOG"
  echo "$out" >> "$LOG"
  printf '\n[exit=%s] %s\n' "$code" "$*"
}

say "Diátaxis experience-docs verification run"
say "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say "temp root: $TMP"
say "vault: $VAULT"
say "python: $($PY --version 2>&1)"
say ""

# ---------------------------------------------------------------- doctor
say "TUTORIAL STEP: brain_doctor (environment preflight)"
run "$PY" "$LAUNCH" cerebro.py doctor

# ---------------------------------------------------------------- crear
say "TUTORIAL STEP: brain_create_vault (fresh vault)"
run "$PY" "$LAUNCH" cerebro.py crear --id EMPRESA-001 --nombre "Acme Consultores" --dest "$VAULT"

say "TUTORIAL STEP: brain_create_vault refuses an existing destination (no overwrite)"
run "$PY" "$LAUNCH" cerebro.py crear --id EMPRESA-001 --nombre "Acme Consultores" --dest "$VAULT"

say "TUTORIAL STEP: brain_create_vault rejects an invalid id (contract test)"
run "$PY" "$LAUNCH" cerebro.py crear --id "MI EMPRESA" --nombre "Acme Consultores" --dest "$TMP/otro"

# ---------------------------------------------------------------- validar
say "TUTORIAL STEP: brain_validate_vault (structural integrity)"
run "$PY" "$LAUNCH" validar_boveda.py --vault "$VAULT" --json

# ---------------------------------------------------------------- estado
say "TUTORIAL STEP: brain_status (structural summary)"
run "$PY" "$LAUNCH" cerebro.py estado --vault "$VAULT"

# ---------------------------------------------------------------- capturar
SYN="$TMP/hallazgo.md"
cat > "$SYN" <<'EOF'
# Draft finding

The client asked for weekly review meetings and one single point of contact.
To be confirmed against the 2026-11-03 meeting.
EOF
say "TUTORIAL STEP: brain_capture (preliminary finding, synthesis file outside the vault)"
run "$PY" "$LAUNCH" cerebro.py capturar --vault "$VAULT" --titulo "Weekly review meetings requested" --archivo "$SYN"

# ---------------------------------------------------------------- consulta
say "TUTORIAL STEP: brain_query (literal candidate search)"
run "$PY" "$LAUNCH" cerebro.py consulta-contextual --vault "$VAULT" --texto "weekly review meetings"

say "TUTORIAL STEP: brain_query with --orientar (natural request ordering)"
run "$PY" "$LAUNCH" cerebro.py consulta-contextual --vault "$VAULT" --texto "the client wants weekly review meetings" --orientar

# ---------------------------------------------------------------- resolver/registrar gates
mkdir -p "$TMP/reg"
CODEVARO="$TMP/reg/codex.json"
NATIVO_OK="$TMP/reg/nativo.json"
NATIVO_EMPTY="$TMP/reg/nativo-empty.json"
cat > "$CODEVARO" <<EOF
{"format": "codex-obsidian-vaults/1", "vaults": [{
  "id": "vault-acme-001", "name": "Acme Consultores", "path": "$VAULT",
  "aliases": ["EMPRESA-001"], "instructions": "90_Sistema/Como_usar.md",
  "entrypoint": "Inicio.md", "projects": []
}]}
EOF
cat > "$NATIVO_OK" <<EOF
{"vaults": {"vault-acme-001": {"path": "$VAULT"}}}
EOF
cat > "$NATIVO_EMPTY" <<'EOF'
{"vaults": {}}
EOF

say "HOW-TO continue-existing-vault: brain_resolve_vault reads local + native registries (read-only)"
run "$PY" "$LAUNCH" resolver_boveda_codex.py --selector EMPRESA-001 --registro "$CODEVARO" --nativo "$NATIVO_OK"

say "HOW-TO continue-existing-vault: brain_register_vault gate — no native Obsidian id, refuses to write"
run "$PY" "$LAUNCH" registrar_boveda_codex.py --vault "$VAULT" --nombre "Acme Consultores" --alias EMPRESA-001 --registro "$TMP/reg/codex2.json" --nativo "$NATIVO_EMPTY"

# ---------------------------------------------------------------- transcript cycle
mkdir -p "$BANK" "$TMP/tr"
PROFILE="$TMP/reg/perfil.json"
cat > "$PROFILE" <<'EOF'
{"company_id": "ACME-001", "allowed_purposes": ["custody", "local_analysis", "internal_query"], "bank": "/PLACEHOLDER"}
EOF
sed -i '' "s|/PLACEHOLDER|$BANK|" "$PROFILE"

say "HOW-TO work-transcripts: brain_transcript_cycle read-only estado over an empty bank"
run "$PY" "$LAUNCH" transcripciones.py estado --bank "$BANK" --profile "$PROFILE" --purpose local_analysis --request-id doc-verify-estado-1

say "HOW-TO work-transcripts: purpose outside allowed_purposes is denied (PURPOSE_DENIED)"
run "$PY" "$LAUNCH" transcripciones.py estado --bank "$BANK" --profile "$PROFILE" --purpose publication --request-id doc-verify-deny-1

say "HOW-TO work-transcripts: ingresar first custody step (commit an immutable original)"
echo "Synthetic transcript line one." > "$TMP/tr/transcript.txt"
run "$PY" "$LAUNCH" transcripciones.py ingresar --bank "$BANK" --profile "$PROFILE" --purpose custody --request-id doc-verify-ingreso-1 --archivo "$TMP/tr/transcript.txt" --source-id SRC-2026-1106-001 --account-id ACC-ACME --attempt-id ATT-1 --commit

say "HOW-TO work-transcripts: estado after one committed capture"
run "$PY" "$LAUNCH" transcripciones.py estado --bank "$BANK" --profile "$PROFILE" --purpose local_analysis --request-id doc-verify-estado-2

# ---------------------------------------------------------------- repo checks
say "REPO CHECK: pytest suite"
run "$PY" -m pytest "$ROOT/tests/" -q

say "REPO CHECK: hermes plugins doctor . --ci"
run hermes plugins doctor . --ci

say "REPO CHECK: hermes plugins list (confirm command used in install how-to)"
run hermes plugins list

echo
echo "Log written to $LOG"
echo "TMP=$TMP"
