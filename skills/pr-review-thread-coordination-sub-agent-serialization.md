---
name: pr-review-thread-coordination-sub-agent-serialization
description: "Coordinating a small batch (2-5) of independent PR review-thread fixes by dispatching one sub-agent per thread. Use when: (1) a PR has multiple open review comments/threads and you want to fix them without one sub-agent stepping on another's edit, (2) two or more of the threads touch the SAME file — dispatch those sequentially, not in parallel, (3) a thread's fix is a one-line test-assertion or docstring change that a cheap (haiku-tier) sub-agent can safely execute, (4) you need to verify each sub-agent's edit landed correctly before running the full test/lint/type-check gate and committing, (5) deciding between running N agents in parallel Task calls vs. one after another for a small (<=5) review-comment batch."
category: tooling
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pr-review
  - review-thread
  - sub-agent-dispatch
  - parallel-dispatch
  - same-file-serialization
  - file-ownership
  - haiku
  - trust-but-verify
  - test-assertion-strengthening
  - tautological-comparison
  - docstring-clarity
  - constructor-parity
  - integration-gate
  - small-batch-review-fix
---

# PR Review Thread Coordination: Sub-Agent Serialization

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Address 4 review threads on a worker-pool PR (ProjectHephaestus #1838, issue #1812) by dispatching one sub-agent per thread, without any two agents corrupting each other's edits. |
| **Outcome** | All 4 threads addressed (tautological self-comparison fixed, missing constructor parameter added, barrier assertion strengthened, misleading docstring clarified); 132 tests pass; mypy/ruff clean; one signed commit. |
| **Verification** | verified-local |

## When to Use

- A PR carries 2-5 open review threads/comments and you want to fix them without a full swarm-scale orchestration (contrast with `parallel-agent-swarm-dispatch-patterns.md`, which targets 5+ agent audit/epic-scale fan-outs).
- Two or more of the threads target the SAME file (e.g., a test file gets both an assertion-strength fix and an unrelated docstring fix) — parallel dispatch on that file risks one agent overwriting the other's edit or committing a stale copy.
- A thread's required fix is small and mechanical enough for a haiku-tier sub-agent (fix a tautological assertion, add a missing constructor parameter, clarify a docstring) — not a design decision.
- You need an explicit verify-before-commit step: read back each edited file (or re-run the specific test) before running the full gate suite, so a sub-agent's silent no-op or partial edit is caught early.
- Deciding whether to fan out N Task calls in one message (parallel) or dispatch them one at a time (sequential) for a small review-thread batch.

## Verified Workflow

### Quick Reference

```text
1. Enumerate every review thread and the exact file each one touches.
2. Group by file:
     - Threads on DISTINCT files -> dispatch their fixer sub-agents in the SAME
       message (parallel Task/Agent calls).
     - Threads on the SAME file -> dispatch those sub-agents ONE AT A TIME
       (wait for each to finish before starting the next), even if they are
       logically independent fixes.
3. After each sub-agent reports done, Read the file it touched and confirm the
   exact line changed as described — do not trust a "done" report alone.
4. Once all threads are addressed, run the full integration gate ONCE
   (unit tests + mypy + ruff), not per-thread.
5. Commit all fixes together with one signed commit.
```

### Detailed Steps

#### 1. Classify each thread by file, not by "logical independence"

Two review comments can be logically unrelated (a test-assertion fix and a docstring fix)
but still collide if they land in the same file. Two sub-agents both opening
`tests/unit/automation/test_worker_pool.py` in parallel — one to strengthen an assertion at
line 717, one to fix a fixture at a different line — risk a last-write-wins overwrite if
either agent re-reads and rewrites the whole file rather than doing a surgical edit, or if
both commit from independent working copies. Build the file map FIRST:

```text
Thread 1: test_jobs.py:110            (tautological self-comparison)
Thread 2: conftest.py:51              (missing lock_dir param)
Thread 3: test_worker_pool.py:717     (weak barrier assertion)
Thread 4: worker_pool.py:170          (misleading docstring)
```

All four files above are DISTINCT, so all four fixer sub-agents were dispatched in parallel.
Had two threads landed in the same file, those two would have been serialized: dispatch the
first, wait for it to complete and be verified, THEN dispatch the second against the
now-updated file.

#### 2. Model tier: haiku is fine for a single, explicitly-scoped mechanical fix

Each of the four fixes was a single-line or single-block, unambiguous change with the exact
before/after text known up front (from the reviewer's comment):

- `assert h1 == h1` -> `assert h1 is h1` (fixes a self-comparison that's tautologically true
  regardless of `__eq__` correctness; `is` tests identity as the test intended).
- Add `lock_dir` parameter to `FakeWorkerPool.__init__` to match the real class's constructor
  signature (parity — a test double that silently drifts from the real signature masks
  constructor-arg regressions).
- Strengthen `assert failures >= 1` to `assert failures == 2` — the concurrent-barrier test
  actually forces exactly 2 workers to fail; "at least 1" would still pass if only 1 failed,
  hiding a regression that weakens the barrier to allow partial failure.
- Clarify a docstring that described `WorkerPool._run`'s exception handling ambiguously —
  the real behavior distinguishes `Exception` (job-level, caught and reported) from
  `BaseException` (propagates, e.g. `KeyboardInterrupt`/`SystemExit`), and the old docstring
  conflated the two layers.

This is the model-tier decision axis from `parallel-agent-swarm-dispatch-patterns.md` Part 4
applied at small scale: MECHANICAL fix with explicit rules -> haiku is fine. None of these
required judgment about what the RIGHT fix is (the reviewer already specified it); the
sub-agent's job was purely to apply it and re-verify.

#### 3. Verify synchronously before running gates

After each sub-agent reports its edit done, `Read` the exact file (or the specific
line range) to confirm:

- The prescribed before-text is gone.
- The prescribed after-text is present, at the right location.
- No stray whitespace/formatting change crept in beyond the intended edit.

Do this BEFORE running the full test suite — a bad edit surfaces immediately as a diff
mismatch, rather than as a confusing test failure 5 minutes later after all 4 agents have
already run.

#### 4. Run the full integration gate ONCE, after all threads are addressed

Do not run the gate suite per-thread. Batch all fixes, verify each individually via `Read`,
then run:

```bash
pixi run pytest tests/unit -v
pixi run mypy
pixi run ruff check hephaestus/ tests/
```

once, across the combined diff. This mirrors the PR-review-loop principle (see
`pr-review-loop-orchestration-agent-patterns.md`) that pre-push validation must cover the
FULL PR diff, not just the most-recently-edited file.

#### 5. Commit all fixes together, signed

One signed commit covering the full batch of review-thread fixes is preferable to one commit
per thread when the fixes are all responses to the same PR review round — it keeps the PR
history readable and maps 1:1 to "addressed round N of review."

### Relationship to existing skills

- `parallel-agent-swarm-dispatch-patterns.md` Part 2 (File Ownership) and Part 7 (Hot-File
  Bundling) establish the general principle that same-file work must serialize. This skill
  is the small-batch (2-5 thread), review-fix-specific application of that principle, where
  the "files" are individual PR review comments rather than GitHub issues or audit findings.
- `pr-review-loop-orchestration-agent-patterns.md` covers the AUTOMATED review loop's own
  code (commit-gated resolution, GO/NO-GO convergence, thread-matching by id). This skill
  covers the ORCHESTRATOR-side workflow for a human/agent manually addressing a batch of
  review comments on one PR — a lighter-weight sibling concern, not a modification to the
  automated loop's internals.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|----------------|-----------------|
| None this session | All 4 threads were classified as touching distinct files up front, so full parallel dispatch was correct on the first attempt; no serialization was actually needed in this instance | N/A | The classification step (file map) is worth doing even when it turns out every thread is on a distinct file — it's what LICENSES parallel dispatch with confidence, not a mere formality |

## Results & Parameters

### Session outcome (ProjectHephaestus PR #1838 / issue #1812, 2026-07-04)

| Thread | File | Fix | Model tier |
|--------|------|-----|------------|
| 1 | `tests/unit/automation/test_jobs.py:110` | `assert h1 == h1` -> `assert h1 is h1` | haiku |
| 2 | `tests/unit/automation/conftest.py:51` | Added missing `lock_dir` param to `FakeWorkerPool.__init__` | haiku |
| 3 | `tests/unit/automation/test_worker_pool.py:717` | `assert failures >= 1` -> `assert failures == 2` | haiku |
| 4 | `hephaestus/automation/worker_pool.py:170` | Clarified `_run` docstring: `Exception` (caught, reported) vs. `BaseException` (propagates) | haiku |

- Dispatch shape: all 4 files distinct -> full parallel dispatch (no serialization needed).
- Verification: each edit read back and confirmed before running gates.
- Gate result: 132 tests pass; mypy and ruff clean across the full tree.
- Commit: one signed commit covering all 4 fixes.

### Tautological self-comparison pattern (general)

```python
# BEFORE (tautologically true regardless of __eq__ correctness):
assert h1 == h1
# AFTER (tests object identity, which is what "same object" tests actually mean):
assert h1 is h1
```

A self-comparison via `==` against the SAME variable is always true if `__eq__` is reflexive
(the default for most objects, and required by the `__eq__` contract) — it provides zero
signal about whether `__eq__` is implemented correctly. If the intent is "this is the exact
same object" use `is`; if the intent is "two independently-constructed values compare equal"
use two DIFFERENT variables (e.g. `h1 == h2` where both were built from the same inputs).

### Constructor-parity pattern for test doubles

When a production class gains a new constructor parameter, every `Fake*`/`Mock*` test double
standing in for it must gain the same parameter (even if unused in the fake's body) — otherwise
callers that pass the new parameter positionally or by keyword against the fake will not
catch a real signature drift, and the fake silently diverges from what it doubles for.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1838 (issue #1812, epic #1809) | Worker pool for agent sessions, build/test, and git operations; 4 review threads addressed via parallel haiku-tier sub-agent dispatch (all threads on distinct files); 132 tests pass, mypy/ruff clean, one signed commit (verified-local) |
