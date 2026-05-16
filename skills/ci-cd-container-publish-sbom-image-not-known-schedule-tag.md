---
name: ci-cd-container-publish-sbom-image-not-known-schedule-tag
description: "Fix `Export image for SBOM` step in a GitHub Actions container-publish workflow failing with `image not known` on `schedule`/`workflow_dispatch` runs. Root cause: the tag-generation block emits the branch tag (`:${github.ref_name}`) only when `github.event_name == push`, so on scheduled/manual runs the local podman storage never gets the `:main` tag that the SBOM step's `podman save ...:main` references. Fix: broaden the event guard to `push|schedule|workflow_dispatch` while keeping the `refs/heads/*` ref guard. Use when: (1) nightly container-publish failing 2+ nights at podman save, (2) `gh workflow run container-publish.yml` succeeds at build but fails at SBOM, (3) the workflow uses `${{ github.ref_name }}` for podman save and only emits the branch tag on push."
category: ci-cd
date: 2026-05-15
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - container-publish
  - podman
  - sbom
  - image-not-known
  - schedule-trigger
  - workflow-dispatch
  - tag-generation
  - nightly-build
  - anchore-sbom-action
---

# Container-Publish SBOM `image not known` on Schedule/Dispatch — Tag-Generation Event Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-15 |
| **Objective** | Stop the nightly `container-publish` workflow from failing at the `Export image for SBOM` step on `schedule` and `workflow_dispatch` runs. |
| **Outcome** | One-line widening of the event guard in the tag-generation block (`push` → `push\|schedule\|workflow_dispatch`). The SBOM step now finds the locally-built `${REGISTRY}/${IMAGE_NAME}:main` image and `podman save` succeeds. |
| **Verification** | verified-ci — ProjectOdyssey PR #5406 merged 2026-05-15 (commit `da1b3f7e`); `gh workflow run container-publish.yml` run `25900780342` reports `success` for `Export image for SBOM`, `Generate SBOM`, and `Upload SBOM`. |

## When to Use

- Nightly (cron / `schedule`) container-publish workflow has failed at `podman save .../<image>:<branch>` for 2+ consecutive nights with `Error: ...:<branch>: image not known`.
- `gh workflow run container-publish.yml` (i.e. `workflow_dispatch`) reproduces the same failure even though the build step itself succeeds.
- Workflow uses `${{ github.ref_name }}` (or equivalent) to address the image for `podman save`, and a separate Bash tag-generation block gates the branch tag on `event_name == "push"`.
- Other tags (`sha-XXXXXX`, `:latest`, semver) ARE present in podman storage — only the branch tag is missing on non-push runs.

## When NOT to Use

- Build step itself fails — that's a different problem (Dockerfile / buildah / registry auth).
- `podman save` is using `:latest` or `:sha-...` and still failing — the tag-generation logic for those tags is separate; this skill targets the branch-tag block specifically.
- The workflow only runs on `push` events (no `schedule`, no `workflow_dispatch`) — this bug cannot trigger.
- `pull_request` event failing — intentionally NOT covered by the fix (PR head refs should not be tagged into the registry).

## Verified Workflow

### Quick Reference

#### Buggy code (before)

```bash
# Branch tag — fires only on push
if [[ "$EVENT_NAME" == "push" && "$REF" == refs/heads/* ]]; then
  TAGS="${TAGS}${REGISTRY}/${IMAGE_NAME}:${REF_NAME}${SUFFIX} "
fi
```

Then later, regardless of event:

```bash
- name: Export image for SBOM
  run: podman save -o /tmp/runtime-image.tar "$REGISTRY/$IMAGE_NAME:${{ github.ref_name }}"
```

On `schedule` / `workflow_dispatch`, `EVENT_NAME` is `schedule` / `workflow_dispatch`, the branch tag is never emitted, and `podman save ...:main` fails with `image not known`.

#### Fixed code (after — PR #5406)

```bash
# Branch tag — also emit on schedule (nightly) and workflow_dispatch so the
# downstream "Export image for SBOM" step can `podman save ...:${github.ref_name}`
# from the locally-built image without round-tripping through the registry.
if [[ ( "$EVENT_NAME" == "push" \
        || "$EVENT_NAME" == "schedule" \
        || "$EVENT_NAME" == "workflow_dispatch" ) \
      && "$REF" == refs/heads/* ]]; then
  TAGS="${TAGS}${REGISTRY}/${IMAGE_NAME}:${REF_NAME}${SUFFIX} "
fi
```

### Why this is safe

