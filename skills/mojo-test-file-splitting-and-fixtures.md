---
name: mojo-test-file-splitting-and-fixtures
description: "Use when: (1) a Mojo test file has >10 fn test_ functions causing intermittent libKGENCompilerRTShared.so JIT heap corruption in CI, (2) a test file takes >120s to compile due to heavyweight backward-pass tests in @always_inline parametric methods, (3) enforcing the ADR-009 per-file test count limit via pre-commit hook, (4) diagnosing and fixing Mojo test suite failures including missing main functions, wrong API usage, and JIT crashes, (5) running Mojo test suites with mojo test or just test-mojo, (6) creating E2E test fixtures for evaluating AI agents on Mojo development tasks"
category: testing
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Mojo Test File Splitting and Fixtures

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Consolidated reference for Mojo test file splitting (ADR-009), fixture creation, test runner patterns, and failure diagnosis |
| **Outcome** | Merged from 8 source skills covering ADR-009 file splitting, compile hang fixes, count guard pre-commit hook, test failure diagnosis, test runner basics, and E2E fixture creation |
| **Verification** | unverified |

## When to Use

- A `.mojo` test file contains more than 10 `fn test_` functions (ADR-009 hard limit)
- CI fails non-deterministically with `libKGENCompilerRTShared.so` JIT fault on a specific test group
- A test file takes >120 seconds to compile (backward-pass tests with large parametric types)
- You need a pre-commit hook to enforce the per-file test count limit going forward
- `just test-mojo` exits non-zero with `❌ FAILED after 3 attempts: ...`
- After a Mojo version upgrade that changes stdlib APIs (string indexing, List.size, etc.)
- Creating E2E test cases for evaluating AI agents on Mojo development tasks

## Verified Workflow

### Quick Reference

```bash
# Count fn test_ functions in a file (use ^fn test_[a-z] to avoid matching comment lines)
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo

# Check all sibling part files for capacity
for f in tests/path/to/test_foo_part*.mojo; do
  echo "$f: $(grep -c '^fn test_' $f)"
done

# Check CI workflow uses glob (no YAML changes needed) or explicit list (must update)
grep -n "test_original_filename" .github/workflows/comprehensive-tests.yml
grep -n "test_original_filename" scripts/validate_test_coverage.py

# Validate coverage after splitting
python3 scripts/validate_test_coverage.py

# Run and capture full test suite
just test-mojo 2>&1 | tee /tmp/test-all-output.log
grep "^❌ FAILED" /tmp/test-all-output.log

# Run individual file
pixi run mojo -I . tests/path/to/file.mojo

# Add count guard check (pre-commit)
python3 scripts/check_test_count.py tests/path/to/test_file.mojo
```

### Splitting Mojo Test Files (ADR-009)

**Root cause**: Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) triggers when a test file exceeds ~10 `fn test_` functions under CI load. ADR-009 mandates ≤10 `fn test_` per file; recommended target is ≤8 (2-test safety buffer).

**Step 1 — Count tests** (use `^fn test_[a-z]` to avoid counting comment lines):
```bash
grep -c "^fn test_[a-z]" tests/shared/core/test_elementwise.mojo
# e.g. 37 — exceeds the ≤10 limit
```

Never trust the issue description's count — always grep the actual file.

**Step 2 — Plan the split** by grouping tests logically (e.g., by function category):
- Target ≤8 tests per file (not minimum possible; 2-test buffer below hard limit of 10)
- 2 part files usually sufficient; only create more if needed

**Step 3 — Create split files** with ADR-009 header comment:
```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Tests for <topic> - Part N of M.
...
"""
```

