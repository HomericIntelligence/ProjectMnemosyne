---
name: mypy-full-compliance-workflow
description: 9-phase workflow to achieve full mypy compliance by fixing all suppressed
  error codes incrementally, decoupling tests/ overrides, and removing disable_error_code
  entirely
category: tooling
date: 2026-02-23
version: 1.0.0
user-invocable: false
---
# Mypy Full Compliance Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Issue** | #687 — Bring mypy to compliance for scylla/ and scripts/ |
| **Objective** | Incrementally fix all suppressed mypy error codes in scylla/ and scripts/, remove them from `disable_error_code`, and simplify tracking infrastructure |
| **Outcome** | ✅ Success — 72 errors fixed across 9 phases (PRs #1069–#1077); `disable_error_code` removed entirely; single-invocation regression guard |

## When to Use

Use this skill when:

- A project has incrementally-adopted mypy (multiple error codes in `disable_error_code`) and you want to achieve full compliance
- You need to systematically fix all suppressed type errors across a large codebase without breaking CI
- You want to decouple tests/ suppression from scylla/+scripts/ so error codes can be removed independently
- You are simplifying a per-directory mypy regression guard script

## Key Insights

### Phase Ordering Matters

Fix error codes in ascending violation-count order — easiest first builds momentum and avoids entangled fixes:

```
var-annotated (9) → misc (4) → index+attr-defined (7) → operator (13) → assignment (12) → arg-type (23) → union-attr (4)
```

### Phase Branches Must Stack

PRs target main but main hasn't merged them yet — each new phase branch must rebase off the prior phase branch, not main:

```bash
# Create phase N branch from phase N-1 (not from main)
git checkout 687-phase7-arg-type
git checkout -b 687-phase8-union-attr
# ... make changes, commit ...

# If you accidentally branched off main:
git stash
git rebase 687-phase7-arg-type
git stash pop
```

### tests/ Override Is Required Before Removing Any Code

Some error codes are zero in scylla/+scripts/ but non-zero in tests/. Removing them from the global `disable_error_code` would immediately break tests/ CI. Fix first by adding a `[[tool.mypy.overrides]]` for `tests.*`:

```toml
[[tool.mypy.overrides]]
module = "tests.*"
disable_error_code = [
    "call-arg",   # tests-only violations
    "union-attr", # etc.
    ...
]
```

Then remove the code from the global list. The `check_mypy_counts.py` script uses `TESTS_ONLY_ERROR_CODES` to track these separately.

### tests/claude-code/ Is NOT Covered by tests.* Override

The `tests/claude-code/` directory has a hyphen in its name — Python module naming means `tests.*` in `[[tool.mypy.overrides]]` does NOT match it. Files there must be fixed directly (add type annotations, rename variables, etc.).

### S101 noqa on Every assert

All new `assert` statements need `# noqa: S101` for ruff's assert-detection rule:

```python
assert self.checkpoint is not None  # noqa: S101
```

### Removing a Code Can Surface New Codes

When you remove `assignment` from `disable_error_code`, mypy may now report `method-assign` in test files (monkey-patching). Always run the full `check_mypy_counts.py` after removing a code to catch newly-surfaced codes before committing.

### pixi.lock Must Always Be Staged

Any change to `pyproject.toml` changes the SHA256 of the local editable package and invalidates `pixi.lock`. Always include `pixi.lock` in every commit touching `pyproject.toml`.

```bash
pixi lock  # regenerate if needed (usually "already up-to-date")
git add pixi.lock
```

### Total Row Calculation in update_table()

When `DISABLED_ERROR_CODES = []`, the Total row in `update_table()` / `update_table_per_dir()` must not sum against the empty list. Sum `actual.values()` directly:

```python
# Wrong (produces 0 when DISABLED_ERROR_CODES is empty):
total = sum(actual.get(c, 0) for c in DISABLED_ERROR_CODES)

# Correct:
total = sum(actual.values())
```

## Verified Workflow

### Phase 0: Remove Globally-Zero Codes (Quick Win)

```bash
# Find codes already at zero across ALL directories
pixi run python scripts/check_mypy_counts.py  # see which codes are 0
# Remove them from pyproject.toml disable_error_code
# Update MYPY_KNOWN_ISSUES.md and check_mypy_counts.py DISABLED_ERROR_CODES
```

### Phase 1: Add tests/ Override to Decouple

```bash
# Create empty tests/__init__.py to enable tests.* module matching
touch tests/__init__.py

# Add to pyproject.toml:
# [[tool.mypy.overrides]]
# module = "tests.*"
# disable_error_code = ["call-arg", ...]

# Remove call-arg from global disable_error_code
# Add TESTS_ONLY_ERROR_CODES list to check_mypy_counts.py
```

### Phases 2–8: Fix Error Codes Incrementally

For each error code:

```bash
# 1. Find all violations
pixi run mypy scylla/ scripts/ --enable-error-code=<code> 2>&1 | grep "\[<code>\]"

# 2. Fix violations (see patterns below)

# 3. Verify zero violations
pixi run mypy scylla/ scripts/ --enable-error-code=<code> 2>&1 | grep "\[<code>\]"
# (should produce no output)

# 4. Remove from pyproject.toml disable_error_code

# 5. Run regression guard to check MYPY_KNOWN_ISSUES.md is current
pixi run python scripts/check_mypy_counts.py --update
pixi run python scripts/check_mypy_counts.py  # should be OK

# 6. Commit + PR
SKIP=audit-doc-policy git commit -m "fix(types): resolve <code> errors [Phase N]"
gh pr create ...
gh pr merge --auto --rebase
```

### Phase 9: Simplify Tracking Infrastructure

Once `DISABLED_ERROR_CODES = []`:

```bash
# Merge 3x per-directory mypy invocations into 1
# run_mypy_per_dir(): single subprocess over all MYPY_PATHS
# partition output lines by file path prefix instead of per-invocation

# Remove scylla/ and scripts/ sections from MYPY_KNOWN_ISSUES.md
# Update docstrings and comments in check_mypy_counts.py
```

## Fix Patterns by Error Code

### var-annotated
Add explicit type annotations to untyped variables:
```python
# Before: settings = {}
settings: dict[str, Any] = {}
```

### misc
Generator yield types, lambda inference, nonlocal binding:
```python
# Lambda narrowing: mypy can't narrow Optional inside lambda
# Before: key=lambda j: abs(j.score - consensus)
key=lambda j: abs((j.score if j.score is not None else 0.0) - consensus)
```

### index / attr-defined
Wrong type inference (e.g., `dict[str, bool]` inferred from first assignment):
```python
# Before: settings = {"flag": True}  → dict[str, bool]
settings: dict[str, Any] = {"flag": True}
```
Also fix wrong import locations (`JudgeResult`, `SubtestSelection`) and non-existent method names.

### operator
`Optional` used in arithmetic — add None-guards:
```python
assert self.experiment_dir is not None  # noqa: S101
# or use walrus operator:
key=lambda t: int(m.group()) if (m := re.search(r"\d+", t)) else 0
```

### assignment
Variable type collision patterns:
```python
# Loop variable `status: RunStatus` then reassigned with str → rename
run_status = ...  # was: status = ...

# `result: E2ERunResult | None` then reassigned with dict → rename
run_result_data = ...  # was: run_result = ...
```

### arg-type
```python
# str | None passed where str expected:
best_subtest or ""

# Optional[X] passed where X expected → assert:
assert self._state is not None  # noqa: S101

# Overloaded function (dict.get) → lambda wrapper:
max(dist, key=lambda g: dist.get(g, 0))
```

### union-attr
```python
# Attribute access on Optional → assert:
assert self.checkpoint is not None  # noqa: S101

# Path | None — separate candidate from result:
rubric_candidate = experiment_dir / "rubric.yaml"
rubric_path: Path | None = rubric_candidate if rubric_candidate.exists() else None

# Match | None — walrus operator:
key=lambda t: int(m.group()) if (m := re.search(r"\d+", t)) else 0
```

## Results & Parameters

### Final State (after all 9 phases)

```toml
# pyproject.toml — disable_error_code removed entirely
# (no globally-disabled error codes)

[[tool.mypy.overrides]]
module = "tests.*"
disable_error_code = [
    "operator", "arg-type", "index", "attr-defined", "union-attr",
    "var-annotated", "call-arg", "misc", "method-assign",
]
```

```python
# scripts/check_mypy_counts.py
DISABLED_ERROR_CODES: list[str] = []  # empty — scylla/+scripts/ compliant
TESTS_ONLY_ERROR_CODES = [
    "call-arg", "var-annotated", "misc", "method-assign", "union-attr",
]
ALL_TRACKED_CODES = DISABLED_ERROR_CODES + TESTS_ONLY_ERROR_CODES
```

```
# Verification
pixi run mypy scylla/ scripts/ → Success: no issues found in 163 source files
python scripts/check_mypy_counts.py → OK — counts match mypy output
```

### Phase Summary

| Phase | Error Code(s) | Violations Fixed | PR |
|-------|---------------|------------------|----|
| 0 | 5 zero codes removed | 0 | #1068 |
| 1 | tests/ override added | 0 | #1069 |
| 2 | var-annotated | 9 | #1070 |
| 3 | misc | 4 | #1071 |
| 4 | index + attr-defined | 7 | #1072 |
| 5 | operator | 13 | #1073 |
| 6 | assignment | 12 | #1074 |
| 7 | arg-type | 23 | #1075 |
| 8 | union-attr | 4 | #1076 |
| 9 | infra simplification | 0 | #1077 |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #687, PRs #1068–#1077 | [notes.md](../../references/notes.md) |
