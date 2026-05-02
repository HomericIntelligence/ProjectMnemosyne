---
name: warn-on-existing-dest-subdir
description: 'Defensive copytree pattern: emit stderr warning before shutil.copytree(dirs_exist_ok=True)
  when destination already exists. Use when: adding observability to re-runnable migration
  scripts, preventing silent overwrites.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Issue** | #3770 — migrate_odyssey_skills: log warning when auxiliary subdir already exists at dest |
| **Follow-up from** | #3228 |
| **File changed** | `scripts/migrate_odyssey_skills.py` |
| **Pattern** | Check `dest.exists()` before `shutil.copytree(dirs_exist_ok=True)`, print to `stderr` |

## When to Use

- When a migration script can be run multiple times against the same destination
- When `shutil.copytree(dirs_exist_ok=True)` is used and silent overwrites are a risk
- When adding observability so operators can detect accidental overwrites on re-migration
- When the same pattern applies to both real-run and dry-run code paths

## Verified Workflow

### Quick Reference

```python
if dest.exists():
    print(
        f"  WARNING: destination subdir already exists and will be merged: {dest}",
        file=sys.stderr,
    )
shutil.copytree(src, dest, dirs_exist_ok=True)
```

1. **Locate every `shutil.copytree(…, dirs_exist_ok=True)` call** in the migration script — both
   the real-run and dry-run code paths need the check.

2. **Before each call, compute `dest`** (the same path `copytree` will write to) and add:

   ```python
   if dest.exists():
       print(
           f"  WARNING: destination subdir already exists and will be merged: {dest}",
           file=sys.stderr,
       )
   ```

3. **Write to `sys.stderr`** (not `stdout`) so the warning is always visible even when
   stdout is piped or redirected. Ensure `import sys` is present at the top of the file.

4. **Keep the dry-run path consistent** — the destination path variable (`dest`) is
   computed outside the `if not dry_run:` / `else:` block in this codebase, so the same
   `dest.exists()` check works unchanged in both branches.

5. **Add two pytest tests** using `capsys`:
   - One for `dry_run=False` — pre-create the destination dir, call `migrate_skill`, assert
     `"WARNING: destination subdir already exists"` in `capsys.readouterr().err`
   - One for `dry_run=True` — same setup, assert the warning fires without any files being
     written

6. **Run tests** to confirm all existing tests still pass and the two new tests pass:

   ```bash
   pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py -v
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | No alternative approaches explored | N/A | Issue was well-scoped: one pattern, two code paths |

## Results & Parameters

```python
# Pattern used in scripts/migrate_odyssey_skills.py
if dest.exists():
    print(
        f"  WARNING: destination subdir already exists and will be merged: {dest}",
        file=sys.stderr,
    )
shutil.copytree(subdir, dest, dirs_exist_ok=True)
```

- Warning message format: `"  WARNING: destination subdir already exists and will be merged: {dest}"`
- Output stream: `sys.stderr` (not `print()` default stdout)
- Applied in 4 locations: real-run references branch, real-run generic branch, dry-run references branch, dry-run generic branch
- Tests: 23 total passing after adding 2 new warning tests
