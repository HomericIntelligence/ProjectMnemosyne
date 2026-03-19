---
name: enable-mypy-check-untyped-defs
description: 'Enable mypy --check-untyped-defs for full Python body type coverage
  and fix surfaced errors. Use when: mypy reports untyped function bodies are not
  checked, or when enabling stricter type coverage.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low — purely additive type checking |
| Time | 15–30 minutes |

## When to Use

- mypy reports: `note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs`
- Adding stricter type-checking coverage to a project
- Enabling `check_untyped_defs = true` in `pyproject.toml` or `--check-untyped-defs` in pre-commit mypy hook
- After adding `disallow_untyped_defs = true` and wanting to also check function bodies

## Verified Workflow

### Step 1: Triage errors before enabling

Always run mypy with the flag first (without committing config changes) to see all errors:

```bash
pixi run mypy scripts/ --check-untyped-defs --exclude generators/
```

Fix all surfaced errors before adding to config files.

### Step 2: Common errors and fixes

**`defaultdict` missing type annotation** (var-annotated):

```python
# Before (fails in untyped body)
file_counts = defaultdict(int)

# After
file_counts: defaultdict[str, int] = defaultdict(int)
```

**Empty list missing annotation** (var-annotated):

```python
# Before
optional = []

# After
optional: list[str] = []
```

**Deprecated Pillow attributes** (attr-defined — Pillow 10+):

```python
# Before (deprecated module-level aliases)
img = img.resize((28, 28), Image.LANCZOS)
img = img.transpose(Image.TRANSPOSE).transpose(Image.FLIP_LEFT_RIGHT)

# After (use enum namespaces)
img = img.resize((28, 28), Image.Resampling.LANCZOS)
img = img.transpose(Image.Transpose.TRANSPOSE).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
```

### Step 3: Update pyproject.toml

```toml
[tool.mypy]
disallow_untyped_defs = true
check_untyped_defs = true
```

### Step 4: Update pre-commit hook

```yaml
- id: mypy
  args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --check-untyped-defs, --python-version, "3.10"]
```

### Step 5: Verify

```bash
pixi run mypy scripts/ --check-untyped-defs --exclude generators/
# → Success: no issues found in N source files

pixi run pre-commit run mypy --all-files
# → mypy.....Passed

pixi run pre-commit run --all-files
# → All hooks passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | No failed attempts — triage-first approach worked | — | Always run the flag manually before committing config to avoid surprise failures |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3370, PR #4036 | [notes.md](../../references/notes.md) |

## Results & Parameters

### pyproject.toml

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
check_untyped_defs = true
explicit_package_bases = true
mypy_path = "."
exclude = "generators/"
```

### .pre-commit-config.yaml

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      files: ^scripts/.*\.py$
      args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --check-untyped-defs, --python-version, "3.10"]
      additional_dependencies: [types-PyYAML]
```

### Triage command

```bash
# Run before touching config files to see all errors upfront
pixi run mypy <source-dir>/ --check-untyped-defs --exclude <excluded-dir>/
```
