---
name: bash-script-and-jq-failure-modes
description: "Diagnose and fix silent failures in bash scripting and jq under strict error-checking modes. Use when: (1) a bash script with set -euo pipefail exits unexpectedly mid-loop or mid-function, (2) grep finds no matches and kills the script via pipefail, (3) bash arrays crash with 'unbound variable' despite being declared, (4) exit 127 appears and all binaries are installed, (5) jq // operator silently drops boolean false values, (6) jq fails with syntax errors on array concatenation with conditionals, (7) Claude Code Bash cwd drifts from Read/Edit absolute paths in multi-worktree sessions, (8) a bash function with set -m + set +e silently aborts mid-execution after a single-command (...) subshell finishes with no error log and no continuation past the subshell, (9) gh api output captured with 2>&1 corrupts jq input via non-JSON stderr lines (deprecation banners, rate-limit notices, GH_DEBUG traces)."
category: debugging
date: 2026-06-13
version: "1.2.0"
verification: verified-ci
user-invocable: false
history: bash-script-and-jq-failure-modes.history
tags:
  - bash
  - pipefail
  - set-euo
  - grep
  - array
  - exit-127
  - shell-function
  - jq
  - boolean
  - falsy
  - cwd
  - worktree
  - tool-divergence
  - json
  - set-m
  - job-control
  - subshell
  - exec-optimization
  - silent-abort
  - orchestrator-rewrite
  - stderr
  - 2>&1
  - command-substitution
  - gh-cli
  - mock-gh
  - integration-test
  - ruff
  - D401
---

# Bash Script and jq Failure Modes Under Strict Error-Checking

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Consolidate known failure modes in bash scripting and jq processing under set -euo pipefail and related strict modes |
| **Outcome** | Synthesised from 6 verified skills; all patterns confirmed in CI or local runs |
| **Theme** | Shell/jq behavior under error-checking modes silently produces wrong behavior, requiring the same class of defensive fixes |

## When to Use

- A bash script with `set -euo pipefail` exits silently mid-loop — especially around `grep \| while read` pipelines
- Bash exits with code 127 and all binaries (`yq`, `jq`, `curl`) are installed — function-not-found, not binary-not-found
- A sourced shell library was recently refactored and old function names were removed or renamed in a merge
- An array is declared (`local -a ARRAY`) but crashes with "unbound variable" when first accessed
- A jq expression using `//` returns empty when the JSON field holds `false`
- jq fails with `syntax error, unexpected '+', expecting '}'` on array concatenation with conditionals
- `Read` shows content that `grep` in Bash cannot find — or a commit lands on the wrong branch — in a multi-worktree session
- A bash function with `set -m` + `set +e` silently aborts mid-execution after a single-command `(...)` subshell finishes, with no error log and no continuation past the subshell — bash trace shows execution jumping to the parent loop. The defang-with-`set +e` pattern is NOT sufficient against this trigger.
- `gh api` output is captured with `2>&1` into a variable, then piped to `jq`, and `jq` returns empty or the script exits with "allows no merge methods" / "no valid value" — even though the API endpoint is valid.
- A Python subprocess integration test needs to stub `gh` without creating a fake binary on `PATH`.
- A docstring on a private helper function (`_foo`) fails ruff D401 despite starting with a capital letter.

Do NOT use when:

- The 127 originates from a bats test (different diagnostic path — bats wraps function calls differently)
- The jq error is unrelated to array concatenation (e.g., malformed JSON input)
- Only one git worktree is checked out (cwd divergence cannot occur)

## Verified Workflow

### Quick Reference

