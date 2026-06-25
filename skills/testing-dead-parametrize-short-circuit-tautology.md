---
name: testing-dead-parametrize-short-circuit-tautology
description: "Use when: (1) a parametrized test contains a conditional ternary/if-else that returns a hardcoded value for certain parametrize inputs instead of calling the function under test; (2) a test asserts a trivially-true condition (e.g. `assert 1 != 0`) because the ternary short-circuited before the real call; (3) a code reviewer flags a parametrize case as 'dead test weight' or 'tautological assertion'; (4) testing invalid inputs in a CLI tool where some inputs trigger argparse's own error path rather than the application validator."
category: testing
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [testing, parametrize, short-circuit, tautology, dead-test, argparse, invalid-input, coverage]
---

# Dead Parametrized Test Case: Short-Circuit Before Code Under Test

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-22 |
| **Objective** | Recognize and fix dead parametrized test cases that short-circuit before calling the code under test, producing a tautological assertion |
| **Outcome** | Reviewer caught this in PR #1570 and the fix removes the ternary so all parametrized cases genuinely exercise the validator |
| **Verification** | verified-local |

## When to Use

- A parametrized test has a ternary like `rc = func(args) if condition else hardcoded_value` — any branch that returns `hardcoded_value` never calls the function under test
- A reviewer comments "dead test weight", "tautological assertion", or "this case short-circuits"
- You see `assert X != 0` where `X` was assigned a hardcoded integer, not a function return value
- Testing CLI tools with invalid inputs: some inputs may reach argparse's own error path (`SystemExit`), others reach the application validator — both paths must be genuinely exercised
- A parametrize case was added to cover an edge input (empty string, `None`, zero) but the test body guards against passing it to the SUT

## Verified Workflow (Quick Reference)

```python
# BROKEN — short-circuit means "" case never calls main()
@pytest.mark.parametrize("name", ["Bad-Name", "1abc", "", "CamelCase"])
def test_invalid_name_nonzero_exit(self, name: str, tmp_path: Path) -> None:
    args = [name] if name else []
    rc = main(["--root", str(tmp_path), *args]) if name else 1  # <- short-circuit!
    assert rc != 0  # tautological for "" case: asserts 1 != 0

# FIXED — all cases call main() unconditionally
@pytest.mark.parametrize("name", ["Bad-Name", "1abc", "", "CamelCase"])
def test_invalid_name_nonzero_exit(self, name: str, tmp_path: Path) -> None:
    rc = main(["--root", str(tmp_path), name])  # "" passed as positional token
    assert rc != 0  # genuinely tests the validator for all cases
```

## Detailed Steps

1. **Spot the pattern**: look for parametrized tests where some branches of a ternary (`if condition else hardcoded_value`) never call the function under test. The tell-tale sign is a hardcoded integer (e.g., `1`, `0`, `-1`) on the right-hand side of `else`.

2. **Check what the SUT actually does** with the edge-case input: does it reach the application validator, or does argparse handle it earlier (raising `SystemExit`)? Either outcome is acceptable as long as the test calls the function and observes a real exit code. Use `pytest.raises(SystemExit)` if argparse exits with a non-zero code directly.

3. **Remove the ternary**. Pass the edge-case input directly to the function under test. For a CLI tool, pass `""` as a positional argv token — argparse accepts it as a string and passes it to the application, where the application's own validator will reject it.

4. **Run the test** to confirm the previously-tautological case now genuinely exercises a real code path and the assertion holds for a real reason.

```bash
# Verify the fix
pixi run pytest tests/unit/scripts_lib/test_scaffold_subpackage.py -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ternary short-circuit for empty string | `rc = main(args) if name else 1` to avoid "empty argv" issues | For `name=""`, the function was never called — `rc=1` was hardcoded, making `assert rc != 0` trivially true with zero coverage of the validation path | Always call the function under test unconditionally; use `pytest.raises(SystemExit)` if argparse exits rather than returning a non-zero integer |
| Dropping `""` from params | Alternative: remove `""` from the parametrize list entirely | Hides the coverage gap rather than fixing it; `_validate_name("")` path stays untested | Pass `""` as a real argv token — argparse accepts it as a positional string and passes it to the application validator |

## Results & Parameters

- **What the fix does**: passes `""` as the positional argv token directly to `main()`. Argparse accepts `""` as a valid positional string and passes it to `args.name`. The application's `_validate_name("")` then returns `"Name must not be empty"`, and `main()` returns `1` for real.
- **Verification command**: `pixi run pytest tests/unit/scripts_lib/test_scaffold_subpackage.py -v` (28 passed)
- **Key insight**: argparse does not reject empty-string positional arguments — it passes them through to the application. The application's validator is therefore responsible for the rejection, and the test correctly exercises that path.

## Verified On

**ProjectHephaestus | PR #1570, issue #1554** — `test_invalid_name_nonzero_exit` had a ternary short-circuit for the `""` case; reviewer flagged as "dead test weight — tautological assertion"; fixed by removing the ternary so `main()` is called unconditionally for all parametrized inputs.
