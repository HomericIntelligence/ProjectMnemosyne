---
name: update-blocker-note
description: 'Update blocked feature NOTE comments with issue tracking references
  and resolution path. Use when: a NOTE comment lacks a tracking issue number, a blocker
  needs a resolution path, or cleanup issues require linking NOTEs to parent tracking
  issues.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | update-blocker-note |
| **Category** | documentation |
| **Trigger** | Cleanup issue for a NOTE/FIXME/TODO comment that references a blocker |
| **Output** | Updated comment with issue number + resolution path line |
| **Scope** | Single-file, comment-only change |

## When to Use

- A GitHub cleanup issue asks you to "link to Track N tracking" for a NOTE comment
- A NOTE comment says "blocked by X" but has no issue number for traceability
- A parent tracking issue (e.g. `#3076`) collects all interop blocker NOTEs
- The success criteria include "NOTE updated with tracking reference"

## Verified Workflow

1. **Read the issue** to identify: file path, line number, current NOTE text, related parent issue
2. **Read the target file** at the specified line range to see exact comment text
3. **Search for the parent tracking issue** if not specified:
   ```bash
   gh issue list --search "Track 4 interop" --state open --limit 10
   ```
4. **Edit the comment** — make two targeted changes:
   - Add `(#<issue-number>)` to the `NOTE:` marker → `NOTE(#3092):`
   - Append a tracking line referencing the parent issue and resolution condition:
     ```
     # Track resolution via #<parent>. Implement when <condition>.
     ```
5. **Verify the diff** with `git diff` — confirm only comment lines changed
6. **Commit** with `fix(scope): update NOTE with tracking reference` format
7. **Push + PR** linked to the cleanup issue with "Closes #N"
8. **Enable auto-merge**: `gh pr merge --auto --rebase`
9. **Post completion comment** to the issue with before/after diff

### Example Edit

Before:
```mojo
# NOTE: Batch iteration blocked by Track 4 (Python↔Mojo interop).
# The data_loader is currently a PythonObject, but step() requires ExTensor.
# Once Track 4 data loading infrastructure is ready, integrate batching here.
```

After:
```mojo
# NOTE(#3092): Batch iteration blocked by Track 4 (Python↔Mojo interop).
# The data_loader is currently a PythonObject, but step() requires ExTensor.
# Once Track 4 data loading infrastructure is ready, integrate batching here.
# Track resolution via #3076. Implement when Python↔Mojo interop is available.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit without Read | Called Edit tool directly on the file | Tool requires file to be read first in the conversation | Always Read the target file before Edit, even if you already saw its content from a sibling file |
| Reading main repo copy | Read `/home/mvillmow/Odyssey2/shared/training/__init__.mojo` | Worktree has its own copy at `.worktrees/issue-3092/` path | Always edit the worktree path, not the main repo path |

## Results & Parameters

### Commit message format

```
fix(training): update NOTE with Track 4 tracking reference

Add issue #<N> to the NOTE comment for <feature> blocked by Track 4
to improve traceability. Also document resolution path via #<parent>.

Closes #<N>
Part of #<parent-epic>
```

### PR body format

```markdown
## Summary
- Updated NOTE comment in `<file>:<line>` to reference issue #<N>
- Added tracking line referencing #<parent> as the resolution path
- No logic changes — comment-only update
```

### Success criteria checklist

- Linked to Track 4 tracking (via parent issue reference in comment)
- Workaround documented (existing `_ = var` or equivalent noted)
- NOTE updated with issue number in marker: `NOTE(#N):`
