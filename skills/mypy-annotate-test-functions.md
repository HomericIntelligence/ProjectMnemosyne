---
name: mypy-annotate-test-functions
description: 'Skill: mypy-annotate-test-functions. Use when annotating test functions and helper classes in pytest test files for mypy compliance.'
category: testing
date: 2026-03-02
version: 1.0.0
user-invocable: false
---

# Mypy Annotate Test Functions Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Issues** | #1120, #1289, #1283 — Annotate test functions in tests/unit/ for mypy compliance |
| **Objective** | Add `-> None` return type annotations to all test functions and explicit type hints to helper classes in pytest test files |
| **Outcome** | ✅ Success — one change to `ConcreteAdapter.run()` in `test_base.py`; all 160 adapter tests pass; all pre-commit hooks pass |
| **PR** | #1318 (ProjectScylla) |

## When to Use

Use this skill when:

- An issue asks to "annotate test functions in tests/unit/X/ for mypy compliance"
- You need to add `-> None` to all `def test_*()` methods in pytest test classes
- Non-test helper classes inside test files (e.g., `ConcreteAdapter`) need proper return type annotations on their method overrides
- Part of a broader mypy compliance wave (e.g., #1120 parent issue with sub-issues per subdirectory)

## Key Insight: Most Tests May Already Be Annotated

When working on a sub-issue asking to annotate a directory, **audit first before making changes**.
In this case, `tests/unit/adapters/` already had `-> None` on all 160 test methods. The only
missing annotation was on `ConcreteAdapter.run()` (a non-test helper override), not on any
`test_*` function.

**Always run this audit first:**
```bash
grep -n "def test_" tests/unit/<dir>/*.py | grep -v "-> None"
```

If that returns nothing, the test methods are already annotated. Then check helper class methods:
```bash
grep -n "def run\|def setUp\|def tearDown" tests/unit/<dir>/*.py | grep -v "-> "
```

## Key Insight: Helper Classes in Test Files Need Annotations Too

Concrete helper classes that implement abstract base classes (e.g., `ConcreteAdapter(BaseAdapter)`)
inside test files need proper type annotations on their method overrides for full mypy compliance,
even though these are not `test_*` methods.

**Pattern**: When a helper class overrides an abstract method without type hints, add parameter
types matching the abstract method signature and the correct return type:

```python
# Before (missing annotations)
class ConcreteAdapter(BaseAdapter):
    def run(self, config, tier_config=None):
        return AdapterResult(exit_code=0, stdout="success", stderr="")

# After (fully annotated)
class ConcreteAdapter(BaseAdapter):
    def run(self, config: AdapterConfig, tier_config: object = None) -> AdapterResult:
        return AdapterResult(exit_code=0, stdout="success", stderr="")
```

Use `object` (not `Any`) for optional parameters that accept any type — it's the most precise
type hint for "I accept anything but don't use it" patterns.

## Key Insight: `object` vs `Any` for Ignored Optional Parameters

When a helper's override accepts a parameter it doesn't use (like `tier_config`), prefer `object`
over `Any`:
- `object` is the most general type — it's precise and mypy-safe
- `Any` disables mypy checking for that parameter — too permissive
- The real production abstract method signature is the authority; check what it uses

## Verified Workflow

```bash
# 1. Audit what's missing
grep -rn "def test_" tests/unit/<dir>/ | grep -v "-> None"
grep -rn "def run\|def setUp" tests/unit/<dir>/ | grep -v "-> "

# 2. Check mypy state first
pre-commit run mypy --files tests/unit/<dir>/*.py

# 3. Make the minimal annotation changes

# 4. Verify tests still pass
pixi run python -m pytest tests/unit/<dir>/ -v --no-cov

# 5. Run pre-commit hooks
pre-commit run --files tests/unit/<dir>/<changed_file>.py

# 6. Commit and push
git add tests/unit/<dir>/<changed_file>.py
git commit -m "test(<dir>): annotate test functions in tests/unit/<dir>/ for mypy compliance"
git push -u origin <branch>
gh pr create --title "[Testing] Annotate test functions in tests/unit/<dir>/ for mypy compliance" \
  --body "Closes #NNNN"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files changed | 1 (`tests/unit/adapters/test_base.py`) |
| Lines changed | 1 (method signature on line 22) |
| Tests affected | 160 adapter unit tests — all pass |
| Pre-commit hooks | All pass (ruff, mypy, black, check-unit-test-structure) |
| Commit message format | `test(<dir>): annotate test functions in tests/unit/<dir>/ for mypy compliance` |
| PR title format | `[Testing] Annotate test functions in tests/unit/<dir>/ for mypy compliance` |

## Anti-Patterns to Avoid

- **Don't mass-add `-> None`** without auditing first — many files may already have it
- **Don't use `Any`** for optional parameters that are deliberately ignored — use `object`
- **Don't skip the helper class audit** — `test_*` methods aren't the only things that need annotation
- **Don't add `-> None` to fixture functions** — check conftest.py separately; fixtures typically
  return typed values and should already be annotated with the correct return type
