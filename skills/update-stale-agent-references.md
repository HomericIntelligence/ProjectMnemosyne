---
name: update-stale-agent-references
description: 'Find and update stale cross-references to deleted agent files in documentation.
  Use when: agent files are deleted or consolidated and docs still reference old agent
  names.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | update-stale-agent-references |
| **Category** | documentation |
| **Trigger** | After agent files are deleted or consolidated |
| **Scope** | `.claude/agents/`, `agents/`, `docs/dev/` markdown files |
| **Outcome** | All stale agent name references replaced with new consolidated agent name |

## When to Use

- Agent consolidation issues (e.g. merging N specialist agents into one general agent)
- Follow-up cleanup after deleting agent `.md` files
- When a grep of `.claude/agents/` or `docs/` reveals references to non-existent files
- Before closing a consolidation PR to verify no dangling cross-references remain

## Verified Workflow

1. **Identify deleted agent names** from the consolidation issue (e.g. issue body lists files deleted)

2. **Run broad grep** across all markdown files to find any references:

   ```bash
   grep -r "algorithm-review-specialist\|safety-review-specialist\|..." \
     --include="*.md" -l
   ```

3. **Inspect each match** with line numbers to understand context:

   ```bash
   grep -n "deleted-agent-name" path/to/file.md
   ```

4. **Read the file** to understand the section and what the correct replacement should be

5. **Edit the file** replacing deleted agent list entries with the consolidated agent:
   - Update count labels (e.g. "Review Specialists (10):" → "Review Specialists (4):")
   - Replace deleted agent bullet points with the new consolidated agent
   - Keep surviving agents (those not deleted) in the list

6. **Re-run grep** to confirm zero remaining stale references:

   ```bash
   grep -r "deleted-agent-name" --include="*.md"
   ```

7. **Commit** with a descriptive message referencing the consolidation issue

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Searching only `.claude/agents/` | Ran grep scoped to `.claude/agents/*.md` | Tracking docs in `docs/dev/` were missed | Always search the full repo, not just the agents directory |
| Assuming hierarchy.md is the only doc to update | Only checked `agents/hierarchy.md` | Status/tracking docs like `agent-claude4-update-status.md` also list agents by name | Search recursively across all `*.md` files |
| Replacing agent names without reading context | Applied sed-style bulk replace | Counting labels ("Review Specialists (10)") also need updating | Read surrounding context before editing; update counts too |

## Results & Parameters

### Grep pattern for the 10 agents deleted in issue #3144

```bash
grep -rn \
  "algorithm-review-specialist\|safety-review-specialist\|performance-review-specialist\|architecture-review-specialist\|documentation-review-specialist\|data-engineering-review-specialist\|dependency-review-specialist\|implementation-review-specialist\|paper-review-specialist\|research-review-specialist" \
  --include="*.md"
```

### Edit pattern (example)

Replace a 10-item deleted-agent list section:

```
**Review Specialists (10):**

- `.claude/agents/algorithm-review-specialist.md`
- ...10 deleted agents...
```

With the consolidated 4-agent section:

```
**Review Specialists (4):**

- `.claude/agents/general-review-specialist.md`
- `.claude/agents/mojo-language-review-specialist.md`
- `.claude/agents/security-review-specialist.md`
- `.claude/agents/test-review-specialist.md`
```

### Key insight

The only file with stale references after issue #3144 was
`docs/dev/agent-claude4-update-status.md` — a tracking doc listing agents
needing Claude 4 updates. The `.claude/agents/` directory and `agents/hierarchy.md`
had already been updated by the original consolidation PR.
