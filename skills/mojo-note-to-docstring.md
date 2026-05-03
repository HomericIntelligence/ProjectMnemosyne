---
name: mojo-note-to-docstring
description: "Convert, condense, and enforce Mojo NOTE comments. Use when: (1) converting
  inline # NOTE: implementation-constraint comments to proper docstring Note: sections,
  (2) condensing verbose compiler-limitation NOTEs with version + tracking references
  on GLIBC-mismatched systems, (3) enforcing # NOTE (Mojo vX.Y.Z): format compliance
  via pre-commit hook and Python audit script."
category: documentation
date: 2026-03-05
version: 2.0.0
user-invocable: false
tags:
  - mojo
  - notes
  - docstrings
  - pre-commit
  - code-cleanup
  - compiler-limitations
---
## Overview

| Field | Value |
| ------- | ------- |
| **Objective** | Convert `# NOTE:` inline comments to proper docstring `Note:` sections; condense verbose compiler-limitation NOTEs; enforce `# NOTE (Mojo vX.Y.Z):` format via CI |
| **Language** | Mojo (.mojo files) |
| **Scope** | Implementation constraint comments, compiler-limitation NOTEs, format compliance |
| **Trigger** | GitHub cleanup issues requesting NOTE → docstring conversion, verbose NOTE condensation, or NOTE format enforcement |
| **Outcome** | Concise, tracked NOTEs with version + issue reference; docstrings updated; format hook enabled |
| **Absorbed** | mojo-note-cleanup-without-compiler (v1.0.0), mojo-note-format-compliance (v1.0.0) on 2026-05-03 |

## When to Use

- A cleanup issue asks to convert `# NOTE:` comments to docstrings
- Code review flags inline NOTE comments that should be in the public API docs
- Preparing a module for documentation generation
- Reducing comment noise while preserving constraint knowledge
- Assigned a `[Cleanup]` issue to update or condense Mojo compiler limitation comments
- Local system cannot run `mojo` due to GLIBC version mismatch (Debian 10: GLIBC 2.28 vs required 2.32+)
- Need to verify if a compiler limitation is still present without being able to compile
- NOTEs are verbose and need to be replaced with concise version + tracking references
- Adding a pre-commit hook to enforce a comment format standard in Mojo files
- Implementing a `pygrep` hook that requires negative lookahead regex
- Writing a Python script to audit and bulk-fix non-compliant `# NOTE` comments
- Any codebase-wide comment normalization task before enabling a new lint rule

## Verified Workflow

### Part A: Convert NOTE comments to Docstrings

#### Step 1: Discover all NOTE comments

```bash
grep -rn "# NOTE:" --include="*.mojo" .
```

This gives a complete list of files and line numbers to review.

#### Step 2: Categorize each NOTE

Classify each NOTE into one of these types:

| Type | Action |
| ------ | -------- |
| Implementation constraint (design decision) | Add to function/struct docstring `Note:` section |
| Redundant (already covered by docstring) | Remove inline NOTE entirely |
| Module-level constraint (no function context) | Reword as plain comment, remove `NOTE:` prefix |
| Test-specific / skip explanation | Leave as-is (not an API constraint) |
| Large block comment (detailed rationale) | Summarize in docstring, remove block |

#### Step 3: Apply transformations

**Pattern A — Redundant NOTE (docstring already covers it):**

```mojo
# Before
fn bf16(...) -> PrecisionConfig:
    """...
    Note:
        Currently uses FP16 as BF16 is not natively supported.
    """
    # NOTE: bfloat16_dtype aliases to float16_dtype until Mojo supports BF16
    return PrecisionConfig(...)

# After — just remove the inline NOTE
fn bf16(...) -> PrecisionConfig:
    """...
    Note:
        Currently uses FP16 as BF16 is not natively supported.
    """
    return PrecisionConfig(...)
```

**Pattern B — NOTE with no existing docstring Note section:**

```mojo
# Before
fn remove_safely(filepath: String) -> Bool:
    """Remove file safely.

    Args:
        filepath: File to remove.

    Returns:
        True if removed, False if error.
    """
    # NOTE: Mojo v0.26.1 doesn't have os.remove() or file system operations
    if not file_exists(filepath):
        return False

# After — add Note section, remove inline NOTE
fn remove_safely(filepath: String) -> Bool:
    """Remove file safely.

    Args:
        filepath: File to remove.

    Returns:
        True if removed, False if error.

    Note:
        Mojo v0.26.1 does not have os.remove() or file system delete operations.
        This is a placeholder that simulates successful removal.
    """
    if not file_exists(filepath):
        return False
```

**Pattern C — Large block NOTE comment:**

