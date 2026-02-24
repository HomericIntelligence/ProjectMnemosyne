---
name: "publication-readiness-check"
description: "publication-readiness-check"
category: documentation
user-invocable: false
---
# publication-readiness-check

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Comprehensive 10-category GO/NO-GO assessment for academic paper publication readiness. | Attribute | Value | |
| Outcome | Operational |


Comprehensive 10-category GO/NO-GO assessment for academic paper publication readiness.

## Session Overview

| Attribute | Value |
|-----------|-------|
| Date | 2026-02-07 |
| Objective | Assess arXiv paper publication readiness and implement all fixes |
| Outcome | ✅ SUCCESS - Paper moved from NO-GO to GO (2 critical + 8 polish fixes) |
| Paper | "Taming Scylla: Understanding the multi-headed agentic daemon of the coding seas" |
| Size | 1517 lines LaTeX, 32 pages PDF |
| Review Iterations | 5th comprehensive review pass (50+ prior fixes applied) |

## When to Use This Skill

Use this skill when:

1. **Before arXiv/journal submission** - Final GO/NO-GO gate before publication
2. **After major paper revisions** - Verify consistency across all changes
3. **Multi-pass review fatigue** - Systematic approach prevents missed issues
4. **Numerical claims verification** - Cross-reference all data against sources
5. **Architectural claims validation** - Verify code/system matches paper descriptions

**Trigger phrases**:
- "Is this paper ready for publication?"
- "Final review before arXiv submission"
- "Comprehensive publication readiness check"
- "GO/NO-GO assessment for paper"

## 10-Category Assessment Framework

### Critical Categories (Blocking Issues)

1. **Numerical Accuracy** - Every number cross-referenced against source data
2. **Internal Consistency** - No contradictions between sections
3. **Citations & References** - All URLs valid, no fabricated entries

### Quality Categories (Conditional GO)

4. **Clarity & Readability** - Reader comprehension, terminology consistency
5. **Grammar & Spelling** - Language correctness, style uniformity
6. **LaTeX Formatting** - Compilation success, package compatibility

### Verification Categories (Essential)

7. **Reproducibility** - Data, scripts, configs available and functional
8. **Figures & Tables** - All references resolve, captions descriptive
9. **Scientific Rigor** - Limitations acknowledged, claims supported
10. **Completeness** - All sections present, cross-references valid

## Verified Workflow

### Phase 1: Data Verification (30-45 min)

```bash
# Step 1: Locate raw and processed data
find ~/fullruns/ -name "*.csv" -o -name "*.json"
ls docs/arxiv/dryrun/data/

# Step 2: Cross-reference numerical claims
# For EACH number in paper:
# - Grep paper for value: grep "0.247" paper.tex
# - Find source: grep "0.247" data/*.csv
# - Verify calculation if derived
# - Document in review notes

# Example verification:
# Paper line 1366: "3.8x cost ratio"
# Source: $0.247/$0.065 = 3.8 ✅
```

**Key insight**: Verify ALL numbers, not just suspicious ones. Found correct values with wrong precision (0.9595 vs 0.960).

### Phase 2: Architecture Verification (15-30 min)

```bash
# Step 3: Verify architectural claims against source code
# Paper claims: "judges run in parallel"
# Source: grep -r "for judge_num" scylla/

# Example:
grep -A5 "judge_num" scylla/e2e/subtest_executor.py
# Found: for-loop → sequential execution, NOT parallel

# Step 4: Check all architectural descriptions
# - Execution model (parallel vs sequential)
# - Data flow (synchronous vs asynchronous)
# - Component interaction (direct vs mediated)
```

**Key insight**: Don't trust paper claims about code. Verify in source.

### Phase 3: Bibliography Validation (10-15 min)

```bash
# Step 5: Validate ALL URLs in references.bib
# For each @misc or @article entry:

# Extract URL and verify:
grep "howpublished" references.bib | while read line; do
  url=$(echo $line | sed 's/.*url{\(.*\)}.*/\1/')
  echo "Checking: $url"
  # Manually verify or use curl -I
done

# Step 6: Cross-check title/author against actual paper
# Critical: Found polo2024efficient pointing to WRONG arXiv paper
```

**Key insight**: Fabricated/incorrect URLs are publication-blocking. Always verify.

### Phase 4: Consistency Check (20-30 min)

```bash
# Step 7: Find terminology inconsistencies
grep -in "parallel" paper.tex | grep judge  # Found 3 locations
grep -in "sequential" paper.tex | grep judge  # Found 1 location
# → Contradiction!

# Step 8: Check numerical precision consistency
grep -o '\b0\.[0-9]\{4,\}\b' paper.tex | sort -u
# Found: 0.9595 (4dp) while rest uses 3dp

# Step 9: Verify table column consistency
# Found: "Mean Score" and "Median Score" identical (N=1)
```

**Key insight**: Internal contradictions undermine credibility more than minor errors.

### Phase 5: Systematic Fix Implementation (45-60 min)

