---
name: mypy-hyphenated-dir-per-file
description: 'Add mypy pre-commit coverage for directories with hyphenated names by
  running mypy per-file. Use when: extending mypy to examples/ with hyphenated subdirs,
  or fixing ''Duplicate module named'' errors.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | `mypy` receives multiple files sharing the same basename (e.g. `download_cifar10.py`) from different hyphenated subdirectories (e.g. `examples/alexnet-cifar10/`, `examples/resnet-cifar10/`). Because hyphens are not valid Python identifiers, mypy cannot resolve the parent directory as a package, and emits an unrecoverable **"Duplicate module named X"** blocker error. |
| **Root cause** | `pre-commit` passes all matched files in one `mypy` invocation. Hyphenated directory names cannot be used as Python package components, so mypy has no way to disambiguate duplicate basenames. |
| **Solution** | A thin wrapper script (`scripts/mypy-each-file.py`) that invokes `mypy` once per file, aggregating exit codes. The pre-commit hook is configured as a `local` hook pointing at this wrapper. |
| **Scope** | Any directory tree where subdirectory names contain hyphens and files may share basenames. Typical example: `examples/` in ML repos. |

## When to Use

Trigger this skill when:

1. You need to add mypy type-checking to `examples/` (or similar dirs) in `.pre-commit-config.yaml`.
2. A pre-commit mypy run fails with **"error: Duplicate module named 'X' (also at '...')"**.
3. The duplicated modules live in directories with hyphenated names that cannot be Python packages.
4. Extending bandit or other linters to `examples/` surfaces the need to add matching mypy coverage.

## Verified Workflow

### Quick Reference

```yaml
# .pre-commit-config.yaml — add this block
- repo: local
  hooks:
    - id: mypy-examples
      name: mypy (examples)
      description: Type-check Python files in examples/ one file at a time
      entry: pixi run python scripts/mypy-each-file.py --ignore-missing-imports --no-strict-optional --explicit-package-bases --check-untyped-defs --python-version 3.10
      language: system
      files: ^examples/.*\.py$
      types: [python]
      pass_filenames: true
```

```python
# scripts/mypy-each-file.py
#!/usr/bin/env python3
"""Run mypy on each file individually to avoid duplicate module name errors.

This wrapper is needed for directories with hyphenated names (e.g. examples/alexnet-cifar10/)
where multiple files share the same basename (download_cifar10.py). Passing them all to a
single mypy invocation causes a "Duplicate module named" blocker error because mypy cannot
resolve the hyphenated directory as a Python package component.

Usage:
    python scripts/mypy-each-file.py [mypy-args...] file1.py file2.py ...

The script separates mypy flags (starting with '-') from file paths, then runs mypy once
per file, aggregating exit codes.
"""

import sys
import subprocess


def main() -> int:
    args = sys.argv[1:]

    # Separate mypy flags from file paths (flags start with '-')
    flags: list[str] = []
    files: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("-"):
            flags.append(arg)
            # Some flags take a value argument (e.g. --python-version 3.10)
            if arg in ("--python-version", "--config-file", "--shadow-file", "--exclude"):
                i += 1
                if i < len(args):
                    flags.append(args[i])
        else:
            files.append(arg)
        i += 1

    if not files:
        print("mypy-each-file: no files to check", file=sys.stderr)
        return 0

    overall_rc = 0
    for filepath in files:
        cmd = [sys.executable, "-m", "mypy"] + flags + [filepath]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            overall_rc = result.returncode

    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
```

### Step-by-step

1. **Identify the gap**: Check `.pre-commit-config.yaml` — confirm mypy only covers `^scripts/.*\.py$`
   while linters like bandit already cover `^(tools|examples)/.*\.py$`.

2. **Understand why bulk invocation fails**: Run `pixi run python -m mypy --explicit-package-bases
   examples/alexnet-cifar10/download_cifar10.py examples/resnet-cifar10/download_cifar10.py` and
   observe the "Duplicate module named" error.

3. **Create the wrapper script** at `scripts/mypy-each-file.py` (see Quick Reference above).
   Key design decisions:
   - Parse flags (leading `-`) vs file paths separately.
   - Handle two-argument flags like `--python-version 3.10`.
   - Aggregate exit codes — return non-zero if any file fails.
   - Return 0 with a message when no files are provided (pre-commit may call with empty list).

4. **Add a `local` hook** to `.pre-commit-config.yaml` using `pass_filenames: true` so
   pre-commit passes the matched files to the wrapper.

5. **Match the existing mypy flags** from the `scripts/` hook (`--ignore-missing-imports`,
   `--no-strict-optional`, `--explicit-package-bases`, `--check-untyped-defs`,
   `--python-version 3.10`) for consistency.

6. **Verify locally**:

   ```bash
   just pre-commit-all
   # or
   pixi run pre-commit run mypy-examples --all-files
   ```

7. **Commit and PR**:

   ```bash
   git add .pre-commit-config.yaml scripts/mypy-each-file.py
   git commit -m "feat(pre-commit): add mypy type-checking coverage for examples/"
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bulk `mypy` invocation on all examples files | Pass all `^examples/.*\.py$` files directly to a single `mypy` run with `--explicit-package-bases` | `mypy` emits "Duplicate module named 'download_cifar10'" because `alexnet-cifar10` and `resnet-cifar10` are not valid Python identifiers — mypy cannot disambiguate the two `download_cifar10.py` files | Hyphenated directory names can never serve as Python package components; per-file invocation is the only robust solution |
| Using `namespace_packages = true` in mypy config | Attempted to configure mypy namespace package support to handle non-standard paths | Does not resolve the duplicate-module conflict when two files truly share the same basename at the same namespace level | The issue is a name collision, not a package discovery problem |
| Adding `--exclude` patterns | Tried excluding one of the duplicate subdirs per invocation | Would suppress legitimate type-check coverage on excluded dirs | Defeats the purpose of extending coverage; per-file wrapper is cleaner |

## Results & Parameters

### Wrapper Script Parameters

| Flag | Value | Purpose |
| ------ | ------- | --------- |
| `--ignore-missing-imports` | (flag) | Suppress errors for unresolved third-party imports |
| `--no-strict-optional` | (flag) | Allow implicit `Optional` — matches project's existing mypy config |
| `--explicit-package-bases` | (flag) | Required to avoid package-root confusion in non-package dirs |
| `--check-untyped-defs` | (flag) | Type-check function bodies even without annotations |
| `--python-version` | `3.10` | Matches the project's minimum supported Python version |

### Pre-commit Hook Config

```yaml
- repo: local
  hooks:
    - id: mypy-examples
      name: mypy (examples)
      description: Type-check Python files in examples/ one file at a time
      entry: pixi run python scripts/mypy-each-file.py --ignore-missing-imports --no-strict-optional --explicit-package-bases --check-untyped-defs --python-version 3.10
      language: system
      files: ^examples/.*\.py$
      types: [python]
      pass_filenames: true
```

### Wrapper Script Exit Code Behaviour

- Returns `0` if all files pass or no files are provided.
- Returns the last non-zero exit code if any file fails.
- Streams mypy output directly (no `capture_output`) so errors appear inline in the terminal.
