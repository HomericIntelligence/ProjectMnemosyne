---
name: cleanup-deprecated-stub
description: 'Delete deprecated stub files safely after verifying no remaining references.
  Use when: a file is marked DEPRECATED, a module was reorganized leaving a stub behind,
  or a cleanup issue requests deletion with import verification.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | cleanup-deprecated-stub |
| **Category** | tooling |
| **Trigger** | File is marked DEPRECATED or is a post-reorganization stub |
| **Output** | File deleted, PR created, auto-merge enabled |

## When to Use

- A `[Cleanup]` issue requests deletion of a deprecated `.mojo` file
- A module was reorganized into a subdirectory and a stub redirect file remains
- The stub contains only docstring/comments (no actual exports or implementations)
- You need to verify no imports reference the file before deleting

## Verified Workflow

1. **Read the deprecated file** to confirm it contains no actual exports (only docstring/comments/redirect text).

2. **Search for direct references** using two parallel searches:
   - `Glob` to confirm the file exists and find its path
   - `Grep` on the module name to see all import references

3. **Distinguish directory vs file imports**: In Mojo, `from shared.training.schedulers import X`
   resolves to `schedulers/__init__.mojo` if `schedulers/` directory exists, NOT to `schedulers.mojo`.
   Verify the directory exists with its own `__init__.mojo`.

4. **Verify no file uses explicit file path** (e.g., `from shared.training.schedulers.mojo import`
   which doesn't exist in Mojo but confirm via grep).

5. **Delete the file**: `git rm <path>` (stages deletion for commit).

6. **Attempt build** to validate: `pixi run mojo build shared`. Note: GLIBC mismatch or Docker-only
   environments may block local build — this is a pre-existing environment constraint, not caused
   by the deletion. Confirm by checking whether mojo works at all in the environment.

7. **Commit with conventional message**:
   ```
   cleanup(<scope>): delete deprecated <name>.mojo stub

   Closes #<number>
   ```

8. **Push and create PR**:
   ```bash
   git push -u origin <branch>
   gh pr create --title "..." --body "Closes #<number>" --label "cleanup"
   gh pr merge --auto --rebase <pr-number>
   ```

## Key Insight: Mojo Directory vs File Resolution

When both `schedulers.mojo` and `schedulers/` directory exist, Mojo resolves
`from shared.training.schedulers import X` to the **directory's `__init__.mojo`**.
The `.mojo` file stub is shadowed and unused. This makes stubs safe to delete
as long as the directory and its `__init__.mojo` exist.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo build shared` to validate | Executed build after deletion to confirm no breakage | GLIBC version mismatch prevented mojo from running at all (pre-existing env issue, not related to deletion) | Check if mojo is runnable in the environment first; GLIBC mismatch is a Docker-only env constraint |
| Searching for `.mojo` file-specific imports | Grepped for `from shared.training.schedulers.mojo` | No matches found (Mojo doesn't use file extensions in imports) | File-extension imports don't exist in Mojo — directory resolution is the relevant check |

## Results & Parameters

**Verified safe deletion criteria:**
- File contains only docstring/comments (zero executable code, zero exports)
- A `schedulers/` directory with `__init__.mojo` exists at the same level
- No grep matches for `<module>.mojo` style imports anywhere in the codebase

**Commit message template:**
```
cleanup(<scope>): delete deprecated <name>.mojo stub

The file was a placeholder left after reorganization. All implementations
live in <module>/ and all imports already resolve to that directory. No
references to this file exist.

Closes #<issue>
```
