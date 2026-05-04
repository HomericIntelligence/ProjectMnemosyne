---
name: tooling-plugin-cache-stale-skill-sync
description: "Use when a plugin skill is not loading updated content after a merge: (1) /reload-plugins loads old skill content even after origin/main has the new version, (2) a plugin added skills without bumping its semver version string, (3) the plugin cache directory is pinned to an old git SHA. Fix by manually syncing files into the version-keyed cache directory."
category: tooling
date: 2026-05-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [plugin, cache, stale, reload-plugins, skill-sync, semver, gitCommitSha, installed_plugins]
---

# Plugin Cache Staleness — Manual Skill Sync

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-04 |
| **Objective** | Load updated skill content from a plugin after new skills were merged without a version bump |
| **Outcome** | `/hephaestus:worktree-cleanup` loaded correct updated content after cache sync + `/reload-plugins` |
| **Verification** | verified-local — confirmed skill content updated in session; not yet confirmed in CI |

## When to Use

- `/reload-plugins` still loads old skill content even though `origin/main` has the updated version
- A plugin shipped new or updated skills in a PR that merged without bumping the plugin's semver version string
- `~/.claude/plugins/installed_plugins.json` shows a `gitCommitSha` that predates the PR you just merged
- Running `/plugin` (marketplace update) didn't refresh the skill content

## Verified Workflow

### Quick Reference

```bash
PLUGIN_NAME="ProjectHephaestus"   # adjust to your plugin
PLUGIN_ID="hephaestus"            # adjust to match cache dir name
PLUGIN_VERSION="3.0.0"            # adjust to installed version
SKILL_NAME="worktree-cleanup"     # adjust to the missing/stale skill

CACHE=~/.claude/plugins/cache/$PLUGIN_NAME/$PLUGIN_ID/$PLUGIN_VERSION
REPO=~/$PLUGIN_NAME               # or wherever the repo is cloned

# 1. Sync missing/updated skill into cache
mkdir -p "$CACHE/skills/$SKILL_NAME"
git -C "$REPO" show origin/main:skills/$SKILL_NAME/SKILL.md > "$CACHE/skills/$SKILL_NAME/SKILL.md"

# 2. Sync updated marketplace.json (so the cache reflects current skill list)
git -C "$REPO" show origin/main:.claude-plugin/marketplace.json > "$CACHE/.claude-plugin/marketplace.json"

# 3. Update gitCommitSha in installed_plugins.json to current origin/main SHA
CURRENT_SHA=$(git -C "$REPO" rev-parse origin/main)
# Edit ~/.claude/plugins/installed_plugins.json:
# Replace the old SHA for this plugin with $CURRENT_SHA
# e.g.: jq --arg sha "$CURRENT_SHA" '(.[] | select(.id == "'"$PLUGIN_ID"'") | .gitCommitSha) = $sha' \
#         ~/.claude/plugins/installed_plugins.json > /tmp/plugins.json && \
#         mv /tmp/plugins.json ~/.claude/plugins/installed_plugins.json

# 4. Run /reload-plugins in Claude Code
```

### Detailed Steps

1. **Identify the cache directory** — find it at `~/.claude/plugins/cache/<PluginName>/<plugin-id>/<version>/`

2. **Identify the stale skill** — run `/hephaestus:<skill-name>` or check the cache directory's `skills/` listing vs the repo's `skills/` listing

3. **Sync the missing skill file** — use `git show origin/main:<path>` to extract the current file from the repo and write it directly into the cache directory (never checkout the branch, just read the blob)

4. **Sync marketplace.json** — the cache has its own copy; update it so the plugin system sees the current skill list

5. **Update `gitCommitSha`** — edit `~/.claude/plugins/installed_plugins.json` to set `gitCommitSha` for the affected plugin to the current `origin/main` SHA so the plugin system knows the cache is current

6. **Run `/reload-plugins`** — the plugin system will now read updated content from the cache

7. **Verify** — invoke the updated skill to confirm it loads the new content

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `/plugin` (marketplace update) | Used the marketplace update command to refresh the plugin | Didn't refresh cache because the version string (`3.0.0`) hadn't changed — the command uses version as cache key | `/plugin` only re-extracts when version changes; a same-version update is a no-op |
| Run `/reload-plugins` before syncing cache | Ran reload without first updating cache files | Loaded old content from stale cache directory — the cache directory is reused, not re-extracted, when version string matches | Must sync files into cache first, then reload |
| Updating `gitCommitSha` alone | Updated the SHA in `installed_plugins.json` hoping it would trigger re-extraction | The cache directory is keyed by version string, not SHA — changing SHA alone does nothing if the version is unchanged | SHA update is necessary but not sufficient; files must be manually synced into the cache directory |

## Results & Parameters

### Root Cause

The plugin cache is keyed by **version string** (semver), not git SHA:

```
~/.claude/plugins/cache/<PluginName>/<plugin-id>/<version>/
```

When a plugin author merges new skills without bumping the version, the cache directory
(e.g., `3.0.0/`) is reused from the prior extraction. The `gitCommitSha` in
`installed_plugins.json` is purely informational — it does not invalidate the cache.

### Cache structure reference

```
~/.claude/plugins/
├── installed_plugins.json          # registry of installed plugins + gitCommitSha
└── cache/
    └── <PluginName>/
        └── <plugin-id>/
            └── <version>/
                ├── .claude-plugin/
                │   ├── marketplace.json    # skill index — must be updated
                │   └── plugin.json
                └── skills/
                    └── <skill-name>/
                        └── SKILL.md       # manually sync here
```

### Verified scenario (2026-05-04)

- Plugin: `ProjectHephaestus/hephaestus@3.0.0`
- PR merged: `#308` at commit `6cf7c87` — added `worktree-cleanup` skill
- Cache SHA: `b4ca3230` (predated PR #308)
- Fix: synced `SKILL.md` + `marketplace.json` into cache, updated SHA → `/reload-plugins` succeeded

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | `/hephaestus:worktree-cleanup` not loading after PR #308 merged without version bump | 2026-05-04; cache at `~/.claude/plugins/cache/ProjectHephaestus/hephaestus/3.0.0/`; verified skill loaded correct content after sync |
