---
name: tiered-skill-migration-tests
description: 'Pattern for testing auxiliary subdir copying in tiered skill migrations.
  Use when: verifying tier-1/tier-2 skills with scripts/, templates/, and references/
  are migrated correctly.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# tiered-skill-migration-tests

## Overview

| Item | Details |
|------|---------|
| Name | tiered-skill-migration-tests |
| Category | testing |
| Description | Pattern for parametrized pytest tests covering auxiliary subdir copying during skill migration for tier-1 and tier-2 skills |
| Source Issue | #3768 (follow-up from #3228) |

## When to Use

- When `migrate_skill()` copies auxiliary subdirs for top-level skills but tier-1/tier-2 coverage is absent
- When adding tests for a migration script that processes `tier-1/` and `tier-2/` subdirectories
- When verifying `scripts/`, `templates/`, and `references/` land at the correct destinations for tiered skills
- When extending existing `TestMigrateSkillAuxiliaryDirs` coverage to include tiered variants

## Verified Workflow

### Quick Reference

```bash
# Run the tests
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py -v

# Run only the new tiered tests
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py -v -k "Tiered"
```

1. **Add a `make_tiered_skill_dir()` fixture helper** that builds source fixtures at
   `skills_root/tier-{tier}/{skill_name}/` with a SKILL.md containing a `tier:` field in frontmatter.

2. **Define a `_TIERED_AUXILIARY_CASES` parametrize list** using `pytest.param` with four fields:
   `(skill_name, tier, extra_subdirs_spec, expected_category)`. Include at minimum:
   - One tier-1 skill with `scripts/`
   - One tier-1 skill with `templates/`
   - One tier-2 skill with `scripts/`
   - One tier-2 skill with `templates/`
   - One tier-2 skill with `references/`
   - One tier-2 skill with both `scripts/` and `templates/`

3. **Write `TestMigrateSkillTieredAuxiliaryDirs`** class with:
   - A single `@pytest.mark.parametrize` method that iterates over `_TIERED_AUXILIARY_CASES`
   - Asserts files exist at correct destinations (`references/` at plugin root; others inside `skills/<name>/`)
   - Also asserts file *contents* match the source to confirm full copy (not just directory creation)
   - A `dry_run=True` test for a tier-1 skill confirming no files are created
   - A negative-assertion test confirming `references/` is NOT placed inside `skills/<name>/` for tier-2

4. **Key destination routing** (same as top-level skills, since `source_skill_md.parent` resolves correctly):
   - `scripts/` → `skills/<category>/<name>/skills/<name>/scripts/`
   - `templates/` → `skills/<category>/<name>/skills/<name>/templates/`
   - `references/` → `skills/<category>/<name>/references/` (plugin root, NOT inside `skills/<name>/`)

5. **Category expectations** must match `determine_category(skill_name, frontmatter, tier=tier)`:
   - tier-1 skills → `tooling` (via `TIER1_CATEGORY`)
   - tier-2 `generate-tests` → `testing` (via `TIER2_CATEGORY_MAP`)
   - tier-2 `generate-docstrings` → `documentation`
   - tier-2 `profile-code` → `optimization`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Combining tier-1 and top-level tests | Reused the `make_skill_dir()` helper for tiered skills | Helper creates dirs at `skills_root/<name>` not `skills_root/tier-{tier}/<name>` | Separate helper `make_tiered_skill_dir()` needed for correct path structure |
| Asserting only directory existence | Checked `dest_dir.exists()` without checking file contents | Passes even if `shutil.copytree` copies an empty directory | Always assert specific files AND read their contents to confirm full copy |

## Results & Parameters

### Parametrize Tuple Structure

```python
pytest.param(
    "skill-name",   # str: skill directory name
    "1",            # str: tier ("1" or "2")
    {"scripts": {"run.sh": "#!/bin/bash\necho hi"}},  # dict: subdir -> {file: content}
    "tooling",      # str: expected Mnemosyne category
    id="tier1-skill-name-scripts",
)
```

### Destination Paths Computed in Test

```python
plugin_dir = mnemosyne_skills / expected_category / skill_name
skill_inner_dir = plugin_dir / "skills" / skill_name

# references/ -> plugin root
dest_dir = plugin_dir / "references"

# everything else -> skill inner dir
dest_dir = skill_inner_dir / subdir_name
```

### Full Test Count After Addition

- Total: 29 tests (21 pre-existing + 8 new)
- Parametrized positive cases: 6
- Targeted tests (dry-run, negative reference routing): 2
