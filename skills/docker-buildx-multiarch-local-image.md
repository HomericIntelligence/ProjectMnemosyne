---
name: docker-buildx-multiarch-local-image
description: "Use when: (1) a multi-arch Docker buildx job fails with 'pull access denied' for a locally-built base image, (2) chaining two buildx multi-arch builds where the second depends on the first's image, (3) using docker-container buildx driver and needing to pass a base image to a downstream build, (4) oci-layout reference fails with 'not a directory' error, (5) arm64 binary check silently passes despite QEMU missing."
category: ci-cd
date: 2026-04-24
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: docker-buildx-multiarch-local-image.history
tags: [docker, buildx, multi-arch, oci, local-image, base-image, github-actions, ci, qemu, oci-layout]
---

# Docker Buildx Multi-Arch Local Image Chaining

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Chain two multi-arch buildx builds without a registry when the second depends on the first |
| **Outcome** | OCI layout directory export + build-contexts reference pattern resolves pull access denied; CI passed |
| **Verification** | verified-ci |
| **History** | [changelog](./docker-buildx-multiarch-local-image.history) |

## When to Use

- A GitHub Actions CI job builds a base image with buildx, then builds a vessel/child image that uses it
- The vessel build fails with `pull access denied for <base-image>` or `not found`
- You are using the default `docker-container` buildx driver (which does NOT share the Docker daemon image store)
- You cannot or do not want to push the base image to a registry just to use it in the same CI job
- `oci-layout` reference fails with: `oci-layout reference "oci-layout:///tmp/foo.tar" could not be resolved: not a directory`
- A `RUN <binary> --version || true` step silently passes on arm64 even when the binary fails (QEMU missing)

## Verified Workflow

### Quick Reference

```yaml
# CRITICAL: QEMU must come BEFORE buildx setup
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3

# Step 1: Build base image — export as OCI layout DIRECTORY (no .tar extension)
- name: Build base image
  uses: docker/build-push-action@v6
  with:
    file: bases/Dockerfile.minimal
    platforms: linux/amd64,linux/arm64
    outputs: type=oci,dest=/tmp/base-minimal        # NO .tar — saves as directory
    tags: achaean-base-minimal:latest

# Step 2: Build vessel — reference OCI layout directory (no .tar)
- name: Build vessel image
  uses: docker/build-push-action@v6
  with:
    file: vessels/goose/Dockerfile
    platforms: linux/amd64,linux/arm64
    build-contexts: achaean-base-minimal:latest=oci-layout:///tmp/base-minimal    # NO .tar
    build-args: BASE_IMAGE=achaean-base-minimal:latest
    push: true
    tags: ghcr.io/org/achaean-goose:latest
```

### Detailed Steps

1. **Diagnose**: Confirm you are using the docker-container buildx driver:
   ```yaml
   - uses: docker/setup-buildx-action@v3
     # No 'driver: docker' → defaults to docker-container driver
   ```

2. **Set up QEMU before buildx** (required for cross-arch emulation):
   ```yaml
   - uses: docker/setup-qemu-action@v3    # MUST come first
   - uses: docker/setup-buildx-action@v3  # MUST come second
   ```
   Without QEMU, arm64 `RUN` steps execute under the wrong emulator context. A `|| true`
   guard will silently pass even when the binary fails or doesn't exist.

3. **Export base image as OCI layout directory** (no `.tar` extension):
   ```yaml
   outputs: type=oci,dest=/tmp/base-<name>    # No .tar extension!
   ```
   - With `.tar` extension: buildx writes a single `.tar` archive file.
   - Without `.tar` extension: buildx writes an OCI layout directory (`index.json`, `blobs/`, etc.).
   - `oci-layout://` requires a **directory** — pointing it at a `.tar` file fails with "not a directory".

4. **Reference the OCI layout directory in the downstream build** using `build-contexts`:
   ```yaml
   build-contexts: <image-name>=oci-layout:///tmp/<name>    # No .tar
   ```
   The image name in `build-contexts` must exactly match the `FROM` line in the Dockerfile
   (or the `BASE_IMAGE` build-arg value).

5. **Verify the vessel Dockerfile uses the build-arg**:
   ```dockerfile
   ARG BASE_IMAGE=achaean-base-minimal:latest
   FROM ${BASE_IMAGE}
   ```

