---
name: adr009-audit-issue-creation
description: 'Audit test files for ADR-009 violations and create one GitHub issue
  per violating file. Use when: CI is failing due to Mojo heap corruption linked to
  per-file test count violations, or when an ADR mandates a test limit and you need
  to enumerate all violations as actionable issues.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Goal** | Enumerate all test files exceeding an ADR-mandated per-file test limit and create one GitHub issue per file |
| **Trigger** | CI flaky failures (heap corruption) + `fn test_` count audit reveals 50-150+ violating files |
| **Output** | ~130 GitHub issues (one per file), labelled `bug,testing,ci-cd`, with split proposals and ADR cross-references |
| **Risk** | Duplicate issue waves if creation script is backgrounded — always run synchronously |

## When to Use

- CI on `main` fails 10+/20 runs with random group rotation (load-dependent heap corruption)
- An ADR specifies a per-file `fn test_` limit (e.g. ≤10) and `grep -c "^fn test_"` shows 50+ files over the limit
- You need traceable, actionable issues for every violation before starting any splits

## Verified Workflow

### Step 1: Count violations

```bash
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then
    echo "$count $f"
  fi
done | sort -rn
```

### Step 2: Map files to CI groups

Read `.github/workflows/comprehensive-tests.yml` to extract which CI job runs each file. Record:

- CI group name
- Sample failing run IDs for that group (from CI failure history)

### Step 3: Check for existing issues (avoid duplicates)

```bash
gh issue list --label "ci-cd" --search "ADR-009" --state open --limit 200 --json number,title
```

### Step 4: Write a synchronous batch creation script

```python
import subprocess, math

VIOLATING_FILES = [
    # (file_path, test_count, ci_group, [sample_run_ids])
    ("tests/shared/core/test_matrix.mojo", 64, "Core Tensors", ["22750802815"]),
    # ... ordered by test_count descending
]

def compute_split(test_count):
    """Split into files of ≤8 tests (buffer below 10-test limit)."""
    return math.ceil(test_count / 8)

def create_issue(file_path, test_count, ci_group, run_ids):
    filename = file_path.split("/")[-1]
    num_files = compute_split(test_count)
    title = f"fix(ci): split {filename} ({test_count} tests) — Mojo heap corruption (ADR-009)"
    body = make_issue_body(...)  # see Results & Parameters
    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body,
         "--label", "bug", "--label", "testing", "--label", "ci-cd"],
        capture_output=True, text=True
    )
    issue_url = result.stdout.strip()
    print(f"Created #{issue_url.split('/')[-1]}: {title}")

# Run in explicit index-range batches — NEVER background this loop
for file_path, test_count, ci_group, run_ids in VIOLATING_FILES[0:20]:
    create_issue(file_path, test_count, ci_group, run_ids)
```

**Critical**: Run `python3 script.py --start 0 20`, then `--start 20 55`, etc. Never use
`run_in_background=True` for this loop — 502 errors + early termination cause the script to
re-run from index 0, generating duplicate waves.

### Step 5: Deduplicate if duplicates were created

```bash
gh issue list --label "ci-cd" --search "Mojo heap corruption" --state open \
  --limit 200 --json number,title | python3 -c "
import sys, json
from collections import defaultdict
issues = json.load(sys.stdin)
by_title = defaultdict(list)
for i in issues:
    by_title[i['title']].append(i['number'])
to_close = []
for title, nums in by_title.items():
    if len(nums) > 1:
        for n in sorted(nums)[1:]:
            to_close.append(n)
print(' '.join(str(n) for n in to_close))
"
# Then close them:
for num in <ids>; do gh issue close "$num" --comment "Duplicate."; done
```

### Step 6: Create wildcard overlap issue (if applicable)

If CI groups use wildcards that overlap with dedicated sub-groups, create one additional issue
documenting the overlap and recommending explicit file enumeration.

### Step 7: Post summary to tracking issue

```bash
gh issue comment <tracking-issue-number> --body "$(cat <<'EOF'
## ADR-009 Audit Complete
- 132 issues created (#3396–#3640)
- Batch 1 Critical (40+ tests): #3396–#3404
...
EOF
)"
```

## Issue Body Template

```markdown
## Problem

`{file_path}` contains **{test_count} `fn test_` functions**, exceeding the ADR-009 limit of 10 per file.

This causes intermittent heap corruption crashes in Mojo v0.26.1 (`libKGENCompilerRTShared.so`
JIT fault), making the **{ci_group}** CI group non-deterministically fail.

## Evidence

- **File**: `{file_path}`
- **Test count**: {test_count} (limit: 10, target after split: ≤8)
- **CI Group**: `{ci_group}`
- **Sample failing run IDs**: {run_ids}
- **CI failure rate**: 13/20 recent runs on `main`

Related: #2942, ADR-009 (`docs/adr/ADR-009-heap-corruption-workaround.md`)

## Fix

Split `{file_path}` into **{num_files} files** of ≤8 tests each:
  - `test_{base}_part1.mojo` (~8 tests)
  - `test_{base}_part2.mojo` (~8 tests)
  ...

Each split file must include the ADR-009 header comment:
```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
```

## Acceptance Criteria

- [ ] Original file replaced by {num_files} files, each with ≤8 `fn test_` functions
- [ ] All original test cases preserved
- [ ] Each new file has the ADR-009 header comment
- [ ] CI workflow updated to reference the new filenames
- [ ] CI group passes reliably
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Background batch script | Used `run_in_background=True` for the 60-file batch | 502 GitHub API errors caused early exit; the task system then re-ran from index 0, creating 3 duplicate waves (41 + 64 + 8 duplicates) | Never background a sequential issue-creation loop — run synchronously with explicit `--start N M` index ranges |
| Single large batch | Ran all 115 files in one `--start 0 115` call | Same problem: 502 error mid-run → background re-execution from 0 | Break into batches of ≤20 and run each synchronously |
| Retry via inline Python | Used inline `python3 -c "exec(open(...)...)"` to retry single failures | Works fine for individual retries but obscures which issues were created | Use the script with `--start` args for all batch work |
| Checking background output files | Tried `strings` and `grep` on persisted task output (54KB HTML-heavy) | GitHub 502 HTML bodies polluted the output making grep/strings useless | After any background run, use `gh issue list` to authoritatively check what was created |

## Results & Parameters

### Final counts (2026-03-06, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Files audited | ~650 test files |
| Files violating ADR-009 (>10 tests) | 131 |
| Issues created | 131 file-split + 1 wildcard overlap = **132** |
| Duplicates created (and closed) | 105 |
| Labels applied | `bug`, `testing`, `ci-cd` |
| Issue numbers | #3396–#3640 |
| Tracking issue updated | #3330 |

### Script parameters

```python
LIMIT = 10          # ADR-009 max fn test_ per file
TARGET = 8          # split target (buffer below limit)
BATCH_SIZE = 20     # max files per synchronous run
LABELS = ["bug", "testing", "ci-cd"]
```

### Deduplication command (reusable)

```bash
gh issue list --label "ci-cd" --search "Mojo heap corruption" \
  --state open --limit 200 --json number,title | python3 -c "
import sys, json
from collections import defaultdict
issues = json.load(sys.stdin)
by_title = defaultdict(list)
for i in issues:
    by_title[i['title']].append(i['number'])
to_close = []
for title, nums in sorted(by_title.items()):
    if len(nums) > 1:
        keep = sorted(nums)[0]
        for n in sorted(nums)[1:]:
            to_close.append(n)
            print(f'Close #{n} (keep #{keep}): {title[:60]}')
print('Close IDs:', ' '.join(str(n) for n in to_close))
"
```
