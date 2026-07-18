---
name: pydantic-options-base-class-refactor-planning-risks
description: "Planning-risk checklist for Pydantic options/model base-class refactors. Use when: (1) consolidating duplicated Pydantic option defaults into shared base classes, (2) preserving constructor/API fields while changing inheritance, (3) reviewing plans that may accidentally add runtime-only fields to options models."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [pydantic, options, inheritance, base-class, refactoring, planning, constructor-compatibility, field-ordering]
---

# Pydantic Options Base-Class Refactor - Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture reviewer risks for planning-only refactors that move duplicated Pydantic option defaults into shared base classes while preserving public constructor/API behavior. |
| **Outcome** | Proposed reviewer workflow only; no implementation or end-to-end verification was performed. |
| **Verification** | unverified - planning artifact only; validate every assumption with structural tests and existing CLI/runtime tests before merging. |

## When to Use

- A plan extracts duplicated Pydantic `BaseModel` option defaults into shared base classes.
- Public constructor kwargs must remain accepted after moving fields to inherited classes.
- Field order, `model_fields`, generated signatures, JSON schema, CLI adapters, or automation tests might depend on declaration placement.
- A reviewer needs to separate configuration options from runtime worker state and reject new options fields that belong on runtime classes.
- The plan was produced from grep/source inspection rather than an implemented, executed refactor.

## Proposed Workflow

<!-- validator-required marker for current ProjectMnemosyne checker: ## Verified Workflow -->

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Enumerate all affected option models and shared/default fields.
rg -n "class .*Options|dry_run|max_workers|verbose|parallel" path/to/package tests

# 2. Confirm runtime-only state remains on worker/runtime classes, not options models.
rg -n "state_dir|runtime|worker" path/to/package tests

# 3. Add structural tests before or with the refactor.
python - <<'PY'
from package.automation.models import PlannerOptions

assert "dry_run" in PlannerOptions.model_fields
assert PlannerOptions(dry_run=True).dry_run is True
assert PlannerOptions.model_fields["parallel"].default == 3
PY

# 4. Run focused model, automation, CLI, lint, and type checks.
pytest tests/unit/automation/test_models.py tests/unit/automation -q
pytest tests/unit -k "cli or entrypoint or options" -q
ruff check .
mypy .
```

### Detailed Steps

1. **Inventory every option model and every duplicated default before introducing base classes.**
   List the affected Pydantic models and fields, then classify each field as public configuration,
   CLI-exposed configuration, inherited common configuration, or runtime-only state. Do this before
   writing class hierarchy changes so reviewers can tell which public constructors must remain stable.

2. **Prove inherited fields preserve public construction behavior.**
   Pydantic inheritance usually exposes inherited fields through `model_fields`, but a plan should not
   rely on memory or intuition. Add structural tests that instantiate every affected model with custom
   values for inherited defaults and assert the values survive construction.

3. **Check field ordering and schema/signature consumers explicitly.**
   Refactors that preserve field names can still change field order, generated signatures, schema order,
   help text order, or snapshots. Grep for `model_fields`, `model_json_schema`, `signature`, CLI option
   generation, and assertions over field names. If any consumer depends on order, pin the expected order
   in tests before changing declarations.

4. **Preserve specialized defaults exactly.**
   Do not move a common-looking field into a base class if one child model intentionally differs. Pin those
   defaults with tests. For example, if a planning model has a `parallel` default that differs from worker
   models, assert that exact default before and after the refactor.

5. **Reject runtime-only fields on options models.**
   If evidence shows a value belongs to runtime worker objects, status trackers, drivers, or worktree
   managers, do not add it to options just to make a base class feel complete. Runtime state in options
   changes the public constructor, CLI expectations, serialization surface, and test fixtures.

6. **Run both structural and behavior-level checks.**
   Model tests catch inherited defaults and constructor overrides. Existing automation and CLI tests catch
   call sites that implicitly relied on local declaration order, class-local annotations, or per-class
   defaults. Lint and type checks catch dead imports and type regressions introduced by the hierarchy move.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust Pydantic inheritance without structural tests | Planned to move common option fields into base classes and rely on inherited fields preserving constructor/API behavior | The plan was not implemented or executed; field inheritance, generated signatures, schema ordering, and custom constructor overrides were assumptions | Add structural tests for every affected model: inherited default present, custom override accepted, model field order/schema expectations explicit where relevant |
| Assume no caller depends on local declaration order or class-local annotations | Grep-style source review found consumers of `dry_run`, `max_workers`, and `verbose`, but did not run CLI/runtime paths | A CLI adapter, snapshot, help generator, or test fixture can depend on declaration order even when field names are unchanged | Search for order-sensitive Pydantic/CLI consumers and run existing automation plus CLI entry point tests |
| Add a runtime `state_dir` to Options for symmetry | Considered broadening options while extracting common defaults | Evidence showed state directories lived on runtime worker/driver classes, not options models; adding it would expand the public options constructor unnecessarily | Treat options models as public configuration only; keep runtime state on runtime classes unless a real call path proves it is user/config input |
| Treat a planning artifact as a verified workflow | Captured risks from source inspection and a proposed plan, not from executed implementation or CI | Without implementation, tests, lint, mypy, and CI, the plan can only identify risks and proposed checks | Mark verification as `unverified` and use a Proposed Workflow until the refactor is executed and confirmed |

## Results & Parameters

### Reviewer Checklist

```text
- [ ] All affected option models listed by name.
- [ ] Common fields classified as inherited configuration, specialized child defaults, or runtime-only state.
- [ ] Constructor override tests added for inherited `dry_run`, `max_workers`, `verbose`, or equivalent fields.
- [ ] Specialized defaults such as planner-only `parallel` are pinned exactly.
- [ ] No runtime-only field such as `state_dir` is added to options without call-path evidence.
- [ ] Grep covers model definitions, planners, implementers, reviewers, CI drivers, address-review paths, and tests.
- [ ] Existing model tests, automation tests, CLI entry point tests, ruff, and mypy are part of the implementation verification.
```

### Risk Signals

| Risk | Review Response |
|------|-----------------|
| Plan says "field names unchanged" but has no structural tests | Request tests for inherited defaults and constructor overrides |
| Plan changes class inheritance and also adds new option fields | Require evidence each new field is public configuration, not runtime state |
| Plan relies on grep only | Treat as unverified; require focused tests plus existing automation/CLI checks |
| One child model has a special default | Pin it in a targeted regression test before deduplication |
| The plan cites exact source files but no executed command output | Keep verification level `unverified` and do not call the workflow verified |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning-only capture for issue #1388: extract duplicated Pydantic automation Options defaults in `hephaestus/automation/models.py` into shared base classes | Source evidence came from grep-style references across automation models, planner, implementer, reviewer, CI driver, address review, PR reviewer, and model tests. No implementation or end-to-end verification was performed. |
