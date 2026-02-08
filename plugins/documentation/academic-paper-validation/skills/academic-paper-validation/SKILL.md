---
name: "Academic Paper Validation"
description: "Systematic workflow for validating and improving academic paper quality through data accuracy checks, statistical rigor improvements, and noise reduction"
category: documentation
date: 2026-02-06
user-invocable: false
---
# Academic Paper Validation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-06 |
| **Objective** | Validate and improve academic paper quality through systematic data accuracy checks, statistical rigor improvements, and noise reduction |
| **Outcome** | Successfully fixed 2 data errors, 2 typos, improved 12+ statistical claims, added proper cross-references, removed 3 degenerate figures |
| **Context** | LaTeX academic paper (paper.tex) describing ProjectScylla evaluation framework with N=1 dryrun results |

## When to Use This Skill

Use this workflow when:

- Preparing an academic paper for submission or publication
- Reviewing a paper that presents experimental results with small sample sizes
- Validating quantitative claims against source data
- Improving statistical rigor and hedging language
- Cleaning up redundant content and low-value visualizations
- Fixing LaTeX cross-references and formatting issues

**Trigger phrases**: "validate the paper", "check paper accuracy", "review paper for errors", "improve paper quality", "prepare paper for submission"

## Verified Workflow

### Phase 1: Data Accuracy (CRITICAL - Do First)

**Objective**: Cross-reference every quantitative claim against source data

**Steps**:
1. Identify all numeric claims in the paper (counts, percentages, ratios, costs)
2. Locate the source data files or analysis outputs
3. Verify each claim by recalculating from raw data
4. Document discrepancies in a table: Location | Current | Ground Truth | Fix
5. Apply fixes using Edit tool with exact string matching

**Example fixes**:
- Figure/table counts: "25 figures and 10 tables" → "24 figures and 10 tables" (counted PDFs)
- Percentages: "80-99%" → "79-95%" (recalculated from actual data)
- Typos: "what it is means" → "what it means"

**Critical**: Fix data errors FIRST before any other changes, as these affect credibility.

### Phase 2: Statistical Language (HIGH Priority)

**Objective**: Adjust language strength to match statistical power (N=1 requires hedging)

**Pattern matching**:
- "confirms" → "is consistent with" / "supports" / "suggests"
- "proves" → "showing" / "indicating"
- "demonstrates" → "suggesting" (when making causal claims)
- Keep "validates" when referring to methodology/pipeline validation (appropriate use)

**Steps**:
1. Search for strong causal language: `grep -n "confirms\|proves\|demonstrates\|validates" paper.tex`
2. For each instance, assess context:
   - Is this a causal claim about results? → Hedge it
   - Is this about methodology/pipeline? → Keep it (validating design ≠ proving results)
3. Replace with hedged alternatives while maintaining conversational tone
4. Verify paper still acknowledges N=1 limitations in dedicated section

**Key principle**: Hedge results, not methodology. N=1 validates the framework works, not that findings generalize.

### Phase 3: Cross-Reference Infrastructure (HIGH Priority)

**Objective**: Replace hardcoded section numbers with LaTeX auto-references

**Steps**:
1. Add `\label{}` to all `\section`, `\subsection`, `\subsubsection` commands
   ```latex
   \section{Introduction}\label{sec:intro}
   \subsection{Cost Analysis}\label{sec:cost-tradeoffs}
   ```

2. Find all hardcoded references:
   ```bash
   grep -n "section [0-9]\|Section [0-9]\|Section~[0-9]" paper.tex
   ```

3. Replace with `\ref{}`:
   - "Section 4" → "Section~\ref{sec:methodology}"
   - "section 3" → "Section~\ref{sec:related}"

4. Remove manual numbering from subsection titles:
   - "Table 4.1:" → no prefix (LaTeX auto-numbers)
   - "\subsubsection{4.2.1 Title}" → "\subsubsection{Title}"

5. Compile twice and verify: `grep "??" paper.log` should return 0

### Phase 4: Redundancy Reduction (MEDIUM Priority)

**Objective**: Reduce repetitive claims while maintaining key results

**Strategy**:
1. Identify repeated numeric claims (e.g., "3.8x" mentioned 6 times)
2. Keep claims in 3 key locations:
   - Abstract/Introduction (first mention)
   - Results section (primary data presentation)
   - Conclusions (final summary)
3. For middle sections, replace with back-references:
   - "3.8x higher" → "significantly higher"
   - "218K vs 113K tokens" → "see Section~\ref{sec:token-analysis} for details"

**Example pattern**:
- 6 mentions of "3.8x" → Reduce to 3 (intro, results, conclusions)
- 4 mentions of token chasm → Reduce to 2 (token analysis section + 1 back-reference)

### Phase 5: LaTeX Formatting (MEDIUM Priority)

**Common issues**:

1. **Markdown in LaTeX**:
   - `**bold**` → `\textbf{bold}`
   - `- list item` → `\begin{itemize}\item list item\end{itemize}`

2. **Appendix structure**:
   - Move `\appendix` command BEFORE appendix content
   - Change `\subsection{Appendix A}` → `\section{Title}` (LaTeX auto-letters them)

3. **Verify**:
   ```bash
   grep "\*\*" paper.tex  # Should find none
   grep "^- " paper.tex   # Should find none
   ```

### Phase 6: Low-Value Content Removal (LOWER Priority)

