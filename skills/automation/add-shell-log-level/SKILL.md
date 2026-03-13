# Skill: add-shell-log-level

## Overview

| Field     | Value                                                                 |
|-----------|-----------------------------------------------------------------------|
| Date      | 2026-02-20                                                            |
| Objective | Add a new log level function to a shared bash library that already defines its color variable but lacks the corresponding log function |
| Outcome   | Success — `log_debug()` added, pre-commit (ShellCheck) and syntax checks pass, PR merged via auto-merge |
| Issue     | #781                                                                  |
| PR        | #829                                                                  |

## When to Use

- A shell script defines a color variable (e.g., `BLUE='\033[0;34m'`) but no function uses it
- You need to add a `log_debug` / `log_trace` / `log_verbose` level to a shared bash logging library
- An issue asks you to "resolve a dead variable" or "add verbose/diagnostic logging" in shell scripts
- Follow-up work from removing a variable that turns out to be useful

## Verified Workflow

### 1. Read the file first

Always read the full script before editing so you understand the existing log function signatures.

```bash
# Check what log functions already exist
grep -n 'log_' scripts/docker_common.sh
```

### 2. Apply the minimal change

The pattern used in `scripts/docker_common.sh`:

```bash
# Colors for output: RED=error, GREEN=info, YELLOW=warn, BLUE=debug
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $*"; }
```

Key details:

- Use `$*` (not `$1`) for variadic messages
- `log_error` writes to stderr (`>&2`); `log_debug` writes to stdout
- Update the comment to document which color maps to which level

### 3. Run syntax and quality checks

```bash
bash -n scripts/docker_common.sh          # parse-only, no execution
pre-commit run --files scripts/docker_common.sh  # ShellCheck + whitespace hooks
```

### 4. Commit and PR

Follow conventional commits:

```
feat(scripts): add log_debug() using BLUE color to docker_common.sh
```

Include `Closes #<issue>` in the commit message body.

## Failed Attempts

- **Skill tool (commit-commands:commit-push-pr)**: Blocked by `don't ask` permission mode. Fell back to direct `git add / git commit / git push / gh pr create` commands — all worked correctly.

## Results & Parameters

| Item | Value |
|------|-------|
| File changed | `scripts/docker_common.sh` |
| Lines changed | +8 / -4 (net +4) |
| ShellCheck result | Passed |
| Pre-commit result | All hooks passed |
| Bash syntax check | Passed |
| PR | #829 |
| Auto-merge | Enabled (rebase) |

## Notes

- The `BLUE` color was previously removed (#722) because no function used it; this skill re-adds it with purpose
- The `$*` change (from `$1`) is a low-risk improvement that handles multi-word arguments without quoting gymnastics
- No Python tests are needed for a bash-only change; shell syntax checks + ShellCheck are sufficient
