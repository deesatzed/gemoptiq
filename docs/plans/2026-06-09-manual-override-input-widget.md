# Manual Override Input Widget Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use test-driven-development to implement this plan task-by-task.

**Goal:** Add a first-class keyboard-facing Textual input flow for arbitrary scoped allow overrides.

**Architecture:** `SentinelTUI` keeps the existing override store and `create_manual_allow_override()` helper as the single policy/trace path. A new `ManualOverrideScreen` modal owns text entry, submits a normalized path pattern on Enter, and dismisses with `None` on Escape/cancel. `SentinelTUI.action_manual_override()` opens the modal and creates the override only when a non-empty pattern is submitted.

**Tech Stack:** Python 3.13, Textual `ModalScreen`, `Input`, existing `SentinelTUI`, `SessionOverrideStore`, and pytest mounted `run_test` coverage.

---

### Task 1: Mounted Modal Input Test

**Files:**
- Modify: `tests/test_tui_policy_integration.py`
- Modify: `src/sentinel/tui.py`

**Step 1: Write failing test**

Add a mounted Textual test proving:
- `action_manual_override()` opens an input modal.
- Typing `src/manual/**` and pressing Enter creates an allow override.
- The trace event has `source: manual`.
- The modal is dismissed and the override applies to a matching file effect.

**Step 2: Run red test**

Run: `pytest -q tests/test_tui_policy_integration.py::test_mounted_manual_override_modal_creates_trace_visible_override`

Expected: fail because the action/modal does not exist.

**Step 3: Implement minimal modal**

Add `ManualOverrideScreen(ModalScreen[str | None])` with one `Input`, an Enter submit handler, Escape cancel binding, and a callback from `SentinelTUI.action_manual_override()`.

**Step 4: Run green test**

Run: `pytest -q tests/test_tui_policy_integration.py::test_mounted_manual_override_modal_creates_trace_visible_override`

Expected: pass.

### Task 2: Cancel/Empty Behavior

**Files:**
- Modify: `tests/test_tui_policy_integration.py`
- Modify: `src/sentinel/tui.py`

**Step 1: Write failing tests**

Add tests proving:
- Escape closes the modal without adding an override.
- Submitting whitespace records the existing manual no-op path and does not add an override.

**Step 2: Run red tests**

Run: `pytest -q tests/test_tui_policy_integration.py -q`

Expected: fail until cancel/empty behavior is wired.

**Step 3: Implement minimal behavior**

Use the existing `create_manual_allow_override()` helper for submitted values. It already handles empty patterns and hard-block precedence.

**Step 4: Run green tests**

Run: `pytest -q tests/test_tui_policy_integration.py`

Expected: pass.

### Task 3: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `GOAL.md`
- Modify: `RISK_NOTES.md`
- Modify: `REPO_MAP.md`
- Modify: `PROGRESS.md`

**Step 1: Update status docs**

Record that the TUI now has a keyboard-facing arbitrary override input, while hard-block precedence and traceability remain unchanged.

**Step 2: Verify**

Run:
- `pytest -q tests/test_tui_policy_integration.py tests/test_readme.py`
- `python -m py_compile src/sentinel/tui.py`
- `git diff --check`

Expected: all pass.
