---
name: tooling-legacy-hierarchical-flat-migration
description: "Migrate remaining legacy hierarchical skills (nested directories with SKILL.md + plugin.json) to flat format (skills/<name>.md). Use when: (1) find skills/ -type d -mindepth 1 returns results, (2) skills have .claude-plugin/plugin.json files, (3) skills use SKILL.md filename instead of <name>.md."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [migration, flat-format, hierarchical, legacy, skill-format, plugin-json]
---

# Legacy Hierarchical to Flat Skill Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Migrate the last 4 skills from nested `skills/<category>/<name>/skills/<name>/SKILL.md` to flat `skills/<name>.md` |
| **Outcome** | All 4 migrated, 0 nested directories remain, 1031/1031 skills valid |
| **Verification** | verified-ci |

## When to Use

- `find skills/ -type d -mindepth 1` returns directories (should be empty)
- Skills have `.claude-plugin/plugin.json` files alongside `SKILL.md`
- Agent created skills in the old nested format: `skills/<category>/<name>/skills/<name>/SKILL.md`
- Marketplace generation misses skills because they're in unexpected paths

## Verified Workflow

### Quick Reference

```bash
# Detect legacy skills
find skills/ -type d -mindepth 1
find skills/ -name "plugin.json"
find skills/ -name "SKILL.md"

# Migrate one skill
cp skills/<cat>/<name>/skills/<name>/SKILL.md skills/<name>.md
cp skills/<cat>/<name>/references/notes.md skills/<name>.notes.md
rm -rf skills/<cat>/<name>/
rmdir skills/<cat>/  # only if empty

# Fix missing version in frontmatter (if needed)
# Add: version: "1.0.0"

# Validate
python3 scripts/validate_plugins.py
```

### Detailed Steps

1. **Identify legacy skills**: `find skills/ -type d -mindepth 1` to find nested directories
2. **Check each for the pattern**: `skills/<cat>/<name>/skills/<name>/SKILL.md` + `.claude-plugin/plugin.json` + `references/notes.md`
3. **Check for existing flat duplicates**: `test -f skills/<name>.md` — if flat version already exists, compare content before overwriting
4. **Copy SKILL.md to flat location**: The SKILL.md files may already have YAML frontmatter (partially migrated) — check and preserve it
5. **Copy references/notes.md**: Rename to `skills/<name>.notes.md`
6. **Fix frontmatter**: Add `version: "1.0.0"` if missing (3 of 4 were missing it)
7. **Delete nested directory**: `rm -rf skills/<cat>/<name>/` removes the entire tree including `.claude-plugin/`
8. **Delete empty category dirs**: `rmdir skills/<cat>/` — only succeeds if empty
9. **Validate**: `python3 scripts/validate_plugins.py` — all skills must pass
10. **Verify clean state**: `find skills/ -type d -mindepth 1` should return nothing

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed SKILL.md needed full rewrite | Expected old format without frontmatter | All 4 already had YAML frontmatter — only needed file move | Check SKILL.md content before assuming a full rewrite is needed; partially migrated files only need relocation |
| Forgot to check for `version` field | Copied SKILL.md directly without checking required fields | 3 of 4 were missing `version: "1.0.0"` in frontmatter, would fail validation | Always verify all required frontmatter fields after copy: name, description, category, date, version |

## Results & Parameters

### Migration Results

```yaml
legacy_skills_found: 4
successfully_migrated: 4
validation_result: 1031/1031 valid
nested_directories_remaining: 0
```

### Legacy Skills Migrated

| Skill | Category Dir | Missing Fields |
|-------|-------------|----------------|
| e2e-resource-exhaustion | `optimization/` | `version` |
| experiment-dataset-triage | `evaluation/` | `version` |
| batch-subprocess-signal-hang | `debugging/` | `version` |
| tensor-dtype-native-ops-inversion | `architecture/` | (none) |

### Detection Commands

```bash
# Find all legacy-format skills
find skills/ -type d -mindepth 1
find skills/ -name "plugin.json"
find skills/ -name "SKILL.md"

# Count flat vs legacy
echo "Flat: $(ls skills/*.md 2>/dev/null | grep -v notes.md | wc -l)"
echo "Legacy dirs: $(find skills/ -type d -mindepth 1 | wc -l)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #1017, migrated last 4 hierarchical skills | 2026-03-25 session |
