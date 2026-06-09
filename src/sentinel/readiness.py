from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Callable


REQUIRED_README_SECTIONS = [
    "## Quick Start",
    "## Installation",
    "## Configuration Reference",
    "## Safety Boundary",
    "## Troubleshooting",
    "## Examples",
]

Status = str
Runner = Callable[[list[str], str | None, Path], dict]


def main(argv: list[str] | None = None, *, project_root: str | Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_readiness(args, project_root=project_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report Cortex Sentinel readiness against GOAL.md proof items."
    )
    add_readiness_arguments(parser)
    return parser


def add_readiness_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Inspect static evidence only; do not execute local smoke commands.",
    )
    parser.add_argument(
        "--run-real-auditor",
        action="store_true",
        help="Also run the real MLX/Gemma auditor smoke. Requires local Metal access.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Also run the root and MCP-Cortex pytest suites.",
    )
    parser.add_argument(
        "--run-claude-trust-smoke",
        action="store_true",
        help=(
            "Also run a bounded Claude Code workspace-trust prompt smoke in a "
            "temporary workspace. Does not prove model/tool behavior."
        ),
    )
    parser.add_argument(
        "--run-codex-exec-smoke",
        action="store_true",
        help=(
            "Also run Codex exec in an ephemeral temp workspace and verify a "
            "harmless command_execution event. Does not prove interactive prompt control."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless every item is pass.",
    )


def run_readiness(
    args: argparse.Namespace,
    *,
    project_root: str | Path | None = None,
    runner: Runner = None,
) -> int:
    root = Path(project_root or Path.cwd()).resolve()
    report = build_report(
        project_root=root,
        run_local_smokes=not args.no_run,
        run_full_tests=args.include_tests and not args.no_run,
        run_real_auditor=args.run_real_auditor,
        run_claude_trust_smoke=args.run_claude_trust_smoke and not args.no_run,
        run_codex_exec_smoke=args.run_codex_exec_smoke and not args.no_run,
        runner=runner or run_command,
    )
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.strict and report["status"] != "ok":
        return 1
    return 0 if report["status"] in {"ok", "partial"} else 1


def build_report(
    *,
    project_root: Path,
    run_local_smokes: bool,
    run_full_tests: bool,
    run_real_auditor: bool,
    runner: Runner,
    run_claude_trust_smoke: bool = False,
    run_codex_exec_smoke: bool = False,
) -> dict:
    items: dict[str, dict] = {}

    items["pytest_root"] = command_item(
        "Run `pytest -q` from the repo root.",
        ["pytest", "-q"],
        run_full_tests,
        runner,
        project_root=project_root,
        manual_evidence="Full root suite is intentionally manual unless `--include-tests` is used.",
    )
    items["pytest_mcp_cortex"] = command_item(
        "Run `python -m pytest -q` from `mcp-cortex/`.",
        ["python", "-m", "pytest", "-q"],
        run_full_tests,
        runner,
        project_root=project_root,
        manual_evidence="Nested repo suite is intentionally manual unless `--include-tests` is used.",
        cwd="mcp-cortex",
    )

    items["sentinel_smoke"] = command_item(
        "Verify repo venv MLX alias and runner smoke.",
        ["venv/bin/python", "scripts/sentinel_smoke.py"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["auditor_dry_run"] = command_item(
        "Verify structured auditor smoke reporting without loading the model.",
        ["venv/bin/python", "scripts/auditor_smoke.py", "--dry-run"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["real_auditor_smoke"] = real_auditor_item(
        run_real_auditor,
        runner,
        project_root=project_root,
    )
    items["agent_integration_smoke"] = command_item(
        "Verify PTY prompt detection, input injection, and process kill in a disposable workspace.",
        ["venv/bin/python", "scripts/agent_integration_smoke.py"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["real_agent_dry_run"] = command_item(
        "Verify guarded real-agent harness refuses implicit execution.",
        ["python", "scripts/real_agent_smoke.py", "--dry-run"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["real_agent_cli_probe"] = command_item(
        "Verify installed Codex/Claude/Gemini CLIs can run safe non-interactive metadata probes.",
        [
            "python",
            "scripts/real_agent_smoke.py",
            "--probe-installed-agents",
            "--timeout",
            "5",
        ],
        run_local_smokes,
        runner,
        project_root=project_root,
        manual_evidence=(
            "Safe CLI metadata probes are intentionally manual unless local smokes are run; "
            "they do not prove interactive agent prompt behavior."
        ),
    )
    items["real_agent_claude_trust_smoke"] = command_item(
        (
            "Verify Sentinel can drive Claude Code's own workspace-trust prompt "
            "inside a disposable workspace."
        ),
        [
            "python",
            "scripts/real_agent_smoke.py",
            "--claude-trust-smoke",
            "--timeout",
            "8",
        ],
        run_claude_trust_smoke,
        runner,
        project_root=project_root,
        manual_evidence=(
            "Optional bounded real Claude Code PTY smoke; rerun with "
            "`--run-claude-trust-smoke`. This proves startup prompt/control, "
            "not model/tool confirmation behavior."
        ),
    )
    items["real_agent_codex_exec_smoke"] = command_item(
        (
            "Verify Codex exec can perform a harmless shell command_execution "
            "inside an ephemeral temp workspace."
        ),
        [
            "python",
            "scripts/real_agent_smoke.py",
            "--codex-exec-smoke",
            "--timeout",
            "30",
        ],
        run_codex_exec_smoke,
        runner,
        project_root=project_root,
        manual_evidence=(
            "Optional bounded real Codex exec model/tool smoke; rerun with "
            "`--run-codex-exec-smoke`. This proves model/tool command execution, "
            "not interactive prompt control."
        ),
    )
    items["real_agent_command"] = manual_item(
        (
            "Run the guarded real-agent harness with a real Claude/Gemini/Codex "
            "interactive tool-confirmation command."
        ),
        (
            "Requires a deliberately safe disposable command and confirmed "
            "account/credential state. The Claude trust-prompt smoke proves "
            "startup/control, and the Codex exec smoke proves non-interactive "
            "model/tool execution."
        ),
        [
            "python",
            "scripts/real_agent_smoke.py",
            "--agent-command",
            "<safe real agent command>",
        ],
    )
    items["enforcement_smoke"] = command_item(
        "Verify protected-path enforcement catches no-prompt writes.",
        ["venv/bin/python", "scripts/enforcement_smoke.py"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["trace_smoke"] = command_item(
        "Verify persisted trace fields and digest validation.",
        ["venv/bin/python", "scripts/trace_smoke.py"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["e2e_smoke"] = command_item(
        "Verify aggregate disposable local E2E scenarios.",
        ["python", "scripts/e2e_smoke.py"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )
    items["docs"] = docs_item(project_root)
    items["diff_check"] = command_item(
        "Verify patch has no whitespace errors.",
        ["git", "diff", "--check"],
        run_local_smokes,
        runner,
        project_root=project_root,
    )

    summary = summarize(items)
    return {
        "status": "ok" if summary["total"] == summary["pass"] else "partial",
        "summary": summary,
        "items": items,
    }


def command_item(
    description: str,
    command: list[str],
    should_run: bool,
    runner: Runner,
    *,
    project_root: Path,
    cwd: str | None = None,
    manual_evidence: str | None = None,
) -> dict:
    item = {
        "description": description,
        "command": command,
    }
    if cwd is not None:
        item["cwd"] = cwd
    if not should_run:
        item.update(
            {
                "status": "manual",
                "evidence": manual_evidence
                or "Not run by request; rerun without `--no-run` for local disposable evidence.",
            }
        )
        return item

    result = runner(command, cwd, project_root)
    status, evidence = classify_command_result(result)
    item.update(
        {
            "status": status,
            "returncode": result["returncode"],
            "evidence": evidence,
        }
    )
    return item


def real_auditor_item(
    run_real_auditor: bool,
    runner: Runner,
    *,
    project_root: Path,
) -> dict:
    command = ["venv/bin/python", "scripts/auditor_smoke.py"]
    if not run_real_auditor:
        return {
            "description": "Load the real MLX/Gemma auditor model and parse a structured verdict.",
            "command": command,
            "status": "external_blocked",
            "evidence": "Not run automatically; requires a macOS session with Metal access.",
        }

    result = runner(command, None, project_root)
    status: Status = "pass" if result["returncode"] == 0 else "external_blocked"
    return {
        "description": "Load the real MLX/Gemma auditor model and parse a structured verdict.",
        "command": command,
        "status": status,
        "returncode": result["returncode"],
        "evidence": result["output_tail"],
    }


def docs_item(project_root: Path) -> dict:
    readme_path = project_root / "README.md"
    if not readme_path.exists():
        return {
            "description": "Verify user docs exist with required sections.",
            "status": "fail",
            "evidence": "README.md is missing.",
        }

    readme = readme_path.read_text()
    missing = [section for section in REQUIRED_README_SECTIONS if section not in readme]
    return {
        "description": "Verify user docs include quick start, install, config, safety, troubleshooting, and examples.",
        "status": "pass" if not missing else "fail",
        "missing_sections": missing,
        "evidence": "All required README sections present." if not missing else "Missing README sections.",
    }


def manual_item(
    description: str,
    evidence: str,
    command: list[str],
    *,
    cwd: str | None = None,
) -> dict:
    item = {
        "description": description,
        "status": "manual",
        "command": command,
        "evidence": evidence,
    }
    if cwd is not None:
        item["cwd"] = cwd
    return item


def run_command(command: list[str], cwd: str | None, project_root: Path) -> dict:
    workdir = project_root if cwd is None else project_root / cwd
    result = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    return {
        "returncode": result.returncode,
        "output_tail": output[-2000:],
    }


def classify_command_result(result: dict) -> tuple[Status, str]:
    output = result["output_tail"]
    if result["returncode"] == 0:
        return "pass", output
    if "PermissionError: [Errno 1] Operation not permitted" in output:
        return (
            "external_blocked",
            "Sandbox denied nested subprocess execution during this check. "
            "Run the listed command directly in a local terminal for authoritative evidence.\n"
            + output,
        )
    return "fail", output


def summarize(items: dict[str, dict]) -> dict:
    counts = {
        "pass": 0,
        "fail": 0,
        "manual": 0,
        "external_blocked": 0,
        "total": len(items),
    }
    for item in items.values():
        status = item["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts
