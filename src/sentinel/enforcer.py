from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from sentinel.effects import FileEffectObserver
from sentinel.policy import FileEffect, PolicyAction, PolicyDecision, SentinelPolicy

logger = logging.getLogger(__name__)


class ContinuousEnforcer:
    def __init__(
        self,
        *,
        runner,
        observer: FileEffectObserver,
        policy: SentinelPolicy,
        interval_seconds: float = 0.25,
        on_block: Callable[[PolicyDecision, list[FileEffect]], None] | None = None,
    ):
        self.runner = runner
        self.observer = observer
        self.policy = policy
        self.interval_seconds = interval_seconds
        self.on_block = on_block
        self.last_decision: PolicyDecision | None = None
        self.last_effects: list[FileEffect] = []
        self.last_rollback_results: list[dict[str, str]] = []
        self.protected_content_baseline: dict[str, bytes] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("ContinuousEnforcer is already active")
            self.observer.snapshot()
            self.capture_protected_baseline()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        thread = None
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
        if thread:
            thread.join(timeout=2)

    def check_once(self) -> PolicyDecision | None:
        effects = self.observer.diff()
        if not effects:
            return None

        decision = self.policy.evaluate(effects)
        self.last_decision = decision
        self.last_effects = effects
        self.last_rollback_results = []

        if decision.action is PolicyAction.BLOCK:
            self.runner.suspend()
            self.last_rollback_results = self.rollback_blocked_effects(effects)
            self.observer.snapshot()
            self.capture_protected_baseline()
            if self.on_block:
                self.on_block(decision, effects)
            return decision

        self.observer.snapshot()
        self.capture_protected_baseline()
        return decision

    def capture_protected_baseline(self) -> None:
        self.protected_content_baseline = self.observer.content_snapshot(
            self.rollback_path_patterns()
        )

    def rollback_path_patterns(self) -> list[str]:
        patterns = list(self.policy.config.protected_paths)
        patterns.extend(["**/.env", "**/.env.local", "**/.ssh/**", ".ssh/**"])
        return patterns

    def rollback_blocked_effects(self, effects: list[FileEffect]) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for effect in effects:
            path = self.observer.safe_path(effect.path)
            if path is None:
                results.append(
                    {
                        "path": effect.path,
                        "operation": effect.operation,
                        "rollback": "skipped-unsafe-path",
                    }
                )
                continue

            baseline = self.protected_content_baseline.get(effect.path)
            operation = effect.operation.lower()
            if operation == "created":
                if path.exists() and path.is_file() and not path.is_symlink():
                    path.unlink()
                    rollback = "deleted-created-file"
                else:
                    rollback = "skipped-created-file"
            elif operation in {"modified", "deleted"} and baseline is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(baseline)
                rollback = "restored-baseline"
            else:
                rollback = "no-baseline"

            results.append(
                {
                    "path": effect.path,
                    "operation": effect.operation,
                    "rollback": rollback,
                }
            )
        return results

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception as e:
                logger.error(f"Continuous enforcement check failed: {e}")
            self._stop_event.wait(self.interval_seconds)