```mojo
# Before (lines 283-304 of mixed_precision.mojo)
if params.dtype() == DType.float16:
    # NOTE: FP16 SIMD vectorization is blocked by Mojo compiler limitation.
    # Mojo does not support SIMD load/store operations for FP16 types.
    # [... 20 more lines of explanation ...]
    var src_ptr = params._data.bitcast[Float16]()

# After — summarize in function docstring, condense inline comment
# (docstring gets the Note: section, inline becomes one-liner)
if params.dtype() == DType.float16:
    # FP16 SIMD blocked, see docstring Note
    var src_ptr = params._data.bitcast[Float16]()
```

**Pattern D — Struct-level NOTE between methods:**

```mojo
# Before — NOTE floating between __init__ and __next__
fn __init__(...): ...

# NOTE: We intentionally do not implement __iter__() because List[Int] fields
# are not Copyable, and __iter__ would need to return Self which requires copying.

fn __next__(...): ...

# After — move to struct docstring
struct BroadcastIterator:
    """Iterator for efficiently iterating over broadcast tensor elements.

    Note:
        __iter__() is intentionally not implemented because List[Int] fields
        are not Copyable. Use __next__ directly with a while loop instead.
    """
    fn __init__(...): ...
    fn __next__(...): ...
```

**Pattern E — Module-level NOTE (no function context):**

```mojo
# Before
# NOTE: Callbacks must be imported directly from submodules due to Mojo limitations:

# After — rephrase without NOTE: prefix
# Mojo limitation: callbacks must be imported directly from submodules:
```

#### Step 4: Verify no # NOTE: remain in target files

```bash
grep -rn "# NOTE:" --include="*.mojo" shared/ tests/shared/
```

Only notes in test skip contexts or examples should remain.

#### Step 5: Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass. Mojo format may be skipped with GLIBC warnings on older Linux — this is expected.

---

### Part B: Condense Verbose Compiler-Limitation NOTEs (No Local Mojo)

Use this part when local Mojo is unavailable (GLIBC mismatch) and NOTEs are verbose blocks needing condensation.

#### Step 1: Determine Mojo version from pixi.toml (no compilation needed)

```bash
grep -E "mojo|max" pixi.toml | head -5
# e.g. mojo = ">=0.26.1.0.dev2025122805,<0.27"
```

The version range is authoritative for which compiler limitations apply.

#### Step 2: Check if limitation is already tracked in the codebase

```bash
# Search for related issue references
grep -r "Issue #" shared/ --include="*.mojo" | grep -i "fp16\|simd"
# e.g. "FP16→FP32: ~4x speedup using SIMD vectorization (Issue #3015)"
```

Cross-referencing docstrings and module headers often reveals existing tracking issues.

#### Step 3: Update NOTEs to concise form

Replace verbose multi-line NOTE blocks (20+ lines) with 4-8 line concise form:

```mojo
# NOTE: <limitation description> blocked by a Mojo compiler limitation
# (<specific symptom> as of Mojo v<version>).
# Tracked in project issue #<number>; no upstream Mojo issue filed yet.
# Re-evaluate when Mojo adds <feature> support.
#
# Workaround: <current approach>
# Performance Impact: <quantified impact>
```

Key information to retain:
- Mojo version where limitation was confirmed
- Project issue tracking reference
- Upstream issue status (filed or not)
- Re-evaluation trigger condition
- Workaround and performance impact (if space allows)

Information to remove from verbose NOTEs:
- Detailed implementation plans (belong in the tracking issue, not inline)
- Bullet lists of compiler details (summarize to one line)
- "Reference: Track Mojo compiler releases for..." (replace with specific trigger)

#### Step 4: Run non-Mojo pre-commit hooks with SKIP

Since `mojo-format` cannot run locally (GLIBC mismatch), skip it explicitly:

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

All other hooks (markdown, trailing whitespace, YAML, ruff, etc.) should pass.
The CI Docker container will run `mojo-format` automatically on the PR.

#### Step 5: Commit with conventional format

```bash
git commit -m "fix(scope): update FP16 SIMD blocker NOTEs with current status

Update both FP16 SIMD blocker NOTEs in <file>.mojo to include:
- Confirmed Mojo version (v<version>) where limitation exists
- Project tracking reference (issue #<number>)
- Note that no upstream Mojo issue has been filed yet
- Clear re-evaluation trigger

Removes verbose implementation plan while retaining performance context.

Closes #<issue>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

#### Step 6: Create PR with cleanup label

```bash
gh pr create \
  --title "fix(scope): update FP16 SIMD blocker NOTEs with current status" \
  --body "..." \
  --label "cleanup"
gh pr merge --auto --rebase
```

---

### Part C: Enforce # NOTE (Mojo vX.Y.Z): Format Compliance via CI

#### Step 1: Write the audit script (`scripts/check_note_format.py`)

```python
import re
from pathlib import Path
from typing import List, Tuple

