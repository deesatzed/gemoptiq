from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MlxEnvironmentStatus:
    ok: bool
    mlx_lm_available: bool
    gemma4_unified_supported: bool
    message: str


def check_mlx_environment() -> MlxEnvironmentStatus:
    spec = importlib.util.find_spec("mlx_lm")
    if spec is None or not spec.submodule_search_locations:
        return MlxEnvironmentStatus(
            ok=False,
            mlx_lm_available=False,
            gemma4_unified_supported=False,
            message="mlx_lm is not importable in this environment.",
        )

    utils_path = Path(next(iter(spec.submodule_search_locations))) / "utils.py"
    if not utils_path.exists():
        return MlxEnvironmentStatus(
            ok=False,
            mlx_lm_available=True,
            gemma4_unified_supported=False,
            message="mlx_lm is installed, but mlx_lm/utils.py was not found.",
        )

    utils_text = utils_path.read_text(errors="replace")
    supported = re.search(
        r"['\"]gemma4_unified['\"]\s*:\s*['\"]gemma4['\"]",
        utils_text,
    ) is not None
    if not supported:
        return MlxEnvironmentStatus(
            ok=False,
            mlx_lm_available=True,
            gemma4_unified_supported=False,
            message="mlx_lm is importable, but gemma4_unified is not mapped to gemma4.",
        )

    return MlxEnvironmentStatus(
        ok=True,
        mlx_lm_available=True,
        gemma4_unified_supported=True,
        message="mlx_lm is importable and gemma4_unified maps to gemma4.",
    )
