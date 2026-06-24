---
name: gha-workflow-concurrency-controls
description: "Choosing GitHub Actions `concurrency:` controls when ADDING them to event-driven workflows that currently lack them — selecting the `group` key and `cancel-in-progress` value per the workflow's trigger and its side-effect idempotency. The ONE decision rule: `cancel-in-progress: true` for idempotent / supersede-able runs (tests, scans, idempotent label POSTs — newest event wins), `cancel-in-progress: false` for non-idempotent publishers that must not be interrupted mid-flight (git tag push, PyPI publish, GitHub release creation). Group-key selection scopes the serialization: `github.event.issue.number` (+ `github.run_id` fallback) for per-issue, `github.ref` for per-tag (distinct tags publish in parallel, same tag never double-publishes), `github.head_ref || github.ref` (NOT `github.sha`) for PR scans so successive pushes collapse. Use when: (1) a workflow has no `concurrency:` block and you must pick `group`/`cancel-in-progress` by trigger, (2) deciding whether cancelling a run is safe — gate it on side-effect idempotency not convenience, (3) a publish/release workflow needs serialization without over- or under-serializing across tags, (4) PR-scan concurrency must collapse rapid successive pushes (use head_ref, NOT sha), (5) confirming `${{ github.* }}` in a `concurrency.group` does NOT introduce a workflow-injection sink (it is a YAML-key context expr, not a `run:` interpolation), (6) confirming a workflow you are editing is NOT a pinned required status-check context before assuming branch-protection interaction."
category: ci-cd
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: unverified
history: gha-workflow-concurrency-controls.history
tags:
  - github-actions
  - concurrency
  - cancel-in-progress
  - concurrency-group
  - idempotency
  - publish-workflow
  - pypi-publish
  - git-tag-push
  - github-release
  - github-ref
  - github-head-ref
  - github-sha
  - pr-scan
  - per-issue-serialization
  - per-tag-serialization
  - workflow-injection
  - context-expression
  - required-status-checks
  - branch-protection
  - planning
  - unverified-assumptions
  - verify-dont-assert
  - side-effect-idempotency
---

# GitHub Actions Workflow Concurrency Controls (Group Key + Cancel-in-Progress Selection)

**History:** [changelog](./gha-workflow-concurrency-controls.history)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-23 |
| **Objective** | Capture the durable decision rules for adding a `concurrency:` block to event-driven GitHub Actions workflows that lack one — how to choose the `group` key and the `cancel-in-progress` value from the workflow's trigger and the idempotency of its side effects. Surfaced while PLANNING (ProjectHephaestus, issue #1548 plan) the addition of `concurrency:` to four workflows: a per-issue automation workflow, a release/publish workflow, an auto-tag workflow, and a PR-scan workflow. |
| **Outcome** | Hypothesis only — the plan was NOT implemented and NOT CI-verified. The author read each target workflow file ONCE; no edit was applied and no CI run confirmed the chosen keys behave as reasoned. Verification stays `unverified`. The decision RULES below are durable; the per-file specifics (insertion lines, trigger shapes, required-context status) are unverified assumptions a reviewer must re-confirm against the live files. |
| **Verification** | unverified |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

Reach for this when you are ADDING a `concurrency:` block to a workflow that currently has none, and you must justify both the group key and the cancel semantics rather than copy-pasting a template. Specifically:

- A workflow runs on a high-frequency event (issue activity, PR pushes, label changes) and stacks redundant in-flight runs because it has no `concurrency:` block — and you need to decide whether the newest run should CANCEL the older one or QUEUE behind it.
- You are tempted to reflexively set `cancel-in-progress: true` everywhere "to save runner minutes" and must first check whether the workflow has a non-idempotent side effect (tag push, PyPI upload, release creation) that a mid-flight cancel would corrupt.
- A publish/release workflow needs serialization so the SAME tag never double-publishes, but DIFFERENT tags should still proceed in parallel — you need the right group key (`github.ref`), not an over-broad one (`github.workflow`) that blocks unrelated tags.
- A PR-scan workflow re-runs on every push to a PR branch and you want successive pushes to the same PR to collapse to one run — you must use `github.head_ref || github.ref`, because `github.sha` makes every push a distinct group and collapses NOTHING.
- A security/edit hook or reviewer flags `${{ github.* }}` inside a `concurrency.group:` as a possible injection sink — you need to know it is a YAML-key context expression, not `run:` shell interpolation, so the env-var-lift rule does not apply.
- You are about to add `concurrency:` to a workflow in a branch-protected repo and must confirm the target is NOT a pinned required status-check context before assuming any merge-queue interaction.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps live under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level — read every step below as **proposed** per the warning above.

