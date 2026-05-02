---
name: verify-and-commit
description: "Take a dirty working tree (implementation already complete) through\
  \ the full verify \u2192 fix \u2192 commit \u2192 PR workflow. Covers running tests,\
  \ fixing pre-commit failures, and creating a PR."
category: ci-cd
date: 2026-02-24
version: 1.0.0
user-invocable: false
---
# Verify and Commit

| Field | Value |
| ------- | ------- |
| Date | 2026-02-24 |
| Objective | Verify a pre-implemented feature, fix linting/typing issues, and ship a PR |
| Outcome | All 1014 e2e unit tests passed; all 3015 total tests passed (78% coverage); all pre-commit hooks passed; PR #1081 created and auto-merge enabled |
| Repository | HomericIntelligence/ProjectScylla |

## When to Use

- Implementation was completed in a previous session (context ran out) and needs verification + commit
- You have a dirty working tree and need to get it through CI before creating a PR
- Pre-commit hooks are failing and need targeted fixes before committing
- mypy known-issue counts have drifted after adding new test files

## Verified Workflow

### Step 1: Run the targeted test suite first

Run only the tests for the area you changed — faster feedback before committing:

```bash
pixi run python -m pytest tests/unit/<module>/ -v --no-cov
```

Look for the summary line. All tests must pass before proceeding.

### Step 2: Run pre-commit on all files

```bash
pre-commit run --all-files
```

Pre-commit runs twice in this project (hooks run, then re-validate). Note which hooks fail.

### Step 3: Fix pre-commit failures

**Ruff format** (auto-fixed by hook, just re-run):
- The hook modifies files in place. After the first run, re-run `pre-commit run --all-files` and it will pass.

**Ruff E501 (line too long) in comments/docstrings**:
- Wrap the line at a natural break point. In help text strings, add a newline + indent:
  ```python
  # Before (>100 chars):
  "  rerun-agents /exp/ → run --config <dir> --results-dir /exp/ --from replay_generated --filter-tier T0 --filter-status failed"
  # After:
  "  rerun-agents /exp/\n    → run --config <dir> --results-dir /exp/ --from replay_generated\n          --filter-tier T0 --filter-status failed"
  ```

**check-mypy-counts (MYPY_KNOWN_ISSUES.md out of date)**:
- Run the update script:
  ```bash
  pixi run python scripts/check_mypy_counts.py --update
  ```
- This regenerates MYPY_KNOWN_ISSUES.md with current counts. Stage the file alongside your other changes.
- Common cause: new test files that introduce `arg-type` errors via mock/patch signatures.

### Step 4: Re-run pre-commit to confirm all green

```bash
pre-commit run --all-files
```

All hooks should show `Passed` or `Skipped`.

### Step 5: Run full test suite (push hook will do this, but catch early)

```bash
pixi run python -m pytest tests/ -v 2>&1 | tail -5
```

### Step 6: Create branch, stage, commit, push, PR

```bash
git checkout -b <issue-number>-<description>

git add <file1> <file2> ... MYPY_KNOWN_ISSUES.md

git commit -m "$(cat <<'EOF'
feat(scope): Short imperative description

Longer explanation of what changed and why. List key additions:
- Thing 1
- Thing 2

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

git push -u origin <branch-name>

gh pr create \
  --title "feat(scope): Short description" \
  --body "$(cat <<'EOF'
## Summary
- Bullet 1
- Bullet 2

## Test plan
- [x] All N unit tests pass
- [x] All M total tests pass (X% coverage)
- [x] All pre-commit hooks pass

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

gh pr merge --auto --rebase
```

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Project-Specific Commands

| Task | Command |
| ------ | --------- |
| Run e2e unit tests only | `pixi run python -m pytest tests/unit/e2e/ -v --no-cov` |
| Run full suite | `pixi run python -m pytest tests/ -v` |
| Update mypy counts | `pixi run python scripts/check_mypy_counts.py --update` |
| Run pre-commit | `pre-commit run --all-files` |

### Pre-commit Hook Order (ProjectScylla)

1. `ruff-format-python` — auto-formats; re-run after first pass
2. `ruff-check-python` — E501 violations must be fixed manually
3. `mypy` — type check (passes if no new errors)
4. `check-mypy-counts` — baseline count check; update with `--update` script
5. Other custom hooks (model config naming, doc policy, markdownlint, YAML, ShellCheck)

### Typical MYPY_KNOWN_ISSUES.md Drift Pattern

When adding new test files that use `unittest.mock.patch` or `MagicMock`, mypy often
raises `arg-type` errors on mock return values. These are pre-existing / accepted errors.
The `check-mypy-counts` hook tracks counts per directory so drift is caught automatically.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1081 — consolidate run subcommands | [notes.md](../../references/notes.md) |
