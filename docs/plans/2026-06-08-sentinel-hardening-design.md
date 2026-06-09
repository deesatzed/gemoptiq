# Cortex Sentinel Hardening Design

**Date:** 2026-06-08
**Status:** Approved by user instruction: "proceed with all next steps"

## Purpose

Close the gap between the current Cortex Sentinel MVP and its documented role as a local safety layer for autonomous coding agents. The hardening pass keeps the current sidecar/TUI shape and adds deterministic checks around the LLM auditor instead of replacing the existing implementation.

## Approach

The implementation should be incremental and test-first:

1. Make the repo reproducible from the top-level with `pytest -q`.
2. Fix the nested MCP-Cortex demo import collision without rewriting the nested package.
3. Add a small Sentinel policy module that evaluates proposed file effects against `sentinel.yaml`.
4. Capture simple workspace file effects around prompts so the auditor and policy layer see more than the prompt text.
5. Add an optional MCP-Cortex bridge that records intent, policy decision, and result traces when the nested package is importable.
6. Add environment and smoke checks for the local MLX/Gemma dependency and child-process runner behavior.

## Architecture

Sentinel remains a parent process around an agent subprocess:

`SentinelTUI -> AgentRunner -> child agent`

The TUI will call:

`FileEffectObserver -> SentinelPolicy -> optional CortexPolicyBridge -> Auditor`

Policy should short-circuit the LLM where deterministic rules already say "block" or "allow". The LLM remains a semantic reviewer for ambiguous prompt/effect pairs.

## Non-Goals

- No production deployment.
- No secret handling beyond local path blocking.
- No broad rewrite of `mcp-cortex`.
- No claim that Sentinel is production authorization infrastructure.
- No real Claude/Gemini invocation that could touch user work without an explicit safe command.

## Acceptance Criteria

- `pytest -q` from `/Volumes/WS4TB/gemOptq` passes for the Sentinel suite.
- `python -m pytest -q` from `mcp-cortex/` passes.
- Protected path effects are blocked before LLM approval.
- Safe auto-approve path effects can be approved deterministically.
- Ambiguous effects still go through the auditor.
- Policy/audit decisions include traceable reasons.
- The docs identify remaining non-production limits.
