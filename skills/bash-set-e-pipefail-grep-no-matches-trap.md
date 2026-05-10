---
name: bash-set-e-pipefail-grep-no-matches-trap
description: "Under set -euo pipefail, a grep pipe that finds no matches exits with status 1, aborting the whole script via pipefail+set-e before the while-read loop body is entered. Use when: (1) a script silently exits mid-loop when processing files that don't match a pattern, (2) a pre-commit hook fails on files that are expected NOT to contain a string, (3) grep | while read exits zero iterations but kills the script."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [bash, pipefail, set-euo, grep, while-read, process-substitution, no-matches, pre-commit, pipeline]
---

# Bash set -euo pipefail: grep No-Match Exits Entire Script

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Process lines matching a pattern in each file under strict bash mode without aborting when files have no matches |
| **Outcome** | Success — replaced `grep pattern file | while read` with process substitution + `grep -q` guard |
| **Verification** | verified-ci |

## When to Use

- A bash script with `set -euo pipefail` exits silently mid-loop when iterating over files
- A pre-commit or CI hook reports failure for files that do NOT contain a searched string (logic inversion symptom)
- A `grep ... | while read` pipeline is used and the loop body is never entered for files with zero matches, yet the script also fails
- `grep` is used as a filter step in a pipeline and some inputs are expected to produce no output

## Verified Workflow

### Quick Reference

```bash
# WRONG — exits entire script when grep finds no matches (pipefail sees exit 1):
grep "pattern" "$file" | while read -r line; do
  process "$line"
done

# CORRECT Option A — process substitution with guard (preferred):
if grep -q "pattern" "$file"; then
  while read -r line; do
    process "$line"
  done < <(grep "pattern" "$file")
fi

# CORRECT Option B — suppress pipefail for the specific pipeline:
set +o pipefail
grep "pattern" "$file" | while read -r line; do
  process "$line"
done
set -o pipefail

# CORRECT Option C — append || true (use with caution — swallows all errors):
grep "pattern" "$file" | while read -r line; do
  process "$line"
done || true
```

### Detailed Steps

1. **Identify the symptom**: A script exits before completing a loop. Adding `set -x` trace shows execution stopping at a `grep | while read` line for inputs that have no matches. The script does not enter the loop body, but also does not continue past the pipeline.

2. **Understand why it fails**: Under `set -euo pipefail`:
   - `grep` exits with status 1 when it finds no matches (this is normal and documented behavior).
   - `pipefail` makes the pipeline's exit status equal to the rightmost non-zero exit code.
   - `set -e` sees status 1 from the pipeline and aborts the script immediately.
   - The `while read` loop body is never entered (zero iterations), but the script also does not continue past the pipeline.

3. **Choose a fix pattern**:
   - **Option A (preferred)**: Use `grep -q` to test first, then read from a process substitution. This is explicit, self-documenting, and does not suppress real errors in the loop body.
   - **Option B**: Temporarily disable `pipefail` around the specific pipeline. Restores strict mode immediately after. Safe but verbose.
   - **Option C**: Append `|| true` to the entire pipeline. Simple, but silently swallows ALL non-zero exits from the loop body, not just grep's. Avoid if the loop body can fail in meaningful ways.

4. **Apply Option A**:
   ```bash
   if grep -q "pattern" "$file"; then
     while read -r line; do
       process "$line"
     done < <(grep "pattern" "$file")
   fi
   ```
   Note: `grep` is called twice — once for the existence check, once to feed the loop. This is acceptable; if the file is large, cache results in a temp array instead.

5. **Verify**: Run the script against files that match the pattern and files that do not. Both cases should complete without aborting. The loop body should execute only for matching files.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `grep "pattern" file \| while read line; do` | Direct pipe from grep to while-read | When grep exits 1 (no matches), pipefail propagates non-zero exit, set -e aborts script | Never pipe grep directly into while-read under set -euo pipefail without a guard |
| `|| true` on the whole pipeline | Appended `|| true` after `done` | Works but silently swallows all errors inside the loop body, masking real failures | Use Option A (process substitution) instead; reserve `|| true` only for truly ignorable errors |
| Logic inversion: else branch sets `rc=1` for non-matching files | Checked for string presence and set failure when absent | The abort-on-grep-miss masked the real logic flow; every non-matching file appeared as a failure | The pipefail trap can invert the apparent logic: what looks like a missing-string check actually never runs the false branch — it exits the script instead |

## Results & Parameters

**Root cause:** `grep` exit codes are: 0 = matches found, 1 = no matches, 2 = error. Under `set -e` + `pipefail`, exit code 1 (no matches) is indistinguishable from a real error and aborts the script.

**Companion trap — arithmetic post-increment under `set -e`:**

```bash
(( count++ ))   # If count was 0, the expression evaluates to 0 → set -e aborts
```

Fix:
```bash
(( count++ )) || true   # Safe: || true prevents set -e from seeing the 0 result
# OR
count=$(( count + 1 ))  # Arithmetic expansion never triggers set -e
```

**Option A template for pre-commit hooks checking workflow files:**

```bash
#!/usr/bin/env bash
set -euo pipefail

rc=0
for workflow_file in .github/workflows/*.yml; do
  if grep -q "gitleaks detect" "$workflow_file"; then
    while read -r line; do
      echo "Found in $workflow_file: $line"
    done < <(grep "gitleaks detect" "$workflow_file")
  else
    echo "WARN: $workflow_file does not call gitleaks detect" >&2
    rc=1
  fi
done
exit "$rc"
```

**Verified on:** HomericIntelligence/Myrmidons PR #564 (2026-05-09). `scripts/check-gitleaks-coe.sh` used `grep "gitleaks detect" "$f" | while read line` inside a loop over workflow files. Files that did NOT contain the string caused the entire pre-commit hook to abort via pipefail, masking a logic inversion bug where `else rc=1` was never reached.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Myrmidons | PR #564 check-gitleaks-coe.sh pre-commit hook | `scripts/check-gitleaks-coe.sh` exited on grep no-match before reaching `else rc=1` branch |
