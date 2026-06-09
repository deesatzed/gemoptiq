import json

from sentinel.policy import FileEffect, PolicyAction, PolicyDecision
from sentinel.session_trace import SessionTraceStore
from sentinel.trace_replay import render_trace_text, summarize_trace


def test_summarize_trace_reports_session_decisions_actions_and_digests(tmp_path):
    store = SessionTraceStore(tmp_path, session_id="example")
    store.record_session_started(
        command="python fixture_agent.py",
        config_path="sentinel.yaml",
        cwd="/tmp/workspace",
    )
    store.record_process_event("process.started", {"pid": 123})
    store.record_decision(
        prompt_line="Update docs?",
        file_effects=[FileEffect("modified", "docs/readme.md")],
        policy_decision=PolicyDecision(
            PolicyAction.ALLOW,
            "All observed file effects are auto-approved by config.",
            matched_pattern="docs/**",
            risk="green",
            effect_ids=["write:workspace"],
            source="override",
            override_id="override-123",
        ),
        auditor_verdict=None,
        auditor_reason=None,
    )
    store.record_user_action("approve", {"source": "test"})
    store.record_enforcement_rollback(
        file_effects=[FileEffect("created", ".env")],
        rollback_results=[
            {
                "path": ".env",
                "operation": "created",
                "rollback": "deleted-created-file",
            }
        ],
    )
    store.record_process_event("process.stopped", {"returncode": 0})

    summary = summarize_trace(store.path)

    assert summary["status"] == "ok"
    assert summary["trace_path"] == str(store.path)
    assert summary["session"]["command"] == "python fixture_agent.py"
    assert summary["session"]["config_path"] == "sentinel.yaml"
    assert summary["event_count"] == 6
    assert summary["event_types"]["decision.recorded"] == 1
    assert summary["event_types"]["enforcement.rollback"] == 1
    assert summary["decisions"][0]["policy_action"] == "allow"
    assert summary["decisions"][0]["policy_risk"] == "green"
    assert summary["decisions"][0]["policy_effect_ids"] == ["write:workspace"]
    assert summary["decisions"][0]["policy_source"] == "override"
    assert summary["decisions"][0]["override_id"] == "override-123"
    assert summary["decisions"][0]["prompt_line"] == "Update docs?"
    assert summary["file_effects"] == [
        {"operation": "modified", "path": "docs/readme.md"},
        {"operation": "created", "path": ".env"},
    ]
    assert summary["rollback_results"] == [
        {"path": ".env", "operation": "created", "rollback": "deleted-created-file"}
    ]
    assert summary["user_actions"] == ["approve"]
    assert summary["process_lifecycle"] == ["process.started", "process.stopped"]
    assert summary["digests_valid"] is True


def test_render_trace_text_includes_human_readable_session_and_decision(tmp_path):
    store = SessionTraceStore(tmp_path, session_id="text")
    store.record_session_started(
        command="python fixture_agent.py",
        config_path="sentinel.yaml",
        cwd="/tmp/workspace",
    )
    store.record_decision(
        prompt_line="Delete src/app.py?",
        file_effects=[FileEffect("deleted", "src/app.py")],
        policy_decision=PolicyDecision(
            PolicyAction.CONFIRM,
            "Delete effect requires explicit confirmation: src/app.py",
            risk="orange",
            effect_ids=["delete:workspace"],
        ),
        auditor_verdict=None,
        auditor_reason=None,
    )
    store.record_enforcement_rollback(
        file_effects=[FileEffect("created", ".env")],
        rollback_results=[
            {
                "path": ".env",
                "operation": "created",
                "rollback": "deleted-created-file",
            }
        ],
    )

    text = render_trace_text(summarize_trace(store.path))

    assert "Cortex Sentinel Trace" in text
    assert "python fixture_agent.py" in text
    assert "Delete src/app.py?" in text
    assert "confirm" in text
    assert "orange" in text
    assert "delete:workspace" in text
    assert "Rollback Results: 1" in text


def test_summarize_trace_flags_bad_digest(tmp_path):
    path = tmp_path / "bad.jsonl"
    event = {
        "session_id": "bad",
        "sequence": 1,
        "timestamp": "2026-01-01T00:00:00Z",
        "event_type": "session.started",
        "payload": {"command": "x"},
        "digest": "sha256:bad",
    }
    path.write_text(json.dumps(event) + "\n")

    summary = summarize_trace(path)

    assert summary["status"] == "error"
    assert summary["digests_valid"] is False
