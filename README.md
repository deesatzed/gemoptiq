# Cortex Sentinel

Cortex Sentinel is a local safety console for running autonomous coding agents.

In plain English: it is like a lab supervisor sitting next to a coding AI. The AI can still do useful work, but Cortex Sentinel watches what it is about to do, pauses risky actions, records what happened, and gives the human a chance to approve, block, or inspect the action.

It is built for local software development. It is not a cloud service, not a hard operating-system sandbox, and not a guarantee that a bad process can never touch a file. It is a practical guardrail and audit trail for high-autonomy coding workflows.

## What This App Is Used For

Use Cortex Sentinel when you want to run an AI coding tool, script, or agent but you do not want to trust it blindly.

Examples:

- Let an agent edit normal source files while blocking `.env`, SSH keys, and other secret-like files.
- Pause the agent before delete operations or ambiguous actions.
- See why a command was allowed, blocked, or sent for review.
- Keep a local JSONL audit trail of prompts, policy decisions, file effects, rollback events, user actions, and process lifecycle events.
- Run disposable smoke tests that prove the safety loop still works before using the app on real work.

## Why Someone Would Want It

Autonomous coding agents can move fast. That is useful, but risky. A tool that can edit files, run shell commands, call network tools, or deploy code can also make mistakes very quickly.

Cortex Sentinel helps with three practical problems:

- **Control:** it can suspend, resume, approve, block, or kill the supervised process.
- **Policy:** deterministic rules block known-dangerous actions such as secret-file access, external network calls, and production deploy attempts.
- **Evidence:** every important decision can be saved locally so a human can review what happened later.

For a college freshman analogy: imagine a self-driving car in a parking lot. Cortex Sentinel is not a concrete wall around the car. It is closer to a driving instructor with a brake pedal, a checklist, and a dashcam.

## What It Does

Cortex Sentinel can:

- launch an agent command from the terminal;
- detect confirmation prompts such as `[y/n]` or lines ending in `?`;
- watch workspace file changes;
- classify file and command effects into risk categories;
- auto-allow low-risk configured paths;
- block protected files and secret-like paths;
- block external network and production deploy command effects;
- require explicit confirmation for deletes;
- ask a local MLX/Gemma auditor for structured review on ambiguous actions;
- show pending approvals in a Textual terminal UI;
- queue multiple pending approvals instead of overwriting them;
- create temporary scoped allow overrides from the CLI, from a pending file effect, or from a manual TUI input modal;
- roll back protected files when a blocked created/modified/deleted protected effect can be safely repaired;
- write local trace files and replay them as JSON or text;
- report current readiness against `GOAL.md`.

## How It Works

At runtime, Cortex Sentinel sits between a human and an agent process.

1. **Runner starts the agent.** The app launches the command you pass to `sentinel run`.
2. **Prompt detector watches output.** If the agent asks for confirmation, the TUI starts a safety check.
3. **File observer checks effects.** The app compares workspace snapshots to see what files were created, modified, or deleted.
4. **Policy layer decides first.** Hard rules block protected paths, secrets, external network commands, and production deploys before any model judgment.
5. **Auditor handles ambiguity.** For review cases, a local MLX/Gemma auditor must return structured JSON. Free-text `YES` is not enough.
6. **Human approves or blocks.** Review and confirm outcomes wait for explicit user action.
7. **Enforcer watches continuously.** A background enforcer can detect no-prompt protected writes and suspend the runner.
8. **Trace store records evidence.** Decisions, file effects, user actions, rollback events, and process events are written to local JSONL traces.

## Quick Start

Install the package into the repo virtual environment:

```bash
venv/bin/python -m pip install -e .
```

Check the local MLX/Gemma environment:

```bash
venv/bin/sentinel check-env
```

Inspect the current proof matrix:

```bash
venv/bin/sentinel readiness --no-run
```

Run disposable local smokes:

```bash
venv/bin/python scripts/sentinel_smoke.py
venv/bin/python scripts/agent_integration_smoke.py
venv/bin/python scripts/enforcement_smoke.py
venv/bin/python scripts/trace_smoke.py
python scripts/e2e_smoke.py
python scripts/real_agent_smoke.py --dry-run
python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5
python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8
python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30
python scripts/readiness_check.py
```

