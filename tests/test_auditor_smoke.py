import json
import subprocess
import sys


def test_auditor_smoke_dry_run_outputs_structured_report():
    result = subprocess.run(
        [sys.executable, "scripts/auditor_smoke.py", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "dry-run"
    assert report["model_id"] == "mlx-community/gemma-4-12B-it-OptiQ-4bit"
    assert report["verdict"]["verdict"] == "allow"
    assert report["verdict"]["risk"] == "green"
    assert "load_seconds" in report["timing"]
    assert "audit_seconds" in report["timing"]
