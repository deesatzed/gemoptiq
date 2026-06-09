from __future__ import annotations

import argparse
import json
import sys

from sentinel.env_check import check_mlx_environment
from sentinel.readiness import add_readiness_arguments, run_readiness
from sentinel.trace_replay import render_trace_text, summarize_trace
from sentinel.tui import SentinelTUI


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_name == "run":
        return run_agent(args)
    if args.command_name == "check-env":
        return check_env()
    if args.command_name == "readiness":
        return run_readiness(args)
    if args.command_name == "trace" and args.trace_command == "replay":
        return replay_trace(args.trace_path, output_format=args.output_format)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="Cortex Sentinel local supervision console.",
    )
    subparsers = parser.add_subparsers(dest="command_name")

    run_parser = subparsers.add_parser("run", help="Run an agent under Sentinel supervision.")
    run_parser.add_argument(
        "--config",
        default="sentinel.yaml",
        help="Path to Sentinel YAML config.",
    )
    run_parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        dest="allow_paths",
        help="Temporarily allow writes matching a path/glob pattern for this session.",
    )
    run_parser.add_argument(
        "agent_command",
        nargs=argparse.REMAINDER,
        help="Agent command after --, for example: -- claude .",
    )

    subparsers.add_parser("check-env", help="Check local MLX/Gemma environment.")

    readiness_parser = subparsers.add_parser(
        "readiness",
        help="Report GOAL.md readiness proof matrix.",
    )
    add_readiness_arguments(readiness_parser)

    trace_parser = subparsers.add_parser("trace", help="Inspect Sentinel trace artifacts.")
    trace_subparsers = trace_parser.add_subparsers(dest="trace_command")
    replay_parser = trace_subparsers.add_parser("replay", help="Summarize a JSONL trace.")
    replay_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        dest="output_format",
        help="Replay output format.",
    )
    replay_parser.add_argument("trace_path", help="Path to a Sentinel JSONL trace file.")

    return parser


def run_agent(args: argparse.Namespace) -> int:
    command_parts = list(args.agent_command)
    if command_parts and command_parts[0] == "--":
        command_parts = command_parts[1:]
    if not command_parts:
        print("sentinel run requires an agent command after --.", file=sys.stderr)
        return 2

    app = SentinelTUI(
        " ".join(command_parts),
        args.config,
        initial_allow_overrides=args.allow_paths,
    )
    app.run()
    return 0


def check_env() -> int:
    status = check_mlx_environment()
    print(status.message)
    return 0 if status.ok else 1


def replay_trace(trace_path: str, *, output_format: str = "json") -> int:
    summary = summarize_trace(trace_path)
    if output_format == "text":
        print(render_trace_text(summary), end="")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
