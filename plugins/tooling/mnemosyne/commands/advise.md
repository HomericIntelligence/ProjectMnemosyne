---
description: Search team knowledge before starting work. Use when starting experiments, debugging unfamiliar errors, or before implementing features with unknowns.
---

# /advise

Search the skills registry for relevant prior learnings before starting work.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Clone location**: `$HOME/.agent-brain/ProjectMnemosyne/`

Single shared clone in user's home directory. Automatically updated before searches.
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
     # Use shared home directory location
     MNEMOSYNE_DIR="$HOME/.agent-brain/ProjectMnemosyne"

     if [ ! -d "$MNEMOSYNE_DIR" ]; then
       # Clone fresh
       mkdir -p "$HOME/.agent-brain"
       gh repo clone HomericIntelligence/ProjectMnemosyne "$MNEMOSYNE_DIR"
     fi

     # Always update to latest main before searching
     git -C "$MNEMOSYNE_DIR" fetch origin
     git -C "$MNEMOSYNE_DIR" checkout main
     git -C "$MNEMOSYNE_DIR" pull --ff-only origin main
   fi
   ```

2. **Parse the user's goal** from $ARGUMENTS
3. **Read `.claude-plugin/marketplace.json`** to find available plugins
4. **Search matching plugins** by:
   - Category first (if user's query implies one)
   - Description keywords and trigger conditions
   - Tags (if present)
   - Select top 5 most relevant matches
5. **Read skill `.md` files** for top matches only (from flat `skills/<name>.md` files)
   - Focus on: `## Failed Attempts`, `## When to Use`, `## Results & Parameters`

6. **CRITICAL — Credibility assessment** for each matched skill:

   Check the `verification` field in YAML frontmatter. If absent, treat as `unverified`.

   Score each skill:
   - `verified-ci` = HIGH confidence — the approach was validated end-to-end in CI
   - `verified-local` = MEDIUM confidence — works locally but CI may differ
   - `verified-precommit` = LOW confidence — only formatting/linting checked, not execution
   - `unverified` or missing = TREAT WITH SKEPTICISM — approach is theoretical

   **Flag contradictions**: If two skills give conflicting advice for the same topic, highlight
   both and explain which is newer/better verified. Example: "Skill A says retry JIT crashes,
   but newer Skill B (verified-ci) says they were actually compile errors."

7. **CRITICAL — Check for history files**:

   For each matched skill, check if a `.history` file exists:
   ```bash
   ls "$MNEMOSYNE_DIR/skills/<name>.history" 2>/dev/null
   ```

   If a history file exists, check the version and read the changelog headers to understand
   how the skill has evolved. A skill at v3.0.0 with a rich history has been battle-tested
   and amended multiple times — it's more trustworthy than a v1.0.0 skill.

   When presenting findings, note the version:
   - `v1.0.0` = initial version, may not have been refined
   - `v2.0.0+` = amended at least once, has a history log showing what changed and why
   - Skills with history files that show prior approaches were wrong are especially valuable —
     they document the evolution from wrong to right

   If a history file shows the skill contradicts its own earlier version, highlight this:
   "> **Evolution note:** This skill was amended from v1.0.0 (which recommended X) to v2.0.0
   > (which recommends Y instead). The history log explains why X didn't work."

8. **Present findings** with credibility markers:
   - What worked (verified approaches) — with verification level and version
   - What failed (critical — prevents wasted effort)
   - Evolution notes from history files (if any)
   - Recommended parameters (copy-paste ready)

### Phase 2: Follow-Up (If Needed)

After presenting findings, ask:
"Would you like me to dig deeper into any of these skills, or are you ready to proceed?"

If the user wants more detail, read the full skill `.md` file and its `.history` file
for the most relevant matches.

> **Note**: If the user's goal involves **creating or fixing skills**, remind them to run
> `/retrospective` which captures session learnings and creates or amends a skill file.

## Output Format

```markdown
### Related Skills Found

| Skill | Version | Verification | Relevance |
|-------|---------|-------------|-----------|
| skill-name | v2.0.0 | verified-ci | Why relevant |
| skill-name | v1.0.0 | unverified | Why relevant (TREAT WITH SKEPTICISM) |

### Evolution Notes

> **skill-name** was amended from v1.0.0 → v2.0.0 on YYYY-MM-DD.
> v1.0.0 recommended using `check_gradients()` with absolute tolerance.
> v2.0.0 switched to `check_gradient()` with relative+absolute tolerance
> because absolute tolerance fails for large-magnitude gradients.
> [Full history](skills/skill-name.history)

### Key Findings

**What Worked** (high confidence):
- Verified approach 1 [verified-ci, v2.0.0]
- Verified approach 2 [verified-local, v1.0.0]

**What Worked** (low confidence — verify before using):
- Approach 3 [verified-precommit only, v1.0.0]

**What Failed** (Critical!):
- Failed approach 1: Why it failed
- Failed approach 2: Why it failed (documented in v1.0.0 → v2.0.0 amendment)

**Recommended Parameters**:
\`\`\`yaml
param1: value1
\`\`\`

**Need more detail?** Ask me to read the full SKILL.md or its .history for any skill above.
```

## Example Workflow

### Invocation

```bash
/skills-registry-commands:advise training a model with GRPO
```

### Output

```markdown
### Related Skills Found

| Skill | Version | Verification | Relevance |
|-------|---------|-------------|-----------|
| grpo-external-vllm | v2.0.0 | verified-ci | Uses external vLLM server for GRPO training |
| grpo-batch-tuning | v1.0.0 | verified-local | Optimal batch sizes for GRPO |

### Evolution Notes

> **grpo-external-vllm** was amended from v1.0.0 → v2.0.0 on 2026-02-15.
> v1.0.0 used same-GPU vLLM which caused OOM. v2.0.0 uses separate GPU.
> [Full history](skills/grpo-external-vllm.history)

### Key Findings

**What Worked** (high confidence):
- External vLLM server prevents memory issues [verified-ci, v2.0.0]
- batch_size=4 with learning_rate=1e-5 for 7B models [verified-ci]

**What Failed** (Critical!):
- vllm_skip_weight_sync errors when vLLM on same GPU (fixed in v2.0.0)
- batch_size > 8 causes OOM on 24GB GPUs
- learning_rate > 5e-5 causes training instability

**Need more detail?** Ask me to read the full SKILL.md or its .history for any skill above.
```
