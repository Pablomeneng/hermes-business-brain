#!/usr/bin/env python3
"""Transcript custody and agent-authored analysis. Console output omits passages."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

from transcripciones_modelo import ModelError, atomic_write, json_bytes, load_json, read_bytes, result, safe_id, safe_path, sha256_bytes, validate_bank_location
from transcripciones_custodia import load_catalog, register_capture, verify_bank
from transcripciones_inventario import reconcile, validate_inventory
from transcripciones_ingreso import ingest, read_parts_manifest
from transcripciones_pipeline import (segment_capture, consolidate_analysis, coverage_report,
    review_snapshot, review_history, store_taxonomy)
from transcripciones_permisos import record_decision
from transcripciones_indice import rebuild_index, watermark
from transcripciones_contexto import build_context_request


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("registrar", "ingresar", "estado", "verificar", "inventario-validar", "conciliar",
                 "segmentar", "analizar", "cobertura", "indexar", "buscar", "revisar-antecedentes", "permiso", "taxonomia"):
        sub = commands.add_parser(name)
        for flag in ("bank", "profile", "request-id", "purpose"):
            sub.add_argument("--" + flag, required=True)
        sub.add_argument("--output", help="Optional immutable JSON report path")
        if name in ("registrar", "ingresar", "segmentar", "analizar", "indexar", "revisar-antecedentes", "permiso", "taxonomia"):
            sub.add_argument("--commit", action="store_true", help="Apply local custody mutation; default is preview")
        if name in ("segmentar", "analizar", "cobertura", "indexar", "revisar-antecedentes"):
            sub.add_argument("--audience", required=True)
        elif name == "estado":
            sub.add_argument("--audience")
        if name == "registrar":
            sub.add_argument("--capture-manifest", required=True)
        elif name in ("conciliar", "inventario-validar"):
            sub.add_argument("--snapshot", required=True)
        elif name == "ingresar":
            source = sub.add_mutually_exclusive_group(required=True)
            source.add_argument("--archivo")
            source.add_argument("--stdin", action="store_true", help="Preserve pasted UTF-8/input bytes from standard input")
            source.add_argument("--parts-manifest")
            for flag in ("source-id", "account-id", "attempt-id"):
                sub.add_argument("--" + flag, required=True)
            sub.add_argument("--closed", action="store_true")
            sub.add_argument("--expected-parts", type=int)
        elif name == "segmentar":
            sub.add_argument("--tr-id", required=True)
            sub.add_argument("--version", required=True)
            sub.add_argument("--policy", required=True)
            sub.add_argument("--max-core-bytes", type=int, default=4096)
            sub.add_argument("--context-bytes", type=int, default=256)
        elif name in ("analizar", "permiso", "taxonomia"):
            sub.add_argument("--input", required=True)
            if name == "taxonomia":
                sub.add_argument("--event")
        elif name == "cobertura":
            sub.add_argument("--tr-id", required=True)
            sub.add_argument("--run", required=True)
        elif name == "indexar":
            sub.add_argument("--snapshot", required=True, help="Expected watermark, or current for the live snapshot")
        elif name == "buscar":
            sub.add_argument("--request", required=True, help="Query/company/audience/purpose JSON; --output is required")
        elif name == "revisar-antecedentes":
            sub.add_argument("--event", required=True)
            sub.add_argument("--snapshot", required=True)
            sub.add_argument("--results", help="Optional agent-authored JSON results array")
            sub.add_argument("--previous", help="Prior immutable review bundle path relative to bank")
            sub.add_argument("--taxonomy-version", help="Exact stored taxonomy for resolved claim identities")
    return p


def _validate_context(args):
    safe_id(args.request_id)
    profile = load_json(args.profile)
    if not isinstance(profile, dict) or not isinstance(profile.get("company_id"), str) or not profile["company_id"].strip():
        raise ModelError("PROFILE_INVALID")
    purposes = profile.get("allowed_purposes")
    if not isinstance(purposes, list) or not all(isinstance(p, str) and p.strip() for p in purposes):
        raise ModelError("PROFILE_INVALID")
    if args.purpose not in purposes:
        raise ModelError("PURPOSE_DENIED")
    bank = validate_bank_location(args.bank, vault=profile.get("vault"))
    if "bank" in profile and validate_bank_location(profile["bank"], vault=profile.get("vault")) != bank:
        raise ModelError("BANK_PROFILE_MISMATCH")
    # Output is a separately requested report, never an overwrite of source data.
    if args.output:
        output = Path(args.output)
        if args.command == "buscar":
            validate_bank_location(output.parent, vault=profile.get("vault"))
        safe_path(output.parent, output.name)
        if output.exists():
            raise ModelError("OUTPUT_EXISTS")
        args._output_safe = True
    return profile


def execute(args):
    profile = _validate_context(args)
    scope = dict(company=profile["company_id"], audience=getattr(args, "audience", None), purpose=args.purpose)
    if args.command == "segmentar":
        return segment_capture(args.bank, args.tr_id, args.version, **scope, policy=args.policy,
                               max_core_bytes=args.max_core_bytes, context_bytes=args.context_bytes, commit=args.commit)
    if args.command == "analizar":
        return consolidate_analysis(args.bank, load_json(args.input), **scope, commit=args.commit)
    if args.command == "cobertura":
        return coverage_report(args.bank, args.tr_id, args.run, **scope)
    if args.command == "taxonomia":
        if args.purpose != "local_analysis":
            raise ModelError("ANALYSIS_SCOPE_REQUIRED")
        return store_taxonomy(args.bank, load_json(args.input), event=load_json(args.event) if args.event else None, commit=args.commit)
    if args.command == "permiso":
        decision = load_json(args.input)
        if decision.get("company") != profile["company_id"] or args.purpose != "custody":
            raise ModelError("PERMISSION_SCOPE_MISMATCH")
        row = record_decision(args.bank, decision, commit=args.commit)
        return result("permiso", evidence={"sequence": row["sequence"], "committed": args.commit,
                                           "decision_hash": sha256_bytes(json_bytes(row))})
    if args.command == "indexar":
        if args.purpose not in ("local_analysis", "internal_query"):
            raise ModelError("INDEX_SCOPE_REQUIRED")
        report = rebuild_index(args.bank, None if args.snapshot == "current" else args.snapshot,
                               **scope, commit=args.commit)
        return result("indexar", evidence=report)
    if args.command == "buscar":
        if not args.output:
            raise ModelError("PRIVATE_OUTPUT_REQUIRED")
        request = load_json(args.request)
        if not isinstance(request, dict) or set(request) - {"query", "company", "audience", "purpose", "references", "limit",
                                                           "task", "entities", "period", "mode"}:
            raise ModelError("QUERY_REQUEST_INVALID")
        if request.get("company") != profile["company_id"] or request.get("purpose") != args.purpose or args.purpose not in ("internal_query", "local_analysis", "evaluation"):
            raise ModelError("QUERY_SCOPE_MISMATCH")
        package = build_context_request(dict(request, bank=args.bank))
        return result("buscar", evidence={"context": package})
    if args.command == "revisar-antecedentes":
        return review_history(args.bank, load_json(args.event), args.snapshot, **scope,
                              results=load_json(args.results) if args.results else None,
                              previous_path=args.previous, taxonomy_version=args.taxonomy_version, commit=args.commit)
    if args.command == "registrar":
        return register_capture(args.bank, args.capture_manifest, commit=args.commit)
    if args.command == "ingresar":
        expected, closed = args.expected_parts, args.closed
        if args.parts_manifest:
            if expected is not None or closed:
                raise ModelError("PARTS_OPTIONS_CONFLICT")
            parts, expected, closed = read_parts_manifest(args.parts_manifest)
        else:
            payload = sys.stdin.buffer.read() if args.stdin else read_bytes(Path(args.archivo).parent, Path(args.archivo).name)
            parts = [(1, payload)]
        return ingest(args.bank, job_id=args.request_id, account_id=args.account_id,
                      source_id=args.source_id, attempt_id=args.attempt_id, parts=parts,
                      closed=closed, expected_parts=expected,
                      method="pasted-text" if args.stdin else "file-import", commit=args.commit)
    if args.command == "verificar":
        return verify_bank(args.bank)
    if args.command == "estado":
        rows = load_catalog(args.bank)
        dimensions = {dimension: dict(Counter(row["states"][dimension] for row in rows))
                      for dimension in ("integrity", "completeness", "analysis", "editorial", "validity")}
        evidence = {"transcriptions": len(rows), "states": dimensions,
                    "account_count": len({o["account_id"] for row in rows for o in row["occurrences"]}),
                    "index_watermark": watermark(args.bank)}
        if args.audience:
            evidence["review_snapshot_id"] = review_snapshot(args.bank, **scope)["snapshot_id"]
        return result("estado", evidence=evidence)
    snapshot = load_json(args.snapshot)
    if args.command == "inventario-validar":
        return result(args.command, input_hashes=[sha256_bytes(json_bytes(snapshot))], evidence=validate_inventory(snapshot))
    return reconcile(snapshot, load_catalog(args.bank))


def _failure(args, exc):
    code = exc.code if isinstance(exc, ModelError) else "INPUT_OR_IO_INVALID"
    output = result(args.command, request_id=args.request_id, status="BLOCKED")
    output["errors"] = [{"code": code, "field": "input", "cause": "Input or local custody validation failed",
                         "recoverable": True, "next_action": "Correct the reported input condition and retry"}]
    output["next_action"] = output["errors"][0]["next_action"]
    return output


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        output = execute(args)
        output.update(operation=args.command, request_id=args.request_id)
        if output["warnings"] and output["status"] == "DONE":
            output["status"] = "DONE_WITH_CONCERNS"
    except (ModelError, OSError, ValueError, TypeError, KeyError) as exc:
        output = _failure(args, exc)
    if args.output and (args.command != "buscar" or getattr(args, "_output_safe", False)):
        try:
            path = Path(args.output)
            safe_path(path.parent, path.name)
            if path.exists():
                raise ModelError("OUTPUT_EXISTS")
            atomic_write(path.parent, path.name, json_bytes(output))
            if args.command == "buscar" and not output["errors"]:
                package = output["evidence"]["context"]
                output = result("buscar", request_id=args.request_id,
                                outputs=[{"path": str(path.absolute()), "sha256": sha256_bytes(json_bytes(output))}],
                                evidence={"candidate_count": len(package["candidates"]), "abstention": package["abstention"],
                                          "semantic_answer_generated": False})
        except (ModelError, OSError, ValueError, TypeError) as exc:
            output = _failure(args, exc)
    # JSON remains lossless even when Windows redirects stdout through cp1252.
    print(json.dumps(output, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if output["status"] in ("DONE", "DONE_WITH_CONCERNS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
