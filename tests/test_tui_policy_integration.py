import asyncio
from unittest.mock import MagicMock, patch

from sentinel.config import SentinelConfig
from sentinel.policy import CommandEffect, FileEffect
from sentinel.policy import PolicyAction, PolicyDecision, SentinelPolicy, SessionOverrideStore
from sentinel.tui import SentinelTUI
from textual.widgets import Input, Static


class FakeLog:
    def __init__(self):
        self.lines = []

    def write_line(self, line):
        self.lines.append(line)


class FakeProgress:
    def __init__(self):
        self.progress = None

    def update(self, *, progress):
        self.progress = progress


class FakeApprovalPanel:
    def __init__(self):
        self.content = ""
        self.display = False

    def update(self, content):
        self.content = content


def make_app():
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner"):
        app = SentinelTUI("echo test")
    app.reasoning_log = FakeLog()
    app.progress = FakeProgress()
    app.approval_panel = FakeApprovalPanel()

    def query_one(selector, widget_type):
        if selector == "#reasoning_log":
            return app.reasoning_log
        if selector == "#drift_meter":
            return app.progress
        if selector == "#approval_panel":
            return app.approval_panel
        return FakeLog()

    app.query_one = MagicMock(side_effect=query_one)
    app.runner = MagicMock()
    app.auditor = MagicMock()
    app.policy = MagicMock()
    app.effect_observer = MagicMock()
    app.effect_observer.diff.return_value = []
    app.cortex_bridge = MagicMock()
    app.trace_store = MagicMock()
    return app


def test_tui_uses_workspace_trace_prompt_and_ignore_config(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config_path = tmp_path / "sentinel.yaml"
    config_path.write_text(
        "\n".join(
            [
                f"workspace_root: {workspace}",
                "trace_dir: traces",
                "ignore_dirs:",
                "  - custom-ignore",
                "prompt_patterns:",
                "  - 'APPROVE:$'",
            ]
        )
    )

    with patch("sentinel.tui.Auditor") as auditor_cls, \
         patch("sentinel.tui.AgentRunner"):
        app = SentinelTUI("echo test", config_path=str(config_path))

    auditor_cls.assert_called_once_with("mlx-community/gemma-4-12B-it-OptiQ-4bit")
    assert app.effect_observer.root == workspace.resolve()
    assert app.effect_observer.ignore_dirs == {"custom-ignore"}
    assert app.trace_store.trace_dir == workspace / "traces"
    assert app.prompt_regex.search("APPROVE:")
    assert not app.prompt_regex.search("Continue?")


def test_tui_seeds_cli_allow_path_override_into_policy():
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner"):
        app = SentinelTUI(
            "echo test",
            initial_allow_overrides=["src/ui/**"],
        )

    effect = FileEffect("modified", "src/ui/button.py")
    override = app.override_store.active_for_effect(effect)
    decision = app.policy.evaluate([effect])

    assert override is not None
    assert override.path_pattern == "src/ui/**"
    assert override.action is PolicyAction.ALLOW
    assert "CLI allow override" in override.reason
    assert decision.action is PolicyAction.ALLOW
    assert decision.source == "override"
    assert decision.override_id == override.override_id


def test_tui_mount_logs_and_traces_cli_allow_path_override():
    runner = MagicMock()
    runner.process = MagicMock(pid=123)
    runner.get_output.return_value = None
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner", return_value=runner):
        app = SentinelTUI(
            "echo test",
            initial_allow_overrides=["src/ui/**"],
        )
    app.reasoning_log = FakeLog()
    app.agent_log = FakeLog()
    app.enforcer = MagicMock()
    app.trace_store = MagicMock()
    app.set_interval = MagicMock()

    def query_one(selector, widget_type):
        if selector == "#reasoning_log":
            return app.reasoning_log
        if selector == "#agent_log":
            return app.agent_log
        return FakeLog()

    app.query_one = MagicMock(side_effect=query_one)

    run(app.on_mount())

    assert any("Startup override active: src/ui/**" in line for line in app.reasoning_log.lines)
    app.trace_store.record_user_action.assert_any_call(
        "override.create",
        {
            "override_id": app.initial_override_records[0]["override_id"],
            "path_pattern": "src/ui/**",
            "action": "allow",
            "ttl_seconds": 900,
            "reason": "CLI allow override",
            "source": "cli",
        },
    )


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_block_policy_suspends_without_auditor():
    app = make_app()
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.BLOCK,
        "Effect touches protected path: .env",
    )

    run(app.perform_audit("Overwrite .env?"))

    app.auditor.audit_intent.assert_not_called()
    app.runner.suspend.assert_called_once()
    app.runner.write_input.assert_not_called()
    assert app.is_paused is True
    assert app.progress.progress == 100
    app.cortex_bridge.record_decision.assert_called_once()
    assert app.cortex_bridge.record_decision.call_args.kwargs["auditor_verdict"] is None
    app.trace_store.record_decision.assert_called_once()


