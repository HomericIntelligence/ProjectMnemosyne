---
name: pr-review-clean-state-handling
description: "Handle PR review plans that report no issues and no fixes required. Use when: review plan says 'No problems found', automated feedback reports clean PR, or CI is pending but no code changes needed."
category: documentation
date: 2026-03-06
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| Category | documentation |
| Trigger | Review plan file reports "No problems found" / "No fixes required" |
| Root Cause | Automated review scripts always ask for fixes even when none are needed |
| Fix | Read the plan, confirm clean state, do not fabricate work |

## When to Use

- A `.claude-review-fix-*.md` file (or similar review plan) states "No problems found"
- The "Fix Order" section says "No fixes required"
- CI has not yet run but the PR code is correct
- Automated review tooling invokes a fix workflow on a clean PR

## Verified Workflow

1. **Read the review plan file** to understand what fixes are requested:

   ```bash
   cat .claude-review-fix-<issue>.md
   ```

2. **Check the "Problems Found" and "Fix Order" sections**. If both say "None" / "No fixes required", the task is complete.

3. **Do NOT create empty commits** to satisfy the automation. An empty commit is worse than no commit.

4. **Optionally verify CI status** to confirm the PR is truly clean:

   ```bash
   gh pr checks <pr-number>
   ```

5. **Report the clean state** to the user and stop. No code changes, no commits, no pushes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Create empty fix commit | Ran `git commit --allow-empty` to satisfy automation | Empty commits add noise to history with zero value | Never fabricate work; if the plan says no fixes, do nothing |
| Re-run grep to find missed issues | Searched codebase for remaining NOTE: comments to fix | The review plan already covered this; extra work is out of scope | Trust the review plan; if it says clean, it is clean |

## Results & Parameters

### Decision Logic

```text
Read review plan
  |
  v
Problems Found == "None"?
  YES --> Fix Order == "No fixes required"?
            YES --> DONE. Report clean state. No commits needed.
            NO  --> Follow the fix order
  NO  --> Implement the listed fixes
```

### Key Rule

When a review plan's "Problems Found" section is empty and "Fix Order" says "No fixes required",
**the correct action is to do nothing and report that the PR is already clean**.
Do not create commits, do not search for extra work, do not push.
