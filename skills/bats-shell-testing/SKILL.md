# Skill: bats-shell-testing

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| PR | #900 |
| Objective | Add BATS (Bash Automated Testing System) test suite for `preflight_check.sh` covering 5 behavioral edge cases, with mocked `gh`/`git` commands to avoid live API calls |
| Outcome | Success — 5/5 tests pass, pre-commit hooks pass, CI workflow added |
| Category | testing |

## When to Use

Trigger this skill when:

- A shell script (`.sh`) has no automated tests and edge cases have been identified in review/issues
- Tests must avoid live external calls (API, git remotes) — requiring mock stubs
- The script uses `set -uo pipefail` and you need to verify `grep`/`jq` exit-code behavior in combination
- You need a runnable BATS suite integrated with `pixi run` and triggered from GitHub Actions CI
- Edge cases include: different exit codes (0 vs 1), warning vs critical paths, empty vs populated command output

## Results & Parameters

### Directory Layout

```
tests/shell/
└── skills/github/gh-implement-issue/   # mirror the script's location under tests/claude-code/
    ├── helpers/
    │   └── common.bash                 # setup_mocks() + clean_state()
    ├── mocks/
    │   ├── gh                          # stub for gh CLI
    │   └── git                         # stub for git
    └── test_preflight_check.bats       # 5 test cases
```

### Mock Pattern

Mock stubs live in `mocks/` and are injected via PATH prepend. Each stub reads environment variables:

```bash
# mocks/gh — behavior controlled by env vars
case "$1 $2" in
    "issue view")
        if [[ "${*}" == *"--json"* ]]; then
            echo "${GH_MOCK_ISSUE_STATE:-{...default open state...}}"
        else
            echo "${GH_MOCK_ISSUE_COMMENTS:-}"
        fi
        ;;
    "pr list")
        echo "${GH_MOCK_PR_JSON:-[]}"
        ;;
esac
```

```bash
# mocks/git — behavior controlled by env vars
case "$1" in
    log)      echo "${GIT_MOCK_LOG:-}"      ;;
    worktree) echo "${GIT_MOCK_WORKTREE:-}" ;;
    branch)   echo "${GIT_MOCK_BRANCH:-}"   ;;
    *)        exit 0 ;;
esac
```

### Helper Pattern

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

### pixi.toml Integration

```toml
[tasks]
test-shell = "bats tests/shell/ --recursive"

[feature.dev.dependencies]
bats-core = ">=1.11.0"   # available on conda-forge
```

### CI Workflow (`.github/workflows/shell-test.yml`)

