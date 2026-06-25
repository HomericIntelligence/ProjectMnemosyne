---
name: gha-trigger-paths-filter-planning-checklist
description: "Planning-time checklist for any change that adds, removes, or edits a GitHub Actions trigger-filter list (`paths:`, `paths-ignore:`, `branches:`, event-type lists) — especially audit-driven one-line YAML edits. Use when: (1) an audit finding (S15 Compliance / license-scan / NOTICE / SBOM) asks you to add a path to a workflow's `pull_request.paths:` filter, (2) you are tempted to quote workflow YAML from an audit excerpt without `Read`-ing the file, (3) the plan cites a downstream script as 'consuming' the new path without grepping the script for that filename, (4) the plan defers verification to a post-merge throwaway PR instead of self-testing in-PR, (5) the workflow has both `pull_request:` and `push:` (or `merge_group:`) triggers and you've only edited one, (6) the workflow may have `paths-ignore:` instead of (or alongside) `paths:`, (7) the job is non-blocking / advisory so trigger bugs rot silently with no CI signal."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - github-actions
  - workflow-trigger
  - paths-filter
  - paths-ignore
  - merge-group
  - push-trigger
  - planning
  - planning-checklist
  - audit-driven-remediation
  - license-scan
  - notice
  - compliance
  - non-blocking-job
  - uncertain-assumptions
---

# GHA Trigger Paths-Filter Planning Checklist

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture a durable planning-time checklist for changes that add/remove/edit a GitHub Actions trigger filter list (`paths:`, `paths-ignore:`, `branches:`, event-types) — particularly the one-line audit-driven YAML edits ("add `'NOTICE'` to the license-scan `pull_request.paths:` filter") that look trivial but routinely ship with unverified assumptions. |
| **Outcome** | A 6-item pre-plan checklist (Read the file, grep the downstream consumer, scan for `paths-ignore:`, check the symmetric `push:` trigger, check for `merge_group:`, prefer in-PR self-test over post-merge throwaway PR) plus a Failed Attempts table of the planning shortcuts that have produced NOGOs in the past. |
| **Verification** | **unverified** — captured BEFORE the originating ProjectHephaestus issue #1517 plan was implemented or CI-validated. Treat every recommendation as a hypothesis. The complementary `gha-workflow-authoring-pitfalls` skill covers verified workflow-authoring rules; this skill is the planning-stage checklist that runs BEFORE you commit to a YAML edit. |

## When to Use

Use this checklist BEFORE you finalize a plan that touches any trigger-filter list in
`.github/workflows/*.yml`. The classic triggering audit finding looks like:

> S15 Compliance: `security.yml` license-scan `pull_request.paths:` filter omits `NOTICE`.
> PRs that touch only `NOTICE` do not trigger the license-scan job.

The fix appears to be a one-line YAML addition. It is — but the planning around it routinely
makes one or more of these unverified assumptions:

1. The exact lines/quote-style in the audit excerpt match the file on disk.
2. The downstream script the audit names actually reads the file you are adding.
3. There is no `paths-ignore:` block that would override or conflict with `paths:`.
4. The workflow's `push:` trigger has matching semantics, or isn't relevant.
5. Branch protection does not use a merge queue (`merge_group:` event).
6. Verification can be deferred to a post-merge "manual one-shot" PR.

This skill is a complement to (NOT a replacement for) `gha-workflow-authoring-pitfalls`
(workflow-authoring rules), `ci-required-check-path-filter-pitfall` (path-filtering a
*required* workflow is a different trap), and `license-scan-marker-excluded-fallback`
(license-scan script-level fallbacks). If your situation also matches one of those, read
them too — they are orthogonal.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. It was
> captured BEFORE the originating ProjectHephaestus issue #1517 plan was implemented or
> CI-confirmed. Verification level: `unverified`. Treat every step as a hypothesis until a
> real PR proves the trigger fires as expected on a NOTICE-only diff (and continues to fire
> on the previously-covered paths).

