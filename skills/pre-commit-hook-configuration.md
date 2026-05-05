---
name: pre-commit-hook-configuration
description: "Use when: (1) ruff or other linter hooks run on hardcoded directories instead of staged files, (2) aligning pre-commit hook versions with pixi-resolved tool versions, (3) updating hook versions with autoupdate, (4) adding a language: pygrep regex hook to catch forbidden patterns, (5) evaluating whether a hook should use pass_filenames: true or false, (6) writing pytest tests to verify pre-commit hook YAML configuration, (7) pre-commit hook uses SCRIPT_DIR/../ to find REPO_ROOT but is installed as .git/hooks/pre-commit in a test repo — resolves to .git/ not repo root, (8) SKIP_TESTS env var needed to prevent test-suite step from running in temporary test repos, (9) just command finds Justfile in a parent directory instead of the test repo, (10) a Go-based hook (e.g. gitleaks) fails to build from source because the system Go version is too old, (11) detect-private-key hook false-fires on test fixtures, TLS unit tests, or k8s secret manifests containing fake/test PEM headers"
category: ci-cd
date: 2026-04-27
version: 2.3.0
user-invocable: false
verification: verified-ci
tags: [pre-commit, hooks, bats, shell-testing, repo-root, test-isolation, gitleaks, golang, prebuilt-binary, detect-private-key, false-positive, tls, kubernetes, test-fixtures]
history: pre-commit-hook-configuration.history
absorbed: [pre-commit-detect-private-key-fixture-exclusion]
---

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-29 |
| Objective | Consolidated pre-commit hook configuration patterns: pass_filenames, version alignment, pygrep hooks, maintenance, config testing, and REPO_ROOT resolution in test repos |
| Outcome | v2.1.0: Added REPO_ROOT resolution fix for hooks installed in .git/hooks/ of test repos; all 332 unit tests pass, CI green. v2.2.0: Added Go-based hook build failure workaround using pre-built binary downloads |
| Verification | verified-ci |
| History | [changelog](./pre-commit-hook-configuration.history) |

## When to Use

- Pre-commit ruff (or other linter) hooks run on hardcoded directories instead of staged files
- Hook `entry` field contains hardcoded paths like `pixi run ruff format src/ scripts/`
- PR review feedback requests `pass_filenames: true` fix for formatter/linter hooks
- A hook has `pass_filenames: false` and the rationale is undocumented
- Pre-commit hook `rev:` is pinned to an old version while `pixi.toml` has been upgraded
- `pixi run mypy` reports different errors than `git commit` triggers
- A periodic manual `grep` audit should be automated at commit time with `language: pygrep`
- Enabling or verifying YAML/markdown/linting hooks in pre-commit configuration
- Updating pre-commit hook versions to latest releases
- Writing pytest tests to verify hook YAML config (skip lists, `files:` patterns, flag presence)
- A security scanner hook (bandit, semgrep) has a `--skip` list that should be intentional and documented
- Pre-commit hook uses `SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"` and `REPO_ROOT="${SCRIPT_DIR}/.."` — but when the hook is installed as `.git/hooks/pre-commit` in a test repo, `SCRIPT_DIR` resolves to `.git/hooks/` and `REPO_ROOT` resolves to `.git/` (not the repo root)
- bats test suite step inside the hook finds `Justfile` in a parent directory instead of the test repo — hook runs unrelated test suites from parent directories
- `SKIP_TESTS=1` env var pattern needed to allow bats tests to invoke the hook without triggering the test-suite step inside the hook
- A Go-based pre-commit hook (e.g., gitleaks) fails to build from source because the system Go version is too old for the hook's `go.mod` requirement
- `pre-commit` with `language: golang` reports "invalid go version" or Go compilation errors for a hook that worked previously

## Verified Workflow

### Quick Reference

