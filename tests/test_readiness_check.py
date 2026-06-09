import json
import subprocess
import sys

from sentinel.readiness import classify_command_result


def test_readiness_check_no_run_reports_goal_status_without_external_actions():
    result = subprocess.run(
        [sys.executable, "scripts/readiness_check.py", "--no-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "partial"
    assert report["summary"]["pass"] >= 1
    assert report["summary"]["external_blocked"] >= 1
    assert report["summary"]["manual"] >= 1
    assert report["items"]["real_auditor_smoke"]["status"] == "external_blocked"
    assert report["items"]["real_agent_cli_probe"]["status"] == "manual"
    assert report["items"]["real_agent_command"]["status"] == "manual"
    assert report["items"]["docs"]["status"] == "pass"


def test_readiness_check_strict_fails_when_goal_is_not_fully_proven():
    result = subprocess.run(
        [sys.executable, "scripts/readiness_check.py", "--no-run", "--strict"],
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert result.returncode == 1
    assert report["status"] == "partial"
    assert report["items"]["real_auditor_smoke"]["status"] == "external_blocked"


def test_readiness_check_include_tests_keeps_no_run_static():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/readiness_check.py",
            "--no-run",
            "--include-tests",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["items"]["pytest_root"]["status"] == "manual"
    assert "--include-tests" in report["items"]["pytest_root"]["evidence"]


def test_readiness_check_classifies_sandbox_denial_as_external_blocked():
    status, evidence = classify_command_result(
        {
            "returncode": 1,
            "output_tail": "PermissionError: [Errno 1] Operation not permitted: 'ps'",
        }
    )

    assert status == "external_blocked"
    assert "Run the listed command directly" in evidence
