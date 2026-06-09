# Approval UX Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use test-driven-development to implement this plan task-by-task.

**Goal:** Add a minimal, testable approval flow for review and confirm policy outcomes.

**Architecture:** `SentinelTUI` will keep one pending approval object for the current prompt. Deterministic allow/block behavior remains unchanged. Review and confirm decisions suspend the agent, log risk/effects/reason, and wait for explicit user approval or block actions.

**Tech Stack:** Python dataclasses, Textual bindings/actions, existing `SentinelTUI`, `PolicyDecision`, `SessionTraceStore`.

---

### Task 1: Pending Approval State

**Files:**
- Modify: `tests/test_tui_policy_integration.py`
- Modify: `src/sentinel/tui.py`

**Step 1: Write failing tests**

Add tests proving:
- `PolicyAction.CONFIRM` creates a pending approval, suspends the runner, does not call the auditor, and does not send input.
- `PolicyAction.REVIEW` with an auditor allow creates a pending approval instead of auto-sending `y`.
- pending approval includes prompt, file effects, policy decision, auditor verdict, and auditor reason.

**Step 2: Run the tests to verify they fail**

Run: `pytest -q tests/test_tui_policy_integration.py`

Expected: failures or errors around missing `pending_approval` behavior.

**Step 3: Implement minimal state**

Add a `PendingApproval` dataclass and `self.pending_approval = None`. For confirm/review outcomes, suspend the runner, set drift to 100, and store the pending approval. Keep allow/block behavior unchanged.

**Step 4: Run tests**

Run: `pytest -q tests/test_tui_policy_integration.py`

Expected: all tests pass.

### Task 2: Explicit Approve And Block Actions

**Files:**
- Modify: `tests/test_tui_policy_integration.py`
- Modify: `src/sentinel/tui.py`

**Step 1: Write failing tests**

Add tests proving:
- `action_approve_pending()` sends `y\n`, records `approve_pending`, resumes the runner if paused, clears pending approval, and sets drift to 0.
- `action_block_pending()` records `block_pending`, keeps/suspends the runner, clears pending approval, and sets drift to 100.
- actions without pending approval only log/record a no-op and do not touch the runner.

**Step 2: Run failing tests**

Run: `pytest -q tests/test_tui_policy_integration.py`

Expected: failures around missing action methods/bindings.

**Step 3: Implement actions**

Add `a` and `b` bindings. Implement explicit actions in `SentinelTUI` using existing runner, trace, and log helpers.

**Step 4: Verify**

Run:
- `pytest -q tests/test_tui_policy_integration.py tests/test_tui.py tests/test_tui_fixes.py`
- `pytest -q`

Expected: all pass.

### Task 3: Status Docs

**Files:**
- Modify: `GOAL.md`
- Modify: `PROGRESS.md`
- Modify: `RISK_NOTES.md`

**Step 1: Update status**

Record that the first-pass approval state/actions are implemented, while richer visual cards and manual screenshots remain open.

**Step 2: Verify formatting**

Run: `git diff --check`

Expected: exit 0.
