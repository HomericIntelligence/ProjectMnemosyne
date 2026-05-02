---
name: dockerfile-layer-caching
description: Optimize Docker layer caching for Python packages when source changes
  more often than dependencies to prevent pip from reinstalling all dependencies on
  every source-only change.
category: ci-cd
date: 2026-02-27
version: 1.0.0
title: Dockerfile Layer Caching for Python Packages
outcome: success
---
# Skill: Dockerfile Layer Caching for Python Packages

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-02-27 |
| **Objective** | Prevent pip dependency reinstall on source-only Docker builds |
| **Outcome** | ✅ Success — source-only builds skip the expensive pip install layer |
| **Context** | ProjectScylla Docker builder stage for Python/hatchling package |

## When to Use This Skill

Apply this pattern when ALL of the following are true:

1. **Python package with `pyproject.toml`** — project uses a PEP 517 build backend (hatchling, flit, setuptools, etc.)
2. **Source changes more often than dependencies** — typical active development cadence
3. **Slow `pip install` in Docker builds** — dependencies take >30 seconds to install
4. **Multi-stage or builder-pattern Dockerfile** — you have a dedicated build stage

**Trigger condition**: "Any source change causes pip to reinstall all dependencies from scratch."

## Problem

The naive pattern copies everything before running `pip install`:

```dockerfile
# BAD: single COPY invalidates the install layer on every source change
COPY pyproject.toml README.md scylla/ /opt/scylla/
RUN pip install /opt/scylla/
```

Docker layer cache is content-addressed: changing a single `.py` file invalidates all layers
that follow the `COPY`, including the expensive dependency install.

## Verified Workflow

### Step 1 — Install the build backend

```dockerfile
# Cached until hatchling version in the RUN command changes
RUN pip install --no-cache-dir hatchling
```

### Step 2 — Dependency layer (the critical caching layer)

```dockerfile
# COPY only pyproject.toml — source changes do NOT invalidate this layer
COPY pyproject.toml /opt/scylla/

# Extract dependencies at build time using tomllib (stdlib in Python 3.11+)
RUN pip install --user --no-cache-dir \
    $(python3 -c "import tomllib; data=tomllib.load(open('/opt/scylla/pyproject.toml','rb')); print(' '.join(data['project']['dependencies']))")
```

**Why this works**: Docker only invalidates the cache when the `pyproject.toml` file changes.
Source files in `scylla/` are not present yet, so they cannot cause cache misses.

### Step 3 — Package install layer (source-only layer)

```dockerfile
# Copy source — this layer IS invalidated by source changes
COPY README.md /opt/scylla/
COPY scylla/ /opt/scylla/scylla/

# --no-deps: dependencies already installed in layer above
RUN pip install --user --no-cache-dir --no-deps /opt/scylla/
```

`--no-deps` prevents pip from re-resolving or re-downloading dependencies, making this
step fast even when it runs (it only installs the package itself, not its transitive deps).

### Full builder stage example

```dockerfile
FROM python:3.14.2-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: Build backend
RUN pip install --no-cache-dir hatchling

# Layer 2: Dependencies (cached until pyproject.toml changes)
COPY pyproject.toml /opt/scylla/
RUN pip install --user --no-cache-dir \
    $(python3 -c "import tomllib; data=tomllib.load(open('/opt/scylla/pyproject.toml','rb')); print(' '.join(data['project']['dependencies']))")

# Layer 3: Package install (only invalidated by source changes)
COPY README.md /opt/scylla/
COPY scylla/ /opt/scylla/scylla/
RUN pip install --user --no-cache-dir --no-deps /opt/scylla/
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Cache behavior matrix

| Change type | Layer 1 (hatchling) | Layer 2 (deps) | Layer 3 (package) |
| ------------- | --------------------- | ---------------- | ------------------- |
| Source file changed | CACHED | CACHED | **RUN** |
| `pyproject.toml` changed | CACHED | **RUN** | **RUN** |
| Dockerfile FROM changed | **RUN** | **RUN** | **RUN** |

### Expected outcome

- Source-only build: only layer 3 executes (`pip install --no-deps` — typically <5 seconds)
- Dependency update: layers 2 + 3 execute (~30–120 seconds depending on deps)
- Cold build: all layers execute

### Verification

After implementing, verify the cache hit with:

```bash
# Build once (cold)
docker build -f docker/Dockerfile .

# Touch a source file
touch scylla/some_module.py

# Rebuild — layer 2 should show "CACHED"
docker build -f docker/Dockerfile . --progress=plain 2>&1 | grep -E "CACHED|RUN pip"
```

Expected output on source-only change:
```
#8 CACHED   # pip install hatchling
#9 CACHED   # COPY pyproject.toml + pip install deps
#10 ...      # COPY scylla/ + pip install --no-deps  (runs)
```

### Python version requirement

- `tomllib` is stdlib since **Python 3.11**
- For Python 3.10, use `tomli` (third-party backport): `pip install tomli` and `import tomli as tomllib`
- The `pyproject.toml` must have dependencies in `[project].dependencies` (PEP 621 format)

## Key Insights

1. **Separate `pyproject.toml` COPY from source COPY** — this is the single most important step
2. **`--no-deps` on the final install** — prevents pip from re-downloading what is already cached in layer 2
3. **Use `tomllib` (stdlib) for extraction** — no extra dependency, always available in Python 3.11+
4. **Layer ordering matters** — stable things (build backend) first, volatile things (source) last
5. **`PIP_NO_CACHE_DIR=1` env var does not affect Docker layer caching** — they are independent mechanisms

## Related Files

- `docker/Dockerfile` — primary implementation location
- `pyproject.toml` — source of truth for `[project].dependencies`

## References

- Issue: HomericIntelligence/ProjectScylla#998
- PR: HomericIntelligence/ProjectScylla#1132
- Branch: `998-auto-impl`
- Commit: `d4deb89` — feat(docker): optimize Dockerfile layer caching for source-only changes
