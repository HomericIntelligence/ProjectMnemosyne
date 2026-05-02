---
name: tooling-plugin-command-codebase-rename
description: "Rename a Claude Code plugin directory, commands, and hooks across an entire codebase. Use when: (1) renaming a plugin from one name to another, (2) renaming a slash command, (3) bulk find-and-replace of plugin/command references across 40+ files."
category: tooling
date: 2026-03-26
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [rename, plugin, command, refactor, bulk-rename, mnemosyne]
---

# Plugin and Command Codebase-Wide Rename

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-26 |
| **Objective** | Rename `skills-registry-commands` plugin to `mnemosyne` and `/retrospective` command to `/learn` across 41 files |
| **Outcome** | All references updated, CI passes, zero stale references remaining |
| **Verification** | verified-ci |

## When to Use

- Renaming a Claude Code plugin directory (e.g., `plugins/tooling/old-name/` to `plugins/tooling/new-name/`)
- Renaming a slash command (e.g., `/old-command` to `/new-command`)
- Bulk find-and-replace of plugin invocations across documentation, skills, and config files
- Need to rename hook scripts that reference the old command name

## Verified Workflow

### Quick Reference

```bash
# 1. Structural renames (preserves git history)
mv plugins/tooling/old-name plugins/tooling/new-name
mv plugins/tooling/new-name/commands/old-cmd.md plugins/tooling/new-name/commands/new-cmd.md
mv plugins/tooling/new-name/hooks/old-trigger.py plugins/tooling/new-name/hooks/new-trigger.py

# 2. Find all files needing content edits
grep -rl "old-name\|/old-cmd\|old-trigger" . --include="*.md" --include="*.json" --include="*.py" | grep -v .git/

# 3. Verify no stale references after edits
grep -rn "old-name" --include="*.md" --include="*.json" --include="*.py" . | grep -v .git/ | grep -v CHANGELOG
```

### Detailed Steps

**Phase 1: Structural renames**

1. Create worktree from origin/main for isolation
2. Rename the plugin directory: `mv plugins/tooling/old/ plugins/tooling/new/`
3. Rename command file: `mv commands/old-cmd.md commands/new-cmd.md`
4. Rename hook scripts: `mv hooks/old-trigger.py hooks/new-trigger.py`
5. Rename internal skill dirs: `mv skills/old-cmd/ skills/new-cmd/`
6. Rename root-level hooks: `mv .claude/hooks/old-trigger.py .claude/hooks/new-trigger.py`
7. `git add -A` to stage all renames

**Phase 2: Content edits (single comprehensive agent)**

Launch ONE agent to edit ALL files — do not split across parallel agents sharing a worktree (see Failed Attempts). The agent should:
1. Get full file list: `grep -rl "old-name" . --include="*.md" --include="*.json" --include="*.py"`
2. Edit each file systematically with these replacements:
   - Plugin name: `old-name` → `new-name`
   - Command invocations: `/old-cmd` → `/new-cmd`
   - Qualified invocations: `/old-name:old-cmd` → `/new-name:new-cmd`
   - Hook filenames: `old-trigger` → `new-trigger`
   - Path references: `commands/old-cmd.md` → `commands/new-cmd.md`
3. In CHANGELOG.md: ADD new entry at top, do NOT modify historical entries
4. Verify zero stale references remain

**Phase 3: Validate and commit**

```bash
python3 scripts/validate_plugins.py
git add -A && git commit && git push
gh pr create && gh pr merge --auto --rebase
```

**Phase 4: Clean up worktree**

```bash
git worktree remove /tmp/worktree-path
git worktree prune
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `git mv` for directory rename | `git mv plugins/tooling/old plugins/tooling/new` | Failed with "bad source" error on directory-to-directory rename | Use plain `mv` + `git add -A` instead of `git mv` for directory renames |
| Parallel agents in shared worktree | Launched 3 parallel Haiku agents to edit non-overlapping files in same worktree | Worktree was lost/cleaned up between phases, losing all edits | Use ONE comprehensive agent for all content edits in a shared worktree, or use separate worktrees per agent |
| Split content edits across 3+ agents | Each agent edited its group of files (plugin files, docs, skills) | Work was lost when worktree disappeared; had to redo everything | Single Sonnet agent handling all 41 files is more reliable than 3 parallel Haiku agents |
| Selective `/retrospective` replacement | Tried replacing all occurrences of "retrospective" | Over-replaced — changed prose descriptions ("retrospective session") not just command names | Only replace `/retrospective` (command invocation), not the general word "retrospective" |

## Results & Parameters

### Rename Scope

```yaml
files_changed: 41
plugin_directory: plugins/tooling/skills-registry-commands/ → plugins/tooling/mnemosyne/
command_file: commands/retrospective.md → commands/learn.md
hook_script: retrospective-trigger.py → learn-trigger.py
skill_dir: skills/retrospective/ → skills/learn/
```

### Replacement Patterns

```yaml
# Order matters — do qualified invocations first, then general
replacements:
  - old: "/skills-registry-commands:retrospective"
    new: "/mnemosyne:learn"
  - old: "/skills-registry-commands:advise"
    new: "/mnemosyne:advise"
  - old: "skills-registry-commands"
    new: "mnemosyne"
  - old: "/retrospective"  # command invocation only
    new: "/learn"
  - old: "retrospective-trigger"
    new: "learn-trigger"
```

### File Groups Affected

| Group | Count | Examples |
| ------- | ------- | --------- |
| Plugin internals | 8 | plugin.json, commands/*.md, hooks/*.py |
| Root config | 2 | .claude/settings.json, .claude/hooks/ |
| Documentation | 5 | CLAUDE.md, README.md, CONTRIBUTING.md |
| Skill files | 27 | Various skills referencing commands |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | PR #1061, full plugin+command rename | 2026-03-26 session |
