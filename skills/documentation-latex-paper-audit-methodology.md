---
name: documentation-latex-paper-audit-methodology
description: "Perform a multi-pass audit of a LaTeX academic paper covering data consistency, cross-references, scientific rigor, and writing quality. Use when: (1) a LaTeX paper needs pre-submission quality verification, (2) you need to verify every hardcoded number against source data, (3) you need to check all \\ref/\\cite/\\input chains for broken references, (4) you need to find orphaned or unincluded table/figure files, (5) you want parallel agent-based audit for speed on large papers, (6) you need to verify scientific claims match the statistical evidence, (7) you need to catch ceiling effects, power analysis gaps, or unreliable score interpretations."
category: documentation
date: 2026-04-26
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: [latex, audit, paper, academic, cross-reference, citation, data-consistency, parallel-agents, scientific-rigor, writing-quality]
---

# LaTeX Paper Strict Audit Methodology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-26 |
| **Objective** | Perform a multi-pass audit of a LaTeX academic paper covering data consistency, cross-references, scientific rigor, and writing quality using parallel agent exploration |
| **Outcome** | Successful -- Pass 1 caught a dangling `\ref{tab:criteria_performance}`, two missing Related Work citations, and hardcoded numbers without table refs. Pass 2 identified ceiling effect confounds, missing power analysis for null results, SRH test validity caveats, figure caption inaccuracies, logical tensions between Results and Conclusions, and score reliability paradoxes. Pass 3 flagged unusual citations, redundant sections, undefined terminology, and confusing qualifiers. |
| **Verification** | verified-local |

## When to Use

- A LaTeX paper is being prepared for submission and needs a final strict audit
- The paper references external data files (CSV, JSON) and you need to verify every hardcoded number matches its source
- The paper uses `\input{}` for tables/figures and you need to verify the inclusion chain is complete
- You suspect orphaned files (tables or figures that exist on disk but are never referenced)
- You want to run the audit quickly using parallel exploration agents
- A previous round of `academic-paper-validation` has been completed and you need a final cross-reference and data consistency pass
- The paper reports null results and you need to check for adequate power analysis caveats
- Metrics cluster near ceiling/floor and the paper needs to acknowledge restricted range
- Inter-rater reliability is poor and subsequent sections interpret scores without caveats

**Trigger phrases**: "strict paper audit", "verify paper references", "check paper data consistency", "audit LaTeX cross-references", "pre-submission paper check", "deep scientific review", "check paper rigor", "writing quality audit"

**Complementary skills**:
- `academic-paper-validation` -- covers statistical methodology, hedging language, and pipeline-first fixes
- `citation-verification-arxiv-abstract-fetch` -- covers primary-source citation verification via arXiv
- `latex-paper-parallel-assembly` -- covers assembling papers from parallel agent parts

## Verified Workflow

### Quick Reference

```bash
# 1. Find all data files
find docs/arxiv/<paper>/ -name "*.csv" -o -name "*.json" | sort

# 2. Check for unresolved references in compiled PDF
grep -c "LaTeX Warning.*undefined" paper.log

# 3. Find all \input commands and verify targets exist
grep -oP '\\input\{[^}]+\}' paper.tex | sort

# 4. Find all \ref targets and verify \label definitions
grep -oP '\\ref\{[^}]+\}' paper.tex | sort -u
grep -oP '\\label\{[^}]+\}' paper.tex tables/*.tex figures/*.tex | sort -u

# 5. Search for TODO/FIXME/placeholder text
grep -rn "TODO\|FIXME\|XXX\|PLACEHOLDER\|TBD" paper.tex tables/ figures/
```

### Phase 0: Parallel Agent Audit Strategy

Deploy 3 parallel Explore agents for maximum coverage:

| Agent | Responsibility | What to Check |
| ------- | --------------- | --------------- |
| **Agent A: Data Consistency** | Read all data files (CSV, JSON, summary.json) and verify every hardcoded number in the paper text against its source | Numbers in text, tables, abstract, conclusions |
| **Agent B: Figure/Table Audit** | Audit all figures and tables for orphans (files on disk not referenced) and missing files (referenced but not on disk) | `\includegraphics`, `\input`, file system listing |
| **Agent C: LaTeX Cross-References** | Check all `\ref`, `\cite`, `\input` chains for completeness and correctness | `\label` definitions, `\ref` usage, `.bib` entries, `\input` targets |

