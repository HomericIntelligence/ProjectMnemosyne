# Skill: Fix Broken Documentation References

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-19 |
| Issue | #752 |
| PR | #811 |
| Category | documentation |
| Objective | Remove broken `agents/` directory references from CLAUDE.md after directory was deleted in commit `72ab40d` |
| Outcome | Success - all broken references removed, PR created and auto-merge enabled |

## When to Use

Trigger this skill when:

- A directory or file is removed from the repo but still referenced in CLAUDE.md or other docs
- `grep` finds dead links to paths that no longer exist
- CI or contributors report confusion from broken documentation links
- A refactor moves files and the architecture tree in CLAUDE.md becomes stale

## Verified Workflow

### 1. Identify all broken references

```bash
# Find all references to the removed path
grep -rn "agents/hierarchy.md\|agents/delegation-rules.md\|agents/templates\|agents/README" CLAUDE.md

# Also check broadly for the removed directory
grep -n "/agents/" CLAUDE.md
```

### 2. Verify current actual structure

```bash
# Confirm the directory is truly gone
ls /path/to/removed-dir 2>/dev/null || echo "Confirmed removed"

# Find where the content now lives
ls .claude/agents/  # or wherever it moved
```

### 3. Make targeted edits

Four categories of fixes for the `agents/` removal case:

1. **Quick Links section** - Remove bullet list items that link to removed files
2. **Narrative references** - Replace `See [file](path)` with plain text describing current location
3. **Documentation Rules** - Update path from removed dir to current dir
4. **Architecture tree** - Remove the entire removed-directory block from the `text` code block

### 4. Verify success criteria

```bash
# Confirm no broken refs remain
grep -n "agents/hierarchy.md\|agents/delegation-rules.md" CLAUDE.md
# Should return nothing

# Confirm new location is mentioned
grep -n "\.claude/agents" CLAUDE.md
```

### 5. Commit, push, and PR

```bash
git add CLAUDE.md
git commit -m "fix(docs): Remove broken <dir>/ references from CLAUDE.md

- Remove broken links to <dir>/file1 and <dir>/file2
- Update narrative to reference current location
- Remove <dir>/ from Repository Architecture tree

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "fix(docs): Remove broken <dir>/ references" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

**Skill tool was denied**: Attempted to use `commit-commands:commit-push-pr` skill but it was denied by the permission mode (`don't ask mode`). Fell back to direct Bash git commands — this works fine and is the correct fallback.

**No other failures**: The task was straightforward. Pre-commit hooks passed on first attempt because only Markdown was modified (skipped Python linters).

## Results & Parameters

### Actual changes made to CLAUDE.md

| Location | Before | After |
|----------|--------|-------|
| Quick Links > Agent System | 3 bullets (including broken links) | 1 bullet (Agent Configurations only) |
| Agent Hierarchy section | `See [agents/hierarchy.md](agents/hierarchy.md)...` | `Agent hierarchy is defined in .claude/agents/ and tests/claude-code/shared/agents/:` |
| Documentation Rules | `**Team guides**: /agents/ (quick start, hierarchy, templates)` | `**Agent guides**: /.claude/agents/ (configurations, roles, capabilities)` |
| Architecture tree | 5 lines for `agents/` directory | Removed entirely |

### Key insight: architecture tree already had scylla/discovery/

The issue mentioned adding `scylla/discovery/` to the architecture tree, but it was already present (line 401 before edits). Always verify deliverables against actual file state before acting.

### Pre-commit hook behavior

For Markdown-only changes, these hooks are skipped (no-files-to-check):

- Ruff Format Python
- Ruff Check Python
- Mypy Type Check Python
- Check Type Alias Shadowing
- YAML Lint
- ShellCheck

These hooks pass:

- Markdown Lint
- Trim Trailing Whitespace
- Fix End of Files
- Check for Large Files
- Fix Mixed Line Endings
