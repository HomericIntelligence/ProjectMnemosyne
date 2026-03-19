---
name: agent-to-skill-conversion
description: 'Convert agent configurations to skills when tasks are fixed/predictable.
  Use when: (1) agent performs repeatable automation steps without adaptive reasoning,
  (2) reducing agent count to simplify hierarchy, (3) moving fixed-step workflows
  to the right abstraction layer.'
category: architecture
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Agent-to-Skill Conversion

Convert Claude Code agent configurations to skills when the task matches the skill pattern
(fixed steps, automation) rather than the agent pattern (adaptive reasoning, exploration).

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-05 |
| Objective | Convert blog-writer and pr-cleanup agents to skills (ProjectOdyssey issue #3145) |
| Outcome | 2 agents removed, 2 skills created, all references updated, PR #3320 created |

## When to Use

- Agent performs fixed, predictable, repeatable steps with no branching logic
- Agent does not require exploration, discovery, or adaptive decision-making
- Agent acts as automation wrapper rather than a reasoning entity
- Goal is to reduce agent count and put functionality at the right abstraction layer

**Trigger phrases**: "convert agent to skill", "agent does fixed steps", "too many agents",
"agent is just automation", "predictable agent workflow"

**Decision criteria** (all three must apply):

- Fixed, predictable steps
- Repeatable automation
- Does NOT require adaptive decision-making

## Verified Workflow

### Phase 1: Identify Candidate Agents

Review agent files and apply criteria:

```bash
# List all agents
ls .claude/agents/

# Check agent workflow for fixed vs adaptive steps
cat .claude/agents/<name>.md
```

Ask: Does this agent explore/discover, or does it follow a fixed checklist?

### Phase 2: Find an Existing Skill as Format Reference

```bash
# Find a similar skill for format reference
ls .claude/skills/
cat .claude/skills/<similar-skill>/SKILL.md
```

Key skill format elements:

- YAML frontmatter: `name`, `description`, `mcp_fallback`, `category`
- `## When to Use` - trigger conditions
- `## Quick Reference` - bash commands for common operations
- `## Workflow` - numbered steps
- `## Error Handling` - table of issues and fixes
- `## References` - related skills

### Phase 3: Create the Skill

Create `<skill-name>/SKILL.md` under `.claude/skills/`:

```markdown
---
name: <skill-name>
description: <description>. Use when <trigger>.
mcp_fallback: none
category: <category>
---

# <Skill Title>

<Brief overview paragraph.>

## When to Use

- Trigger condition 1
- Trigger condition 2

### Quick Reference

```bash
# Key commands
```

## Workflow

1. **Step 1** - Description
2. **Step 2** - Description
...

## Error Handling

| Problem | Solution |
|---------|----------|
| Issue 1 | Fix 1 |

## References

- Related skill: `<skill-name>`
```

### Phase 4: Delete the Agent Files

```bash
rm .claude/agents/<name>-specialist.md
```

### Phase 5: Update All References

Find and update every file that references the deleted agents:

```bash
# Find all references
grep -rl "<agent-name>" . --include="*.md"

# Common locations to check:
# - Other skill SKILL.md files (agent: field in frontmatter)
# - agents/hierarchy.md (agent count table, Level 3 diagram)
# - agents/README.md (Operational Agents section, Level 3 listing)
# - docs/dev/ files
```

**Update agent count in hierarchy.md:**

- Diagram box: `Level 3: Specialists (N agents)` → reduce N by count of removed agents
- Level 3 summary: `X total (Y implementation/execution specialists + 13 code review specialists)`
- Agent Count table: Level 3 row and Total row
- Level 3 Breakdown bullet: remove agent names from list
- Historical Note: update to reflect conversion rationale

**Update agents/README.md:**

- Level 3 section header count
- Implementation/Execution Specialists count and bullet list
- Operational Agents total count
- Level 3 Component Specialists section

### Phase 6: Commit and PR

```bash
git add .claude/agents/<deleted>.md .claude/skills/<new>/ \
        agents/hierarchy.md agents/README.md \
        .claude/skills/<updated>/SKILL.md

git commit -m "refactor(agents): convert <name> agents to skills

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` command directly | `just` not in PATH in this environment | Use `pixi run pre-commit run --all-files` instead |
| Running `pixi run npx markdownlint-cli2` directly | Called markdownlint outside pre-commit | `npx` not in pixi environment PATH | Markdown linting runs correctly via the pre-commit hook |
| Expecting mojo-format to pass | Ran pre-commit expecting all hooks to pass | GLIBC version incompatibility on host (requires 2.32-2.34, host has older) | mojo-format failure is environment-specific, not caused by our changes; other hooks still validate |
| Edit tool after long gap without re-read | Tried to edit a file not recently read | Edit tool requires a Read in current session | Always re-read files before editing if session has been long or file may have been modified |

## Results & Parameters

### Files Changed Pattern

For each agent converted to skill:

| Action | File |
|--------|------|
| Create | `.claude/skills/<name>/SKILL.md` |
| Delete | `.claude/agents/<name>-specialist.md` |
| Update | `agents/hierarchy.md` (counts, listings) |
| Update | `agents/README.md` (counts, listings) |
| Update | Any skill with `agent: <name>` in frontmatter |

### Agent Count Formula

```text
New total = Old total - number of converted agents
New Level 3 = Old Level 3 - number of converted agents
New implementation specialists = Old count - number of converted agents
```

### Skill Frontmatter Template (ProjectOdyssey format)

```yaml
---
name: <kebab-case-name>
description: <What it does>. Use when <trigger condition>.
mcp_fallback: none
category: <doc|github|phase|mojo|agent|quality|testing|review>
---
```

### Cross-Reference Search Pattern

```bash
# Find all references to old agent name
grep -rl "old-agent-name\|old-agent-specialist" . --include="*.md"

# Check for agent: field in skill frontmatter
grep -r "^agent:" .claude/skills/ --include="SKILL.md"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3145, PR #3320 | [notes.md](../references/notes.md) |

## Related Skills

- `agent-validate-config` - Validate agent YAML frontmatter after changes
- `agent-coverage-check` - Verify agent hierarchy coverage is still complete after removal
- `agent-hierarchy-diagram` - Regenerate hierarchy diagram after agent count changes
