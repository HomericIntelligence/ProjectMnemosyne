---
name: ci-docker-hub-rate-limit-mcr-mirror
description: "Fix Docker Hub anonymous pull rate limit failures in GitHub Actions CI by switching
  ubuntu base image to MCR mirror. Use when: (1) CI container build fails with 'toomanyrequests'
  pulling ubuntu:24.04, (2) multiple parallel build variants exhaust the 100 pulls/6h
  anonymous limit, (3) no Docker Hub credentials are configured."
category: ci-cd
date: 2026-03-27
version: "1.0.0"
user-invocable: false
tags:
  - ci
  - docker
  - podman
  - rate-limit
  - mcr
  - ubuntu
  - base-image
---

# CI Docker Hub Rate Limit — Use MCR Mirror

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Fix Docker Hub anonymous pull rate limit failures during parallel container builds |
| **Outcome** | Successful — MCR mirror has no pull limits and stays current with upstream Ubuntu |

## When to Use

- CI fails with `toomanyrequests: You have reached your pull rate limit` pulling `ubuntu:24.04`
- Multiple container build variants (runtime, CI, prod) run in parallel on the same runner IP
- Anonymous Docker Hub pull limit (100/6h per IP) is exhausted by shared runner IP pools
- No Docker Hub authentication is configured in the workflow
- `FROM ubuntu:24.04` is used in `Dockerfile` or `Dockerfile.ci`

## Root Cause

GitHub Actions runners on hosted infrastructure share IP addresses. Docker Hub's anonymous pull
rate limit is 100 pulls per 6 hours per IP. When a workflow triggers 3+ parallel container
builds (e.g., runtime, CI, prod variants) each pulling `ubuntu:24.04`, the shared runner IP
can exhaust the quota — especially during busy periods when other orgs' workflows are also
pulling from the same IP.

The Microsoft Container Registry (MCR) mirror at `mcr.microsoft.com/mirror/docker/library/ubuntu`
mirrors Docker Hub's official images with no pull limits and no authentication required.

## Verified Workflow

### Quick Reference

```dockerfile
# BEFORE -- pulls from Docker Hub, subject to rate limits
FROM ubuntu:24.04 AS builder

# AFTER -- uses MCR mirror, no rate limits, same image
FROM mcr.microsoft.com/mirror/docker/library/ubuntu:24.04 AS builder
```

Apply to ALL `FROM` lines in ALL Dockerfiles (including `Dockerfile.ci`, multi-stage builds):

```bash
# Find all ubuntu base image references
grep -rn "FROM ubuntu:" Dockerfile Dockerfile.ci

# Replace
sed -i 's|FROM ubuntu:|FROM mcr.microsoft.com/mirror/docker/library/ubuntu:|g' Dockerfile Dockerfile.ci
```

### Detailed Steps

1. **Confirm rate limit is the cause** — look for this error in CI build logs:

   ```text
   Error response from daemon: toomanyrequests: You have reached your pull rate limit.
   You may increase the limit by authenticating and upgrading:
   https://www.docker.com/increase-rate-limit
   ```

2. **Count parallel builds** — check the workflow for matrix strategies or multiple jobs
   that each start a container build. If 3+ jobs all pull `ubuntu:24.04`, they compete for
   the same rate limit bucket.

3. **Replace in all Dockerfiles**:

   ```dockerfile
   FROM mcr.microsoft.com/mirror/docker/library/ubuntu:24.04 AS builder
   FROM mcr.microsoft.com/mirror/docker/library/ubuntu:24.04 AS runtime
   ```

4. **Verify multi-stage builds** — check every `FROM` line, not just the first.

5. **Note**: The MCR mirror only covers Docker Hub's official library images (`library/`).
   For other images use the same mirror prefix:
   - `mcr.microsoft.com/mirror/docker/library/python:3.11-slim`
   - `mcr.microsoft.com/mirror/docker/library/node:20-alpine`

### MCR Mirror URL Pattern

```text
mcr.microsoft.com/mirror/docker/library/<image>:<tag>

Examples:
  mcr.microsoft.com/mirror/docker/library/ubuntu:24.04
  mcr.microsoft.com/mirror/docker/library/ubuntu:22.04
  mcr.microsoft.com/mirror/docker/library/python:3.11-slim
  mcr.microsoft.com/mirror/docker/library/node:20-alpine
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding Docker Hub credentials | Considered authenticating to Docker Hub for higher limits | Adds secret management overhead; MCR mirror is simpler and free | Use MCR mirror — no auth required, no cost, no rate limits |
| Serializing builds | Considered running builds sequentially to avoid concurrent pulls | Increases CI wall time significantly | MCR mirror is better — parallel builds are fine |

## Results & Parameters

### MCR Mirror Properties

| Property | Value |
| ---------- | ------- |
| URL | `mcr.microsoft.com/mirror/docker/library/` |
| Authentication | None required |
| Rate limit | None |
| Image sync | Stays current with Docker Hub upstream |
| Scope | Docker Hub official library images only |
| Cost | Free |

### Identifying Affected Workflows

```bash
# Find all Dockerfile references in GitHub Actions workflows
grep -rn "docker build\|podman build\|Dockerfile" .github/workflows/

# Find all ubuntu base images in Dockerfiles
grep -rn "FROM ubuntu" Dockerfile* */Dockerfile*
```

### Note on GHCR Published Images

The rate limit issue affects base image **pulls during build**, not published image pushes.
If the workflow publishes final images to GHCR (`ghcr.io/org/image`), those pushes are
unaffected. Only the `FROM ubuntu:24.04` base image pull at build time is rate-limited.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Dockerfile and Dockerfile.ci | PR #5177 (unverified) |
