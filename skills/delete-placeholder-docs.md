---
name: delete-placeholder-docs
description: 'Delete empty placeholder documentation stubs and remove broken links.
  Use when: stub files contain only placeholder text, YAGNI cleanup is needed, or
  broken links must be fixed.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
|----------|-------|
| Category | documentation |
| Complexity | S |
| Files changed | N stubs deleted + M referencing files updated |
| Pre-requisite | Confirm all files contain only placeholder text before deleting |

Deletes documentation stub files that contain only placeholder text (e.g. `Content here.`) and
removes all broken links to the deleted files from other documents. Applies the YAGNI principle:
documentation should be written alongside feature implementation, not created as empty stubs.

## When to Use

- A GitHub issue asks to delete empty/placeholder documentation files
- Files contain only placeholder text like "Content here." or similar boilerplate
- `docs/index.md` or other navigation files link to non-existent or stub content
- Cleanup pass after a documentation reorganization left orphaned stubs

## Verified Workflow

1. **Identify stub files** - Grep for placeholder text to confirm and find all stubs:

   ```bash
   grep -rl "Content here\." docs/
   ```

2. **Find all referencing files** - Search for links to each stub path across all docs:

   ```bash
   grep -rl "custom-layers\|debugging\.md\|..." docs/
   ```

3. **Read referencing files** - Read each file that links to stubs to understand context
   before editing (required by Edit tool).

4. **Delete stub files** - Use a single `rm` command for all stubs at once:

   ```bash
   rm docs/advanced/stub1.md docs/core/stub2.md docs/dev/stub3.md
   ```

5. **Update referencing files** - For each file containing broken links:
   - Remove the entire bullet/line for the deleted file
   - If removing from a section that becomes empty, remove or simplify the section
   - Keep links that point to real, substantive files (e.g. `benchmarking.md`, `troubleshooting.md`)

6. **Verify no broken links remain**:

   ```bash
   grep -rl "deleted-stub-path" docs/
   # Should return: No files found
   ```

7. **Run pre-commit** skipping hooks with known environmental failures:

   ```bash
   SKIP=mojo-format pixi run pre-commit run --all-files
   ```

8. **Commit, push, create PR** with `Closes #<issue>` in the message.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Deleting files without checking referencing files first | Ran `rm` on all stubs immediately | Left broken links in `docs/README.md`, `docs/glossary.md`, `docs/advanced/troubleshooting.md`, `docs/getting-started/first_model.md` | Always grep for all references before deleting |
| Running `just pre-commit-all` | Used `just` to invoke pre-commit | `just` not in PATH in this environment | Use `pixi run pre-commit run --all-files` directly |
| Expecting all pre-commit hooks to pass | Ran full pre-commit suite | `mojo-format` fails due to GLIBC version mismatch (pre-existing env issue, not caused by our changes) | Use `SKIP=mojo-format` when the hook failure is environmental, not code-related |

## Results & Parameters

**Session outcome**: Deleted 17 stub files, updated 5 referencing documents, all relevant
pre-commit hooks passed (markdown lint, ruff, yaml, trailing whitespace, etc.).

**Files typically referencing stubs**:
- `docs/index.md` - Main navigation hub (most links)
- `docs/README.md` - Directory structure tree + Next Steps section
- `docs/glossary.md` - See Also section
- `docs/getting-started/first_model.md` - Learn More + Related Documentation sections
- Topic-specific docs with cross-reference sections

**Key pattern for updating referencing files**: When a section in a nav file (like `index.md`)
contains only stubs, remove the entire section. When a section contains a mix, remove only
the stub links and keep substantive ones.

**Commit message format**:

```
docs: delete N empty placeholder documentation stubs

Remove all documentation files containing only "Content here." as
placeholder text. Per YAGNI, documentation should be written alongside
feature implementation, not created as empty stubs beforehand.

Also remove all broken links to the deleted files from:
- docs/index.md
- docs/README.md
- docs/glossary.md
- docs/advanced/troubleshooting.md
- docs/getting-started/first_model.md

Closes #NNNN
```
