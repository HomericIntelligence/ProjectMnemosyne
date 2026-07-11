---
name: parallel-agent-research-and-swarm-orchestration
description: "Orchestrate parallel Myrmidon swarm agents for architecture research review, corpus audit, multi-phase task execution, and automated GitHub pipelines. Use when: (1) reviewing a corpus of 10+ research documents using 1 lead + 5 parallel sub-agents per idea, (2) running a 10-dimension quality audit of research corpora with parallel agent delegation, (3) executing a complex multi-phase session spanning 3+ phases (cleanup, rebase, CI, merge, knowledge capture) with feedback loops and decision gates, (4) building or running a 6-phase GitHub issue automation pipeline (plan → review-plan → implement → review-PR → address-review → drive-green), (5) implementing post-merge recommendations from a chief architect review with parallel doc/test fixes and branch rebase."
category: architecture
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: parallel-agent-research-and-swarm-orchestration.history
tags: [myrmidon, swarm, parallel-agents, l0-commander, multi-phase, orchestration, arch-research, corpus-audit, lora, layer-pruning, citation-verification, github-pipeline, pr-review, ci-driver, architect-review, wave-based, feedback-loop, knowledge-capture]
---

# Parallel Agent Research and Swarm Orchestration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Canonical synthesis of the L0 commander / Myrmidon swarm pattern across four use domains: architecture research review, corpus quality audit, end-to-end multi-phase orchestration, and 6-phase GitHub issue automation |
| **Outcome** | Supersedes: arch-research-myrmidon-swarm-review (v2.0.0), research-corpus-audit-parallel-agent-pattern (v2.0.0), myrmidon-swarm-end-to-end-orchestration-full-workflow (v1.7.0), automation-6phase-issue-pr-pipeline (v1.0.0), architect-review-implementation (v1.0.0) |
| **Verification** | verified-ci |

## When to Use

- Reviewing a corpus of 10+ existing research documents for citation accuracy, Big-O correctness, and baseline comparison validity using the 1-lead + 5-sub-agent Myrmidon pattern
- Auditing research corpora across 10 quality dimensions with parallel agent delegation and file:line evidence grading
- End-to-end task that spans 3+ distinct phases with dependencies (cleanup → rebase → PR → CI fix → merge → knowledge capture)
- Mix of destructive and creative operations requiring explicit user approval gates before deployment
- Building or running a 6-phase GitHub issue automation loop (plan-all, review-plans, implement-all, review-PRs, address-review, drive-green)
- Implementing inline PR review comments via GitHub GraphQL `addPullRequestReview` mutation
- Implementing post-merge recommendations from a chief architect review involving parallel doc/test additions and branch rebase
- Running an ecosystem-wide strict audit across 10+ repos, filing per-repo Epics and child issues
- Recovering mid-session from GitHub org API usage limits

Do NOT use when:
- Task is a single well-defined wave (use `myrmidon-waves-worktree-cleanup-rebase-pr-merge`)
- All sub-tasks are known upfront, session < 30 minutes, no exploration needed

## Verified Workflow

### Quick Reference — Research Review (1 lead + 5 sub-agents per idea)

```
Phase 0: Pre-flight baseline verification
  → Web-fetch authoritative config.json for each baseline model
  → Inject canonical baselines verbatim into every agent prompt

Phase 1: N lead agents launched in parallel (one per idea)
  → Each lead spawns 5 sub-agents in parallel:
     a. Citation Verifier    → verification_{id}_citations.md
     b. Complexity Auditor   → verification_{id}_complexity.md
     c. Literature Gap Finder → verification_{id}_literature.md
     d. Comparison Validator → verification_{id}_comparison.md
     e. Feasibility Checker  → verification_{id}_feasibility.md

Phase 2: Lead agents synthesize → review_{id}_{name}.md
Phase 3a: Synthesis doc validator → review_synthesis_docs.md
Phase 3b: Coordinator → review_summary.md (per-idea verdict table + systemic errors)
```

**Naming drift**: ideas 1.x–5.x use `{citations,comparison,complexity,feasibility,literature}`; ideas 6.x use `{citation_verifier,comparison_validator,complexity_auditor,feasibility_checker,literature_gap_finder}`. Always glob BOTH patterns.

