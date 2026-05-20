---
name: bats-shell-test-patterns
description: "Use when: (1) adding BATS test coverage to any shell script (preflight check, Docker entrypoint, CLI wrapper), (2) stubbing external CLI binaries (gh, kubectl, aws, curl, git) under BATS with per-test configurable responses via fake-binary shims, (3) a recursive glob in a bash test runner silently skips files at depth >=3, (4) replacing `|| true` in bash test helpers with an observable captured-rc pattern that satisfies a no-silent-failures lint guard."
category: testing
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: bats-shell-test-patterns.history
tags:
  - bats
  - bash
  - shell-testing
  - fake-binary
  - shim
  - mocking
  - globstar
  - captured-rc
  - docker-entrypoint
  - pixi
  - ci
---

# Skill: BATS Shell Test Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Consolidated BATS shell-testing patterns: suite scaffolding, fake-binary shims, globstar pitfall, and captured-rc pattern |
| **Outcome** | Success — synthesised from 5 validated skills covering preflight scripts, Docker entrypoints, CLI wrappers, and test infrastructure |
| **Category** | testing |

## When to Use

Trigger this skill when:

1. A shell script (`.sh`) has no automated tests and edge cases must be covered with BATS
2. Tests must avoid live external calls (API, git remotes) — requiring mock stubs or fake-binary shims
3. Writing BATS tests for a Docker entrypoint that validates env vars, chains credentials, and dispatches sub-commands
4. Stubbing `gh`, `kubectl`, `aws`, `curl`, or `git` with per-test configurable responses (look up the fake-binary shim pattern)
5. A bash test runner uses `dir/**/*.ext` and coverage is suspiciously low — files at depth >=3 are silently skipped
6. A test helper previously used `cmd || true` and the repo now enforces a no-silent-failures lint guard

## Verified Workflow

### 1. Suite scaffolding — standard layout

Mirror the script's location under `tests/shell/`:

```text
tests/shell/
└── <category>/<script-name>/
    ├── helpers/
    │   └── common.bash          # setup_mocks() + clean_state()
    ├── mocks/
    │   ├── gh                   # stub for gh CLI
    │   ├── git                  # stub for git
    │   └── <other-cmd>          # one stub per external command
    └── test_<script>.bats       # test cases
```

### 2. Basic env-var mock pattern

Stubs live in `mocks/` and respond via exported env vars:

```bash
# mocks/gh — subcommand dispatch via env vars
case "$1 $2" in
    "issue view")
        if [[ "${*}" == *"--json"* ]]; then
            echo "${GH_MOCK_ISSUE_STATE:-{}}"
        else
            echo "${GH_MOCK_ISSUE_COMMENTS:-}"
        fi
        ;;
    "pr list") echo "${GH_MOCK_PR_JSON:-[]}" ;;
esac

# mocks/git — simple env-var responses
case "$1" in
    log)      echo "${GIT_MOCK_LOG:-}"      ;;
    worktree) echo "${GIT_MOCK_WORKTREE:-}" ;;
    branch)   echo "${GIT_MOCK_BRANCH:-}"   ;;
    *)        exit 0 ;;
esac
```

```bash
# helpers/common.bash
_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_MOCKS_DIR="${_HELPERS_DIR}/../mocks"

setup_mocks() { export PATH="${_MOCKS_DIR}:${PATH}"; }

clean_state() {
    unset GH_MOCK_ISSUE_STATE GH_MOCK_PR_JSON GH_MOCK_ISSUE_COMMENTS \
          GIT_MOCK_LOG GIT_MOCK_WORKTREE GIT_MOCK_BRANCH || true
}
```

### 3. Fake-binary shim with lookup file (scalable pattern)

When env-var mocks get unwieldy (many keys, per-test configurable responses), use a lookup file:

