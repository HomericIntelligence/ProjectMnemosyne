---
name: ci-mojo-podman-root-cause-fixes
description: "Fix four distinct CI root-cause classes that co-occur in Mojo/Podman-based projects: (1) mkdocs --strict broken relative links, (2) Podman container PermissionError writing to host-side paths (fix: write to /tmp inside container, then podman cp), (3) wiring up Mojo ASAN builds via justfile + libasan8 in Dockerfile, (4) breaking Mojo circular imports by extracting shared constants to a zero-dependency leaf module. Use when: docs deploy fails with broken link, benchmark workflow gets PermissionError, ASAN variable is unused in justfile, or mojo build fails with 'cannot implicitly convert X to X' due to circular import through a constants file."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
tags:
  - ci-cd
  - podman
  - mojo
  - mkdocs
  - asan
  - circular-imports
  - dockerfile
  - justfile
---

# CI/CD Root Cause Fixes: mkdocs Links, Podman Paths, Mojo ASAN, Circular Imports

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Fix four distinct CI failure root causes in ProjectOdyssey |
| **Outcome** | All four fixed in PR #5178 (verified pre-commit; CI pending) |
| **Repository** | ProjectOdyssey (Mojo ML research platform) |
| **PR** | #5178 |

## When to Use

- `mkdocs build --strict` fails with broken relative link in an ADR or doc file
- Benchmark or output workflow gets `PermissionError` when Python inside a Podman container
  tries to write to a directory that was created on the host runner
- `justfile` defines `MOJO_ASAN := "--sanitize address"` but the variable is never used in any recipe
- `mojo build` fails with `cannot implicitly convert 'X' to 'X'` (same type name, both sides)
  and the cycle goes through a constants-only import

## Verified Workflow

> **Note**: PR #5178 was created at end of session; CI validation is pending.
> Workflow steps are based on pre-commit verification only.

### Quick Reference

```bash
# Fix 1: mkdocs strict broken link
# File at docs/adr/ADR-014.md with link: ../../docs/dev/mojo-jit-crash-workaround.md
# docs/adr/ is already inside docs/, so ../../docs/ exits the docs tree
# Correct relative path from docs/adr/ to docs/dev/:
sed -i 's|../../docs/dev/|../dev/|g' docs/adr/ADR-014-jit-crash-retry-mitigation.md

# Fix 2: podman cp pattern (write inside container, copy out)
# In your workflow, replace:
#   python3 scripts/benchmark.py --output benchmark-results/$SUITE.json
# With:
#   CONTAINER_ID=$(podman compose ps -q projectodyssey-dev)
#   podman exec $CONTAINER_ID python3 /repo/scripts/benchmark.py --output /tmp/benchmark-results/$SUITE.json
#   mkdir -p benchmark-results
#   podman cp $CONTAINER_ID:/tmp/benchmark-results/$SUITE.json benchmark-results/$SUITE.json

# Fix 3: wire ASAN in justfile
# Find the unused variable and add a recipe that uses it:
grep -n "MOJO_ASAN\|sanitize" justfile

# Fix 4: break circular import via constants extraction
# Create shared/tensor/tensor_constants.mojo (zero imports)
# Move MAX_TENSOR_BYTES, WARN_TENSOR_BYTES there
# Update any_tensor.mojo and tensor_creation.mojo to import from tensor_constants
```

### Detailed Steps

#### Fix 1: mkdocs `--strict` Broken Relative Link

**Root cause**: mkdocs resolves relative links relative to the _file's location_, not the
project root. An ADR at `docs/adr/ADR-014.md` that links
`../../docs/dev/mojo-jit-crash-workaround.md` resolves as:

```text
docs/adr/ → (up one) docs/ → (up two) . → (down) docs/dev/
= ./docs/dev/mojo-jit-crash-workaround.md  ✓ path exists
```

This looks correct but mkdocs `--strict` catches that going up two levels from `docs/adr/`
exits the documentation tree and then re-enters it, making the link non-relative in the
rendered site. The fix is simply one level fewer:

```bash
# From docs/adr/ → docs/dev/ is exactly one "../"
# WRONG:
[workaround](../../docs/dev/mojo-jit-crash-workaround.md)
# CORRECT:
[workaround](../dev/mojo-jit-crash-workaround.md)
```

**Diagnosis command**:

```bash
# Reproduce locally (same failure mode as CI)
pixi run mkdocs build --strict 2>&1 | grep "WARNING\|ERROR" | head -20
```