### Quick Reference — the 6-item pre-plan checklist

Run all six BEFORE you write the plan body. Each item is a tool call, not a thought
experiment.

```bash
# 1. READ the workflow file. The audit excerpt is NOT the file.
#    Confirm line numbers, quote style ('NOTICE' vs "NOTICE"), key order,
#    indentation, and whether the trigger uses paths: or paths-ignore:.
#    (Use your repo-aware Read tool; falling back to:)
sed -n '1,40p' .github/workflows/security.yml

# 2. GREP the downstream consumer for the filename. If the audit says
#    "scripts/check_license_compliance.py consumes NOTICE," prove it.
grep -nE "NOTICE|notice_path|open\\(.*NOTICE" scripts/check_license_compliance.py

# 3. SCAN for paths-ignore: at every level of the workflow. paths: and
#    paths-ignore: are mutually exclusive per trigger; if both are present
#    on the same event, behavior is not additive.
grep -nE "paths-ignore:|paths:" .github/workflows/security.yml

# 4. CHECK the symmetric push: trigger. A pull_request.paths: edit does
#    NOT change push-trigger behavior. If the audit cares about main-branch
#    coverage (e.g., for cron/release artifacts), the push: block needs its
#    own edit (or its own deliberate absence).
grep -nE "^on:|pull_request:|push:|schedule:|merge_group:|workflow_dispatch:" \
  .github/workflows/security.yml

# 5. CHECK for merge_group: events. If branch protection uses merge queues,
#    merge_group is a separate trigger and does NOT honor pull_request.paths:.
gh api repos/:owner/:repo/rules/branches/main 2>/dev/null \
  | grep -E "merge_queue|required_status_checks"

# 6. PLAN an IN-PR self-test, not a post-merge throwaway PR. Include a
#    one-character touch to the newly-added path (e.g., a trailing newline
#    on NOTICE) in the SAME PR as the trigger-list edit, so the PR itself
#    proves the job fired on the new path. Drop the touch in a final
#    "revert test touch" commit before merge, or leave it (it's harmless).
```

### Detailed Steps and Durable Insights

#### 1. The audit excerpt is NOT the file — `Read` before you quote

Audit reports lift snippets out of context. They strip surrounding `paths-ignore:`,
sibling triggers, and comments. A plan that quotes "lines 3-13" from the audit can ship
with the wrong quote style (`"NOTICE"` vs `'NOTICE'`), wrong indentation, or — worst —
miss a `paths-ignore:` block that overrides the change. The cost of opening the file is
five seconds; the cost of merging a plan that doesn't match the file on disk is one full
review cycle.

#### 2. The "downstream script consumes this file" claim must be grepped, not assumed

If the audit says "scripts/check_license_compliance.py reads `NOTICE`," prove it before
you cite it in your plan. The causal chain "script reads NOTICE → paths must include
NOTICE" is plausible but unverified. The script may read `pyproject.toml` and never touch
`NOTICE`; it may read `NOTICE` via a path constant that itself isn't covered by the audit
finding. Cite the grep hit (file:line) in the plan body — that single line of evidence
converts the plan from "assertion" to "claim with proof."

#### 3. `paths:` and `paths-ignore:` are mutually exclusive per trigger

Per GitHub's docs: if both `paths:` and `paths-ignore:` are present on the same trigger
event, GitHub uses `paths:` and ignores `paths-ignore:`. They are NOT additive. If the
workflow has `paths-ignore:` only, adding `paths:` is a behavior change beyond just the
new entry — it inverts the filter from deny-list to allow-list. Scan for both keys before
proposing an edit to either.

#### 4. The symmetric `push:` trigger has its own paths semantics (or absence)

`on.pull_request.paths:` is event-scoped. Editing it does NOT change what happens on
`push:` to main. If the workflow has:

```yaml
on:
  pull_request:
    paths: ['pyproject.toml', 'requirements*.txt']  # you add 'NOTICE' here
  push:
    branches: [main]                                # no paths: at all → runs on every push
```