### Quick Reference

The single decision rule, then the group-key map:

| Workflow side effect | Idempotent / supersede-able? | `cancel-in-progress` | Group key | Why |
| - | - | - | - | - |
| Tests / scans / lint on a PR | Yes — newest commit's result is the only one that matters | `true` | `github.head_ref \|\| github.ref` | Successive pushes to the same PR collapse to one run; matches the repo's existing `test.yml` convention |
| Idempotent label POST on an issue | Yes — re-POSTing the same label is a no-op | `true` | `github.event.issue.number \|\| github.run_id` | Per-issue serialization; newest event wins; `run_id` fallback keeps a `workflow_call`/no-issue path uniquely grouped |
| git tag push | NO — a cancelled run can leave a tag pushed but its release uncreated | `false` | `github.ref` | Serialize same-ref runs; never interrupt a half-done tag operation |
| PyPI publish | NO — a cancel can leave a partial/duplicate upload | `false` | `github.ref` (the tag) | Same tag never double-publishes; distinct tags publish in parallel |
| GitHub release creation | NO — half-created release is worse than serializing | `false` | `github.ref` | Same as PyPI — gate on idempotency, not convenience |

**The rule in one line:** set `cancel-in-progress` from the idempotency of the side effect, NOT from a desire to save minutes. Cancelling a half-finished publish is worse than letting it run.

### Detailed Steps

**1. Classify the workflow's side effect before touching the keys.**
Ask only one question: *if a run is killed at an arbitrary point, can the system be left in a corrupt or half-applied state?*
- No (tests, scans, idempotent label POST) → the run is supersede-able → `cancel-in-progress: true`. The newest event's result is the only one that matters; killing the older run is free.
- Yes (git tag push, PyPI publish, GitHub release creation) → the run must NOT be interrupted → `cancel-in-progress: false`. New runs QUEUE behind the in-flight one instead of cancelling it.

**2. Choose the group key to scope serialization to the right unit of work.**

