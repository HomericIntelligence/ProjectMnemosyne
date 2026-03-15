---
name: experiment-analysis-script-patterns
description: "Patterns for fixing experiment analysis scripts: directory regex matching, run multiplier correctness, exit code semantics, and retry shell script error handling. Use when: analysis script discovers 0 experiments, run totals are wrong, or retry scripts abort on first failure."
category: evaluation
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| Category | evaluation |
| Complexity | Low |
| Context | Post-experiment analysis of dryrun result directories |
| Key Files | `scripts/analyze_dryrun3.py`, `retry_dryrun3.sh` |

## When to Use

- Analysis script discovers 0 or fewer experiments than expected
- Run count totals (expected/missing) are off by a fixed multiplier
- Retry shell script aborts the whole suite when one test fails
- Go/NoGo exit code not propagating to calling script or CI

## Verified Workflow

### Quick Reference

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| 0 experiments discovered | Regex doesn't match actual dir names | Loosen timestamp pattern: `T\d{6}` → `T[\d-]+` |
| Wrong expected/missing counts | Multiplied by 3 (assumed 3 runs/subtest) | Change multiplier to 1 |
| Retry script aborts on failure | `set -e` exits on first non-zero | Remove `set -e`; capture failures explicitly |
| No exit code from analysis | `generate_report()` returns None | Return `(verdict, reasons)`, `sys.exit(1)` on NOGO |

### Step 1 — Diagnose the regex

Run the discovery function against a known directory to see if it matches:

```python
import re, pathlib
pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{6})-(\w+)-(test-\d{3})$")  # OLD
results_dir = pathlib.Path("~/dryrun3").expanduser()
matches = [d.name for d in results_dir.iterdir() if pattern.match(d.name)]
print(f"Matched: {len(matches)} of {sum(1 for d in results_dir.iterdir() if d.is_dir())}")
```

If matched count is 0 but dirs exist, the regex is wrong. Inspect actual dir names:

```bash
ls ~/dryrun3 | head -5
# e.g.: 2026-02-23T18-56-10-test-017
#       ^timestamp with dashes^ ^test^
```

The dashes in the seconds component (`T18-56-10`) break `T\d{6}` (which expects 6 contiguous digits).

### Step 2 — Fix the regex

```python
# WRONG: T\d{6} requires exactly 6 contiguous digits after T
pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{6})-(\w+)-(test-\d{3})$")

# CORRECT: T[\d-]+ matches any digit/dash sequence (handles dashes in HH-MM-SS)
pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T[\d-]+)-(test-\d{3})$")
```

Also update group references: test name is now group 2 (not group 3, since the intermediate `(\w+)` capture was removed).

### Step 3 — Fix the run multiplier

Confirm runs-per-subtest before hardcoding:

```bash
# Count run_NNN dirs under a known subtest
ls ~/dryrun3/2026-*/T0/00/ | grep "^run_" | wc -l
```

If it's 1 (not 3), update every `* 3` in the analysis script:

```python
# WRONG
expected_runs = TOTAL_SUBTESTS_FULL * 3
total_missing_runs += (expected - actual) * 3

# CORRECT (1 run per subtest)
expected_runs = TOTAL_SUBTESTS_FULL
total_missing_runs += expected - actual
```

### Step 4 — Add exit code semantics

Make `generate_report()` return `(verdict, reasons)` and have `main()` use it:

```python
def generate_report(all_results: list[dict]) -> tuple[str, list[str]]:
    ...
    verdict, reasons = go_nogo(all_results)
    # ... print report ...
    return verdict, reasons  # ADD THIS


def main() -> None:
    ...
    verdict, reasons = generate_report(all_results)
    if verdict == "NOGO":
        sys.exit(1)
    sys.exit(0)  # GO or CONDITIONAL_GO
```

### Step 5 — Fix shell retry script

Replace `set -e` with per-test error capture:

```bash
# WRONG: set -e aborts entire script on first non-zero exit
set -euo pipefail

# CORRECT: track failures without aborting
set -uo pipefail
FAILED_TESTS=()

for test in "${ALL_TESTS[@]}"; do
    if ! pixi run python scripts/manage_experiment.py run \
        --config "tests/fixtures/tests/$test" \
        --results-dir "$RESULTS_DIR" \
        -v; then
        FAILED_TESTS+=("$test")
        echo "WARNING: $test exited with non-zero status"
    fi
done

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo "=== TESTS WITH ERRORS: ${FAILED_TESTS[*]} ==="
fi
```

### Step 6 — Add pre/post-run analysis

Wrap the retry loop with analysis calls so you get Go/NoGo before and after:

```bash
echo "=== PRE-RUN STATUS ==="
pixi run python scripts/analyze_dryrun3.py --results-dir "$RESULTS_DIR" || true

# ... run all tests ...

echo "=== POST-RUN STATUS ==="
pixi run python scripts/analyze_dryrun3.py --results-dir "$RESULTS_DIR"
# exit code propagates: 0=GO, 1=NOGO
```

Use `|| true` on the pre-run call so a NOGO state before retries doesn't abort the script.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original regex `T\d{6}` | Expected timestamp format `T185610` (6 contiguous digits) | Actual dirs use `T18-56-10` (dashes between HH, MM, SS) | Always inspect actual dir names before writing regex — shell `ls \| head` is faster than assuming |
| Group 3 for test name | Regex had 3 groups; test name was group 3 | After removing the intermediate `(\w+)` group, test name dropped to group 2 | Group indices shift when you remove captures — update all `.group(N)` calls together |
| `* 3` multiplier | Assumed 3 runs per subtest (standard dryrun config) | dryrun3 was configured with 1 run per subtest | Read the actual artifact count before coding the multiplier; don't assume from docs |
| `set -e` in retry loop | Used `set -euo pipefail` for safety | Any single test failure (including infrastructure errors) aborted the entire 47-test suite | `set -e` is incompatible with "retry all failures" workflows; use explicit error capture instead |

## Results & Parameters

### Regex Pattern

```python
# For dirs named: YYYY-MM-DDTHH-MM-SS-test-NNN
pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T[\d-]+)-(test-\d{3})$")
# group(1) = timestamp, group(2) = test-NNN
```

### Shell Script Template

```bash
#!/usr/bin/env bash
set -uo pipefail

RESULTS_DIR=~/dryrun3
FAILED_TESTS=()

# Pre-run analysis (|| true so NOGO doesn't abort)
pixi run python scripts/analyze_dryrun3.py --results-dir "$RESULTS_DIR" || true

for test in "${ALL_TESTS[@]}"; do
    if ! pixi run python scripts/manage_experiment.py run \
        --config "tests/fixtures/tests/$test" \
        --results-dir "$RESULTS_DIR" \
        --threads 2 --parallel 1 -v; then
        FAILED_TESTS+=("$test")
        echo "WARNING: $test exited with non-zero status"
    fi
done

[ ${#FAILED_TESTS[@]} -gt 0 ] && echo "ERRORS: ${FAILED_TESTS[*]}"

# Post-run analysis — exit code propagates to caller
pixi run python scripts/analyze_dryrun3.py --results-dir "$RESULTS_DIR"
```

### Exit Code Convention

| Verdict | Exit Code | Meaning |
|---------|-----------|---------|
| GO | 0 | All criteria met, paper-ready |
| CONDITIONAL_GO | 0 | Minor warnings, proceed with caution |
| NOGO | 1 | Missing data or incomplete runs, don't write paper yet |