**Wave limit**: Do NOT launch all 39 ideas in one message. Confirmed failure. Use two waves: 17 leads (groups 1–3) then 22 leads (groups 4–6).

### Quick Reference — Corpus Audit (10 dimensions)

```bash
# Wave 1: 4 parallel agents grouped by tool type
# Agent A (Haiku): D1(completeness)+D3(baseline split)+D4(TTFT/TPOT)+D7(accuracy) — grep-driven
# Agent B (Sonnet): D2(citation spot-check) — read 5 files, check 15 numeric values
# Agent C (Sonnet): D5(TPOT direction)+D6(novelty verdicts) — targeted reads
# Agent D (Sonnet): D8(matrix)+D9(ranking)+D10(spec accuracy) — read 4 artifacts

# Wave 2: synthesize in main context; apply structural-F cap rule
# D3=F or D10=F caps overall at C regardless of other grades
```

Grading starts at F; raise only with file:line evidence. Response length cap ~300 words per dimension.

### Quick Reference — End-to-End L0 Orchestration

```bash
# Phase 1: Exploration — 1 Sonnet sub-agent gathers state + /advise call
# Phase 2: L0 designs multi-wave plan with wave assignments, agent tiers, time estimates
# Phase 3: User Approval Gate — NEVER spawn destructive agents without explicit approval
# Phase 4: Wave Execution
#   Wave 1 (Haiku, parallel): mechanical cleanup
#   Wave 2a (Sonnet, parallel): analysis + rebase + PR
#   Wave 2b (Haiku, parallel with 2a): conflict checks
#   Wave 3 (Haiku): prune + verify
# Phase 5: CI Monitoring + Fix Loop
gh pr checks <N> --watch
gh run view <run-id> --log-failed
# Fix agent → push → re-enable auto-merge
gh pr merge --auto --rebase <N>
# Phase 6: Knowledge Capture — 1 Sonnet sub-agent per skill (parallel)
# Phase 7: Tracking Issue on target repo
TITLE="chore(triage): $(date +%Y-%m-%d) issue classification pass"
gh issue create --repo <owner>/<repo> --title "$TITLE" --body "$(cat session-summary.md)"
```

**Pre-launch checks** (run before plan presentation):

```bash
gh repo view --json autoMergeAllowed --jq '.autoMergeAllowed'
ls .pre-commit-config.yaml 2>/dev/null && echo "hooks present" || echo "NO HOOKS"
ls package-lock.json dagger/package-lock.json pixi.lock 2>/dev/null
```

### Quick Reference — 6-Phase GitHub Issue Automation

```python
# Phase sequence per repo per iteration:
# 1. plan-all       — plan every open issue, post plan as GH issue comment
# 2. review-plans   — review every posted plan, post plan-review as GH issue comment
# 3. implement-all  — implement every issue, create PR (saves session_id)
# 4. review-PRs     — review each PR, post INLINE review comments (GraphQL)
# 5. address-review — for each PR with unresolved threads, resume implementer session
# 6. drive-green    — 1 fix iteration on red CI, enable auto-merge [FINAL LOOP ONLY]

# address_review session reuse:
session_id = self._load_impl_session_id(issue_number)
cmd = ["claude", "--resume", session_id, "--print", ...] if session_id else ["claude", "--print", ...]

# Pre-discovery no-PR guard:
pr_map = self._discover_prs(issue_numbers)  # BEFORE submitting workers
futures = {executor.submit(self._address_issue, n, pr_map[n], slot): n
           for n, slot in zip(filtered_issues, slots)}

# drive-green gating:
if loop == loops:
    ci_driver.run(repo_dir, issue_numbers)
```

### Quick Reference — Architect Review Implementation

