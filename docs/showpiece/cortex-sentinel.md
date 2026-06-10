# Cortex Sentinel Showpiece Brief

## One-Sentence Story

Cortex Sentinel is a local safety console that lets a developer run autonomous coding agents with deterministic policy, human approval, protected-file rollback evidence, and replayable traces.

## Why It Is A Showpiece

This repo is not just a wrapper script. It demonstrates a complete safety loop around local coding agents:

- It launches real local commands through a supervised runner.
- It distinguishes hard policy blocks from model-assisted review.
- It has a terminal UI for approve, block, pause, kill, and scoped override actions.
- It records decision evidence in local traces instead of relying on memory or chat summaries.
- It includes a readiness matrix and disposable smokes that separate proven behavior from open gaps.
- It keeps the limitation visible: this is supervision, not a hard sandbox.

The landing page should make that loop legible in the first screen: agent request, effect classification, policy decision, rollback event, and trace replay.

## Demo Narrative

Use this sequence for a short walkthrough:

1. Open `docs/index.html`.
2. Explain that coding agents can edit files and run commands quickly, so they need a local control layer.
3. Point to the hero console: the agent proposes a risky command, Sentinel classifies it, and policy blocks it.
4. Point to the decision queue: ambiguous work waits for the human.
5. Point to rollback evidence: a protected `.env` write is detected, suspended, and rolled back in a disposable smoke.
6. Point to trace replay: the decision trail can be audited later.
7. Close with the boundary: proven supervision, not guaranteed containment.

## Verified Claims To Use

These are appropriate public claims for the README and landing page:

- Root test suite has passed with `142 passed`.
- Nested MCP-Cortex tests have passed with `11 passed`.
- A fresh independent GitHub clone passed after the optional MCP-Cortex skip fix with `140 passed, 2 skipped`.
- Codex full-screen TUI smoke has proven workspace trust, command approval, and harmless output.
- Claude Code startup trust-prompt control has been proven in a disposable workspace.
- Continuous protected-file enforcement has proven suspend plus rollback for a no-prompt `.env` write.
- The real MLX/Gemma auditor has produced structured output in a Metal-capable local session.

## Claims To Avoid

Do not describe Cortex Sentinel as:

- a hard sandbox;
- a complete terminal emulator;
- a production security boundary;
- a cloud authorization service;
- a full MCP proxy;
- proven for full interactive Claude/Gemini tool-confirmation behavior.

## Landing Page Checklist

- First viewport says "Cortex Sentinel" clearly.
- First viewport explains why someone would want it.
- First viewport shows the agent supervision loop visually.
- Proof section uses measured or explicitly named evidence.
- Boundary section makes the limitation impossible to miss.
- Try-it section uses real repo commands.

## README Checklist

- Explain the app to a non-specialist.
- Link to the landing page.
- Link to the GOAL proof contract.
- Preserve tested sections: Quick Start, Installation, Configuration Reference, Safety Boundary, Troubleshooting, and Examples.
- Preserve core command strings used by README tests.
- Separate "what is proven" from "what is open."
