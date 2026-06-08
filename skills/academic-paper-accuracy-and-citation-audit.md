---
name: academic-paper-accuracy-and-citation-audit
description: "Use when: (1) performing a multi-pass LaTeX paper audit covering data consistency, cross-references, scientific rigor, and writing quality before submission; (2) verifying every numerical claim in a research paper against source data files (CSV, JSON) with parallel agents and fixing errors; (3) finding academic citations for unsupported claims via parallel web searches and filling citation gaps with real published papers including full BibTeX metadata; (4) verifying every numeric claim in a corpus citation against the cited paper's arXiv abstract via parallel WebFetch agents — distinguishing fabricated papers from misquoted real ones; (5) fixing LaTeX build errors from unescaped underscores in table cells (Missing $ inserted)."
category: documentation
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: academic-paper-accuracy-and-citation-audit.history
tags: [latex, audit, paper, academic, citation, bibtex, arxiv, data-consistency, cross-reference, numerical-accuracy, parallel-agents, scientific-rigor, writing-quality, fabrication-detection, webfetch, web-search, pandas, pivot-table, idxmax, underscore-escape, missing-dollar]
---

# Academic Paper Accuracy and Citation Audit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Audit academic papers for accuracy across five dimensions: numerical claims vs source data, LaTeX cross-reference integrity, scientific rigor, citation correctness (gap-filling and primary-source verification), and LaTeX build fixups |
| **Outcome** | Consolidated workflow that, on real ProjectScylla/ProjectOdyssey/ArchIdeas papers, caught broken `\ref` chains, ceiling-effect confounds, stale inline tables, pandas NaN/idxmax/pivot_table bugs, fabricated citation ranges, swapped numbers, and Missing-$ build errors |
| **Verification** | verified-ci |

## When to Use

- A LaTeX paper is being prepared for submission and needs a final strict audit (data, cross-refs, rigor, writing).
- The paper references external data files (CSV, JSON) and every hardcoded number must be traced to its source.
- The paper has both auto-generated tables AND hand-written inline tables that may be stale.
- Multiple aggregation levels exist (per-run, per-subtest, per-tier, per-experiment) and tables/figures may compute the same metric at different levels.
- The paper reports null results, near-ceiling/floor metrics, or poor inter-rater reliability that need rigor caveats.
- The paper contains assertions without `\cite` references, or hedged language to upgrade with real citations + full BibTeX.
- A corpus makes numeric claims attributed to specific arXiv papers and you must verify them against primary sources, distinguishing fabricated papers from real-but-misquoted ones (including post-knowledge-cutoff IDs).
- A LaTeX build fails with `! Missing $ inserted` and the error context shows an underscore in a table cell.

**Trigger phrases**: "strict paper audit", "verify paper references", "check data consistency", "verify all numbers", "correctness audit", "find citations", "fill citation gaps", "citation verification", "swarm audit", "post-correction audit", "Missing $ inserted", "underscore escape".

**Boundary**: IN — paper accuracy audit (data/cross-ref/rigor), citation gap-filling, claim verification against arXiv abstracts, LaTeX compilation fixups. OUT — paper writing/assembly, ADR documentation.

## Verified Workflow

### Quick Reference

