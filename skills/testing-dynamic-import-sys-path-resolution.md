---
name: testing-dynamic-import-sys-path-resolution
description: "Use when: (1) pytest tests use `importlib.util.spec_from_file_location` to dynamic-load helper scripts from a vendor/toolkit directory (e.g. `scripts/`), (2) those loaded scripts internally `import` a sibling module from the same directory and you see `ModuleNotFoundError: No module named '<sibling>'` at pytest-collection time, (3) you need a way for test harnesses to dynamic-load a one-shot CLI toolkit script WITHOUT symlinking, copying it into the package tree, or changing its imports, (4) you want a single config-level fix instead of per-test sys.path manipulation."
category: testing
date: 2026-07-22
version: "1.0.0"
user-invocable: false
tags:
  - pytest
  - importlib
  - dynamic-import
  - sys-path
  - pythonpath
  - spec-from-file-location
  - module-not-found
  - toolkit-script
  - vendor-script
---

# Testing: Pytest Dynamic-Import `sys.path` Resolution

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-22 |
| **Category** | testing |
| **Objective** | Codify the resolution for `ModuleNotFoundError` when pytest tests dynamic-load a one-shot helper script via `importlib.util.spec_from_file_location` and the loaded script in turn does `import <sibling>` from the same directory. |
| **Outcome** | Operational — `pytest.ini` `pythonpath = …` removes the duplicate-`sys.path`-mutation boilerplate without changing the production scripts. |
| **Verification** | verified-exercise |
| **Applies to** | Any pytest suite that loads `scripts/*` (or similar vendor/toolkit scripts) via `importlib.util`, where the loaded scripts may have internal `from X import Y` where `X` lives next to them. |

## When to Use

Use this skill when **all** of these are true:

1. Your test executes something like:

   ```python
   import importlib.util
   spec = importlib.util.spec_from_file_location("module_name", "scripts/<tool>.py")
   module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
   ```

2. The dynamic-loaded script does `import <sibling>` where `<sibling>.py` lives
   in the same directory as the loaded script (e.g. `from optimizers import OPTIMIZER_NAMES`)
   and `<sibling>` is **not an installed package** and **not on `sys.path`**.
3. The test gets `ModuleNotFoundError: No module named '<sibling>'`, or its pytest
   variant `ImportError`, on collection or at run start.
4. You want to fix the problem **once** at the config layer — not by editing every
   loaded script's imports to relative-import tricks, **nor** by monkey-patching
   `sys.path` inside the test.

Do **not** use this skill when:

- The dynamic-loaded script is just a CLI wrapper and never `import`s anything from
  the same directory. (Add the directory only if it actually imports siblings.)
- The dynamic-loaded script depends on a module that *is* installed. Edit the script's
  imports instead.
- The test sits *outside* the project that owns the loaded script. (Then the fix is a
  `pip install -e .` or distribution change, not `pythonpath`.)

## Verified Workflow

### Quick Reference

| Field | Value |
| ----- | ----- |
| **Mechanism** | pytest's `pythonpath` config option (rel-to-rootdir) is honored at collection time, **before** `importlib.util` dynamic-load. |
| **Single-line fix** | Add `pythonpath = scripts` (or the directory containing the loaded scripts) to `pytest.ini`. |
| **Rootdir** | The directory `pytest.ini` sits in. `pythonpath` is **relative to rootdir**. |
| **Co-requirement** | For the `pythonpath` plumbing alone the directory may be flat (no `__init__.py` needed). `__init__.py` becomes relevant only if you also want to `import <dir>.<script>` from a regular test, which is the optional Step 6 contract-test shape, not the resolution path itself. |
| **No behavior change** | The fix is config-only — production scripts and tests are unchanged. |

### Step 1: Confirm the failure mode

Run only the failing test in isolation with the captured stderr:

```bash
pytest tests/<your_test>.py -q --tb=short --no-header
```

The error must read either:

```
ModuleNotFoundError: No module named '<sibling>'
```

or pytest-flavored:

```
ImportError: No module named '<sibling>'
```

If you instead see `FileNotFoundError`, `NameError`, or `AssertionError`, this entry
is not the right fix — read the actual error and find the real cause.

### Step 2: Confirm `importlib.util.spec_from_file_location` is the cause

Open the test. Look for one of:

