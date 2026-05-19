---
name: academic-paper-validation-and-publication
description: "Canonical workflow for academic paper validation and publication readiness: data accuracy checks, iterative accuracy review, peer-review prep, LaTeX section-adding patterns, paper-readiness epic management. Use when: (1) preparing a manuscript for submission, (2) running an iterative-accuracy review pass, (3) adding architecture/methodology sections to a LaTeX paper, (4) managing a paper-readiness epic with sub-tasks."
category: documentation
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: academic-paper-validation-and-publication.history
tags: [merged, academic, paper, latex, publication, validation]
---
# Academic Paper Validation and Publication

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidated workflow for validating, revising, and publishing academic papers |
| **Outcome** | Merged from 7 skills covering full paper lifecycle |
| **Scope** | Data validation, iterative accuracy review, LaTeX editing, TikZ diagrams, arXiv submission |

## When to Use

Use this skill when:

1. **Preparing a manuscript for submission** — final data accuracy pass, LaTeX build, arXiv tarball
2. **Running an iterative accuracy review** — second-pass after prior fix round, catching regressions
3. **Adding architecture/methodology sections** — TikZ diagrams, cross-references, section structure
4. **Managing a paper-readiness epic** — multi-issue dependency planning, systematic branch workflow
5. **Consolidating scattered LaTeX files** — migrating to `docs/arxiv/<name>/` structure
6. **Validating all numerical claims** — cross-referencing paper against `summary.json`, `runs.csv`, `judges.csv`

**Do NOT use for:**
- Initial paper drafting
- Simple proofreading without data validation
- Papers without quantitative claims

## Verified Workflow

### Phase 0: Epic Planning (multi-issue readiness)

When managing a paper-readiness epic with dependent sub-issues:

```markdown
| Priority | Issue | Effort | Dependencies |
|----------|-------|--------|--------------|
| P0       | #NNN  | Small  | None         |
| P1       | #NNN  | Medium | None         |
| P2       | #NNN  | Large  | P1 (fixtures) |
```

**Key insight**: Identify independent issues first (can run in parallel); note which issues require
expanded fixtures or data from earlier issues.

For each issue use the systematic branch workflow:

```bash
git checkout main && git pull origin main
git checkout -b <issue-number>-<description>
# implement + tests
pre-commit run --files <modified-files>
git add <files> && git commit -m "type(scope): description"
git push -u origin <branch-name>
gh pr create --title "..." --body "Refs \#<number>"
gh pr merge --auto --squash
```

### Phase 1: Data Cross-Validation

**Identify all numerical claims:**

```bash
grep -E '[0-9]+\.[0-9]+' paper.tex   # Decimal numbers
grep -E '\$[0-9]+\.[0-9]+' paper.tex # Dollar amounts
grep -E '[0-9]+%' paper.tex          # Percentages
```

**Locate source data files** (adapt paths to project):

```bash
# Typical layout:
data/summary.json             # Aggregate tier metrics
data/runs.csv                 # Per-run execution data
data/statistical_results.json # Correlation/p-value results
data/judges.csv               # Judge evaluations
data/criteria.csv             # Criteria scores
```

**Read data sources in parallel before making any edits** — front-loading verification catches
all errors upfront instead of incrementally.

Create a verification table:

```
| Claim | Source File | Actual Value | Status |
|-------|-------------|--------------|--------|
| T5 CoP = $0.065 | summary.json:49 | 0.06531415 | ✓ |
```

**Precision standards:**
- Scores: 3 decimal places (0.973)
- Costs: 3 decimal places ($0.135)
- Correlations: 3 decimal places (ρ=0.935)
- Percentages: integer (78%)

### Phase 2: Identify Systematic Issues

```bash
# Methodology consistency
grep -i "median\|mean\|average" paper.tex
grep -n "sequentially\|parallel\|concurrent" paper.tex

# Terminology consistency
grep -i "categories\|criteria" paper.tex

# Effect-size labels (must match paper's own threshold table)
grep -n "negligible\|small\|medium\|large" paper.tex | head -20
grep -n "medium-large\|small-medium" paper.tex  # Non-standard composites = errors

# Cross-references
grep '\\ref{' paper.tex
```

