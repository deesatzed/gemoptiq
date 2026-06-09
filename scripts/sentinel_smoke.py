#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.env_check import check_mlx_environment
from sentinel.runner import AgentRunner


def main() -> int:
    env_status = check_mlx_environment()
    print(f"mlx_lm: {env_status.message}")

    runner = AgentRunner(
        "python3 -c \"import sys; print('sentinel-smoke-ready', flush=True); "
        "line=sys.stdin.readline().strip(); print(f'sentinel-smoke-input:{line}', flush=True)\""
    )
    runner.start()
    try:
        output = wait_for_output(runner)
        if "sentinel-smoke-ready" not in output:
            print(f"unexpected initial output: {output!r}", file=sys.stderr)
            return 1

        runner.write_input("ok\n")
        response = wait_for_output(runner)
        if "sentinel-smoke-input:ok" not in response:
            print(f"unexpected input response: {response!r}", file=sys.stderr)
            return 1
    finally:
        runner.kill()

    print("runner: ok")
    return 0


def wait_for_output(runner: AgentRunner, timeout_seconds: float = 5.0) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        output = runner.get_output()
        if output:
            return output
        time.sleep(0.05)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