| Problem | Fix |
| --------- | ----- |
| Hook runs on all files, not staged | Set `pass_filenames: true`, remove hardcoded dirs from `entry` |
| Hook `rev:` out of sync with pixi | Run `pixi run <tool> --version`, update `rev:` to match exactly |
| Update all hooks to latest | `pre-commit autoupdate` |
| Add zero-dep regex guardrail | Add `language: pygrep` hook stanza |
| Hook with `pass_filenames: false` needs rationale | Read script, add inline comment if global scan is intentional |
| Verify hook config without running pre-commit | Parse YAML with `yaml.safe_load()` in pytest |
| Hook REPO_ROOT resolves to .git/ in test repos | Use `git rev-parse --show-toplevel` to find repo root; use dedicated variable `REPO_ROOT_HOOK` |
| `just` finds Justfile in parent dir during hook test | Guard with `command -v just && [[ -f "${REPO_ROOT_HOOK}/Justfile" ]]` |
| bats tests trigger hook's test-suite step | Set `SKIP_TESTS=1` in bats test before invoking hook |
| Go-based hook fails to build from source (old Go) | Convert to `repo: local` hook that downloads pre-built binary |

### Step 1: Fix pass_filenames for Ruff (and Other Linters)

Verify current state before touching anything:

```bash
git log --oneline -5
cat .pre-commit-config.yaml
```

The broken pattern:

```yaml
# BROKEN - hardcoded dirs, filenames not passed
- id: ruff-format-python
  name: Ruff Format Python
  entry: pixi run ruff format src/ scripts/
  language: system
  types: [python]
  pass_filenames: false
```

The fixed pattern:

```yaml
# FIXED - no hardcoded dirs, filenames passed by pre-commit
- id: ruff-format-python
  name: Ruff Format Python
  entry: pixi run ruff format
  language: system
  types: [python]
  pass_filenames: true

- id: ruff-check-python
  name: Ruff Check Python
  entry: pixi run ruff check --fix
  language: system
  types: [python]
  pass_filenames: true
```

Verify hooks pass:

```bash
pixi run pre-commit run --all-files
# or: just pre-commit-all
```

### Step 2: Evaluate Whether pass_filenames: false Is Intentional

1. Read `.pre-commit-config.yaml` — note `entry:`, `files:`, and `pass_filenames:` values
2. Read the script referenced in `entry:` — check argument handling:
   - Uses `sys.argv` for positional args? → could support `pass_filenames: true`
   - Does whole-repo scanning (`Path.glob`, `os.walk`, `find_files(repo_root)`)? → `pass_filenames: false` is correct
   - Ignores positional args entirely? → `pass_filenames: false` is correct
3. Grep the script for argument handling:

```bash
grep -n "sys.argv\|argparse\|positional" <script-path>
```

| Script behavior | Correct setting |
| ---------------- | ----------------- |
| Iterates over `sys.argv[1:]` as file paths | `pass_filenames: true` |
| Uses `argparse` with positional `files` argument | `pass_filenames: true` |
| Scans repo root with `Path.glob` / `os.walk` | `pass_filenames: false` |
| Only checks `"--flag" in sys.argv` (no positional args) | `pass_filenames: false` |
| Reads a fixed config/workflow file at a hardcoded path | `pass_filenames: false` |

If `pass_filenames: false` is intentional, add an inline comment:

```yaml
        # pass_filenames: false is intentional — this script performs a whole-repo
        # <operation> against <target>, not per-file validation.
        # The files: pattern handles efficient triggering; the script ignores file args.
        pass_filenames: false
```

Verify no regression:

```bash
pixi run pre-commit run <hook-id> --all-files
```

### Step 3: Align Hook Versions with Pixi

Identify the mismatch:

```bash
grep -A1 "mirrors-mypy" .pre-commit-config.yaml
grep "mypy" pixi.toml
```

Find the pixi-resolved version:

```bash
pixi run mypy --version
# Output: mypy 1.19.1 (compiled: yes)
```

Update the `rev:` field:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.19.1   # was v1.8.0
```

Verify:

```bash
just pre-commit-all
# or: pixi run pre-commit run --all-files
```

General pattern for any mirrored hook:

```bash
# 1. Find current rev
grep -A1 "<hook-name>" .pre-commit-config.yaml

# 2. Find pixi-resolved version
pixi run <tool> --version