**Romano et al. (2006) hard boundaries** — no composite labels:

| Label | δ range |
| ------- | --------- |
| negligible | < 0.11 |
| small | 0.11–0.27 |
| medium | 0.28–0.42 |
| large | ≥ 0.43 |

### Phase 3: Implement Fixes Atomically

**Always `Read` immediately before `Edit`** — exact string matching is required.

```python
# Read the section first
Read(file_path="/path/to/paper.tex", offset=430, limit=15)
# Then edit with copy-pasted exact text
Edit(file_path="...", old_string="<paste exact text>", new_string="corrected text")
```

- Apply one fix at a time for dependent edits
- For independent edits (different sections), parallel calls work
- Use `replace_all=True` only for simple terminology standardization
- Verify compilation after each major change group

```bash
cd <paper-directory>
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex  # Second pass resolves cross-refs
grep "^!" paper.log   # Should return 0
grep "??" paper.log   # Should return 0
```

### Phase 4: Iterative Accuracy Review (second pass)

After a first round of fixes, verify no new inconsistencies were introduced:

```bash
# Confirm prior fix values are gone
grep "old_value" paper.tex  # Should be 0 matches

# Check for internal contradictions:
# Summary section written early vs. analysis section written later
grep -n "test-021\|partial\|early stages" paper.tex
```

**Patterns to catch on second pass:**
- Summary description diverged from detailed analysis section
- Effect-size label uses composite term (e.g., "medium-large") — use hard boundary
- Table columns lack scope (mean/total/best) — add to caption
- Counter-intuitive metric combos (e.g., Best Score = 0.00 with 40% pass rate) — add explanatory sentence
- Cache read pricing footnote when cache% ≥ 90% and paper quotes base rates

**Cache read footnote template:**

```latex
Agent pricing & \$3/\$15 per M tokens & \$1/\$5 per M tokens\footnote{Cache read tokens
are priced at \$0.10/M (10\% of input price). Since 97\% of tokens in our
experiments are cache reads, the effective per-token cost is significantly lower.} \\
```

### Phase 5: 10-Category GO/NO-GO Assessment

Evaluate before final submission:

| \# | Category | What to Check |
| --- | ---------- | --------------- |
| 1 | **Numerical Accuracy** | All claims match raw data sources |
| 2 | **Internal Consistency** | Terminology, methodology, cross-refs |
| 3 | **Clarity & Readability** | Logical flow, jargon defined |
| 4 | **Grammar & Spelling** | Typos, style consistency |
| 5 | **LaTeX Formatting** | Clean compile, resolved refs, escaping |
| 6 | **Citations & References** | Complete entries, URLs verified |
| 7 | **Reproducibility** | Configs exist, data accessible |
| 8 | **Figures & Tables** | Captions, cross-refs, format |
| 9 | **Scientific Rigor** | Limitations, hedging, hypotheses |
| 10 | **Completeness** | All sections, appendices, acknowledgements |

**Grade definitions:**
- ✅ GO — no blocking issues
- ⚠️ CONDITIONAL GO — minor non-blocking issues
- ❌ NO-GO — must fix before publication

**Decision:** Any NO-GO grade → overall NO-GO. All GO → overall GO. Mix → CONDITIONAL GO.

**Citation completeness check:**

```bash
grep -o '\\cite{[^}]*}' paper.tex | sed 's/\\cite{//;s/}//' | tr ',' '\n' | sort -u > cited.txt
grep '^@' references.bib | sed 's/@[^{]*{//;s/,//' | sort > bibitems.txt
comm -23 cited.txt bibitems.txt  # Missing from .bib
comm -13 cited.txt bibitems.txt  # Orphaned .bib entries
```

### Phase 6: LaTeX Structure — Adding Architecture Sections

**Add TikZ imports after hyperref:**

```latex
\usepackage{tikz}
\usetikzlibrary{positioning, arrows.meta, shapes.geometric, fit, backgrounds}
```

**CRITICAL — font commands after `\\` in nodes must use braces:**

