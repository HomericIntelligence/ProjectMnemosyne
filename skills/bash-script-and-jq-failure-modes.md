---
name: bash-script-and-jq-failure-modes
description: "Diagnose and fix silent failures in bash scripting and jq under strict error-checking modes. Use when: (1) a bash script with set -euo pipefail exits unexpectedly mid-loop or mid-function, (2) grep finds no matches and kills the script via pipefail, (3) bash arrays crash with 'unbound variable' despite being declared, (4) exit 127 appears and all binaries are installed, (5) jq // operator silently drops boolean false values, (6) jq fails with syntax errors on array concatenation with conditionals, (7) Claude Code Bash cwd drifts from Read/Edit absolute paths in multi-worktree sessions, (8) a bash function with set -m + set +e silently aborts mid-execution after a single-command (...) subshell finishes with no error log and no continuation past the subshell, (9) gh API call uses 2>&1 and non-JSON stderr (deprecation warnings, debug traces) corrupts the captured JSON blob causing jq failures or false exit-1."
category: debugging
date: 2026-06-12
version: "1.2.0"
verification: verified-local
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
  - stderr-corruption
  - stdout-only
  - gh-api
  - 2>&1
  - mock-gh
  - integration-testing-bash
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
- A `gh api` call captures output with `raw=$(gh api ... 2>&1)`, jq then fails or returns empty, and gh itself succeeds — suspect non-JSON stderr (deprecation banner, update notice, debug trace) corrupting the captured blob.
- An integration test for a bash script needs to exercise `gh` calls hermetically without hitting GitHub — and the script sources `gh` by name, so a mock bash function (`gh() { ... }; export -f gh`) is needed.

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

# --- 2>&1 STDERR CORRUPTION: capture stdout only ---
# WRONG — any non-JSON stderr line (deprecation banner, debug trace) corrupts $raw:
raw=$(gh api "repos/${repo}" 2>&1)
# CORRECT — capture stdout only; gh writes its own errors to stderr on failure:
raw=$(gh api "repos/${repo}")
# In error message, reference ${repo} not ${raw} (gh already logged error to stderr):
echo "Error: gh api failed for repo ${repo}" >&2

# --- MOCK-GH BASH FUNCTION PATTERN (integration tests) ---
# Override gh in shell scope; export -f makes it available to sourced scripts
gh() {
  case "$1 $2" in
    "api repos/owner/repo")
      printf '%s\n' '{"allow_squash_merge":true,"allow_rebase_merge":false,"allow_merge_commit":false}'
      ;;
    *)
      echo "Unexpected gh call: $*" >&2; return 1 ;;
  esac
}
export -f gh
# Then source the script under test (do NOT run it as a subprocess — export -f only works in same shell):
source scripts/choose_merge_flag.sh
# Call the function directly:
result=$(choose_merge_flag "owner/repo")
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

### Failure Mode 8: `2>&1` Merging gh stderr into JSON Capture

When a bash script captures `gh api` output with `raw=$(gh api ... 2>&1)` and pipes `$raw` into `jq`, any non-JSON line on stderr (deprecation notice, update banner, `DEBUG:` trace, or rate-limit warning) is prepended to the JSON blob. `jq` then fails or produces empty output. The script may exit with "no merge methods allowed" or a similar false negative even though the API call succeeded.

**Root cause**: `2>&1` redirects file descriptor 2 (stderr) into file descriptor 1 (stdout) before command substitution captures stdout. `gh` writes warnings, deprecation notices, and debug traces to stderr — they are not part of the JSON response.

**Fix — capture stdout only:**

```bash
# WRONG — any non-JSON stderr line corrupts $raw:
raw=$(gh api "repos/${repo}" 2>&1)
echo "$raw" | jq -r '.allow_squash_merge'

# CORRECT — gh writes errors to stderr automatically on non-zero exit:
raw=$(gh api "repos/${repo}")
echo "$raw" | jq -r '.allow_squash_merge'
```

**Consequence of removing `${raw}` from the error message**: If you previously echoed `$raw` in the error path to surface gh's error detail, remove it — gh already wrote its own error to stderr before exiting non-zero. Reference `${repo}` (or the URL) in the error message instead:

```bash
if ! raw=$(gh api "repos/${repo}"); then
  echo "Error: gh api failed for repos/${repo} — see gh error above" >&2
  exit 1
fi
```

**Verification note (unverified)**: The assumption that gh always writes error detail to stderr on non-zero exit holds for standard HTTP errors (404, 401, 403, 422) and auth failures. Network timeouts and certain rate-limit responses may not emit human-readable stderr — if silent failures are a concern, add `GH_DEBUG=1` in CI for additional diagnostics.

**jq `.[0] // ""` safety when all fields are `false`**: When the jq expression is `.[0] // ""` operating on a string extracted from an object (e.g., the result of selecting the first enabled merge flag), and all three flag fields (`allow_squash_merge`, `allow_rebase_merge`, `allow_merge_commit`) are `false`, the outer bash conditional then correctly enters the "no methods allowed" branch. The `.[0]` operates on a string/null (not a boolean), so `//` is safe here — it is NOT the boolean `//` falsy trap from Failure Mode 4. This was assessed by code reading, not local execution.

### Failure Mode 9: mock-gh Bash Function Pattern for Hermetic Integration Tests

Shell scripts that call `gh` by name cannot be tested with Python's `fake binary on PATH` pattern for subprocess isolation if the script is sourced into the same shell (rather than invoked as a subprocess). The fix is to define `gh` as a bash function in the test harness, then `export -f gh` to make it available in the sourced environment.

**Pattern (Python pytest calling bash via subprocess with mock function injected):**

```python
import subprocess
import textwrap

def test_choose_merge_flag_prefers_squash(tmp_path):
    """gh mock returns squash-only; script should emit --squash."""
    mock_gh = textwrap.dedent("""\
        gh() {{
          case "$1 $2" in
            "api repos/owner/repo")
              printf '%s\\n' '{{"allow_squash_merge":true,"allow_rebase_merge":false,"allow_merge_commit":false}}'
              ;;
            *)
              echo "Unexpected gh call: $*" >&2; return 1 ;;
          esac
        }}
        export -f gh
    """)
    script = mock_gh + "\nsource scripts/choose_merge_flag.sh\nchoose_merge_flag owner/repo\n"
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "--squash"
```

**Critical escaping note**: In Python f-strings / `textwrap.dedent`, curly braces in the bash function body (`{`, `}`) must be doubled (`{{`, `}}`) to avoid `KeyError` from `.format()`. If the string is a plain literal (no `.format()` call), doubling is still safest practice.

**Unverified assumption**: The `export -f gh` + `source script.sh` pattern was confirmed from team knowledge base (ProjectMnemosyne skill `bats-shell-test-patterns`) but was not run locally before this plan was written. The escaping of `{{`/`}}` in Python f-strings is critical and should be verified when the tests are first executed.

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
| `raw=$(gh api ... 2>&1)` piped into jq | Captured `gh api` output with `2>&1` to also capture gh's error messages; then piped `$raw` into `jq -r ...` | Non-JSON stderr (deprecation banner, debug trace, update notice) is prepended to the JSON blob; jq then fails to parse or returns empty/null; the script exits with a false "no merge methods" error even when the API call succeeds | Drop `2>&1` from command substitutions that capture JSON from `gh api`; capture stdout only (`raw=$(gh api ...)`); gh writes its own errors to stderr on non-zero exit automatically |
| Include `$raw` in error message when `2>&1` is removed | Kept `echo "Error: $raw" >&2` in the error path after removing `2>&1` | `$raw` is empty on failure (stdout-only capture); the error message is unhelpful | On `gh api` failure, reference `${repo}` (the URL/resource) in the error message — gh already emitted its own error to stderr; do not re-echo an empty variable |

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
| HomericIntelligence/ProjectHephaestus | Issue #1122 — planning session 2026-06-12 — `scripts/choose_merge_flag.sh:21` used `2>&1` merging gh stderr into `$raw`; any non-JSON line corrupts jq parse and causes false exit-1 "no merge methods" | `2>&1` stderr corruption of JSON capture (unverified — plan only, not yet executed) |
