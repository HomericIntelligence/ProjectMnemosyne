---
name: hephaestus-plugin-migration
description: "Migrate Claude Code plugin from ProjectMnemosyne to ProjectHephaestus. Use when: (1) switching enabled plugins between marketplaces, (2) updating ~/.claude/settings.json enabledPlugins or extraKnownMarketplaces, (3) separating command plugins from data-store marketplaces"
category: tooling
date: 2026-03-27
version: "1.0.0"
user-invocable: false
tags: [claude-code, plugin, marketplace, migration, hephaestus, mnemosyne, settings]
---

# Hephaestus Plugin Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Replace ProjectMnemosyne plugin with ProjectHephaestus plugin in Claude Code global settings |
| **Outcome** | Successful - plugins reloaded and all commands available |

## When to Use

- Migrating enabled plugins from one marketplace to another in `~/.claude/settings.json`
- Switching from `skills-registry-commands@ProjectMnemosyne` to `hephaestus@ProjectHephaestus`
- Needing to understand the `enabledPlugins` and `extraKnownMarketplaces` format in Claude Code settings
- Separating command-providing plugins from data-store marketplaces (commands in one repo, data in another)

## Verified Workflow

### Quick Reference

```bash
# Edit ~/.claude/settings.json:
# 1. Replace old plugin with new in enabledPlugins
# 2. Add new marketplace to extraKnownMarketplaces (if not present)
# 3. Old marketplace can be removed from extraKnownMarketplaces if
#    the new plugin clones the data repo independently

cat ~/.claude/settings.json | python3 -m json.tool
```

### Detailed Steps

1. **Identify current plugin configuration** in `~/.claude/settings.json`:
   - Check `enabledPlugins` for the old entry (e.g., `"skills-registry-commands@ProjectMnemosyne": true`)
   - Check `extraKnownMarketplaces` for registered marketplaces

2. **Update `enabledPlugins`**:
   - Remove: `"skills-registry-commands@ProjectMnemosyne": true`
   - Add: `"hephaestus@ProjectHephaestus": true`

3. **Update `extraKnownMarketplaces`**:
   - Add ProjectHephaestus entry with git source format:
     ```json
     {
       "source": {
         "source": "git",
         "url": "https://github.com/HomericIntelligence/ProjectHephaestus.git"
       }
     }
     ```
   - ProjectMnemosyne can be removed from `extraKnownMarketplaces` because ProjectHephaestus commands (`/advise`, `/learn`) clone ProjectMnemosyne independently to `$HOME/.agent-brain/ProjectMnemosyne/`

4. **Reload plugins** in the Claude Code session (or restart the session)

5. **Verify** the new commands are available: `/advise`, `/learn`, `/myrmidon-swarm`, `/repo-analyze`, `/repo-analyze-quick`, `/repo-analyze-strict`, `/create-reusable-utilities`, `/github-actions-python-cicd`, `/python-repo-modernization`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct settings.json edit worked first try | N/A | Solution was straightforward |

## Results & Parameters

### Configuration

The key formats in `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "hephaestus@ProjectHephaestus": true
  },
  "extraKnownMarketplaces": [
    {
      "source": {
        "source": "git",
        "url": "https://github.com/HomericIntelligence/ProjectHephaestus.git"
      }
    }
  ]
}
```

Format rules:
- `enabledPlugins` keys follow the pattern `"pluginName@MarketplaceName": true`
- `extraKnownMarketplaces` entries use nested `source` object with `"source": "git"` and `"url"` fields

### Expected Output

- All ProjectHephaestus commands appear in `/` slash-command list
- `/advise` and `/learn` still query ProjectMnemosyne data (cloned to `$HOME/.agent-brain/ProjectMnemosyne/`)
- No errors on plugin reload

### Key Insight

When migrating plugins between marketplaces, the old marketplace may still serve as a data backend. ProjectMnemosyne stores skills data while ProjectHephaestus provides the commands that query it. However, ProjectHephaestus commands handle cloning ProjectMnemosyne independently, so the old marketplace does not need to remain in `extraKnownMarketplaces`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence | Claude Code global settings migration | verified-local: settings applied and plugins reloaded successfully |

## References

- [claude-plugin-marketplace](claude-plugin-marketplace.md) - Marketplace setup and schema details
- [claude-code-settings-config](claude-code-settings-config.md) - Claude Code settings.json configuration
- [ProjectHephaestus](https://github.com/HomericIntelligence/ProjectHephaestus) - New plugin provider
- [ProjectMnemosyne](https://github.com/HomericIntelligence/ProjectMnemosyne) - Skills data store
