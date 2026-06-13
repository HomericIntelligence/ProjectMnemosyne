---
name: architecture-ocp-dip-abc-protocol-planning-risks
description: "Planning assumptions and risks when adding Protocol/ABC interfaces (OCP/DIP refactoring) to an existing codebase with no existing abstractions. Use when: (1) planning to introduce typing.Protocol or abc.ABC to an automation pipeline, (2) adding abstract methods to existing base classes, (3) reviewing an OCP/DIP refactoring plan before implementation."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: ["ocp", "dip", "protocol", "abc", "abstractmethod", "solid", "refactoring", "planning"]
---

# OCP/DIP ABC/Protocol Refactoring — Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Document planning assumptions and risks when introducing typing.Protocol and abc.ABC to an existing codebase (ProjectHephaestus issue #1193) |
| **Outcome** | Unverified planning artifact — implementation not yet attempted |
| **Verification** | unverified |

## When to Use

- Before implementing an OCP/DIP refactoring plan that adds Protocol or ABC definitions
- When reviewing a plan that assumes existing method names, inheritance hierarchies, or entry-points that were inferred from grep output rather than direct file inspection
- When introducing abstract methods to base classes that already have concrete subclasses
- Before adding `@abstractmethod` to any existing base class in a pipeline with multiple concrete implementations
- Before exporting new protocol/interface types from a package's `__init__.py` that has automation-boundary tests

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Verify entry-point method names before adding @abstractmethod
grep -n "def run\|def execute\|def __call__" hephaestus/automation/phase_*.py

# Verify reviewer inheritance before adding abstract methods to BaseReviewer
grep -n "class.*Reviewer" hephaestus/automation/pr_reviewer.py hephaestus/automation/address_review.py hephaestus/automation/plan_reviewer.py hephaestus/automation/audit_reviewer.py 2>/dev/null

# Verify DatasetDownloader subclass method signatures before adding download_dataset abstract
grep -n "def download_" hephaestus/datasets/*.py

# Inspect __init__.py before adding exports to avoid automation-boundary violations
cat hephaestus/automation/__init__.py
grep -r "from hephaestus.automation" tests/unit/test_automation_boundary.py
```

### Detailed Steps

1. **Verify every assumed method name before adding `@abstractmethod`**

   Do NOT assume entry-point method names from grep summaries. Read each subclass file directly to confirm the method exists with the exact name.

2. **Verify inheritance hierarchy for all concrete subclasses**

   If a plan says "AuditReviewer and PlanReviewer are standalone," confirm this by reading their class definitions. If they DO inherit the ABC base class, adding an abstract method will break them at instantiation if they use a different method name.

3. **Treat any new abstract method as a new API, not a rename**

   When a plan proposes adding `download_dataset()` to a DatasetDownloader ABC, this is a new method — each subclass needs a concrete implementation added (not just a rename of existing methods).

4. **Audit `__init__.py` before adding protocol exports**

   Read the target `__init__.py` to check what `__all__` currently contains. For `hephaestus/automation/__init__.py`, also run the automation-boundary test to verify exporting from it does not expose the automation layer to the base import surface.

5. **Run automation-boundary tests explicitly after any `__init__.py` change**

   ```bash
   pixi run pytest tests/unit/test_automation_boundary.py tests/unit/test_import_surface.py -v
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Infer entry-point from grep | Grep output showed `run()` in pipeline output but not all phase files were read directly | StageMixin plan assumed all five phase subclasses have `run()` — unverified for FollowUpPhase and others | Always open each file directly; grep shows definitions but misses inheritance or aliasing |
| Assume reviewer inheritance from class name | "Reviewer" suffix was treated as evidence of BaseReviewer inheritance | AuditReviewer and PlanReviewer may be standalone; if they DO inherit BaseReviewer with a different method name, `@abstractmethod review_issues` would break them | Read each class definition's base class list explicitly |
| Plan `download_dataset` as a rename | DatasetDownloader subclasses each define `download_<name>` — plan treated `download_dataset` as a thin wrapper | No such method exists; adding it abstract requires adding a concrete implementation to every subclass, potentially with signature mismatches | Never propose an abstract method that doesn't already exist in at least one subclass without explicitly flagging it as a new API addition |
| Export from automation __init__ without reading it | Plan added protocol exports to `hephaestus/automation/__init__.py` without checking current `__all__` or automation-boundary constraints | Automation-boundary tests (`test_automation_boundary.py`, `test_import_surface.py`) enforce that the library layer cannot import from `hephaestus.automation`; new exports might be safe within automation but could silently break the boundary | Always read `__init__.py` and run boundary tests before modifying exports |

## Results & Parameters

### Five High-Risk Assumptions to Verify Before Implementing

1. **StageMixin entry-point**: All five `StageMixin` subclasses (PlanPhase, ImplementPhase, ReviewPhase, PRCreatePhase, FollowUpPhase) were assumed to have a `run()` method. Verify with:
   ```bash
   grep -n "def run\b" hephaestus/automation/phase_plan.py hephaestus/automation/phase_implement.py hephaestus/automation/phase_review.py hephaestus/automation/phase_pr_create.py hephaestus/automation/phase_follow_up.py 2>/dev/null
   ```

2. **Reviewer inheritance**: AuditReviewer and PlanReviewer were noted as "standalone" (not inheriting BaseReviewer). If they do NOT inherit, the ABC constraint is irrelevant. If they DO inherit with a different method name, the abstract method breaks them. Verify with:
   ```bash
   grep -n "^class.*Reviewer" hephaestus/automation/audit_reviewer.py hephaestus/automation/plan_reviewer.py 2>/dev/null
   ```

3. **DatasetDownloader `download_dataset`**: No unified `download_dataset()` method exists across subclasses — this is a new API addition, not a rename. Each subclass must have a concrete `download_dataset()` added. Verify subclass methods with:
   ```bash
   grep -n "def download_" hephaestus/datasets/*.py
   ```

4. **`automation/__init__.py` exports**: Read the file before adding exports and confirm current `__all__` and whether it is safe to add protocol types to the public surface.

5. **Automation boundary**: Any `_interfaces.py` placed in `hephaestus/automation/` is internal to the automation layer. External library code cannot import it without violating the boundary. Protocols intended for cross-layer use should be placed in the library layer (e.g., `hephaestus/utils/` or a dedicated `hephaestus/interfaces/` module).

### General Pattern

When proposing OCP/DIP abstractions for an existing pipeline:
- The plan is only as reliable as its file-level verification
- Grep-based inference of method names is a starting hypothesis, not a guarantee
- Abstract method additions to existing base classes are high-risk — each concrete subclass must already implement the method OR the plan explicitly budgets for adding it
- Automation-boundary tests are easy to accidentally violate when adding new exports

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1193 OCP/DIP refactoring plan | Planning artifact only — implementation not attempted |
