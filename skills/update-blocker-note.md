---
name: update-blocker-note
description: 'Update blocked feature NOTE comments with issue tracking references
  and resolution path. Use when: a NOTE comment lacks a tracking issue number, a blocker
  needs a resolution path, cleanup issues require linking NOTEs to parent tracking
  issues, or pre-commit mojo-format fails due to GLIBC incompatibility.'
category: documentation
date: 2026-04-07
version: 1.1.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | update-blocker-note |
| **Category** | documentation |
| **Trigger** | Cleanup issue for a NOTE/FIXME/TODO comment that references a blocker |
| **Output** | Updated comment with issue number + resolution path line |
| **Scope** | Single-file or multi-file comment-only change |

## When to Use

- A GitHub cleanup issue asks you to "link to Track N tracking" for a NOTE comment
- A NOTE comment says "blocked by X" but has no issue number for traceability
- A parent tracking issue (e.g. `#3076`) collects all interop blocker NOTEs
- The success criteria include "NOTE updated with tracking reference"
- A GitHub issue asks to "clean up" or "update" NOTE comments that document blocked features
- NOTEs reference an unresolved initiative (e.g., "Track 4", "Phase 2") without an issue number
- The blocking initiative is still active — action is to track, not implement
- Pre-commit `mojo-format` hook fails with GLIBC version errors (environment limitation)

## Verified Workflow

1. **Read the issue** — `gh issue view <number> --comments` to get the full plan including file/line locations and related parent issue
2. **Search for all NOTEs** — `Grep` for `NOTE.*Track 4` / `NOTE.*blocked` across `*.mojo` files to confirm count and locations:
   ```bash
   gh issue list --search "Track 4 interop" --state open --limit 10
   ```
3. **Read each target file** at the specified line range to see exact comment text before editing
4. **Apply edits** with `Edit` tool — make targeted changes:
   - Add `(#<issue-number>)` to the `NOTE:` marker → `NOTE(#3092):`
   - Append a tracking line referencing the parent issue and resolution condition:
     ```
     # Track resolution via #<parent>. Implement when <condition>.
     ```
   - For inline `# NOTE:` comments: append reference on same or following line
   - For docstring `Note:` sections: append reference as last sentence of the Note paragraph
   - For `# Blocked:` comments: append `- see #<issue> (parent: #<parent>)` inline
5. **Verify the diff** with `git diff` — confirm only comment lines changed
6. **Run pre-commit**:
   ```bash
   pixi run pre-commit run --all-files
   # If mojo-format fails with GLIBC errors:
   SKIP=mojo-format pixi run pre-commit run --all-files
   ```
   GLIBC incompatibility is a pre-existing infrastructure issue, not caused by comment changes. All other hooks (markdownlint, ruff, trailing-whitespace) must pass.
7. **Commit** with `fix(scope): update NOTE with tracking reference` or `docs(scope): add issue references` format
8. **Push + PR** linked to the cleanup issue with "Closes #N" and optionally `--label cleanup`
9. **Enable auto-merge**: `gh pr merge --auto --rebase`
10. **Post completion comment** to the issue with before/after diff

## Edit Patterns

### Inline NOTE Comment

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

### Docstring Note Section

```mojo
# Before
Note:
    data_loader remains PythonObject until Track 4 implements
    Mojo data loading infrastructure.

# After
Note:
    data_loader remains PythonObject until Track 4 implements
    Mojo data loading infrastructure. Tracked in #3076 (parent: #3059).
```

### Blocked Comment

```mojo
# Before
# Blocked: Track 4 (Python↔Mojo interop)

# After
# Blocked: Track 4 (Python↔Mojo interop) - see #3076 (parent: #3059)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit without Read | Called Edit tool directly on the file | Tool requires file to be read first in the conversation | Always Read the target file before Edit, even if you already saw its content from a sibling file |
| Reading main repo copy | Read `/home/mvillmow/Odyssey2/shared/training/__init__.mojo` | Worktree has its own copy at `.worktrees/issue-3092/` path | Always edit the worktree path, not the main repo path |
| Running `just pre-commit-all` | Used `just` command runner | `just` not in PATH in this environment | Use `pixi run pre-commit run --all-files` directly |
| Running mojo-format hook normally | Let all pre-commit hooks run | GLIBC_2.32/2.33/2.34 not found on host; mojo binary incompatible with older Linux | Skip mojo-format with `SKIP=mojo-format` — comment-only changes don't need formatting |
| Implementing the blocked feature | Tried to implement Python data loader integration | Track 4 is still active; implementation blocked | When blocker is unresolved, update comments with issue refs only — do NOT implement |

## Results & Parameters

### Commit message format

```
fix(training): update NOTE with Track 4 tracking reference

Add issue #<N> to the NOTE comment for <feature> blocked by Track 4
to improve traceability. Also document resolution path via #<parent>.

Closes #<N>
Part of #<parent-epic>
```

```
docs(training): add issue references to Track 4 Python interop NOTEs

Updates N blocked NOTEs in shared/<module>/ to reference tracking
issues #<issue> and #<parent>. <Initiative> remains active;
no functional changes made.

Closes #<issue>
```

### PR body format

```markdown
## Summary
- Updated NOTE comment in `<file>:<line>` to reference issue #<N>
- Added tracking line referencing #<parent> as the resolution path
- No logic changes — comment-only update
```

### Pre-commit command (with GLIBC workaround)

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

### Success criteria checklist

- Linked to Track 4 tracking (via parent issue reference in comment)
- Workaround documented (existing `_ = var` or equivalent noted)
- NOTE updated with issue number in marker: `NOTE(#N):`
