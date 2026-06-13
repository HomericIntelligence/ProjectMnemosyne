---
name: bash-stderr-mktemp-trap-return
description: "Pattern for separating stderr from stdout in bash functions using mktemp + trap RETURN. Use when: (1) a bash function calls a tool that mixes stderr into stdout (e.g., 2>&1 corrupts jq input), (2) you need clean stdout for piping while still capturing error details, (3) function uses local temp files that need guaranteed cleanup."
category: debugging
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Bash stderr/stdout Separation: mktemp + trap RETURN

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Separate stderr from stdout in bash functions so tools like `jq` receive clean JSON input |
| **Outcome** | Proposed pattern — not yet validated in CI |
| **Verification** | unverified |

## When to Use

- A bash function uses `2>&1` to redirect stderr into stdout, corrupting downstream JSON parsing (e.g., `jq` fails with parse errors)
- You need stdout clean for pipe consumers while still capturing stderr for diagnostics/error messages
- You want guaranteed temp file cleanup on function exit (including early returns and error exits)
- The script uses `#!/usr/bin/env bash` — the pattern relies on bash-specific `trap RETURN`

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Replace: output=$(gh pr view ... 2>&1)
# With: mktemp + trap RETURN separation

my_function() {
  local _err_file
  _err_file=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$_err_file'" RETURN

  local output
  output=$(gh pr view --json mergeStateStatus 2>"$_err_file") || {
    echo "gh failed: $(cat "$_err_file")" >&2
    return 1
  }

  # output is now guaranteed clean stdout — safe to pipe to jq
  echo "$output" | jq -r '.mergeStateStatus'
}
```

### Detailed Steps

1. **Declare a local temp file variable** before any `mktemp` call — `local _err_file` ensures the variable is scoped to the function.
2. **Create the temp file** with `_err_file=$(mktemp)` — creates a unique file in `/tmp`.
3. **Register a RETURN trap immediately** — `trap "rm -f '$_err_file'" RETURN` fires when the function returns (any path: normal return, `return 1`, even `set -e` exits from within the function). The `shellcheck disable=SC2064` suppresses the SC2064 warning (shellcheck flags single-quoted expressions in traps because it can't expand variables at trap-definition time — this is intentional here).
4. **Redirect stderr to the file** — `command 2>"$_err_file"` instead of `2>&1`.
5. **Check exit code and report stderr** — `|| { echo "... $(cat "$_err_file")" >&2; return 1; }`.
6. **Use clean stdout** downstream — pipe to `jq`, assign to variables, etc.

### RETURN trap vs EXIT trap

| Trap | Fires On | Use When |
|------|----------|----------|
| `trap ... RETURN` | Function return (any path) | Cleanup local to a function; called multiple times safely |
| `trap ... EXIT` | Script exit | Cleanup for the entire script; fires once |

**Caveat for sourced scripts**: `trap RETURN` fires on function exit when the function is defined in a file sourced with `.` (dot-source) from bash. If the same file is sourced from `/bin/sh` or `dash`, RETURN traps are silently ignored and temp files leak. The pattern is safe only when the caller shell is bash. Verify the shebang is `#!/usr/bin/env bash`, not `#!/bin/sh`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `2>&1` redirect | `output=$(gh pr view ... 2>&1)` | Stderr (warning lines, progress output) merged into `$output`; downstream `jq` received non-JSON lines and failed with parse errors | Never use `2>&1` when stdout is piped to a structured parser like `jq` |
| `2>/dev/null` suppress | `output=$(gh pr view ... 2>/dev/null)` | Silently swallowed error messages; debugging failures became very difficult | Suppress stderr only if diagnostics are truly never needed |
| `local tmpfile; tmpfile=$(mktemp); trap "rm -f $tmpfile" EXIT` | Used EXIT trap instead of RETURN trap | EXIT fires only once on script exit, not on each function call; temp files accumulated for the script lifetime | Use RETURN trap for function-scoped cleanup |

## Results & Parameters

**Pattern summary**:
```bash
# In any bash function that calls an external tool with structured stdout output:
local _err_file
_err_file=$(mktemp)
# shellcheck disable=SC2064
trap "rm -f '$_err_file'" RETURN

local result
result=$(external_tool --json-output 2>"$_err_file") || {
  local err_msg
  err_msg=$(cat "$_err_file")
  echo "external_tool failed: $err_msg" >&2
  return 1
}
# result is now clean, pipe-safe stdout
```

**Verification status**: The pattern is theoretically sound per bash manual (trap RETURN described in bash 4.x+). Not yet confirmed in the CI environment for ProjectHephaestus. Bash version >=4.2 required for reliable `trap RETURN` behavior in sourced functions.

**Source**: Planning notes for ProjectHephaestus issue #1125 (`choose_merge_flag.sh` stderr/jq fix).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1125 planning — proposed fix for `scripts/choose_merge_flag.sh:21` | Pattern designed, not yet CI-validated |
