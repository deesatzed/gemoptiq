#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import textwrap
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.config import SentinelConfig
from sentinel.effects import FileEffectObserver
from sentinel.enforcer import ContinuousEnforcer
from sentinel.policy import PolicyAction, SentinelPolicy
from sentinel.pty_runner import PtyAgentRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test no-prompt protected-path enforcement.")
    parser.add_argument("--dry-run", action="store_true", help="Emit a representative report.")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(
            json.dumps(
                build_report(
                    "dry-run",
                    True,
                    True,
                    True,
                    protected_file_present=False,
                    rollback_performed=True,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="sentinel-enforcement-smoke-") as tmp:
        workspace = Path(tmp)
        agent_script = workspace / "agent_writes_secret.py"
        protected_file = workspace / ".env"
        agent_script.write_text(
            textwrap.dedent(
                f"""
                import pathlib
                import time

                pathlib.Path({str(protected_file)!r}).write_text("SECRET=1")
                print("wrote-protected-file", flush=True)
                time.sleep(60)
                """
            ).strip()
        )

        runner = PtyAgentRunner(f"{sys.executable} {agent_script}")
        observer = FileEffectObserver(workspace)
        policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))
        enforcer = ContinuousEnforcer(
            runner=runner,
            observer=observer,
            policy=policy,
            interval_seconds=0.05,
        )

        runner.start()
        enforcer.start()
        try:
            wait_for_block_and_rollback(enforcer, timeout_seconds=5)

            protected_effect_detected = bool(
                enforcer.last_decision and enforcer.last_decision.action is PolicyAction.BLOCK
            )
            runner_suspended = protected_effect_detected
            protected_file_present = protected_file.exists()
            rollback_performed = any(
                result.get("rollback") in {"deleted-created-file", "restored-baseline"}
                for result in enforcer.last_rollback_results
            )
            status = (
                "ok"
                if protected_effect_detected
                and runner_suspended
                and rollback_performed
                and not protected_file_present
                else "error"
            )
            report = build_report(
                status,
                protected_effect_detected,
                runner_suspended,
                True,
                protected_file_present=protected_file_present,
                rollback_performed=rollback_performed,
                workspace=str(workspace),
                matched_pattern=(
                    enforcer.last_decision.matched_pattern
                    if enforcer.last_decision
                    else None
                ),
                effects=[
                    {"operation": effect.operation, "path": effect.path}
                    for effect in enforcer.last_effects
                ],
                rollback_results=enforcer.last_rollback_results,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if status == "ok" else 1
        finally:
            enforcer.stop()
            runner.kill()


def wait_for_block_and_rollback(enforcer: ContinuousEnforcer, *, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    saw_block = False
    while time.time() < deadline:
        saw_block = bool(
            enforcer.last_decision and enforcer.last_decision.action is PolicyAction.BLOCK
        )
        if saw_block and enforcer.last_rollback_results:
            return True
        time.sleep(0.05)
    return saw_block


def build_report(
    status,
    protected_effect_detected,
    runner_suspended,
    disposable_workspace,
    *,
    protected_file_present=None,
    rollback_performed=None,
    workspace="",
    matched_pattern=None,
    effects=None,
    rollback_results=None,
):
    return {
        "status": status,
        "protected_effect_detected": protected_effect_detected,
        "runner_suspended": runner_suspended,
        "protected_file_present": protected_file_present,
        "rollback_performed": rollback_performed,
        "disposable_workspace": disposable_workspace,
        "matched_pattern": matched_pattern,
        "effects": effects or [],
        "rollback_results": rollback_results or [],
        "workspace": workspace,
    }


if __name__ == "__main__":
    raise SystemExit(main())
