---
name: shell-script-integration-test-tier-coverage
description: "Pattern for ensuring integration tests cover all preference tiers in shell scripts with N-tier fallback logic. Use when: (1) a shell script has N-tier fallback/preference logic but tests only cover the first N-1 tiers, (2) adding a test for a bash script that uses bash-function-override injection (export a mock `gh` function via a Python pytest helper), (3) reviewing test coverage gaps in `scripts/choose_merge_flag.sh` or similar tiered-preference scripts, (4) constructing flat REST JSON bodies for each tier of a jq-driven preference selector."
category: testing
date: 2026-06-13
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: shell-script-integration-test-tier-coverage.history
tags:
  - shell
  - bash
  - integration-test
  - mock
  - choose_merge_flag
  - tier-coverage
  - jq
  - bash-function-override
  - pytest
  - python
---

# Shell Script Integration Test Tier Coverage

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Add missing integration test for the `--merge` fallback path in `scripts/choose_merge_flag.sh` (ProjectHephaestus issue #1277) |
| **Outcome** | Success — single new pytest function added; all 7 tests pass locally and in CI |
| **Verification** | verified-ci — PR #1305 submitted, CI green |

## When to Use

Trigger this skill when:

1. A shell script uses an if-elif/case chain with N preference tiers and tests only cover N-1 of them
2. The uncovered tier is a fallback (the "last resort" branch hit when all higher-priority conditions are false)
3. The existing test file uses a `_run_with_mock_gh(json_body)` Python helper that injects `gh` as a bash function override
4. You need to construct a JSON body that targets a specific branch in `choose_merge_flag.sh` by setting boolean flags
5. You encounter the pattern: `if allow_rebase_merge → --rebase; elif allow_squash_merge → --squash; else → --merge`
6. Auditing test coverage for any script that dispatches on GitHub REST API's `allow_rebase_merge` / `allow_squash_merge` / `allow_merge_commit` fields

## Verified Workflow

### 1. Enumerate all branches in the script under test

Read the script (e.g., `scripts/choose_merge_flag.sh`) and list every branch:

```
Tier 1: if allow_rebase_merge   → output "--rebase"
Tier 2: elif allow_squash_merge → output "--squash"
Tier 3: else                    → output "--merge"
```

Count the branches, then count the existing test functions. Missing tiers = add one test per gap.

### 2. Understand the Python `_run_with_mock_gh` helper

The test file (`tests/integration/test_choose_merge_flag_sh.py`) uses a **Python** function (not bash), which constructs a bash heredoc and runs it via `subprocess.run`:

```python
def _run_with_mock_gh(json_body: str, repo: str = "owner/repo") -> subprocess.CompletedProcess:
    """Run choose_merge_flag with a mock gh function returning json_body."""
    script = f"""
gh() {{
    case "$1" in
        api) printf '%s\\n' '{json_body}' ;;
        *) command gh "$@" ;;
    esac
}}
export -f gh
. {SNIPPET}
choose_merge_flag {repo}
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
    )
```

Key details:
- `json_body` is a flat REST JSON string (not nested GraphQL)
- `export -f gh` makes the bash function override visible to the sourced script
- The helper returns `subprocess.CompletedProcess` — check `.returncode` and `.stdout.strip()`
- No new infrastructure needed — just call this helper with a different JSON body

### 3. Construct the JSON body for the missing tier

The script consumes **GitHub REST API** response format (flat keys), NOT GraphQL nested format:

```python
# Tier 1: rebase preferred — all allowed, rebase wins
body = '{"allow_rebase_merge":true,"allow_squash_merge":true,"allow_merge_commit":true}'
# Expected: result.stdout.strip() == "--rebase"

# Tier 2: squash fallback — rebase not allowed
body = '{"allow_rebase_merge":false,"allow_squash_merge":true,"allow_merge_commit":false}'
# Expected: result.stdout.strip() == "--squash"

# Tier 3: merge fallback — rebase and squash not allowed
body = '{"allow_rebase_merge":false,"allow_squash_merge":false,"allow_merge_commit":true}'
# Expected: result.stdout.strip() == "--merge"

# Error case: no methods allowed
body = '{"allow_rebase_merge":false,"allow_squash_merge":false,"allow_merge_commit":false}'
# Expected: result.returncode == 1, "allows no merge methods" in result.stderr
```

### 4. Add one test function per missing tier

Follow the exact shape of existing test functions — no scaffolding changes required:

```python
def test_shell_helper_selects_merge_when_rebase_and_squash_disallowed() -> None:
    """Falls back to merge commit when both rebase and squash are not permitted."""
    body = '{"allow_rebase_merge":false,"allow_squash_merge":false,"allow_merge_commit":true}'
    result = _run_with_mock_gh(body)
    assert result.returncode == 0
    assert result.stdout.strip() == "--merge"
```

No test runner registration needed — pytest auto-discovers all `test_*` functions.

### 5. Verify locally before pushing

```bash
pixi run pytest tests/integration/test_choose_merge_flag_sh.py -v
```

All 7 tests should pass. The integration test file is small and fast (pure subprocess, no live `gh` calls).

### Quick Reference

| Goal | What to do |
|------|------------|
| Find uncovered tiers | Read script + count if/elif/else branches; count existing test functions |
| Target Tier 1 (rebase) | `allow_rebase_merge: true`, others false |
| Target Tier 2 (squash) | `allow_squash_merge: true`, rebase false |
| Target Tier 3 (merge) | `allow_merge_commit: true`, rebase+squash false |
| Add test | One new `test_*` function; reuse `_run_with_mock_gh` helper — no new infra |
| No script changes | New tier test is test-only; the script under test is untouched |
| JSON format | Flat REST keys (`allow_rebase_merge`), NOT nested GraphQL |
| Assert output | `result.stdout.strip() == "--merge"` (strip trailing newline) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Used nested GraphQL JSON format: `{"data":{"repository":{"pullRequest":...}}}` | Script reads REST API flat response (`allow_rebase_merge`), not GraphQL nested format | Always check the actual `gh api` call in the script (`gh api repos/{repo}`) to determine which JSON schema applies |
| 2 | Assumed test file was bash (`test_choose_merge_flag.sh`) | Test file is Python pytest (`test_choose_merge_flag_sh.py`) — `_run_with_mock_gh` is a Python function wrapping `subprocess.run` | Check file extension and language before writing test code |
| 3 | Assumed bash-style registration needed | pytest auto-discovers `test_*` functions — no explicit runner list | No `test_runner.sh` or function list needed; just name the function `test_*` |

## Results & Parameters

### Actual implementation (verified CI, PR #1305)

```python
def test_shell_helper_selects_merge_when_rebase_and_squash_disallowed() -> None:
    """Falls back to merge commit when both rebase and squash are not permitted."""
    body = '{"allow_rebase_merge":false,"allow_squash_merge":false,"allow_merge_commit":true}'
    result = _run_with_mock_gh(body)
    assert result.returncode == 0
    assert result.stdout.strip() == "--merge"
```

- 7 total tests in the file after adding this one
- All pass locally and in CI
- No new imports, no new fixtures, no helper changes

### Known fragility: single quotes in JSON inside bash f-string

The `_run_with_mock_gh` helper interpolates `json_body` into an f-string that becomes a bash heredoc. If `json_body` ever contains single quotes (e.g., a string value with an apostrophe), the bash function body breaks. For boolean-only payloads this is not a risk, but watch if the JSON schema changes.

**Mitigation**: use a temporary file for the JSON body if it must contain single quotes.

### Pattern generalisation

This pattern applies to any shell script with N-tier preference logic and a `_run_with_mock_<tool>` injection helper:

1. Enumerate all branches
2. Determine the JSON/env-var format the script actually consumes (REST vs GraphQL vs env vars)
3. Map each branch to the configuration that routes into it
4. Add one Python test function per uncovered branch, reusing the existing helper
5. Run locally to confirm, then push

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1277 — add `--merge` fallback path test (2026-06-13) | PR #1305; 7/7 tests pass; single new pytest function `test_shell_helper_selects_merge_when_rebase_and_squash_disallowed` |