#### Fix 2: Podman Container PermissionError on Host Paths

**Root cause**: The GitHub Actions workflow creates `benchmark-results/` on the host runner
filesystem, then passes that path as `--output benchmark-results/$SUITE.json` to a Python
script that runs _inside_ a Podman container. The container has no access to host paths.

**Fix pattern**:

```yaml
# BEFORE (broken):
- name: Run benchmark
  run: |
    mkdir -p benchmark-results
    just run-benchmark $SUITE --output benchmark-results/$SUITE.json

# AFTER (correct):
- name: Run benchmark
  run: |
    CONTAINER_ID=$(podman compose ps -q projectodyssey-dev)
    podman exec "$CONTAINER_ID" mkdir -p /tmp/benchmark-results
    podman exec "$CONTAINER_ID" \
      python3 /repo/scripts/benchmark.py \
      --output /tmp/benchmark-results/${SUITE}.json
    mkdir -p benchmark-results
    podman cp "$CONTAINER_ID:/tmp/benchmark-results/${SUITE}.json" \
      "benchmark-results/${SUITE}.json"
```

**Key commands**:

```bash
# Get container ID for a compose service
CONTAINER_ID=$(podman compose ps -q <service-name>)

# Run command inside container
podman exec "$CONTAINER_ID" <command>

# Copy file from container to host
podman cp "$CONTAINER_ID:/container/path" "host/path"
```

**Rule**: Any output file that a CI step needs to persist (for artifact upload, summary
generation, etc.) must be written to a host path. If the tool that generates it runs inside
a container, use `podman cp` to extract it after the container step completes.

#### Fix 3: Wiring Mojo ASAN Builds

Mojo 0.26.1 supports `--sanitize address`. Ubuntu 24.04 (used in CI) requires `libasan8`
(gcc-13 ASAN runtime).

**Step 3a — Add `libasan8` to Dockerfile base stage**:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasan8 \       # <-- add this
    && rm -rf /var/lib/apt/lists/*
```

**Step 3b — Add `test-group-asan` recipe to justfile**:

The justfile likely already has `MOJO_ASAN := "--sanitize address"` defined but unused.
Wire it up:

```makefile
# Existing (unused):
MOJO_ASAN := "--sanitize address"

# Add recipe:
test-group-asan path pattern:
    #!/usr/bin/env bash
    set -euo pipefail
    just run-test-group "{{path}}" "{{pattern}}" "{{MOJO_ASAN}}"
```

**Step 3c — Create ASAN workflow** (`.github/workflows/asan-tests.yml`):

```yaml
name: ASAN Tests
on:
  push:
    branches: [main]
    paths:
      - 'shared/**/*.mojo'
      - 'tests/**/*.mojo'
      - '.github/workflows/asan-tests.yml'
  pull_request:
    paths:
      - 'shared/**/*.mojo'
      - 'tests/**/*.mojo'
  schedule:
    - cron: '0 4 * * 1'  # Weekly Monday 04:00 UTC
  workflow_dispatch:

jobs:
  asan-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Pixi
        uses: prefix-dev/setup-pixi@v0.8.1
      - name: Load container image
        run: |
          # ... standard image load pattern
      - name: Run ASAN tests
        run: |
          just test-group-asan tests/shared/core "test_*.mojo"
```

**Note on `--shared-libasan`**: Mojo also supports `--shared-libasan` for builds that
produce shared libraries. The standard `--sanitize address` is sufficient for test binaries.

#### Fix 4: Break Circular Import via Constants Extraction

**Root cause**: `any_tensor.mojo` re-exports constants used by `tensor_creation.mojo`, and
`tensor_creation.mojo` imports from `any_tensor.mojo`, while `any_tensor.mojo` imports from
`tensor_creation.mojo`. This creates a compile cycle.

The fix is to extract the shared constants to a zero-dependency leaf module:

**Step 4a — Create `shared/tensor/tensor_constants.mojo`**:

```mojo
"""Shared numeric constants for tensor size limits.

This module has no imports from other shared.tensor or shared.core modules
so it can be safely imported by any module in the package without
creating circular dependencies.
"""

# Maximum allowed tensor size in bytes (prevents accidental allocation of huge tensors)
alias MAX_TENSOR_BYTES: Int = 8 * 1024 * 1024 * 1024  # 8 GB

