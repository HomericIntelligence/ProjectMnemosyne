---
name: auto-impl-preflight
description: 'Verify auto-impl issue completion and detect already-done work before
  starting. Use when: (1) prior session committed work and created a PR but implementation
  plan may have additional items not captured in the commit, (2) starting an auto-impl
  session and need to check if work was already done in a previous session.'
category: documentation
date: 2026-04-07
version: 1.1.0
user-invocable: false
---
# Auto-Impl Preflight Check

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-05 |
| Category | documentation |
| Objective | Verify that a prior auto-impl session completed all required steps, and identify any gaps between the implementation plan and actual commits |
| Outcome | SUCCESS — confirmed 3/4 planned file changes were committed; identified 1 missing item (testing-strategy.md update); PR already open |
| Issue | #3089 (document Float16 precision limitations in tests) |

## When to Use

Trigger this skill when:

- The worktree branch is named `<number>-auto-impl`
- `git log --oneline -5` shows a recent commit with "Closes #<number>"
- `gh pr list --head <branch>` shows an open PR already exists
- The issue has a detailed implementation plan (e.g., in issue comments) with multiple files to modify
- Need to determine if all plan items were executed or if some were skipped

**Do NOT use this skill** when:

- No commit exists yet (issue has not been implemented at all)
- The issue has no structured plan to compare against
- The PR was already merged

## Verified Workflow

### Step 1: Orient — check git log and PR state

```bash
git log --oneline -5
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)"
```

If a commit with "Closes #N" exists AND an open PR exists, prior session did substantial work. Proceed to Step 2.

### Step 2: Read the implementation plan from the issue

```bash
gh issue view <number> --comments
```

Extract the list of files to modify from the plan. Note each file and what change was planned.

### Step 3: Verify each planned file

For each file in the plan, read the relevant section to confirm the change was made:

```bash
# Read file header or changed section
```

Compare actual state against plan. Create a checklist:

- [x] File A — change present
- [x] File B — change present
- [ ] File C — change MISSING

### Step 4: For missing items, assess importance

Ask: Is the missing item in the issue's **Success Criteria** (required) or only in the implementation plan's Notes section (optional)?

- If in Success Criteria: implement the missing change
- If only in plan notes: document the gap in a PR comment and proceed

### Step 5: Handle the gap

**Option A — Implement the missing change:**

```bash
# Make the edit
# Run pre-commit
cd /path/to/worktree && just pre-commit-all
# Amend commit or create new commit
git add <file>
git commit -m "docs: add missing <description> from implementation plan

Part of #<number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push
```

**Option B — Document the gap:**

```bash
gh issue comment <number> --body "## Completion Review

Implementation is mostly complete (commit <sha>). One item from the plan was not included:

- docs/dev/testing-strategy.md Float16 subsection — this was in the plan notes but not in the issue Success Criteria. The core documentation objective (test file headers) is complete.

PR #<pr-number> is ready for review."
```

### Step 6: Verify PR is linked correctly

```bash
gh pr view <pr-number> --json body -q '.body'
```

Confirm "Closes #<number>" appears in the PR body. If not, edit the PR:

```bash
gh pr edit <pr-number> --body "$(gh pr view <pr-number> --json body -q '.body')

Closes #<number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | No failed attempts in this session — pattern was followed correctly | N/A | The key risk is over-implementing: adding changes beyond what Success Criteria require, or re-implementing things already done |

## Results & Parameters

### Session Summary — Issue #3089

- **Issue**: #3089 — "Document Float16 precision limitations in tests"
- **Branch**: `3089-auto-impl`
- **Prior commit**: `ad271e9c docs(tests): document Float16 precision limitations in test headers`
- **Open PR**: #3200 (already created by prior session)
- **Plan items**: 4 files (3 test files + 1 docs/dev file)
- **Completed**: 3/4 — all 3 test file headers updated
- **Missing**: `docs/dev/testing-strategy.md` Float16 subsection (in plan notes, NOT in Success Criteria)
- **Action taken**: Verified existing state; determined PR was complete for the issue's stated Success Criteria

### Key Decision Point

The implementation plan (in issue comments) listed 4 files to modify. The commit only touched 3. However, reading the issue's **Success Criteria** section showed:

```
- [ ] All Float16 precision NOTEs reviewed
- [ ] Limitations documented in test headers
- [ ] Tests appropriately handle Float16 cases
```

None of the success criteria mentioned `testing-strategy.md`. The missing file was only in the plan's "nice to have" section. Therefore the PR was already complete for the issue's requirements.

**Pattern**: Always compare missing items against Success Criteria, not just the plan notes.

### Diagnostic Commands

```bash
# Check what was committed vs plan
git show --stat HEAD

# Verify file header was updated
head -50 tests/models/test_alexnet_layers.mojo

# Check PR state and body
gh pr view <number> --json state,body,url

# Check issue success criteria
gh issue view <number> --json body -q '.body'
```
