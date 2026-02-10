---
name: advise
description: Search team knowledge before starting work. Use when starting experiments, debugging unfamiliar errors, or before implementing features with unknowns.
user-invocable: false
---

# /advise

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Search the skills registry for relevant prior learnings before starting work. - Starting a new experiment or task |
| Outcome | Operational |


Search the skills registry for relevant prior learnings before starting work.

## When to Use

- Starting a new experiment or task
- Before implementing a feature with unknowns
- When debugging an unfamiliar error
- When you want to avoid repeating past mistakes

## Invocation

```
/advise <topic or goal>
```

Examples:
```
/advise training a model with GRPO
/advise debugging SIMD errors in Mojo
/advise setting up GitHub Actions for ML
```

## Verified Workflow

1. **Parse user's goal** from the prompt
2. **Read `marketplace.json`** for available plugins
3. **Search matching plugins** by:
   - Description keywords
   - Tags (exact match)
   - Category (if specified)
4. **Read relevant SKILL.md files** for matches
5. **Return structured findings**

## Output Format

```markdown
### Related Skills Found

| Skill | Category | Relevance |
|-------|----------|-----------|
| skill-name | category | Why relevant |

### Key Findings

**What Worked**:
- Verified approach 1
- Verified approach 2

**What Failed** (Critical!):
- Failed approach 1: Why it failed
- Failed approach 2: Why it failed

**Recommended Parameters**:
\`\`\`yaml
param1: value1
param2: value2
\`\`\`
```

## Implementation for Importing Agents

Add this to your project's `CLAUDE.md`:

```markdown
## Commands

### /advise

Search skills registry for relevant experiments before starting work.

1. Read user's goal/question
2. Read `marketplace.json` to find matching plugins
3. For each match, read the plugin's SKILL.md
4. Summarize: what worked, what failed, recommended parameters
5. Always prioritize Failed Attempts - these prevent wasted effort
```

## Required Files

Your project needs:
- `marketplace.json` - Index of available plugins
- `plugins/<category>/<name>/skills/<name>/SKILL.md` - Skill documents

## Search Priority

1. **Failed Attempts first** - Most valuable, prevents wasted effort
2. **Exact tag matches** - High confidence relevance
3. **Description keywords** - Broader matches
4. **Copy-paste configs** - When available, include them

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Searching only by exact tag match | Missed relevant skills with different tags | Include description keyword matching |
| Not prioritizing Failed Attempts | Users repeated mistakes | Show failures first in output |
| Vague search queries | Too many irrelevant results | Encourage users to be specific about context |
| Reading all SKILL.md files | Performance issues with large registry | Filter by category/tags first, then read |
| Not showing parameter snippets | Users had to open files manually | Include copy-paste configs in summary |


## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- Source: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- See `skill-documentation-patterns` for writing searchable skills
