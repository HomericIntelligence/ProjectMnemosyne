---
name: mojo-limitation-note-standardization
description: "Standardize Mojo language/compiler limitation NOTEs to use consistent `# NOTE (Mojo vX.Y.Z):` format. Use when: cleaning up docs with inconsistent NOTE formats, auditing Mojo codebases, or implementing cleanup issues requiring NOTE standardization."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Purpose** | Standardize Mojo limitation comment format across codebase |
| **Target Pattern** | `# NOTE (Mojo vX.Y.Z):` |
| **Scope** | All `.mojo` files with limitation NOTEs |
| **Issue Type** | Cleanup issues (e.g., GitHub `[Cleanup]` label) |

## When to Use

- A GitHub issue requests documenting or standardizing Mojo language limitation NOTEs
- Pre-commit or code review flags inconsistent NOTE comment formats
- Auditing Mojo codebase for comments that lack version information
- Cleanup phase of a development section that introduced many limitation workarounds

## Verified Workflow

1. **Read the issue** to identify affected files and NOTE locations:
   ```bash
   gh issue view <number> --comments
   ```

2. **Search for all NOTE variants** in `.mojo` files:
   ```
   Grep pattern="# NOTE" glob="**/*.mojo" output_mode="content"
   ```
   Look for variants missing version info:
   - `# NOTE:` (no version)
   - `# NOTE: Mojo v0.26.1` (inline version, non-standard)
   - `# NOTE (Mojo v0.26.1):` (correct — skip these)

3. **Read each affected file** before editing (required by Edit tool).

4. **Apply standardization** using Edit tool — change `# NOTE:` or `# NOTE: Mojo vX.Y.Z` to `# NOTE (Mojo vX.Y.Z):`:
   - Pattern: `# NOTE:` → `# NOTE (Mojo v0.26.1):`
   - Pattern: `# NOTE: Mojo v0.26.1 ...` → `# NOTE (Mojo v0.26.1): ...`

5. **Verify no regressions** — files already using `# NOTE (Mojo vX.Y.Z):` need NO changes.

6. **Run pre-commit hooks**:
   ```bash
   pixi run pre-commit run --all-files
   ```
   The `mojo format` hook may fail due to GLIBC version issues in some environments — this is expected and not caused by the documentation changes. All other hooks (markdownlint, ruff, yaml, trailing-whitespace) must pass.

7. **Commit and push**:
   ```bash
   git add <files>
   git commit -m "docs(cleanup): document Mojo language limitation NOTEs with version info\n\nCloses #<number>"
   git push -u origin <branch>
   ```

8. **Check for existing PR** before creating a new one:
   ```bash
   gh pr create ...
   # If PR exists: gh pr merge <number> --auto --rebase
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Grepping for all NOTEs broadly | Used case-insensitive grep on all `.mojo` files for "NOTE" | Output was 39KB+ with many irrelevant matches (docstring `Note:`, print statements, etc.) | Narrow the grep pattern to `# NOTE` (with hash) to exclude prose and docstrings |
| Assuming all NOTEs need changes | Planned to edit all NOTE occurrences found | Many NOTEs already used correct `# NOTE (Mojo vX.Y.Z):` format | Always read target lines first; skip already-correct entries |
| Using `replace_all` on multi-file patterns | Considered batch replace across all files | Edit tool requires the file to be read first; `replace_all` is per-file, not cross-file | Read each file individually before editing; do targeted per-file edits |

## Results & Parameters

**Standard NOTE format** (canonical):
```mojo
# NOTE (Mojo v0.26.1): <description of limitation>
```

**Variants that need updating**:
```mojo
# NOTE: <description>                    # Missing version
# NOTE: Mojo v0.26.1 <description>       # Version inline, not in parens
```

**Files affected in ProjectOdyssey issue #3071** (for reference):
- `shared/training/mixed_precision.mojo` (2 NOTEs — FP16 SIMD limitation)
- `shared/utils/file_io.mojo` (1 NOTE — missing `os.remove()`)
- `benchmarks/scripts/compare_results.mojo` (1 NOTE — argv parsing)
- `examples/lenet-emnist/run_infer.mojo` (1 NOTE — image decoding)
- `shared/training/__init__.mojo` (1 NOTE — Track 4 interop)
- `shared/training/trainer_interface.mojo` (1 NOTE — Track 4 interop)

**Files already correct** (no changes needed):
- `shared/core/broadcasting.mojo`
- `shared/__init__.mojo`
- `shared/training/precision_config.mojo`
- `tests/shared/core/test_unsigned.mojo`
- `tests/shared/core/test_conv.mojo`
