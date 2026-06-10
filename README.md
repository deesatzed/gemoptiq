# Cortex Sentinel

Local safety console for autonomous coding agents.

**Cortex Sentinel lets you run tools like Codex, Claude Code, Gemini, or scripted agents with a brake pedal, a policy gate, rollback evidence, and a replayable audit trail.**

It is the public-facing app in this repo. It is not a hard operating-system sandbox and it does not promise that unsafe software can never touch a file. It is a practical supervision layer for local development: watch the agent, stop risky actions, ask the human before ambiguous actions, and keep evidence of what happened.

## Showpiece

- Landing page: [docs/index.html](docs/index.html)
- Showpiece brief: [docs/showpiece/cortex-sentinel.md](docs/showpiece/cortex-sentinel.md)
- Gap analysis and proof contract: [GOAL.md](GOAL.md)

The landing page is intentionally built around the real product story: a local agent asks to act, Sentinel classifies the effect, protected paths are blocked, review actions wait for a human, and trace replay proves the session later.

## Why This Exists

Coding agents are useful because they can inspect a repo, edit files, run commands, and iterate quickly. That is also why they are risky. A fast agent can delete a file, touch secrets, run a network command, or drift away from the task before a human notices.

Cortex Sentinel is for developers who want the productivity of local coding agents without treating the agent as fully trusted infrastructure.

In college-freshman terms: imagine a student lab where a robot can solder, cut, and test parts. Cortex Sentinel is the lab supervisor. It does not make the tools harmless, but it can pause the robot, enforce rules, ask for permission, write down what happened, and help restore damage in known protected areas.

## What It Does

1. Launches a local command or coding agent through `sentinel run`.
2. Watches output for confirmation prompts and risky command text.
3. Detects file effects in the workspace.
4. Applies deterministic policy before any model judgment.
5. Blocks protected files, secret-like paths, external network commands, and production deploy effects.
6. Sends ambiguous actions to a local MLX/Gemma auditor when configured.
7. Shows pending decisions in a terminal UI with approve, block, pause, kill, and override controls.
8. Records JSONL traces with policy decisions, file effects, user actions, rollback events, process lifecycle events, and stable digests.
9. Replays traces as JSON or text so the session can be inspected later.

## What Is Proven

Current evidence from this repo:

- Root test suite has passed with `142 passed`.
- Nested `mcp-cortex` suite has passed with `11 passed`.
- A fresh independent clone from GitHub passed after the optional MCP-Cortex dependency path was fixed: `140 passed, 2 skipped`.
- The MLX/Gemma auditor smoke has loaded `mlx-community/gemma-4-12B-it-OptiQ-4bit` and returned structured `allow` / `green` output in a Metal-capable local session.
- Codex full-screen TUI smoke has been proven through workspace trust, command approval, and harmless output `SENTINEL_CODEX_TUI_OK`.
- Claude Code startup trust-prompt control has been proven in a disposable workspace.
- Continuous protected-file enforcement is proven with a no-prompt `.env` write that suspends the runner and rolls back the created protected file.

What is still open:

- Full interactive Claude/Gemini tool-confirmation flows are not yet proven end to end.
- Default readiness leaves the real Gemma auditor external-blocked unless a Metal-capable session opts in.
- MCP-Cortex is trace-oriented in this version. It records decisions; it does not proxy or authorize real MCP traffic.
- Sentinel supervises and reacts. It is not a kernel sandbox, container boundary, or formal security product.

## Quick Start

Install into a local Python environment:

```bash
pip install -e .
```

If you are using this repo's virtual environment:

```bash
venv/bin/python -m pip install -e .
```

Check the local MLX/Gemma environment:

```bash
sentinel check-env
```

Inspect the current proof matrix:

```bash
sentinel readiness --no-run
python scripts/readiness_check.py
```

Run a simple command under supervision:

```bash
sentinel run --config sentinel.yaml -- python -c "print('ready')"
```

Run with a temporary scoped path override:

```bash
sentinel run --config sentinel.yaml --allow-path "src/ui/**" -- python agent.py
```

Replay a saved trace:

```bash
sentinel trace replay .sentinel/traces/<session>.jsonl
sentinel trace replay --format text .sentinel/traces/<session>.jsonl
```

## Installation

From the repository root:

```bash
python -m pip install -e .
```

This installs the `sentinel` console script:

```bash
sentinel --help
sentinel check-env
sentinel run --config sentinel.yaml -- python agent.py
sentinel run --config sentinel.yaml --allow-path "src/ui/**" -- python agent.py
sentinel readiness --no-run
sentinel trace replay .sentinel/traces/<session>.jsonl
sentinel trace replay --format text .sentinel/traces/<session>.jsonl
```

The local Gemma auditor uses `mlx_lm` with:

```text
mlx-community/gemma-4-12B-it-OptiQ-4bit
```

The repo virtual environment has been verified to contain the needed `gemma4_unified -> gemma4` mapping. The real auditor smoke requires macOS Metal access.

## Configuration Reference

Default config file: `sentinel.yaml`.

```yaml
workspace_root: .
protected_paths:
  - "**/.env"
  - "~/.ssh/**"
auto_approve_paths:
  - "docs/**"
model_id: "mlx-community/gemma-4-12B-it-OptiQ-4bit"
ignore_dirs:
  - ".git"
  - "__pycache__"
  - ".sentinel"
prompt_patterns:
  - "\\?\\s*$"
  - "\\[y/n\\]"
trace_dir: ".sentinel/traces"
pty_mode: false
override_ttl_seconds: 900
model_parameters:
  max_tokens: 96
  temperature: 0.0
risk_thresholds:
  read:secret: block
  write:secret: block
  delete:workspace: confirm
  execute:shell: review
  network:external: block
  deploy:production: block
policy_profile: default
policy_profiles:
  locked:
    protected_paths:
      - "**/.env"
      - "~/.ssh/**"
    auto_approve_paths:
      - "docs/public/**"
```

Policy outcomes:

- `allow`: continue when deterministic policy approves.
- `block`: refuse or suspend the risky action.
- `review`: ask the auditor, then wait for explicit user approval.
- `confirm`: wait for explicit user approval without using the auditor.

Temporary overrides:

- `sentinel run --allow-path "src/ui/**" -- ...` creates a trace-visible allow override for the current session.
- Repeating `--allow-path` adds multiple patterns.
- Pressing `m` in the TUI opens a manual override input.
- Overrides cannot bypass hard blocks for protected paths, secret-like paths, external network effects, or production deploy effects.
- Overrides expire according to `override_ttl_seconds`.

## Safety Boundary

Cortex Sentinel separates deterministic policy from LLM judgment. Protected paths, secret-like paths, external network effects, and production deploy effects are hard policy decisions. They do not rely on the auditor.

Important limitations:

- Continuous enforcement is polling-based. It detects, suspends, and can roll back protected-path effects after they appear; it is not pre-write OS sandboxing.
- Real Claude Code startup trust-prompt control is proven. Real Codex non-interactive model/tool command execution is proven. Real Codex full-screen TUI workspace trust and command approval are proven. Full interactive Claude/Gemini tool-confirmation behavior is not yet proven.
- The PTY runner answers basic terminal queries and starts children with a usable default 24x80 window size. It is still not a complete terminal emulator.
- `scripts/real_agent_smoke.py` is opt-in and only as safe as the command you pass to it. Use disposable workspaces and avoid secrets.
- MCP-Cortex integration is trace-oriented in this app version. It records decisions; it does not proxy or authorize real MCP traffic.
- Do not pass secrets, credentials, PHI, private keys, or unnecessary sensitive data into prompts or traces.

## How It Works

At runtime, Cortex Sentinel sits between the human and the agent process.

1. **Runner starts the agent.** The app launches the command passed to `sentinel run`.
2. **Prompt detector watches output.** If the agent asks for confirmation, the TUI starts a safety check.
3. **File observer checks effects.** The app compares workspace snapshots to see what files were created, modified, or deleted.
4. **Policy layer decides first.** Hard rules block protected paths, secrets, external network commands, and production deploys.
5. **Auditor handles ambiguity.** For review cases, a local MLX/Gemma auditor must return structured JSON. Free-text `YES` is not enough.
6. **Human approves or blocks.** Review and confirm outcomes wait for explicit user action.
7. **Enforcer watches continuously.** A background enforcer can detect no-prompt protected writes and suspend the runner.
8. **Trace store records evidence.** Decisions, file effects, user actions, rollback events, and process events are written to local JSONL traces.

## Testing Done

Unit and integration tests:

```bash
pytest -q
(cd mcp-cortex && python -m pytest -q)
```

Disposable local smokes:

```bash
venv/bin/python scripts/sentinel_smoke.py
venv/bin/python scripts/agent_integration_smoke.py
venv/bin/python scripts/enforcement_smoke.py
venv/bin/python scripts/trace_smoke.py
python scripts/e2e_smoke.py
```

