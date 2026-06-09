import json

from sentinel.policy import FileEffect, PolicyAction, PolicyDecision
from sentinel.session_trace import SessionTraceStore


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_trace_store_writes_session_started_event(tmp_path):
    store = SessionTraceStore(tmp_path)

    event = store.record_session_started(
        command="python agent.py",
        config_path="sentinel.yaml",
        cwd="/tmp/workspace",
    )

    rows = read_jsonl(store.path)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "session.started"
    assert rows[0]["sequence"] == 1
    assert rows[0]["payload"]["command"] == "python agent.py"
    assert rows[0]["payload"]["config_path"] == "sentinel.yaml"
    assert rows[0]["payload"]["cwd"] == "/tmp/workspace"
    assert rows[0]["digest"].startswith("sha256:")
    assert rows[0]["digest"] == event["digest"]


def test_trace_store_records_decision_with_policy_auditor_and_file_effects(tmp_path):
    store = SessionTraceStore(tmp_path)

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

    row = read_jsonl(store.path)[0]
    assert row["event_type"] == "decision.recorded"
    assert row["payload"]["prompt_line"] == "Update docs?"
    assert row["payload"]["file_effects"] == [
        {"operation": "modified", "path": "docs/readme.md"}
    ]
    assert row["payload"]["policy"]["action"] == "allow"
    assert row["payload"]["policy"]["matched_pattern"] == "docs/**"
    assert row["payload"]["policy"]["risk"] == "green"
    assert row["payload"]["policy"]["effect_ids"] == ["write:workspace"]
    assert row["payload"]["policy"]["source"] == "override"
    assert row["payload"]["policy"]["override_id"] == "override-123"
    assert row["payload"]["auditor"]["verdict"] is None
    assert row["payload"]["auditor"]["reason"] is None


def test_trace_store_records_process_lifecycle_and_user_action(tmp_path):
    store = SessionTraceStore(tmp_path)

    store.record_process_event("process.started", {"pid": 123})
    store.record_user_action("kill", {"source": "keyboard"})

    rows = read_jsonl(store.path)
    assert [row["event_type"] for row in rows] == ["process.started", "user.action"]
    assert rows[0]["payload"]["pid"] == 123
    assert rows[1]["payload"]["action"] == "kill"
    assert rows[1]["payload"]["details"] == {"source": "keyboard"}


def test_trace_store_records_enforcement_rollback_without_file_contents(tmp_path):
    store = SessionTraceStore(tmp_path)

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

    row = read_jsonl(store.path)[0]

    assert row["event_type"] == "enforcement.rollback"
    assert row["payload"]["file_effects"] == [
        {"operation": "created", "path": ".env"}
    ]
    assert row["payload"]["rollback_results"] == [
        {"path": ".env", "operation": "created", "rollback": "deleted-created-file"}
    ]
    assert "SECRET" not in json.dumps(row)
