---
name: planning-mismatched-issue-surfaces-review-risks
description: "Capture reviewer-checkable risks for implementation plans when an issue title, body, or acceptance text point at different surfaces. Use when: (1) the title and body appear to ask for different changes, (2) a DRY/refactor plan depends on private import aliases or inherited option fields, (3) a plan intentionally excludes adjacent fields or call sites, (4) the plan was written from grep evidence and has not been executed."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, review-risk, issue-scope, requirements-alignment, dry-refactor, pydantic-options, logging, import-alias, unverified-assumptions]
---

# Planning Mismatched Issue Surfaces — Review Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve a concise checklist for plans where an issue presents more than one plausible acceptance surface and the plan must make its assumptions reviewer-checkable. |
| **Outcome** | Planning discipline captured from an unexecuted implementation plan. The workflow is proposed, not validated by implementation or CI. |
| **Verification** | unverified — plan-stage learning only; no code was applied and no verification commands were observed passing. |

## When to Use

- The issue title and issue body appear to ask for different but related changes.
- A plan treats both surfaces as acceptance criteria and you need reviewer confirmation that this is not scope creep.
- A DRY/refactor plan preserves old private call sites through import aliases or compatibility shims.
- A typed options/model refactor uses inheritance or shared defaults and could alter public schema shape, field order, defaults, or CLI semantics.
- A plan excludes adjacent fields or nearby models and needs those exclusions explicitly ratified.
- The plan cites grep/file evidence but the proposed verification commands have not been run.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until implementation and CI confirm it.

### Quick Reference

```bash
# 1. Capture the potentially mismatched requirement surfaces before planning.
gh issue view <issue> --json title,body

# 2. Re-derive the implementation surface from stable symbols, not remembered line numbers.
rg -n "<distinctive helper|field|default|call-site>" src/ tests/

# 3. Check compatibility assumptions explicitly.
python - <<'PY'
import old_module
import new_module
assert old_module._private_helper is new_module._private_helper
PY

# 4. Compare public model/API shape before and after a Pydantic/dataclass DRY refactor.
python - <<'PY'
from package.models import Options
print(Options.model_json_schema())
print(Options.model_fields)
PY
```

### Detailed Steps

1. **Name each requirement surface separately.** If a title says "centralize logging setup" but the body says "deduplicate Options models," write both as acceptance surfaces. Do not silently collapse one into the other. Ask the reviewer to confirm whether implementing both is correct or over-scoped.

2. **Separate evidence from assumptions.** Put grep-derived file lists, symbols, and line locations under "evidence read." Put issue title/body, unexecuted test commands, and inferred module ownership under "assumptions to verify." A reviewer should not have to infer which claims are facts.

3. **Make helper-location choices reviewable.** If the proposed shared helper lives in a module whose name suggests narrower ownership, call that out. The reviewer should decide whether the location is an acceptable home or whether a new general module is cleaner.

4. **Preserve compatibility intentionally, then test identity.** When private call sites stay alive through `from new_home import _helper as _helper`, add an identity/import smoke test. Import aliases preserve object identity only if every old lookup still resolves through the old module attribute.

5. **Treat model inheritance as an API change until proven otherwise.** Pydantic/dataclass base-class extraction can change schema field order, inherited field exposure, defaults, validation, or generated docs. Add tests for exact public fields only when those details are intentionally part of the contract; otherwise prefer targeted behavioral assertions.

6. **Ratify exclusions.** If nearby fields such as `state_dir` or `verbose` are intentionally excluded from the shared base, state why and ask the reviewer to confirm against the current models and issue text.

7. **Label verification commands as guardrails unless run.** A plan can contain good commands without having executed them. Do not present proposed grep, schema, CLI, or unit-test commands as passing evidence until they actually run.

## Verified Workflow

_Not applicable._ This skill is `unverified`: it captures a planning/review-risk checklist from an unexecuted plan. The actionable workflow is under **Proposed Workflow** above; this placeholder exists for the marketplace validator's required section shape and makes no verification claim.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat only the issue body as scope | Planned only the DRY Options extraction even though the title named logging setup centralization | The implementer can satisfy the body and still miss a title-level acceptance surface a reviewer expects | Record title and body as separate surfaces and ask the reviewer to ratify whether both are in scope |
| Hide an inferred helper location inside implementation steps | Picked a co-located utility module as the shared helper home without naming the ownership tradeoff | A reviewer may reject the module as too narrow or semantically misleading only after implementation churn | Call helper-home choices out as reviewer assumptions before coding |
| Assume import aliases preserve all private compatibility | Kept old `_setup_logging` call sites via aliases and treated that as enough | Alias identity and lookup behavior are compatibility claims, not facts until imported and compared | Add smoke tests for import identity and keep old public/private import expectations explicit |
| Collapse shared option fields too aggressively | Treated similarly named options as one DRY surface | CLI semantics may require distinct public fields even when defaults match | Keep fields distinct when they represent separate operator knobs; share only defaults/helpers where behavior is identical |
| Over-constrain schema tests | Asserted exact field sets/order for every model after inheritance extraction | Exact schema tests catch regressions but can also freeze harmless internal refactors | Use exact schema tests only for intentional public contract details; otherwise assert defaults and exposed-field presence/absence |

## Results & Parameters

### Reviewer Checklist

```markdown
## Plan review risk checklist

- [ ] Requirement surfaces: title, body, and acceptance criteria are reconciled explicitly.
- [ ] Scope decision: reviewer agrees the plan is not under-scoped or over-scoped.
- [ ] Helper location: module ownership is intentional, not just convenient.
- [ ] Compatibility: old imports/private call sites have identity or behavior tests.
- [ ] Typed models: defaults, field names, schema exposure, and CLI semantics are preserved.
- [ ] Exclusions: nearby fields/models left out of the refactor are listed with rationale.
- [ ] Verification honesty: proposed commands are not described as passing evidence unless run.
```

### Risk Categories to Surface

- **Requirement alignment risk:** completing one surface while missing another plausible acceptance surface.
- **Module-boundary risk:** a helper home that is convenient but semantically too narrow.
- **Behavior/API risk:** inherited fields or aliases changing schema, validation, defaults, or import compatibility.
- **Test brittleness risk:** tests that prove the contract but freeze incidental ordering or implementation shape.
- **Verification risk:** grep-based dedupe proving literal removal without proving runtime equivalence.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1387 planning capture | The plan reconciled a title/body mismatch: title asked to centralize duplicated automation logging setup, while body asked for DRY extraction across Options Pydantic models. Unverified assumptions included using `hephaestus/automation/_review_utils.py` as the helper home, preserving private `_setup_logging` call sites through import aliases, keeping `PlannerOptions.parallel` distinct while sharing `DEFAULT_WORKER_COUNT`, excluding `state_dir`, and not adding `verbose` to models that do not expose it. File evidence came from planning-time grep over `_review_utils.py`, `planner.py`, `plan_reviewer.py`, `ci_driver.py`, `implementer_cli.py`, `audit_reviewer.py`, `models.py`, and related tests; no implementation or verification commands were run during learning capture. |
