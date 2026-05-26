---
name: python-cli-cwd-github-repo-detect
description: "Package a pip-installable Python CLI that auto-detects (org, repo) from cwd via git rev-parse + git remote get-url origin (handles both SSH and HTTPS URLs). Use when: (1) shipping a CLI that should default to acting on the current GitHub repo (POLA), (2) want a $PATH binary without `pixi run` / `python -m` wrappers."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, packaging, cli, github, console-scripts]
---

# Python CLI: cwd-aware GitHub Repo Detection + Pip-Installable Binary

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Document the pattern for a Python CLI that auto-scopes to the cwd GitHub repo |
| **Outcome** | Pattern shipped in hephaestus-automation-loop; defaults to cwd repo, auto-detects org from origin |
| **Verification** | verified-local (smoke + unit tests verify SSH and HTTPS URL parsing; CI still running) |

## When to Use

- Shipping a Python CLI that should default to "act on the current GitHub repo" when run with no args (POLA)
- Making the CLI pip-installable so users don't need `pixi run`
- Need to derive `(org, repo_slug)` from the working directory

## Verified Workflow

### Quick Reference

```python
# Detect (org, repo) from cwd
top  = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
url  = subprocess.check_output(["git", "remote", "get-url", "origin"]).decode().strip()
tail = url.split("github.com", 1)[1].lstrip(":/")  # "Org/Repo[.git]"
org  = tail.split("/", 1)[0]
repo = Path(top).name
```

```toml
# pyproject.toml -- makes the CLI a $PATH binary
[project.scripts]
my-tool = "my_package.cli:main"
```

### Detailed Steps

Detection helper:

```python
def detect_cwd_repo() -> tuple[str | None, str | None]:
    """Return (org, repo_name) for cwd, or (None, None) if not a github.com repo."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return (None, None)
    repo = Path(top).name or None

    org: str | None = None
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
        # Handles both git@github.com:Org/Repo.git and https://github.com/Org/Repo[.git]
        if "github.com" in url:
            tail = url.split("github.com", 1)[1].lstrip(":/")
            parts = tail.split("/", 1)
            if len(parts) == 2:
                org = parts[0]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return (org, repo)
```

**Key parsing trick:** `url.split("github.com", 1)[1].lstrip(":/")` handles BOTH SSH (`git@github.com:Org/Repo.git`) and HTTPS (`https://github.com/Org/Repo.git`) without regex. The character right after "github.com" is either `:` (SSH) or `/` (HTTPS); lstripping both leaves a clean `Org/Repo[.git]`. The `.git` suffix doesn't matter when we only take the first path segment.

**Packaging as pip-installable binary** -- add to `pyproject.toml`:

```toml
[project.scripts]
my-tool = "my_package.module:main"
```

After `pip install -e .` (or installing the wheel), `my-tool` is on `$PATH` for any environment that pip-installed the package -- no `pixi run` or `python -m` wrapper required.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Regex on origin URL | Match SSH and HTTPS in one regex | Brittle -- fails on URLs with auth tokens, query strings, or trailing slashes | `split("github.com", 1)[1].lstrip(":/")` is unambiguous and works for every URL shape |
| Hardcoded `DEFAULT_ORG` fallback | Silent fallback when cwd had no remote | Surprising -- operator forks to a different org and the tool still acts on the original | No silent default; require either --org or a detectable cwd origin |
| `pixi run my-tool` as canonical invocation | Force users into the pixi env | Couples the CLI to one env manager; breaks `pip install` use cases | A console_script entry point in `[project.scripts]` works for pip, pipx, uv, pixi |
| `[tool.poetry.scripts]` instead of `[project.scripts]` | Use Poetry-style config | PEP 621 `[project.scripts]` is the standard; `[tool.poetry.scripts]` is poetry-only | Always use `[project.scripts]` for portable packaging |

## Results & Parameters

Tested in hephaestus-automation-loop CLI (PR HomericIntelligence/ProjectHephaestus#591). Smoke tests:
- `hephaestus-automation-loop` (no flags) -> "Defaulting to current repo: HomericIntelligence/ProjectHephaestus"
- `hephaestus-automation-loop --org` (no arg) -> "Discovering repos in HomericIntelligence ..." (org auto-detected)

Both SSH and HTTPS remote URL parsing covered by `tests/unit/automation/test_loop_runner.py`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | hephaestus-automation-loop CLI default-to-cwd-repo (PR #591) | First pip-installable CLI in the repo that auto-scopes to the cwd github repo |
