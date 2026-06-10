# README And Landing Showpiece Design

## Context

The repository had a factual README but no public landing page. That made the GitHub repo look unchanged from a product/showcase perspective even though the codebase had substantial evidence-backed functionality.

## Goal

Make Cortex Sentinel understandable and compelling from the repository front door while preserving truthful safety boundaries and existing verification surfaces.

## Selected Approach

Use three artifacts:

1. `README.md` as the GitHub front door.
2. `docs/index.html` as a standalone static landing page.
3. `docs/showpiece/cortex-sentinel.md` as the demo and claim-control brief.

This keeps the public story strong without hiding the actual proof matrix or overstating the security model.

## Alternatives Considered

- README-only polish: faster, but still leaves no landing page or visual product artifact.
- Full web app scaffold: more impressive visually, but unnecessary dependency and build surface for a documentation/showpiece task.
- Static HTML landing page: best fit because it is portable, reviewable, and can be opened directly or hosted by GitHub Pages later.

## Design Notes

- The landing hero uses a product-screen visual that shows the agent supervision loop instead of a generic marketing graphic.
- The README leads with purpose, user value, proof, and safety boundary before deeper setup details.
- The showpiece brief defines allowed claims and claims to avoid.
- The artifact should not claim hard sandboxing, complete MCP authorization, or full Claude/Gemini tool-confirmation proof.

## Verification

Required checks:

- `pytest -q tests/test_readme.py`
- `python scripts/release_check.py --skip-wheel`
- `git diff --check`

Broader checks should be run before pushing when time permits.
