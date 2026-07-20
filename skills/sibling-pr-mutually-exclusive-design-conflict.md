---
name: sibling-pr-mutually-exclusive-design-conflict
description: "Use when: (1) two OPEN pull requests each individually pass CI and diff cleanly against `main`, but implement mutually incompatible designs for the same subsystem (e.g. one PR removes an aggregator job another PR's tests assert must exist); (2) reviewing/landing a PR that touches a shared architectural surface (a CI aggregator/gate job, a shared config schema, a ruleset/branch-protection contract) and a sibling PR touching the same surface is also open; (3) deciding whether standard two-dot (`origin/main..branch`) review is sufficient before merging when a sibling PR on the same subsystem exists — it is NOT, because that view only proves compatibility with `main`, never with the sibling; (4) planning to merge one of two competing-design PRs and needing to prove the OTHER one doesn't silently rot into a design the merged one just invalidated; (5) a merge-queue, aggregator-job, or gate-workflow redesign is in flight via multiple parallel PRs from different authors or sessions."
category: ci-cd
date: 2026-07-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pr-review
  - sibling-pr
  - merge-conflict
  - design-conflict
  - merge-queue
  - aggregator-job
  - two-dot-diff-blind-spot
  - merge-simulation
  - ci-cd-architecture
  - homericintelligence
  - achaeanfleet
---