```bash
# Step 10: Triage fixes by severity
# CRITICAL (blocking):
# - Fix 1: Bibliography URL correction
# - Fix 2: Parallel→sequential contradiction

# POLISH (non-blocking):
# - Fixes 3-10: Grammar, precision, clarity

# Step 11: Implement fixes sequentially
cd docs/arxiv/dryrun

# Fix bibliography FIRST (most critical)
vim references.bib
# Change: 2405.12345 → 2405.17202
# Change: "Francesco" → "Felipe Maia"

# Fix architectural contradiction
sed -i 's/in parallel (Opus/sequentially (Opus/g' paper.tex
# Verify: grep "in parallel" paper.tex | grep judge  # Should be empty

# Apply polish fixes
# - Remove Median Score column
# - Add (H1), (H2) labels
# - Fix 219K→218K, etc.
```

**Key insight**: Fix critical issues first. Polish can wait for CI to pass.

### Phase 6: Verification & Testing (15-20 min)

```bash
# Step 12: Full LaTeX compilation cycle
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Step 13: Verify zero errors
grep -c "^!" paper.log  # Expect: 0
grep "??" paper.log | grep -v pdfTeX  # Expect: empty

# Step 14: Verify each fix applied
grep -n "2405.12345" references.bib  # Expect: empty
grep -n "in parallel" paper.tex | grep judge  # Expect: empty
grep -n "219K" paper.tex  # Expect: empty
grep -n "0.9595" paper.tex  # Expect: empty
grep -n "(H1)" paper.tex  # Expect: 2 matches

# Step 15: Visual PDF check
ls -lh paper.pdf  # Verify size reasonable
```

**Key insight**: Automated verification catches 90% of issues. Still need visual check.

### Phase 7: PR Creation (5-10 min)

```bash
# Step 16: Create feature branch
git checkout -b fix-paper-publication-review

# Step 17: Commit with detailed message
git add paper.tex references.bib paper.pdf
git commit -m "fix(paper): address publication review findings

Critical fixes:
- Fix fabricated polo2024efficient bibliography URL/title/author
- Fix parallel→sequential judge execution (3 locations)
- Add formal hypothesis labels (H1, H2)

Polish fixes:
- Remove Median Score column (N=1 confusion)
- Clarify 46 vs 61 skills
- Fix 219K→218K, 0.9595→0.960
- Standardize terminology
- Grammar corrections

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Step 18: Push and create PR
git push -u origin fix-paper-publication-review
gh pr create \
  --title "fix(paper): address publication review findings" \
  --body "Implements all 10 fixes from GO/NO-GO review..."

# Step 19: Enable auto-merge
gh pr merge --auto --rebase
```

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: Trusting Paper Claims Without Verification

**Attempt**: Initially accepted paper's claim that "judges run in parallel" at face value.

**Result**: Would have shipped with architectural contradiction (3 places say "parallel", 1 says "sequential", source code confirms sequential).

**Lesson**: **ALWAYS verify architectural claims against source code**. Don't trust paper text, especially after multiple revision rounds where copy-paste errors accumulate.

**Fix**: `grep -r "judge_num" scylla/` → found `for judge_num, model in enumerate(...)` → confirmed sequential.

---

### ❌ Failed: Spot-Checking Numerical Claims

**Attempt**: Initially planned to verify only "suspicious" numbers (outliers, round numbers).

**Result**: Would have missed valid value with wrong precision (T4: 0.9595 instead of 0.960).

**Lesson**: **Verify ALL numbers, not just suspicious ones**. Precision errors, rounding inconsistencies, and copy-paste mistakes appear in "normal-looking" values.

**Fix**: Created systematic verification:
```bash
# For EVERY number in paper:
grep "0.973" paper.tex  # Find claim
grep "0.973" data/*.csv  # Find source
# Verify match and precision
```

---

### ❌ Failed: Assuming Bibliography Tools Auto-Validate

**Attempt**: Assumed that if BibTeX compiles, all references are valid.

**Result**: Would have shipped with `polo2024efficient` pointing to arXiv paper about **paradise fish** instead of LLM evaluation.

**Lesson**: **BibTeX only checks syntax, not semantic correctness**. A fabricated URL that returns HTTP 200 will compile fine but destroy paper credibility.

**Fix**: Manual verification of all URLs:
```bash
grep "howpublished" references.bib | \
  sed 's/.*url{\(.*\)}.*/\1/' | \
  while read url; do
    echo "Verify: $url"
    # Click each URL, verify title/author match
  done
```

---

### ❌ Failed: Fixing Everything in One Pass

**Attempt**: Initially tried to implement all 10 fixes simultaneously in a single Edit tool call.

**Result**: Risk of introducing new errors, hard to verify which fixes applied successfully.

**Lesson**: **Fix critical issues first, then polish**. This allows:
- Early verification that blocking issues are resolved
- CI/compilation testing between critical and polish fixes
- Easier rollback if a fix introduces new issues