Auditor and real-agent smokes:

```bash
venv/bin/python scripts/auditor_smoke.py --dry-run
venv/bin/python scripts/auditor_smoke.py
python scripts/real_agent_smoke.py --dry-run
python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5
python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8
python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30
python scripts/real_agent_smoke.py --codex-tui-smoke --timeout 60
```

Readiness and release checks:

```bash
sentinel readiness --no-run
python scripts/readiness_check.py
python scripts/release_check.py --skip-wheel
python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check
git diff --check
```

`scripts/readiness_check.py` emits a JSON proof matrix for [GOAL.md](GOAL.md). By default it runs local disposable smokes and safe non-interactive agent metadata probes, leaves full test suites and remaining real interactive agent commands as manual evidence, and marks the real auditor smoke externally blocked unless `--run-real-auditor` is provided in a Metal-capable session.

## Drift From The Initial Plan

The initial plan was to make the local Gemma auditor and basic agent supervision work. The project grew into a broader local safety console.

Useful drift:

- Added deterministic policy before relying on model judgment.
- Added continuous protected-file enforcement and rollback.
- Added persistent trace storage and trace replay.
- Added package metadata, a `sentinel` CLI, and a readiness matrix.
- Added a guarded real-agent harness and safe CLI metadata probes.
- Added bounded Claude Code and Codex smokes for real local interaction evidence.
- Added a richer TUI approval flow, approval queue, dedicated panel, and manual override input.

Unresolved drift:

- Real Gemma verification is proven in Metal-capable local runs but remains opt-in in default readiness.
- Full interactive Claude/Gemini tool-confirmation runs are still not complete.
- MCP-Cortex is trace-oriented metadata support, not a full MCP authorization proxy.

## Troubleshooting

Check the environment:

```bash
sentinel check-env
```

If `scripts/auditor_smoke.py` fails with `No Metal device available`, rerun it from a local macOS terminal/session that has GPU/Metal access:

```bash
venv/bin/python scripts/auditor_smoke.py
```

If editable install tries to download dependencies, make sure the environment can reach PyPI or install in an environment where `setuptools`, `PyYAML`, and `textual` are already available.

If no prompts are detected, tune `prompt_patterns` in `sentinel.yaml`.

If trace replay reports invalid digests, treat the trace as modified and do not rely on it as audit evidence.

Trace replay includes enforcement rollback metadata when a protected file effect is rolled back. Rollback events record paths, operations, and rollback result names; they do not store protected file contents.

## Examples

Run a simple command under supervision:

```bash
sentinel run --config sentinel.yaml -- python -c "print('ready')"
```

Run a coding agent under supervision only in a disposable workspace until behavior is proven:

```bash
sentinel run --config sentinel.yaml -- claude .
```

Run with a temporary scoped override:

```bash
sentinel run --config sentinel.yaml --allow-path "docs/drafts/**" -- python agent.py
```

Replay a trace:

```bash
sentinel trace replay .sentinel/traces/session-example.jsonl
sentinel trace replay --format text .sentinel/traces/session-example.jsonl
```

Run the guarded real-agent smoke only with an explicit disposable command:

```bash
python scripts/real_agent_smoke.py --dry-run
python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5
python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8
python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30
python scripts/real_agent_smoke.py --codex-tui-smoke --timeout 60
python scripts/real_agent_smoke.py --agent-command "claude ." --approval-input n
python scripts/real_agent_smoke.py \
  --agent-command "python fixture_agent.py" \
  --interaction "Trust workspace.*\\?=>y" \
  --interaction "Run safe tool.*\\?=>n" \
  --expect-output "answers:y,n"
```

Run the local verification set:

```bash
sentinel readiness --no-run
python scripts/readiness_check.py
pytest -q
(cd mcp-cortex && python -m pytest -q)
venv/bin/python scripts/sentinel_smoke.py
venv/bin/python scripts/agent_integration_smoke.py
venv/bin/python scripts/enforcement_smoke.py
venv/bin/python scripts/trace_smoke.py
python scripts/e2e_smoke.py
python scripts/real_agent_smoke.py --dry-run
python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5
python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8
python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30
python scripts/real_agent_smoke.py --codex-tui-smoke --timeout 60
git diff --check
```

Run the release metadata and wheel check:

```bash
python scripts/release_check.py --skip-wheel
python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check
```
