---
name: planning-pr-body-extract-sibling-artifact-at-runtime
description: "When planning a PR-open task whose body must embed content produced by an UPSTREAM sibling issue (loss log, benchmark table, verification transcript, dataset checksum), the plan MUST specify a run-time extraction pipeline that pulls the artifact from `gh issue view <sibling> --comments` at execute time, via an explicit placeholder token (e.g. `<<LOSS_LOG>>`) that the create-PR step substitutes; the plan MUST NOT include an illustrative numeric example inline with a hedging note telling the executor to overwrite it. Illustrative values leak into shipped PRs when the hedging note is skimmed. The dependency guard is a TWO-part check: (a) `gh issue view <sibling> --json state -q .state == \"CLOSED\"` AND (b) the sibling's comments contain a well-defined sentinel section (e.g. `## Loss Log`, `## Verification Transcript`, `## Benchmark Results`) that carries the artifact; a CLOSED-as-duplicate or CLOSED-as-wontfix sibling passes (a) but fails (b), and the plan must abort with a specific verdict message on either failure. Use when: (1) planning a `Closes #N` PR-open task where the PR body must cite quantitative evidence produced by a sibling verification/validation task, (2) the PR body template has a section (loss log, benchmark table, checksum) whose CONTENT lives in a dependent issue's comments not in the branch, (3) any planning session where you catch yourself writing example numbers inline with a note saying 'the executor must replace these before creating the PR', (4) a dependent PR-open task where the sibling is `CLOSED` but you have not confirmed the required artifact section actually exists in its comments."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pr-body
  - pr-open
  - sibling-task
  - sentinel-section
  - placeholder-token
  - runtime-extraction
  - dependency-guard
  - verification-evidence
  - illustrative-values-hazard
---

# Planning: PR-Body Verification Evidence — Extract From Sibling At Run Time, Never Fabricate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | When a PR-open plan's body must embed an artifact (loss log, benchmark table) produced by an upstream sibling task, extract it at execute time from the sibling issue's comments via a placeholder-substitution pipeline instead of writing illustrative values inline. |
| **Outcome** | PLAN ONLY — captured during a planning session for ProjectOdyssey issue #5527 (PR-open task closing #3187, dependent on sibling validation task #5526). The originating plan included an illustrative loss log block with hedging prose; this skill documents the corrective pattern. Not yet applied end-to-end. |
| **Verification** | unverified |

## When to Use

- Planning a PR-open task whose body must contain quantitative evidence produced by a sibling issue (a training loss log, an inference latency table, a verification transcript, a dataset checksum).
- The PR body is authored by an EXECUTING agent that runs `gh pr create --body-file <path>`; the body template needs a slot filled from data outside the branch.
- You catch yourself in a plan writing "example: epoch 0 | step 0 | loss = 6.9412 …" followed by "the executor must overwrite this with real values from `gh issue view <N> --comments` before creating the PR."
- The dependent sibling issue is `CLOSED` but you have not confirmed the specific artifact section is present in its comments (guards against duplicate/wontfix closures).

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed end-to-end: no PR was opened using the placeholder pipeline in
> this session, no `sed`/`awk` substitution was run against a live sibling issue,
> and CI has not confirmed the sentinel-guard pattern. The example commands are
> derived from `gh` CLI reference behavior and standard shell substitution; test
> each against your specific sibling issue's comment structure before trusting it.

### Quick Reference

```bash
# 1. Dependency guard — TWO parts (both must pass):
sibling=5526
state=$(gh issue view "$sibling" --json state -q .state)
[ "$state" = "CLOSED" ] || { echo "ABORT: sibling #$sibling not CLOSED (state=$state)"; exit 1; }

# 2. Sentinel-guarded artifact extraction:
sentinel="## Loss Log"
gh issue view "$sibling" --comments --json comments -q '.comments[].body' \
  | awk -v s="$sentinel" '
      $0 ~ "^"s"$" {emit=1; print; next}
      emit && /^## / {emit=0}
      emit {print}
    ' > /tmp/artifact.md

[ -s /tmp/artifact.md ] || { echo "ABORT: sibling #$sibling closed but sentinel '$sentinel' not found in comments"; exit 1; }

# 3. Substitute placeholder in PR body template:
grep -q '<<LOSS_LOG>>' pr-body.md.template || { echo "ABORT: placeholder token missing from template"; exit 1; }
sed -e "/<<LOSS_LOG>>/{
    r /tmp/artifact.md
    d
}" pr-body.md.template > pr-body.md

# 4. Final guard — no placeholder survived into body:
grep -q '<<' pr-body.md && { echo "ABORT: unsubstituted placeholder remains"; exit 1; }

# 5. Open PR:
gh pr create --body-file pr-body.md --title "..." --label "..."
```

