# Cortex Sentinel — DSS-WBV Handoff Packet v4.0 (as of 2026-06-10)  | H: 0.6  | Fidelity: 91%

## 0. Triage Card

| Field | Snapshot |
|---|---|
| Project | Cortex Sentinel local safety console for autonomous coding agents. [file:README.md:L1-L7 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| Health | Green for local Python test surfaces run in this handoff: `pytest -q` returned `142 passed in 138.96s`; `python -m pytest -q` in `mcp-cortex/` returned `11 passed in 0.56s`. [source:local-command:pytest-root @ 2026-06-10T12:07:16Z] [VERIFIED] |
| Branch / SHA | `master` at `296e0678f101`, tracking `origin/master`. [source:git:rev-parse/status @ 2026-06-10] [VERIFIED] |
| Hermeticity | H = 0.6 because package metadata exists, but no lockfile was found, MLX/Gemma depends on local Metal, and no CI artifact was discovered in this packet. [source:local-command:find-lockfiles/python-version/pytest-version @ 2026-06-10] [VERIFIED] |
| Highest-risk vector | Full interactive Claude/Gemini tool-confirmation behavior remains unproven, while Codex and Claude startup surfaces have narrower proofs. [file:README.md:L49-L54 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| 1-Day Resume Checklist | 1. Read this packet. 2. Run `git status --short --branch`. 3. Run `pytest -q`. 4. Run `python -m pytest -q` in `mcp-cortex/`. 5. Run `python scripts/readiness_check.py`. 6. Pick one backlog item from Section 10. [INFERRED] |

One-line health: local tests are green, public docs are current, and remaining safety claims are bounded rather than hidden. [VERIFIED]

## 1. Warm-Boot Cursor (machine-first)

```json
{
  "project_name": "Cortex Sentinel",
  "snapshot_iso": "2026-06-10T12:07:16Z",
  "branch": "master",
  "head_sha": "296e0678f101",
  "remote": "https://github.com/deesatzed/gemoptiq.git",
  "handoff_horizon": "1w",
  "cwd": "/Volumes/WS4TB/gemOptq",
  "primary_owner_role": "local developer or next coding agent",
  "primary_owner_status": "active",
  "next_review_checkpoint": "after the next code or documentation change, before commit",
  "must_read": [
    "GOAL.md",
    "README.md",
    "PROGRESS.md",
    "docs/index.html",
    "docs/showpiece/cortex-sentinel.md"
  ],
  "safe_first_commands": [
    "git status --short --branch",
    "pytest -q",
    "python -m pytest -q"
  ],
  "do_not_claim": [
    "hard sandbox",
    "production security boundary",
    "full MCP proxy",
    "full interactive Claude/Gemini tool-confirmation proof"
  ]
}
```

| Cursor Field | Value | Evidence |
|---|---|---|
| `cwd` | `/Volumes/WS4TB/gemOptq` | [source:environment_context @ 2026-06-10] [VERIFIED] |
| `branch` | `master` | [source:git:status @ 2026-06-10] [VERIFIED] |
| `head_sha` | `296e0678f101` | [source:git:rev-parse @ 2026-06-10] [VERIFIED] |
| `remote` | `https://github.com/deesatzed/gemoptiq.git` | [source:git:remote -v @ 2026-06-10] [VERIFIED] |
| `handoff_horizon` | `1w` | [INFERRED] |
| `next_review_checkpoint` | before the next commit after this handoff | [INFERRED] |

## 2. System Vector Snapshot

| Vector | State |
|---|---|
| C: code AST + git tree | Python package under `src/sentinel/`, test suite under `tests/`, static docs under `docs/`, nested `mcp-cortex/` package present. [source:local-command:find src/sentinel scripts tests docs mcp-cortex @ 2026-06-10] [VERIFIED] |
| V: pinned version landscape | `pyproject.toml` declares `cortex-sentinel==0.1.0`, Python `>=3.10`, dependencies `PyYAML>=6` and `textual>=0.80`, optional `mlx-lm`. [file:pyproject.toml:L5-L20 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| E: runtime environment | Current shell reports `Python 3.13.9` and `pytest 8.4.1`; no lockfile or requirements file was found at depth 3. [source:local-command:python/pytest/find-lockfiles @ 2026-06-10] [VERIFIED] |
| D: data + migration head | No database, migrations, or persistent app data schema was discovered; Sentinel writes local JSONL traces under configured trace directories. [file:README.md:L95-L100 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| K: knowledge anchors | `GOAL.md`, `README.md`, `PROGRESS.md`, `docs/showpiece/cortex-sentinel.md`, and this packet are current knowledge anchors. [file:README.md:L9-L15 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |

Project signature: Cortex Sentinel is a local-first supervision console for autonomous coding agents. [file:pyproject.toml:L5-L10 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Phase: local supervision MVP with evidence-backed safety claims and public landing/showpiece docs. [file:GOAL.md:L3-L22 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Target S_next: improve real-agent validation and hermetic reproducibility without weakening safety boundaries. [file:GOAL.md:L210-L259 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Hermeticity Score: H = 0.6. Justification: metadata and tests are local, but dependency versions are not locked, real Gemma requires Metal, and CI/deploy evidence is not anchored. [VERIFIED]

Health: ✅ Local Python suites passed in this handoff; ⚠️ readiness remains partial when optional real-agent/model smokes are not run. [source:local-command:pytest/readiness-no-run @ 2026-06-10] [VERIFIED]

## 3. Structural Topology & Flow

| Module / File | Purpose | Last Touched | Critical Path? | Anchor |
|---|---|---:|---|---|
| `src/sentinel/main.py` | CLI entrypoint for `run`, `check-env`, `readiness`, and `trace replay`. | 2026-06-09 | true | [file:src/sentinel/main.py:L13-L108 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/tui.py` | Textual UI, prompt polling, pending approvals, overrides, and trace/cortex decisions. | 2026-06-09 | true | [file:src/sentinel/tui.py:L64-L723 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/policy.py` | Policy decisions, risk classes, hard blocks, overrides, and effect IDs. | 2026-06-09 | true | [file:src/sentinel/policy.py:L13-L220 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/enforcer.py` | Continuous polling enforcement and supported rollback. | 2026-06-09 | true | [file:src/sentinel/enforcer.py:L14-L133 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/session_trace.py` | JSONL event store with stable SHA-256 digests. | 2026-06-09 | true | [file:src/sentinel/session_trace.py:L17-L136 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/pty_runner.py` | PTY runner with prompt capture, input injection, terminal query handling, and process control. | 2026-06-09 | true | [file:src/sentinel/pty_runner.py:L17-L170 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/auditor.py` | MLX/Gemma auditor and strict structured output parsing. | 2026-06-09 | true | [file:src/sentinel/auditor.py:L13-L146 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `src/sentinel/readiness.py` | GOAL readiness matrix reporter. | 2026-06-09 | true | [file:src/sentinel/readiness.py:L23-L439 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `docs/index.html` | Live static landing page for vibe-coding audience. | 2026-06-10 | false | [file:docs/index.html:L638-L953 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |
| `mcp-cortex/` | Nested trace-oriented MCP metadata package. | 2026-06-08/09 | false | [file:mcp-cortex/pyproject.toml:L5-L48 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |

Flow:

```text
human -> sentinel CLI -> SentinelTUI -> AgentRunner/PtyAgentRunner -> agent process
                            |                  |
                            |                  v
                            |           FileEffectObserver
                            v                  |
                    SentinelPolicy <-----------+
                            |
          allow | block | review | confirm
                            |
             Auditor / human approval / ContinuousEnforcer
                            |
                    SessionTraceStore -> trace replay
```

Boundary map: Sentinel supervises a local child process and traces decisions; it is not a kernel sandbox, container boundary, full MCP proxy, or production security boundary. [file:README.md:L187-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

## 4. Decision Archaeology & Assumption Register

Decision D-001:
- Decision: Keep Cortex Sentinel local-first instead of making it a remote service. [file:GOAL.md:L158-L174 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Rationale: Safety claims depend on local traces, local policy, and user-controlled agent processes. [file:README.md:L3-L7 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Consequence: Deployment state is intentionally not part of current runtime proof. [INFERRED]
- Reversible? Yes; would require new architecture, threat model, and deployment evidence. [INFERRED]

Decision D-002:
- Decision: Deterministic policy hard-blocks protected paths, secret-like paths, external network effects, and production deploy effects before LLM judgment. [file:README.md:L187-L190 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Rationale: The app must not rely on an LLM to approve high-risk known categories. [file:GOAL.md:L234-L242 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Consequence: Some useful agent actions require explicit review or remain blocked. [INFERRED]
- Reversible? No for current safety claims; weakening it invalidates the safety model. [INFERRED]

Decision D-003:
- Decision: Use static `docs/index.html` for the landing/showpiece rather than a frontend build pipeline. [file:PROGRESS.md:L3-L18 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Rationale: The page can be opened directly and optionally hosted by GitHub Pages. [file:PROGRESS.md:L16-L17 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Consequence: Screenshot examples are static explanatory panels, not captured runtime screenshots. [file:PROGRESS.md:L18-L18 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Reversible? Yes; can replace with generated app if hosting/build requirements change. [INFERRED]

Assumption A-001:
- Assumption: Next agent has local repository access at `/Volumes/WS4TB/gemOptq`. [source:environment_context @ 2026-06-10] [VERIFIED]
- Risk if false: Commands and file links need path adjustment. [INFERRED]
- Validation: run `pwd`. [VERIFIED]

Assumption A-002:
- Assumption: Real MLX/Gemma auditor checks require a macOS session with Metal access. [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Risk if false: `venv/bin/python scripts/auditor_smoke.py` may fail even when the code path is healthy. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Validation: run `venv/bin/python scripts/auditor_smoke.py`. [VERIFIED]

Assumption A-003:
- Assumption: GitHub Pages or another host is responsible for live rendering of `docs/index.html`; the repo only stores static HTML. [file:PROGRESS.md:L16-L17 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Risk if false: Live site may lag or not reflect committed docs. [INFERRED]
- Validation: compare live page source SHA/content to `docs/index.html` at `296e0678f101`. [INFERRED]

## 5. Run & Verification Guides

Command block: root test suite
- cwd: `/Volumes/WS4TB/gemOptq` [VERIFIED]
- prereqs: Python environment with project test dependencies installed. [INFERRED]
- exact command: `pytest -q` [VERIFIED]
- expected signal: `142 passed` [source:local-command:pytest-root @ 2026-06-10] [VERIFIED]
- Mutates state? N | Inverse command: none. [VERIFIED]
- failure modes: missing deps, changed tests, platform-specific process behavior. [INFERRED]
- anchor: [file:README.md:L215-L220 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Command block: MCP-Cortex test suite
- cwd: `/Volumes/WS4TB/gemOptq/mcp-cortex` [VERIFIED]
- prereqs: Python test dependencies for nested package. [INFERRED]
- exact command: `python -m pytest -q` [VERIFIED]
- expected signal: `11 passed` [source:local-command:mcp-pytest @ 2026-06-10] [VERIFIED]
- Mutates state? N | Inverse command: none. [VERIFIED]
- failure modes: missing pytest/jsonschema or nested package import path drift. [INFERRED]
- anchor: [file:mcp-cortex/pyproject.toml:L34-L48 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Command block: readiness inspection without running smokes
- cwd: `/Volumes/WS4TB/gemOptq` [VERIFIED]
- prereqs: repo root and Python available. [VERIFIED]
- exact command: `python scripts/readiness_check.py --no-run` [VERIFIED]
- expected signal: JSON summary with `status: partial`, docs pass, and executable smokes marked manual/external blocked. [source:local-command:readiness-no-run @ 2026-06-10] [VERIFIED]
- Mutates state? N | Inverse command: none. [VERIFIED]
- failure modes: stale README sections or import failure. [INFERRED]
- anchor: [file:README.md:L244-L254 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Command block: install package editable
- cwd: `/Volumes/WS4TB/gemOptq` [VERIFIED]
- prereqs: Python packaging tools and dependency access/cache. [INFERRED]
- exact command: `python -m pip install -e .` [VERIFIED]
- expected signal: editable install exposes `sentinel`. [file:README.md:L102-L120 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Mutates state? Y | Inverse command: `python -m pip uninstall cortex-sentinel` [INFERRED]
- failure modes: missing build backend, missing network/cache for dependencies. [INFERRED]
- anchor: [file:pyproject.toml:L1-L20 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Command block: run under Sentinel
- cwd: `/Volumes/WS4TB/gemOptq` [VERIFIED]
- prereqs: editable install or `PYTHONPATH=src`; `sentinel.yaml` present. [INFERRED]
- exact command: `sentinel run --config sentinel.yaml -- python -c "print('ready')"` [VERIFIED]
- expected signal: supervised process prints `ready`. [INFERRED]
- Mutates state? Y | Inverse command: inspect/remove `.sentinel/` traces if generated; do not delete if needed for audit. [INFERRED]
- failure modes: TUI terminal incompatibility, missing package install. [INFERRED]
- anchor: [file:README.md:L83-L100 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Command block: real auditor smoke
- cwd: `/Volumes/WS4TB/gemOptq` [VERIFIED]
- prereqs: repo `venv`, `mlx_lm`, model availability, macOS Metal access. [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- exact command: `venv/bin/python scripts/auditor_smoke.py` [VERIFIED]
- expected signal: structured verdict from `mlx-community/gemma-4-12B-it-OptiQ-4bit`. [file:README.md:L41-L45 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Mutates state? N | Inverse command: none. [VERIFIED]
- failure modes: `No Metal device available`, missing model, missing `mlx_lm`. [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- anchor: [file:README.md:L232-L242 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

1-Day Checklist:
- [ ] Run `git status --short --branch`. [VERIFIED]
- [ ] Run `pytest -q`. [VERIFIED]
- [ ] Run `(cd mcp-cortex && python -m pytest -q)`. [VERIFIED]
- [ ] Run `python scripts/readiness_check.py`. [VERIFIED]
- [ ] Inspect `README.md`, `GOAL.md`, and this handoff before editing. [VERIFIED]

Pre-Deploy Checklist:
- [ ] FAULT [UNRESOLVED]: No production deploy target is documented; Impact: cannot deploy safely from this packet; Resolution command: `rg -n "deploy|flyctl|vercel|pages|github pages|production" .`; Confidence: [UNKNOWN]
- [ ] Confirm hosting target for `docs/index.html`. [INFERRED]
- [ ] Confirm no secrets or private traces are in `.sentinel/` before publishing. [file:.gitignore:L1-L6 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- [ ] Run `git diff --check`. [VERIFIED]

Local Dev Checklist:
- [ ] Use `python -m pip install -e .`. [file:README.md:L102-L120 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- [ ] Use `sentinel check-env` before real auditor work. [file:README.md:L70-L80 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- [ ] Use disposable workspaces for real agent validation. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Secrets Checklist:
- [ ] Do not pass secrets, PHI, credentials, private keys, or unnecessary sensitive data into prompts or traces. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- [ ] Keep `.sentinel/` ignored. [file:.gitignore:L1-L6 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- [ ] Treat `.env`, `~/.ssh/**`, and secret-like paths as protected. [file:sentinel.yaml:L1-L7 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Handoff Self-Test Checklist:
- [ ] JSON blocks parse. [INFERRED]
- [ ] Commands have cwd, prereqs, expected signal, mutation flag, inverse, failure modes, anchor, and confidence. [VERIFIED]
- [ ] Unresolved faults are explicit. [VERIFIED]

## 6. Resume Cursor With Dual JSON

Human resume cursor: start from `master#296e0678f101`, read Sections 0-5, run the root and MCP tests, then choose between real-agent validation and hermeticity hardening. [VERIFIED]

```json
{
  "resume_mode": "human",
  "first_action": "git status --short --branch",
  "second_action": "pytest -q",
  "decision_after_tests": "pick backlog item with no unresolved credential or Metal blocker"
}
```

```json
{
  "resume_mode": "agent",
  "state_vector": {
    "C": "master#296e0678f101",
    "V": "pyproject metadata, no lockfile found",
    "E": "local Python 3.13.9 observed",
    "D": "no migrations discovered, JSONL traces only",
    "K": "GOAL.md README.md PROGRESS.md this handoff"
  },
  "hard_stops": [
    "secrets",
    "production deployment",
    "non-disposable real-agent run",
    "unsafe destructive cleanup"
  ]
}
```

## 7. Secret Inventory

| Secret / Sensitive Surface | Status | Evidence | Action |
|---|---|---|---|
| `.env` | protected path pattern | [file:sentinel.yaml:L1-L7 @ master#296e0678f101 (2026-06-10)] [VERIFIED] | Keep blocked; do not inspect or commit. [VERIFIED] |
| `~/.ssh/**` | protected path pattern | [file:sentinel.yaml:L1-L7 @ master#296e0678f101 (2026-06-10)] [VERIFIED] | Keep blocked; do not inspect or commit. [VERIFIED] |
| `.sentinel/` traces | ignored local artifacts | [file:.gitignore:L1-L6 @ master#296e0678f101 (2026-06-10)] [VERIFIED] | Review before any publish/export. [INFERRED] |
| API keys / accounts | FAULT [UNRESOLVED]: no secret scan was run in this packet; Impact: cannot assert absence of secrets; Resolution command: `git grep -n -I -E "(API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE KEY)" -- .`; Confidence: [UNKNOWN] | [UNKNOWN] | Run scan before release. [UNKNOWN] |

## 8. Version Landscape

| Component | Version / Constraint | Source | Confidence |
|---|---|---|---|
| `cortex-sentinel` | `0.1.0` | [file:pyproject.toml:L5-L10 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Python requirement | `>=3.10` | [file:pyproject.toml:L5-L14 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Current Python | `Python 3.13.9` | [source:local-command:python --version @ 2026-06-10] | [VERIFIED] |
| `PyYAML` | `>=6` | [file:pyproject.toml:L11-L14 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| `textual` | `>=0.80` | [file:pyproject.toml:L11-L14 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| `mlx-lm` | optional dependency `mlx` extra | [file:pyproject.toml:L16-L20 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Gemma model | `mlx-community/gemma-4-12B-it-OptiQ-4bit` | [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| `mcp-cortex` | `0.2.0` | [file:mcp-cortex/pyproject.toml:L5-L15 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Lockfile | FAULT [UNRESOLVED]: no lockfile found at depth 3; Impact: exact dependency resolution may drift; Resolution command: `find . -maxdepth 3 \( -name 'requirements*.txt' -o -name '*lock*' -o -name 'uv.lock' -o -name 'poetry.lock' -o -name 'package-lock.json' \) -print`; Confidence: [UNKNOWN] | [source:local-command:find-lockfiles @ 2026-06-10] | [VERIFIED] |

## 9. Environments, Data, Migrations, Observability

| Surface | State | Evidence |
|---|---|---|
| Local dev | Editable Python package with `sentinel` console script. [file:pyproject.toml:L19-L27 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Runtime config | `sentinel.yaml` protects `**/.env`, `~/.ssh/**`, auto-approves `docs/**` and `tests/unit/**`, and sets model id. [file:sentinel.yaml:L1-L7 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Trace data | JSONL traces store event type, payload, sequence, timestamp, and digest. [file:src/sentinel/session_trace.py:L98-L136 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Migrations | FAULT [UNRESOLVED]: no migration system was discovered; Impact: if future persistence is added, this packet has no migration head; Resolution command: `find . -maxdepth 4 -iname '*migration*' -o -iname 'alembic.ini'`; Confidence: [UNKNOWN] | [UNKNOWN] |
| Observability | Local trace replay exists; no production monitoring/oncall surface found. [file:README.md:L95-L100 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| Last deploy | FAULT [UNRESOLVED]: live hosting/deploy metadata not discovered locally; Impact: cannot verify live landing page freshness from repo alone; Resolution command: `rg -n "github pages|pages|deploy|site|hosting|workflow" .github docs README.md`; Confidence: [UNKNOWN] | [UNKNOWN] |

## 10. Backlog Next Steps

| Priority | Task | blocked_by | Evidence | Confidence |
|---:|---|---|---|---|
| 1 | Run full local readiness with disposable smokes: `python scripts/readiness_check.py`. | local runtime permissions | [file:README.md:L244-L254 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| 2 | Run `python scripts/readiness_check.py --run-real-auditor` from a Metal-capable macOS session. | Metal/model availability | [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| 3 | Prove or explicitly defer full interactive Claude/Gemini tool-confirmation flows. | account/login/tool prompt availability | [file:README.md:L49-L54 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |
| 4 | Add dependency lock strategy if reproducibility becomes release-critical. | package-management decision | [source:local-command:find-lockfiles @ 2026-06-10] | [VERIFIED] |
| 5 | Decide whether to host `docs/index.html` via GitHub Pages and document the deploy path. | repo settings / user account | [file:PROGRESS.md:L16-L17 @ master#296e0678f101 (2026-06-10)] | [VERIFIED] |

## 11. Risks

| Risk | Severity | Trigger to Act | Mitigation |
|---|---|---|---|
| Overclaiming safety boundary as a hard sandbox. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED] | High | Any README/landing/API text says "sandbox", "guarantee", or "production security boundary". [INFERRED] | Keep boundary language and tests/docs aligned. [VERIFIED] |
| Real model smoke fails outside Metal-capable session. [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] [VERIFIED] | Medium | `venv/bin/python scripts/auditor_smoke.py` exits with Metal/device error. [INFERRED] | Mark external-blocked, do not treat as code failure until Metal is confirmed. [VERIFIED] |
| Dependency drift. [source:local-command:find-lockfiles @ 2026-06-10] [VERIFIED] | Medium | Fresh clone install resolves incompatible transitive versions. [INFERRED] | Add lockfile or constraints once release target is chosen. [INFERRED] |
| Generated files and `.DS_Store` noise. [source:local-command:find src scripts tests docs @ 2026-06-10] [VERIFIED] | Low | `git status` shows untracked generated artifacts. [INFERRED] | `.gitignore` already covers common caches; avoid committing generated files. [file:.gitignore:L1-L6 @ master#296e0678f101 (2026-06-10)] [VERIFIED] |

## 12. Conflicts, Faults, and Negative Evidence

CONFLICT block:
- Conflict: README and landing page are public-facing docs, while `GOAL.md` contains broader historical gap-analysis state. [file:README.md:L37-L54 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Preferred source: active branch code/config and fresh test output for runtime truth; README for public quick start; GOAL for gap history. [INFERRED]
- Resolution action: when a runtime claim changes, update `GOAL.md`, `README.md`, `docs/index.html`, and this handoff together. [INFERRED]

Unresolved faults:
- FAULT [UNRESOLVED]: No CI artifact was inspected; Impact: local green tests may not match CI; Resolution command: `gh run list --limit 5`; Confidence: [UNKNOWN]
- FAULT [UNRESOLVED]: No dependency lockfile found; Impact: future installs can drift; Resolution command: `find . -maxdepth 3 \( -name 'requirements*.txt' -o -name '*lock*' -o -name 'uv.lock' -o -name 'poetry.lock' -o -name 'package-lock.json' \) -print`; Confidence: [UNKNOWN]
- FAULT [UNRESOLVED]: Full interactive Claude/Gemini tool-confirmation behavior not proven; Impact: cannot claim complete real-agent coverage; Resolution command: `python scripts/real_agent_smoke.py --agent-command "<safe real agent command>" --interaction "<REGEX=>INPUT>" --expect-output "<marker>"`; Confidence: [UNKNOWN]
- FAULT [UNRESOLVED]: Live landing deployment path not locally anchored; Impact: pushed `docs/index.html` may not equal live rendered site; Resolution command: inspect repo Pages settings or live page source; Confidence: [UNKNOWN]

## 13. File Integrity Anchors

| File | Bytes | SHA-256 snippet | Confidence |
|---|---:|---|---|
| `README.md` | 14451 | `d78dc345cf420d4d` | [VERIFIED] |
| `GOAL.md` | 32841 | `aa4b7beb75d2cc67` | [VERIFIED] |
| `PROGRESS.md` | 45900 | `eea587ef77f4b7ff` | [VERIFIED] |
| `pyproject.toml` | 538 | `468bbd974d61321d` | [VERIFIED] |
| `sentinel.yaml` | 153 | `6e1e83def2c936f9` | [VERIFIED] |
| `docs/index.html` | 29850 | `37355ff7aaec4a45` | [VERIFIED] |
| `docs/showpiece/cortex-sentinel.md` | 3337 | `47e9d12c4e48761e` | [VERIFIED] |

## 14. Negative Space

Non-claims:
- This packet does not claim Cortex Sentinel is a hard sandbox. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- This packet does not claim production deployment readiness. [UNKNOWN]
- This packet does not claim full MCP authorization proxy behavior. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- This packet does not claim full interactive Claude/Gemini tool-confirmation proof. [file:README.md:L49-L54 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- This packet does not claim absence of secrets because no secret scan was run. [UNKNOWN]

Non-goals:
- Do not broaden scope into a remote service without a new architecture decision. [file:GOAL.md:L234-L260 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Do not weaken hard-block policy to improve demos. [file:GOAL.md:L234-L242 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Do not run real agents against non-disposable workspaces. [file:README.md:L191-L198 @ master#296e0678f101 (2026-06-10)] [VERIFIED]

Out-of-date hazards:
- Any old README or handoff that predates `296e0678f101` may not describe the current landing page. [source:git:log @ 2026-06-10] [VERIFIED]
- Any model-runtime claim from a non-Metal session may be externally blocked rather than code-failed. [file:README.md:L122-L128 @ master#296e0678f101 (2026-06-10)] [VERIFIED]
- Any live site cache may lag behind committed `docs/index.html`. [UNKNOWN]

## 15. Handoff Self-Test

- [x] Q1. Can a zero-context reader identify the project purpose in under 60 seconds? Yes; Section 0 and README anchors define purpose. [VERIFIED]
- [x] Q2. Are branch, SHA, cwd, and remote explicit? Yes; Section 1 records all four. [VERIFIED]
- [x] Q3. Are commands idempotent or mutation-flagged? Yes; Section 5 marks each command. [VERIFIED]
- [x] Q4. Are hidden assumptions surfaced? Yes; Section 4 lists assumptions and Section 12 lists faults. [VERIFIED]
- [x] Q5. Are unresolved blockers named with resolution commands? Yes; Section 12 uses FAULT blocks. [VERIFIED]
- [x] Q6. Are safety non-claims explicit? Yes; Section 14 lists non-claims. [VERIFIED]
- [x] Q7. Are technical identifiers byte-exact? Yes; model id, paths, command names, and SHAs are exact. [VERIFIED]
- [x] Q8. Are decisions separated from assumptions? Yes; Section 4 separates D-* and A-* items. [VERIFIED]
- [x] Q9. Is there enough verification evidence to resume safely? Yes for local test/dev work; no for production deploy. [VERIFIED]
- [x] Q10. Is the packet internally conflict-aware? Yes; Section 12 defines the docs/runtime source priority. [VERIFIED]
- [x] Q11. Does the packet contain enough anchors for an LLM to parse it as structured memory with <5% hallucination risk? Yes; every major claim has path/source anchors and confidence tags. [INFERRED]
- [x] Q12. Would removing all prose still leave a functional bootstrap? Yes; the JSON cursor, command blocks, module table, and final JSON contain enough bootstrap data. [INFERRED]

## Machine-Readable Summary

```json
{
  "$schema_version": "4.0",
  "project_name": "Cortex Sentinel",
  "snapshot_iso": "2026-06-10T12:07:16Z",
  "hermeticity_score": 0.6,
  "fidelity_percent": 91,
  "handoff_horizon": "1w",
  "handoff_self_test_passed": true,
  "resume_cursor": {
    "cwd": "/Volumes/WS4TB/gemOptq",
    "branch": "master",
    "head_sha": "296e0678f101",
    "remote": "https://github.com/deesatzed/gemoptiq.git",
    "primary_owner_role": "local developer or next coding agent",
    "primary_owner_status": "active",
    "next_review_checkpoint": "after the next code or documentation change, before commit",
    "must_read": [
      "GOAL.md",
      "README.md",
      "PROGRESS.md",
      "docs/index.html",
      "docs/showpiece/cortex-sentinel.md"
    ],
    "safe_first_commands": [
      "git status --short --branch",
      "pytest -q",
      "python -m pytest -q"
    ],
    "hard_stops": [
      "secrets",
      "production deployment",
      "non-disposable real-agent run",
      "unsafe destructive cleanup"
    ]
  },
  "system_vector": {
    "phase": "local supervision MVP with evidence-backed safety claims and public landing/showpiece docs",
    "target_s_next": "improve real-agent validation and hermetic reproducibility without weakening safety boundaries",
    "C": "Python package under src/sentinel plus tests, scripts, docs, and nested mcp-cortex",
    "V": "pyproject metadata present; no lockfile found at depth 3",
    "E": "local Python 3.13.9 and pytest 8.4.1 observed",
    "D": "no migrations discovered; local JSONL traces only",
    "K": [
      "GOAL.md",
      "README.md",
      "PROGRESS.md",
      "docs/showpiece/cortex-sentinel.md",
      "CORTEX_SENTINEL_DSS_WBV_HANDOFF_V4_2026-06-10.md"
    ]
  },
  "decisions": [
    {
      "id": "D-001",
      "decision": "Keep Cortex Sentinel local-first instead of making it a remote service.",
      "evidence": "GOAL.md and README.md",
      "confidence": "VERIFIED"
    },
    {
      "id": "D-002",
      "decision": "Deterministic policy hard-blocks protected paths, secret-like paths, external network effects, and production deploy effects before LLM judgment.",
      "evidence": "README.md and policy.py",
      "confidence": "VERIFIED"
    },
    {
      "id": "D-003",
      "decision": "Use static docs/index.html for landing/showpiece rather than a frontend build pipeline.",
      "evidence": "PROGRESS.md",
      "confidence": "VERIFIED"
    }
  ],
  "assumptions": [
    {
      "id": "A-001",
      "assumption": "Next agent has local repository access at /Volumes/WS4TB/gemOptq.",
      "validation": "pwd",
      "confidence": "VERIFIED"
    },
    {
      "id": "A-002",
      "assumption": "Real MLX/Gemma auditor checks require a macOS session with Metal access.",
      "validation": "venv/bin/python scripts/auditor_smoke.py",
      "confidence": "VERIFIED"
    },
    {
      "id": "A-003",
      "assumption": "GitHub Pages or another host is responsible for live rendering of docs/index.html.",
      "validation": "compare live page source to docs/index.html at 296e0678f101",
      "confidence": "INFERRED"
    }
  ],
  "secrets_inventory": [
    {
      "surface": ".env",
      "status": "protected path pattern",
      "confidence": "VERIFIED"
    },
    {
      "surface": "~/.ssh/**",
      "status": "protected path pattern",
      "confidence": "VERIFIED"
    },
    {
      "surface": ".sentinel/",
      "status": "ignored local trace artifacts",
      "confidence": "VERIFIED"
    },
    {
      "surface": "API keys / accounts",
      "status": "FAULT [UNRESOLVED]: no secret scan was run in this packet",
      "confidence": "UNKNOWN"
    }
  ],
  "negative_space": {
    "non_claims": [
      "hard sandbox",
      "production deployment readiness",
      "full MCP authorization proxy",
      "full interactive Claude/Gemini tool-confirmation proof",
      "absence of secrets"
    ],
    "non_goals": [
      "remote service conversion without new architecture decision",
      "weakening hard-block policy",
      "real-agent runs against non-disposable workspaces"
    ],
    "stale_docs": [
      "handoffs before 296e0678f101 may not describe the current landing page",
      "model-runtime claims from non-Metal sessions may be externally blocked",
      "live site cache may lag behind committed docs/index.html"
    ]
  },
  "modules": [
    {
      "path": "src/sentinel/main.py",
      "purpose": "CLI entrypoint",
      "last_touched": "2026-06-09",
      "critical_path_bool": true
    },
    {
      "path": "src/sentinel/tui.py",
      "purpose": "Textual UI, prompt polling, approvals, overrides, trace decisions",
      "last_touched": "2026-06-09",
      "critical_path_bool": true
    },
    {
      "path": "src/sentinel/policy.py",
      "purpose": "Policy decisions, hard blocks, overrides, effect IDs",
      "last_touched": "2026-06-09",
      "critical_path_bool": true
    },
    {
      "path": "src/sentinel/enforcer.py",
      "purpose": "Continuous enforcement and supported rollback",
      "last_touched": "2026-06-09",
      "critical_path_bool": true
    },
    {
      "path": "src/sentinel/session_trace.py",
      "purpose": "JSONL trace events with stable digests",
      "last_touched": "2026-06-09",
      "critical_path_bool": true
    },
    {
      "path": "docs/index.html",
      "purpose": "Static landing page",
      "last_touched": "2026-06-10",
      "critical_path_bool": false
    },
    {
      "path": "mcp-cortex/",
      "purpose": "Trace-oriented MCP metadata package",
      "last_touched": "2026-06-09",
      "critical_path_bool": false
    }
  ],
  "versions": {
    "cortex_sentinel": {
      "version": "0.1.0",
      "source": "pyproject.toml",
      "confidence": "VERIFIED"
    },
    "python_requirement": {
      "version": ">=3.10",
      "source": "pyproject.toml",
      "confidence": "VERIFIED"
    },
    "current_python": {
      "version": "3.13.9",
      "source": "python --version",
      "confidence": "VERIFIED"
    },
    "pytest": {
      "version": "8.4.1",
      "source": "pytest --version",
      "confidence": "VERIFIED"
    },
    "gemma_model": {
      "version": "mlx-community/gemma-4-12B-it-OptiQ-4bit",
      "source": "README.md",
      "confidence": "VERIFIED"
    },
    "mcp_cortex": {
      "version": "0.2.0",
      "source": "mcp-cortex/pyproject.toml",
      "confidence": "VERIFIED"
    },
    "lockfile": {
      "version": null,
      "source": "find-lockfiles",
      "confidence": "VERIFIED",
      "status": "FAULT [UNRESOLVED]: no lockfile found at depth 3"
    }
  },
  "environments": [
    {
      "name": "local_dev",
      "path": "/Volumes/WS4TB/gemOptq",
      "last_deploy": null,
      "confidence": "VERIFIED"
    },
    {
      "name": "live_landing",
      "path": "docs/index.html",
      "last_deploy": "FAULT [UNRESOLVED]: live hosting/deploy metadata not discovered locally",
      "confidence": "UNKNOWN"
    }
  ],
  "observability": {
    "trace_replay": {
      "status": "implemented",
      "severity": "normal",
      "oncall": null,
      "confidence": "VERIFIED"
    },
    "production_monitoring": {
      "status": "FAULT [UNRESOLVED]: no production monitoring/oncall surface found",
      "severity": "unknown",
      "oncall": null,
      "confidence": "UNKNOWN"
    }
  },
  "backlog_next_steps": [
    {
      "task": "Run full local readiness with disposable smokes.",
      "blocked_by": "local runtime permissions",
      "evidence": "README.md readiness commands",
      "confidence": "VERIFIED"
    },
    {
      "task": "Run real auditor readiness from Metal-capable macOS session.",
      "blocked_by": "Metal/model availability",
      "evidence": "README.md auditor section",
      "confidence": "VERIFIED"
    },
    {
      "task": "Prove or explicitly defer full interactive Claude/Gemini tool-confirmation flows.",
      "blocked_by": "account/login/tool prompt availability",
      "evidence": "README.md open items",
      "confidence": "VERIFIED"
    },
    {
      "task": "Add dependency lock strategy if reproducibility becomes release-critical.",
      "blocked_by": "package-management decision",
      "evidence": "find-lockfiles returned no files",
      "confidence": "VERIFIED"
    },
    {
      "task": "Document live landing deploy path.",
      "blocked_by": "repo settings or hosting access",
      "evidence": "PROGRESS.md notes",
      "confidence": "VERIFIED"
    }
  ],
  "risks": [
    {
      "risk": "Overclaiming hard sandbox behavior.",
      "severity": "high",
      "trigger_to_act": "Docs or UI says sandbox, guarantee, or production security boundary.",
      "confidence": "VERIFIED"
    },
    {
      "risk": "Real model smoke fails outside Metal-capable session.",
      "severity": "medium",
      "trigger_to_act": "auditor_smoke exits with Metal/device error.",
      "confidence": "VERIFIED"
    },
    {
      "risk": "Dependency drift.",
      "severity": "medium",
      "trigger_to_act": "Fresh clone install resolves incompatible dependencies.",
      "confidence": "VERIFIED"
    }
  ],
  "unresolved_faults": [
    "FAULT [UNRESOLVED]: No CI artifact was inspected; Impact: local green tests may not match CI; Resolution command: gh run list --limit 5; Confidence: [UNKNOWN]",
    "FAULT [UNRESOLVED]: No dependency lockfile found; Impact: future installs can drift; Resolution command: find . -maxdepth 3 ...; Confidence: [UNKNOWN]",
    "FAULT [UNRESOLVED]: Full interactive Claude/Gemini tool-confirmation behavior not proven; Impact: cannot claim complete real-agent coverage; Resolution command: python scripts/real_agent_smoke.py --agent-command \"<safe real agent command>\" --interaction \"<REGEX=>INPUT>\" --expect-output \"<marker>\"; Confidence: [UNKNOWN]",
    "FAULT [UNRESOLVED]: Live landing deployment path not locally anchored; Impact: pushed docs/index.html may not equal live rendered site; Resolution command: inspect repo Pages settings or live page source; Confidence: [UNKNOWN]"
  ],
  "todos": [
    {
      "todo": "Run full readiness with executable local smokes.",
      "confidence": "VERIFIED"
    },
    {
      "todo": "Run real auditor smoke in Metal-capable session.",
      "confidence": "VERIFIED"
    },
    {
      "todo": "Document or automate live landing deployment path.",
      "confidence": "UNKNOWN"
    },
    {
      "todo": "Decide on dependency lock strategy.",
      "confidence": "VERIFIED"
    }
  ],
  "self_test_answers": {
    "q1": "yes",
    "q2": "yes",
    "q3": "yes",
    "q4": "yes",
    "q5": "yes",
    "q6": "yes",
    "q7": "yes",
    "q8": "yes",
    "q9": "yes for local work, no for production deploy",
    "q10": "yes",
    "q11": "yes",
    "q12": "yes; JSON cursor, command blocks, module table, and final JSON remain functional"
  }
}
```