def test_prompt_command_effects_are_passed_to_policy():
    app = make_app()
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.BLOCK,
        "Network access requires explicit policy approval: curl https://example.com",
        risk="red",
        effect_ids=["network:external"],
    )

    run(app.perform_audit("Run command: curl https://example.com?"))

    _, kwargs = app.policy.evaluate.call_args
    assert kwargs["command_effects"] == [
        CommandEffect("network:external", "Run command: curl https://example.com?")
    ]
    app.auditor.audit_intent.assert_not_called()


def test_allow_policy_auto_approves_without_auditor():
    app = make_app()
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.ALLOW,
        "All observed file effects are auto-approved by config.",
    )

    run(app.perform_audit("Update docs?"))

    app.auditor.audit_intent.assert_not_called()
    app.runner.write_input.assert_called_once_with("y\n")
    app.runner.suspend.assert_not_called()
    assert app.progress.progress == 0
    app.cortex_bridge.record_decision.assert_called_once()
    assert app.cortex_bridge.record_decision.call_args.kwargs["auditor_verdict"] is None
    app.trace_store.record_decision.assert_called_once()


def test_review_policy_uses_auditor():
    app = make_app()
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.REVIEW,
        "Observed file effects are outside auto-approve paths; requires audit.",
    )
    app.auditor.audit_intent.return_value = (True, "YES. Safe.")

    run(app.perform_audit("Update src?"))

    app.auditor.audit_intent.assert_called_once()
    app.runner.write_input.assert_not_called()
    app.runner.suspend.assert_called_once()
    assert app.is_paused is True
    assert app.pending_approval.prompt_line == "Update src?"
    assert app.pending_approval.policy_decision.action is PolicyAction.REVIEW
    assert app.pending_approval.auditor_verdict is True
    assert app.pending_approval.auditor_reason == "YES. Safe."
    assert app.progress.progress == 100
    app.cortex_bridge.record_decision.assert_called_once()
    assert app.cortex_bridge.record_decision.call_args.kwargs["auditor_verdict"] is True
    app.trace_store.record_decision.assert_called_once()


def test_confirm_policy_creates_pending_approval_without_auditor():
    app = make_app()
    file_effect = FileEffect("deleted", "src/app.py")
    app.effect_observer.diff.return_value = [file_effect]
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.CONFIRM,
        "Delete effect requires explicit confirmation: src/app.py",
        effect=file_effect,
        risk="orange",
        effect_ids=["delete:workspace"],
    )

    run(app.perform_audit("Delete src/app.py?"))

    app.auditor.audit_intent.assert_not_called()
    app.runner.write_input.assert_not_called()
    app.runner.suspend.assert_called_once()
    assert app.is_paused is True
    assert app.pending_approval.prompt_line == "Delete src/app.py?"
    assert app.pending_approval.file_effects == [file_effect]
    assert app.pending_approval.policy_decision.risk == "orange"
    assert app.pending_approval.auditor_verdict is None
    assert app.pending_approval.auditor_reason is None
    assert app.progress.progress == 100


def test_pending_approval_logs_structured_confirm_context():
    app = make_app()
    file_effect = FileEffect("deleted", "src/app.py")
    decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "Delete effect requires explicit confirmation: src/app.py",
        effect=file_effect,
        risk="orange",
        effect_ids=["delete:workspace"],
    )

    app.create_pending_approval(
        prompt_line="Delete src/app.py?",
        file_effects=[file_effect],
        policy_decision=decision,
        auditor_verdict=None,
        auditor_reason=None,
    )

    text = "\n".join(app.reasoning_log.lines)
    assert "APPROVAL REQUIRED" in text
    assert "Command: echo test" in text
    assert "Prompt: Delete src/app.py?" in text
    assert "Policy: confirm" in text
    assert "Risk: orange" in text
    assert "Reason: Delete effect requires explicit confirmation: src/app.py" in text
    assert "Effect IDs: delete:workspace" in text
    assert "File Effects:" in text
    assert "- deleted: src/app.py" in text
    assert "Auditor: not run" in text
    assert "Controls: a=approve, b=block, o=override path, k=kill agent" in text