```bash
setup() {
    GH_FAKE_DIR="$(mktemp -d)"
    FAKE_GH_COUNTS="$GH_FAKE_DIR/counts"
    : > "$FAKE_GH_COUNTS"
    FAKE_GH_FAIL_REPOS=""

    cat > "$GH_FAKE_DIR/gh" <<'FAKE'
#!/usr/bin/env bash
set -uo pipefail
repo=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo) repo="$2"; shift 2 ;;
        *) shift ;;
    esac
done
name="${repo##*/}"
for failed in ${FAKE_GH_FAIL_REPOS:-}; do
    [[ "$failed" == "$name" ]] && { echo "fail" >&2; exit 1; }
done
count=$(awk -F= -v n="$name" '$1==n {print $2; exit}' "$FAKE_GH_COUNTS" 2>/dev/null)
printf '%s\n' "${count:-0}"
FAKE
    chmod +x "$GH_FAKE_DIR/gh"
    PATH="$GH_FAKE_DIR:$PATH"
    export PATH FAKE_GH_COUNTS FAKE_GH_FAIL_REPOS
}

teardown() { rm -rf "$GH_FAKE_DIR"; }

write_counts() {
    : > "$FAKE_GH_COUNTS"
    for pair in "$@"; do printf '%s\n' "$pair" >> "$FAKE_GH_COUNTS"; done
}

@test "sort: typical ordering" {
    write_counts Foo=10 Bar=2 Baz=5
    run sort_repos_by_open_count "TestOrg" Foo Bar Baz
    [ "$status" -eq 0 ]
    [ "$output" = $'Bar\nBaz\nFoo' ]
}
```

**Key insight**: Bash associative arrays cannot be exported to subprocesses. Use a `key=value` lookup file; export only the file path (a plain scalar).

### 4. Docker entrypoint patterns

Override `$HOME` and guard against system credential contamination:

```bash
setup() {
    setup_mocks; clean_state
    _TMPDIR="$(mktemp -d)"
    export HOME="${_TMPDIR}/home"
    mkdir -p "${HOME}/.claude"
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

Skip tests that require root-owned paths (`/workspace`, `/output`) on non-root machines — they WILL run in Docker CI containers:

```bash
@test "--run-agent success path" {
    if ! mkdir -p /workspace /output /prompt 2>/dev/null; then
        skip "Cannot create /workspace|/output|/prompt (not running as root)"
    fi
    # ...
}
```

**`set -e` + `((errors++))` gotcha**: When `validate_env()` uses `((errors++))`, bash's `set -e` exits when `errors` increments from 0→1 (arithmetic returns exit code 1). Only the first validation error is ever logged; assert `[ "$status" -eq 1 ]` and `[[ "$output" == *"[ERROR]"* ]]`, NOT `*"Validation failed"*`.

Useful Docker entrypoint mocks:

```bash
# timeout mock — shifts away duration, supports exit-code injection
shift  # remove timeout duration
if [[ -n "${TIMEOUT_MOCK_EXIT:-}" ]]; then exit "${TIMEOUT_MOCK_EXIT}"; fi
exec "$@"

# git clone mock — creates destination dir so downstream ls -A checks don't fail
case "$1" in
    clone)
        _target="${!#}"
        mkdir -p "$_target" 2>/dev/null || true
        exit "${GIT_MOCK_CLONE_EXIT:-0}"
        ;;
    *) exit 0 ;;
esac
```

### 5. Globstar recursive-glob pitfall

Replace `**` globs with `find | mapfile` for depth-safe test discovery:

```bash
# WRONG — silently skips files at depth >=3 without shopt -s globstar
for test_file in tests/**/*.mojo; do run "$test_file"; done

# RIGHT — find recurses regardless of bash shell options
mapfile -t test_files < <(
    find tests -name "test_*.mojo" \
        -not -path "*/helpers/*" \
        | sort
)
echo "Discovered ${#test_files[@]} test files"
for test_file in "${test_files[@]}"; do
    run "$test_file" || exit 1
done
```

**Why**: In bash, `**` is equivalent to `*` unless `shopt -s globstar` is active. Justfiles, Makefiles, and CI scripts often run a fresh bash without it.

### 6. Captured-rc pattern (replace `|| true`)

```bash
# Pattern 1: just capture rc, no debug surface
_rc=0; cmd || _rc=$?; : $((_rc))

# Pattern 2: capture rc + stdout
_rc=0; output=$(cmd) || _rc=$?

# Pattern 3: capture + debug log (recommended for test helpers)
_rc=0; cmd || _rc=$?
if (( _rc != 0 )); then echo "DEBUG: cmd failed rc=$_rc" >&2; fi
```

Use this when a test helper calls a command whose failure is expected on some paths. The `|| true` pattern discards the exit code; this pattern preserves it for transcript debugging while satisfying a forbid-`|| true` lint guard.

### 7. pixi.toml + CI integration

```toml
[tasks]
test-shell = "bats tests/shell/ --recursive"

[feature.dev.dependencies]
bats-core = ">=1.11.0"   # available on conda-forge
```

```yaml
# .github/workflows/shell-test.yml
on:
  pull_request:
    paths:
      - "**/*.sh"
      - "tests/shell/**"
      - ".github/workflows/shell-test.yml"
  push:
    branches: [main]