# Two Green Sibling PRs Can Implement Mutually Incompatible Designs — Diff-Against-Main Cannot Detect It

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-19 |
| **Objective** | During an ecosystem-wide merge-queue rollout, decide how to land two open AchaeanFleet PRs (#725 and #730) that both touched the same CI aggregator design. |
| **Outcome** | Discovered #725 deleted the `merge-gate` aggregator job (the `needs:`-fan-in job that produces one required context reused by both PR-side and `merge_group`-side events) and renamed the smoke job, while #730 simultaneously hardened a test asserting that exact aggregator contract must exist. Both PRs were individually green against `main` — neither's own CI or two-dot diff exposed the conflict, because each was consistent with `main` in isolation; the incompatibility only existed BETWEEN the two branches. Resolved by explicit user decision to keep the already-merged aggregator design (#724) and close #725 as superseded. |
| **Verification** | verified-local — confirmed by checking out #730's branch and simulating a merge of #725 onto it (`git merge --no-commit --no-ff <725-branch>`), which produced a real content conflict on `_required.yml` and a test failure that neither PR's own CI run had ever surfaced, since neither PR's CI tests against the other's tree. |

## When to Use

- Two or more OPEN PRs touch the same architectural surface — a CI aggregator/gate job, a shared
  schema, a branch-protection/ruleset contract, a shared config file with implied invariants — and
  each is individually green.
- Before recommending "merge this PR, it's green and clean," when you know or suspect a sibling PR
  on the same subsystem also exists and is open.
- A repo's CI redesign (merge-queue migration, gate-workflow restructuring, aggregator-job rename)
  is happening across multiple PRs, especially from different authors, sessions, or agents that
  aren't aware of each other's in-flight work.
- Deciding whether it's safe to land PR A and leave PR B open for later — verify B still makes sense
  against the tree A will produce, not just against `main` as it stands today.

## Verified Workflow

### Quick Reference

```bash
# Standard two-dot review (origin/main..branch) proves ONLY "this PR is consistent with main
# as it stands right now." It proves NOTHING about consistency with a sibling PR's branch,
# even when both target the same subsystem and both are individually green.

# To actually detect a design conflict between two open sibling PRs:
git fetch origin pr-a-branch pr-b-branch
git checkout -b sim-merge pr-a-branch
git merge --no-commit --no-ff origin/pr-b-branch
# A real CONTENT conflict here proves incompatibility that neither PR's own CI caught.
# Absence of a content conflict does NOT prove design compatibility — also run the
# resulting tree's own test suite; a semantic conflict (B's test asserts a contract
# A's changes remove) can merge cleanly at the text level while still being broken.
uv run pytest tests/ -k <relevant-subsystem-tests>   # or the repo's equivalent
git merge --abort   # this was a throwaway simulation, not a real merge
git branch -D sim-merge
```

### Detailed Steps

1. **Recognize that CI passing on each sibling PR individually is not evidence of mutual
   compatibility.** Each PR's CI run tests that PR's branch merged with `main` — never merged with
   the OTHER open PR's branch. Two branches can each be a perfectly valid evolution of `main` while
   being mutually exclusive with each other.
2. **Two-dot (`origin/main..branch`) and three-dot (`origin/main...branch`) diffs share this blind
   spot** — both compare a single branch against `main`; neither one involves the sibling branch at
   all. (See the related `pr-review-two-dot-vs-three-dot-diff` entry: that skill picks the right
   lens for a STALE branch's relationship to `main`; this entry is about a DIFFERENT axis — a
   branch's relationship to another, equally-current sibling branch. Both matter; neither subsumes
   the other.)
3. **When you know two open PRs touch the same subsystem, explicitly simulate the merge.** Check out
   one branch, run `git merge --no-commit --no-ff <other-branch>`, and inspect the result — both for
   literal text conflicts AND, if it merges cleanly at the text level, for whether the combined tree
   still makes semantic sense (run the affected test suite against the simulated merge). A test
   added by PR B that specifically asserts a contract PR A's changes remove is the clearest
   fingerprint: it may not conflict textually (different files, or non-overlapping hunks in the same
   file) while still being a real design conflict.
4. **Abort the simulation cleanly afterward** (`git merge --abort`, delete the scratch branch) — it
   exists only to surface the conflict, not to become a real merge commit.
5. **Once a genuine design conflict is confirmed, it needs a human decision, not an automated
   resolution.** Which design wins is an architectural choice (which aggregator pattern, which
   ruleset semantics), not something a reviewer should silently pick a side on. Present both designs
   and their tradeoffs, then act on the explicit choice — in the verified case, the user chose to
   keep the already-landed aggregator pattern (#724) and close the conflicting PR (#725) as
   superseded, rather than trying to reconcile the two designs into a hybrid.
6. **After resolving, re-verify the KEPT PR still passes cleanly** — closing the conflicting sibling
   doesn't retroactively fix anything in the surviving PR; confirm its CI is still green and its own
   tests (including any hardened by the closed sibling's now-abandoned direction) still hold.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|----------------|-----------------|
| Reviewed #725 and #730 independently, each against `origin/main` | Standard two-dot diff review, confirmed each PR green in isolation | Both looked mergeable individually; the conflict only existed BETWEEN them, invisible from either single-branch view | When two open PRs touch the same architectural surface, review them AS A PAIR (merge-simulate one onto the other) in addition to reviewing each against main |
| Assumed "both PRs are green" meant "no conflict to worry about" | Treated passing CI as sufficient evidence of mergeability | CI green only proves compatibility with `main` at PR-open time, never with a sibling PR's divergent changes to the same subsystem | Green CI on two sibling PRs is necessary but not sufficient for both being simultaneously mergeable; explicitly check subsystem overlap |
| Planned to merge PR A first and "deal with B's conflict when GitHub flags it" | Assumed GitHub's own mergeability check (MERGEABLE/CONFLICTING) would catch the issue once A landed | GitHub's mergeability check only detects TEXTUAL conflicts after the fact; a semantic conflict (B's test still passes syntactically against a tree where its asserted contract no longer holds) can merge without GitHub ever flagging it, and by then it's a broken `main` post-merge instead of a caught pre-merge issue | Proactively simulate the merge BEFORE landing either PR when you know they share a subsystem, rather than relying on GitHub's post-hoc conflict detection |

## Results & Parameters

- **Reproduced on:** AchaeanFleet PR #725 vs PR #730 (both touching the CI merge-queue aggregator
  design — `.github/workflows/_required.yml` and `tests/test_merge_queue_readiness.py`).
- **Simulation method:** checked out #730's branch, ran `git merge --no-commit --no-ff` with #725's
  branch — surfaced a real conflict on `_required.yml` plus a test (`test_merge_queue_readiness.py`)
  that #730 had just hardened to assert the exact `merge-gate` aggregator contract #725 deleted.
- **Resolution:** explicit user decision to keep the already-merged aggregator design (landed via
  PR #724) and close #725 as superseded by that design; #730's hardened test was correct against the
  kept design and required no further change.
- **General rule verified:** when two open PRs are known to touch the same architectural surface,
  neither PR's own CI, nor a two-dot/three-dot diff of either against `main`, is sufficient evidence
  of mutual compatibility — only an explicit merge simulation (or equivalent cross-branch review)
  surfaces the conflict before it becomes a post-merge break.

### Related skills

- `pr-review-two-dot-vs-three-dot-diff` — covers the orthogonal single-branch-vs-main diff-lens
  choice; useful background but does not cover the cross-branch sibling-PR case this entry addresses.
- `planning-cross-pr-interface-dependency` — covers planning a capstone PR against sibling issues'
  DECLARED (not-yet-merged) interfaces; related in spirit (unmerged siblings) but addresses planning
  a NEW PR against future interfaces, not detecting an existing conflict between two ALREADY-OPEN PRs.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| AchaeanFleet PR #725 vs #730 | Ecosystem-wide merge-queue rollout; two open PRs independently modifying the same CI aggregator design | verified-local; merge-simulation (`git merge --no-commit --no-ff`) surfaced both a textual conflict on `_required.yml` and a semantic conflict on the aggregator contract that neither PR's own CI run had detected; resolved via explicit user decision to keep #724's design and close #725 |
