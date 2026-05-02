---
name: strip-note-prefix-comments
description: 'Strip NOTE: prefix variants from plain comments in Mojo files without
  functional changes. Use when: a follow-up cleanup issue targets # NOTE: markers
  in test/example/script files, files contain # NOTE(#N): or # NOTE (version): variants,
  or scope must be verified against actual file state before editing.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: strip-note-prefix-comments

## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | strip-note-prefix-comments |
| **Category** | documentation |
| **Language** | Mojo |
| **Trigger** | Follow-up cleanup issue stripping `# NOTE:` prefix from test/example/script files |
| **Outcome** | Success — 9 markers stripped across 6 files, all pre-commit hooks passed, PR created |
| **Related** | Follow-up from issue #3072; see also `note-comment-cleanup` skill |

## When to Use

- A GitHub issue is a follow-up from a prior `# NOTE:` cleanup pass that left test/example files untouched
- Issue lists specific files and line numbers but they may have already been partially fixed
- Files contain variant patterns: `# NOTE(#N):`, `# NOTE (Mojo vX.Y):`, `# NOTE:` (bare)
- Changes are comment-only (no functional impact) and must pass `mojo format` pre-commit hook

## Verified Workflow

### 1. Verify actual state before editing

The issue description may be stale — some files may have already been cleaned in previous sessions.
Always grep first; do NOT trust the line numbers in the issue body.

```bash
grep -rn "# NOTE" tests/ examples/ shared/ benchmarks/ scripts/ --include="*.mojo"
```

This catches all variants:

- `# NOTE: text`
- `# NOTE(#3084): text`
- `# NOTE (Mojo v0.26.1): text`

Compare results against the issue's file list. Files with zero hits are already done — skip them.

### 2. Categorize variant patterns

| Pattern | Conversion |
| --------- | ----------- |
| `# NOTE: text` | `# text` |
| `# NOTE(#N): text` | `# text (#N):` — preserve issue reference at end |
| `# NOTE (Mojo vX.Y): text` | `# text (Mojo vX.Y).` — preserve version context inline |

The version/issue context is valuable — move it inline rather than dropping it.

### 3. Edit in parallel

All edits are independent. Use parallel Edit tool calls for all files. Each call targets
the exact multi-line block (including the continuation line) to avoid ambiguity.

### 4. Verify

```bash
grep -rn "# NOTE" <all scoped files> --include="*.mojo"
```

Expected: zero output.

### 5. Stage only the modified files (never `git add -A`)

```bash
git add tests/models/... examples/... shared/__init__.mojo benchmarks/... scripts/...
```

### 6. Commit — all pre-commit hooks should pass

Comment-only Mojo edits pass `mojo format`, `trailing-whitespace`, and `end-of-file-fixer`.
No compilation or test execution needed locally (CI is authoritative for Mojo builds).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting issue line numbers | Read files at the exact lines from the issue body | Several files had no `# NOTE` at those lines — already cleaned | Always grep first to discover actual state |
| Searching only `# NOTE:` (colon) | `grep -n "# NOTE:"` | Missed `# NOTE(#3084):` and `# NOTE (Mojo v0.26.1):` variants | Use `# NOTE` (no colon) to catch all variants |
| Dropping issue/version context | `# NOTE(#3084): text` → `# text` | Loses traceability to the referenced issue | Move context inline: `# text (#3084)` |

## Results & Parameters

```text
Files modified: 6
NOTE markers removed: 9
Variants encountered:
  # NOTE:            — 6 occurrences (bare, test/init/script files)
  # NOTE(#N):        — 1 occurrence (googlenet train.mojo)
  # NOTE (Mojo vX):  — 2 occurrences (run_infer.mojo, compare_results.mojo)
Pre-commit hooks: all passed (mojo format, trailing-whitespace, end-of-file-fixer)
PR: created with auto-merge enabled
```

### Grep command to scope work

```bash
grep -rn "# NOTE" tests/ examples/ shared/ benchmarks/ scripts/ --include="*.mojo"
```

### Edit pattern for `# NOTE (Mojo vX.Y): text`

```text
old: # NOTE (Mojo v0.26.1): PNG/JPEG image loading requires external image processing libraries.
new: # PNG/JPEG image loading requires external image processing libraries (Mojo v0.26.1).
```
