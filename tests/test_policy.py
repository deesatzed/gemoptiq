from sentinel.config import SentinelConfig
from sentinel.policy import (
    CommandEffect,
    FileEffect,
    PolicyAction,
    SentinelPolicy,
    SessionOverrideStore,
)


def test_protected_path_blocks_before_audit():
    policy = SentinelPolicy(
        SentinelConfig(
            protected_paths=["**/.env", "~/.ssh/**"],
            auto_approve_paths=["docs/**"],
        )
    )

    decision = policy.evaluate([FileEffect("modified", ".env")])

    assert decision.action is PolicyAction.BLOCK
    assert "protected path" in decision.reason
    assert decision.matched_pattern == "**/.env"


def test_auto_approve_path_allows_without_audit():
    policy = SentinelPolicy(
        SentinelConfig(
            protected_paths=["**/.env"],
            auto_approve_paths=["docs/**"],
        )
    )

    decision = policy.evaluate([FileEffect("created", "docs/notes.md")])

    assert decision.action is PolicyAction.ALLOW
    assert "auto-approved" in decision.reason
    assert decision.matched_pattern == "docs/**"


def test_mixed_auto_approve_and_workspace_path_requires_review():
    policy = SentinelPolicy(
        SentinelConfig(
            protected_paths=["**/.env"],
            auto_approve_paths=["docs/**"],
        )
    )

    decision = policy.evaluate(
        [
            FileEffect("modified", "docs/notes.md"),
            FileEffect("modified", "src/sentinel/tui.py"),
        ]
    )

    assert decision.action is PolicyAction.REVIEW
    assert "requires audit" in decision.reason


def test_no_file_effects_requires_review():
    policy = SentinelPolicy(SentinelConfig(auto_approve_paths=["docs/**"]))

    decision = policy.evaluate([])

    assert decision.action is PolicyAction.REVIEW
    assert "No file effects" in decision.reason


def test_safe_docs_edit_records_low_risk_effect_id():
    policy = SentinelPolicy(
        SentinelConfig(
            protected_paths=["**/.env"],
            auto_approve_paths=["docs/**"],
        )
    )

    decision = policy.evaluate([FileEffect("modified", "docs/notes.md")])

    assert decision.action is PolicyAction.ALLOW
    assert decision.risk == "green"
    assert decision.effect_ids == ["write:workspace"]


def test_source_delete_requires_explicit_confirmation():
    policy = SentinelPolicy(SentinelConfig(auto_approve_paths=["docs/**"]))

    decision = policy.evaluate([FileEffect("deleted", "src/sentinel/tui.py")])

    assert decision.action is PolicyAction.CONFIRM
    assert decision.risk == "orange"
    assert "Delete" in decision.reason
    assert decision.effect_ids == ["delete:workspace"]


def test_shell_command_requires_review_with_command_effect_id():
    policy = SentinelPolicy(SentinelConfig())

    decision = policy.evaluate(
        [],
        command_effects=[CommandEffect("execute:shell", "pytest -q")],
    )

    assert decision.action is PolicyAction.REVIEW
    assert decision.risk == "yellow"
    assert "Shell command" in decision.reason
    assert decision.effect_ids == ["execute:shell"]


def test_external_network_command_blocks():
    policy = SentinelPolicy(SentinelConfig())

    decision = policy.evaluate(
        [],
        command_effects=[CommandEffect("network:external", "curl https://example.com")],
    )

    assert decision.action is PolicyAction.BLOCK
    assert decision.risk == "red"
    assert "Network" in decision.reason
    assert decision.effect_ids == ["network:external"]


def test_production_deploy_command_blocks():
    policy = SentinelPolicy(SentinelConfig())

    decision = policy.evaluate(
        [],
        command_effects=[CommandEffect("deploy:production", "flyctl deploy")],
    )

    assert decision.action is PolicyAction.BLOCK
    assert decision.risk == "red"
    assert "production deploy" in decision.reason.lower()
    assert decision.effect_ids == ["deploy:production"]


def test_secret_read_blocks_even_without_configured_protected_paths():
    policy = SentinelPolicy(SentinelConfig())

    decision = policy.evaluate([FileEffect("read", ".env")])

    assert decision.action is PolicyAction.BLOCK
    assert decision.risk == "red"
    assert "secret" in decision.reason.lower()
    assert decision.effect_ids == ["read:secret"]


def test_risk_threshold_can_require_confirmation_for_workspace_write():
    policy = SentinelPolicy(
        SentinelConfig(risk_thresholds={"write:workspace": "confirm"})
    )

    decision = policy.evaluate([FileEffect("modified", "src/app.py")])

    assert decision.action is PolicyAction.CONFIRM
    assert decision.risk == "yellow"
    assert decision.effect_ids == ["write:workspace"]
    assert "threshold" in decision.reason.lower()


def test_session_override_allows_scoped_workspace_path():
    overrides = SessionOverrideStore()
    override = overrides.add_path_override(
        "src/ui/**",
        PolicyAction.ALLOW,
        ttl_seconds=60,
        reason="Current UI refactor",
        now_seconds=100,
    )
    policy = SentinelPolicy(SentinelConfig(), override_store=overrides)

    decision = policy.evaluate(
        [FileEffect("modified", "src/ui/button.py")],
        now_seconds=120,
    )

    assert decision.action is PolicyAction.ALLOW
    assert decision.source == "override"
    assert decision.override_id == override.override_id
    assert decision.matched_pattern == "src/ui/**"
    assert "Current UI refactor" in decision.reason


def test_expired_session_override_is_ignored():
    overrides = SessionOverrideStore()
    overrides.add_path_override(
        "src/ui/**",
        PolicyAction.ALLOW,
        ttl_seconds=10,
        reason="Expired refactor",
        now_seconds=100,
    )
    policy = SentinelPolicy(SentinelConfig(), override_store=overrides)

    decision = policy.evaluate(
        [FileEffect("modified", "src/ui/button.py")],
        now_seconds=111,
    )

    assert decision.action is PolicyAction.REVIEW
    assert decision.source == "policy"
    assert decision.override_id is None


def test_session_override_cannot_bypass_protected_path_block():
    overrides = SessionOverrideStore()
    overrides.add_path_override(
        "**/.env",
        PolicyAction.ALLOW,
        ttl_seconds=60,
        reason="Unsafe request",
        now_seconds=100,
    )
    policy = SentinelPolicy(
        SentinelConfig(protected_paths=["**/.env"]),
        override_store=overrides,
    )

    decision = policy.evaluate([FileEffect("modified", ".env")], now_seconds=120)

    assert decision.action is PolicyAction.BLOCK
    assert decision.source == "policy"
    assert decision.override_id is None
