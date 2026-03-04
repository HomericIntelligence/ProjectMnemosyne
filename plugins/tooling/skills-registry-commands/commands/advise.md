---
description: Search team knowledge before starting work
---

# /advise

Search the skills registry for relevant prior learnings before starting work.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Clone location**: `<ProjectRoot>/build/<PID>/ProjectMnemosyne/`

Each Claude Code session gets its own isolated clone (via process ID) to avoid interference.
Automatically skipped if already running in the ProjectMnemosyne repository.

## Instructions

When the user invokes this command:

### Phase 1: Search and Present Findings

1. **Setup repository** (if not already cloned):
   ```bash
   # Detect if already in ProjectMnemosyne
   CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
   if [[ "$CURRENT_REMOTE" == *"ProjectMnemosyne"* ]] && [[ "$CURRENT_REMOTE" != *"ProjectMnemosyne-"* ]]; then
     # Already in ProjectMnemosyne - use current directory
     MNEMOSYNE_DIR="."
   else
     # Use PID-scoped build directory to avoid interference between Claude instances
     MNEMOSYNE_DIR="build/$$/ProjectMnemosyne"

     if [ ! -d "$MNEMOSYNE_DIR" ]; then
       # Clone fresh
       mkdir -p "build/$$"
       gh repo clone HomericIntelligence/ProjectMnemosyne "$MNEMOSYNE_DIR"
     else
       # Update existing clone before analysis
       # Ensure we're on main branch
       if ! git -C "$MNEMOSYNE_DIR" symbolic-ref HEAD | grep -q "refs/heads/main"; then
         echo "Error: $MNEMOSYNE_DIR is not on main branch."
         echo "Fix: rm -rf build/$$"
         exit 1
       fi

       # Ensure no local commits or conflicts
       if ! git -C "$MNEMOSYNE_DIR" pull --ff-only origin main; then
         echo "Error: Cannot fast-forward $MNEMOSYNE_DIR/main. May have local commits or conflicts."
         echo "Fix: rm -rf build/$$"
         exit 1
       fi
     fi
   fi
   ```

2. **Parse the user's goal** from $ARGUMENTS
3. **Read `.claude-plugin/marketplace.json`** to find available plugins
4. **Search matching plugins** by:
   - Category first (if user's query implies one)
   - Description keywords and trigger conditions
   - Tags (if present)
   - Select top 5 most relevant matches
5. **Read SKILL.md files** for top matches only
   - Focus on: `## Failed Attempts`, `## When to Use`, `## Results & Parameters`
6. **Present findings**:
   - What worked (verified approaches)
   - What failed (critical — prevents wasted effort)
   - Recommended parameters (copy-paste ready)

### Phase 2: Follow-Up (If Needed)

After presenting findings, ask:
"Would you like me to dig deeper into any of these skills, or are you ready to proceed?"

If the user wants more detail, read the full SKILL.md for the most relevant matches.

> **Note**: If the user's goal involves **creating or fixing skills**, remind them to run `/retrospective` which includes the Pre-Commit Validation Checklist, or point them to the [Top CI Failures](retrospective.md#top-ci-failures-most-common) section in the retrospective command for the most common plugin validation errors.

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

**Need more detail?** Ask me to read the full SKILL.md for any skill above.
```

## Example Workflow

### Invocation

```bash
/skills-registry-commands:advise training a model with GRPO
```

### Output

```markdown
### Related Skills Found

| Skill | Category | Relevance |
|-------|----------|-----------|
| grpo-external-vllm | training | Uses external vLLM server for GRPO training |
| grpo-batch-tuning | optimization | Optimal batch sizes for GRPO |

### Key Findings

**What Worked**:
- External vLLM server prevents memory issues
- batch_size=4 with learning_rate=1e-5 for 7B models
- Separate GPU setup for vLLM server

**What Failed** (Critical!):
- vllm_skip_weight_sync errors when vLLM on same GPU
- batch_size > 8 causes OOM on 24GB GPUs
- learning_rate > 5e-5 causes training instability

**Need more detail?** Ask me to read the full SKILL.md for any skill above.
```
