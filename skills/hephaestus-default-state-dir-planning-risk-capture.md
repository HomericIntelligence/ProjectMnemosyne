---
name: hephaestus-default-state-dir-planning-risk-capture
description: "Planning checklist for centralizing ProjectHephaestus automation default state-dir construction around the repo-local build/.issue_implementer path. Use when: (1) a plan consolidates duplicated state_dir defaults, (2) reviewers must preserve explicit state_dir overrides, (3) tests add literal-string audits around build/.issue_implementer, (4) helper placement may introduce automation circular imports."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - projecthephaestus
  - automation
  - state-dir
  - path-centralization
  - planning-risk
  - build-issue-implementer
  - review-checklist
---

# ProjectHephaestus Default State Directory Planning Risk Capture

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve the planning review checklist for centralizing the ProjectHephaestus automation default state directory so `build/.issue_implementer` is defined once and all default constructors use a shared helper. |
| **Outcome** | Planning-only learning captured from a ProjectHephaestus issue #1394 implementation plan. The proposed implementation was not executed in this capture. |
| **Verification** | unverified - issue #1394 was not fetched in the capture turn, code/test behavior was inferred from planning context, and no implementation tests or CI were run. |

## When to Use

- A ProjectHephaestus automation plan centralizes duplicated default `state_dir` construction.
- Reviewers need to confirm explicit `state_dir` overrides still bypass any default helper.
- A change moves default path construction for planner, implementer, review, audit, or CI automation into one shared location.
- A plan proposes an AST or grep audit for remaining `build/.issue_implementer` literals.
- Helper placement in `hephaestus.automation` could create circular imports or change import-time side effects.
- Tests cover a new helper but may miss constructor, logging, or CLI call sites that actually consume the default directory.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Confirm the duplicated default path surface before editing.
rg -n 'build/\.issue_implementer|state_dir|DEFAULT_STATE_DIR|ensure_state_dir' \
  hephaestus/automation tests

# Confirm explicit overrides still have direct coverage.
rg -n 'state_dir=.*tmp_path|state_dir = tmp_path|--state-dir' tests hephaestus/automation

# After implementation, the only remaining production literal should be the
# canonical constant/helper location. A test literal may remain to pin the audit.
rg -n 'build/\.issue_implementer' hephaestus/automation tests
```

### Detailed Steps

1. **Verify the issue premise and current code before implementation.** Fetch/read the issue body and re-run the path search in the current tree. Do not rely on line numbers from an earlier plan; default constructors and CLI entry points drift quickly.
2. **Choose the helper home by dependency direction, not convenience.** `_review_utils.py` was proposed as the shared home for `DEFAULT_STATE_DIR` and `ensure_state_dir`, but that placement is an assumption. Confirm every intended consumer can import it without a cycle, especially planner and implementer entry points.
3. **Preserve override semantics first.** Any constructor or CLI path that receives an explicit `state_dir` must use that value unchanged. The helper should only run for omitted/default values.
4. **Preserve the on-disk layout exactly.** The default must remain repo-local `build/.issue_implementer`, not `.issue_implementer`, not a CWD-relative directory, and not a path rooted at the caller's temporary test directory unless an override requested that.
5. **Check directory creation timing.** If `AuditReviewer().__post_init__` or a similar constructor creates the default directory earlier than before, review tests and call sites for unwanted side effects. Earlier creation may be harmless, but it is not automatically behavior-preserving.
6. **Centralize all live defaults, including CLI extras.** Planner and implementer `main()` defaults, `planner_review_loop.py`, reviewer constructors, and any remaining automation default must route through the same helper if they still construct the default path.
7. **Make the literal audit precise.** An AST audit should allow the canonical constant and a literal-pin regression test only. It must not ban unrelated historical strings in documentation, comments, notes, or old test fixtures unless those are part of the runtime surface.
8. **Test behavior-bearing call sites.** Add direct helper tests, but also cover constructor/logging/CLI consumers so a wrong import path, eager mkdir, or override regression fails at the call site where users feel it.
9. **Run the repo's real gates after implementation.** The plan assumed commands such as `pixi run pytest`, `pixi run ruff`, `pixi run mypy`, and ProjectMnemosyne validation behavior. Confirm current task names and run the relevant gates before claiming the refactor is safe.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> This section is present for compatibility with `scripts/validate_plugins.py`, which currently requires `## Verified Workflow` for every flat skill. The actionable workflow for this unverified planning capture is the `## Proposed Workflow` section above.

