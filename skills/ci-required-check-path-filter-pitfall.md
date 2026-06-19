---
name: ci-required-check-path-filter-pitfall
description: "Use when: (1) an issue asks you to run a build/job ONLY on PRs that touch certain paths (e.g. a Dockerfile, a subdirectory) and the target workflow is a REQUIRED status check — adding a workflow-level on.pull_request.paths: filter is a trap that makes path-irrelevant PRs un-mergeable, (2) planning a smoke/build gate that you are tempted to soft-fail with continue-on-error: true (a repo may have a forbid-suppressions guard that fails CI on it), (3) tempted to rewrite a digest-pinned Dockerfile FROM to an mcr.microsoft.com mirror to dodge Docker Hub rate limits (this changes the shipped image digest), (4) deciding base-image arch for a pixi/conda smoke build (linux-64 workspace cannot build linux/arm64), (5) writing a CI implementation plan and you need an uncertain-assumptions checklist a reviewer can verify (is the workflow actually a required check? are cited line numbers fresh? is the action SHA verified upstream?)."
category: ci-cd
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: ci-required-check-path-filter-pitfall.history
tags:
  - github-actions
  - branch-protection
  - required-checks
  - planning
  - paths-filter
  - dockerfile
  - continue-on-error
  - mcr-mirror
  - digest-pinning
  - uncertain-assumptions
---

# CI Required Check + Path Filter Pitfall

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Capture the durable planning rule that adding a workflow-level `on.pull_request.paths:` filter to a workflow that is wired as a REQUIRED status check is a trap: on PRs that don't touch the filtered paths the whole workflow is SKIPPED, the required context never reports, and the PR becomes un-mergeable. Plus the planning-hygiene corollaries for CI build/smoke-gate work. |
| **Outcome** | A transferable "don't path-filter a required workflow" rule, a resolution menu (unconditional job / separate non-required workflow / per-job `if:` on a changed-files step that still reports), and an uncertain-assumptions checklist for CI plans. |
| **Verification** | **unverified** — this is a PLAN that was written but never executed or merged. The required-check claim was inferred from a filename, not confirmed via the branch-protection API. Treat every assertion as a hypothesis. |

> ### CENTRAL RISK CONFIRMED (v1.1.0)
>
> The #1 flagged risk of this skill — *"is the workflow ACTUALLY a required status check?"* —
> **materialized on a real repo.** In a re-plan, the assumption was finally checked with
> `gh api repos/:owner/:repo/branches/<branch>/protection --jq '.required_status_checks.contexts'`
> and the answer came back as a **short, fixed list that did NOT include the target workflow**.
> The keystone premise (the workflow is required, so a `paths:` filter would brick PRs) was
> **FALSE** — which flipped the correct design from *always-run* to a **dedicated path-filtered
> workflow** (the literal, KISS, requirement-matching design). Leaving the premise unverified had
> earned a reviewer **NOGO**. Lesson, now empirical, not hypothetical: **query branch protection
> FIRST; never infer required-ness from a filename.** See "When to Use" for the exact command and
> decision rule, and Results & Parameters for the verified example output.

## When to Use

> **DO THIS FIRST — before any reasoning about required-check / path-filter interactions.**
> Query branch protection to learn whether your workflow's check name is actually required:
>
> ```bash
> gh api repos/:owner/:repo/branches/<branch>/protection \
>   --jq '.required_status_checks.contexts'
> ```
>
> **Decision rule:**
> - The workflow's check name **IS in** that list → it **IS required**. A workflow-level `paths:`
>   filter that can skip it will leave the required status **un-reported and block merge**.
>   Do NOT path-filter it: use an always-run job, or move it to a separate **non-required**
>   workflow.
> - The workflow's check name is **NOT in** that list → it is **safe to path-filter**: a skip
>   won't block merge, and a workflow-level `paths:` filter is the correct, **KISS**,
>   requirement-matching design (it also matches an issue that literally asks for path scoping).
>
> Never infer required-ness from a filename (e.g. `_required.yml`) — verify it with the API.

