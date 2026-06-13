---
name: architecture-ocp-dip-verify-before-planning
description: "Verification checklist before planning Protocol/ABC additions in Python. Use when: (1) planning to add abstract base classes or Protocol interfaces, (2) planning to make an existing class abstract, (3) planning OCP/DIP refactors in ProjectHephaestus automation."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# OCP/DIP Planning: Verify Before You Plan

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Prevent false claims about method names, inheritance, and test instantiation when planning Protocol/ABC additions |
| **Outcome** | First plan NOGO'd with Grade F; second plan correct after reading actual source files |
| **Verification** | unverified — planning skill only |

## When to Use

- Before proposing `@abstractmethod` on any method name
- Before making any existing base class abstract (`class Foo(ABC)`)
- Before modifying any `__init__.py` to export new types
- When planning OCP/DIP improvements to hephaestus/automation/ or any module with a test suite

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Confirm the method exists on ALL concrete subclasses
grep -n "def <method_name>" hephaestus/automation/_*_phase.py hephaestus/automation/*_reviewer.py

# 2. Count direct instantiations of the target base class in tests
grep -c "TargetClass(" tests/unit/path/to/test_file.py

# 3. Read __init__.py before touching it
cat hephaestus/automation/__init__.py | head -100
```

### Detailed Steps

1. **For each method you plan to mark `@abstractmethod`**: grep the concrete subclass files directly (`grep -n "def <method>"`) and confirm zero-gap coverage before writing the plan.
2. **For each class you plan to make `ABC`**: grep the test suite for direct instantiation (`grep -c "ClassName("`) — if count > 0, the class cannot be made abstract without migrating those tests.
3. **Before editing `__init__.py`**: read it. If it uses `__getattr__` lazy loading, do NOT add eager imports. Keep new protocols in a private `_interfaces.py` module and document that callers must import directly.
4. **For reviewer/phase hierarchies**: check inheritance explicitly. In ProjectHephaestus, `AuditReviewer` and `PlanReviewer` are standalone (no `BaseReviewer` inheritance); only `PRReviewer` and `AddressReviewer` inherit `BaseReviewer`. A Protocol covers all four structurally; ABC covers only the two that inherit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Phase `@abstractmethod run()` | Added `@abstractmethod run()` to `StageMixin` claiming all five phase classes have `run()` | All five phase files have zero `def run` matches — entry points are domain-specific (`_generate`, `_finalize_pr`, etc.) | Always grep the concrete files before claiming a method exists |
| `DatasetDownloader(ABC)` | Made `DatasetDownloader` abstract with `@abstractmethod download_dataset()` | 15 direct `DatasetDownloader(...)` instantiations in test suite → 15 `TypeError` | Grep test files for direct instantiation before making any class abstract |
| `review_issues` as entry-point | Used `review_issues` as the abstract method name for reviewers | All four reviewers use `run()`, not `review_issues` | Read the actual method names; don't infer from domain concepts |
| Eager `__init__.py` export | Planned to add `ReviewerProtocol` to `_LAZY_EXPORTS` in `automation/__init__.py` | File uses `__getattr__` lazy loading — eager imports defeat the pattern | Read `__init__.py` before modifying; if lazy loading present, keep new types in `_interfaces.py` |

## Results & Parameters

**Correct final plan for #1193:**
- `hephaestus/automation/_interfaces.py` — new file with `ReviewerProtocol(Protocol)` with `def run(self) -> Any`
- `hephaestus/automation/_reviewer_base.py:61` — `class BaseReviewer(ABC)` + `@abstractmethod run()` at end of class
- `tests/unit/automation/test_interfaces.py` — six `issubclass(X, ReviewerProtocol)` conformance tests
- NO changes to `StageMixin`, `DatasetDownloader`, or `automation/__init__.py`

**Reviewer entry-points (verified 2026-06-13):**
- `PRReviewer.run` — `pr_reviewer.py:396`
- `AddressReviewer.run` — `address_review.py:350`
- `AuditReviewer.run` — `audit_reviewer.py:197`
- `PlanReviewer.run` — `plan_reviewer.py:99`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1193 — OCP/DIP abstraction audit | Plan R0 NOGO'd (Grade F); R1 accepted after source verification |
