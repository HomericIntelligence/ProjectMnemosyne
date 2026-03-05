# Skill: ruff-c901-mccabe-complexity

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-05 |
| Category | tooling |
| Objective | Enable C901 McCabe complexity rule in ruff with a pragmatic threshold |
| Outcome | Success — C901 enabled at max-complexity=12, all 65 violations resolved |
| Issue | #1377 (follow-up from #1356) |

## When to Use

- Enabling a new ruff lint rule across a large codebase with existing violations
- Deciding between refactoring complex functions vs. annotated suppression
- Setting a McCabe complexity threshold that balances strictness with practicality
- Documenting intentional complexity suppressions so future developers understand rationale

## Verified Workflow

### 1. Audit violations at candidate threshold

```bash
# Count violations at complexity=10 (default)
pixi run ruff check scylla/ scripts/ --select C901 2>&1 | grep "C901"

# Get file:line locations for all violations
pixi run ruff check scylla/ scripts/ --select C901 2>&1 | grep -E "C901|-->" | paste - -
```

### 2. Choose threshold

- Default threshold (10) produced 65 violations
- Threshold 12 accepted 22 functions (complexity 11–12) as within bounds
- Threshold 12 flagged 43 functions (complexity > 12) for suppression
- Rule: accept complexity 11–12 for orchestration/CLI code; suppress > 12 with rationale

### 3. Update pyproject.toml

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

### 4. Add annotated suppressions

Place `# noqa: C901  # <rationale>` on the **first line** of the function def (the `def` line), not on the return type annotation line. For multi-line signatures this is critical.

```python
# CORRECT — noqa on the def line
def run_subtest(  # noqa: C901  # orchestration with many retry/outcome paths
    self,
    tier_id: TierID,
    ...
) -> SubTestResult:

# WRONG — noqa on closing paren/return type line (ruff ignores it)
def run_subtest(
    self,
    ...
) -> SubTestResult:  # noqa: C901  # this does NOT suppress the violation
```

### 5. Rationale categories used

| Rationale | Functions |
|-----------|-----------|
| `orchestration with many retry/outcome paths` | `run`, `run_subtest`, `_implement_all`, `_run_batch`, `cmd_run`, `rerun_experiment`, `rerun_judges_experiment` |
| `pipeline with sequential conditional stages` | `_run_mojo_pipeline`, `_run_python_pipeline` |
| `CLI dispatch with many command branches` | `main` (multiple), `cmd_run`, `cmd_visualize` |
| `validation with many independent rule checks` | `validate_frontmatter`, `check_configs` |
| `config loader with many format/version branches` | `load`, `load_run`, `load_rubric_weights` |
| `workspace state detection with many file patterns` | `_get_workspace_state`, `_get_workspace_files`, `_merge_tier_resources` |
| `action map with many tier state branches` | `build` (TierActionBuilder) |
| `text report formatting with many conditional branches` | `format_text` |
| `AST traversal with many node type branches` | `detect_shadowing` |

### 6. Verify and run tests

```bash
# Verify C901 only
pixi run ruff check scylla/ scripts/ --select C901

# Verify all rules
pixi run ruff check scylla/ scripts/

# Run full test suite
pixi run python -m pytest tests/ -v
```

## Failed Attempts

### Placing noqa on return type line of multi-line signatures

**What was tried:** For multi-line function signatures, placed `# noqa: C901` on the closing `) -> ReturnType:` line.

**Why it failed:** Ruff reports C901 violations at the line where `def` appears. For multi-line signatures, the `def` keyword is on a different line than the return type. Ruff only checks noqa on the line it reports the error, so the suppression was silently ignored and the violation persisted.

**Fix:** Always place `# noqa: C901` on the `def` line itself.

### Using --max-complexity CLI flag

**What was tried:** `pixi run ruff check scylla/ scripts/ --select C901 --max-complexity 10`

**Why it failed:** Ruff does not accept `--max-complexity` as a CLI flag. The threshold must be configured in `pyproject.toml` under `[tool.ruff.lint.mccabe]`.

## Results & Parameters

### Final pyproject.toml config

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

### Violation summary

| Complexity Range | Count | Action |
|-----------------|-------|--------|
| > 12 (suppressed) | 43 | `# noqa: C901` with rationale |
| 11–12 (accepted) | 22 | No change needed |
| Total at threshold 10 | 65 | — |

### Files modified

- `pyproject.toml` — add C901 to select, add mccabe section
- 29 source files — add annotated `# noqa: C901` suppressions

### Test results

- 4434 passed, 1 skipped
- Combined coverage: 75.23%
- All ruff checks clean
