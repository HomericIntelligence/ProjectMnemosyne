---
name: planning-normalize-liveness-at-fetch-layer
description: "When a pure classifier / state-machine consumes a fact object assembled from an external API, derive the minimal orthogonal signals at the FETCH / normalization layer so no contradictory or ambiguous combination can reach the classifier — don't push a raw over-rich fact bag (e.g. `pr_number` + `pr_is_open` + `pr_is_merged` as three independent fields) into the classifier and then rely on it to guard every impossible combination. Use when: (1) designing a pure classifier that consumes a facts dataclass built from GitHub / a DB / any external API, (2) the fact object carries an identifier field PLUS separate boolean liveness flags that can combine into a state the classifier doesn't explicitly handle, (3) a plan reviewer flags a 'falls through / silently misclassifies' path for an edge combination (closed PR, draft PR, deleted-but-cached row), (4) you are tempted to add a guard clause inside a pure function to reject an 'impossible' input — normalize upstream instead, (5) reconstructing in-memory queues from a durable journal (GitHub-as-journal) where the fetch layer already exists and can collapse states cheaply, (6) any 'make illegal states unrepresentable' boundary-normalization decision. This is a plan-review NOGO finding on ProjectHephaestus #1813 (pipeline seeding + admission control), not a shipped fix."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - planning
  - pure-classifier
  - state-machine
  - fetch-layer-normalization
  - make-illegal-states-unrepresentable
  - producer-boundary
  - liveness-signal
  - github-pr-state
  - facts-dataclass
  - plan-review-nogo
  - silent-misclassification
  - total-function
  - pipeline-seeding
  - admission-control
---

# Planning: Normalize Liveness at the Fetch Layer (Not in the Classifier)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | When a pure classifier / state-machine consumes a fact object, derive the minimal orthogonal signals at the FETCH / normalization layer so no contradictory or ambiguous combination can reach the classifier. Do NOT push a raw, over-rich fact bag (e.g. `pr_number` + `pr_is_open` + `pr_is_merged` as three independent fields) into the classifier and rely on it to guard every impossible combination. |
| **Outcome** | **This is a plan-review finding, not a shipped fix.** A plan reviewer graded ProjectHephaestus issue #1813 (pipeline seeding + admission control) NOGO because the proposed `IssueFacts` design modeled GitHub PR state as three independent fields, letting a CLOSED/abandoned (non-merged) PR fall through the classifier's branch order and get silently re-queued to IMPLEMENTATION. The revised plan adopts fetch-layer normalization: the `seed_issue` fetcher yields `pr_number=None` for any PR that is neither open nor merged, so the pure classifier only ever receives one of {no live PR, open PR, merged PR}. The impossible 4th combination cannot reach the classifier at all. |
| **Verification** | verified-local — surfaced by a plan-review NOGO on ProjectHephaestus #1813; the fetch-layer normalization was adopted in the revised plan. It was NOT executed end-to-end in CI. This skill records a design lesson from plan review, not a merged implementation. |
| **Live observation that motivated this** | A reviewer NOGO'd a plan whose `classify_issue` branch order was `merged→FINISHED`, `open→(CI\|PR_REVIEW)`, else fall through to ordered-rank state-label logic. A closed PR (`pr_number!=None`, `pr_is_open=False`, `pr_is_merged=False`) falls THROUGH to the rank branch and, if the issue still carries `state:implementation-*` (or `>= plan-go`), gets SILENTLY re-queued to IMPLEMENTATION even though it already had a (dead) PR. The classifier never "sees" that a PR existed. |

## When to Use

- Designing a pure classifier / state-machine that consumes a "facts" dataclass assembled from an external API (GitHub, a DB, etc.).
- The fact object carries an identifier field PLUS separate boolean liveness flags (e.g. `pr_number` + `pr_is_open` + `pr_is_merged`) that can combine into a state the classifier doesn't explicitly handle.
- A plan reviewer flags a "falls through / silently misclassifies" path for an edge combination — a closed PR, a draft PR, a deleted-but-cached row.
- You are tempted to add a guard clause inside a pure function to reject an "impossible" input — consider normalizing upstream instead.
- Reconstructing in-memory queues from a durable journal (GitHub-as-journal) where the fetch layer already exists and can collapse states cheaply.
- Any "make illegal states unrepresentable" boundary-normalization decision, where the cheapest place to collapse the ambiguity is the producer, not each consumer.

**Don't use when:**