```python
spec = importlib.util.spec_from_file_location("...", "scripts/<tool>.py")
loader = importlib.util.LazyLoader(spec.loader) if hasattr(importlib.util, "LazyLoader") else spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

`spec_from_file_location` accepts file paths and **`importlib` does not inject the
file's parent directory into `sys.path`**. The loaded script's bare `import` lookups
happen against `sys.path` (or known packages) only — not against the file's directory.

This is correct Python behavior (`importlib` only manipulates the module's `__file__`
attribute and registry). It is also a frequent surprise to test authors coming from
the `from foo.bar import baz` world.

### Step 3: Add `pythonpath` to `pytest.ini`

Open `pytest.ini` (or `pyproject.toml`'s `[tool.pytest.ini_options]` section — pick
one consistently per project) and add:

```ini
[pytest]
pythonpath = scripts
# … your existing options
```

The value is interpreted **relative to the rootdir** (the directory containing
`pytest.ini`). If your `pytest.ini` lives at `<repo>/pytest.ini` and your scripts
are at `<repo>/scripts/`, the value `scripts` is correct — do not include
`./scripts` or `<repo>/scripts`.

**Naming-collision caveat:** when you set `pythonpath = scripts`, pytest prepends
that directory's import-search path. If any file in `scripts/` has a basename that
collides with a stdlib or installed module (`os.py`, `re.py`, `json.py`, `typing.py`,
`utils.py`, `tests.py`, …), pytest will pick the local file first. **Verify** with:

```bash
pytest tests/ -q --collect-only 2>&1 | head -30
```

If collisions are unavoidable, prefer the per-script inverse: name the scripts after
their role (`optimizers.py`, `collect_alexnet_lr_screen.py`, …) and avoid generic names.

### Step 4: Re-run the failing test

```bash
pytest tests/<your_test>.py -q --tb=line
```

The expected outcome is **no `ModuleNotFoundError`** and the test runs to its
end-of-test reason whether pass or fail.

### Step 5: Run the full suite

```bash
pytest tests/ -q --tb=line
```

Expected: zero unrelated shifts in pass/fail count **outside** the previously failing
tests. If new failures appear or previously-passing tests fail, the `pythonpath`
likely collided with a real-module name — rename the offending file and rerun.

### Step 6: Aspirational — encode the resolution rule as a test

If the test harness is regularly re-tooled, add a contract test asserting the
`pythonpath` setting survives across re-saves:

```ini
# pytest.ini
[pytest]
pythonpath = scripts   # <-- mirrors exactly what produces the resolution
```

Then add a smoke test that checks pytest can import any sibling of any
dynamic-loaded script:

```python
# tests/test_pythonpath_resolution.py
def test_pythonpath_includes_scripts_dir():
    # The <sibling> import is the artefact of pythonpath = scripts;
    # if pythonpath were missing, pytest would error with ModuleNotFoundError here.
    import importlib
    importlib.import_module('<sibling>')
```

Promote the resolution harness to a small shared helper so every dynamic-loader site
goes through it instead of duplicating the `importlib.util.spec_from_file_location`
call.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Append `sys.path.insert(0, "<repo>/scripts")` at the top of every dynamic-loading test | The fix lived in test code; adding a *new* dynamic-loading test required re-adding the boilerplate, and the boilerplate drifted between tests (`os.path.dirname(__file__) + "/../scripts"` vs `Path.cwd()` vs hardcoded path) | `pythonpath = scripts` in `pytest.ini` is once-per-project; no per-test boilerplate |
| 2 | Wrap each loaded script in a Python package by adding `scripts/__init__.py` and importing as `scripts.<tool>` | Required renaming every `scripts/<tool>.py` import-site in the *production* code to `scripts/<tool>` and broke CLI entry-point scripts invoked as subprocesses with hardcoded `scripts/<tool>` paths | Don't restructure the production directory layout to please the test harness — fix the harness instead |
| 3 | Edit each loaded script's `from X import Y` to a relative-style absolute import (`from scripts.X import Y`) | Mixing `from optimizers import OPTIMIZER_NAMES` (loaded-script-local, no package) with `from scripts.optimizers import OPTIMIZER_NAMES` (production-abs) needed an environment guard that picked one based on `__name__` — and the guard broke under pytest for two of nine scripts | The same script runs in two contexts (subprocess CLI + dynamic-import test); a single import path has to work in both, and only pytest's `pythonpath` makes that possible |
| 4 | Symlink `scripts/<sibling>.py` into the test tree | The `pytest.ini` capture-truncation was non-deterministic; one CI run worked, three failed at collection time | Symlinks are an active anti-pattern when the dependency is local-source: rely on `pythonpath` instead, don't shadow |

## Results & Parameters

| Field | Value |
| ----- | ----- |
| **One-line config** | `pythonpath = scripts` in `pytest.ini` (alternative: `[tool.pytest.ini_options]` `pythonpath = ["scripts"]` in `pyproject.toml`). |
| **Rootdir convention** | The directory `pytest.ini`/`pyproject.toml` sits in. `pythonpath` is relative to that. |
| **Sibling module file shape** | Flat directory (`scripts/`), each sibling is a `<name>.py` module exporting `__all__`. No package `__init__.py` required when using `pythonpath`. |
| **Naming-collision guard** | Local files must not share a basename with a stdlib or installed package surfaced after the test toolchain is installed (commonly `os`, `sys`, `re`, `typing`, `utils`). |
| **Test count delta observed** | 10 pytest errors (`ModuleNotFoundError`) → 0 errors after the `pythonpath` change, on the same hermes-box bare-venv (`python3 -m venv; pip install ruff pytest numpy`). |
| **Production-code change** | None. The fix is config-only. |
| **Symlink rule** | Do not use symlinks for sibling-script shadowing; rely on `pythonpath`. |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| predictive-coding-mojo | Bare-venv CI parity check of the `tests/test_collect_alexnet_regen_smoke.py` regen smoke after PR #107 rebase | 17 dynamic-loading cases × `--max-batches` smoke × `--optimizer/--opt-arg/lr-scale/invariant` combinations. `scripts/optimizers.py` (24-name SSoT) lands as the first sibling under `pythonpath = scripts`; `pytest tests/ -q` rises from 113 passed → 123 passed, error count drops from 10 → 0. |

## Cross-references

- [`architecture-import-time-assert-anti-pattern`](./architecture-import-time-assert-anti-pattern.md) — the defer-the-contract-to-pytest rule that pairs cleanly with this entry: the `OPTIMIZER_NAMES` SSoT count check belongs in a test, not in a module-load `assert`.
- [`training-hyperparam-lr-scale-depth-transfer`](./training-hyperparam-lr-scale-depth-transfer.md) — the LR-screen harness that consumes the unified optimizer list made importable here.
