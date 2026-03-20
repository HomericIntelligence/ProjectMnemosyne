---
name: enable-mccabe-complexity-c901
description: Enable C901 McCabe complexity rule in ruff for an existing Python project.
  Use when the codebase has complex functions (15+ branches) or when enabling C901
  as a follow-up to ruff rule set expansion.
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Enable C901 McCabe Complexity (ruff)

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Enable C901 (McCabe complexity) rule in ruff with max-complexity=12, suppress inherently complex orchestration/pipeline functions |
| **Outcome** | ✅ Success — C901 enabled, 43 functions suppressed with annotated noqa directives, 0 remaining violations |
| **Project** | ProjectScylla |
| **PR** | #1422 (Closes #1377) |

## When to Use This Skill

Use when:
- ✅ Adding C901 to an existing project that has `# noqa: C901` directives already (or previously had them and removed them)
- ✅ You want max-complexity enforcement with annotated suppressions for orchestration code
- ✅ Following up after a ruff rule set expansion that exposed C901 violations
- ✅ You need to decide between max-complexity=10 vs. 12

Do NOT use when:
- ❌ Adding C901 to a greenfield project with no complex functions (just add it to `select`, no further work needed)
- ❌ Refactoring all complex functions (often not worth it for orchestration code — annotated suppressions are better)

## Verified Workflow

### Phase 1: Discovery — Count Violations at Each Threshold

**IMPORTANT**: `ruff check` does NOT support a `--max-complexity` CLI flag. Configure threshold in `pyproject.toml`.

```bash
# Step 1: Temporarily set max-complexity=10 in pyproject.toml, then count
pixi run ruff check --select C901 scylla/ scripts/

# Step 2: Set max-complexity=12 and count again
# The difference tells you how many functions are in the 11-12 "noisy zone"
```

### Phase 2: Choose max-complexity Threshold

| Threshold | Use when |
|-----------|----------|
| **10** | Greenfield, small codebases, strict quality bar |
| **12** | Mature codebases with orchestration/pipeline code; reduces noise from inherently complex functions |

**Rule of thumb**: If you have >20 violations at 10 and most are orchestration/pipeline/CLI dispatch, use 12.

### Phase 3: Update `pyproject.toml`

```toml
[tool.ruff.lint]
# Add C901 to select list
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

### Phase 4: Categorize and Suppress Violations

For each remaining violation (complexity > 12), choose:

| Function Type | Action |
|--------------|--------|
| Pipeline orchestration (`_run_*_pipeline`) | Suppress — sequential conditional stages are inherent |
| LLM judge runners | Suppress — many retry/outcome paths |
| CLI dispatch (`main()`) | Suppress — many command branches are inherent |
| Config loaders | Suppress or refactor — depends on actual CC |
| Validation checkers | Suppress — many independent rule checks |
| Workspace/resource builders | Suppress — many conditional suffix/pattern rules |

**Suppress pattern** (always include rationale):

```python
def run_llm_judge(  # noqa: C901  # orchestration with many retry/outcome paths
    self,
    ...
```

**Rationale category strings** (copy-paste ready):
- `orchestration with many retry/outcome paths`
- `pipeline with sequential conditional stages`
- `CLI dispatch with many command branches`
- `validation with many independent rule checks`
- `config loader with many format/version branches`
- `workspace state detection with many file patterns`

### Phase 5: Verify

```bash
# Must show "All checks passed!"
pixi run ruff check --select C901 scylla/ scripts/

# Full rule check
pixi run ruff check scylla/ scripts/

# Tests must pass (no regressions from any refactoring)
pixi run python -m pytest tests/ -v
```

## Results & Parameters

### ProjectScylla Baseline (2026-03-05)

After enabling C901 with max-complexity=12 on ~18K line Python codebase:

| Threshold | Violations |
|-----------|-----------|
| CC > 10 | 65 |
| CC > 12 | 43 |
| CC > 12 (after suppressions) | **0** |

All 43 violations at CC > 12 were suppressed with annotated noqa directives. No refactoring was done — the complexity is inherent to the function responsibilities.

### Affected Function Categories

| Category | Count | Action |
|----------|-------|--------|
| Pipeline orchestration | ~8 | suppress |
| LLM judge runners | ~3 | suppress |
| CLI dispatch | ~10 | suppress |
| Config loaders | ~4 | suppress |
| Validation checkers | ~6 | suppress |
| Tier/experiment managers | ~8 | suppress |
| Miscellaneous complex | ~4 | suppress |

### Final `pyproject.toml` Configuration

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1422, issue #1377 | [notes.md](../../references/notes.md) |