```bash
# --- Cross-reference & structural integrity ---
grep -oP '\\ref\{[^}]+\}'  paper.tex | sort -u            # all \ref targets
grep -rnP '\\label\{[^}]+\}' paper.tex tables/*.tex        # all \label defs
grep -oP '\\input\{[^}]+\}' paper.tex | sort -u            # all \input targets
grep -oP '\\cite[tp]?\{[^}]+\}' paper.tex | tr ',' '\n' | sort -u   # all cite keys
grep -oP '@\w+\{([^,]+),' references.bib | sort -u         # all bib keys
grep -rnP 'TODO|FIXME|XXX|PLACEHOLDER|TBD|\?\?' paper.tex tables/*.tex

# --- Data consistency ---
grep -nP '\d+\.\d+%|\$\d+\.\d+|\d+ (subtests|runs|tiers|judges|criteria)' paper.tex
grep -rn "is not None" src/.../reporting/   # pandas NaN-leak bug pattern
grep -rn "nan" <generated-tables-dir>        # literal nan in ALL generated files

# --- Citation discovery (cite-free assertions) ---
grep -n -E '(suggest|evidence|often|typically|tend to|commonly|generally|studies (show|indicate))' paper.tex | grep -v '\\cite'

# --- arXiv citation verification ---
grep -nP 'arXiv:[0-9]{4}\.[0-9]{4,5}' <corpus glob>   # citations to verify

# --- LaTeX underscore build fix ---
grep -n "_" docs/arxiv/<paper>/tables/*.tex | grep -v "\\\_"   # unescaped underscores

# --- Compile & confirm (run pdflatex twice to resolve refs) ---
pdflatex -interaction=nonstopmode paper.tex && bibtex paper && \
  pdflatex -interaction=nonstopmode paper.tex && pdflatex -interaction=nonstopmode paper.tex
grep -c "LaTeX Warning.*undefined" paper.log   # must be 0
grep "^!" paper.log                            # must be empty
```

### Detailed Steps

#### A. Data Consistency Verification (numbers vs source)

**Principle**: check BOTH directions — every number in the paper has a matching value in a data file, AND every important result in a data file is actually reported.

1. Read all data sources (`summary.json`, `statistical_results.json`, `runs.csv`, `criteria.csv`, `subtests.csv`, `judges.csv`).
2. Extract every hardcoded number from the paper text (percentages, dollar amounts, counts, test statistics).
3. Cross-check each against its source; build a verification table:

   ```markdown
   | Category | Paper Claim | Data Value | Source File | Match? |
   |----------|-------------|------------|-------------|--------|
   | T0 pass rate | 0.42 | 0.42 | summary.json | YES |
   | T6 cost | $0.070 | $0.106 | runs.csv | NO (34%) |
   ```

4. **Recompute independently** with pandas from raw `runs.csv` rather than trusting `summary.json` (which may be stale or use the wrong aggregation):

   ```python
   import pandas as pd
   df = pd.read_csv('runs.csv')
   tier_stats = df.groupby('tier').agg(
       mean_score=('score', 'mean'), mean_cost=('cost_usd', 'mean'), n_runs=('score', 'count'))
   ```

5. Flag any number that cannot be traced, diverges from its source, or whose aggregation level is ambiguous (pooled tier-level vs per-subtest mean can differ by ~0.23).

#### B. LaTeX Cross-Reference Chain Audit (the most critical structural phase)

Checking label existence alone is insufficient — you must verify the file containing the label is actually `\input`-ed, or the PDF renders "??".

