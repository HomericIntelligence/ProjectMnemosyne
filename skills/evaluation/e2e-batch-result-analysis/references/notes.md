# Reference Notes: e2e-batch-result-analysis

## Session Context

**Date**: 2026-02-19
**Repository**: ProjectScylla
**Task**: Analyze 47-test E2E dry run results from 2026-02-14 and generate analysis files + issue filing script

## Batch Run Details

```
Model: haiku (claude-haiku)
Judge: haiku
Runs per sub-test: 1
Max sub-tests: 3
Thinking: None
Tiers: T0 only
Threads: 2
Wall time: ~4.5 hours
Results: /home/mvillmow/dryrun/
```

## Key File Paths (ProjectScylla)

```
/home/mvillmow/dryrun/batch_summary.json         # All 47 test results
/home/mvillmow/dryrun/thread_logs/thread_0.log   # Thread 0 execution log (2,186 lines)
/home/mvillmow/dryrun/thread_logs/thread_1.log   # Thread 1 execution log (4,108 lines)
/home/mvillmow/dryrun/{timestamp}-{test_id}/     # Per-test result directories (47)
/home/mvillmow/dryrun/analysis/                  # Generated analysis output
```

## Framework Bug: criteria_scores=None

### Error Signature

```
2026-02-14 06:01:53 [ERROR] scylla.e2e.parallel_executor: Worker exception for T0/02:
ValidationError: 1 validation error for RunResult
criteria_scores

pydantic_core._pydantic_core.ValidationError: 1 validation error for RunResult
criteria_scores
  Input should be a valid dictionary [type=dict_type, input_value=None, input_url=...]

Traceback (most recent call last):
  ...
  criteria_scores=judgment.get("criteria_scores", {}),
```

**Location**: `scylla/e2e/subtest_executor.py` (line ~761)

### Why `.get("criteria_scores", {})` Returns None

```python
d = {"criteria_scores": None}
d.get("criteria_scores", {})  # Returns None, not {}
# Because the key EXISTS, just has value None
# The default is only used when key is MISSING

# Fix:
d.get("criteria_scores") or {}  # Returns {} when value is None or falsy
```

### Secondary Error

```
ValueError: Judge response missing required 'score' field.
Keys found: ['type', 'subtype', 'is_error', 'result']
```

This occurs when the judge LLM returns an API error envelope. The code must check `is_error`
before accessing `score`. See `e2e-judge-rubric-design` skill for the correct pattern.

## Batch Run Timeline (Thread 1)

Three distinct sessions visible in thread_1.log:

| Session | Approx Time | Behavior |
|---------|-------------|---------|
| Session 1 | ~00:28 UTC | Real runs with costs ($0.6–$3.9), real results |
| Session 2 | ~11:16 UTC | All exit code -1, 0s — `pixi` not on PATH |
| Session 3 | ~13:59 UTC | 12 tests: $0 cost, 8-22s — ValidationError on resume; rest ran normally |

## True First-Run Results (from thread_1.log Session 1)

| Test | Session 1 Result | batch_summary Result |
|------|-----------------|---------------------|
| test-031 | PASS ($0.61) | FAIL ($0.00) — overwritten by bug |
| test-036 | PASS ($0.77) | FAIL ($0.00) — overwritten by bug |
| test-012 | PASS ($3.93) | FAIL ($0.00) — overwritten by bug |
| test-016 | PASS ($2.33) | FAIL ($0.00) — overwritten by bug |
| test-047 | PASS ($1.56) | FAIL ($0.00) — overwritten by bug |
| test-002 | PASS (0.940, $0.90) | FAIL ($0.00) — overwritten by bug |
| test-007 | FAIL ($2.22) | FAIL ($0.00) — both sessions failed |
| test-021 | FAIL ($0.73) | FAIL ($0.00) — both sessions failed |
| test-026 | FAIL ($2.36) | FAIL ($0.00) — both sessions failed |
| test-040 | FAIL ($3.36) | FAIL ($0.00) — both sessions failed |
| test-042 | FAIL ($1.50) | FAIL ($0.00) — both sessions failed |
| test-010 | FAIL ($2.06) | FAIL ($0.00) — both sessions failed |
| test-030 | FAIL ($1.76) | FAIL ($0.00) — both sessions failed |

