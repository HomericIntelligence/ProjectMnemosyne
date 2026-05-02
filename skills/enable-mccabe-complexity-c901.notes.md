# Reference Notes: enable-mccabe-complexity-c901

## Session Context

**Date**: 2026-03-05
**Project**: ProjectScylla
**Issue**: #1377 — Enable C901 (McCabe complexity) rule in ruff configuration
**PR**: #1422
**Branch**: 1377-auto-impl

## Background

Issue #1377 was a follow-up from #1356, where 15+ functions had `# noqa: C901` directives
suppressing McCabe complexity warnings. Those were removed during #1356 (unused noqa for
non-enabled rule). Issue #1377 asked to either enable C901 and refactor, or document the
decision not to enable it.

## Key Decisions

1. **max-complexity = 12** (not 10) — reduces noise from inherently complex orchestration code
2. **Suppress all CC > 12 with annotated noqa** — refactoring orchestration/pipeline code
   creates indirection without clarity gain
3. **No new files created** — purely configuration + inline suppressions

## Violation Discovery

Ran: `pixi run ruff check --select C901 scylla/ scripts/`

Critical pitfall: `--max-complexity` is NOT a valid ruff CLI flag. The plan incorrectly specified:
```bash
pixi run ruff check --select C901 --max-complexity 10 scylla/ scripts/
```
This produces: `error: unexpected argument '--max-complexity' found`

The correct approach is to set max-complexity in `pyproject.toml` and run ruff normally.

## Files Modified

- `pyproject.toml` — added `C901` to `select`, added `[tool.ruff.lint.mccabe]` section
- 29 source files — added `# noqa: C901  # <rationale>` to complex function definitions

## Named Functions Suppressed

From issue context: `run_llm_judge`, `_run_mojo_pipeline`, `_run_python_pipeline`,
`check_configs`, `detect_shadowing`, `build_resource_suffix`, `load` (config loader),
plus ~35 others.

## Test Results

- `pixi run ruff check scylla/ scripts/` → All checks passed!
- `pixi run python -m pytest tests/ -v` → 4434 passed, 1 skipped

## Implementation Was Pre-Complete

When the session started, the implementation was already done (commit `1c23455`). The task
was simply to run the retrospective and create the PR. This confirms the workflow is
straightforward once the CLI flag pitfall is known.
