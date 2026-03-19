---
name: delete-deprecated-file
description: 'Delete a deprecated file after verifying no remaining imports or references.
  Use when: (1) file marked DEPRECATED needs removal, (2) consolidation leaves stub/re-export
  files, (3) cleanup issues require file deletion with safety checks.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | delete-deprecated-file |
| **Category** | tooling |
| **Complexity** | Low |
| **Time** | < 5 minutes |
| **Risk** | Low (read-only verification before deletion) |

Safely delete deprecated files from the codebase by first verifying no active imports
reference the file, then deleting it, and finally confirming tests still pass.

## When to Use

- A file has a `DEPRECATED` marker and is scheduled for deletion
- Consolidation work left behind a stub or re-export file
- A GitHub cleanup issue explicitly requests file deletion
- The file is no longer imported anywhere in the codebase

## Verified Workflow

### 1. Read the Issue

```bash
gh issue view <number> --comments
```

Identify the target file path and any known dependencies.

### 2. Verify No Active Imports

Search for all imports of the file across the codebase:

```bash
# For Mojo files
grep -r "from.*mock_models\|import.*mock_models" tests/ shared/ --include="*.mojo"

# General pattern
grep -r "<module_name>" . --include="*.mojo" --include="*.py"
```

If any active imports are found, update them before deleting the file.

### 3. Check Git History (Optional)

```bash
git log --oneline -- path/to/deprecated/file.mojo
```

Confirms the file's purpose and consolidation history.

### 4. Delete the File

```bash
git rm path/to/deprecated/file.mojo
```

Using `git rm` stages the deletion immediately.

### 5. Commit and Push

```bash
git add -u
git commit -m "cleanup(scope): delete deprecated <file>

<file> was a re-export stub left after consolidation.
No active imports reference this file.

Closes #<issue-number>"
git push -u origin <branch>
```

### 6. Create PR

```bash
gh pr create \
  --title "cleanup(scope): delete deprecated <file>" \
  --body "Closes #<issue-number>"
```

### 7. Verify CI

```bash
gh pr checks <pr-number> --watch
```

## Results & Parameters

**Session Example** (Issue #3062):

- **File deleted**: `tests/shared/fixtures/mock_models.mojo`
- **Reason**: Re-export stub left after consolidation, marked `DEPRECATED`
- **Imports found**: 0 (safe to delete)
- **PR created**: #3254
- **CI**: Passed

**Key observations**:

- The file had already been deleted in a prior commit on the branch (`213f7566`)
- The PR was also already created (`#3254`) before the retrospective session
- The branch `3062-auto-impl` tracked `origin/3062-auto-impl` cleanly
- No test failures because no other file imported the deprecated module

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — clean execution | The deletion and PR were pre-done by auto-impl | No failures in this session | Verify branch/PR state before starting; work may already be done |

## Notes

- Always use `git rm` instead of `rm` to stage the deletion atomically
- Check `git status` before starting — prior automation may have already completed the work
- The `DEPRECATED` marker in the file and issue body are the authoritative signals for safe deletion
- Pre-commit hooks will catch any residual import references if linting is configured