### Quick Reference

```bash
python3 scripts/validate_plugins.py
```

### Detailed Steps

1. Treat this skill as a planning review checklist, not as an executed implementation recipe.
2. Before implementing issue #1394, verify every premise against the current ProjectHephaestus tree.
3. Promote this learning to verified-local or verified-ci only after the default-state-dir refactor is implemented and its tests pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating `_review_utils.py` as obviously canonical | The plan assumed `_review_utils.py` is the best shared home for `DEFAULT_STATE_DIR` and `ensure_state_dir`. | That may be correct, but it was not proven against all import directions and could introduce a circular import. | Verify dependency direction and import graph before choosing the helper module. |
| Assuming earlier directory creation is harmless | The plan treated `AuditReviewer()` default directory creation in `__post_init__` as likely safe. | Earlier `mkdir` timing can create observable side effects in constructors, tests, dry runs, or logging-only paths. | Add call-site tests around construction timing and explicit overrides, not just helper behavior. |
| Relying on duplicated literal removal alone | The plan focused on removing repeated `build/.issue_implementer` strings. | Removing literals can still change behavior if defaults become CWD-relative, skip `get_repo_root()`, or touch explicit overrides. | Assert exact path layout and override preservation, not just literal count. |
| Writing an over-broad AST audit | The plan proposed a guard against duplicated path literals. | A naive audit can fail on docs, comments, history, or the literal-pin test itself. | Scope the audit to runtime code and explicitly allow the canonical constant plus one regression-test literal. |
| Trusting inferred tests and command names | The plan referenced test names and `pixi` commands from context rather than re-reading every target. | Test names, CLI tasks, and constructor behavior may have drifted since the plan context was gathered. | Re-read the relevant files and command definitions before finalizing implementation or verification. |

## Results & Parameters

### Planning Inputs To Verify

| Item | Capture Status | Reviewer Action |
|------|----------------|-----------------|
| ProjectHephaestus issue #1394 body | Not fetched during this capture | Fetch/read the issue before implementation and reconcile the plan with the current issue text. |
| Current `rg` line numbers | May drift | Re-run the searches in the implementation branch. |
| Constructor behavior and tests | Inferred from plan context | Re-read `AuditReviewer`, planner, implementer, and review-loop constructors plus their tests. |
| `get_repo_root()` return type | Assumed Path-compatible | Verify the actual return type and all path-joining call sites. |
| CLI and validation commands | Assumed | Confirm current `pixi` tasks and run the relevant gates. |
| GitHub review semantics | Not re-queried | Treat PR/review behavior as external and time-sensitive if the implementation plan depends on it. |

### Review Focus

| Risk | Required Evidence |
|------|-------------------|
| Explicit override regression | Tests where `state_dir=tmp_path` or `--state-dir` remains untouched by the default helper. |
| Layout regression | Assertions that omitted defaults still resolve to `<repo_root>/build/.issue_implementer`. |
| Circular import | Import smoke tests or targeted unit tests for every consumer that imports the helper. |
| Eager side effects | Constructor tests that prove any earlier `mkdir` timing is intended and non-disruptive. |
| False-positive literal audit | Audit tests with allowed canonical constant, allowed pin literal, and rejected duplicate runtime literal. |
| Incomplete centralization | Search evidence showing planner, implementer, planner-review-loop, reviewer, and CLI defaults all share the helper. |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1394 planning capture | unverified - checklist extracted from a just-produced implementation plan; no implementation, tests, or CI were run in this capture. |
