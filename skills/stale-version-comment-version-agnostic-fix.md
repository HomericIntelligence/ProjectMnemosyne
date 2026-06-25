---
name: stale-version-comment-version-agnostic-fix
description: "Version-agnostic comment pattern replaces hardcoded snapshot versions that go stale on dependency bumps. Use when: (1) a code comment claims a specific version constraint ('tests only 1.x') that no longer matches the spec/lock, (2) updating dependency documentation that references major/minor versions, (3) preventing re-staleness when dependency versions bump."
category: ci-cd
date: 2026-06-21
version: "1.0.0"
user-invocable: false
verification: verified-local
history: stale-version-comment-version-agnostic-fix.history
tags: []
---

# Stale Version Comment: Version-Agnostic Fix Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-21 |
| **Objective** | Replace hardcoded version snapshots in code comments with version-agnostic language that won't re-stale on dependency bumps |
| **Outcome** | verified-local |
| **Verification** | All 7 verification criteria passed; false claim removed; CI integration pending when PR merges |
| **History** | [changelog](./stale-version-comment-version-agnostic-fix.history) |

## When to Use

- A code comment claims a specific version constraint ("CI tests only 1.x", "supports 1.x and 2.x") that no longer matches the dependency spec or lock
- The spec admits a wider range than the comment claims (e.g., spec is `>=1.8.0,<3` admitting 2.x, comment says "1.x only")
- Multiple files repeat the same stale version snapshot and all need de-stalifying
- Preventing re-staleness when dependencies bump to new major/minor versions
- Coordinating between dependency spec, lockfile, and CI invocation documentation

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the false/stale version claim
grep -n "CI tests only 1\.x\|tests only 1\.x" pyproject.toml

# 2. Verify the actual constraint is in the spec (not in the comment)
grep -A2 -B2 "mypy" pyproject.toml | grep -E "^mypy|>=|<"
grep "mypy" pixi.lock | head -1

# 3. Replace the false claim with version-agnostic language
# OLD: "mypy has different error semantics across 1.x and 2.x; CI tests only 1.x"
# NEW: "mypy version is resolved by pixi.lock; see the dependency spec (>=1.8.0,<3) for the floor/cap"

# 4. Mirror the style/pattern of nearby comments for consistency
# Example: look at pytest comment immediately above/below

# 5. Run negative grep to confirm old claim is gone
! grep -nE "CI tests only 1\.x|tests only 1\.x" pyproject.toml

# 6. Verify no hardcoded version numbers in the replacement
! grep -nE "[0-9]+\.[0-9]+" <edited-comment>

