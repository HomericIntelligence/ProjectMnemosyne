---
name: verify-ci-preexisting-failures
description: 'Verify that CI failures on a PR are pre-existing on main before attempting
  fixes. Use when: PR has CI failures that appear unrelated to its changes, or review
  plan claims failures are pre-existing.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | verify-ci-preexisting-failures |
| **Category** | documentation |
| **Use Case** | Confirm CI failures existed before this PR before wasting time fixing them |
| **Result** | Confident no-op commit or targeted fix based on evidence |

## When to Use

- PR touches only markdown/documentation files but has CI failures involving code execution
- Review plan states both CI failures are pre-existing on `main`
- CI failures are in categories unrelated to the PR's change type (e.g., link checker on a code PR, Mojo crashes on a docs-only PR)
- You are about to implement fixes but want to confirm the failures actually originate from this PR

## Verified Workflow

1. **Read the review plan** to understand which CI failures are claimed as pre-existing.

2. **Check for any references to removed/renamed files** that the PR might have introduced:
   ```bash
   grep -rn "old-filename.md" . --include="*.md"
   # Expected: no output if all references were updated
   ```

3. **Confirm the deleted/renamed file is gone**:
   ```bash
   ls agents/old-filename.md
   # Expected: file not found
   ```

4. **Verify the CI run IDs cited in the review plan** exist on `main`:
   ```bash
   gh run view <run-id> --json jobs | python3 -c \
     "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'FailingJob' in j['name']]"
   ```

5. **Check git status** to confirm branch is clean and no unintended changes remain:
   ```bash
   git status
   git log --oneline -5
   ```

6. **Conclusion**: If grep finds no broken references, the deleted file is gone, and CI run IDs confirm the same failures on `main` — the PR is correct and no fixes are needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Immediately fixing CI | Jumping to fix CI failures without first verifying their origin | Would have introduced unnecessary changes to a PR that was already correct | Always verify failure origin before implementing fixes |
| Skipping verification | Trusting the review plan without independent confirmation | Could miss genuine issues introduced by the PR | Run the grep/ls checks even if the plan says no fixes needed |

## Results & Parameters

**Session outcome**: PR #3334 (issue #3147) required zero fixes. Both CI failures confirmed pre-existing on `main`:

- `Check Markdown Links` — lychee fails on root-relative paths (`/.claude/...`) throughout repo, not fixable without `--root-dir` flag in CI config
- `Core Activations` — `mojo: error: execution crashed` pre-dates this PR (confirmed via run `22748872310` on `main`)

**Key commands used**:

```bash
# Verify no stale references remain
grep -rn "agent-hierarchy.md" . --include="*.md"

# Confirm deleted file is gone
ls agents/agent-hierarchy.md

# Confirm link check failure is pre-existing
gh run list --branch main --limit 5 --json name,conclusion

# Confirm Mojo crash on main
gh run view 22748872310 --json jobs | python3 -c \
  "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'Activ' in j['name']]"
```

**Decision rule**: If a PR only modifies markdown files and CI failures are in unrelated domains (Mojo execution, link resolution with root-relative paths), treat them as pre-existing until proven otherwise.
