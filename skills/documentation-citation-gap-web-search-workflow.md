---
name: documentation-citation-gap-web-search-workflow
description: "Find academic citations for unsupported claims in LaTeX papers using parallel web searches. Use when: (1) a paper makes assertions without \\cite references, (2) you need to fill citation gaps with real, published papers, (3) you want to upgrade hedged language ('anecdotal evidence') to properly cited claims, (4) you need full BibTeX metadata (authors, venue, year, DOI, volume, pages) for discovered papers."
category: documentation
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [citation, web-search, latex, bibtex, academic-writing, citation-gap, paper-discovery, parallel-search]
---

# Finding Citations for Unsupported Claims via Web Search

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-26 |
| **Objective** | Find real, published academic papers to cite for unsupported claims in a LaTeX paper, using targeted web searches to discover papers and retrieve full bibliographic metadata. |
| **Outcome** | Successfully found two strong citations for claims in a ProjectScylla research paper: (1) IJCAI 2024 survey on multi-agent LLM systems for the claim that multi-agent architectures improve frontier model performance, and (2) MDPI Electronics Dec 2025 empirical study showing 7B-8B multi-agent configs underperformed single-agent baselines by -4.4% to -35.3%, backing the claim that smaller models struggle with coordination overhead. Both added to references.bib with full metadata and cited in paper.tex. |
| **Verification** | verified-local (citations added to paper.tex and references.bib; paper not recompiled). |
| **Complements** | `citation-verification-arxiv-abstract-fetch` -- that skill verifies existing citations against primary sources; this skill discovers new citations for uncited claims. |

## When to Use

- A LaTeX paper contains assertions without `\cite` references nearby.
- Review feedback flags unsupported claims that need academic backing.
- You want to replace hedged language ("Anecdotal evidence suggests...") with properly cited statements ("Recent work demonstrates..." with `\cite{key}`).
- You need full BibTeX entries (not just paper titles) including DOI, volume, pages, publisher.

## Verified Workflow

### Step 1: Detect Unsupported Claims

Grep the LaTeX source for assertion patterns near cite-free zones:

```bash
# Find sentences with assertion language but no \cite within ~200 chars
grep -n -E '(suggest|evidence|often|typically|tend to|commonly|generally)' paper.tex \
  | grep -v '\\cite'
```

Also look for hedging language that signals missing citations:
- "Anecdotal evidence suggests..."
- "It is commonly believed..."
- "Research has shown..." (without a cite)
- "Studies indicate..." (without a cite)

### Step 2: Formulate Parallel Web Searches

For each unsupported claim, craft 2-3 search queries using different strategies:

1. **Exact claim language + qualifier**: Use the claim's own words as keywords, adding "research paper" or "arxiv" or "survey"
2. **Technical terms + empirical**: Focus on the technical phenomenon with "empirical study" or "benchmark"
3. **Negation/contrast search**: If the claim is about a limitation, search for studies that found the limitation

**Example for two claims:**

```
Claim A: "multi-agent architectures often improve performance for frontier models"
  Query 1: "multi-agent LLM performance improvement research paper"
  Query 2: "multi-agent systems large language models survey arxiv"
  Query 3: "multi-agent architecture frontier model benchmark"

Claim B: "smaller models struggle with coordination overhead of multi-agent systems"
  Query 1: "small language models multi-agent coordination overhead"
  Query 2: "multi-agent LLM model size performance empirical study"
  Query 3: "7B 8B model multi-agent underperformance"
```

Run searches for all claims in parallel (one WebSearch per query) to minimize wall-clock time.

### Step 3: Evaluate Search Results

For each candidate paper, check:
1. **Directness**: Does the paper's finding directly support the claim, or only tangentially?
2. **Empirical vs. survey**: Empirical studies with quantified results are strongest; surveys that mention the phenomenon are acceptable but weaker.
3. **Recency and venue**: Prefer peer-reviewed venues (IJCAI, NeurIPS, ACL, AAAI, EMNLP) and recent publications.
4. **Specificity**: A paper showing "-4.4% to -35.3% underperformance" is stronger than one saying "sometimes worse."

