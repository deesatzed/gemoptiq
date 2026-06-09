import json
import importlib.util
import subprocess
import sys
from pathlib import Path


def load_real_agent_smoke_module():
    spec = importlib.util.spec_from_file_location(
        "real_agent_smoke",
        Path("scripts/real_agent_smoke.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_real_agent_smoke_dry_run_outputs_guarded_report():
    result = subprocess.run(
        [sys.executable, "scripts/real_agent_smoke.py", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "dry-run"
    assert report["requires_explicit_command"] is True
    assert report["disposable_workspace"] is True
    assert report["executed"] is False


def test_real_agent_smoke_requires_explicit_agent_command():
    result = subprocess.run(
        [sys.executable, "scripts/real_agent_smoke.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--agent-command is required" in result.stderr


def test_real_agent_smoke_runs_supplied_command_in_disposable_workspace():
    fixture_command = (
        f"{sys.executable} -c \""
        "import pathlib, sys; "
        "sys.stdout.write('Fixture real-agent prompt [y/n]? '); sys.stdout.flush(); "
        "answer=sys.stdin.readline().strip(); "
        "pathlib.Path('answer.txt').write_text(answer); "
        "print('answer:' + answer, flush=True)"
        "\""
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/real_agent_smoke.py",
            "--agent-command",
            fixture_command,
            "--approval-input",
            "n",
            "--expect-output",
            "answer:n",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["executed"] is True
    assert report["disposable_workspace"] is True
    assert report["prompt_detected"] is True
    assert report["input_injected"] is True
    assert report["process_killed"] is True
    assert "Fixture real-agent prompt" in report["prompt_text"]
    assert "answer:n" in report["response_text"]


def test_real_agent_smoke_runs_scripted_multi_prompt_interactions_in_order():
    fixture_command = (
        f"{sys.executable} -c \""
        "import sys; "
        "sys.stdout.write('Trust workspace [y/n]? '); sys.stdout.flush(); "
        "trust=sys.stdin.readline().strip(); "
        "sys.stdout.write('Run safe tool [y/n]? '); sys.stdout.flush(); "
        "tool=sys.stdin.readline().strip(); "
        "print('answers:' + trust + ',' + tool, flush=True)"
        "\""
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/real_agent_smoke.py",
            "--agent-command",
            fixture_command,
            "--interaction",
            r"Trust workspace.*\?=>y",
            "--interaction",
            r"Run safe tool.*\?=>n",
            "--expect-output",
            "answers:y,n",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["interaction_count"] == 2
    assert report["interactions"][0]["input_injected"] is True
    assert report["interactions"][1]["input_injected"] is True
    assert "answers:y,n" in report["response_text"]


def test_real_agent_smoke_probe_command_reports_noninteractive_agent_metadata():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/real_agent_smoke.py",
            "--probe-agent-command",
            f"fixture={sys.executable} -c \"print('fixture-agent 1.0')\"",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    probe = report["agent_probes"]["fixture"]

    assert report["status"] == "ok"
    assert report["safe_noninteractive_probe"] is True
    assert report["proves_interactive_behavior"] is False
    assert report["pass_count"] == 1
    assert probe["status"] == "pass"
    assert probe["returncode"] == 0
    assert "fixture-agent 1.0" in probe["evidence"]


def test_real_agent_smoke_named_claude_trust_mode_uses_disposable_safe_command(
    monkeypatch,
    capsys,
):
    module = load_real_agent_smoke_module()
    captured = {}

    def fake_run_agent_smoke(**kwargs):
        captured.update(kwargs)
        return {
            "status": "ok",
            "executed": True,
            "disposable_workspace": True,
            "prompt_detected": True,
            "input_injected": True,
            "process_killed": True,
            "claude_trust_smoke": True,
        }

    monkeypatch.setattr(module, "run_agent_smoke", fake_run_agent_smoke)

    exit_code = module.main(["--claude-trust-smoke", "--timeout", "3"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["claude_trust_smoke"] is True
    assert captured["command"] == module.CLAUDE_TRUST_COMMAND
    assert captured["approval_input"] == "2"
    assert "Quick.*safety.*check" in captured["prompt_pattern"]
    assert captured["timeout_seconds"] == 3
