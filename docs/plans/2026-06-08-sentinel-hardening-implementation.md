# Cortex Sentinel Hardening Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Cortex Sentinel's MVP safety claims reproducible, policy-backed, and test-covered while preserving the current sidecar architecture.

**Architecture:** Add a deterministic local policy module and file-effect observer around the existing `SentinelTUI` audit path. Keep MCP-Cortex as a nested optional package and bridge to it through a small adapter, not direct cross-repo rewrites.

**Tech Stack:** Python 3.13, pytest, Textual, MLX-LM, YAML, optional nested `mcp-cortex`.

---

### Task 1: Reproducible Test Setup

**Files:**
- Create: `pytest.ini`
- Modify: `tests/test_auditor.py`
- Modify: `tests/test_runner.py`
- Modify: `tests/test_sentinel_config.py`
- Modify: `mcp-cortex/examples/__init__.py`

**Steps:**
1. Run `pytest -q` and preserve the current failure evidence.
2. Add top-level pytest config with `pythonpath = . src` and `testpaths = tests`.
3. Standardize Sentinel tests on `sentinel.*` imports.
4. Add `mcp-cortex/examples/__init__.py` so local examples beat installed `examples` packages.
5. Verify `pytest -q` from root and `python -m pytest -q` from `mcp-cortex/`.

### Task 2: Deterministic Sentinel Policy

**Files:**
- Create: `src/sentinel/policy.py`
- Create: `tests/test_policy.py`
- Modify: `src/sentinel/tui.py`

**Steps:**
1. Write failing tests for protected path block, auto-approve path allow, and ambiguous review.
2. Implement `FileEffect` and `SentinelPolicy.evaluate`.
3. Wire the policy into `SentinelTUI.perform_audit` before the LLM call.
4. Verify targeted and full tests.

### Task 3: File Effect Observation

**Files:**
- Create: `src/sentinel/effects.py`
- Create: `tests/test_effects.py`
- Modify: `src/sentinel/tui.py`

**Steps:**
1. Write failing tests for detecting created, modified, and deleted files under a workspace root.
2. Implement a lightweight snapshot/diff observer using `Path.rglob`.
3. Use the diff output as `observed_effect` context during prompt audits.
4. Verify targeted and full tests.

### Task 4: Optional MCP-Cortex Bridge

**Files:**
- Create: `src/sentinel/cortex_bridge.py`
- Create: `tests/test_cortex_bridge.py`
- Modify: `src/sentinel/tui.py`

**Steps:**
1. Write failing tests for bridge disabled when unavailable, and trace events when available.
2. Implement import-path setup for local `mcp-cortex/src` without requiring install.
3. Map Sentinel file effects to MCP-Cortex `Intent` and `CapabilityContract`.
4. Record blocked/allowed result events.
5. Verify targeted and full tests.

### Task 5: Environment and Smoke Checks

**Files:**
- Create: `src/sentinel/env_check.py`
- Create: `tests/test_env_check.py`
- Create: `scripts/sentinel_smoke.py`

**Steps:**
1. Write failing tests for MLX module missing, model-remapping missing, and model-remapping present.
2. Implement non-invasive environment check helpers.
3. Add a smoke script that runs Sentinel-adjacent runner behavior without launching a real high-autonomy agent.
4. Verify targeted and full tests.

### Task 6: Docs Refresh

**Files:**
- Modify: `REPO_MAP.md`
- Modify: `RISK_NOTES.md`
- Modify: `CORTEX_SENTINEL_DSS_WBV_HANDOFF.md` if needed.

**Steps:**
1. Update verified command table.
2. Reclassify resolved risks and remaining risks.
3. Keep non-production limits explicit.
4. Run final verification.