def test_pending_approval_logs_structured_auditor_context():
    app = make_app()
    file_effect = FileEffect("modified", "src/app.py")
    decision = PolicyDecision(
        PolicyAction.REVIEW,
        "Observed file effects are outside auto-approve paths; requires audit.",
        risk="yellow",
        effect_ids=["write:workspace"],
    )

    app.create_pending_approval(
        prompt_line="Update src/app.py?",
        file_effects=[file_effect],
        policy_decision=decision,
        auditor_verdict=True,
        auditor_reason="Structured auditor reason.",
    )

    text = "\n".join(app.reasoning_log.lines)
    assert "APPROVAL REQUIRED" in text
    assert "Policy: review" in text
    assert "Risk: yellow" in text
    assert "Effect IDs: write:workspace" in text
    assert "Auditor: approved" in text
    assert "Auditor Reason: Structured auditor reason." in text


def test_pending_approval_shows_dedicated_approval_panel():
    app = make_app()
    file_effect = FileEffect("deleted", "src/app.py")
    decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "Delete effect requires explicit confirmation: src/app.py",
        risk="orange",
        effect_ids=["delete:workspace"],
    )

    app.create_pending_approval(
        prompt_line="Delete src/app.py?",
        file_effects=[file_effect],
        policy_decision=decision,
        auditor_verdict=None,
        auditor_reason=None,
    )

    assert app.approval_panel.display is True
    assert "APPROVAL REQUIRED" in app.approval_panel.content
    assert "Command: echo test" in app.approval_panel.content
    assert "Prompt: Delete src/app.py?" in app.approval_panel.content
    assert "Risk: orange" in app.approval_panel.content
    assert "- deleted: src/app.py" in app.approval_panel.content


def test_pending_approval_panel_clears_after_approve_or_block():
    app = make_app()
    app.pending_approval = MagicMock()
    app.approval_panel.display = True
    app.approval_panel.content = "APPROVAL REQUIRED"
    app.is_paused = True

    app.action_approve_pending()

    assert app.approval_panel.display is False
    assert app.approval_panel.content == "No pending approval."

    app.pending_approval = MagicMock()
    app.approval_panel.display = True
    app.approval_panel.content = "APPROVAL REQUIRED"
    app.is_paused = False

    app.action_block_pending()

    assert app.approval_panel.display is False
    assert app.approval_panel.content == "No pending approval."


def test_second_pending_approval_is_queued_without_replacing_current():
    app = make_app()
    first_decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "First delete requires confirmation.",
        risk="orange",
        effect_ids=["delete:workspace"],
    )
    second_decision = PolicyDecision(
        PolicyAction.REVIEW,
        "Second write requires review.",
        risk="yellow",
        effect_ids=["write:workspace"],
    )

    app.create_pending_approval(
        prompt_line="Delete src/first.py?",
        file_effects=[FileEffect("deleted", "src/first.py")],
        policy_decision=first_decision,
        auditor_verdict=None,
        auditor_reason=None,
    )
    app.create_pending_approval(
        prompt_line="Update src/second.py?",
        file_effects=[FileEffect("modified", "src/second.py")],
        policy_decision=second_decision,
        auditor_verdict=True,
        auditor_reason="Auditor allowed second action.",
    )

    assert app.pending_approval.prompt_line == "Delete src/first.py?"
    assert [approval.prompt_line for approval in app.pending_approval_queue] == [
        "Update src/second.py?"
    ]
    assert "Prompt: Delete src/first.py?" in app.approval_panel.content
    assert "Queue: 1 waiting" in app.approval_panel.content
    assert any("Queued pending approval: Update src/second.py?" in line for line in app.reasoning_log.lines)


