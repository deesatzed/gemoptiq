# GOAL.md

## Current Truth Snapshot

Cortex Sentinel is currently a test-passing local supervision MVP for autonomous coding-agent commands.

Verified working:

- `pytest -q` from `/Volumes/WS4TB/gemOptq` passes with `134 passed`.
- `python -m pytest -q` from `mcp-cortex/` passes with `11 passed`.
- `venv/bin/python scripts/sentinel_smoke.py` passes and confirms the repo venv has `gemma4_unified -> gemma4`.
- `python scripts/readiness_check.py` and `sentinel readiness` run the local disposable proof matrix. Default local smoke mode leaves the optional Claude trust-prompt smoke manual; `python scripts/readiness_check.py --run-claude-trust-smoke` currently reports `11 pass`, `3 manual`, and `1 external_blocked`.
- `python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5` passes and confirms safe non-interactive version probes for installed Codex, Claude Code, and Gemini CLIs. This does not prove interactive prompt/control behavior.
- `python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8` passes and confirms Sentinel can launch Claude Code in a disposable workspace, detect Claude Code's own startup trust prompt, inject the safe `No, exit` response, and kill the process.
- Sentinel can launch a child process, read line-buffered output, detect simple confirmation prompts, pause/resume/kill the process group, apply deterministic protected-path and auto-approve policy, pass ambiguous actions to the MLX auditor path, record rollback events in local traces, optionally record MCP-Cortex-style decision traces, and disclose at runtime that MCP-Cortex is trace-only rather than an authorization proxy.

Not yet proven or missing:

- `scripts/auditor_smoke.py` now exists and dry-run mode verifies structured smoke output, but real Gemma 4 model-load fails in this execution session because MLX reports no Metal device available.
- PTY-style interaction is proven against disposable synthetic agent fixtures, including a sequential startup-plus-tool-confirmation-shaped fixture. Codex, Claude Code, and Gemini CLI executables are discoverable through safe non-interactive metadata probes. Claude Code startup trust-prompt control is proven in a disposable workspace, but full real Claude/Gemini/Codex model/tool confirmation behavior remains unproven; the latest Claude attempt trusted the temp workspace and typed the harmless prompt but did not reach a tool permission prompt before timeout.
- Continuous filesystem enforcement is implemented for protected file effects and proven with a disposable no-prompt `.env` write smoke test that suspends the runner and rolls back the protected file.
- Strict structured auditor verdicts resistant to prompt injection or stray `YES` text.
- First-pass richer policy model with stable effect IDs, risk classes, secret/deploy/network hard blocks, and delete confirmation.
- Prompt-time command-effect inference and first-pass structured extraction for obvious shell, network, and deploy commands.
- Minimal pending-approval UX with explicit approve/block actions for review and confirm outcomes.
- Richer config schema with policy profiles, prompt patterns, model parameters, trace path, PTY mode, risk thresholds, workspace root, ignore dirs, and strict validation.
- Dynamic scoped session overrides with expiry, hard-block precedence, and trace-visible override source.
- TUI controls to create/list/clear session overrides from a pending approval plus a first-class manual override input for arbitrary patterns.
- CLI controls to add arbitrary temporary allow-path overrides for a session.
- Installable package metadata, `sentinel` console script, user-facing README, and runtime safety-boundary warning.
- Human-readable trace replay output with policy risk/effect/source fields.
- Release metadata/wheel check workflow.
- Structured pending-approval context in the reasoning log.
- Dedicated approval panel for pending decisions.
- FIFO queue behavior for multiple pending approvals.
- Mounted Textual approval-panel inspection and bounded Claude Code startup trust-prompt validation; full model/tool validation remains open.
- Aggregate disposable E2E smoke covering core local scenarios.
- Guarded opt-in real-agent smoke harness for disposable command validation.
- Machine-readable readiness/proof matrix for current GOAL.md status.

## Full-Featured Application Target

