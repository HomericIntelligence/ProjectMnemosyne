---
name: claude-code-slash-command-discovery
description: 'Fix slash commands not appearing in Claude Code autocomplete by moving
  .md files to the correct auto-discovered directory. Use when: commands sit in an
  unregistered plugin directory and are not discoverable.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Claude Code Slash Command Discovery

## Overview

| Item | Details |
| ------ | --------- |
| Name | claude-code-slash-command-discovery |
| Category | tooling |
| Root cause | Commands placed in `.claude/plugins/<name>/commands/` without marketplace registration are never loaded |
| Fix | Move `.md` files to `.claude/commands/` (project) or `~/.claude/commands/` (user-level) |
| Outcome | Commands appear immediately in autocomplete on next session |

## When to Use

- Custom slash commands exist as `.md` files but never appear in Claude Code autocomplete
- Commands are stored under `.claude/plugins/<name>/commands/` without an `installed_plugins.json` entry or `enabledPlugins` setting
- A plugin was scaffolded manually (not installed via marketplace) so the discovery mechanism bypasses it
- Commands should be available cross-project (user-level) rather than only in one repo

## Verified Workflow

### 1. Identify the dead-end location

Check whether the commands are in an unregistered plugin directory:

```bash
ls .claude/plugins/*/commands/*.md
```

If files are here but not showing in autocomplete, the plugin is not registered.

### 2. Create the auto-discovered directories

```bash
# Project-level (available only in this repo)
mkdir -p .claude/commands/

# User-level (available in every repo)
mkdir -p ~/.claude/commands/
```

### 3. Copy command files to correct locations

```bash
cp .claude/plugins/<plugin-name>/commands/*.md .claude/commands/
cp .claude/commands/*.md ~/.claude/commands/
```

### 4. Remove the dead plugin directory

```bash
# Project-level (safe — within cwd)
rm -rf .claude/plugins/<plugin-name>/

# User-level (outside cwd — run manually or with explicit permission)
rm -rf ~/.claude/plugins/<plugin-name>/
```

> **Note**: Safety hooks may block `rm -rf` on paths outside the working directory. Run the `~/.claude/plugins/` removal manually if blocked.

### 5. Commit the migration

```bash
git add .claude/commands/
git rm -r .claude/plugins/<plugin-name>/
git commit -m "fix: move <name> from broken plugin to .claude/commands/ for slash command discovery"
```

### 6. Verify

Start a new Claude Code session and type `/` — the commands should appear in autocomplete.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Placing commands in `.claude/plugins/<name>/commands/` | Created plugin directory structure with plugin.json and command .md files | Claude Code only loads plugin commands from plugins registered in `installed_plugins.json` + `enabledPlugins` — unregistered plugins are silently ignored | Plugin directory structure requires marketplace registration; without it, files are dead |
| Expecting plugin.json alone to enable commands | Created `.claude-plugin/plugin.json` in the plugin directory | `plugin.json` describes the plugin but does not register it — registration requires marketplace install flow | A plugin.json alone has no effect on discovery without the install flow |
| `rm -rf ~/.claude/plugins/...` from within project | Tried to delete user-level plugin dir in same bash command as project-level cleanup | Safety hook blocks `rm -rf` on paths outside the current working directory | Run user-level deletions manually or ask user to confirm separately |

## Results & Parameters

### Discovery mechanism summary

| Location | Scope | Registration required? |
| ---------- | ------- | ------------------------ |
| `.claude/commands/*.md` | Current project only | No — auto-discovered |
| `~/.claude/commands/*.md` | All projects for this user | No — auto-discovered |
| `.claude/plugins/<name>/commands/*.md` | Plugin-scoped | Yes — needs marketplace install + `enabledPlugins` |

### Copy-paste migration script

```bash
PLUGIN_NAME="repo-analyzer"

# Project-level
mkdir -p .claude/commands/
cp .claude/plugins/${PLUGIN_NAME}/commands/*.md .claude/commands/

# User-level (run separately if safety hook blocks ~/ paths)
mkdir -p ~/.claude/commands/
cp .claude/commands/*.md ~/.claude/commands/

# Cleanup
rm -rf .claude/plugins/${PLUGIN_NAME}/

# Commit
git add .claude/commands/
git rm -r .claude/plugins/${PLUGIN_NAME}/
git commit -m "fix: move ${PLUGIN_NAME} from broken plugin to .claude/commands/ for slash command discovery"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | repo-analyzer commands migration | [notes.md](../../references/notes.md) |
