# Freshman Landing Page Upgrade Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Cortex Sentinel landing page so a vibe-coding college freshman understands the problem, the workflow, concrete examples, and the safety boundary.

**Architecture:** Keep the landing page as standalone static HTML in `docs/index.html`. Use CSS-built screenshot panels and example flows instead of external image dependencies so the page remains portable and easy to host with GitHub Pages.

**Tech Stack:** Static HTML, CSS, existing Markdown docs, existing pytest/release checks.

---

### Task 1: Rewrite Landing Page Around Concrete User Problems

**Files:**
- Modify: `docs/index.html`

**Steps:**

1. Replace the abstract hero with a problem-first intro for vibe coding.
2. Add concrete problem cards: secret files, risky shell/network commands, deletes, and no audit trail.
3. Preserve clear product name and first-viewport value proposition.

### Task 2: Add Screenshot-Style Examples

**Files:**
- Modify: `docs/index.html`

**Steps:**

1. Add static screenshot panels showing blocked command, protected `.env` rollback, approval queue, and trace replay.
2. Use realistic command/result language from the repo.
3. Keep the examples honest about what is proven and what remains open.

### Task 3: Add Freshman-Friendly Walkthrough

**Files:**
- Modify: `docs/index.html`

**Steps:**

1. Add a "what happens step by step" section.
2. Explain the role of deterministic policy, the local auditor, human approval, and traces in plain language.
3. Add before/after comparison for running agents with and without Sentinel.

### Task 4: Update Project Progress

**Files:**
- Modify: `PROGRESS.md`

**Steps:**

1. Record the landing-page upgrade and its audience.
2. Note that screenshots are static UI examples, not new runtime screenshots.

### Task 5: Verify, Commit, Push

**Commands:**

```bash
python -c "from html.parser import HTMLParser; from pathlib import Path; p=HTMLParser(); p.feed(Path('docs/index.html').read_text()); p.close(); print('html-parse-ok')"
pytest -q tests/test_readme.py tests/test_release_check.py
python scripts/release_check.py --skip-wheel
git diff --check
git status --short --branch
git add docs/index.html docs/plans/2026-06-10-freshman-landing-page-upgrade.md PROGRESS.md
git commit -m "Improve landing page for vibe coding audience"
git push origin master
```
