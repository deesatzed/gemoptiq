#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.trace_replay import render_trace_text, summarize_trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Cortex Sentinel trace summary.")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        dest="output_format",
        help="Replay output format.",
    )
    parser.add_argument("trace_path", help="Path to a Sentinel JSONL trace file.")
    args = parser.parse_args(argv)

    summary = summarize_trace(args.trace_path)
    if args.output_format == "text":
        print(render_trace_text(summary), end="")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
