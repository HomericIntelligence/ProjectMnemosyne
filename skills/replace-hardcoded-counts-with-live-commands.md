---
name: replace-hardcoded-counts-with-live-commands
description: Replace hardcoded test/file counts in README badges and prose with a
  live command users can run. Use when a CI check enforces doc accuracy but counts
  change frequently, making the docs flaky.
category: documentation
date: 2026-03-03
version: 1.0.0
user-invocable: true
---
# Replace Hardcoded Counts with Live Commands

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Remove flaky hardcoded test counts from README.md (badge + prose) and replace with a live command users can run |
| **Outcome** | Three locations updated; pre-commit passes; PR #1325 merged |
| **Related Issues** | ProjectScylla #1322 |

## When to Use This Skill

Use this skill when:

- CI fails because a hardcoded test/file count in README drifted from the actual value
- An issue requests removing a `scripts/check_test_counts.py` CI check that enforces doc accuracy
- A badge like `tests-2026%2B` or prose like `115+ test files` needs to stay accurate but the count changes frequently
- The fix should be "stop maintaining the number" rather than "update the number"

**Triggers:**

- Issue title contains "flaky test count", "remove count check", "stale count"
- `scripts/check_test_counts.py` referenced in issue as something to delete
- Badge URL contains a hardcoded number (e.g., `tests-2026%2B`)
- README prose contains `N+ test files` or `N+ tests, all passing`

## Verified Workflow

### Phase 1: Locate All Hardcoded Count References

```bash
# Find all occurrences in README.md and docs
grep -n "2026%2B\|[0-9]\+\+ test\|check_test_counts\|[0-9]\+\+ tests" README.md CLAUDE.md docs/*.md
```

Check these locations systematically:

| Location | What to Check |
|----------|--------------|
| Badge line (top of README) | `tests-N%2B` in shields.io URL |
| `### Testing` section | `N+ test files` in prose and bullets |
| Research features checklist | `N+ tests, all passing` bullet |
| CLAUDE.md "Current Status" | Any count references |

### Phase 2: Determine Whether to Update or Remove

**Remove the count** (this skill) when:
- The number changes frequently and a CI script enforces it
- The issue explicitly asks to stop tracking the count

**Update the count** (see `fix-doc-metric-discrepancies` skill) when:
- The count is just stale but should remain documented
- No CI script enforces it; it just drifted

### Phase 3: Apply the Three Standard Fixes

**1. Badge — replace number-in-URL with static label:**

```
# Before
[![Tests](https://img.shields.io/badge/tests-2026%2B-brightgreen.svg)](#)

# After
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#)
```

**2. Testing section prose — replace count with live command:**

```markdown
# Before
ProjectScylla has a comprehensive test suite with **115+ test files** covering all functionality.

# After
ProjectScylla has a comprehensive test suite covering all functionality. To see the current test count:

```bash
pixi run pytest tests/ --collect-only -q | tail -1
```
```

Also remove counts from sub-bullets (e.g., `**Unit Tests** (115+ files):` → `**Unit Tests**:`).

**3. Features checklist — remove the number:**

```
# Before
✅ **Comprehensive test suite** (2026+ tests, all passing)

# After
✅ **Comprehensive test suite** (all passing)
```

### Phase 4: Delete the Enforcement Script (if it exists)

If `scripts/check_test_counts.py` exists, delete it:

```bash
git rm scripts/check_test_counts.py
```

Also remove any CI reference to it (check `.github/workflows/*.yml` for `check_test_counts`).

> **Note:** In the session that produced this skill, the script did not exist in the worktree — confirm with `ls scripts/check_test_counts.py` before attempting deletion.

### Phase 5: Verify and Commit

```bash
# Confirm no stale count references remain
grep -n "2026%2B\|115+ test\|check_test_counts" README.md

# Run pre-commit on changed files
pre-commit run --files README.md

# Commit
git add README.md   # add any other changed files
git commit -m "docs(readme): replace hardcoded test counts with live command

- Replace tests-2026%2B badge with tests-passing badge
- Replace '115+ test files' prose with live pytest --collect-only command
- Remove '2026+ tests' from research features checklist

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>
gh pr create \
  --title "[Docs] Remove flaky test count from README" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Observations

1. **Issue description may list artifacts that don't exist** — the issue said "remove `scripts/check_test_counts.py`" but the file was never in the repo. Verify existence before deleting.

2. **Three locations to update, not one** — badge URL, Testing section prose, and features checklist all contain hardcoded counts independently. Missing any one leaves stale content.

3. **`tests-passing` is a better badge than `tests-NNN%2B`** — shields.io static badges with a live CI link are more durable. If CI is wired to shields, use the CI badge endpoint instead.

4. **Live command pattern** — `pixi run pytest tests/ --collect-only -q | tail -1` gives the user the count on demand without baking it into docs. Use `--collect-only -q` (not `-v`) to keep output parseable.

5. **Pre-commit on docs changes** — markdown-lint and audit-doc-policy hooks run on `.md` files. Always run `pre-commit run --files README.md` before committing.

6. **Skill tool blocked in don't-ask mode** — `/commit-commands:commit-push-pr` requires Skill tool permission. Fall back to direct `git` + `gh` commands when running autonomously.

## Results

| File | Changes Applied |
|------|----------------|
| `README.md` | Badge: `tests-2026%2B` → `tests-passing`; prose: replaced `115+ test files` with live command block; checklist: removed `(2026+ tests, all passing)` count |
| `scripts/check_test_counts.py` | Not present — no action taken |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1322, PR #1325 | Pre-commit passed (markdown-lint, audit-doc-policy, trim-whitespace, end-of-files) |
