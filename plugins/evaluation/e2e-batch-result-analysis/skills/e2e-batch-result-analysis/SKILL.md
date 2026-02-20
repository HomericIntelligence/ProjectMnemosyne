---
name: e2e-batch-result-analysis
description: "Analyze E2E batch dry run results: triage failures, write local analysis files, generate GitHub issue filing script"
category: evaluation
date: 2026-02-19
user-invocable: false
---

# E2E Batch Result Analysis

Analyze a completed E2E batch run: categorize failures, write structured analysis files locally, and
generate a shell script to file all GitHub issues at once (rather than filing issues directly).

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-02-19 | Analyze 47-test dry run (Haiku/T0), write analysis files, generate issue script | All files written under `<results-dir>/analysis/`, `file_issues.sh` syntax-checks clean |

## When to Use

- (1) A batch E2E run has completed and `batch_summary.json` exists
- (2) You need to triage which failures are framework bugs vs model limitations
- (3) You want analysis written to local files before deciding whether to file GitHub issues
- (4) You need a reviewable shell script instead of direct issue creation (better for large batches)
- (5) Thread logs need to be cross-referenced to understand resume/checkpoint failures

## Verified Workflow

### 1. Read Data Sources in Parallel

Read `batch_summary.json` for structured results AND thread logs for error patterns simultaneously:

```bash
# Structured results (47 tests)
cat <results-dir>/batch_summary.json

# Error patterns in logs
grep -n "ValidationError\|criteria_scores\|is_error\|Error\|Exception" \
  <results-dir>/thread_logs/thread_0.log | head -100

grep -n "ValidationError\|criteria_scores\|is_error\|Error\|Exception" \
  <results-dir>/thread_logs/thread_1.log | head -100

# First-run vs re-run: find EXPERIMENT COMPLETE blocks
grep -A5 "EXPERIMENT COMPLETE" <results-dir>/thread_logs/thread_0.log | head -200
grep -A5 "EXPERIMENT COMPLETE" <results-dir>/thread_logs/thread_1.log | head -200
```

**Critical**: Thread logs contain multiple run sessions. Look for cost patterns:
- `$0.0000` cost + `8-22s` duration = framework failure (zero API calls)
- `$0.0000` cost + `100-200s` duration = framework failure after partial setup (e.g., repo clone)
- Non-zero cost + score 0.0 = model failure

### 2. Categorize Failures

Two distinct categories require different handling:

**Category 1: Framework Bugs (Zero-Cost)**
- All 3 sub-tests fail simultaneously
- Zero tokens consumed
- Duration 8-22s (or longer if repo clone happened first)
- Error: `pydantic_core._pydantic_core.ValidationError: 1 validation error for RunResult`
- Root cause: `criteria_scores=None` in checkpoint data; `judgment.get("criteria_scores", {})` returns `None` when key exists but is null

**Category 2: Model Failures (Non-Zero Cost)**
- Model ran, consumed tokens and budget
- Score 0.0 on all sub-tests
- Check rubric to understand what was required

**Key lookup**: Cross-reference `batch_summary.json` `total_cost` field:
- `total_cost == 0.0` AND `status == "fail"` → Framework Bug (re-run needed)
- `total_cost > 0.0` AND `status == "fail"` → Model Failure (harder problem)

### 3. Cross-Reference Thread Logs for First-Run Results

When batch was re-run (e.g., after pixi path fix), `batch_summary.json` reflects the **latest** run.
Thread logs contain ALL run sessions. Extract first-run results:

```bash
# Find all EXPERIMENT COMPLETE blocks with costs
grep -E "Starting test-|Completed test-|EXPERIMENT COMPLETE|No passing results|Best Tier|Total Cost" \
  <results-dir>/thread_logs/thread_1.log
```

Look for patterns:
- Session 1 (~00:28 UTC): Real costs, real results
- Session 2 (~11:16 UTC): All exit code -1, no costs (e.g., `pixi` not on PATH)
- Session 3 (~13:59 UTC): Zero-cost failures = ValidationError on resume

This reveals tests that **passed** in Session 1 but show as FAIL in `batch_summary.json`.

### 4. Create Output Directory Structure

```bash
mkdir -p <results-dir>/analysis/failures
mkdir -p <results-dir>/analysis/issues
```

### 5. Write Analysis Files Using Python for Bulk Generation

Use Python to generate the 47+ issue files from `batch_summary.json` programmatically:

```python
import json, os

with open('<results-dir>/batch_summary.json') as f:
    data = json.load(f)

results = sorted(data['results'], key=lambda r: r['test_id'])
output_dir = '<results-dir>/analysis/issues'

for r in results:
    test_id = r['test_id']
    name = r['test_name']
    status = r['status'].upper()
    is_framework_bug = r['total_cost'] == 0.0 and status == 'FAIL'

    title = f'[E2E] {test_id}: {name} - {status}'
    content = f'# {title}\n\n...'  # Build full issue body

    with open(f'{output_dir}/{test_id}.md', 'w') as f:
        f.write(content)
```

