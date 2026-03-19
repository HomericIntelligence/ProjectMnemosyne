---
name: migrate-skill-aux-dirs
description: 'Copy auxiliary subdirectories (scripts/, templates/, hooks/) when migrating
  skills. Use when: fixing a migration script that silently drops subdirs, or porting
  skills with non-SKILL.md content.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# migrate-skill-aux-dirs

## Overview

| Item | Details |
|------|---------|
| Name | migrate-skill-aux-dirs |
| Category | tooling |
| Problem | Migration scripts that only copy SKILL.md silently drop scripts/, templates/, hooks/ subdirs |
| Solution | After writing SKILL.md, iterate source subdirs and copy each to the correct destination |
| Key Tool | `shutil.copytree(..., dirs_exist_ok=True)` |

## When to Use

- A skill migration script copies only `SKILL.md` and ignores subdirectories
- Skills like `gh-create-pr-linked` have `scripts/` and `templates/` that disappear after migration
- Adding auxiliary subdir support to `migrate_skill()` or any analogous function
- Writing tests for subdir-copy behavior (TDD: confirm failure first, then fix)

## Verified Workflow

### 1. Identify the Pattern

The bug manifests when `migrate_skill()` only creates target dirs and writes `SKILL.md`/`plugin.json`
without iterating the source skill directory for other subdirectories.

```python
# BEFORE (broken) — only SKILL.md is copied
skill_md_path.write_text(transformed)
# subdirs silently dropped

# AFTER (fixed) — iterate all subdirs
source_dir = source_skill_md.parent
for subdir in sorted(source_dir.iterdir()):
    if not subdir.is_dir() or subdir.name.startswith("."):
        continue
    if subdir.name == "references":
        dest = plugin_dir / "references"  # plugin root
    else:
        dest = skill_md_dir / subdir.name  # alongside SKILL.md
    shutil.copytree(subdir, dest, dirs_exist_ok=True)
```

### 2. Routing Rules

| Subdir | Destination in Mnemosyne |
|--------|--------------------------|
| `scripts/` | `skills/<category>/<name>/skills/<name>/scripts/` |
| `templates/` | `skills/<category>/<name>/skills/<name>/templates/` |
| `hooks/` | `skills/<category>/<name>/skills/<name>/hooks/` |
| `references/` | `skills/<category>/<name>/references/` (plugin root) |
| `.hidden/` | **Skipped** (starts with `.`) |

### 3. Use `dirs_exist_ok=True`

```python
import shutil
shutil.copytree(src, dest, dirs_exist_ok=True)
```

This allows merging into pre-existing destination directories without raising `FileExistsError`.
Without this flag, re-running migration would fail if any subdir already exists.

### 4. Update dry-run to report subdirs

```python
else:
    print(f"  [DRY RUN] Would create: {plugin_dir}")
    source_dir = source_skill_md.parent
    for subdir in sorted(source_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("."):
            continue
        if subdir.name == "references":
            print(f"  [DRY RUN] Would copy references/ -> skills/{category}/{skill_name}/references/")
        else:
            print(f"  [DRY RUN] Would copy {subdir.name}/ -> skills/{category}/{skill_name}/skills/{skill_name}/{subdir.name}/")
```

### 5. Write Tests First (TDD)

Key test cases to cover before fixing:

```python
def test_skill_with_scripts_subdir_copies_scripts(tmp_path, migrate_module):
    # Make skill dir with scripts/create_pr.sh
    # Call migrate_skill(...)
    expected = mnemosyne_skills / "tooling" / "name" / "skills" / "name" / "scripts"
    assert expected.exists()
    assert (expected / "create_pr.sh").exists()

def test_hidden_directories_not_copied(tmp_path, migrate_module):
    # .hidden/ must NOT appear in output

def test_dry_run_does_not_copy_files(tmp_path, migrate_module):
    # plugin_dir must not exist after dry_run=True

def test_existing_destination_does_not_raise(tmp_path, migrate_module):
    # Pre-create dest subdir; copytree with dirs_exist_ok=True must merge, not error
```

### 6. Import `shutil`

Add `import shutil` at the top of the script — the standard library module is all that's needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Putting `references/` alongside SKILL.md | Placed `references/` inside `skills/<name>/` | Mnemosyne convention puts `references/` at plugin root, not alongside SKILL.md | Check the Mnemosyne plugin layout spec before routing subdirs |
| Using `shutil.copytree` without `dirs_exist_ok` | Called `copytree(src, dest)` | Raises `FileExistsError` on second migration run if dest already exists | Always use `dirs_exist_ok=True` for idempotent behavior |
| Skipping dry-run subdir reporting | Only dry-run printed the plugin_dir line | Users had no visibility into what subdirs would be copied | Dry-run branch should mirror the real branch's output with `[DRY RUN]` prefix |

## Results & Parameters

```python
# Full fixed migrate_skill() subdir block — drop into any similar migration function
import shutil

source_dir = source_skill_md.parent
for subdir in sorted(source_dir.iterdir()):
    if not subdir.is_dir() or subdir.name.startswith("."):
        continue
    if subdir.name == "references":
        dest = plugin_dir / "references"
        shutil.copytree(subdir, dest, dirs_exist_ok=True)
    else:
        dest = skill_md_dir / subdir.name
        shutil.copytree(subdir, dest, dirs_exist_ok=True)
```

Key parameters:
- `dirs_exist_ok=True` — required for idempotent re-runs
- Skip hidden dirs (`name.startswith(".")`) — avoids copying `.git`, `.cache`, etc.
- `references/` routing to plugin root — follows Mnemosyne plugin layout convention
- 11 unit tests, all using `unittest.mock.patch.object` to override `MNEMOSYNE_SKILLS_DIR`
