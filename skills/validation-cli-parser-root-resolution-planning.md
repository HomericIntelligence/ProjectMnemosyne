---
name: validation-cli-parser-root-resolution-planning
description: "Planning review checklist for consolidating repo-root-aware validation CLI parser boilerplate in Hephaestus-like Python repos. Use when: (1) a plan extracts argparse/root-resolution helpers for validation/version CLIs, (2) reviewers need to separate real common parser behavior from intentional parser variants, (3) preserving --json, --version, --repo-root, argv injection, prog/epilog, exit codes, and special control flow matters."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, cli, argparse, validation, repo-root, parser-refactor, hephaestus]
---

# Validation CLI Parser/Root-Resolution Planning Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve review guidance from a ProjectHephaestus implementation plan for issue #1418: extract repeated validation CLI parser and repo-root resolution boilerplate into `hephaestus.cli.utils` helpers such as `create_validation_parser()` and `resolve_repo_root()`. |
| **Outcome** | Proposed planning guidance only. The underlying Hephaestus refactor, cited grep counts, file classifications, issue contents, and tests were not validated during the learn capture. |
| **Verification** | unverified - this skill captures plan-review guidance, not an executed workflow. |

## When to Use

- You are reviewing a plan to centralize `argparse` setup for validation, version, or consistency CLIs in a Python repo.
- The plan proposes a shared `create_validation_parser()` or `resolve_repo_root()` helper and claims many CLIs share identical `--repo-root` behavior.
- A grep count or exclusion list is used to scope a parser refactor, especially one based on `--repo-root` text.
- Some CLIs have special parser behavior, early returns, custom `SystemExit` handling, or non-standard `prog`/`epilog` output.
- You need a concise checklist for preserving `--json`, `--version`, `--repo-root`, argv injection, help text, exit codes, and public exports.

## Verified Workflow

> **Proposed Workflow - NOT verified.** This workflow has not been validated end-to-end. It is planning guidance captured from a ProjectHephaestus issue #1418 plan. Treat all file counts, line numbers, and issue/test references as hypotheses until re-checked against the current repository.

### Quick Reference

```bash
# Rebuild the scope from current source. Do not trust an old count.
rg -l -g '*.py' -- "--repo-root" hephaestus/validation hephaestus/version/consistency.py

# Separate parser text from actual repo-root resolution behavior.
rg -n "args\\.repo_root|get_repo_root|--repo-root|create_parser|parse_args" \
  hephaestus/validation hephaestus/version/consistency.py

# Re-check public exports and helper semantics before adding another helper.
rg -n "def create_parser|__all__|from hephaestus\\.cli import|add_argument\\(.*version" \
  hephaestus/cli tests/unit/cli

# Focused verification matrix for the implementation PR.
pixi run pytest tests/unit/cli tests/unit/validation tests/unit/version -q
pixi run pytest tests/integration -k "validation or version or console" -q
pixi run ruff check hephaestus tests
pixi run ruff format --check hephaestus tests
```

### Detailed Steps

1. **Rebuild the migration scope from current source.** A prior plan derived scope from `rg -l -g '*.py' -- "--repo-root" hephaestus/validation hephaestus/version/consistency.py` and claimed 13 files. Treat that count and any exclusion list as drift-prone until re-run. Review the resulting file list, not only the count.

2. **Classify by actual repo-root resolution, not by flag text.** A file containing `--repo-root` is not automatically a candidate for the shared helper. Confirm whether it resolves `args.repo_root`, calls `get_repo_root()`, or only accepts the flag for a different workflow.

3. **Review parser variants before excluding or homogenizing them.** The prior plan classified `coverage.py`, `audit.py`, `type_aliases.py`, and `mypy_per_file.py` as intentional variants because they do not resolve `args.repo_root`. That classification depends on current behavior. Open each file before preserving or removing the exception.

4. **Verify existing helper semantics before adding a new helper.** The plan assumed an existing `create_parser()` was unsuitable because it registers `-V`/`--version` and defaults `prog` to `hephaestus`. Confirm the actual helper signature, side effects, default `prog`, and version flag behavior before accepting a new `create_validation_parser()`.

5. **Preserve CLI contracts exactly.** The shared helper must not change console-script `prog`, help output, epilog text, duplicate or remove `--version`/`-V`, alter `--json`, or break `main(argv)` injection used by tests.