```bash
# Phase 1: Implement recommended actions in parallel (doc gaps, test coverage, comment accuracy)
# Phase 2: Commit (stage specific files, not --all)
git add <specific-files>
# Phase 3: Rebase against origin/main
git fetch origin main && git rebase origin/main
# Phase 4: Resolve complex conflicts (doubled class definitions → use main as base + apply diffs)
git show origin/main:<file> > /tmp/file_main.py
# Phase 5: Verify — run tests, mypy counts
# Phase 6: Push force-with-lease
git push origin <branch> --force-with-lease
```

### Phase Corpus Review — Detailed Phases

**Phase A: Research New Ideas (when ideas have no prior docs)**

1. Read `SHARED_PRELUDE.md` verbatim; inject into every new-idea lead agent prompt.
2. Launch N new-idea lead agents in parallel; each spawns 5 sub-agents.
3. Each agent produces: `research_6_N_<slug>.md`, `summary_6_N_<slug>.md`, 5× `verification_6_N_<role>.md`, then `review_6_N_<slug>.md`.
4. arXiv IDs must be WebFetch-verified before citation.

**Phase B: Per-Idea Merge + Myrmidon Re-Validation**

Collapse separate review/summary/verification files into one `research_X_Y.md` per idea:

- Step B1: Extend SHARED_PRELUDE with new baseline (web-fetch canonical config.json).
- Step B2: One lead per idea (39× in 2 waves of 17+22); each reads all legacy files, integrates silently, spawns 5 validation sub-agents.
- Step B3: Delete legacy docs after all merges complete.
- Step B4: Regenerate synthesis docs from merged corpus.

**Phase C: Accuracy Review-and-Fix Pass (in-place, marker-free)**

Fix priority order: (1) KV cache/FLOP values, (2) wrong arXiv IDs, (3) claim mismatches, (4) invalid table rows, (5) wrong directional arrows, (6) missing prior art, (7) training/synergy caveats. No `[corrected: ...]` markers; no new subsections; verdicts out of scope.

**Phase D: Verdict Removal Pass**

Remove verdict tokens, Final Verdict / Recommendation sections, Prior Art Classification status lines, verdict-adjacent bullets. Preserve all technical content. Two-wave execution (17+22 same as Phase C). Groups 1–4: inline sentence extraction. Groups 5.x: Status lines. Groups 5.9–5.10 / 4.x outliers: full section block removal. Group 6: inline token extraction; Assessment sections — strip tokens only, preserve prose.

### LoRA / Low-Rank Parameterization Review Checklist

Three cases for any W = W_core + A·B document:

| Case | Formula | Inference Benefit |
|------|---------|------------------|
| Case 1: Merged | W_full materialized | ZERO — identical to dense |
| Case 2: Unmerged, W_core present | x·W_core + (x·A)·B | 1.5× MORE bandwidth — regression |
| Case 3: Unmerged, W_core absent | (x·A)·B only | 2× fewer weight bytes, ~1.64× TPOT improvement |

**Every claim must specify which case it applies to.** Red flags: document claims both TTFT penalty AND throughput improvement for "unmerged"; cites GaLore optimizer savings for LoRA weight reduction; uses dLoRA 38.9% for TPOT at batch=1 decode.

Key citations to verify: GaLore (optimizer states, not weights), CoLA (nonlinearity σ between A·B, ≤7B only), WeLore (post-training compression), dLoRA (grey literature, compute-bound multi-request only), GaLore 2 (suspect — vague, modest improvement).

### Layer Pruning / Residual Gating Review Checklist

**"Static at inference" implementation paths:**

| Path | Inference Speedup? |
|------|-------------------|
| Frozen soft gates (g_i frozen, F_i(x) still runs) | NONE — full layer executes |
| Frozen hard-zero gate + conditional execution | YES — static branch, no GPU divergence |
| Model surgery (physically remove g_i < 0.5 layers) | YES — identical to model designed with fewer layers |

Model surgery removes the entire layer block (norm + attention/MLP) — not just the sublayer.

Training overhead: scalar gates ≈ 1.00× (< 0.01%). Hyper-Connections SHC ≈ 1.05–1.15× (n×d² expansion). Do NOT attribute SHC overhead to scalar gates.

