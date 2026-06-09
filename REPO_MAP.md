# REPO_MAP.md

## Project Type

Top-level project is Cortex Sentinel: a local Python sidecar/TUI that launches and supervises an autonomous coding agent process, detects confirmation prompts, asks a local Gemma 4 MLX auditor for a YES/NO risk verdict, and can auto-approve, suspend, resume, or kill the child process.

The `mcp-cortex/` directory is a nested Git repository and separate Python package. It is an alpha MCP policy/capability/context/trace reference harness that Cortex Sentinel documentation treats as a future deterministic policy layer.

## Tech Stack

- Python 3.13 observed in the active environment.
- Top-level Sentinel modules under `src/sentinel/`.
- `textual` TUI widgets.
- `mlx_lm` local model inference for `mlx-community/gemma-4-12B-it-OptiQ-4bit`.
- `yaml` config loading from `sentinel.yaml`.
- `subprocess`, process groups, and POSIX signals for agent lifecycle control.
- Nested `mcp-cortex` package supports Python >=3.10 and has no runtime dependencies; dev dependencies are `pytest` and `jsonschema`.

## Package Manager

Top-level Sentinel now uses `pyproject.toml` with setuptools and exposes a `sentinel` console script. The repo venv has been verified with `venv/bin/python -m pip install -e .`.

Nested `mcp-cortex/` uses its own `pyproject.toml` with setuptools.

## Commands

| Purpose | Command | Verified |
|---|---|---|
| Sentinel tests | `pytest -q` | Yes: `136 passed in 138.49s` |
| MCP-Cortex full tests | `python -m pytest -q` from `mcp-cortex/` | Yes: `11 passed in 0.52s` |
| Editable install | `venv/bin/python -m pip install -e .` | Yes |
| Sentinel CLI help | `venv/bin/sentinel --help` | Yes |
| Sentinel run help | `venv/bin/sentinel run --help` | Yes |
| Sentinel env check | `venv/bin/sentinel check-env` | Yes: `mlx_lm is importable and gemma4_unified maps to gemma4` |
| Sentinel readiness static matrix | `venv/bin/sentinel readiness --no-run` | Yes: `partial`, static/manual matrix |
| Sentinel trace replay JSON | `venv/bin/sentinel trace replay .sentinel/cli-test-traces/cli-smoke.jsonl` | Yes |
| Sentinel trace replay text | `venv/bin/sentinel trace replay --format text .sentinel/cli-test-traces/cli-smoke.jsonl` | Yes |
| Aggregate E2E smoke | `python scripts/e2e_smoke.py` | Yes: status ok with all scenario booleans true |
| Real-agent smoke harness dry run | `python scripts/real_agent_smoke.py --dry-run` | Yes: guarded dry-run report |
| Real-agent CLI metadata probe | `python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5` | Yes: Codex, Claude Code, and Gemini version probes pass; not interactive proof |
| Readiness proof matrix | `python scripts/readiness_check.py` | Yes: `10 pass`, `5 manual`, `1 external_blocked` |
| Readiness proof matrix with tests | `python scripts/readiness_check.py --include-tests` | Partial: `10 pass`, `1 manual`, `2 external_blocked` in this managed session because nested root-suite subprocess calls are denied |
| Release check dry run | `python scripts/release_check.py --skip-wheel` | Yes |
| Release wheel check | `python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check` | Yes: builds `cortex_sentinel-0.1.0-py3-none-any.whl` |
| MCP-Cortex example schema validation | `PYTHONPATH=src python scripts/validate_examples.py` from `mcp-cortex/` | Yes |
| MCP-Cortex CLI help | `PYTHONPATH=src python -m mcp_cortex.cli --help` from `mcp-cortex/` | Yes |
| MCP-Cortex demo script | `PYTHONPATH=src python examples/demo_policy_gate.py` from `mcp-cortex/` | Yes |
| Sentinel smoke, repo venv | `venv/bin/python scripts/sentinel_smoke.py` | Yes: runner OK; MLX mapping check reports `gemma4_unified` maps to `gemma4` |
| Sentinel smoke, shell Python | `python scripts/sentinel_smoke.py` | Yes: runner OK; shell MLX mapping check reports `gemma4_unified` is not mapped |

## Entry Points

