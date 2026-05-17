---
name: testing-bats-fake-binary-shim-with-lookup-file
description: 'Skill: testing-bats-fake-binary-shim-with-lookup-file. Use when stubbing external CLI binaries (gh, kubectl, aws, curl) under BATS with per-test configurable responses.'
category: testing
date: 2026-05-17
version: 1.0.0
user-invocable: false
---
# Skill: testing-bats-fake-binary-shim-with-lookup-file

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-05-17 |
| PR | HomericIntelligence/ProjectHephaestus#421 |
| Objective | Stub out external CLI binaries (like `gh`, `kubectl`, `aws`) under BATS shell tests using a per-test fake binary on PATH, with configurable per-call responses passed from the BATS test to the fake binary |
| Outcome | Success — 11 BATS tests using this exact pattern, all green in CI |
| Category | testing |
| Verification | verified-ci |

## When to Use

Trigger this skill when:

1. Writing BATS tests for a shell function that shells out to `gh`, `kubectl`, `aws`, `curl`, etc.
2. You need per-test configurable responses without recompiling or rebuilding mocks.
3. You are tempted to reach for `declare -A` to map argv → response — DON'T; use a lookup file.
4. You need orthogonal failure-mode toggles (e.g. simulate a repo failing) alongside the response table.

## Key Insight

**Bash associative arrays (`declare -A`) cannot be exported to subprocesses.** If you try
`export FAKE_GH_RESPONSES_<key>=value` for each key, you end up needing to enumerate keys,
which is brittle and pollutes the environment.

**The fix:** write a simple `key=value` lookup file from the BATS test, export the FILE PATH
(a plain scalar), and have the fake binary read the file with `awk`. Plain scalar env vars
(single string or space-separated list) export cleanly and complement the lookup file for
boolean/failure-mode toggles.

## Verified Workflow

1. In `setup()`:
   - `mktemp -d` for the fake binary directory.
   - Write the fake script (heredoc), `chmod +x` it.
   - Initialise the lookup file (`: > "$FAKE_GH_COUNTS"`).
   - Prepend the directory to `PATH` and `export PATH` + the file-path env var + any scalar toggles.
2. The fake binary:
   - Parses argv, extracts the discriminating key (e.g. `--repo` value).
   - Uses `awk -F= -v n="$key" '$1==n {print $2; exit}' "$LOOKUP_FILE"` to fetch its configured response.
   - Falls back to a sensible default if the key is absent.
3. The BATS test uses a helper like `write_counts()` to populate the lookup file per-test, then runs the function under test with `run`.
4. Use a space-separated env var (e.g. `FAKE_GH_FAIL_REPOS="Foo Bar"`) for orthogonal toggles like simulated failures — these export cleanly because they are strings, not associative arrays.
5. In `teardown()`: `rm -rf` the mktemp dir so fake binaries don't leak into sibling tests.

### Quick Reference

Real example from `tests/shell/scripts/test_repo_ordering.bats` in ProjectHephaestus:

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

teardown() {
    rm -rf "$GH_FAKE_DIR"
}

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `declare -A FAKE_GH_COUNTS; export FAKE_GH_COUNTS` then read from fake binary | Bash cannot export associative arrays to subprocesses — fake binary sees an empty array | Associative arrays are shell-local; never crossable to a forked subprocess |
| 2 | Hardcoding responses inside the fake binary script | Need to regenerate the script per test or use case statements that explode in size | Doesn't scale and couples test setup to fake-binary source |
| 3 | Setting one env var per key (`FAKE_GH_COUNT_Foo=10`) | Requires test to enumerate keys, fake binary to know them, and pollutes env | Loses generality — only viable for very small fixed key sets |

## Results & Parameters

- **Lookup file format:** `key=value\n` per line; `awk -F=` parses cleanly even when values contain spaces (as long as the key has no `=`).
- **Failure-mode flags:** use a space-separated scalar env var (`FAKE_X_FAIL="a b c"`) and iterate with `for x in $VAR; do ... done`.
- **Defensive shell settings:** always `set -uo pipefail` in the fake binary so a missing env var aborts loudly instead of silently doing the wrong thing.
- **Teardown is mandatory:** `rm -rf` the mktemp dir — leaving fake binaries on `PATH` leaks into sibling tests.
- **Discriminating key:** typically extracted via argv parsing (e.g. value after `--repo`). Use `${var##*/}` to strip prefixes like `Org/`.

## Verified On

- **HomericIntelligence/ProjectHephaestus PR #421** — 11 BATS tests using this exact pattern, all green in CI.

## Related Skills

- `bats-shell-testing` — general BATS test-suite scaffolding and `pixi`/CI integration.
- `docker-entrypoint-bats` — BATS testing of container entrypoints.
