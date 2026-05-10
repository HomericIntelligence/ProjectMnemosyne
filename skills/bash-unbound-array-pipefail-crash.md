---
name: bash-unbound-array-pipefail-crash
description: "Bash arrays not initialized before use crash with 'unbound variable' under
  set -euo pipefail. Use when: (1) a script dies silently at an array length check
  (${#ARRAY[@]}), (2) bash -u causes a crash on an array declared but never assigned,
  (3) a function crashes on first failed-agent tracking despite apparent initialization."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [bash, array, pipefail, set-euo, unbound-variable, local-a, initialization]
---

# Bash Unbound Array Crash Under set -euo pipefail

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Prevent bash script crash when tracking failed agents in an array |
| **Outcome** | Success — used `local -a ARRAY=()` at function start; script ran correctly |
| **Verification** | verified-ci |

## When to Use

- A bash function crashes silently or with "unbound variable" at a line using `${#ARRAY[@]}` or `${ARRAY[@]}`
- An array is conditionally populated (e.g., only when failures occur) but may never be assigned before being read
- A script uses `set -euo pipefail` (strict mode) and an array that "should be initialized" is not
- A function uses `declare -a` or `local -a` without `=()` and later crashes on first index access

## Verified Workflow

### Quick Reference

```bash
# WRONG — array declared but not initialized; crashes under set -euo pipefail:
my_function() {
  local -a FAILED_AGENT_NAMES
  # ... some conditional logic that may or may not populate the array ...
  echo "Failed: ${#FAILED_AGENT_NAMES[@]}"  # crashes here: unbound variable
}

# CORRECT — initialize empty array at declaration:
my_function() {
  local -a FAILED_AGENT_NAMES=()
  # ... conditional logic ...
  echo "Failed: ${#FAILED_AGENT_NAMES[@]}"  # safe: returns 0 if empty
}
```

### Detailed Steps

1. **Identify the crash point**: Run the script with `bash -x` to trace execution. Look for the last line before the crash — it will be an array reference like `${#ARRAY[@]}` or `${ARRAY[0]}`.

2. **Check the declaration**: Find where the array is declared. If it uses `declare -a ARRAY` or `local -a ARRAY` without `=()`, it is declared but not initialized.

3. **Understand why this crashes**: Under `set -u`, bash treats an uninitialized array as an unbound variable. Even `local -a ARRAY` without `=()` leaves the array in an "unset" state — `bash -u` considers it unbound when first indexed.

4. **Fix**: Add `=()` to the declaration:
   ```bash
   local -a FAILED_AGENT_NAMES=()
   ```
   Or for global scope:
   ```bash
   declare -a FAILED_AGENT_NAMES=()
   ```

5. **Verify**: Re-run with `set -euo pipefail` active. The array length check `${#FAILED_AGENT_NAMES[@]}` should return `0` on the first call instead of crashing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `local -a FAILED_AGENT_NAMES` (no `=()`) | Declared array without initializing | Under `set -u`, `bash` treats an unassigned array as unbound on first access | Always use `=()` when declaring arrays; declaration alone is not initialization |
| Guarding with `[[ -v ARRAY ]]` check | Used `[[ -v FAILED_AGENT_NAMES ]]` before access | Verbose and easy to miss in new code paths; doesn't fix the root cause | Initialize at declaration instead of guarding every access site |

## Results & Parameters

**Root cause:** In bash, `local -a ARRAY` and `declare -a ARRAY` *declare* the variable as an array type but leave it in an unset state. Under `set -u` (nounset), reading an unset variable — including `${#ARRAY[@]}` — triggers "unbound variable" and causes `set -e` to exit the script immediately.

**The fix is one character:** `=()` on the declaration line.

```bash
# Pattern to use in all functions that track lists of failures/successes:
my_function() {
  local -a FAILED_AGENT_NAMES=()
  local -a SUCCEEDED_AGENT_NAMES=()
  local -i failure_count=0

  for agent in "${AGENTS[@]}"; do
    if ! run_agent "$agent"; then
      FAILED_AGENT_NAMES+=("$agent")
      (( failure_count++ )) || true   # arithmetic exit code guard
    fi
  done

  echo "Failures: ${#FAILED_AGENT_NAMES[@]}"
}
```

**Note on arithmetic expressions:** `(( expr ))` exits non-zero when the result is 0, which can trip `set -e`. Use `(( expr )) || true` or `(( expr++ ))` when incrementing counters under strict mode.

**Verified on:** HomericIntelligence/Myrmidons PR #623 (2026-05-09). The `scripts/apply.sh` function that tracked failed agents crashed at `${#FAILED_AGENT_NAMES[@]}` before any agent had failed, because the array was never populated and bash -u treated it as unbound.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Myrmidons | PR #623 apply.sh failed-agent tracking | `scripts/apply.sh` function crash under `set -euo pipefail` |
