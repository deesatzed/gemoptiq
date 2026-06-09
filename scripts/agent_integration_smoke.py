#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import textwrap
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.pty_runner import PtyAgentRunner

PROMPT_PATTERN = re.compile(r"\?\s*$|\[y/n\]", re.IGNORECASE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test PTY-backed agent integration.")
    parser.add_argument("--dry-run", action="store_true", help="Emit a representative report.")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(json.dumps(build_report("dry-run", True, True, True, True), indent=2, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory(prefix="sentinel-agent-smoke-") as tmp:
        workspace = Path(tmp)
        agent_script = workspace / "agent_fixture.py"
        output_file = workspace / "approved.txt"
        agent_script.write_text(
            textwrap.dedent(
                f"""
                import pathlib
                import sys
                import time

                sys.stdout.write("Fixture agent wants to write approved.txt. Proceed [y/n]? ")
                sys.stdout.flush()
                answer = sys.stdin.readline().strip().lower()
                if answer == "y":
                    pathlib.Path({str(output_file)!r}).write_text("approved")
                    print("approved-write-complete", flush=True)
                else:
                    print("blocked", flush=True)
                time.sleep(60)
                """
            ).strip()
        )

        runner = PtyAgentRunner(f"{sys.executable} {agent_script}")
        runner.start()
        prompt_text = ""
        response_text = ""
        prompt_detected = False
        input_injected = False
        file_written = False
        killed = False
        try:
            prompt_text = wait_for_output(runner, lambda seen: bool(PROMPT_PATTERN.search(seen)))
            prompt_detected = bool(PROMPT_PATTERN.search(prompt_text))
            if prompt_detected:
                runner.write_input("y\n")
                input_injected = True
                response_text = wait_for_output(runner, lambda seen: "approved-write-complete" in seen)
                file_written = output_file.read_text() == "approved"
        finally:
            runner.kill()
            killed = runner.process is None

        status = "ok" if all([prompt_detected, input_injected, file_written, killed]) else "error"
        report = build_report(
            status,
            prompt_detected,
            input_injected,
            file_written,
            killed,
            prompt_text=prompt_text,
            response_text=response_text,
            workspace=str(workspace),
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if status == "ok" else 1


def wait_for_output(runner: PtyAgentRunner, done, timeout_seconds: float = 5.0) -> str:
    deadline = time.time() + timeout_seconds
    seen = ""
    while time.time() < deadline:
        chunk = runner.get_output()
        if chunk:
            seen += chunk
            if done(seen):
                return seen
        time.sleep(0.05)
    return seen


def build_report(
    status,
    prompt_detected,
    input_injected,
    file_written,
    killed,
    *,
    prompt_text="",
    response_text="",
    workspace="",
):
    return {
        "status": status,
        "prompt_detected": prompt_detected,
        "input_injected": input_injected,
        "disposable_workspace": True,
        "file_written": file_written,
        "process_killed": killed,
        "prompt_text": prompt_text,
        "response_text": response_text,
        "workspace": workspace,
    }


if __name__ == "__main__":
    raise SystemExit(main())