6. **Keep repo-root type expectations explicit.** If `resolve_repo_root()` returns a `Path`, verify every migrated call site already accepts a `Path` for `args.repo_root` and any downstream `get_repo_root()` interaction. Do not assume `str` and `Path` are interchangeable in tests or JSON output.

7. **Preserve special control flow before moving root detection.** `schema.py` was assumed to need its no-files early return before repo-root auto-detection. `tier_labels.py` was assumed to need preserved exception-to-exit-2 behavior. Review `markdown.py` and version consistency entry points for similar custom control flow before extracting common code.

8. **Verify public export expectations.** The plan assumed `tests/unit/cli/test_utils.py` asserts symbols in `cli.utils.__all__` are re-exported by `hephaestus.cli`. Open the test and the package `__init__` before adding public helpers or changing `__all__`.

9. **Build tests around behavior, not only helper unit coverage.** Add utility tests for the new helper, then run existing validation/version CLI tests that exercise argv injection, `--json`, `--version`, `--repo-root`, parser variants, exit codes, and console-script entry points.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust an old grep count | The plan scoped the refactor from a prior `rg` and claimed 13 matching files | Counts and file lists drift; worktrees and new CLIs can change the result | Re-run the exact grep in the implementation branch and review the file list before deciding scope |
| Treat all `--repo-root` parsers as identical | Proposed migration based on flag presence alone | Some CLIs may register the flag but intentionally avoid `args.repo_root` resolution or have custom parser behavior | Tie migration to actual repo-root resolution usage, not text matches |
| Assume the existing parser helper is unsuitable | The plan said existing `create_parser()` adds `-V`/`--version` and defaults `prog` to `hephaestus` | This was not verified during learn capture; helper semantics can change | Open the helper and tests before introducing `create_validation_parser()` |
| Move root auto-detection ahead of special branches | A shared resolver can be called before current early returns or custom error handling | `schema.py`, `tier_labels.py`, `markdown.py`, and version consistency entry points may rely on current ordering and exit codes | Preserve early returns, custom exceptions, and exit-code mapping before extracting common code |
| Validate only the new helper | A narrow helper test could pass while console-script behavior drifts | Users observe help text, `prog`, `--json`, `--version`, argv injection, and exit codes | Run focused CLI utility, validation, version, integration entry-point, and ruff checks |

## Results & Parameters

### Unverified assumptions to clear before implementation

- GitHub issue #1418 contents and acceptance criteria were relied on by the plan but not verified during this learn capture.
- Current grep results and line numbers in `hephaestus/validation/*`, `hephaestus/version/consistency.py`, and `tests/unit/cli/test_utils.py` were not verified during this learn capture.
- Existing CLI tests named in the verification matrix and their behavior around argv injection and exit codes were not verified during this learn capture.
- The stated prior learning about a dry refactoring workflow was not verified during this learn capture.

### Reviewer checklist

- Confirm the exact current file list for `--repo-root`; do not accept the stale "13 files" count without re-running it.
- Open every proposed parser variant exclusion and decide based on behavior, not filename.
- Confirm whether existing `create_parser()` can be extended or configured before adding another helper.
- Check for duplicate version flags and changed `prog`/help/epilog output.
- Confirm `Path` return values are accepted at every migrated call site.
- Preserve `schema.py` no-files early return before repo-root auto-detection.
- Preserve `tier_labels.py` exception-to-exit-2 behavior.
- Treat `markdown.py` and version consistency CLIs as special until their control flow is read.
- Verify `cli.utils.__all__` and `hephaestus.cli` re-export expectations before changing public API.
- Require tests that exercise `--json`, `--version`, `--repo-root`, argv injection, exit codes, parser variants, and console entry points.

### Verification matrix for the implementation PR

Run the repo's focused tests for the touched areas, then lint for unused imports and behavior drift:

```bash
pixi run pytest tests/unit/cli tests/unit/validation tests/unit/version -q
pixi run pytest tests/integration -k "validation or version or console" -q
pixi run ruff check hephaestus tests
pixi run ruff format --check hephaestus tests
```

The skill itself is `unverified`: only ProjectMnemosyne skill format validation should be claimed unless the Hephaestus refactor is actually implemented and tested.