Cortex Sentinel should become a local-first safety console for high-autonomy development agents. A full-featured version should let a software engineer run an agent under supervision, see what it is doing, enforce local policy before risky actions proceed, preserve an auditable session trail, and intervene quickly when behavior drifts from the declared task.

The application must remain honest about its boundary: it is local supervision and safety assistance, not a guarantee that an unsafe agent can never write, leak, or destroy data.

## Gap Analysis

### GAP-001: Real Model Runtime Not Yet Reverified

**Severity:** High
**Current state:** The repo `venv` has the required `gemma4_unified -> gemma4` mapping, and `scripts/auditor_smoke.py --dry-run` proves structured smoke reporting. The real smoke currently fails in this session with `No Metal device available`, so actual model load/latency remains unverified here.
**Full-feature requirement:** A repeatable command proves the configured model loads, applies the chat template, returns a structured verdict, and reports latency/memory bounds.
**Acceptance evidence:** `venv/bin/python scripts/auditor_smoke.py` exits 0 and records model id, load status, first-token latency, total latency, and parsed verdict.

### GAP-002: Real Agent PTY Integration Is Partially Proven

**Severity:** Reduced from High to Medium
**Current state:** `PtyAgentRunner` now captures prompts without newline, injects input, prevents double-start, kills process groups, and can launch commands in a specified disposable working directory. `scripts/agent_integration_smoke.py` proves prompt detection, input injection, disposable file write, and kill behavior in a temporary workspace. `scripts/real_agent_smoke.py` provides a guarded opt-in harness for caller-supplied real-agent commands, requiring an explicit command and running it in a temporary workspace. It now supports repeated `--interaction "REGEX=>INPUT"` steps for startup-plus-tool-confirmation-shaped flows and rejects expected-output matches that already appeared before the final response. It also has safe non-interactive CLI metadata probes; in this session, Codex, Claude Code, and Gemini version probes pass. `python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8` proves Sentinel can drive Claude Code's startup trust prompt in a disposable workspace, inject the safe `No, exit` response, and kill the process. A real Claude Code tool-confirmation attempt using the multi-step harness trusted the temp workspace and typed the harmless prompt but did not reach a tool permission prompt or produce the encoded expected output before timeout. Full real Claude/Gemini/Codex model/tool confirmation behavior remains unproven until the harness is run successfully with a deliberately safe command that exercises that flow.
**Full-feature requirement:** Sentinel can run at least one real local agent command in a safe fixture workspace and detect/handle its confirmation prompts without corrupting terminal interaction.
**Acceptance evidence:** `tests/test_pty_runner.py` passes; `venv/bin/python scripts/agent_integration_smoke.py` exits 0 with `prompt_detected`, `input_injected`, `file_written`, and `process_killed` all true. `tests/test_real_agent_smoke.py` proves the guarded harness dry-run, explicit-command requirement, disposable cwd execution, prompt detection, input injection, expected output detection, sequential multi-prompt interactions, process kill, non-interactive probe reporting, and named Claude trust-prompt smoke wiring. `python scripts/real_agent_smoke.py --probe-installed-agents --timeout 5` exits 0 with `pass_count: 3` for Codex, Claude Code, and Gemini. `python scripts/real_agent_smoke.py --claude-trust-smoke --timeout 8` exits 0 with `prompt_detected`, `input_injected`, and `process_killed` true. A full model/tool confirmation Claude/Gemini/Codex command still needs to complete successfully through that harness.

### GAP-003: Continuous Enforcement Is Implemented For Protected File Effects