```bash
# --- EXIT 127: trace the missing function ---
bash -x tests/foo.sh 2>&1 | head -80
git log --all --oneline --grep='<function-name-stem>'
git show <sha>:scripts/lib/api.sh | grep -A 50 '^old_function_name()'

# --- GREP KILLING SCRIPT: guard before piping ---
# WRONG:
grep "pattern" "$file" | while read -r line; do process "$line"; done
# CORRECT (preferred):
if grep -q "pattern" "$file"; then
  while read -r line; do process "$line"; done < <(grep "pattern" "$file")
fi

# --- UNBOUND ARRAY: always initialize ---
# WRONG:
local -a FAILED=
# CORRECT:
local -a FAILED=()

# --- ARITHMETIC COUNTER: guard set -e ---
(( count++ )) || true
# or:
count=$(( count + 1 ))

# --- JQ BOOLEAN: never use // on booleans ---
# WRONG:
value=$(echo "$json" | jq -r '.converged // empty')
# CORRECT:
value=$(echo "$json" | jq -r '.converged | if . == null then "" else tostring end')

# --- JQ ARRAY CONCAT COMPATIBILITY: build array in bash ---
files_json="[\"${DIR}/file1.sh\"]"
if [[ "$condition" == "true" ]]; then files_json+=", \"${DIR}/extra.sh\""; fi
files_json+="]"
jq -n --argjson files "$files_json" '{ files: $files }'

# --- CWD DIVERGENCE: anchor at session start ---
cd /abs/path/to/main/worktree && pwd
git rev-parse --show-toplevel
git worktree list

# --- GH API 2>&1 CORRUPTION: capture stdout only ---
# WRONG — merges stderr into $raw; any non-JSON line breaks jq:
raw=$(gh api "repos/${repo}" 2>&1)
flag=$(printf '%s' "$raw" | jq -r '...')
# CORRECT — capture stdout only; gh writes its error to stderr on failure:
if ! raw=$(gh api "repos/${repo}"); then
    echo "gh api repos/${repo} failed" >&2
    return 1
fi
flag=$(printf '%s' "$raw" | jq -r '...')
```

### Failure Mode 1: Exit 127 — Orphaned Shell Function

Exit 127 in a bash test has two distinct causes: missing binary vs. missing function. The `-x` trace distinguishes them — a missing binary shows `command not found`; a missing function just stops.

1. Trace where the 127 fires: `bash -x tests/foo.sh 2>&1 | head -100`
2. Ignore misleading stdout (e.g., tool help text emitted in an unexpected context).
3. Search git history for the function:
   ```bash
   git log --all --oneline --grep='<function-name-stem>'
   git show <sha>:scripts/lib/api.sh | grep -A 50 '^old_function()'
   ```
4. Restore the function body and add a delegate shim so both old and new callers work.
5. Fix any co-located `jq select` fallback bugs (see Failure Mode 4).

### Failure Mode 2: grep No-Match Killing Script Under set -euo pipefail

`grep` exits 1 when it finds no matches. Under `set -e` + `pipefail`, this exit code is indistinguishable from a real error and aborts the script — the loop body is never entered, but the script also does not continue.

**Preferred fix — process substitution with guard:**

```bash
if grep -q "pattern" "$file"; then
  while read -r line; do
    process "$line"
  done < <(grep "pattern" "$file")
fi
```

**Alternative — temporarily disable pipefail:**

```bash
set +o pipefail
grep "pattern" "$file" | while read -r line; do process "$line"; done
set -o pipefail
```

Avoid `|| true` at the end of the whole pipeline — it silently swallows all errors inside the loop body, not just grep's exit 1.

### Failure Mode 3: Unbound Array Under set -u

`local -a ARRAY` and `declare -a ARRAY` *declare* the variable as an array type but leave it in an unset state. Under `set -u` (nounset), reading `${#ARRAY[@]}` or `${ARRAY[0]}` on an unset array triggers "unbound variable" and `set -e` exits immediately.

**Fix — one character:**

```bash
# WRONG:
local -a FAILED_AGENT_NAMES
# CORRECT:
local -a FAILED_AGENT_NAMES=()
```

**Pattern for tracking failures:**

```bash
my_function() {
  local -a FAILED=()
  local -i failure_count=0
  for item in "${ITEMS[@]}"; do
    if ! run_item "$item"; then
      FAILED+=("$item")
      (( failure_count++ )) || true  # arithmetic exit code guard
    fi
  done
  echo "Failures: ${#FAILED[@]}"
}
```

### Failure Mode 4: jq // Operator Dropping Boolean false

jq's `//` operator returns the right side when the left is `false` OR `null`. This traces to Perl's `||` semantics — unlike most JSON tools, jq treats `false` and `null` as equivalent "alternatives."

