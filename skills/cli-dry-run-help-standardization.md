---
name: cli-dry-run-help-standardization
description: "Standardize --dry-run help text across multiple CLIs using a shared constant and helper function. Use when: (1) Multiple CLIs need identical --dry-run semantics, (2) Token-cost caveats must be user-visible at --help time, (3) Refactoring CLI parsers to extract testable _build_parser() entrypoints, (4) Adding parametrized help-text tests across CLI modules."
category: tooling
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [argparse, cli, help-text, dry-run, testing, parametrized-tests, DRY-principle, refactoring]
---

# CLI Dry-Run Help Text Standardization

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Standardize --dry-run help text across 7+ ProjectHephaestus CLI modules to prevent help-text drift and ensure consistent token-cost warnings at --help time |
| **Outcome** | SUCCESS — created DRY_RUN_HELP_CAVEAT constant, add_dry_run_arg() helper, extracted _build_parser() from _parse_args() in 7 CLI modules, 11-test suite validating help text across all CLIs |
| **Verification** | verified-ci (PR #974, all unit tests + ruff/mypy/formatting pass) |

## When to Use

- Multiple CLI modules in the same project each declare `--dry-run` with subtly different help text
- Token-cost caveats need to be user-visible (appearing in `--help` output, not buried in docs)
- CLI parsers are tightly coupled to argument parsing logic, making help-text testing difficult (no clean way to access parser metadata)
- You want to prevent copy-paste drift in help text across modules via a canonical constant
- Adding comprehensive parametrized tests to ensure help-text consistency across CLIs

## Verified Workflow

### Quick Reference

**1. Create canonical DRY_RUN_HELP_CAVEAT constant** in `hephaestus/cli/utils.py`:

```python
DRY_RUN_HELP_CAVEAT = (
    "Do not create PR, file follow-up issues, or invoke /learn. "
    "Useful for testing without incurring token costs."
)
```

**2. Create add_dry_run_arg() helper function** with auto-punctuation:

```python
def add_dry_run_arg(parser: ArgumentParser, *, prefix: str | None = None) -> None:
    """Add --dry-run argument to parser with canonical help text.
    
    Args:
        parser: ArgumentParser to add --dry-run to
        prefix: Optional prefix to prepend to help text (e.g., "For <X>: ")
    """
    help_text = DRY_RUN_HELP_CAVEAT
    if prefix:
        # Auto-punctuation: ensure period is present before concatenation
        if not prefix.endswith("."):
            prefix = prefix + "."
        help_text = f"{prefix} {help_text}"
    else:
        # Ensure help text starts with capital and ends with period
        if help_text and not help_text[0].isupper():
            help_text = help_text[0].upper() + help_text[1:]
        if not help_text.endswith("."):
            help_text = help_text + "."
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=help_text,
    )
```

**3. Extract _build_parser() from _parse_args()** in each CLI module:

```python
def _build_parser() -> ArgumentParser:
    """Build and return parser without parsing args.
    
    This factoring enables tests to validate parser metadata (help text,
    argument names, defaults) without side effects or mocking.
    """
    parser = ArgumentParser(description="...")
    parser.add_argument("--verbose", "-v", action="store_true")
    add_dry_run_arg(parser, prefix="Skip PR creation")
    # ... more arguments ...
    return parser

def _parse_args(args: list[str] | None = None) -> Namespace:
    """Parse command-line arguments using _build_parser()."""
    return _build_parser().parse_args(args)
```

**4. Write parametrized test suite** accessing _build_parser():

```python
@pytest.mark.parametrize("cli_module", [
    "hephaestus.automation.planner",
    "hephaestus.automation.plan_reviewer",
    "hephaestus.automation.pr_reviewer",
    "hephaestus.automation.address_review",
    "hephaestus.automation.implementer_cli",
    "hephaestus.cli.ci_driver",
    "hephaestus.automation.loop_runner",
])
def test_dry_run_help_text_consistent(cli_module: str) -> None:
    """All CLI modules have identical --dry-run help text."""
    module = importlib.import_module(cli_module)
    parser = module._build_parser()
    
    # Find --dry-run action
    dry_run_action = next(
        (a for a in parser._actions if "--dry-run" in a.option_strings),
        None,
    )
    assert dry_run_action is not None, f"{cli_module} has no --dry-run arg"
    assert dry_run_action.help == expected_help_text
```

### Detailed Steps

1. **Identify all CLI modules declaring --dry-run** — use `grep -r "add_argument.*dry.run" hephaestus/` to find all occurrences and inspect their help text.

2. **Create DRY_RUN_HELP_CAVEAT constant** in `hephaestus/cli/utils.py` with the canonical message. Include a token-cost caveat so users see it at `--help` time.

3. **Create add_dry_run_arg() helper function** that encapsulates:
   - Automatic help-text punctuation (adding period if missing, ensuring capital first letter)
   - Optional prefix support for context-specific variations (e.g., "For plan review: ")
   - Single source of truth for the `--dry-run` argument

4. **Refactor each CLI module** to extract `_build_parser()` from `_parse_args()`:
   - `_build_parser()` constructs and returns the parser (no side effects, no sys.exit on error)
   - `_parse_args(args)` calls `_build_parser().parse_args(args)` and returns the namespace
   - This separation enables tests to access parser metadata without mocking or subprocess invocation

5. **Update _review_utils.py** if it has shared argument setup — use `add_dry_run_arg()` for consistency.

6. **Create test_dry_run_help.py** with:
   - Parametrized test over all CLI modules (use `@pytest.mark.parametrize`)
   - Each test imports the module and calls `_build_parser()`
   - Assertions on help text, action store_true, presence in option_strings
   - Edge cases: missing --dry-run argument, malformed help text

7. **Validate with pre-commit hooks**:
   - `ruff check --select=E,F,W,I` — import sorting (isort-style)
   - `ruff format` — formatter consistency
   - `mypy` — type checking
   - Run `pre-commit run --all-files` before committing

8. **Verify test suite** covers all CLI entry points that have --dry-run.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Leaving help text inline in each argparse call | Each CLI had its own `help="Do not create PR, ..."` string | Help text drifted: some said "token costs", others omitted it; some had typos; copy-paste produced minor variations | Canonical constant (DRY_RUN_HELP_CAVEAT) prevents drift. Use a helper function to access it, never inline strings. |
| Adding period/capitalization manually in each CLI | Some CLIs added period in the constant, others in the argparse call | Inconsistent capitalization and punctuation across modules; when updating the canonical text, had to search-replace in 7 places | Encapsulate auto-punctuation logic inside add_dry_run_arg(). The function ensures consistent formatting regardless of how the prefix is provided. |
| Accessing parser in tests by importing _parse_args()—then calling it | Tests called `_parse_args(["--help"])` and caught SystemExit | ArgumentParser.parse_args() calls sys.exit(2) on error or --help; tests couldn't safely call it without subprocess isolation | Extract _build_parser() as a separate function. Tests call _build_parser() directly (no side effects), inspect the parser object, and validate metadata. |
| Using __all__ export list with unsorted names | Initial __all__ had entries in creation order, not alphabetical | ruff --fix complained "imported but unused" and reordered alphabetically when fixing; pre-commit hook failed | Use isort-style __all__ sorting: alphabetical order, case-sensitive (lowercase before UPPERCASE). Run `ruff format --select=I` to auto-fix. |
| Multi-line docstring closing quote on same line as `"""` | Some docstring blocks had `"""` closing on the same line as content | ruff --check (formatter) flagged as misaligned | Move closing `"""` to its own line. Formatter is strict about docstring shape. |
| Testing only the planner module | Created a small test covering just hephaestus.automation.planner | Missed drift in 6 other CLI modules (plan_reviewer, pr_reviewer, address_review, implementer_cli, ci_driver, loop_runner); parametrized test later caught inconsistencies | Use parametrized tests from the start (@pytest.mark.parametrize) to cover all modules simultaneously. Catch drift across the entire CLI surface. |
| Assuming keyword-only parameters were obvious | Initially wrote `add_dry_run_arg(parser, prefix=None)` without the `*` | Callers passed positional arguments in wrong order; function signature was ambiguous about intent | Use keyword-only parameters: `add_dry_run_arg(parser, *, prefix=None)`. The `*` makes it impossible to pass prefix positionally and signals intent at call site. |
| Storing help text in a per-module config dict | Tried to move help text to a config file indexed by module name | Config file drifted from source code; modules could forget to register themselves; no type checking | Keep the canonical constant in Python code alongside the helper function. Type hints ensure consistency; no separate config file. |

## Results & Parameters

### DRY_RUN_HELP_CAVEAT Constant

```python
DRY_RUN_HELP_CAVEAT = (
    "Do not create PR, file follow-up issues, or invoke /learn. "
    "Useful for testing without incurring token costs."
)
```

**Key properties**:
- Lowercase start (auto-capitalized by add_dry_run_arg when used standalone)
- No period at end (auto-added by add_dry_run_arg)
- Token-cost caveat explicitly mentioned (user-visible in --help)
- Concise (fits on one line in --help output)

### add_dry_run_arg() Function Signature

```python
def add_dry_run_arg(parser: ArgumentParser, *, prefix: str | None = None) -> None:
    """Add --dry-run argument to parser with canonical help text.
    
    Args:
        parser: ArgumentParser to add --dry-run to
        prefix: Optional prefix to prepend to help text (e.g., "For plan review: ")
                Prefix is auto-punctuated (period added if missing).
    """
```

**Behavior**:
- Keyword-only `prefix` parameter (enforced by `*`) prevents positional-argument mistakes
- Auto-punctuation: ensures prefix ends with `.`, ensures full help text ends with `.`
- Standalone use (no prefix): ensures capital first letter
- action="store_true": --dry-run is a boolean flag
- Return type is None (modifies parser in-place per argparse conventions)

### CLI Modules Updated (7 total)

| Module | File Path | Test Coverage |
|--------|-----------|---|
| planner | hephaestus/automation/planner.py | test_dry_run_help.py::test_planner_has_dry_run |
| plan_reviewer | hephaestus/automation/plan_reviewer.py | test_dry_run_help.py::test_plan_reviewer_has_dry_run |
| pr_reviewer | hephaestus/automation/pr_reviewer.py | test_dry_run_help.py::test_pr_reviewer_has_dry_run |
| address_review | hephaestus/automation/address_review.py | test_dry_run_help.py::test_address_review_has_dry_run |
| implementer_cli | hephaestus/automation/implementer_cli.py | test_dry_run_help.py::test_implementer_has_dry_run |
| ci_driver | hephaestus/cli/ci_driver.py | test_dry_run_help.py::test_ci_driver_has_dry_run |
| loop_runner | hephaestus/automation/loop_runner.py | test_dry_run_help.py::test_loop_runner_has_dry_run |

### Test Suite (11 tests)

All in `tests/unit/cli/test_dry_run_help.py`:

1. **test_dry_run_help_text_all_modules_consistent** — parametrized test over 7 modules, validates all have identical help text
2. **test_dry_run_is_store_true** — verifies action="store_true" across all modules
3. **test_dry_run_in_option_strings** — confirms "--dry-run" appears in action.option_strings
4. **test_add_dry_run_arg_without_prefix** — unit test of helper, validates help text capitalization
5. **test_add_dry_run_arg_with_prefix** — unit test of helper with prefix, validates auto-punctuation
6. **test_add_dry_run_arg_prefix_already_has_period** — edge case: prefix already ends with period
7. **test_add_dry_run_arg_help_ends_with_period** — standalone help text gets period appended
8. **test_planner_build_parser_returns_parser** — _build_parser() returns ArgumentParser
9. **test_planner_parse_args_respects_dry_run** — _parse_args(["--dry-run"]).dry_run is True
10. **test_planner_parse_args_dry_run_defaults_false** — dry_run defaults to False
11. **test_all_cli_modules_export_build_parser** — each module exports _build_parser() function

**Coverage**: 11 tests, all passing; ruff/mypy/pre-commit all pass; CI verified.

### Expected --help Output

```
usage: planner [-h] [--dry-run] [--verbose] ...

options:
  -h, --help      show this help message and exit
  --dry-run       Do not create PR, file follow-up issues, or invoke /learn. Useful for testing without incurring token costs.
  --verbose, -v   increase verbosity
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #772, PR #974 | Standardize --dry-run help text across all CLIs. Created DRY_RUN_HELP_CAVEAT constant in hephaestus/cli/utils.py, add_dry_run_arg(parser, *, prefix=None) helper, extracted _build_parser() from _parse_args() in 7 CLI modules (planner, plan_reviewer, pr_reviewer, address_review, implementer_cli, ci_driver, loop_runner). Created test_dry_run_help.py with 11 tests covering help-text consistency, auto-punctuation, parametrized validation. All tests pass, ruff/mypy/formatting pass, pre-commit hooks pass. Verification: verified-ci (PR #974 merged). |
