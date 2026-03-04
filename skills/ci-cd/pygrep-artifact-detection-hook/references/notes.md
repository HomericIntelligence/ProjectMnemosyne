# Raw Notes: pygrep-artifact-detection-hook

## Session Context

- **Date**: 2026-03-03
- **Issue**: HomericIntelligence/ProjectScylla#1366
- **Branch**: 1366-auto-impl
- **PR**: HomericIntelligence/ProjectScylla#1401

## Problem Statement

The phrase "Mojo equivalents" appeared in `scylla/` docstrings across two consecutive quality audits
(Feb 2026: #1347, March 2026: #1366). A prior manual fix (PR #1121) cleaned the artifacts once but
they returned. A pre-commit gate was needed to make regression impossible.

## Implementation Details

### Files Changed

1. `.pre-commit-config.yaml` — added `check-mojo-artifacts` hook (9 lines)
2. `tests/unit/scripts/test_check_mojo_artifacts.py` — 12 unit tests (new file, ~55 lines)

### Hook Placement Decision

Placed in the first `local` repo block alongside `check-shell-injection` (also a pygrep hook).
This keeps all zero-dependency phrase guards together.

### Ruff D301 Issue

First commit attempt failed with:
```
D301 Use `r"""` if any backslashes in a docstring
```
The test module docstring contained `\\.py$` (double backslash to represent a literal backslash in
the regex). Fix: add `r` prefix to docstring and use single backslash `\.py$`.

### Test Design Rationale

pygrep uses case-sensitive matching. Negative test cases include:
- `# No mojo (lowercase)` — capital N, lowercase m → no match (correct, case-sensitive)
- `# mojo equivalents (all lowercase)` → no match

Positive test cases include:
- Exact phrase `Mojo equivalents`
- Exact phrase `no Mojo`
- Embedded in longer sentences

### Baseline Verification

Confirmed `scylla/` contained zero matches before adding the hook:
```bash
grep -rn 'Mojo equivalents\|no Mojo' scylla/
# (no output)
```

## Timeline

1. Read issue + explore codebase: ~3 min
2. Add hook to `.pre-commit-config.yaml`: ~1 min
3. Write test file: ~3 min
4. Run tests (all 4011+12 pass): ~2 min
5. First commit attempt → D301 error → fix docstring → second commit: ~2 min
6. Push + create PR: ~1 min