- On `schedule` / `workflow_dispatch` running from the default branch, `github.ref` is `refs/heads/main` and `github.ref_name` is `main`. The retained `refs/heads/*` ref guard still gates correctly.
- Tag events (`refs/tags/v*`) are handled by the separate semver block below in the workflow and are untouched.
- `pull_request` events (where `github.ref_name` is a PR head ref) are deliberately NOT in the broadened set — no risk of polluting GHCR with PR-branch tags.

### Verification commands

```bash
# Trigger manually to confirm the fix
gh workflow run container-publish.yml --ref main

# Find the run and inspect the SBOM-related steps
RUN_ID=$(gh run list --workflow=container-publish.yml --event=workflow_dispatch \
           --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --json jobs --jq '
  .jobs[]
  | select(.name == "build-and-push (runtime)")
  | .steps[]
  | select(.name | test("SBOM|Export"))
  | "\(.conclusion)\t\(.name)"'
# Expected (post-fix):
# success    Export image for SBOM
# success    Generate SBOM
# success    Upload SBOM
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Assumed nightly failures were a podman/registry flake | Re-ran the nightly hoping it was transient | Failed identically 3 consecutive nights — not a flake, a logic bug | When a scheduled workflow fails on the same step 3+ nights running, it's a configuration bug, not infra |
| Looked at the SBOM step in isolation | Read `Export image for SBOM` step logs trying to find why `podman save` was failing | The bug is in a *different* step (tag generation, ~50 lines earlier). The SBOM step is the victim, not the culprit | When a downstream step says "image not known", trace back to where the tag was supposed to be created |
| Considered `paths:` filter as the cause | Hypothesized the workflow wasn't running on schedule | `gh run list --event=schedule --workflow=container-publish.yml` showed the workflow IS running — it just produces no `:main` tag on schedule | `paths:` filter is irrelevant for `schedule` events (filters don't apply to `schedule` triggers). Different debugging path |
| Wanted to add only `schedule` (not `workflow_dispatch`) | Initial scope: just fix the nightly | Then `gh workflow run` (the natural verification step) would still fail — same root cause | Cover all event types that legitimately operate on the default branch: `push` + `schedule` + `workflow_dispatch` |

## Alternative Fix Shapes (Rejected)

| Alternative | Why Rejected |
|---|---|
| `podman save` by SHA tag (`:sha-XXXXXX`) instead of branch tag | Couples the SBOM step to the tag-generation block's SHA logic; brittle if SHA-tag naming changes |
| Round-trip through registry: `podman push :main` then `podman pull` then `save` | Adds registry round-trip latency; pollutes registry with intermediate tags on non-push events; requires push permission on scheduled runs |
| Tag the image after build with `podman tag <last-tag> :main` | Adds an extra step that itself can fail; the root issue is the missing tag generation, not a downstream rename |
| Skip SBOM on non-push events | Defeats the purpose of nightly SBOM refresh for security/vuln tracking |

## Results & Parameters

### Full before/after of the tag-generation block

Before (only the branch-tag stanza shown — surrounding stanzas for `:latest`, `:sha-XXXXXX`, semver unchanged):

```bash
# Branch tag
if [[ "$EVENT_NAME" == "push" && "$REF" == refs/heads/* ]]; then
  TAGS="${TAGS}${REGISTRY}/${IMAGE_NAME}:${REF_NAME}${SUFFIX} "
fi
```

After:

```bash
# Branch tag — also emit on schedule (nightly) and workflow_dispatch so the
# downstream "Export image for SBOM" step can `podman save ...:${github.ref_name}`
# from the locally-built image without round-tripping through the registry.
if [[ ( "$EVENT_NAME" == "push" \
        || "$EVENT_NAME" == "schedule" \
        || "$EVENT_NAME" == "workflow_dispatch" ) \
      && "$REF" == refs/heads/* ]]; then
  TAGS="${TAGS}${REGISTRY}/${IMAGE_NAME}:${REF_NAME}${SUFFIX} "
fi
```

### Verification snippet (post-merge)

```text
$ gh workflow run container-publish.yml --ref main
✓ Created workflow_dispatch event for container-publish.yml at main

$ gh run view 25900780342 --json jobs --jq '...'
success    Export image for SBOM
success    Generate SBOM
success    Upload SBOM
```

## Verified On

- **Repo**: HomericIntelligence/ProjectOdyssey
- **PR**: #5406 (merged 2026-05-15)
- **Commit**: `da1b3f7e`
- **Workflow run**: `25900780342` — `workflow_dispatch` on `main`, all SBOM steps `success`
- **Symptom prior to fix**: 3 consecutive nightly failures 2026-05-12 / 2026-05-13 / 2026-05-14, all at the same `Export image for SBOM` step with `Error: ghcr.io/homericintelligence/projectodyssey:main: image not known`
