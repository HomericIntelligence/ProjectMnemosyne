---
name: git-rebase-over-deletion
description: Fix CI failure caused by git rebase replaying a deletion commit that
  over-removes active code. Use when ImportError appears for symbols that should exist
  after a deprecation-removal commit.
category: debugging
date: 2026-02-21
version: 1.0.0
user-invocable: false
---
# Skill: git-rebase-over-deletion

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | N/A (CI fix) |
| PR | #882 |
| Objective | Fix CI failure caused by git rebase/merge replaying commits in wrong order, resulting in over-deletion of active classes |
| Outcome | Success — 2350 tests pass, all pre-commit hooks green |
| Category | debugging |

## When to Use

Trigger this skill when:

- CI `Test` workflow on `main` starts failing after a deprecation-removal commit
- The failure is an `ImportError` for symbols that *should* exist (not deprecated)
- `git log` shows a fix commit followed later by a removal commit — wrong replay order
- Multiple test modules fail to collect simultaneously (cascade from one `ImportError`)
- The removal commit message says "remove deprecated X" but X was used in active code

**Trigger phrases**:

- "CI broke on main after [deprecation-removal commit]"
- "ImportError: cannot import name 'X' from 'package.module'"
- "N test modules failed to collect"
- "commit removed too much — also deleted the active base classes"

## Root Cause Pattern

This failure pattern has a specific shape:

1. **Session A** adds `ClassA` + `ClassB` (fix commit)
2. **Session B** removes `DeprecatedClass` — but the removal commit was authored against a state *before* the fix, so it also removes the newly added classes
3. A rebase/merge replays both commits, with removal *after* the fix → fix is undone
4. `pre-commit auto-fixes` commit follows, cementing the broken state

**Diagnostic signal**: The broken commit message says "remove deprecated X" but the file also lost other unrelated symbols.

## Verified Workflow

### 1. Confirm the ImportError

```bash
<package-manager> run python -c "from <package>.<module> import ClassA, ClassB; print('OK')"
# Expected (broken): ImportError: cannot import name 'ClassA'
```

### 2. Identify the bad commit

```bash
git log --oneline <file-path>
# Look for: a "remove deprecated X" commit that follows a fix commit
```

### 3. Read the current file state

Look for:
- Missing classes that should exist
- Stale decorators (e.g., `@dataclass` on a Pydantic `BaseModel`)
- Duplicate field declarations in a class body
- Unused imports left behind by the deletion

### 4. Restore missing symbols

Add back the classes/functions that were accidentally deleted. Check existing tests to understand expected signatures/defaults.

### 5. Clean up artifacts

- Remove stale decorators left by the bad merge
- Remove duplicate field declarations
- Remove unused imports

### 6. Update exports

If there's an `__init__.py` that re-exports symbols, add the restored ones.

### 7. Verify

```bash
# Quick import check
<package-manager> run python -c "from <package>.<module> import ClassA, ClassB; print('OK')"

# Run affected tests
<package-manager> run python -m pytest <test-path> -v

# Full test suite
<package-manager> run python -m pytest tests/ --no-cov

# Pre-commit
pre-commit run --files <changed-files>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Root cause | Removal commit authored pre-fix replayed post-fix via rebase |
| Diagnostic signal | Broken commit message says "remove deprecated X" but other symbols also gone |
| Canary imports | `import warnings` + `import dataclasses` unused after bad merge |
| Commit type | `fix:` |

## Key Takeaways

1. **Deprecation removal commits are high-risk** — always `grep` the file before committing to confirm only the deprecated symbol is removed
2. **Rebase replay order matters** — a fix + removal pair replayed in wrong order will undo the fix
3. **Stale decorators signal bad merge** — e.g., `@dataclass` on a Pydantic `BaseModel`
4. **Duplicate field declarations = bad merge artifact** — Python ignores earlier definitions silently
5. **Unused imports are canaries** — if `warnings`/`dataclasses` are imported but unused, something was deleted that left them behind

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | CI main breakage after PR #832, fixed in PR #882 | [notes.md](../../references/notes.md) |
