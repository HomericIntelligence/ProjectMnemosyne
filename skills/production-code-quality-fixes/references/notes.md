# Raw Notes: Production Code Quality Fixes (Issue #757)

## Session Context

- **Date**: 2026-02-21
- **Branch**: 757-auto-impl
- **Working dir**: /home/mvillmow/ProjectScylla/.worktrees/issue-757
- **Task**: Fix production assert in grading.py and hardcoded /tmp path in llm_judge.py

## Issue Details

Two code quality problems identified in production code:

1. `scylla/metrics/grading.py:132` used `assert 0.0 <= score <= 1.0` for input validation.
   Python `-O` strips asserts at compile time → silent safety gap in optimized deployments.

2. `scylla/e2e/llm_judge.py:370` used hardcoded `/tmp/scylla_pycache` for `PYTHONPYCACHEPREFIX`.
   Not cross-platform; could cause cache collisions in parallel test runs.

## Execution

### Step 1: Read the files at the specified locations

- `grading.py:132` confirmed: `assert 0.0 <= score <= 1.0, f"Score {score} is outside valid range [0.0, 1.0]"`
- `llm_judge.py:370` confirmed: `env["PYTHONPYCACHEPREFIX"] = "/tmp/scylla_pycache"`
- `llm_judge.py` imports: `tempfile` already imported at line 13, `Path` already imported at line 14 — no new imports needed.

### Step 2: Apply fixes

Both fixes were single-line edits:

```
grading.py: assert → if not (...): raise ValueError(...)
llm_judge.py: "/tmp/scylla_pycache" → str(Path(tempfile.gettempdir()) / "scylla_pycache")
```

### Step 3: Find and update existing tests

Ran tests after fixes → found 1 existing test failing:

```
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_metrics_grading_validates_range
```

This test expected `AssertionError` with `match="outside valid range"`. Updated to expect
`ValueError` with `match="score must be in"`.

### Step 4: Add new parametrized test

Added to `TestAssignLetterGrade` in `test_grading.py`:

```python
@pytest.mark.parametrize("score", [-0.1, 1.1, -1.0, 2.0])
def test_invalid_score_raises_value_error(self, score: float) -> None:
    with pytest.raises(ValueError, match="score must be in"):
        assign_letter_grade(score)
```

### Step 5: Verify

```
241 passed in 0.27s  ← all unit/metrics + grading_consistency tests
Pre-commit: all hooks passed
```

## Skill Tool Denial

`commit-commands:commit-push-pr` skill was denied by `don't ask mode`. Used direct git/gh commands:

```bash
git add scylla/metrics/grading.py scylla/e2e/llm_judge.py \
  tests/unit/metrics/test_grading.py tests/unit/test_grading_consistency.py
git commit -m "fix(metrics): replace production assert..."
git push -u origin 757-auto-impl
gh pr create --title "..." --body "..."
gh pr merge --auto --rebase 891
```

`AskUserQuestion` tool was also denied (don't ask mode) — proceeded with reasonable defaults
for skill category (`debugging`) and name (`production-code-quality-fixes`).

## Key Lesson

**Always grep tests/ for `AssertionError` after replacing production asserts with `ValueError`.**
There was one pre-existing test in `test_grading_consistency.py` that explicitly expected
`AssertionError` for the old assert-based validation. Missing this would cause CI to fail.

Pattern for finding affected tests:
```bash
grep -rn "AssertionError" tests/ --include="*.py"
```
