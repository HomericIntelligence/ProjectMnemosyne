# Session Notes: verify-ci-preexisting-failures

## Date
2026-03-05

## Context

Working on PR #3334 implementing issue #3147: merge `agents/agent-hierarchy.md` into `agents/hierarchy.md`.

The `.claude-review-fix-3147.md` review plan described two CI failures and stated both were pre-existing on `main`.

## Objective

Implement all fixes from the review plan, or confirm none were needed.

## Steps Taken

1. Read `.claude-review-fix-3147.md` — the review plan
2. Ran `grep -rn "agent-hierarchy.md" . --include="*.md"` — only match was the review plan file itself
3. Ran `git status` — branch clean, only untracked file was the review plan
4. Confirmed last commit `58e1c98e docs(agents): merge agent-hierarchy.md into hierarchy.md` already implemented the fix

## CI Failures (Both Pre-existing)

### 1. Check Markdown Links (lychee)
- Root-relative paths like `/.claude/shared/*.md` and `/agents/hierarchy.md` fail without `--root-dir`
- These paths exist throughout the repo and fail on `main` too
- This PR only changed `agent-hierarchy.md` → `hierarchy.md` (correct target)
- No new broken links introduced

### 2. Core Activations (Mojo execution crash)
- `mojo: error: execution crashed` for all 4 activation test files
- PR only changes markdown files — cannot cause Mojo crashes
- Confirmed pre-existing via CI run `22748872310` on `main`

## Outcome

Zero fixes required. PR already correctly implemented:
- `agents/agent-hierarchy.md` deleted
- Content merged into `agents/hierarchy.md`
- All 7 cross-references updated (CLAUDE.md, agents/README.md, etc.)

## Key Learning

When a review plan says "no fixes needed," still verify independently:
- Check for stale references with grep
- Confirm deleted files are actually gone
- Spot-check CI run IDs cited as evidence
- Only then conclude the PR is ready