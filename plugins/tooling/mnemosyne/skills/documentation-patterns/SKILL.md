---
name: documentation-patterns
description: Best practices for writing effective skill documentation. Use when creating new skills, improving skill discoverability, or documenting failed attempts.
user-invocable: false
---

# Skill Documentation Patterns

How to write skills that Claude can find and use effectively.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Document patterns for high-quality skill documentation |
| Outcome | Improved skill discoverability and reuse |
| Source | Sionic AI HuggingFace blog |

## When to Use

- Creating a new skill after `/retrospective`
- Improving an existing skill's discoverability
- Writing trigger conditions for `/advise` matching
- Documenting failed attempts (most valuable content)
- Making configs and parameters copy-paste ready

## Verified Workflow

### 1. Write Specific Trigger Conditions

The description field determines if `/advise` finds your skill. Be specific:

**Bad (vague):**
```
"description": "Pruning experiments"
```

**Good (specific):**
```
"description": "GRPO training with external vLLM server. Use when: (1) Running vLLM on separate GPUs, (2) Encountering vllm_skip_weight_sync errors, (3) OpenAI API parsing issues. Verified on gemma-3-12b-it."
```

Pattern: `{what} + Use when: {numbered triggers} + Verified on: {environment}`

### 2. Document Failed Attempts (Most Valuable)

Failed attempts save weeks of trial-and-error. Use this table format:

```markdown
| Attempt | Why it Failed | Lesson Learned |
|---------|---------------|----------------|
| Running vLLM without --served-model-name | 404 Model 'default' not found | Must add --served-model-name default |
| Execution without vllm_skip_weight_sync | 404 /update_flattened_params/ error | Mandatory flag when using vllm serve |
```

### 3. Use Concrete Numbers, Not Vague Advice

**Bad:**
```
Use a small learning rate
```

**Good:**
```
RoPE theta=100 works well for short sequences. d_proj=64+ prevents information loss. ksim=4 optimal with 16-bucket token distribution.
```

### 3.5. Include Environment Details in Overview

Add environment context for reproducibility:

```markdown
## Overview

| Item | Details |
|------|---------|
| Date | YYYY-MM-DD |
| Objective | [What was the goal] |
| Outcome | [What happened] |
| Hardware | NVIDIA A100-SXM4-80GB |
| Software | PyTorch 2.0.1, CUDA 11.8 |
| Dataset | 100K train / 10K eval |
| Runtime | 24 GPU hours |
| Source | [Blog/paper/issue link] |
```

**Why**: Reproducibility requires environment context. "Works on A100-80GB" might fail on V100-16GB due to memory constraints.

### 4. Make Configs Copy-Paste Ready

```yaml
# GRPO Training Config (Ready to copy-paste)
rlhf_type: grpo
use_vllm: true
vllm_mode: server
vllm_skip_weight_sync: true  # Mandatory when using standard vllm serve
tensor_parallel_size: 2
gpu_memory_utilization: 0.9
dtype: bfloat16
```

### 5. Include Error-to-Solution Mappings

Use this structured format for documenting errors:

```markdown
## Error: [Error Title/Message]

**Symptom**: [What the user sees/experiences]
**Cause**: [Root cause explanation]
**Solution**: [Step-by-step fix]
**Prevention**: [How to avoid in future]
**Related Errors**: [Links to similar issues]
```

**Example:**

```markdown
## Error: RuntimeError - RoPE freqs dimension mismatch

**Symptom**:
```
RuntimeError: The size of tensor a (32) must match the size of tensor b (16)
at non-singleton dimension 3
```

**Cause**: Standard RoPE implementations output freqs with shape `[seq_len, head_dim/2]`, but attention layer expects `[seq_len, head_dim]` for broadcasting.

**Solution**:
```python
# In apply_rotary_pos_emb function
freqs = torch.cat((freqs, freqs), dim=-1)  # Duplicate to match head dimension
freqs = freqs.unsqueeze(0).unsqueeze(0)    # Add batch and head dims [1, 1, seq, dim]
```

**Prevention**:
- Always verify RoPE freqs shape before attention computation
- Add assertion: `assert freqs.shape[-1] == head_dim`

**Related Errors**:
- Attention mask broadcasting errors
- Position embedding shape mismatches
```
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Vague descriptions like "ML training" | Claude can't match to user queries | Include numbered trigger conditions |
| Optional failures section | Teams skip it, lose most valuable info | Make failures REQUIRED in validation |
| Pseudo-code in documentation | Users can't copy-paste directly | Always use real, tested commands |
| Missing environment details | Works on my machine problems | Include versions, hardware specs |
| Long prose explanations | Hard to scan quickly | Use tables and bullet points |

## Results & Parameters

```yaml
# Skill quality checklist
required_sections:
  - "When to Use"           # Trigger conditions
  - "Verified Workflow"     # What worked
  - "Failed Attempts"       # What didn't (most valuable)
  - "Results & Parameters"  # Copy-paste configs

description_pattern: "{what} + Use when: {numbered triggers} + Verified on: {env}"

# Anti-patterns to avoid
avoid:
  - Vague trigger conditions
  - Optional failures section
  - Pseudo-code instead of real commands
  - Missing version/environment info
  - Prose-heavy explanations

# Metrics that matter
skill_quality_indicators:
  - Times surfaced by /advise
  - Times referenced in subsequent experiments
  - Copy-paste success rate
```

## Cultural Notes

From the Sionic AI blog:

1. **Frictionless contribution**: `/retrospective` takes 30 seconds; Claude writes it
2. **Reward specificity**: Skills with precise descriptions get surfaced, reused, cited
3. **Celebrate failures**: "I tried X and it broke because Y" is the most valuable content
4. **Timing matters**: Capture knowledge while fresh (end-of-session, not two weeks later)

## References

- Source blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Template gist: https://gist.github.com/sigridjineth/2f0ef5d1d56e884a84f1580de21db597
