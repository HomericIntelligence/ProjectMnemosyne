---
name: legacy-code-deletion-safe-removal-pattern
description: Safe removal of legacy dead code files marked as fallback/reference-only. Use when a code file claims "kept for reference/fallback only" but has zero real callers across the codebase, leading to stale back-references in production code that create cognitive load during maintenance.
category: tooling
date: 2026-06-04
version: 1.0.0
user-invocable: true
verification: verified-local
tags:
  - legacy-code
  - code-deletion
  - refactoring
  - yagni
  - dead-code
---

# Legacy Code Deletion: Safe Removal Pattern

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-06-04 |
| **Objective** | Safely identify and remove legacy code files marked as fallback/reference-only with zero real callers, then scrub all stale back-references in production code |
| **Outcome** | Successful deletion of 587-line legacy bash automation loop driver + 52-line bash helper + 480 lines of associated tests; 8 stale back-references scrubbed across 4 production files; 1093 unit/integration tests pass + 26 shell tests pass |
| **Verification** | verified-local (all test suites pass, ruff/mypy clean, grep verification confirms zero remaining callers) |

## When to Use This Skill

Use this pattern whenever:

- A code file explicitly states "kept for reference" or "fallback only" in its header comment
- The file has a declared replacement (e.g., "Python version already handles this")
- You suspect the file has zero real callers in production code
- A codebase audit or code review flags the file as dead weight
- Removing the file would reduce cognitive load and maintenance surface area
- Multiple files or comments refer back to the legacy code (stale back-references)

## Root Cause

Legacy fallback code accumulates because:

1. **Explicit retention for "just in case"** — premature defense against hypothetical scenarios (YAGNI anti-pattern)
2. **Forgotten migration** — replacement was built and verified working, but old code lingers "just in case"
3. **Zero caller verification gap** — it's assumed nobody uses it, but never systematically verified via codebase grep
4. **Stale reference accumulation** — production code comments point at the fallback code, creating maintenance overhead and confusion even if nobody calls it
5. **No automated enforcement** — unlike broken imports (which fail CI), dead code passes all checks

## Verified Workflow

### 1. Confirm the Legacy Declaration

Read the file header to confirm explicit fallback/reference language:

```bash
head -20 scripts/run_automation_loop.sh
# Expected: "# This script is kept for reference / fallback only"
# OR: "# Deprecated in favor of hephaestus-automation-loop (Python)"
```

### 2. Identify the Declared Replacement

Locate the production replacement and confirm it is actively maintained and tested:

```bash
# Example: bash driver → Python console script
grep -n "hephaestus-automation-loop\|entry.points" pyproject.toml
grep -n "loop_runner" hephaestus/automation/
# Confirm integration tests exercise the replacement
grep -r "hephaestus-automation-loop\|loop_runner" tests/integration/
```

### 3. Verify Zero Real Callers (Critical Step)

Search the entire codebase for **actual function/script calls** to the legacy code:

```bash
# For a bash script, search for invocations
grep -r "run_automation_loop\.sh" --include="*.py" --include="*.sh" --include="*.md" .
grep -r "./scripts/run_automation_loop" --include="*.py" --include="*.sh" --include="*.md" .
grep -r "bash.*run_automation_loop" --include="*.py" --include="*.sh" --include="*.md" .

# For Python functions, search for imports and calls
grep -r "from legacy_module import\|import legacy_module\|legacy_module\(\)" --include="*.py" .

# Check GitHub workflows, CI files, and scripts
grep -r "run_automation_loop" .github/ scripts/ || echo "No matches"
```

Expected result: **zero matches** (except in the legacy file itself and its test suite).

### 4. Find and List All Stale Back-References

Search for comments that reference the legacy code **without actually calling it**:

```bash
# Example: find comments pointing to the bash script
grep -rn "run_automation_loop\|repo_ordering\.sh" --include="*.py" .
# Expected output: production code comments mentioning the file but not importing/calling it
```

Document the locations:
- `hephaestus/automation/loop_runner.py` — line X comment references bash equivalent
- `hephaestus/github/rate_limit.py` — line Y mentions old script behavior
- etc.

### 5. Rewrite Stale Back-References as Self-Contained Explanations

For each stale reference, replace the back-reference with a self-contained explanation of why the code works the way it does:

**Before:**
```python
# See scripts/run_automation_loop.sh for ordering logic
repo_order = compute_order(repos)
```

**After:**
```python
# Order repos by dependency: pull requests first, then implementation,
# then discovery — ensures dependent issues resolve before dependents.
repo_order = compute_order(repos)
```

This preserves the context without depending on a file you're about to delete.

### 6. Remove the Legacy File and Its Tests

Delete the legacy code file and any tests that exclusively test it:

```bash
rm scripts/run_automation_loop.sh
rm tests/shell/scripts/test_run_automation_loop.bats
rm scripts/shell/lib/repo_ordering.sh  # helper-only code
rm tests/shell/scripts/test_repo_ordering.bats
```

