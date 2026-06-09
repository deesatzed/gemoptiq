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
CODEX_EXEC_MARKER = "SENTINEL_CODEX_OK"
CODEX_EXEC_PROMPT = (
    "Use the shell to run exactly this harmless command, then report the output: "
    "python -c 'print(\"SENTINEL_CODEX_OK\")'"
)
CODEX_TUI_MARKER = "SENTINEL_CODEX_TUI_OK"
CODEX_TUI_PROMPT = (
    "Use the shell to run exactly this harmless command and then report its output: "
    "python -c 'print(\"\".join(map(chr,[83,69,78,84,73,78,69,76,95,67,79,68,69,88,95,84,85,73,95,79,75])))'"
)
CODEX_TUI_INTERACTIONS = [
    (r"Do.*trust|Yes, continue|Press enter", "y"),
    (r"Would you like to run the following command|Yes, proceed", "y"),
]
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
        "--codex-exec-smoke",
        action="store_true",
        help=(
            "Run Codex exec in an ephemeral temp workspace and verify a harmless "
            "shell command_execution event. Proves model/tool behavior, not "
            "interactive prompt control."
        ),
    )
    parser.add_argument(
        "--codex-tui-smoke",
        action="store_true",
        help=(
            "Run Codex's full-screen TUI in an ephemeral git workspace, "
            "answer workspace trust and command approval prompts, and verify "
            "a harmless command output marker."
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
    parser.add_argument(
        "--interaction",
        action="append",
        default=[],
        metavar="REGEX=>INPUT",
        help=(
            "Script a prompt/input step. Repeat to prove multi-prompt flows, "
            "such as startup trust followed by a tool confirmation."
        ),
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

    if args.codex_exec_smoke:
        with tempfile.TemporaryDirectory(prefix="sentinel-codex-exec-smoke-") as tmp:
            report = run_codex_exec_smoke(Path(tmp), timeout_seconds=args.timeout)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "ok" else 1

    if args.codex_tui_smoke:
        with tempfile.TemporaryDirectory(prefix="sentinel-codex-tui-smoke-") as tmp:
            report = run_codex_tui_smoke(Path(tmp), timeout_seconds=args.timeout)
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
            interactions=parse_interactions(args.interaction),
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "ok" else 1


def parse_interactions(values: list[str]) -> list[tuple[str, str]]:
    interactions: list[tuple[str, str]] = []
    for value in values:
        if "=>" not in value:
            raise SystemExit("--interaction must use REGEX=>INPUT.")
        pattern, input_text = value.split("=>", 1)
        if not pattern:
            raise SystemExit("--interaction requires a non-empty regex.")
        interactions.append((pattern, input_text))
    return interactions


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


def run_codex_exec_smoke(workspace: Path, *, timeout_seconds: float) -> dict:
    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "-C",
        str(workspace),
        "--json",
        CODEX_EXEC_PROMPT,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            input="",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip()
        return {
            "status": "error",
            "codex_exec_smoke": True,
            "disposable_workspace": True,
            "workspace": str(workspace),
            "command": command,
            "returncode": None,
            "tool_output_detected": False,
            "proves_model_or_tool_behavior": False,
            "interactive_prompt_control": False,
            "error": "timeout",
            "output_tail": output[-2000:],
        }

    events = parse_jsonl_events(result.stdout)
    command_events = [
        event.get("item", {})
        for event in events
        if event.get("type") == "item.completed"
        and event.get("item", {}).get("type") == "command_execution"
    ]
    completed_tool_event = next(
        (
            item
            for item in command_events
            if item.get("exit_code") == 0
            and item.get("status") == "completed"
            and CODEX_EXEC_MARKER in item.get("aggregated_output", "")
        ),
        None,
    )
    tool_output_detected = completed_tool_event is not None
    status = "ok" if result.returncode == 0 and tool_output_detected else "error"
    output = (result.stdout + result.stderr).strip()
    return {
        "status": status,
        "codex_exec_smoke": True,
        "disposable_workspace": True,
        "workspace": str(workspace),
        "command": command,
        "returncode": result.returncode,
        "tool_output_detected": tool_output_detected,
        "tool_exit_code": completed_tool_event.get("exit_code") if completed_tool_event else None,
        "proves_model_or_tool_behavior": tool_output_detected,
        "interactive_prompt_control": False,
        "event_count": len(events),
        "output_tail": output[-2000:],
    }


def run_codex_tui_smoke(workspace: Path, *, timeout_seconds: float) -> dict:
    git_result = subprocess.run(
        ["git", "init"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    command = (
        "codex --no-alt-screen "
        f"-C {shlex.quote(str(workspace))} "
        f"-s read-only -a untrusted {shlex.quote(CODEX_TUI_PROMPT)}"
    )
    if git_result.returncode != 0:
        return {
            "status": "error",
            "codex_tui_smoke": True,
            "disposable_workspace": True,
            "workspace": str(workspace),
            "command": command,
            "interactive_prompt_control": False,
            "proves_model_or_tool_behavior": False,
            "error": "git init failed",
            "output_tail": (git_result.stdout + git_result.stderr).strip()[-2000:],
        }

    report = run_agent_smoke(
        command=command,
        workspace=workspace,
        approval_input="n",
        prompt_pattern=DEFAULT_PROMPT_PATTERN,
        expect_output=CODEX_TUI_MARKER,
        timeout_seconds=timeout_seconds,
        interactions=CODEX_TUI_INTERACTIONS,
    )
    interaction_steps = report.get("interactions", [])
    interaction_control = len(interaction_steps) == len(CODEX_TUI_INTERACTIONS) and all(
        step.get("prompt_detected") and step.get("input_injected")
        for step in interaction_steps
    )
    marker_seen = CODEX_TUI_MARKER in report.get("response_text", "")
    report["codex_tui_smoke"] = True
    report["interactive_prompt_control"] = bool(interaction_control)
    report["proves_model_or_tool_behavior"] = bool(marker_seen)
    return report


def parse_jsonl_events(output: str) -> list[dict]:
    events: list[dict] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


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
    interactions: list[tuple[str, str]] | None = None,
) -> dict:
    scripted_interactions = interactions or []
    prompt_regex = re.compile(prompt_pattern, re.IGNORECASE)
    runner = PtyAgentRunner(command, cwd=str(workspace))
    prompt_text = ""
    response_text = ""
    interaction_results: list[dict] = []
    prompt_detected = False
    input_injected = False
    killed = False
    started = False
    expected_seen_before_response = False
    try:
        runner.start()
        started = True
        if scripted_interactions:
            for pattern, input_text in scripted_interactions:
                step_regex = re.compile(pattern, re.IGNORECASE)
                step_output = wait_for_output(
                    runner,
                    lambda seen, regex=step_regex: bool(regex.search(seen))
                    or bool(input_injected and expect_output and expect_output in seen),
                    timeout_seconds=timeout_seconds,
                )
                step_detected = bool(step_regex.search(step_output))
                expected_seen = bool(expect_output and expect_output in step_output)
                if expected_seen and not input_injected:
                    expected_seen_before_response = True
                if expected_seen and input_injected and not step_detected:
                    response_text += step_output
                    break
                prompt_text += step_output
                step_injected = False
                if step_detected:
                    runner.write_input(_with_newline(input_text))
                    step_injected = True
                    input_injected = True
                interaction_results.append(
                    {
                        "pattern": pattern,
                        "prompt_detected": step_detected,
                        "input_injected": step_injected,
                    }
                )
                if not step_detected:
                    break
            prompt_detected = all(step["prompt_detected"] for step in interaction_results)
            if expect_output:
                if expect_output not in response_text:
                    response_text = wait_for_output(
                        runner,
                        lambda seen: expect_output in seen,
                        timeout_seconds=timeout_seconds,
                    )
            else:
                response_text = wait_for_output(
                    runner,
                    lambda seen: len(seen) > 0,
                    timeout_seconds=min(timeout_seconds, 3.0),
                )
        else:
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
    if not scripted_interactions:
        expected_seen_before_response = bool(expect_output and expect_output in prompt_text)
    if expect_output and expect_output not in response_text:
        status = "error"
    if expected_seen_before_response:
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
        expected_output_seen_before_response=expected_seen_before_response,
        interactions=interaction_results,
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
    expected_output_seen_before_response: bool = False,
    interactions: list[dict] | None = None,
) -> dict:
    interaction_results = interactions or []
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
        "expected_output_seen_before_response": expected_output_seen_before_response,
        "interaction_count": len(interaction_results),
        "interactions": interaction_results,
    }


def _with_newline(value: str) -> str:
    return value if value.endswith("\n") else value + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
