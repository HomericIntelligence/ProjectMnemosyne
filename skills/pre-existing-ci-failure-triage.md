---
name: pre-existing-ci-failure-triage
description: 'Triage CI failures on a PR to determine if they are pre-existing on
  main or introduced by the PR. Use when: CI fails but PR changes look unrelated,
  deciding whether to block merge on CI failures, or distinguishing infrastructure/flaky
  failures from code regressions.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Pre-Existing CI Failure Triage

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Determine if CI failures on a PR are pre-existing on main or introduced by the PR's changes |
| Outcome | Confirmed: both failures pre-existing; PR merged without fixes |
| PR | #3363 (issue #3158, CLAUDE.md trim from 1786 to 1199 lines) |

Documentation-only PRs frequently show CI failures that exist on `main` unrelated to the PR.
This skill documents the triage workflow to distinguish pre-existing from introduced failures.

## When to Use

- CI fails on a PR but the PR only changes documentation/config (no code)
- CI failure category (link-checking, infrastructure crashes) seems unrelated to PR scope
- Need to decide whether to block merge or proceed
- Suspecting flaky or pre-existing infrastructure failures

## Verified Workflow

1. **Identify failure categories** - Read the CI failure logs to categorize each failure type:
   - Link checker failures (e.g. lychee, markdown-link-check)
   - Runtime crashes (`execution crashed`, OOM)
   - Test assertion failures
   - Build/compile failures

2. **Check if failure exists on main** - For each failure type, check recent main runs:

   ```bash
   # Check recent runs of the failing workflow on main
   gh run list --branch main --workflow "<Workflow Name>" --limit 5

   # View a specific main run's failures
   gh run view <run-id> --log-failed 2>&1 | head -100
   ```

3. **Correlate with PR changes** - Check if PR touched any files that could cause the failure:

   ```bash
   # List all files changed by the PR
   git diff main..<branch> --name-only

   # Check specifically for source files relevant to the failure
   git diff main..<branch> --name-only | grep "\.mojo$"
   git diff main..<branch> --name-only | grep "\.py$"
   ```

4. **Verify new links (for link-check failures)** - If the PR adds new links, verify they use
   relative paths and all target files exist:

   ```bash
   # Check target files exist
   ls path/to/linked/file1.md path/to/linked/file2.md

   # Grep new links added in the PR
   git diff main..<branch> -- "*.md" | grep "^+" | grep -o '([^)]*\.md)'
   ```

5. **Document findings** - Summarize:
   - Which failures are pre-existing (with evidence: run IDs on main)
   - Which failures were introduced (with the specific changed file)
   - Whether any action is required

6. **Decide action**:
   - Pre-existing only → PR is ready to merge as-is
   - PR introduced failures → fix before merging

## Key Commands

```bash
# List recent workflow runs on main to find pre-existing failures
gh run list --branch main --workflow "Comprehensive Tests" --limit 5
gh run list --branch main --workflow "Check Markdown Links" --limit 5

# View failed logs for a specific run
gh run view <run-id> --log-failed 2>&1 | grep -E "(error|crash|failed)" | head -50

# Confirm no relevant source files changed
git diff main..<branch> --name-only | grep -E "\.(mojo|py)$"

# Check CLAUDE.md or doc line counts
wc -l CLAUDE.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming failures require fixes | Saw red CI and started planning fixes | Both failures were pre-existing on main | Always check main's CI history before concluding a PR introduced failures |
| Root-relative link analysis | Worried new links in CLAUDE.md would trigger lychee errors | New links used relative paths, not root-relative; all targets existed | Distinguish root-relative (`/path`) from relative (`path`) — lychee fails on root-relative, not relative |
| Blaming doc PR for test crashes | `execution crashed` failures looked alarming | These were infrastructure-level crashes on main unrelated to docs | `execution crashed` (runtime) vs test assertion failures are different root causes |

## Results & Parameters

**Session outcome**: No fixes required. Both CI failures confirmed pre-existing.

**Evidence collected**:

```bash
# 1. No Mojo files in PR
git diff main..3158-auto-impl --name-only | grep "\.mojo$"
# Output: (empty — confirmed no Mojo changes)

# 2. CLAUDE.md line count
wc -l CLAUDE.md
# Output: 1199 (target was <1400)

# 3. All new linked files exist
ls .claude/shared/output-style-guidelines.md \
   .claude/shared/tool-use-optimization.md \
   docs/dev/testing-strategy.md
# Output: all three files present
```

**Failure signatures**:

| Failure | Signature | Pre-existing on main? |
|---------|-----------|----------------------|
| Check Markdown Links | lychee cannot resolve root-relative paths (`/.claude/shared/`) | Yes — 5+ consecutive failures on main |
| Comprehensive Tests | `mojo: error: execution crashed` (runtime, not assertion) | Yes — same crashes in main run 22748872310 |
