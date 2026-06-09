#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path


REQUIRED_README_SECTIONS = [
    "## Quick Start",
    "## Installation",
    "## Configuration Reference",
    "## Safety Boundary",
    "## Troubleshooting",
    "## Examples",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Cortex Sentinel release checks.")
    parser.add_argument(
        "--skip-wheel",
        action="store_true",
        help="Validate metadata/docs without building a wheel.",
    )
    parser.add_argument(
        "--wheel-dir",
        default="dist",
        help="Directory where pip wheel should place release artifacts.",
    )
    args = parser.parse_args(argv)

    report = build_report(
        build_wheel=not args.skip_wheel,
        wheel_dir=Path(args.wheel_dir),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


def build_report(*, build_wheel: bool, wheel_dir: Path) -> dict:
    pyproject = load_pyproject()
    project = pyproject.get("project", {})
    scripts = project.get("scripts", {})
    readme_report = inspect_readme()

    report = {
        "status": "ok",
        "project": {
            "name": project.get("name"),
            "version": project.get("version"),
            "requires_python": project.get("requires-python"),
        },
        "console_script": scripts.get("sentinel"),
        "readme": readme_report,
        "wheel": {
            "built": False,
            "files": [],
        },
    }

    required_ok = (
        report["project"]["name"] == "cortex-sentinel"
        and bool(report["project"]["version"])
        and report["console_script"] == "sentinel.main:main"
        and readme_report["required_sections_present"]
    )
    if not required_ok:
        report["status"] = "error"
        return report

    if build_wheel:
        wheel_report = build_wheel_artifact(wheel_dir)
        report["wheel"] = wheel_report
        if not wheel_report["built"]:
            report["status"] = "error"

    return report


def load_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def inspect_readme() -> dict:
    readme = Path("README.md").read_text()
    missing = [section for section in REQUIRED_README_SECTIONS if section not in readme]
    return {
        "required_sections_present": not missing,
        "missing_sections": missing,
    }


def build_wheel_artifact(wheel_dir: Path) -> dict:
    wheel_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            ".",
            "--wheel-dir",
            str(wheel_dir),
        ],
        capture_output=True,
        text=True,
    )
    files = sorted(path.name for path in wheel_dir.glob("*.whl"))
    return {
        "built": result.returncode == 0 and bool(files),
        "files": files,
        "returncode": result.returncode,
        "stderr": result.stderr[-2000:],
    }


if __name__ == "__main__":
    raise SystemExit(main())