Key citations: Mixture of Depths [Raposo et al., 2024, arXiv:2404.02258] (closest prior art — DYNAMIC per-token), LayerDrop [Fan et al., 2020, arXiv:1909.11556] (RANDOM not learned), ShortGPT [Men et al., 2024, arXiv:2403.03853], GateSkip [Laitenberger et al., 2024, arXiv:2510.13876]. Author name: "Frankle and **Carbin**" (not Carlin) for LTH.

Composition order for ideas 4.4+4.5: 4.5 gating FIRST (determine survivors), then 4.4 (set skip topology to survivors). Opposite order breaks skip-interval anchor points.

### Inline Derivation Standard

Always show full computation for analytically-derived numeric claims:

```
# Correct: ~8.0 GB [derived: 64 layers × 2 × 8 KV heads × 128 dims × 32,768 tokens × 2 bytes (BF16) = 8,589,934,592 bytes ≈ 8.0 GB]
# Wrong: ~8.0 GB [derived from first principles]
```

Multi-baseline: use a `**Derivation:**` block before/after the table substituting values for each baseline.

### Exec Summary Overhead Honesty

When an idea increases TPOT via sequential passes, the exec summary table MUST include a bolded TPOT row and a warning callout. Applies to: in-arch AR loops, iterative refinement decoders, diffusion-based decoders, speculative decoding overhead. FLOPs rows alone are misleading when inference is memory-bandwidth-bound.

### Model Surgery Implementation Recipe (PyTorch)

```python
gate_values = {i: torch.sigmoid(model.gate_logits[i]).item() for i in range(len(model.layers))}
active_indices = [i for i, g in gate_values.items() if g >= 0.5]
model.layers = nn.ModuleList([model.layers[i] for i in active_indices])
if hasattr(model, 'gate_logits'):
    del model.gate_logits
torch.save(model.state_dict(), f"model_p{len(active_indices)/len(gate_values):.2f}.pt")
```

### GraphQL Patterns (6-Phase Pipeline)

```python
# Post inline review — addPullRequestReview mutation
gh api graphql -f query='mutation { addPullRequestReview(input: {
  pullRequestId: "<pr_node_id>", event: COMMENT,
  comments: [{path: "...", line: N, body: "..."}]
}) { pullRequestReview { id } } }'

# Resolve thread
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "<thread_id>"}) { thread { id } } }'
```

Selective resolution: only resolve threads explicitly listed in Claude's `{"addressed": [...]}` JSON output. Never resolve threads not mentioned.

### Worktree / __pycache__ Cleanup

```bash
find .claude/worktrees/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
git worktree remove .claude/worktrees/agent-<id>
git worktree prune
```

### Per-Namespace Sequential Dispatch (mega-cluster split)

When a cluster's members share a common filename prefix (e.g., `mojo-*`), parallel sub-PRs race on branch refs during auto-merge cascades. Split by theme into sequential sub-PRs:

```bash
jq '.absorbed_skills | length' cluster.json  # If > ~30, consider splitting
jq -r '.absorbed_skills[]' cluster.json | sed 's/-.*//' | sort -u  # Check shared prefix
```

Each sub-PR references parent epic with `Refs #<parent>` (NOT `Closes`) until final sub-PR. Each deletion sweep must be skip-missing-safe:

```bash
for f in "${FILES[@]}"; do
  [ -f "skills/$f.md" ] && git rm "skills/$f.md" || true
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using prelude baseline specs directly | Accepted SHARED_PRELUDE.md numbers at face value | Prelude had 5 factual errors (wrong vocab, wrong context, wrong head_dim, wrong head counts) cascading into all research docs | Always web-fetch authoritative config.json before any quantitative analysis |
| Single-agent review | Reviewing multiple ideas sequentially | Context window exhaustion; cross-contamination between ideas | One lead agent per idea; no agent works on more than one idea |
| Agent self-approval stall | Agents invoked /hephaestus:advise internally and waited for approval | Stalled indefinitely; verification files appeared without corresponding review files | Detect stalled agents; unblock by sending explicit approval via SendMessage |
| Trusting "68 GB KV at 32K" for A2 | SHARED_PRELUDE stated A2 KV = ~68 GB at 32K context | Used Q-heads (64) instead of KV-heads (8); ~8× overestimate. Correct: 64L×2×8KV×128hd×32768×2B ≈ 8.59 GB | Always verify KV formulas use n_kv not n_q |
| N4 before N1/N2/N3 | Researched combined idea before component ideas had docs | N4 requires cross-references to component prior art; without them agent fabricates details | Always research component ideas fully before launching N4 agent |
| Processing all 39 ideas in one agent message | One giant Agent call listing all 39 ideas | Context exhaustion before half complete | Split into waves (17+22); parallel agents within each group are fine |
| Verification file role-name drift ignored | Assumed all ideas use same verification suffix pattern | Ideas 1.x–5.x and 6.x use different naming conventions; glob-only missed 6.x files | Each lead agent must glob BOTH naming patterns before reading |
| Adding `[corrected: ...]` markers during Phase C | Using inline correction markers to trace Phase C changes | User opted out — markers clutter corpus | Phase C is marker-free: minimum text change, no inline traces |
| Treating pre-existing `## Corrections applied:` as banned | Agent flagged Phase B metadata header as banned and removed it | It was legitimate pre-existing content, not added by the Phase C/D agent | Check git history or context before flagging a section as "agent-added banned content" |
| Removing whole `## Assessment` sections in group 6 docs during Phase D | Removed entire Assessment section because it contained verdict token | Group 6 Assessment sections contain mixed technical content; removing whole section destroys analysis | For mixed-content sections: strip only verdict tokens; preserve surrounding prose |
| Treating "unmerged" as a single case (LoRA) | Single "unmerged" row covering all three cases | TTFT and TPOT values contradictory | Always split into Case 1/2/3 before populating any table |
| Using GaLore optimizer savings for LoRA training benefit | Cited GaLore Table 1 (65.5%) to support LoRA Everywhere (50%) | Different mechanisms: GaLore reduces gradient states; LoRA reduces weight parameters | Cite separately; different mechanisms |
| Applying dLoRA 38.9% to TPOT (batch=1 decode) | Used 38.9% overhead as TPOT estimate | dLoRA measures compute-bound multi-request; batch=1 TPOT is bandwidth-bound | dLoRA only valid for Case 2 in compute-bound serving |
| Claiming "static at inference" speedup from frozen soft gates | Doc claimed "static, therefore zero overhead" for frozen gate values | Frozen soft gates still run F_i(x) before the multiply; only model surgery produces real speedup | Frozen gate VALUE ≠ eliminated computation; model surgery (Scenario C) required |
| Attributing 1.05–1.15× training overhead to scalar gates | Cited Hyper-Connections SHC overhead range for scalar gates | SHC uses n×d² expansion; scalar gates add ~64 scalar ops total | 1.05–1.15× correct for SHC; scalar gates ≈ 1.00× |
| Missing Mixture of Depths as prior art | Literature review omitted MoD for learned layer skipping | MoD is closest related work for learned binary skip decisions at scale | Always check MoD [Raposo et al., 2024, arXiv:2404.02258] first for any "learned layer skip" idea |
| Misspelling LTH author name | "Frankle and Carlin" in multiple docs | Correct name is Michael Carbin (MIT CSAIL) | Add to citation checklist: always verify second author of LTH = Carbin |
| Single-agent corpus audit | Reading all 68+ files in main context | Context bloat; impractical at scale | Use parallel agents; each reads a subset; synthesize in main context |
| Using `↑ negligible` for zero-overhead ideas | `↑ negligible` in TPOT cells | Convention requires `≈ ref` for true no-overhead ideas | `↑` = real overhead, `≈ ref` = negligible/zero, `↓` = improvement |
| Wrong section header in corpus | `## Quality Tradeoff Evidence` instead of `## Accuracy / Quality Tradeoff` | D7 grep missed the section entirely | Header must match corpus standard exactly |
| Trust FlashInfer "4× speedup" for total TPOT | Used attention-kernel 4× as total TPOT improvement | Weight loading (~64 GB for 32B) is unchanged; realistic TPOT = (weight_BW + KV_BW_before)/(weight_BW + KV_BW_after) | Always compute realistic TPOT using total bandwidth, not kernel-only speedup |
| Parallel fix agents on overlapping file sets | Two agents whose file lists were not partitioned | Both edited same files; merge conflicts guaranteed | Always partition file list explicitly between parallel agents |
| Background agents for large-batch derivation fixes | `run_in_background: true` agents across 29 files | Both failed with "ConnectionRefused" after ~2M tokens / 77 tool uses | Prefer foreground agents with clear scope; split large batches; avoid background for >50 tool calls |
| Over-broad Wave 1 agent scope (orchestration) | "Remove stale worktrees" without explicit list | Removed too many before rebase analysis, discarding branches with unreleased work | Provide exact list of worktree paths; never use general instruction |
| Auto-merge assumption | Enabled auto-merge and moved to Phase 6 | 2 PRs failed pre-commit; auto-merge blocked | Always monitor CI after PR creation; have Phase 5 fix workflow ready |
| Not re-enabling auto-merge after CI fix | Fix agent pushed commit, declared done | GitHub silently cleared auto-merge on force-push | After every push to a PR branch, re-run `gh pr merge --auto --rebase <N>` and verify |
| Skipping tracking issue creation | Session ended after Phase 6 PRs merged | Results not searchable via `gh issue list` in future sessions | Always create `chore(triage): YYYY-MM-DD` tracking issue as Phase 7 |
| Agent worktrees with __pycache__ blocking removal | `git worktree remove` on Python worktrees | Fails with "contains untracked files" even though __pycache__ is irrelevant | Clean `__pycache__` first: `find .claude/worktrees/agent-* -type d -name __pycache__ -exec rm -rf {} +` |
| Two index.ts agents racing to same file | Dispatched parallel agents touching different functions in same file | Even non-overlapping edits in same file create merge conflicts | Same-file edits must always be sequential, even for non-overlapping functions |
| Dispatched 4 sub-PRs in parallel for shared-prefix namespace | Planned simultaneous Mojo mega-cluster sub-PRs | Parallel agents on shared `mojo-*` namespace race on branch refs and auto-merge cascade rebases | Per-namespace sequential dispatch: detect shared prefix, split by theme, dispatch one at a time |
| Forking branch from wrong base | Created branch from feature branch instead of main | Picked up 12 extra unrelated commits; MERGEABLE state wrong | Verify base: `git log --oneline main..HEAD`. If wrong: `git checkout -b <branch> main && git cherry-pick <sha>` |
| Workers discover own PR | `_find_pr_for_issue()` called inside each worker thread | Claude launched before confirming PR exists — wastes quota | Move `_discover_prs()` to `run()` level; workers only receive confirmed `(issue_number, pr_number)` pairs |
| Resolving all review threads | Resolved every unresolved thread after Claude ran | Threads Claude did not address were incorrectly closed | Only resolve threads in Claude's `{"addressed": [...]}` list |
| Parallel filer agents on same repo | Multiple filer retries against same repo concurrently | Created exact-title duplicate issues requiring cleanup pass | Run exactly one filer agent per repo; idempotency check before filing |
| Findings.json as nested object | Audit agent returned nested JSON (`project`, `findings`, `summary` keys) | Filer agents expected flat array; caused KeyError | Enforce flat array format in prompt; add Python extraction fallback |
| Write tool blocked in worktree agents | Audit agents couldn't write report.md ("Subagents should return findings as text") | L0 received inline but no file written; filer agents had no input | Instruct agents to print full report as final message; L0 orchestrator uses Write tool to save it |