```latex
% WRONG — causes "missing \item" error
\node[component] (n) at (0,0) {Label \\ \tiny (subtitle)};

% CORRECT
\node[component, align=center] (n) at (0,0) {Label \\ {\tiny (subtitle)}};
```

**Prefer stacked block diagrams over complex DAGs:**

```latex
\begin{tikzpicture}[
  layer/.style={draw, rectangle, rounded corners, minimum width=10cm,
    minimum height=1.2cm, text centered, font=\small, align=center},
  arrow/.style={-Stealth, thick}
]
\node[layer, fill=blue!10] (runner) at (0,0)
  {\textbf{E2E Runner} \\ {\scriptsize Experiment Orchestration}};
\node[layer, fill=blue!10, below=0.4cm of runner] (workspace)
  {\textbf{Workspace Manager} \\ {\scriptsize Git Worktrees}};
\draw[arrow] (runner.south) -- (workspace.north);
\end{tikzpicture}
```

**Fix long path overflow with itemize:**

```latex
% BEFORE (overflows margin)
injects files (CLAUDE.md from config/tiers/TN/subtest-NN/CLAUDE.md, ...)

% AFTER
injects tier-specific configuration files:
\begin{itemize}
\item CLAUDE.md from \texttt{config/tiers/TN/subtest-NN/CLAUDE.md}
\item Skills from \texttt{config/tiers/TN/subtest-NN/.claude-plugin/skills}
\end{itemize}
```

### Phase 7: Directory Consolidation for arXiv

When consolidating scattered paper files:

```bash
mkdir -p docs/arxiv/<name>/{figures,tables,data,raw,archives}

# Use git mv to preserve history
git mv docs/paper.tex docs/arxiv/<name>/paper.tex
git mv docs/references.bib docs/arxiv/<name>/references.bib
git mv docs/paper-dryrun/figures/* docs/arxiv/<name>/figures/
git mv docs/paper-dryrun/tables/* docs/arxiv/<name>/tables/
git mv docs/paper-dryrun/data/* docs/arxiv/<name>/data/
```

**Internal path updates required:**

| Pattern | Old Value | New Value |
| --------- | ----------- | ----------- |
| `\graphicspath{}` | `{{paper-dryrun/}}` | `{{./}}` |
| `\input{}` | `{paper-dryrun/tables/...}` | `{tables/...}` |

**arXiv directives (REQUIRED):**

```latex
\documentclass[11pt]{article}
\pdfoutput=1 % Required by arXiv
```

**arXiv tarball verification:**

```bash
cd docs/arxiv/<name> && ./build.sh
# Expect: Compilation successful, validation passed, tarball created
```

### Quick Reference

| Task | Command |
|------|---------|
| Find all decimal numbers | `grep -E '[0-9]+\.[0-9]+' paper.tex` |
| Find unresolved refs | `grep "??" paper.log` |
| Find LaTeX errors | `grep "^!" paper.log` |
| Check effect-size labels | `grep -n "medium-large\|small-medium" paper.tex` |
| Two-pass compile | `pdflatex paper.tex && pdflatex paper.tex` |
| Verify old value gone | `grep "old_text" paper.tex \| wc -l` |
| Find orphaned cite refs | `comm -23 cited.txt bibitems.txt` |
| Check methodology terms | `grep -n "median\|mean\|average" paper.tex` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit without reading first | Applied multi-line Edit using recalled text | Exact string (incl. whitespace) didn't match; "String to replace not found" | Always `Read` with `offset`/`limit` immediately before `Edit`; copy-paste from output |
| Guessing data file paths | Used `docs/paper-dryrun/data/` based on paper references | Actual files were in project root | Use `find . -name "filename.csv"` to locate data files |
| Trusting prior review passes | Skipped deep checks after "4+ review passes already" | Found 2 publication-blocking issues (fabricated URL, architectural contradiction) | Use systematic 10-category framework every time |
| Spot-checking only "suspicious" numbers | Planned to verify only outlier/round numbers | Missed valid-looking value with wrong precision (T4: 0.9595 instead of 0.960) | Verify ALL numerical claims, not just suspicious ones |
| Batch editing multiple sections at once | Applied multiple edits in parallel on same file | Earlier edits shifted line numbers; later edits failed with cascade errors | For dependent edits (same file), apply sequentially |
| Complex DAG TikZ layout | Multi-column DAG with different box widths and diagonal arrows | Boxes misaligned; hard to follow data flow | Prefer uniform-width stacked block diagrams |
| TikZ bare font command after `\\` | `\node{Label \\ \tiny (sub)}` | LaTeX "missing \item" error | Wrap font commands in braces: `{\tiny (sub)}` |
| Assuming bibliography tools validate URLs | BibTeX compiled with fabricated arXiv URL | URL returned HTTP 200 but pointed to wrong paper | Manual verification of all bibliography URLs required |
| Replace-all for effect-size labels | `replace_all=true` on "medium" | Broke correct "medium" labels (δ=0.313) | Target specific δ value context, not just the label string |
| Assuming `cd` persists across Bash calls | `cd docs && bibtex paper` in separate call | Each Bash invocation resets working directory | Chain commands with `&&` or use absolute paths |

