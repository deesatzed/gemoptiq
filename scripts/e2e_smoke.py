#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.auditor import parse_audit_response
from sentinel.config import load_config
from sentinel.policy import FileEffect, PolicyAction, SentinelPolicy
from sentinel.session_trace import SessionTraceStore


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sentinel-e2e-smoke-") as tmp:
        workspace = Path(tmp)
        checks = {
            "safe_auto_approval": safe_auto_approval(),
            "protected_path_block": protected_path_block(),
            "ambiguous_auditor_review": ambiguous_auditor_review(),
            "no_prompt_protected_write": no_prompt_protected_write(),
            "pty_prompt_handling": pty_prompt_handling(),
            "trace_export": trace_export(workspace),
            "config_profile": config_profile(workspace),
        }
        status = "ok" if all(checks.values()) else "error"
        report = {
            "status": status,
            "disposable_workspace": True,
            "workspace": str(workspace),
            **checks,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if status == "ok" else 1


def safe_auto_approval() -> bool:
    policy = SentinelPolicy(load_config("missing-e2e-config.yaml"))
    policy.config.auto_approve_paths = ["docs/**"]
    decision = policy.evaluate([FileEffect("modified", "docs/readme.md")])
    return decision.action is PolicyAction.ALLOW and decision.risk == "green"


def protected_path_block() -> bool:
    policy = SentinelPolicy(load_config("missing-e2e-config.yaml"))
    policy.config.protected_paths = ["**/.env"]
    decision = policy.evaluate([FileEffect("modified", ".env")])
    return decision.action is PolicyAction.BLOCK and decision.risk == "red"


def ambiguous_auditor_review() -> bool:
    result = parse_audit_response("The action may be safe, but I cannot tell.")
    return result.verdict == "block" and bool(result.reason)


def no_prompt_protected_write() -> bool:
    report = run_json_script("scripts/enforcement_smoke.py")
    return (
        report.get("status") == "ok"
        and report.get("protected_effect_detected") is True
        and report.get("runner_suspended") is True
        and report.get("rollback_performed") is True
        and report.get("protected_file_present") is False
        and report.get("disposable_workspace") is True
    )


def pty_prompt_handling() -> bool:
    report = run_json_script("scripts/agent_integration_smoke.py")
    return (
        report.get("status") == "ok"
        and report.get("prompt_detected") is True
        and report.get("input_injected") is True
        and report.get("process_killed") is True
    )


def trace_export(workspace: Path) -> bool:
    store = SessionTraceStore(workspace / "traces", session_id="e2e-smoke")
    store.record_session_started(
        command="python fixture_agent.py",
        config_path="sentinel.yaml",
        cwd=str(workspace),
    )
    store.record_process_event("process.started", {"pid": 123})
    store.record_decision(
        prompt_line="Update docs?",
        file_effects=[FileEffect("modified", "docs/readme.md")],
        policy_decision=SentinelPolicy(load_config("missing-e2e-config.yaml")).evaluate(
            [FileEffect("modified", "src/app.py")]
        ),
        auditor_verdict=True,
        auditor_reason="E2E smoke approval.",
    )
    store.record_user_action("approve_pending")
    store.record_process_event("process.stopped", {"returncode": 0})
    rows = [json.loads(line) for line in store.path.read_text().splitlines()]
    event_types = {row["event_type"] for row in rows}
    return (
        {"session.started", "decision.recorded", "user.action", "process.started", "process.stopped"}
        <= event_types
        and all(str(row.get("digest", "")).startswith("sha256:") for row in rows)
    )


def config_profile(workspace: Path) -> bool:
    config_path = workspace / "sentinel.yaml"
    config_path.write_text(
        "\n".join(
            [
                "policy_profile: locked",
                "policy_profiles:",
                "  locked:",
                "    protected_paths:",
                "      - '**/.env'",
                "    auto_approve_paths:",
                "      - 'docs/public/**'",
            ]
        )
    )
    config = load_config(str(config_path), strict=True)
    policy = SentinelPolicy(config)
    allow_decision = policy.evaluate([FileEffect("modified", "docs/public/readme.md")])
    block_decision = policy.evaluate([FileEffect("modified", ".env")])
    return (
        config.policy_profile == "locked"
        and allow_decision.action is PolicyAction.ALLOW
        and block_decision.action is PolicyAction.BLOCK
    )


def run_json_script(script_path: str) -> dict:
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
