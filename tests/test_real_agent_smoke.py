import json
import subprocess
import sys


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