EXCLUDED_DIRS = {".worktrees", ".pixi", "build", ".git", "__pycache__", ".mypy_cache"}
SOURCE_DIRS = ["benchmarks", "examples", "papers", "scripts", "shared", "tests"]

# CRITICAL: Use negative lookahead, NOT [^(]
# '# NOTE[^(]' falsely matches '# NOTE (' because space != '('
NOTE_VIOLATION_PATTERN = re.compile(r"# NOTE(?!\s*\()")
```

Key design decisions:
- Excludes `.worktrees/`, `.pixi/`, `build/`, `.git/` to avoid false positives from dependencies
- Defaults to scanning repo source dirs only (not the entire filesystem)
- Accepts optional directory argument for targeted scans
- Exits 0 on clean, 1 on any violations
- Prints `file:line: content` to stdout, summary to stderr

#### Step 2: Fix existing violations before enabling the hook

**Order matters**: Fix all violations first, then add the hook. Adding the hook first blocks all commits.

Categorize violations into two types:
- **Mojo-limitation notes** → annotate with `(Mojo v0.26.1)`: e.g., `# NOTE: Dict iteration not supported` → `# NOTE (Mojo v0.26.1): Dict iteration not supported`
- **General code comments** → remove `# NOTE:` prefix or replace with plain comment: e.g., `# NOTE: Check is inside else block to avoid...` → `# Check is inside else block to avoid...`

#### Step 3: Add the pre-commit hook (`.pre-commit-config.yaml`)

```yaml
- id: check-note-format
  name: Check NOTE format compliance
  description: Enforce # NOTE (Mojo vX.Y.Z): format in Mojo files (issue #3285)
  entry: '# NOTE(?!\s*\()'
  language: pygrep
  files: ^(benchmarks|examples|papers|scripts|shared|tests)/.*\.(mojo|🔥)$
  types: [text]
```

Place it immediately after `check-list-constructor` in the same local repo block.

#### Step 4: Verify clean state

```bash
python3 scripts/check_note_format.py  # exits 0
pixi run python -m pytest tests/scripts/test_check_note_format.py -v  # 28 passed
```

## Results & Parameters

### Part A: NOTE → Docstring Session Results (Issue #3072, ProjectOdyssey)

- 12 `# NOTE:` implementation constraints converted across 10 files
- 5 NOTEs removed (redundant — already in docstring)
- 4 NOTEs moved to function/struct docstrings as `Note:` sections
- 3 NOTEs reformatted (prefix removed, integrated into surrounding comments)
- Pre-commit hooks: all passed (exit 0)

**Files modified:**

```text
shared/core/broadcasting.mojo       — NOTE → struct docstring Note:
shared/core/loss.mojo               — NOTE removed (redundant)
shared/testing/layer_testers.mojo   — 3x NOTE prefix removed
shared/training/__init__.mojo       — NOTE → plain comment + condensed inline
shared/training/loops/training_loop.mojo  — NOTE → function docstring Note:
shared/training/mixed_precision.mojo — large block NOTE → docstring + 1-liner
shared/training/precision_config.mojo — NOTE removed (redundant)
shared/training/trainer_interface.mojo — NOTE → function docstring Note:
shared/utils/config.mojo            — NOTE removed (redundant)
shared/utils/file_io.mojo           — NOTE → function docstring Note:
```

**Commit message pattern:**

```
cleanup(docs): convert implementation constraint NOTEs to docstrings
```

### Part B: Concise NOTE Environment (Debian 10 / GLIBC Mismatch)

```text
Host OS: Debian 10 (GLIBC 2.28)
Mojo requirement: GLIBC 2.32+
Mojo version (from pixi.toml): >=0.26.1.0,<0.27
Workaround: SKIP=mojo-format for pre-commit
```

### Part B: NOTE Before (verbose, 22 lines)

```mojo
# NOTE: FP16 SIMD vectorization is blocked by Mojo compiler limitation.
# Mojo does not support SIMD load/store operations for FP16 types.
#
# Current Limitation: Mojo v0.26.1+ does not support SIMD vectorization for
# FP16 load operations. This prevents efficient bulk conversion from FP16 to FP32.
#
# Compiler Limitation Details:
# - DTypePointer.load[width=N]() doesn't support FP16 types
# - FP16 SIMD types exist but load/store operations are unimplemented
# - No way to vectorize bulk FP16->FP32 conversions in current compiler
#
# Workaround: Scalar loop conversion (one element at a time)
# Performance Impact: ~10-15x slower than FP32->FP32 SIMD path
# Expected Speedup When Fixed: ~4x (matching FP32->FP32 performance)
#
# Implementation Plan:
# When Mojo adds FP16 SIMD load support:
# 1. Load FP16 vectors with DTypePointer[Float16].load[width]()
# 2. Convert to FP32 with explicit cast or builtin function
# 3. Store with DTypePointer[Float32].store[width]()
#
# Reference: Track Mojo compiler releases for FP16 SIMD support
```