## Results & Parameters

### Agent Tier Assignment

| Task | Tier | Reason |
| ------ | ------ | -------- |
| Exploration + state gathering | Sonnet | Structured output synthesis across many data sources |
| Research corpus review (lead agent) | Sonnet | Diff reading, synthesis, PR description |
| Citation Verifier sub-agent | Sonnet | Web fetch + semantic judgment |
| Complexity Auditor sub-agent | Sonnet | Mathematical re-derivation |
| Stale worktree removal | Haiku | Mechanical: rm artifacts + git worktree remove |
| Conflict pre-check (closed PRs) | Haiku | Binary output |
| Pre-commit/lint CI fix | Haiku | Pattern-based fix |
| Complex CI fix (logic errors) | Sonnet | Requires code understanding |
| Skill creation in Mnemosyne | Sonnet | Synthesis of learnings into structured docs |
| Issue filing (40+ issues) | Sonnet | Rate-limit resilience over Haiku |
| L0 orchestration | Sonnet/Opus | Session architecture, wave sequencing, user interaction |

### Corpus Review Reference Parameters

| Wave | Groups | Ideas | Lead Agents | Sub-Agents |
| ------ | -------- | ------- | ------------- | ------------ |
| 1 | 1, 2, 3 | 1.1–1.7, 2.1–2.2, 3.1–3.8 | 17 | 85 |
| 2 | 4, 5, 6 | 4.1–4.7, 5.1–5.10, 6.1–6.5 | 22 | 110 |