6. **Remove `|| true` guards** from `RUN` checks once QEMU is confirmed present:
   ```dockerfile
   # WRONG (hides failures):
   RUN goose --version || true
   # CORRECT (fails the build if binary missing/wrong arch):
   RUN goose --version
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `type=oci,dest=/tmp/foo.tar` + `oci-layout:///tmp/foo.tar` | Added `.tar` extension to dest and oci-layout path, thinking it referenced the archive | `oci-layout://` requires a directory; `.tar` creates a single archive file — fails with `not a directory` | Omit `.tar` extension entirely so buildx saves an OCI layout directory |
| QEMU step missing, arm64 check with `\|\| true` | Forgot `docker/setup-qemu-action`; `RUN goose --version \|\| true` passed silently | Without QEMU, arm64 binary invocations fail silently when guarded by `\|\| true` | Set up QEMU before buildx; remove `\|\| true` once QEMU is confirmed present |
| `RUN goose --version \|\| true` with QEMU present | Kept `\|\| true` even after fixing QEMU ordering | `\|\| true` masks all failures regardless of QEMU; real binary errors won't fail the build | Always remove `\|\| true` from version/sanity checks after confirming QEMU is set up |
| Build base with `outputs: type=docker,dest=/tmp/base.tar` then load | Used docker output type thinking it would work like OCI | `type=docker` does not support multi-platform builds — build fails with "multiple platforms not supported" | Use `type=oci` for multi-arch OCI archives; `type=docker` is single-platform only |
| Build base with `load: true`, reference by image name in vessel | Used `load: true` to push into daemon, then let vessel FROM pull from daemon | `docker-container` driver builds in an isolated container that does NOT share the host Docker daemon image store; vessel build cannot resolve the image | Either switch to `driver: docker` (loses multi-arch) or export via OCI layout directory |
| Switch buildx driver to `driver: docker` | Set `driver: docker` in setup-buildx-action | Works for single-arch, but `driver: docker` does NOT support multi-platform builds — `--platform linux/amd64,linux/arm64` fails | Only use `driver: docker` when multi-arch is not needed; for multi-arch use OCI layout directory pattern |
| Push base to registry, reference by registry URL | Built and pushed base to GHCR, then referenced in vessel FROM | Adds registry round-trip latency and requires push permissions for intermediate images; overly complex | OCI layout directory via `/tmp` is simpler and faster for same-job chaining |

## Results & Parameters

### OCI Layout: Directory vs Tarball

| `dest=` value | Result on disk | `oci-layout://` compatible? |
| --------------- | ---------------- | ------------------------------ |
| `/tmp/foo.tar` | Single `.tar` archive file | No — fails with "not a directory" |
| `/tmp/foo` | OCI layout directory (`index.json`, `blobs/`, `oci-layout`) | Yes |

**Rule**: Always omit `.tar` from `dest=` when the output will be consumed via `oci-layout://`.

### QEMU + Buildx Step Order

```yaml
# CORRECT order — QEMU registers binfmt handlers before buildx starts
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3

# WRONG order — buildx starts without arm64 emulation available
- uses: docker/setup-buildx-action@v3
- uses: docker/setup-qemu-action@v3
```

### Driver Comparison

| Driver | Multi-Arch | Shares Daemon Store | Best For |
| -------- | ----------- | --------------------- | ---------- |
| `docker-container` (default) | Yes | No | Multi-arch builds, caching, push to registry |
| `docker` | No | Yes | Single-arch builds, load into local daemon |

### OCI Layout Directory Pattern Template

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-qemu-action@v3      # MUST be before buildx

      - uses: docker/setup-buildx-action@v3    # MUST be after QEMU

      - name: Build base image (OCI layout directory — no .tar)
        uses: docker/build-push-action@v6
        with:
          file: bases/Dockerfile.node
          platforms: linux/amd64,linux/arm64
          outputs: type=oci,dest=/tmp/base-node    # No .tar
          tags: achaean-base-node:latest

      - name: Build vessel image
        uses: docker/build-push-action@v6
        with:
          file: vessels/claude/Dockerfile
          platforms: linux/amd64,linux/arm64
          build-contexts: achaean-base-node:latest=oci-layout:///tmp/base-node    # No .tar
          build-args: BASE_IMAGE=achaean-base-node:latest
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/achaean-claude:latest
```

### Key Notes

- `oci-layout://` prefix is required in `build-contexts` value
- The path after `oci-layout://` must point to a **directory**, not a `.tar` file
- The path must be absolute (use `/tmp/` not `./tmp/`)
- The image name key in `build-contexts` must exactly match what the Dockerfile's `FROM` resolves to
- `docker/setup-qemu-action` must come BEFORE `docker/setup-buildx-action`
- Remove `|| true` from `RUN` checks once QEMU is confirmed in the correct position
- This works without any registry — base image stays local to the runner

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | CI repair — goose multi-arch vessel build failing with pull access denied | 2026-04-23; OCI tarball pattern resolved the issue, CI passed |
| AchaeanFleet | CI repair — build-goose-multiarch job; oci-layout "not a directory" + QEMU ordering | 2026-04-24; directory (no .tar) + QEMU-before-buildx pattern resolved all failures, CI passed |