# 3. Update rev to match exactly
# 4. Run pre-commit to verify, commit + PR
```

### Step 4: Update Hook Versions with autoupdate

```bash
# Check for and update all hooks to latest versions
pre-commit autoupdate
```

Expected output:

```
[https://github.com/adrienverge/yamllint] updating v1.35.1 -> v1.38.0
[https://github.com/pre-commit/pre-commit-hooks] updating v4.5.0 -> v6.0.0
```

After updating, always run all hooks to verify nothing broke:

```bash
pre-commit run --all-files
```

Configuration files to verify exist:
- `.markdownlint.json` — Markdown linting rules
- `.yamllint.yaml` — YAML linting rules

### Step 5: Add a pygrep Hook for Forbidden Patterns

Convert the manual grep command to a pygrep regex:

```bash
# Original manual audit command
grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME' examples/
```

Add hook stanza (pygrep uses Python `re` syntax — use `|` inside a group, not `\|`):

```yaml
- repo: local
  hooks:
    - id: check-print-debug-artifacts
      name: Check for NOTE/TODO/FIXME in print statements
      description: >-
        Fail if examples/ contains print() calls with NOTE, TODO, or FIXME
        left over from development/debugging.
      entry: 'print.*(NOTE|TODO|FIXME)'
      language: pygrep
      files: ^examples/
```

Placement tip: add new hooks to an existing `repo: local` block; do not create a new `- repo: local` per hook.

Validate the baseline is clean before committing:

```bash
SKIP=mojo-format,mypy pixi run pre-commit run check-print-debug-artifacts --all-files
```

Write pytest tests for the regex (fast, zero network access):

```python
import re
PATTERN = re.compile(r"print.*(NOTE|TODO|FIXME)")

POSITIVE_CASES = [
    ('print("NOTE: fix this")', "bare NOTE"),
    ('print("TODO: remove")', "bare TODO"),
    ('# print("NOTE: commented")', "commented-out print still flagged"),  # pygrep sees raw line
]
NEGATIVE_CASES = [
    ('print("hello world")', "no keyword"),
    ('log("TODO: ignored")', "non-print call"),
]

@pytest.mark.parametrize("line,description", POSITIVE_CASES)
def test_positive_match(line, description):
    assert bool(PATTERN.search(line)), f"Expected match for {description!r}: {line!r}"

@pytest.mark.parametrize("line,description", NEGATIVE_CASES)
def test_negative_no_match(line, description):
    assert not bool(PATTERN.search(line)), f"Unexpected match for {description!r}: {line!r}"
```

### Step 6: Write Pytest Tests for Hook YAML Config

Parse `.pre-commit-config.yaml` directly — no pre-commit or bandit binary needed:

```python
import re, yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"

def _load_hook(hook_id: str) -> dict:
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text())
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            if hook.get("id") == hook_id:
                return hook
    return {}

def _all_flags(hook: dict) -> list[str]:
    """Return all CLI tokens from entry string + args list."""
    flags = []
    entry = hook.get("entry", "")
    if entry:
        flags.extend(entry.split())
    flags.extend(hook.get("args", []))
    return flags
```

Test skip list presence and minimality:

```python
DOCUMENTED_SKIPS = {"B310", "B202"}

def test_skip_list_is_minimal(bandit_hook):
    skip_ids = _get_skip_ids(bandit_hook)
    undocumented = set(skip_ids) - DOCUMENTED_SKIPS
    assert not undocumented, (
        f"Undocumented bandit skip IDs found: {undocumented}. "
        "Add rationale before expanding."
    )
```

Test `files:` pattern coverage with parametrize:

```python
@pytest.mark.parametrize("path", [
    "scripts/download_mnist.py",
    "tests/scripts/test_security.py",
])
def test_pattern_matches_expected(bandit_hook, path):
    pattern = bandit_hook.get("files", "")
    assert re.search(pattern, path)

@pytest.mark.parametrize("path", [
    "shared/nn/layers/conv2d.mojo",
])
def test_pattern_excludes_non_targets(bandit_hook, path):
    pattern = bandit_hook.get("files", "")
    assert not re.search(pattern, path)
```

### Step 7: Fix REPO_ROOT Resolution in Hooks Installed in Test Repos

**Root cause**: When a hook is installed as `.git/hooks/pre-commit` in a temporary test repo,
`SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"` resolves to `.git/hooks/`, so
`REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"` resolves to `.git/` — not the repo root.

All working-tree paths derived from `REPO_ROOT` (find, validate, agents directory) will silently
operate on `.git/` contents instead of the actual source tree.

**Fix pattern**:

```bash
# At the top of the hook, after SCRIPT_DIR is set:
# Use git rev-parse to find the actual working-tree root — immune to install location
REPO_ROOT_HOOK="$(git rev-parse --show-toplevel 2>/dev/null || echo "${REPO_ROOT}")"

# Use REPO_ROOT_HOOK for ALL working-tree path references:
find "${REPO_ROOT_HOOK}/agents" -name "*.yaml" ...
"${REPO_ROOT_HOOK}/scripts/check-dangerous-flags.sh"
```

**Test-suite step guard** — prevents `just` from finding a Justfile in a parent directory when the hook runs in a temporary test repo:

```bash
# BEFORE fix — just finds Justfile in parent directory:
if command -v just &>/dev/null; then
  just test
fi

# AFTER fix — guards that Justfile is in the hook's own repo:
if command -v just &>/dev/null && [[ -f "${REPO_ROOT_HOOK}/Justfile" ]]; then
  just --justfile "${REPO_ROOT_HOOK}/Justfile" test
fi
```

**SKIP_TESTS guard** — allows bats tests to invoke the hook without triggering the test-suite step:

```bash
# In hook:
if [[ "${SKIP_TESTS:-0}" != "1" ]] && command -v just &>/dev/null && [[ -f "${REPO_ROOT_HOOK}/Justfile" ]]; then
  just --justfile "${REPO_ROOT_HOOK}/Justfile" test
fi

# In bats test:
SKIP_TESTS=1 run .git/hooks/pre-commit
```

**`|| true` in conditional pipelines**:

```bash
# BROKEN under set -euo pipefail — false condition aborts the script:
[[ -n "$n" ]] && printf '%s\n' "$n"

# FIXED:
[[ -n "$n" ]] && printf '%s\n' "$n" || true
```

The `|| true` prevents the shell from aborting when the `&&` condition is false. Required in any
`set -euo pipefail` hook that uses short-circuit conditionals.

**Diagnosis**:
- bats test fails with "No such file or directory" on agents/fleet paths → likely `REPO_ROOT` pointing to `.git/`
- `just` finds unrelated Justfile from parent directory → add `[[ -f "${REPO_ROOT_HOOK}/Justfile" ]]` guard
- Hook works on real commits but fails in bats tests → `SKIP_TESTS=1` pattern needed

### Step 8: Convert Go-Based Hooks from Source Build to Pre-Built Binary

**Root cause**: pre-commit's `language: golang` support builds hooks from source using the system Go compiler. When a hook's `go.mod` requires a newer Go version than what's installed (e.g., gitleaks v8.30.1 requires Go 1.24.11 but system has Go 1.15.15), the build fails with:

```
invalid go version '1.24.11': must match format 1.23
```

**Diagnosis checklist**:
1. `go version` shows the system Go version
2. Check the hook's `go.mod` for the required Go version
3. Check if conda-forge/pixi provides a newer Go: `pixi search go` (often only old versions available)

**Fix**: Convert from `language: golang` (builds from source) to a `repo: local` hook that downloads the pre-built binary release:

```yaml
# BEFORE (broken — requires Go 1.24+ but system has Go 1.15):
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.30.1
  hooks:
    - id: gitleaks

# AFTER (downloads pre-built binary):
- repo: local
  hooks:
    - id: gitleaks
      name: Gitleaks Secret Scan
      entry: bash -c 'GITLEAKS_VERSION="8.30.1"; GITLEAKS_BIN="$HOME/.local/bin/gitleaks"; if [ ! -x "$GITLEAKS_BIN" ]; then mkdir -p "$HOME/.local/bin" && curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" | tar -xz -C "$HOME/.local/bin" gitleaks; fi && "$GITLEAKS_BIN" protect --staged'
      language: system
      pass_filenames: false
```

**Key design decisions**:
- Binary is cached at `$HOME/.local/bin/gitleaks` — only downloaded once
- `curl -sSfL` fails fast on HTTP errors (`-f`) and follows redirects (`-L`)
- `pass_filenames: false` because gitleaks scans the git diff, not individual files
- Version is pinned inline — update the `GITLEAKS_VERSION` string when upgrading

**Verification**:

```bash
pre-commit run gitleaks --all-files
```

**This pattern applies to any Go-based hook** where the system Go is too old and upgrading Go is not feasible (e.g., constrained CI environments, conda-forge only providing old Go versions).

## Hook-Specific Patterns

### detect-private-key: Excluding Test Fixtures

Use when `detect-private-key` fires on files that contain fake/test credentials (TLS unit tests, Kubernetes secret manifests, example certs). Do **not** delete the hook — that would miss real leaks. Use `exclude:` to scope it.

**Quick Reference**:

```yaml
# .pre-commit-config.yaml — under detect-private-key hook entry:
- id: detect-private-key
  exclude: '^(k8s/metrics-security\.yaml|tests/unit/test_grpc_tls\.cpp)$'
```

For broader exclusions (test directories, example certs, k8s secret patterns):

```yaml
- id: detect-private-key
  exclude: '^(tests/|fixtures/|examples/|k8s/.*-secret.*\.yaml|k8s/.*-security.*\.yaml)$'
```

**Step-by-step**:

1. **Identify flagged files** — read CI log from the `detect-private-key` hook; it lists each triggering path.
2. **Confirm they are test fixtures** — verify the file is a unit test, example cert, generated credential, or Kubernetes manifest. If it contains real credentials, fix that instead of excluding.
3. **Locate the hook entry** in `.pre-commit-config.yaml` — find the `repo: https://github.com/pre-commit/pre-commit-hooks` block and `- id: detect-private-key`.
4. **Add `exclude:` directly under the hook id** — value is a Python regex anchored with `^...$`.
5. **Escape regex metacharacters**: forward slashes `/` do not need escaping; dots `.` in filenames must be escaped as `\.`.
6. **Verify locally**: `pre-commit run detect-private-key --all-files` — excluded files should pass; all other paths still checked.
7. **Commit** — `.pre-commit-config.yaml` is in version control; CI picks it up automatically.

**Regex rules for the `exclude:` field**:

| Pattern | Matches |
| --------- | --------- |
| `^path/to/file\.ext$` | Exact file |
| `^(file1\.yaml\|file2\.cpp)$` | Either of two exact files |
| `^tests/` | All files under `tests/` |
| `^k8s/.*-secret.*\.yaml$` | Any k8s YAML with `-secret` in the name |
| `^k8s/.*-security.*\.yaml$` | Any k8s YAML with `-security` in the name |

**Typical PEM patterns that trigger false positives in test files**:

```
-----BEGIN CERTIFICATE-----
-----BEGIN PRIVATE KEY-----
-----BEGIN RSA PRIVATE KEY-----
-----BEGIN EC PRIVATE KEY-----
-----BEGIN CERTIFICATE REQUEST-----
```

These appear in TLS unit tests (`test_grpc_tls.cpp`, `test_tls_*.py`) and Kubernetes secret manifests that embed cert/key material as base64 or raw PEM for local dev environments.

**Failed attempts for this pattern**:

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Delete the hook entirely | Remove `detect-private-key` from `.pre-commit-config.yaml` | Would miss real credential leaks in non-test paths — eliminates security value | Use `exclude:` to scope the hook, never remove it entirely |
| Move test files to a different path | Rename `tests/unit/test_grpc_tls.cpp` to avoid detection | Disrupts test structure and doesn't scale for k8s manifests | Path-based `exclude:` is correct; don't relocate files to satisfy a hook |
| Add `# noqa` or inline ignore comments | Tried per-line directives in C++ source | `detect-private-key` is a grep-based hook — inline suppressions not supported | Hook-level `exclude:` is the only supported suppression mechanism |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assuming changes needed for pass_filenames fix | Started planning edits to `.pre-commit-config.yaml` | Fix was already committed | Always check `git log` before implementing fixes from a review plan |
| Running tests first before fixing hook | Ran `pixi run python -m pytest tests/ -v` | `ModuleNotFoundError: No module named 'scripts.dashboard'` — pre-existing unrelated failure | Pre-existing test failures are not blockers; verify they are unrelated before spending time on them |
| Pinning `rev:` to `>=1.19.1` | Tried using a semver range in the `rev:` field | `rev:` only accepts exact git tags, not semver ranges | Always use an exact tag (e.g. `v1.19.1`) matching the installed binary |
| Guessing the tag from the pixi constraint | Assumed v1.19.0 from constraint `>=1.19.1` | pixi resolves to the latest satisfying version | Always run `pixi run <tool> --version` rather than inferring from the constraint |
| Switching to `pass_filenames: true` without reading the script | Assumed symmetry with a sibling hook | Script does whole-repo scan and does not process positional file args | Always read the script before deciding |
| Checking only hook config for pass_filenames decision | Looked at `files:` pattern and `entry:` only | Did not reveal whether the script actually processes `sys.argv[1:]` | Must grep the script for argument handling code |
| Check only `args` list for `--skip` in hook config tests | Looked for skip IDs in `hook["args"]` | The actual config used `entry: "pixi run bandit -ll --skip B310,B202"` — flags were in `entry`, not `args` | Always normalise flags from both `entry` and `args`; write a `_all_flags()` helper |
| Assert `https://` in scripts using `urlopen` | Checked that download scripts use HTTPS | `download_mnist.py` uses `http://` for original mirrors | The safety property is "hardcoded constant", not "https". Check for a module-level `*URL = "..."` constant |
| Regex `[A-Z_]+BASE_URL\s*=` for URL constants | Looked for `*BASE_URL` naming pattern | `download_cifar10.py` uses `CIFAR10_URL` (not `BASE_URL`) | Use broader pattern `^[A-Z][A-Z0-9_]*URL\s*=\s*["\']` with `re.MULTILINE` |
| Single commit on hook failure | Expected pre-commit to leave file unchanged after failure | Ruff reformatted the file; re-staging needed | After a hook modifies files, re-stage and commit again (never use `--no-verify`) |
| `pygrep` commented-out print as negative case | Added `# print("NOTE: ...")` to NEGATIVE_CASES | `pygrep` matches raw line — `# print(...)` still contains `print.*NOTE` | Move commented-out prints to POSITIVE_CASES; pygrep does not understand comments |
| Using `\|` alternation in pygrep entry | Wrote `print.*NOTE\|print.*TODO\|print.*FIXME` (grep syntax) | pygrep uses Python `re` syntax; `\|` is a literal pipe | Use `(NOTE\|TODO\|FIXME)` group syntax |
| Treating all CI failures as PR-related | Initially considered fixing flaky test failures | Failures were `mojo: error: execution crashed` — pre-existing infra issue | Check `main` branch CI history to distinguish pre-existing flaky failures from PR regressions |
| Using `${REPO_ROOT}` for find/validate paths in hook installed in .git/hooks/ | Used `find "${REPO_ROOT}/agents" -name "*.yaml"` in hook where `REPO_ROOT="${SCRIPT_DIR}/.."` | When hook is `.git/hooks/pre-commit`, `SCRIPT_DIR` is `.git/hooks/` so `REPO_ROOT` is `.git/` — find operates on `.git/agents/` which doesn't exist | Use `REPO_ROOT_HOOK="$(git rev-parse --show-toplevel 2>/dev/null \|\| echo "${REPO_ROOT}")"` and replace all working-tree paths with `${REPO_ROOT_HOOK}` |
| Removed `[[ $# -eq 0 ]] && return 0` guard from `report_unmanaged()` | Cleaned up what appeared to be a redundant guard in `report_unmanaged()` | Broke bats test 299 — the guard is needed in `report_unmanaged()` specifically (different from `get_unmanaged_names()` where the check was correctly replaced with array-length check) | Only remove the `$# -eq 0` guard from `get_unmanaged_names()`; keep it in `report_unmanaged()` |
| `just test` inside hook without Justfile guard | Hook ran `if command -v just; then just test; fi` | When hook runs in a temporary test repo (bats test), `just` searches upward and finds the real repo's Justfile, running the full test suite inside the temp repo context | Add `[[ -f "${REPO_ROOT_HOOK}/Justfile" ]]` guard before calling `just`; also set `SKIP_TESTS=1` in bats tests that invoke the hook |
| `[[ -n "$n" ]] && printf '%s\n' "$n"` without `\|\| true` | Short-circuit conditional in hook body under `set -euo pipefail` | When the `&&` condition is false (empty `$n`), bash treats the command as having failed (exit 1), which triggers `set -e` to abort the script | Add `\|\| true`: `[[ -n "$n" ]] && printf '%s\n' "$n" \|\| true` |
| `pixi search gitleaks` for pre-built binary | Tried to install gitleaks via conda-forge | Not available on conda-forge | Go-based security tools are rarely packaged for conda; use pre-built GitHub release binaries |
| Checking if pixi provides newer Go | Ran `pixi search go` | Only Go 1.15 available via system/conda | Cannot rely on conda-forge for up-to-date Go; use pre-built binaries for Go-based hooks |
| Pinning to older gitleaks version | Considered downgrading gitleaks to a version with lower Go requirement | All recent gitleaks versions (v8.18+) require Go 1.22+ which is still newer than system Go 1.15 | The Go version gap is too large to bridge by downgrading the hook; pre-built binary is the only viable path |

## Results & Parameters

### Working Ruff Hook Configuration

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: ruff-format-python
      name: Ruff Format Python
      entry: pixi run ruff format
      language: system
      types: [python]
      pass_filenames: true

    - id: ruff-check-python
      name: Ruff Check Python
      entry: pixi run ruff check --fix
      language: system
      types: [python]
      pass_filenames: true
```

### Version Alignment Commit Message Template

```text
fix(pre-commit): upgrade mirrors-mypy rev from vOLD to vNEW

Align the mirrors-mypy pre-commit hook revision with the mypy version
resolved by pixi (>=1.19.1,<2), eliminating the version mismatch where
`pixi run mypy` and the pre-commit hook could behave differently.

Closes #<issue>
```

### pygrep Hook Parameters

| Field | Value | Notes |
| ------- | ------- | ------- |
| `language` | `pygrep` | Zero external deps; pattern matched via Python `re` |
| `entry` | `'print.*(NOTE\|TODO\|FIXME)'` | Quoted to prevent shell expansion |
| `files` | `^examples/` | Scope to one directory; adjust as needed |
| `types` | (omitted) | Defaults to all text files; add `[python]` to restrict |
| `pass_filenames` | (omitted) | pygrep handles file iteration automatically |

### Hook Config Test Structure

```text
TestBanditHookExists        (4 tests)  — hook id, entry, name present
TestBanditSkipList          (4 tests)  — --skip present, B310/B202 in list, list minimal
TestBanditSeverityThreshold (2 tests)  — -ll present, -l alone rejected
TestBanditFilesPattern      (12 tests) — 8 match + 4 exclude, parametrized
TestBanditNosecRationale    (4 tests)  — urlopen/extractall exist, safe usage verified
```

### REPO_ROOT_HOOK Pattern for Hooks Installed in .git/hooks/

```bash
# In the hook file (.git/hooks/pre-commit or scripts/pre-commit.sh):

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"  # May be .git/ when installed as .git/hooks/pre-commit

# Use git rev-parse to find actual repo root regardless of install location:
REPO_ROOT_HOOK="$(git rev-parse --show-toplevel 2>/dev/null || echo "${REPO_ROOT}")"

# All working-tree references use REPO_ROOT_HOOK:
find "${REPO_ROOT_HOOK}/agents" -name "*.yaml" -not -path "*/.git/*" | ...
"${REPO_ROOT_HOOK}/scripts/check-dangerous-flags.sh"

# Test-suite guard (prevents just from running in temp repos):
if [[ "${SKIP_TESTS:-0}" != "1" ]] && command -v just &>/dev/null && [[ -f "${REPO_ROOT_HOOK}/Justfile" ]]; then
  just --justfile "${REPO_ROOT_HOOK}/Justfile" test
fi
```

```bash
# In bats tests that invoke the hook:
SKIP_TESTS=1 run "${REPO_ROOT}/.git/hooks/pre-commit"
assert_success
```

### Verification Commands

```bash
# Run all hooks
pixi run pre-commit run --all-files

# Run specific hook
pixi run pre-commit run <hook-id> --all-files

# Check pre-existing CI failures vs PR regressions
gh run list --branch main --limit 10
gh run view <run-id> --log-failed
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Myrmidons | shellcheck-warnings swarm; 332 unit tests pass, CI green; REPO_ROOT_HOOK pattern, SKIP_TESTS guard, Justfile guard, `\|\| true` fix (2026-04-24) | verified-ci |
| ProjectScylla | gitleaks v8.30.1 Go build failure; converted from `language: golang` to pre-built binary download in `.pre-commit-config.yaml` (2026-04-27) | verified-local |
