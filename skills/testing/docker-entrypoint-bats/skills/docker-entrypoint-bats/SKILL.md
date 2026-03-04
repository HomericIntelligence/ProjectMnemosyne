---
name: docker-entrypoint-bats
description: "Skill: docker-entrypoint-bats. Use when adding BATS tests for Docker entrypoint scripts that handle credential chains, environment validation, and command dispatch."
category: testing
date: 2026-03-03
user-invocable: false
---

# Skill: docker-entrypoint-bats

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| PR | ProjectScylla #1341 |
| Issue | ProjectScylla #1159 |
| Objective | Add BATS test coverage for `docker/entrypoint.sh` (457 lines, 0% shell coverage) covering env validation, credential chain, and command dispatch |
| Outcome | Success — 57 new tests pass (22 validate_env, 10 credentials, 25 commands); all 3799 Python tests unaffected |
| Category | testing |

## When to Use

Trigger this skill when:

- A Docker entrypoint shell script needs BATS test coverage
- The script validates environment variables with complex regex patterns
- The script has a credential lookup chain (multiple file paths with priority ordering)
- The script dispatches to sub-commands (`--run-agent`, `--run-judge`, `--run`, etc.)
- Tests must avoid writing to root-owned paths (`/workspace`, `/output`, `/prompt`, `/mnt/...`)
- System-level credential files (e.g. `/tmp/host-creds/.credentials.json`) may exist on the test machine and pollute auth-failure tests
- The script uses `set -euo pipefail` with `((errors++))` — only the first error is ever reported (early exit from arithmetic returning 1)

## Results & Parameters

### Directory Layout

```
tests/shell/
└── docker/entrypoint/       # mirrors docker/entrypoint.sh path
    ├── helpers/
    │   └── common.bash      # setup_mocks() + clean_state()
    ├── mocks/
    │   ├── claude            # stub for claude CLI
    │   ├── timeout           # stub for timeout (supports exit-code injection)
    │   ├── git               # stub for git (clone creates target dir)
    │   ├── python            # stub for python
    │   └── python3 -> python # symlink
    ├── test_validate_env.bats    # 22 tests: validate_env()
    ├── test_credentials.bats     # 10 tests: ensure_clean_claude_environment()
    └── test_commands.bats        # 25 tests: main() dispatch
```

### Key Mock Patterns

**claude mock** — exits with `${CLAUDE_MOCK_EXIT:-0}`, prints `"claude 1.0.0-mock"` for `--version`:
```bash
#!/usr/bin/env bash
case "$1" in
    --version) echo "claude 1.0.0-mock"; exit 0 ;;
    *)         echo "mock agent output"; exit "${CLAUDE_MOCK_EXIT:-0}" ;;
esac
```

**timeout mock** — shifts away duration, passes through or exits with `${TIMEOUT_MOCK_EXIT}`:
```bash
#!/usr/bin/env bash
shift  # remove timeout duration
if [[ -n "${TIMEOUT_MOCK_EXIT:-}" ]]; then exit "${TIMEOUT_MOCK_EXIT}"; fi
exec "$@"
```

**git mock** — `clone` creates the target directory so downstream `ls -A` checks don't fail:
```bash
#!/usr/bin/env bash
case "$1" in
    clone)
        _target="${!#}"  # last argument = destination path
        mkdir -p "$_target" 2>/dev/null || true
        exit "${GIT_MOCK_CLONE_EXIT:-0}"
        ;;
    *) exit 0 ;;
esac
```

### HOME Override Pattern

Each test overrides `$HOME` to a temp dir so credential file operations don't pollute the real home:

```bash
setup() {
    setup_mocks
    clean_state
    _TMPDIR="$(mktemp -d)"
    export HOME="${_TMPDIR}/home"
    mkdir -p "${HOME}/.claude"
}

teardown() {
    rm -rf "${_TMPDIR}"
}
```

### System Credential Contamination Guard

Pre-existing `/tmp/host-creds/.credentials.json` on the test machine causes auth-failure tests to
see "credentials found" instead of the no-auth path. Back it up in `setup()` and restore in `teardown()`:

```bash
setup() {
    # ... HOME setup ...
    _HOST_CREDS_BACKUP=""
    if [[ -f /tmp/host-creds/.credentials.json ]]; then
        _HOST_CREDS_BACKUP="$(cat /tmp/host-creds/.credentials.json)"
        rm -f /tmp/host-creds/.credentials.json
    fi
}

teardown() {
    if [[ -n "${_HOST_CREDS_BACKUP:-}" ]]; then
        mkdir -p /tmp/host-creds
        echo "${_HOST_CREDS_BACKUP}" > /tmp/host-creds/.credentials.json
    fi
    rm -rf "${_TMPDIR}"
}
```

### Root-Path Skip Pattern

Scripts hard-coding `/workspace`, `/output`, `/prompt`, `/mnt/claude-creds` can't be tested on
non-root machines. Skip gracefully:

```bash
@test "--run-agent success path writes result.json" {
    if ! mkdir -p /workspace /output /prompt 2>/dev/null; then
        skip "Cannot create /workspace|/output|/prompt (not running as root)"
    fi
    echo "test task" > /prompt/task.md
    # ...
}
```

These tests WILL run on CI where the container runs as root.

### Credential Function Invocation

`ensure_clean_claude_environment()` is called by `python`, `python3`, `bash`, `sh`, `--run-agent`,
`--run-judge`, `--run`, and unknown commands — but NOT by `--validate`.

To test credential behavior without running a full agent/judge, use python passthrough:

