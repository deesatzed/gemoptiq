from pathlib import Path

from sentinel.cortex_bridge import CortexBridge
from sentinel.policy import FileEffect, PolicyAction, PolicyDecision


def test_bridge_disabled_when_package_root_missing(tmp_path):
    bridge = CortexBridge(project_root=tmp_path)

    result = bridge.record_decision(
        prompt_line="Update docs?",
        file_effects=[FileEffect("modified", "docs/readme.md")],
        policy_decision=PolicyDecision(PolicyAction.ALLOW, "auto-approved"),
        auditor_verdict=None,
        auditor_reason=None,
    )

    assert result["enabled"] is False
    assert result["status"] == "disabled"


def test_bridge_records_policy_and_result_trace_when_available():
    bridge = CortexBridge(project_root=Path.cwd())

    result = bridge.record_decision(
        prompt_line="Update docs?",
        file_effects=[FileEffect("modified", "docs/readme.md")],
        policy_decision=PolicyDecision(PolicyAction.ALLOW, "auto-approved"),
        auditor_verdict=None,
        auditor_reason=None,
    )

    assert result["enabled"] is True
    assert result["status"] == "recorded"
    assert result["decision"]["allowed"] is True
    assert result["trace_event_count"] == 3
    assert result["result_digest"].startswith("sha256:")


def test_bridge_maps_protected_path_to_secret_read_effect():
    bridge = CortexBridge(project_root=Path.cwd())

    result = bridge.record_decision(
        prompt_line="Read .env?",
        file_effects=[FileEffect("modified", ".env")],
        policy_decision=PolicyDecision(PolicyAction.BLOCK, "protected path"),
        auditor_verdict=None,
        auditor_reason=None,
    )

    assert result["enabled"] is True
    assert result["decision"]["allowed"] is False
    assert "read:secrets" in result["requested_effects"]
