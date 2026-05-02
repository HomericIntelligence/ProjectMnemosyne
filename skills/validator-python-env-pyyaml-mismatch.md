---
name: validator-python-env-pyyaml-mismatch
description: "Run a Python validation script when `python3` fails with `ModuleNotFoundError: No module named 'yaml'` because `python3` and `python` point at different environments. Use when: (1) `python3` lacks PyYAML, (2) `pip show pyyaml` appears installed anyway, (3) validation works only under a different interpreter such as conda-backed `python`."
category: tooling
date: 2026-04-03
version: "1.0.1"
user-invocable: false
verification: verified-local
tags:
  - validator
  - validation
  - python
  - pyyaml
  - environment
---

# Validator: Python Environment PyYAML Mismatch

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-03 |
| **Objective** | Get a Python validation script running when `python3` and `python` resolve to different environments with different installed packages |
| **Outcome** | Successful — `python3` failed to import `yaml`, `python` resolved to the conda interpreter with PyYAML installed, and validation passed under `python scripts/validate_plugins.py` |
| **Verification** | verified-local |

## When to Use

- `python3 <validator-script>` fails with `ModuleNotFoundError: No module named 'yaml'`
- `python3 -m pip show pyyaml` or other package checks give confusing results
- `which -a python python3` shows that `python` and `python3` are different binaries

## Verified Workflow

### Quick Reference

```bash
which -a python python3

python3 -c 'import sys; print(sys.executable); import yaml'
python -c 'import sys; print(sys.executable); import yaml; print(yaml.__file__)'

python <validator-script>
```

### Detailed Steps

1. Reproduce the validator failure exactly:
   ```bash
   python3 <validator-script>
   ```
   If the error is `ModuleNotFoundError: No module named 'yaml'`, the script itself may be fine and the interpreter environment may be wrong.

2. Compare the active interpreters:
   ```bash
   which -a python python3
   python3 -c 'import sys; print(sys.executable)'
   python -c 'import sys; print(sys.executable)'
   ```
   In the verified session:
   - `python3` resolved to `/opt/homebrew/opt/python@3.14/bin/python3.14`
   - `python` resolved to `/opt/homebrew/Caskroom/miniconda/base/bin/python`

3. Test whether each interpreter can import `yaml`:
   ```bash
   python3 -c 'import yaml'
   python -c 'import yaml; print(yaml.__file__)'
   ```
   If `python3` fails but `python` succeeds, do not install packages blindly yet. First confirm this is just an interpreter mismatch.

4. Run the validator with the interpreter that actually has PyYAML:
   ```bash
   python <validator-script>
   ```
   This is the fastest path when the conda-backed `python` already has the needed dependency.

5. Record the mismatch so future sessions do not waste time:
   - `python3` may be Homebrew or system Python
   - `python` may be the conda environment the repo actually expects
   - package presence in one interpreter says nothing about the other

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Ran `python3 <validator-script>` directly | The active `python3` interpreter did not have `PyYAML`, so the validator failed before checking any inputs | When a validator fails on `import yaml`, check interpreter resolution before debugging the validator logic |
| Attempt 2 | Trusted package presence checks without comparing interpreters | `python3 -m pip show pyyaml` did not prove that the same `python3` binary running the script could import `yaml` | Always print `sys.executable` for the exact interpreter that is failing |
| Attempt 3 | Assumed the fix required installing new dependencies | A working interpreter with PyYAML was already available as `python` from the conda environment | Prefer interpreter alignment over package installation when multiple Python environments coexist |

## Results & Parameters

**Interpreter mismatch observed in the verified session**:

```text
python3 -> /opt/homebrew/opt/python@3.14/bin/python3.14
python  -> /opt/homebrew/Caskroom/miniconda/base/bin/python
working yaml import -> /opt/homebrew/Caskroom/miniconda/base/lib/python3.13/site-packages/yaml/__init__.py
```

**Command pattern that failed**:

```bash
python3 <validator-script>
```

**Command pattern that worked**:

```bash
python <validator-script>
```

**Why this matters**:

- A validator can be correct even when the default `python3` in your shell is not
- Installing `PyYAML` into the wrong interpreter wastes time and can create more environment drift

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Python repository | Running a script-based validator from an isolated worktree | `python3` failed on `import yaml`, `python` resolved to the conda environment with PyYAML, and `python <validator-script>` passed once the interpreter mismatch was corrected |
