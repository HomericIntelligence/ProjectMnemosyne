---
name: ci-cd-opencode-asset-arch-naming
description: 'Documents that opencode (sst/opencode) release assets use x64 (not amd64)
  in their filenames, requiring a TARGETARCH→arch mapping case statement in Dockerfiles.
  Use when: building a vessel Dockerfile for opencode or downloading opencode release
  assets in CI, and getting 404 errors for asset downloads.'
category: ci-cd
date: 2026-04-24
version: 1.0.0
user-invocable: false
---
# ci-cd-opencode-asset-arch-naming

The `sst/opencode` project uses Node.js/npm ecosystem asset naming conventions, not the
Linux standard (`amd64`/`arm64`). The amd64 asset is named `opencode-linux-x64.tar.gz`,
not `opencode_linux_amd64.tar.gz`. Docker's `TARGETARCH` build arg must be mapped via a
`case` statement before constructing the download URL.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-04-24 |
| PR | AchaeanFleet #547 |
| Objective | Fix opencode vessel Dockerfile to download correct release asset for amd64/arm64 |
| Outcome | Success — CI passed after adding TARGETARCH→arch case statement (verified-ci) |
| Category | ci-cd |
| Project | AchaeanFleet |

## Key Fact: opencode Asset Naming Convention

opencode uses **hyphen-separated** names with **x64** (not amd64) for the x86-64 architecture.

| Docker TARGETARCH | opencode asset filename |
| ------------------- | ------------------------ |
| `amd64` | `opencode-linux-x64.tar.gz` |
| `arm64` | `opencode-linux-arm64.tar.gz` |

This follows the Node.js/npm naming convention since opencode is a TypeScript/Bun project,
not the Linux tool convention used by most Go/Rust binaries.

## Contrast: Naming Conventions Across Tools

| Tool | Ecosystem | amd64 asset name | arm64 asset name |
| ------ | ----------- | ----------------- | ----------------- |
| opencode | TypeScript/Bun | `opencode-linux-x64.tar.gz` | `opencode-linux-arm64.tar.gz` |
| yq | Go | `yq_linux_amd64` | `yq_linux_arm64` |
| goose | Rust | `x86_64-unknown-linux-gnu` | `aarch64-unknown-linux-gnu` |

**Rule**: Always verify release asset names with `gh api` before hardcoding any download URL
in a Dockerfile or CI script.

## When to Use

- Writing or updating a Dockerfile that downloads opencode from GitHub releases
- Getting HTTP 404 errors when downloading opencode in a Docker build or CI pipeline
- Implementing multi-arch (`--platform linux/amd64,linux/arm64`) builds for opencode vessels
- Auditing other Dockerfiles that reference non-standard asset naming

## Verified Workflow

### Step 1: Verify release asset names

Always check the actual asset names before writing the Dockerfile:

```bash
gh api "repos/sst/opencode/releases/tags/v1.4.3" --jq '.assets[].name'
# Output includes:
# opencode-linux-x64.tar.gz
# opencode-linux-arm64.tar.gz
# opencode-darwin-arm64.tar.gz
# opencode-darwin-x64.tar.gz
# opencode-win32-x64.zip
```

For the latest release:

```bash
gh api "repos/sst/opencode/releases/latest" --jq '.assets[].name'
```

### Step 2: Write the Dockerfile with a TARGETARCH mapping case statement

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG OPENCODE_VERSION=v1.4.3
ARG TARGETARCH=amd64

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN case "${TARGETARCH}" in \
      amd64) OPENCODE_ARCH="x64" ;; \
      arm64) OPENCODE_ARCH="arm64" ;; \
      *) echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/sst/opencode/releases/download/${OPENCODE_VERSION}/opencode-linux-${OPENCODE_ARCH}.tar.gz" \
        -o /tmp/opencode.tar.gz && \
    tar -xzf /tmp/opencode.tar.gz -C /usr/local/bin && \
    rm /tmp/opencode.tar.gz && \
    chmod +x /usr/local/bin/opencode
```

### Step 3: Why `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` is needed

Docker's default shell (`/bin/sh -c`) does not support `pipefail`. Setting the shell to bash
with `pipefail` ensures that a failure in any piped command (e.g., `curl | tar`) causes the
`RUN` step to fail rather than silently succeeding with a corrupt binary.

This must be set before any multi-command `RUN` step that uses pipes or `case`.

### Step 4: Build multi-arch locally to verify

```bash
# Test amd64
docker build -f vessels/opencode/Dockerfile \
  --build-arg BASE_IMAGE=achaean-base-node:latest \
  --build-arg TARGETARCH=amd64 \
  -t achaean-opencode:amd64-test .

# Test arm64 (requires QEMU or buildx)
docker buildx build -f vessels/opencode/Dockerfile \
  --platform linux/arm64 \
  --build-arg BASE_IMAGE=achaean-base-node:latest \
  -t achaean-opencode:arm64-test .
```

### Step 5: Commit and PR

```bash
git add vessels/opencode/Dockerfile
git commit -m "fix(opencode): map TARGETARCH to x64/arm64 for release asset download

opencode uses Node.js/npm asset naming: amd64→x64, hyphen-separated.
The incorrect filename opencode_linux_amd64.tar.gz does not exist in
the sst/opencode releases. Use opencode-linux-x64.tar.gz for amd64.

Also add pipefail shell option required for case statement RUN steps."

git push -u origin <branch>
gh pr create --title "fix(opencode): correct asset arch naming in vessel Dockerfile"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `opencode_linux_amd64.tar.gz` | Used Go-style underscore+amd64 naming (common for most Linux tools) | Asset does not exist in sst/opencode releases; curl returns 404 | opencode follows Node.js/npm naming: `x64` not `amd64`, hyphens not underscores |
| Hardcoded amd64 path without TARGETARCH | Built single-arch image without case statement | Image fails on arm64 hosts or multi-arch CI matrix | Always add TARGETARCH mapping for any binary supporting multiple architectures |

## Results & Parameters

### Files changed

| File | Change |
| ------ | -------- |
| `vessels/opencode/Dockerfile` | Add `ARG TARGETARCH=amd64`, `SHELL` directive, `case` statement mapping TARGETARCH to opencode arch name |

### The case statement pattern

```dockerfile
ARG TARGETARCH=amd64
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN case "${TARGETARCH}" in \
      amd64) OPENCODE_ARCH="x64" ;; \
      arm64) OPENCODE_ARCH="arm64" ;; \
      *) echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/sst/opencode/releases/download/${OPENCODE_VERSION}/opencode-linux-${OPENCODE_ARCH}.tar.gz" \
        ...
```

The `ARG TARGETARCH=amd64` default value ensures the Dockerfile works without `--platform`
or `--build-arg TARGETARCH=...` for local single-arch builds. Docker's BuildKit automatically
sets `TARGETARCH` when using `--platform`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | PR #547, vessels/opencode/Dockerfile | verified-ci |

## Related Skills

- **dockerfile-env-version-pin** — Pin tool versions in Dockerfiles via ARG/ENV
- **dockerfile-cargo-to-prebuilt-binary** — Replace slow builds with pre-built binary downloads
- **docker-buildx-multiarch-local-image** — Multi-arch build patterns with buildx

## References

- sst/opencode releases: <https://github.com/sst/opencode/releases>
- AchaeanFleet PR #547: (AchaeanFleet internal)
- Node.js download naming convention: <https://nodejs.org/dist/> (uses `x64` not `amd64`)
