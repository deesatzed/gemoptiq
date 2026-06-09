#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.auditor import AuditResult, Auditor
from sentinel.config import SentinelConfig


DEFAULT_INTENT = "Update project documentation in docs/ without changing code."
DEFAULT_EFFECT = "PROMPT: Update docs?\nFILE EFFECTS:\n- modified: docs/README.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test the Cortex Sentinel auditor.")
    parser.add_argument(
        "--model-id",
        default=SentinelConfig().model_id,
        help="MLX model id to load.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not load MLX; emit a representative structured report.",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        report = build_report(
            status="dry-run",
            model_id=args.model_id,
            result=AuditResult(
                verdict="allow",
                risk="green",
                reason="Dry-run structured auditor path is parseable.",
                raw_response='{"verdict":"allow","risk":"green","reason":"Dry-run structured auditor path is parseable."}',
            ),
            load_seconds=0.0,
            audit_seconds=0.0,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    load_start = time.perf_counter()
    auditor = Auditor(args.model_id)
    load_seconds = time.perf_counter() - load_start

    if auditor.model is None or auditor.tokenizer is None:
        report = {
            "status": "error",
            "model_id": args.model_id,
            "error": "Model or tokenizer not initialized.",
            "timing": {"load_seconds": load_seconds, "audit_seconds": 0.0},
        }
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    audit_start = time.perf_counter()
    result = auditor.audit_intent_result(DEFAULT_INTENT, DEFAULT_EFFECT)
    audit_seconds = time.perf_counter() - audit_start

    report = build_report(
        status="ok" if result.verdict in {"allow", "block", "review"} else "error",
        model_id=args.model_id,
        result=result,
        load_seconds=load_seconds,
        audit_seconds=audit_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


def build_report(
    *,
    status: str,
    model_id: str,
    result: AuditResult,
    load_seconds: float,
    audit_seconds: float,
):
    return {
        "status": status,
        "model_id": model_id,
        "timing": {
            "load_seconds": round(load_seconds, 6),
            "audit_seconds": round(audit_seconds, 6),
        },
        "verdict": {
            "verdict": result.verdict,
            "risk": result.risk,
            "reason": result.reason,
        },
        "raw_response": result.raw_response,
    }


if __name__ == "__main__":
    raise SystemExit(main())
