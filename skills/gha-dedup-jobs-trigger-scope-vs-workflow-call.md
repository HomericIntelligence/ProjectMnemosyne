---
name: gha-dedup-jobs-trigger-scope-vs-workflow-call
description: "Use when: (1) two GitHub Actions workflows run the SAME job on every PR (double-billed runner minutes) and you are deciding HOW to de-duplicate — before reflexively reaching for workflow_call extraction, (2) planning a CI DRY-deduplication issue and need a decision rule between trigger-scoping vs workflow_call extraction vs outright deletion, (3) a 'duplicate' workflow ALSO carries a unique schedule:/workflow_dispatch trigger that naive deletion would silently kill, (4) you must confirm whether a duplicated job NAME is even a required branch-protection context before assuming a deletion is safe."
category: ci-cd
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: unverified
history: gha-dedup-jobs-trigger-scope-vs-workflow-call.history
tags:
  - github-actions
  - workflow-deduplication
  - dry
  - workflow-call
  - trigger-scope
  - pull-request-trigger
  - schedule-trigger
  - workflow-dispatch
  - required-status-checks
  - branch-protection
  - rulesets
  - runner-cost
  - kiss
  - planning
---

# GitHub Actions: De-Duplicating Jobs — Trigger-Scope vs workflow_call vs Deletion

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Pick the RIGHT fix when two workflows run identical jobs on every PR: a decision rule among (a) trigger-scoping the `on:` block, (b) job-level `if:` scoping, (c) `workflow_call` extraction, and (d) outright deletion — instead of defaulting to extraction or to a workflow-wide trigger change |
| **Outcome** | For ProjectHephaestus issue #1182 (`security.yml` vs `_required.yml` both running `pip-audit`/`sast` on every PR), the KISS fix is to **add `if: github.event_name != 'pull_request'` to ONLY the duplicate jobs** — because `security.yml` also contains a THIRD job (`license-scan`) that is BLOCKING only on `pull_request`. A workflow-wide trigger change would have silently dropped that gate (got a NOGO). Captured as a planning artifact. |
| **Verification** | unverified — planning artifact only; the plan was NOT executed or confirmed in CI |
| **History** | [changelog](./gha-dedup-jobs-trigger-scope-vs-workflow-call.history) |

## When to Use

- Two workflow files run the **same job** (e.g. `pip-audit`, SAST/`sast`, lint, test) on every PR, so each PR burns double the runner minutes, and you are deciding **how** to de-duplicate.
- You are scoping/planning a CI DRY-deduplication issue and want a decision rule **before** reaching for `workflow_call` extraction (the usual advice — but not always correct).
- A workflow that looks like a pure duplicate **also** has a unique `schedule:` cron or `workflow_dispatch` trigger that a naive delete would silently remove (a regression hidden behind the word "duplicate").
- You need to confirm **which job names are actually required** branch-protection contexts before assuming deleting/scoping a workflow is safe.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end in CI. It is a planning artifact derived from scoping ProjectHephaestus issue #1182; treat every step as a hypothesis until a real CI run confirms it. Verification level: `unverified`. Re-run the `gh api .../rulesets` check at implementation time — rulesets can change between planning and execution.

### Quick Reference

```text
DECISION RULE — pick by structure (not by reflex).
PREREQUISITE: read the WHOLE workflow file end-to-end and ENUMERATE EVERY JOB
first. An audit/issue-supplied line range is a STARTING POINT, not the file's
full extent — a third job hiding below the range is exactly what breaks the
naive fix (see Failed Attempts).

1. OUTRIGHT DELETE the duplicate workflow
   ONLY IF it has NO unique triggers/jobs
   AND its job names are NOT required branch-protection contexts.

2. TRIGGER-SCOPE (narrow the workflow-wide `on:` block, e.g. drop `pull_request`)
   ONLY SAFE IF *EVERY* job in the workflow tolerates losing that event.
   GitHub Actions triggers are WORKFLOW-WIDE, not per-job — you cannot remove
   `on: pull_request` for only some jobs. So this is valid only when the
   duplicate workflow's PR-time jobs are ALL pure duplicates satisfying NO
   required check, AND no OTHER job in the file needs the event.
   GATE: if any single job uniquely needs the event → DO NOT do this; use (3).

3. JOB-LEVEL `if:` SCOPE (the correct granularity when one job needs the event)
   WHEN the duplicate jobs share a file with a UNIQUE job that genuinely needs
   the event you'd otherwise remove. Keep the workflow-wide trigger; add
   `if: github.event_name != 'pull_request'` to ONLY the duplicate jobs.
   The unique job (and the `on:` block) stays untouched. An `if:`-skipped job
   reports neutral/skipped (never failing), so skipping a NON-required job on
   PRs won't block branch protection — but verify the skipped job isn't itself
   a required context.

4. workflow_call EXTRACTION
   WHEN BOTH workflows genuinely must run the SAME job on OVERLAPPING events
   AND the bodies are (or should be) identical — i.e. you can't just scope it.
```

