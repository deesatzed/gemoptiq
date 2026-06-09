# REVIEW.md

## Review Scope

Reviewed the Codex TUI smoke changes in `scripts/real_agent_smoke.py`, PTY window sizing in `src/sentinel/pty_runner.py`, readiness wiring in `src/sentinel/readiness.py`, related regression tests, and synchronized status docs.

## Summary Judgment

Proceed.

## Findings

| Severity | Category | Finding | Why It Matters | Required Fix |
|---|---|---|---|---|
| None | Correctness | No blocking findings after the stricter interaction-control fix. | The Codex TUI smoke now requires both expected prompts to be detected and injected before claiming interactive prompt control. | None. |

## Correctness

The original zero-size PTY issue is covered by a child-process window-size fixture. The Codex TUI smoke now initializes a disposable git workspace, requires both workspace-trust and command-approval interactions, and separately checks for the output marker.

## Security and Privacy

The real-agent smoke remains opt-in and uses ephemeral workspaces. It does not pass secrets by default. The tested Codex command is read-only and emits a fixed sentinel marker.

## Tests

Fresh verification:

- `pytest -q tests/test_real_agent_smoke.py tests/test_pty_runner.py tests/test_readiness_check.py tests/test_readme.py tests/test_cli.py`: `31 passed in 2.03s`.
- `python -m py_compile src/sentinel/pty_runner.py scripts/real_agent_smoke.py src/sentinel/readiness.py`: exits 0.
- `git diff --check`: exits 0.
- `python scripts/real_agent_smoke.py --codex-tui-smoke --timeout 60`: exits 0 with two interactions detected/injected and `SENTINEL_CODEX_TUI_OK`.
- `pytest -q`: `142 passed in 128.80s`.
- `python -m pytest -q` from `mcp-cortex/`: `11 passed in 0.56s`.

## Maintainability

The new Codex TUI path reuses the existing real-agent harness and readiness item pattern. The main maintenance risk is CLI prompt text drift in future Codex versions.

## Performance

No production-path performance change. The new real Codex TUI smoke is opt-in and bounded by timeout.

## UI/UX Impact

No application UI changes. Documentation now states that Codex TUI command approval is proven while Claude/Gemini full interactive tool-confirmation remains unproven.

## Regression Risk

Low for normal Sentinel runtime. Medium for the optional Codex TUI smoke because it depends on Codex CLI prompt wording and local app-server/runtime availability.

## Scope Creep Check

Changes are limited to the PTY runner, real-agent smoke harness, readiness matrix, tests, and truth/status docs.

## Required Fixes Before Done

None.

## Optional Improvements

- Add equivalent safe full interactive tool-confirmation smokes for Claude Code and Gemini when account/auth state is suitable.
- Add more terminal capability responses only when required by a verified real-agent failure.