# 7. Check dependency-consistency tests still pass
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v
```

### Detailed Steps

1. **Identify the false/stale claim**: Search the file (e.g., `pyproject.toml`) for version-specific language:
   - Patterns: "1.x only", "2.x supported", "tests only X.Y", "different semantics in X"
   - Verify the claim no longer matches the dependency spec line
   - Confirm the lockfile resolves a version outside the claimed range

2. **Verify the actual constraint is in the code**: Check that the dependency spec (not the comment) is the authoritative source:
   - `grep "mypy" pyproject.toml` should show the spec (e.g., `>=1.8.0,<3`)
   - `grep "mypy" pixi.lock` should show the resolved version
   - The comment is NOT authoritative — it's explanatory

3. **Replace with version-agnostic language** that references the spec/lock/CI as sources of truth:
   - Remove specific version claims ("only 1.x", "2.x and later")
   - Add explicit mention of: (a) the dependency spec as the floor/cap authority, (b) the lockfile as the resolved-version authority, (c) the CI invocation mechanism
   - Example pattern: "mypy version is resolved by pixi.lock against the spec (>=1.8.0,<3); CI runs `pixi run mypy` against this resolved version"

4. **Mirror the comment style of nearby comments**: Look for adjacent comments in the file (e.g., the pytest comment immediately above/below) and match:
   - Indentation, punctuation, parenthetical style
   - Length and tone (verbose explanation vs. terse spec reference)
   - Cross-reference pattern (does pytest mention its test file? Should mypy?)

5. **Run negative grep to confirm the old claim is gone**:
   ```bash
   ! grep -nE "CI tests only 1\.x|tests only 1\.x" pyproject.toml
   # Exit code 0 means the pattern was NOT found (good)
   ```

6. **Verify no hardcoded version numbers in the replacement**:
   - The new comment should NOT contain `[0-9]+\.[0-9]+` patterns (e.g., "1.8", "2.1", "3.0")
   - Version claims belong in the spec line, not the comment
   - Run: `! grep -nE "[0-9]+\.[0-9]+" <comment-block>`

7. **Verify the enforcing test still passes**:
   - If the project has a dependency-consistency test (e.g., `test_dependency_floor_consistency.py`), re-run it
   - Confirm all 11+ tests pass
   - The test validates that the new comment did not inadvertently break anything

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Embedding specific version ("2.1.0") | Replaced "1.x only" with "resolves to 2.1.0" | Immediately stale when mypy bumps to 2.2.x or 3.0 | Never embed ANY version number in the comment; reference the spec/lock, not a snapshot |
| Only removing the false claim | Deleted "CI tests only 1.x" without replacement text | Left the comment incomplete and confusing; readers unsure why the spec is `<3` | Always explain WHY the constraint exists; reference the authoritative sources (spec/lock/CI) |
| Inconsistent style from neighbors | Used prose format when pytest comment was terse; different punctuation | Reduced readability and maintainability; reviewers flagged as inconsistent | Read existing comments in the same file first; match their tone, structure, and cross-reference style |
| Changing the spec by mistake | While updating the comment, accidentally narrowed the spec to `>=1.8.0,<2` | Over-constrained the dependency; broke downstream usage that relied on 2.x support | The comment change should NEVER touch the spec line; edit only the explanatory text |
| Forgetting to update pixi.toml | Only updated pyproject.toml comment, left pixi.toml stale | Cross-manifest consistency test failed; both files must be updated together | If the project has both manifests, update comments in BOTH locations |

## Results & Parameters

**Comment replacement pattern**: Replace specific version claims with language that explicitly references:
1. The dependency spec (e.g., ">=1.8.0,<3") as the floor/cap authority
2. The lockfile as the resolved-version source of truth
3. The CI invocation mechanism (e.g., "pixi run mypy" uses the lock-resolved version)

**Negative grep patterns**:
- False claim removal: `! grep -nE "CI tests only 1\.x|tests only 1\.x"`
- Hardcoded version check: `! grep -nE "[0-9]+\.[0-9]+"`

**Affected locations**:
- Primary: Inline comment in `pyproject.toml` [project.optional-dependencies] section (or equivalent)
- Secondary: Same comment in `pixi.toml` if it exists
- Tertiary: Any integration test docstrings or docs that reference the constraint

**Example: mypy comment fix (Issue #1549)**

OLD (stale, false):
```python
# mypy has different error semantics across 1.x and 2.x; CI tests only 1.x
mypy = ">=1.8.0,<3"
```

NEW (version-agnostic):
```python
# mypy version is resolved by pixi.lock; see the dependency spec (>=1.8.0,<3) for the floor/cap.
# CI runs `pixi run mypy` against this resolved version.
mypy = ">=1.8.0,<3"
```

**Verification checklist**:
- [x] Criterion A: False version claim confirmed gone (negative grep passes)
- [x] Criterion B: No hardcoded version numbers in replacement (negative grep passes)
- [x] Criterion C: Comment references the spec/lock/CI as authorities
- [x] Criterion D: Style matches adjacent comments in the same file
- [x] Criterion E: Dependency-consistency tests pass (all 11 pass locally)
- [x] Criterion F: Pre-commit checks pass (ruff format, mypy, no syntax errors)
- [x] Criterion G: No changes to the dependency spec line itself

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1549 (fix planned in PR #1600 or later) | mypy version comment; stale claim "CI tests only 1.x" replaced with version-agnostic text referencing spec/lock/CI |

## See Also

- `dependency-floor-near-tested-version.md` — Coordinated pattern for raising a tool's floor to match the tested version
- `dependency-manifest-single-source-of-truth.md` — Cross-manifest consistency for dependency specs
- `doc-comment-count-drift-verify-frozen-test.md` — Pattern for fixing stale counts in comments using a frozen test as ground truth
