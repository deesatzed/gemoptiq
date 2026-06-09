import json
import subprocess
import sys


def test_e2e_smoke_outputs_core_scenario_report():
    result = subprocess.run(
        [sys.executable, "scripts/e2e_smoke.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["disposable_workspace"] is True
    assert report["safe_auto_approval"] is True
    assert report["protected_path_block"] is True
    assert report["ambiguous_auditor_review"] is True
    assert report["no_prompt_protected_write"] is True
    assert report["pty_prompt_handling"] is True
    assert report["trace_export"] is True
    assert report["config_profile"] is True
