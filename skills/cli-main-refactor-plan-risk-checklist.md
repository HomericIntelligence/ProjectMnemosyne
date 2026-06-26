---
name: cli-main-refactor-plan-risk-checklist
description: "Planning checklist for behavior-preserving refactors of over-complex Python CLI main() functions. Use when: (1) removing C901 suppressions by extracting workflow or handler helpers, (2) an issue suggests a stale subcommand model but the live CLI is flag-driven, (3) JSON/error/dry-run paths must remain byte-for-byte compatible, (4) helper complexity targets were estimated in a plan but not yet proven by Ruff or tests."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - cli
  - argparse
  - refactoring
  - c901
  - planning
  - reviewer-risks
  - json-output
  - dry-run
  - issue-premise
  - behavior-preserving
---

# CLI main() Refactor Plan Risk Checklist

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture reviewer risks for plans that decompose over-complex Python CLI `main()` functions into small parser, workflow, and handler helpers while preserving existing flag-based behavior. |
| **Outcome** | Planning-only learning. The source plan targeted removal of `# noqa: C901` from two CLI entrypoints by extracting helpers, but the implementation and CI verification had not run yet. |
| **Verification** | unverified - no code was changed, no Ruff output was produced after extraction, and no tests or CI ran for the planned refactor. |

This skill is about the planning and review surface for a CLI refactor, not the mechanics of
writing every helper. It is most useful when the implementation goal is "reduce complexity without
changing the command contract."

## When to Use

- A Python CLI `main()` function is too complex and the plan proposes extracting parser, workflow,
  and handler helpers to remove `# noqa: C901`.
- The issue body suggests adding or changing subcommands, but the live CLI is currently
  flag-driven and no `args.command`, `subparsers`, or `add_parser` dispatch exists.
- The CLI has output-mode contracts such as `--json`, `--dry-run`, `--no-swarm`, `--push-all`, or
  error paths where small ordering changes can become behavior regressions.
- The plan cites helper LOC or complexity targets before actually running Ruff with
  `--ignore-noqa`.
- A reviewer needs to separate facts verified from disk from assumptions inferred from a plan.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a planning checklist
> until implementation, Ruff, focused tests, and CI confirm the behavior.

### Proposed Workflow

### Quick Reference

```bash
# 1. Verify the live CLI shape before accepting the issue's proposed architecture.
rg -n "args\\.command|subparsers|add_parser" path/to/cli_a.py path/to/cli_b.py
rg -n "add_argument|--json|--dry-run|--no-swarm|--push-all" path/to/cli_a.py path/to/cli_b.py

# 2. Measure complexity in a way that ignores existing suppressions.
pixi run ruff check --select C901 --ignore-noqa path/to/cli_a.py path/to/cli_b.py

# 3. Confirm the suppression is actually gone, not hidden in a moved line.
rg -n "noqa: C901" path/to/cli_a.py path/to/cli_b.py

# 4. Keep the entrypoint thin and delegate behavior to helpers.
python3 - <<'PY'
import ast

targets = {
    "path/to/cli_a.py": {"main": 10, "_run_workflow": 35},
    "path/to/cli_b.py": {"main": 10, "_process_item": 30},
}
for path, limits in targets.items():
    tree = ast.parse(open(path).read())
    seen = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in limits:
            seen[node.name] = node.end_lineno - node.lineno + 1
    missing = set(limits) - set(seen)
    assert not missing, f"{path} missing {sorted(missing)}"
    for name, limit in limits.items():
        assert seen[name] <= limit, f"{path}:{name} is {seen[name]}L > {limit}L"
PY

# 5. Run focused behavior tests for the risky modes, not just structure checks.
pixi run pytest tests/unit/path/test_cli_a.py::TestMain tests/unit/path/test_cli_b.py::TestMain
pixi run ruff check path/to/cli_a.py path/to/cli_b.py tests/unit/path/test_cli_a.py tests/unit/path/test_cli_b.py
pixi run ruff format --check path/to/cli_a.py path/to/cli_b.py tests/unit/path/test_cli_a.py tests/unit/path/test_cli_b.py
```

### Detailed Steps

1. **Verify the issue premise against the live parser before choosing the refactor shape.**
   If the issue body talks about subcommand dispatch, grep for actual subparser usage. When the
   current CLI is flag-driven, a behavior-preserving refactor extracts workflow and handler helpers;
   it does not invent a new subcommand layer to satisfy stale issue wording.

