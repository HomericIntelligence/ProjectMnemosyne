---
name: git-stash-pop-conflict-semantic-merge
description: "Use when: (1) git stash pop produces merge conflicts and Safety Net blocks git checkout -- (discard) or git stash drop (delete), (2) a stash from an old branch conflicts with heavily refactored HEAD, (3) you need to evaluate which side of each conflict hunk is semantically correct rather than blindly choosing ours or theirs."
category: tooling
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Git Stash Pop Conflict: Semantic Merge Resolution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Resolve merge conflicts produced by `git stash pop` when Safety Net blocks both the discard path (`git checkout --`) and the delete path (`git stash drop`) |
| **Outcome** | Successful — all conflict markers resolved, pre-commit passed, branch pushed to PR |
| **Verification** | verified-local (pre-commit passed; CI validation pending) |

## When to Use

- `git stash pop` produces conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) in one or more files
- Safety Net blocks `git checkout -- <file>` (discard uncommitted changes permanently)
- Safety Net blocks `git stash drop stash@{N}` (permanently deletes stashed changes)
- The stash originated from an old branch and the stashed file version predates significant refactoring
- You want to evaluate each conflict hunk individually rather than accepting all-ours or all-theirs

## Verified Workflow

### Quick Reference

```bash
# 1. Find all conflict locations in a file
grep -n "<<<<<<\|======\|>>>>>>" <file>

# 2. Read surrounding context for each hunk (determine which side is semantically correct)
# Use Read tool or: sed -n '<start>,<end>p' <file>

# 3. Resolve each hunk by editing — keep the correct side, remove markers
# Repeat for all hunks

# 4. Verify no conflict markers remain
grep -c "<<<<<<\|======\|>>>>>>" <file>    # must output 0

# 5. Stage the resolved file
git add <file>

# 6. Continue work (commit, push, etc.)
```

### Detailed Steps

1. **Locate all conflicts** — Run `grep -n "<<<<<<\|======\|>>>>>>" <file>` to list every line with a conflict marker. Note the line numbers so you can read each hunk in context.

2. **Read each hunk** — For every conflict block, read a window of ~10 lines around it. Understand:
   - `<<<<<<< Updated upstream` (or `HEAD`) is the current branch state
   - `=======` is the divider
   - `>>>>>>> Stashed changes` is the stash content

3. **Evaluate semantics for each hunk independently** — Do not apply a global "accept ours" or "accept theirs" decision. Ask:
   - Which side has correct numbering / formatting?
   - Which side has more descriptive content?
   - Does one side contain content that was intentionally removed in HEAD?
   - Could the stash contain a genuine improvement that HEAD lacks?

4. **Edit out the markers** — Use the Edit tool to replace each conflict block with the correct content. Remove all three marker lines (`<<<<<<<`, `=======`, `>>>>>>>`).

5. **Verify resolution** — Run `grep -c "<<<<<<\|======\|>>>>>>" <file>`. Output must be `0`. If nonzero, a hunk was missed.

6. **Stage the file** — `git add <file>`. This signals to git that the conflict is resolved.

7. **Check overall status** — `git status` to confirm no other files remain in conflicted state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | `git checkout -- skills/learn/SKILL.md` | Safety Net blocked: "discards uncommitted changes permanently" | Safety Net treats `checkout --` as a destructive discard; cannot be used even for conflict resolution |
| Attempt 2 | `git stash drop stash@{0}` | Safety Net blocked: "permanently deletes stashed changes" | Even deleting an unwanted stash entry is blocked; must surface the command to the user or use Edit-based resolution |
| Attempt 3 | `git stash` (to save working state) then check main | No local changes existed to save — the conflicted file was already the working state produced by the failed stash pop | `git stash pop` leaves conflicted files as working-tree modifications; there is no separate "new" stash to create |

## Results & Parameters

### Common Hunk Patterns from Old-Branch Stashes

| Pattern | Likely Correct Side | How to Tell |
|---------|---------------------|-------------|
| Step numbering (e.g., step 6 vs step 5) | HEAD (upstream) | Step count changes with refactoring; stash has stale numbering |
| Indentation inside heredoc / code block | HEAD (upstream) | Stash may have content at column 0 that was moved inside a block |
| Section description detail | HEAD (upstream) | Upstream adds detail over time; stash has older, terser text |
| A new failure mode or edge case note | Stash | If the stash adds content that HEAD deleted, evaluate whether it's still valid |

### Decision Flowchart

```
For each conflict hunk:
  Is one side obviously outdated (old numbering, removed section)?
  ├─ YES → Take the other side (HEAD or stash, whichever is current)
  └─ NO → Can the content be merged (stash adds a line HEAD lacks)?
      ├─ YES → Manually combine both sides (true merge)
      └─ NO → Pick whichever side is more complete/descriptive
```

### Verification Commands

```bash
# Confirm no markers remain
grep -c "<<<<<<\|======\|>>>>>>" <file>   # expect: 0

# Confirm file is staged
git status                                 # expect: "Changes to be committed: modified: <file>"

# Confirm pre-commit passes (do this before committing)
pre-commit run --files <file>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | `skills/learn/SKILL.md` — stash from branch `136-auto-impl` conflicted with HEAD after step-renumbering refactor | Stash `stash@{0}` left in place (not dropped) after resolution |
