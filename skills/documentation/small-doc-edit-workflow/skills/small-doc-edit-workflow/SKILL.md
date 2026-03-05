---
name: small-doc-edit-workflow
description: "Workflow for implementing small, well-specified documentation edits in a worktree. Use when: (1) issue specifies exact insert location, (2) change is adding a note/clarification to markdown, (3) single targeted Edit with pre-commit verification."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | documentation |
| **Complexity** | S (small) |
| **Typical runtime** | < 5 minutes |
| **Key tools** | Read, Edit, Bash (pre-commit), git, gh |

## When to Use

- Issue specifies exact line number or anchor text for the insertion point
- Change is a single block of markdown to insert (note, warning, clarification)
- No structural refactoring required — pure additive change
- File is an existing markdown doc (`.md`)

## Verified Workflow

1. **Read the prompt file** — parse issue title, deliverable, and exact insertion point
2. **Read the target file** — confirm current content and line numbers
3. **Apply Edit** — use `old_string` anchored to the line just before and after the insertion point
4. **Run pre-commit** — `pixi run pre-commit run --all-files` to verify markdownlint and other hooks
5. **Commit** — stage only the modified file; use conventional commit format with `Closes #<issue>`
6. **Push and create PR** — `git push -u origin <branch>` then `gh pr create`
7. **Enable auto-merge** — `gh pr merge --auto --rebase <pr-number>`

### Key Edit Pattern

Use surrounding context to anchor the insertion uniquely:

```python
# old_string: the line before + newline
old_string = "Paste it into a new Claude Code session at the root of ProjectOdyssey.\n\n---"

# new_string: original line + new content + rest
new_string = """Paste it into a new Claude Code session at the root of ProjectOdyssey.

**Output**: Present the analysis as conversation text only. Do not create files or commit
the analysis to the repository.

---"""
```

### Pre-commit Caveat

The `mojo format` hook may print GLIBC version errors (library incompatibility with the host OS)
but still exits 0 — this is non-fatal. The markdown lint and Python hooks run normally.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` as the command runner | `just` not on PATH in this environment | Fall back to `pixi run pre-commit run --all-files` directly |
| Using `replace_all: false` without sufficient context | Tried a short old_string that could match multiple locations | Edit tool requires unique old_string | Always include the line before AND after the insertion point |

## Results & Parameters

### Commit message format

```text
docs(<scope>): <what was added>

<One sentence why>

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### PR body format

```markdown
## Summary

- Added `**Output**` note to `docs/ANALYSIS_PROMPT.md` after line 4

## Changes

- `docs/ANALYSIS_PROMPT.md`: Added note after instruction line

## Verification

- [x] `pixi run pre-commit run --all-files` passes (markdownlint, trailing-whitespace, etc.)

Closes #<issue-number>
```

### Auto-merge command

```bash
gh pr merge --auto --rebase <pr-number>
```
