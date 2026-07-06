---
name: planning-pr-body-extract-sibling-artifact-at-runtime
description: "When planning a PR-open task whose body must embed content produced by an UPSTREAM sibling issue (loss log, benchmark table, verification transcript, dataset checksum), the plan MUST specify a run-time extraction pipeline that pulls the artifact from `gh issue view <sibling> --comments` at execute time, via an explicit placeholder token (e.g. `<<LOSS_LOG>>`) that the create-PR step substitutes; the plan MUST NOT include an illustrative numeric example inline with a hedging note telling the executor to overwrite it. Illustrative values leak into shipped PRs when the hedging note is skimmed. The dependency guard is a TWO-part check: (a) `gh issue view <sibling> --json state -q .state == \"CLOSED\"` AND (b) the sibling's comments contain a well-defined sentinel section (e.g. `## Loss Log`, `## Verification Transcript`, `## Benchmark Results`) that carries the artifact; a CLOSED-as-duplicate or CLOSED-as-wontfix sibling passes (a) but fails (b), and the plan must abort with a specific verdict message on either failure. Use when: (1) planning a `Closes #N` PR-open task where the PR body must cite quantitative evidence produced by a sibling verification/validation task, (2) the PR body template has a section (loss log, benchmark table, checksum) whose CONTENT lives in a dependent issue's comments not in the branch, (3) any planning session where you catch yourself writing example numbers inline with a note saying 'the executor must replace these before creating the PR', (4) a dependent PR-open task where the sibling is `CLOSED` but you have not confirmed the required artifact section actually exists in its comments."
category: architecture
date: 2026-07-02
version: "1.1.0"
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
  - structural-gate-vs-conditional-override
  - paired-sentinel-boundary
  - artifact-property-verification-before-embed
  - monotone-loss-check
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
- You are tempted to write a **conditional prose override** ("if the numeric values above differ from what #N captured, the executing agent must overwrite this block") — this is the exact anti-pattern this skill's v1.1.0 amendment addresses: replace conditional overrides with unconditional structural gates.
- You are extracting a sentinel section from the sibling's comment stream using a next-heading heuristic (`sed -n '/## Loss Log/,/^## /p'`) — this greedily runs to the next `##` or EOF and silently swallows adjacent content. Use a **paired begin/end sentinel** (`## Loss Log` … `## End Loss Log`) instead.
- The plan's PR body asserts a **property** of the extracted artifact ("loss is monotone-decreasing", "N tensors were validated", "exit code was 0", "no warnings emitted") — that property must be verified by a structural check on the extracted artifact BEFORE embedding, not asserted in prose after.

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

# 2. PAIRED-sentinel-guarded artifact extraction (v1.1.0: begin + end markers,
#    not a next-heading heuristic — the sibling task's plan MUST emit BOTH
#    `## Loss Log` and `## End Loss Log`):
begin="## Loss Log"
end="## End Loss Log"
gh issue view "$sibling" --comments --json comments -q '.comments[].body' \
  > /tmp/sibling_comments.md

grep -qxF "$begin" /tmp/sibling_comments.md || { echo "ABORT: sibling #$sibling missing begin sentinel '$begin'"; exit 1; }
grep -qxF "$end"   /tmp/sibling_comments.md || { echo "ABORT: sibling #$sibling missing end sentinel '$end' (unbounded section)"; exit 1; }

awk -v b="$begin" -v e="$end" '
    $0 == b {f=1; next}
    $0 == e {f=0}
    f {print}
' /tmp/sibling_comments.md > /tmp/artifact.md

[ -s /tmp/artifact.md ] || { echo "ABORT: extracted artifact between sentinels is empty"; exit 1; }

# 3. PROPERTY VERIFICATION (v1.1.0) — verify structural claims about the
#    artifact BEFORE embedding it in the PR body. Any prose claim in the PR
#    body of the form "loss is monotone-decreasing" / "N tensors validated" /
#    "no warnings" MUST be paired with a check here that fails the plan if
#    the property does not hold.
#
# Example: monotone-decreasing loss check (assumes loss is the LAST column
# of each row; adjust to your artifact format):
awk 'NR==1 {p=$NF; next} {if ($NF > p) {print "NON-MONOTONE at line " NR ": " $NF " > " p; exit 1} p=$NF}' /tmp/artifact.md \
  || { echo "ABORT: #$sibling loss series not monotone-decreasing — PR body claim is false"; exit 1; }

# 4. Substitute placeholder in PR body template:
grep -q '<<LOSS_LOG>>' pr-body.md.template || { echo "ABORT: placeholder token missing from template"; exit 1; }
sed -e "/<<LOSS_LOG>>/{
    r /tmp/artifact.md
    d
}" pr-body.md.template > pr-body.md

