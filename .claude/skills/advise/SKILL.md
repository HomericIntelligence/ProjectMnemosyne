---
name: advise
description: "Search team knowledge before starting work. Use at session start or before experiments."
category: marketplace
---

# Advise

Search the ProjectMnemosyne skills registry for relevant prior learnings.

## When to Use

- Starting a new experiment or task
- Before implementing a feature with unknowns
- When debugging an unfamiliar error
- When you want to avoid repeating past mistakes

## Quick Reference

```bash
# User invokes
/advise <topic or goal>

# Claude searches marketplace.json and returns findings
```

## Workflow

1. Parse user's goal/question from the prompt
2. Read `marketplace.json` for available plugins
3. Search matching plugins by:
   - Tags (exact match)
   - Description (keyword match)
   - Category (if specified)
4. Read relevant SKILL.md files for matches
5. Summarize findings in structured format

## Output Format

### Related Skills Found

| Skill | Category | Relevance |
|-------|----------|-----------|
| skill-name | category | Why this skill is relevant |

### Key Findings

**What Worked**:

- Verified approach 1
- Verified approach 2

**What Failed** (Critical!):

- Failed approach 1: Why it failed
- Failed approach 2: Why it failed

**Recommended Parameters**:

```yaml
param1: value1
param2: value2
```

## Implementation Notes

- Always check Failed Attempts first - these prevent wasted effort
- Prioritize skills with matching tags over keyword matches
- Include copy-paste ready configs when available
- Link to full skill for detailed workflow

## References

- See CLAUDE.md for plugin standards
- See `marketplace.json` for searchable index