**jq manual (1.6+):** "The operator `//` produces its left-hand side if it is not `false` or `null`, and otherwise produces its right-hand side."

**Correct patterns by use case:**

```jq
# Serialize boolean to string (null-safe):
.converged | if . == null then "" else tostring end

# Default only for null/missing (not false):
(.converged // false) | tostring

# In object construction:
{convergence: (.converged | if . == null then null else tostring end)}
```

Also applies to `select` + fallback:

```bash
# WRONG — select filters out the row; // never fires on empty:
result=$(jq -r '.[] | select(.name == $name) | .status // "unknown"' ...)
# CORRECT — first() so fallback applies when no match:
result=$(jq -r 'first(.[] | select(.name == $name) | .status) // "unknown"' ...)
result="${result:-unknown}"   # shell-level fallback
```

### Failure Mode 5: jq Array Concatenation Syntax Error (Older jq)

`] + (if $var then [...] else [] end)` works on jq 1.6+ but fails on older versions with `syntax error, unexpected '+', expecting '}'`.

**Fix — build the array in bash:**

```bash
local files_json
files_json="[\"${INSTALL_DIR}/file1.sh\", \"${HELPERS_DIR}/file2.sh\""
if [[ "$condition" == "true" ]]; then
  files_json+=", \"${DIR}/optional.sh\""
fi
files_json+="]"

jq -n \
  --argjson files "$files_json" \
  '{ files: $files }'
```

### Failure Mode 6: Bash CWD Drifting from Edit/Read Absolute Paths

Claude Code's Bash tool persists cwd across invocations. Read/Edit/Write/Grep/Glob always use absolute paths verbatim. When a `cd <other-worktree>` appears in any Bash call, Bash commands silently operate on the sibling worktree while Edit/Read operate on the main worktree.

**Tool cwd behavior:**

| Tool | CWD-dependent? | Notes |
| ---- | -------------- | ----- |
| Bash | YES — persists across calls | Every `cd` leaks into the next Bash turn |
| Read | NO | Requires absolute path |
| Edit | NO | Requires absolute path |
| Write | NO | Requires absolute path |
| Grep | NO | Uses absolute or workspace-relative path arg |
| Glob | NO | Uses absolute or workspace-relative path arg |

**Prevention — anchor cwd at session start:**

```bash
cd /abs/path/to/main/worktree && pwd
git worktree list
git rev-parse --show-toplevel
```

**Prefer cwd-free patterns:**

```bash
git -C /abs/path/to/other/worktree status       # no cd needed
(cd /abs/path/to/other/worktree && cmd)          # subshell — does not leak
```

**Detection when results disagree:**

```bash
pwd
git rev-parse --show-toplevel
realpath <file>
git log -1 --oneline -- <file>
```

**Recovery from stray commit in wrong worktree:**

```bash
cd /wrong/worktree && git log --oneline -5
cd /correct/worktree && git cherry-pick <stray-sha>
cd /wrong/worktree && git reset --hard HEAD~1
```

### Failure Mode 7: `set -m` + Single-Command `(...)` Subshell Exec-Optimization Silent Abort

