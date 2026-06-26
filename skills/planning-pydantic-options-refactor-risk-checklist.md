---
name: planning-pydantic-options-refactor-risk-checklist
description: "Planning checklist for DRY refactors of Pydantic option models where constructor names, defaults, schema behavior, and CLI/API compatibility must not change. Use when: (1) a plan centralizes duplicated option defaults with BaseModel inheritance, (2) issue title/body disagree about the requested change, (3) a reviewer needs the unverified assumptions and compatibility risks called out before implementation."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pydantic
  - options-models
  - api-compatibility
  - issue-premise
  - reviewer-risk
  - constructor-compatibility
  - cli-defaults
  - unverified-assumptions
---

# Planning Pydantic Options Refactors: Reviewer Risk Checklist

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture durable planning discipline for a DRY refactor that centralizes duplicated Pydantic automation option defaults while preserving existing constructor fields, CLI behavior, schema expectations, and public import boundaries. |
| **Outcome** | A plan for ProjectHephaestus issue #1387 proposed `WorkerOptionsBase`, `_MaxWorkersOptionsBase`, `_VerboseMaxWorkersOptionsBase`, and `_DEFAULT_WORKER_COUNT` for six option models. The plan is useful, but it relies on several unverified assumptions a reviewer must check before implementation. |
| **Verification** | unverified - the source was an implementation plan and risk review only. The issue body, full consumer surface, Pydantic schema behavior, and CLI default sources were not independently verified in this capture. |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

Use this skill when a plan says "this refactor is only internal DRY cleanup" for Pydantic models that are
constructed by CLIs, imported by tests, serialized, or inspected through Pydantic metadata. Inheritance can
preserve field names while still changing field order, schema shape, introspection, or public module surface.

## When to Use

- Reviewing an implementation plan that introduces a Pydantic base class for existing option/config models.
- The issue title and issue body point at different work, and the plan chooses one as authoritative.
- A plan relies on local line references or a narrow `rg` check to prove an option field does not exist.
- The plan promises constructor/API compatibility but only names a few consumers.
- The refactor shares a default value across CLI-facing fields such as `parallel` and `max_workers`.
- A new base class is intentionally not exported at package root, but tests or callers may still import it from the module.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> The marketplace validator requires the literal `## Verified Workflow` section below. Read the steps as
> proposed review discipline, not as a completed verification run.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Confirm the real requested work before accepting a title/body mismatch.
gh issue view 1387 --repo HomericIntelligence/ProjectHephaestus \
  --json title,body --jq '{title, body}'

# Map current option fields and duplicated defaults.
rg -n "class .*Options|agent:|dry_run:|max_workers:|parallel:|verbose:" \
  hephaestus/automation/models.py

# Absence checks must cover the repo, not only one file.
rg -n "state_dir|--state-dir|state-dir" hephaestus tests docs pyproject.toml

# Build a consumer matrix for all six option models.
rg -n "PlannerOptions|ImplementerOptions|ReviewerOptions|PlanReviewerOptions|AddressReviewOptions|CIDriverOptions" \
  hephaestus tests

# Look for Pydantic introspection or serialization expectations that inheritance may perturb.
rg -n "model_fields|model_dump|model_json_schema|schema\\(|__fields__|dict\\(" hephaestus tests

# Confirm default sources before introducing a shared constant.
rg -n "add_max_workers_arg|--parallel|default=3|max_workers|parallel" hephaestus/automation tests

