import json
import subprocess
import sys


def test_agent_integration_smoke_dry_run_outputs_structured_report():
    result = subprocess.run(
        [sys.executable, "scripts/agent_integration_smoke.py", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "dry-run"
    assert report["prompt_detected"] is True
    assert report["input_injected"] is True
    assert report["disposable_workspace"] is True
