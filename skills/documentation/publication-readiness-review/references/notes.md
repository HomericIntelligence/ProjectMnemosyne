# Publication Readiness Review - Session Notes

## Session Context

**Date:** 2026-02-07
**Paper:** "Taming Scylla: A Measurement Study of AI Agent Architectures Under Real-World Economic Constraints"
**File:** `/home/mvillmow/ProjectScylla/docs/arxiv/dryrun/paper.tex`
**Status:** 6th+ review pass, final GO/NO-GO assessment

## Raw Session Data

### Paper Specifications

```
Lines: 1517
Pages: 32
Bibliography entries: 10
Figures: 4 (PDF format)
Tables: 9 (inline) + 1 (external via \input)
Build system: build.sh (4-pass LaTeX compilation)
```

### Data Sources Verified

1. **summary.json** - Aggregate metrics per tier
   - tier_scores: {T0: 0.973, T1: 0.970, T2: 0.983, T3: 0.983, T4: 0.9595, T5: 0.983, T6: 0.943}
   - tier_costs: {T0: 0.135, T1: 0.127, T2: 0.138, T3: 0.129, T4: 0.168, T5: 0.065, T6: 0.247}
   - total_cost: 1.0111618

2. **runs.csv** - Per-run execution data
   - Columns: tier, run_number, score, input_tokens, output_tokens, cost, duration_seconds
   - 7 tiers × 1 run each = 7 rows
   - Total duration: 1288.82 seconds

3. **statistical_results.json** - Correlation analysis
   - score_vs_impl_rate: {spearman_rho: 0.935, p_value: 0.002}
   - score_vs_token_total: {spearman_rho: -0.571, p_value: 0.180}

4. **judges.csv** - Judge evaluations
   - 21 judge evaluations (7 tiers × 3 judges)
   - Judges: Opus, Sonnet, Haiku

5. **criteria.csv** - Detailed criteria scores
   - 105 criteria scores (21 judges × 5 criteria)
   - Criteria: alignment, completeness, correctness, clarity, documentation

### Numerical Claims Verified

**Tier Scores (all match summary.json):**
- T0 (Prompts): 0.973 ✅
- T1 (Skills): 0.970 ✅
- T2 (Tooling): 0.983 ✅
- T3 (Delegation): 0.983 ✅
- T4 (Hierarchy): 0.960 ✅ (rounded from 0.9595)
- T5 (Hybrid): 0.983 ✅
- T6 (Super): 0.943 ✅

**Cost-of-Pass Values (all match summary.json):**
- T0: $0.135 ✅
- T1: $0.127 ✅
- T2: $0.138 ✅
- T3: $0.129 ✅
- T4: $0.168 ✅
- T5: $0.065 ✅ (Frontier CoP)
- T6: $0.247 ✅

**Derived Metrics:**
- Cost ratio: 3.8x = $0.247 / $0.065 ✅
- Total cost: $1.01 (summary.json: 1.0111618) ✅
- Total duration: ~1289 seconds (runs.csv sum: 1288.82) ✅

**Statistical Claims:**
- Spearman ρ=0.935, p=0.002 (score vs impl_rate) ✅
- 21 judge evaluations ✅
- 105 criteria scores ✅

**Token Counts (paper lines 1097-1109):**
Verified against runs.csv - all values match exactly.

### Internal Consistency Checks Performed

**Judge execution methodology:**
```bash
grep -n "sequential" paper.tex
# Results: Lines 670, 898 - both say "sequentially" ✅
```

**Consensus method:**
```bash
grep -n "mean\|median" paper.tex
# Results: Lines 670, 782, 923, 1194, 1307 - all say "mean" ✅
```

