# Session Notes: Claude Code Slash Command Discovery

## Session Date
2026-03-15

## Project
ProjectHephaestus — `/repo-analyze`, `/repo-analyze-quick`, `/repo-analyze-strict` commands

## Problem Statement

Three slash commands were defined as `.md` files in `.claude/plugins/repo-analyzer/commands/`
at both project level and `~/.claude/plugins/repo-analyzer/commands/`. Despite existing, none
appeared in Claude Code autocomplete.

## Root Cause

Claude Code discovers slash commands from two auto-discovered locations:
- `.claude/commands/*.md` (project-level)
- `~/.claude/commands/*.md` (user-level)

Plugin directories (`.claude/plugins/<name>/commands/`) are only loaded if the plugin is:
1. Installed via the marketplace (registered in `installed_plugins.json`)
2. Enabled in `settings.json` under `enabledPlugins`

The repo-analyzer had neither — it was scaffolded manually with a `plugin.json` and command
files, but never went through the install flow. Claude Code silently skips unregistered plugins.

## Fix Applied

```
.claude/plugins/repo-analyzer/commands/repo-analyze.md
  → .claude/commands/repo-analyze.md
  → ~/.claude/commands/repo-analyze.md

.claude/plugins/repo-analyzer/commands/repo-analyze-quick.md
  → .claude/commands/repo-analyze-quick.md
  → ~/.claude/commands/repo-analyze-quick.md

.claude/plugins/repo-analyzer/commands/repo-analyze-strict.md
  → .claude/commands/repo-analyze-strict.md
  → ~/.claude/commands/repo-analyze-strict.md
```

Project-level plugin dir removed and committed.
User-level plugin dir (`~/.claude/plugins/repo-analyzer/`) requires manual removal (safety hook
blocked `rm -rf` outside cwd).

## Commit

Branch: `hephaestus-full-remediation`
Message: `fix: move repo-analyzer from broken plugin to .claude/commands/ for slash command discovery`

## Key Insight

The `plugin.json` file in `.claude-plugin/plugin.json` describes a plugin but does NOT register
it. Registration is a separate step that requires going through the marketplace install flow.
Without registration, the entire plugin directory tree is invisible to Claude Code's command
discovery — there are no error messages or warnings.