# Threshold above which a warning is emitted during allocation
alias WARN_TENSOR_BYTES: Int = 1024 * 1024 * 1024  # 1 GB
```

**Step 4b — Update importers**:

```mojo
# In any_tensor.mojo — replace local alias definitions with:
from shared.tensor.tensor_constants import MAX_TENSOR_BYTES, WARN_TENSOR_BYTES

# In tensor_creation.mojo — replace import from any_tensor:
# BEFORE:
from shared.tensor.any_tensor import MAX_TENSOR_BYTES
# AFTER:
from shared.tensor.tensor_constants import MAX_TENSOR_BYTES
```

**Step 4c — Update `__init__.mojo` if constants were re-exported there**:

```mojo
# In shared/tensor/__init__.mojo, add:
from shared.tensor.tensor_constants import MAX_TENSOR_BYTES, WARN_TENSOR_BYTES
```

**Decision tree for breaking a Mojo circular import involving constants**:

```text
Does the cycle go through a constants-only import?
  YES → Extract constants to a new zero-dependency leaf module
        Rule: The leaf module must have ZERO imports from the same package

Does the cycle go through a utility function?
  YES → See mojo-circular-import-type-identity-fix skill

Does the cycle go through a type definition?
  YES → See mojo-circular-import-type-identity-fix skill
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Heap corruption hypothesis | Assumed CI failures were a recurrence of the Mojo heap corruption bug (now fixed at compiler level) | That bug is fixed; user explicitly corrected this assumption | Don't attribute new CI failures to previously-fixed bugs |
| Sub-agents for implementation | Delegated to sub-agents via worktrees | Agents produced correct analysis and plans but left changes unstaged — no commits | Verify sub-agent outputs include committed changes, not just summaries |
| Checkout main with unstaged changes | Tried `git checkout main` directly | Failed due to unstaged changes from sub-agent work | Run `git stash` first, or switch via worktrees |
| `../../docs/dev/` link assumed correct | The path resolves to the right file on disk | mkdocs `--strict` detects the link exits the docs tree even if the file exists | mkdocs strict validates the _path logic_, not just file existence |

## Results & Parameters

### Files Changed

| File | Change Type | Purpose |
| ------ | ------------- | --------- |
| `docs/adr/ADR-014-jit-crash-retry-mitigation.md` | Edit | Fix broken relative link (`../../docs/dev/` → `../dev/`) |
| `.github/workflows/benchmark.yml` | Edit | Write to `/tmp/` inside container, `podman cp` out |
| `.github/workflows/asan-tests.yml` | New | ASAN test workflow |
| `Dockerfile` | Edit | Add `libasan8` to base stage |
| `justfile` | Edit | Add `test-group-asan` recipe wiring `MOJO_ASAN` |
| `shared/tensor/tensor_constants.mojo` | New | Zero-dependency constants leaf module |
| `shared/tensor/any_tensor.mojo` | Edit | Import constants from `tensor_constants` |
| `shared/tensor/tensor_creation.mojo` | Edit | Import constants from `tensor_constants` (not `any_tensor`) |

### Diagnosis Commands

```bash
# mkdocs link check
pixi run mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR"

# Benchmark PermissionError — check which path is being written
grep -n "output\|benchmark-results" .github/workflows/benchmark.yml

# ASAN justfile variable — find unused MOJO_ASAN
grep -n "MOJO_ASAN" justfile

# Circular import — find the cycle
grep -rn "^from shared.tensor.any_tensor import" shared/tensor/ --include="*.mojo"
grep -rn "^from shared.tensor.tensor_creation import" shared/tensor/ --include="*.mojo"
```

### Dependency Invariant After Fix

```text
tensor_constants.mojo   (no imports from shared.tensor.* or shared.core.*)
        ↑
any_tensor.mojo         (imports from tensor_constants)
tensor_creation.mojo    (imports from tensor_constants, not from any_tensor)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5178 | All four fixes committed and pushed; CI pending |

## References

- [mojo-circular-import-type-identity-fix](mojo-circular-import-type-identity-fix.md) - Deeper circular import fix for type identity errors
- [mojo-method-wrapper-circular-import](mojo-method-wrapper-circular-import.md) - Circular import fix via function-scoped imports
- [ci-cd-flaky-ci-root-cause-triage](ci-cd-flaky-ci-root-cause-triage.md) - Broader CI triage methodology
- [podman-ci-containerization](podman-ci-containerization.md) - Full Podman CI setup pattern
