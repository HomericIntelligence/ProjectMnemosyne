---
name: bash-stderr-jq-separation
description: "Pattern for separating stderr from stdout in bash functions that pipe command output into jq. Use when: (1) a bash function captures CLI output (gh api, curl, etc.) for JSON parsing, (2) the command may emit stderr warnings/banners alongside valid JSON stdout, (3) 2>&1 is used to combine channels before piping into jq — this corrupts JSON parsing."
category: debugging
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - bash
  - stderr
  - stdout
  - jq
  - mktemp
  - trap
  - RETURN
  - gh
  - json
  - subprocess
---

# Bash Stderr/JQ Separation: mktemp + trap RETURN Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Prevent gh/curl stderr noise (warnings, banners, debug traces) from corrupting jq JSON input |
| **Outcome** | mktemp + trap RETURN pattern cleanly separates channels; dedicated regression test guards against re-introduction |
| **Verification** | unverified — plan not yet implemented in CI |

## When to Use

- A bash function does `raw=$(command 2>&1)` and pipes `$raw` into `jq`
- `gh api`, `curl`, `aws`, or similar tools may emit stderr warnings alongside valid JSON stdout
- The function is a sourced bash function (not a top-level script), requiring RETURN trap for cleanup
- Writing Python integration tests that need to mock a bash CLI tool (see companion skill `bash-mock-gh-python-subprocess-export-f`)
- Adding a regression guard test: the stderr-noise test is the correct guard, not the happy-path test alone

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# WRONG: 2>&1 mixes gh stderr into jq input, corrupting JSON parsing
choose_merge_flag() {
  local raw
  raw=$(gh api "repos/${repo}/..." 2>&1)       # BUG: stderr prepended to JSON
  echo "$raw" | jq -r '...'                    # jq rejects non-JSON prefix
}

# CORRECT: mktemp + trap RETURN separates channels
choose_merge_flag() {
  local raw flag _err_file
  _err_file=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$_err_file'" RETURN              # cleanup on function exit
  if ! raw=$(gh api "repos/${repo}/..." 2>"$_err_file"); then
    echo "gh api failed: $(cat "$_err_file")" >&2
    return 1
  fi
  flag=$(printf '%s' "$raw" | jq -r '...')
  echo "$flag"
}
```

### Detailed Steps

1. **Replace `2>&1`** on the command that produces JSON stdout with `2>"$_err_file"`
2. **Add `_err_file=$(mktemp)`** before the command to allocate a unique temp file
3. **Add `trap "rm -f '$_err_file'" RETURN`** immediately after mktemp to ensure cleanup on function exit
4. **Add `# shellcheck disable=SC2064`** before the trap line — shellcheck warns about single-quoted trap expressions, but single-quoting is correct here (expands `$_err_file` at trap-set time, not at trap-fire time)
5. **Use `$(cat "$_err_file")`** in error messages instead of `$raw` — `$raw` is now clean JSON-only
6. **Add a dedicated stderr-noise regression test** — the happy-path test alone is not sufficient; see Results section

### Why Single-Quote the Trap Expression

```bash
trap "rm -f '$_err_file'" RETURN   # CORRECT: $_ err_file expands NOW (at trap-set)
trap 'rm -f "$_err_file"'  RETURN  # WRONG: $_err_file expands LATER (at trap-fire)
                                    # by which point the local var may be gone
```

The `# shellcheck disable=SC2064` silences SC2064 ("Trap statement evaluates on definition, not when triggered"). This is intentional: we want the path captured at definition time.

### RETURN Trap in Sourced Bash Functions

`trap ... RETURN` fires when a bash **function** returns, not when the script exits. This makes it correct for cleanup inside sourced bash functions:

```bash
. ./scripts/choose_merge_flag.sh   # source the script
choose_merge_flag owner/repo       # RETURN trap fires when this function exits
                                   # NOT when the surrounding shell exits
```