- `pyproject.toml`: top-level package metadata and `sentinel` console script.
- `README.md`: user-facing quick start, install, config, safety, troubleshooting, and examples.
- `src/sentinel/main.py`: CLI entrypoint with `run`, `check-env`, `readiness`, and `trace replay` subcommands, including repeated `run --allow-path` startup overrides.
- `src/sentinel/readiness.py`: packaged GOAL.md proof matrix reporter used by both `sentinel readiness` and `scripts/readiness_check.py`.
- `src/sentinel/tui.py`: TUI orchestration, startup safety and MCP-Cortex trace-only boundary disclosures, prompt detection, prompt-time command-effect inference, structured JSON/Bash command extraction, audit call, deterministic auto-approve/block behavior, structured pending approval context, FIFO pending-approval queue, dedicated approval panel lifecycle, explicit approve/block actions, CLI startup override seeding, pending/manual session override creation including a Textual manual input modal, override list/clear actions, and suspend/resume/kill controls.
- `src/sentinel/runner.py`: child process runner, stdout reader, stdin writer, process-group suspend/resume/kill.
- `src/sentinel/auditor.py`: MLX model load and prompt/effect audit.
- `src/sentinel/config.py`: YAML config loader with defaults, strict validation, policy profiles, workspace root, ignore dirs, prompt patterns, model parameters, risk thresholds, trace path, PTY mode, and override TTL.
- `src/sentinel/policy.py`: deterministic policy layer with protected-path checks, auto-approve paths, file/command effect classification, stable effect IDs, risk classes, configured thresholds, scoped session overrides, and allow/block/review/confirm outcomes.
- `src/sentinel/effects.py`: lightweight workspace snapshot/diff observer for created, modified, and deleted file effects, plus safe workspace-relative content snapshots for protected-path rollback.
- `src/sentinel/enforcer.py`: continuous polling enforcement, runner suspension on policy block, and rollback for blocked protected-path or built-in secret-path file effects when an in-memory baseline is available.
- `src/sentinel/session_trace.py`: local JSONL session traces with stable digests, including enforcement rollback metadata without file contents.
- `src/sentinel/trace_replay.py`: summary and text replay helpers for trace artifacts, including rollback result summaries.
- `src/sentinel/cortex_bridge.py`: optional MCP-Cortex trace/policy bridge when the nested package is present.
- `src/sentinel/env_check.py`: non-invasive MLX/Gemma environment check.
- `scripts/release_check.py`: local release metadata, README, console script, and wheel-build verifier.
- `scripts/readiness_check.py`: thin repo wrapper around the packaged readiness reporter.
- `scripts/e2e_smoke.py`: disposable aggregate E2E smoke for policy, PTY, enforcement, trace, and config-profile scenarios.
- `scripts/real_agent_smoke.py`: guarded opt-in disposable real-agent command harness plus safe non-interactive installed-agent CLI metadata probes.
- `mcp-cortex/src/mcp_cortex/cli.py`: nested package CLI.
- `mcp-cortex/examples/demo_policy_gate.py`: deterministic MCP-Cortex demo.

## Major Folders

- `src/sentinel/`: top-level Sentinel implementation.
- `tests/`: top-level Sentinel tests.
- `docs/plans/`: Sentinel design document.
- `mcp-cortex/`: nested Git repo for MCP-Cortex alpha package.
- `mcp-cortex/src/mcp_cortex/`: MCP-Cortex implementation.
- `mcp-cortex/tests/`: MCP-Cortex tests.
- `mcp-cortex/docs/`: MCP-Cortex architecture, security, roadmap, and specification docs.
- `mcp-cortex/schemas/`: JSON Schemas for MCP-Cortex objects.
- `mcp-cortex/examples/`: JSON examples and demo script.

## Existing Patterns To Preserve

- Conservative default-to-block behavior when the auditor/model cannot produce a clear YES verdict.
- Process-group based lifecycle control for the supervised agent.
- Short dataclass-style configuration model.
- MCP-Cortex documentation consistently labels the nested package as alpha, not production authorization infrastructure.
- Nested repo boundary: do not treat `mcp-cortex/` as ordinary top-level files when committing from the parent repo.

## Tests and Verification

Top-level Sentinel tests cover runner lifecycle, auditor parsing/error handling, config defaults/validation/profiles, CLI commands and startup overrides, README coverage, release checks, aggregate local E2E smoke, guarded real-agent smoke harness behavior including non-interactive probe reporting, basic TUI controls, pending approval context/panel/actions/queueing, mounted Textual approval-panel inspection, pending/manual TUI override controls including mounted manual modal submit/cancel/empty-input behavior, TUI config wiring, prompt-time command-effect inference, structured command extraction, runtime safety warning and MCP-Cortex trace-only disclosure, deterministic policy decisions, richer file/command effect classification, threshold-driven decisions, scoped session overrides, trace risk/effect-id/source persistence, human-readable trace replay, file-effect observation, optional MCP-Cortex bridging, and MLX environment checks.

MCP-Cortex full tests now pass after making local `examples/` importable.

## Likely Files For Current Task

- `REPO_MAP.md`
- `RISK_NOTES.md`
- `CORTEX_SENTINEL_DSS_WBV_HANDOFF.md`
- `docs/plans/2026-06-08-cortex-sentinel-design.md`
- `src/sentinel/tui.py`
- `src/sentinel/runner.py`
- `src/sentinel/auditor.py`
- `src/sentinel/config.py`
- `src/sentinel/policy.py`
- `src/sentinel/effects.py`
- `src/sentinel/cortex_bridge.py`
- `src/sentinel/env_check.py`
- `scripts/sentinel_smoke.py`
- `sentinel.yaml`
- `mcp-cortex/README.md`
- `mcp-cortex/CODEX_HANDOFF.md`
- `mcp-cortex/docs/ROADMAP.md`

## Unknowns

- The repo venv check reports `mlx_lm` is importable and `gemma4_unified` maps to `gemma4`; the shell/miniforge Python does not have that mapping.
- Whether the real Gemma 4 model loads and responds with acceptable latency on this machine.
- Whether Sentinel can reliably interact with Claude Code, Gemini CLI, or other real agent TUIs rather than line-buffered dummy subprocesses, including their exact tool-call output formats.
- Whether `mcp-cortex` is intended to stay as a nested Git repo or be vendored/submoduled/packaged as a dependency.
- Whether release packaging should include wheel publishing, signed artifacts, or a stricter versioning policy.
