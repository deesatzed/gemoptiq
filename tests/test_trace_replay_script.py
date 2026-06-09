import json
import subprocess
import sys

from sentinel.policy import FileEffect, PolicyAction, PolicyDecision
from sentinel.session_trace import SessionTraceStore


def test_trace_replay_script_outputs_summary_json(tmp_path):
    store = SessionTraceStore(tmp_path, session_id="script")
    store.record_session_started(command="python agent.py", config_path="sentinel.yaml", cwd="/tmp")
    store.record_process_event("process.started", {"pid": 1})
    store.record_decision(
        prompt_line="Proceed?",
        file_effects=[FileEffect("created", "docs/a.md")],
        policy_decision=PolicyDecision(PolicyAction.ALLOW, "allowed"),
        auditor_verdict=None,
        auditor_reason=None,
    )
    store.record_process_event("process.stopped", {"returncode": 0})

    result = subprocess.run(
        [sys.executable, "scripts/trace_replay.py", str(store.path)],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)

    assert summary["status"] == "ok"
    assert summary["trace_path"] == str(store.path)
    assert summary["event_count"] == 4
    assert summary["decisions"][0]["prompt_line"] == "Proceed?"
    assert summary["file_effects"] == [{"operation": "created", "path": "docs/a.md"}]
