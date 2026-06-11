---
name: projecthephaestus-d103-test-docstrings
description: "ProjectHephaestus enforces ruff D103 on test functions too — every new test_* function needs a one-line docstring or CI fails. Use when: (1) adding new tests or public functions to ProjectHephaestus, (2) seeing D103 / ruff-format failures in ProjectHephaestus CI."
category: ci-cd
date: 2026-06-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - projecthephaestus
  - ruff
  - docstring
  - d103
  - pre-commit
  - ci
---

# ProjectHephaestus: D103 Docstrings Required on Tests

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-10 |
| **Objective** | Capture the ProjectHephaestus-specific lint policy that ruff D103 ("Missing docstring in public function") applies to `tests/` too — not just `hephaestus/` — and the strict `ruff format` reflow rules that bite freshly-authored modules. |
| **Outcome** | SUCCESS — PR #1069 merged green at 2026-06-10T02:58:16Z after fix commit `1e01e0f0` added one-line docstrings to every new `test_*` function plus `scan()`/`main()` in the new validation module, and let `ruff format` reflow hand-formatted `subprocess.run(...)` and `re.compile(...)` calls. |
| **Verification** | verified-ci — PR #1069 lint job went green after the fix commit; the PR merged. |

## When to Use

- Adding any new `.py` file to ProjectHephaestus — production code under `hephaestus/` or test code under `tests/`.
- CI lint job fails with `D103 Missing docstring in public function` on a `test_*` function.
- CI ruff-format hook fails on a multi-line `subprocess.run([...], capture_output=True, text=True, check=True)` you hand-formatted.
- CI ruff-format hook fails on a `re.compile(r"...")` you broke across multiple lines.
- You're about to push new ProjectHephaestus code and have not run `pre-commit run --all-files` first.

## Verified Workflow

### Quick Reference

```bash
# BEFORE pushing any new .py files in ProjectHephaestus:
pixi run ruff check hephaestus/ tests/
pixi run ruff format hephaestus/ tests/

# Or, comprehensively (catches every hook CI runs):
pre-commit run --all-files
```

### Detailed Steps

1. **Every new public function in `hephaestus/` AND in `tests/` needs a one-line docstring.**
   Ruff D103 does NOT exempt `tests/` in ProjectHephaestus — the `pyproject.toml` ruff config has no per-directory ignore for D-rules on tests. Every `test_*` function is a public function from ruff's perspective.

2. **For test functions, the name already conveys intent — keep the docstring short.**
   Example: `"""Verify shell helper defines the function."""` or `"""Verify flags hardcoded rebase."""`. One line, ending in a period, in imperative or third-person mood.

3. **For public functions in `hephaestus/`, prefer Google-style docstrings with `Args:` and `Returns:`.**
   Example for `scan()` and `main()` in `hephaestus/validation/skill_merge_method.py`:
   ```python
   def scan(paths: list[Path]) -> list[Finding]:
       """Scan paths for skill-merge-method violations.

       Args:
           paths: Paths to scan.

       Returns:
           List of findings.
       """
   ```

4. **After adding docstrings, run `pixi run ruff format hephaestus/ tests/` — do not hand-format.**
   Ruff format will:
   - Reflow `subprocess.run([...], capture_output=True, text=True, check=True)` onto one argument per line when the line exceeds the width budget.
   - Collapse a `re.compile(r"...")` you wrote across 3 lines back onto a single line when it fits.
   - Add a blank line after a module-level docstring.
   Fighting these is wasted churn; just let the formatter own layout.

5. **Run `pre-commit run --all-files` once before pushing.**
   This catches D103, ruff-format reflow, markdownlint, yamllint, and every other hook the CI lint job runs. The cost of one local run is much less than a fail-then-fix CI round-trip.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Push new `test_*` functions without docstrings | `test_shell_helper_defines_function`, `test_flags_hardcoded_rebase`, and the five `test_skill_merge_method` cases were written without docstrings, assuming pytest tests are exempt | Ruff D103 flagged every new `test_*` function in CI; lint job red on the initial push of PR #1069 | ProjectHephaestus ruff config does NOT exempt `tests/`; add `"""Verify X."""` to every new test function |
| Push new validation module with undocumented public funcs | `scan()` and `main()` in `hephaestus/validation/skill_merge_method.py` had no docstrings | D103 fired in CI lint job for both public symbols | Public functions in `hephaestus/` need Google-style docstrings with `Args:` and `Returns:` |
| Hand-format multi-line `subprocess.run(...)` and 3-line `re.compile(...)` | Wrote `subprocess.run([...], capture_output=True, text=True, check=True)` on one logical line, and broke `re.compile(r"...")` across 3 lines | Ruff format wanted args reflowed (one per line) and the regex collapsed back to one line | Don't fight ruff format; run `pixi run ruff format` before pushing |

## Results & Parameters

- **PR**: ProjectHephaestus#1069 (issue #911), merged 2026-06-10T02:58:16Z.
- **Fix commit**: `1e01e0f0` ("fix: Address CI failures for PR ProjectHephaestus#1069").
- **Files affected by the fix commit**:
  - `hephaestus/validation/skill_merge_method.py` — added docstrings to `scan()` and `main()`, ruff-format reflow of `subprocess.run(...)` and `re.compile(...)`, blank line after module docstring.
  - `tests/integration/test_choose_merge_flag_sh.py` — added docstrings to 2 new `test_*` functions.
  - `tests/unit/github/test_tidy_agent_prompt_merge_method.py` — added docstring to 1 new `test_*` function.
  - `tests/unit/validation/test_skill_merge_method.py` — added docstrings to 5 new `test_*` functions.
- **Config reference**: ProjectHephaestus's `pyproject.toml` ruff configuration does not add a per-directory ignore for D103 on `tests/`. D103 fires repo-wide, so every new `test_*` function in the test suite must carry a docstring.
- **Cost of one local `pre-commit run --all-files`**: seconds — strictly cheaper than a CI fail-then-fix cycle, which costs a separate fix commit, a PR re-review pass, and a re-run of the entire CI matrix.
