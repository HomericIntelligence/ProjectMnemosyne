---
name: container-image-security-patching
version: 1.0.0
description: "Fix Trivy container scan failures by bumping pinned base image digests, adding apt-get upgrade, and running npm audit fix. Use when: Trivy CI step fails with HIGH/CRITICAL CVEs, docker-build-timing workflow fails on all branches, or base image has known vulnerabilities."
category: ci-cd
date: 2026-03-22
user-invocable: false
---

# Container Image Security Patching

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Trivy vulnerability scan fails CI with HIGH/CRITICAL CVEs in pinned base images |
| **Root Cause** | SHA256-pinned base images freeze OS packages and npm deps at a point in time |
| **Fix** | Bump digests + add apt-get upgrade + npm audit fix as defense-in-depth |
| **CI Workflow** | docker-test.yml / ci-image.yml with `aquasecurity/trivy-action` |
| **Impact** | Was failing on every branch for 3+ days before diagnosis |

## When to Use

- Trivy scan step fails with `Total: N (HIGH: X, CRITICAL: Y)`
- `docker-build-timing` or `ci-image` workflow fails on all branches (not just your PR)
- `gh run list --workflow docker-test.yml` shows consecutive failures across branches
- CVEs are in OS packages (libc-bin, openssl) or npm transitive deps (cross-spawn, minimatch, tar)
- Base image is pinned to SHA256 digest (reproducibility pattern)

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the CVEs
gh run view <run_id> --log-failed 2>&1 | grep -E "CVE|Total:"

# 2. Pull latest base images and get new digests
docker pull python:3.12-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
docker pull node:20-slim
docker inspect --format='{{index .RepoDigests 0}}' node:20-slim

# 3. Update Dockerfile SHA256 digests (replace_all for multiple FROM lines)
# 4. Add apt-get upgrade in runtime stage
# 5. Add npm audit fix after npm install -g
# 6. Update ci/Containerfile with same digests
```

### Step 1: Diagnose — confirm it's a base image issue

```bash
# Check if failure is pre-existing (not caused by your PR)
gh run list --workflow docker-test.yml --limit 5 --json conclusion,headBranch
# If all branches show "failure", it's a base image issue

# Get the specific CVEs
gh run view <run_id> --log-failed 2>&1 | grep -E "CVE|Total:"
```

Two categories of CVEs:
- **OS-level** (libc-bin, openssl, etc.) — from `python:X-slim` or `debian:X` base
- **npm transitive deps** (cross-spawn, glob, minimatch, tar) — from `node:X-slim` bundled npm

### Step 2: Bump base image digests

```bash
# Get latest digests
docker pull python:3.12-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
# → python@sha256:NEWDIGEST

docker pull node:20-slim
docker inspect --format='{{index .RepoDigests 0}}' node:20-slim
# → node@sha256:NEWDIGEST
```

Replace ALL occurrences of the old SHA in `docker/Dockerfile` and `ci/Containerfile`:
```dockerfile
# Before
FROM python:3.12-slim@sha256:OLDDIGEST
# After
FROM python:3.12-slim@sha256:NEWDIGEST
```

### Step 3: Add defense-in-depth patches

Even with bumped digests, add these layers for future CVEs:

**OS packages** — add `apt-get upgrade` in the runtime stage:
```dockerfile
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

**npm packages** — add `npm audit fix` after CLI install:
```dockerfile
RUN npm install -g @anthropic-ai/claude-code@2.1.74 \
    && cd /usr/local/lib/node_modules/@anthropic-ai/claude-code \
    && npm audit fix --force 2>/dev/null || true
```

### Step 4: Update ALL Dockerfiles consistently

Check for the old digest in both:
- `docker/Dockerfile` (experiment runner image)
- `ci/Containerfile` (CI image)

Both must use the same digest for consistency.

### Step 5: Verify locally (optional)

```bash
docker build -f docker/Dockerfile -t scylla-runner:test .
docker run --rm aquasec/trivy image --severity HIGH,CRITICAL scylla-runner:test
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Only bumping python:3.12-slim digest | Updated Python base image SHA only | npm CVEs from node:20-slim remained (cross-spawn, minimatch, tar) | Must bump ALL pinned image digests, not just the primary base |
| Pinning to SHA256 without upgrade | Relied solely on digest pinning for security | Pinned images freeze vulnerabilities at the pin date; no automatic patches | Digest pinning gives reproducibility but needs periodic bumps + apt-get upgrade as fallback |
| Ignoring docker-test failures | Assumed Trivy failures were transient | Failure persisted for 3+ days across all branches, blocking PRs | Check `gh run list --workflow X` across branches; if ALL fail, it's infra not your code |

## Results & Parameters

### Dockerfile Pattern (Copy-Paste)

```dockerfile
# Base image with SHA256 pin (update periodically)
FROM python:3.12-slim@sha256:DIGEST_HERE

# OS-level CVE patching (defense-in-depth)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js from pinned source stage
FROM node:20-slim@sha256:DIGEST_HERE AS node-source

# npm CVE patching after CLI install
RUN npm install -g @anthropic-ai/claude-code@X.Y.Z \
    && cd /usr/local/lib/node_modules/@anthropic-ai/claude-code \
    && npm audit fix --force 2>/dev/null || true
```

### CI Workflow Pattern (Trivy)

```yaml
- uses: aquasecurity/trivy-action@0.35.0
  with:
    image-ref: ${{ env.IMAGE_TAG }}
    format: table
    exit-code: '1'           # Fail CI on findings
    ignore-unfixed: true     # Skip unfixed CVEs
    severity: HIGH,CRITICAL  # Only block on serious issues
```

### Key Files

| File | Purpose |
|------|---------|
| `docker/Dockerfile` | Experiment runner image (python + node + claude-code) |
| `ci/Containerfile` | CI image (python + pixi + pre-commit) |
| `.github/workflows/docker-test.yml` | Docker build timing + Trivy scan |
| `.github/workflows/ci-image.yml` | CI image build + Trivy scan |

### Maintenance Schedule

Weekly CI workflows (`ci-image.yml` schedule: Monday 06:00 UTC) rebuild images to pick up base image patches. But if the pinned SHA doesn't change, the same vulnerable packages persist. Bump digests monthly or when Trivy blocks CI.
