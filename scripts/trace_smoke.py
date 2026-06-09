#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.policy import FileEffect, PolicyAction, PolicyDecision
from sentinel.session_trace import SessionTraceStore


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sentinel-trace-smoke-") as tmp:
        trace_dir = Path(tmp) / "traces"
        store = SessionTraceStore(trace_dir, session_id="trace-smoke")
        store.record_session_started(
            command="python fixture_agent.py",
            config_path="sentinel.yaml",
            cwd=tmp,
        )
        store.record_process_event("process.started", {"pid": 12345})
        store.record_decision(
            prompt_line="Fixture agent wants to write docs. Proceed [y/n]?",
            file_effects=[FileEffect("modified", "docs/readme.md")],
            policy_decision=PolicyDecision(
                PolicyAction.REVIEW,
                "Observed file effects are outside auto-approve paths; requires audit.",
            ),
            auditor_verdict=True,
            auditor_reason="Structured auditor allowed the docs change.",
        )
        store.record_user_action("approve", {"source": "smoke"})
        store.record_enforcement_rollback(
            file_effects=[FileEffect("created", ".env")],
            rollback_results=[
                {
                    "path": ".env",
                    "operation": "created",
                    "rollback": "deleted-created-file",
                }
            ],
        )
        store.record_process_event("process.stopped", {"returncode": 0})

        rows = [json.loads(line) for line in store.path.read_text().splitlines()]
        report = {
            "status": "ok" if trace_has_required_fields(rows) else "error",
            "trace_path": str(store.path),
            "event_count": len(rows),
            "has_command_metadata": has_command_metadata(rows),
            "has_prompt_text": has_prompt_text(rows),
            "has_file_effects": has_file_effects(rows),
            "has_policy_decision": has_policy_decision(rows),
            "has_auditor_verdict": has_auditor_verdict(rows),
            "has_user_action": has_user_action(rows),
            "has_rollback_event": has_rollback_event(rows),
            "has_process_lifecycle": has_process_lifecycle(rows),
            "has_stable_digests": has_stable_digests(rows),
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "ok" else 1


def trace_has_required_fields(rows):
    return all(
        [
            has_command_metadata(rows),
            has_prompt_text(rows),
            has_file_effects(rows),
            has_policy_decision(rows),
            has_auditor_verdict(rows),
            has_user_action(rows),
            has_rollback_event(rows),
            has_process_lifecycle(rows),
            has_stable_digests(rows),
        ]
    )


def has_command_metadata(rows):
    return any(
        row["event_type"] == "session.started"
        and row["payload"].get("command")
        and row["payload"].get("config_path")
        and row["payload"].get("cwd")
        for row in rows
    )


def has_prompt_text(rows):
    return any(row["payload"].get("prompt_line") for row in rows)


def has_file_effects(rows):
    return any(row["payload"].get("file_effects") for row in rows)


def has_policy_decision(rows):
    return any(row["payload"].get("policy", {}).get("action") for row in rows)


def has_auditor_verdict(rows):
    return any("verdict" in row["payload"].get("auditor", {}) for row in rows)


def has_user_action(rows):
    return any(row["event_type"] == "user.action" for row in rows)


def has_rollback_event(rows):
    return any(
        row["event_type"] == "enforcement.rollback"
        and row["payload"].get("rollback_results")
        and "SECRET" not in json.dumps(row)
        for row in rows
    )


def has_process_lifecycle(rows):
    event_types = {row["event_type"] for row in rows}
    return {"process.started", "process.stopped"} <= event_types


def has_stable_digests(rows):
    return bool(rows) and all(str(row.get("digest", "")).startswith("sha256:") for row in rows)


if __name__ == "__main__":
    raise SystemExit(main())
