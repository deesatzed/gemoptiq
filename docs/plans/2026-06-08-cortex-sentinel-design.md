# Design Document: Cortex Sentinel

**Date:** 2026-06-08
**Status:** Approved
**Topic:** Sovereign Overseer for AI Agents

## 1. Vision & Purpose
Cortex Sentinel is a local, high-performance "Overseer" application designed for Software Engineers who use high-autonomy AI agents (e.g., Claude Code, Gemini-CLI). It solves the "Trust vs. Autonomy" gap by providing a safety governance layer that monitors agents in real-time, auto-approves low-risk tasks, and kills processes that drift into unsafe behavior.

## 2. Core Architecture
- **Sidecar Auditor:** The Sentinel runs as a parent process, spawning the target agent (e.g., `claude code`) as a child. It monitors `stdin`/`stdout` and file system events.
- **Inference Engine:** **Gemma 4 12B** (MLX) performs semantic auditing of the agent's behavior.
- **Policy Engine:** **mcp-cortex** provides deterministic rule enforcement and append-only tracing.

## 3. Key Features
### 3.1. Intelligent Auto-Yes
- Monitors agent output for confirmation prompts.
- Gemma 4 compares the agent's stated intent with the proposed file changes.
- If the action is pre-approved (via `sentinel.yaml`) and the semantic risk is low, the Sentinel injects `y\n` automatically.

### 3.2. Drift Detection & Enforcement
- **Drift:** When an agent's physical actions (file edits) diverge from its stated goals.
- **Enforcement:**
    - **Suspend (`SIGSTOP`):** Pauses the agent for human review when drift is detected.
    - **Terminate (`SIGKILL`):** Immediate shutdown on critical policy violations (e.g., accessing `.env`).

### 3.3. Hybrid Policy Management
- **Static (`sentinel.yaml`):** Global rules for protected paths and auto-approval zones.
- **Dynamic (Chat):** Per-session verbal overrides (e.g., "Allow all edits in `src/ui` for this hour").

## 4. UI/UX: The Trust HUD
A Terminal User Interface (TUI) providing:
- **Agent Output:** Dimmed view of the monitored agent.
- **Reasoning Stream:** Live feed of Gemma 4's `<|channel>thought` process.
- **Drift Meter:** Visual representation of trust levels.
- **Kill Switch:** Immediate manual override.

## 5. Technical Stack
- **Runtime:** Python 3.13
- **Inference:** `mlx-lm` (patched for `gemma4_unified`)
- **Policy:** `mcp-cortex`
- **TUI:** `rich` / `textual`
- **FS Monitoring:** `watchdog`

## 6. Success Criteria
- **Safety:** Zero unauthorized writes to protected paths.
- **Efficiency:** 90% reduction in manual "Yes" confirmations for safe paths.
- **Low Overhead:** Minimal latency impact on the monitored agent.