jobs:
  bats:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - run: pixi run test-shell
```

### Quick Reference

| Task | Pattern |
|------|---------|
| PATH-inject mocks | `export PATH="${_MOCKS_DIR}:${PATH}"` in `setup_mocks()` |
| Per-test configurable fake binary | lookup file: `awk -F= -v n="$key" '$1==n {print $2; exit}' "$LOOKUP_FILE"` |
| Failure-mode toggle | space-separated scalar: `FAKE_X_FAIL="a b c"` |
| Teardown fake binaries | `rm -rf "$FAKE_DIR"` in `teardown()` — mandatory |
| Recursive test discovery | `mapfile -t arr < <(find tests -name 'test_*.ext' \| sort)` |
| Suppress abort, keep rc | `_rc=0; cmd \|\| _rc=$?; : $((_rc))` |
| Docker HOME isolation | `export HOME="$(mktemp -d)/home"` |
| Script path from test file | `SCRIPT="$(git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel)/<path>"` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `declare -A FAKE_GH_COUNTS; export FAKE_GH_COUNTS` then read from fake binary | Bash cannot export associative arrays to subprocesses — fake binary sees empty array | Associative arrays are shell-local; use a key=value lookup file instead |
| 2 | Hardcoding responses inside the fake binary script | Need to regenerate the script per test or use exploding case statements | Doesn't scale; couples test setup to fake-binary source |
| 3 | Setting one env var per key (`FAKE_GH_COUNT_Foo=10`) | Requires test to enumerate keys and pollutes env | Loses generality; only viable for very small fixed key sets |
| 4 | `for f in tests/**/*.mojo` (no shopt) | Bash treats `**` as `*` without `shopt -s globstar`; only matches depth 2 — silent | `**` is opt-in in bash; never assume it recurses |
| 5 | `shopt -s globstar` at top of recipe | Functional in that recipe but a footgun — copy-pasted loops elsewhere silently regress | Encode recursion in the command (`find`), not in shell state |
| 6 | `find ... \| while read f; do ...; done` | Pipe creates subshell — counters and exit codes don't propagate to parent | Use `mapfile -t arr < <(find ...)` with process substitution |
| 7 | `for f in $(find ...)` | Splits on IFS — breaks on paths containing spaces | `mapfile` + `"${arr[@]}"` is whitespace-safe |
| 8 | `cmd \|\| true` in test helpers | Discards exit code; conflicts with forbid-`\|\| true` lint guards | Capture rc with `_rc=0; cmd \|\| _rc=$?` — preserves observability |
| 9 | `cmd \|\| :` as cosmetic alternative to `\|\| true` | Functionally identical; lint guard should catch it too | Don't paper over the policy with synonyms; refactor the structure |
| 10 | `set +e; cmd; rc=$?; set -e` to avoid abort | Works but verbose and requires careful scoping | Use `\|\| _rc=$?` capture; reserve `set +e` for multi-command blocks |
| 11 | Asserting `*"Validation failed"*` with `((errors++))` under `set -e` | `set -e` exits when `errors` goes from 0 to 1 (arithmetic returns 1); message never printed | Assert `[ "$status" -eq 1 ]` and `*"[ERROR]"*` only |

## Results & Parameters

- **bats-core version**: `>=1.11.0` (available on conda-forge)
- **Lookup file format**: `key=value\n` per line; `awk -F=` parses cleanly
- **Failure-mode flags**: space-separated scalar env var; iterate with `for x in $VAR; do ... done`
- **Teardown is mandatory**: `rm -rf` the mktemp dir — fake binaries on `PATH` leak into sibling tests
- **Split large entrypoints**: 3 files by functional area (validate env, credentials, commands) keeps each under ~150 lines
- **Verified coverage**: 57 Docker entrypoint tests (22 validate_env, 10 credentials, 25 commands); 11 fake-binary shim tests; 83 Myrmidons bats tests; 298/298 Mojo test files discovered after `find|mapfile` fix

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1341 — Docker entrypoint BATS coverage | 57 new tests; all 3799 Python tests unaffected |
| HomericIntelligence/ProjectHephaestus | PR #421 — fake-binary shim | 11 BATS tests using lookup-file pattern, all green in CI |
| HomericIntelligence/Myrmidons | PR #711 — captured-rc refactor | 83 bats + 51 stand-alone tests; lint guard passes |
| HomericIntelligence/ProjectOdyssey | PR #5389 — globstar fix | `tests/**/*.mojo` matched 41/298; `find\|mapfile` reached 298/298 |
