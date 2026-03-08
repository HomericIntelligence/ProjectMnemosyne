---
name: batch-pr-pre-commit-fixes
description: "Systematically fix multiple failing PRs with pre-commit hook failures — covers auto-format fixes, expanded-scope self-catch scenarios, merge conflict resolution, and BAD_PATTERNS rebase regressions"
category: ci-cd
date: 2026-03-08
user-invocable: false
---

# Batch PR Pre-commit Fixes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-08 (updated; originally 2026-02-15) |
| **Objective** | Fix failing pre-commit CI checks on multiple open PRs |
| **Outcome** | ✅ All PRs brought to green; CI passing |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PRs #1462, #1452 (2026-03-08) | [notes.md](../../references/notes.md) |
| ProjectMnemosyne | PRs #685–#697 (2026-02-15) | [notes.md](../../references/notes.md) |

## When to Use

- Multiple open PRs are failing CI with `pre-commit` hook failures
- A PR expanded a pre-commit hook's scope (e.g., from one file to `*.md`) and the new check caught pre-existing violations — a **"self-catch"** scenario
- A branch has diverged from `main` and has merge conflicts blocking CI from even running
- Formatting violations (ruff-format, black, markdownlint) need trivial single-line fixes
- After a rebase, tests fail because `BAD_PATTERNS` lists got truncated

**Common trigger phrases:**

- "Fix these failing PRs"
- "Multiple PRs failing pre-commit"
- "PR failing with N tier label mismatches"
- "Branch has merge conflicts, CI won't run"

## Verified Workflow

### Phase 0: Triage before touching anything

```bash
# Check status of all open PRs
gh pr list --state open
gh pr checks <number>

# For each failing PR, read the CI log
gh run view <run-id> --log-failed | head -60

# Check if branch is behind main (causes merge conflicts → CI won't even run)
gh pr view <number> --json mergeable,mergeStateStatus
# "CONFLICTING" → rebase needed before CI can trigger
```

The hook name in the CI log tells you which fix path to take:

| Hook | Fix Path |
|------|----------|
| `Ruff Format Python` | Auto-fix (blank lines, indentation) |
| `Markdown Lint` | Auto-fix (MD032 blank lines) |
| `Check Tier Label Consistency` | Manual doc fixes (see self-catch path below) |
| `Audit Doc Policy Violations` | Check if `ProjectMnemosyne/` is on disk (local-only) |

### Phase 1: Fix trivial formatting (ruff-format, markdownlint)

```bash
git checkout <branch>
git pull origin <branch>

# Let the hook auto-fix
pre-commit run --all-files

# Check what changed
git status --short

# Stage only the changed files
git add <changed-files>
git commit -m "fix(tests): add missing blank line between test classes"
git push origin <branch>
```

**Key**: always `git status --short` after pre-commit to know what was auto-fixed before staging.

### Phase 2: Fix "self-catch" expanded-scope pre-commit hook

When a PR widens a pre-commit hook (e.g., from checking one file to scanning `*.md`), and the
wider scan catches pre-existing violations in other files the PR didn't touch:

**Step 1**: Reproduce the exact CI environment (exclude untracked local dirs):

```bash
# Wrong — includes ProjectMnemosyne/ which doesn't exist in CI
pixi run python scripts/check_tier_label_consistency.py

# Correct — matches CI (ProjectMnemosyne/ is untracked, absent in CI)
pixi run python scripts/check_tier_label_consistency.py --exclude ProjectMnemosyne
```

**Step 2**: Fix all violations. For tier-label mismatches, watch for **contextual regex traps**
where the regex fires on a tier number + a tier name that appears *later on the same line*:

| Original text | Fires on | Correct rewrite |
|--------------|----------|-----------------|
| `T1-T3 (Skills/Tooling/Delegation)` | T3+Skills | `T1 (Skills) through T3 (Delegation)` |
| `T4-T5 (Hierarchy/Hybrid)` | T5+Hierarchy | `T4 (Hierarchy) and T5 (Hybrid)` |
| `T4-T6 (Hierarchy/Hybrid/Super)` | T6+Hierarchy | `T4 (Hierarchy) through T6 (Super)` |
| `T0-T1 (prompts + skills)` | T1+prompts | `T0 (Prompts) or T1 (Skills)` |
| `T1-T2 (skills/tools)` | T2+skills | `T1 (Skills) and T2 (Tooling)` |

**Step 3**: Verify clean before committing:

```bash
pixi run python scripts/check_tier_label_consistency.py --exclude ProjectMnemosyne
# Should print: "No tier label mismatches found."
```

**Step 4**: Commit with a descriptive message:

```bash
git add <all modified .md files>
git commit -m "docs: fix N tier label mismatches caught by expanded consistency checker"
git push origin <branch>
```

### Phase 3: Fix branches behind main (merge conflicts)

If `mergeStateStatus == "CONFLICTING"`, CI won't trigger until the branch is rebased:

```bash
git checkout <branch>
git fetch origin main
git log --oneline HEAD..origin/main | wc -l  # How many commits behind?

git rebase origin/main
# For script files where PR added new functionality, take the PR version:
git checkout --theirs <conflicted-script>
git add <conflicted-script>
git rebase --continue
```

**After rebase**: always re-run the tests immediately:

```bash
pixi run python -m pytest tests/unit/scripts/test_<checker>.py --override-ini="addopts=" -q
```