```bash
_run_cred_check() {
    run bash "$SCRIPT" python --version
}
```

This calls `ensure_clean_claude_environment` then `exec`s the mock python which exits 0.

### `set -e` with `((errors++))` — Only First Error Reported

When `validate_env()` uses `((errors++))` to count errors, bash's `set -e` exits the script
when `errors` increments from 0 to 1 (arithmetic returns exit code 1). This means:

- Only the first validation error is ever logged
- "Validation failed with N error(s)" is NEVER printed to stdout (the script exits before reaching it)
- Tests must NOT assert `[[ "$output" == *"Validation failed"* ]]`
- Tests SHOULD assert `[ "$status" -eq 1 ]` and `[[ "$output" == *"[ERROR]"* ]]`

## Verified Workflow

### 1. Read the script and identify testing surfaces

```bash
# Identify: external commands, hard-coded paths, env vars, exit codes
grep -n 'exit \|exec \|cd \|mkdir \|chmod \|cp ' docker/entrypoint.sh
```

For `docker/entrypoint.sh`, key surfaces were:
- `validate_env()` — regex checks on TIER, RUN_NUMBER; auth check
- `ensure_clean_claude_environment()` — credential chain with 3 paths + env var fallback
- `main()` — case dispatch with 8+ branches

### 2. Compute the SCRIPT path

```python
import os
print(os.path.relpath('docker/entrypoint.sh', 'tests/shell/docker/entrypoint'))
# → ../../../../docker/entrypoint.sh
```

Use in `.bats` files:
```bats
SCRIPT="$(git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel)/docker/entrypoint.sh"
```

### 3. Create helpers and mocks

```bash
mkdir -p tests/shell/docker/entrypoint/{helpers,mocks}
# Write helpers/common.bash, mocks/claude, mocks/timeout, mocks/git, mocks/python
chmod +x tests/shell/docker/entrypoint/mocks/{claude,timeout,git,python}
cd tests/shell/docker/entrypoint/mocks && ln -sf python python3
```

### 4. Split tests by functional area

Three files keeps each under ~150 lines and allows targeted runs:
- `test_validate_env.bats` — pure env var validation, no credential side effects
- `test_credentials.bats` — credential chain, uses python passthrough to trigger
- `test_commands.bats` — main() dispatch, includes HOME/host-creds contamination guard

### 5. Run tests iteratively

```bash
pixi run test-shell 2>&1 | grep -E "(ok |not ok |# )"
# Fix failures, re-run until all pass
```

### 6. Update CI workflow

Add explicit path to `shell-test.yml` `pull_request.paths` (alongside `**/*.sh`):

```yaml
paths:
  - "**/*.sh"
  - "tests/shell/**"
  - "docker/entrypoint.sh"   # explicit for clarity
  - ".github/workflows/shell-test.yml"
```

## Failed Attempts

### Attempt 1 — Testing credentials via `--validate`

**What happened**: Initial tests for `ensure_clean_claude_environment()` used `bash "$SCRIPT" --validate`,
expecting to see credential messages. But `--validate` only calls `validate_env()` — it never calls
`ensure_clean_claude_environment()`.

**Diagnosis**: Read the `main()` case statement — `--validate` routes directly to `validate_env`, not to
`ensure_clean_claude_environment`.

**Fix**: Use `python --version` passthrough instead, which calls `ensure_clean_claude_environment` then
`exec`s the mock python. This tests the credential path without needing `/workspace` or `/output`.

### Attempt 2 — `mkdir -p /workspace` in test setup fails with permission denied

**What happened**: Tests creating `/workspace`, `/output`, `/prompt` for `--run-agent`/`--run-judge` paths
failed with `mkdir: cannot create directory '/workspace': Permission denied` because the test runner
isn't root.

**Fix**: Wrap with `if ! mkdir -p /workspace /output /prompt 2>/dev/null; then skip "..."; fi`.
These tests will skip on developer machines but run correctly on CI where containers run as root.

### Attempt 3 — System `/tmp/host-creds/.credentials.json` contaminates auth tests

**What happened**: The development machine had a real `/tmp/host-creds/.credentials.json`. Tests
expecting no-auth failures were silently using these credentials, making `--run-judge` report
"MODEL is not set" instead of "No authentication".

**Diagnosis**: `ensure_clean_claude_environment()` checks `/tmp/host-creds/.credentials.json` first in the
priority chain. Real credentials on the dev machine invisibly satisfied the auth check.

**Fix**: Backup and remove `/tmp/host-creds/.credentials.json` in `setup()`, restore in `teardown()`.
Added to both `test_credentials.bats` and `test_commands.bats`.

### Attempt 4 — Asserting "Validation failed" message after error accumulation

**What happened**: Test `"no auth + invalid TIER → two errors reported"` asserted:
`[[ "$output" == *"Validation failed"* ]]`. This always failed — the line was never printed.

**Diagnosis**: `validate_env()` uses `((errors++))`. Under `set -euo pipefail`, when `errors` goes from
0 → 1, the arithmetic expression exits with code 1, triggering `set -e` to abort the function.
The `"Validation failed with ${errors} error(s)"` line is never reached.

**Fix**: Change assertion to `[[ "$output" == *"[ERROR]"* ]]` — the error log line before the
`((errors++))` is always printed.

## Related Skills

- `bats-shell-testing` — Original BATS setup skill (preflight_check.sh, gh/git mocking patterns)
- `credential-mount-context-manager` — Credential chain architecture for Docker/WSL2 containers
