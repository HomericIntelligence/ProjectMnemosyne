---
name: pre-commit-hook-config-tests
description: "Write pytest unit tests that verify pre-commit hook configuration from YAML. Use when: a security hook has an intentional skip list needing rationale, verifying files: pattern coverage, or ensuring suppressions reflect real codebase usage."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Skill** | pre-commit-hook-config-tests |
| **Category** | testing |
| **Language** | Python / pytest |
| **Primary file** | `.pre-commit-config.yaml` |
| **Test target** | Hook YAML config (parsed directly — no pre-commit invocation) |

Tests the pre-commit hook configuration by parsing `.pre-commit-config.yaml` with
`yaml.safe_load()` and making assertions against the resulting dict. No pre-commit
or bandit binary needed — the tests run in milliseconds with zero network access.

## When to Use

- A security scanner hook (bandit, semgrep, etc.) has a `--skip` list that should be intentional and documented
- You need to verify a hook's `files:` regex matches the expected directory trees
- You want to guard against accidental removal of severity flags (e.g. `-ll`)
- You need to confirm that suppressed warnings correspond to real usage patterns in the codebase (not stale suppressions)
- Similar to how `pygrep` hook regex tests work, but for full CLI tool hooks

## Verified Workflow

### Step 1 — Read the hook config

```python
import yaml
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
```

### Step 2 — Normalise flags from both `entry` and `args`

Pre-commit hooks embed flags in either the `entry` string or a separate `args` list.
Write a helper that checks both so tests stay valid regardless of config style:

```python
def _all_flags(hook: dict) -> list[str]:
    """Return all CLI tokens from entry string + args list."""
    flags: list[str] = []
    entry = hook.get("entry", "")
    if entry:
        flags.extend(entry.split())   # e.g. "pixi run bandit -ll --skip B310,B202"
    flags.extend(hook.get("args", []))
    return flags
```

### Step 3 — Test skip list presence and minimality

```python
def _get_skip_ids(hook: dict) -> list[str]:
    flags = _all_flags(hook)
    skip_value = ""
    for i, flag in enumerate(flags):
        if flag.startswith("--skip="):
            skip_value = flag.split("=", 1)[1]
            break
        if flag == "--skip" and i + 1 < len(flags):
            skip_value = flags[i + 1]
            break
    return [s.strip() for s in skip_value.split(",") if s.strip()]

def test_b310_is_skipped(bandit_hook):
    skip_ids = _get_skip_ids(bandit_hook)
    assert "B310" in skip_ids, "B310 must be skipped — urlopen with hardcoded URLs"

def test_skip_list_is_minimal(bandit_hook):
    """Fail if undocumented IDs are added — forces rationale documentation."""
    documented = {"B310", "B202"}
    undocumented = set(_get_skip_ids(bandit_hook)) - documented
    assert not undocumented, f"Undocumented skip IDs: {undocumented}"
```

### Step 4 — Test `files:` pattern with parametrize

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
    "examples/train_lenet5.py",
])
def test_pattern_excludes_non_targets(bandit_hook, path):
    pattern = bandit_hook.get("files", "")
    assert not re.search(pattern, path)
```

### Step 5 — Verify suppressions reflect real codebase usage

```python
def test_b310_trigger_exists():
    """Fails if urlopen() disappears — suppression may become stale."""
    scripts_dir = REPO_ROOT / "scripts"
    found = [f for f in scripts_dir.glob("*.py") if "urlopen" in f.read_text()]
    assert found, "B310 skip may be stale — no urlopen() in scripts/"

def test_b310_uses_hardcoded_urls():
    """urlopen() must call a module-level URL constant, not user input."""
    for script in (REPO_ROOT / "scripts").glob("download_*.py"):
        src = script.read_text()
        if "urlopen" in src:
            assert re.search(r'^[A-Z][A-Z0-9_]*URL\s*=\s*["\']', src, re.MULTILINE), \
                f"{script.name}: no hardcoded *URL constant found"
```

### Step 6 — Run and verify

```bash
pixi run python -m pytest tests/scripts/test_bandit_hook_config.py -v
# 27 passed in 0.07s
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Check only `args` list for `--skip` | Looked for skip IDs in `hook["args"]` | The actual config used `entry: "pixi run bandit -ll --skip B310,B202"` — flags were in the entry string, not `args` | Always normalise flags from both `entry` and `args`; write a `_all_flags()` helper |
| Assert `https://` in scripts using `urlopen` | Checked that download scripts use HTTPS URLs | `download_mnist.py` and `download_fashion_mnist.py` use `http://` for their original mirrors | The safety property is "hardcoded constant", not "https". Check for a module-level `*URL = "..."` constant instead |
| Regex `[A-Z_]+BASE_URL\s*=` for URL constants | Looked for `*BASE_URL` naming pattern | `download_cifar10.py` uses `CIFAR10_URL` (not `BASE_URL`) | Use broader pattern `^[A-Z][A-Z0-9_]*URL\s*=\s*["\']` with `re.MULTILINE` |
| Single commit on hook failure | Expected pre-commit to leave file unchanged | Ruff reformatted the file, changing whitespace/line lengths; re-staging needed | After a hook modifies files, re-stage and commit again (never use `--no-verify`) |

## Results & Parameters

### Final test structure (27 tests, 0.07s)

```text
TestBanditHookExists        (4 tests)  — hook id, entry, name present
TestBanditSkipList          (4 tests)  — --skip present, B310/B202 in list, list minimal
TestBanditSeverityThreshold (2 tests)  — -ll present, -l alone rejected
TestBanditFilesPattern      (12 tests) — 8 match + 4 exclude, parametrized
TestBanditNosecRationale    (4 tests)  — urlopen/extractall exist, safe usage verified
```

### Key imports

```python
import re
from pathlib import Path
import pytest
import yaml
```

No `subprocess`, no pre-commit invocation, no bandit binary required.

### Minimality guard pattern

```python
DOCUMENTED_SKIPS = {"B310", "B202"}

def test_skip_list_is_minimal(bandit_hook):
    undocumented = set(_get_skip_ids(bandit_hook)) - DOCUMENTED_SKIPS
    assert not undocumented, (
        f"Undocumented bandit skip IDs found: {undocumented}. "
        "Add rationale to TestBanditSkipList docstring before expanding."
    )
```

This pattern forces any future skip additions to go through a documented rationale in the test class docstring.
