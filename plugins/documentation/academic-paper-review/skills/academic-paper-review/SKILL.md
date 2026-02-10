---
name: "Academic Paper Review & Quality Improvement"
description: "Comprehensive academic paper review workflow: data validation, tone formalization, error correction, and reproducibility fixes"
category: documentation
date: 2026-02-05
user-invocable: false
---
# Academic Paper Review & Quality Improvement

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-05 |
| Objective | Perform comprehensive review and quality improvement of academic paper including data validation, tone formalization, and error correction |
| Outcome | ✓ Successfully improved paper quality: fixed all errors, removed contractions, marked colloquial segments, validated data accuracy |
| Context | Technical paper with N=1 dryrun results needing academic formalization |

## When to Use This Skill

Use this skill when you need to:
- **Review academic/technical papers** for publication readiness
- **Validate quantitative claims** against source data
- **Formalize informal writing** to academic standards
- **Fix reproducibility issues** (broken paths, incorrect scripts)
- **Ensure statistical rigor** in claims (appropriate language for sample sizes)

**Trigger Conditions:**
- User asks to "review the paper"
- User requests "make the tone more formal"
- Paper has mix of informal and formal language
- Quantitative claims need verification
- Appendices reference nonexistent files/scripts

## Verified Workflow

### Phase 1: Structured Analysis (Create Analysis Plan First)

**DO NOT start fixing immediately.** First, create a comprehensive analysis plan:

1. **Read the entire paper** to understand scope and structure
2. **Create systematic analysis plan** organized by severity:
   - CRITICAL: Factual errors, broken paths, incorrect data
   - IMPORTANT: Statistical language issues, inconsistencies
   - MINOR: Spelling, grammar, style
3. **Validate against source data** - Read actual data files before claiming errors
4. **Document findings** before making any changes

**Key Learning:** The analysis plan incorrectly flagged judge agreement statistics as wrong. Always verify claims by recomputing from source data first.

### Phase 2: Data Validation

**Critical:** Always verify quantitative claims against source data.

```bash
# Example: Verify judge agreement statistics
python3 << 'EOF'
import numpy as np
from scipy import stats

# Extract actual scores from result.json
opus_scores = [0.96, 0.95, 0.95, 0.96, 0.95, 0.95, 0.93]
sonnet_scores = [0.96, 0.96, 1.00, 1.00, 1.00, 1.00, 0.90]
haiku_scores = [1.00, 1.00, 1.00, 0.99, 0.9286, 1.00, 1.00]

# Compute correlations
spearman_rho, _ = stats.spearmanr(opus_scores, sonnet_scores)
pearson_r, _ = stats.pearsonr(opus_scores, sonnet_scores)
print(f"Spearman ρ = {spearman_rho:.3f}")
print(f"Pearson r = {pearson_r:.3f}")
EOF
```

**Verified Approach:**
- Extract raw data from source files (JSON, CSV)
- Recompute statistics independently
- Compare with paper's claims
- Only flag as error if values actually differ

### Phase 3: Path/Reproducibility Fixes

**Extract archived data** if references point to nonexistent directories:

```bash
# Check if archives exist
ls docs/*.tar.gz

# Extract to create referenced directory structure
tar -xzf docs/dryrun-analysis.tar.gz -C docs/
tar -xzf docs/dryrun-data.tar.gz -C docs/

# Verify extraction
ls docs/paper-dryrun/paper-dryrun/figures/*.png | wc -l
ls docs/paper-dryrun/paper-dryrun/tables/*.md
```

**Update script paths** to reference actual scripts:

```bash
# Find actual script names
ls scripts/*.py | grep -E "(run|experiment)"

# Update paper references
# Wrong: scylla/run_evaluation.py
# Right: scripts/run_e2e_experiment.py
```

### Phase 4: Tone Formalization (Two-Step Process)

**Step 1: Remove all contractions** using replace_all:

```python
contractions = {
    "don't": "do not",
    "doesn't": "does not",
    "can't": "cannot",
    "I'm": "I am",
    "it's": "it is",
    "that's": "that is",
    "there's": "there is",
    "let's": "let us",
    "we're": "we are",
    "isn't": "is not",
    "haven't": "have not",
    "I'd": "I would",
    "I'll": "I will",
    "I've": "I have",
    "here's": "here is",
    "what's": "what is",
    # ... etc
}

# Use Edit tool with replace_all=true for each
```

**Step 2: Mark colloquial segments** with tags for manual review:

Wrap informal phrases with `<coq>` tags:
- "Here's the thing" → `<coq>Here is the thing</coq>`
- "heavy hitter" → `<coq>heavy hitter</coq>`
- "nails it" → `<coq>nails it</coq>`
- "Over-engineering at its finest" → `<coq>Over-engineering at its finest</coq>`
- "eats the budget" → `<coq>eats the budget</coq>`

**Result:** User can then manually replace tagged segments with formal equivalents.

### Phase 5: Statistical Language Rigor

For small sample sizes (N=1, N=7), replace strong claims:

