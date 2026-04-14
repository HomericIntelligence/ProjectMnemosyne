---
name: academic-paper-myrmidon-swarm-review
description: "Parallel myrmidon swarm review of academic papers and AI architecture research docs using role-stratified agents for comprehensive, simultaneous coverage. Use when: (1) reviewing a large academic paper with statistical methodology or Vega-Lite figures, (2) reviewing an AI architecture research doc for citation accuracy / complexity / literature gaps / comparison validity / feasibility, (3) need thorough parallel coverage faster than sequential review."
category: documentation
date: 2026-04-13
version: "1.1.0"
user-invocable: false
verification: verified-local
history: academic-paper-myrmidon-swarm-review.history
tags: [academic, paper-review, myrmidon, swarm, latex, statistics, vega-lite, architecture-research, kv-cache, quantization-review]
---

# Academic Paper Myrmidon Swarm Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Comprehensive parallel review of academic papers OR AI architecture research docs using role-stratified swarm agents. For LaTeX papers: statistical methodology, data accuracy, writing quality, figure/caption verification. For arch research docs: citation verification, complexity audit, literature gap finding, comparison validation, feasibility checking. |
| **Outcome** | Operational — LaTeX paper: caught 4 CRITICAL figure/caption mismatches, 8 missing citations (ProjectScylla#1758). Arch research doc (TurboQuant 5.1): caught context length mislabel (68.7 GB labeled "32K"), head_dim error, TPOT overstatement, 3 missing literature citations. |
| **Verification** | verified-local |
| **History** | [changelog](./academic-paper-myrmidon-swarm-review.history) |

## When to Use

**For LaTeX academic papers:**
- Reviewing a large academic paper (>1,000 lines of LaTeX) presenting experimental results
- Paper has figures generated from Vega-Lite `.vl.json` specs requiring caption verification
- Paper uses non-parametric statistics (Kruskal-Wallis, Mann-Whitney U, Cliff's delta, Krippendorff's alpha)

**For AI architecture research docs:**
- Reviewing a `research_*.md` or `summary_*.md` doc for numerical correctness (KV cache sizes, TPOT estimates, complexity claims)
- Verifying citations (arXiv IDs, author names, venue, summary faithfulness) against known literature
- Finding literature gaps (papers that should be cited but aren't)
- Validating comparison Nx claims against canonical architecture parameters

**Both:**
- Need parallel coverage across multiple specialist domains simultaneously
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
| Trust "32K ctx" label in arch research docs | Accepted KV cache figures labeled "32K ctx" without re-deriving from the formula | The 68.7 GB figure (A2 KV cache) was labeled "32K ctx" but computed with 262,144 tokens; the label was wrong | Always re-derive KV cache from scratch: `num_layers × 2 × n_KV_heads × head_dim × seq_len × 2`; check that the result matches the seq_len in the label |
| Use attention-kernel speedup as TPOT speedup | Cited FlashInfer "4× speedup for 4-bit KV" as evidence of "4× TPOT improvement" | Attention kernel speedup is for the KV-attention portion only; TPOT also includes weight loading (unchanged); for a 32B model at 262K context, realistic TPOT gain is ~1.6×, not 4× | Compute realistic TPOT: `(weight_BW + KV_BW) / (weight_BW + KV_BW/4)` — weight_BW dominates at shorter contexts |

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

### Architecture Research Doc Review — 5-Agent Pattern

When reviewing an individual `research_*.md` + `summary_*.md` doc from the ArchIdeas corpus:

```
5 Sonnet specialists in parallel (Wave 1), all read research_*.md and summary_*.md:
  A — Citation Verifier:    arXiv IDs, author names, venue, summary faithfulness, fabrications
  B — Complexity Auditor:   Re-derive KV/FLOPs formulas; check context length labels; dequant overhead
  C — Literature Gap Finder: Missing papers, underweighted methods, key missing citations
  D — Comparison Validator: Nx claims, layer fractions, TPOT derivation (include weight bandwidth!)
  E — Feasibility Checker:  Scope discipline, STE soundness, training stability risks, implementation effort

Each writes to: verification_{id}_{domain}.md

Wave 2 — Lead reviewer synthesizes into: review_{id}_{name}.md
  8 sections: Citation Verification / Missing Literature / Big-O Verification /
               Nx Comparison / Feasibility / Quality Analysis / Novelty / Final Verdict
```

**Scope constraint discipline check**: For idea 5.1 (KV-cache-only quantization), each sub-agent must verify the analysis never bleeds into weight quantization territory. Each idea may have a scope constraint note in SHARED_PRELUDE.md.

**Canonical architecture parameters to use** (may differ from SHARED_PRELUDE.md v1):
- A1 GatedAttn head_dim = 256 (NOT 128); 24Q/4KV (full-attn layers)
- A2: 8 KV heads, head_dim=128, all 64 layers; context=262,144 (not 32,768)
- B: 2 KV heads × head_dim=256 (product=512; same footprint as 4×128)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | docs/arxiv/haiku/paper.tex — 2,180-line ablation study, 1,080 runs, 7 tiers, Claude Haiku 4.5 | PR HomericIntelligence/ProjectScylla#1758 |
| ArchIdeas research | review of idea 5.1 TurboQuant (KV cache QAT) — 5 Sonnet specialists + synthesis | Apr 2026 — found context mislabel, head_dim error, TPOT overstatement, 3 missing papers |
