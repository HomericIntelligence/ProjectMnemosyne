# Expand Ruff Rule Set Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #756 - Expand ruff rule set with B, S, C90, SIM, RUF rules |
| **Objective** | Enable 5 additional ruff rule sets, fix all violations, document suppressed rules with rationale |
| **Outcome** | ✅ Success — 583 violations fixed across 104 files, all pre-commit hooks pass, 2396 tests pass |

## When to Use

Use this skill when:

- Expanding a ruff configuration to include new rule sets (B, S, C90, SIM, RUF or others)
- Performing a bulk code quality uplift across a large codebase
- Need to distinguish between real violations to fix vs. false positives to suppress with rationale
- Setting up McCabe complexity thresholds for the first time

## Verified Workflow

### 1. Discovery Phase — Scope the Work

Before touching `pyproject.toml`, run discovery to count violations per rule:

```bash
# Count violations per rule code
pixi run ruff check --select B,S,C90,SIM,RUF scylla/ scripts/ 2>&1 \
  | grep -oP "^(B|S|C9|SIM|RUF)\d+" | sort | uniq -c | sort -rn
```

This gives a clear picture of scale before committing to any approach.

### 2. Update pyproject.toml — Add Rules and Ignores Together

Add all new rules AND their documented global ignores in one shot. Never add rules without also deciding what gets ignored:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "RUF", "B", "SIM", "C90", "S"]
ignore = [
    # ... existing ignores ...
    # RUF001/RUF002: Unicode math/scientific symbols are intentional notation
    "RUF001",
    "RUF002",
    # S101: assert for invariant validation; intentional in test files
    "S101",
    # S603/S607: subprocess with controlled/trusted input — not user-facing
    "S603",
    "S607",
    # S105/S106: false positives — metric names matching password heuristics
    "S105",
    "S106",
    # S110: try/except/pass for best-effort cleanup (with comment documenting intent)
    "S110",
    # S112: try/except/continue for resilient iteration (with comment documenting intent)
    "S112",
    # S108: /tmp/ paths in test fixtures / PYTHONPYCACHEPREFIX — not security-sensitive
    "S108",
    # SIM117: nested `with` where inner is pytest.raises() — can't be merged
    "SIM117",
    # RUF003: en-dash in docstrings is intentional notation
    "RUF003",
    # B017: broad pytest.raises(Exception) with inline comment naming actual type
    "B017",
]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

**Key decision**: max-complexity = 12 (not 10) reduces noise from legitimately complex orchestration functions while still catching truly problematic code.

### 3. Auto-Fix Safe Violations First

Apply all safe auto-fixes before doing any manual work:

```bash
# Safe auto-fixes
pixi run ruff check --fix scylla/ scripts/ tests/

# Unsafe auto-fixes (review output carefully — these are usually correct)
pixi run ruff check --unsafe-fixes --fix scylla/ scripts/ tests/
```

**Unsafe fixes that are reliably correct:**
- `RUF022`: sorts `__all__` lists (always correct)
- `RUF005`: iterable unpacking instead of concatenation (always correct)
- `RUF059`: prefix unused unpacked variables with `_` (always correct)
- `SIM105`: `contextlib.suppress` conversion (correct when no important log is being omitted)
- `SIM102`: merge nested `if` with `and` (correct when no comment separates them)
- `SIM108`: ternary operator conversion (correct for simple if/else)
- `SIM118`: remove `.keys()` in `for x in dict.keys()` (always correct)
- `B007`: rename unused loop vars to `_var` (always correct)

### 4. Fix B904 Manually (No Auto-Fix Available)

B904 requires adding `from e` or `from None` to raise statements in except blocks. There is no auto-fix. Pattern:

```python
# BEFORE (B904 violation):
except SomeError as e:
    raise AnotherError("msg")

# AFTER:
except SomeError as e:
    raise AnotherError("msg") from e

# BEFORE (no variable):
except SomeError:
    raise AnotherError("msg")

# AFTER:
except SomeError:
    raise AnotherError("msg") from None
```

With 38 violations, use a sub-agent to process all files in parallel.

### 5. Add C901 noqa Comments for Complex Functions

Do NOT refactor complex orchestration functions to pass C901 — add documented suppressions:

```python
def run_subtest(  # noqa: C901  # subtest execution orchestration with many outcome paths
    ...
```

**Rationale threshold**: Functions with complexity > 12 that are inherently complex due to:
- CLI main functions with many command paths
- Orchestration functions with many retry/skip conditions
- Statistical computation pipelines
- Validation functions with many rule checks

### 6. Fix Line-Length Violations from Edits

After adding `from e`/`from None` and noqa comments, check for E501 violations:

```bash
pixi run ruff check --select E501 scylla/ scripts/ tests/
```

Fix by wrapping raise statements in parentheses:

```python
# BEFORE (too long):
raise SomeError("Very long message here") from None

# AFTER:
raise SomeError(
    "Very long message here"
) from None
```

### 7. Handle tests/ Directory Separately

Don't forget — pre-commit runs ruff on `tests/` too. After fixing source/scripts:

```bash
pixi run ruff check tests/ 2>&1 | grep -oP "^(RUF|SIM|B|C9|S)\d+" | sort | uniq -c | sort -rn
```

Apply the same auto-fix pass to tests/. Check if global ignores already cover test violations (S108, SIM117, B017 often appear in tests and are legitimately false positives there).

### 8. Verify Before Committing

```bash
# Ruff clean across all directories
pixi run ruff check scylla/ scripts/ tests/

# Format check passes
pixi run ruff format --check scylla/ scripts/ tests/

# Full pre-commit
pixi run pre-commit run --all-files

# Tests still pass with adequate coverage
pixi run python -m pytest tests/ -v
```

**Critical**: Stage ALL unstaged files before committing — pre-commit hooks stash unstaged changes and may fail if format changes conflict with stashed content.

## Failed Attempts

### Attempt 1: Committing with unstaged pixi.lock

**What was tried**: Staging source files and committing without `pixi.lock`

**Why it failed**: Pre-commit hooks stash unstaged files; format hook then modifies staged files but can't apply changes because the stash conflicts. Results in a loop of "Stashed changes conflicted with hook auto-fixes".

**Fix**: Always `git add pixi.lock` (or any other modified lockfiles) before committing.

### Attempt 2: Using --unsafe-fixes for SIM117 in test files

**What was tried**: `pixi run ruff check --select SIM117 --unsafe-fixes --fix tests/`

**Why it failed**: SIM117 violations where inner `with` is `pytest.raises()` cannot be auto-fixed — pytest semantics require `raises()` to be the innermost context manager. The auto-fixer correctly refuses.

**Fix**: Add `SIM117` to global ignore list with documented rationale.

### Attempt 3: Trying to fix all 35 C901 violations by refactoring

**What was considered**: Refactoring each complex function to reduce cyclomatic complexity

**Why it wasn't pursued**: Orchestration functions (run_subtest: 20, rerun_experiment: 21, build_resource_suffix: 22) have inherent complexity that can't be meaningfully reduced without introducing indirection that makes the code harder to understand. The correct approach is `# noqa: C901` with rationale.

**Lesson**: max-complexity = 12 (not 10) correctly filters out incidental complexity. Functions over 12 that are still legitimately complex warrant suppression, not refactoring.

## Results & Parameters

### Final pyproject.toml Configuration

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "RUF", "B", "SIM", "C90", "S"]
ignore = [
    "D100", "D104", "D203", "D213", "D417",  # existing D-rule ignores
    "RUF001", "RUF002",  # intentional math notation
    "RUF003",            # intentional en-dash in docstrings
    "S101",              # assert for invariant validation
    "S603", "S607",      # controlled subprocess calls
    "S105", "S106",      # metric-name strings flagged as passwords
    "S108",              # /tmp/ in test fixtures and PYTHONPYCACHEPREFIX
    "S110",              # try/except/pass for best-effort cleanup
    "S112",              # try/except/continue for resilient iteration
    "SIM117",            # pytest.raises() must be innermost context manager
    "B017",              # broad pytest.raises(Exception) with inline comment
]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

### Violation Scale (before fixes)

| Rule | Violations | Fixed | Suppressed (global) |
|------|-----------|-------|---------------------|
| S603 | 52 | 0 | 52 (controlled subprocess) |
| S607 | 49 | 0 | 49 (controlled subprocess) |
| B904 | 38 | 38 | 0 |
| C901 | 55 | 0 | 55 (noqa with rationale) |
| SIM105 | 18 | 18 | 0 |
| SIM102 | 15 | 15 | 0 |
| RUF022 | 15 | 15 | 0 |
| SIM108 | 12 | 12 | 0 |
| S108 | 131 | 1 | 130 (test fixtures) |
| SIM117 | 40 | 0 | 40 (pytest.raises pattern) |

### Test Results

```
2396 passed, 8 warnings in 51.74s
Coverage: 74.36% (threshold: 73%)
Pre-commit: All hooks passed
```

## Key Takeaways

1. **Discovery first**: Always count violations per rule before expanding — knowing scale upfront prevents surprises
2. **Global ignores with rationale**: Never add a rule and leave violations suppressed with bare `# noqa`; always include the rule code and a reason
3. **max-complexity = 12, not 10**: The ruff default of 10 generates too many false positives on orchestration code; 12 is the right threshold for this kind of codebase
4. **Unsafe fixes are safe for bulk cleanup**: RUF022/RUF005/SIM105/SIM108/B007 unsafe fixes are reliably correct and can be applied without manual review
5. **Stage everything before committing**: Lockfile changes (pixi.lock) must be staged or pre-commit hook conflicts will occur
6. **tests/ directory needs the same treatment**: Pre-commit runs ruff on tests/ too — don't forget it
7. **Sub-agents accelerate B904**: With 38 manual B904 fixes across many files, delegating to a sub-agent is faster than editing file-by-file in the main agent

## Related

- Issue #756: Expand ruff rule set with B, S, C90, SIM, RUF rules
- PR #965: Implementation PR
- Skill: `pre-commit-maintenance` — verifying hooks pick up pyproject.toml changes automatically
- Skill: `batch-pr-pre-commit-fixes` — handling pre-commit failures across phases
