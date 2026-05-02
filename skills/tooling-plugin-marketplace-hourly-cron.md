---
name: tooling-plugin-marketplace-hourly-cron
description: "Set up a cron job to auto-update Claude Code plugin marketplaces hourly.
  Use when: (1) a custom marketplace (e.g., ProjectMnemosyne) needs to stay current
  without manual /plugin update, (2) ensuring new skills are available on next Claude
  Code session start."
category: tooling
date: 2026-03-25
version: 1.0.0
user-invocable: false
verification: verified-local
tags:
  - cron
  - plugin
  - marketplace
  - auto-update
  - claude-code
---

# Plugin Marketplace Hourly Cron Update

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Auto-update a Claude Code plugin marketplace (ProjectMnemosyne) every hour via cron so new skills are available on next session start |
| **Outcome** | Success - cron job installed, marketplace updates hourly, no manual intervention needed |
| **Verification** | verified-local |

## When to Use

- A custom plugin marketplace (git-based) needs to stay current without running `/plugin` manually
- New skills are merged to ProjectMnemosyne frequently and should be available on next Claude Code session
- Multiple developers share a marketplace and need consistent, up-to-date skill registries
- You want zero-touch marketplace freshness between Claude Code sessions

## Verified Workflow

### Quick Reference

```bash
# Two commands needed:
# 1. Update the marketplace index (git pull on the marketplace repo)
claude plugin marketplace update ProjectMnemosyne

# 2. Update the installed plugin to pick up new versions
claude plugin update mnemosyne@ProjectMnemosyne

# Install as hourly cron (runs at minute 0 of every hour):
(crontab -l 2>/dev/null; echo "0 * * * * /home/<user>/.local/bin/claude plugin marketplace update ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1 && /home/<user>/.local/bin/claude plugin update mnemosyne@ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1") | crontab -
```

### Detailed Steps

1. **Identify the CLI commands** — Claude Code has two distinct update operations:
   - `claude plugin marketplace update <name>` — pulls latest git for the marketplace index (the repo that lists available plugins)
   - `claude plugin update <plugin>@<marketplace>` — updates an installed plugin to the latest version from the marketplace

2. **Use absolute paths in cron** — cron does not load shell profiles, so the `claude` binary must be referenced by full path (e.g., `/home/<user>/.local/bin/claude`)

3. **Chain both commands** — use `&&` so the plugin update only runs if the marketplace update succeeds

4. **Log output** — redirect stdout and stderr to `/tmp/claude-plugin-update.log` for debugging

5. **Install the cron job**:
   ```bash
   (crontab -l 2>/dev/null; echo "# Update ProjectMnemosyne plugin marketplace hourly
   0 * * * * /home/<user>/.local/bin/claude plugin marketplace update ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1 && /home/<user>/.local/bin/claude plugin update mnemosyne@ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1") | crontab -
   ```

6. **Verify installation**: `crontab -l`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using just `claude` without full path | `0 * * * * claude plugin marketplace update ...` | cron does not source `.bashrc`/`.profile`, so `claude` is not on PATH | Always use absolute path to binary in cron jobs (e.g., `/home/<user>/.local/bin/claude`) |
| Updating only the marketplace | `claude plugin marketplace update ProjectMnemosyne` alone | Marketplace index updates but installed plugin version doesn't change | Must also run `claude plugin update <plugin>@<marketplace>` to pick up new plugin versions |

## Results & Parameters

### Claude Code Plugin CLI Reference

| Command | Purpose |
| --------- | --------- |
| `claude plugin marketplace update [name]` | Pull latest git for marketplace (updates all if no name) |
| `claude plugin update <plugin>@<marketplace>` | Update installed plugin to latest version |
| `claude plugin marketplace list` | List configured marketplaces |
| `claude plugin list` | List installed plugins |

### Marketplace Storage Locations

| Item | Path |
| ------ | ------ |
| Marketplace repos | `~/.claude/plugins/marketplaces/<name>/` |
| Installed plugins | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` |
| Plugin registry | `~/.claude/plugins/installed_plugins.json` |
| Marketplace config | `~/.claude/plugins/known_marketplaces.json` |

### Cron Job Parameters

```bash
# Schedule: every hour at minute 0
# Log file: /tmp/claude-plugin-update.log
# Binary: absolute path to claude CLI
0 * * * * /home/<user>/.local/bin/claude plugin marketplace update ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1 && /home/<user>/.local/bin/claude plugin update mnemosyne@ProjectMnemosyne >> /tmp/claude-plugin-update.log 2>&1
```

### Adapting for Other Marketplaces

Replace `ProjectMnemosyne` and `mnemosyne@ProjectMnemosyne` with your marketplace and plugin names:

```bash
# List your marketplaces
claude plugin marketplace list

# List installed plugins to find the correct name
claude plugin list
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence ecosystem | Session setting up hourly auto-update for ProjectMnemosyne marketplace | Cron job installed, both commands tested manually, log output confirmed |