## Actual Results Summary (corrected)

After accounting for framework bugs:
- True first-run passes: 24 (batch_summary) + 6 (hidden by bug) = **30/47 = 63.8%**
- True first-run failures: 17/47 = **36.2%**

The 13 framework bug failures should be re-run with `--fresh` before drawing conclusions.

## Output Files Generated

```
/home/mvillmow/dryrun/analysis/
├── README.md              (master summary, 47-row table)
├── analysis.md            (full analysis with recommendations)
├── failures/
│   ├── summary.md         (categorized failure breakdown)
│   ├── test-002.md        (framework bug, first-run PASS)
│   ├── test-006.md        (model failure, Mojo build errors)
│   ├── test-007.md        (framework bug, first-run FAIL)
│   ├── test-010.md        (framework bug, first-run FAIL)
│   ├── test-012.md        (framework bug, first-run PASS)
│   ├── test-014.md        (model failure, code deletion)
│   ├── test-016.md        (framework bug, first-run PASS)
│   ├── test-017.md        (model failure, Mojo slot mgmt)
│   ├── test-020.md        (model failure, dataset loaders)
│   ├── test-021.md        (framework bug, first-run FAIL)
│   ├── test-023.md        (model failure, unused vars)
│   ├── test-025.md        (model failure, FIXME/TODO)
│   ├── test-026.md        (framework bug, first-run FAIL)
│   ├── test-028.md        (model failure, tensor ops)
│   ├── test-029.md        (model failure, stride lists)
│   ├── test-030.md        (framework bug, first-run FAIL)
│   ├── test-031.md        (framework bug, first-run PASS)
│   ├── test-032.md        (model failure, Float64)
│   ├── test-036.md        (framework bug, first-run PASS)
│   ├── test-038.md        (model failure, eye() test)
│   ├── test-040.md        (framework bug, first-run FAIL)
│   ├── test-042.md        (framework bug, first-run FAIL)
│   └── test-047.md        (framework bug, first-run PASS)
├── issues/
│   ├── epic.md            (epic issue body)
│   └── test-001.md        (through test-047.md, 47 files)
└── file_issues.sh         (shell script, syntax-checked OK)
```

## Python Pattern for Bulk File Writing

```python
import json, os

with open('<results-dir>/batch_summary.json') as f:
    data = json.load(f)

results = sorted(data['results'], key=lambda r: r['test_id'])
output_dir = '<results-dir>/analysis/issues'
os.makedirs(output_dir, exist_ok=True)

framework_bugs = {
    'test-002', 'test-007', 'test-010', 'test-012', 'test-016',
    'test-021', 'test-026', 'test-030', 'test-031', 'test-036',
    'test-040', 'test-042', 'test-047'
}

for r in results:
    test_id = r['test_id']
    status = r['status'].upper()
    is_framework_bug = test_id in framework_bugs
    is_model_fail = status == 'FAIL' and not is_framework_bug

    # First line must be the issue title for file_issues.sh
    title = f'[E2E] {test_id}: {r["test_name"]} - {status}'
    content = f'# {title}\n\n...'

    with open(f'{output_dir}/{test_id}.md', 'w') as f:
        f.write(content)
```

## Issue Identification Pattern (from file_issues.sh)

```bash
# Extract issue title from first line of each issue file:
title=$(head -1 "$issue_file" | sed 's/^# //')

# Extract issue number from gh issue create URL output:
url=$(gh issue create --title "$title" --body-file "$issue_file" --label "evaluation")
num="${url##*/}"   # strips everything up to last /
```
