---
name: impl-already-committed-and-pr-open
description: 'Detect and handle auto-impl worktrees where all changes are already
  committed and a PR is already open. Use when: branch is named <number>-auto-impl,
  git status is clean, and git log HEAD shows a commit matching the issue title.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# impl-already-committed-and-pr-open

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-05 |
| Category | documentation |
| Objective | Recognize that an auto-impl session has nothing left to do because work was pre-committed |
| Outcome | SUCCESS — read files, confirmed both target files already had changes, found existing open PR, reported state |
| Issue | #3087 ([Cleanup] Track image loading external dependency) |

## When to Use

Trigger this skill when ALL of the following are true:

- You are in a worktree branch named `<number>-auto-impl`
- `git status` shows clean working tree (only untracked `.claude-prompt-*.md`)
- `git log --oneline -1` shows a commit message matching the issue title
- `gh pr list --head <branch>` returns an open PR

**Do NOT use this skill** when:

- `git status` shows staged or unstaged changes
- The files referenced in the issue are missing the expected content
- No PR exists yet

## Verified Workflow

### Step 1: Check git status immediately

```bash
git log --oneline -3
git status
```

If the log already contains a commit matching the issue title and status is clean, the work is done.

### Step 2: Read target files to confirm content is present

```bash
# Read the specific lines cited in the issue
```

Verify the expected changes are actually in the files. Do not trust the commit message alone.

### Step 3: Check for an existing PR

```bash
gh pr list --head <branch-name>
```

If an open PR exists, it will include the PR number, title, and URL.

### Step 4: Optionally verify PR details

```bash
gh pr view <pr-number>
```

Confirm `auto-merge` is enabled and the PR description includes `Closes #<number>`.

### Step 5: Report and stop

Report the PR URL to the user. Do **not**:

- Create a duplicate commit
- Push again (branch is already up to date with remote)
- Create a second PR

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| (None in this session) | N/A | N/A | The verify-first pattern was followed correctly; no spurious actions taken |
| Anticipated failure: re-committing | Staging `.claude-prompt-*.md` or re-editing target files to "have something to commit" | Creates noise commit with unrelated files or duplicate changes | Never commit prompt files; verify file content matches issue requirements before touching anything |
| Anticipated failure: creating duplicate PR | Running `gh pr create` without first checking `gh pr list --head <branch>` | Creates a second open PR for the same branch, causing CI confusion | Always check for existing PRs before creating one |

## Results & Parameters

### Session Summary

- **Issue**: #3087 — "[Cleanup] Track image loading external dependency"
- **Branch**: `3087-auto-impl`
- **Worktree**: `/home/mvillmow/Odyssey2/.worktrees/issue-3087`
- **Files checked**: `examples/lenet-emnist/run_infer.mojo:340-346`, `examples/lenet-emnist/README.md:253-277`
- **Finding**: Both files already contained the full structured NOTE comment and README section
- **Confirming commit**: `f320de3d docs(lenet-emnist): document image loading limitation and Python interop workaround`
- **PR found**: #3193 (OPEN, auto-merge enabled, `cleanup` label, `Closes #3087`)
- **Action taken**: None (correct)

### Key Decision Points

1. **Read files before assuming work is needed.** The `.claude-prompt-*.md` file says "implement" but the branch may already be fully implemented.
2. **Check `gh pr list --head <branch>` before `gh pr create`.** A previous session may have already created the PR.
3. **`git status` clean + matching commit = done.** No need to look further unless file content verification fails.

### Diagnostic Commands

```bash
# Check commit history
git log --oneline -5

# Check working tree state
git status

# Verify target file content
# (use Read tool with line range from issue)

# Check for existing PR
gh pr list --head "$(git branch --show-current)"

# View PR details
gh pr view <number>
```