# 5. STRUCTURAL GATE (v1.1.0) — no placeholder survived into body. This is
#    the UNCONDITIONAL gate that replaces the R0 conditional-prose override
#    ("if these values differ, the executor must overwrite this block").
grep -q '<<' pr-body.md && { echo "ABORT: unsubstituted placeholder remains — executor MUST NOT proceed"; exit 1; }

# 6. Open PR:
gh pr create --body-file pr-body.md --title "..." --label "..."
```

### Detailed Steps

1. **In the plan document**, define the PR body template as a file the executing agent will materialize. Every value the executor cannot derive from the branch itself becomes a `<<TOKEN>>` placeholder (all-caps, angle-bracketed twice, distinct from `${VAR}` shell syntax).
2. **Never** include example numeric values inline. Not even with a hedging note. Reviewers may skim the hedge and treat the example as truth; executors may forget to replace it. A missing placeholder MUST fail the create-PR step, so the failure mode is loud.
3. Define the **sibling-artifact extraction** as a two-part guard: (a) state check (`state == CLOSED`), (b) sentinel-section presence in comments. Both must pass — a CLOSED-as-duplicate or CLOSED-as-wontfix sibling passes (a) but fails (b).
4. Choose the **sentinel section heading** to match what the sibling task's PLAN specifies as its deliverable — e.g. if the sibling is a "validation task" whose deliverable is "post a `## Loss Log` comment on the issue," the sentinel is `## Loss Log`. Sentinel names should be documented in a plan glossary so upstream planners know the expected section names.
5. Add a **final substitution guard** that greps the assembled body for any surviving `<<` before invoking `gh pr create` — a leaked placeholder is a broken PR body, not a shipping incident.
6. **In review**, the substitution log (which artifact came from which sibling comment) should be captured in the PR body itself as a footnote so the merge reviewer can audit provenance without re-running the pipeline.

### Structural Gates > Conditional Overrides (v1.1.0)

An instruction of the form "*if X differs from Y, the executor MUST do Z*" is a **conditional-override** gate: it only fires if the executor NOTICES the mismatch. Executors skim. Reviewers skim. Conditional gates fail silently the moment attention lapses.

Replace every conditional-override in the plan with an **unconditional structural gate** — a check that fires regardless of executor attention:

| Conditional (weak) | Structural (strong) |
| ---- | ---- |
| "if the loss values above differ from #5526's, the executor MUST overwrite this block" | `<<LOSS_LOG>>` + render script `grep -q '<<' pr-body.md && exit 1` |
| "if the file list above is not exhaustive, the executor MUST update it" | `<<CHANGED_FILES>>` + render step `git diff --name-only <base>...HEAD > /tmp/files` + gate on token |
| "if the referenced compat wrapper is missing, the executor MUST use SKIP=" | `[ -x scripts/compat.sh ] || export SKIP=<hook-id>` up-front, no conditional prose |

The rule: if you catch yourself writing "if X, the executor MUST Y" in a plan, either **remove the illustrative differing content entirely** (so nothing NEEDS to be replaced) OR **replace it with a placeholder + gate that fails when unresolved**.

### Paired Sentinel Boundaries (v1.1.0)

A sentinel section that starts at `## Loss Log` and runs "until the next `##` heading OR end of file" is a **next-heading heuristic**. Two failure modes:

1. **Greedy over-capture** — if the sibling's comment stream has no other `##` heading after the log, extraction runs to EOF and silently swallows unrelated adjacent content (signature lines, review discussion, edit history).
2. **Silent truncation** — if the sibling's task appends closing prose using an unexpected `##` heading (e.g. `## Notes`), extraction stops early and drops the tail of the log.

Fix: require the sibling task's plan to emit a **paired begin + end sentinel** (`## Loss Log` … `## End Loss Log`). The extractor is `awk` with an explicit end-match. The guard step (see Quick Reference §2) `grep -qxF`s for BOTH sentinels before extracting; missing either sentinel is an ABORT with a message identifying which is missing. This makes the section boundary EXPLICIT in the sibling issue's contract, not inferred by heuristic in the consumer.

### Property Verification Before Embed (v1.1.0)

Any prose claim in the PR body about a **property** of the extracted artifact — "loss is monotone-decreasing", "all N tensors passed", "exit code was 0", "no warnings emitted", "the checksum matches", "count of failures is 0" — is a claim that will be evaluated by the merge reviewer as fact. If the property does not hold on the actual extracted artifact, the PR body is lying (even if unintentionally), and the reviewer will NOGO.

Fix: for every property claim, add a **structural check** on the extracted artifact BEFORE substituting it into the PR body. If the check fails, ABORT with `Verdict: BLOCKED | Reason: <property> does not hold on artifact from #<sibling>`.

Common structural checks:

- **Monotone-decreasing** (loss, error, time-to-convergence): `awk 'NR==1 {p=$NF; next} {if ($NF > p) exit 1; p=$NF}' artifact.md`
- **Count-N**: `[ "$(wc -l < artifact.md)" -eq N ]`
- **Exit code 0**: extract exit-code line; `grep -q '^exit_code: 0$' artifact.md`
- **No warnings**: `! grep -qE '^(WARN|WARNING|W:)' artifact.md`
- **Checksum match**: `sha256sum -c expected.sha256 < artifact.md`

