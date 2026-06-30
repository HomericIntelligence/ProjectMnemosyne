---
name: architecture-ocp-dip-verify-before-planning
description: "Verification checklist before planning Protocol/ABC additions in Python. Use when: (1) planning to add abstract base classes or Protocol interfaces, (2) planning to make an existing class abstract, (3) planning OCP/DIP refactors in ProjectHephaestus automation, (4) planning a CONSOLIDATION whose issue body ENUMERATES N offending classes/sites — the enumeration is as stale as a 'Evidence:' section: re-verify EACH enumerated item against the current tree (prior PRs may have already consolidated some onto a canonical helper, one may have NO persistence at all, another may already be consistent), grep each file for the actual IO pattern instead of trusting the class list, and search for whether the 'canonical helper to create' already exists before scoping a build, (5) scoping a Protocol to ONLY the classes it STRUCTURALLY satisfies — when two concrete stores have genuinely different method signatures (e.g. save(issue_number, record: dict) vs save(state: BaseModel)), write a minimal common-denominator Protocol scoped to the matching subset with a runtime issubclass conformance test, mirroring the repo's existing Protocol idiom, NOT a flat Protocol asserted to cover both."
category: architecture
date: 2026-06-30
version: "1.1.0"
user-invocable: false
verification: unverified
history: architecture-ocp-dip-verify-before-planning.history
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
- **When the issue body ENUMERATES N offending classes/sites** for a consolidation/Protocol
  extraction — the enumeration is as stale as a `Evidence:` section. Re-verify EACH enumerated item
  against the current tree before scoping.
- **Before "creating" the canonical helper the issue asks for** — search for it first; it often
  already exists and most consumers already use it.
- **When two concrete classes you want one Protocol to cover have different method signatures** —
  scope the Protocol to the structurally-matching subset, do not assert universal coverage.

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
5. **For each class the issue ENUMERATES as an offender**: grep that exact file for the real IO
   pattern (`grep -nE "read_text|write_secure|model_dump_json|json.loads|json.dumps" <file>`) before
   trusting the list. A class may have ALREADY been consolidated onto the canonical helper by a prior
   PR, may have NO on-disk persistence at all (the "writes `issue-{n}.json`" claim can be flatly
   false — it only queries GitHub), or may already be consistent. Treat the issue's class list as a
   hypothesis, not a fact.
6. **Before scoping a "build the canonical helper" task**: search for the helper first
   (`grep -rn "def save_state_file\|def load_state_file" hephaestus/`). If it already exists and most
   managers already use it, the real work shrinks from "build an abstraction over N classes" to
   "document the existing contract as a Protocol + converge the remaining outlier(s)."
7. **Before writing ONE Protocol over multiple stores**: read each `save`/`load` signature. If they
   genuinely differ — e.g. `save(issue_number, record: dict)` vs `save(state: BaseModel)` (single
   arg, keyed off `state.issue_number`) — do NOT write a flat Protocol claimed to cover both. Write a
   minimal common-denominator Protocol scoped to the matching subset (the `(issue_number, record)`
   stores) with a runtime `issubclass` conformance test, and mirror the repo's EXISTING Protocol
   idiom (`ReviewerProtocol` in the same `_interfaces.py`, `runtime_checkable`, imported directly to
   preserve the `__init__` lazy-export design) rather than inventing a parallel abstraction or adding
   eager `__init__` exports.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Phase `@abstractmethod run()` | Added `@abstractmethod run()` to `StageMixin` claiming all five phase classes have `run()` | All five phase files have zero `def run` matches — entry points are domain-specific (`_generate`, `_finalize_pr`, etc.) | Always grep the concrete files before claiming a method exists |
