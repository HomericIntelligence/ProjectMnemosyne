---
name: ci-validate-coverage-steps-fallback
description: "Use when: (1) a GitHub Actions CI job has been migrated from a matrix (strategy.matrix.test-group) to sequential named steps and the pre-commit validate-test-coverage hook now reports all test files as uncovered (0 covered groups), (2) validate_test_coverage.py parse_ci_matrix() returns an empty dict after removing strategy.matrix from a workflow, (3) adding support for both matrix-style and sequential-steps-style test group definitions in the same validation script."
category: ci-cd
date: 2026-05-04
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - ci-cd
  - github-actions
  - validate-test-coverage
  - sequential-steps
  - matrix-migration
  - pre-commit
  - parse_ci_matrix
---

# CI Validate Coverage Steps Fallback

> **WARNING**: Verification level is `verified-precommit`. The pre-commit hook passes locally.
> Full CI verification is pending. Treat workflow steps as guidance, not guaranteed-correct.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-04 |
| **Objective** | Fix `validate_test_coverage.py` so it correctly parses test groups from sequential workflow steps after a matrix-to-steps migration |
| **Outcome** | Pre-commit `validate-test-coverage` hook passes after migration; 0 false "uncovered" reports |
| **Verification** | verified-precommit |

## When to Use

- The `pre-commit` hook `validate-test-coverage` reports 200+ uncovered test files that were
  previously covered by a CI matrix
- You just migrated a GHA job from `strategy.matrix.test-group` entries to individual named steps
  each running `just test-group "<path>" "<pattern>"`
- `python3 scripts/validate_test_coverage.py` shows 0 covered groups despite the workflow
  having many `just test-group` steps
- You need `parse_ci_matrix()` to handle both matrix format and sequential-steps format

## Verified Workflow

> Note: Verification level is `verified-precommit` — pre-commit hook passes locally, full CI is pending.

### Quick Reference

```bash
# Diagnose: confirm 0 groups found after migration
python3 scripts/validate_test_coverage.py

# After applying the fix, verify it passes:
python3 scripts/validate_test_coverage.py

# Run the pre-commit hook specifically
pixi run pre-commit run validate-test-coverage --all-files
```

### Detailed Steps

1. **Confirm the symptom** — run `python3 scripts/validate_test_coverage.py` and observe output
   like "253 uncovered test files" or "0 CI test groups found".

2. **Confirm the root cause** — open the workflow file and verify `strategy.matrix` is absent:

   ```bash
   grep -n "strategy\|matrix\|test-group" .github/workflows/comprehensive-tests.yml | head -20
   ```

3. **Locate `parse_ci_matrix()` in `scripts/validate_test_coverage.py`** — find the section
   that loops over `test_job.get("strategy", {}).get("matrix", {}).get("test-group", [])`.

4. **Add the sequential-steps fallback** after the existing matrix loop. Insert this block
   immediately after the `for entry in ...` matrix loop closes but before the `return groups`
   statement:

   ```python
   # In parse_ci_matrix(), after the existing matrix loop:
   if not groups:
       # No matrix — parse sequential steps directly (post-matrix migration format)
       steps = test_job.get("steps", [])
       for step in steps:
           run_cmd = step.get("run", "")
           if "test-group" not in run_cmd:
               continue
           step_name = step.get("name", "unknown")
           # Collapse backslash-newline YAML multi-line continuations.
           # yaml.safe_load() preserves literal "\\\n" in multi-line run: values.
           collapsed = run_cmd.replace("\\\n", " ")
           collapsed = " ".join(line.strip() for line in collapsed.splitlines())
           import re as _re
           m = _re.search(
               r'just\s+test-group\s+"?([^\s"]+)"?\s+"?(.+?)(?:"?\s*$|$)',
               collapsed
           )
           if m:
               path = m.group(1)
               pattern_raw = m.group(2)
           else:
               parts = collapsed.split()
               try:
                   tg_idx = parts.index("test-group")
                   path = parts[tg_idx + 1].strip('"')
                   pattern_raw = " ".join(parts[tg_idx + 2:])
               except (ValueError, IndexError):
                   continue
           # Strip quotes and YAML multi-line backslash artifacts ("\\ " from folding)
           pattern_raw = pattern_raw.replace("\\ ", " ").replace("\\", " ")
           pattern_raw = pattern_raw.strip('"').strip("'").strip()
           key = f"{step_name}::{path}"
           groups[key] = {"path": path, "pattern": pattern_raw}
   ```

5. **Verify the fix**:

   ```bash
   python3 scripts/validate_test_coverage.py
   # Should print 0 uncovered files and exit 0
   ```

6. **Run pre-commit** to confirm the hook passes:

   ```bash
   pixi run pre-commit run validate-test-coverage --all-files
   ```

7. **Commit and create PR** via the standard workflow.

### Key Implementation Details

- **YAML multi-line `run:` values**: After `yaml.safe_load()`, a `run:` block with backslash
  continuations (`\` at end of line) comes through as literal `"\\\n"` (two chars: backslash
  + newline). Must collapse with `.replace("\\\n", " ")`.
- **Residual `\\ "` artifacts**: After collapsing, individual lines may still contain `\\ `
  prefixes from YAML folding. Strip with `.replace("\\ ", " ")`.
- **Group key format**: Use `f"{step_name}::{path}"` to allow multiple steps covering the same
  path (e.g., different test patterns in the same directory).
- **Guard condition `if not groups:`**: Only activate the fallback when the matrix loop found
  nothing. This preserves backward compatibility with matrix-format workflows.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Leaving script unchanged after matrix migration | Migrated GHA job to sequential steps without updating `validate_test_coverage.py` | `parse_ci_matrix()` navigated to `strategy.matrix.test-group` which no longer exists; found 0 groups; reported 253 uncovered files | Always update `validate_test_coverage.py` when changing GHA test job structure |
| Simple string split on `run:` values | Used `run_cmd.split()` to extract `just test-group` args | Multi-line YAML `run:` values contain literal `"\\\n"` after `yaml.safe_load()`; `split()` treated them as single tokens | Must collapse `"\\\n"` continuations before parsing |
| Regex without collapsing first | Applied regex directly to raw `run_cmd` | `"\\\n"` in the middle of the command broke every regex match | Collapse multi-line continuations before applying regex |
| Using step index as group key | `groups[str(i)] = ...` | Opaque keys made debugging impossible; also collided if multiple steps covered the same index conceptually | Use `f"{step_name}::{path}"` for readable, unique keys |

## Results & Parameters

### Expected output after fix

```text
Checking CI test coverage...
Found N CI test groups
All test files are covered by CI
```

`validate_test_coverage.py` exits 0 with no uncovered files reported.

### Files changed

| File | Change |
| ------ | -------- |
| `scripts/validate_test_coverage.py` | Added sequential-steps fallback in `parse_ci_matrix()` |

### Workflow file structure this targets

```yaml
jobs:
  test-mojo-comprehensive:
    steps:
      - name: "Run Core Tests"
        run: |
          just test-group "tests/shared/core" "test_*.mojo"
      - name: "Run Data Tests"
        run: |
          just test-group "tests/shared/data" "test_*.mojo"
```

### Prior matrix structure (now replaced)

```yaml
jobs:
  test-mojo-comprehensive:
    strategy:
      matrix:
        test-group:
          - name: "Core Tests"
            path: "tests/shared/core"
            pattern: "test_*.mojo"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | fix/pixi-env-isolation-signed branch | Pre-commit hook passes after matrix-to-steps migration; CI pending |
