---
name: deprecated-file-cleanup
description: 'Safely delete deprecated stub files after verifying no active imports
  reference them. Use when: a file is marked DEPRECATED, a cleanup issue asks to delete
  a helper/utility, or you need to verify zero consumers before deletion.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | deprecated-file-cleanup |
| **Category** | tooling |
| **Effort** | Low (< 10 min) |
| **Risk** | Low — verify imports first |

Workflow for safely deleting deprecated stub files in a codebase. The key insight is that
deprecated stubs are often docstring-only placeholders pointing to the new location; no code
actually imports them. Verify this before deleting.

## When to Use

- Issue title contains `[Cleanup] Delete deprecated`
- File body contains `DEPRECATED` marker with consolidation notice
- File to delete is in a `helpers/` or similar utility directory
- You need to confirm zero consumers before removal

## Verified Workflow

1. **Read the deprecated file** — confirm it is a stub (no real code, only a docstring or
   redirect comment). If it has real code, stop and escalate.

2. **Search for imports** — use Grep to find any file that imports from the deprecated path:

   ```bash
   Grep pattern="helpers/gradient_checking|from tests.helpers.gradient" --output_mode=content
   ```

   Check ALL matches: docs, workflow files, test files, conftest. Only `.md` docs and the
   prompt file itself are acceptable matches. Any `.mojo`/`.py` import is a blocker.

3. **Delete the file**:

   ```bash
   rm path/to/deprecated_file.mojo
   ```

4. **Update documentation** — search for references in `.md` files (ADRs, READMEs, integration
   guides) and remove or update lines that list the now-deleted file. Do NOT remove references
   that explain the migration history; only remove file-listing entries.

5. **Run pre-commit** (skip mojo-format if GLIBC incompatible in the environment):

   ```bash
   SKIP=mojo-format pixi run pre-commit run --all-files
   ```

   All non-mojo hooks must pass (markdown lint, trailing whitespace, YAML, etc.).

6. **Commit with conventional message**:

   ```
   cleanup(tests): delete deprecated <filename>

   The <path> file was a deprecated stub pointing to <new location>.
   No files imported from it. Remove the file and update <doc> to
   reflect current state.

   Closes #<issue>
   ```

7. **Push and create PR** with auto-merge enabled.

## Results & Parameters

```bash
# Verify no imports (adapt pattern to file being deleted)
Grep pattern="helpers/<filename>|from <module_path>" output_mode=content

# Skip mojo-format when GLIBC incompatible
SKIP=mojo-format pixi run pre-commit run --all-files

# Commit
git commit -m "cleanup(tests): delete deprecated <filename>"

# Auto-merge PR
gh pr merge --auto --rebase <pr-number>
```

**Observed outcome**: 2 files changed, 20 deletions. PR #3251 created and auto-merge enabled.
All non-mojo pre-commit hooks passed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running full pre-commit | `pixi run pre-commit run --all-files` without SKIP | mojo-format fails with GLIBC_2.32/2.33/2.34 not found — environment incompatibility, not our change | Use `SKIP=mojo-format` when mojo binary cannot run locally; CI will still validate Mojo format |
| Checking only .mojo files for imports | Grepped only `*.mojo` files | Would miss Python imports or workflow references | Always search all file types with no glob filter first |
