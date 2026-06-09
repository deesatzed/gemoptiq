from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
import yaml


DEFAULT_MODEL_ID = "mlx-community/gemma-4-12B-it-OptiQ-4bit"
DEFAULT_PROMPT_PATTERNS = [r"\?\s*$", r"\[y/n\]"]
DEFAULT_MODEL_PARAMETERS = {
    "max_tokens": 96,
    "temperature": 0.0,
}
DEFAULT_RISK_THRESHOLDS = {
    "read:secret": "block",
    "write:secret": "block",
    "delete:workspace": "confirm",
    "execute:shell": "review",
    "network:external": "block",
    "deploy:production": "block",
}


class ConfigError(ValueError):
    pass


@dataclass
class SentinelConfig:
    protected_paths: list[str] = field(default_factory=list)
    auto_approve_paths: list[str] = field(default_factory=list)
    model_id: str = DEFAULT_MODEL_ID
    workspace_root: str | None = None
    ignore_dirs: list[str] = field(default_factory=lambda: [".git", "__pycache__", ".sentinel"])
    prompt_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_PROMPT_PATTERNS))
    model_parameters: dict[str, object] = field(default_factory=lambda: deepcopy(DEFAULT_MODEL_PARAMETERS))
    risk_thresholds: dict[str, str] = field(default_factory=lambda: deepcopy(DEFAULT_RISK_THRESHOLDS))
    policy_profile: str = "default"
    policy_profiles: dict[str, dict] = field(default_factory=dict)
    trace_dir: str = ".sentinel/traces"
    pty_mode: bool = False
    override_ttl_seconds: int = 900


LIST_FIELDS = {
    "protected_paths",
    "auto_approve_paths",
    "ignore_dirs",
    "prompt_patterns",
}
PATH_FIELDS = {
    "protected_paths",
    "auto_approve_paths",
    "workspace_root",
    "trace_dir",
}
DICT_FIELDS = {
    "model_parameters",
    "risk_thresholds",
    "policy_profiles",
}
BOOL_FIELDS = {"pty_mode"}
INT_FIELDS = {"override_ttl_seconds"}
STRING_FIELDS = {"model_id", "workspace_root", "policy_profile", "trace_dir"}


def load_config(path_str: str, *, strict: bool = False) -> SentinelConfig:
    path = Path(path_str)
    if not path.exists():
        return SentinelConfig()

    try:
        with path.open('r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        if strict:
            raise ConfigError(f"Invalid YAML: {exc}") from exc
        return SentinelConfig()

    if not isinstance(data, dict):
        if strict:
            raise ConfigError("Config root must be a mapping.")
        return SentinelConfig()

    config_data = _filtered_config_data(data, strict=strict)
    profile_name = config_data.get("policy_profile", "default")
    profile_data = _profile_data(config_data, profile_name, strict=strict)
    if profile_data:
        config_data = _merge_profile(config_data, profile_data, strict=strict)

    config_data = _normalize_paths(config_data)
    return SentinelConfig(**config_data)


def _filtered_config_data(data: dict, *, strict: bool) -> dict:
    valid_fields = set(SentinelConfig.__dataclass_fields__.keys())
    unknown_fields = sorted(key for key in data if key not in valid_fields)
    if unknown_fields and strict:
        raise ConfigError(f"Unknown config keys: {', '.join(unknown_fields)}")

    filtered = {
        key: value
        for key, value in data.items()
        if key in valid_fields and value is not None
    }
    _validate_types(filtered, strict=strict)
    return filtered


def _profile_data(config_data: dict, profile_name: str, *, strict: bool) -> dict:
    if profile_name == "default":
        return {}
    profiles = config_data.get("policy_profiles") or {}
    if profile_name not in profiles:
        if strict:
            raise ConfigError(f"Unknown policy profile: {profile_name}")
        return {}
    profile = profiles[profile_name]
    if not isinstance(profile, dict):
        if strict:
            raise ConfigError(f"Policy profile {profile_name} must be a mapping.")
        return {}
    return profile


def _merge_profile(config_data: dict, profile_data: dict, *, strict: bool) -> dict:
    valid_profile_fields = {
        "protected_paths",
        "auto_approve_paths",
        "ignore_dirs",
        "prompt_patterns",
        "model_parameters",
        "risk_thresholds",
        "trace_dir",
        "pty_mode",
        "override_ttl_seconds",
    }
    unknown_fields = sorted(key for key in profile_data if key not in valid_profile_fields)
    if unknown_fields and strict:
        raise ConfigError(f"Unknown policy profile keys: {', '.join(unknown_fields)}")

    profile_filtered = {
        key: value
        for key, value in profile_data.items()
        if key in valid_profile_fields and value is not None
    }
    _validate_types(profile_filtered, strict=strict)

    merged = dict(config_data)
    for key, value in profile_filtered.items():
        if key in {"model_parameters", "risk_thresholds"}:
            merged_value = deepcopy(DEFAULT_MODEL_PARAMETERS if key == "model_parameters" else DEFAULT_RISK_THRESHOLDS)
            current = merged.get(key)
            if isinstance(current, dict):
                merged_value.update(current)
            merged_value.update(value)
            merged[key] = merged_value
        else:
            merged[key] = value
    return merged


def _validate_types(data: dict, *, strict: bool) -> None:
    if not strict:
        return
    for key in LIST_FIELDS:
        if key in data and not _is_str_list(data[key]):
            raise ConfigError(f"{key} must be a list of strings.")
    for key in DICT_FIELDS:
        if key in data and not isinstance(data[key], dict):
            raise ConfigError(f"{key} must be a mapping.")
    for key in BOOL_FIELDS:
        if key in data and not isinstance(data[key], bool):
            raise ConfigError(f"{key} must be a boolean.")
    for key in INT_FIELDS:
        if key in data and not isinstance(data[key], int):
            raise ConfigError(f"{key} must be an integer.")
    for key in STRING_FIELDS:
        if key in data and not isinstance(data[key], str):
            raise ConfigError(f"{key} must be a string.")


def _normalize_paths(data: dict) -> dict:
    normalized = dict(data)
    for key in ["protected_paths", "auto_approve_paths"]:
        if key in normalized and isinstance(normalized[key], list):
            normalized[key] = [
                _expand_path_pattern(value) if isinstance(value, str) else value
                for value in normalized[key]
            ]
    for key in ["workspace_root", "trace_dir"]:
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = _expand_path_pattern(normalized[key])
    return normalized


def _expand_path_pattern(value: str) -> str:
    if value.startswith("~"):
        return str(Path(value).expanduser())
    return value


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