The check runs at PLAN-render time (before `gh pr create`), so property violations block the PR from opening — the falsehood never reaches a reviewer.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 planning session: include an illustrative loss log block (`epoch 0 | step 0 | loss = 6.9412 …`) inline in the PR body template, with a hedging note telling the executor to overwrite it from `gh issue view 5526 --comments` before creating the PR. | Two failure modes: (a) a reviewer skimming the plan may treat the numbers as real and evaluate the PR's claims against them, (b) an executing agent may skip the hedging note and ship the example values into the PR body. The hedge is silent enforcement — silent enforcement is not enforcement. | Never include example quantitative values inline in a plan for PR body content. Use a `<<TOKEN>>` placeholder whose absence fails the create-PR step loudly. |
| Attempt 2 | Guard only on `state == CLOSED` for the sibling issue before extracting the artifact. | A CLOSED-as-duplicate sibling passes state check but has no `## Loss Log` section; the extraction yields an empty file that gets silently substituted into the PR body. | Guard is TWO parts: state check AND sentinel-section presence in comments. Both must pass. |
| Attempt 3 (v1.1.0) | ProjectOdyssey #5527 R0 plan: use conditional-prose override in the PR body template — "*if the numeric values above differ from what #5526 captured, the executing agent must overwrite this block*" — alongside illustrative loss values. | The conditional gate only fires if the executor notices the mismatch. R0 reviewer NOGO'd because the illustrative content plus prose override is functionally identical to "shipping fabricated numbers with a note asking the reader to be careful." | Replace conditional-override prose with an UNCONDITIONAL structural gate: use `<<TOKEN>>` placeholder + render-time `grep -q '<<' pr-body.md && exit 1` gate that fails regardless of executor attention. Structural gates > conditional overrides. |
| Attempt 4 (v1.1.0) | ProjectOdyssey #5527 R0 plan: extract the sibling's loss log using `sed -n '/## Loss Log/,/^## /p'` — a next-heading heuristic. | Two silent failure modes: (a) if the sibling's comment has no subsequent `##`, extraction runs to EOF and swallows adjacent content (review chatter, edit history); (b) if the sibling appends `## Notes` immediately after, extraction stops early and truncates the log. Either way the substituted content is wrong and the PR body claims cannot be trusted. | Require the sibling task's plan to emit a PAIRED begin + end sentinel (`## Loss Log` … `## End Loss Log`). Extract with `awk` on the explicit end-match. Guard `grep -qxF`s for BOTH sentinels before extracting. |
| Attempt 5 (v1.1.0) | ProjectOdyssey #5527 R0 plan: assert in the PR body that the loss log "confirms decreasing loss" without running a monotonicity check on the extracted artifact. | The claim is evaluated by the reviewer as a fact about the artifact; if the artifact does not satisfy the claim, the PR body is (unintentionally) false and the reviewer NOGO's on false verification claims. | For every property claim in the PR body ("monotone-decreasing", "count of N", "exit code 0", "no warnings"), add a structural check on the extracted artifact BEFORE substitution. On failure: `Verdict: BLOCKED | Reason: <property> does not hold on artifact from #<sibling>`. Never assert in prose without a matching structural check. |

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
| ProjectOdyssey | Issue #5527 R1 revision (2026-07-02) — v1.1.0 amendment: R0 plan NOGO'd on conditional-override prose, next-heading sentinel heuristic, and unverified monotone-loss claim. R1 replaced all three with placeholder tokens + paired sentinels + structural property checks. Corrective pattern documented, not yet exercised end-to-end on a real PR. | See ProjectOdyssey issue #5527 R0 NOGO verdict and R1 verdict for the delta. |

## References

- [audit-remediation-verify-evidence-before-planning](audit-remediation-verify-evidence-before-planning.md) — sibling skill about verifying audit evidence before planning; this skill covers the run-time-extraction analogue for PR bodies.
- [planning-pr-body-numeric-claims-source-derived](planning-pr-body-numeric-claims-source-derived.md) — companion skill for quantitative claims the executor derives from source at run time.
- [planning-pr-open-file-scope-via-git-diff](planning-pr-open-file-scope-via-git-diff.md) — companion skill for file-path claims.
- [planning-pr-open-load-bearing-assumption-hygiene](planning-pr-open-load-bearing-assumption-hygiene.md) — companion skill for probing repo settings and reading referenced compat scripts.
- [planning-self-identified-defects-must-be-fixed-not-noted](planning-self-identified-defects-must-be-fixed-not-noted.md) — meta-rule sibling: a plan that self-flags defects (illustrative content + hedge) and does not fix them is a NOGO. This skill is the domain-specific fix for sibling-artifact content.
