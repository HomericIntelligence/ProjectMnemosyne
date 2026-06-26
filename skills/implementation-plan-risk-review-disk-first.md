---
name: implementation-plan-risk-review-disk-first
description: "Use when reviewing or writing implementation plans that refactor stale issue claims against current repository state and need explicit uncertainty/risk capture. Focus on disk-first premise checks, unverified external sources, and reviewer risks before implementation starts."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - implementation-plan
  - stale-issue
  - disk-first
  - refactoring
  - logging
  - c901
  - reviewer-risks
  - assumptions
  - ast
---

# Implementation Plan Risk Review - Disk-First Refactors

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture how to review or write an implementation plan when a stale issue body proposes refactors but current disk state, AST measurements, and source files are the real planning authority. |
| **Outcome** | Planning artifact only. The plan for ProjectHephaestus issue #1404 used local file and AST observations to scope centralized logging and C901 refactors, but the implementation was not executed and the proposed tests were not run. |
| **Verification** | unverified - plan was not implemented end-to-end, CI was not run, and remote issue comments were not directly verified during capture. |

## When to Use

- A GitHub issue describes current code structure, but the repository may have drifted since the issue was written.
- A plan proposes refactoring production call sites, centralized logging setup, CLI parser behavior, or high-complexity functions based on current files.
- The plan relies on local measurements such as `rg`, AST parsing, line numbers, or linter spans, and a reviewer needs to know which facts were actually verified.
- The plan has behavior-preservation assumptions that can only be proven by tests or by running affected CLIs.
- You need to separate "the disk says this today" from "the issue body or remote comments may say something else."

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a proposed review checklist until an implementation PR and CI confirm it.

### Proposed Workflow

#### Quick Reference

```bash
# Prefer current disk and structured measurements over stale issue prose.
rg -n "logging\\.basicConfig\\(" hephaestus/

# Use AST or the tool's own parser when the invariant is semantic.
python - <<'PY'
import ast
from pathlib import Path

for path in Path("hephaestus").rglob("*.py"):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "basicConfig"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logging"
            ):
                print(f"{path}:{node.lineno}: logging.basicConfig")
PY

# Re-measure complexity instead of trusting issue counts or stale line numbers.
pixi run ruff check hephaestus/ --select C901 --ignore-noqa
```

#### Detailed Steps

1. **Treat disk state as authoritative for scoping.** Start by reading and measuring the current checkout. If an issue claims "subcommands" or names old files, verify the current production callers, current function names, and current linter spans before deciding scope.

2. **Use structured checks when the invariant is semantic.** For static guards such as "no production `logging.basicConfig` calls remain," prefer an AST-based test over grep alone. A grep can miss aliases, comments, multiline calls, or fixture-only exceptions. The guard should scan production `hephaestus/` code and avoid forbidding legitimate test fixtures.

3. **Separate verified observations from unverified externals.** A plan may cite local files and line numbers from the current checkout while not directly verifying the remote issue body, remote comments, or the proposed tests. State that distinction in the plan so reviewers do not mistake local scoping evidence for full issue validation.

4. **Document behavior-parity assumptions explicitly.** Centralizing logging is risky even when call-site replacement looks mechanical. `setup_logging` must preserve level, format, datefmt, stdout/stderr stream behavior, and file-handler behavior. In particular, any CLI that writes a run log needs a regression test proving it still writes the same file and does not duplicate or drop handlers.

5. **Turn helper-extraction plans into parser and exit-code review checklists.** Reducing C901 by extracting helpers from CLI modules can silently change behavior. Review parser semantics, JSON emission paths, dry-run behavior, no-swarm/no-agent behavior, PR check fallback behavior, push-all/dry-run behavior, and exit codes.

6. **Make drift checks precise without overfitting.** A static check for stale `# noqa: C901` suppressions should catch only the suppressions intended for removal or rationale, not every future complexity exception in the repository. Prefer tool-backed checks such as Ruff where possible; if using text checks, scope them to specific files and explain why.

7. **Require reviewers to re-run the proof commands after implementation.** This skill captures planning discipline, not proof that the refactor works. The implementation PR still needs unit tests, CLI behavior checks, linter checks, and any file-output assertions promised by the plan.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust stale issue prose over the checkout | Used issue-body claims about current subcommands or call counts as the refactor scope | Issue bodies drift; the current checkout may have different files, callers, and linter spans | Scope refactors from current disk state using `rg`, AST parsing, and tool output before writing the plan |
| Treat centralized logging as mechanical replacement | Planned to replace `logging.basicConfig` calls with a shared helper without proving stream, format, datefmt, and file-handler parity | Logging behavior is user-visible and operational; handler clearing or reconfiguration can duplicate logs, drop logs, or move output between stderr/stdout | List every behavior-parity assumption and require focused regression tests, especially for run-log file behavior |
| Use grep-only anti-drift checks | Proposed preventing future production `logging.basicConfig` calls with text matching alone | Grep-only checks can overmatch tests/comments and under-detect semantic call forms | Use AST-based checks over production code, with deliberate fixture exclusions |
| Extract C901 helpers by shape alone | Planned helper extraction from complex CLI functions based on local spans | CLI functions often encode parser behavior, JSON output, dry-run behavior, and exit-code contracts that can break without obvious type or lint failures | Review behavior surfaces, not just complexity scores |
| Cite local file line numbers as durable truth | Recorded paths and line numbers from one checkout as if they would remain valid through implementation | Line numbers drift after edits and across branches | Treat line numbers as planning coordinates only; re-anchor by function names and tests during implementation |

## Results & Parameters

### ProjectHephaestus issue #1404 planning capture

This skill was created from a plan for ProjectHephaestus issue #1404. The plan was not executed. Its useful reusable pattern is disk-first risk capture, not a verified implementation recipe.

Local observations the plan relied on:

- `rg` and AST measurements found 9 production `logging.basicConfig` callers rather than trusting stale issue-body claims.
- Current C901 spans were read from on-disk code in `hephaestus/github/tidy.py` and `hephaestus/github/pr_merge.py`.
- The plan cited current checkout paths including `hephaestus/logging/utils.py`, `hephaestus/logging/__init__.py`, `hephaestus/automation/loop_runner.py`, `hephaestus/github/tidy.py`, `hephaestus/github/pr_merge.py`, and affected automation modules.
- The remote GitHub issue #1404 body and remote comments were not directly verified during this capture.
- The proposed implementation tests and CI were not run.

Highest-uncertainty assumptions reviewers should check:

- `setup_logging` preserves plain-text level, format, datefmt, stdout/stderr behavior, handler clearing/reconfiguration semantics, and file-handler behavior.
- `setup_logging` datefmt affects only plain-text formatting, not JSON formatter output.
- Importing `setup_logging` from affected modules does not introduce circular imports.
- Replacing local `basicConfig` calls does not change stderr/stdout stream expectations.
- Any static anti-drift test scans production `hephaestus/` code and does not ban legitimate test fixtures.
- Any static check for stale `# noqa: C901` suppressions catches only the intended stale suppressions and does not overfit to incidental text.

Reviewer focus for helper extraction in `tidy` and `pr_merge`:

- Parser semantics remain identical.
- JSON emission paths and non-JSON paths remain identical.
- Dry-run and no-swarm behavior remain identical.
- PR check fallback behavior remains identical.
- `push_all` plus dry-run behavior remains identical.
- Exit codes remain identical across success, skip, and failure paths.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1404 implementation plan review capture | unverified; local planning observations only, implementation/tests/CI not run, remote issue body/comments not verified in this capture |