```bash
# Which workflows have a UNIQUE trigger (so deletion would lose something)?
grep -rl "schedule:" .github/workflows/
grep -rl "workflow_dispatch:" .github/workflows/

# Which job NAMES are ACTUALLY required contexts? (run at IMPLEMENTATION time, not just plan time)
gh api repos/$ORG/$REPO/rulesets --jq '.[].id' | while read id; do
  gh api repos/$ORG/$REPO/rulesets/$id \
    --jq '.rules[]?|select(.type=="required_status_checks").parameters.required_status_checks[].context'
done | sort -u
```

### Detailed Steps

The concrete case: `security.yml` and `_required.yml` BOTH ran identical `pip-audit` (dependency scan) and `sast` jobs on every `pull_request`. The instinct is "extract a `workflow_call` callee." That is wrong here. Work the decision rule:

0. **ENUMERATE EVERY JOB IN THE FILE FIRST — read it end-to-end.** Before choosing ANY fix, list every job the workflow defines. The first plan for issue #1182 read only `security.yml:18-96` (the line range the audit supplied) and asserted "only `pip-audit`/`sast` exist." It never read `:97-137`, where a THIRD job — `license-scan`, running `scripts/check_license_compatibility.py` — lived. An audit/issue-supplied line range is a STARTING POINT, not the file's full extent. A workflow-wide trigger change is only safe AFTER you've confirmed NO job in the workflow depends on the event you're removing.

1. **Map WHICH events actually overlap.** The duplication existed **only** on the `pull_request` event. `security.yml` also had a weekly `schedule:` cron **and** `workflow_dispatch` that `_required.yml` lacked. So `security.yml` is NOT a pure duplicate — it carries a unique scheduled scan. `grep -rl "schedule:" .github/workflows/` surfaces this; do it before calling anything a "duplicate."

2. **Confirm WHICH job names are required contexts.** A `gh api .../rulesets` check proved the required contexts were the **`_required.yml`** job names (`security/dependency-scan`, `security/secrets-scan`), NOT the `security.yml` job names. So `security.yml`'s PR-time jobs satisfied **zero** branch-protection checks — pure wasted runner minutes. (Job-name-vs-required-context mismatch is the same class of trap as the slash-in-job-id pitfall; never assume the name you see is the name that's required.)

3. **Check whether the bodies are even identical** (they were NOT here). `security.yml` installed pixi inline via `prefix-dev/setup-pixi` (with a load-bearing anti-stale-cache comment) while `_required.yml` used a `./.github/actions/setup-pixi-env` composite action. A shared `workflow_call` callee would force **one** setup mechanism on both workflows — more surface area and a behavior change, against KISS/YAGNI.