```yaml
# Per-issue automation (idempotent label POST): serialize per issue,
# but keep a unique group on a workflow_call / no-issue path so it isn't
# all collapsed into one empty-string group.
concurrency:
  group: ${{ github.workflow }}-${{ github.event.issue.number || github.run_id }}
  cancel-in-progress: true

# Release / publish (tag push, PyPI, release): serialize per TAG so the
# same tag never double-publishes, while DIFFERENT tags proceed in parallel.
# Do NOT cancel — a half-done publish must finish or queue.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false

# PR scan (tests/security): collapse successive pushes to the SAME PR.
# Use head_ref (the PR branch), NOT github.sha — each sha is a distinct
# group and would collapse nothing. Matches the repo's test.yml convention.
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

Key facts:
- `github.ref` per-tag: distinct tags get distinct groups (parallel), the same tag re-run serializes (never double-publishes).
- `github.head_ref || github.ref`: `head_ref` is only set on `pull_request`; the `|| github.ref` keeps push/non-PR events grouped. Successive pushes to one PR share the branch ref → they collapse.
- `github.sha` is WRONG for "collapse successive pushes": every commit is a new SHA → every push is a new group → no collapse ever happens.
- `github.event.issue.number || github.run_id`: `run_id` is unique per run, so a path with no issue (e.g. `workflow_call`) still gets a unique group instead of falling into a shared empty group.

**3. Confirm the group expression is NOT an injection sink.**
`concurrency.group:` is a workflow-level YAML KEY whose value is a context expression evaluated by the Actions runner — it is NOT `run:` shell that splices attacker-controllable text into a command. The workflow-injection / env-var-lift mitigation (lift `${{ github.* }}` into `env:` before using in `run:`) applies to shell interpolation, NOT to a `group:` key. So `${{ github.head_ref }}` or `${{ github.event.issue.number }}` in a group key introduces no injection sink. (Contrast: the SAME `github.head_ref` IS a dangerous source inside `run:` — see `gha-workflow-authoring-pitfalls`.)

**4. Confirm no branch-protection interaction before assuming one.**
Adding `concurrency:` to a workflow that is NOT a pinned required status-check context cannot brick the merge queue — there is no required context whose cancellation/serialization would leave a PR un-mergeable. Before assuming any interaction, enumerate the repo/org ruleset required contexts and confirm the target workflow's jobs are not among them. (In the issue #1548 plan, none of the four target workflows were required contexts — but that was a single read, re-verify per repo. See `gha-required-checks-branch-protection`.)

**5. Treat every per-file specific as an unverified assumption (this plan was never applied).**
The plan author read each of the four target files ONCE and never applied/CI-ran the edits. A reviewer/implementer MUST independently confirm, against the LIVE files, each item in the "assumptions a reviewer must check" rows of the Failed Attempts table below — exact insertion lines, trigger shapes, and required-context status — before treating any of them as fact.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Universal cancel | Assume `cancel-in-progress: true` is universally safe "to save minutes" | WRONG for publishers: a cancelled tag-push/PyPI/release run can leave a tag pushed but release uncreated, or a partial PyPI upload | Gate cancel semantics on side-effect IDEMPOTENCY, not convenience; publishers get `cancel-in-progress: false` |
| Key publish on `github.workflow` alone | Group a release/publish workflow on just `github.workflow` | Over-serializes (blocks unrelated tags) or under-serializes depending on form — wrong granularity | For `release.yml` prefer `github.ref` (the tag): same-tag races serialize while DISTINCT tags proceed in parallel |
| Key PR scan on `github.sha` | Use `github.sha` for PR-scan concurrency group | Each SHA is a distinct group, so rapid successive pushes to the same PR branch do NOT collapse | Use `github.head_ref \|\| github.ref` so successive pushes to one PR share a group and collapse |
| Treat `${{ github.* }}` in group as injection | Apply env-var-lift to `${{ github.head_ref }}` inside `concurrency.group:` | The mitigation is for `run:` shell splicing; a `group:` key is a context-expr YAML key, not a shell sink | No env-var-lift needed in a `concurrency.group:`; it introduces no injection sink |
| Assume branch-protection interaction | Assume adding `concurrency:` could brick the merge queue | A non-required workflow's serialization can't leave a PR un-mergeable; the assumption was unchecked | Enumerate ruleset required contexts FIRST; only a pinned required context could interact |
| (Reviewer-check) Exact insertion lines | Plan asserts specific permissions/jobs-boundary insertion line numbers in each of the four files | Based on a SINGLE read; edits were never applied/CI-run, so line numbers may have drifted or been misread | UNVERIFIED — re-read each file and confirm the `concurrency:` insertion point (top-level, after `on:`/`permissions:`, before `jobs:`) on the live file |
| (Reviewer-check) `auto-tag.yml` trigger | Plan assumes `auto-tag.yml` is `workflow_dispatch`-only | Single-read assumption; trigger shape drives whether `github.ref` is even meaningful | UNVERIFIED — `grep` the live `on:` block; if it also fires on push/tag, reconsider the group key |
| (Reviewer-check) label POST idempotency | Plan assumes `auto-label-needs-plan.yml`'s label POST is truly idempotent (justifying `cancel-in-progress: true`) | Idempotency was inferred, not proven; a non-idempotent POST would make cancel unsafe | UNVERIFIED — confirm the POST is add-label (idempotent) not a stateful/append op before allowing cancel |
| (Reviewer-check) required-context status | Plan assumes none of the four workflows are required status-check contexts | Single read of rulesets; a missed pinned context changes the branch-protection calculus | UNVERIFIED — enumerate org + repo ruleset required contexts and confirm none of the four jobs are pinned |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Verification level** | unverified (planning learning — plan NOT implemented, NOT CI-verified) |
| **Decision rule** | `cancel-in-progress: true` ⇔ idempotent/supersede-able side effect; `false` ⇔ non-idempotent publisher (tag/PyPI/release) |
| **Per-issue group** | `${{ github.workflow }}-${{ github.event.issue.number \|\| github.run_id }}`, `cancel-in-progress: true` |
| **Per-tag (publish) group** | `${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: false` |
| **PR-scan group** | `${{ github.workflow }}-${{ github.head_ref \|\| github.ref }}`, `cancel-in-progress: true` |
| **Anti-pattern** | `github.sha` for PR-scan collapse (each sha = distinct group, no collapse) |
| **Injection** | `${{ github.* }}` in `concurrency.group:` is a context-expr key, NOT a `run:` sink — no env-var-lift needed |
| **Branch protection** | Only a pinned required status-check context can interact — verify before assuming |

### Verified On

| Repo | Context | Status |
| ---- | ------- | ------ |
| ProjectHephaestus | issue #1548 plan (add `concurrency:` to four workflows) | Planning only — unverified; no edit applied, no CI run |
