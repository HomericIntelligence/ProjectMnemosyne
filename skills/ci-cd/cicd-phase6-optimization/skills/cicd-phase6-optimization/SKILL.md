---
name: cicd-phase6-optimization
description: "CI/CD optimization: pin runners, changed-files pre-commit, copy .pixi in Dockerfile, measure speedup. Use when: speeding up PR CI by scoping pre-commit to changed files, preventing cache invalidation by pinning ubuntu-latest, fixing redundant pixi install in Dockerfile multi-stage builds, or measuring before/after CI speedup via gh CLI."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Reduce CI/CD wall-clock time across PRs and nightly runs |
| **Techniques** | Runner pinning, changed-files-only pre-commit, Dockerfile .pixi copy, speedup report script |
| **Context** | Mojo/Python monorepo with 500+ test files, 27+ GitHub Actions workflows, pixi environment manager |
| **Outcome** | 0 `ubuntu-latest` references across all workflow files; pre-commit scoped to changed files on PRs; Dockerfile runtime stage avoids redundant install; gh CLI speedup report script for before/after comparison |

## When to Use

Trigger this skill when:

1. **Cache invalidation from ubuntu-latest**: GitHub updates the default runner image, invalidating all caches simultaneously — pin to `ubuntu-24.04` to control upgrade timing.
2. **Pre-commit too slow on PRs**: `--all-files` runs pre-commit on 500+ files every PR — switch to `--from-ref`/`--to-ref` for changed files only.
3. **Dockerfile runtime stage reinstalls dependencies**: Multi-stage build where the runtime stage re-runs `pixi install --frozen` instead of copying the `.pixi` directory from builder.
4. **No CI speedup data**: Need before/after metrics to prove optimizations are working.
5. **Batch-replacing runner versions**: 60+ `ubuntu-latest` references across many workflow files need bulk replacement.

## Verified Workflow

### Quick Reference

```bash
# 1. Pin all runners (bulk sed across all workflow files)
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done

# 2. Verify: should be 0
grep -r "ubuntu-latest" .github/workflows/*.yml | wc -l

# 3. Validate test coverage still passes
python scripts/validate_test_coverage.py

# 4. Generate speedup report
python scripts/ci_speedup_report.py
```

### Step 1: Pin All Runners to ubuntu-24.04

**Problem**: `ubuntu-latest` causes unpredictable cache invalidation when GitHub updates the default.

**Fix**: Use `sed` for bulk replacement across all workflow files:

```bash
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done

# Verify zero remaining
grep -rc "ubuntu-latest" .github/workflows/ | grep -v ":0"
```

**Note**: Entries in `README.md` documentation examples are fine to leave — only
actual `*.yml` workflow files matter.

### Step 2: Pre-commit Changed Files Only for PRs

**Problem**: `pre-commit run --all-files` runs on every file in a 500+ file repo for every PR.

**Fix**: Use `--from-ref`/`--to-ref` on PRs, keep `--all-files` for pushes to main.

```yaml
- name: Run pre-commit hooks (excluding mojo-format)
  env:
    EVENT_NAME: ${{ github.event_name }}
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ "$EVENT_NAME" = "pull_request" ]; then
      git fetch origin "$BASE_REF" --depth=1
      SKIP=mojo-format pixi run pre-commit run --from-ref "origin/$BASE_REF" --to-ref HEAD --show-diff-on-failure
    else
      SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure
    fi
```

**Security note**: Use `env:` variables to capture `github.event_name` and `github.base_ref`
rather than inlining `${{ }}` expressions in shell `run:` commands. This satisfies workflow
injection security checks (pre-commit hooks, security scanners). Even though `base_ref` is
not typically user-controlled, the pattern is correct practice.

**Why `git fetch` is needed**: `actions/checkout` with default `fetch-depth: 1` only
fetches the HEAD commit. The base branch ref is unavailable without an explicit fetch.

### Step 3: Dockerfile Multi-Stage — Copy .pixi Instead of Reinstalling

**Problem**: Runtime stage re-runs `curl | bash` Pixi installer + `pixi install --frozen`,
duplicating the builder stage's work.

**Before** (runtime stage):
```dockerfile
ENV PIXI_VERSION=0.65.0

RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Redundant: installs Pixi again
RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash

COPY pixi.toml pixi.lock ./
# Redundant: reinstalls all dependencies
RUN pixi install --frozen
```

**After** (runtime stage):
```dockerfile
ENV PIXI_VERSION=0.65.0

# curl no longer needed — remove from apt-get list
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Pixi binary and installed environment from builder
COPY --from=builder /root/.pixi /root/.pixi
COPY --from=builder /build/.pixi /app/.pixi

# Dependency files still needed for pixi to resolve env
COPY pixi.toml pixi.lock ./
```

**Result**: `pixi install` count drops from 2 to 1. Eliminates the `curl | bash` download
and full re-installation in every runtime/ci/production stage.

