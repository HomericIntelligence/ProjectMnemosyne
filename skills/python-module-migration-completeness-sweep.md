---
name: python-module-migration-completeness-sweep
description: "Ensure zero stale references when moving a Python module to a new package path. Use when: (1) moving scripts/X.py to X/__init__.py, (2) renaming a module, (3) any import path change that affects multiple file types."
category: architecture
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, module-migration, import-sweep, refactoring, completeness]
---

# Python Module Migration Completeness Sweep

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Move scripts/inference360.py to inference360/__init__.py and ensure zero stale references across the entire repository |
| **Outcome** | Successfully migrated with zero remaining stale references after comprehensive sweep |
| **Verification** | verified-local |

## When to Use

- Moving a Python module from one package to another (e.g., scripts/X.py to X/__init__.py)
- Renaming a module that is referenced across multiple file types
- Any import path change that affects shell scripts, justfile, docs, CI configs, and test monkeypatch strings

## Verified Workflow

### Quick Reference

```bash
# After module move, sweep ALL file types for stale references
grep -rn "old.module.path" \
  --include="*.py" --include="*.sh" --include="*.yaml" \
  --include="*.yml" --include="*.toml" --include="*.j2" \
  --include="*.md" . 2>/dev/null \
  | grep -v third_party | grep -v .venv | grep -v __pycache__ \
  | grep -v .git/ | grep -v docs/assessments/
```

### Detailed Steps

1. **Use git mv** to preserve file history: `git mv scripts/X.py X/__init__.py`
2. **Create __main__.py** for `python -m X` support:
   ```python
   from __future__ import annotations
   from . import main
   if __name__ == "__main__":
       raise SystemExit(main())
   ```
3. **Update pyproject.toml**:
   - Add new package to `[tool.setuptools.packages.find]`
   - Add to coverage sources in `[tool.coverage.run]`
4. **Sweep ALL file types** for stale references:
   - Python imports: `from scripts.X` and `import scripts.X`
   - Test monkeypatch strings: `monkeypatch.setattr("scripts.X.SYMBOL", ...)`
   - Shell scripts: `python -m scripts.X` invocations
   - Justfile: recipe commands
   - Markdown docs: CLI invocation examples in runbooks
   - Jinja2 templates: path references
5. **Exclude historical docs** (e.g., docs/assessments/) from the sweep
6. **Verify completeness**: grep sweep should return ZERO results outside excluded paths

### Subprocess Binary Verification Pattern

When testing helpers that locate and verify external binaries, always use `check=True`:

```python
def _just_bin() -> str:
    local_just = ROOT / ".bin" / "just"
    if local_just.exists():
        return str(local_just)
    found = which("just")
    if found is None:
        pytest.skip("just is required")
    try:
        subprocess.run([found, "--version"], capture_output=True, check=True, text=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("just binary is not available or broken")
    return found
```

**Why check=True**: Using `check=False` without manually checking `returncode` means broken binaries that exit with code 1 pass through silently.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sweep only .py files | grep only Python files for stale refs | Missed monkeypatch strings, shell scripts, justfile, docs | Must sweep ALL file types |
| Exclude docs/ entirely | Skip all docs during sweep | Missed docs/runbooks/ with CLI examples | Only exclude historical docs, not operational docs |
| check=False with manual returncode | subprocess.run check=False then check returncode | Broke when code simplified away the manual check | Use check=True and catch CalledProcessError |
| sed with dotted patterns only | sed -i s/scripts.X/new.X/g | Missed shell script path formats | Use both dotted and slashed patterns |

## Results & Parameters

- **Files migrated**: scripts/inference360.py to inference360/__init__.py
- **Files updated**: 52 files across tests, scripts, justfile, docs, CI configs
- **Stale references after sweep**: 0 (outside excluded historical docs)
- **Test results**: 533 passed, 16 skipped
- **Coverage**: 80.13% (fail_under=80)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | PR #116 (closes #82) | scripts/inference360.py to inference360/__init__.py, 52 files changed |
