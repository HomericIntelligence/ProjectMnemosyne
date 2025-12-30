---
description: Search team knowledge before starting work
---

# /advise

Search the skills registry for relevant prior learnings before starting work.

## Instructions

When the user invokes this command:

1. **Parse the user's goal** from $ARGUMENTS
2. **Read the marketplace.json** file to find available plugins
3. **Search matching plugins** by:
   - Description keywords
   - Tags (if present)
   - Category (if specified)
4. **Read relevant SKILL.md files** for matches
5. **Return structured findings** with:
   - What worked (verified approaches)
   - What failed (critical - prevents wasted effort)
   - Recommended parameters (copy-paste ready)

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

**Recommended Parameters**:
\`\`\`yaml
param1: value1
\`\`\`
```

## Example

```
/skills-registry-commands:advise training a model with GRPO
```