### Step 4: Retrieve Full Bibliographic Metadata

Initial search results rarely have complete metadata. Run follow-up searches:

```
Query: "<exact paper title>" authors year DOI
Query: "<exact paper title>" arxiv bibtex
```

Or fetch directly from arXiv/publisher pages:

```
WebFetch: https://arxiv.org/abs/<ID>
WebFetch: https://doi.org/<DOI>
```

Collect for each paper:
- Full author list (all authors, correctly spelled)
- Exact title
- Venue (journal/conference name)
- Year, volume, number, pages
- DOI (for permanent linking)
- arXiv ID if applicable

### Step 5: Create BibTeX Entries and Update LaTeX

**BibTeX entry format:**

```bibtex
@article{authorYYYYkeyword,
  title     = {Full Paper Title},
  author    = {Last1, First1 and Last2, First2 and Last3, First3},
  journal   = {Journal Name},
  year      = {2024},
  volume    = {XX},
  number    = {YY},
  pages     = {1--25},
  doi       = {10.XXXX/YYYYYY},
  note      = {arXiv:XXXX.XXXXX},
}
```

**LaTeX prose update:** When adding citations, also update the surrounding prose to match the citation strength:

| Before (hedged) | After (cited) |
| ------------------ | --------------- |
| "Anecdotal evidence suggests X" | "Recent work demonstrates X~\\cite{key}" |
| "It is commonly believed that Y" | "Y, as shown by~\\cite{key}" |
| "Studies indicate Z" | "\\citet{key} found Z" |

### Step 6: Verify Consistency

- Ensure `\cite{key}` keys in paper.tex match entries in references.bib
- Check that the cited paper's actual findings match the claim (do not over-generalize)
- If the paper only partially supports the claim, qualify the prose accordingly

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Broad initial queries | Searched "multi-agent systems language models" without qualifiers | Returned thousands of irrelevant results spanning robotics, game theory, classical MAS | Always add qualifiers: "research paper", "arxiv", "survey", "empirical study", or specific model sizes (7B, 8B) to narrow to relevant LLM literature |
| Relying on first search for metadata | Tried to extract full BibTeX metadata (authors, DOI, volume, pages) from initial search snippets | Search snippets rarely contain complete bibliographic data; got partial author lists and missing DOIs | Always run a follow-up search with the exact paper title + "DOI" or fetch the arxiv/publisher page directly for complete metadata |
| Single query per claim | Used only one search query per unsupported claim | Sometimes the best paper is found only with an alternative formulation; the first query may surface surveys when you need empirical work | Use 2-3 query formulations per claim with different angles (survey vs empirical, exact language vs technical terms) and run them in parallel |

## Results & Parameters

### Citation quality hierarchy

When multiple candidate papers are found, prefer in this order:

1. **Empirical study with quantified results** directly measuring the claimed phenomenon (strongest)
2. **Systematic survey** that synthesizes multiple studies confirming the claim
3. **Position paper or tutorial** from a recognized venue that states the claim as established
4. **Workshop paper or preprint** with relevant findings (weakest but acceptable if nothing better exists)

### Search query templates

| Claim type | Query template |
| ------------ | ---------------- |
| Performance improvement | `"<technology> performance improvement <domain> empirical study"` |
| Performance limitation | `"<technology> <limitation> <model size> benchmark results"` |
| Architectural advantage | `"<architecture> vs <baseline> comparison survey"` |
| Cost/efficiency trade-off | `"<technology> cost efficiency trade-off analysis"` |

### Parallel search pattern

For N unsupported claims with M query formulations each, dispatch N*M web searches in parallel in a single message. Typical timing: 2-3 claims with 2-3 queries each = 4-9 parallel searches, completing in under 30 seconds.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla arxiv paper | Two unsupported claims in paper.tex about multi-agent LLM performance | Found IJCAI 2024 survey (guo2024llmmultiagents) and MDPI Electronics Dec 2025 empirical study (dervishi2025multiagent); added BibTeX entries with full metadata including DOI, volume, pages; updated paper.tex prose from "Anecdotal evidence" to "Recent work" with proper \cite commands |