- An issue literally says "run a build/test only on PRs that touch `<path>`" (e.g. the Dockerfile) and the workflow you'd add it to is a **required** status check. The naive `paths:` filter CANNOT satisfy this without bricking unrelated PRs.
- You are about to add a `paths:`/`paths-ignore:` block to a consolidated `_required.yml`-style workflow and want to know why that is wrong.
- You are planning a smoke/build gate and considering `continue-on-error: true` to make it advisory.
- You want to swap a Docker base image to an MCR mirror to dodge Docker Hub rate limits in CI.
- You are choosing a base-image architecture for a pixi/conda (`linux-64`) workspace.
- You are writing a CI implementation plan and need the high-value reviewer-facing content: the list of assumptions the plan did NOT verify.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. It is an
> implementation PLAN that was written but never executed or merged. Verification level:
> `unverified`. The central claim — that the target workflow is a *required* status check —
> was **inferred from the filename `_required.yml` and a `pull_request: branches:[main]`
> trigger, NOT confirmed** via `gh api repos/:owner/:repo/branches/main/protection`. Treat
> the whole thing as a hypothesis until CI confirms.

### Quick Reference

```yaml
# THE TRAP — DO NOT DO THIS on a workflow that is a required status check:
on:
  pull_request:
    branches: [main]
    paths:                       # <-- on a REQUIRED workflow this is a footgun
      - 'Dockerfile'             # PRs that don't touch Dockerfile SKIP the whole
      - 'docker/**'              # workflow → the required context NEVER REPORTS →
                                 # PR stuck "Expected — Waiting for status to be
                                 # reported" → un-mergeable forever.
```

```yaml
# RESOLUTION A — make the JOB run unconditionally (preferred when cheap & self-contained).
# The required workflow always runs; the build job is fast enough to always run.
jobs:
  readonly-fs-smoke: { ... }
  dockerfile-smoke-build:        # insert AFTER readonly-fs-smoke, BEFORE security-dependency-scan
    runs-on: ubuntu-24.04        # host linux/amd64; single-arch (see arch note)
    steps:
      - uses: actions/checkout@<sha>
      - uses: docker/setup-buildx-action@<sha>   # verify SHA upstream, do not copy blindly
      - run: docker buildx build --load -t hermes:smoke .   # BLOCKING (no continue-on-error)
  security-dependency-scan: { ... }
```

```yaml
# RESOLUTION B — per-job changed-files gate that STILL REPORTS a status.
# The job always starts (so the required check reports); a paths-filter step decides
# whether to do real work or exit trivially-green.
  dockerfile-smoke-build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@<sha>
      - id: changes
        uses: dorny/paths-filter@<sha>
        with:
          filters: |
            docker: ['Dockerfile', 'docker/**']
      - if: steps.changes.outputs.docker == 'true'
        run: docker buildx build --load -t hermes:smoke .
      # job still completes & reports success even when docker == 'false'
```

```yaml
# RESOLUTION C — put the path-filtered job in a SEPARATE, NON-required workflow.
# A non-required workflow may use a workflow-level paths: filter freely, because a
# skipped non-required check does not block the merge.
```

### Detailed Steps and Durable Insights

#### 1. HEADLINE — never put a workflow-level `paths:` filter on a required workflow

When a GitHub Actions workflow is registered as a **required status check** in branch
protection, a workflow-level `on.pull_request.paths:` (or `paths-ignore:`) filter means: on any
PR that does not touch the filtered paths, **the entire workflow does not run**. GitHub does not
synthesize a passing status for a workflow that never ran — the required context simply **never
reports**. The PR shows `Expected — Waiting for status to be reported` and is **un-mergeable**.

