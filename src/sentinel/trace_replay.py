from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from sentinel.session_trace import _digest


def summarize_trace(trace_path: str | Path) -> dict:
    path = Path(trace_path)
    rows = _read_jsonl(path)
    digests_valid = all(_digest_without_digest(row) == row.get("digest") for row in rows)

    session_event = next((row for row in rows if row.get("event_type") == "session.started"), None)
    decisions = [_decision_summary(row) for row in rows if row.get("event_type") == "decision.recorded"]

    return {
        "status": "ok" if rows and digests_valid else "error",
        "trace_path": str(path),
        "session_id": rows[0].get("session_id") if rows else None,
        "event_count": len(rows),
        "event_types": dict(Counter(row.get("event_type") for row in rows)),
        "session": session_event.get("payload", {}) if session_event else {},
        "decisions": decisions,
        "file_effects": _collect_file_effects(rows),
        "rollback_results": _collect_rollback_results(rows),
        "user_actions": [
            row.get("payload", {}).get("action")
            for row in rows
            if row.get("event_type") == "user.action"
        ],
        "process_lifecycle": [
            row.get("event_type")
            for row in rows
            if str(row.get("event_type", "")).startswith("process.")
        ],
        "digests_valid": digests_valid,
    }


def render_trace_text(summary: dict) -> str:
    lines = [
        "Cortex Sentinel Trace",
        f"Status: {summary.get('status')}",
        f"Trace: {summary.get('trace_path')}",
        f"Session: {summary.get('session_id')}",
        f"Events: {summary.get('event_count')}",
        f"Digests valid: {summary.get('digests_valid')}",
        "",
        "Session Metadata",
    ]
    session = summary.get("session") or {}
    lines.extend(
        [
            f"Command: {session.get('command', '')}",
            f"Config: {session.get('config_path', '')}",
            f"CWD: {session.get('cwd', '')}",
            "",
            "Decisions",
        ]
    )

    decisions = summary.get("decisions") or []
    if not decisions:
        lines.append("- none")
    for decision in decisions:
        effects = ", ".join(decision.get("policy_effect_ids") or [])
        lines.append(
            "- "
            f"#{decision.get('sequence')} "
            f"{decision.get('policy_action')} "
            f"risk={decision.get('policy_risk')} "
            f"source={decision.get('policy_source')} "
            f"effects={effects} "
            f"prompt={decision.get('prompt_line')}"
        )
        reason = decision.get("policy_reason")
        if reason:
            lines.append(f"  reason={reason}")

    user_actions = ", ".join(action for action in summary.get("user_actions") or [] if action)
    process_lifecycle = ", ".join(summary.get("process_lifecycle") or [])
    rollback_results = summary.get("rollback_results") or []
    lines.extend(
        [
            "",
            f"Rollback Results: {len(rollback_results)}",
            f"User Actions: {user_actions or 'none'}",
            f"Process Lifecycle: {process_lifecycle or 'none'}",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _digest_without_digest(row: dict) -> str:
    event = dict(row)
    event.pop("digest", None)
    return _digest(event)


def _decision_summary(row: dict) -> dict:
    payload = row.get("payload", {})
    policy = payload.get("policy", {})
    auditor = payload.get("auditor", {})
    return {
        "sequence": row.get("sequence"),
        "prompt_line": payload.get("prompt_line"),
        "policy_action": policy.get("action"),
        "policy_reason": policy.get("reason"),
        "policy_risk": policy.get("risk"),
        "policy_effect_ids": policy.get("effect_ids") or [],
        "policy_source": policy.get("source"),
        "override_id": policy.get("override_id"),
        "auditor_verdict": auditor.get("verdict"),
        "auditor_reason": auditor.get("reason"),
        "file_effect_count": len(payload.get("file_effects") or []),
    }


def _collect_file_effects(rows: list[dict]) -> list[dict]:
    effects: list[dict] = []
    for row in rows:
        effects.extend(row.get("payload", {}).get("file_effects") or [])
    return effects


def _collect_rollback_results(rows: list[dict]) -> list[dict]:
    rollback_results: list[dict] = []
    for row in rows:
        if row.get("event_type") == "enforcement.rollback":
            rollback_results.extend(row.get("payload", {}).get("rollback_results") or [])
    return rollback_results