**Caveat**: RETURN trap is bash-specific. If the script is sourced from `/bin/sh` or `dash`, the RETURN trap is silently ignored and the temp file leaks. The script shebang `#!/usr/bin/env bash` makes this safe for direct execution; sourcing from `/bin/sh` callers is the risk.

### Regression Guard: Stderr-Noise Test

A happy-path test that passes valid JSON is NOT sufficient as a regression guard for the `2>&1` bug. The bug only manifests when the mock `gh` actually writes to stderr. The dedicated test is:

```python
def test_shell_helper_handles_gh_stderr_noise():
    """Verify stderr noise does not corrupt jq JSON parsing."""
    bash_script = """
gh() {
    printf '%s\\n' '{"rebaseMergeAllowed":true,"squashMergeAllowed":false,"mergeCommitAllowed":false}'
    echo "WARNING: gh cli update available" >&2   # simulate stderr noise
    return 0
}
export -f gh

. ./scripts/choose_merge_flag.sh
choose_merge_flag owner/repo
"""
    result = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "--rebase"
    assert "WARNING" not in result.stdout   # stderr must not appear in stdout
```

Without the fix, `result.stdout` would contain `"WARNING: gh cli update available\n{...}"` and jq would fail, returning empty or exit 1.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `raw=$(gh api ... 2>&1)` piped into jq | Combined stdout+stderr then passed to jq | gh stderr (warnings, banners, debug) prepended to JSON; jq rejects non-JSON prefix | Never use `2>&1` when stdout goes to a text parser |
| `2>/tmp/gh.err` hardcoded path | Used a fixed path instead of mktemp | `/tmp/gh.err` is a global namespace; concurrent calls clobber each other | Always use `mktemp` for unique temp files in functions |
| `trap ... EXIT` instead of RETURN | Used EXIT trap inside a bash function | EXIT fires when the surrounding shell exits, not when the function returns; temp file persists for the entire shell session lifetime | Use `RETURN` trap in bash functions; `EXIT` only for top-level scripts or `main()` patterns |
| Double-quoted trap expression | `trap "rm -f \"$_err_file\"" RETURN` | Escaping gets complex and error-prone | Single-quote the path with `'$_err_file'` (expands at trap-set time); add `# shellcheck disable=SC2064` |
| Happy-path test as regression guard | Asserted correct flag output when mock gh returns clean JSON | Test passes both before and after the fix — it never exercises the stderr-corruption path | The regression guard MUST have the mock emit a warning on stderr; otherwise the `2>&1` re-introduction is invisible |

## Results & Parameters

**Reproduce the bug before the fix:**

```bash
bash -c '
gh() {
  echo "Warning: this is stderr noise" >&2
  printf '"'"'{"rebaseMergeAllowed":true,"squashMergeAllowed":false,"mergeCommitAllowed":false}'"'"'\n'
}
export -f gh
. scripts/choose_merge_flag.sh
choose_merge_flag owner/repo
'
# With 2>&1 bug: empty output (exit 1) — jq fails on non-JSON prefix
# With mktemp fix: --rebase (exit 0)
```

**Count of tests the plan adds:**

The issue body specifies 3 required tests. The plan adds a 4th (stderr-noise regression guard). The reviewer should confirm whether 4 tests are welcome or the plan should be trimmed to 3 (dropping the dedicated regression test and relying on the general stderr-noise assertion).

**jq boolean fields and `//` operator:**

If the script uses `jq -r '... | .[0] // ""'`, ensure the `// ""` is applied to the array element (after filtering), not to boolean fields directly. The `//` operator treats `false` as falsy — use `if . == null then` for null-guards on booleans (see `bash-script-and-jq-failure-modes` skill, Failure Mode 4).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1125 planning (unverified) | `scripts/choose_merge_flag.sh:21` fix + `tests/integration/test_choose_merge_flag_sh.py` |
