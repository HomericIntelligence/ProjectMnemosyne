# Academic Paper Validation - Detailed Notes

## Session Context

**Date**: 2026-02-06
**Branch**: `review-paper`
**Commit**: `2b3bfe1` - docs(paper): fix data accuracy, improve rigor, and reduce noise

## Ground Truth Data

### Figure/Table Counts
- **Source**: `~/fullruns/test001-dryrun/` analysis pipeline outputs
- **PDFs generated**: 24 (counted in `figures/` directory)
- **LaTeX tables**: 10 files (tab01-tab10.tex, note tab06 is 0 bytes but still counts)
- **Original claims**: "25 figures and 10 tables" (line 1139), "26 figures and 9 tables" (line 1402)
- **Corrected to**: "24 figures and 10 tables" (both locations)

### Cache Read Token Percentages
- **Source data**: `runs.csv` from dryrun
- **Actual values by tier**:
  - T0: 82.6%
  - T1: 79.3%
  - T2: 82.5%
  - T3: 79.3%
  - T4: 79.1%
  - T5: 95.4% (outlier!)
  - T6: 82.9%
- **Range**: 79-95% (full), 79-83% (excluding T5 outlier)
- **Original claim**: "80-99%" (line 960 caption), "~79-83%" (line 964 body)
- **Corrected to**: "79-95%" with outlier notation

## All Edits Made

### Data Accuracy Fixes (Phase 1)
1. Line 1139: Figure count from 25→24
2. Line 1402: Figure/table count "26 figures and 9 tables" → "24 figures and 10 tables"
3. Line 960 (caption): Cache % "80-99%" → "79-95%"
4. Line 964 (body): Added outlier notation "(79--83% excluding T5's 95% outlier)"
5. Line 99: Typo "what it is means" → "what it means"
6. Line 442: Typo "combine then together" → "combine them together"

### Statistical Language (Phase 2)
1. Line 960 caption: "confirming" → "consistent with"
2. Line 964 body: "confirming" → "showing"
3. Line 1104: "confirm" → "suggest"
4. Line 1111: "confirming" → "indicating"
5. Line 1087: Added "This supports the multi-judge consensus design"
6. Line 1255: "proving" → "showing"
7. Line 1257: "confirmed" → "data is consistent with"
8. Line 1268: "hints of being confirmed" → "preliminary support"
9. Line 1457: "confirms" → "is consistent with"
10. Line 1465: "visually confirms" → "visually illustrates"
11. Line 1521: "confirms" → "suggests"
12. Line 82 (abstract): "demonstrating" → "suggesting"

### Cross-References (Phase 3)
Added labels:
- `\label{sec:intro}` (line 61)
- `\label{sec:related}` (line 130)
- `\label{sec:methodology}` (line 183)
- `\label{sec:tiered-ablation}` (line 406)
- `\label{sec:dimensions}` (line 449)
- `\label{sec:metrics}` (line 560)
- `\label{sec:results}` (line 875)
- `\label{sec:token-analysis}` (line 953)
- `\label{sec:discussion}` (line 1113)
- `\label{sec:cost-tradeoffs}` (line 1143)
- `\label{sec:judge-behavior}` (line 1176)

Fixed references:
- Line 103-104: "section 3" → `\ref{sec:related}`, "section 4" → `\ref{sec:methodology}`
- Line 991: "Section 4" → `\ref{sec:tiered-ablation}`
- Line 1124: "Section 4" → `\ref{sec:methodology}`
- Line 1164: "Section 4" → `\ref{sec:tiered-ablation}`
- Multiple figure captions updated with proper section refs

Removed manual numbering:
- "Table 4.1:", "Table 4.2:", "Table 4.3:" → no prefix
- "Table 1:", "Table 2:", "Table 3:" → no prefix
- "\subsubsection{4.2.1 ...}" → "\subsubsection{...}"
- "\subsubsection{4.2.2 ...}" → "\subsubsection{...}"
- "\subsubsection{4.2.3 ...}" → "\subsubsection{...}"
- "\subsubsection{4.2.4 ...}" → "\subsubsection{...}"