### Detailed Steps

1. **In the plan document**, define the PR body template as a file the executing agent will materialize. Every value the executor cannot derive from the branch itself becomes a `<<TOKEN>>` placeholder (all-caps, angle-bracketed twice, distinct from `${VAR}` shell syntax).
2. **Never** include example numeric values inline. Not even with a hedging note. Reviewers may skim the hedge and treat the example as truth; executors may forget to replace it. A missing placeholder MUST fail the create-PR step, so the failure mode is loud.
3. Define the **sibling-artifact extraction** as a two-part guard: (a) state check (`state == CLOSED`), (b) sentinel-section presence in comments. Both must pass — a CLOSED-as-duplicate or CLOSED-as-wontfix sibling passes (a) but fails (b).
4. Choose the **sentinel section heading** to match what the sibling task's PLAN specifies as its deliverable — e.g. if the sibling is a "validation task" whose deliverable is "post a `## Loss Log` comment on the issue," the sentinel is `## Loss Log`. Sentinel names should be documented in a plan glossary so upstream planners know the expected section names.
5. Add a **final substitution guard** that greps the assembled body for any surviving `<<` before invoking `gh pr create` — a leaked placeholder is a broken PR body, not a shipping incident.
6. **In review**, the substitution log (which artifact came from which sibling comment) should be captured in the PR body itself as a footnote so the merge reviewer can audit provenance without re-running the pipeline.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 planning session: include an illustrative loss log block (`epoch 0 | step 0 | loss = 6.9412 …`) inline in the PR body template, with a hedging note telling the executor to overwrite it from `gh issue view 5526 --comments` before creating the PR. | Two failure modes: (a) a reviewer skimming the plan may treat the numbers as real and evaluate the PR's claims against them, (b) an executing agent may skip the hedging note and ship the example values into the PR body. The hedge is silent enforcement — silent enforcement is not enforcement. | Never include example quantitative values inline in a plan for PR body content. Use a `<<TOKEN>>` placeholder whose absence fails the create-PR step loudly. |
| Attempt 2 | Guard only on `state == CLOSED` for the sibling issue before extracting the artifact. | A CLOSED-as-duplicate sibling passes state check but has no `## Loss Log` section; the extraction yields an empty file that gets silently substituted into the PR body. | Guard is TWO parts: state check AND sentinel-section presence in comments. Both must pass. |

## Results & Parameters

### Configuration

```yaml
plan-pattern:
  pr-body:
    template-path: pr-body.md.template
    placeholders:
      - token: "<<LOSS_LOG>>"
        source:
          type: sibling-issue-comment
          sibling: 5526
          sentinel-section: "## Loss Log"
    guards:
      pre-extract:
        - sibling.state == CLOSED
        - sibling.comments contains sentinel-section
      post-substitute:
        - "no `<<` tokens remain in assembled body"
```

### Expected Output

- If sibling is OPEN → abort with `ABORT: sibling #<N> not CLOSED (state=OPEN)`.
- If sibling is CLOSED but sentinel absent → abort with `ABORT: sibling #<N> closed but sentinel '## Loss Log' not found in comments`.
- If PR body template is missing the placeholder token → abort with `ABORT: placeholder token missing from template` (guards against a plan revision that removed the token).
- If any `<<` remains after substitution → abort with `ABORT: unsubstituted placeholder remains`.
- On success → `gh pr create` runs against a body with real, provenance-traceable artifact content, no hedging prose, no illustrative fabrications.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5527 planning session (2026-07-02) — captured the anti-pattern (illustrative loss log block in plan) that motivated this skill; corrective pattern PLAN ONLY, not executed. | See ProjectOdyssey issue #5527 comments for the originating plan. |

## References

- [audit-remediation-verify-evidence-before-planning](audit-remediation-verify-evidence-before-planning.md) — sibling skill about verifying audit evidence before planning; this skill covers the run-time-extraction analogue for PR bodies.
- [planning-pr-body-numeric-claims-source-derived](planning-pr-body-numeric-claims-source-derived.md) — companion skill for quantitative claims the executor derives from source at run time.
- [planning-pr-open-file-scope-via-git-diff](planning-pr-open-file-scope-via-git-diff.md) — companion skill for file-path claims.
- [planning-pr-open-load-bearing-assumption-hygiene](planning-pr-open-load-bearing-assumption-hygiene.md) — companion skill for probing repo settings and reading referenced compat scripts.
