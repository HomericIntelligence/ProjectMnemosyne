---
name: claude-plugin-format
description: Official Claude Code plugin format requirements. Use when creating new plugins, debugging "plugin has invalid manifest" errors, or when skills/commands don't appear after installation.
---

# Claude Code Plugin Format

Official format requirements for Claude Code plugins based on debugging a marketplace that wouldn't load.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Fix ProjectMnemosyne marketplace to use official Claude Code plugin format |
| Outcome | All plugins validated and working after schema compliance fixes |
| Source | https://github.com/anthropics/claude-plugins-official |

## When to Use

- Creating a new Claude Code plugin from scratch
- Getting "Unrecognized key(s) in object" validation errors
- Skills not appearing after plugin installation
- Commands not showing up in slash command list
- Setting up a plugin marketplace
- Converting custom plugins to official format

## Verified Workflow

### 1. Marketplace Location (CRITICAL)

**Official requirement**: `.claude-plugin/marketplace.json` at repository root

```bash
# Correct location
.claude-plugin/marketplace.json

# Wrong locations (will not work)
marketplace.json                    # Root level - NOT VALID
.claude/marketplace.json            # Wrong directory
plugins/marketplace.json            # Wrong directory
```

**Marketplace format**:
```json
{
  "name": "ProjectMnemosyne",
  "owner": {
    "name": "HomericIntelligence",
    "url": "https://github.com/HomericIntelligence"
  },
  "description": "Skills marketplace for the HomericIntelligence agentic ecosystem",
  "version": "1.0.0",
  "plugins": [
    {
      "name": "plugin-name",
      "description": "...",
      "version": "1.0.0",
      "source": "./plugins/category/plugin-name",
      "category": "tooling",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### 2. Plugin Directory Structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # ONLY plugin.json goes here
├── commands/                 # User-invocable slash commands
│   └── command-name.md
├── skills/                   # Background knowledge
│   └── skill-name/
│       └── SKILL.md
├── agents/                   # Optional: custom agents
├── hooks/                    # Optional: lifecycle hooks
│   └── hooks.json
└── references/               # Optional: supporting docs
    └── notes.md
```

**CRITICAL**: Only `plugin.json` goes in `.claude-plugin/`. All other directories (`commands/`, `skills/`, etc.) go at plugin root.

### 3. plugin.json Schema (STRICT)

**Allowed fields ONLY**:
```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "What it does. Use when: (1) trigger 1, (2) trigger 2.",
  "author": {
    "name": "Author Name"
  },
  "skills": "./skills"
}
```

**Fields that cause validation errors**:
- `tags` - NOT allowed in plugin.json (only in marketplace.json)
- `category` - NOT allowed (derived from directory structure)
- `date` - NOT allowed
- Any other custom fields

### 4. SKILL.md Frontmatter Schema (STRICT)

**Allowed fields ONLY**:
```yaml
---
name: skill-name
description: What it does. Use when <specific triggers>. Use after <specific scenarios>.
---
```

Optional fields:
- `version: 1.0.0`
- `license: MIT`

**Fields that cause validation errors**:
- `category` - NOT in official schema
- `invokedBy` - NOT in official schema
- `source` - NOT in official schema
- `date` - NOT in official schema
- Any other custom fields

### 5. Command vs Skill Distinction

**Commands** (`commands/` directory):
- User-invocable slash commands
- Show up as `/plugin-name:command-name`
- Frontmatter: `description`, `allowed-tools` (optional)

**Skills** (`skills/` directory):
- Background knowledge Claude uses automatically
- NOT user-invocable
- Activated based on `description` triggers
- Frontmatter: `name`, `description`

### 6. Validation Script Requirements

Update `validate_plugins.py` to match official schema:

```python
# Required fields per official docs
REQUIRED_PLUGIN_FIELDS = {"name", "version", "description"}

# NOT required (contrary to custom implementations)
# category - derived from directory structure
# date - optional metadata
# tags - only in marketplace.json, not plugin.json
```

## Failed Attempts

| Attempt | Why it Failed | Lesson Learned |
|---------|---------------|----------------|
| Adding `tags` to plugin.json | "Unrecognized key(s) in object: 'tags'" error | Tags only go in marketplace.json index, not individual plugin.json files |
| Root-level `marketplace.json` | Claude Code doesn't read it | Must be `.claude-plugin/marketplace.json` per official docs |
| Extra frontmatter in SKILL.md (`category`, `invokedBy`, `source`, `date`) | Plugin validator rejected unknown fields | Only `name` and `description` allowed in SKILL.md frontmatter |
| Putting skills in project `.claude/skills/` AND plugin `skills/` | Duplication and confusion | Use plugin `skills/` directory only |
| Expecting `tags` field in validation | CI failed because official schema doesn't require it | Only validate `name`, `version`, `description` |
| Using `/advise` as a skill instead of command | Skill didn't show up for users to invoke | Skills are auto-activated, commands are user-invocable |

## Results & Parameters

### Valid plugin.json (copy-paste ready)
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Short description. Use when: (1) specific trigger.",
  "author": {
    "name": "Your Name"
  },
  "skills": "./skills"
}
```

### Valid SKILL.md frontmatter (copy-paste ready)
```yaml
---
name: my-skill
description: What it does. Use when starting X, debugging Y, or implementing Z.
---
```

### Valid command frontmatter (copy-paste ready)
```yaml
---
description: What this command does
allowed-tools: Bash(git:*), Read, Write
---
```

### Marketplace generation script
```python
# Output to correct location
output_file = ".claude-plugin/marketplace.json"

# Don't require non-standard fields
REQUIRED_PLUGIN_FIELDS = {"name", "version", "description"}
```

### Directory structure checklist
- [ ] `.claude-plugin/marketplace.json` exists (NOT root marketplace.json)
- [ ] plugin.json has no `tags` field
- [ ] SKILL.md frontmatter has only `name` and `description`
- [ ] Commands in `commands/` directory (if user-invocable)
- [ ] Skills in `skills/` directory (if background knowledge)
- [ ] No duplicate skills in `.claude/skills/`

## Key Insights

1. **Schema is strict**: Claude Code plugin validator rejects ANY unrecognized fields
2. **Marketplace location matters**: Must be `.claude-plugin/marketplace.json`
3. **Tags go in marketplace, not plugins**: Searchability is in the index, not individual plugins
4. **Commands ≠ Skills**: Commands are slash commands, skills are auto-activated knowledge
5. **Validation must match official schema**: Custom fields will break installation

## References

- Official plugins repo: https://github.com/anthropics/claude-plugins-official
- Example plugin: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/example-plugin
- Plugin docs: https://code.claude.com/docs/en/plugins
- Skills docs: https://code.claude.com/docs/en/skills
- Marketplace docs: https://code.claude.com/docs/en/discover-plugins
