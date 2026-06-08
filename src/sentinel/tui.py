import asyncio
from typing import List
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, ProgressBar
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from sentinel.runner import AgentRunner
from sentinel.auditor import Auditor
from sentinel.config import load_config

class SentinelTUI(App):
    TITLE = "Cortex Sentinel"
    SUB_TITLE = "Trust HUD"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("k", "kill_agent", "Kill Agent", show=True),
        Binding("p", "toggle_pause", "Pause/Resume Agent", show=True),
    ]

    def __init__(self, command: str, config_path: str = "sentinel.yaml"):
        super().__init__()
        self.command = command
        self.config = load_config(config_path)
        self.runner = AgentRunner(command)
        self.auditor = Auditor(self.config.model_id)
        self.output_history: List[str] = []
        self.max_history = 10
        self.is_paused = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical():
                yield Log(id="agent_log")
            with Vertical():
                yield Log(id="reasoning_log")
        yield ProgressBar(id="drift_meter", total=100)
        yield Footer()

    async def on_mount(self) -> None:
        self.runner.start()
        self.query_one("#agent_log", Log).write_line(f"Starting agent: {self.command}")
        self.set_interval(0.1, self.poll_output)

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
            if clean_line.endswith("?") or "[y/n]" in clean_line.lower():
                await self.perform_audit(clean_line)

            line = self.runner.get_output()

    async def perform_audit(self, prompt_line: str) -> None:
        reasoning_log = self.query_one("#reasoning_log", Log)
        reasoning_log.write_line(f"Detected potential prompt: {prompt_line}")
        
        # Simple MVP intent/effect extraction from history
        stated_intent = "\n".join(self.output_history[:-1])
        observed_effect = prompt_line

        # Run the synchronous audit in a thread
        reasoning_log.write_line("Auditing action...")
        loop = asyncio.get_event_loop()
        verdict, reasoning = await loop.run_in_executor(
            None, self.auditor.audit_intent, stated_intent, observed_effect
        )
        
        reasoning_log.write_line(f"Auditor Verdict: {'APPROVED' if verdict else 'BLOCKED'}")
        reasoning_log.write_line(f"Reasoning: {reasoning}")

        if verdict:
            reasoning_log.write_line("Auto-approving (sending 'y')...")
            self.runner.write_input("y\n")
            self.query_one("#drift_meter", ProgressBar).update(progress=0)
        else:
            reasoning_log.write_line("Action blocked. Suspending agent.")
            self.action_toggle_pause()
            self.query_one("#drift_meter", ProgressBar).update(progress=100)

    def action_kill_agent(self) -> None:
        self.runner.kill()
        self.query_one("#agent_log", Log).write_line("Agent killed.")
        self.query_one("#reasoning_log", Log).write_line("Agent killed by user.")

    def action_toggle_pause(self) -> None:
        if self.is_paused:
            self.runner.resume()
            self.is_paused = False
            self.query_one("#reasoning_log", Log).write_line("Agent resumed.")
        else:
            self.runner.suspend()
            self.is_paused = True
            self.query_one("#reasoning_log", Log).write_line("Agent suspended.")

    async def action_quit(self) -> None:
        self.runner.kill()
        await self.action_exit()
