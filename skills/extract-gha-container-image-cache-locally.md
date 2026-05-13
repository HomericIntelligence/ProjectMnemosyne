---
name: extract-gha-container-image-cache-locally
description: "Extract a GitHub-Actions-cached Podman container image tar (produced by actions/cache + podman save) and re-upload it as a downloadable workflow artifact so a developer can podman load the exact CI image locally for forensic reproduction. Use when: (1) a CI bug is suspected to live in the cached container bytes rather than source code, (2) you need to bisect whether a stale cache is masking or causing a regression, (3) you want bit-identical local repro of a hard-to-reproduce CI failure (e.g. JIT SIGILL, runner-specific glibc/SIMD issues)."
category: debugging
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-actions, podman, container, cache, forensics, ci-debugging]
---

# Extract GHA-Cached Container Image Locally

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Objective** | Pull the exact container image tarball that GitHub Actions cached for a failing CI job, and load it locally for forensic inspection. |
| **Outcome** | Successful. Extracted ~2.7 GB uncompressed (~760 MB compressed) tar from ProjectOdyssey CI, loaded into local Podman, ran the exact image bash to reproduce modular/modular#6413. |
| **Verification** | verified-ci |

## When to Use

- You suspect a CI failure is caused by **what's inside the cached container image** (pixi env bytes, installed binaries) rather than source code, and need to pull the exact bytes to inspect locally.
- The upstream CI uses `actions/cache` + `podman save` to cache a built image keyed on `hashFiles(Dockerfile, pixi.toml, pixi.lock)` (or similar deterministic inputs), and you want to bisect whether the cache hit is the variable that flips the bug.
- You need a **bit-identical local repro** of a runner-only failure (JIT SIGILL, glibc-version-sensitive crash, SIMD/AVX detection bug) and your dev box's freshly built image doesn't reproduce.
- You want to forensically compare a "good" cache entry vs a "bad" one before evicting either.

**Do NOT use when:**
- The image can be reproducibly rebuilt locally from the same `Dockerfile` + `pixi.lock` — just build it.
- The cache key is non-deterministic (e.g. includes `${{ github.run_id }}`) — you can't predict it.
- You only need the build logs, not the image bytes — use `gh run view --log` instead.

## Verified Workflow

### Quick Reference

```bash
# 1. Add the workflow file (see "Verified workflow YAML" below) and push to a branch.

# 2. Dispatch on the branch whose cache key you want:
gh workflow run extract-cached-image.yml --ref <branch>

# 3. Find the run ID and download the artifact:
RUN_ID=$(gh run list --workflow=extract-cached-image.yml --limit=1 --json databaseId --jq '.[0].databaseId')
gh run download "$RUN_ID"  # downloads container-image-<full-cache-key>/

# 4. Load and inspect locally:
podman load -i container-image-*/dev.tar
podman run --rm -it <loaded-image-tag> bash
cat container-image-*/manifest.txt   # provenance: cache key, head sha, tar sha256, source hashes
```

### Detailed Steps

1. **Identify the upstream cache key.** Read the composite action / workflow that does the caching (in our case `setup-container/action.yml`) and copy the exact `key:` expression. ProjectOdyssey uses:

   ```yaml
   key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
   ```

   Your extractor MUST reconstruct this string exactly — a one-character mismatch and you get a cache miss.

2. **Add `.github/workflows/extract-cached-image.yml`** with the full YAML in the "Results & Parameters" section below. Key design points:

   - `on: workflow_dispatch` only — manual, no automatic trigger
   - Optional `key_hash_override` input lets you pin to a historical hash
   - **`hashFiles(...)` is evaluated in a step's `env:` block, not at job-level `env:`** (see Failed Attempts row 1)
   - **All `workflow_dispatch` inputs flow through `env:`, never interpolated directly into `run:`** (see Failed Attempts row 2)
   - On cache miss the job **fails fast** (`exit 1`) so you don't silently upload an empty bundle
   - Bundles `dev.tar` + a `manifest.txt` with provenance (cache key, ref, head sha, tar sha256, source file hashes)
   - Uses pinned-SHA actions for `actions/checkout@v4`, `actions/cache/restore@v4`, `actions/upload-artifact@v7`
   - `if-no-files-found: error` and `retention-days: 7` on the upload

3. **Push the workflow on the branch whose cache you want to extract.** The workflow must exist on that ref for `--ref` dispatch to find it.

4. **Dispatch:**

   ```bash
   gh workflow run extract-cached-image.yml --ref <branch>
   # Optional: pin to a specific hash if the current source files have drifted
   gh workflow run extract-cached-image.yml --ref <branch> -f key_hash_override=<sha256-from-original-run>
   ```

5. **Wait, then locate the run and the artifact name.** The artifact is named `container-image-<full-resolved-cache-key>` so multiple extractions don't collide.

   ```bash
   gh run list --workflow=extract-cached-image.yml --limit=5
   RUN_ID=<id>
   gh run view "$RUN_ID"   # confirm "cache hit" in the log
   ```

6. **Download and verify provenance before trusting the bytes:**

   ```bash
   gh run download "$RUN_ID"
   cat container-image-*/manifest.txt
   sha256sum container-image-*/dev.tar   # must match manifest
   ```