Also update any README or documentation that lists the legacy script:

```bash
# Remove entry from documentation
grep -n "run_automation_loop" docs/ README.md scripts/README.md
# Edit to remove the entry
```

### 7. Run Comprehensive Verification

Execute the full test suite to ensure no hidden dependencies:

```bash
# Run unit tests
pytest tests/unit -v --tb=short

# Run integration tests
pytest tests/integration -v --tb=short

# Run shell tests (if applicable)
./tests/shell/run_all_tests.sh

# Run linting and type checks
ruff check hephaestus/ tests/
mypy hephaestus/

# Confirm grep shows zero references to the deleted code
grep -r "run_automation_loop\|repo_ordering\.sh" --include="*.py" --include="*.sh" . \
  && echo "FAIL: stale references remain" || echo "PASS: no remaining references"
```

Expected: all tests pass, no remaining references, no lint/type errors.

### 8. Commit with Clear Rationale

Use a conventional commit message that explains the deletion:

```bash
git add scripts/run_automation_loop.sh tests/shell/scripts/test_*.bats \
        hephaestus/automation/loop_runner.py hephaestus/github/rate_limit.py \
        hephaestus/automation/planner.py hephaestus/automation/session_naming.py \
        scripts/README.md

git commit -S -m "refactor(scripts): remove legacy run_automation_loop.sh

Delete the legacy bash automation loop driver (587 LoC) and its dead support
infrastructure. The Python replacement (hephaestus-automation-loop) has been
the canonical driver since pyproject.toml:68 and is already verified by
integration tests. The bash script's own header declared it 'kept for
reference / fallback only' — exactly the YAGNI anti-pattern audits flag.

Deletes:
- scripts/run_automation_loop.sh (587 lines)
- scripts/shell/lib/repo_ordering.sh (bash helper)
- tests/shell/scripts/test_run_automation_loop.bats
- tests/shell/scripts/test_repo_ordering.bats

Scrubs stale back-references in production code (8 comments pointing at
the deleted script) across:
- hephaestus/automation/loop_runner.py (6 refs)
- hephaestus/github/rate_limit.py (1 ref)
- hephaestus/automation/planner.py (1 ref)
- hephaestus/automation/session_naming.py (1 ref)

Verification:
- All 1093 unit + integration tests pass
- Remaining bats shell suite (26 tests) passes
- ruff checks clean on all edited Python files
- mypy reports no issues

Closes #745"
```

## Failed Attempts

None. The verification approach (systematically grep all callers, then rewrite back-references, then test) worked cleanly on the first attempt.

## Results & Parameters

### Grep Commands Reference

```bash
# Verify zero callers
grep -r "run_automation_loop\.sh\|run_automation_loop\(\)" --include="*.py" --include="*.sh" --include="*.md" .

# Find back-references (comments only)
grep -rn "run_automation_loop\|repo_ordering" --include="*.py" --include="*.md" hephaestus/

# Verify deletion worked
[ -f scripts/run_automation_loop.sh ] && echo "FAIL: file still exists" || echo "PASS: file deleted"
```

### Verification Checklist

- [ ] Legacy file header explicitly states "reference only" / "fallback only"
- [ ] Replacement code identified and confirmed working (e.g., via integration tests)
- [ ] Grep confirms zero real callers across entire codebase
- [ ] All stale back-references identified and located
- [ ] Back-references rewritten as self-contained explanations (no file dependency)
- [ ] Legacy file deleted
- [ ] Associated test files deleted (tests that exclusively test legacy code)
- [ ] Documentation/README updated to remove legacy file references
- [ ] All unit tests pass (`pytest tests/unit -v`)
- [ ] All integration tests pass (`pytest tests/integration -v`)
- [ ] All shell tests pass (if applicable)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy .`)
- [ ] Final grep confirms zero references to deleted code

### Key Insights

1. **Always verify "fallback" code has zero real callers via grep** — explicit "fallback only" claims are not self-enforcing; the codebase may still depend on it in ways not obvious from reading the header.

2. **Stale comments are cognitive load** — production code comments that point at non-existent files create confusion during maintenance. Rewrite them as self-contained explanations that explain *why* the code works, not *where* to find documentation.

3. **Deletion PRs benefit from comprehensive verification** — showing what breaks and what doesn't (e.g., "1093 tests pass, remaining 26 shell tests pass, zero ruff/mypy issues") helps reviewers understand the blast radius and confidence level.

4. **Test deletion is part of cleanup** — removing unit tests that exclusively test the legacy code is appropriate and reduces maintenance surface. Only keep tests that exercise active code paths.

## Related Skills

- `ci-stale-pattern-cleanup` — for removing stale CI patterns that reference deleted test files
- `fixme-todo-cleanup` — for removing obsolete TODO/FIXME comments
- `mkdocs-nav-cleanup` — for removing deleted file references from documentation
