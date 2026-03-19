---
name: verify-before-fix
description: 'Verify PR state before implementing review fixes to avoid unnecessary
  changes. Use when: a fix plan is provided but the PR may already be correct, CI
  failures are present that may be pre-existing, or a docs-only PR has unrelated test
  failures.'
category: documentation
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | verify-before-fix |
| **Category** | documentation |
| **Complexity** | Low |
| **Risk** | Low — read-only verification |

Confirms whether a PR already satisfies its success criteria before applying fixes.
Prevents wasted effort and accidental regressions from implementing unnecessary changes.

## When to Use

- A `.claude-review-fix-<number>.md` plan says "no fixes required" — confirm before skipping
- CI shows failing tests on a documentation-only PR
- Pre-existing CI failures may be unrelated to the PR's diff
- Review feedback has already been addressed in a previous commit

## Verified Workflow

1. **Read the fix plan** — check if it says "no fixes required"
2. **Verify success criteria** directly in the working directory:
   - Check the actual file contents match what was requested
   - Confirm referenced canonical docs exist
3. **Attribute CI failures** — determine if failures predate the PR change:
   - A docs-only diff (`.md` files only) cannot cause Mojo test failures
   - Compare failing tests against the PR diff to rule out causation
4. **Conclude**: if all criteria are met and failures are pre-existing, no commit is needed

### Example Verification Commands

```bash
# Verify a CLAUDE.md section is within line budget
grep -n "## Testing Strategy" CLAUDE.md
# Then count lines in that section

# Confirm canonical doc exists
ls -la docs/dev/testing-strategy.md

# Check PR diff scope (docs only = cannot break tests)
git diff main...HEAD --name-only
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Implementing fixes when plan says none needed | Following fix script template literally without reading the conclusion | Would create an empty or no-op commit | Always read the fix plan conclusion before taking action |
| Treating all CI failures as blockers | Blocking merge on 3 failing test groups for a docs-only PR | Failures were pre-existing and unrelated to the diff | Attribute failures to the diff — docs changes cannot break Mojo tests |
| Running full test suite to verify no-op | Running `pytest` to confirm nothing changed | Time wasted; result was already known from the diff | A documentation-only diff has a deterministic blast radius |

## Results & Parameters

**Session context**: PR #3348 (issue #3153) — trimmed `CLAUDE.md` Testing Strategy section

**Success criteria verified**:

```bash
# 1. Section is <= 10 lines (was 3 lines after trim)
grep -A5 "## Testing Strategy" CLAUDE.md

# 2. Canonical doc exists
ls -la docs/dev/testing-strategy.md

# 3. Markdown linting passes
just pre-commit-all
```

**Key conclusion pattern**:

> "The diff is exactly what the issue requested. The failing CI tests are pre-existing and
> unrelated to a documentation-only change. No fixes required."

**When to escalate**: If the fix plan identifies real problems (broken links, missing files,
wrong content), implement those. Only skip implementation when the plan explicitly concludes
"no fixes required" AND independent verification confirms the success criteria are met.