Each part file needs:
- Full import block (Mojo has no shared include mechanism — copy imports verbatim into every file)
- Any shared helper functions redefined in each file (test helpers can't be imported across files)
- Its own `fn main() raises:` that calls only the tests in that file

```mojo
fn main() raises:
    """Run <name>_partN tests."""
    print("Running <name>_partN tests...")
    test_foo()
    print("✓ test_foo")
    # ...
    print("\nAll N <name>_partN tests passed!")
```

**Step 4 — Delete the original file**:
```bash
rm tests/shared/core/test_elementwise.mojo
```
`validate_test_coverage.py` will fail if the original exists but is not in the CI workflow — original must be deleted; split files fully replace it.

**Step 5 — Check CI workflow and validate_test_coverage.py**:

A glob in the CI workflow does NOT mean `validate_test_coverage.py` also uses globs. Always check both files independently.

```bash
# Check CI workflow
grep -n "test_elementwise" .github/workflows/comprehensive-tests.yml
# If GLOB pattern (test_*.mojo) → new part files auto-discovered, no changes needed
# If EXPLICIT filename → replace with all part filenames in the pattern field

# Check validate_test_coverage.py
grep "test_elementwise" scripts/validate_test_coverage.py
# If found → replace single entry with entries for each part file (1-for-N replacement)
# If not found → no changes needed
```

**Step 6 — Verify counts and commit**:
```bash
for f in tests/shared/core/test_elementwise_part*.mojo; do
  count=$(grep -c "^fn test_" "$f")
  echo "$(basename $f): $count tests"  # Must all be ≤10
done
python3 scripts/validate_test_coverage.py  # Must exit 0

git add tests/shared/core/test_elementwise.mojo \  # staged as deleted
        tests/shared/core/test_elementwise_part*.mojo
git commit -m "fix(ci): split test_elementwise.mojo into N files per ADR-009"
gh pr create --title "fix(ci): split <file> per ADR-009" --body "Closes #<issue>"
```

### Fixing Compile Hangs (>120s) by Moving Heavyweight Tests

When a test file compiles too slowly due to backward-pass tests that instantiate large parametric types (e.g., FC layers with 9216→4096 weights):

1. Identify the overloaded file: `grep -n "fn test_" tests/models/test_foo_part4.mojo`
2. Find a sibling part file with capacity (pick one with fewer than 8 tests):
   ```bash
   for f in tests/models/test_foo_part*.mojo; do
     echo "$f: $(grep -c '^fn test_' $f)"
   done
   ```
3. Move the heavyweight tests: copy function body to sibling, add to sibling's `main()`, delete from original, remove from original's `main()`
4. Update docstrings in both files
5. Verify counts: original should decrease, sibling should increase but stay ≤10
6. Commit:
   ```bash
   SKIP=mojo-format git commit -m "fix(tests): move backward tests from part4 to part5 to resolve compile hang"
   ```

**Never delete backward-pass tests** — move them to a sibling with capacity. Check existing sibling capacity before creating a new part file.

### ADR-009 Count Guard Pre-Commit Hook

Add a pre-commit hook to enforce the per-file limit going forward:

**Script** (`scripts/check_test_count.py`):
```python
import re, sys
from pathlib import Path
from typing import List

LIMIT = 10  # ADR-009: stay below the ~15-test crash threshold
_TEST_FN_RE = re.compile(r"^\s*fn test_", re.MULTILINE)  # re.MULTILINE is CRITICAL

def is_mojo_test_file(path: Path) -> bool:
    return path.suffix == ".mojo" and "tests" in path.parts

def count_tests_in_file(path: Path) -> int:
    try:
        return len(_TEST_FN_RE.findall(path.read_text(encoding="utf-8")))
    except OSError:
        return 0

def check_files(file_paths: List[str]) -> int:
    violations = []
    for raw in file_paths:
        path = Path(raw)
        if not is_mojo_test_file(path):
            continue
        count = count_tests_in_file(path)
        if count > LIMIT:
            violations.append(f"  {path}: {count} tests (limit: {LIMIT}) — split per ADR-009")
    if violations:
        for msg in violations:
            print(msg)
        return 1
    print(f"All test file(s) within the {LIMIT}-test limit.")
    return 0

if __name__ == "__main__":
    sys.exit(check_files(sys.argv[1:]))
```

**Pre-commit hook** (`.pre-commit-config.yaml`):
```yaml
- id: check-test-count
  name: Check Mojo Test Count (ADR-009)
  description: Fail if any Mojo test file exceeds 10 tests (heap-corruption threshold per ADR-009)
  entry: python3 scripts/check_test_count.py
  language: system
  files: '^tests/.*\.mojo$'
  pass_filenames: true
```

Key choices:
- `pass_filenames: true` — pre-commit passes only staged files; script never walks repo
- `files: '^tests/.*\.mojo$'` — scoped to test Mojo files; production files skipped
- `language: system` — uses project's pixi/system Python, no virtualenv needed

### Diagnosing and Fixing Mojo Test Suite Failures

Run and capture: `just test-mojo 2>&1 | tee /tmp/test-all-output.log`

Categorize each `❌ FAILED after 3 attempts:` entry:

| Category | Error Pattern | Fix |
|----------|--------------|-----|
| No main | `module does not define a 'main' function` | Add `fn main() raises:` calling all test functions |
| Relative import | `cannot import relative to a top-level package` | Skip file in test runner (library file, not a test) |
| String indexing | `no matching method in call to '__getitem__'` | Use `.as_bytes()[j]` and compare to ASCII codes |
| Float type | `cannot be converted from 'Float32' to 'Float64'` | `full()` always takes `Float64` fill value |
| Wrong import name | `module 'X' does not contain 'Y'` | Grep actual function names in source module |
| Wrong arg order | `value passed to 'atol' cannot be converted from StringLiteral` | `assert_close_float(a, b, rtol, atol, message)` — message is 5th arg |
| `List.size()` | `'List[T]' value has no attribute 'size'` | Use `len(list)` instead |
| Duplicate var | `invalid redefinition of '__'` | Use unique names `_bn2_rm`, `_bn2_rv` for nested batch norm outputs |
| Reshape needed | `Incompatible dimensions for matmul: 1 != N` | Flatten 4D→2D after `global_avgpool2d` before `linear` |
| JIT crash | `execution crashed` / `libKGENCompilerRTShared.so` | File upstream issue, skip in test runner |

**Skip non-test files in justfile** (`__init__.mojo`, `conftest.mojo`, library files without `main`):
```bash
if [[ "$(basename "$test_file")" == "__init__.mojo" ]] || \
   [[ "$(basename "$test_file")" == "conftest.mojo" ]] || \
   [[ "$test_file" == "tests/helpers/fixtures.mojo" ]] || \
   [[ "$test_file" == "tests/helpers/utils.mojo" ]]; then
    continue
fi
```

**API changes in Mojo v0.26.1**:
```mojo
# String character indexing
# OLD (broken): var ch = part[j]
var part_bytes = part.as_bytes()
var ch = Int(part_bytes[j])
if ch < 48 or ch > 57:  # ord("0")==48, ord("9")==57

# full() fill value
# OLD (broken): return full(shape, Float32(0.1), DType.float32)
return full(shape, Float64(0.1), DType.float32)  # full() always takes Float64

# List.size() → len()
# OLD: assert_true(params.size() == 10, "count mismatch")
assert_true(len(params) == 10, "count mismatch")
for i in range(len(params)):

# assert_close_float signature: (a, b, rtol, atol, message)
# OLD (broken): assert_close_float(val1, val2, 0.0, "message")
assert_close_float(val1, val2, 0.0, 0.0, "message")

# Import name changes:
# cross_entropy_loss → cross_entropy (in shared.core.loss)
# max_pool2d → maxpool2d (in shared.core.pooling)
# Linear class → linear function (in shared.core.linear)
```

**Flatten 4D→2D after global_avgpool2d**:
```mojo
# global_avgpool2d returns (batch, C, 1, 1) NOT (batch, C)
# linear() requires 2D input (batch, features)
var pooled = global_avgpool2d(features)     # (batch, C, 1, 1)
var batch_size = pooled.shape()[0]
var flat_shape = List[Int]()
flat_shape.append(batch_size)
flat_shape.append(C)
var flat = pooled.reshape(flat_shape)       # (batch, C)
var logits = linear(flat, fc_weights, fc_bias)
```

**maxpool2d empty output guard** (when kernel > input spatial dims):
```mojo
if out_height <= 0 or out_width <= 0:
    var empty_shape = List[Int](capacity=4)
    empty_shape.append(batch); empty_shape.append(channels)
    empty_shape.append(0); empty_shape.append(0)
    return zeros(empty_shape, x.dtype())
```

**Add main() to test files**:
```mojo
fn main() raises:
    print("Starting <Model> Tests...")
    print("  test_foo...", end="")
    test_foo()
    print(" OK")
    print("All <Model> Tests passed!")
```

**Check actual function names before importing**:
```bash
grep -n "^fn " shared/core/loss.mojo | head -10
grep -n "^fn \|^struct " shared/core/linear.mojo | head -10
grep -n "^fn maxpool" shared/core/pooling.mojo | head -5
```

**JIT crash handling** (`execution crashed` with `libKGENCompilerRTShared.so`):
- Individual test passes in isolation; full suite fails on 4th+ call
- Cannot reproduce locally (tried 30-100x — environment-specific to GitHub Actions)
- Skip in justfile with issue reference:
  ```bash
  if [[ "$test_file" == "tests/models/test_vgg16_e2e.mojo" ]]; then
      echo "Skipping $test_file (issue #NNNN - JIT heap corruption)"
      continue
  fi
  ```

### Running Mojo Tests

```bash
# Run all tests
mojo test tests/

# Run specific file
mojo test tests/test_tensor.mojo

# Run with verbose output
mojo test -v tests/

# Run with include path (required for most project structures)
pixi run mojo -I . tests/path/to/test_file.mojo

# Run via justfile
just test-mojo

# Run tests matching pattern
./scripts/run_tests.sh tensor
```

**Mojo test conventions**:
- Test functions must start with `test_`
- Test files must match `test_*.mojo` or `*_test.mojo`
- Tests run independently — no shared state between tests
- Use `raises` keyword for exception testing

### Creating E2E Test Fixtures for Mojo Agent Evaluation

Test fixture structure:
```
tests/fixtures/tests/test-XXX/
├── test.yaml           # Main definition (repo, commit, tiers)
├── prompt.md           # Task prompt for agent
├── config.yaml         # Timeout, cost limits
├── expected/
│   ├── criteria.md     # Detailed requirement descriptions
│   └── rubric.yaml     # Weighted scoring rubric
└── t0-t6/              # Tier sub-test directories
```

**Mojo v0.26.1 criteria to include in rubric**:
```yaml
# R003: Mojo Syntax Compliance
criteria:
  - "fn main() entry point"
  - "print() function used"
  - "out self in constructors (not mut self)"
  - "mut self in mutating methods"
  - "No deprecated patterns (inout, @value, DynamicVector)"
  - "List literals [1, 2, 3] not List[Int](1, 2, 3)"
  - "Tuple return syntax -> Tuple[T1, T2]"

# R014: Code Formatting
criteria:
  - "mojo format --check passes"
```

**Rubric weight distribution** (total 16.0 pts for 14 requirements):
| Category | Weight | Points |
|----------|--------|--------|
| Functional | 50% | 7.5 pts |
| Build/Compile | 22% | 3.5 pts |
| Documentation | 16% | 2.5 pts |
| Safety/Patterns | 16% | 2.5 pts |

**test.yaml template**:
```yaml
id: "test-XXX"
name: "Mojo Task Name"
description: |
  Description of what agent must accomplish.
source:
  repo: "https://github.com/modular/modular"
  hash: "COMMIT_HASH"
task:
  prompt_file: "prompt.md"
  timeout_seconds: 7200
validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"
tiers:
  - T0  # Prompts (24 sub-tests)
  - T1  # Skills (11 sub-tests)
  - T2  # Tooling (15 sub-tests)
  - T3  # Delegation (43 sub-tests with Mojo agents)
  - T4  # Hierarchy (7 sub-tests)
  - T5  # Hybrid (15 sub-tests)
  - T6  # Super (1 sub-test)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep original file alongside split parts | Rename `test_foo.mojo` → `test_foo_part1.mojo`, create `test_foo_part2.mojo`, keep `test_foo.mojo` | Original still has all tests; `validate_test_coverage.py` reports it as uncovered | Original must be deleted; split files fully replace it |
| Split to 3 files of ~12 tests each | Create part1/part2/part3 with ~12 tests each | Still exceeds ≤10 limit; can still trigger heap corruption | Target ≤8 per file; hard stop at 10 |
| Update CI workflow YAML explicitly when glob covers it | Added `test_datasets_part1.mojo test_datasets_part2.mojo` to pattern | Unnecessary when pattern already uses `test_*.mojo` glob | Check glob coverage before editing CI YAML |
| Skipped `validate_test_coverage.py` check | CI workflow used glob `training/test_*.mojo` so assumed no other files needed updating | `validate_test_coverage.py` had a separate exclusion list with the original filename hardcoded | Always grep the original filename in `validate_test_coverage.py` even when CI workflow uses globs |
| Shared imports via include | Extract common imports to a shared header file | Mojo v0.26.1 has no `#include` mechanism | Copy imports verbatim into every part file |
| Trust issue description for test count | Used count from issue body (said 25) | Actual count was 31 — off by 6 | Always grep `^fn test_[a-z]` to get real count; issue descriptions are often approximate |
| Delete backward tests instead of moving | Removed `test_fc1_backward_float32` | Loses test coverage for backward passes | Move to sibling part, never delete |
| Split into a new part6 when part5 had capacity | Created brand new `test_alexnet_layers_part6.mojo` | Overkill — part5 had only 6 tests out of 10 | Check existing sibling capacity before creating new files |
| Using `Float32` in `full()` calls | Passed `Float32(0.1)` as fill value | `full()` signature requires `Float64` fill_value | Check function signatures before assuming type compatibility |
| `var x_flat = x` (no reshape) | Skipped reshape after `global_avgpool2d` | Passed 4D tensor `(B,C,1,1)` to `linear()` which expects 2D | `global_avgpool2d` always returns 4D; always reshape to 2D before FC layers |
| Reusing `var _:` and `var __:` in nested blocks | Second batch_norm call redeclared `_` and `__` | Mojo treats `_` and `__` as named variables, not wildcards | Use unique names `_bn2_rm`, `_bn2_rv` for subsequent batch norm outputs |
| No `re.MULTILINE` flag in count guard | Used `re.compile(r"^\s*fn test_")` without flag | `^` only matches the very start of the string; subsequent occurrences missed | Always use `re.MULTILINE` when matching line-anchored patterns in multi-line files |
| `pass_filenames: false` in count guard hook | Script walked entire `tests/` tree | Ran on every commit regardless of what was staged | Use `pass_filenames: true`; let pre-commit filter to staged files |
| Filtering by filename prefix only in count guard | Checked `path.name.startswith("test_")` | Would accept `test_foo.mojo` outside `tests/`, flagging production files | Check both suffix AND that `"tests"` appears in `path.parts` |
| Splitting VGG16 main() to run only 3 tests | Reduced tests in main() to avoid 4th JIT crash | User rejected — ADR-009 was wrong explanation; real fix is in maxpool2d | Always investigate root cause before applying ADR workarounds |

## Results & Parameters

### ADR-009 Split Naming Convention

| Parameter | Value |
|-----------|-------|
| Mojo version with bug | v0.26.1 |
| Crash trigger threshold | >10 `fn test_` per file |
| ADR-009 hard limit | ≤10 `fn test_` per file |
| Recommended target | ≤8 `fn test_` per file (2-test buffer) |
| Split naming convention | `test_<name>_part1.mojo`, `test_<name>_part2.mojo` |
| CI failure rate before fix | ~65% (13/20 runs) |

### Example Split Distribution

```
test_elementwise_part1.mojo:  5 tests  (abs, sign)
test_elementwise_part2.mojo:  8 tests  (exp, log)
test_elementwise_part3.mojo:  8 tests  (log10, log2, sqrt)
test_elementwise_part4.mojo:  6 tests  (sin, cos)
test_elementwise_part5.mojo: 10 tests  (clip, rounding, logical)
Total: 37 tests preserved across 5 files
```

### Count Guard Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `LIMIT` | 10 | ADR-009 safety margin (crash at ~15) |
| Regex | `^\s*fn test_` with `re.MULTILINE` | Catches indented definitions; ignores string mentions |
| Hook `files` | `'^tests/.*\.mojo$'` | Scoped to test Mojo files only |
| `pass_filenames` | `true` | Pre-commit provides staged file list |

### Mojo Integer Division Gotcha (Pool Output Shape)

```
(1 + 0 - 2) // 2 + 1 = (-1) // 2 + 1 = -1 + 1 = 0  # empty output!
```
`maxpool2d(kernel=2, stride=2)` on a 1×1 input produces 0×0 output. Always guard: if `out_height <= 0 or out_width <= 0: return empty tensor`.

### Pre-Commit Hooks That Run on Mojo Files

- `mojo format` — auto-formats code
- `Check for deprecated List[Type](args) syntax` — catches anti-patterns
- `Validate Test Coverage` — verifies all test files appear in CI workflow pattern
- `check-test-count` (ADR-009) — enforces ≤10 test functions per file