**Severity:** Reduced from High to Medium
**Current state:** `ContinuousEnforcer` polls file effects, applies `SentinelPolicy`, suspends the runner when protected effects are detected, and rolls back blocked protected or built-in secret file effects inside the observed workspace by deleting newly-created protected files or restoring modified/deleted protected files from an in-memory baseline. It is wired into `SentinelTUI` lifecycle and proven by `scripts/enforcement_smoke.py` using a no-prompt `.env` write in a disposable workspace. Remaining work is true pre-write sandboxing and broader effect coverage.
**Full-feature requirement:** Continuous filesystem observation or sandbox-mediated execution detects protected-path writes immediately and suspends/kills the agent according to policy.
**Acceptance evidence:** `tests/test_enforcer.py` passes; `venv/bin/python scripts/enforcement_smoke.py` exits 0 with `protected_effect_detected`, `runner_suspended`, and `rollback_performed` true for `.env`, while `protected_file_present` is false. Additional real-agent and true pre-write sandbox evidence is still needed.

### GAP-004: Policy Model Has First-Pass Risk Classification

**Severity:** Reduced from High to Medium
**Current state:** `SentinelPolicy` now classifies file and command effects with stable effect IDs and risk classes. It supports allow/block/review/confirm outcomes, blocks protected paths and secret-like paths, blocks external network and production deploy command effects, requires confirmation for deletes, applies stricter configured risk thresholds for non-hard effects, supports scoped session overrides after hard-block checks, and records risk/effect IDs/source metadata in persisted session traces. `SentinelTUI` now infers obvious shell/network/deploy command effects from recent output and prompt text, extracts command text from JSON `command`/`cmd` fields and common Bash tool-call lines, then passes command effects into policy evaluation. The remaining gap is validation against real agent protocols and a richer human approval queue for confirm/review outcomes.
**Full-feature requirement:** Policy should classify read/write/delete/execute/network/deploy effects, account for command risk, support deny/allow/review/require-confirmation outcomes, and explain decisions with stable reasons.
**Acceptance evidence:** `tests/test_policy.py` covers safe docs edits, source edits, deletes, shell commands, network calls, secrets access, and production deploy attempts. `tests/test_tui_policy_integration.py` proves prompt-time command effects are inferred, structured tool command text is extracted, and command effects are passed to policy. `tests/test_session_trace.py` proves policy risk and effect IDs are persisted.

### GAP-005: Auditor Verdict Parsing Was Too Coarse

**Severity:** Reduced from High to Medium
**Current state:** `Auditor.audit_intent_result` now requires a structured JSON verdict and the legacy tuple API delegates to that parser. Free-text `YES` no longer approves. Remaining work is to verify the real model consistently emits the requested JSON schema.
**Full-feature requirement:** Auditor requires a strict final schema, such as `{"verdict":"allow|block|review","risk":"green|yellow|orange|red","reason":"..."}`. Invalid or ambiguous output must block or require human review.
**Acceptance evidence:** `tests/test_auditor.py` proves stray `YES` in reasoning does not approve; malformed output blocks; structured allow/block/review outputs parse correctly. Real-model schema adherence still needs `venv/bin/python scripts/auditor_smoke.py` in a Metal-capable session.

### GAP-006: Human Approval UX Has Minimal Tested State

**Severity:** Reduced from High to Medium
**Current state:** `SentinelTUI` now has a `PendingApproval` state and FIFO queue for review/confirm outcomes, logs a structured approval block with command, prompt, policy action/reason/risk, effect IDs, file effects, auditor result, queue depth, and controls, shows the same context in a dedicated approval panel, suspends the runner while waiting, advances queued approvals before resuming, clears the panel after approve/block when the queue is empty, and exposes explicit approve/block/override key actions. Auditor-allowed review decisions no longer silently auto-send `y`. A mounted Textual `run_test` inspection proves the real widget tree renders and clears the approval panel. The Claude Code startup trust prompt is now proven through the PTY harness; remaining work is full model/tool prompt validation.
**Full-feature requirement:** The TUI should show current command, proposed action, file effects, policy reason, auditor verdict, risk class, and clear approve/block/resume/kill controls.
**Acceptance evidence:** `tests/test_tui_policy_integration.py` proves block, allow, review, confirm, structured pending approval context, dedicated approval panel show/clear behavior in fake widgets and a mounted Textual app, FIFO queued pending approvals, approve pending, block pending, and no-op pending action transitions.

