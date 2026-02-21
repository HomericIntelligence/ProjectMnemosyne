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

### Phase 1: Search and Present Initial Findings

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
3. **Read the marketplace.json** file to find available plugins
4. **Search matching plugins** by:
   - Description keywords
   - Tags (if present)
   - Category (if specified)
5. **Read relevant SKILL.md files** for matches
6. **Present initial findings** with:
   - What worked (verified approaches)
   - What failed (critical - prevents wasted effort)
   - Recommended parameters (copy-paste ready)

### Phase 2: Structured Interview

After presenting initial findings, conduct a structured interview to refine recommendations:

1. **Batch questions by topic** (3-4 questions per batch):
   - **Batch 1: Context & Constraints**
     - What are your specific constraints? (time, resources, dependencies)
     - What environment are you working in? (local, cloud, specific tools)
     - Are there any non-negotiable requirements?

   - **Batch 2: Prior Attempts**
     - Have you tried any approaches already? What happened?
     - What didn't work and why?
     - What partial solutions do you have?

   - **Batch 3: Preferred Approach**
     - Which approach from the findings resonates most?
     - What tradeoffs are acceptable to you?
     - Do you prefer speed, robustness, or simplicity?

   - **Batch 4: Success Criteria**
     - How will you know this worked?
     - What metrics or outputs validate success?
     - What's your next step after this?

2. **Use AskUserQuestion tool** for each batch:
   - Present 3-4 related questions together
   - Provide clear options where applicable
   - Allow custom responses via "Other" option
   - Record user's decisions

3. **Interview best practices**:
   - Don't ask all questions at once (overwhelming)
   - Reference specific skills/findings in questions
   - Propose 2-3 solutions per question where applicable
   - Keep questions non-obvious and in-depth

### Phase 3: Refine and Document

1. **Synthesize interview results** into decisions table
2. **Refine recommendations** based on user's specific context
3. **Create actionable next steps** tailored to their answers

## Output Format

### Phase 1 Output (Before Interview)

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

### Phase 3 Output (After Interview)

```markdown
### Interview Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Specific constraints? | [User's answer] | [Why this matters] |
| Prior attempts? | [What they tried] | [How this informs approach] |
| Preferred approach? | [User's preference] | [Tradeoffs accepted] |
| Success criteria? | [User's validation] | [How to measure] |

### Refined Recommendations

Based on your context, here's the tailored approach:

1. **Recommended Approach**: [Specific approach from findings + user preferences]
   - Why: [Matches their constraints and preferences]
   - Tradeoffs: [What they're accepting vs avoiding]

2. **Specific Parameters**:
   \`\`\`yaml
   # Customized for your environment
   param1: value1  # Based on: [user context]
   param2: value2  # Avoiding: [what failed for them/others]
   \`\`\`

3. **Critical Warnings**:
   - Avoid: [What failed that matches their context]
   - Watch for: [Known gotchas relevant to their setup]

### Next Steps

1. [Immediate first action based on their next step]
2. [Second action]
3. [Validation step based on their success criteria]
```

## Interview Best Practices

Based on **plan-review-interview** skill (evaluation category):

### What Works

1. **Batch 3-4 related questions per topic** - Manageable, focused conversations
2. **Reference specific findings** - "The skill X mentions Y failed. Have you encountered this?"
3. **Propose 2-3 solutions per question** - Helps users make informed decisions
4. **Document decisions immediately** - Don't wait, capture as you go
5. **Keep questions non-obvious** - Go deeper than surface-level clarifications

### What to Avoid

| Anti-Pattern | Why It Fails | Solution |
|--------------|--------------|----------|
| Ask all questions at once | Overwhelming; decisions not linked to context | Batch by topic (max 4 questions) |
| Generic questions without references | Hard to trace which decisions affect which recommendations | Reference specific skills/findings |
| Skip decision documentation | Decisions get lost; can't track reasoning | Create decisions table immediately |
| Obvious/surface questions | Wastes time; doesn't add value | Ask about tradeoffs, concerns, edge cases |

## Example Workflow

### Invocation

```bash
/skills-registry-commands:advise training a model with GRPO
```

### Phase 1: Initial Search Output

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
```

### Phase 2: Interview Questions (Example Batch)

**Batch 1: Context & Constraints**

1. What GPU setup do you have? (Single GPU, Multi-GPU, Cloud)
2. What model size are you training? (1B, 7B, 13B+)
3. Any memory constraints we should know about?

**Batch 2: Prior Attempts**

1. Have you tried GRPO training before? What happened?
2. Did you encounter vllm_skip_weight_sync errors?
3. What batch sizes have you tested?

### Phase 3: Refined Output

```markdown
### Interview Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| GPU setup? | Single RTX 4090 (24GB) | Memory-constrained, need careful batching |
| Prior attempts? | vllm_skip_weight_sync errors | Confirms need for separate vLLM setup |
| Preferred approach? | External vLLM server | Willing to trade setup complexity for stability |

### Refined Recommendations

Based on your RTX 4090 setup and prior errors:

1. **Recommended Approach**: External vLLM server on separate GPU/process
   - Why: Prevents vllm_skip_weight_sync errors you encountered
   - Tradeoffs: More setup complexity, but much more stable

2. **Specific Parameters**:
   \`\`\`yaml
   # Optimized for RTX 4090 24GB
   batch_size: 4          # Based on: 24GB memory limit
   learning_rate: 1e-5    # Avoiding: instability from higher LR
   vllm_server: "localhost:8000"  # Separate process
   \`\`\`

3. **Critical Warnings**:
   - Avoid: Running vLLM on same GPU (causes your skip_weight_sync error)
   - Watch for: OOM if batch_size > 4 on 24GB GPU

### Next Steps

1. Start external vLLM server: `python -m vllm.entrypoints.openai.api_server --model <model>`
2. Configure GRPO with batch_size=4, learning_rate=1e-5
3. Monitor for OOM; reduce batch_size to 2 if needed
```