When a bash function combines `set -m` (job control, putting the function's subshell in its own process group) with a single-command `(...)` subshell whose last/only command is an external binary, bash applies exec-optimization: the subshell process `exec`-replaces itself into the external command. When that command exits, the subshell PID dies with its rc — but the parent function's continuation context can be lost. Subsequent commands in the function body (including `rc=$?`, `phase_done` logging, `wait`, and follow-up phases) never execute. Bash `-x` trace shows execution jumping directly to the outer parent loop.

The classic "defang errexit" pattern (`set +e` + `trap 'set -e' RETURN`) does NOT help here, because nothing after the subshell runs to be defanged. Adding more `set +e` is the wrong direction.

**Diagnostic recipe: silent abort after single-command subshell**

```bash
# Add this near the top of the suspect function:
set -E
trap 'echo "[DIAG] ERR at line $LINENO rc=$? cmd=$BASH_COMMAND" >&2' ERR
trap 'echo "[DIAG] EXIT rc=$? last_line=$LINENO" >&2' EXIT
# Re-run with: bash -x script.sh ... 2> trace.log
# If START banner appears but no DONE/ERR fires after the subshell,
# the bash subshell exec-replaced into the external command and never returned.
```

Concrete symptom signature (from ProjectHephaestus `scripts/run_automation_loop.sh`):
- `phase 1/6 plan START` logged on every invocation (75/75).
- Planner Python process logs "Planning complete" (rc=0).
- No `phase_done`, no `Warning:`, no `phase 2` banner ever logged.
- Outer `wait()` always reports non-zero.
- `bash -x` trace shows the next command after the planner subshell is the OUTER loop's echo — process_repo's trace simply does not resume.

**Fixes (in order of preference):**

1. **Restructure to avoid the single-command subshell.** Extract the work into a real function or pipe through another stage so the subshell does not have a single trailing external command:
   ```bash
   # Instead of:
   ( cd "$dir" || exit 1; "$PLAN_BIN" --foo "$bar" )
   # Use:
   run_plan() { cd "$1" || return 1; "$PLAN_BIN" --foo "$2"; echo done; }
   run_plan "$dir" "$bar"
   ```
   The trailing `echo done` (or any builtin) blocks exec-optimization.

2. **Rewrite the orchestrator in Python.** When 3+ interacting safety mechanisms (`set -euo pipefail` + `set -m` + `set +e` defang + ERR/EXIT traps + RETURN traps + single-command subshells) accumulate, the rewrite-to-Python option becomes lower-risk than another patch. The Python equivalent uses `subprocess.run` inside a plain `for phase in ALL_PHASES` loop — phase isolation is then **structural**, not behavioral, and no shell-option landmine can silently skip iterations. See ProjectHephaestus `hephaestus/automation/loop_runner.py` for the verified replacement pattern.

### Failure Mode 8: `2>&1` in Command Substitution Corrupts jq Input

When `gh api` (or any CLI that emits non-JSON to stderr) is captured with `2>&1` inside `$()`, deprecation banners, update notices, and `GH_DEBUG=1` traces are merged into the captured variable. Any non-JSON line appearing before the JSON body causes `jq` to fail or return empty — silently under `-r`, producing downstream "no valid value" / "allows no merge methods" false errors even when the API response is correct.

**Trigger conditions:**
- `gh` CLI writes to stderr: deprecation notices, "A new release of gh is available", rate-limit hints, or `GH_DEBUG` traces.
- The variable is later piped to `jq`.
- `jq` receives a mixed blob (e.g., `"warning: new gh version available\n{...json...}"`) and either errors or returns empty.
- Downstream code interprets empty as "no valid value" and falls through to a failure path.

**Bug pattern:**

```bash
# WRONG — merges gh stderr into $raw; any non-JSON line breaks jq
if ! raw=$(gh api "repos/${repo}/merge-methods" 2>&1); then
    echo "failed: ${raw}" >&2
    return 1
fi
flag=$(printf '%s' "$raw" | jq -r '.allow_squash_merge // false')
```

The `2>&1` was added to capture gh's error message into `$raw` for the error path — but it also captures all advisory stderr on the success path.

**Correct pattern — capture stdout only:**

```bash
# CORRECT — capture stdout only; gh writes its own error to stderr on failure
if ! raw=$(gh api "repos/${repo}/merge-methods"); then
    echo "gh api repos/${repo}/merge-methods failed" >&2
    echo "  (check: gh auth status; token needs 'repo' scope; repo exists)" >&2
    return 1
fi
flag=$(printf '%s' "$raw" | jq -r '.allow_squash_merge // false')
```

On failure, `$raw` is empty (gh already wrote its error message to stderr). The error path message should not reference `$raw`.

**Diagnostic: verify corruption is the cause:**

```bash
# Run with GH_DEBUG=1 and capture both separately:
raw_out=$(gh api "repos/owner/repo" 2>/tmp/gh_stderr.txt)
cat /tmp/gh_stderr.txt   # should contain only diagnostic lines, not JSON
echo "$raw_out" | jq .   # should parse cleanly
```

### Failure Mode 9: Stubbing `gh` in Python Subprocess Integration Tests

When integration-testing shell scripts that call `gh`, creating a fake `gh` binary on PATH is fragile (requires temp dir, PATH manipulation, cleanup). The simpler pattern uses an inline bash function with `export -f`:

```python
import subprocess
from pathlib import Path

SNIPPET = Path(__file__).resolve().parents[2] / "scripts" / "choose_merge_flag.sh"

def _run_choose(json_body: str, *, stderr_noise: bool = False) -> subprocess.CompletedProcess[str]:
    """Run choose_merge_flag with a mocked gh that returns json_body on stdout."""
    if stderr_noise:
        gh_impl = (
            f"gh() {{\n"
            f"    case \"$1\" in\n"
            f"        api)\n"
            f"            echo \"warning: new gh version available\" >&2\n"
            f"            printf '%s\\n' '{json_body}'\n"
            f"            ;;\n"
            f"    esac\n"
            f"}}"
        )
    else:
        gh_impl = f"gh() {{ case \"$1\" in api) printf '%s\\n' '{json_body}';; esac; }}"

    script = f"""
{gh_impl}
export -f gh
. {SNIPPET}
choose_merge_flag owner/repo
"""
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)
```

Key points:
- `export -f gh` makes the bash function visible to the sourced script — no fake binary needed.
- `stderr_noise: bool` flag lets tests verify the fix holds even when gh emits non-JSON to stderr.
- The sourced script (`. SNIPPET`) runs in the same shell process, so the exported function is inherited.
- Docstring must use imperative mood ("Run …") — not "Helper to run …" — to satisfy ruff D401.

### Failure Mode 10: ruff D401 Applies to Private Helper Docstrings

ruff enforces D401 ("First line of docstring should be in imperative mood") on **all** public and private functions, including those named `_foo`. The rule checks whether the first word of the docstring is an imperative verb.

**Fails D401:**
```python
def _run_choose(json_body: str) -> subprocess.CompletedProcess[str]:
    """Helper to run choose_merge_flag with a mocked gh."""  # "Helper" is not imperative
```

**Passes D401:**
```python
def _run_choose(json_body: str) -> subprocess.CompletedProcess[str]:
    """Run choose_merge_flag with a mocked gh that returns json_body on stdout."""
```

Common failing openers: "Helper to", "Wrapper for", "Utility that", "Used to". Use "Run", "Execute", "Return", "Build", "Validate" instead.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reading stderr/stdout from test runner | Examined "Available tasks:" output in stdout to diagnose 127 | Output was pixi help text from `yq` called in unexpected context — a red herring | Trust `bash -x` trace over raw stdout when diagnosing exit 127 |
| Assuming 127 = missing binary | Checked whether `yq`\|`jq`\|`curl` were installed | All binaries present; 127 came from a missing bash function in a sourced library | Exit 127 has two distinct causes: missing binary vs. missing function; `-x` trace distinguishes them |
| `grep "pattern" file \| while read line; do` | Direct pipe from grep into while-read | When grep exits 1 (no matches), pipefail propagates non-zero exit and set -e aborts script | Never pipe grep into while-read under set -euo pipefail without a guard |
| `\|\| true` on the whole while-read pipeline | Appended `\|\| true` after `done` | Works but silently swallows ALL errors inside loop body, masking real failures | Use process substitution (Option A); reserve `\|\| true` only for truly ignorable errors |
| Logic inversion: else sets rc=1 for non-matching files | Expected that `else rc=1` would fire on non-matching files | The abort-on-grep-miss masked the real logic flow; else branch was never reached | Pipefail trap can invert apparent logic: what looks like a missing-string check exits instead |
| `local -a FAILED_AGENT_NAMES` (no `=()`) | Declared array without initializing | Under `set -u`, bash treats unassigned array as unbound on first access | Always use `=()` when declaring arrays; declaration alone is not initialization |
| Guarding with `[[ -v ARRAY ]]` check | Used `[[ -v FAILED_AGENT_NAMES ]]` before each access | Verbose and easy to miss in new code paths; doesn't fix root cause | Initialize at declaration instead of guarding every access site |
| `.converged // empty` | Used jq alternative operator to skip null | `false` is falsy in jq — `//` triggers on `false` too, returning empty | Never use `//` with boolean fields; use `if . == null` instead |
| `.converged // "false"` | Tried to default to string "false" | `//` replaces `false` with the alternative regardless — output is always `"false"` even when `.converged` is `true` | The alternative operator is wrong for booleans; use `tostring` with a null guard |
| `.converged \| tostring` | Direct tostring without null check | Works for booleans but crashes if field is missing (null input to tostring) | Add `// null` guard before `tostring` or use `if . == null then "" else tostring end` |
| jq inline array concatenation `] + (if $cond then [...] else [] end)` | Used jq's `+` operator for conditional array building | Fails on jq 1.5 and some distro-patched builds with `syntax error, unexpected '+'` | Build conditional arrays in bash; pass via `--argjson` for version compatibility |
| Trust Edit succeeded (multi-worktree) | Assumed Edit on an absolute path edited the file Bash subsequently grep'd | Edit operated on main worktree path; Bash grep ran in sibling worktree via stale cwd | Edit and Bash can target different copies of the same logical file when multiple worktrees exist |
| Re-Read to verify after Edit | Re-read file via Read (absolute path) to confirm the edit landed | Read showed correct content (main worktree) — but Bash kept grepping wrong copy via relative path | A successful Read does not prove subsequent Bash commands see the same file |
| Python heredoc rewrite | Switched to `python3 <<EOF` rewrite when Edit refused | Python interpreter inherits Bash cwd; opened relative path resolving into wrong worktree | Heredoc/subprocess tools inherit Bash cwd — same root cause, different surface |
| Grep with relative path | Used `grep PATTERN .github/workflows/file.yml` to confirm change | Relative path resolved against stale cwd; returned no match | Always use absolute paths in Bash when cross-checking Edit results |
| Blame the Edit tool | Suspected Edit was silently no-oping or operating on a cached buffer | Edit had worked correctly — divergence was in the verifier, not the editor | When two tools disagree, suspect cwd before suspecting tool bugs |
| `set -m` + single-command `(...)` subshell exec-optimization | Defang errexit inside the function via `set +e` + `trap 'set -e' RETURN`; expected `rc=$?` to capture exit and `phase_done` to fire | bash trace shows no commands execute after the subshell completes — control returns directly to the outer parent loop. `set -m` puts the subshell in its own process group, and bash optimises single-command subshells via exec-replace, so the subshell PID dies with the command's rc and the parent's continuation context is lost. `set +e` does not help because nothing runs after the subshell to be defanged. | Diagnose with `bash -x` + ERR/EXIT traps inside the function: if `phase_start` banners appear but `phase_done` banners NEVER appear (even with stderr captured), the function body is not running past the subshell. Don't add more `set +e` — restructure to avoid the single-command subshell (e.g., extract into a real function), or replace the bash orchestrator entirely. |
| `gh api … 2>&1` in command substitution | Added `2>&1` to capture gh's error message into `$raw` for the error path in `choose_merge_flag.sh` | gh also writes deprecation banners, update notices, and GH_DEBUG traces to stderr on SUCCESS paths; merging these into `$raw` before piping to jq produced non-JSON input, causing jq to return empty; downstream "allows no merge methods" false error on valid repos | Never redirect `2>&1` in a `$(…)` capturing API output for jq; capture stdout only; on failure `$raw` is empty and gh already printed the error to stderr |
| Using "Helper to" opener for private function docstring | Wrote `"""Helper to run choose_merge_flag with a mocked gh."""` on `_run_choose` | ruff D401 rejected it: "Helper" is not imperative mood | ruff D401 applies to private functions too; use imperative verb openers ("Run", "Execute", "Build", "Return") regardless of whether the function name starts with `_` |

## Results & Parameters

### grep exit code semantics

```
grep exit codes: 0 = matches found, 1 = no matches, 2 = error
Under set -e + pipefail, exit code 1 (no matches) is indistinguishable from a real error.
```

### Arithmetic counter guard pattern

```bash
(( count++ )) || true       # safe: || true prevents set -e seeing 0 result
count=$(( count + 1 ))      # also safe: arithmetic expansion never triggers set -e
```

### Restored function with delegate shim pattern

```bash
# Restored original with retry logic:
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
result=$(echo "$json" | jq -r --arg name "$name" \
  'first(.[] | select(.name == $name) | .status) // "unknown"')
result="${result:-unknown}"   # shell fallback in case jq returns empty
```

### Pre-commit hook template (grep no-match safe)

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

### Session-start checklist for multi-worktree sessions

```bash
cd /abs/path/to/main/worktree
pwd
git worktree list
git rev-parse --show-toplevel
```

### gh api stdout-only capture pattern

```bash
# Capture stdout only — do NOT use 2>&1 when the output is piped to jq
if ! raw=$(gh api "repos/${owner}/${repo}"); then
    echo "gh api failed" >&2
    return 1
fi
result=$(printf '%s' "$raw" | jq -r '.some_field // empty')
```

On failure, `$raw` is empty; gh has already written its error message to stderr. Do not reference `$raw` in the error message.

### mock-gh bash function pattern for Python integration tests

```python
import subprocess
from pathlib import Path

SNIPPET = Path(__file__).resolve().parents[2] / "scripts" / "choose_merge_flag.sh"

def _run_choose(json_body: str, *, stderr_noise: bool = False) -> subprocess.CompletedProcess[str]:
    """Run choose_merge_flag with a mocked gh that returns json_body on stdout."""
    if stderr_noise:
        gh_impl = (
            f"gh() {{\n"
            f"    case \"$1\" in\n"
            f"        api)\n"
            f"            echo \"warning: new gh version available\" >&2\n"
            f"            printf '%s\\n' '{json_body}'\n"
            f"            ;;\n"
            f"    esac\n"
            f"}}"
        )
    else:
        gh_impl = f"gh() {{ case \"$1\" in api) printf '%s\\n' '{json_body}';; esac; }}"

    script = f"""
{gh_impl}
export -f gh
. {SNIPPET}
choose_merge_flag owner/repo
"""
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)
```

Key: `export -f gh` exports the bash function into the environment so the sourced script inherits it. No fake binary on PATH needed. The `stderr_noise=True` variant verifies the fix holds under realistic gh advisory output.

### ruff D401 imperative-mood docstring openers

| Fails D401 | Passes D401 |
| ---------- | ----------- |
| "Helper to run X" | "Run X with …" |
| "Wrapper for X" | "Wrap X and return …" |
| "Utility that does X" | "Execute X and …" |
| "Used to build X" | "Build X from …" |
| "This function validates X" | "Validate X against …" |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Myrmidons | PR #564 — check-gitleaks-coe.sh pre-commit hook exited on grep no-match before reaching else rc=1 | grep \| while-read abort under pipefail |
| HomericIntelligence/Myrmidons | PR #623 — apply.sh failed-agent tracking crashed at `${#FAILED_AGENT_NAMES[@]}` | Unbound array under set -u |
| HomericIntelligence/Myrmidons | PR #623 — convergence serialization bats test 318 failing on false value | jq // operator falsy boolean trap |
| HomericIntelligence/Myrmidons | CI debug session — test-api-retry.sh exit 127 after `_agamemnon_curl_retry` renamed | Exit-127 function recovery |
| ai-maestro (23blocks-OS) | Issue #272 — install-agent-cli.sh jq syntax error on older jq | jq array concatenation compatibility |
| HomericIntelligence/ProjectOdyssey | Multi-worktree session — stray commit cf710fb4 on ci-pipe-handler-cores-gate branch | Bash cwd drift from Edit/Read absolute paths |
| HomericIntelligence/ProjectHephaestus | Session 2026-05-26 — `scripts/run_automation_loop.sh` `process_repo` silently aborting after planner subshell (phases 2-6 skipped 75/75 invocations); replaced with `hephaestus/automation/loop_runner.py` | `set -m` + single-command subshell exec-optimization silent abort |
| HomericIntelligence/ProjectHephaestus | Issue #1122, PR #1273 — `scripts/choose_merge_flag.sh` `2>&1` on `gh api` merged deprecation banners into `$raw`, causing jq to return empty; spurious "allows no merge methods" exit-1 on valid repos | `2>&1` in command substitution corrupts jq input; mock-gh bash function integration test pattern; ruff D401 on private helper docstrings |