# Minimum local verification for the refactor.
pixi run pytest tests/unit/automation/test_models.py -q
pixi run pytest tests/unit/automation/test_package_imports.py -q
pixi run pytest tests/unit/automation -q
pixi run ruff check hephaestus/automation/models.py tests/unit/automation/test_models.py
pixi run mypy
pixi run pre-commit run --files hephaestus/automation/models.py tests/unit/automation/test_models.py
```

### Detailed Steps

1. **Resolve issue-title versus issue-body conflicts from the source of truth.** In the #1387 plan, the title allegedly referenced `_setup_logging`, while the plan treated the issue body as authoritative for an `Options` model refactor. That may be correct, but only after reading the live issue body. Quote the evidence in the plan and make the mismatch explicit so the implementer does not silently solve the wrong problem.

2. **Turn narrow grep facts into bounded claims.** `rg -n "state_dir:" hephaestus/automation/models.py` can prove only that no `state_dir:` annotation appears in that file. It does not prove there is no CLI flag, config key, docs reference, serialized field, or alternate spelling. If the conclusion is "do not add a new `state_dir` option," search repo-wide for `state_dir`, `state-dir`, and any relevant parser option before treating absence as evidence.

3. **Build the complete consumer matrix, not just named call sites.** The plan named `Planner.options.parallel` and `add_max_workers_arg()`, but compatibility depends on every constructor, attribute read, parser helper, test fixture, serialization call, and import. Search for each concrete option class, then classify each hit as construction, field access, schema/introspection, or import surface. The reviewer should challenge any "preserves API" claim that lacks this matrix.

4. **Treat Pydantic inheritance as observable until disproven.** Moving `agent`, `dry_run`, `max_workers`, and `verbose` into base classes may preserve constructor keyword names, but it can still affect `model_fields` order, generated JSON schema order, `repr`, dumps, docs generated from schema, or tests that inspect class annotations. Add tests for both behavior and metadata when callers might depend on those surfaces.

5. **Keep negative compatibility tests for fields that must not appear.** `PlannerOptions` should keep `parallel` and should not gain a stray `max_workers`; non-verbose workflows should not gain `verbose`; no model should gain `state_dir`. Compatibility tests should assert absence where the plan's promise is "do not add a field."

6. **Verify every default source before centralizing it.** `_DEFAULT_WORKER_COUNT = 3` is a good DRY move only if every CLI parser default and model default already agrees. Search parser helpers, CLI construction sites, and tests for hard-coded `3`, `default=3`, `--parallel`, and `max_workers`. If a CLI default diverges, the shared constant can accidentally change behavior or hide a deliberate distinction.

7. **Decide whether the new base class is part of the module API.** Leaving `WorkerOptionsBase` out of `hephaestus.automation.__init__` may preserve the package root export surface, but importing it from `hephaestus.automation.models` still creates a module-level surface. If tests import it directly, the plan should state that module-level import is acceptable and root export remains unchanged.

8. **Order reviewer focus by blast radius.** For this class of refactor, reviewer attention should go first to (a) issue premise/title mismatch, (b) constructor and serialized field compatibility, (c) Pydantic metadata/schema changes, (d) CLI default parity, and (e) public import/export expectations. Style and naming are secondary.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat the issue body as authoritative without showing the live body | The plan ignored a title/body mismatch because the body allegedly pointed to `Options` models | If the live issue body is not re-read, the implementer may solve the wrong issue, especially when the title names an unrelated `_setup_logging` target | Confirm the issue title and body with `gh issue view` and quote the evidence before choosing which premise drives the plan |
| Use a single-file grep to prove a field is absent | `rg -n "state_dir:" hephaestus/automation/models.py` had no matches | That proves only one annotation spelling is absent from one file; it does not rule out CLI flags, docs, configs, tests, serialized keys, or alternate spellings | Make absence claims repo-wide and spelling-aware before using them to exclude fields from a compatibility refactor |
| Name only obvious callers as API coverage | The plan cited `Planner.options.parallel` and `add_max_workers_arg()` but did not enumerate all constructors and serialized consumers | Pydantic models can be used through direct construction, parser glue, fixtures, dumps, schemas, or imports; a partial list misses compatibility regressions | Build a consumer matrix with `rg` for every concrete option class and classify each hit before claiming compatibility |
| Assume inheritance is behavior-only cleanup | Shared fields moved into base classes while constructor names remained stable | Pydantic inheritance can still change field order, schema/introspection output, annotations, or representation, even when keyword construction works | Add tests for field presence, absence, defaults, inherited custom values, and any metadata/schema surface the repo uses |
| Share worker default `3` without checking parser sources | Introduced `_DEFAULT_WORKER_COUNT = 3` for `parallel` and `max_workers` | A hidden CLI default or parser helper could intentionally diverge; a shared constant would mask or change that behavior | Search parser helpers and tests for every hard-coded default before centralizing a CLI-facing value |
| Treat non-export from package root as the only public-surface question | Left `WorkerOptionsBase` out of `hephaestus.automation.__init__` and tested root exports only | Module-level imports from `hephaestus.automation.models` may still become relied on, especially once tests import the base class | State the intended API boundary: root export unchanged, module import acceptable or explicitly internal |

## Results & Parameters

### Risk checklist for the ProjectHephaestus #1387 options-model plan

- **Issue premise risk:** Title allegedly points to `_setup_logging`; plan chooses the body and `Options` models. Reviewer must confirm the live issue body.
- **Narrow-source risk:** Plan relies on local line references and an `rg` absence check for `state_dir`; reviewer should widen the search to repo consumers, parser flags, docs, and serialization.
- **Compatibility risk:** Preserving field names does not automatically preserve Pydantic field order, schema, dump output, annotations, or import behavior.
- **Default-source risk:** `_DEFAULT_WORKER_COUNT = 3` aligns `parallel` and `max_workers` only if all CLI helpers and tests already share that default.
- **Surface-area risk:** `WorkerOptionsBase` is intentionally not exported from the package root, but importing it from `hephaestus.automation.models` in tests still creates a module-visible implementation detail.

### Minimum assertions to add to `tests/unit/automation/test_models.py`

```python
def test_all_workflow_options_share_agent_and_dry_run_defaults():
    ...

def test_worker_count_defaults_stay_in_sync_without_adding_max_workers_to_planner():
    ...

def test_verbose_remains_limited_to_existing_verbose_workflows():
    ...

def test_inherited_option_values_can_be_customized():
    ...

def test_no_new_state_dir_field_is_introduced():
    ...
```

### Verification level

This skill is `unverified`. The ProjectMnemosyne skill file itself should pass
`python3 scripts/validate_plugins.py`, but the ProjectHephaestus implementation plan was not
executed, the issue body was not fetched during this capture, and no ProjectHephaestus tests or CI
were observed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1387 implementation plan for centralizing duplicated automation option defaults in Pydantic base classes | unverified - plan-review learning only; reviewer should confirm live issue body, full consumer matrix, Pydantic metadata behavior, CLI defaults, and import/export surface before implementation |