**Critical**: The first line of each issue file should be `# <issue title>` so `file_issues.sh` can
extract it with `head -1 | sed 's/^# //'`.

### 6. Write `file_issues.sh`

The script should:
1. Accept `--dry-run` flag for safe testing
2. Create any missing labels first
3. Create epic issue, capture number from URL
4. Loop through all test issue files, create each, capture number
5. Post a comment on the epic linking all per-test issues
6. Post a final analysis comment on the epic

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISSUES_DIR="$SCRIPT_DIR/issues"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Extract URL -> issue number
url_to_num() { echo "${1##*/}"; }

# Create epic
EPIC_URL=$(gh issue create \
  --title "E2E Dry Run: All N Tests (Model/Tier, Date)" \
  --body-file "$ISSUES_DIR/epic.md" \
  --label "evaluation")
EPIC_NUM=$(url_to_num "$EPIC_URL")
sleep 1

# Create per-test issues
declare -A ISSUE_MAP
for issue_file in "$ISSUES_DIR"/test-*.md; do
  test_id=$(basename "$issue_file" .md)
  title=$(head -1 "$issue_file" | sed 's/^# //')
  url=$(gh issue create --title "$title" --body-file "$issue_file" --label "evaluation")
  ISSUE_MAP["$test_id"]=$(url_to_num "$url")
  sleep 1
done
```

### 7. Syntax-Check the Script

```bash
bash -n <results-dir>/analysis/file_issues.sh && echo "OK"
```

### 8. Dry-Run Before Filing

```bash
bash <results-dir>/analysis/file_issues.sh --dry-run
```

Verify the output shows correct titles and file paths before running for real.

## Results & Parameters

### Output Directory Structure

```
<results-dir>/analysis/
├── README.md                    # Master summary: config table, aggregate stats, full results table
├── analysis.md                  # Full analysis: costs, durations, failure categories, recommendations
├── failures/
│   ├── summary.md               # Failure categorization with tables
│   └── <test_id>.md × N        # Per-failure root cause (one per failure)
├── issues/
│   ├── epic.md                  # Epic issue body (markdown)
│   └── <test_id>.md × N        # Per-test issue bodies (title = first line)
└── file_issues.sh               # Shell script to file all issues
```

### Key Metrics to Include in README.md

```markdown
| Metric | Value |
|--------|-------|
| Total Tests | 47 |
| Passed | 24 (51.1%) |
| Failed | 23 (48.9%) |
| Total Cost (all) | $54.18 |
| Total Cost (passes) | $35.46 |
| Mean CoP | $0.37 |
| Median CoP | $0.17 |
```

### Failure Root Cause Template

```markdown
## Root Cause
Framework bug: When resuming from checkpoint, `criteria_scores=None` in stored judge results
causes a Pydantic `ValidationError` in `RunResult` construction.

**Error**:
pydantic_core._pydantic_core.ValidationError: 1 validation error for RunResult
criteria_scores
  Input should be a valid dictionary [type=dict_type, input_value=None]

**Fix**:
# Change:
criteria_scores=judgment.get("criteria_scores", {}),
# To:
criteria_scores=judgment.get("criteria_scores") or {},
```

### Cost-of-Pass Formula

```
frontier_cop = total_cost / 1   (when 1 run, 1 pass)
```

When `best_score < 1.0`, the test partially passed. A score of 0.667 means 2/3 sub-tests passed.

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Using bash `cat <<'EOF'` heredoc for issue file content | Bash heredocs with nested code blocks cause EOF delimiter conflicts; tool permission issues with `cat > file` | Use Python `open(path, 'w')` for bulk file writing |
| Spawning a Bash subagent to write multiple files | Subagent had write permission denied for some files; inconsistent permissions across tool calls | Write files directly from main agent using the Write tool or Python |
| Using `judgment.get("criteria_scores", {})` default | When `criteria_scores` key exists but value is `None`, `.get()` returns `None` not `{}` | Use `judgment.get("criteria_scores") or {}` instead |
| Reading batch_summary.json with an Explore subagent | Returned summarized data, lost exact numeric values needed for tables | Use Bash agent with `cat` or Read tool to get raw JSON |
| Trusting batch_summary.json as ground truth for all failures | Re-runs overwrote first-run results; 5 tests showed FAIL but had PASS in first run | Always cross-reference thread logs for multi-session batches |
| Trying to write failure files via Bash heredoc with backtick code blocks | Markdown code blocks inside heredocs break EOF detection | Write via Python or the Write tool, not bash heredoc |
| `bash -n` syntax check in wrong directory | Script uses relative paths; syntax check passes but runtime would fail | Run `bash -n` from the script's own directory |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | 47-test dry run, Haiku/T0, 2026-02-14 | [notes.md](../references/notes.md) |

## Related Skills

- `bulk-issue-filing` — Pattern for batch `gh issue create` with rate limiting
- `e2e-framework-bug-fixes` — Fixing `criteria_scores` and other E2E framework bugs
- `experiment-recovery-tools` — Re-running failed/incomplete agents and judges
- `checkpoint-result-validation` — Validating checkpoint data before resuming
