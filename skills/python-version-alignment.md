---
name: python-version-alignment
description: Align Python version across pyproject.toml classifiers, pixi.toml, and
  Dockerfile when drift is detected
category: tooling
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Python Version Alignment

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Issue** | #1118 - [Docs] Standardize Python version specification across configs |
| **Objective** | Align Python version in `docker/Dockerfile`, `pyproject.toml`, and `pixi.toml` |
| **Outcome** | ✅ Dockerfile updated from `python:3.14.2-slim` to `python:3.12-slim` (pinned SHA256) |
| **Root Cause** | Accidental drift — Dockerfile was manually updated to 3.14 without updating classifiers |
| **Key Learning** | Use `docker pull` to get a fresh pinned SHA256 digest before updating `FROM` lines |

## When to Use

Use this workflow when:

- A quality audit flags version mismatch across config files
- `pyproject.toml` classifiers don't match the Dockerfile base image Python version
- `pixi.toml` resolves a different Python than the Dockerfile uses
- PR review mentions "Python version drift" or "config inconsistency"

Trigger symptoms:
- Dockerfile `FROM python:X.Y.Z-slim` doesn't match `pyproject.toml` classifier max version
- CI/CD runs on a different Python than local `pixi` environment
- `requires-python = ">=3.10"` but Dockerfile uses `3.14.x` (bleeding edge)

## Verified Workflow

### Step 1: Audit all three files

```bash
# Check pyproject.toml classifiers and requires-python
grep -n "python\|Python\|3\.[0-9]" pyproject.toml

# Check pixi.toml constraint
grep -n "python" pixi.toml

# Check Dockerfile FROM lines
grep -n "FROM python\|python3\." docker/Dockerfile
```

### Step 2: Determine the canonical version

The canonical version is the **highest version listed in `pyproject.toml` classifiers**.
`requires-python = ">=3.10"` sets the minimum; the Dockerfile should use the *tested* maximum.

Example:
```toml
# pyproject.toml classifiers → canonical max = 3.12
"Programming Language :: Python :: 3.10",
"Programming Language :: Python :: 3.11",
"Programming Language :: Python :: 3.12",
```

### Step 3: Pull the target image and get its SHA256 digest

```bash
# Pull the target image (use -slim variant for smaller size)
docker pull python:3.12-slim

# Get the pinned digest
docker inspect python:3.12-slim --format='{{index .RepoDigests 0}}'
# Output: python@sha256:<digest>
```

### Step 4: Update the Dockerfile

Replace all `FROM` lines and any `python3.X` path references:

```dockerfile
# Before (drifted):
FROM python:3.14.2-slim@sha256:<old-digest> AS builder
...
COPY --from=builder /root/.local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# After (aligned):
# Python 3.12 aligns with pyproject.toml classifiers (3.10-3.12); requires-python = ">=3.10"
FROM python:3.12-slim@sha256:<new-digest> AS builder
...
COPY --from=builder /root/.local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
```

**Important**: In multi-stage Dockerfiles, update **both** stages (builder + runtime) and the `COPY` path.

### Step 5: Verify no remaining old-version references

```bash
grep -rn "3\.14\|python3\.14" docker/ pyproject.toml pixi.toml
# Should produce no output
```

### Step 6: Run tests and commit

```bash
pixi run python -m pytest tests/unit/ -v --tb=short -q

git add docker/Dockerfile
git commit -m "docs(docker): align Dockerfile Python version with pyproject.toml classifiers"
```

## Failed Attempts

### ❌ Attempt: Updating only the first `FROM` line in a multi-stage build

**What Went Wrong**:

In a multi-stage Dockerfile, there are two `FROM` lines (builder + runtime). Updating only the
first one leaves the runtime stage on the old version. Additionally, the `COPY --from=builder`
path contains the Python version (e.g., `python3.14`) and must also be updated.

**Prevention**: Always grep for ALL version references in the Dockerfile before committing:

```bash
grep -n "3\.[0-9][0-9]\|python3\.[0-9]" docker/Dockerfile
```

## Results & Parameters

### Files Changed (Issue #1118)

| File | Change |
|------|--------|
| `docker/Dockerfile` line 15 | `python:3.14.2-slim@sha256:1a3c6...` → `python:3.12-slim@sha256:f3fa41d7...` |
| `docker/Dockerfile` line 44 | Same update for runtime stage |
| `docker/Dockerfile` line 53 | `python3.14/site-packages` → `python3.12/site-packages` |

### Final State After Fix

```
pyproject.toml:  requires-python = ">=3.10", classifiers 3.10-3.12  (unchanged)
pixi.toml:       python = ">=3.10"                                   (unchanged)
docker/Dockerfile: FROM python:3.12-slim@sha256:f3fa41d7...          (updated)
```

### Docker SHA256 Digest (as of 2026-02-27)

```
python:3.12-slim → sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
```

Note: SHA256 digests change when Docker Hub publishes security patches. Re-pull before updating.

### Test Results

- 3185 tests passed, 78.36% coverage (above 75% threshold)
- Pre-push coverage hook validated and passed

## References

- PR #1166: https://github.com/HomericIntelligence/ProjectScylla/pull/1166
- Issue #1118: Discovered during February 2026 quality audit (P2)
- See `references/notes.md` for raw session details

## Tags

`python`, `dockerfile`, `version-drift`, `pyproject`, `pixi`, `configuration`, `quality-audit`