### Phase 1: Data Consistency Verification (Agent A)

**Objective**: Verify every hardcoded number in the paper against its data source.

**Critical principle**: Check in BOTH directions:
1. **Paper to data**: Every number in the paper text has a matching value in a data file
2. **Data to paper**: Important results in data files are actually reported in the paper

**Steps**:

1. Read all data source files:
   ```bash
   # Typical data files for a Scylla paper
   cat data/summary.json
   cat data/statistical_results.json
   cat data/criteria.csv
   cat data/runs.csv
   cat data/subtests.csv
   ```

2. Extract all hardcoded numbers from paper text:
   ```bash
   # Find lines with percentages, dollar amounts, counts
   grep -nP '\d+\.\d+%|\$\d+\.\d+|\d+ (subtests|runs|tiers|judges|criteria)' paper.tex
   ```

3. Cross-check each number against its source. Common locations:
   - Abstract numbers -> `summary.json` or `statistical_results.json`
   - Table values -> corresponding CSV files
   - Cost figures -> `fig08_cost_quality_pareto.csv` or cost analysis tables
   - Token counts -> `runs.csv` aggregates

4. Flag any number that cannot be traced to a data source.

5. Flag any number where the paper value diverges from the data value.

### Phase 2: Figure and Table File Audit (Agent B)

**Objective**: Ensure every figure/table file is both referenced AND included.

**Steps**:

1. List all figure and table files on disk:
   ```bash
   ls figures/*.png figures/*.pdf figures/*.vl.json 2>/dev/null | wc -l
   ls tables/*.tex tables/*.md 2>/dev/null | wc -l
   ```

2. Extract all `\includegraphics` and `\input` references from paper.tex:
   ```bash
   grep -oP '\\includegraphics(\[[^\]]*\])?\{[^}]+\}' paper.tex
   grep -oP '\\input\{[^}]+\}' paper.tex
   ```

3. Cross-reference the two lists:
   - **Missing files**: Referenced in .tex but not on disk (build will fail)
   - **Orphaned files**: On disk but never referenced (not errors, but worth flagging)
   - **Unincluded files**: `.tex` file exists on disk AND has a `\label{}` that is `\ref{}`-ed in paper.tex, BUT the file is never `\input{}`-ed

4. Check .tex/.md table pairs match:
   ```bash
   # Every .tex table should have a matching .md
   for f in tables/*.tex; do
     md="${f%.tex}.md"
     [ -f "$md" ] || echo "MISSING MD: $md"
   done
   ```

### Phase 3: LaTeX Cross-Reference Chain Audit (Agent C)

**Objective**: Verify all `\ref`, `\cite`, `\input` chains are complete.

**This is the most critical phase.** The key insight is that checking label existence alone is insufficient -- you must also verify the file containing the label is actually `\input`-ed.

#### 3a. Verify \ref -> \label -> \input chain

```bash
# 1. Collect all \ref targets
grep -oP '\\ref\{([^}]+)\}' paper.tex | sort -u > /tmp/refs.txt

# 2. Collect all \label definitions across ALL .tex files
grep -rnP '\\label\{([^}]+)\}' paper.tex tables/*.tex > /tmp/labels.txt

# 3. Collect all \input targets
grep -oP '\\input\{([^}]+)\}' paper.tex | sort -u > /tmp/inputs.txt

# 4. For each \ref, verify:
#    a) A \label exists (in any .tex file)
#    b) The file containing that \label is \input-ed by paper.tex
#    Both conditions must be true, or the reference renders as "??"
```

**Common failure mode**: A table file like `tables/tab04_criteria_performance.tex` contains `\label{tab:criteria_performance}`, and `paper.tex` uses `\ref{tab:criteria_performance}`, but `paper.tex` never has `\input{tables/tab04_criteria_performance}`. The label exists on disk but is invisible to the LaTeX compiler. The PDF shows "??" instead of a table number.

