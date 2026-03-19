---
name: podman-nextjs-ci-container
description: "Build Podman/Docker dev containers for Next.js projects with full CI simulation. Use when: creating Containerfiles for Node.js/Next.js, running CI in containers, debugging native module builds."
category: ci-cd
date: 2026-03-19
user-invocable: false
---

# Podman Next.js CI Container

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Create a Podman dev container that runs the full CI pipeline (test, lint, typecheck, build) for a Next.js project with native Node modules |
| **Stack** | Next.js 14, Vitest, ESLint, TypeScript, node-pty, Podman |
| **Base Image** | `docker.io/library/node:20.19.2-bookworm-slim` |
| **Result** | 486 tests pass, lint clean, tsc clean, build succeeds — all inside container |

## When to Use

- Creating a `Containerfile` or `Dockerfile` for a Next.js project
- Setting up containerized CI that includes test, lint, typecheck, and build steps
- Debugging Podman/Docker build failures involving native Node.js modules (node-pty, cozo-node)
- Needing reproducible builds across different developer machines
- Running sequential CI steps (test → lint → tsc → build) in a single container

## Verified Workflow

### Quick Reference

```bash
# Build
podman build -t ai-maestro-dev -f Containerfile .

# Run individual checks
podman run --rm ai-maestro-dev yarn test
podman run --rm ai-maestro-dev yarn lint
podman run --rm ai-maestro-dev yarn build

# Full CI chain
podman run --rm ai-maestro-dev sh -c 'yarn test && yarn lint && npx tsc --noEmit && (rm -rf .next || true) && yarn build'

# Interactive shell
podman run --rm -it ai-maestro-dev bash
```

### Step 1: Choose the Right Base Image

Use a specific pinned version of Node that satisfies all dependency requirements:

```dockerfile
FROM docker.io/library/node:20.19.2-bookworm-slim
```

**Critical:** Always use the fully-qualified `docker.io/library/` prefix — Podman fails with short names.

### Step 2: Install System Dependencies for Native Modules

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3 \
    git \
    && rm -rf /var/lib/apt/lists/*
```

`build-essential` + `python3` are required for native module compilation (node-gyp).

### Step 3: Layer-Cache Dependencies

```dockerfile
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile && yarn cache clean
COPY . .
```

Copy manifests before source so dependency installation is cached unless package.json/yarn.lock change.

**Critical:** If you modify package.json (e.g., adding scripts), you MUST run `yarn install` on the host first to update yarn.lock. Otherwise `--frozen-lockfile` will fail.

### Step 4: Non-Root User and Memory Settings

```dockerfile
RUN chown -R node:node /app
USER node
ENV NODE_OPTIONS="--max-old-space-size=4096"
```

- The `node` user already exists in the base image (UID/GID 1000) — don't try to create it
- 4GB heap is required for Next.js production builds in containers

### Step 5: Container Ignore File

Create `.containerignore`:
```
node_modules
.next
.git
*.md
!package.json
marketing/
docs/images/
.env*
.DS_Store
```

### Step 6: Package.json Scripts

```json
{
  "container:build": "podman build -t ai-maestro-dev -f Containerfile .",
  "container:test": "podman run --rm ai-maestro-dev yarn test",
  "container:lint": "podman run --rm ai-maestro-dev yarn lint",
  "container:build-app": "podman run --rm ai-maestro-dev yarn build",
  "container:shell": "podman run --rm -it ai-maestro-dev bash",
  "container:ci": "podman run --rm ai-maestro-dev sh -c 'yarn test && yarn lint && npx tsc --noEmit && (rm -rf .next || true) && yarn build'"
}
```

### Step 7: Stale .next Cache Fix

When running build after other steps sequentially, the `.next` directory from a previous build can cause hangs. Always clean it:

```bash
(rm -rf .next || true) && yarn build
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| node:20.18.3 base image | Used older Node LTS | vite 7.3.1 requires >=20.19.0, build failed with engine incompatibility | Always check vite/next engine requirements before picking Node version |
| `npm install -g yarn` in Dockerfile | Tried installing yarn globally | yarn is pre-installed in official node images, command fails | Check what's already in the base image before adding install steps |
| `groupadd -g 1000 node` | Tried creating node user with GID 1000 | GID 1000 already taken by existing `node` user in base image | Use the existing `node` user — it's already set up correctly |
| Short image names (`node:20.19.2`) | Used Docker-style short names | Podman requires fully-qualified names, fails to resolve | Always prefix with `docker.io/library/` for Podman compatibility |
| Sequential test+lint+tsc+build without .next cleanup | Ran all CI steps in sequence | Build step hangs due to stale `.next` cache from previous runs | Add `rm -rf .next` before the build step in CI chains |
| Default Node heap size | Ran Next.js build without memory override | OOM crash during production build in constrained container | Set `NODE_OPTIONS="--max-old-space-size=4096"` for Next.js builds |

## Results & Parameters

### Containerfile (Complete)

```dockerfile
# AI Maestro Dev Container
FROM docker.io/library/node:20.19.2-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile && yarn cache clean
COPY . .

RUN chown -R node:node /app
USER node
ENV NODE_OPTIONS="--max-old-space-size=4096"

CMD ["yarn", "test"]
```

### Verified CI Results (in container)

| Check | Command | Result |
|-------|---------|--------|
| Tests | `yarn test` | 486 tests pass, 13 test files |
| Lint | `yarn lint` | Warnings only, no errors |
| Typecheck | `npx tsc --noEmit` | Clean |
| Build | `yarn build` | 53 pages generated |
| Full CI | `container:ci` script | All 4 steps pass sequentially |

### Key Configuration

| Parameter | Value | Why |
|-----------|-------|-----|
| Node version | 20.19.2 | Minimum for vite 7.3.1 |
| Base image | bookworm-slim | Minimal Debian with native build support |
| Heap size | 4096 MB | Required for Next.js production builds |
| User | `node` (existing) | Non-root, pre-configured in base image |
| yarn flag | `--frozen-lockfile` | Reproducible installs, fails if lockfile stale |
