import json
import subprocess
import sys


def test_trace_smoke_outputs_trace_artifact_with_required_events():
    result = subprocess.run(
        [sys.executable, "scripts/trace_smoke.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["trace_path"]
    assert report["has_command_metadata"] is True
    assert report["has_prompt_text"] is True
    assert report["has_file_effects"] is True
    assert report["has_policy_decision"] is True
    assert report["has_auditor_verdict"] is True
    assert report["has_user_action"] is True
    assert report["has_rollback_event"] is True
    assert report["has_process_lifecycle"] is True
    assert report["has_stable_digests"] is True
