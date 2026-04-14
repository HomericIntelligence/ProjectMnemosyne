---
name: arch-research-myrmidon-swarm-review
description: "Parallel AI architecture research review using Myrmidon Swarm pattern: 1 lead agent per idea + 5 parallel sub-agents (citation verifier, complexity auditor, literature gap finder, comparison validator, feasibility checker) + coordinator. Use when: (1) reviewing a corpus of 10+ research documents for correctness, (2) verifying citations, Big-O claims, and baseline comparisons at scale, (3) producing independent review documents that can be cross-checked."
category: architecture
date: 2026-04-14
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: []
history: arch-research-myrmidon-swarm-review.history
---

# Myrmidon Swarm: Parallel Architecture Research Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Review and validate 31 AI architecture research documents (research + summary pairs) for citation accuracy, Big-O correctness, baseline comparison validity, and implementation feasibility |
| **Outcome** | Successful — 31 review docs, 155 verification files, 2 synthesis reports, 1 final summary produced |
| **Verification** | verified-local |

## When to Use

- Reviewing a corpus of 10+ existing research documents for factual correctness
- Verifying that cited papers exist, summaries are faithful, and arXiv IDs are not fabricated
- Cross-checking Big-O complexity tables and Nx improvement claims against canonical baseline specs
- Finding missing literature that changes novelty classifications
- Producing independent review documents for a research corpus
- Generating research docs for new ideas that have no prior `research_*.md`/`summary_*.md` files, where each new idea needs full 5-role Myrmidon treatment alongside (or after) the existing corpus review

## Verified Workflow

### Quick Reference

```
Phase 0: Pre-flight baseline verification
  → Web-fetch authoritative config.json for each baseline model
  → Identify all errors in the shared context/prelude document
  → Inject canonical baselines verbatim into every agent prompt

Phase 1: 31 lead agents launched in parallel (one per idea)
  → Each lead spawns 5 sub-agents in parallel:
     a. Citation Verifier (WebFetch each paper; confirm existence/authors)
     b. Complexity Auditor (re-derive Big-O independently; check concrete byte calcs)
     c. Literature Gap Finder (rerun search queries + synonym variants)
     d. Comparison Validator (validate Nx claims, directional arrows)
     e. Feasibility Checker (hardware, training stability, framework support)
  → Each sub-agent emits verification_{id}_{role}.md

Phase 2: Lead agents synthesize → review_{id}_{name}.md
Phase 3a: Synthesis doc validator → review_synthesis_docs.md
Phase 3b: Coordinator → review_summary.md
```

### Detailed Steps

1. **Pre-flight baseline verification** — Before any agents run, web-fetch authoritative specs for every baseline model (e.g., HuggingFace config.json). Compare against any shared context document. If they disagree, the web-verified spec wins. Document all discrepancies as "inherited errors" and inject them into every agent prompt so sub-agents know which errors to attribute to the prelude vs. original author reasoning.

2. **Parallel lead agent launch** — Launch all N lead agents in a single message (one Agent tool call per idea). Each lead gets: canonical baselines + inherited error callouts + the research/summary doc pair for its idea.

