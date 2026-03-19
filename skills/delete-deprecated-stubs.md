---
name: delete-deprecated-stubs
description: 'Safely delete deprecated re-export stub files after verifying no code
  imports reference them. Use when: cleanup issues target files marked DEPRECATED,
  consolidation left behind compatibility shims, or doc references need updating post-deletion.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | delete-deprecated-stubs |
| **Category** | documentation |
| **Trigger** | Cleanup issue targeting a deprecated/stub file |
| **Language** | Any (demonstrated with Mojo) |
| **Output** | Deleted file, updated docs, passing pre-commit |

## When to Use

- A file is annotated with `DEPRECATED`, `# legacy`, or `# compatibility shim`
- A cleanup GitHub issue says "delete file X"
- Consolidation left a re-export stub that duplicates canonical location
- Documentation references a file that no longer exists or has moved

## Verified Workflow

### Step 1: Confirm file exists and read it

```bash
# Confirm the target
ls tests/shared/fixtures/mock_models.mojo
```

Read the file to understand what it re-exports and confirm it is truly a stub.

### Step 2: Search for all import references

Search `.mojo` files (or language-appropriate extension) for the module name:

```bash
# Grep across all source files — not just same directory
grep -r "mock_models" --include="*.mojo" .
```

Key insight: **only comments and docs may reference it** — not actual `import` or `from` statements. If actual imports exist, update callers before deleting.

### Step 3: Delete the file

```bash
rm tests/shared/fixtures/mock_models.mojo
```

### Step 4: Update documentation references

Search non-code files for the old path:

```bash
grep -r "mock_models" --include="*.md" .
grep -r "mock_models" --include="*.mojo" .  # catches __init__.mojo comments
```

For each hit, update the reference to point to the canonical location (e.g., `shared/testing/test_models.mojo`).

Files to check:
- `__init__.mojo` or `__init__.py` in the same directory (may have backward-compat comments)
- `docs/dev/*.md` — architecture/pattern docs
- `tools/*.md` — integration guides

### Step 5: Run pre-commit hooks

```bash
pixi run pre-commit run --files <changed files>
```

Expected: all hooks pass except `mojo format` if GLIBC is incompatible with the local environment (known infrastructure issue — CI will handle it).

### Step 6: Commit, push, create PR

```bash
git add <changed files>
git commit -m "cleanup(scope): delete deprecated <filename>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking only `.mojo` files for references | Grepped only source code for imports | Missed references in `__init__.mojo` comments and `.md` doc files | Always grep across ALL file types after deletion |
| Assuming `__init__.mojo` was clean | Did not read it before deleting | It had a backward-compat comment referencing the deleted file | Always read the `__init__` file in the same directory |

## Results & Parameters

**Session outcome**: Deleted `tests/shared/fixtures/mock_models.mojo` (41-line re-export stub). Updated 3 documentation locations. PR #3254 created with auto-merge enabled.

**Key parameters**:
- Search pattern: exact module name (e.g., `mock_models`) across all file types
- Doc update strategy: replace old path with canonical path in all `.md` and `__init__` comments
- Pre-commit skip: `mojo format` hook may fail in environments with old GLIBC — use `SKIP=mojo-format` if needed, document reason

**Commit message template**:

```text
cleanup(fixtures): delete deprecated <filename>

Remove the deprecated re-export stub `<path>` that was left behind
after consolidation into `<canonical-path>`. Update documentation
references to point to the canonical location.

Closes #<issue-number>
```
