---
name: verify-delegated-agent-claims-run-full-suite
description: "Don't trust a sub-agent's success report for a delegated git/rebase/refactor task — independently re-verify the load-bearing claims (merge-base re-parented, main-only symbols present, actual return values), and run the FULL test suite locally from the worktree cwd before pushing a merge candidate. Use when: (1) an Opus/Sonnet sub-agent reports 'rebased onto main, all tests pass, force-pushed' and you are about to trust it, (2) CI keeps failing on a DIFFERENT test each round after a delegated rebase/refactor, (3) you are validating a merge candidate with a hand-picked test subset, (4) a path-relative test gives a false failure because you ran from the wrong checkout."
category: tooling
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [delegation, sub-agent, rebase, verification, full-suite, worktree, merge-base, ci-cost]
---

# Verify Delegated Agent Claims and Run the Full Suite Before Pushing

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-27 |
| **Objective** | Break the cycle where a delegated rebase/refactor sub-agent reports success but CI fails on a different test each round, by independently re-verifying structural/behavioral claims and running the full suite locally before pushing |
| **Outcome** | Cycle broken once claims were independently verified and the entire unit suite (4926 tests) was run once from the worktree cwd, catching all remaining stale-assertion failures at once |
| **Verification** | verified-ci |

## When to Use

- A sub-agent (especially an Opus rebase/conflict-resolution or refactor agent) reports "rebased onto main, all tests pass, force-pushed" and you are about to wait on CI trusting that report.
- CI keeps failing on a DIFFERENT test each round after a delegated rebase/refactor — a sign the agent's structural claim was wrong and/or you are testing the wrong subset.
- You are about to validate a merge candidate by running only the specific tests you THINK are affected.
- A path-relative test produces a false failure because the full suite was run from the main repo root instead of the worktree root.

## Verified Workflow

### Quick Reference

```bash
# After a delegated rebase/refactor agent reports success, BEFORE trusting it:
# 1. Re-verify structural claims independently (don't trust the report):
git fetch origin
git merge-base origin/main origin/<branch>      # MUST equal: git rev-parse origin/main
git show origin/<branch>:<file> | grep -c <main-only-symbol>   # MUST be > 0 (branch contains main)

# 2. Verify behavioral claims by RUNNING the contract, not reading the summary:
pixi run python -c "from <mod> import f; assert f()==<expected>"   # e.g. per-phase values

# 3. Run the FULL suite from the WORKTREE cwd (what CI runs), not a subset, BEFORE pushing:
cd <worktree-root> && pixi run pytest tests/unit/ -q --no-cov -p no:cacheprovider \
  --ignore=<known-network-hang-files>
#    A subset hides stale tests that only the full run exercises; one full local run
#    catches what would otherwise be N sequential CI failures.
```

### Detailed Steps

1. **Re-verify the rebase actually re-parented.** Compare `git merge-base origin/main origin/<branch>` against `git rev-parse origin/main`. If they differ, the branch never re-parented onto main — the agent's "rebased onto main" claim is false regardless of what its summary says.
2. **Confirm main-only symbols are present on the branch.** `git show origin/<branch>:<file> | grep -c <main-only-symbol>` must be > 0. This proves the branch actually contains the main commits it claims to, catching half-applied rebases and dropped commits.
3. **Verify behavioral claims by executing the contract.** Do not read the agent's summary to confirm a value regression was fixed — run the function and assert its return value (e.g. per-phase values). Claims like "the value is now X" must be observed, not narrated.
4. **Run the ENTIRE unit suite once from the worktree cwd before pushing.** A hand-picked subset hides stale assertions that only the full run exercises. One full local run catches what would otherwise be N sequential ~18-min CI failures, each surfacing a different test.
5. **Run from cwd == the worktree root**, never the main repo root, so path-relative tests (`Path(__file__).parents[N]`) resolve against the correct checkout instead of giving a false failure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusted the agent's report | Trusted a sub-agent's "rebased onto main, force-pushed, all green" report and waited on CI | The rebase had not re-parented (merge-base still stale) / had a half-applied regression; CI failed; multiple wasted ~20-min CI rounds | Independently re-verify a delegated agent's structural claims (merge-base, main-only symbol present, actual return values) before believing "success" |
| Tested only the affected subset | Validated each fix by running only the SPECIFIC tests I thought were affected | Each CI round failed on a DIFFERENT stale test I hadn't run locally (test_planner_loop, then test_implementer, ...) | Before pushing a merge candidate, run the FULL unit suite once from the worktree cwd; partial subsets hide stale tests and turn one local run into N CI round-trips |
| Ran full suite from wrong cwd | Ran the full suite but from the MAIN repo root | A worktree-relative path test gave a false failure (parents[N] resolved to the wrong checkout) | Run the full suite with cwd == the worktree root so path-relative tests scan the right tree |

## Results & Parameters

**Cost framing (why this discipline pays for itself):**

- Each CI round on ProjectHephaestus is ~18 min for the unit matrix.
- Trusting unverified agent reports + partial local testing turned a 1-step fix into MANY hours (each round surfaced a new, different failure that a single full local run would have caught).
- The corrective discipline is cheap by comparison: a handful of `git merge-base`/`grep`/`python -c` checks plus ONE full-suite run (~4926 tests) from the worktree cwd.

**Copy-paste verification block:**

```bash
git fetch origin
[ "$(git merge-base origin/main origin/<branch>)" = "$(git rev-parse origin/main)" ] \
  && echo "RE-PARENTED OK" || echo "STALE BASE — agent claim FALSE"
git show origin/<branch>:<file> | grep -c <main-only-symbol>   # > 0 required
pixi run python -c "from <mod> import f; assert f()==<expected>; print('VALUE OK')"
cd <worktree-root> && pixi run pytest tests/unit/ -q --no-cov -p no:cacheprovider \
  --ignore=<known-network-hang-files>
```

**Cross-references:** see the sibling skills on rebase re-parenting / merge-base verification (`git-workflow-rebase-worktree-signing`, `pr-rebase-conflict-resolution-patterns`) and on worktree-relative test cwd (`git-worktree-sys-path-precedence-issue`, `python-path-resolution-cwd-resolve-contract`).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | #1657 (2026-06-27) — long multi-round rebase/refactor session where sub-agents repeatedly reported success but CI failed on a different test each round | Cycle broke after independent structural verification + one full-suite run (4926 tests) from the worktree cwd |
