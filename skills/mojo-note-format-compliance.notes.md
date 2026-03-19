# Session Notes: mojo-note-format-compliance

**Date**: 2026-03-07
**Issue**: ProjectOdyssey #3285
**PR**: ProjectOdyssey #3885

## Context

Issue #3071 required manual review of NOTE formats. This task added a lightweight CI check
so `# NOTE:` patterns without `(Mojo vX.Y.Z)` are caught automatically going forward.

## Files Created/Modified

- `scripts/check_note_format.py` — new Python audit script
- `tests/scripts/test_check_note_format.py` — 28 pytest tests
- `.pre-commit-config.yaml` — new `check-note-format` pygrep hook
- ~20 `.mojo` source files — ~37 violations fixed

## Key Bug: Wrong Regex

First attempt used `# NOTE[^(]` which seemed correct but failed because:

```
"# NOTE (Mojo v0.26.1): explanation"
       ^--- space here, not '('
```

`[^(]` means "any character that is not `(`". Space is not `(`, so the pattern matched
the compliant `# NOTE ` prefix. This caused 7 test failures when the tests correctly
asserted that compliant lines should not be flagged.

**Fix**: Use negative lookahead `(?!\s*\()` which means "not followed by optional
whitespace then `(`". This handles both `# NOTE(` and `# NOTE (` as compliant.

## GLIBC Issue

The `mojo-format` pre-commit hook fails on this dev host (Debian 10, GLIBC 2.28)
because Mojo requires GLIBC 2.32+. Used `SKIP=mojo-format` per the documented
workaround in CLAUDE.md. CI runs on Ubuntu 24.04 where it passes.

## Violation Classification

Violations fell into two categories:

1. **Mojo-specific limitations** (language/stdlib gaps) → add `(Mojo v0.26.1)`
   - `__all__` not supported, Dict iteration incomplete, no atof, etc.

2. **General code annotations** (design decisions, not Mojo limitations) → remove NOTE prefix
   - `# NOTE: Check is inside else block` — just a code comment, not a Mojo quirk
   - `# NOTE: These imports are commented out` — informational, not version-specific

## Test Pattern

28 tests structured as:
- `TestNoteViolationPattern` — regex unit tests (6 cases)
- `TestIsExcluded` — directory exclusion logic (6 cases)
- `TestFindViolations` — file scanning (9 cases)
- `TestScanSourceDirs` — repo-root scanning (2 cases)
- `TestMainExitCodes` — integration tests via subprocess (5 cases)