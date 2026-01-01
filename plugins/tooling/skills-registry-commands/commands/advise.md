---
description: Search team knowledge before starting work
---

# /advise

Search the skills registry for relevant prior learnings before starting work.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Clone location**: `<ProjectRoot>/build/<PID>/`

Commands in the same session share the clone via process ID.

## Instructions

When the user invokes this command:

1. **Setup repository** (if not already cloned):
   ```bash
   BUILD_DIR="build/$$"

   # Clone repository if not present
   if [ ! -d "$BUILD_DIR" ]; then
     gh repo clone HomericIntelligence/ProjectMnemosyne "$BUILD_DIR"
   else
     # Update existing clone
     git -C "$BUILD_DIR" pull --ff-only origin main
   fi
   ```

2. **Parse the user's goal** from $ARGUMENTS
3. **Read the marketplace.json** file to find available plugins
4. **Search matching plugins** by:
   - Description keywords
   - Tags (if present)
   - Category (if specified)
5. **Read relevant SKILL.md files** for matches
6. **Return structured findings** with:
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