### Redundancy Reduction (Phase 4)
1. Line 933 caption: Removed "3.8x higher at $0.247" from caption
2. Line 947: Removed "3.8x Frontier CoP" from cost ranking
3. Line 1152: Removed "or 3.8x Frontier CoP" parenthetical
4. Line 1261: "3.8x cheaper" → "significantly cheaper"
5. Line 960 caption: Removed specific token numbers, kept concept
6. Lines 1164-1165: Replaced detailed token comparison with back-ref to Section~\ref{sec:token-analysis}

### LaTeX Formatting (Phase 5)
1. Lines 1408-1425: Converted Markdown to LaTeX:
   - `**bold**` → `\textbf{bold}`
   - `- list` → `\begin{itemize}\item list\end{itemize}`
2. Moved `\appendix` command from line 1449 to line 1320 (before appendix content)
3. Changed appendix subsections to sections:
   - `\subsection{Appendix A: ...}` → `\section{...}`
   - `\subsection{Appendix B: ...}` → `\section{...}`
   - `\subsection{Appendix C: ...}` → `\section{...}`

### Content Cleanup (Phase 6)
Removed figures:
1. `fig16_success_variance_by_test` (lines 1490-1495) - all zeros for N=1
2. `fig24_score_histograms` (lines 1536-1541) - single-bin histograms
3. `fig25_impl_rate_by_tier` (lines 1544-1549) - bootstrap CIs collapse to points

Trimmed captions:
1. Line 1529 (fig22): Removed "cost amplification effect" claim
2. Line 1555 (fig26): Shortened to 1-2 sentences

## Compilation Results

### Before fixes
- Warnings: Multiple unresolved references
- Manual section numbers incorrect
- Inconsistent data claims

### After fixes
```bash
pdflatex -interaction=nonstopmode paper.tex  # First pass
pdflatex -interaction=nonstopmode paper.tex  # Second pass resolves refs

# Verification
grep -c "??" paper.log   # Output: 0 (no unresolved refs)
grep -c "^!" paper.log   # Output: 0 (no errors)

# Output
paper.pdf: 32 pages, 5.3 MB
```

## Key Learnings

### 1. Data Accuracy Must Come First
Cross-referencing quantitative claims against source data revealed 2 critical errors that would have undermined credibility. These MUST be fixed before any other improvements.

### 2. Context Matters for Statistical Language
Not all "confirms" or "validates" should be hedged. Methodology validation (N=1 confirms pipeline works) is different from results generalization (N=1 suggests findings may generalize). Review each instance in context.

### 3. Systematic Phase Approach Works
Working through 6 distinct phases (accuracy → language → cross-refs → redundancy → formatting → cleanup) prevented missing issues and ensured consistent application of fixes.

### 4. LaTeX Compilation is Verification
Compiling twice and checking for `??` and `!` in the log file is the ultimate test. All fixes must pass this test.

### 5. N=1 Requires Special Handling
Papers presenting N=1 pilot results need careful hedging while still maintaining readable, conversational tone. The pattern is: acknowledge limitations explicitly in one section, then use hedged language throughout.

## Related Files

- Source paper: `/home/mvillmow/ProjectScylla/docs/paper.tex`
- Source data: `~/fullruns/test001-dryrun/`
- Compiled PDF: `/home/mvillmow/ProjectScylla/docs/paper.pdf`
- Plan document: Available in session transcript

## Statistics

- Total edits: 50+ individual Edit tool invocations
- Lines changed: 73 insertions, 91 deletions (net -18 lines)
- Figures removed: 3
- Cross-references added: 11 labels + 9+ reference conversions
- Statistical language improvements: 12+
- Data errors fixed: 2 critical, 2 typos
- Compilation: Success, 0 errors, 0 unresolved refs