### GAP-007: MCP-Cortex Is Disclosed As Trace-Oriented

**Severity:** Reduced from Medium-High to Medium
**Current state:** `CortexBridge` records decisions through nested MCP-Cortex when available. It does not proxy real MCP tool calls. `README.md` documents that boundary, and `SentinelTUI.on_mount()` now writes a runtime line stating MCP-Cortex is trace-only metadata recording, not a tool-call authorization proxy.
**Full-feature requirement:** Sentinel should either integrate with a real MCP adapter/proxy path or clearly limit MCP-Cortex to local trace/policy metadata.
**Acceptance evidence:** `tests/test_tui_fixes.py::TestTUIFixes::test_on_mount_starts_enforcer` proves the runtime trace-only disclosure is emitted; `README.md` documents the MCP-Cortex trace-only limitation. A real MCP proxy remains out of scope for this version.

### GAP-008: Persistent Session Trace Is Implemented

**Severity:** Reduced from Medium-High to Medium
**Current state:** `SessionTraceStore` writes local JSONL events with stable digests. `SentinelTUI` records session start, process lifecycle, decisions, user actions, and enforcement rollback results without file contents. `scripts/trace_smoke.py` proves command metadata, prompt text, file effects, policy decision, auditor verdict, user action, rollback event, process lifecycle events, and digests are present in a persisted artifact. `scripts/trace_replay.py` and `sentinel trace replay` render summary JSON and human-readable text, including policy risk, effect IDs, source, override id, and rollback result count. Remaining work is longer real-agent session validation.
**Full-feature requirement:** Sessions should be written to local durable storage with command metadata, policy decisions, file effects, auditor outputs, user overrides, and process lifecycle events.
**Acceptance evidence:** `tests/test_session_trace.py`, `tests/test_trace_replay.py`, `tests/test_trace_replay_script.py`, and `tests/test_cli.py` pass; `venv/bin/python scripts/trace_smoke.py` exits 0 with all required trace fields and `has_rollback_event` true. `scripts/trace_replay.py <trace.jsonl>` and `sentinel trace replay --format text <trace.jsonl>` emit validated summaries.

### GAP-009: Configuration Has First-Pass Profiles And Validation

**Severity:** Reduced from Medium to Low-Medium
**Current state:** `SentinelConfig` now supports workspace root, ignore dirs, prompt patterns, model parameters, risk thresholds, policy profiles, trace storage, PTY mode, and override TTL. `load_config(..., strict=True)` validates unknown keys and bad types while non-strict loading remains backward-compatible for missing or malformed files. `SentinelTUI` now honors configured workspace root, ignore dirs, trace directory, prompt patterns, and model id. Risk thresholds are wired into `SentinelPolicy`, and config is reachable through the packaged `sentinel run --config ...` CLI.
**Full-feature requirement:** Config should support workspace root, ignore dirs, prompt patterns, model parameters, risk thresholds, policy profiles, trace storage, PTY mode, and override TTLs.
**Acceptance evidence:** `tests/test_sentinel_config.py` covers defaults, validation errors, path expansion, bad YAML, unknown keys, and realistic profile files. `tests/test_tui_policy_integration.py` proves the TUI honors workspace, trace, ignore, prompt, and model config.

### GAP-010: Dynamic Session Overrides Have Core Policy Support

