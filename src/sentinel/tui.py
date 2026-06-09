import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Log, ProgressBar, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from sentinel.runner import AgentRunner
from sentinel.auditor import Auditor
from sentinel.config import DEFAULT_MODEL_ID, DEFAULT_PROMPT_PATTERNS, load_config
from sentinel.cortex_bridge import CortexBridge
from sentinel.effects import FileEffectObserver
from sentinel.enforcer import ContinuousEnforcer
from sentinel.policy import (
    CommandEffect,
    FileEffect,
    PolicyAction,
    PolicyDecision,
    SentinelPolicy,
    SessionOverride,
    SessionOverrideStore,
)
from sentinel.session_trace import SessionTraceStore


@dataclass(frozen=True)
class PendingApproval:
    prompt_line: str
    file_effects: list[FileEffect]
    policy_decision: PolicyDecision
    auditor_verdict: bool | None
    auditor_reason: str | None


class ManualOverrideScreen(ModalScreen[str | None]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="manual_override_dialog"):
            yield Static("Manual allow override", id="manual_override_title")
            yield Input(
                placeholder="Path glob, for example src/ui/**",
                id="manual_override_input",
            )
            yield Static("Enter creates a temporary allow override. Escape cancels.")

    def on_mount(self) -> None:
        self.query_one("#manual_override_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SentinelTUI(App):
    TITLE = "Cortex Sentinel"
    SUB_TITLE = "Trust HUD"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("k", "kill_agent", "Kill Agent", show=True),
        Binding("p", "toggle_pause", "Pause/Resume Agent", show=True),
        Binding("a", "approve_pending", "Approve Pending", show=True),
        Binding("b", "block_pending", "Block Pending", show=True),
        Binding("o", "override_pending", "Override Path", show=True),
        Binding("m", "manual_override", "Manual Override", show=True),
        Binding("v", "list_overrides", "List Overrides", show=True),
        Binding("x", "clear_overrides", "Clear Overrides", show=True),
    ]

    def __init__(
        self,
        command: str,
        config_path: str = "sentinel.yaml",
        *,
        initial_allow_overrides: list[str] | None = None,
    ):
        super().__init__()
        self.command = command
        self.config = load_config(config_path)
        workspace_root = self._workspace_root()
        trace_dir = self._trace_dir(workspace_root)
        self.runner = AgentRunner(command)
        self.auditor = Auditor(self._model_id())
        self.override_store = SessionOverrideStore()
        self.initial_override_records: list[dict[str, object]] = []
        self.policy = SentinelPolicy(self.config, override_store=self.override_store)
        self.effect_observer = FileEffectObserver(
            workspace_root,
            ignore_dirs=self._ignore_dirs(),
        )
        self.cortex_bridge = CortexBridge(workspace_root)
        self.trace_store = SessionTraceStore(trace_dir)
        self.enforcer = ContinuousEnforcer(
            runner=self.runner,
            observer=self.effect_observer,
            policy=self.policy,
            on_block=self.handle_continuous_block,
        )
        self.output_history: List[str] = []
        self.max_history = 50
        self.is_paused = False
        self.pending_approval: PendingApproval | None = None
        self.pending_approval_queue: list[PendingApproval] = []
        self.prompt_regex = re.compile("|".join(self._prompt_patterns()), re.IGNORECASE)
        self.seed_initial_allow_overrides(initial_allow_overrides or [])

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical():
                yield Log(id="agent_log")
            with Vertical():
                yield Log(id="reasoning_log")
        approval_panel = Static("No pending approval.", id="approval_panel")
        approval_panel.display = False
        yield approval_panel
        yield ProgressBar(id="drift_meter", total=100)
        yield Footer()

    def _model_id(self) -> str:
        model_id = getattr(self.config, "model_id", DEFAULT_MODEL_ID)
        return model_id if isinstance(model_id, str) else DEFAULT_MODEL_ID

    def _workspace_root(self) -> Path:
        workspace_root = getattr(self.config, "workspace_root", None)
        if isinstance(workspace_root, str) and workspace_root:
            return Path(workspace_root).expanduser().resolve()
        return Path.cwd()

    def _trace_dir(self, workspace_root: Path) -> Path:
        trace_dir = getattr(self.config, "trace_dir", ".sentinel/traces")
        if not isinstance(trace_dir, str) or not trace_dir:
            trace_dir = ".sentinel/traces"
        trace_path = Path(trace_dir).expanduser()
        if not trace_path.is_absolute():
            trace_path = workspace_root / trace_path
        return trace_path

    def _ignore_dirs(self) -> set[str]:
        ignore_dirs = getattr(self.config, "ignore_dirs", None)
        if isinstance(ignore_dirs, list) and all(isinstance(item, str) for item in ignore_dirs):
            return set(ignore_dirs)
        return set(FileEffectObserver.DEFAULT_IGNORES)

    def _prompt_patterns(self) -> list[str]:
        prompt_patterns = getattr(self.config, "prompt_patterns", None)
        if (
            isinstance(prompt_patterns, list)
            and prompt_patterns
            and all(isinstance(item, str) for item in prompt_patterns)
        ):
            return prompt_patterns
        return list(DEFAULT_PROMPT_PATTERNS)

    def seed_initial_allow_overrides(self, path_patterns: list[str]) -> None:
        for path_pattern in path_patterns:
            if not isinstance(path_pattern, str) or not path_pattern.strip():
                continue
            normalized_pattern = path_pattern.strip()
            ttl = self._override_ttl_seconds()
            override = self.override_store.add_path_override(
                normalized_pattern,
                PolicyAction.ALLOW,
                ttl_seconds=ttl,
                reason="CLI allow override",
            )
            self.initial_override_records.append(
                {
                    "override_id": override.override_id,
                    "path_pattern": normalized_pattern,
                    "action": PolicyAction.ALLOW.value,
                    "ttl_seconds": ttl,
                    "reason": "CLI allow override",
                    "source": "cli",
                }
            )

    def record_initial_overrides(self) -> None:
        if not self.initial_override_records:
            return
        reasoning_log = self.query_one("#reasoning_log", Log)
        for details in self.initial_override_records:
            self.trace_store.record_user_action("override.create", details)
            reasoning_log.write_line(
                f"Startup override active: {details['path_pattern']} -> {details['action']} "
                f"for {details['ttl_seconds']}s."
            )

    async def on_mount(self) -> None:
        self.enforcer.start()
        self.runner.start()
        self.trace_store.record_session_started(
            command=self.command,
            config_path="sentinel.yaml",
            cwd=str(Path.cwd()),
        )
        self.trace_store.record_process_event(
            "process.started",
            {"pid": self.runner.process.pid if self.runner.process else None},
        )
        self.query_one("#agent_log", Log).write_line(f"Starting agent: {self.command}")
        self.query_one("#reasoning_log", Log).write_line(
            "Safety boundary: Cortex Sentinel is local supervision, not a hard sandbox."
        )
        self.query_one("#reasoning_log", Log).write_line(
            "MCP-Cortex mode: trace-only metadata recording, not a tool-call authorization proxy."
        )
        self.record_initial_overrides()
        self.set_interval(0.1, self.poll_output)

    async def on_unmount(self) -> None:
        """Ensure the agent process is killed when the TUI exits."""
        self.enforcer.stop()
        self.trace_store.record_process_event("process.stopped", {})
        self.runner.kill()

    async def poll_output(self) -> None:
        if self.is_paused:
            return

        line = self.runner.get_output()
        while line:
            clean_line = line.strip()
            self.query_one("#agent_log", Log).write_line(clean_line)
            self.output_history.append(clean_line)
            if len(self.output_history) > self.max_history:
                self.output_history.pop(0)

            # Prompt detection
            if self.prompt_regex.search(clean_line):
                await self.perform_audit(clean_line)

            line = self.runner.get_output()

    async def perform_audit(self, prompt_line: str) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        reasoning_log.write_line(f"Detected potential prompt: {prompt_line}")

        file_effects = self.current_file_effects()
        command_effects = self.current_command_effects(prompt_line)
        policy_decision = self.policy.evaluate(
            file_effects,
            command_effects=command_effects,
        )
        reasoning_log.write_line(f"Policy Decision: {policy_decision.action.value.upper()}")
        reasoning_log.write_line(f"Policy Reason: {policy_decision.reason}")
        reasoning_log.write_line(f"Policy Risk: {policy_decision.risk}")
        if policy_decision.effect_ids:
            reasoning_log.write_line(f"Policy Effects: {', '.join(policy_decision.effect_ids)}")

        if policy_decision.action is PolicyAction.BLOCK:
            reasoning_log.write_line("Action blocked by deterministic policy.")
            self.record_cortex_decision(prompt_line, file_effects, policy_decision, None, None)
            self.action_toggle_pause()
            self.query_one("#drift_meter", ProgressBar).update(progress=100)
            return

        if policy_decision.action is PolicyAction.ALLOW:
            reasoning_log.write_line("Auto-approving by deterministic policy.")
            self.record_cortex_decision(prompt_line, file_effects, policy_decision, None, None)
            self.runner.write_input("y\n")
            self.query_one("#drift_meter", ProgressBar).update(progress=0)
            return

        if policy_decision.action is PolicyAction.CONFIRM:
            reasoning_log.write_line("Action requires explicit confirmation.")
            self.record_cortex_decision(prompt_line, file_effects, policy_decision, None, None)
            self.create_pending_approval(
                prompt_line=prompt_line,
                file_effects=file_effects,
                policy_decision=policy_decision,
                auditor_verdict=None,
                auditor_reason=None,
            )
            return

        # Simple MVP intent/effect extraction from history
        stated_intent = "\n".join(self.output_history[:-1])
        observed_effect = self.format_observed_effect(prompt_line, file_effects)

        # Run the synchronous audit in a thread
        reasoning_log.write_line("Auditing action...")
        loop = asyncio.get_event_loop()
        verdict, reasoning = await loop.run_in_executor(
            None, self.auditor.audit_intent, stated_intent, observed_effect
        )
        
        reasoning_log.write_line(f"Auditor Verdict: {'APPROVED' if verdict else 'BLOCKED'}")
        reasoning_log.write_line(f"Reasoning: {reasoning}")
        self.record_cortex_decision(prompt_line, file_effects, policy_decision, verdict, reasoning)

        if verdict:
            reasoning_log.write_line("Auditor allowed; awaiting explicit approval.")
            self.create_pending_approval(
                prompt_line=prompt_line,
                file_effects=file_effects,
                policy_decision=policy_decision,
                auditor_verdict=verdict,
                auditor_reason=reasoning,
            )
        else:
            reasoning_log.write_line("Action blocked. Suspending agent.")
            self.action_toggle_pause()
            self.query_one("#drift_meter", ProgressBar).update(progress=100)

    def create_pending_approval(
        self,
        *,
        prompt_line: str,
        file_effects: list[FileEffect],
        policy_decision: PolicyDecision,
        auditor_verdict: bool | None,
        auditor_reason: str | None,
    ) -> None:
        approval = PendingApproval(
            prompt_line=prompt_line,
            file_effects=file_effects,
            policy_decision=policy_decision,
            auditor_verdict=auditor_verdict,
            auditor_reason=auditor_reason,
        )
        if not self.is_paused:
            self.action_toggle_pause()
        if self.pending_approval is not None:
            self.pending_approval_queue.append(approval)
            self.trace_store.record_user_action(
                "approval.queue",
                {
                    "prompt_line": prompt_line,
                    "queue_depth": len(self.pending_approval_queue),
                },
            )
            self.query_one("#reasoning_log", Log).write_line(
                f"Queued pending approval: {prompt_line}"
            )
            self.update_pending_approval_panel(self.pending_approval)
            self.query_one("#drift_meter", ProgressBar).update(progress=100)
            return

        self.pending_approval = approval
        self.write_pending_approval(self.pending_approval)
        self.query_one("#drift_meter", ProgressBar).update(progress=100)

    def write_pending_approval(self, approval: PendingApproval) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        lines = self.render_pending_approval(approval)
        for line in lines:
            reasoning_log.write_line(line)
        approval_panel = self.query_one("#approval_panel", Static)
        approval_panel.update("\n".join(lines))
        approval_panel.display = True

    def update_pending_approval_panel(self, approval: PendingApproval) -> None:
        approval_panel = self.query_one("#approval_panel", Static)
        approval_panel.update("\n".join(self.render_pending_approval(approval)))
        approval_panel.display = True

    def render_pending_approval(self, approval: PendingApproval) -> list[str]:
        decision = approval.policy_decision
        lines = [
            "APPROVAL REQUIRED",
            f"Command: {self.command}",
            f"Prompt: {approval.prompt_line}",
            f"Policy: {decision.action.value}",
            f"Risk: {decision.risk}",
            f"Reason: {decision.reason}",
        ]
        if decision.effect_ids:
            lines.append(f"Effect IDs: {', '.join(decision.effect_ids)}")
        else:
            lines.append("Effect IDs: none")

        if approval.file_effects:
            lines.append("File Effects:")
            lines.extend(
                f"- {effect.operation}: {effect.path}"
                for effect in approval.file_effects
            )
        else:
            lines.append("File Effects: none observed")

        if approval.auditor_verdict is None:
            lines.append("Auditor: not run")
        else:
            verdict = "approved" if approval.auditor_verdict else "blocked"
            lines.append(f"Auditor: {verdict}")
            if approval.auditor_reason:
                lines.append(f"Auditor Reason: {approval.auditor_reason}")

        queue_depth = len(self.pending_approval_queue)
        if queue_depth:
            suffix = "approval" if queue_depth == 1 else "approvals"
            lines.append(f"Queue: {queue_depth} waiting {suffix}")

        lines.append("Controls: a=approve, b=block, o=override path, k=kill agent")
        return lines

    def clear_pending_approval_panel(self) -> None:
        approval_panel = self.query_one("#approval_panel", Static)
        approval_panel.update("No pending approval.")
        approval_panel.display = False

    def advance_pending_approval_queue(self) -> bool:
        if not self.pending_approval_queue:
            return False
        self.pending_approval = self.pending_approval_queue.pop(0)
        self.write_pending_approval(self.pending_approval)
        self.query_one("#drift_meter", ProgressBar).update(progress=100)
        return True

    def current_file_effects(self):
        return self.effect_observer.diff()

    def current_command_effects(self, prompt_line: str) -> list[CommandEffect]:
        candidates = self.command_text_candidates(prompt_line)
        for command_text, _is_structured_command in candidates:
            lower_command = command_text.lower()
            if (
                "flyctl deploy" in lower_command
                or "deploy" in lower_command
                and "production" in lower_command
            ):
                return [CommandEffect("deploy:production", command_text)]
        for command_text, _is_structured_command in candidates:
            if re.search(r"\b(curl|wget)\s+https?://", command_text.lower()):
                return [CommandEffect("network:external", command_text)]
        for command_text, is_structured_command in candidates:
            if is_structured_command or re.search(r"\b(run|execute|command):", command_text.lower()):
                return [CommandEffect("execute:shell", command_text)]
        return []

    def command_text_candidates(self, prompt_line: str) -> list[tuple[str, bool]]:
        candidates: list[tuple[str, bool]] = []
        for line in self.output_history[-10:]:
            for command in self.extract_structured_commands(line):
                candidates.append((command, True))
        candidates.append((prompt_line, False))
        return candidates

    @classmethod
    def extract_structured_commands(cls, line: str) -> list[str]:
        commands = cls.extract_json_commands(line)
        commands.extend(cls.extract_text_tool_commands(line))
        return commands

    @classmethod
    def extract_json_commands(cls, line: str) -> list[str]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return []
        return cls.extract_command_values(payload)

    @classmethod
    def extract_command_values(cls, value: object) -> list[str]:
        commands: list[str] = []
        if isinstance(value, dict):
            for key, nested_value in value.items():
                if key.lower() in {"command", "cmd"} and isinstance(nested_value, str):
                    stripped = nested_value.strip()
                    if stripped:
                        commands.append(stripped)
                    continue
                commands.extend(cls.extract_command_values(nested_value))
        elif isinstance(value, list):
            for item in value:
                commands.extend(cls.extract_command_values(item))
        return commands

    @staticmethod
    def extract_text_tool_commands(line: str) -> list[str]:
        commands: list[str] = []
        for pattern in [
            r"\bBash\(\s*command\s*=\s*\"(?P<command>[^\"]+)\"\s*\)",
            r"\bBash\(\s*command\s*=\s*'(?P<command>[^']+)'\s*\)",
            r"\bBash\(\s*(?P<command>[^)]+)\)",
            r"\bCommand:\s*(?P<command>.+)$",
        ]:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                command = match.group("command").strip()
                if command:
                    commands.append(command)
        return commands

    def record_cortex_decision(
        self,
        prompt_line,
        file_effects,
        policy_decision,
        auditor_verdict,
        auditor_reason,
    ):
        try:
            self.cortex_bridge.record_decision(
                prompt_line=prompt_line,
                file_effects=file_effects,
                policy_decision=policy_decision,
                auditor_verdict=auditor_verdict,
                auditor_reason=auditor_reason,
            )
        except Exception:
            # Tracing must never prevent local process control.
            pass
        try:
            self.trace_store.record_decision(
                prompt_line=prompt_line,
                file_effects=file_effects,
                policy_decision=policy_decision,
                auditor_verdict=auditor_verdict,
                auditor_reason=auditor_reason,
            )
        except Exception:
            pass

    def handle_continuous_block(self, policy_decision, file_effects):
        try:
            reasoning_log = self.query_one("#reasoning_log", Log)
            reasoning_log.write_line("Continuous policy block: protected file effect detected.")
            reasoning_log.write_line(f"Policy Reason: {policy_decision.reason}")
            self.record_cortex_decision(
                "continuous file enforcement",
                file_effects,
                policy_decision,
                None,
                None,
            )
            rollback_results = getattr(self.enforcer, "last_rollback_results", [])
            if rollback_results:
                self.trace_store.record_enforcement_rollback(
                    file_effects=file_effects,
                    rollback_results=rollback_results,
                )
                reasoning_log.write_line("Rollback recorded for blocked file effect.")
        except Exception:
            pass

    @staticmethod
    def format_observed_effect(prompt_line, file_effects):
        lines = [f"PROMPT: {prompt_line}"]
        if file_effects:
            lines.append("FILE EFFECTS:")
            lines.extend(f"- {effect.operation}: {effect.path}" for effect in file_effects)
        else:
            lines.append("FILE EFFECTS: none observed")
        return "\n".join(lines)

    def action_kill_agent(self) -> None:
        self.trace_store.record_user_action("kill_agent")
        self.runner.kill()
        self.query_one("#agent_log", Log).write_line("Agent killed.")
        self.query_one("#reasoning_log", Log).write_line("Agent killed by user.")

    def action_toggle_pause(self) -> None:
        if self.is_paused:
            self.trace_store.record_user_action("resume_agent")
            self.runner.resume()
            self.is_paused = False
            self.query_one("#reasoning_log", Log).write_line("Agent resumed.")
        else:
            self.trace_store.record_user_action("pause_agent")
            self.runner.suspend()
            self.is_paused = True
            self.query_one("#reasoning_log", Log).write_line("Agent suspended.")

    def action_approve_pending(self) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        if self.pending_approval is None:
            self.trace_store.record_user_action("approve_pending.noop")
            reasoning_log.write_line("No pending approval to approve.")
            return

        self.trace_store.record_user_action("approve_pending")
        self.runner.write_input("y\n")
        self.pending_approval = None
        if self.advance_pending_approval_queue():
            reasoning_log.write_line("Advanced to next pending approval.")
            return
        self.clear_pending_approval_panel()
        if self.is_paused:
            self.runner.resume()
            self.is_paused = False
        reasoning_log.write_line("Pending action approved.")
        self.query_one("#drift_meter", ProgressBar).update(progress=0)

    def action_block_pending(self) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        if self.pending_approval is None:
            self.trace_store.record_user_action("block_pending.noop")
            reasoning_log.write_line("No pending approval to block.")
            return

        self.trace_store.record_user_action("block_pending")
        self.pending_approval = None
        if self.advance_pending_approval_queue():
            reasoning_log.write_line("Advanced to next pending approval.")
            return
        self.clear_pending_approval_panel()
        if not self.is_paused:
            self.runner.suspend()
            self.is_paused = True
        reasoning_log.write_line("Pending action blocked.")
        self.query_one("#drift_meter", ProgressBar).update(progress=100)

    def create_session_override(
        self,
        path_pattern: str,
        action: PolicyAction,
        *,
        ttl_seconds: int | None = None,
        reason: str,
        source: str = "tui",
    ) -> SessionOverride:
        ttl = ttl_seconds or self._override_ttl_seconds()
        override = self.override_store.add_path_override(
            path_pattern,
            action,
            ttl_seconds=ttl,
            reason=reason,
        )
        details = {
            "override_id": override.override_id,
            "path_pattern": path_pattern,
            "action": action.value,
            "ttl_seconds": ttl,
            "reason": reason,
            "source": source,
        }
        self.trace_store.record_user_action("override.create", details)
        self.query_one("#reasoning_log", Log).write_line(
            f"Override created: {path_pattern} -> {action.value} for {ttl}s."
        )
        return override

    def create_manual_allow_override(self, path_pattern: str) -> SessionOverride | None:
        normalized_pattern = path_pattern.strip()
        reasoning_log = self.query_one("#reasoning_log", Log)
        if not normalized_pattern:
            self.trace_store.record_user_action(
                "override.create.noop",
                {
                    "reason": "empty path pattern",
                    "source": "manual",
                },
            )
            reasoning_log.write_line("No path pattern provided for manual override.")
            return None

        override = self.create_session_override(
            normalized_pattern,
            PolicyAction.ALLOW,
            reason="Manual allow override",
            source="manual",
        )
        reasoning_log.write_line(
            f"Manual override created: {normalized_pattern} -> {PolicyAction.ALLOW.value}."
        )
        return override

    async def action_manual_override(self) -> None:
        await self.push_screen(ManualOverrideScreen(), self.handle_manual_override_pattern)

    def handle_manual_override_pattern(self, path_pattern: str | None) -> None:
        if path_pattern is None:
            self.trace_store.record_user_action("override.input.cancel")
            self.query_one("#reasoning_log", Log).write_line("Manual override cancelled.")
            return
        self.create_manual_allow_override(path_pattern)

    def action_override_pending(self) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        if self.pending_approval is None:
            self.trace_store.record_user_action("override.create.noop")
            reasoning_log.write_line("No pending approval to override.")
            return
        if not self.pending_approval.file_effects:
            self.trace_store.record_user_action("override.create.noop")
            reasoning_log.write_line("No file effect is available for an override.")
            return

        effect = self.pending_approval.file_effects[0]
        self.create_session_override(
            effect.path,
            PolicyAction.ALLOW,
            reason="Allow path from pending approval",
            source="pending",
        )

    def action_list_overrides(self) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        self.trace_store.record_user_action("override.list")
        overrides = self.override_store.list_active()
        if not overrides:
            reasoning_log.write_line("No active session overrides.")
            return
        for override in overrides:
            reasoning_log.write_line(
                f"Override active: {override.path_pattern} -> {override.action.value} "
                f"until {override.expires_at_seconds:.0f} ({override.override_id})."
            )

    def action_clear_overrides(self) -> None:
        count = self.override_store.clear()
        self.trace_store.record_user_action("override.clear", {"count": count})
        self.query_one("#reasoning_log", Log).write_line(
            f"Cleared {count} session override(s)."
        )

    def _override_ttl_seconds(self) -> int:
        ttl = getattr(self.config, "override_ttl_seconds", 900)
        return ttl if isinstance(ttl, int) and ttl > 0 else 900

    async def action_quit(self) -> None:
        self.trace_store.record_user_action("quit")
        self.enforcer.stop()
        self.runner.kill()
        self.exit()