**Cross-reference verification:**
```bash
# All \label{} targets:
sec:related, sec:methodology, sec:architecture, sec:adapter, sec:tiered-ablation,
sec:token-analysis, sec:metrics, sec:further, sec:cost-tradeoffs, sec:judge-behavior,
fig:architecture, fig:exec-pipeline, fig:tier-deps, fig:token-dist, fig:judge-variance,
fig:judge-agreement, fig:criteria-tier, tab:software, tab:models, tab:test-suite,
tab:tier-summary, tab:token-analysis, tab:timing-analysis, tab:judge-summary,
tab:criteria-performance, eq:cop

# All \ref{} targets checked - all resolve ✅
```

### Citation Verification

**Bibliography entries (all verified):**
1. liu2023agentbench - https://arxiv.org/abs/2308.03688
2. jimenez2024swebench - https://arxiv.org/abs/2310.06770
3. yao2024taubench - https://arxiv.org/abs/2406.12952
4. zhu2024promptbench - https://arxiv.org/abs/2306.04528
5. polo2024efficient - https://arxiv.org/abs/2405.17202
6. projectodyssey - GitHub repository (commit 011a3ff)
7. anthropic2024claude - Anthropic product page
8. gao2024lmevalharness - https://arxiv.org/abs/2404.03508
9. safetynet - GitHub repository
10. ccmarketplace - Claude Code marketplace

**Citation audit:**
```bash
# All citations found in paper
grep -o '\cite{[^}]*}' paper.tex | sed 's/\\cite{//;s/}//' | sort -u
# Result: All 10 entries cited ✅

# No orphaned citations (all cited entries exist in .bib) ✅
# No missing citations (all .bib entries cited in paper) ✅
```

### LaTeX Build Results

```bash
cd docs/arxiv/dryrun && ./build.sh

[1/4] Cleaning auxiliary files...
✓ Cleaned

[2/4] Compiling LaTeX (4-step cycle)...
  Pass 1/4: pdflatex (generating aux)...
  Pass 2/4: bibtex (resolving citations)...
  Pass 3/4: pdflatex (inserting citations)...
  Pass 4/4: pdflatex (finalizing references)...
✓ Compilation successful

[3/4] Validating output...
  PDF: 505511 bytes, 32 pages
✓ Validation passed

[4/4] Creating submission tarball...
✓ Tarball created: 406524 bytes, 29 files
```

**Key metrics:**
- 0 errors ✅
- 0 unresolved references ✅
- PDF size: 505KB
- Tarball size: 406KB
- Files included: 29

### Issues Found and Fixed

#### Issue 1: Docker Reference (Line 883)

**Category:** Grammar & Spelling (Technical Accuracy)
**Grade:** CONDITIONAL GO
**Severity:** Minor (non-blocking)

**Problem:**
```latex
Container Runtime & Docker \\
```

**Context:** Paper and codebase use git worktrees for isolation, not Docker containers. This was flagged in prior reviews but persisted.

**Fix Applied:**
```latex
Isolation & Git Worktrees \\
```

**Verification:**
```bash
grep -i docker paper.tex
# Returns 0 matches ✅
```

**Commit:** 5efe544
**PR:** #380

### Scientific Rigor Verification

**N=1 Limitation Acknowledgements:**
- Line 1017: "single test case"
- Line 1191-1192: "N = 1 test case severely limits statistical power"
- Line 1303-1304: "N = 1 test case"
- Line 1322-1328: Extended discussion of N=1 impact on reliability

**Hedging Language (appropriate use):**
- Line 85: "suggests that architectural sophistication..."
- Line 1366: "data is consistent with..."
- Line 1376: "preliminary support for..."

**Ceiling Effect Acknowledged:**
- Line 1238-1243: "narrow range (.943-.983) creates ceiling effect"
- Line 1342-1345: "restricted score range limits discrimination"

**Honest Conclusions:**
- Line 1381: "no real practical takeaway yet"
- Line 1335-1336: Single model limitation acknowledged

### Reproducibility Checklist