**Severity:** Reduced from Medium to Low-Medium
**Current state:** `SessionOverrideStore` supports scoped path overrides with TTL/expiry, and `SentinelPolicy` can apply active overrides only after protected-path, secret, network, and production-deploy hard blocks. Override decisions include source and override id, and `SessionTraceStore` persists those fields. `SentinelTUI` now exposes actions to create an allow override from the current pending approval's file effect, open a first-class manual Textual input for arbitrary glob overrides, list active overrides, and clear overrides, with user-action trace events. `SentinelTUI.create_manual_allow_override(...)` normalizes arbitrary trace-visible allow overrides and rejects empty patterns. `sentinel run --allow-path "src/ui/**" -- ...` seeds arbitrary trace-visible allow overrides for the current session.
**Full-feature requirement:** A user can add scoped temporary policy overrides, such as allowing writes to `src/ui/**` for the current session, with TTL and trace recording.
**Acceptance evidence:** `tests/test_policy.py` proves overrides are scoped, expire, and cannot bypass hard protected-path blocks. `tests/test_session_trace.py` proves override source/id are persisted. `tests/test_tui_policy_integration.py` proves pending override creation, mounted manual override input submission/cancel/empty behavior, manual arbitrary allow override creation, empty manual pattern rejection, hard-block precedence, startup CLI override seeding, list, clear, and trace user actions. `tests/test_cli.py` proves repeated `--allow-path` patterns are passed into the TUI.

### GAP-011: Packaging And CLI Are Implemented For Local Use

**Severity:** Reduced from Medium to Low
**Current state:** Top-level `pyproject.toml` defines the `cortex-sentinel` package and `sentinel = sentinel.main:main` console script. CLI subcommands cover `sentinel run --config ... -- <agent command>`, `sentinel check-env`, `sentinel readiness`, and `sentinel trace replay <trace.jsonl>`. Editable install into the repo venv succeeds, installed help/env/readiness/trace commands were manually verified, and `scripts/release_check.py` validates package metadata/docs and builds a local wheel. Remaining work is only formal release publishing/versioning policy.
**Full-feature requirement:** A user can install/run Sentinel with stable commands, e.g. `sentinel run --config sentinel.yaml -- claude ...`, using the repo venv or package install, and can inspect current readiness without reading every artifact manually.
**Acceptance evidence:** `venv/bin/python -m pip install -e .` exits 0; `tests/test_cli.py` and `tests/test_release_check.py` pass; `venv/bin/sentinel --help`, `venv/bin/sentinel run --help`, `venv/bin/sentinel check-env`, `venv/bin/sentinel readiness --no-run`, and `venv/bin/sentinel trace replay ...` exit 0; `python scripts/release_check.py --wheel-dir /tmp/cortex-sentinel-release-check` exits 0 and emits `cortex_sentinel-0.1.0-py3-none-any.whl`; `python scripts/readiness_check.py` exits 0 and emits the current GOAL.md proof matrix.

### GAP-012: Security Boundary Is Documented And Surfaced At Runtime

**Severity:** Reduced from Medium to Low
**Current state:** `README.md` documents the safety boundary and known limitations. `SentinelTUI.on_mount()` writes a startup warning that Cortex Sentinel is local supervision, not a hard sandbox. Remaining work is broader UX polish, not basic boundary disclosure.
**Full-feature requirement:** Runtime and docs should clearly state what Sentinel can and cannot prevent, especially around already-completed writes, shell escapes, external tools, and unobserved side effects.
**Acceptance evidence:** `tests/test_readme.py` checks the safety docs, and `tests/test_tui_fixes.py::TestTUIFixes::test_on_mount_starts_enforcer` checks the startup warning.

### GAP-013: Local End-To-End Scenario Matrix Exists

**Severity:** Reduced from Medium to Low-Medium
**Current state:** `scripts/e2e_smoke.py` now runs a disposable aggregate E2E smoke covering safe auto-approval, protected-path block, ambiguous auditor fallback, no-prompt protected write enforcement, PTY prompt handling, trace export, and config profile behavior. `scripts/real_agent_smoke.py --claude-trust-smoke` adds a bounded real Claude Code startup/control proof. Remaining work is full model/tool validation against Claude/Gemini/Codex protocols.
**Full-feature requirement:** End-to-end tests should cover safe auto-approval, protected-path block, ambiguous auditor review, no-prompt protected write, PTY prompt handling, trace export, and config profiles.
**Acceptance evidence:** `tests/test_e2e_smoke.py` passes; `python scripts/e2e_smoke.py` exits 0 with all scenario booleans true and `disposable_workspace: true`.