| `DatasetDownloader(ABC)` | Made `DatasetDownloader` abstract with `@abstractmethod download_dataset()` | 15 direct `DatasetDownloader(...)` instantiations in test suite → 15 `TypeError` | Grep test files for direct instantiation before making any class abstract |
| `review_issues` as entry-point | Used `review_issues` as the abstract method name for reviewers | All four reviewers use `run()`, not `review_issues` | Read the actual method names; don't infer from domain concepts |
| Eager `__init__.py` export | Planned to add `ReviewerProtocol` to `_LAZY_EXPORTS` in `automation/__init__.py` | File uses `__getattr__` lazy loading — eager imports defeat the pattern | Read `__init__.py` before modifying; if lazy loading present, keep new types in `_interfaces.py` |
| Trust the issue's "6 inconsistent state classes" enumeration (#1432) | Planned a StateStore abstraction over all 6 enumerated sites | Direct source grep: 3 (`ReviewState` in `_reviewer_base.py`, `ci_driver.py`, `address_review.py`) were already consolidated onto `load_state_file`/`save_state_file` by #597/#1178/#1193; `PlannerStateManager` has NO on-disk persistence (it only queries GitHub — the `issue-{n}.json` write claim was false); `ImplementationStateManager` was already consistent. Only `ArmingStateStore` was a genuine outlier | An issue body that ENUMERATES N offenders is as stale as a `Evidence:` section — grep each enumerated file for the actual IO pattern; do not trust the class list |
| "Create" a canonical state-store helper (#1432) | Scoped the plan to build `save_state_file`/`load_state_file` | The helpers already existed in `_review_utils` and most managers already used them | Search for the canonical helper BEFORE scoping a build — the work was actually "document the existing contract + converge the 1 outlier" |
| One flat `save(issue_number, record)` Protocol over both stores (#1432) | Asserted the Protocol covers `ArmingStateStore` AND `ImplementationStateManager` | Signatures differ: `ArmingStateStore.save(issue_number, record: dict)` vs `ImplementationStateManager.save(state: BaseModel)` (single arg, keyed off `state.issue_number`). A rigid `save(issue_number, record)` covers the first, not the second | Scope the Protocol to the structurally-matching subset with a runtime `issubclass` conformance test; mirror the existing `ReviewerProtocol` idiom, don't invent a parallel abstraction |

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

## What to Double-Check (unverified plan assumptions)

These are the UNVERIFIED branches of the #1432 StateStore plan. The plan was produced but NOT
executed — record them as "what the reviewer should verify on disk before implementing," not as
facts:

- **`tests/unit/automation/test_interfaces.py` existence is ASSUMED** (inferred from a skill mention,
  not verified). The plan branches on `ls` — confirm the file actually exists before appending to it
  vs creating it.
- **`runtime_checkable` Protocols check METHOD-NAME presence only, not signatures.** A passing
  `issubclass(ArmingStateStore, StateStore)` does NOT prove `save(issue_number, record)` matches the
  Protocol's signature. The real guard is the round-trip behavior test, not the structural
  `issubclass` test.
- **Can an `ArmingStateStore` record ever be a JSON non-dict** (a bare list)? `load_state_file`
  returns the raw payload, which a new `dict(record)` wrapper would choke on. The malformed-file path
  is covered, but a well-formed non-object payload is an untested edge.
- **Keep `import json` in `arming_state.py`** — it is still used by `save`'s `json.dumps`. Easy to
  over-remove during the import edit.
- **The plan was NOT executed**: no tests run, no CI. Verification level is `unverified`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1193 — OCP/DIP abstraction audit | Plan R0 NOGO'd (Grade F); R1 accepted after source verification |
| ProjectHephaestus | Issue #1432 — "8 state management classes, inconsistent persistence — extract StateStore Protocol" | Planning only (unverified, not executed). Issue enumerated 6 inconsistent sites; source verification showed 5/6 were already consolidated, persistence-free, or consistent — only `ArmingStateStore` was a genuine outlier. Scoped a minimal common-denominator Protocol over the `(issue_number, record)` stores, not a flat one over both signatures |
