---
name: note-comment-cleanup
description: 'Systematically review and clean up NOTE/Note comment inconsistencies:
  remove stale markers, convert docstring NOTEs to prose, normalize casing. Use when:
  auditing code comments for a cleanup issue, standardizing NOTE vs Note casing, or
  removing outdated reference markers.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | note-comment-cleanup |
| **Category** | documentation |
| **Language** | Mojo / Python / any |
| **Trigger** | Cleanup issue targeting NOTE/Note comments |
| **Outcome** | Consistent `# NOTE:` casing, stale markers removed, docstring NOTEs converted to prose |

## When to Use

- A GitHub cleanup issue asks to audit "miscellaneous NOTE comments"
- Codebase has mixed `# Note:` and `# NOTE:` usage in the same modules
- Stale "X removed" or "See issue #N" NOTEs reference closed issues or deleted code
- Docstrings contain `NOTE:` prefixes that should be plain prose

## Verified Workflow

### 1. Discovery — find all NOTE variants

```bash
# Find all NOTE/Note/note patterns across Mojo files
grep -rn "# NOTE:\|# Note:\|# note:" shared/ --include="*.mojo"

# Find stale "removed" markers
grep -rn "removed\|deprecated\|See issue #" scripts/ --include="*.py"
```

Use the Grep tool (`output_mode: content`, `-n: true`) for each variant separately.
Run the full codebase grep first, then targeted reads for context.

### 2. Categorize NOTEs into dispositions

| Category | Action |
|----------|--------|
| Stale "X removed" markers | **Remove** — changelog noise once code is gone |
| Reference to closed GitHub issue | **Update** — remove issue number or reword |
| NOTE inside a docstring | **Convert to prose** — strip `NOTE:` prefix |
| Mixed casing (`# Note:` in `shared/`) | **Normalize** — `# Note:` → `# NOTE:` |
| Mojo language limitation notes | **Keep** — still accurate, explains constraints |
| Precision/epsilon justifications | **Keep** — critical for correctness |
| Open issue/tracker references | **Keep** — still actionable |

### 3. Verify referenced issues are actually closed

```bash
gh issue view <N> --json state,title
```

Only remove/update NOTEs referencing closed issues if they add no standalone value.

### 4. Make edits

- Use `Edit` tool with `replace_all: false` for unique strings
- Use `replace_all: true` only for exact duplicates (e.g., same NOTE in multiple methods)
- Read each file before editing (required by Edit tool)
- Docstring NOTE conversion: remove `NOTE:` prefix, adjust capitalization if needed

### 5. Handle mojo-format hook failure (GLIBC incompatibility)

On older Linux machines, the `mojo` binary requires GLIBC >= 2.32 which may not be present:

```bash
# Skip only the mojo-format hook; run all others
SKIP=mojo-format pixi run pre-commit run --all-files
```

The `mojo-format` hook will pass in CI (Docker has correct GLIBC). All other hooks
(ruff, markdownlint, trailing-whitespace, end-of-file-fixer, check-yaml) must pass locally.

### 6. Check for ruff auto-formatting

The first pre-commit run may auto-reformat Python files (ruff-format). Check git status
after pre-commit and stage any reformatted files before committing:

```bash
git status  # Look for modified Python files
git add <ruff-reformatted-file>
```

### 7. Commit with conventional format

```
cleanup(comments): review and clean up miscellaneous reference NOTEs

- Remove N stale "X removed" marker comments from scripts/
- Update NOTE referencing closed issue #N
- Convert M inline NOTE: prefixes inside docstrings to plain prose
- Normalize all # Note: → # NOTE: in shared/ source files (K files)

Closes #<issue>
Part of #<parent>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running pre-commit in background and waiting | Used `run_in_background=True` then `TaskOutput` to poll | TaskOutput `block` and `timeout` params require JSON types not strings; polling was unclear | Run pre-commit synchronously with explicit timeout; check output file directly via Bash if background |
| Running `just pre-commit-all` | Called `just` command directly | `just` not on PATH in this environment | Use `pixi run pre-commit run --all-files` instead |
| Running multiple pre-commit hooks by name in one call | `pixi run pre-commit run trailing-whitespace end-of-file-fixer` | pre-commit CLI doesn't accept multiple hook IDs as positional args | Run `--all-files` or one hook at a time with `--hook-stage` |
| Editing without reading | Attempted Edit on files not yet read in session | Edit tool requires prior Read in the conversation | Always Read before Edit; batch reads in parallel for efficiency |

## Results & Parameters

**Session stats (issue #3074):**

- Files modified: 23
- Lines removed (stale): 8
- NOTEs converted (docstring → prose): 6 locations across 3 files
- NOTEs normalized (`# Note:` → `# NOTE:`): ~20 occurrences across 17 files
- All non-mojo hooks: PASS
- `mojo-format`: SKIP (GLIBC incompatibility on host; passes in CI Docker)

**Grep patterns used:**

```bash
# Primary discovery
grep -rn "# NOTE:\|# Note:" shared/ --include="*.mojo"

# Stale markers
grep -rn "removed\|get_plan_dir" scripts/ --include="*.py"

# Verify nothing remains
grep -rn "# Note:" shared/ --include="*.mojo"  # Should return 0 matches
```

**Key NOTEs to always keep (do not remove):**

- FP16 SIMD vectorization blocked by compiler limitation
- `epsilon=3e-4` precision justifications referencing issue #2704
- Track 4 (Python↔Mojo interop) blocker references
- Mojo language limitation notes (`no __all__`, `no os.remove()`, BF16 alias)