### GAP-014: User-Facing README Exists

**Severity:** Reduced from Medium to Low
**Current state:** `README.md` now includes quick start, installation, config reference, safety boundary, troubleshooting, examples, Claude trust-prompt smoke usage, and explicit remaining limitations. Remaining work is to keep docs synchronized as model/tool validation improves.
**Full-feature requirement:** Docs should include quick start, installation, config reference, safety model, known limitations, troubleshooting, and examples.
**Acceptance evidence:** `tests/test_readme.py` asserts required sections and core commands are present.

### GAP-015: Repo Hygiene Needs Cleanup

**Severity:** Low-Medium
**Current state:** Generated `__pycache__` files, `.DS_Store`, root scripts, nested repo status, and untracked files need an intentional cleanup/commit strategy.
**Full-feature requirement:** `.gitignore`, repo structure, and commit boundaries should be clean enough for repeatable development.
**Acceptance evidence:** `git status --short` contains only intentional tracked changes after cleanup; generated artifacts are ignored.

## /goal

OUTCOME:
Build Cortex Sentinel from its current local MVP into a full-featured, locally runnable agent supervision application whose safety claims are evidence-backed: real model smoke works from the repo venv, real or PTY-backed agent interaction is tested, protected-path enforcement works without relying only on prompts, policy decisions are structured and traceable, sessions are persistently auditable, and user-facing docs explain exact capabilities and limits.

PROOF OF DONE:

1. Run `pytest -q` from `/Volumes/WS4TB/gemOptq` and confirm it exits 0.
2. Run `python -m pytest -q` from `/Volumes/WS4TB/gemOptq/mcp-cortex` and confirm it exits 0.
3. Run `venv/bin/python scripts/sentinel_smoke.py` and confirm it exits 0.
4. Run a new real auditor smoke command, expected name `venv/bin/python scripts/auditor_smoke.py`, and confirm it loads `mlx-community/gemma-4-12B-it-OptiQ-4bit`, produces a structured verdict, and reports latency.
5. Run a PTY or real-agent integration smoke command, expected name `venv/bin/python scripts/agent_integration_smoke.py`, and confirm prompt detection, pause/resume/kill, and input injection work in a disposable workspace.
6. Run `python scripts/real_agent_smoke.py --dry-run` and, when safe credentials/workspace are available, run it with a real local agent command in a disposable workspace.
7. Run an enforcement smoke command, expected name `venv/bin/python scripts/enforcement_smoke.py`, and confirm protected-path writes are blocked or stopped even when no confirmation prompt appears.
8. Inspect the persisted session trace artifact from the smoke tests and confirm it contains command metadata, prompt text, file effects, policy decisions, auditor verdicts, user actions, rollback events, process lifecycle events, and stable digests.
9. Run `python scripts/e2e_smoke.py` and confirm the aggregate disposable E2E report is `ok`, including no-prompt protected write rollback.
10. Inspect user docs and confirm they include quick start, config reference, safety boundary, troubleshooting, and examples.
11. Run `git diff --check` and confirm it exits 0.
12. Provide a final changed-file summary, remaining limitations, and exact command outputs used as evidence.

SCOPE:

- Modify only:
  - `src/sentinel/`
  - `tests/`
  - `scripts/`
  - `docs/`
  - root project metadata/config files such as `pyproject.toml`, `pytest.ini`, `.gitignore`, `README.md`, `GOAL.md`, `REPO_MAP.md`, `RISK_NOTES.md`
  - `sentinel.yaml` and example config files
  - `mcp-cortex/` only for narrowly scoped compatibility fixes or integration tests needed by Sentinel