**Verification file naming drift** (handle both):

- Ideas 1.x–5.x: `verification_{id}_{citations|comparison|complexity|feasibility|literature}.md`
- Ideas 6.x: `verification_{id}_{citation_verifier|comparison_validator|complexity_auditor|feasibility_checker|literature_gap_finder}.md`

### Corpus Audit Grading Thresholds

```
D2 Citation: A=15/15, B=12-14/15, C=9-11/15, F<9/15
D3 Baseline: A=all docs have A1+A2+B+C; F=any file missing both A1 and A2
D4 TTFT/TPOT: A=all docs have both rows (N_docs×4 expected); F=any missing both
D5 Overhead: A=all pass; F=any of 3.4/4.6/5.6 shows TPOT decreasing
D6 Novelty: A=5/5 paper-specific, C=3/5
D7 Accuracy section: A=all 34 have section, C=1-3 missing
D8 Matrix: A=34×34 + synergy≥10 + conflict≥3; F<30
D9 Ranking: A=34 ranked with citations, F<25
D10 Spec: A=all 4 cross-checks pass; F=any fabricated number
Structural cap: D3=F OR D10=F → overall capped at C
```

### LoRA FLOPs Reference at r=d/4

```
Dense matmul (d×d): FLOPs = 2d² per token

Case 2 (W_core + A·B unmerged):
  Total: 3d²  ← 1.5× MORE than dense

Case 3 (pure A·B unmerged):
  Total: d²   ← 0.5× of dense (2× FASTER)

CoLA empirical (≤7B): 1.64× TPOT throughput improvement
  1/(0.18 + 0.82/2) ≈ 1.64×  ✓
```

### Layer Pruning Reference Figures (at p=0.75)

```
TTFT: A1 at 8K → ~0.75× baseline ✓  (MLP fraction ≈ 90%)
TPOT (batch=1): ~0.75× baseline ✓   (bandwidth-bound; weight bytes ∝ active layers)

ShortGPT post-hoc (no fine-tune):
  LLaMA 2-7B: 27.1% pruned, MMLU 45.39→43.96 (−3.2% relative)
  LLaMA 2-13B: 24.6% pruned, MMLU 55.00→54.69 (−0.6% relative)

GateSkip (with calibration):
  Llama-3.1-8B at 25% savings: >90% baseline accuracy ✓
  Llama-3.2-1B at 25% savings: sharp quality cliff
```

### Realistic TPOT Improvement (KV Quantization)

| Model | Seq Len | KV BW Before | Weight BW | Realistic INT4 KV TPOT |
|-------|---------|-------------|----------|------------------------|
| A1 (27B Hybrid) | 32K | ~2.0 GB | ~54 GB | ~1.03× |
| A2 (32B Dense) | 32K | ~8.0 GB | ~64 GB | ~1.13× |
| A2 (32B Dense) | 262K | ~68.7 GB | ~64 GB | ~1.63× |
| B (397B MoE) | 32K | ~1.0 GB | ~34 GB (active) | ~1.02× |

### 6-Phase Pipeline Key Invariants

