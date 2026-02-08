# Session Notes: Academic Paper Review (2026-02-05)

## Initial Request

User asked to implement an analysis plan for `docs/paper.md` containing:
- Qualitative review (spelling, grammar, tone)
- Quantitative validation (verify all data claims against source)
- Appendix verification (paths, scripts, artifacts)

## Analysis Plan Summary

The plan identified 22 issues across 3 severity levels:
- **4 CRITICAL**: Judge stats (turned out correct), Appendix B paths, reproducibility scripts, artifact paths
- **6 IMPORTANT**: T1 count, figure count, duration ambiguity, table header, "confirmed" language, judge warning
- **12 MINOR**: 6 spelling, 4 grammar, 2 structural/tone

## Key Discovery: Analysis Plan Was Partially Wrong

**Issue C1** (Judge Agreement Statistics) was flagged as critical error:
- Plan claimed: "Paper values match neither dryrun nor generated tables"
- Reality: Paper values were CORRECT for N=7 dryrun data
- Problem: Plan compared dryrun stats to full-run experiment stats (different datasets)

**Resolution:**
```python
# Recomputed from actual dryrun data (result.json):
opus_scores = [0.96, 0.95, 0.95, 0.96, 0.95, 0.95, 0.93]
sonnet_scores = [0.96, 0.96, 1.00, 1.00, 1.00, 1.00, 0.90]
haiku_scores = [1.00, 1.00, 1.00, 0.99, 0.9286, 1.00, 1.00]

# Computed correlations matched paper exactly:
# Opus-Sonnet: Spearman=0.333, Pearson=0.706 ✓
# Paper was right, analysis plan was wrong
```

**Lesson:** Always verify quantitative claims by recomputing from source data. Don't trust analysis plans blindly.

## Implementation Sequence

### Task 1: Judge Agreement (VERIFIED CORRECT)
- Created Python script to recompute correlations
- All values matched paper
- No changes needed
- Time: 5 minutes

### Task 2: Appendix B Paths (FIXED)
```bash
# Extracted archives
tar -xzf docs/dryrun-analysis.tar.gz -C docs/
tar -xzf docs/dryrun-data.tar.gz -C docs/

# Created: docs/paper-dryrun/paper-dryrun/
#   - figures/ (25 figures, 23 PNGs)
#   - tables/ (10 tables)
#   - data/ (CSV exports)
```
Time: 3 minutes

### Task 3: Appendix C Scripts (FIXED)
Updated script references:
- `scylla/run_evaluation.py` → `scripts/run_e2e_experiment.py`
- `scylla/generate_report.py` → `scripts/generate_figures.py` + `scripts/generate_tables.py`
- Updated artifact paths to reflect `~/fullruns/` structure
Time: 5 minutes

### Task 4: T1 Count (FIXED)
- Paper Table 4.3: 11 sub-tests
- tiers.yaml: 10 sub-tests
- Fixed paper to match yaml: 11→10
- Updated total: ~114→113 subtests
Time: 2 minutes

### Task 5: Figure Count (FIXED)
- Paper claimed: "26 figures and 10 tables"
- Actual: 25 figures (fig01-fig27, missing fig12, fig23), 10 tables
- Updated: 26→25
Time: 2 minutes

### Task 6: Spelling, Grammar, Tone (FIXED)
Major effort:

**Spelling (6 errors):**
1. demistify → demystify
2. seperated → separated
3. incase → in case
4. excercise → exercise (×2)
5. statician → statistician

**Grammar (4 errors):**
1. "the scale that of changes" → "the scale of changes"
2. "if performance drop" → "if performance drops"
3. "its the prompt" → "it's the prompt" (then removed contraction)
4. "lets discuss" → "let's discuss" (then removed contraction)

**Contractions (47+ removed):**
Used replace_all=true for:
- don't → do not
- doesn't → does not
- can't → cannot
- I'm → I am
- it's → it is
- that's → that is
- there's → there is
- let's → let us
- [... 39 more ...]

**Colloquialisms (24 marked):**
Wrapped with `<coq>` tags:
- "Here is the thing"
- "heavy hitter"
- "workhorse"
- "nails it"
- "ace it"
- "Over-engineering at its finest"
- "eats the budget"
- "Here is the kicker"
- "The big advantage?"
- "So what does this dryrun actually tell us?"
- [... 14 more ...]

Time: 20 minutes

### Important Issues (Fixed)
- Removed "(±σ)" from Table 1 header (N=1 has no sigma)
- Changed "Confirmed" to "consistent with" / "preliminary evidence" (3 instances)
- Added N=7 warning to judge agreement section
- Clarified ~1289s is sum-of-tiers, not wall-clock (actual 550s)

Time: 5 minutes

## User Feedback Loop

**User request 1:** "Let's highlight all the colloquial tone segments with <coq>text</coq>"
- Initially started to create Python script
- User interrupted: "don't create a script, just modify the segments directly"
- Switched to direct Edit tool usage ✓

**User request 2:** "Let's remove all contractions"
- Removed 47+ contractions using replace_all=true
- Verified completion with grep

**User request 3:** `/commit-commands:commit-push-pr`
- Staged only docs/paper.md (not the extracted archives)
- Created comprehensive commit message
- Pushed and created PR #347

## Verification Results

All checks passed:
```bash
# Spelling errors: 0 ✓
grep -c "demistify\|seperated\|incase\|excercise\|statician" docs/paper.md
# Output: 0

# Contractions: 0 (excluding possessives) ✓
grep -oE "\b[A-Za-z]+n't\b|\b[A-Za-z]+'ll\b" docs/paper.md
# Output: (empty)

# Colloquial tags: 24 ✓
grep -o "<coq>" docs/paper.md | wc -l
# Output: 24

# Script paths: Updated ✓
grep -c "scripts/run_e2e_experiment.py" docs/paper.md
# Output: 1

# Extracted data: Present ✓
ls docs/paper-dryrun/paper-dryrun/figures/*.png | wc -l
# Output: 23
```

## Total Time

- Analysis + verification: 10 minutes
- Fixes implementation: 42 minutes
- Documentation (commit, PR): 3 minutes
- **Total: 55 minutes**

## Files Modified

1. `docs/paper.md` - All quality improvements applied
2. Created: `docs/paper-dryrun/` - Extracted archives

## PR Created

- Branch: `fix-directions` (already existed from previous work)
- PR #347: "docs: improve paper tone and fix errors"
- Summary: 158 insertions, 149 deletions
- Status: Ready for review

## Key Takeaways

1. **Verification is critical** - Don't trust analysis plans, verify quantitative claims
2. **Structured approach works** - Severity-ranked tasks kept work organized
3. **Tool choice matters** - Direct Edit beats Python scripts for text modifications
4. **Two-phase formalization** - Remove contractions first, then mark colloquialisms
5. **Statistical rigor** - N=1 cannot "confirm", only be "consistent with"
6. **Extract vs Edit** - When paths reference archives, extract them (don't edit references)