4. **Check the GATE before trigger-scoping: does EVERY job tolerate losing the event?** The first plan said "drop `pull_request` from `security.yml`'s `on:` block." That FAILED the gate. `license-scan` (the third job from step 0) is BLOCKING **only** on `pull_request`: `scripts/check_license_compatibility.py` returns exit 1 when `GITHUB_EVENT_NAME == "pull_request"` and advisory exit 0 otherwise. It exists ONLY in `security.yml`. Removing the workflow-wide `pull_request` trigger to kill the pip-audit/sast double-run would have **silently dropped the only enforcing license-compatibility gate** — a regression. That plan got a **NOGO**. Because GitHub Actions triggers are workflow-wide (you can't remove `on: pull_request` for only some jobs), the trigger-scope option is off the table the moment one job uniquely needs the event.

5. **Apply the corrected KISS fix — job-level `if:` on ONLY the duplicate jobs.** Keep the `pull_request` trigger; add `if: github.event_name != 'pull_request'` to `pip-audit` and `sast` ONLY; leave `license-scan` and the `on:` block untouched. Zero new files, the double-run ends, the unique weekly scan survives, and the license gate still blocks on PRs.

   ```yaml
   # security.yml — BEFORE (all three jobs run on every PR; pip-audit/sast duplicate _required.yml)
   on:
     pull_request:
     schedule:
       - cron: "0 6 * * 1"   # weekly — UNIQUE, _required.yml lacks this
     workflow_dispatch:

   jobs:
     pip-audit:
       runs-on: ubuntu-latest
       # ... duplicate of _required.yml's dependency-scan
     sast:
       runs-on: ubuntu-latest
       # ... duplicate of _required.yml's secrets-scan
     license-scan:                       # UNIQUE: blocking ONLY on pull_request
       runs-on: ubuntu-latest
       # ... runs scripts/check_license_compatibility.py (exit 1 on PRs, advisory otherwise)

   # security.yml — AFTER (PR-time duplication gone; license gate + scheduled scan preserved)
   on:
     pull_request:                       # KEEP — license-scan needs it
     schedule:
       - cron: "0 6 * * 1"
     workflow_dispatch:

   jobs:
     pip-audit:
       runs-on: ubuntu-latest
       if: github.event_name != 'pull_request'   # skip the duplicate on PRs
       # ...
     sast:
       runs-on: ubuntu-latest
       if: github.event_name != 'pull_request'   # skip the duplicate on PRs
       # ...
     license-scan:                       # UNTOUCHED — still runs/blocks on PRs
       runs-on: ubuntu-latest
       # ...
   ```

   An `if:`-skipped job reports `neutral`/`skipped` (never failing), so skipping `pip-audit`/`sast` on PRs is safe and won't block branch protection — **provided** those skipped job names aren't themselves required contexts (here the required contexts live in `_required.yml`, so they aren't). Verify that before relying on it.

6. **Add a REGRESSION GUARD to the acceptance check.** The verification MUST assert that the unique job still runs on the event removed from the others — e.g. awk-assert `license-scan` has NO `if:` before its `runs-on`, and that the `pull_request` trigger is still present in `on:`. A naive `grep pull_request → expect zero matches` acceptance check would have **passed in the exact regression state** (trigger removed = license gate gone). Never write an acceptance check that passes when the regression has occurred — assert the property you want to KEEP, not just the change you made.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Default to `workflow_call` extraction | Reflexively planned to extract the shared `pip-audit`/`sast` jobs into a reusable `_checks.yml` callee and wire both workflows to it | The two job bodies were NOT byte-identical (inline `prefix-dev/setup-pixi` with a load-bearing anti-stale-cache comment vs a `./.github/actions/setup-pixi-env` composite); a shared callee forces ONE setup mechanism on both plus new file + caller wiring | Over-engineering. Trigger-scoping solved it with zero new files. Only extract when both workflows genuinely need the SAME job on OVERLAPPING events and bodies are/should be identical |
| Outright delete `security.yml` as a "duplicate" | Planned to delete the whole workflow since its PR jobs duplicated `_required.yml` | `security.yml` also had a weekly `schedule:` cron + `workflow_dispatch` that `_required.yml` lacked — deletion would silently kill the weekly scheduled scan (a regression) | `grep -rl "schedule:" .github/workflows/` to find UNIQUE triggers before deleting anything called a "duplicate"; delete only if it has NO unique triggers/jobs |
| Assume the duplicate jobs satisfy required checks | Assumed `security.yml`'s `pip-audit`/`sast` jobs were load-bearing required contexts, so any change is risky | `gh api .../rulesets` showed the required contexts were the `_required.yml` job names (`security/dependency-scan`, `security/secrets-scan`), NOT `security.yml`'s — its PR jobs satisfied ZERO required checks (pure waste) | Verify with `gh api repos/$ORG/$REPO/rulesets` which job NAMES are actually required BEFORE assuming a deletion/scope-change is unsafe — and re-run it at implementation time, rulesets drift |
| Drop the PR trigger without auditing the rest of the workflow | Planned to remove `pull_request` from `on:` assuming only the duplicate jobs ran on PRs | `pull_request` under `on:` fires the ENTIRE workflow — another job could secretly depend on the PR trigger | Confirm no other job in the workflow relies on the PR trigger before scoping it away; the trigger is workflow-wide |
| Trigger-scope the whole `on:` block | Removed `pull_request` from security.yml to kill pip-audit/sast double-run | Silently dropped `license-scan` — a third PR-only blocking job in the same file (read only :18-96, missed :97-137) | Enumerate EVERY job before a workflow-wide trigger change; use job-level `if:` when one job uniquely needs the event |
| Acceptance check `grep pull_request → zero matches` | Wrote a verification that asserts the `pull_request` trigger is gone after the fix | That check PASSES in the regression state (trigger removed = license gate dropped) — it would have green-lit the NOGO plan | A regression guard must assert the property you want to KEEP (unique job still runs on the event), never just the change you made |

## Results & Parameters

### Quick Reference

- **Four fixes, by structure (escalating granularity):** outright-delete (no unique triggers AND not a required context) < trigger-scope the whole `on:` block (ONLY if EVERY job tolerates losing the event) < job-level `if:` on only the duplicate jobs (when a unique job in the same file needs the event) < `workflow_call` extraction (both workflows need the same job on overlapping events, bodies identical). Pick the leftmost that applies AND passes its safety gate — it's the KISS option.
- **The trigger-scope safety gate:** a workflow-wide trigger change (`on:`) affects EVERY job; it is safe only after you read the whole file and confirm no job uniquely depends on the event. If one does, drop to job-level `if:` granularity.
- **`security.yml` / `_required.yml` (issue #1182):** the file had THREE jobs — `pip-audit`, `sast`, AND `license-scan` (not two). `license-scan` (runs `scripts/check_license_compatibility.py`; exit 1 only on `pull_request`) is the sole enforcing license gate and exists only here. The first plan (drop the workflow-wide `pull_request` trigger) would have silently dropped it → NOGO. Corrected fix: keep the `pull_request` trigger; add `if: github.event_name != 'pull_request'` to `pip-audit`/`sast` ONLY; leave `license-scan` and `on:` untouched. Zero new files.
- **Verification commands that mattered:** read the WHOLE workflow (don't trust the audit's line range — the missed `:97-137` is what caused the NOGO); `grep -rl "schedule:" .github/workflows/` (find unique triggers); `gh api repos/$ORG/$REPO/rulesets --jq '...required_status_checks[].context'` (confirm which job NAMES are actually required); and a REGRESSION GUARD (awk-assert `license-scan` has no `if:` before `runs-on` and `pull_request` is still in `on:`) — never a `grep pull_request → zero matches` check, which passes in the regression state.

### Uncertain assumptions / risks (re-check before implementing)

- **Not executed/verified in CI.** Verification level is `unverified` — this is a planning artifact only. Confirm on a real PR/run that the double-run actually stops and the scheduled scan still fires.
- **`gh api .../rulesets` output was read at plan time.** Rulesets can change. Re-run the rulesets query at implementation time before assuming `security.yml`'s jobs are non-required.
- **Whether the weekly scheduled scan is genuinely WANTED** (vs. acceptable to delete outright) was assumed, not confirmed with a human. The plan preserved it conservatively (trigger-scope rather than delete).
- **The workflow-wide trigger is the gotcha being exploited.** `pull_request` applies to the whole workflow; confirm no other job in `security.yml` secretly depended on the PR trigger before dropping it. (In issue #1182 one did — `license-scan` — which is why the corrected fix uses job-level `if:` instead of a workflow-wide trigger change.)
- **Trust the file, not the audit's line range.** The NOGO root cause was reading only the issue-supplied `:18-96` and missing `license-scan` at `:97-137`. Always read the workflow end-to-end and enumerate every job before choosing a fix.

### Related skills

- `gha-workflow-authoring-pitfalls` — pitfall #7 (a `pull_request` trigger is workflow-wide; the `changes-gate` `needs:`/`if:` pattern for gating heavy jobs on label/auto-merge events). This skill is the planning-time decision rule for the inverse problem: which workflow should own the PR trigger at all.
- `gha-required-checks-branch-protection` — the verified `workflow_call`-extraction + summary-aggregator pattern, i.e. option 3 of the decision rule above. Reach for that skill once you've decided extraction is the right fix.

## References

- [GitHub Actions: Events that trigger workflows — `pull_request`, `schedule`, `workflow_dispatch`](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [GitHub Actions: Reusing workflows (`workflow_call`)](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub: Managing rulesets and required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
