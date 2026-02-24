# Session Notes: plugin-generalization

Detailed notes from the plugin generalization session.

## Verified Examples

### Example 1: ProjectMnemosyne Marketplace

**Date**: 2026-01-03
**Context**: Generalize all 33 repository-specific plugins to work across multiple repositories

**Scope**:
- 33 plugins with `source:` field removed
- 42 files changed total
- 109 plugins validated after migration

**Categories Affected**:
| Category | Plugins Updated |
|----------|-----------------|
| ci-cd | 9 |
| tooling | 9 |
| testing | 5 |
| evaluation | 5 |
| architecture | 4 |
| training | 2 |

**Specific Commands Used**:

```bash
# Find all plugins with source field
grep -r "^source:" plugins/ --include="SKILL.md"

# Batch remove source fields (example for testing category)
for file in plugins/testing/*/skills/*/SKILL.md; do
  sed -i '/^source: ProjectOdyssey$/d' "$file"
done

# Validate all plugins
python scripts/validate_plugins.py

# Regenerate marketplace
python scripts/generate_marketplace.py
```

**Key Files Modified**:
- `CLAUDE.md` - Added "Cross-Repository Compatibility" section
- `templates/experiment-skill/skills/SKILL_NAME/SKILL.md` - Updated template
- `templates/experiment-skill/.claude-plugin/plugin.json` - Added requires/verified_on
- `templates/experiment-skill/references/notes.md` - "Verified Examples" structure

**Commit**: `bcbf719e refactor: generalize plugins for cross-repository compatibility`

## Raw Findings

### Source Field Patterns Found

1. **Project sources** (to remove):
   - `source: ProjectOdyssey`
   - `source: ProjectScylla`

2. **URL sources** (to keep as references):
   - `source: https://huggingface.co/blog/sionic-ai/...`

3. **Inline code examples** (to keep):
   - `source:` in YAML code blocks showing config structure

### Template Structure Changes

**Before**:
```yaml
---
name: skill-name
source: ProjectOdyssey
date: YYYY-MM-DD
---
```

**After**:
```yaml
---
name: skill-name
date: YYYY-MM-DD
---
# ... content ...

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Original implementation | [notes.md](../references/notes.md) |
```

### Plugin.json Optional Fields

```json
{
  "requires": {
    "tools": [{"name": "mojo", "version": ">=0.25.0"}],
    "languages": ["mojo", "python"]
  },
  "verified_on": [
    {"project": "ProjectOdyssey", "context": "CI setup"}
  ]
}
```

## External References

- Sionic AI skills pattern: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Claude Code plugin docs: https://docs.claude.com/claude-code/plugins
