---
name: academic-paper-myrmidon-swarm-review
description: "Parallel myrmidon swarm review of academic papers using role-stratified agents (Opus=professor, Sonnet=expert, Haiku=student) for comprehensive, simultaneous coverage. Use when: (1) reviewing a large academic paper with statistical methodology, (2) need thorough parallel coverage faster than sequential review, (3) paper has figures generated from Vega-Lite specs that require caption verification."
category: documentation
date: 2026-04-08
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [academic, paper-review, myrmidon, swarm, latex, statistics, vega-lite]
---

# Academic Paper Myrmidon Swarm Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Objective** | Comprehensive parallel academic paper review using role-stratified myrmidon swarm agents across statistical methodology, data accuracy, writing quality, and figure/caption verification |
| **Outcome** | Operational — caught 4 CRITICAL figure/caption mismatches, 8 missing statistical citations, effect size framing issues, and N-level labeling errors across a 2,180-line paper. Paper compiled cleanly post-fix. PR HomericIntelligence/ProjectScylla#1758 created. |
| **Verification** | verified-local (paper compiled cleanly; CI pending) |

## When to Use

- Reviewing a large academic paper (>1,000 lines of LaTeX) presenting experimental results
- Paper has figures generated from Vega-Lite `.vl.json` specs requiring caption verification
- Need parallel coverage across statistical methodology, data accuracy, and writing quality simultaneously
- Paper uses non-parametric statistics (Kruskal-Wallis, Mann-Whitney U, Cliff's delta, Krippendorff's alpha)
- Want to catch issues faster than sequential single-agent review

## Verified Workflow

### Quick Reference

```bash
# 1. Launch parallel swarm (5 agents + 1 coordinator)
# Opus: statistical methodology professor
# Sonnet x2: data accuracy expert + writing/framing expert
# Haiku x2: line-by-line number verifier x2 (split paper halves)

# 2. Verify figure captions against VL JSON specs
for f in docs/arxiv/haiku/figures/*.vl.json; do
  echo "=== $f ===" && cat "$f" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('title:', d.get('title',''))
print('x:', d.get('encoding',{}).get('x',{}).get('field',''))
print('y:', d.get('encoding',{}).get('y',{}).get('field',''))
print('color:', d.get('encoding',{}).get('color',{}).get('field',''))
"
done

# 3. Build paper to verify fixes compile
pixi install --environment docs
pixi run --environment docs bash build.sh
```

### Detailed Steps

1. **Advisement phase**: Run `/advise` to search ProjectMnemosyne for existing skills (`academic-paper-validation`, `academic-paper-review-quality-improvement`, `latex-paper-peer-review`, `pixi-tectonic-latex-build`). Read any relevant ones before starting.

2. **Launch swarm coordinator (Opus)**: Coordinator subdivides the paper into domains and delegates to 5 specialist agents in parallel:
   - **Opus professor**: Statistical methodology — test selection, effect size reporting, confidence intervals, inter-rater reliability
   - **Sonnet expert A**: Data accuracy — every number in the paper verified against source data/tables
   - **Sonnet expert B**: Writing quality — framing, hedging language, academic tone, effect size rhetoric
   - **Haiku student A**: Line-by-line pass over paper lines 1–1090 (odd sections)
   - **Haiku student B**: Line-by-line pass over paper lines 1091–2180 (even sections)

3. **Figure caption verification**: For every figure, read its `.vl.json` spec to determine what it actually shows. Do NOT assume the caption is correct. Cross-check:
   - Which variable is on x-axis, y-axis, color channel
   - What the title field says
   - Whether the caption describes the same variable mapping

4. **Aggregate findings**: Coordinator collects all findings, deduplicates, and classifies as CRITICAL / IMPORTANT / MINOR.

5. **Apply fixes in priority order**: CRITICAL first (figure/caption mismatches, N-level labeling), then IMPORTANT (effect size framing, missing citations), then MINOR (wording, hedging).

6. **Add statistical citations**: Verify `references.bib` contains original source papers for every statistical test used (see checklist in Results & Parameters).

7. **Build verification**: Run `pixi run --environment docs bash build.sh`. Fix any LaTeX compilation errors before declaring done.

