---
name: gha-workflow-concurrency-controls
description: "Choosing GitHub Actions `concurrency:` controls when ADDING them to event-driven workflows that currently lack them — selecting the `group` key and `cancel-in-progress` value per the workflow's trigger and its side-effect idempotency. The ONE decision rule: `cancel-in-progress: true` for idempotent / supersede-able runs (tests, scans, idempotent label POSTs — newest event wins), `cancel-in-progress: false` for non-idempotent publishers that must not be interrupted mid-flight (git tag push, PyPI publish, GitHub release creation). Group-key selection scopes the serialization: `github.event.issue.number` (+ `github.run_id` fallback) for per-issue, `github.ref` for per-tag (distinct tags publish in parallel, same tag never double-publishes), `github.head_ref || github.ref` (NOT `github.sha`) for PR scans so successive pushes collapse. Bare group keys (without `${{ github.workflow }}-` prefix) work correctly for single-workflow repos — the workflow-prefix is defensive but optional when cross-workflow collision is not a concern. Use when: (1) a workflow has no `concurrency:` block and you must pick `group`/`cancel-in-progress` by trigger, (2) deciding whether cancelling a run is safe — gate it on side-effect idempotency not convenience, (3) a publish/release workflow needs serialization without over- or under-serializing across tags, (4) PR-scan concurrency must collapse rapid successive pushes (use head_ref, NOT sha), (5) confirming `${{ github.* }}` in a `concurrency.group` does NOT introduce a workflow-injection sink (it is a YAML-key context expr, not a `run:` interpolation), (6) confirming a workflow you are editing is NOT a pinned required status-check context before assuming branch-protection interaction."
category: ci-cd
date: 2026-06-24
version: "2.0.0"
user-invocable: false
verification: verified-ci
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
  - side-effect-idempotency
  - verified-ci
---

# GitHub Actions Workflow Concurrency Controls (Group Key + Cancel-in-Progress Selection)

