# Claude Plugin Format - Session Notes

## Session Context

**Date**: 2025-12-29
**Objective**: Fix ProjectMnemosyne marketplace plugins that weren't loading
**Initial Error**: `Plugin has an invalid manifest file... Unrecognized key(s) in object: 'tags'`

## Problem Discovery Timeline

### Issue 1: Skills not appearing
User installed `skills-registry-commands` plugin but `/advise` and `/retrospective` didn't appear.

**Investigation**:
- Checked plugin structure
- Found skills in `skills/` directory (correct)
- Found commands in `commands/` directory (correct)
- Found duplicate skills in project `.claude/skills/` (incorrect)

### Issue 2: Marketplace file location
- Root `marketplace.json` was current but wrong location
- `.claude-plugin/marketplace.json` was outdated with deleted plugins

**Resolution**: Moved to `.claude-plugin/marketplace.json` per official docs

### Issue 3: plugin.json validation error
Error: `Unrecognized key(s) in object: 'tags'`

**Investigation via official repo**:
```bash
# Analyzed anthropics/claude-plugins-official
# Found commit-commands plugin.json:
{
  "name": "commit-commands",
  "description": "...",
  "author": { "name": "Anthropic", "email": "..." }
}
# NO tags field!
```

**Resolution**: Removed `tags` from all plugin.json files

### Issue 4: SKILL.md validation error
Skills had non-standard frontmatter fields causing validation failures.

**Investigation via official repo**:
```yaml
# Official example-skill frontmatter:
---
name: example-skill
description: This skill should be used when...
version: 1.0.0
---
# Only these fields allowed!
```

**Resolution**: Stripped all SKILL.md files to only `name` and `description`

## Files Modified

### Deleted
- `/marketplace.json` (wrong location)
- `/.claude/skills/advise/` (duplicate)
- `/.claude/skills/retrospective/` (duplicate)

### Updated
- `.claude-plugin/marketplace.json` - moved from root, updated with current 4 plugins
- `scripts/generate_marketplace.py` - output to `.claude-plugin/`
- `scripts/validate_plugins.py` - removed non-standard required fields
- `plugins/ci-cd/github-actions-mojo/.claude-plugin/plugin.json` - removed tags
- `plugins/tooling/skills-registry-commands/.claude-plugin/plugin.json` - removed tags
- `plugins/training/grpo-external-vllm/.claude-plugin/plugin.json` - removed tags
- `plugins/training/spec-driven-experimentation/.claude-plugin/plugin.json` - removed tags
- `plugins/tooling/skills-registry-commands/skills/advise/SKILL.md` - removed category, invokedBy
- `plugins/tooling/skills-registry-commands/skills/retrospective/SKILL.md` - removed category, invokedBy
- `plugins/tooling/skills-registry-commands/skills/documentation-patterns/SKILL.md` - removed category, source, date
- `plugins/tooling/skills-registry-commands/skills/validation-workflow/SKILL.md` - removed category, source, date

### Added
- `plugins/tooling/skills-registry-commands/commands/advise.md` - slash command
- `plugins/tooling/skills-registry-commands/commands/retrospective.md` - slash command

## Commits Created

1. `fee587b` - fix: update marketplace to official Claude Code plugin format
2. `587be28` - fix: add trailing newline and update bundled script output path
3. `6712128` - fix: remove non-standard required fields from validation
4. `db4f54d` - fix: remove tags from plugin.json (not in official schema)
5. `e55f911` - feat: add advise and retrospective as slash commands
6. `c2e4c9c` - fix: remove non-standard frontmatter fields from SKILL.md files
7. `af63c35` - fix: add target repository to /retrospective command

## Key Documentation References

- https://github.com/anthropics/claude-plugins-official
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/discover-plugins

## Testing Results

After all fixes:
- Plugin validation script passes: 4/4 plugins valid
- Marketplace location correct: `.claude-plugin/marketplace.json`
- No schema errors on installation
- Commands appear as `/skills-registry-commands:advise` and `/skills-registry-commands:retrospective`

## Lessons for Future Plugins

1. **Always check official repo first** before adding custom fields
2. **Schema is strict** - any unrecognized field breaks validation
3. **Location matters** - marketplace must be in `.claude-plugin/`
4. **Commands vs skills** - understand the distinction
5. **Tags only in marketplace** - not in individual plugin.json files
6. **Frontmatter minimalism** - only official fields in SKILL.md