**Important**: Also remove `curl` from the runtime stage's `apt-get install` list — it's
only needed in the builder stage for the Pixi installer download.

### Step 4: Before/After Speedup Report Script

Create `scripts/ci_speedup_report.py` using `gh run list` to fetch workflow durations:

```python
"""Compare CI workflow durations: recent (last 3 days) vs baseline (7-14 days ago)."""
import subprocess, json, sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

WORKFLOWS = [
    "comprehensive-tests.yml",
    "pre-commit.yml",
    "security.yml",
    "nightly-comprehensive.yml",
    "docker.yml",
]

def fetch_runs(workflow: str, limit: int) -> List[Dict[str, Any]]:
    result = subprocess.run(
        ["gh", "run", "list", "--workflow", workflow, "--limit", str(limit),
         "--json", "createdAt,updatedAt,conclusion,name,databaseId"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return []
    return json.loads(result.stdout)

def parse_duration(created_at: str, updated_at: str) -> Optional[float]:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        start = datetime.strptime(created_at, fmt).replace(tzinfo=timezone.utc)
        end = datetime.strptime(updated_at, fmt).replace(tzinfo=timezone.utc)
        return max((end - start).total_seconds(), 0)
    except ValueError:
        return None
```

**Key design**: Duration = `updatedAt - createdAt` (includes queue time, but consistent
across both windows, so comparisons are valid). Only `success`/`failure` conclusions counted
(skip in-progress and cancelled runs).

**Output**: Markdown table:

```markdown
| Workflow | Baseline avg | Recent avg | Change | Runs (baseline/recent) |
|----------|-------------|-----------|--------|------------------------|
| pre-commit.yml | 4m 32s | 1m 15s | -72.4% (faster) | 8/3 |
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Inline `${{ github.event_name }}` in `run:` | Used `if [ "${{ github.event_name }}" = "pull_request" ]` directly in shell | Pre-commit security hook blocked the edit: "GitHub Actions workflow injection risk" | Always use `env:` block to capture `github.event.*` before using in shell — even non-sensitive context values like `event_name` |
| `glob` for .github/workflows files | Used Glob tool with pattern `.github/workflows/*.yml` | Glob returned "No files found" (hidden directory not traversed) | Glob doesn't match hidden directories (`.github/`); use `ls` via Bash or full path reads instead |
| Read Dockerfile.ci without re-reading after sed | Tried to Edit without re-reading | "File has been modified since read" error after `sed -i` replaced content | Always re-read a file after any Bash modification before using Edit tool on it |
| Using `curl` in runtime Dockerfile stage | Left `curl` in `apt-get install` after removing the `pixi install` step | `curl` was only needed for `pixi.sh/install.sh` — removing the install makes `curl` unnecessary | When removing a tool's installation step, also audit and remove its prerequisites from apt-get |

## Results & Parameters

### Runner Pinning

```bash
# Count before
grep -rc "ubuntu-latest" .github/workflows/ | grep -v ":0" | wc -l  # e.g. 63

# Bulk replace
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done

# Count after (should be 0 in *.yml files)
grep -rc "ubuntu-latest" .github/workflows/*.yml | grep -v ":0" | wc -l
```

### Pre-commit Workflow (Complete Step)

```yaml
- name: Run pre-commit hooks (excluding mojo-format)
  env:
    EVENT_NAME: ${{ github.event_name }}
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ "$EVENT_NAME" = "pull_request" ]; then
      git fetch origin "$BASE_REF" --depth=1
      SKIP=mojo-format pixi run pre-commit run \
        --from-ref "origin/$BASE_REF" \
        --to-ref HEAD \
        --show-diff-on-failure
    else
      SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure
    fi

- name: Run mojo format (advisory - non-blocking)
  continue-on-error: true
  env:
    EVENT_NAME: ${{ github.event_name }}
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ "$EVENT_NAME" = "pull_request" ]; then
      pixi run pre-commit run mojo-format \
        --from-ref "origin/$BASE_REF" \
        --to-ref HEAD \
        --show-diff-on-failure || echo "::warning::mojo format check failed (non-blocking)"
    else
      pixi run pre-commit run mojo-format --all-files --show-diff-on-failure \
        || echo "::warning::mojo format check failed (non-blocking)"
    fi
```

### Validation

```bash
# 1. Runner pinning: 0 ubuntu-latest in workflow files
grep -c "ubuntu-latest" .github/workflows/*.yml

# 2. Changed-files-only pre-commit
grep "from-ref" .github/workflows/pre-commit.yml

# 3. Dockerfile: 1 pixi install (builder only)
grep -c "pixi install" Dockerfile.ci

# 4. Test coverage still valid
python scripts/validate_test_coverage.py  # exit 0

# 5. Speedup report
python scripts/ci_speedup_report.py
```