def test_approval_actions_advance_queue_before_resuming_agent():
    app = make_app()
    app.is_paused = True
    first_decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "First delete requires confirmation.",
        risk="orange",
        effect_ids=["delete:workspace"],
    )
    second_decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "Second delete requires confirmation.",
        risk="orange",
        effect_ids=["delete:workspace"],
    )
    app.create_pending_approval(
        prompt_line="Delete src/first.py?",
        file_effects=[FileEffect("deleted", "src/first.py")],
        policy_decision=first_decision,
        auditor_verdict=None,
        auditor_reason=None,
    )
    app.create_pending_approval(
        prompt_line="Delete src/second.py?",
        file_effects=[FileEffect("deleted", "src/second.py")],
        policy_decision=second_decision,
        auditor_verdict=None,
        auditor_reason=None,
    )

    app.action_approve_pending()

    app.runner.write_input.assert_called_once_with("y\n")
    app.runner.resume.assert_not_called()
    assert app.is_paused is True
    assert app.pending_approval.prompt_line == "Delete src/second.py?"
    assert app.pending_approval_queue == []
    assert "Prompt: Delete src/second.py?" in app.approval_panel.content
    assert app.approval_panel.display is True
    assert app.progress.progress == 100

    app.action_block_pending()

    app.runner.resume.assert_not_called()
    assert app.pending_approval is None
    assert app.pending_approval_queue == []
    assert app.approval_panel.display is False
    assert app.progress.progress == 100


def test_mounted_approval_panel_renders_and_clears_with_real_widget_tree():
    runner = MagicMock()
    runner.process = MagicMock(pid=123)
    runner.get_output.return_value = None
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner", return_value=runner):
        app = SentinelTUI("echo test")

    app.enforcer = MagicMock()
    app.trace_store = MagicMock()
    decision = PolicyDecision(
        PolicyAction.CONFIRM,
        "Delete effect requires explicit confirmation: src/app.py",
        risk="orange",
        effect_ids=["delete:workspace"],
    )

    async def scenario():
        async with app.run_test(size=(100, 30)) as pilot:
            panel = app.query_one("#approval_panel", Static)
            assert panel.display is False

            app.create_pending_approval(
                prompt_line="Delete src/app.py?",
                file_effects=[FileEffect("deleted", "src/app.py")],
                policy_decision=decision,
                auditor_verdict=None,
                auditor_reason=None,
            )
            await pilot.pause()

            assert panel.display is True
            assert "APPROVAL REQUIRED" in str(panel.content)
            assert "Prompt: Delete src/app.py?" in str(panel.content)
            assert "Risk: orange" in str(panel.content)

            app.action_block_pending()
            await pilot.pause()

            assert panel.display is False
            assert str(panel.content) == "No pending approval."

    run(scenario())


def test_mounted_manual_override_modal_creates_trace_visible_override():
    runner = MagicMock()
    runner.process = MagicMock(pid=123)
    runner.get_output.return_value = None
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner", return_value=runner):
        app = SentinelTUI("echo test")

    app.enforcer = MagicMock()
    app.trace_store = MagicMock()

    async def scenario():
        async with app.run_test(size=(100, 30)) as pilot:
            await app.action_manual_override()
            await pilot.pause()

            input_widget = app.screen.query_one("#manual_override_input", Input)
            input_widget.value = "src/manual/**"
            await pilot.press("enter")
            await pilot.pause()

            effect = FileEffect("modified", "src/manual/file.py")
            decision = app.policy.evaluate([effect])

            assert decision.action is PolicyAction.ALLOW
            assert decision.source == "override"
            assert count_manual_override_inputs(app) == 0
            create_calls = [
                call.args
                for call in app.trace_store.record_user_action.call_args_list
                if call.args and call.args[0] == "override.create"
            ]
            assert create_calls
            details = create_calls[-1][1]
            assert details["path_pattern"] == "src/manual/**"
            assert details["source"] == "manual"

    run(scenario())


def test_mounted_manual_override_modal_escape_cancels_without_override():
    runner = MagicMock()
    runner.process = MagicMock(pid=123)
    runner.get_output.return_value = None
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner", return_value=runner):
        app = SentinelTUI("echo test")

    app.enforcer = MagicMock()
    app.trace_store = MagicMock()

    async def scenario():
        async with app.run_test(size=(100, 30)) as pilot:
            await app.action_manual_override()
            await pilot.pause()
            assert count_manual_override_inputs(app) == 1

            await pilot.press("escape")
            await pilot.pause()

            assert count_manual_override_inputs(app) == 0
            assert app.override_store.list_active() == []
            assert not any(
                call.args and call.args[0] == "override.create"
                for call in app.trace_store.record_user_action.call_args_list
            )

    run(scenario())