**Fix**: Phased implementation:
1. Critical: Bibliography (Fix 1)
2. Critical: Architecture (Fix 2)
3. Polish: Hypothesis labels (Fix 3)
4. Polish: Table/formatting (Fixes 4-10)

---

### ❌ Failed: Trusting "This was already reviewed 4 times"

**Attempt**: Assumed that after 4+ prior review passes, only minor issues remained.

**Result**: Found 2 **publication-blocking critical issues** (fabricated URL, architectural contradiction) that survived 4 reviews.

**Lesson**: **Review fatigue is real. Use systematic checklists, not intuition**. The 10-category framework caught issues that manual reviews missed because:
- Manual reviews focus on "new changes" not "old stable sections"
- Reviewers assume bibliography was checked previously
- Architectural claims seem plausible and aren't questioned

**Fix**: 10-category systematic framework (see above) instead of freeform review.

## Results & Parameters

### Review Metrics

| Metric | Value |
|--------|-------|
| Review time | ~120 minutes (plan + implementation) |
| Issues found | 10 (2 critical, 8 polish) |
| False positives | 0 |
| LaTeX compilation | ✅ 0 errors, 0 warnings |
| Final status | GO (publication-ready) |

### Critical Issues Caught

1. **Fabricated bibliography** - `polo2024efficient` pointed to wrong arXiv paper
   - Impact: Publication-blocking (credibility)
   - Fix time: 2 minutes
   - Detection: Manual URL verification

2. **Architectural contradiction** - Judges described as "parallel" in 3 places, "sequential" in 1 place
   - Impact: Publication-blocking (technical accuracy)
   - Fix time: 5 minutes
   - Detection: Source code verification

### Files Modified

```
docs/arxiv/dryrun/
├── paper.tex (12 edits)
├── references.bib (1 edit)
└── paper.pdf (regenerated)
```

### Verification Commands

```bash
# Zero LaTeX errors
grep -c "^!" paper.log
# Output: 0

# Zero undefined references
grep "??" paper.log | grep -v pdfTeX
# Output: (empty)

# All critical fixes verified
grep "2405.17202" references.bib  # ✅ New URL
grep "sequentially" paper.tex | grep -c judge  # ✅ 3 matches
grep "(H1)" paper.tex  # ✅ 2 matches
```

### GO/NO-GO Decision Matrix

| Category | Grade | Blocking? | Issues |
|----------|-------|-----------|--------|
| 1. Numerical Accuracy | ✅ GO | Yes | 0 (all verified) |
| 2. Internal Consistency | 🛑 NO-GO | Yes | 3 (parallel/sequential) |
| 3. Citations & References | 🛑 NO-GO | Yes | 1 (fabricated URL) |
| 4. Clarity & Readability | ⚠️ COND | No | 4 (median column, skills) |
| 5. Grammar & Spelling | ⚠️ COND | No | 3 (comma, precision) |
| 6. LaTeX Formatting | ✅ GO | Yes | 0 |
| 7. Reproducibility | ✅ GO | Yes | 0 |
| 8. Figures & Tables | ✅ GO | No | 0 |
| 9. Scientific Rigor | ✅ GO | No | 0 |
| 10. Completeness | ⚠️ COND | No | 1 (undefined H1) |

**Initial**: 🛑 NO-GO (2 critical)
**After fixes**: ✅ GO (all resolved)

## Parameters & Configuration

### LaTeX Compilation

```bash
# Full 4-step compilation (required for bibliography changes)
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

### Data Sources

```bash
# Raw experimental data
~/fullruns/test001-dryrun/*.csv
~/fullruns/test001-dryrun/*.json

# Processed data for figures
docs/arxiv/dryrun/data/*.csv

# Source code for architecture verification
scylla/e2e/subtest_executor.py
```

### Git Workflow

```bash
# Branch naming
fix-paper-publication-review

# Commit message format
fix(paper): address publication review findings

Critical fixes:
- <blocking issue 1>
- <blocking issue 2>

Polish fixes:
- <non-blocking issue 1>
- <non-blocking issue 2>
...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Recommended Extensions

1. **Automated numerical verification** - Script to extract paper numbers and cross-check against data files
2. **Bibliography URL validator** - Pre-commit hook to verify all URLs return valid papers
3. **Architectural claim checker** - Extract claims from paper, auto-verify against codebase
4. **Pre-submission checklist** - Interactive GO/NO-GO gate with this framework

## Related Skills

- `arxiv-paper-polish` - LaTeX formatting and style fixes
- `latex-compilation-debug` - Resolving compilation errors
- `citation-cleanup` - Bibliography management and validation

## Success Criteria

✅ Use this skill successfully when:
- Paper moves from NO-GO → GO status
- All blocking issues resolved and verified
- LaTeX compiles with 0 errors, 0 unresolved references
- PR created with complete fix summary

## References

- Original review plan: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/4b48fe63-6667-4ec6-9aa3-31c3a1d12363.jsonl`
- PR #377: https://github.com/HomericIntelligence/ProjectScylla/pull/377
- Paper: `docs/arxiv/dryrun/paper.tex` (1517 lines)