- The fact object is already a closed sum type (an enum / tagged union) that cannot express the contradiction — the illegal state is already unrepresentable and there is nothing to normalize.
- The extra fields are genuinely orthogonal and every combination is meaningful to the classifier — collapsing them would lose information the classifier needs.
- There is exactly one consumer and the "guard" is a one-liner that will never be duplicated — though even then, prefer the fetch layer so a second consumer inherits the collapse for free.

## Verified Workflow

*(Verified-local: this is a plan-review design decision on ProjectHephaestus #1813, adopted in the revised plan. It has not been executed end-to-end in CI.)*

### Quick Reference

```text
SMELL:  a pure classifier receives  id + is_open + is_merged  (three
        independent fields) and you find yourself writing
        `if pr_number is not None and not open and not merged: ...`
        inside the classifier to handle the "closed PR" case.

FIX:    collapse the ambiguity at the FETCH layer. The fetcher surfaces
        an identifier as a LIVE signal only when it is genuinely live.
        A PR that is neither open nor merged surfaces as pr_number=None
        ("no PR"). The classifier then receives only representable states.

RULE:   normalize at the producer boundary; defend nothing at the consumer.
        A pure classifier stays pure and TOTAL (every input → exactly one
        output) only if its input type cannot express contradictions.
```

### Detailed Steps

1. **Name the ambiguous combination explicitly.** In #1813 the four combinations of `(pr_is_open, pr_is_merged)` for a non-null `pr_number` are: `(F,F)` closed/abandoned, `(T,F)` open, `(F,T)` merged, `(T,T)` impossible. The classifier explicitly handled merged and open; `(F,F)` and `(T,T)` were unhandled and fell through.

2. **Trace where the unhandled combination lands.** Follow the branch order. In #1813 a closed PR fell through `merged→FINISHED` and `open→(CI|PR_REVIEW)` into the ordered-rank state-label branch, which re-queued the issue to IMPLEMENTATION if it still carried `state:implementation-*` (or ranked `>= plan-go`). The dead PR was invisible to the classifier — a silent misclassification baked into the FACT DESIGN, not a bug in one branch.

3. **Move the collapse to the fetch / normalization layer.** Change the fetcher (`seed_issue`) so an identifier surfaces as a live signal only when it is genuinely live. A PR that is neither open nor merged yields `pr_number=None` ("no PR"). Now the classifier's input can only express {no live PR, open PR, merged PR}.

4. **Confirm the classifier is now TOTAL.** Every input maps to exactly one output because the input type can no longer express the contradiction. No downstream guard is needed — the impossible/ambiguous 4th state cannot reach the classifier at all. This is "make illegal states unrepresentable" applied at the layer boundary.

5. **Apply the same collapse to every consumer path.** The normalization lives once in the fetcher, so both seeding AND restart reconstruction (queue rebuild from the GitHub journal) inherit it for free. Do not re-derive liveness at each call site.

6. **Watch for the recurring smell in review.** If you find yourself adding `if pr_number is not None but not open and not merged` (or any "reject the impossible input") guard inside a pure function, stop — that guard must be repeated at every consumer. Move the collapse to the fetch layer instead.

This pattern complements `architecture-github-labels-as-state-vocabulary` — that skill covers the ordered-rank pure-classifier that reads mutually-exclusive `state:*` labels; this skill covers making the OTHER inputs to that same classifier (the PR liveness signals) unable to express a contradiction. Where a consumer must instead branch on a genuinely closed sum type, see `exception-discriminator-enums-state-machine-pola` for keeping that dispatch total and POLA-compliant.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Over-rich fact bag pushed to the classifier: `IssueFacts` carried `pr_number: int\|None`, `pr_is_open: bool`, `pr_is_merged: bool` as three independent fields, and `classify_issue` handled `merged→FINISHED`, `open→(CI\|PR_REVIEW)`, else fell through to ordered-rank state-label logic. | A CLOSED PR (`pr_number!=None`, open=False, merged=False) falls THROUGH to the rank branch and, if the issue still carries `state:implementation-*` (or ranks `>= plan-go`), gets SILENTLY re-queued to IMPLEMENTATION even though it already had a (dead) PR. The classifier never sees the PR existed. Reviewer graded it NOGO. | Don't let the input type express contradictions. A silent misclassification baked into the FACT DESIGN is worse than a bug in one branch — it has no single line to fix. |
| 2 | Proposed fix "just add an `if pr_number is not None and not open and not merged` guard inside `classify_issue`" to reject the closed-PR combination. | Keeps the classifier impure and branchy, and the guard must be repeated everywhere the facts are consumed — seeding AND restart reconstruction (queue rebuild from the GitHub journal). Two copies of the same guard drift out of sync. | Normalize once at the fetch layer, not N times at each consumer. A guard inside the pure function is the smell that the collapse belongs upstream. |
| 3 | Treat a draft PR (or a deleted-but-cached PR row) as "has a PR" because `pr_number` is non-null. | Same failure class: a draft PR is not a live CI/review signal, but a non-null `pr_number` makes the classifier believe work is in flight. The 4th/5th combinations multiply as the fact schema grows. | The collapse rule generalizes: an identifier surfaces as a LIVE signal only when the entity is genuinely live (open or merged). Everything else → `pr_number=None`. One rule at the fetcher covers closed, abandoned, and draft-not-counted alike. |

## Results & Parameters

### The Corrected Design (Fetch-Layer Collapse)

`seed_issue(...)` normalizes so a PR surfaces to the classifier only when it is genuinely live; `classify_issue(facts)` then receives only {no live PR, open PR, merged PR} and is TOTAL.

| `pr_is_open` | `pr_is_merged` | Raw combination | Surfaced `pr_number` | Classifier sees |
|:---:|:---:|-----------------|:---:|-----------------|
| `False` | `False` | closed / abandoned (or draft-not-counted) | `None` | no live PR |
| `True`  | `False` | open PR | the real number | open PR → CI \| PR_REVIEW |
| `False` | `True`  | merged PR | the real number | merged PR → FINISHED |
| `True`  | `True`  | impossible (API can't return this) | `None` | no live PR (unreachable) |

The pure classifier is now **TOTAL**: every input maps to exactly one output, because the input type can no longer express the contradiction. No downstream guard is required.

### Fetch-Layer Collapse (Python Sketch)

```python
def _surface_pr_number(pr_number: int | None, pr_is_open: bool, pr_is_merged: bool) -> int | None:
    """Surface a PR to the classifier only when it is a LIVE signal.

    A PR that is neither open nor merged (closed / abandoned /
    draft-not-counted) collapses to None — "no live PR" — so the pure
    classifier can never receive the ambiguous 4th combination.
    """
    if pr_number is None:
        return None
    if pr_is_open or pr_is_merged:
        return pr_number
    return None  # closed / abandoned — treat as "no PR"


def seed_issue(raw: RawGitHubIssue) -> IssueFacts:
    """Normalization / fetch layer: derive minimal orthogonal signals."""
    return IssueFacts(
        number=raw.number,
        state_label=raw.state_label,          # ordered-rank vocabulary
        pr_number=_surface_pr_number(         # <-- collapse happens HERE
            raw.pr_number, raw.pr_is_open, raw.pr_is_merged
        ),
        pr_is_open=raw.pr_is_open,
        pr_is_merged=raw.pr_is_merged,
    )


def classify_issue(facts: IssueFacts) -> PipelineState:
    """Pure, TOTAL classifier — receives only representable states."""
    if facts.pr_number is not None and facts.pr_is_merged:
        return PipelineState.FINISHED
    if facts.pr_number is not None and facts.pr_is_open:
        return PipelineState.CI if facts.ci_running else PipelineState.PR_REVIEW
    # No live PR: fall through to ordered-rank state-label logic — and a
    # closed PR can NEVER reach here as a live signal, so no guard needed.
    return _classify_by_state_rank(facts.state_label)
```

The same `seed_issue` normalization is reused by restart reconstruction (rebuilding the in-memory queue from the GitHub-as-journal), so both seeding and restart inherit the collapse from one place.

### The Principle (Generalized)

- **Prefer normalizing at the producer boundary over defending at the consumer.** A pure classifier stays pure and total only if its input type cannot express contradictions.
- **The smell:** an `if id is not None but not open and not merged` (or any "reject the impossible input") guard inside a pure function. That guard must be repeated at every consumer.
- **The fix:** move the collapse to the fetch/normalization layer. Make illegal states unrepresentable at the layer boundary; every downstream consumer inherits it for free.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | plan-review NOGO on issue #1813 (pipeline seeding + admission control); fetch-layer normalization adopted in the revised plan | plan-review finding, verified-local. The `seed_issue` fetcher yields `pr_number=None` for any PR that is neither open nor merged, so the pure `classify_issue` receives only {no live PR, open PR, merged PR}. Not executed end-to-end in CI. |
