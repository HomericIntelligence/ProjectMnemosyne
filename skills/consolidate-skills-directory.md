---
name: consolidate-skills-directory
description: 'Consolidate a dual plugins/+skills/ structure into a single skills/<category>/<name>/
  directory. Use when: (1) ProjectMnemosyne has both plugins/ and skills/ directories
  causing confusion, (2) migrating flat legacy skills to plugin format, (3) updating
  all tooling and CI to reference the new canonical location.'
category: tooling
date: 2026-02-23
version: 1.0.0
user-invocable: false
---
# Consolidate skills/ Directory

Migrate from a dual `plugins/` + `skills/` structure to a single canonical `skills/<category>/<name>/` location for all skills.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-23 |
| Objective | Consolidate 225 plugins/ + 88 legacy skills/ into a single skills/ directory |
| Outcome | ✅ 310 skills in skills/, plugins/ contains only skills-registry-commands |

## When to Use

- ProjectMnemosyne has both `plugins/<category>/<name>/` and `skills/<name>/` directories
- New contributors are confused about where to put skills
- Tooling (CI, scripts) needs to scan a single directory
- Legacy flat skills need migration to the standard plugin format (`<category>/<name>/.claude-plugin/plugin.json + skills/<name>/SKILL.md`)

## Verified Workflow

### 1. Write migration script

Create `scripts/migrate_to_skills.py` to convert flat legacy skills:

- Reads `category` from `plugin.json` or SKILL.md YAML frontmatter
- Falls back to name-based keyword inference (e.g. `fix-*` → `debugging`, `mypy-*` → `testing`)
- **Critical**: detect in-place migrations (when `legacy_dir == target_dir`) and skip file copies — just add `.claude-plugin/plugin.json`
- Add YAML frontmatter to any SKILL.md that lacks `---` delimiters

Map non-standard categories: `workflow→tooling`, `refactoring→architecture`, `automation→tooling`, `docs→documentation`.

### 2. Update scripts to accept multiple scan directories

```python
# generate_marketplace.py — new signature
def main():
    # First arg ending in .json = output file, rest = scan dirs
    # Default: output=.claude-plugin/marketplace.json, scan_dirs=[skills/, plugins/]
    ...
    generate_marketplace(scan_dirs, repo_root)

# validate_plugins.py — new signature
def main():
    # All args = scan dirs
    # Default: [skills/, plugins/]
    ...
```

### 3. Move plugins/ → skills/ with bash

```bash
for category in plugins/*/; do
  cat_name=$(basename "$category")
  for plugin in "$category"*/; do
    plugin_name=$(basename "$plugin")
    [ "$cat_name/$plugin_name" = "tooling/skills-registry-commands" ] && continue
    mkdir -p "skills/$cat_name"
    [ -d "skills/$cat_name/$plugin_name" ] && rm -rf "skills/$cat_name/$plugin_name"
    mv "$plugin" "skills/$cat_name/$plugin_name"
  done
  [ "$cat_name" != "tooling" ] && rmdir "$category" 2>/dev/null
done
```

### 4. Fix any stray skills after migration

After `git restore .` + switching branches, check for:
- Legacy flat dirs still at `skills/<name>/` (not `skills/<category>/<name>/`)
- Skills that have `.claude-plugin/plugin.json` but no `skills/<name>/SKILL.md` (partially-migrated)

```bash
# Find stray flat dirs (top-level dirs in skills/ that aren't categories)
find skills -maxdepth 1 -mindepth 1 -type d | grep -v -E "^skills/(architecture|ci-cd|debugging|documentation|evaluation|optimization|testing|tooling|training)$"
```

### 5. Update CI and commands

- `.github/workflows/validate-plugins.yml`: trigger on `skills/**` + `plugins/**`, pass both to script
- `.github/workflows/update-marketplace.yml`: same
- `plugins/tooling/skills-registry-commands/commands/retrospective.md`: generate into `skills/<category>/<name>/`
- `CLAUDE.md`, `README.md`, `.claude/shared/plugin-standards.md`: update Required Structure section

### 6. Add YAML frontmatter to migrated legacy SKILL.md files

```python
for plugin_json_path in skills_root.rglob('.claude-plugin/plugin.json'):
    skill_md = find_skill_md(plugin_json_path.parent.parent)
    if not skill_md.read_text().startswith('---'):
        plugin_data = json.loads(plugin_json_path.read_text())
        frontmatter = build_frontmatter(plugin_data)
        skill_md.write_text(frontmatter + skill_md.read_text())
```

### 7. Handle stray legacy skills that have `.claude-plugin/` but no `skills/<name>/SKILL.md`

These are partially-migrated skills with rich `plugin.json` metadata but the SKILL.md wasn't moved. Detect and migrate manually:

```python
for plugin_json_path in skills_root.rglob('.claude-plugin/plugin.json'):
    plugin_dir = plugin_json_path.parent.parent
    skill_files = list((plugin_dir / 'skills').glob('*/SKILL.md'))
    if not skill_files:  # Missing SKILL.md subdir
        migrate_in_place(plugin_dir)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

```yaml
# Final state after migration
skills_count: 310
skills_location: skills/<category>/<name>/
exception: plugins/tooling/skills-registry-commands/  # stays in plugins/

# Validation command
validate: python3 scripts/validate_plugins.py skills/ plugins/

# Marketplace generation command
generate: python3 scripts/generate_marketplace.py .claude-plugin/marketplace.json skills/ plugins/

# Category inference priority
category_sources:
  1: plugin.json "category" field
  2: SKILL.md YAML frontmatter "category:" field
  3: Name keyword inference (fix-* → debugging, mypy-* → testing, etc.)
  4: Default → tooling

# Non-standard category mappings
category_map:
  workflow: tooling
  refactoring: architecture
  automation: tooling
  docs: documentation
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #183 — 971 files changed | [notes.md](../references/notes.md) |