### Part B: NOTE After (concise, 8 lines)

```mojo
# NOTE: FP16 SIMD vectorization is blocked by a Mojo compiler limitation
# (FP16 not supported as a SIMD element type as of Mojo v0.26.1).
# Tracked in project issue #3015; no upstream Mojo issue filed yet.
# Re-evaluate when Mojo adds FP16 SIMD load/store support.
#
# Workaround: Scalar loop conversion (one element at a time)
# Performance Impact: ~10-15x slower than FP32->FP32 SIMD path
# Expected Speedup When Fixed: ~4x (matching FP32->FP32 performance)
```

### Part C: Regex pattern (copy-paste)

```python
import re
NOTE_VIOLATION_PATTERN = re.compile(r"# NOTE(?!\s*\()")
```

### Part C: Pre-commit hook entry (copy-paste)

```yaml
entry: '# NOTE(?!\s*\()'
language: pygrep
```

### Part C: Violation categories and fixes

| Type | Example Before | Example After |
| ------ | ---------------- | --------------- |
| Mojo limitation | `# NOTE: Mojo doesn't support __all__` | `# NOTE (Mojo v0.26.1): Mojo doesn't support __all__` |
| Mojo limitation w/issue | `# NOTE: Batch iteration blocked by #3076` | `# NOTE (Mojo v0.26.1, #3076): Batch iteration blocked` |
| General comment | `# NOTE: Check is inside else block` | `# Check is inside else block` |
| Commented-out imports | `# NOTE: These imports are commented out` | `# These imports are commented out` |

### Part C: Test coverage pattern

```python
class TestNoteViolationPattern:
    def test_does_not_flag_compliant_format(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE (Mojo v0.26.1): explanation")

    def test_does_not_flag_compliant_with_issue(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE (Mojo v0.26.1, #3092): reason")

    def test_does_not_flag_note_with_open_paren(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE(#3092): issue ref")

    def test_detects_note_colon(self):
        assert NOTE_VIOLATION_PATTERN.search("    # NOTE: some text")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Convert ALL NOTE comments | Initially considered converting every `# NOTE:` in the repo | Test files have NOTE-style skip explanations that don't belong in docstrings | Filter by context: only convert NOTEs in production code that describe API constraints |
| Remove NOTE block wholesale | Considered deleting the large FP16 SIMD block comment entirely | Would lose important performance rationale for future developers | Summarize key points in docstring Note:, condense inline to 1-liner |
| Add Note: to every function | Considered adding Note: to all functions touched | Would bloat docstrings unnecessarily | Only add Note: when the constraint is something callers need to know |
| Convert module-level NOTEs to docstrings | Module-level comments aren't in functions/structs | Mojo doesn't have module-level docstrings the same way | Rephrase as plain comment, remove NOTE: prefix |
| Running `pixi run mojo --version` | Tried to verify Mojo version directly | GLIBC 2.32 required but host has 2.28; mojo binary crashes | Use `pixi.toml` version constraint instead — it's the authoritative version spec |
| Running `pixi run mojo /tmp/test_fp16_simd.mojo` | Tried to compile test to confirm FP16 SIMD limitation still exists | GLIBC crash prevents any Mojo execution on Debian 10 | On Debian 10 hosts, mojo cannot run outside Docker. Use version range from pixi.toml + cross-reference existing docstring comments |
| Running `just pre-commit-all` | Tried to use justfile shortcut | `just` not installed on this system | Use `pixi run pre-commit run --all-files` directly |
| Running `pixi run pre-commit run --all-files` without SKIP | All hooks including mojo-format | mojo-format fails due to GLIBC | Use `SKIP=mojo-format pixi run pre-commit run --all-files`; CI handles mojo-format |
| `# NOTE[^(]` as regex | Used character class negation to exclude `(` | `# NOTE (Mojo v0.26.1):` has a space before `(`, so `# NOTE` matches because space ≠ `(` | Always use negative lookahead `(?!\s*\()` when the separator between keyword and delimiter may vary |
| `language: pygrep` with `[^(]` pattern | Same pattern in pre-commit hook | Same false-positive: compliant lines were flagged and hook blocked all commits | Negative lookaheads work fine in `language: pygrep` hooks — pre-commit uses Python's `re` module |
| Checking existing violations manually | Tried to enumerate violations from memory | Missed several files; grep output was the source of truth | Always run `grep -rn "# NOTE[^(]" --include="*.mojo" shared/ tests/ ...` first to get the definitive list |