Run a simple command under supervision:

```bash
venv/bin/sentinel run --config sentinel.yaml -- python -c "print('ready')"
```

Run a coding agent under supervision only in a disposable workspace until behavior is proven:

```bash
venv/bin/sentinel run --config sentinel.yaml -- claude .
```

Run with a temporary scoped path override:

```bash
venv/bin/sentinel run --config sentinel.yaml --allow-path "src/ui/**" -- python agent.py
```

In the TUI:

- `a` approves a pending action.
- `b` blocks a pending action.
- `o` creates an allow override from the current pending file effect.
- `m` opens a manual override input for an arbitrary glob such as `src/ui/**`.
- `v` lists active overrides.
- `x` clears overrides.
- `p` pauses or resumes the agent.
- `k` kills the agent.

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

The local Gemma auditor uses `mlx_lm` with `mlx-community/gemma-4-12B-it-OptiQ-4bit`. The repo virtual environment has been verified to contain the needed `gemma4_unified -> gemma4` mapping, but real model loading requires a macOS session with Metal access.

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

- `allow`: continue without model review when deterministic policy approves.
- `block`: suspend or refuse the action.
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
- Real Claude Code startup trust-prompt control is proven in a disposable workspace with `--claude-trust-smoke`. Real Codex non-interactive model/tool command execution is proven with `--codex-exec-smoke`. Full interactive Claude/Gemini/Codex tool-confirmation behavior is not yet proven.
- `scripts/real_agent_smoke.py` is opt-in and only as safe as the command you pass to it. Use disposable workspaces and avoid secrets.
- MCP-Cortex integration is trace-oriented in this app version. It records decisions; it does not proxy or authorize real MCP traffic.
- The real Gemma auditor smoke requires local Metal access.
- Do not pass secrets, credentials, PHI, private keys, or unnecessary sensitive data into prompts or traces.

## Testing Done And Current Results

The project has several layers of tests.

Unit and integration tests:

- `pytest -q`: last verified with `136 passed in 138.88s`.
- `python -m pytest -q` from `mcp-cortex/`: last verified with `11 passed in 0.52s`.

Smoke tests:

- `venv/bin/python scripts/sentinel_smoke.py`: verifies the repo venv can import `mlx_lm` and has the `gemma4_unified -> gemma4` mapping.
- `venv/bin/python scripts/auditor_smoke.py --dry-run`: verifies structured auditor output without loading the real model.
- `venv/bin/python scripts/agent_integration_smoke.py`: verifies PTY prompt detection, input injection, disposable file write, and process kill.
- `venv/bin/python scripts/enforcement_smoke.py`: verifies a no-prompt `.env` write is detected, the runner is suspended, rollback is performed, and the protected file is absent after rollback.
- `venv/bin/python scripts/trace_smoke.py`: verifies trace fields and stable digests.
- `python scripts/e2e_smoke.py`: verifies the aggregate local safety loop, including safe auto-approval, protected-path block, ambiguous auditor fallback, no-prompt protected write rollback, PTY prompt handling, trace export, and config profile behavior.
- `python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5`: verifies safe non-interactive version probes for Codex, Claude Code, and Gemini. This does not prove interactive agent behavior.
- `python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8`: verifies Sentinel can launch Claude Code in a disposable workspace, detect Claude's own startup trust prompt, inject the safe `No, exit` response, and kill the process. This proves startup prompt/control only; it does not prove model/tool confirmation behavior.
- `python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30`: verifies Codex can run a harmless shell `command_execution` in an ephemeral temp workspace and produce `SENTINEL_CODEX_OK`. This proves real model/tool command execution, not interactive prompt control. In this managed session, it needs local app-server access outside the restricted sandbox.
- `python scripts/real_agent_smoke.py --interaction "REGEX=>INPUT" ...`: supports scripted multi-prompt disposable flows, such as startup trust followed by a tool confirmation. The harness now rejects expected-output matches that already appeared before the final response, so echoed prompts cannot count as successful tool output.

Readiness matrix:

- `python scripts/readiness_check.py`: default local mode is `partial`, with `10 pass`, `5 manual`, `1 external_blocked`, and `0 fail`. Optional real-agent smokes remain manual unless explicitly requested.
- `python scripts/readiness_check.py --run-claude-trust-smoke --run-codex-exec-smoke`: last verified as `partial`, with `12 pass`, `3 manual`, `1 external_blocked`, and `0 fail` when Codex exec has local app-server access.
- The remaining external block is the real MLX/Gemma auditor smoke in this managed session because Metal is unavailable.
- The remaining real-agent manual item is a full interactive tool-confirmation command in a disposable workspace. Claude Code startup trust, Codex non-interactive model/tool execution, and synthetic multi-prompt flows are now proven. A real Claude Code tool attempt trusted the temp workspace and typed the harmless prompt, but it did not reach a tool permission prompt before timeout. Gemini prompted for browser authentication in this session.

Release checks:

- `python scripts/release_check.py --skip-wheel` verifies package metadata, README sections, and the console script.
- `python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check` has built a local wheel: `cortex_sentinel-0.1.0-py3-none-any.whl`.

## Drift From The Initial Plan

The initial direction was to make the local Gemma auditor and basic agent supervision work. The project grew into a broader local safety console.

Useful drift:

- Added deterministic policy before relying on model judgment.
- Added continuous protected-file enforcement and rollback.
- Added persistent trace storage and trace replay.
- Added package metadata, a `sentinel` CLI, and a readiness matrix.
- Added a guarded real-agent harness and safe CLI metadata probes.
- Added a bounded Claude Code trust-prompt smoke for real PTY startup/control evidence.
- Added scripted multi-prompt interactions to the real-agent harness for startup-plus-tool-confirmation-shaped flows.
- Added a bounded Codex exec smoke for real non-interactive model/tool command execution evidence.
- Added a richer TUI approval flow, approval queue, dedicated panel, and manual override input.

Unresolved drift:

- The plan expected real Gemma auditor verification, but this execution session has no Metal device. Dry-run auditor checks pass, but real model load is still externally blocked here.
- The plan expected real local agent validation. PTY fixtures, CLI version probes, a bounded Claude Code startup trust prompt, synthetic multi-prompt flows, and Codex non-interactive model/tool execution pass, but a deliberately safe real interactive Claude/Gemini/Codex tool-confirmation run is still not complete.
- MCP-Cortex is used as trace-oriented metadata support, not as a full MCP authorization proxy.

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

Run with a temporary scoped override:

```bash
sentinel run --config sentinel.yaml --allow-path "docs/drafts/**" -- python agent.py
```

Replay a trace:

```bash
sentinel trace replay .sentinel/traces/session-example.jsonl
sentinel trace replay --format text .sentinel/traces/session-example.jsonl
```

Run the structured auditor dry run:

```bash
venv/bin/python scripts/auditor_smoke.py --dry-run
```

Run the real auditor smoke when Metal is available:

```bash
venv/bin/python scripts/auditor_smoke.py
```

Run the guarded real-agent smoke only with an explicit disposable command:

```bash
python scripts/real_agent_smoke.py --dry-run
python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5
python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8
python scripts/real_agent_smoke.py --codex-exec-smoke --timeout 30
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
git diff --check
```

`scripts/readiness_check.py` emits a JSON proof matrix for the `GOAL.md` checks. It runs local disposable smokes and safe non-interactive agent CLI metadata probes by default, leaves full test suites and full real interactive agent commands as manual evidence, and marks the real auditor smoke as externally blocked unless `--run-real-auditor` is provided in a Metal-capable session. Add `--run-claude-trust-smoke` to run the bounded Claude Code startup trust-prompt smoke in a disposable workspace. Add `--run-codex-exec-smoke` to run the bounded Codex exec model/tool smoke in an ephemeral temp workspace.

Use `--include-tests` when you want the readiness report to run the root and MCP-Cortex pytest suites as part of the matrix. In managed/sandboxed sessions, nested subprocess calls inside the root suite may be reported as externally blocked; run `pytest -q` directly for authoritative root-suite evidence.

Run the release metadata and wheel check:

```bash
python scripts/release_check.py --skip-wheel
python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check
```