7. **Load into Podman and inspect:**

   ```bash
   podman load -i container-image-*/dev.tar
   podman images | head             # find the loaded tag
   podman run --rm -it <tag> bash   # interactive shell in the exact CI image
   ```

8. **Extract first, evict later.** Resist the urge to `gh api -X DELETE /repos/.../actions/caches/<id>` until you've confirmed you have the tar locally and the sha256 matches the manifest. Once evicted, that cache entry is gone forever and you can't go back (see Failed Attempts row 3).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1. `hashFiles()` in job-level env | Put `DOCKERFILE_HASH: ${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}` in the job's top-level `env:` block | `gh workflow run` dispatch failed with HTTP 422: `Unrecognized function: 'hashFiles'. Located at position 1 within expression: hashFiles(...)`. The `hashFiles` function is only available in step-level expression contexts, not job-level `env:`. | Move every `hashFiles(...)` call into the specific step's `env:` block (`steps.<step>.env`). Job-level `env:` only supports a restricted expression vocabulary. |
| 2. Direct `${{ inputs.x }}` in run blocks | Wrote `hash="${{ inputs.key_hash_override }}"` directly inside a `run:` shell body | `security_reminder_hook` flagged it as a command-injection sink — a malicious dispatcher could put `"; rm -rf / #` in the input. | Always route `workflow_dispatch` inputs through `env:` and reference them as plain shell vars (`${KEY_HASH_OVERRIDE}`) inside `run:`. Same rule applies to any expression sourced from user-controlled data (PR titles, issue bodies, fork PRs). |
| 3. Premature cache eviction | Deleted the suspected-bad cache entry via `gh api -X DELETE /repos/.../actions/caches/<id>` before extracting, to force a fresh rebuild and see whether the bug disappeared | Once evicted, that specific tar was gone — we couldn't extract the "bad" bytes for direct comparison with a freshly built "good" image. The forensic A/B was no longer possible. | **Extract first, evict later.** Treat the cache as a one-shot crime scene: download the artifact and confirm sha256 before mutating cache state. |
| 4. Naive tar dump without manifest | First draft just uploaded `dev.tar` with no metadata | A few hours later we couldn't tell which cache key the tar came from, which ref/head sha was current at extraction time, or whether the `pixi.lock` was the same as today's. Forensic value drops fast without provenance. | Always bundle a `manifest.txt` alongside the tar: cache key, ref, head sha, runner uid, tar sha256, and sha256 of every source file that feeds the cache key. Future-you needs this to know you're working with the same image. |
| 5. Silent upload on cache miss | First draft skipped the cache-hit check — if the restore missed, it would happily upload a zero-byte bundle | Easy to chase phantom bugs in an empty image | `actions/cache/restore` exposes `steps.<id>.outputs.cache-hit`. Gate the bundle/upload steps on `== 'true'` and `exit 1` on miss so the workflow fails loudly. Pair with `if-no-files-found: error` on `upload-artifact`. |

## Results & Parameters

### Verified workflow YAML

Drop this into `.github/workflows/extract-cached-image.yml` and adjust the cache key expression in the **Compute cache key** step to match your repo's caching action. ProjectOdyssey's working version is at commit `45abbe13` on branch `bisect/6413-positive-control`.