1. `\ref` → `\label` → `\input`: for each `\ref`, confirm (a) a `\label` exists somewhere AND (b) that file is `\input`-ed by `paper.tex`. Common failure: `tables/tab04_*.tex` has `\label{tab:criteria_performance}` and `paper.tex` uses `\ref{...}`, but `paper.tex` never `\input`s the file → "??".
2. `\cite` → `.bib`: `comm -23 cites.txt bibkeys.txt` to find citations lacking bib entries.
3. `\begin`/`\end` environment pairs: `diff` the sorted/counted lists.
4. Figure/table files: detect **missing** (referenced, not on disk → build fails), **orphaned** (on disk, never referenced), and **unincluded** (labeled + ref'd but never `\input`-ed). Verify `.tex`/`.md` table pairs match.
5. Placeholder text: grep `TODO|FIXME|XXX|PLACEHOLDER|TBD|??`.

#### C. Scientific Rigor Review (read holistically — do conclusions follow from evidence?)

- **Ceiling/floor effects**: if metrics cluster within <10% of scale bounds (e.g., pass rates 0.903–1.000), name "ceiling effect" as a confound in Limitations; null results may reflect restricted range, not equivalence.
- **Power analysis**: null-result papers MUST acknowledge absence of (or include) formal power analysis.
- **Statistical test validity**: add caveats for debated tests (Scheirer-Ray-Hare, Sawilowsky 1990); check multiple-comparison corrections. Note SRH (two-way ranked) and Kruskal-Wallis (one-way) produce different H-values by design — verify which test was used before flagging recomputation discrepancies.
- **Figure caption vs content**: "faceted by X" must match the actual figure (a single-model study cannot meaningfully facet by model); cross-check `.vl.json` specs against captions.
- **Logical tension**: Discussion/Conclusions must not overstate Results (non-significant pass rate + significant score ≠ "tiers equivalent").
- **Score reliability paradox**: if inter-rater reliability is poor (Krippendorff α < 0.667), every downstream score-based section needs a caveat.

#### D. Numerical Correctness — Common Code/Data Bug Patterns

These survive multiple narrative-only passes; at least one agent must recompute from raw data with independent code.

| Pattern | Detection | Fix |
| ------- | --------- | --- |
| Stale inline tables | Compare inline (hand-written) tables vs `runs.csv`; systematic offset = old data version | Recompute and update |
| Aggregation-method mismatch | Table vs figure disagree for same metric | Clarify computation method; footnote |
| False universality ("all 14 reject") | Check every individual case incl. small-N tiers | "13 of 14" + footnote on exception |
| pandas `is not None` NaN leak | grep `is not None` in table-gen code (`float('nan') is not None` is True) | Replace with `pd.notna()` — fix ALL files, not one |
| Over-scoring judges (impl_rate>1.0) | Check scores exceeding rubric max | Footnote with full trace; do not silently clip |
| `idxmax()` alphabetical tie-break | For every "best X" claim, check for ties on the primary metric | Tiebreak with secondary metric (see code below) |
| `pivot_table` cross-experiment averaging | Index omits a grouping dim → silently averages, deflating Spearman ~0.5→~0.1, α 0.135→0.034 | Include ALL grouping dims in pivot index |
| Multiple statistical output files | Main file may use wrong grouping factor; correct results in `srh_tier_experiment.json` | Cite the correct file |
| Figure/caption mismatch after corrections | Read every `.vl.json`; compare `title`/`encoding.y.field`/`mark` vs `\caption{}` | Update whichever is wrong |
| Residual old-narrative + causal language | grep old framing ("degradation", "harm", "caused", "led to") near null results | Replace with neutral/associative framing |
| Precision inconsistency (body vs appendix) | Same statistic at different decimals (H=4.0 vs 4.00; p=0.202 vs 0.2015) | Standardize: 2dp test stats, 3-4dp p-values |
| Consensus vs per-judge level | "only one >1.0" may be true at one level, false at another | Qualify "at the consensus level" |

```python
# idxmax() tiebreaker
max_val = tier_stats['pass_rate'].max()
tied = tier_stats[tier_stats['pass_rate'] == max_val]
best_tier = tied['mean_score'].idxmax() if len(tied) > 1 else tied.index[0]

# pivot_table — include ALL grouping dimensions
pivot = df.pivot_table(index=['experiment', 'tier', 'subtest', 'run_number'],
                       columns='judge', values='score')   # NOT just [tier, subtest, run_number]
```

#### E. Citation Gap-Filling via Web Search (uncited assertions → real papers)

1. **Detect** cite-free assertions and hedged language ("Anecdotal evidence suggests...", "Studies indicate..." without `\cite`).
2. **Search in parallel** — for each claim craft 2-3 queries with different angles (exact-claim-language, technical-terms + "empirical study", negation/contrast). Always add qualifiers ("research paper", "arxiv", "survey", model sizes like 7B/8B) to avoid thousands of irrelevant hits. Dispatch all N claims × M queries in one message.
3. **Evaluate** candidates by directness, empirical-vs-survey strength, recency/venue (IJCAI, NeurIPS, ACL, AAAI, EMNLP preferred), and specificity (quantified results beat "sometimes worse").
4. **Retrieve full metadata** with a follow-up search (`"<exact title>" authors year DOI`) or `WebFetch https://arxiv.org/abs/<ID>` — initial snippets rarely have complete BibTeX.
5. **Write BibTeX + update prose** to match citation strength:

   ```bibtex
   @article{authorYYYYkeyword,
     title = {Full Paper Title}, author = {Last1, First1 and Last2, First2},
     journal = {Journal Name}, year = {2024}, volume = {XX}, number = {YY},
     pages = {1--25}, doi = {10.XXXX/YYYYYY}, note = {arXiv:XXXX.XXXXX},
   }
   ```

   | Before (hedged) | After (cited) |
   | --- | --- |
   | "Anecdotal evidence suggests X" | "Recent work demonstrates X~\cite{key}" |
   | "Studies indicate Z" | "\citet{key} found Z" |

6. **Verify consistency**: cite keys match bib entries; do not over-generalize beyond the cited paper's actual findings.

#### F. Primary-Source Citation Verification via arXiv Abstract (catch fabrication/misquoting)

No text pattern can catch a fabricated range or a real-paper misquote — only direct primary-source verification does.

1. **Enumerate** every citation with a specific numeric claim (`grep -n 'arXiv:[0-9]{4}\.[0-9]{4,5}'` then filter for adjacent %, ×, PPL, GB, tokens, accuracy points).
2. **Partition** the corpus into ~6 non-overlapping file groups (~6-7 files each, sized to a ~30-WebFetch budget per agent).
3. **Dispatch parallel agents** (`subagent_type: general-purpose`, `run_in_background: true`), each READ-ONLY with its file list. Skip bibliography-completeness and pre-2024 foundational papers (Transformer, Mamba, LoRA, RoPE) unless the claim is surprising.
4. **Per citation**, `WebFetch https://arxiv.org/abs/<ID>` and verify 5 dimensions:
   (a) paper exists, (b) title/authors match, (c) numeric claim supported by abstract, (d) direction/polarity not reversed, (e) ranges not fabricated precision ("2.9–4.1×" vs abstract "~3×").

   ```text
   url: https://arxiv.org/abs/<ID>
   prompt: Return exact title, authors, submission date, abstract verbatim, and any
     numeric claim matching <specific claim from corpus>. Quote verbatim. If the ID
     does not resolve to a real paper, say so explicitly.
   ```

5. **Apply remedies** by finding type:
   - Body-level number correct but not in abstract → annotate `[per Table X / §Y of paper body]` (most common).
   - Fabricated/polarity-reversed → replace with abstract's actual claim verbatim.
   - Wrong author list/title → correct from arXiv metadata.
   - Blanket `UNVERIFIED`/`POST-CUTOFF` flag on a real paper → replace with verified abstract-grounded language; post-cutoff-ness alone says nothing about existence or accuracy.
6. **Re-sweep** after remediation — the verification pass is the only gate for this defect class.

#### G. LaTeX Build Fixup — `! Missing $ inserted` from Underscores

1. Build and capture: `bash build.sh 2>&1 | grep -A3 "Missing"`. The error means LaTeX read `_` as a math subscript.
2. Read the `l.NN ...` line context (the error header never names the underscore).
3. In the offending table `.tex`, change `_` → `\_` for every underscore in **plain-text** cells (snake_case identifiers like `code_quality`, `build_pipeline`). Do NOT escape underscores inside `$...$` / `\(...\)` math.
4. Rebuild and confirm exit 0, PDF generated, no `Missing $` in the log.

#### H. Compile, Cross-Check PDF, and Multi-Pass Strategy

- Compile twice (pdflatex → bibtex → pdflatex → pdflatex); confirm 0 undefined warnings, 0 `^!` errors, no "??" refs or "[?]" citations.
- When possible, read the compiled PDF and confirm table/figure numbers and citations render correctly.
- **Parallel agents** (3+ with distinct data sources): Agent A data consistency, Agent B figure/table files, Agent C cross-references; add statistics/figure-spec agents for deeper passes. **Pre-flight recomputation**: run ONE pandas script before spawning agents and embed its JSON in each prompt, so agents don't diverge on aggregation logic.
- **Multiple passes find DIFFERENT bugs**: Pass 1 structural (refs/data/LaTeX), Pass 2 scientific rigor, Pass 3 writing quality + systematic code-bug scan, Post-correction pass (after major narrative changes) for residual old-narrative language, figure/caption alignment, and causal framing. Model tiering works well: Opus for high-value sections (abstract, conclusions), Sonnet for data-dense (results, statistics), Haiku for structural (cross-refs, appendices).
- **Writing quality** (Pass 3): flag non-academic citations in formal sections, redundant restatements, undefined coined terms on first use, and confusing parenthetical qualifiers.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Check `\label` existence only | Confirmed `\label{tab:criteria_performance}` existed in a table file | File was never `\input`-ed, so the label was invisible to LaTeX — PDF showed "??" | Verify the FULL chain: `\ref` → `\label` → file is `\input`-ed |
| Single-agent sequential audit | One agent reading paper.tex top-to-bottom | Too slow for large papers; missed cross-cutting issues | Use parallel agents with distinct data-source responsibilities |
| Single-pass review | Catch data, refs, rigor, writing in one pass | First pass caught structural issues but missed scientific-rigor problems entirely | Use ≥2 passes (structural then content); add a writing pass |
| Fix `is not None` in one file only | Fixed the NaN leak in summary.py | Same bug existed in detail.py and comparison.py (12 instances) | When finding a systematic pattern, grep ALL related files before declaring done |
| Compare best-tier at rounded precision | Checked T1 best CoP ($0.037) against rounded values | T2 was $0.0366 vs T1 $0.0373 — both round to $0.037 but T2 wins | Always compare "best X" claims at full precision |
| `idxmax()` not caught in 4 prior passes | Prior passes checked best-tier claims at full precision | Did not check for ties where `idxmax()` picks alphabetically first | After one best-X mislabel, add the tiebreaker to ALL table-gen code |
| Verify paper values against pipeline output only | 4 passes verified inter-rater stats against tab03 | tab03 was itself wrong (pivot_table bug); confirming wrong values | ≥1 agent must recompute from raw data with independent code |
| Independent SRH recomputation was actually KW | Ran scipy `kruskal()` to verify paper's SRH H-stats | KW (one-way) ≠ SRH (two-way ranked); produced false discrepancy | Verify which test was used before recomputing |
| Broad citation-search queries | Searched "multi-agent systems language models" with no qualifiers | Thousands of irrelevant hits (robotics, game theory) | Add qualifiers: "research paper", "arxiv", "survey", model sizes |
| Relying on first search for metadata | Extracted BibTeX from initial search snippets | Snippets lack complete authors/DOI/pages | Follow-up search with exact title + "DOI", or fetch arxiv/publisher page |
| Blanket `[post-cutoff, unverified]` flags | Flagged 37 post-cutoff arXiv IDs without checking | All 37 resolved to real papers with matching titles/authors | Post-cutoff-ness ≠ fabrication; fetch the abstract, then decide |
| Regex to flag fabricated numeric claims | Tried patterns for "too-precise ranges" / numbers absent from abstracts | No text pattern distinguishes a fabricated range from a real one, or detects reversed polarity | Citation fabrication needs direct primary-source verification, not regex |
| Verify full bibliography per file | One agent verified 30+ citations incl. foundational papers | Exhausted 30-WebFetch budget before reaching high-risk body claims | Focus on body numeric claims; skip well-known pre-2024 foundational papers |
| Rely on the `Missing $` error message alone | Read the error header without the line context | Header never mentions underscores or "subscript" | Always inspect the `l.NN ...` line context to find the offending char |
| `vl2png` with default npx invocation | `npx vl2png` to render VL specs | Missing packages; default 207×369 too small | Use `npx -p vega-lite -p vega-cli -p canvas vl2png` + explicit width/height + scale 3 |

## Results & Parameters

### Configuration

```yaml
paper_root: docs/arxiv/<paper>/
paper_file: paper.tex
bib_file: references.bib
data_dir: data/          # summary.json, statistical_results.json, runs.csv, judges.csv, criteria.csv
audit_agents: 3          # per pass (add stats/figure-spec agents for deep passes)
review_passes: 3+        # structural / scientific / writing (+ post-correction if narrative changed)
webfetch_budget: 30      # per citation-verification agent
severity_levels: [critical, important, minor]
```

### Expected Output

A findings report organized by severity:

- **CRITICAL**: broken `\ref` chains ("??"), numbers disagreeing with data sources, missing `\input` for labeled files, conclusions contradicting results, fabricated/polarity-reversed citation claims, pivot_table cross-experiment averaging.
- **IMPORTANT**: uncited claims, hardcoded numbers without table refs, `.tex`/`.md` mismatches, unacknowledged ceiling effects, null results without power-analysis caveat, best-tier mislabels, systematic `is not None`, figure/caption mismatches.
- **MINOR**: orphaned files, TODO/FIXME remnants, precision inconsistencies, unusual citations, redundant sections, undefined terms, author-list/title drift, body-table numbers needing `[per Table X]`.

### Strict Audit Checklist

```markdown
Pass 1 — Structural
- [ ] Every hardcoded number traced to a data source (both directions)
- [ ] Every \ref has a \label in a file that is \input-ed
- [ ] Every \cite has a matching .bib entry; \begin/\end pairs balanced
- [ ] No TODO/FIXME/PLACEHOLDER; .tex/.md table pairs consistent
- [ ] Compiled PDF has 0 "??" refs and 0 "[?]" citations; build exits 0

Pass 2 — Scientific Rigor
- [ ] Ceiling/floor effects acknowledged; null results have power caveat
- [ ] SRH validity caveat (Sawilowsky 1990); figure captions match content
- [ ] Discussion does not overstate Results; poor-reliability scores caveated

Pass 3 — Writing + Code Bugs
- [ ] Citations academically appropriate; no redundancy; coined terms defined
- [ ] No is-not-None / idxmax / pivot_table bugs; precision consistent

Citation gates (when applicable)
- [ ] Cite-free assertions filled with real papers + full BibTeX
- [ ] Every numeric arXiv citation verified against the abstract (5 dimensions)
```

### Citation Quality Hierarchy (gap-filling)

1. Empirical study with quantified results directly measuring the claim (strongest)
2. Systematic survey synthesizing multiple confirming studies
3. Position/tutorial paper from a recognized venue
4. Workshop paper or preprint (weakest, acceptable if nothing better)

### arXiv Verification Defect Sub-Classes

Fabricated range; swapped numbers; wrong figure + wrong model attribution; headline understating a qualifier; paper-body quotes labeled as abstract; wrong author list; truncated title; reversed polarity. All are real papers misquoted — caught only by abstract fetch, never by regex.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Haiku ablation paper (`docs/arxiv/haiku/`), multi-pass audit | Caught dangling `\ref`, missing Related Work citations, ceiling effect, missing power analysis, SRH caveat, misleading "faceted by model" caption, logical tension |
| ProjectScylla | `docs/arxiv/haiku/paper.tex` (~2,400 lines), 5-agent swarm w/ pre-flight recomputation | Found idxmax() tie-break bug and CRITICAL pivot_table cross-experiment averaging (Spearman ~0.5→~0.1, α 0.135→0.034) that survived 4 prior passes; 280+ claims verified across 20 sections |
| ProjectScylla | arxiv paper, uncited multi-agent LLM claims | Found IJCAI 2024 survey + MDPI Electronics 2025 empirical study; added full BibTeX (DOI, volume, pages); upgraded "Anecdotal evidence" to cited prose |
| ArchIdeas research corpus | Pre-release citation-hygiene audit (39 files, ~60 numeric citations, 6 parallel agents) | Surfaced 6 HIGH fabrications + ~17 MEDIUM over-specifications; all cited papers real, the quotes were wrong |
| ProjectOdyssey | Haiku paper build, `tables/tab04_criteria_performance.tex` | Fixed `! Missing $ inserted` by escaping `code_quality`, `build_pipeline`, `overall_quality`; paper compiled to 56 pages |

## References

- [LaTeX cross-referencing guide](https://www.overleaf.com/learn/latex/Cross_referencing_sections_and_equations)
- [LaTeX special characters reference](https://en.wikibooks.org/wiki/LaTeX/Special_Characters)
- [arXiv submission guide](https://arxiv.org/help/submit_tex)