…then post-merge the license-scan still runs on every main push regardless of NOTICE.
That's often the intended behavior, but flag it in the plan so the reviewer doesn't have
to figure it out. If the `push:` block ALSO has a `paths:` filter, you usually want to
add the same path to BOTH (or document why not).

#### 5. `merge_group:` is a separate event — `pull_request.paths:` does not cover it

If the repo uses GitHub merge queues, `merge_group` events are a distinct trigger. They
do NOT inherit `pull_request.paths:` semantics. A workflow that's required at merge time
via the merge queue but path-filtered on `pull_request:` can behave unexpectedly. For
ProjectHephaestus today this is likely not relevant (no merge queue configured), but the
audit-checklist value of checking once is high. Confirm with:

```bash
gh api repos/:owner/:repo/rules/branches/main \
  --jq '.[] | select(.type=="merge_queue")'
```

#### 6. Prefer in-PR self-test over post-merge "manual one-shot" PR

A plan that says "after merge, open a NOTICE-only test PR to verify the trigger fires"
is a plan that will not be verified. The discipline rarely survives merge — the issue
closes, the verification PR is never opened, and the next time anyone notices the bug is
the next audit. Instead, include a one-character touch to the newly-added path in the
SAME PR as the YAML edit. The PR itself runs the modified workflow, the Actions tab shows
the job firing for the new path, and the evidence lives in the PR record forever. If you
want to keep the diff cosmetically clean, revert the touch in a final commit.

#### 7. Non-blocking jobs rot silently — flag the absence of CI signal

If the job in question is non-blocking (e.g., `continue-on-error: true`, or simply not in
the branch-protection required-checks list), a bad trigger filter has NO immediate CI
signal. A path-filter typo that excludes 90% of PRs will not turn anything red. The job
just stops running. Add a one-line note to the plan: "license-scan is non-blocking, so
a regression here will not surface in CI — verify the trigger fires before merge."

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| Quote the workflow YAML from the audit excerpt | Plan body included a 10-line YAML snippet copied from the audit report as the "current state" of the file | Audit excerpt used double-quotes; file used single-quotes; the proposed Edit failed `old_string` matching → reviewer NOGO ("plan does not match repo") | Always `Read` the actual file before quoting. The audit excerpt is a paraphrase, not the source of truth |
| Cite the downstream script without grepping | Plan asserted "scripts/check_license_compliance.py consumes NOTICE so the paths filter must include it" | Reviewer asked for the file:line; the planner had inferred it from the audit headline. The script DID read NOTICE — but the planner had no evidence at plan time → NOGO until proof was added | Grep the consumer for the filename; cite file:line in the plan body. Plausible causal chains are not evidence |
| Defer verification to a post-merge throwaway PR | Plan included a one-liner: "After merge, open a NOTICE-only PR to verify the trigger fires" | The verification PR was never opened. Next audit re-found the same issue → infinite-loop remediation | Self-test in-PR: include a one-character touch to the newly-added path in the same PR as the YAML edit. The Actions tab is the evidence |
| Edit only `pull_request.paths:`, leave `push:` alone | Plan added `'NOTICE'` to `pull_request.paths:` without checking the symmetric `push:` block | `push:` block had its own `paths:` filter that also omitted NOTICE → main-branch coverage still broken after merge → second remediation PR needed | Always check BOTH `pull_request:` AND `push:` (and `schedule:`, `workflow_dispatch:`, `merge_group:`) trigger paths semantics. Edit both or explicitly document why only one |
| Miss `paths-ignore:` interaction | Plan added `paths:` to a workflow that already had `paths-ignore:` | GitHub silently dropped `paths-ignore:` (mutually exclusive per trigger). Trigger semantics inverted from deny-list to allow-list, accidentally narrowing the trigger to ONLY the new entry | Grep for both `paths:` and `paths-ignore:` on every trigger event before editing either; understand the mutual-exclusion rule |
| Assume no merge queue | Plan ignored `merge_group:` because "we don't use merge queues" | Repo had silently enabled a merge queue 3 months earlier; `merge_group` events ran the workflow without `pull_request.paths:` filtering → all PRs ran the heavy job in the queue regardless of path | Check `gh api repos/:owner/:repo/rules/branches/main` for `merge_queue` once at plan time. It's a 1-second tool call that prevents a class of surprise |
| Treat a non-blocking job as low-risk | Plan downplayed the change because "license-scan is advisory" | Non-blocking → no CI signal when the trigger filter rotted. The bug shipped and stayed shipped for 6 months until the next compliance audit | Non-blocking jobs need MORE planning rigor, not less, because they have no immediate failure signal. Add an explicit "no CI signal on regression" note to the plan |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Originating repo/issue** | HomericIntelligence/ProjectHephaestus, issue #1517 (audit S15 Compliance: `security.yml` license-scan `paths:` filter omits NOTICE) |
| **Change class** | One-line addition of `'NOTICE'` to `on.pull_request.paths:` in a non-blocking workflow |
| **Verification level** | `unverified` — captured BEFORE plan implementation or CI confirmation |
| **Complement skills** | `gha-workflow-authoring-pitfalls` (verified workflow-authoring rules), `ci-required-check-path-filter-pitfall` (path-filtering a REQUIRED workflow is a different trap), `license-scan-marker-excluded-fallback` (license-scan SCRIPT-level fallbacks, not trigger-level), `audit-remediation-verify-evidence-before-planning` (general audit-finding verification discipline) |

