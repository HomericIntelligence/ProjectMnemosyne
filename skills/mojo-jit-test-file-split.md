---
name: mojo-jit-test-file-split
description: 'Pattern for splitting Mojo test files to avoid JIT heap corruption in
  libKGENCompilerRTShared.so. Use when: (1) Mojo test file crashes deterministically
  on Nth sequential call to a complex function, (2) crash stack shows libKGENCompilerRTShared.so,
  (3) test file has >10 test functions running deep-network-scale operations.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 JIT heap corruption when too many test functions accumulate memory in a single session |
| **Symptom** | Deterministic crash at Nth sequential call to a complex function (`libKGENCompilerRTShared.so`) |
| **Fix** | Split the single test file into multiple part files, each with ≤10 test functions (≤5 recommended for deep networks) |
| **Context** | Deep networks (VGG-16, ResNet) with many layers are especially prone — each forward pass allocates large intermediate tensors |
| **ADR** | ADR-009 in ProjectOdyssey documents this pattern |

## When to Use

- A Mojo test file crashes with a stack trace containing `libKGENCompilerRTShared.so`
- The crash is deterministic at the Nth sequential call to the same function (e.g., 4th call)
- The test file runs large model forward passes (deep CNNs, transformers)
- CI shows a test file passing fewer tests than it has functions (early exit on crash)
- You see `execution crashed` with no Python exception or Mojo error message

## Verified Workflow

### Quick Reference

```bash
# Count test functions in a file
grep -c "^fn test_" tests/models/test_my_model_e2e.mojo

# If count > 5 for deep networks, split the file
# Part 1: first half of tests
# Part 2: second half of tests
# Delete original
```

### Step 1: Identify the crash pattern

Check the error output for the signature:

```text
execution crashed
#0 0x... /libKGENCompilerRTShared.so+0x3cb78b
#1 0x... /libKGENCompilerRTShared.so+0x3c93c6
```

Confirm it's deterministic — run twice and verify it crashes at the same test.

### Step 2: Count test functions in the failing file

```bash
grep -c "^fn test_" tests/models/test_vgg16_e2e.mojo
# e.g., output: 10
```

Rule of thumb: for VGG-16-scale networks (13 conv layers + 3 FC), ≤5 tests per file is safe.

### Step 3: Create part1 and part2 files

Add the ADR-009 header comment at the top of each new file:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<model>_e2e.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Duplicate any shared helpers (`conv_block`, `forward`) in both files — Mojo has no `include` mechanism.

Split the tests roughly in half:

- **Part 1**: forward pass tests, training tests (heavier)
- **Part 2**: gradient checks, output range, numerical stability (lighter)

Update each file's `main()` to only call the tests it contains.

### Step 4: Delete the original file

```bash
git rm tests/models/test_vgg16_e2e.mojo
```

### Step 5: Verify CI auto-discovers both files

Check that the CI workflow uses a glob pattern (not a hardcoded list):

```yaml
# In .github/workflows/comprehensive-tests.yml
- name: Run test group
  run: just test-group "tests/models" "test_*.mojo"
```

If it uses `pattern: "test_*.mojo"`, no workflow changes are needed — both `_part1.mojo` and `_part2.mojo`
will be discovered automatically.

### Step 6: Verify test counts

```bash
grep -c "^fn test_" tests/models/test_vgg16_e2e_part1.mojo  # should be ≤5
grep -c "^fn test_" tests/models/test_vgg16_e2e_part2.mojo  # should be ≤5
```

### Step 7: Commit

```bash
git add tests/models/test_vgg16_e2e_part1.mojo \
        tests/models/test_vgg16_e2e_part2.mojo \
        tests/models/test_vgg16_e2e.mojo   # staged as deleted

git commit -m "fix(tests): split test_<model>_e2e.mojo to avoid JIT heap corruption

Split 10-test file into two 5-test files following ADR-009 workaround
pattern. The crash at the 4th sequential forward() call is caused by
Mojo v0.26.1 JIT heap corruption (libKGENCompilerRTShared.so).

Closes #<issue>
"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reduce batch size | Halved batch_size from 4 to 2 in all tests | Crash still occurs — the issue is cumulative JIT memory across test function calls, not per-call memory | Batch size is not the root cause; number of sequential JIT compilations is |
| Use smaller model variant | Considered using fewer channels (e.g., VGG-8) | Would change test semantics and no longer test VGG-16 architecture | Keep the real model, reduce the number of calls per session instead |
| Add teardown between tests | Mojo has no per-test teardown hooks in v0.26.1 | Not applicable — Mojo `main()` runs tests sequentially with shared JIT state | Architecture limitation; file splitting is the only reliable workaround |

## Results & Parameters

**Safe limits (VGG-16 scale)**:

| Network Scale | Safe Tests Per File | Notes |
|--------------|--------------------|----|
| Shallow (≤5 layers) | ≤10 | Standard Mojo guidance |
| Medium (6–10 layers) | ≤7 | LeNet-5, small ResNets |
| Deep (11+ layers) | ≤5 | VGG-16, ResNet-50 |

**Naming convention** for split files:

```text
test_<model>_e2e.mojo        → deleted
test_<model>_e2e_part1.mojo  → forward/training tests
test_<model>_e2e_part2.mojo  → gradient/numerical/stability tests
```

**ADR reference**: `docs/adr/ADR-009-heap-corruption-workaround.md` in ProjectOdyssey.