**History:** [changelog](./gha-workflow-concurrency-controls.history)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-24 |
| **Objective** | Capture the durable decision rules for adding a `concurrency:` block to event-driven GitHub Actions workflows that lack one — how to choose the `group` key and the `cancel-in-progress` value from the workflow's trigger and the idempotency of its side effects. Surfaced while planning (ProjectHephaestus, issue #1548) the addition of `concurrency:` to four workflows: a per-issue automation workflow, a release/publish workflow, an auto-tag workflow, and a PR-scan workflow. |
| **Outcome** | Implemented and CI-verified. PR #1590 applied concurrency blocks to all four workflows (`auto-label-needs-plan.yml`, `auto-tag.yml`, `release.yml`, `security.yml`) and all required CI checks passed (test, integration, pr-policy, lint). The decision rules and group-key patterns were confirmed correct in practice. The actual implementation used simpler bare group keys (without `${{ github.workflow }}-` prefix) — valid for single-workflow repos where cross-workflow group collision is not a concern. |
| **Verification** | verified-ci (PR #1590 passed all required CI checks on 2026-06-24) |
| **Files Amended** | `auto-label-needs-plan.yml`, `auto-tag.yml`, `release.yml`, `security.yml` |

## When to Use

Reach for this when you are ADDING a `concurrency:` block to a workflow that currently has none, and you must justify both the group key and the cancel semantics rather than copy-pasting a template. Specifically:

- A workflow runs on a high-frequency event (issue activity, PR pushes, label changes) and stacks redundant in-flight runs because it has no `concurrency:` block — and you need to decide whether the newest run should CANCEL the older one or QUEUE behind it.
- You are tempted to reflexively set `cancel-in-progress: true` everywhere "to save runner minutes" and must first check whether the workflow has a non-idempotent side effect (tag push, PyPI upload, release creation) that a mid-flight cancel would corrupt.
- A publish/release workflow needs serialization so the SAME tag never double-publishes, but DIFFERENT tags should still proceed in parallel — you need the right group key (`github.ref`), not an over-broad one (`github.workflow`) that blocks unrelated tags.
- A PR-scan workflow re-runs on every push to a PR branch and you want successive pushes to the same PR to collapse to one run — you must use `github.head_ref || github.ref`, because `github.sha` makes every push a distinct group and collapses NOTHING.
- A security/edit hook or reviewer flags `${{ github.* }}` inside a `concurrency.group:` as a possible injection sink — you need to know it is a YAML-key context expression, not `run:` shell interpolation, so the env-var-lift rule does not apply.
- You are about to add `concurrency:` to a workflow in a branch-protected repo and must confirm the target is NOT a pinned required status-check context before assuming any merge-queue interaction.

## Verified Workflow

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

### Actual Group Keys Used (CI-Verified)

The four workflows amended in PR #1590 used these exact concurrency blocks — notably WITHOUT the `${{ github.workflow }}-` prefix, which is optional for single-workflow repos:

| Workflow | Trigger | Group key used | `cancel-in-progress` | Rationale |
| -------- | ------- | -------------- | -------------------- | --------- |
| `auto-label-needs-plan.yml` | `issues` events | `auto-label-needs-plan-${{ github.event.issue.number \|\| github.run_id }}` | `true` | Per-issue idempotent label POST; newest event wins |
| `auto-tag.yml` | `workflow_dispatch` only | `auto-tag-${{ github.workflow }}` | `false` | Non-idempotent tag push; `workflow_dispatch`-only means only one meaningful run at a time anyway |
| `release.yml` | tag push (`refs/tags/v*`) | `release-${{ github.ref }}` | `false` | Non-idempotent release publish; per-ref so different tags run in parallel |
| `security.yml` | `pull_request`, `push` | `security-${{ github.head_ref \|\| github.ref }}` | `true` | Idempotent security scan; collapses successive pushes per PR branch |

**Bare-key vs. workflow-prefixed key:** The planned snippets used `${{ github.workflow }}-${{ github.ref }}` style; the actual implementation used simpler bare keys (`release-${{ github.ref }}` etc.). Both are correct. The workflow-prefix prevents cross-workflow collision if two workflows accidentally share a group name; the bare form is more readable and sufficient for repos where this is not a concern.

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
# Bare-key form (no workflow prefix) — sufficient for single-workflow repos.
concurrency:
  group: auto-label-needs-plan-${{ github.event.issue.number || github.run_id }}
  cancel-in-progress: true

# Auto-tag (workflow_dispatch only — non-idempotent tag push):
# Use github.workflow as the bare key; only one dispatch can run at a time.
concurrency:
  group: auto-tag-${{ github.workflow }}
  cancel-in-progress: false

# Release / publish (tag push, PyPI, release): serialize per TAG so the
# same tag never double-publishes, while DIFFERENT tags proceed in parallel.
# Do NOT cancel — a half-done publish must finish or queue.
concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

# PR scan (tests/security): collapse successive pushes to the SAME PR.
# Use head_ref (the PR branch), NOT github.sha — each sha is a distinct
# group and would collapse nothing. Matches the repo's test.yml convention.
concurrency:
  group: security-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

Key facts:
- `github.ref` per-tag: distinct tags get distinct groups (parallel), the same tag re-run serializes (never double-publishes).
- `github.head_ref || github.ref`: `head_ref` is only set on `pull_request`; the `|| github.ref` keeps push/non-PR events grouped. Successive pushes to one PR share the branch ref → they collapse.
- `github.sha` is WRONG for "collapse successive pushes": every commit is a new SHA → every push is a new group → no collapse ever happens.
- `github.event.issue.number || github.run_id`: `run_id` is unique per run, so a path with no issue (e.g. `workflow_call`) still gets a unique group instead of falling into a shared empty group.
- Bare keys vs. workflow-prefixed: `${{ github.workflow }}-` prefix is defensive but optional. Use it if cross-workflow collision is a realistic concern; omit it for readability in repos with clear event-to-workflow mapping.

**3. Confirm the group expression is NOT an injection sink.**
`concurrency.group:` is a workflow-level YAML KEY whose value is a context expression evaluated by the Actions runner — it is NOT `run:` shell that splices attacker-controllable text into a command. The workflow-injection / env-var-lift mitigation (lift `${{ github.* }}` into `env:` before using in `run:`) applies to shell interpolation, NOT to a `group:` key. So `${{ github.head_ref }}` or `${{ github.event.issue.number }}` in a group key introduces no injection sink. (Contrast: the SAME `github.head_ref` IS a dangerous source inside `run:` — see `gha-workflow-authoring-pitfalls`.)

**4. Confirm no branch-protection interaction before assuming one.**
Adding `concurrency:` to a workflow that is NOT a pinned required status-check context cannot brick the merge queue — there is no required context whose cancellation/serialization would leave a PR un-mergeable. Before assuming any interaction, enumerate the repo/org ruleset required contexts and confirm the target workflow's jobs are not among them. (For issue #1548, none of the four target workflows were required contexts — confirmed by enumerating ruleset contexts.)

**5. Verify per-file specifics against the live files before assuming line numbers.**
The group-key decision rules are durable. Exact insertion lines in any specific workflow file may drift — always re-read the live file and confirm the insertion point (top-level, after `on:`/`permissions:`, before `jobs:`) before editing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Universal cancel | Assume `cancel-in-progress: true` is universally safe "to save minutes" | WRONG for publishers: a cancelled tag-push/PyPI/release run can leave a tag pushed but release uncreated, or a partial PyPI upload | Gate cancel semantics on side-effect IDEMPOTENCY, not convenience; publishers get `cancel-in-progress: false` |
| Key publish on `github.workflow` alone | Group a release/publish workflow on just `github.workflow` | Over-serializes (blocks unrelated tags) or under-serializes depending on form — wrong granularity | For `release.yml` prefer `github.ref` (the tag): same-tag races serialize while DISTINCT tags proceed in parallel |
| Key PR scan on `github.sha` | Use `github.sha` for PR-scan concurrency group | Each SHA is a distinct group, so rapid successive pushes to the same PR branch do NOT collapse | Use `github.head_ref \|\| github.ref` so successive pushes to one PR share a group and collapse |
| Treat `${{ github.* }}` in group as injection | Apply env-var-lift to `${{ github.head_ref }}` inside `concurrency.group:` | The mitigation is for `run:` shell splicing; a `group:` key is a context-expr YAML key, not a shell sink | No env-var-lift needed in a `concurrency.group:`; it introduces no injection sink |
| Assume branch-protection interaction | Assume adding `concurrency:` could brick the merge queue | A non-required workflow's serialization can't leave a PR un-mergeable; the assumption was unchecked | Enumerate ruleset required contexts FIRST; only a pinned required context could interact |
| Using `github.workflow-` prefix in group key | Plan proposed `${{ github.workflow }}-${{ github.ref }}` etc. to prevent cross-workflow collisions | Not incorrect but unnecessary — simpler bare keys work fine in repos where workflows don't accidentally share a concurrency group name; the actual implementation used the shorter form | For single-repo, single-workflow-per-event scenarios, the workflow-prefix is defensive but optional; use bare event-scoped keys for readability, add prefix if cross-workflow collision is a real concern |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Verification level** | verified-ci (PR #1590, ProjectHephaestus issue #1548; all required CI checks passed on 2026-06-24) |
| **Decision rule** | `cancel-in-progress: true` ⇔ idempotent/supersede-able side effect; `false` ⇔ non-idempotent publisher (tag/PyPI/release) |
| **Per-issue group (confirmed)** | `auto-label-needs-plan-${{ github.event.issue.number \|\| github.run_id }}`, `cancel-in-progress: true` |
| **Per-tag (publish) group (confirmed)** | `release-${{ github.ref }}`, `cancel-in-progress: false` |
| **Auto-tag group (confirmed)** | `auto-tag-${{ github.workflow }}`, `cancel-in-progress: false` (workflow_dispatch-only) |
| **PR-scan group (confirmed)** | `security-${{ github.head_ref \|\| github.ref }}`, `cancel-in-progress: true` |
| **Anti-pattern** | `github.sha` for PR-scan collapse (each sha = distinct group, no collapse) |
| **Bare vs. prefixed keys** | Bare keys (no `github.workflow-` prefix) are sufficient for single-workflow repos; prefixed form is defensive but optional |
| **Injection** | `${{ github.* }}` in `concurrency.group:` is a context-expr key, NOT a `run:` sink — no env-var-lift needed |
| **Branch protection** | Only a pinned required status-check context can interact — none of the four amended workflows are required contexts (confirmed) |
| **auto-tag.yml trigger** | `workflow_dispatch`-only (confirmed) — validates the planning assumption |
| **label POST idempotency** | `auto-label-needs-plan.yml` uses add-label (idempotent) — confirms `cancel-in-progress: true` is safe (confirmed) |

### Verified On

| Repo | Context | Status |
| ---- | ------- | ------ |
| ProjectHephaestus | issue #1548 / PR #1590 — added `concurrency:` to auto-label-needs-plan.yml, auto-tag.yml, release.yml, security.yml | verified-ci (all required CI checks passed: test, integration, pr-policy, lint; 2026-06-24) |
