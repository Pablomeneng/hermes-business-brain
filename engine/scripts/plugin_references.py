#!/usr/bin/env python3
"""CLI wrapper over the vendored ``referencias_externas`` engine module.

The upstream ``referencias_externas.py`` is a library without a command-line
entry point; this wrapper exposes its operations as a small argv interface so
the ``brain_references`` Hermes tool can drive it as a subprocess. It only adds
argument parsing and JSON printing around the vendored functions — no logic is
changed. Like the engine, it never reads a URL and registers metadata only
(records are prepared by the caller as JSON files outside the vault).

Actions:
  register   --bank PATH --metadata FILE [--commit]   register a reference record
  read       --bank PATH --reference-id ID --version-id VERSION   read one record
  decisions  --bank PATH                              list the permission chain
  verify     --bank PATH --refs FILE --company C --audience A --purpose P
             [--no-require-read] [--require-internal]  transitive closure check

Output is a single JSON document on stdout. Non-zero exit on engine errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from referencias_externas import (
    external_decisions,
    read_reference,
    record_external_decision,
    register_reference,
    verify_references,
)
from transcripciones_modelo import ModelError


def _load(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("register", help="Register local reference metadata (no content import)")
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True, help="JSON reference record prepared outside the vault")
    p.add_argument("--commit", action="store_true", help="Apply the custody mutation; default is a preview")

    p = sub.add_parser("read", help="Read one versioned reference record")
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--reference-id", required=True)
    p.add_argument("--version-id", required=True)

    p = sub.add_parser("decisions", help="List the permission decision chain for a bank")
    p.add_argument("--bank", type=Path, required=True)

    p = sub.add_parser("verify", help="Verify the transitive closure of external references")
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--refs", type=Path, required=True, help="JSON array of reference descriptors")
    p.add_argument("--company", required=True)
    p.add_argument("--audience", required=True)
    p.add_argument("--purpose", required=True)
    p.add_argument("--no-require-read", action="store_true", help="Do not require reading evidence for external refs")
    p.add_argument("--require-internal", action="store_true", help="Require 'interno' sensitivity for external refs")

    args = parser.parse_args()
    try:
        if args.action == "register":
            result = register_reference(args.bank, _load(args.metadata), commit=args.commit)
        elif args.action == "read":
            result = read_reference(args.bank, args.reference_id, args.version_id)
        elif args.action == "decisions":
            result = {"decisions": external_decisions(args.bank)}
        else:
            result = verify_references(
                args.bank,
                _load(args.refs),
                {"company": args.company, "audience": args.audience, "purpose": args.purpose},
                require_read=not args.no_require_read,
                require_internal=args.require_internal,
            )
    except ModelError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "error": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