**Common rebase regression — BAD_PATTERNS truncation**: When a PR kept only 4 patterns in
`BAD_PATTERNS` for backwards-compat, but `main` had already expanded it to 20, the post-rebase
test file includes tests for all 20 patterns while the script only has 4. Fix by restoring the
full list:

```python
BAD_PATTERNS: list[tuple[str, str]] = [
    # Original 4
    (r"T3.*Tool", "T3 is Delegation, not Tooling"),
    (r"T4.*Deleg", "T4 is Hierarchy, not Delegation"),
    (r"T5.*Hier", "T5 is Hybrid, not Hierarchy"),
    (r"T2.*Skill", "T2 is Tooling, not Skills"),
    # Reverse/symmetric set from main (bounded to avoid cross-tier false positives)
    (r"T2.{0,10}Deleg", "T2 is Tooling, not Delegation"),
    (r"T3.{0,10}Hier", "T3 is Delegation, not Hierarchy"),
    (r"T4.{0,10}Hybrid", "T4 is Hierarchy, not Hybrid"),
    (r"T1.{0,10}Tool", "T1 is Skills, not Tooling"),
    (r"T0.{0,10}Skill", "T0 is Prompts, not Skills"),
    (r"T1.{0,10}Prompt", "T1 is Skills, not Prompts"),
    (r"T2.{0,10}Prompt", "T2 is Tooling, not Prompts"),
    (r"T3.{0,10}Skill", "T3 is Delegation, not Skills"),
    (r"T4.{0,10}Tool", "T4 is Hierarchy, not Tooling"),
    (r"T5.{0,10}Deleg", "T5 is Hybrid, not Delegation"),
    (r"T6.{0,10}Hier", "T6 is Super, not Hierarchy"),
    (r"T6.{0,10}Hybrid", "T6 is Super, not Hybrid"),
    (r"T0.{0,10}Tool", "T0 is Prompts, not Tooling"),
    (r"T0.{0,10}Deleg", "T0 is Prompts, not Delegation"),
    (r"T5.{0,10}Skill", "T5 is Hybrid, not Skills"),
    (r"T6.{0,10}Deleg", "T6 is Super, not Delegation"),
]
```

### Phase 4: Force-push rebased branch

```bash
git push --force-with-lease origin <branch>
```

`--force-with-lease` only succeeds if nobody else pushed to the remote since your last fetch — safe for solo work.

### Phase 5: Verify CI

```bash
# Wait ~30s then:
gh pr checks <number>

# If no checks appear, confirm push landed:
gh pr view <number> --json commits  # Latest SHA should match HEAD

# Check mergeable status:
gh pr view <number> --json mergeable,mergeStateStatus
```

## Failed Attempts

| Attempt | What Happened | Fix |
|---------|--------------|-----|
| Fixing both PRs in parallel | Git state confusion; committed to wrong branch | Do one PR completely (checkout → fix → commit → push → verify CI started) before moving to next |
| Running `pre-commit` without excluding untracked dirs | 63 mismatches locally vs 20 in CI; `ProjectMnemosyne/` was scanned locally | Pass `--exclude ProjectMnemosyne` to match CI environment |
| Pre-push hook fluke test failure | `test_load_test` failed with "language, tiers unexpected" at 22% into 4725-test run; not reproducible | Retry the push — transient `_SCHEMA_CACHE` ordering issue in full test suite |
| `git stash pop` on wrong branch | Applied main-branch stash to feature branch, causing 16 merge-conflict files in `tests/unit/analysis/` | Resolve with `git checkout --ours <dir> && git add <dir>` (feature branch didn't touch those files) |
| Not running tests after rebase | BAD_PATTERNS regression caused 32 test failures; pushed a broken branch | Always run `pytest tests/unit/scripts/` immediately after resolving rebase conflicts |

## Results & Parameters

### Tier Label Canonical Mapping (ProjectScylla)

```
T0 = Prompts    T1 = Skills    T2 = Tooling    T3 = Delegation
T4 = Hierarchy  T5 = Hybrid    T6 = Super
```

### Commit Message Templates

```
fix(tests): add missing blank line between test classes
docs: fix N tier label mismatches caught by expanded consistency checker
fix(scripts): restore full BAD_PATTERNS set after rebase onto main
fix(skills): Apply markdownlint auto-fixes to <skill-name>
fix(ci): Regenerate pixi.lock after removing lint environment
```

### CI Check Names (ProjectScylla)

| Check | What it runs |
|-------|-------------|
| `pre-commit` | All hooks in `.pre-commit-config.yaml` |
| `test (unit, tests/unit)` | `pixi run pytest tests/unit/ --cov-fail-under=75` |
| `test (integration, tests/integration)` | `pixi run pytest tests/integration/` |
| `Dependency vulnerability scan` | `pip-audit` |
| `docker-validation` | Docker build + smoke test |

### Pre-commit Hook Reference

| Hook | Purpose | Common Fix |
|------|---------|------------|
| `Ruff Format Python` | Python formatting | 2 blank lines between top-level classes |
| `markdownlint-cli2` | Markdown formatting | MD032 blank lines around lists |
| `Check Tier Label Consistency` | Tier name correctness | Fix T2/Skills→Tooling etc., or rewrite contextual ranges |
| `trailing-whitespace` | Strip trailing spaces | Auto-fixed by hook |
| `end-of-file-fixer` | Ensure newline at EOF | Auto-fixed by hook |