- Read/reference:
  - `REPO_MAP.md`
  - `RISK_NOTES.md`
  - `CORTEX_SENTINEL_DSS_WBV_HANDOFF.md`
  - `GEMMA4_HANDOFF.md`
  - `docs/plans/2026-06-08-cortex-sentinel-design.md`
  - `docs/plans/2026-06-08-sentinel-hardening-design.md`
  - `mcp-cortex/README.md`
  - `mcp-cortex/CODEX_HANDOFF.md`
  - `mcp-cortex/docs/`
- Do not modify:
  - private credentials, `.env` files, SSH keys, or external account state
  - unrelated sibling repos
  - generated caches except to add ignore rules or remove them when explicitly safe

CONSTRAINTS:

- Use the repo venv for MLX/Gemma runtime verification: `venv/bin/python`.
- Do not treat shell/miniforge Python as the authoritative Sentinel runtime unless explicitly required.
- Preserve process-group kill/suspend behavior unless replacing it with a tested safer equivalent.
- Do not weaken protected-path behavior to make auto-approval easier.
- Do not rely on LLM approval for hard protected-path violations.
- Do not claim production-grade safety, sandboxing, or MCP authorization unless implemented and verified.
- Do not add dependencies unless they are necessary for PTY handling, filesystem monitoring, packaging, or persistence and are documented.
- Prefer small, test-first changes. Each new behavior needs a failing test first unless it is documentation-only.
- Keep MCP-Cortex integration compatible with the nested repo boundary; do not perform broad rewrites of `mcp-cortex`.

SAFETY / PROVENANCE:

- Preserve an auditable record of policy decisions, auditor outputs, user actions, and process lifecycle events.
- Separate deterministic policy decisions from LLM semantic judgments.
- If a safety claim cannot be proven with a local command or fixture, document it as a limitation rather than a feature.
- Prefer block/review over silent allow when effects are unknown, unparseable, or outside configured scope.
- Never pass secrets, PHI, credentials, private keys, or unnecessary sensitive data into model prompts or traces.

ITERATION:

1. Start by creating or updating `.gitignore` and packaging metadata so the repo has clean repeatable commands.
2. Implement one gap at a time in this priority order:
   - real auditor smoke
   - PTY/real-agent integration
   - continuous protected-path enforcement
   - structured auditor verdicts
   - richer policy model
   - approval UX
   - persistent session trace
   - config profiles and overrides
   - packaging/docs
   - repo hygiene
3. For each gap:
   - write a failing test or smoke fixture first,
   - implement the smallest behavior that satisfies it,
   - run the nearest relevant test,
   - update docs and risk notes if the project status changes.
4. After every 2-3 completed gaps, run the full verification set from `PROOF OF DONE`.
5. Keep a concise progress log in `PROGRESS.md` if the task spans multiple sessions.

STOP:

Pause and summarize instead of continuing if:

- Real model loading requires credentials, network access, unavailable GPU/Metal access, or a destructive environment change.
- A real-agent smoke test would run an agent against non-disposable files.
- Continuous enforcement requires a privileged kernel/system extension, production deployment, or broad permission change.
- The same failing verification persists after 3 distinct root-cause-driven repair attempts.
- The implementation would materially change product scope, such as becoming a remote service instead of a local-first tool.
- Any step risks exposing secrets, credentials, PHI, private keys, or sensitive user data.

COMPLETE:

Mark this goal complete only when every `PROOF OF DONE` item passes with actual command output or file-inspection evidence, the user-facing docs match implemented behavior, and remaining limitations are explicitly documented rather than hidden.

## Recommended First Implementation Slice

Do not try to build the entire application in one pass. Start with:

1. `scripts/auditor_smoke.py` using `venv/bin/python`.
2. Structured auditor output parsing and tests.
3. A PTY-backed runner prototype in a disposable fixture workspace.
4. Continuous protected-path enforcement for `.env` and configured protected paths.

This slice proves the core safety loop before expanding UX, persistence, packaging, and MCP proxy work.
