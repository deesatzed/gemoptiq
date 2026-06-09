from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sentinel.policy import FileEffect, PolicyAction, PolicyDecision


class CortexBridge:
    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.enabled = False
        self.gateway = None
        self._mcp_cortex = None
        self._load_local_mcp_cortex()

    def record_decision(
        self,
        *,
        prompt_line: str,
        file_effects: list[FileEffect],
        policy_decision: PolicyDecision,
        auditor_verdict: bool | None,
        auditor_reason: str | None,
    ) -> dict[str, Any]:
        if not self.enabled or self.gateway is None or self._mcp_cortex is None:
            return {"enabled": False, "status": "disabled"}

        requested_effects = self._requested_effects(file_effects)
        capability = self._mcp_cortex.CapabilityContract(
            capability="capability://sentinel/agent-supervision",
            version="0.1.0",
            input_schema={"type": "object"},
            effects=requested_effects,
            forbidden_effects=["read:secrets", "write:production", "deploy:production"],
            requires=[],
            assurance_level="A2",
            risk="medium",
        )
        intent = self._mcp_cortex.Intent.create(
            goal={
                "desired_state": "agent.action.reviewed",
                "prompt": prompt_line,
                "sentinel_policy_action": policy_decision.action.value,
            },
            requested_effects=requested_effects,
            constraints={"no_external_network": True},
            requester="sentinel://tui",
        )
        decision = self.gateway.propose_and_check(
            intent,
            capability,
            context_labels=["code"],
        )
        result_event = self.gateway.record_result(
            intent,
            capability,
            {
                "sentinel_policy": {
                    "action": policy_decision.action.value,
                    "reason": policy_decision.reason,
                    "matched_pattern": policy_decision.matched_pattern,
                },
                "auditor": {
                    "verdict": auditor_verdict,
                    "reason": auditor_reason,
                },
                "file_effects": [
                    {"operation": effect.operation, "path": effect.path}
                    for effect in file_effects
                ],
            },
            actor="sentinel://tui",
        )
        return {
            "enabled": True,
            "status": "recorded",
            "decision": decision.to_dict(),
            "requested_effects": requested_effects,
            "trace_event_count": len(self.gateway.trace_log.all()),
            "result_digest": result_event.digest,
        }

    def _load_local_mcp_cortex(self) -> None:
        local_src = self.project_root / "mcp-cortex" / "src"
        if not local_src.exists():
            return
        local_src_str = str(local_src)
        if local_src_str not in sys.path:
            sys.path.insert(0, local_src_str)

        try:
            import mcp_cortex  # type: ignore
        except ImportError:
            return

        self._mcp_cortex = mcp_cortex
        self.gateway = mcp_cortex.CortexGateway()
        self.enabled = True

    @staticmethod
    def _requested_effects(file_effects: list[FileEffect]) -> list[str]:
        effects: set[str] = set()
        if not file_effects:
            return ["tool:call"]

        for effect in file_effects:
            normalized = effect.path.replace("\\", "/")
            if normalized == ".env" or normalized.endswith("/.env") or normalized.startswith(".ssh/"):
                effects.add("read:secrets")
            elif effect.operation in {"created", "modified", "deleted"}:
                effects.add("write:workspace")
            else:
                effects.add("tool:call")
        return sorted(effects)