**Referenced configuration files (all exist):**
```bash
ls config/tiers/tiers.yaml  # ✅
ls config/models/claude-opus-4-5.yaml  # ✅
ls config/models/claude-sonnet-4-5.yaml  # ✅
ls config/models/claude-haiku-4-5.yaml  # ✅
ls tests/fixtures/tests/*/test.yaml | wc -l  # 47 files ✅
```

**Data files accessible:**
```bash
ls docs/arxiv/dryrun/data/
# runs.csv ✅
# judges.csv ✅
# criteria.csv ✅
# summary.json ✅
# subtests.csv ✅
# statistical_results.json ✅
```

**Raw execution data:**
```bash
ls docs/arxiv/dryrun/raw/T*/
# T0_Prompts/ ... T6_Super/ ✅
# Each contains replay.sh for exact reproduction ✅
```

**Repository information:**
- URL: https://github.com/HomericIntelligence/ProjectScylla ✅
- Commit: Referenced in paper (011a3ff for ProjectOdyssey) ✅

### Lessons Learned

#### Why Manual Verification Beats Automation

**Attempted automated approach:**
```python
import re
import json

# Tried to extract all numbers from LaTeX
pattern = r'\b\d+\.\d+\b'
with open('paper.tex') as f:
    numbers = re.findall(pattern, f.read())

# Problem: Got 200+ matches including:
# - Section numbers (1.2, 3.4)
# - Line numbers from cat -n output
# - Page numbers from references
# - Actual data values mixed in

# Context needed to distinguish "0.973 (T0 score)" from "0.973 (line number)"
```

**Why manual was better:**
- LaTeX macros break simple regex (`\textbf{0.973}` vs `0.973`)
- Context distinguishes metric type (score vs cost vs correlation)
- Human judgment catches semantic errors regex misses
- Structured category-by-category review prevents fatigue

#### Review Order Matters

**Failed approach:** Review all 10 categories simultaneously
**Successful approach:** One category at a time, fully completed

**Why sequential worked better:**
1. Lower cognitive load per category
2. Consistent grading standards within category
3. Issues documented immediately (not deferred to end)
4. Clear progress tracking (3/10 categories complete)

#### Trust But Verify

**Assumption:** Prior 5+ reviews caught all issues
**Reality:** Docker reference still present despite prior "fixes"

**Key insight:** Each review has different scope/depth. Always verify from first principles, even after multiple passes.

### Time Breakdown

| Phase | Duration | Notes |
|-------|----------|-------|
| Setup & context gathering | 15 min | Read prior review history, locate data sources |
| Category 1-10 reviews | 2.5 hours | ~15 min per category for 32-page paper |
| Numerical verification | 45 min | Manual calculation checks against raw data |
| Fix implementation | 10 min | Single line change + verification |
| Build verification | 5 min | Run build.sh, check PDF output |
| Documentation | 30 min | PR comment, commit message |
| **Total** | **~4 hours** | For comprehensive 10-category review |

### Grading Calibration

**NO-GO threshold (critical issues):**
- Numerical claims don't match data
- LaTeX doesn't compile
- Missing citations or fabricated URLs
- Major scientific errors (incorrect methodology descriptions)

**CONDITIONAL GO threshold (non-blocking issues):**
- Minor terminology inconsistencies
- Style/formatting improvements
- Technical accuracy (Docker vs Git Worktrees)
- Build verification needed but likely to pass

**GO threshold (ready for publication):**
- All critical checks pass
- Only cosmetic or preference-based concerns remain
- Paper meets community standards for preprint/journal

### Tools & Commands Used

**Grep patterns for numerical verification:**
```bash
grep -E '\b0\.[0-9]{3}\b' paper.tex  # Find 3-decimal scores
grep -E '\$0\.[0-9]{3}\b' paper.tex  # Find cost values
grep -E 'ρ=[0-9]\.[0-9]{3}' paper.tex  # Find correlations
grep -E 'p=[0-9]\.[0-9]{3}' paper.tex  # Find p-values
```

