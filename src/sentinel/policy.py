from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
import time
from uuid import uuid4

from sentinel.config import SentinelConfig


class PolicyAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class FileEffect:
    operation: str
    path: str

    def normalized_path(self) -> str:
        return str(Path(self.path).expanduser()).replace("\\", "/")


@dataclass(frozen=True)
class CommandEffect:
    operation: str
    command: str


@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyAction
    reason: str
    matched_pattern: str | None = None
    effect: FileEffect | None = None
    risk: str = "yellow"
    effect_ids: list[str] = field(default_factory=list)
    source: str = "policy"
    override_id: str | None = None


@dataclass(frozen=True)
class SessionOverride:
    override_id: str
    path_pattern: str
    action: PolicyAction
    expires_at_seconds: float
    reason: str

    def is_active(self, now_seconds: float) -> bool:
        return now_seconds <= self.expires_at_seconds

    def matches(self, effect: FileEffect) -> bool:
        pattern = str(Path(self.path_pattern).expanduser()).replace("\\", "/")
        return SentinelPolicy._matches(effect.normalized_path(), pattern)


class SessionOverrideStore:
    def __init__(self):
        self._overrides: list[SessionOverride] = []

    def add_path_override(
        self,
        path_pattern: str,
        action: PolicyAction,
        *,
        ttl_seconds: int,
        reason: str,
        now_seconds: float | None = None,
    ) -> SessionOverride:
        now = time.time() if now_seconds is None else now_seconds
        override = SessionOverride(
            override_id=f"override-{uuid4()}",
            path_pattern=path_pattern,
            action=action,
            expires_at_seconds=now + ttl_seconds,
            reason=reason,
        )
        self._overrides.append(override)
        return override

    def active_for_effect(
        self,
        effect: FileEffect,
        *,
        now_seconds: float | None = None,
    ) -> SessionOverride | None:
        now = time.time() if now_seconds is None else now_seconds
        for override in self._overrides:
            if override.is_active(now) and override.matches(effect):
                return override
        return None

    def list_active(self, *, now_seconds: float | None = None) -> list[SessionOverride]:
        now = time.time() if now_seconds is None else now_seconds
        return [override for override in self._overrides if override.is_active(now)]

    def clear(self) -> int:
        count = len(self._overrides)
        self._overrides.clear()
        return count