**Before:** "Confirmed", "This confirms the hypothesis"
**After:** "Consistent with", "Preliminary evidence supports", "The data supports this hypothesis"

**Add explicit warnings:**
```markdown
**Note**: N=7 is insufficient for reliable correlation estimates; these
values are reported for completeness but should be interpreted with extreme
caution.
```

**Remove misleading headers:**
- Table header "Mean Score (±σ)" → "Mean Score" (when N=1 has no σ)

### Phase 6: Use Task Tracking

```bash
# Create tasks for organization
TaskCreate: "Fix critical judge agreement statistics"
TaskCreate: "Fix Appendix B paths"
TaskCreate: "Fix spelling, grammar, and tone issues"

# Update as you work
TaskUpdate: taskId=1, status="in_progress"
TaskUpdate: taskId=1, status="completed", description="..."
```

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Don't: Trust analysis plan without verification

**What happened:** Analysis plan flagged judge agreement statistics as "CRITICAL: DO NOT match any generated data"

**Why it failed:** The plan compared dryrun stats (N=7) to full-run stats (N=2245+) from different experiments. They're supposed to differ.

**Correct approach:** Always recompute from source data before claiming error:
```python
# Recomputed from actual dryrun result.json:
# Opus-Sonnet: Spearman ρ = 0.333 ✓ MATCHES PAPER
# Paper was correct, analysis plan was wrong
```

**Lesson:** Verification beats assumption. Read source data first.

### ❌ Don't: Create Python scripts for simple edits

**What happened:** Started to write a Python script to find colloquial phrases

**Why it failed:** User interrupted - "don't create a script, just modify the segments directly"

**Correct approach:** Use Edit tool directly for text modifications. Scripts are overkill for simple search-and-replace.

### ❌ Don't: Start fixing before understanding scope

**What failed:** Could have started editing without creating the structured analysis plan

**Why this works:** The analysis plan provided:
- Clear severity ranking (CRITICAL vs IMPORTANT vs MINOR)
- Complete inventory of issues (22 total)
- Organized workflow (fix critical first)
- Verification checklist

**Lesson:** 15 minutes planning saves hours of rework.

## Results & Parameters

### Input

Paper state:
- 1342 lines, ~30K words
- 47+ contractions throughout
- 24 colloquial segments
- 6 spelling errors, 4 grammar errors
- Inconsistent statistical language (N=1 claiming "confirmed")
- Broken references to `docs/paper-dryrun/` (didn't exist)
- Wrong script paths in Appendix C

### Output

Improvements:
- ✓ All contractions removed (47+ replacements)
- ✓ All colloquial segments marked with `<coq>` tags (24 segments)
- ✓ All spelling errors fixed (6)
- ✓ All grammar errors fixed (4)
- ✓ Statistical language appropriate for N=1 data
- ✓ Extracted archives to create `docs/paper-dryrun/` structure
- ✓ Updated Appendix C with correct script paths
- ✓ Added N=7 sample size warnings
- ✓ Fixed T1 count inconsistency (11→10)
- ✓ Updated figure count (26→25)

### Verification Commands

```bash
# Check spelling fixes applied
grep -c "demistify\|seperated\|incase\|excercise\|statician" docs/paper.md
# Expected: 0

# Check contractions removed
grep -oE "\b[A-Za-z]+n't\b|\b[A-Za-z]+'ll\b" docs/paper.md | wc -l
# Expected: 0 (only possessives remain like "Krippendorff's")

# Check colloquial tags added
grep -o "<coq>" docs/paper.md | wc -l
# Expected: 24 (12 pairs)

# Check extracted data exists
ls docs/paper-dryrun/paper-dryrun/figures/*.png | wc -l
# Expected: 23

# Check script paths updated
grep -c "scripts/run_e2e_experiment.py" docs/paper.md
# Expected: 1+
```

## Key Success Factors

1. **Structured analysis before action** - Create severity-ranked plan first
2. **Verify data claims** - Recompute from source, don't trust analysis plan
3. **Two-phase tone improvement** - Remove contractions first, then mark colloquialisms
4. **Task tracking** - Keep user informed of progress
5. **Extracting archives** - Don't edit references, extract data to match references
6. **Statistical rigor** - Use appropriate language for sample sizes

## Common Pitfalls

1. **Trusting analysis without verification** → Always recompute from source data
2. **Creating scripts for simple edits** → Use Edit tool directly
3. **Fixing before planning** → 15 min planning saves hours
4. **Over-editing colloquialisms** → Tag first, let user decide replacements
5. **Ignoring sample size** → N=1 cannot "confirm", only "be consistent with"

## Integration with Existing Workflows

This skill complements:
- `/commit` - Commit changes with clear academic improvement message
- PR review workflows - Can be used pre-submission for self-review
- Documentation quality skills - Same principles apply to technical docs

## Related Skills

- `technical-writing-qa` - Broader than academic papers
- `data-validation` - Subset of this skill's Phase 2
- `reproducibility-check` - Subset of this skill's Phase 3
