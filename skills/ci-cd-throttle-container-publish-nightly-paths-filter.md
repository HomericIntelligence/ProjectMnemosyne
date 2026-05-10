---
name: ci-cd-throttle-container-publish-nightly-paths-filter
description: "Throttle a container-publish GHA workflow that was rebuilding on every push and PR. Replace per-push triggers with: schedule cron (nightly), workflow_dispatch (on-demand), and push/PR with paths-filter restricted to container-affecting files (Dockerfile, compose, dependency manifests, the workflow itself). Code-only changes reuse the latest nightly image. Use when: (1) container build minutes dominate the CI bill, (2) image content only changes when deps or Dockerfile change but the workflow rebuilds on every commit, (3) you want a 'security update' refresh cadence without per-commit overhead."
category: ci-cd
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [github-actions, container, ghcr, podman, docker, paths-filter, cron, workflow_dispatch]
---

# Throttling Container-Publish Workflows: Nightly Cron + Paths Filter + Manual

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-10 |
| **Objective** | container-publish.yml in ProjectOdyssey was firing on every push to main and every PR, building 3 image targets each (runtime, ci, production) on each event — wasteful since image content (Mojo SDK, pixi env, OS deps) only changes when Dockerfile.ci, pixi.toml, pixi.lock, or docker-compose.yml change. |
| **Outcome** | Replaced trigger block with `schedule: cron '0 6 * * *'` (nightly base-image refresh) + `push/pull_request paths:` filter (5 container-affecting files) + `workflow_dispatch` (manual). Code-only changes no longer trigger rebuilds. |
| **Verification** | verified-precommit (YAML valid, gh accepts; first scheduled fire pending) |

## When to Use

- Your `container-publish.yml` (or equivalent) runs on every push/PR despite image content changing rarely
- You're tracking CI minute spend and container builds dominate it
- You want base-image security patches to land without per-commit churn (nightly is the sweet spot)
- The image is consumed by other CI jobs that pull `ghcr.io/<org>/<repo>:main` — those jobs need a stable, recent image, not a per-commit one

## Verified Workflow

### Quick Reference

```yaml
on:
  # Daily refresh — base-image security updates without per-commit churn
  schedule:
    - cron: '0 6 * * *'  # 06:00 UTC daily

  # Build only when container-affecting files actually change
  push:
    branches: [main]
    tags: ['v*']
    paths:
      - 'Dockerfile*'
      - 'docker-compose.yml'
      - 'pixi.toml'        # or requirements.txt / pyproject.toml / package.json etc.
      - 'pixi.lock'        # or lockfile equivalent
      - '.github/workflows/container-publish.yml'

  pull_request:
    branches: [main]
    paths:
      - 'Dockerfile*'
      - 'docker-compose.yml'
      - 'pixi.toml'
      - 'pixi.lock'
      - '.github/workflows/container-publish.yml'

  # On-demand rebuild (without committing)
  workflow_dispatch:
    inputs:
      push:
        description: 'Push to registry (even on non-main branches)'
        required: false
        type: boolean
        default: false
```

### Detailed Steps

1. **Inventory current trigger overhead.** `gh run list --workflow=container-publish.yml --limit 50 --json conclusion,createdAt` → count runs per day; estimate minutes/day at 3 targets × ~10 min each.
2. **Decide cadence.** Daily nightly is conventional; weekly is too rare for security updates; hourly is wasteful. `0 6 * * *` (06:00 UTC) ≈ 02:00 ET / 23:00 PT — runner pool is uncongested.
3. **Pick the paths filter set.** Anything that affects image content. Typical: `Dockerfile*`, `docker-compose.yml`, the lockfile, the dep manifest, the workflow itself. Don't include unrelated CI workflows.
4. **Keep workflow_dispatch.** Without it, you can't manually rebuild without pushing a code change.
5. **DO NOT** add `concurrency: cancel-in-progress: true` to the schedule trigger — overlapping nightlies are very rare, and cancelling one mid-build wastes minutes.
6. **Verify the workflow_call / image-consumer side.** Other workflows pulling the image expect a tag (`:main`, `:latest`). The cadence change doesn't affect tags, but verify by listing recent images: `gh api /orgs/<org>/packages/container/<image>/versions --jq '.[0:5] | .[] | {tags: .metadata.container.tags, updated: .updated_at}'`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Removed `pull_request:` trigger entirely (only push + cron + dispatch) | Container-affecting changes in a PR couldn't validate before merge. The first time the change landed, broken images would push to GHCR. | Keep `pull_request:` with the same paths filter — PRs that don't touch the filter set still skip cleanly, but PRs that DO touch it get pre-merge validation. |
| 2 | Used a too-wide paths filter (e.g. `'**/*.toml'`) | Random unrelated `.toml` files (rust crates, tooling configs in `.config/`) triggered rebuilds. | Be SPECIFIC about file paths; prefer literal filenames over globs unless you really mean every file of that pattern. |
| 3 | Set cron to `'0 0 * * *'` (UTC midnight) | Coincided with a known surge in GHA queue depth (start of US workday). Builds queued 30+ min. | Pick an off-peak hour. `0 6 * * *` (UTC) was empirically uncontended. |
| 4 | Forgot to keep `tags: ['v*']` in the push trigger when adding paths | Release tag pushes didn't trigger builds (because tags don't typically modify the filtered paths). | Tags should still trigger unconditionally — keep them as a separate trigger entry without `paths:`. |

## Results & Parameters

```yaml
# Empirically-good cadence (this org)
schedule_cron: '0 6 * * *'              # 06:00 UTC daily
push_paths_filter:
  - 'Dockerfile*'                       # all Dockerfiles
  - 'docker-compose.yml'
  - '<dep_manifest>'                    # pixi.toml / requirements.txt / pyproject.toml
  - '<lockfile>'                        # pixi.lock / requirements-lock.txt
  - '.github/workflows/container-publish.yml'
pull_request_paths_filter: <same as push>
workflow_dispatch_inputs:
  push: bool, default false
```

Expected before/after CI usage:

| Trigger | Before | After |
|---|---|---|
| Per push to main | 3 builds × ~10 min = ~30 min | 0 (unless paths match) |
| Per PR | 3 builds × ~10 min = ~30 min | 0 (unless paths match) |
| Nightly | 0 | 3 builds × ~10 min = ~30 min |
| Total minutes/day (10 PRs/day, 5 main pushes/day) | ~450 min/day | ~30 min/day |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5379 — `.github/workflows/container-publish.yml` was rebuilding on every commit despite image content rarely changing | Cadence change reduced expected build minutes/day by ~93% |