#### 3b. Verify \cite -> .bib entries

```bash
# 1. Collect all \cite keys
grep -oP '\\cite[tp]?\{([^}]+)\}' paper.tex | tr ',' '\n' | sort -u > /tmp/cites.txt

# 2. Collect all @article/@inproceedings/etc. keys from .bib
grep -oP '@\w+\{([^,]+),' references.bib | sort -u > /tmp/bibkeys.txt

# 3. Find citations without bib entries
comm -23 /tmp/cites.txt /tmp/bibkeys.txt
```

#### 3c. Verify \begin/\end environment pairs

```bash
# Check that every \begin{env} has a matching \end{env}
grep -oP '\\begin\{([^}]+)\}' paper.tex | sort | uniq -c > /tmp/begins.txt
grep -oP '\\end\{([^}]+)\}' paper.tex | sort | uniq -c > /tmp/ends.txt
diff /tmp/begins.txt /tmp/ends.txt
```

#### 3d. Search for unsupported claims

```bash
# Find claims that should have citations but don't
# Look for patterns like "studies show" or "research has demonstrated" without \cite
grep -nP '(studies (show|have|demonstrate)|research (has|demonstrates|shows)|literature (suggests|shows)|prior work)' paper.tex | grep -v '\\cite'
```

For claims lacking citations, use web search to find supporting papers. Common sources:
- IJCAI, AAAI, NeurIPS, ICML proceedings for multi-agent system surveys
- ACL, EMNLP for LLM evaluation methodology
- arXiv preprints for recent agent framework papers

#### 3e. Search for placeholder text

```bash
grep -rnP 'TODO|FIXME|XXX|PLACEHOLDER|TBD|\?\?' paper.tex tables/*.tex
```

### Phase 4: Compile and Verify

```bash
# Compile twice to resolve all references
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Check for unresolved references (should be 0)
grep -c "LaTeX Warning.*undefined" paper.log
grep "??" paper.log

# Check for errors (should be 0)
grep "^!" paper.log
```

### Phase 5: Cross-Check Compiled PDF

When possible, read the compiled PDF and compare rendered output against LaTeX source:
- Table numbers render correctly (not "??")
- Figure numbers render correctly
- Citations render as author-year or numbered (not "[?]")
- No obviously broken formatting

### Phase 6: Deep Scientific Review (Pass 2)

**Objective**: Verify that scientific claims, statistical methodology, and interpretations are sound.

This phase requires reading the paper holistically -- not just checking references, but evaluating whether the conclusions follow from the evidence.

#### 6a. Ceiling/Floor Effect Detection

When all metrics cluster near their maximum or minimum (e.g., pass rates 0.903--1.000), explicitly name "ceiling effect" as a confound in the Limitations section. Null results (non-significant differences between conditions) may reflect restricted range rather than true equivalence.

**What to check**:
- Read the Results section and note the range of key metrics
- If the range is < 10% of the scale, flag as potential ceiling/floor effect
- Verify the Limitations section acknowledges this if present

#### 6b. Power Analysis for Null Results

Studies whose central finding is a null result (no significant difference between tiers/conditions) MUST acknowledge the absence of formal power analysis or include one. Reviewers will flag this omission.

**What to check**:
- Identify all non-significant statistical tests in the Results
- If non-significance is interpreted as "equivalence" or "no difference" in Discussion/Conclusions, flag it
- Verify Limitations mentions sample size adequacy or power analysis

#### 6c. Statistical Test Validity Caveats

Certain statistical tests have known limitations that must be acknowledged:
- **Scheirer-Ray-Hare (SRH) interaction test**: Has debated validity (Sawilowsky 1990). Always add a caveat when reporting SRH results.
- **Multiple comparisons**: Check if p-value corrections (Bonferroni, Holm, etc.) are applied when many tests are run.

#### 6d. Figure Caption vs. Content Accuracy