## Results & Parameters

### Statistical Test Configs (copy-paste ready)

```yaml
bootstrap:
  n_resamples: 10000
  random_state: 42
  confidence_level: 0.95
  method: "BCa"

power_analysis:
  n_simulations: 10000
  random_state: 42
  adequate_power_threshold: 0.80

statistical:
  alpha: 0.05
  min_samples:
    bootstrap_ci: 2
    mann_whitney: 2
    normality_test: 3
    kruskal_wallis: 2
```

### TikZ Style Templates (copy-paste ready)

```latex
% Stacked layer diagram
layer/.style={draw, rectangle, rounded corners, minimum width=10cm,
  minimum height=1.2cm, text centered, font=\small, align=center}

% Horizontal flow diagram
block/.style={draw, rectangle, rounded corners, text width=2.5cm,
  minimum height=1.5cm, text centered, font=\small, align=center}

% Dependency graph node
tier/.style={draw, rectangle, rounded corners, minimum width=1.2cm,
  minimum height=0.8cm, text centered, font=\small}
```

### Paper Validation Checklist

```markdown
## Paper Validation Checklist

### Phase 1: Data Cross-Validation
- [ ] Extract all numerical claims from paper
- [ ] Locate source data files (JSON, CSV, logs)
- [ ] Verify tier scores match summary.json
- [ ] Verify token counts match run data
- [ ] Verify timing values match logs
- [ ] Verify derived metrics (ratios, percentages)
- [ ] Verify statistical claims (correlations, p-values)

### Phase 2: Methodology Consistency
- [ ] Check statistical method descriptions (median vs mean)
- [ ] Verify terminology matches implementation
- [ ] Check category/criteria lists match rubrics
- [ ] Verify model IDs and version numbers
- [ ] Check cross-references (Section/Figure/Table refs)
- [ ] Check effect-size labels use paper's own threshold table (no composites)

### Phase 3: Grammar & Formatting
- [ ] Run spell check
- [ ] Check subject-verb agreement
- [ ] Verify LaTeX syntax correct
- [ ] Check for TODO/FIXME/XXX markers

### Phase 4: Final Verification
- [ ] Compile LaTeX (pdflatex + bibtex + pdflatex ×2)
- [ ] Check for unresolved references (??)
- [ ] Review PDF page count
- [ ] Git diff review
- [ ] Pre-commit hooks pass
- [ ] Commit with detailed message
```

### Tone Conversion Examples (Academic → Conversational)

```
Before: **Observation**: T6 (everything enabled) is the most expensive...
After:  Here's the kicker: T6 costs the most despite scoring the lowest...

Before: **Haiku is the easy grader**: Awards S grades in 5/7 tiers...
After:  Haiku hands out S grades like candy—5 out of 7 tiers got perfect scores.
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Paper-readiness epic \#330 (6 issues), paper revision PR \#335 | [history](academic-paper-validation-and-publication.history) |
| ProjectScylla | Paper validation workflow 2026-02-07, publication readiness review | [history](academic-paper-validation-and-publication.history) |
| ProjectScylla | Iterative accuracy review branch 1048-haiku-analysis-paper | [history](academic-paper-validation-and-publication.history) |
