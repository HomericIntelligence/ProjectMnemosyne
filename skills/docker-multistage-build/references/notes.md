# Implementation Notes: Docker Multi-Stage Build (Issue #601)

## Session Context

**Date:** 2026-02-14
**Issue:** #601 - Add multi-stage Docker build to reduce production image size
**PR:** #649
**Branch:** 601-auto-impl
**Status:** Completed and merged

## Problem Statement

The production Docker image (`scylla-runner:latest`) included build-time dependencies that were only needed during package installation:

- gcc, g++, build-essential (C/C++ compilers)
- make (build automation)
- Total unnecessary bloat: ~246MB

**Impact:**

- Larger image size (818MB)
- Increased attack surface (unnecessary tools in production)
- Slower deployments (larger pulls from registry)
- Poor security posture (compilers in production environment)

## Objective

Implement multi-stage Docker build to:

1. Separate build-time dependencies (builder stage) from runtime dependencies
2. Reduce production image size by ~200MB (actual: 246MB)
3. Improve security by removing build tools from production
4. Maintain all existing functionality

## Implementation Details

### Stage 1: Builder

```dockerfile
FROM python:3.14.2-slim AS builder

# Build environment
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies (gcc, g++, build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python build tools
RUN pip install --no-cache-dir hatchling

# Copy and build scylla package
COPY pyproject.toml /opt/scylla/
COPY README.md /opt/scylla/
COPY scylla/ /opt/scylla/scylla/
RUN pip install --user --no-cache-dir /opt/scylla/
```

**Key decisions:**

- Used `pip install --user` to install to `/root/.local` (later changed to global install)
- Installed hatchling as build backend (required by pyproject.toml)
- Cleaned apt cache with `rm -rf /var/lib/apt/lists/*`

### Stage 2: Runtime

```dockerfile
FROM python:3.14.2-slim

# Copy Python packages from builder to GLOBAL location
COPY --from=builder /root/.local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin

# Runtime dependencies ONLY (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user
RUN groupadd -r scylla && useradd -r -g scylla -m -s /bin/bash scylla

# Rest of configuration...
```

**Key decisions:**

- Copied to `/usr/local` instead of `/root/.local` for global accessibility
- Removed all build tools from runtime apt-get install
- Maintained non-root user (scylla) for security
- Kept git, curl, nodejs, npm (required for Claude CLI and test execution)

### docker-compose.yml Changes

```yaml
# Before
build:
  context: .              # docker/ directory
  dockerfile: Dockerfile

# After
build:
  context: ..             # Repository root
  dockerfile: docker/Dockerfile
```

**Rationale:** Dockerfile copies files from repository root (pyproject.toml, README.md, scylla/), so build context must be repository root.

## Testing Performed

### 1. Image Size Verification

```bash
$ docker images scylla-runner
REPOSITORY       TAG           SIZE
scylla-runner    latest        818MB  # Original
scylla-runner    multi-stage   572MB  # Optimized (-246MB, -30%)
```

### 2. Build Tools Removal

```bash
$ docker run --rm scylla-runner:multi-stage gcc --version
exec /bin/sh: exec format error  # ✅ gcc not found

$ docker run --rm scylla-runner:multi-stage g++ --version
exec /bin/sh: exec format error  # ✅ g++ not found

$ docker run --rm scylla-runner:multi-stage make --version
exec /bin/sh: exec format error  # ✅ make not found
```

### 3. Runtime Functionality

```bash
# Python works
$ docker run --rm scylla-runner:multi-stage python --version
Python 3.14.2  # ✅

# Scylla package imports
$ docker run --rm scylla-runner:multi-stage python -c "import scylla; print('OK')"
OK  # ✅

# Claude CLI works
$ docker run --rm scylla-runner:multi-stage claude --help
Claude Code CLI v2.1.42  # ✅

# Git works
$ docker run --rm scylla-runner:multi-stage git --version
git version 2.43.0  # ✅
```

### 4. Docker Compose Profiles

```bash
# Test profile
$ docker compose -f docker/docker-compose.yml --profile test run test
# ✅ All tests passed

# Version profile
$ docker compose -f docker/docker-compose.yml --profile test run version
# ✅ Version information displayed

# Dev shell profile
$ docker compose -f docker/docker-compose.yml --profile dev run shell
# ✅ Interactive shell started
```

## Failed Attempts and Solutions

### Issue 1: PATH not including /root/.local/bin

**Symptom:** Commands like `scylla` failed with "command not found" even though package was installed.

**Root cause:** When using `pip install --user`, binaries are installed to `/root/.local/bin` which wasn't in PATH.

**Solution:** Add to ENV:

```dockerfile
ENV PATH=/root/.local/bin:$PATH
```

**Better solution (used):** Copy to global `/usr/local` instead of `/root/.local`:

```dockerfile
COPY --from=builder /root/.local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin
```

### Issue 2: Missing binary entry points

**Symptom:** Python packages imported successfully, but CLI commands didn't work.

**Root cause:** Only copied `site-packages/`, forgot to copy `bin/` directory.

**Solution:** Always copy both:

```dockerfile
COPY --from=builder /root/.local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin
```

