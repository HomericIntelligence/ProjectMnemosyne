# Docker Multi-Stage Build Implementation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Issue** | #601 |
| **PR** | #649 |
| **Objective** | Reduce Docker production image size by separating build-time and runtime dependencies |
| **Outcome** | ✅ **246MB reduction (30%)**: 818MB → 572MB |
| **Status** | Completed and merged |

## When to Use This Skill

Apply this pattern when:

1. **Large Docker images** with build tools in production (gcc, g++, build-essential, make)
2. **Python projects** requiring compiled C extensions (cryptography, pillow, numpy, pandas)
3. **Security concerns** about unnecessary tooling in production images
4. **Deployment optimization** needed for faster pulls and container startup
5. **Clear separation** between build-time and runtime dependencies exists

**Do NOT use** when:

- Image is already minimal (<100MB)
- No compiled dependencies exist (pure Python)
- Build tools are required at runtime (dynamic compilation use cases)

## Verified Workflow

### 1. Analyze Current Image

```bash
# Build current single-stage image
docker build -f docker/Dockerfile -t app:current .

# Check image size
docker images app:current

# Verify which packages are installed
docker run --rm app:current dpkg -l | grep -E "gcc|g\+\+|build-essential|make"
```

**Expected findings:**

- Build tools present in production image
- Larger image size (>500MB for Python apps with dependencies)
- Attack surface includes unnecessary packages

### 2. Design Multi-Stage Dockerfile

**Pattern:**

```dockerfile
# ============================================================================
# Stage 1: Builder - Install Python packages with build dependencies
# ============================================================================
FROM python:3.10-slim AS builder

# Set build environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies (will NOT be in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python build tools
RUN pip install --no-cache-dir hatchling

# Copy project files
COPY pyproject.toml /opt/app/
COPY README.md /opt/app/
COPY src/ /opt/app/src/

# Install to /usr/local for global access (alternative: --user flag with /root/.local)
RUN pip install --no-cache-dir /opt/app/

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.10-slim

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set runtime environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install ONLY runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Rest of runtime configuration...
WORKDIR /workspace
CMD ["python", "-m", "app"]
```

**Key decisions:**

- **Global install vs user install:** Use global (`/usr/local`) for multi-user containers, user (`/root/.local`) for single-user
- **Base image version:** Pin to specific minor version (e.g., `python:3.10.12-slim`) for reproducibility
- **Layer order:** Put least-changing layers first for better Docker cache utilization

### 3. Update Build Context (if needed)

If Dockerfile copies files from repository root:

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: ..           # Changed from '.' to parent directory
      dockerfile: docker/Dockerfile
```

### 4. Build and Verify

```bash
# Build multi-stage image
docker build -f docker/Dockerfile -t app:multi-stage .

# Compare sizes
docker images app

# Verify build tools NOT present (should fail)
docker run --rm app:multi-stage gcc --version
# Expected: "gcc: not found"

# Verify runtime functionality works
docker run --rm app:multi-stage python --version
docker run --rm app:multi-stage python -c "import myapp; print('OK')"
```

### 5. Test All Functionality

```bash
# Test docker-compose profiles
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml --profile test run test
docker compose -f docker/docker-compose.yml --profile dev run shell

# Test entrypoint
docker run --rm app:multi-stage --help
docker run --rm app:multi-stage --version

# Test with mounted volumes
docker run --rm -v $(pwd):/workspace app:multi-stage pytest
```

## Failed Attempts

### ❌ Attempt 1: Using `pip install --user` with wrong PATH

**What we tried:**

```dockerfile
# Builder stage
RUN pip install --user --no-cache-dir /opt/app/

