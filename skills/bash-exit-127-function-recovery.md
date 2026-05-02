---
name: bash-exit-127-function-recovery
description: "Diagnose and recover bash shell functions dropped during a merge when a test harness exits with code 127. Use when: (1) a standalone bash test returns exit 127 and all binaries are installed, (2) a sourced shell library was refactored and an old function name was removed or renamed, (3) CI test output shows exit 127 from a raw bash test script rather than from bats."
category: debugging
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [bash, exit-127, shell-function, test-harness, merge-regression, function-recovery, api-retry, jq]
---

# Bash Exit 127: Orphaned Test Harness Function Recovery

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Diagnose exit code 127 from a standalone bash test harness caused by a shell function removed in a prior merge |
| **Outcome** | Successful — all 24 tests in test-api-retry.sh pass after restoring dropped function; 51/51 bats unit tests pass |
| **Verification** | Verified locally only — CI validation pending |
| **Project** | Myrmidons (HomericIntelligence/Myrmidons) |

## When to Use

- A standalone bash test (`bash tests/foo.sh`) exits with code 127
- All required binaries (`yq`, `jq`, `curl`) are confirmed installed — the 127 is not from a missing tool
- A sourced shell library was recently refactored, renamed, or had functions removed in a merge
- CI test harness exits 127 and stdout/stderr contain misleading "Available tasks:" or other noise
- A function in a sourced library was renamed (e.g., `_agamemnon_curl_retry` → `_agamemnon_curl`) and the test still calls the old name

Do NOT use when:
- The 127 originates from a bats test (different diagnostic path — bats wraps calls)
- The required binary is genuinely absent from PATH

## Verified Workflow

### Quick Reference

```bash
# Step 1: Trace exactly where the 127 fires
bash -x tests/foo.sh 2>&1 | head -80

# Step 2: Find when the function last existed
git log --all --oneline --grep='<function-name-stem>'
# e.g. git log --all --oneline --grep='retry'

# Step 3: Inspect the function at that commit
git show <sha>:scripts/lib/api.sh | grep -A 40 '_agamemnon_curl_retry'

# Step 4: Restore function into the library file, wire delegate
# (add the old function body back; make the new name call it)

# Step 5: Verify
bash tests/foo.sh
# or: pixi run test-api-retry
```

### Detailed Steps

1. **Confirm 127 is a missing bash function, not a missing binary**

   Run the test with `-x` tracing:
   ```bash
   bash -x tests/foo.sh 2>&1 | head -100
   ```
   The trace will cut off abruptly at the exact line that fails. Look for a bare function call (e.g., `+ _agamemnon_curl_retry ...`) with no preceding `command not found` for a binary — this pattern confirms a missing bash function, not a missing tool.

2. **Ignore misleading stdout noise**

   If the test runner emits "Available tasks:" or pixi help text in stdout, this is a red herring — it means some tool (e.g., `yq` called without arguments in a weird context) emitted help output. The actual 127 source is elsewhere. Trust `bash -x` trace, not stdout.

3. **Search git history for the function**

   ```bash
   # Find commits mentioning the function name stem
   git log --all --oneline --grep='retry'
   git log --all --oneline -- scripts/lib/api.sh | head -10

   # Inspect the file at a candidate commit
   git show <sha>:scripts/lib/api.sh | grep -n '_agamemnon_curl_retry'

   # Extract the full function body
   git show <sha>:scripts/lib/api.sh | grep -A 50 '^_agamemnon_curl_retry()'
   ```

4. **Restore the dropped function**

   Add the function body back to the library file (e.g., `scripts/lib/api.sh`). If the merge renamed the function rather than deleting its logic, wire the renamed version to delegate to the restored one:

   ```bash
   # Restored original with full retry logic:
   _agamemnon_curl_retry() {
     # ... restored body from git history ...
   }

   # Renamed shim delegates back so both callers work:
   _agamemnon_curl() {
     _agamemnon_curl_retry "$@"
   }
   ```

5. **Fix co-located `jq select` bug (if present)**

   If `agamemnon_status_by_name` or similar uses `select` with a fallback:
   ```bash
   # WRONG — select filters out the row; // "unknown" never fires on empty
   result=$(jq -r '.[] | select(.name == $name) | .status // "unknown"' ...)

   # CORRECT — use first() so the fallback applies when no match
   result=$(jq -r 'first(.[] | select(.name == $name) | .status) // "unknown"' ...)
   # Also add shell-level fallback:
   result="${result:-unknown}"
   ```

6. **Run full test suite to verify**

   ```bash
   bash tests/test-api-retry.sh      # or: pixi run test-api-retry
   # Expected: 24 passed, 0 failed

   bats tests/                        # or: pixi run test
   # Expected: 51/51 tests pass
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reading stderr/stdout from test runner | Examined "Available tasks:" output in stdout to diagnose 127 | Output was pixi help text emitted when `yq` was called without args in a weird path — a red herring, not the 127 source | Trust `bash -x` trace over raw stdout when diagnosing 127 |
| Assuming 127 = missing binary | Checked whether `yq`/`jq`/`curl` were installed | All binaries were present; the 127 came from a missing bash function in a sourced library, not a missing executable | Exit 127 in bash tests has two distinct causes: missing binary vs. missing function — the `-x` trace distinguishes them |
| `jq '.[] \| select(.name == $name) \| .status // "unknown"'` | Used `//` fallback after `select` to return "unknown" when no element matches | `select` filters out the row entirely when no match; the `//` never sees empty string — it sees nothing | Use `first(.[] \| select(...) \| .status) // "unknown"` + shell `${result:-unknown}` fallback |

## Results & Parameters

### Test suite result after fix (Myrmidons)

```
# pixi run test-api-retry
tests/test-api-retry.sh: 24 passed, 0 failed

# pixi run test  (bats)
51 tests, 0 failures
```

### Pattern: Restored function with delegate shim

```bash
# In scripts/lib/api.sh — restored original with retry logic:
_agamemnon_curl_retry() {
  local max_attempts="${AGAMEMNON_MAX_RETRIES:-3}"
  local attempt=1
  local response
  while [ "$attempt" -le "$max_attempts" ]; do
    response=$(curl -sf "$@") && { printf '%s' "$response"; return 0; }
    attempt=$((attempt + 1))
    sleep 1
  done
  return 1
}

# Renamed public function delegates so both old and new callers work:
_agamemnon_curl() {
  _agamemnon_curl_retry "$@"
}
```

### jq select + fallback pattern

```bash
# Correct pattern for "find by name, default to 'unknown'":
result=$(echo "$json" | jq -r --arg name "$name" \
  'first(.[] | select(.name == $name) | .status) // "unknown"')
result="${result:-unknown}"   # shell fallback in case jq returns empty
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Myrmidons | CI debug session — `tests/test-api-retry.sh` returning exit 127 after `_agamemnon_curl_retry` was dropped in merge that renamed it to `_agamemnon_curl` | 24/24 standalone tests + 51/51 bats tests pass after restoration |