Check that figure captions accurately describe the figure content:
- "Faceted by X" claims must match the actual figure structure (e.g., a single-model study cannot meaningfully "facet by model" -- it produces one panel)
- Axis labels in captions must match actual axis labels in the figure
- When possible, cross-check Vega-Lite `.vl.json` specs against caption descriptions

#### 6e. Logical Tension Detection

Check whether the Discussion/Conclusions make claims stronger than the Results support:
- If pass rate is non-significant but score IS significant, claiming "tiers are equivalent" is an overstatement
- If some metrics show significant differences and others do not, the Discussion must acknowledge this nuance
- Flag any instance where "no significant difference" in one metric is generalized to a blanket equivalence claim

#### 6f. Score Reliability Paradox

If inter-rater reliability is poor (e.g., Krippendorff's alpha < 0.667), flag any subsequent sections that analyze or interpret those scores without adequate caveats. Poor reliability means score-based analyses may not be meaningful.

**What to check**:
- Find the inter-rater reliability section and note the alpha/kappa values
- If reliability is below standard thresholds, trace forward to every section that uses those scores
- Verify each such section includes a reliability caveat

### Phase 7: Writing Quality Audit (Pass 3)

**Objective**: Catch writing issues that weaken the paper's clarity and credibility.

#### 7a. Citation Quality Check

Flag non-academic or unusual citations in a scientific paper:
- Negotiation books, self-help references, blog posts in formal methodology sections
- Replace with standard measurement theory, statistics, or domain-specific references
- Verify that all citations are appropriate for the context in which they appear

#### 7b. Redundancy Detection

Look for sections that repeat the same idea in different words:
- Compare the Abstract, Introduction summary, Results summary, and Conclusions
- Each should add new information, not just rephrase the same finding
- Condense repeated statements to a single clear formulation

#### 7c. Terminology Consistency

Check that coined or specialized terms are defined on first use:
- Scan for terms in quotes or italics that lack parenthetical definitions
- Terms like "budget frontier model", "cost-of-pass", or study-specific terminology must be defined before use
- Verify consistent usage throughout (no switching between synonyms)

#### 7d. Qualifier Clarity

Simplify sentences with unclear parenthetical qualifiers:
- Flag sentences where parenthetical asides add ambiguity rather than precision
- Check that qualifiers like "broadly", "generally", "in most cases" are supported by the data
- Remove or clarify hedging language that weakens otherwise supported claims

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Check \label existence only | Verified that `\label{tab:criteria_performance}` existed in `tables/tab04_criteria_performance.tex` | The file was never `\input`-ed in paper.tex, so the label was invisible to LaTeX -- PDF showed "??" | Must verify the FULL chain: `\ref` -> `\label` -> file is `\input`-ed. Label existence on disk is necessary but not sufficient. |
| Single-agent sequential audit | One agent reading paper.tex top-to-bottom checking everything | Too slow for large papers (100+ pages); missed cross-cutting issues | Use 3 parallel agents with distinct responsibilities: data, files, cross-references |
| Check claims by reading paper only | Assumed Related Work citations were complete because the text read well | Two claims ("studies have shown coordination overhead" and "multi-agent system surveys") had no `\cite` | Systematically grep for claim patterns without adjacent `\cite` commands |
| Trust hardcoded numbers | Accepted token distribution numbers in the text without checking | Numbers were correct but had no table reference for readers to verify | Every hardcoded number should either reference a table/figure or be trivially derivable |
| Single-pass review | Tried to catch everything (data, references, scientific rigor, writing) in one pass | First pass caught data/reference issues but missed scientific rigor problems entirely | Use at least 2 passes: structural (refs, data) then content (logic, methodology). A third pass for writing quality is recommended. |
| Trusting "monotonic" claims | Initially simplified a sentence about capability-gap monotonicity without checking the data | The simplification could mask a data interpretation issue (e.g., Sonnet-Haiku disagrees more than Opus-Haiku despite smaller capability gap) | Always verify mathematical/statistical claims against the actual numbers before editing |

## Results & Parameters

### Configuration

```yaml
# Audit scope for a typical Scylla paper
paper_root: docs/arxiv/<paper>/
paper_file: paper.tex
bib_file: references.bib
data_dir: data/
tables_dir: tables/
figures_dir: figures/

# Parallel agent count (per pass)
audit_agents: 3

# Number of review passes
review_passes: 3  # Pass 1: structural, Pass 2: scientific, Pass 3: writing

# Severity levels for findings
severity_levels:
  - critical    # Broken references (renders as "??"), incorrect data
  - important   # Missing citations, orphaned includes
  - minor       # Orphaned files, style inconsistencies
```

### Expected Output

A findings report organized by severity:

- **CRITICAL**: Broken `\ref` chains, numbers that disagree with data sources, missing `\input` for labeled files, conclusions contradicting results
- **IMPORTANT**: Claims without citations, hardcoded numbers without table references, `.tex`/`.md` pair mismatches, ceiling effects unacknowledged, null results without power analysis caveat, unreliable scores analyzed without caveats
- **MINOR**: Orphaned files on disk, TODO/FIXME remnants, environment pair mismatches, unusual citations, redundant sections, undefined terminology, unclear qualifiers

### Checklist Summary

```markdown
## Strict Audit Checklist

### Pass 1: Structural (Data, References, Files)
- [ ] Every hardcoded number in text traced to a data source
- [ ] Data-to-paper direction checked (important results not omitted)
- [ ] Every \ref has a \label in a file that is \input-ed
- [ ] Every \cite has a matching .bib entry
- [ ] Every \begin{env} has a matching \end{env}
- [ ] No TODO/FIXME/PLACEHOLDER text remains
- [ ] No claims without citations in Related Work / Introduction
- [ ] .tex/.md table pairs are consistent
- [ ] No orphaned \input files (exist on disk, never included)
- [ ] Compiled PDF has 0 "??" references
- [ ] Compiled PDF has 0 "[?]" citations

### Pass 2: Scientific Rigor
- [ ] Ceiling/floor effects acknowledged in Limitations if metrics cluster near bounds
- [ ] Null results accompanied by power analysis caveat
- [ ] SRH test results include validity caveat (Sawilowsky 1990)
- [ ] Figure captions match actual figure content (no misleading "faceted by X")
- [ ] Discussion/Conclusions claims do not overstate Results
- [ ] Score-based analyses caveat poor inter-rater reliability if alpha < 0.667

### Pass 3: Writing Quality
- [ ] All citations are academically appropriate for context
- [ ] No redundant sections repeating the same finding
- [ ] All coined/specialized terms defined on first use
- [ ] No confusing parenthetical qualifiers that add ambiguity
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Haiku ablation study paper (`docs/arxiv/haiku/`) -- Pass 1 | Caught dangling `\ref{tab:criteria_performance}`, two missing Related Work citations, hardcoded token numbers without table refs |
| ProjectScylla | Haiku ablation study paper (`docs/arxiv/haiku/`) -- Pass 2 | Identified ceiling effect in pass rates (0.903--1.000), missing power analysis for null tier-equivalence claim, SRH validity caveat needed, misleading "faceted by model" caption for single-model study, logical tension between non-significant pass rate and significant score difference |
| ProjectScylla | Haiku ablation study paper (`docs/arxiv/haiku/`) -- Pass 3 | Flagged negotiation book citation in methodology section, redundant restatements of tier equivalence across Discussion/Conclusions, undefined "budget frontier model" term, confusing parenthetical qualifiers in statistical interpretation sentences |

## References

- [academic-paper-validation](academic-paper-validation.md) -- Complementary skill for statistical methodology and pipeline-first fixes
- [citation-verification-arxiv-abstract-fetch](citation-verification-arxiv-abstract-fetch.md) -- Primary-source citation verification
- [latex-paper-parallel-assembly](latex-paper-parallel-assembly.md) -- Assembling papers from parallel agent outputs
- [LaTeX cross-referencing guide](https://www.overleaf.com/learn/latex/Cross_referencing_sections_and_equations)
- [arXiv submission guide](https://arxiv.org/help/submit_tex)
