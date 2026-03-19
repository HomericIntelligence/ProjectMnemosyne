---
name: pr-review-no-action-determination
description: 'Determine when a PR requires no fixes by distinguishing pre-existing
  CI failures from PR-introduced regressions. Use when: PR has red CI but changes
  are unrelated to failing jobs.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | pr-review-no-action-determination |
| **Category** | ci-cd |
| **Trigger** | PR has CI failures but changes appear unrelated |
| **Outcome** | Confirmed no-action determination with evidence |

## When to Use

- A PR shows red CI checks but only modifies documentation, configuration, or agent files
- `link-check` fails on a PR that did not add new broken links
- Runtime crash tests fail on a PR that does not touch the crashing code
- You need to verify a PR is merge-ready despite failing CI jobs
- A review plan states "no fixes required" and you need to confirm correctness

## Verified Workflow

1. **Identify failing CI jobs** — read the review plan or check `gh run list --branch <branch>` to enumerate failures.

2. **Classify each failure** — for each failing job, determine if it could plausibly be caused by the PR's diff:
   - Agent/config-only changes cannot cause Mojo runtime crashes
   - Documentation-only changes cannot cause test execution failures
   - Link-check failures from `CLAUDE.md` root-relative paths predate any PR

3. **Cross-check on main** — confirm failures are pre-existing by checking main branch CI:

   ```bash
   gh run list --branch main --workflow "<failing-workflow-name>" --limit 3
   gh run view <main-run-id> --log-failed | grep -E "(FAILED|error)"
   ```

4. **Confirm PR diff scope** — verify the PR only touches the expected files:

   ```bash
   gh pr diff <pr-number> --name-only
   ```

5. **Declare no-action** — if all failures are pre-existing and unrelated to the PR diff, the PR is ready to merge as-is. Document findings:

   ```bash
   gh issue comment <issue-number> --body "CI failures confirmed pre-existing. PR ready to merge."
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Applying fixes for link-check failures | Attempted to update links in new files to pass lychee link-check | The checker fails on root-relative paths in CLAUDE.md and other pre-existing files regardless of what the PR adds — the tool lacks `--root-dir` configuration | link-check failures are infrastructure-level; fixing individual file links does not resolve the CI job |
| Treating all red CI as blocking | Assumed every CI failure required a code fix | Autograd test crashes are Mojo runtime instability unrelated to agent config changes; fixing them is out of scope for a config PR | Scope discipline: only fix regressions introduced by the PR, not pre-existing repo-wide issues |

## Results & Parameters

### Confirming pre-existing link-check failure

```bash
# Check if link-check fails on main (confirms pre-existing)
gh run list --branch main --workflow "Check Markdown Links" --limit 3 --json status,conclusion,databaseId

# View failure details
gh run view <run-id> --log-failed | grep -E "ERROR|404|not found"
```

### Confirming pre-existing test crashes

```bash
# Check if the same test group crashes on main
gh run list --branch main --workflow "Comprehensive Tests" --limit 3
gh run view <run-id> --log-failed | grep "execution crashed"
```

### Final determination output

When both checks confirm pre-existing failures, document:

```
## CI Failure Analysis

| Job | Status | Caused by this PR? | Evidence |
|-----|--------|--------------------|----------|
| link-check | FAIL | No | Fails on main (run #XXXXX) — lychee lacks --root-dir |
| Autograd tests | FAIL | No | Fails on main (run #XXXXX) — Mojo runtime crash |

**Conclusion**: PR is merge-ready. No fixes required.
```
