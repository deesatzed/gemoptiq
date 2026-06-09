#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.pty_runner import PtyAgentRunner

DEFAULT_PROMPT_PATTERN = r"\?\s*$|\[y/n\]"
CLAUDE_TRUST_COMMAND = "claude --bare --safe-mode --permission-mode plan --tools ''"
CLAUDE_TRUST_PROMPT_PATTERN = (
    r"Quick.*safety.*check|No,.*exit|Enter.*confirm|Accessing.*workspace"
)
DEFAULT_AGENT_PROBES = [
    ("codex", ["codex", "--version"]),
    ("claude", ["claude", "--version"]),
    ("gemini", ["gemini", "--version"]),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Opt-in smoke test for a real local agent command in a disposable workspace."
    )
    parser.add_argument("--dry-run", action="store_true", help="Emit a guarded representative report.")
    parser.add_argument(
        "--probe-installed-agents",
        action="store_true",
        help="Run safe non-interactive version probes for known local agent CLIs.",
    )
    parser.add_argument(
        "--claude-trust-smoke",
        action="store_true",
        help=(
            "Run Claude Code's workspace trust prompt in a temp workspace, answer "
            "'No, exit', and kill the process. Does not prove model/tool behavior."
        ),
    )
    parser.add_argument(
        "--probe-agent-command",
        action="append",
        default=[],
        metavar="NAME=COMMAND",
        help="Run a safe non-interactive metadata probe command. Repeatable; primarily for tests/custom probes.",
    )
    parser.add_argument("--agent-command", help="Real agent command to run inside a temp workspace.")
    parser.add_argument(
        "--approval-input",
        default="n",
        help="Input sent when a prompt is detected. Defaults to 'n' for safety.",
    )
    parser.add_argument(
        "--prompt-pattern",
        default=DEFAULT_PROMPT_PATTERN,
        help="Regex used to detect an interactive prompt.",
    )
    parser.add_argument(
        "--expect-output",
        default="",
        help="Optional output marker to wait for after input injection.",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="Maximum seconds to wait.")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(json.dumps(build_report("dry-run", executed=False), indent=2, sort_keys=True))
        return 0

    if args.probe_installed_agents or args.probe_agent_command:
        probes = parse_probe_commands(args.probe_agent_command)
        if args.probe_installed_agents or not probes:
            probes.extend(DEFAULT_AGENT_PROBES)
        report = build_agent_probe_report(probes, timeout_seconds=args.timeout)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "ok" else 1

    if args.claude_trust_smoke:
        with tempfile.TemporaryDirectory(prefix="sentinel-claude-trust-smoke-") as tmp:
            report = run_agent_smoke(
                command=CLAUDE_TRUST_COMMAND,
                workspace=Path(tmp),
                approval_input="2",
                prompt_pattern=CLAUDE_TRUST_PROMPT_PATTERN,
                expect_output="",
                timeout_seconds=args.timeout,
            )
            report["claude_trust_smoke"] = True
            report["proves_model_or_tool_behavior"] = False
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "ok" else 1

    if not args.agent_command:
        parser.error("--agent-command is required unless --dry-run is used.")

    with tempfile.TemporaryDirectory(prefix="sentinel-real-agent-smoke-") as tmp:
        workspace = Path(tmp)
        report = run_agent_smoke(
            command=args.agent_command,
            workspace=workspace,
            approval_input=args.approval_input,
            prompt_pattern=args.prompt_pattern,
            expect_output=args.expect_output,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "ok" else 1


def parse_probe_commands(values: list[str]) -> list[tuple[str, list[str]]]:
    probes: list[tuple[str, list[str]]] = []
    for value in values:
        if "=" not in value:
            raise SystemExit("--probe-agent-command must use NAME=COMMAND.")
        name, command_text = value.split("=", 1)
        name = name.strip()
        command = shlex.split(command_text)
        if not name or not command:
            raise SystemExit("--probe-agent-command must include a non-empty name and command.")
        probes.append((name, command))
    return probes


def build_agent_probe_report(
    probes: list[tuple[str, list[str]]],
    *,
    timeout_seconds: float,
) -> dict:
    results = {
        name: run_agent_probe(command, timeout_seconds=timeout_seconds)
        for name, command in probes
    }
    pass_count = sum(1 for result in results.values() if result["status"] == "pass")
    return {
        "status": "ok" if pass_count else "unavailable",
        "safe_noninteractive_probe": True,
        "proves_interactive_behavior": False,
        "pass_count": pass_count,
        "total": len(results),
        "agent_probes": results,
    }


def run_agent_probe(command: list[str], *, timeout_seconds: float) -> dict:
    executable = shutil.which(command[0])
    if executable is None:
        return {
            "status": "missing",
            "command": command,
            "executable": "",
            "returncode": None,
            "evidence": f"{command[0]} not found on PATH.",
        }
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip()
        return {
            "status": "timeout",
            "command": command,
            "executable": executable,
            "returncode": None,
            "evidence": output[-2000:],
        }

    output = (result.stdout + result.stderr).strip()
    return {
        "status": "pass" if result.returncode == 0 else "error",
        "command": command,
        "executable": executable,
        "returncode": result.returncode,
        "evidence": output[-2000:],
    }


def run_agent_smoke(
    *,
    command: str,
    workspace: Path,
    approval_input: str,
    prompt_pattern: str,
    expect_output: str,
    timeout_seconds: float,
) -> dict:
    prompt_regex = re.compile(prompt_pattern, re.IGNORECASE)
    runner = PtyAgentRunner(command, cwd=str(workspace))
    prompt_text = ""
    response_text = ""
    prompt_detected = False
    input_injected = False
    killed = False
    started = False
    try:
        runner.start()
        started = True
        prompt_text = wait_for_output(
            runner,
            lambda seen: bool(prompt_regex.search(seen)),
            timeout_seconds=timeout_seconds,
        )
        prompt_detected = bool(prompt_regex.search(prompt_text))
        if prompt_detected:
            runner.write_input(_with_newline(approval_input))
            input_injected = True
            response_text = wait_for_output(
                runner,
                lambda seen: expect_output in seen if expect_output else len(seen) > 0,
                timeout_seconds=min(timeout_seconds, 3.0),
            )
    finally:
        runner.kill()
        killed = runner.process is None

    status = "ok" if started and prompt_detected and input_injected and killed else "error"
    if expect_output and expect_output not in response_text:
        status = "error"
    return build_report(
        status,
        executed=True,
        command=command,
        workspace=str(workspace),
        prompt_detected=prompt_detected,
        input_injected=input_injected,
        process_killed=killed,
        prompt_text=prompt_text,
        response_text=response_text,
        expect_output=expect_output,
    )


def wait_for_output(runner: PtyAgentRunner, done, *, timeout_seconds: float) -> str:
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
    status: str,
    *,
    executed: bool,
    command: str = "",
    workspace: str = "",
    prompt_detected: bool = False,
    input_injected: bool = False,
    process_killed: bool = False,
    prompt_text: str = "",
    response_text: str = "",
    expect_output: str = "",
) -> dict:
    return {
        "status": status,
        "executed": executed,
        "requires_explicit_command": True,
        "disposable_workspace": True,
        "command": command,
        "workspace": workspace,
        "prompt_detected": prompt_detected,
        "input_injected": input_injected,
        "process_killed": process_killed,
        "prompt_text": prompt_text,
        "response_text": response_text,
        "expect_output": expect_output,
    }


def _with_newline(value: str) -> str:
    return value if value.endswith("\n") else value + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
