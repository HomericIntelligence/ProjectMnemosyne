---
name: bandit-replace-pygrep-security-hook
description: 'Replace a naive pygrep shell=True pre-commit hook with bandit for AST-based
  Python security scanning. Use when: false positives from pygrep, need to catch os.system/subprocess
  misuse, upgrading pre-commit security checks.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Bandit: Replace pygrep shell=True Pre-commit Hook

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-05 |
| **Objective** | Replace naive `shell=True` pygrep hook with bandit for accurate AST-based Python security scanning |
| **Outcome** | Zero false positives, 2 suppressions, catches 20+ vulnerability classes |
| **PR** | HomericIntelligence/ProjectOdyssey#3355 |
| **Issue** | HomericIntelligence/ProjectOdyssey#3157 |

## When to Use

Invoke when:

- A `pygrep shell=True` hook produces false positives in comments, docstrings, or string literals
- You need to catch `os.system()`, `subprocess.call(str)`, hardcoded passwords, SQL injection — not just `shell=True`
- Upgrading pre-commit security quality from string-match to AST-based analysis
- The pygrep hook misses injection vectors beyond `shell=True`

## Verified Workflow

### Step 1 — Audit existing codebase with bandit before changing the hook

Always run bandit first to identify what will trigger before modifying `.pre-commit-config.yaml`:

```bash
pixi run bandit -ll -r scripts/ tests/ 2>&1 | grep -E "Issue:|Location:|Total issues"
```

Key: `-ll` means **medium+ severity** (not "low level" as the flag name implies):

- `-l` = LOW severity and above
- `-ll` = MEDIUM severity and above (recommended starting point)
- `-lll` = HIGH severity only

### Step 2 — Categorize findings to determine skip list

Common finding patterns in ML/data science projects:

| Bandit ID | Description | Typical Verdict |
| ----------- | ------------- | ----------------- |
| B310 | `urlopen` with controlled URLs | Skip — intentional download scripts |
| B202 | `tarfile.extractall` without validation | Skip — dataset extraction scripts |
| B108 | Hardcoded `/tmp` directory | Add `# nosec B108` inline |
| B101 | `assert` statements | Skip or ignore — test code uses asserts |
| B311 | `random` for security | Evaluate case by case |

### Step 3 — Replace the pygrep hook in `.pre-commit-config.yaml`

```yaml
# Security checks - bandit for accurate Python security scanning
# Replaces naive pygrep shell=True check with AST-based analysis
# Skips: B310 (urlopen with controlled URLs), B202 (tarfile in download scripts)
- repo: local
  hooks:
    - id: bandit
      name: Bandit Security Scan
      description: Scan Python files for security vulnerabilities using bandit
      entry: pixi run bandit -ll --skip B310,B202
      language: system
      files: ^(scripts|tests)/.*\.py$
      types: [python]
      pass_filenames: true
```

Key design choices:
- `pass_filenames: true` — bandit receives individual staged files (efficient)
- `language: system` — uses `pixi run bandit` from the project environment
- `files:` — scope to `scripts/` and `tests/` (adjust to match your project layout)
- `--skip` — comma-separated list of test IDs to suppress at the hook level

### Step 4 — Add inline suppressions for remaining false positives

For `/tmp` in CLI default args or test code (acceptable suppressions):

```python
# CLI tool with user-overridable default
default=pathlib.Path("/tmp"),  # nosec B108 - CLI tool default, user-overridable

# Test code
fix_build_errors.cleanup_worktree(pathlib.Path("/tmp/test"), branch="test")  # nosec B108 - test code
```

### Step 5 — Add bandit to package manager dependencies

For pixi projects:

```toml
# pixi.toml
bandit = ">=1.7.5"
```

### Step 6 — Verify zero medium/high findings

```bash
pixi run bandit -ll --skip B310,B202 -r scripts/ tests/ 2>&1 | tail -10
# Expected: Medium: 0, High: 0
```

### Step 7 — Run pre-commit to confirm hook passes

```bash
pixi run pre-commit run --all-files
# Expected: Bandit Security Scan ... Passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `-ll` thinking it means "low level" | Expected it to flag only high-confidence issues | `-ll` actually means MEDIUM+ severity (not low), causing confusion about threshold | `-l` = LOW+, `-ll` = MEDIUM+, `-lll` = HIGH+ |
| Keeping B108 in skip list | Skipped all hardcoded /tmp warnings globally | Better to use inline `# nosec B108` so the skip is scoped and documented | Inline suppressions are more precise than global skips |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Severity threshold | `-ll` (medium and above) |
| Skipped test IDs | `B310` (urlopen), `B202` (tarfile) |
| Inline suppressions | 2x `# nosec B108` |
| Total false positives | 0 |
| Vulnerability classes detected | 20+ (shell injection, SQLi, hardcoded secrets, etc.) |
| Hook runtime | ~2-3s on 30k lines of Python |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3157, PR #3355 | [notes.md](../../references/notes.md) |

## Key Takeaway

Bandit with `-ll --skip <ids>` is the correct replacement for `pygrep shell=True`:

- AST-based: no false positives from comments/strings
- Catches `os.system()`, `subprocess.call(str)`, hardcoded passwords, SQL injection
- `-ll` = MEDIUM+ severity is the right default threshold
- Use `--skip` for project-level suppressions, `# nosec` for inline suppressions
- Add `pass_filenames: true` so pre-commit passes individual staged files