| Invariant | Enforcement |
| ----------- | ------------- |
| `address_review` resolves only explicitly-addressed threads | Parse `{"addressed": [...]}` JSON |
| `ci_driver` runs exactly 1 fix iteration per PR | No internal retry loop |
| `drive-green` runs only on final loop | `if loop == LOOPS:` gate |
| `pr_reviewer` is read-only | No `git push`, no `git commit` |
| Workers never launch for PR-less issues | `_discover_prs()` runs in `run()` before any executor.submit |
| Dry-run suppresses all mutations | Every mutation gated on `not dry_run` |

### Session Scale References

| Session | Metric | Value |
| ------- | ------ | ----- |
| ProjectHephaestus 2026-04-05 | Starting/ending worktrees | 32 → 1 |
| ProjectHephaestus 2026-04-05 | PRs created/merged | 6/6 |
| ProjectTelemachy 2026-04-25 | Issues → remaining | 57 → 6 (89% closure) |
| ProjectTelemachy 2026-04-25 | Total wall clock | ~2.5 hours |
| HomericIntelligence/Odysseus 2026-04-28 | Repos audited / findings | 15 repos / 680 findings |
| Mnemosyne 2026-05-18 | Skill-corpus consolidation | 1,100→690 skills, 17 clusters |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas | 31 AI architecture ideas (sections 1–5 plus 4.7) | Qwen3.5-27B Hybrid, Qwen3-32B Dense, Qwen3.5-397B-A17B MoE baselines |
| ArchIdeas | 4 new ideas (N1–N4) added to 31-idea corpus | research_6_1–6_4 produced by parallel Myrmidon swarms |
| ArchIdeas | 39-idea corpus merge (Phase B) | 195 merged verification files; synthesis docs regenerated |
| ArchIdeas | 39-idea corpus accuracy fix (Phase C) | In-place surgical fixes; Baseline C (K2 Family / LLM360): L=80, d=8192, d_ff=28672 |
| ArchIdeas | 39-idea corpus verdict removal (Phase D) | All PURSUE/INVESTIGATE/DEPRIORITIZE tokens removed; two-wave (17+22) |
| ArchIdeas corpus | 34 ideas, 68 files, 5 artifacts — 10-dimension audit | All 10 dimensions graded with file:line evidence; grade raised B→A |
| ArchIdeas idea 5.1 (TurboQuant) | Per-idea review with 5-agent swarm | Context length mislabel (68.7 GB at 262K labeled "32K"), A1 head_dim error, TPOT overstatement found |
| ArchIdeas corpus | 39-file remediation + inline derivation standard | Background agents failed at ~2M tokens; foreground agents succeeded |
| ArchIdeas corpus | Exec summary honesty — research_6_1_inarch_ar_loop.md | Added TPOT row with warning callout (W × 1.5–2.5× vs +0.18% FLOPs) |
| ProjectHephaestus | 32 worktrees → 1, 6 PRs, 3 skills, 2026-04-05 | Full L0 session: exploration → plan → approval → 3 waves → 2 CI fixes → 3 parallel /learn agents |
| ProjectScylla | 64 issues classified, 12 PRs merged, 2026-04-12 | Myrmidon swarm triage + Phase 7 tracking issue |
| ProjectProteus | 43-issue classification + 20 EASY implementations, 2026-04-25 | TypeScript/Bash/YAML; auto-merge disabled; npm install fix required |
| ProjectTelemachy | 57 → 6 issues (89% closure), 17 PRs, 2026-04-25 | Per-file Sonnet mega-agents; deterministic classification from contention counts |
| HomericIntelligence/Odysseus | Ecosystem-wide strict audit, 15 repos, 680 findings, 2026-04-28 | 15 Epics + child issues; Haiku rate-limit failure at 40+ issues |
| Mnemosyne | 2026-05-18 skill-corpus consolidation (17 clusters) | Mojo mega-cluster sub-PRs \#1808-\#1811 sequential dispatch |
| ProjectHephaestus | 6-phase pipeline design + implementation, 2026-04-24 | 251 tests pass, ruff + mypy clean |
| ProjectScylla | State machine refactor chief architect review implementation, 2026-02-23 | 3 doc/test tasks completed, branch rebased, 72/72 tests passing |
