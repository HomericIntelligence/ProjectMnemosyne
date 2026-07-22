---
target_skill: architecture-import-time-assert-anti-pattern
date: 2026-07-22
---

# Project-specific evidence: Import-time Assert Anti-pattern

## Project
- predictive-coding-mojo.

## Registry
- `scripts/optimizers.py`, 24-name optimizer SSoT (baselines + exotics).
  Loaded under `pytest pythonpath = scripts` (see
  [`testing-dynamic-import-sys-path-resolution`](./testing-dynamic-import-sys-path-resolution.md)).

## Before
- Top-of-file: `assert len(OPTIMIZER_NAMES) == 24, "SSoT drift"`.
- Caught by a `code-reviewer-minimax-m3` pass on PR #107.

## After
- Top-of-file: `OPTIMIZER_NAMES: tuple[str, ...] = BASELINE_NAMES + EXOTIC_NAMES`
  (tuple-literal assignment, no assert).
- Comment marker at the assignment: `# 24 entries; see tests/test_optimizers_ssot.py`.

## Open follow-up
- `tests/test_optimizers_ssot.py` (drift-catcher test, not yet authored).
  Until it lands, the 24-name contract is convention-only.