2. **Separate measured facts from estimated helper boundaries.** AST line counts and current file
   locations are useful planning facts, but helper cyclomatic complexity after extraction is still
   an estimate until Ruff runs on the changed code with `--ignore-noqa`.

3. **Keep `main()` as parser/throttle/logging glue only.** The thin entrypoint should parse args,
   configure shared CLI state, and call one workflow helper. Any branching over domain outcomes
   belongs in named helpers that can be tested directly.

4. **Preserve output and exit semantics as the primary acceptance criterion.** For JSON CLIs, assert
   payload status, key names, and exit codes. For dry-run paths, assert no side-effecting helper is
   called. For "skip" flags, assert both the log/JSON result and nonzero/zero exit behavior.

5. **Add tests for continuation semantics explicitly.** If the current loop logs an exception for
   one item and continues to the next, encode that in a test. Otherwise, extraction can accidentally
   turn a per-item failure into a workflow failure or mask a final failure as success.

6. **Verify with the checks that can disprove the plan.** A normal Ruff run can be fooled by an
   existing `# noqa`. Use `--ignore-noqa` for C901, grep for remaining suppressions, and run the
   focused CLI tests that cover the output modes named in the plan.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue's stale subcommand model | Planned around subcommand dispatch because the issue body suggested it | Disk search showed no `args.command`, `subparsers`, or `add_parser` use in the target CLIs; changing to subcommands would alter the command contract | Verify parser shape from the live code before planning; flag-driven CLIs should be decomposed into helpers without changing flags |
| Treat helper complexity targets as proven | Set LOC and CC goals for extracted helpers during planning | The plan measured current LOC with AST, but post-refactor CC was not run because implementation had not happened | Mark helper CC targets as estimates and require `ruff check --select C901 --ignore-noqa` after extraction |
| Assume parser extraction preserves JSON/error behavior | Moved inline parser construction into `_build_arg_parser()` and relied on existing main tests | Parser extraction is usually low risk, but JSON/error paths can depend on ordering of throttle setup, environment validation, and early returns | Keep focused tests for `--json` failures, no-work paths, and dry-run paths; do not rely only on help-text or parser tests |
| Treat per-item merge errors as obviously nonfatal | Planned to catch merge exceptions inside a per-item helper and keep processing | That continuation behavior was an assumption until tested; catching too broadly can also hide final workflow failure semantics | Add a multi-item test proving item 2 still runs after item 1 fails, and separately decide what final exit code should mean |
| Rely on normal Ruff after removing a suppression | Planned to remove `# noqa: C901` and run standard lint | A normal Ruff invocation can be hidden by surviving `noqa` comments, and a grep for one exact format can miss variants | Use both `rg "noqa: C901"` and `ruff check --select C901 --ignore-noqa` on the target files |

## Results & Parameters

### Reviewer Focus Checklist

```text
CLI behavior preservation
- Does the refactor preserve the current flag-based interface instead of adding subcommands?
- Are all existing JSON payload keys, statuses, and exit codes unchanged?
- Do dry-run and skip flags avoid side effects in the same places as before?
- Are per-item failures caught at the same boundary as before?

Complexity verification
- Did C901 run with --ignore-noqa after extraction?
- Are all target-file # noqa: C901 suppressions gone?
- Are helper LOC/complexity targets measured after implementation, not just estimated in the plan?

Premise honesty
- Which facts came from live rg/AST/file reads?
- Which claims depend on unverified issue text, live GitHub state, CI, or post-refactor test output?
```

### Source Planning Pattern

The source plan targeted two Python CLI entrypoints with over-complex `main()` functions. It made
these useful moves:

- Measured current `main()` locations and lengths from disk before planning.
- Rejected a stale subcommand-dispatch premise after searching for live parser dispatch.
- Planned thin `main()` functions plus extracted workflow and handler helpers.
- Named behavior tests for JSON/error paths, dry-run/skip behavior, legacy fallback, and per-item
  exception continuation.
- Added `ruff check --select C901 --ignore-noqa` and `rg "noqa: C901"` as acceptance gates.

The same plan also carried these unverified assumptions:

- Exact helper cyclomatic complexity would be acceptable after extraction.
- Existing test coverage was broad enough to protect every CLI flag and JSON/error path.
- Merge or action exceptions should be logged and processing should continue to later items.
- Helper names and APIs read during planning would still be the right integration points during
  implementation.
- No live GitHub issue body, CI output, or post-refactor Ruff/test result had been verified.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for a behavior-preserving CLI complexity refactor | Planning-only capture from issue #1403. No implementation, Ruff run, focused pytest run, or CI run had occurred when this skill was created. |
