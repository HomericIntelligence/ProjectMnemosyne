---
name: plugin-generalization
description: "Generalize skills/plugins for cross-repository compatibility"
category: tooling
date: 2026-01-03
---

# Plugin Generalization

Migrate plugins/skills from repository-specific to cross-repository compatible format.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-03 |
| Objective | Make plugins work across multiple repositories without hardcoded references |
| Outcome | Success - 33 plugins migrated, 109 validated |

## When to Use

- Plugins have `source: ProjectName` in YAML frontmatter
- Hardcoded paths like `tests/shared/core/` need abstraction
- PR numbers embedded in workflows (e.g., "PR #3050")
- Migrating a skills marketplace to support multiple projects
- New team wants to use existing skills in different codebase

## Verified Workflow

### 1. Identify Repository-Specific Content

```bash
# Find all plugins with source: field in frontmatter
grep -r "^source:" plugins/ --include="SKILL.md"

# Count affected plugins
grep -r "^source:" plugins/ --include="SKILL.md" | wc -l
```

### 2. Update Templates First

Update `templates/experiment-skill/` with new structure:

**SKILL.md template changes:**
- Remove `source:` from frontmatter
- Add "Verified On" section at bottom
- Use placeholders: `<project-root>`, `<test-path>`, `<package-manager>`

**plugin.json template changes:**
- Remove `source_project` field
- Add optional `requires` object for tool dependencies
- Add optional `verified_on` array for provenance

### 3. Batch Remove Source Fields

```bash
# Remove source: lines from frontmatter
for file in plugins/<category>/*/skills/*/SKILL.md; do
  sed -i '/^source: ProjectName$/d' "$file"
done
```

### 4. Add "Verified On" Sections

Add to end of each SKILL.md:

```markdown
## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectName | PR #XXX context | [notes.md](../../references/notes.md) |
```

### 5. Move Specifics to References

Create `references/notes.md` with project-specific details:
- Exact commands used
- Specific file paths
- PR/commit links
- Environment details

### 6. Update CLAUDE.md

Add "Cross-Repository Compatibility" section with guidelines.

### 7. Validate and Regenerate

```bash
# Validate all plugins
python scripts/validate_plugins.py

# Regenerate marketplace index
python scripts/generate_marketplace.py
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Writing notes.md before reading | File write error - must read first | Always read files before writing to them |
| Assuming all `source:` were frontmatter | Some were inline code examples | Use `^source:` regex to match only frontmatter |
| Manual file-by-file updates | Too slow for 33 plugins | Use sed/batch scripts for bulk changes |
| Removing source URLs | URLs are references, not project sources | Only remove `source: ProjectName`, keep reference URLs |

## Results & Parameters

### Files Changed Per Plugin

| File | Change Type | Lines |
|------|-------------|-------|
| SKILL.md | Modify | ~10-20 (remove source, add Verified On) |
| references/notes.md | Create | ~30-50 (project-specific details) |
| plugin.json | Modify | ~5 (add requires, verified_on) |

### Generalization Checklist

- [ ] Remove `source:` from YAML frontmatter
- [ ] Replace hardcoded paths with placeholders
- [ ] Add "Verified On" section
- [ ] Create/update references/notes.md with specifics
- [ ] Update plugin.json with optional fields
- [ ] Run validation script
- [ ] Regenerate marketplace.json

### Placeholder Reference

| Placeholder | Example | Purpose |
|-------------|---------|---------|
| `<project-root>` | `/home/user/project` | Repository root |
| `<test-path>` | `tests/` | Test directory |
| `<package-manager>` | `pixi`, `npm`, `pip` | Package manager command |
| `<pr-number>` | `3050` | Pull request number |
| `<branch>` | `feature/xyz` | Git branch name |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Generalized 33 plugins across 8 categories | [notes.md](../../references/notes.md) |

## References

- CLAUDE.md "Cross-Repository Compatibility" section
- templates/experiment-skill/ for updated templates
- scripts/validate_plugins.py for validation