```yaml
name: Extract Cached Container Image

# Forensic helper: pull the GHA-cached `podman save` tarball for this branch's
# setup-container key and upload it as a workflow artifact. Used to extract
# a "bad" cached image suspected of triggering a CI-only bug so we can run
# it locally and confirm whether the bug lives in the cached bytes.
#
# Manual dispatch only; no automatic trigger. Uses the same cache key as
# the upstream caching action so it lands on whichever tar the upstream
# test job would have used.

on:
  workflow_dispatch:
    inputs:
      key_hash_override:
        description: >
          Override the hashFiles(Dockerfile, pixi.toml, pixi.lock) value
          to pin to a specific cache. Leave blank to compute fresh.
        required: false
        default: ""

permissions:
  contents: read

jobs:
  extract:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      # Route the user-supplied override through env: to avoid command
      # injection (security_reminder_hook flags direct interpolation
      # of inputs into a run: block).
      KEY_HASH_OVERRIDE: ${{ inputs.key_hash_override }}
    steps:
      - name: Checkout
        uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4
        with:
          fetch-depth: 1

      - name: Export runner UID
        id: uid
        run: echo "user_id=$(id -u)" >> "$GITHUB_OUTPUT"

      - name: Compute cache key
        id: key
        env:
          UID_VAL: ${{ steps.uid.outputs.user_id }}
          # hashFiles() is ONLY valid in a step-level env: block, never
          # at job level. Adjust the file list to match the upstream
          # caching action exactly.
          DOCKERFILE_HASH: ${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
        run: |
          if [ -n "${KEY_HASH_OVERRIDE}" ]; then
            hash="${KEY_HASH_OVERRIDE}"
          else
            hash="${DOCKERFILE_HASH}"
          fi
          key="container-image-uid${UID_VAL}-${hash}"
          echo "key=${key}" >> "$GITHUB_OUTPUT"
          echo "Resolved cache key: ${key}"

      - name: Restore cached image tar
        id: cache
        uses: actions/cache/restore@1bd1e32a3bdc45362d1e726936510720a7c30a57  # v4
        with:
          path: /tmp/podman-image-cache
          key: ${{ steps.key.outputs.key }}

      - name: Report cache state
        env:
          CACHE_HIT: ${{ steps.cache.outputs.cache-hit }}
          CACHE_KEY: ${{ steps.key.outputs.key }}
        run: |
          if [ "${CACHE_HIT}" = "true" ]; then
            echo "::notice::cache hit on $(date -Iseconds) for key ${CACHE_KEY}"
            if ! ls -la /tmp/podman-image-cache/; then
              echo "warn: could not list cache dir" >&2
            fi
            if [ -f /tmp/podman-image-cache/dev.tar ]; then
              SIZE=$(stat -c %s /tmp/podman-image-cache/dev.tar)
              echo "::notice::image tar size: ${SIZE} bytes ($((SIZE / 1024 / 1024)) MB)"
              sha256sum /tmp/podman-image-cache/dev.tar
            fi
          else
            echo "::error::cache MISS for key ${CACHE_KEY}"
            echo "(Either the key changed or the entry was evicted.)"
            exit 1
          fi

      - name: Bundle metadata
        env:
          CACHE_KEY: ${{ steps.key.outputs.key }}
          UID_VAL: ${{ steps.uid.outputs.user_id }}
          HEAD_REF: ${{ github.ref }}
          HEAD_SHA: ${{ github.sha }}
        run: |
          mkdir -p extract-bundle
          cp /tmp/podman-image-cache/dev.tar extract-bundle/dev.tar
          {
            echo "=== Extracted by extract-cached-image.yml on $(date -Iseconds) ==="
            echo "cache key:    ${CACHE_KEY}"
            echo "ref:          ${HEAD_REF}"
            echo "head sha:     ${HEAD_SHA}"
            echo "runner uid:   ${UID_VAL}"
            echo "tar size:     $(stat -c %s extract-bundle/dev.tar) bytes"
            echo "tar sha256:   $(sha256sum extract-bundle/dev.tar | awk '{print $1}')"
            echo
            echo "=== Source file hashes that feed the cache key ==="
            for f in Dockerfile pixi.toml pixi.lock; do
              echo "${f}  sha256:  $(sha256sum "${f}" | awk '{print $1}')"
            done
          } > extract-bundle/manifest.txt
          cat extract-bundle/manifest.txt

      - name: Upload image tar artifact
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7
        with:
          name: container-image-${{ steps.key.outputs.key }}
          path: extract-bundle/
          retention-days: 7
          if-no-files-found: error
```

### Local download + load commands

```bash
# Dispatch on the branch you care about
gh workflow run extract-cached-image.yml --ref bisect/6413-positive-control

# Find the most recent run
RUN_ID=$(gh run list \
  --workflow=extract-cached-image.yml \
  --limit=1 \
  --json databaseId --jq '.[0].databaseId')

# Wait for it to complete
gh run watch "$RUN_ID"

# Download the artifact (defaults to current directory)
gh run download "$RUN_ID"

# Verify the bytes match the manifest before trusting them
sha256sum container-image-*/dev.tar
cat container-image-*/manifest.txt

# Load and run
podman load -i container-image-*/dev.tar
podman images | head
podman run --rm -it <loaded-image-tag> bash
```

### Observed sizes (ProjectOdyssey, May 2026)

| Metric | Value |
|---|---|
| `dev.tar` uncompressed | ~2.7 GB |
| `dev.tar` compressed (artifact upload) | ~760 MB |
| Download time on home connection | ~2-5 min |
| Extraction time on ubuntu-latest runner | ~30 s (cache restore is the bulk) |

### Adjustment matrix for other repos

| Upstream caching uses... | Adjust this in the workflow |
|---|---|
| Different `hashFiles()` inputs (e.g. `Containerfile`, `poetry.lock`) | The `DOCKERFILE_HASH` expression in the **Compute cache key** step |
| No UID prefix in the key | Drop the `uid${UID_VAL}-` portion of the key string |
| A different cache `path:` (e.g. `/var/cache/image.tar`) | The `path:` field in the **Restore cached image tar** step |
| A tarball with a different filename | The `/tmp/podman-image-cache/dev.tar` paths in **Report cache state** and **Bundle metadata** |
| Docker (not Podman) | The `podman load -i` becomes `docker load -i`; everything else is identical |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey (HomericIntelligence) | PR #5399 / commit `45abbe13` on branch `bisect/6413-positive-control`. Used to extract the ~2.7 GB cached image tarball during forensic investigation of modular/modular#6413 (Mojo JIT SIGILL on GHA Azure runners). Workflow dispatched manually, cache hit on first try after fixing the job-level `hashFiles()` bug, artifact downloaded and `podman load`-ed successfully on developer workstation. | See PR #5399 description and the file `.github/workflows/extract-cached-image.yml` at commit `45abbe13`. |