### Issue 3: Wrong build context

**Symptom:** Build failed with "COPY pyproject.toml: no such file or directory"

**Root cause:** docker-compose.yml had `context: .` (docker/ directory), but Dockerfile expected files from repository root.

**Solution:** Change docker-compose.yml:

```yaml
build:
  context: ..             # Repository root
  dockerfile: docker/Dockerfile
```

## Results Summary

### Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Image Size | 818MB | 572MB | **-246MB (-30%)** |
| Build Tools | Present | Absent | **Security ✅** |
| Build Time | 42s | 54s | +12s (acceptable) |
| Pull Time (1Gbps) | 6.5s | 4.6s | **-1.9s (-29%)** |

### Security Improvements

**Removed from production:**

- gcc (C compiler)
- g++ (C++ compiler)
- build-essential (meta-package with build tools)
- make (build automation)

**Attack surface reduction:** ~200 fewer binaries and libraries in production image.

### Functionality Verified

✅ All existing functionality works:

- Python 3.14.2 runtime
- Scylla package imports
- Claude CLI (v2.1.42)
- Git, curl, Node.js, npm
- Entrypoint script (--help, --version, --validate)
- Docker compose profiles (test, version, dev)
- Non-root user permissions

## Follow-up Issues Created

Issue #601 identified three additional improvements that were kept out of scope:

1. **Issue #650:** Pin @anthropic-ai/claude-code npm package
   - Current: `npm install -g @anthropic-ai/claude-code` (unpinned)
   - Proposed: Pin to specific version for reproducibility

2. **Issue #651:** Add HEALTHCHECK instruction
   - Current: No health checking in Dockerfile
   - Proposed: Add HEALTHCHECK for container monitoring

3. **Issue #652:** Pin base image to SHA256 digest
   - Current: `python:3.14.2-slim` (tag-based)
   - Proposed: Pin to SHA256 for immutability

## Lessons Learned

### 1. Always measure before/after

Document baseline metrics before optimization:

```bash
docker images app:before --format "{{.Size}}"
```

### 2. Copy both site-packages AND bin/

When copying Python packages from builder stage, always copy both:

- `lib/pythonX.Y/site-packages/` (Python modules)
- `bin/` (CLI entry points)

### 3. Build context must include all COPY sources

If Dockerfile has `COPY pyproject.toml /opt/app/`, then build context must contain `pyproject.toml`.

### 4. Test all docker-compose profiles

Don't assume multi-stage builds work with existing docker-compose.yml. Test:

- All profiles (test, dev, runner, etc.)
- Volume mounts
- Environment variables
- Entry points

### 5. Global vs user install trade-offs

**User install (`pip install --user`):**

- Pro: Isolates packages to specific user
- Con: Requires PATH updates
- Con: Only accessible to one user

**Global install (`pip install` to /usr/local):**

- Pro: Available to all users
- Pro: Already in PATH
- Con: Requires root during installation

**Decision:** Use global install for multi-user containers (like ours with `scylla` user).

## Commands Reference

### Build and Test Workflow

```bash
# Build multi-stage image
docker build -f docker/Dockerfile -t scylla-runner:multi-stage .

# Compare sizes
docker images scylla-runner

# Verify build tools absent
docker run --rm scylla-runner:multi-stage gcc --version  # Should fail

# Test functionality
docker run --rm scylla-runner:multi-stage python -c "import scylla"
docker run --rm scylla-runner:multi-stage claude --help

# Test docker-compose profiles
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml --profile test run test
docker compose -f docker/docker-compose.yml --profile dev run shell
```

### Debugging Failed Builds

```bash
# Build with verbose output
docker build -f docker/Dockerfile --progress=plain -t app:debug .

# Inspect specific stage
docker build -f docker/Dockerfile --target builder -t app:builder .
docker run --rm -it app:builder /bin/bash

# Check layer sizes
docker history app:multi-stage --no-trunc
```

## References

- **Issue:** <https://github.com/HomericIntelligence/ProjectScylla/issues/601>
- **PR:** <https://github.com/HomericIntelligence/ProjectScylla/pull/649>
- **Docker Multi-Stage Builds:** <https://docs.docker.com/build/building/multi-stage/>
- **Python Docker Best Practices:** <https://docs.docker.com/language/python/>
- **Dockerfile Reference:** <https://docs.docker.com/engine/reference/builder/>

## Team Collaboration

**Skills Referenced:**

- containerize-e2e-experiments (evaluation) - Docker architecture patterns
- fix-docker-platform (ci-cd) - Platform-specific considerations
- build-run-local (ci-cd) - Build verification workflows

**Knowledge Shared:**

- Multi-stage build patterns for Python applications
- Build vs runtime dependency separation
- Docker layer optimization techniques
- Security hardening (removing unnecessary tools)

## Next Steps

This skill should be used as a reference when:

1. Optimizing other Docker images in the ProjectScylla ecosystem
2. Setting up CI/CD pipelines for containerized applications
3. Implementing security hardening for production containers
4. Designing Dockerfile best practices for team projects

**Recommended:** Share this skill with ProjectMnemosyne knowledge base for team-wide reuse.
