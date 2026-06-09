from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sentinel.policy import FileEffect, PolicyDecision


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SessionTraceStore:
    def __init__(self, trace_dir: str | Path, *, session_id: str | None = None):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or f"session-{uuid4()}"
        self.path = self.trace_dir / f"{self.session_id}.jsonl"
        self._sequence = 0

    def record_session_started(self, *, command: str, config_path: str, cwd: str):
        return self.record(
            "session.started",
            {
                "command": command,
                "config_path": config_path,
                "cwd": cwd,
            },
        )

    def record_process_event(self, event_type: str, payload: dict):
        return self.record(event_type, payload)

    def record_user_action(self, action: str, details: dict | None = None):
        return self.record(
            "user.action",
            {
                "action": action,
                "details": details or {},
            },
        )

    def record_decision(
        self,
        *,
        prompt_line: str,
        file_effects: list[FileEffect],
        policy_decision: PolicyDecision,
        auditor_verdict: bool | None,
        auditor_reason: str | None,
    ):
        return self.record(
            "decision.recorded",
            {
                "prompt_line": prompt_line,
                "file_effects": [
                    {"operation": effect.operation, "path": effect.path}
                    for effect in file_effects
                ],
                "policy": {
                    "action": policy_decision.action.value,
                    "reason": policy_decision.reason,
                    "matched_pattern": policy_decision.matched_pattern,
                    "effect": _to_jsonable(policy_decision.effect),
                    "risk": policy_decision.risk,
                    "effect_ids": policy_decision.effect_ids,
                    "source": policy_decision.source,
                    "override_id": policy_decision.override_id,
                },
                "auditor": {
                    "verdict": auditor_verdict,
                    "reason": auditor_reason,
                },
            },
        )

    def record_enforcement_rollback(
        self,
        *,
        file_effects: list[FileEffect],
        rollback_results: list[dict[str, str]],
    ):
        return self.record(
            "enforcement.rollback",
            {
                "file_effects": [
                    {"operation": effect.operation, "path": effect.path}
                    for effect in file_effects
                ],
                "rollback_results": rollback_results,
            },
        )

    def record(self, event_type: str, payload: dict):
        self._sequence += 1
        event = {
            "session_id": self.session_id,
            "sequence": self._sequence,
            "timestamp": now_iso(),
            "event_type": event_type,
            "payload": _to_jsonable(payload),
        }
        event["digest"] = _digest(event)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        return event


def _to_jsonable(value):
    if is_dataclass(value):
        data = asdict(value)
        if "action" in data and hasattr(data["action"], "value"):
            data["action"] = data["action"].value
        return _to_jsonable(data)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _digest(event: dict) -> str:
    digest_payload = {key: value for key, value in event.items() if key != "digest"}
    encoded = json.dumps(
        digest_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()
