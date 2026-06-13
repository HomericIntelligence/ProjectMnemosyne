---
name: github-actions-cli-required-env-var-guard
description: "Guard pattern for required GitHub Actions env vars in Python CLI main() functions. Use when: (1) a console-script reads a required workflow env var with bare os.environ[\"VAR\"] and crashes with KeyError outside the workflow, (2) adding validation for GITHUB_REPOSITORY or similar vars that are always set in Actions but absent locally, (3) the tool has a sibling env-var guard to mirror."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - python
  - github-actions
  - env-var
  - console-scripts
  - keyerror
  - input-validation
  - GITHUB_REPOSITORY
  - architecture
---

# github-actions-cli-required-env-var-guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix KeyError when GitHub Actions env vars are unset outside the workflow |
| **Outcome** | Replaced bare `os.environ["KEY"]` with `.get()` + validation guard; 4102 tests pass |
| **Verification** | verified-local (4102 unit tests pass; CI pending on PR #1311) |
| **Source** | ProjectHephaestus issue #1300 / PR #1311 |

## When to Use

- A console-script reads a GitHub Actions env var with bare `os.environ["KEY"]` and crashes with `KeyError` when run locally or outside the workflow
- Adding input validation for `GITHUB_REPOSITORY`, `GITHUB_TOKEN`, `ISSUE_NUMBER`, or similar vars
- The tool has an existing guard pattern (sibling var) to mirror for consistency
- `--help` or `--version` appear to crash but the real crash is bare invocation without the env var (argparse `action="version"` exits before the read)

## Verified Workflow

### Quick Reference

```python
# Replace this:
repo = os.environ["GITHUB_REPOSITORY"]

# With this:
repo = os.environ.get("GITHUB_REPOSITORY", "")
if not repo or "/" not in repo:
    message = f"Unexpected GITHUB_REPOSITORY {repo!r} (expected owner/name)"
    if args.json:
        emit_json_status(1, message)
    else:
        print(message, file=sys.stderr)
    return 1
```

### Detailed Steps

1. Replace `os.environ["VAR"]` with `os.environ.get("VAR", "")`
2. Immediately after: validate with `if not value or <format-check>:`
   - For `GITHUB_REPOSITORY`: check `"/" not in repo` (must be `owner/name`)
   - For `ISSUE_NUMBER`: check `not raw.isdigit()` (must be positive integer)
3. Output error via the module's existing error path (`emit_json_status` when `args.json`, else `print(..., file=sys.stderr)`)
4. Return 1 (not raise — lets the caller/entrypoint see the exit code)
5. Place guard between `parse_args()` and the first API/subprocess call
6. Mirror the format of any sibling guard in the same function for consistency
7. Add two unit tests: one for missing var (`monkeypatch.delenv`), one for malformed value

### Test Pattern

```python
def test_main_rejects_missing_github_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("ISSUE_BODY", "### Severity\n\nmajor\n")
    assert sl.main([]) == 1

def test_main_rejects_malformed_github_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "no-slash-here")
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("ISSUE_BODY", "### Severity\n\nmajor\n")
    assert sl.main([]) == 1
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Blaming `--version` | Issue description said `--version` crashes | argparse `action="version"` calls `sys.exit(0)` inside `parse_args()`, before the env read; `--version` never crashes | Read the code: parse_args() exits first for --help/--version; the crash is bare invocation |
| Raising on bad value | Raise ValueError instead of returning 1 | Unhandled exception shows a traceback, not a clean error message; callers see exit code 1 either way but traceback is confusing | Use `return 1` with a printed message, consistent with sibling guards |

## Results & Parameters

- `GITHUB_REPOSITORY` format: `owner/name` (slash required)
- Empty string `""` (from `.get()` fallback) is caught by `not repo`
- Slashless value like `"myrepo"` caught by `"/" not in repo`
- Validation fires AFTER `parse_args()` so `--help`/`--version` still work without env vars
- Pattern generalizes to any `owner/name` slug env var in GitHub Actions scripts

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1300 / PR #1311 | Added GITHUB_REPOSITORY guard to severity_label.main(); 4102 unit tests pass locally |