3. **5 sub-agent roles per lead** — Each lead immediately spawns 5 sub-agents in parallel. Role assignments:
   - **Citation Verifier**: WebFetch every cited paper. Verdict per paper: YES / NO / PARTIALLY / COULD NOT VERIFY. Check author names, year, venue, and that the research doc's summary matches the actual abstract. Flag hallucinated arXiv IDs.
   - **Complexity Auditor**: Re-derive every Big-O independently. Recompute every concrete byte value (KV cache, weight memory) using canonical baseline specs. Surface hidden costs: router FLOPs O(d·E) for MoE, gradient memory 2× during training.
   - **Literature Gap Finder**: Run the pre-canned search queries from the original idea list plus 3–5 synonym variants. Compare against cited papers. Focus on post-cutoff papers, seminal overlooked work, and papers that would change the novelty classification.
   - **Comparison Validator**: Validate every Nx claim and every ↓/↑/= arrow in summary tables. Recompute using canonical baseline parameter values (not just symbolic O notation). Flag best-case-without-disclaimer claims.
   - **Feasibility Checker**: Hardware feasibility (custom kernels? Triton/CUDA?), training stability (routing collapse, expert collapse), framework support, cross-idea synergy claims (read the other idea's doc to confirm).

4. **Synthesis** — After all 5 sub-agent verification files land, lead agent synthesizes → review doc with 8 sections: citation verification, missing literature, Big-O verification, technical correctness, prior art check, verdict check, error summary, confidence scores. Assigns PASS / PASS WITH ISSUES / NEEDS REVISION / FAIL.

5. **Phase 3a synthesis doc validation** — One agent reads all synthesis artifacts (priority rankings, implementation specs, cross-reference matrices) and cross-checks each claim against the 31 reviews. Flags claims that rest on corrected Nx values or ideas with FAIL/NEEDS REVISION verdicts.

6. **Phase 3b coordinator** — One coordinator reads all 31 reviews + synthesis validation report. Produces: per-idea verdict table, aggregate stats, systemic error pattern analysis, revised priority ranking.

### Phase A: Research New Ideas (when ideas have no prior docs)

When adding N new ideas to an existing corpus that already has Phase 1–3 complete:

1. **Read the existing `SHARED_PRELUDE.md`** verbatim — inject into every new-idea lead agent prompt. New ideas get the same canonical baseline specs.

2. **Launch N new-idea lead agents in parallel** (one per idea). Each agent:
   - Spawns 5 sub-agents in parallel (same roles: Citation Verifier, Complexity Auditor, Literature Gap Finder, Comparison Validator, Feasibility Checker)
   - Produces `research_6_N_<slug>.md`, `summary_6_N_<slug>.md`, 5× `verification_6_N_<role>.md`, then `review_6_N_<slug>.md`
   - Follows the same 8-section review template as Phase 2 lead agents

3. **Critical prior art each new-idea agent MUST check** (inject these search terms explicitly):
   - N1 (in-arch AR loop with stop-token break): RWKW inference loops, Medusa/EAGLE speculative decoding trained-in, PonderNet, ACT (Adaptive Computation Time)
   - N2 (prefill/decode split): Splitwise (Patel 2023, arXiv:2311.18677), DistServe (Zhong 2024, arXiv:2401.09670), SARATHI-Serve chunked prefill (Agrawal 2023)
   - N3 (block-diffusion AR decoder): BD3-LM (arXiv:2406.15253), MDLM (Sahoo 2024, arXiv:2406.07524), LLaDA (Nie 2025, arXiv:2502.09992), Fast-dLLM (arXiv:2505.05175)
   - N4 (combined N1+N2+N3): cite all three base papers above; cross-synergy analysis required

4. **arXiv IDs must be WebFetch-verified** before citation — same rule as Phase 1.

5. **After Phase A completes**: new `research_6_N_*.md` files are equivalent to existing `research_1_*`–`research_5_*` files and can be included in the LaTeX paper on equal footing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using prelude/command baseline specs directly | Accepted SHARED_PRELUDE.md baseline numbers at face value | Prelude had 5 factual errors: wrong vocab (151,936→248,320 for A1/B), wrong context (32,768→262,144), wrong head_dim (128→256 for GatedAttn), wrong head counts for B global attention. These cascaded into all 31 research docs | Always web-fetch authoritative config.json before starting any quantitative analysis |
| Single-agent review | Tried reviewing multiple ideas sequentially | Context window exhaustion; cross-contamination between ideas | One lead agent per idea; no agent works on more than one idea |
| Agent self-approval stall | 4 agents invoked `/hephaestus:advise` internally, presented a plan, and waited for approval | Agents stalled indefinitely waiting for human approval in background context | Detect stalled agents by checking for verification files without corresponding review files; unblock by sending explicit approval via SendMessage |
| Trusting "68 GB KV at 32K" for A2 | SHARED_PRELUDE stated A2 (Qwen3-32B) KV cache = ~68 GB at 32K context | Wrong: used 64 Q-heads instead of 8 KV-heads in formula; ~8× overestimate. Correct: 64L × 2 × 8KV × 128hd × 32768tok × 2B = ~8.59 GB | Always verify KV cache formulas use KV head count not Q head count |
| N4 before N1/N2/N3 | Tried to research the combined idea before the three component ideas had research docs | N4 requires cross-references to N1, N2, N3 prior art and Big-O analysis; without them the N4 agent fabricates component details | Always research component ideas N1, N2, N3 fully before launching N4 agent |
| Trusting author complexity claims for new ideas | Accepted "O(n) per token" claim from a new idea's mechanism description without re-deriving | Author was counting attention heads as O(1); when DeltaNet state per head is O(d²), full per-token cost is O(d²) not O(n·d) | Complexity Auditor sub-agent must re-derive every Big-O for new ideas, same as for existing corpus |

## Results & Parameters

### Systemic Error Patterns Found (apply to any similar review)

1. **KV cache formula error**: `n_q` (query heads) used instead of `n_kv` (KV heads) → 8× overestimate for GQA models
2. **Context window mislabeling**: Concrete byte values computed at native context but labeled with a smaller context value
3. **Vocab propagation**: Shared vocab across model families confused; each baseline may have different vocab size
4. **Speedup figure context mismatch**: Long-context speedup figures (e.g., "3× at 65K context") incorrectly cited at short context (8K–32K) where MLP FLOPs dominate attention
5. **Citation discipline failures**: Anonymous keys ("Multiple authors"), missing §X.Y section references, post-cutoff papers without "unverified" flags

### Review Document Template (8 sections)

```markdown
## 1. Paper Citation Verification (YES/NO/PARTIALLY/COULD NOT VERIFY per paper)
## 2. Missing Literature (papers the review should have cited)
## 3. Big-O / Complexity Verification (table: original vs. corrected)
## 4. Technical Correctness (mechanism, feasibility, fairness)
## 5. Prior Art Classification Check (EXISTS/PARTIAL/NOVEL — confirmed or revised)
## 6. Verdict Check (PURSUE/INVESTIGATE/DEPRIORITIZE — confirmed or revised)
## 7. Error Summary (Critical / Minor / Suggestions)
## 8. Confidence Scores (literature, technical, comparison, overall — 1-10)
```

### Correction Pass (post-review)

After reviews complete, launch parallel surgical correction agents (one per group of 5–8 ideas). Each agent:
- Reads the review files for its assigned ideas
- Makes in-place edits to research/summary docs
- Adds `[corrected: ...]` inline notes so changes are traceable
- Never touches review_*.md or verification_*.md (read-only ground truth)

### New Idea Research — Verified arXiv IDs (2026-04-14)

These IDs were WebFetch-verified during the N1–N4 research pass:

| Idea | Key paper | arXiv ID | Verified |
|------|-----------|----------|---------|
| N1 (AR loop + stop token) | PonderNet | arXiv:2107.05407 | YES |
| N1 | EAGLE speculative decoding | arXiv:2401.15077 | YES |
| N2 (prefill/decode split) | Splitwise | arXiv:2311.18677 | YES |
| N2 | DistServe | arXiv:2401.09670 | YES |
| N3 (block diffusion AR) | BD3-LM | arXiv:2406.15253 | YES |
| N3 | MDLM | arXiv:2406.07524 | YES |
| N3 | LLaDA | arXiv:2502.09992 | YES |
| N3 | Fast-dLLM | arXiv:2505.05175 | YES |

### N1–N4 Final Verdicts

| Idea | Verdict | Rationale |
|------|---------|-----------|
| N1 (In-arch AR loop + stop token) | INVESTIGATE | Novel framing; prior art (PonderNet, Medusa) covers components but not the specific trained-in stop-token-as-architecture-gate |
| N2 (Prefill/decode split) | PURSUE | Splitwise and DistServe validate the operational benefit; architectural-level split (vs. system-level) is the novel angle |
| N3 (Block-diffusion AR decoder) | INVESTIGATE | BD3-LM and LLaDA are close prior art; the AR-across-blocks + diffusion-within-block combination at architecture level has novelty |
| N4 (Combined N1+N2+N3) | INVESTIGATE | Synergy benefit is plausible but compounding complexity; depends on N2 and N3 independently proving out first |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | 31 AI architecture ideas (sections 1–5 plus 4.7) | Qwen3.5-27B Hybrid, Qwen3-32B Dense, Qwen3.5-397B-A17B MoE baselines |
| ArchIdeas | 4 new ideas (N1–N4) added to existing 31-idea corpus | research_6_1 through research_6_4 produced by parallel Myrmidon swarms; all 4 included in final LaTeX paper |