def test_mounted_manual_override_modal_empty_submit_records_noop():
    runner = MagicMock()
    runner.process = MagicMock(pid=123)
    runner.get_output.return_value = None
    with patch("sentinel.tui.load_config", return_value=SentinelConfig()), \
         patch("sentinel.tui.Auditor"), \
         patch("sentinel.tui.AgentRunner", return_value=runner):
        app = SentinelTUI("echo test")

    app.enforcer = MagicMock()
    app.trace_store = MagicMock()

    async def scenario():
        async with app.run_test(size=(100, 30)) as pilot:
            await app.action_manual_override()
            await pilot.pause()

            input_widget = app.screen.query_one("#manual_override_input", Input)
            input_widget.value = "   "
            await pilot.press("enter")
            await pilot.pause()

            assert count_manual_override_inputs(app) == 0
            assert app.override_store.list_active() == []
            app.trace_store.record_user_action.assert_any_call(
                "override.create.noop",
                {
                    "reason": "empty path pattern",
                    "source": "manual",
                },
            )

    run(scenario())


def count_manual_override_inputs(app: SentinelTUI) -> int:
    return sum(len(screen.query("#manual_override_input")) for screen in app.screen_stack)


def test_approve_pending_resumes_and_sends_yes():
    app = make_app()
    app.pending_approval = MagicMock()
    app.is_paused = True

    app.action_approve_pending()

    app.trace_store.record_user_action.assert_any_call("approve_pending")
    app.runner.write_input.assert_called_once_with("y\n")
    app.runner.resume.assert_called_once()
    assert app.is_paused is False
    assert app.pending_approval is None
    assert app.progress.progress == 0


def test_block_pending_keeps_agent_suspended():
    app = make_app()
    app.pending_approval = MagicMock()
    app.is_paused = False

    app.action_block_pending()

    app.trace_store.record_user_action.assert_any_call("block_pending")
    app.runner.suspend.assert_called_once()
    app.runner.write_input.assert_not_called()
    assert app.is_paused is True
    assert app.pending_approval is None
    assert app.progress.progress == 100


def test_pending_actions_without_pending_approval_are_noops():
    app = make_app()

    app.action_approve_pending()
    app.action_block_pending()

    app.runner.write_input.assert_not_called()
    app.runner.resume.assert_not_called()
    app.runner.suspend.assert_not_called()
    app.trace_store.record_user_action.assert_any_call("approve_pending.noop")
    app.trace_store.record_user_action.assert_any_call("block_pending.noop")


def test_override_pending_creates_scoped_override_for_first_file_effect():
    app = make_app()
    app.override_store = SessionOverrideStore()
    app.policy = SentinelPolicy(app.config, override_store=app.override_store)
    file_effect = FileEffect("modified", "src/ui/button.py")
    app.pending_approval = MagicMock(file_effects=[file_effect])

    app.action_override_pending()

    override = app.override_store.active_for_effect(file_effect)
    assert override is not None
    assert override.path_pattern == "src/ui/button.py"
    assert override.action is PolicyAction.ALLOW
    assert "pending approval" in override.reason
    app.trace_store.record_user_action.assert_any_call(
        "override.create",
        {
            "override_id": override.override_id,
            "path_pattern": "src/ui/button.py",
            "action": "allow",
            "ttl_seconds": 900,
            "reason": "Allow path from pending approval",
            "source": "pending",
        },
    )
    assert any("Override created" in line for line in app.reasoning_log.lines)


def test_manual_allow_override_creates_scoped_trace_visible_override():
    app = make_app()
    app.override_store = SessionOverrideStore()
    app.policy = SentinelPolicy(app.config, override_store=app.override_store)

    override = app.create_manual_allow_override(" src/manual/** ")
    effect = FileEffect("modified", "src/manual/file.py")
    decision = app.policy.evaluate([effect])

    assert override is not None
    assert override.path_pattern == "src/manual/**"
    assert override.action is PolicyAction.ALLOW
    assert decision.action is PolicyAction.ALLOW
    assert decision.source == "override"
    assert decision.override_id == override.override_id
    app.trace_store.record_user_action.assert_any_call(
        "override.create",
        {
            "override_id": override.override_id,
            "path_pattern": "src/manual/**",
            "action": "allow",
            "ttl_seconds": 900,
            "reason": "Manual allow override",
            "source": "manual",
        },
    )
    assert any("Manual override created" in line for line in app.reasoning_log.lines)


