---
name: claude-plugin-marketplace
description: Set up Claude Code plugin marketplaces. Use when registering skills, fixing schema errors, or installing from private repos.
category: tooling
date: 2025-12-30
---

# Claude Code Plugin Marketplace Setup

## Overview

| Field | Value |
|-------|-------|
| Date | 2025-12-30 |
| Objective | Register a private skills marketplace with Claude Code CLI |
| Outcome | Successfully registered marketplace and installed 7 plugins |
| Time Spent | ~2 hours (mostly debugging schema issues) |

## When to Use

Use this skill when:

1. **Setting up a new skills marketplace** - Need to create marketplace.json and plugin.json files
2. **Fixing "Unrecognized key(s)" errors** - plugin.json has unsupported fields
3. **Fixing "Expected object, received string" errors** - marketplace.json owner format wrong
4. **Installing plugins from private repositories** - Need correct authentication
5. **Understanding Claude Code plugin schema** - Official docs don't list all constraints

## Verified Workflow

### Step 1: Create Valid plugin.json

The plugin.json schema is **strict**. Only these fields are supported:

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Trigger conditions with specific use cases.",
  "author": {
    "name": "Author Name"
  },
  "skills": "./skills"
}
```

**Valid fields only**:

- `name` (required): Lowercase kebab-case identifier
- `version` (required): Semver string
- `description` (required): Use cases and trigger conditions
- `author` (required): Object with `name` field
- `skills` (required): Path to skills directory

### Step 2: Create Valid marketplace.json

```json
{
  "name": "MarketplaceName",
  "owner": {
    "name": "OrganizationName",
    "url": "https://github.com/OrganizationName"
  },
  "description": "Marketplace description",
  "version": "1.0.0",
  "plugins": [
    {
      "name": "plugin-name",
      "description": "Plugin description",
      "version": "1.0.0",
      "source": "./plugins/category/plugin-name",
      "category": "category-name",
      "tags": []
    }
  ]
}
```

**Critical**: `owner` must be an object with `name` and `url`, NOT a string.

### Step 3: Register Marketplace

```bash
# Option A: From GitHub (if auth works)
claude plugin marketplace add https://github.com/Org/Repo

# Option B: From local path (always works)
claude plugin marketplace add /path/to/local/repo
```

### Step 4: Install Plugins

```bash
# Install specific plugin from marketplace
claude plugin install plugin-name@MarketplaceName

# List available plugins
claude plugin marketplace list
```

### Step 5: Verify Installation

```bash
# Check marketplace is registered
claude plugin marketplace list

# Check plugins are installed (look in ~/.claude/settings.json)
cat ~/.claude/settings.json | grep -A5 "plugins"
```

## Failed Attempts

| Attempt | Error | Root Cause | Fix |
|---------|-------|------------|-----|
| Remote GitHub URL registration | SSH/HTTPS authentication failed | Private repo without cached credentials | Use local path instead of GitHub URL |
| marketplace.json with `owner: "string"` | `owner: Expected object, received string` | Schema requires owner to be an object | Change to `owner: { "name": "...", "url": "..." }` |
| plugin.json with `date` field | `Unrecognized key(s) in object: 'date'` | Schema doesn't support date field | Remove date from plugin.json (put in SKILL.md instead) |
| plugin.json with `category` field | `Unrecognized key(s) in object: 'category'` | Schema doesn't support category | Remove category (derive from directory structure) |
| plugin.json with `tags` field | `Unrecognized key(s) in object: 'tags'` | Schema doesn't support tags | Remove tags (use in marketplace.json only) |
| plugin.json with `source_project` field | `Unrecognized key(s) in object: 'source_project'` | Custom field not supported | Remove entirely |

## Results & Parameters

### Minimal Valid plugin.json Template

```json
{
  "name": "skill-name",
  "version": "1.0.0",
  "description": "Trigger conditions. Use when: (1) scenario, (2) scenario.",
  "author": {
    "name": "Team Name"
  },
  "skills": "./skills"
}
```

### Marketplace Registration Commands

```bash
# Register from local directory (recommended for private repos)
claude plugin marketplace add /absolute/path/to/marketplace

# Install all plugins
claude plugin install skill-1@MarketplaceName
claude plugin install skill-2@MarketplaceName

# Verify
claude plugin marketplace list
```

### Directory Structure

```text
marketplace-repo/
├── .claude-plugin/
│   └── marketplace.json      # Required: marketplace index
├── plugins/
│   └── <category>/
│       └── <skill-name>/
│           ├── .claude-plugin/
│           │   └── plugin.json    # Minimal schema only
│           ├── skills/<skill-name>/
│           │   └── SKILL.md       # Knowledge document
│           └── references/
│               └── notes.md
└── scripts/
    ├── generate_marketplace.py   # Regenerate marketplace.json
    └── validate_plugins.py       # CI validation
```

## Key Insights

1. **Schema is stricter than documented** - Claude Code's plugin schema rejects many fields that seem reasonable (date, category, tags in plugin.json)

2. **Local registration always works** - When GitHub auth fails, use absolute local path

3. **Category from directory, not metadata** - Category is derived from `plugins/<category>/` path, not from plugin.json

4. **owner must be an object** - The marketplace.json `owner` field requires `{ "name": "...", "url": "..." }` format

5. **Validate iteratively** - Run `claude plugin marketplace add` after each schema change to catch errors early

## References

- [Claude Code Skills Training Blog](https://huggingface.co/blog/sionic-ai/claude-code-skills-training)
- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [ProjectMnemosyne Repository](https://github.com/HomericIntelligence/ProjectMnemosyne)