# Runtime stage
COPY --from=builder /root/.local /root/.local
# Missing: PATH update
```

**Why it failed:**

- Binaries installed to `/root/.local/bin` were not in PATH
- Commands like `scylla` or `pytest` failed with "command not found"

**Solution:**

```dockerfile
# Runtime stage
ENV PATH=/root/.local/bin:$PATH
```

### ❌ Attempt 2: Copying only site-packages without bin/

**What we tried:**

```dockerfile
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
# Missing: /root/.local/bin
```

**Why it failed:**

- Python packages were importable, but CLI entry points were missing
- Commands registered in setup.py `console_scripts` were unavailable

**Solution:**

```dockerfile
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin
```

### ❌ Attempt 3: Wrong build context in docker-compose.yml

**What we tried:**

```yaml
build:
  context: .              # docker/ directory
  dockerfile: Dockerfile
```

**Why it failed:**

- Dockerfile had `COPY pyproject.toml /opt/app/` which didn't exist in docker/ directory
- Build failed with "no such file or directory"

**Solution:**

```yaml
build:
  context: ..             # Repository root
  dockerfile: docker/Dockerfile
```

## Results & Parameters

### Image Size Comparison

| Version | Size | Reduction |
|---------|------|-----------|
| Original (single-stage) | 818MB | - |
| Multi-stage | 572MB | **-246MB (-30%)** |

### Build Time Impact

- **Initial build:** +12 seconds (due to two stages)
- **Cached build:** No difference (Docker layer caching works for both stages)
- **CI/CD impact:** Faster pulls outweigh slightly slower builds

### Files Modified

1. **docker/Dockerfile** - Split into builder and runtime stages
2. **docker/docker-compose.yml** - Updated build context from `docker/` to repository root

### Verification Commands

```bash
# Size reduction
docker images scylla-runner --format "{{.Repository}}:{{.Tag}} - {{.Size}}"

# Build tools absent
docker run --rm scylla-runner:multi-stage gcc --version      # ❌ not found
docker run --rm scylla-runner:multi-stage g++ --version      # ❌ not found
docker run --rm scylla-runner:multi-stage make --version     # ❌ not found

# Runtime functionality present
docker run --rm scylla-runner:multi-stage python --version   # ✅ Python 3.14.2
docker run --rm scylla-runner:multi-stage git --version      # ✅ git 2.43.0
docker run --rm scylla-runner:multi-stage claude --help      # ✅ Claude CLI v2.1.42
docker run --rm scylla-runner:multi-stage python -c "import scylla; print('OK')"  # ✅ OK
```

## Implementation Checklist

When implementing multi-stage builds, verify:

- [ ] Builder stage installs all build dependencies (gcc, g++, build-essential)
- [ ] Builder stage compiles Python packages with C extensions
- [ ] Runtime stage copies compiled packages from builder
- [ ] Runtime stage does NOT install build tools
- [ ] PATH includes binary directories if using --user install
- [ ] Build context in docker-compose.yml points to correct directory
- [ ] Image size is measured before and after (document reduction)
- [ ] All functionality tests pass in new image
- [ ] docker-compose profiles still work
- [ ] CI/CD pipelines updated if needed

## Related Skills

- **containerize-e2e-experiments** - Docker architecture patterns and layer optimization
- **fix-docker-platform** - Platform-specific build considerations
- **build-run-local** - Build verification and testing workflows

## References

- Issue #601: <https://github.com/HomericIntelligence/ProjectScylla/issues/601>
- PR #649: <https://github.com/HomericIntelligence/ProjectScylla/pull/649>
- Docker Multi-Stage Builds: <https://docs.docker.com/build/building/multi-stage/>
- Python Docker Best Practices: <https://docs.docker.com/language/python/>

## Team Knowledge

**Key Learning:** When separating build and runtime stages, always verify that:

1. Python packages are in the correct site-packages directory
2. Binary entry points are in PATH
3. Build context includes all files referenced in COPY statements

**Common Pitfall:** Forgetting to copy `/root/.local/bin` or update PATH when using `pip install --user`.

**Best Practice:** Pin base image to specific minor version (e.g., `python:3.10.12-slim`) for reproducibility, but avoid SHA256 digests unless regulatory compliance requires it.