8. **Create PR**: Commit all fixes and create PR with detailed description of all changes made.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix captions before reading VL JSON | Rewrote figure captions based on paper context and section headings | Captions were wrong — the figures showed different variables than assumed | Always read the `.vl.json` spec before touching a figure caption |
| Use system LaTeX | `pdflatex build.sh` or `latexmk` | No system LaTeX installed in the environment | Use `pixi install --environment docs` then `pixi run --environment docs bash build.sh` |
| Sequential single-agent review | One Sonnet agent reading 2,180 lines end-to-end | Slow and likely to miss cross-domain issues (statistical + framing + data accuracy simultaneously) | Parallel role-stratified swarm is faster and catches more cross-domain issues |
| Accept BCa bootstrap at n=9 | Reported BCa bootstrap confidence intervals for binary pass-rate data with n=9 per cell | BCa bootstrap is unreliable at very small sample sizes for binary data | Prefer Clopper-Pearson exact intervals for binary data at n<=15; report BCa as secondary |

## Results & Parameters

### Swarm Agent Role Mapping

| Role | Model | Domain | Focus |
|------|-------|--------|-------|
| Coordinator | Opus | Orchestration | Subdivide, delegate, aggregate, deduplicate |
| Professor | Opus | Statistical methodology | Test selection, effect size reporting, CIs, alpha |
| Expert A | Sonnet | Data accuracy | Every number verified against source tables |
| Expert B | Sonnet | Writing/framing | Rhetoric, hedging, academic tone, overstatement |
| Student A | Haiku | Line verification | Lines 1–N/2 (look for typos, wrong numbers, broken refs) |
| Student B | Haiku | Line verification | Lines N/2+1–N (look for typos, wrong numbers, broken refs) |

### Statistical Citation Checklist

Add these to `references.bib` if the paper uses these methods:

| Test / Method | Citation |
|---------------|----------|
| Kruskal-Wallis test | Kruskal & Wallis (1952) |
| Mann-Whitney U test | Mann & Whitney (1947) |
| Holm-Bonferroni correction | Holm (1979) |
| Bootstrap confidence intervals (BCa) | Efron (1987) |
| Ranks-based nonparametric ANOVA | Scheirer, Ray & Hare (1976) |
| Clopper-Pearson exact CI | Clopper & Pearson (1934) |
| Cliff's delta | Cliff (1993) |
| Vargha-Delaney A statistic | Vargha & Delaney (2000) |
| Krippendorff's alpha | Krippendorff (1970 / 2011) |

### Common Statistical Pitfalls

1. **Cliff's delta direction**: `delta=+1` means group A dominates group B (first argument > second). `delta=-1` means group B dominates. Easy to invert — verify against the raw comparison.

2. **Effect size rhetoric**: "small" Cliff's delta (|δ| < 0.33) should not be called a "critical cliff" or "dramatic drop". Use "statistically significant decline" or "sharp performance drop" instead. Reviewers flag rhetorical overstatement.

3. **N-level labeling**: If subtests have 3 runs each, N=120×3=360 is **run-level** not **subtest-level**. True subtest-level aggregation would yield N=120. Label correctly.

4. **Missing data bias disclosure**: If inter-rater reliability (e.g., Krippendorff's alpha) is computed on a subset where judge evaluations are available, this must be explicitly disclosed as a limitation. The reported alpha is biased upward for easy cases.

5. **Krippendorff's alpha confidence interval**: If alpha is near zero (e.g., -0.030 to 0.100), always report a bootstrap CI. Negative alpha = systematic disagreement (worse than chance), not just low reliability.

6. **BCa bootstrap vs. Clopper-Pearson**: For binary outcome data (pass/fail) with n<=15, Clopper-Pearson exact interval is preferred. BCa bootstrap is secondary and should be labeled as such.

### LaTeX Build Path (No System LaTeX)

```bash
# Install docs environment (first time or after pixi.toml changes)
pixi install --environment docs

# Build
pixi run --environment docs bash build.sh

# Verify output
ls -la docs/arxiv/haiku/*.pdf
```

### Figure Caption Verification Pattern

```bash
# Extract key fields from a VL spec to verify caption
python3 - <<'EOF'
import json, glob

for path in sorted(glob.glob("docs/arxiv/haiku/figures/*.vl.json")):
    with open(path) as f:
        spec = json.load(f)
    enc = spec.get("encoding", {})
    print(f"\n=== {path} ===")
    print(f"  title : {spec.get('title', '(none)')}")
    print(f"  x     : {enc.get('x', {}).get('field', '?')} ({enc.get('x', {}).get('type', '?')})")
    print(f"  y     : {enc.get('y', {}).get('field', '?')} ({enc.get('y', {}).get('type', '?')})")
    print(f"  color : {enc.get('color', {}).get('field', '?')}")
    print(f"  facet : {spec.get('facet', {}).get('field', '(none)')}")
EOF
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | docs/arxiv/haiku/paper.tex — 2,180-line ablation study, 1,080 runs, 7 tiers, Claude Haiku 4.5 | PR HomericIntelligence/ProjectScylla#1758 |
