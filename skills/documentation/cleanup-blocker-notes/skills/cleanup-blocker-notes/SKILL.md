---
name: cleanup-blocker-notes
description: "Update blocked NOTE comments with issue tracking references. Use when: a NOTE/TODO documents a feature blocked by an unresolved external dependency, a cleanup issue asks to update blocker comments, or pre-commit mojo-format fails due to GLIBC incompatibility in the local environment."
category: documentation
date: 2026-03-04
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | cleanup-blocker-notes |
| **Category** | documentation |
| **Trigger** | Cleanup issues for blocked NOTE/TODO comments in Mojo source files |
| **Output** | Comment-only edits adding issue tracking references; no functional code changes |

## When to Use

- A GitHub issue asks to "clean up" or "update" NOTE comments that document blocked features
- NOTEs reference an unresolved initiative (e.g., "Track 4", "Phase 2") without an issue number
- The blocking initiative is still active — action is to track, not implement
- Pre-commit `mojo-format` hook fails with GLIBC version errors (environment limitation)

## Verified Workflow

1. **Read the issue** — `gh issue view <number> --comments` to get the full plan including file/line locations
2. **Search for all NOTEs** — `Grep` for `NOTE.*Track 4` / `NOTE.*blocked` across `*.mojo` files to confirm count and locations
3. **Read each file** at the target lines to verify exact current content before editing
4. **Apply edits** with `Edit` tool — add `Tracked in #<issue> (parent: #<parent>)` to each NOTE line
   - For inline `# NOTE:` comments: append reference on the same line or following line
   - For docstring `Note:` sections: append reference as last sentence of the Note paragraph
   - For `# Blocked:` comments: append ` - see #<issue> (parent: #<parent>)` inline
5. **Run pre-commit** — `pixi run pre-commit run --all-files`
   - If `mojo-format` fails with GLIBC errors: use `SKIP=mojo-format pixi run pre-commit run --all-files`
   - GLIBC incompatibility is a pre-existing infrastructure issue, not caused by comment changes
   - All other hooks (markdownlint, ruff, trailing-whitespace, etc.) must pass
6. **Commit** with `docs(scope): add issue references to <initiative> <type> NOTEs`
   - Include `Closes #<issue>` in commit message
7. **Push and create PR** — `gh pr create` with `--label cleanup`
8. **Enable auto-merge** — `gh pr merge --auto --rebase`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` command runner | `just` not in PATH in this environment | Use `pixi run pre-commit run --all-files` directly |
| Running mojo-format hook normally | Let all pre-commit hooks run | GLIBC_2.32/2.33/2.34 not found on host; mojo binary incompatible with Debian 10 libc | Skip mojo-format with `SKIP=mojo-format` — comment-only changes don't need formatting |
| Implementing the blocked feature | Tried to implement Python data loader integration | Track 4 is still active; implementation blocked | When blocker is unresolved, update comments with issue refs only — do NOT implement |

## Results & Parameters

### Edit Pattern for Inline NOTE Comments

```mojo
# Before
# NOTE: Feature X blocked by Track 4 (Python↔Mojo interop).
# For now, placeholder used until Track 4 is ready.

# After
# NOTE: Feature X blocked by Track 4 (Python↔Mojo interop).
# Tracked in #3076 (parent: #3059). Placeholder used until Track 4 is ready.
```

### Edit Pattern for Docstring Note Sections

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

### Edit Pattern for Blocked Comments

```mojo
# Before
# Blocked: Track 4 (Python↔Mojo interop)

# After
# Blocked: Track 4 (Python↔Mojo interop) - see #3076 (parent: #3059)
```

### Pre-commit Command (with GLIBC workaround)

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

### Commit Message Template

```
docs(training): add issue references to Track 4 Python interop NOTEs

Updates N blocked NOTEs in shared/<module>/ to reference tracking
issues #<issue> and #<parent>. <Initiative> remains active;
no functional changes made.

Closes #<issue>
```
