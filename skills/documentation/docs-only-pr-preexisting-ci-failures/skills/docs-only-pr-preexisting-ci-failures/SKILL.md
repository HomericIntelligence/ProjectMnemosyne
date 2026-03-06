---
name: docs-only-pr-preexisting-ci-failures
description: "Verify and close a review-fix task when a docs-only PR has no actual code changes needed and CI failures are pre-existing. Use when: a review-fix plan concludes no changes are required, CI failures are unrelated to the PR diff, or a docs-only PR needs final pre-commit verification before merge."
category: documentation
date: 2026-03-06
user-invocable: false
---

# Skill: docs-only-pr-preexisting-ci-failures

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-06 |
| Objective | Verify a docs-only PR (ADR index update) is complete and no fixes are needed despite CI failures |
| Outcome | Success — pre-commit passes, no code changes needed, PR ready to merge |
| Category | documentation |

## When to Use

Use this skill when:

- A `.claude-review-fix-<number>.md` plan states "No problems found" or "No fixes needed"
- A PR modifies only documentation files (e.g., `docs/adr/README.md`) and CI test failures are in
  unrelated test groups (e.g., `Core Elementwise`, `Core Tensors`)
- You need to confirm a docs-only PR is merge-ready without making code changes
- CI reports failing test groups but the PR diff cannot possibly affect those tests

## Verified Workflow

### 1. Read the review fix plan

```bash
cat .claude-review-fix-<PR>.md
```

Look for:
- "No problems found" or "No fixes needed" — if present, no code changes are needed
- List of CI failures — verify they are in test groups unrelated to the changed files
- Verification commands suggested in the plan

### 2. Verify current git state

```bash
git status
git log --oneline -5
```

Confirm the feature branch is clean (no uncommitted changes) and the relevant commit exists
(e.g., the ADR index entry was already committed in a prior commit).

### 3. Verify the change is correct

For ADR index PRs, confirm the entry exists in `docs/adr/README.md`:

```bash
grep "ADR-00N" docs/adr/README.md
```

Also confirm the ADR file itself exists and the metadata matches:

```bash
head -20 docs/adr/ADR-00N-<name>.md
```

### 4. Run pre-commit to confirm hooks pass

```bash
pixi run pre-commit run --all-files 2>&1 | tail -20
```

Expected output: all hooks show `Passed`. The `mojo format` hook may emit GLIBC errors
(environment incompatibility on the local host) but still reports `Passed` at the end —
this is a known pre-existing environment issue, not a failure of the PR.

### 5. Confirm no commit is needed

If git status shows only the untracked `.claude-review-fix-<PR>.md` file and no modified files,
there is nothing to commit. The task is complete.

Do NOT commit the `.claude-review-fix-*.md` file — it is a task instruction artifact, not
part of the implementation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | No alternative approaches needed | Plan was clear: no changes required | When a review-fix plan says "no fixes needed," trust it and just verify + close |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| PR | #3338 |
| Issue | #3150 |
| Branch | `3150-auto-impl` |
| Files changed by PR | `docs/adr/README.md` only |
| Pre-commit result | All hooks passed |
| CI failures | `Core Elementwise`, `Core Tensors` — pre-existing, unrelated to diff |
| Commit needed | None |
| GLIBC errors | Present during pre-commit (env issue) but hooks still pass |

## Key Insights

1. **Trust the review-fix plan**: When `.claude-review-fix-<N>.md` says "No problems found,"
   the job is to verify, not to find something to fix. Read the plan carefully before
   touching anything.

2. **Docs-only PRs cannot cause test failures**: If a PR only changes markdown files in
   `docs/adr/`, any failing test groups are definitionally pre-existing. No investigation
   of the test failures is needed — just confirm the diff is documentation-only.

3. **GLIBC errors in pre-commit are environment noise**: On the worktree host, `mojo format`
   emits GLIBC version errors but still reports `Passed`. These are not hook failures.
   Look at the final per-hook status lines, not the stderr noise.

4. **Do not commit task artifacts**: The `.claude-review-fix-*.md` file is a task instruction
   file placed by automation. It should never be staged or committed.

5. **Untracked files in git status are normal**: After a no-op review fix, `git status` shows
   only the untracked `.claude-review-fix-*.md` file. This is the expected clean state.