### The reviewer-facing assumption inventory (copy-paste into plan body)

For an `on.pull_request.paths:` filter edit, list these explicitly under "Uncertain
Assumptions" in the plan body, with the tool-call evidence for each:

| # | Assumption | Tool call that resolves it | Plan body line |
|---|------------|----------------------------|----------------|
| 1 | Workflow file content matches the audit excerpt | `Read .github/workflows/<wf>.yml` | "Confirmed against file on disk at SHA `<sha>`" |
| 2 | The downstream consumer actually reads the new path | `grep -n <filename> scripts/<consumer>.py` | "Consumer reads \<filename> at `scripts/<consumer>.py:<line>`" |
| 3 | No `paths-ignore:` is present | `grep -nE "paths-ignore:" .github/workflows/<wf>.yml` | "No `paths-ignore:` present (or: present, see resolution X)" |
| 4 | Symmetric `push:` trigger has compatible semantics | Manual workflow inspection | "`push:` block has no `paths:` → already covers; OR `push.paths:` also needs the edit" |
| 5 | No `merge_group:` event in use | `gh api repos/:owner/:repo/rules/branches/main` | "No `merge_queue` rule configured" |
| 6 | Self-test will run in-PR | Include a touch to the new path in the same PR | "PR includes `touch <newpath>` to exercise the new trigger" |
| 7 | Job is blocking / non-blocking | `gh api repos/:owner/:repo/branches/main/protection --jq '.required_status_checks.contexts'` | "Job is non-blocking (not in required-checks list) → trigger regressions have no CI signal" |

### Decision matrix — pull_request.paths vs push.paths vs merge_group

| Coverage need | `pull_request.paths:` | `push.paths:` (main) | `merge_group:` |
|---------------|----------------------|---------------------|----------------|
| Pre-merge PR check | YES — edit | n/a | n/a |
| Post-merge main scan | n/a | YES — edit (or omit `paths:` entirely for "run on every push") | n/a |
| Merge-queue gating | n/a | n/a | YES — `merge_group` event does not honor pull_request paths |
| Nightly / scheduled | n/a (use `schedule:`) | n/a | n/a |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1517 — planning artifact for audit S15 Compliance fix | Add `'NOTICE'` to `.github/workflows/security.yml` `on.pull_request.paths:`. Plan was written but NOT executed end-to-end at the time of skill capture; verification level `unverified`. The skill captures the planning anti-patterns surfaced while drafting the plan, before any in-PR or CI evidence existed |