Consequence for requirements: an issue that says "build the image only on PRs that touch the
Dockerfile" **cannot** be satisfied by a `paths:` block on the required workflow. The literal
request and the required-check mechanic are in direct conflict.

**Resolution menu** (pick one, and document *why* you rejected the naive `paths:` block so a
reviewer doesn't misread "issue asked for path scoping, plan added no `paths:`" as a miss):

- **A. Unconditional cheap job** — if the path-scoped job is cheap and self-contained, just run
  it on every PR of the required workflow. Simplest; no path logic to get wrong.
- **B. Per-job `if:` on a changed-files detection step** (e.g. `dorny/paths-filter`) — the job
  always *starts* (so the required check reports), and the heavy step is gated by the
  changed-files output. The job reports a trivially-green status when the paths don't match.
- **C. Separate, non-required workflow** — move the path-filtered job into its own workflow that
  is NOT a required check. A non-required workflow may use a workflow-level `paths:` filter
  freely, because a skipped non-required check does not block merge.

> Note the distinction from a *job-level* `if:` skip on an *already-running* workflow: a job
> skipped by `if:` inside a workflow that DID run keeps the SHA's prior status and stays
> satisfied. The trap here is the WHOLE WORKFLOW being skipped by a `paths:` filter so the
> required context never posts at all. Don't conflate the two.

#### 2. Grep for an anti-suppression guard BEFORE proposing any soft-fail step

A repo can have an active "forbid-suppressions" guard that fails CI when it finds
`continue-on-error: true` anywhere in `.github/workflows/`. Before proposing ANY advisory /
soft-fail CI step, grep the workflows AND the test suite for such a guard. If one exists, the new
step MUST be blocking. (A smoke/build gate should be blocking anyway — an advisory build that
never fails the PR provides no protection.)

```bash
grep -rnE "continue-on-error|forbid.?suppress|no.?suppress|advisory" .github/ tests/
```

#### 3. MCR-mirror trick applies to UNPINNED bases only — never to a digest-pinned FROM

Rewriting a Dockerfile `FROM` to `mcr.microsoft.com/mirror/docker/library/...` to dodge Docker
Hub anonymous-pull rate limits is valid **only for unpinned base images**. If the base is pinned
by SHA digest (`FROM image@sha256:...`), rewriting it to an MCR mirror **changes the digest** and
therefore the shipped artifact — that is an image change masquerading as a CI convenience. Do not
do it. State the trade-off explicitly: accept the rate-limit flake risk, or add registry auth,
rather than silently changing the image.

#### 4. Match base-image arch to the package toolchain (single-arch smoke builds)

A pixi/conda workspace restricted to `linux-64` **cannot** build `linux/arm64`. Keep smoke builds
single-arch (host `linux/amd64`); do not add a multi-arch build matrix that the toolchain can't
satisfy.

#### 5. The high-value reviewer content: the uncertain-assumptions checklist

For any CI plan, the most useful thing you can hand a reviewer is the list of things you did NOT
verify. For this class of change, surface these as explicit risks (see Results & Parameters for
the full instantiated list):

1. Is the workflow ACTUALLY a required check? (inferred from filename, not API-confirmed).
2. Are the cited line numbers fresh, or stale from a single earlier read? (anchor on job/section
   NAMES, not line numbers).
3. Is the action SHA verified against the upstream tag, or copied from a sibling workflow that
   might itself be stale?
4. Is the build tool (e.g. `docker buildx`) actually present on the runner image you assumed?
5. Will a fresh `docker build` in CI hit Docker Hub anonymous rate limits on shared runner IPs?
   (the #1 real-world flake for this exact change.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Workflow-level `paths:` filter on a required check | Added `on.pull_request.paths: ['Dockerfile', ...]` to a required workflow to "run the build only on Dockerfile PRs" | On PRs not touching the paths the WHOLE workflow is skipped; the required context never reports; PR stuck `Expected — Waiting for status to be reported` → un-mergeable | Path-scope at the JOB level (per-job `if:` on a changed-files step that still reports), or put the path-filtered job in a SEPARATE non-required workflow; NEVER path-filter a required workflow |
| Soft-fail the build with `continue-on-error: true` | Made the smoke/build gate advisory so it wouldn't block PRs | The repo has a forbid-suppressions guard + regression test that fail CI on any `continue-on-error: true` in workflows | Grep workflows AND tests for an anti-suppression guard before proposing advisory steps; make smoke/build gates blocking (they should be anyway) |
| Rewrite digest-pinned `FROM` to MCR mirror to dodge rate limits | Swapped a `FROM image@sha256:...` line to `mcr.microsoft.com/mirror/docker/library/...` for rate-limit relief | Changing the registry changes the image DIGEST → changes the shipped artifact; a "CI convenience" silently alters the deliverable | The MCR-mirror trick is for UNPINNED bases only; for a digest-pinned base, accept the flake or add auth, and state the trade-off explicitly |
| Cite insertion point by line number | Plan anchored edits on `_required.yml:281/:283/:359`, `publish.yml:5/:28`, `Dockerfile:5,14` | Line numbers drift with concurrent edits; any merge to the workflow shifts them, so the cited insertion point becomes wrong | Anchor edits on job/section NAMES (after `readonly-fs-smoke`, before `security-dependency-scan`), not line numbers |
| Assume the workflow is a required check from its name | Built the entire "don't path-filter" argument on the filename `_required.yml` + `pull_request: branches:[main]` | Never confirmed via `gh api repos/:owner/:repo/branches/main/protection`; if it is NOT a required check, a `paths:` filter is acceptable and the always-run design is needlessly conservative | Confirm required-check status with the branch-protection API before reasoning about it; flag it as the #1 unverified assumption otherwise |
| Assumed `_required.yml` was a required check from its filename | Reasoning about path-filter safety on an unverified premise | `gh api .../protection` showed only 2 contexts required; the workflow was NOT among them → premise false, reviewer NOGO | ALWAYS query branch protection before reasoning about required-check / path-filter interactions; never infer required-ness from a filename |
| Chose always-run-on-every-PR to avoid a (nonexistent) blocking-skip problem | Conservative design to dodge required-check skip | Wasted CI on every unrelated PR; reviewer flagged as non-KISS + a silent reinterpretation of the issue's path-scoped requirement | When the check is NOT required, path-filter it — matches the literal requirement and avoids wasted CI |
| Copy an action SHA from a sibling workflow | Reused `docker/setup-buildx-action@8d2750c...  # v3` from `publish.yml` without checking upstream | If the sibling's pin is stale or wrong, the new job inherits the same staleness | Verify the action SHA against the upstream tag independently; do not propagate a pin you haven't checked |
| Assume `docker buildx` is preinstalled on the runner | Assumed `ubuntu-24.04` GitHub-hosted runners ship buildx and that no setup action is strictly needed for a `--load` build | Not validated against the actual runner image; an assumption, not a fact | Include `docker/setup-buildx-action` defensively, but flag runner-tool availability as unverified rather than asserting it |
| Ignore Docker Hub rate limits for a fresh CI build | Acknowledged the rate-limit risk but added no mitigation (no auth, no mirror — because the base is digest-pinned) | Shared runner IPs hit Docker Hub anonymous-pull limits — the #1 real-world flake for this exact change | Either accept the flake risk explicitly or add registry auth; do not leave the #1 flake unmitigated and unstated |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Repo / issue** | HomericIntelligence/ProjectHermes, issue #562 (implementation plan) |
| **Change class** | Add a Dockerfile smoke build to a consolidated required workflow, path-scoped to Dockerfile PRs |
| **Central rule** | A workflow-level `paths:` filter on a REQUIRED workflow makes path-irrelevant PRs un-mergeable (required context never reports) |
| **Chosen design** | Always-run cheap smoke job (Resolution A), single-arch `linux/amd64`, blocking (no `continue-on-error`), digest-pinned base kept as-is |
| **Verification status** | **unverified** — plan only; CI never confirmed; required-check status never queried |

### Branch-protection verification (copy-paste) — DO THIS FIRST

```bash
# List the required status-check contexts for a branch:
gh api repos/:owner/:repo/branches/<branch>/protection \
  --jq '.required_status_checks.contexts'
```

Example output from a real run (the empirical confirmation of this skill's #1 risk):

```json
["Secret Scanning (gitleaks)","justfile-check"]
```

The candidate workflow's check name was **NOT** in that list → it is **not** a required check →
path-filtering it is the correct design. The earlier always-run plan (built on the unverified
assumption it *was* required) was over-conservative and earned a reviewer NOGO.

| Branch-protection result | Conclusion | Correct design |
| ------------------------ | ---------- | -------------- |
| Workflow's check name **IS** in `.required_status_checks.contexts` | It **IS** required | Do NOT path-filter (a skip leaves the required status un-reported → blocks merge). Use an always-run job, or move it to a separate non-required workflow |
| Workflow's check name is **NOT** in the list | It is **not** required | Path-filtering is correct (a skip won't block merge). It matches the literal "run only on PRs touching `<path>`" requirement and avoids wasted CI — the KISS design |

### The uncertain assumptions (the reviewer-facing checklist)

| # | Assumption | Why it's uncertain | What to do |
| - | ---------- | ------------------ | ---------- |
| 1 | `_required.yml` IS a required status check | Inferred from filename + `pull_request: branches:[main]`; NOT confirmed via branch-protection API | `gh api repos/:owner/:repo/branches/main/protection`; if not required, a `paths:` filter is fine and always-run is over-conservative |
| 2 | Cited line numbers (`_required.yml:281/:283/:359`, `publish.yml:5/:28`, `Dockerfile:5,14`) are current | Read once; any concurrent edit shifts them | Anchor on job/section names (after `readonly-fs-smoke`, before `security-dependency-scan`) |
| 3 | `docker/setup-buildx-action@8d2750c... # v3` SHA is correct | Copied from `publish.yml`, not cross-checked upstream | Verify against the upstream tag independently |
| 4 | `docker buildx` is available on `ubuntu-24.04` runners (and setup action optional for `--load`) | Assumed true as of 2026; not validated on the actual runner image | Keep the setup step defensively; flag as unverified |
| 5 | A fresh `docker build` won't hit Docker Hub rate limits | Acknowledged but NOT mitigated (base is digest-pinned, so no mirror/auth added) | Reviewer weighs accepting the flake vs adding registry auth |

### External dependencies relied on WITHOUT direct verification

- The GitHub workflow JSON schema URL (`https://json.schemastore.org/github-workflow`) — taken
  from the repo's own schema-validation job, not fetched.
- `check-jsonschema` — assumed installable.
- Branch-protection configuration — never queried.
- Upstream action tags — not cross-checked against the pinned SHAs.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHermes | Issue #562 — implementation plan (R0) | Add Dockerfile smoke build to `_required.yml`, path-scoped to Dockerfile PRs; **unverified** — plan written, never executed or merged; required-check status never confirmed via API |
| ProjectHermes | Issue #562 — R1 re-plan (NOGO→re-plan) | **CENTRAL RISK CONFIRMED.** R1 ran `gh api repos/HomericIntelligence/ProjectHermes/branches/main/protection --jq '.required_status_checks.contexts'` → `["Secret Scanning (gitleaks)","justfile-check"]` ONLY. The docker-build workflow was NOT a required check → R0's keystone premise was FALSE → correct design is a dedicated path-filtered `.github/workflows/docker-build.yml` on `pull_request.paths`. Still `unverified` (R1 remained a plan), but the "is it actually required?" risk was empirically checked and proven decisive |