**Internal consistency checks:**
```bash
grep -n "sequential\|parallel" paper.tex
grep -n "mean\|median" paper.tex
grep -n "T4.*subtest" paper.tex  # Check tier subtest counts
```

**Cross-reference audit:**
```bash
# Extract labels
grep -o '\\label{[^}]*}' paper.tex | sed 's/\\label{//;s/}//' | sort > labels.txt

# Extract references
grep -o '\\ref{[^}]*}' paper.tex | sed 's/\\ref{//;s/}//' | sort > refs.txt

# Find orphaned refs (cited but no label)
comm -23 refs.txt labels.txt
```

**Citation audit:**
```bash
# Extract citations from paper
grep -o '\\cite{[^}]*}' paper.tex | sed 's/\\cite{//;s/}//' | tr ',' '\n' | sort -u > cited.txt

# Extract bib keys
grep '^@' references.bib | sed 's/@[^{]*{//;s/,//' | sort > bibkeys.txt

# Find missing (cited but not in .bib)
comm -23 cited.txt bibkeys.txt

# Find orphaned (in .bib but not cited)
comm -13 cited.txt bibkeys.txt
```

**Build verification:**
```bash
cd docs/arxiv/dryrun
./build.sh

# Check output
ls -lh paper.pdf arxiv-submission.tar.gz
pdfinfo paper.pdf | grep Pages  # Should show 32
```

## Recommendations for Next Session

### Pre-Review Setup

1. **Create review workspace:**
   ```bash
   mkdir -p /tmp/paper-review
   cd /tmp/paper-review

   # Copy paper and data
   cp docs/arxiv/dryrun/paper.tex .
   cp -r docs/arxiv/dryrun/data .
   cp docs/arxiv/dryrun/references.bib .
   ```

2. **Prepare verification tools:**
   - Calculator app or Python REPL for recalculating derived metrics
   - Spreadsheet for tracking numerical claims vs data sources
   - Text editor with split view (paper.tex + data files side-by-side)

3. **Review prior history:**
   - Read previous review PR comments
   - Note categories where issues were found before
   - Check if any issues were deferred (not fixed)

### During Review

1. **Use structured checklist per category**
2. **Document issues with:**
   - Line number
   - Exact current text
   - Exact proposed fix
   - Severity (NO-GO / CONDITIONAL / cosmetic)
3. **Take breaks between categories** to maintain focus

### After Review

1. **Prioritize fixes:** NO-GO → CONDITIONAL → cosmetic
2. **Re-run full review** on critical categories after fixes applied
3. **Visual PDF review:** Read generated PDF end-to-end for flow/readability

## Future Enhancements

### Automation Opportunities

**What could be automated:**
- LaTeX build verification (already done via build.sh)
- Cross-reference checking (label/ref matching)
- Citation completeness (cited vs bib keys)
- URL accessibility checking (for bibliography)

**What should stay manual:**
- Numerical verification against data sources (requires context)
- Internal consistency of methodology descriptions
- Scientific rigor assessment (judgment calls)
- Clarity and readability evaluation

### Checklist Templates

Consider creating category-specific checklist templates:
- `checklist-numerical-accuracy.md`
- `checklist-internal-consistency.md`
- `checklist-latex-formatting.md`
- etc.

Each with specific grep commands, file locations, and acceptance criteria pre-filled.

### Integration with CI/CD

**Potential GitHub Actions workflow:**
```yaml
name: Paper Quality Check
on: [pull_request]
jobs:
  build:
    - name: LaTeX Build
      run: cd docs/arxiv/dryrun && ./build.sh
  cross-refs:
    - name: Check Cross-References
      run: ./scripts/check-refs.sh paper.tex
  citations:
    - name: Verify Citations
      run: ./scripts/check-citations.sh paper.tex references.bib
```

This would catch build failures and orphaned references automatically.