```yaml
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

### Test Case Pattern

```bats
@test "<scenario description>" {
    export GH_MOCK_ISSUE_STATE='{"state":"CLOSED","title":"Done","closedAt":"2024-01-01T00:00:00Z"}'
    # set other env vars as needed...

    run bash "$SCRIPT" 800

    [ "$status" -eq 1 ]
    [[ "$output" == *"[STOP]"* ]]
}
```

## Verified Workflow

### 1. Identify the script and its external dependencies

Read the script under test. Note every external command call (`gh`, `git`, `jq`, etc.):

- Commands that hit the network or filesystem need mocking
- Pure utilities already on the system (`jq` was available system-wide here) can be left real
- Note which env vars or arguments control behavior

### 2. Create the directory structure

```bash
mkdir -p tests/shell/skills/<category>/<skill>/mocks
mkdir -p tests/shell/skills/<category>/<skill>/helpers
```

Mirror the path structure under `tests/shell/` that parallels `tests/claude-code/` for discoverability.

### 3. Write mock stubs (chmod +x)

One stub per external command. Use `case "$1"` or `case "$1 $2"` for subcommand dispatch.
Default each env var with `${VAR:-default}` so tests that don't set it get a safe no-op.

```bash
chmod +x tests/shell/.../mocks/gh tests/shell/.../mocks/git
```

### 4. Write the BATS helper

Keep `common.bash` minimal — just `setup_mocks()` and `clean_state()`. Compute the mocks path
relative to the helper using `${BASH_SOURCE[0]}` so it works regardless of CWD.

### 5. Compute the correct relative path to the script under test

Use Python to compute the relative path from the test file's directory to the target script:

```python
import os
test_dir = os.path.dirname("tests/shell/.../test_foo.bats")
target   = "tests/claude-code/.../scripts/foo.sh"
print(os.path.relpath(target, test_dir))
# -> ../../../../claude-code/.../scripts/foo.sh
```

Set this in the test file using `$BATS_TEST_FILENAME`:

```bats
SCRIPT="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)/../../../../claude-code/.../foo.sh"
```

### 6. Write test cases following the 5-scenario template

For each scenario:
- `setup()` calls `setup_mocks` + `clean_state`
- Export only the env vars needed for this scenario
- Use `run bash "$SCRIPT" <issue-number>`
- Assert `$status` and key strings in `$output`

### 7. Run locally before committing

```bash
bats tests/shell/ --recursive
```

All tests must pass before staging.

### 8. Add bats-core to pixi.toml

```toml
[feature.dev.dependencies]
bats-core = ">=1.11.0"
```

Verify it's on conda-forge first: `pixi search 'bats*'`

### 9. Add CI workflow (shell-test.yml)

Trigger only on `.sh` file changes and `tests/shell/**` for fast CI.

### 10. Commit, push, PR, auto-merge

```bash
git add pixi.toml .github/workflows/shell-test.yml tests/shell/
git commit -m "feat(tests): Add BATS test suite for <script>.sh\n\nCloses #<issue>"
git push -u origin <branch>
gh pr create --title "feat(tests): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

### Attempt 1 — Wrong relative path from test file to script

**What happened**: The initial path in `SCRIPT="..."` used `../../../../../../tests/claude-code/...` but
the test file is only 5 levels deep in `tests/shell/skills/github/gh-implement-issue/`, not 8.
The result was `No such file or directory` for every test, all reporting status 127 (not found).

**Diagnosis**: Counted directory levels manually instead of computing them.

**Fix**: Use Python `os.path.relpath()` to compute the correct relative path:

```python
import os
print(os.path.relpath(
    "tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh",
    "tests/shell/skills/github/gh-implement-issue"
))
# -> ../../../../claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh
```

**Key lesson**: Never count `../` steps manually for paths more than 3 levels deep. Always compute with
`os.path.relpath()`.

### Attempt 2 — PREFLIGHT_SCRIPT defined in helper but not used

**What happened**: The initial `common.bash` defined `PREFLIGHT_SCRIPT` variable pointing to the script.
But the BATS file `load`s the helper before the test-level `SCRIPT` variable is set, and `BASH_SOURCE[0]`
inside the helper resolves to the helper file's path, not the test file's path. The relative traversal
in the helper was wrong for a different reason than Attempt 1.

**Fix**: Define `SCRIPT` directly in the test file using `$BATS_TEST_FILENAME` (which resolves correctly
in each test's context). Keep `common.bash` only for `setup_mocks()` and `clean_state()`.

### Attempt 3 — bats not available via apt without sudo / npm without root

**What happened**: `sudo apt-get install bats` required a password. `npm install -g bats` failed due to
permissions.

**Fix**: Install `bats-core` directly from GitHub into `~/.local`:

```bash
git clone --depth 1 https://github.com/bats-core/bats-core.git /tmp/bats-install/bats-core
/tmp/bats-install/bats-core/install.sh ~/.local
# bats is now at ~/.local/bin/bats
```

For CI, use pixi with `bats-core` from conda-forge — it's available as `bats-core = ">=1.11.0"`.

## Related Skills

- `shellcheck-scope-templates` — ShellCheck integration patterns
- `add-shell-log-level` — Shell script structured logging
- `git-worktree-collision-fix` — E2E testing with worktree isolation
