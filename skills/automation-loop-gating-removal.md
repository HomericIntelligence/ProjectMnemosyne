---
name: automation-loop-gating-removal
description: "Patterns for removing defensive gating when upstream bug is fixed. Use when: (1) removing a gate function that guards against an upstream issue, (2) making previously-gated CLI flags optional, (3) cleaning up environment variable injections that are no longer needed, (4) synchronizing shell script invocations with CLI changes."
category: tooling
date: 2026-06-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [automation, loop-runner, argparse, gating, refactoring, cli]
---

# Automation Loop Gating Removal

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Document patterns for safely removing defensive gating and simplifying CLI semantics when upstream bugs are fixed |
| **Outcome** | Successfully removed HEPH_LOOP_INDEX gating and made --issues optional in hephaestus-automation-loop; all CI tests pass |
| **Verification** | verified-ci (PR #820; all automation tests pass in CI) |

## When to Use

- Removing a gate/guard function that shields against a now-fixed upstream bug
- Making a previously-required CLI flag optional (or vice versa)
- Cleaning up environment variable injections tied to a specific lifecycle phase
- Coordinating CLI argument changes across shell scripts and Python consumers
- Refactoring argparse flags from one semantic (required-when-present) to another (optional discovery)

## Verified Workflow

### Quick Reference: Five-Part Refactoring Pattern

**Pattern 1: Argparse Best Practice — nargs="+" + default=[]**
```python
# BEFORE (silently accepts empty --issues list):
parser.add_argument("--issues", nargs="*", default=[])
# Result: --issues (no values) → [] (silent discovery mode, violates AC5)

# AFTER (optional flag with error on no-value):
parser.add_argument("--issues", nargs="+", default=[])
# Result: --issues absent → [] (discovery mode)
#         --issues (no values) → argparse error exit 2
#         --issues N1 N2 ... → [N1, N2, ...]
```

**Pattern 2: Gate Deletion Verification**
```bash
# BEFORE: grep for gate call sites
grep -r "HEPH_LOOP_INDEX" hephaestus/ scripts/ tests/
# Expected: 5 files mention it

# AFTER: delete gate function + all call sites
rm -f gate_definition_line
# Verify deletion is complete:
grep -r "HEPH_LOOP_INDEX" hephaestus/ scripts/ tests/
# Expected: 0 hits (complete removal)
```

**Pattern 3: Test Behavior Update — Delete Old, Assert New**
```python
# BEFORE: test asserts gate behavior (skip when no issues)
def test_process_repo_skips_issue_phases_when_no_issues():
    # Asserts: phases skipped when --issues not provided
    pass

# AFTER: delete old test, add new test
# Test deleted (old behavior no longer exists)
# New test added: verify NO skip occurs (new behavior)
def test_process_repo_no_skip_without_gating():
    # Asserts: phases run even when --issues not provided
    pass
```

**Pattern 4: Environment Variable Cleanup — Code + Docstring**
```python
# BEFORE: env var injected with docstring justifying it
def _phase_env(phase_name):
    """Populate environment with phase-specific variables.

    HEPH_LOOP_INDEX and HEPH_TOTAL_LOOPS are gated to drive-green phase only
    because ci_driver.py skips if HEPH_LOOP_INDEX is not set (issue #689 workaround).
    """
    if phase_name == "drive-green":
        return {"HEPH_LOOP_INDEX": ..., "HEPH_TOTAL_LOOPS": ...}
    return {}

# AFTER: gate removed, injection removed, docstring updated
def _phase_env(phase_name):
    """Populate environment with phase-specific variables."""
    return {}  # No phase-specific env vars (ci_driver gates removed)
```

**Pattern 5: Cross-Script Synchronization**
```bash
# BEFORE: shell script invokes automation loop with --force-run flag
scripts/shell/drive_prs_green_ecosystem.sh:308
    hephaestus-automation-loop --issues ... --force-run

# AFTER: flag removed from Python argparse definition
# Update all shell script invocations
git grep -l "hephaestus-automation-loop" scripts/
# Found: drive_prs_green_ecosystem.sh (2 invocations)
# Edit: remove --force-run from both
sed -i 's/ --force-run//' scripts/shell/drive_prs_green_ecosystem.sh
```

### Detailed Steps

1. **Identify the upstream bug and its gating** — Look for docstrings that reference issue numbers or explain why a gate exists. Example: `ci_driver.py` skips phases if `HEPH_LOOP_INDEX` is unset (issue #689 workaround).

2. **Verify the upstream fix is deployed** — Confirm the issue is resolved in the upstream component before proceeding.

3. **Make argparse changes atomically** — If changing a flag from required to optional (or vice versa):
   - Audit all call sites that pass the flag
   - Update argparse definition with correct `nargs` and `default`
   - Use `nargs="+"` + `default=[]` for optional-when-absent, error-when-present-with-no-value semantics (POLA)
   - Test all three states: absent, present-no-value (error), present-with-values

4. **Delete gate function and ALL call sites** — Use grep to find every reference:
   ```bash
   grep -rn "gate_function_name\|HEPH_LOOP_INDEX" hephaestus/ scripts/ tests/
   ```
   Delete the definition and every call site. Verify with post-deletion grep returning 0 hits.

5. **Update tests for behavior change** — When behavior changes:
   - Delete old tests that assert the OLD behavior
   - Add new tests that assert the NEW behavior
   - Avoid keeping old test with modified assertions (reader confusion; cleaner to delete + replace)

6. **Clean up environment variable injections** — If phases no longer need env vars:
   - Delete the injection code from `_phase_env()` or equivalent
   - Delete the justifying docstring comment
   - Update docstring to reflect new behavior

7. **Sync shell scripts** — Find all invocations of the CLI in shell scripts:
   ```bash
   git grep -l "hephaestus-automation-loop\|<cli-name>"
   ```
   Update all invocations to remove deleted flags.

8. **Run full test suite** — Verify no orphaned references or behavior regressions:
   ```bash
   pixi run pytest tests/unit/automation/ -v
   pixi run pytest tests/integration/ -v
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `nargs="*"` for optional flag | Use `nargs="*"` to accept zero-or-more values | Silently accepts empty list when flag is present with no value (`--issues` → `[]`); violates POLA (AC5: flag changes behavior silently) | Use `nargs="+"` instead; requires ≥1 value, returns argparse error if flag present with no value |
| Keeping old test with modified assertions | Modify existing test to assert new behavior instead of deleting | Reader sees test name implies old behavior but test actually checks new; leads to confusion during maintenance | Delete old test entirely; add new test with name reflecting new behavior |
| Removing injection code but keeping docstring | Delete env var injection from `_phase_env()` but leave the justifying docstring | Stale comment claims behavior that no longer exists; future maintainers trust docstring over code | Delete both injection code AND justifying docstring; update module docstring to reflect current state |
| Manual shell script edits | Manually search and edit drive_prs_green_ecosystem.sh | Easy to miss invocations; if multiple calls exist, some may be missed | Use `git grep` to find all invocations first, then batch-edit with sed or manual review of all found sites |

## Results & Parameters

### Evidence Files from Issue #820

| File | Lines | Change | Purpose |
|------|-------|--------|---------|
| `hephaestus/automation/ci_driver.py` | 2560-2570 | Argparse `--issues` flag: `nargs="+"` + `default=[]` | Make --issues optional with POLA error semantics |
| `hephaestus/automation/loop_runner.py` | 859-867 | Delete `_phase_env()` env var injection + docstring | Remove HEPH_LOOP_INDEX/HEPH_TOTAL_LOOPS gating |
| `scripts/shell/drive_prs_green_ecosystem.sh` | 308, 314 | Remove `--force-run` flag (2 invocations) | Sync shell invocations with removed argparse flag |
| `tests/unit/automation/test_loop_runner.py` | (deleted) | Remove `test_process_repo_skips_issue_phases_when_no_issues()` | Delete test asserting old behavior (skip when no --issues) |
| `tests/unit/automation/test_loop_runner.py` | (added) | Add test: verify phases run when --issues omitted | New test asserts phases always run (gate removed) |

### CI Verification

```
All tests pass:
- tests/unit/automation/ : 42 tests ✓
- tests/integration/automation/ : 12 tests ✓
- Pre-commit hooks (ruff, mypy, yamllint) : ✓
- PR #820 CI gate: ✓
```

### Key Metrics

- **Gate call sites eliminated**: 5 files → 0 hits post-deletion
- **Tests updated**: 1 deleted (old behavior) + 1 added (new behavior)
- **Shell script invocations synced**: 2 sites in `drive_prs_green_ecosystem.sh`
- **Code lines affected**: ~30 LOC net removal (cleaner design)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #820 — Make --issues optional and remove HEPH_LOOP_INDEX gating | PR #820; all automation tests pass in CI; verified-ci level |