def test_manual_allow_override_rejects_empty_pattern():
    app = make_app()

    override = app.create_manual_allow_override("   ")

    assert override is None
    assert app.override_store.list_active() == []
    app.trace_store.record_user_action.assert_any_call(
        "override.create.noop",
        {
            "reason": "empty path pattern",
            "source": "manual",
        },
    )
    assert any("No path pattern" in line for line in app.reasoning_log.lines)


def test_manual_allow_override_cannot_bypass_protected_path_blocks():
    app = make_app()
    app.override_store = SessionOverrideStore()
    app.policy = SentinelPolicy(app.config, override_store=app.override_store)

    app.create_manual_allow_override("**/.env")
    decision = app.policy.evaluate([FileEffect("modified", ".env")])

    assert decision.action is PolicyAction.BLOCK
    assert decision.source == "policy"
    assert "secret-like path" in decision.reason


def test_override_pending_without_file_effect_is_noop():
    app = make_app()
    app.pending_approval = MagicMock(file_effects=[])

    app.action_override_pending()

    app.trace_store.record_user_action.assert_any_call("override.create.noop")
    assert any("No file effect" in line for line in app.reasoning_log.lines)


def test_list_and_clear_session_overrides_log_and_trace():
    app = make_app()
    app.override_store = SessionOverrideStore()
    app.policy = SentinelPolicy(app.config, override_store=app.override_store)
    app.create_session_override(
        "src/ui/**",
        PolicyAction.ALLOW,
        ttl_seconds=120,
        reason="UI refactor",
    )

    app.action_list_overrides()
    app.action_clear_overrides()

    assert any("src/ui/**" in line for line in app.reasoning_log.lines)
    assert app.override_store.list_active() == []
    app.trace_store.record_user_action.assert_any_call("override.list")
    app.trace_store.record_user_action.assert_any_call("override.clear", {"count": 1})


def test_current_file_effects_reads_effect_observer():
    app = make_app()
    app.effect_observer = MagicMock()
    app.effect_observer.diff.return_value = [FileEffect("modified", "src/app.py")]

    assert app.current_file_effects() == [FileEffect("modified", "src/app.py")]


def test_review_audit_includes_file_effect_context():
    app = make_app()
    app.policy.evaluate.return_value = PolicyDecision(
        PolicyAction.REVIEW,
        "Observed file effects are outside auto-approve paths; requires audit.",
    )
    app.effect_observer = MagicMock()
    app.effect_observer.diff.return_value = [FileEffect("modified", "src/app.py")]
    app.auditor.audit_intent.return_value = (True, "YES. Safe.")

    run(app.perform_audit("Update src?"))

    _, observed_effect = app.auditor.audit_intent.call_args.args
    assert "PROMPT: Update src?" in observed_effect
    assert "modified: src/app.py" in observed_effect


def test_current_command_effects_detects_shell_network_and_deploy():
    app = make_app()

    assert app.current_command_effects("Run command: pytest -q?") == [
        CommandEffect("execute:shell", "Run command: pytest -q?")
    ]
    assert app.current_command_effects("Run command: curl https://example.com?") == [
        CommandEffect("network:external", "Run command: curl https://example.com?")
    ]
    assert app.current_command_effects("Run command: flyctl deploy?") == [
        CommandEffect("deploy:production", "Run command: flyctl deploy?")
    ]


def test_current_command_effects_extracts_json_tool_command_from_history():
    app = make_app()
    app.output_history = [
        '{"tool": "bash", "arguments": {"command": "curl https://example.com/api"}}',
    ]

    assert app.current_command_effects("Approve tool call?") == [
        CommandEffect("network:external", "curl https://example.com/api")
    ]


def test_current_command_effects_extracts_bash_tool_command_from_history():
    app = make_app()
    app.output_history = [
        'Tool call: Bash(command="flyctl deploy --remote-only")',
    ]

    assert app.current_command_effects("Proceed?") == [
        CommandEffect("deploy:production", "flyctl deploy --remote-only")
    ]