**Identify degenerate content** (shows zero variance or adds no insight):

For N=1 experiments:
- Box plots with no variance (all values identical)
- Bootstrap confidence intervals that collapse to points
- Histograms with single bins

**Steps**:
1. Review all figures in appendix
2. For each, ask: "Does this show meaningful variance or provide insight?"
3. Remove degenerate figures by deleting entire `\begin{figure}...\end{figure}` blocks
4. Trim verbose captions that repeat body text (keep 1-2 descriptive sentences)

**Example removals**:
- `fig16_success_variance_by_test` (all zeros for N=1)
- `fig24_score_histograms` (single-bin histograms)
- `fig25_impl_rate_by_tier` (bootstrap CIs collapse to points)

### Verification Checklist

After all changes:

```bash
cd docs/
# Compile twice to resolve references
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Check for errors
grep -c "??" paper.log      # Should be 0 (no unresolved refs)
grep -c "^!" paper.log       # Should be 0 (no LaTeX errors)

# Spot-check key fixes
grep -n "24 figures and 10 tables" paper.tex  # Verify counts
grep -n "79--95" paper.tex                     # Verify percentages
grep -n "Section~\\ref{" paper.tex | head     # Verify cross-refs work

# Verify PDF
ls -lh paper.pdf  # Should exist and be reasonable size
```

## Failed Approaches

### ❌ Attempting to fix all issues in parallel

**What happened**: Initially tried to make multiple types of edits simultaneously (data fixes + language improvements + formatting), which made it hard to track which changes addressed which issues.

**Why it failed**: Without a clear phase structure, it's easy to miss critical data errors or apply inconsistent patterns.

**Solution**: Work through phases sequentially. Data accuracy MUST come first because it affects credibility. Then statistical language, then cross-references, then cleanup.

### ❌ Using `replace_all=true` for statistical language

**What happened**: Tried using `replace_all=true` to replace all instances of "confirms" at once.

**Why it failed**: Some uses of "confirms" are appropriate (e.g., "confirms the ceiling effect" in methodology context) while others need hedging (results claims). Blanket replacement breaks appropriate uses.

**Solution**: Manually review each instance in context and decide whether to hedge. Use `replace_all=false` (default) and provide enough surrounding context to make each replacement unique.

### ❌ Removing "validates" from all contexts

**What happened**: Initial plan was to replace "validates" along with "confirms/proves/demonstrates".

**Why it failed**: "Validates" is appropriate when discussing methodology validation (N=1 validates that pipeline works) versus results generalization (N=1 doesn't validate findings generalize). Removing it everywhere weakened appropriate claims.

**Solution**: Keep "validates" for pipeline/methodology/design validation. Only hedge when making causal claims about results or generalizing findings.

## Results & Parameters

### Input Parameters

- **Source file**: `docs/paper.tex` (LaTeX academic paper, 1561 lines)
- **Source data**: `~/fullruns/test001-dryrun/` (raw experimental data)
- **Tool**: Edit tool for precise string replacement
- **Sample size**: N=1 (key constraint requiring hedged language)

### Output Metrics

- **Data errors fixed**: 2 (figure/table counts, cache percentages)
- **Typos fixed**: 2
- **Statistical language improvements**: 12+ instances
- **Cross-references added**: 11 section labels + 9 reference conversions
- **Redundancy reductions**: ~8 instances
- **LaTeX formatting fixes**: ~4 markdown-to-LaTeX conversions + appendix restructure
- **Figures removed**: 3 degenerate figures
- **Final PDF**: 32 pages, 5.3 MB, 0 errors, 0 unresolved references
- **Net change**: 73 insertions, 91 deletions (-18 lines, improved quality)

### Key Commands

```bash
# Data validation
cd ~/fullruns/test001-dryrun/
python -c "import pandas as pd; df = pd.read_csv('runs.csv'); print(df['cache_read_tokens'].sum() / df['total_tokens'].sum())"

# Search patterns
grep -n "confirms\|proves\|demonstrates" docs/paper.tex
grep -n "section [0-9]" docs/paper.tex
grep -n "Table [0-9]:" docs/paper.tex

# Compilation
cd docs/
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex  # Second pass resolves refs

# Verification
grep -c "??" paper.log
grep -c "^!" paper.log
```

### Configuration Files

No configuration files required. Uses standard LaTeX packages:
- `hyperref` (for cross-references)
- `graphicx` (for figures)
- Standard article class

## Failed Attempts

| Approach | Why It Failed | What We Learned |
|----------|---------------|-----------------|
| Skipping data validation | Found 2 data errors during later review that had to be fixed last-minute | Always validate quantitative claims against source data FIRST |
| Using strong causal language ("proves", "confirms") with N=1 | Reviewer feedback noted overclaiming from small sample | Hedge results appropriately - N=1 validates methodology, not generalizability |
| Manual section numbering | Section reordering broke all references | Use LaTeX `\label{}` and `\ref{}` for automatic cross-referencing |

## Related Skills

- `latex-compilation` - Compiling LaTeX documents with proper error checking
- `statistical-rigor` - Applying appropriate statistical language for sample sizes
- `code-review` - Systematic review patterns applicable to paper review
- `cross-referencing` - LaTeX label and reference management

## Tags

`academic-writing`, `latex`, `paper-review`, `data-validation`, `statistical-rigor`, `n=1`, `quality-assurance`, `documentation`
