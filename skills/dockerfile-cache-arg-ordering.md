---
name: dockerfile-cache-arg-ordering
description: Assert Dockerfile ARG declarations appear before RUN commands that consume
  them, ensuring Docker build-cache is correctly invalidated when build-args change.
category: testing
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# Dockerfile Cache ARG Ordering

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-03-02 |
| **Objective** | Add a static test asserting that `ARG EXTRAS` is declared before the Layer 2 dependency-install `RUN` in `docker/Dockerfile`, so Docker cache is correctly invalidated when `--build-arg EXTRAS=...` changes |
| **Outcome** | ✅ 1 new test added to existing `TestBuilderStageOrdering`; 17 tests pass (was 16); PR #1307 merged |
| **Context** | Follow-up to #1139 — existing 7 static-analysis tests verified structure but not build-arg cache semantics |

## When to Use This Skill

Use this pattern when:

1. **A Dockerfile uses `ARG` to control which optional dependencies are installed** (e.g., `ARG EXTRAS=""` consumed in a `pip install` `RUN`)
2. **Static Dockerfile tests exist** but do not yet assert build-arg cache ordering
3. **You need a regression guard** that catches accidental reordering of `ARG` / `RUN` lines
4. **No Docker daemon is available** — static text analysis tests are sufficient

**Trigger phrases**:
- "ARG EXTRAS doesn't bust the cache"
- "changing --build-arg doesn't cause a rebuild"
- "extend static tests to assert ARG invalidates layer cache"
- "Dockerfile cache-key discipline for build args"

## Docker ARG Cache-Key Mechanics

Docker only incorporates an ARG value into the build-cache key for instructions that appear **after** the ARG declaration.

```dockerfile
# WRONG — ARG after RUN: changing EXTRAS does NOT bust the cache
RUN pip install ... $EXTRAS    # cache hit even when EXTRAS changes
ARG EXTRAS=""

# CORRECT — ARG before RUN: changing EXTRAS busts the cache
ARG EXTRAS=""
RUN pip install ... $EXTRAS    # cache miss when EXTRAS changes
```

Reference: [Docker ARG docs](https://docs.docker.com/reference/dockerfile/#arg)

## Verified Workflow

### Step 1: Identify the anchor strings

Find a unique string in the `ARG EXTRAS` line and a unique string in the target `RUN`:

```bash
grep -n "ARG EXTRAS\|os.environ.get" docker/Dockerfile
# 52:ARG EXTRAS=""
# 54:RUN python3 -c "...os.environ.get('EXTRAS', '')..."
```

### Step 2: Add the test to the existing `TestBuilderStageOrdering` class

```python
def test_arg_extras_before_layer2_install(self, lines: list[str]) -> None:
    """ARG EXTRAS must appear before the Layer 2 dependency install RUN.

    Docker's build cache incorporates ARG values in the cache key, but only
    for instructions that appear *after* the ARG declaration.  If ARG EXTRAS
    appeared after the Layer 2 RUN, changing --build-arg EXTRAS=... would NOT
    bust the cache and the wrong dependency set would be used.

    We anchor the Layer 2 RUN on ``os.environ.get`` — this string is unique
    to the dynamic dependency-install RUN command.
    """
    arg_extras_idx = _first_line_containing(lines, "ARG EXTRAS")
    layer2_idx = _first_line_containing(lines, "os.environ.get")
    _assert_before(
        arg_extras_idx,
        layer2_idx,
        "ARG EXTRAS declaration",
        "Layer 2 dependency install RUN (os.environ.get line)",
    )
```

**Location**: `tests/unit/docker/test_dockerfile_layer_ordering.py` — inside `TestBuilderStageOrdering`

### Step 3: Update the module docstring

Add item `3a` to document the new invariant alongside items 3 and 4:

```
  3. pyproject.toml copied before Layer 2 pip install (cache-key discipline)
  3a. ARG EXTRAS declared before Layer 2 pip install (cache-key discipline for build-arg)
  4. Layer 2 pip install before source COPY (Layer 3)
```

### Step 4: Run tests

```bash
pixi run python -m pytest tests/unit/docker/test_dockerfile_layer_ordering.py -v --override-ini="addopts="
# 17 passed in 0.03s
```

## Key Helpers Used

All helpers are already present in `test_dockerfile_layer_ordering.py`:

| Helper | Purpose |
| -------- | --------- |
| `_first_line_containing(lines, *fragments)` | Returns 0-based index of first line matching all fragments |
| `_assert_before(earlier, later, earlier_desc, later_desc)` | Asserts ordering with helpful failure messages |
| `lines` fixture | Reads Dockerfile as list of lines (module-scoped) |

No new helpers needed — reuse existing infrastructure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test Delta

| Metric | Before | After |
| -------- | -------- | ------- |
| Tests in `TestBuilderStageOrdering` | 6 | 7 |
| Tests in `test_dockerfile_layer_ordering.py` | 16 | 17 |
| Full suite (all tests) | 3585 | 3586 |

### PR

| Item | Details |
| ------ | --------- |
| Issue | #1206 |
| PR | #1307 |
| Files changed | `tests/unit/docker/test_dockerfile_layer_ordering.py` (+22 lines) |

## Key Takeaways

1. **ARG must precede the RUN that consumes it** — otherwise `--build-arg` changes are silently ignored by the cache
2. **Static text analysis is sufficient** — no Docker daemon needed for ordering assertions
3. **Reuse existing helpers and test class** — avoids boilerplate and keeps tests DRY
4. **Pick unique anchors** — `"os.environ.get"` is more specific than `"EXTRAS"` which appears in many places
5. **Document with a module docstring update** — keeps the invariant list at the top of the file in sync

## Related Skills

- **dockerfile-layer-ordering**: Full set of Dockerfile layer ordering invariants (the parent test file)
- **static-dockerfile-testing**: General pattern for no-daemon Dockerfile static analysis
