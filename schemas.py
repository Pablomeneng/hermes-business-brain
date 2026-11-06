"""JSON-schema definitions for the hermes-business-brain tools.

Each schema mirrors the argparse interface of the corresponding vendored
upstream script (see the engine scripts for the authoritative flag lists).
Paths are always user-provided; the engine never touches implicit locations
except the Codex/Obsidian registries whose paths can be overridden with
``registro``/``nativo`` arguments.
"""

# ---------------------------------------------------------------------------
# brain_doctor
# ---------------------------------------------------------------------------
BRAIN_DOCTOR = {
    "type": "object",
    "description": (
        "Run a read-only environment preflight for the Business Brain engine "
        "(Obsidian vault toolkit): reports Python, PyYAML/jsonschema availability, "
        "Obsidian installation candidates, and optionally whether a vault's company "
        "config exists. Never installs anything and never writes. Use when checking "
        "whether the environment is ready to create or operate a business vault."
    ),
    "properties": {
        "vault": {
            "type": "string",
            "description": "Optional absolute path to a vault to include in the preflight report.",
        },
    },
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_create_vault
# ---------------------------------------------------------------------------
BRAIN_CREATE_VAULT = {
    "type": "object",
    "description": (
        "Create a new empty business vault from the bundled Obsidian template. "
        "Never overwrites: fails if the destination already exists. Use to bootstrap "
        "a new company vault (then run brain_validate_vault and brain_status)."
    ),
    "properties": {
        "id": {
            "type": "string",
            "description": "Company id, 2-64 chars: letters, digits, dash or underscore (e.g. EMPRESA-001).",
            "pattern": r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}",
        },
        "nombre": {
            "type": "string",
            "description": "Display name for the company (no newlines).",
        },
        "dest": {
            "type": "string",
            "description": "Absolute path where the new vault directory will be created; must not exist.",
        },
    },
    "required": ["id", "nombre", "dest"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_validate_vault
# ---------------------------------------------------------------------------
BRAIN_VALIDATE_VAULT = {
    "type": "object",
    "description": (
        "Validate the structural integrity of a business vault: note ids, wikilinks, "
        "transfers, frontmatter. This checks integrity only, never business truth. "
        "Use after creating or editing a vault, or when a vault misbehaves."
    ),
    "properties": {
        "vault": {
            "type": "string",
            "description": "Absolute path to the vault directory to validate.",
        },
        "json": {
            "type": "boolean",
            "description": "Emit the full JSON report instead of the condensed summary. Default true.",
            "default": True,
        },
    },
    "required": ["vault"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_status
# ---------------------------------------------------------------------------
BRAIN_STATUS = {
    "type": "object",
    "description": (
        "Show a structural summary of the company vault: company id/name, note "
        "counts by type, editorial state, installed templates and bases, source "
        "summary. Read-only; a count, not validated truth. Use to inspect any vault."
    ),
    "properties": {
        "vault": {
            "type": "string",
            "description": "Absolute path to the vault directory.",
        },
    },
    "required": ["vault"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_register_vault
# ---------------------------------------------------------------------------
BRAIN_REGISTER_VAULT = {
    "type": "object",
    "description": (
        "Register an already-open Obsidian vault in the Codex local router so Codex "
        "can resolve it (updates the Codex selector registry; requires the vault to "
        "already have an id in Obsidian's native registry). Does not create or modify "
        "the vault. May read/write the user's Codex and Obsidian registry files under "
        "the home directory; override with registro/nativo."
    ),
    "properties": {
        "vault": {
            "type": "string",
            "description": "Absolute path to the vault already opened in Obsidian.",
        },
        "nombre": {
            "type": "string",
            "description": "Human-readable name for the vault entry.",
        },
        "alias": {
            "type": "string",
            "description": "Business id used as an alias, e.g. EMPRESA-001.",
        },
        "registro": {
            "type": "string",
            "description": "Optional absolute path to the Codex vaults registry JSON (default: ~/.codex/obsidian/vaults.json).",
        },
        "nativo": {
            "type": "string",
            "description": "Optional absolute path to the Obsidian native registry JSON (platform default).",
        },
        "instrucciones": {
            "type": "string",
            "description": "Vault-relative instructions file (default 90_Sistema/Como_usar.md).",
            "default": "90_Sistema/Como_usar.md",
        },
        "inicio": {
            "type": "string",
            "description": "Vault-relative entrypoint note (default Inicio.md).",
            "default": "Inicio.md",
        },
        "proyecto": {
            "type": "string",
            "description": "Optional absolute path to the Codex project directory that should resolve this vault.",
        },
    },
    "required": ["vault", "nombre", "alias"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_resolve_vault
# ---------------------------------------------------------------------------
BRAIN_RESOLVE_VAULT = {
    "type": "object",
    "description": (
        "Resolve which registered vault a Codex project (or a selector string) maps "
        "to, verifying it against Obsidian's native registry. Read-only for the "
        "registries (defaults under the user home; override with registro/nativo). "
        "Use before operating on a vault to confirm identity."
    ),
    "properties": {
        "selector": {
            "type": "string",
            "description": "Selector matching a registered id, name, alias, or absolute vault path.",
        },
        "project": {
            "type": "string",
            "description": "Absolute path of the Codex project whose registered vault should be resolved. Exactly one of selector/project must be given.",
        },
        "registro": {
            "type": "string",
            "description": "Optional absolute path to the Codex vaults registry JSON (default: ~/.codex/obsidian/vaults.json).",
        },
        "nativo": {
            "type": "string",
            "description": "Optional absolute path to the Obsidian native registry JSON (platform default).",
        },
    },
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_query
# ---------------------------------------------------------------------------
BRAIN_QUERY = {
    "type": "object",
    "description": (
        "Contextual consultation over a vault: candidate note blocks matched by "
        "literal text, source/topic/scope/date filters, optionally ordered by the "
        "terms of a natural request. Returns candidates only, never a generated "
        "semantic answer. Use to pull existing vault knowledge into a task."
    ),
    "properties": {
        "vault": {"type": "string", "description": "Absolute path to the vault directory."},
        "texto": {"type": "string", "description": "Literal text to match against note blocks."},
        "tema": {"type": "string", "description": "Optional topic filter."},
        "ambito": {"type": "string", "description": "Optional scope filter."},
        "fecha": {"type": "string", "description": "Optional date filter (YYYY-MM-DD)."},
        "limite": {"type": "integer", "description": "Maximum number of candidates (default 10).", "default": 10},
        "orientar": {
            "type": "boolean",
            "description": "Order candidates by terms from a natural request instead of raw match strength (no semantic generation).",
            "default": False,
        },
    },
    "required": ["vault", "texto"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_capture
# ---------------------------------------------------------------------------
BRAIN_CAPTURE = {
    "type": "object",
    "description": (
        "Save preliminary findings as a draft capture note in the vault without "
        "declaring them approved knowledge. The synthesis markdown must be prepared "
        "in a file OUTSIDE the vault and Git; sources, if any, must already be "
        "registered with brain_references/operacion sources. Use to preserve raw "
        "findings early in a task."
    ),
    "properties": {
        "vault": {"type": "string", "description": "Absolute path to the vault directory."},
        "titulo": {"type": "string", "description": "Title of the capture note."},
        "archivo": {
            "type": "string",
            "description": "Absolute path to the authorized synthesis markdown file outside the vault and Git.",
        },
        "fuente": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Source ids (F-...) already registered; repeatable.",
        },
    },
    "required": ["vault", "titulo", "archivo"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_knowledge_map
# ---------------------------------------------------------------------------
BRAIN_KNOWLEDGE_MAP = {
    "type": "object",
    "description": (
        "Preview the knowledge map (Markdown/Canvas renderings) derived from the "
        "vault's notes and relations. Read-only: writes nothing to the vault. Use to "
        "review structure before planning new content."
    ),
    "properties": {
        "vault": {"type": "string", "description": "Absolute path to the vault directory."},
    },
    "required": ["vault"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_relations
# ---------------------------------------------------------------------------
BRAIN_RELATIONS = {
    "type": "object",
    "description": (
        "Query typed relations stored in a vault and their real state (proposals, "
        "confirmations). Read-only. Use to see how notes/entities are connected."
    ),
    "properties": {
        "vault": {"type": "string", "description": "Absolute path to the vault directory."},
        "id": {"type": "string", "description": "Optional filter: relation originates from or targets this note id."},
    },
    "required": ["vault"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_references
# ---------------------------------------------------------------------------
BRAIN_REFERENCES = {
    "type": "object",
    "description": (
        "Local versioned external-reference registry over a private bank directory "
        "(custody area outside any vault and any Git worktree). Registers metadata "
        "only, never imports content and never touches the network; records are "
        "prepared as JSON files outside the vault, then committed here. Actions: "
        "register (add a metadata record), read (fetch one record), decisions "
        "(list the permission chain), verify (transitive closure check of "
        "references/transcripts)."
    ),
    "properties": {
        "action": {
            "type": "string",
            "enum": ["register", "read", "decisions", "verify"],
            "description": "Operation to run against the reference bank.",
        },
        "bank": {
            "type": "string",
            "description": "Absolute path to the private custody bank directory (must not be inside a vault or Git worktree).",
        },
        "commit": {
            "type": "boolean",
            "description": "Apply the custody mutation; default is a preview that validates without writing.",
            "default": False,
        },
        "metadata": {
            "type": "string",
            "description": "[register] Absolute path to the JSON reference record (referencia-externa.v1) prepared outside the vault.",
        },
        "reference_id": {
            "type": "string",
            "description": "[read] Id of the registered reference.",
        },
        "version_id": {
            "type": "string",
            "description": "[read] Version id (EV-...) of the registered reference.",
        },
        "refs": {
            "type": "string",
            "description": "[verify] Absolute path to a JSON array of reference descriptors to verify transitively.",
        },
        "company": {"type": "string", "description": "[verify] Company id scope."},
        "audience": {"type": "string", "description": "[verify] Audience scope."},
        "purpose": {"type": "string", "description": "[verify] Purpose scope (e.g. local_analysis, custody)."},
        "require_read": {
            "type": "boolean",
            "description": "[verify] Require reading evidence for external references (default true).",
            "default": True,
        },
        "require_internal": {
            "type": "boolean",
            "description": "[verify] Require 'interno' sensitivity for external references.",
            "default": False,
        },
    },
    "required": ["action", "bank"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_naming
# ---------------------------------------------------------------------------
BRAIN_NAMING = {
    "type": "object",
    "description": (
        "Plan (or apply) readable filename changes for a vault from a spec JSON "
        "prepared outside the vault and Git. Default is a read-only plan; pass "
        "apply=True to execute, which requires a backup directory. Use to "
        "de-obfuscate generated filenames safely."
    ),
    "properties": {
        "vault": {"type": "string", "description": "Absolute path to the vault directory."},
        "spec": {
            "type": "string",
            "description": "Absolute path to the naming spec JSON prepared outside the vault.",
        },
        "apply": {
            "type": "boolean",
            "description": "Apply the rename plan instead of only previewing it.",
            "default": False,
        },
        "sha_plan": {
            "type": "string",
            "description": "Expected SHA-256 of the plan file; rejects mismatches when applying.",
        },
        "backup_dir": {
            "type": "string",
            "description": "Absolute path of the backup directory required when applying.",
        },
    },
    "required": ["vault", "spec"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# brain_transcript_cycle
# ---------------------------------------------------------------------------
BRAIN_TRANSCRIPT_CYCLE = {
    "type": "object",
    "description": (
        "Drive one step of the transcript custody and analysis pipeline over a "
        "private bank (custody area outside any vault and Git worktree). Steps: "
        "ingresar (import transcript bytes/parts), registrar (commit a capture "
        "receipt), segmentar (split a committed capture into spans), analizar "
        "(consolidate agent-authored analysis), cobertura (coverage report), "
        "indexar (rebuild the query index), revisar-antecedentes (historical "
        "context for new analysis), taxonomia (store taxonomy), permiso (record a "
        "custody purpose decision), estado/verificar/inventario-validar/conciliar "
        "(read-only custody checks), buscar (query context package). A full cycle "
        "is: ingresar -> registrar -> segmentar -> analizar -> cobertura -> indexar. "
        "Profile JSON must contain company_id and allowed_purposes and live outside "
        "the vault."
    ),
    "properties": {
        "step": {
            "type": "string",
            "enum": [
                "ingresar",
                "registrar",
                "segmentar",
                "analizar",
                "cobertura",
                "indexar",
                "revisar-antecedentes",
                "taxonomia",
                "permiso",
                "estado",
                "verificar",
                "inventario-validar",
                "conciliar",
                "buscar",
            ],
            "description": "Pipeline step to execute.",
        },
        "bank": {
            "type": "string",
            "description": "Absolute path to the private custody bank (must not be inside a vault or Git worktree).",
        },
        "profile": {
            "type": "string",
            "description": "Absolute path to the profile JSON: {company_id, allowed_purposes:[...], optional bank/vault}.",
        },
        "request_id": {
            "type": "string",
            "description": "Caller-supplied request id for the custody ledger (default: generated).",
        },
        "purpose": {
            "type": "string",
            "description": "Purpose scope that must be allowed by the profile (e.g. custody, local_analysis).",
        },
        "commit": {
            "type": "boolean",
            "description": "Apply the local custody mutation; default is a read-only preview.",
            "default": False,
        },
        "audience": {
            "type": "string",
            "description": "Audience scope; required for segmentar/analizar/cobertura/indexar/revisar-antecedentes, optional for estado.",
        },
        "archivo": {
            "type": "string",
            "description": "[ingresar] Absolute path to the transcript file to import.",
        },
        "parts_manifest": {
            "type": "string",
            "description": "[ingresar] Absolute path to a JSON parts manifest instead of a single file.",
        },
        "source_id": {"type": "string", "description": "[ingresar] Transcript source id."},
        "account_id": {"type": "string", "description": "[ingresar] Account id."},
        "attempt_id": {"type": "string", "description": "[ingresar] Attempt id."},
        "closed": {
            "type": "boolean",
            "description": "[ingresar] Mark the capture closed (complete).",
        },
        "expected_parts": {
            "type": "integer",
            "description": "[ingresar] Expected part count for closed captures.",
        },
        "capture_manifest": {
            "type": "string",
            "description": "[registrar] Absolute path to the capture receipt JSON produced by ingresar.",
        },
        "tr_id": {
            "type": "string",
            "description": "[segmentar/cobertura] Transcript id.",
        },
        "version": {
            "type": "string",
            "description": "[segmentar] Version id to segment.",
        },
        "policy": {
            "type": "string",
            "description": "[segmentar] Segmentation policy id.",
        },
        "max_core_bytes": {
            "type": "integer",
            "description": "[segmentar] Max bytes for a core segment (default 4096).",
        },
        "context_bytes": {
            "type": "integer",
            "description": "[segmentar] Context bytes around a segment (default 256).",
        },
        "run": {
            "type": "string",
            "description": "[cobertura] Analysis run id.",
        },
        "input": {
            "type": "string",
            "description": "[analizar/permiso/taxonomia] Absolute path to the JSON input payload prepared outside the vault.",
        },
        "event": {
            "type": "string",
            "description": "[revisar-antecedentes/taxonomia] Absolute path to the event JSON.",
        },
        "snapshot": {
            "type": "string",
            "description": "[revisar-antecedentes/inventario-validar/conciliar/indexar] Snapshot JSON path, or 'current' for the live watermark.",
        },
        "results": {
            "type": "string",
            "description": "[revisar-antecedentes] Optional agent-authored results JSON array path.",
        },
        "previous": {
            "type": "string",
            "description": "[revisar-antecedentes] Prior review bundle path relative to the bank.",
        },
        "taxonomy_version": {
            "type": "string",
            "description": "[revisar-antecedentes] Exact stored taxonomy version for claim resolution.",
        },
        "request": {
            "type": "string",
            "description": "[buscar] Absolute path to the query request JSON {query, company, audience, purpose, ...}.",
        },
        "output": {
            "type": "string",
            "description": "Optional absolute path for an immutable JSON report; must not already exist.",
        },
    },
    "required": ["step", "bank", "profile", "purpose"],
    "additionalProperties": False,
}

# name -> (schema, engine script, description)
TOOLS = [
    ("brain_doctor", BRAIN_DOCTOR, "cerebro.py"),
    ("brain_create_vault", BRAIN_CREATE_VAULT, "cerebro.py"),
    ("brain_validate_vault", BRAIN_VALIDATE_VAULT, "validar_boveda.py"),
    ("brain_status", BRAIN_STATUS, "cerebro.py"),
    ("brain_register_vault", BRAIN_REGISTER_VAULT, "registrar_boveda_codex.py"),
    ("brain_resolve_vault", BRAIN_RESOLVE_VAULT, "resolver_boveda_codex.py"),
    ("brain_query", BRAIN_QUERY, "cerebro.py"),
    ("brain_capture", BRAIN_CAPTURE, "cerebro.py"),
    ("brain_knowledge_map", BRAIN_KNOWLEDGE_MAP, "cerebro.py"),
    ("brain_relations", BRAIN_RELATIONS, "cerebro.py"),
    ("brain_references", BRAIN_REFERENCES, "plugin_references.py"),
    ("brain_naming", BRAIN_NAMING, "nombres_legibles.py"),
    ("brain_transcript_cycle", BRAIN_TRANSCRIPT_CYCLE, "transcripciones.py"),
]