class SentinelPolicy:
    def __init__(
        self,
        config: SentinelConfig,
        *,
        override_store: SessionOverrideStore | None = None,
    ):
        self.config = config
        self.override_store = override_store or SessionOverrideStore()

    def evaluate(
        self,
        effects: list[FileEffect],
        command_effects: list[CommandEffect] | None = None,
        now_seconds: float | None = None,
    ) -> PolicyDecision:
        command_effects = command_effects or []
        if not effects and not command_effects:
            return PolicyDecision(PolicyAction.REVIEW, "No file effects available; requires audit.")

        for effect in effects:
            matched = self._match_any(effect, self.config.protected_paths)
            if matched:
                return PolicyDecision(
                    PolicyAction.BLOCK,
                    f"Effect touches protected path: {effect.path}",
                    matched_pattern=matched,
                    effect=effect,
                    risk="red",
                    effect_ids=[self._file_effect_id(effect)],
                )

        for effect in effects:
            if self._is_secret_path(effect.normalized_path()):
                return PolicyDecision(
                    PolicyAction.BLOCK,
                    f"Effect touches secret-like path: {effect.path}",
                    effect=effect,
                    risk="red",
                    effect_ids=[self._file_effect_id(effect)],
                )

        command_ids = [self._command_effect_id(effect) for effect in command_effects]
        for effect, effect_id in zip(command_effects, command_ids):
            if effect_id == "network:external":
                return PolicyDecision(
                    PolicyAction.BLOCK,
                    f"Network access requires explicit policy approval: {effect.command}",
                    risk="red",
                    effect_ids=[effect_id],
                )
            if effect_id == "deploy:production":
                return PolicyDecision(
                    PolicyAction.BLOCK,
                    f"Production deploy attempt is blocked: {effect.command}",
                    risk="red",
                    effect_ids=[effect_id],
                )

        file_ids = [self._file_effect_id(effect) for effect in effects]

        override_decision = self._override_decision(
            effects,
            file_ids,
            command_effects,
            now_seconds,
        )
        if override_decision:
            return override_decision

        threshold_decision = self._threshold_decision(
            effect_ids=file_ids + command_ids,
            default_action=None,
        )
        if threshold_decision:
            return threshold_decision

        for effect, effect_id in zip(effects, file_ids):
            if effect_id == "delete:workspace":
                return PolicyDecision(
                    PolicyAction.CONFIRM,
                    f"Delete effect requires explicit confirmation: {effect.path}",
                    effect=effect,
                    risk="orange",
                    effect_ids=[effect_id],
                )

        if command_ids:
            return PolicyDecision(
                PolicyAction.REVIEW,
                "Shell command effect requires audit.",
                risk="yellow",
                effect_ids=command_ids + file_ids,
            )

        auto_matches = [
            self._match_any(effect, self.config.auto_approve_paths)
            for effect in effects
        ]
        if self.config.auto_approve_paths and all(auto_matches):
            first_match = next((match for match in auto_matches if match), None)
            return PolicyDecision(
                PolicyAction.ALLOW,
                "All observed file effects are auto-approved by config.",
                matched_pattern=first_match,
                risk="green",
                effect_ids=file_ids,
            )

        return PolicyDecision(
            PolicyAction.REVIEW,
            "Observed file effects are outside auto-approve paths; requires audit.",
            risk="yellow",
            effect_ids=file_ids,
        )

    def _override_decision(
        self,
        effects: list[FileEffect],
        file_ids: list[str],
        command_effects: list[CommandEffect],
        now_seconds: float | None,
    ) -> PolicyDecision | None:
        if not effects or command_effects:
            return None

        overrides = [
            self.override_store.active_for_effect(effect, now_seconds=now_seconds)
            for effect in effects
        ]
        if not all(overrides):
            return None

        first_override = overrides[0]
        if first_override is None:
            return None
        if any(override.action is not first_override.action for override in overrides if override):
            return None

        return PolicyDecision(
            first_override.action,
            f"Session override applies: {first_override.reason}",
            matched_pattern=first_override.path_pattern,
            effect=effects[0],
            risk="green" if first_override.action is PolicyAction.ALLOW else "yellow",
            effect_ids=file_ids,
            source="override",
            override_id=first_override.override_id,
        )

    def _threshold_decision(
        self,
        *,
        effect_ids: list[str],
        default_action: PolicyAction | None,
    ) -> PolicyDecision | None:
        thresholds = getattr(self.config, "risk_thresholds", {}) or {}
        for effect_id in effect_ids:
            threshold = thresholds.get(effect_id)
            action = self._action_from_threshold(threshold)
            built_in_default = self._default_action_for_effect_id(effect_id)
            if action is None or action is default_action or action is built_in_default:
                continue
            return PolicyDecision(
                action,
                f"Risk threshold requires {action.value} for {effect_id}.",
                risk="red" if action is PolicyAction.BLOCK else "yellow",
                effect_ids=[effect_id],
            )
        return None

    def _match_any(self, effect: FileEffect, patterns: list[str]) -> str | None:
        path = effect.normalized_path()
        for pattern in patterns:
            normalized_pattern = str(Path(pattern).expanduser()).replace("\\", "/")
            if self._matches(path, normalized_pattern):
                return pattern
        return None

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        if fnmatch(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch(path, pattern[3:]):
            return True
        return False

    @staticmethod
    def _file_effect_id(effect: FileEffect) -> str:
        operation = effect.operation.lower()
        path = effect.normalized_path()
        if SentinelPolicy._is_secret_path(path):
            if operation in {"read", "accessed"}:
                return "read:secret"
            return "write:secret"
        if operation in {"deleted", "delete", "removed", "remove"}:
            return "delete:workspace"
        if operation in {"created", "create", "modified", "modify", "write", "written"}:
            return "write:workspace"
        if operation in {"read", "accessed"}:
            return "read:workspace"
        return f"{operation}:workspace"

    @staticmethod
    def _command_effect_id(effect: CommandEffect) -> str:
        operation = effect.operation.lower()
        command = effect.command.lower()
        if operation == "deploy:production" or "flyctl deploy" in command:
            return "deploy:production"
        if operation == "network:external":
            return "network:external"
        if operation in {"execute:shell", "shell"}:
            return "execute:shell"
        return operation

    @staticmethod
    def _action_from_threshold(threshold: object) -> PolicyAction | None:
        if not isinstance(threshold, str):
            return None
        try:
            return PolicyAction(threshold)
        except ValueError:
            return None

    @staticmethod
    def _default_action_for_effect_id(effect_id: str) -> PolicyAction | None:
        if effect_id == "delete:workspace":
            return PolicyAction.CONFIRM
        if effect_id == "execute:shell":
            return PolicyAction.REVIEW
        if effect_id in {"read:secret", "write:secret", "network:external", "deploy:production"}:
            return PolicyAction.BLOCK
        return None

    @staticmethod
    def _is_secret_path(path: str) -> bool:
        path_parts = [part for part in path.split("/") if part]
        name = path_parts[-1] if path_parts else path
        return name in {".env", ".env.local"} or ".ssh" in path_parts
