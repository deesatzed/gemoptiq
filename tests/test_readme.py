from pathlib import Path


def test_readme_contains_user_facing_required_sections():
    readme = Path("README.md").read_text()

    required_headings = [
        "## Quick Start",
        "## Installation",
        "## Configuration Reference",
        "## Safety Boundary",
        "## Troubleshooting",
        "## Examples",
    ]
    for heading in required_headings:
        assert heading in readme

    required_commands = [
        "pip install -e .",
        "sentinel check-env",
        "sentinel run --config sentinel.yaml --",
        "sentinel run --config sentinel.yaml --allow-path",
        "sentinel readiness",
        "sentinel trace replay",
        "scripts/auditor_smoke.py",
        "scripts/e2e_smoke.py",
        "scripts/real_agent_smoke.py",
    ]
    for command in required_commands:
        assert command in readme
