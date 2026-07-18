---
name: architecture-ocp-dip-abc-protocol-planning-risks
description: "Plan and implement safe Python ABC/Protocol refactors by verifying real hierarchy and test constraints first, then combining abstract inheritance enforcement with structural Protocol coverage. Use when: (1) adding abc.ABC or typing.Protocol to an existing hierarchy, (2) adding an abstract method to a base class with concrete or test-only subclasses, (3) introducing a shared interface across mixed-inheritance classes, (4) protecting lazy package-import boundaries and contract tests during an OCP/DIP refactor."
category: architecture
date: 2026-07-17
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags: ["ocp", "dip", "protocol", "abc", "abstractmethod", "runtime-checkable", "contract-test", "planning", "refactoring"]
history: architecture-ocp-dip-abc-protocol-planning-risks.history
---

# Safe Python ABC/Protocol Refactoring

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Introduce ABC and Protocol contracts without inventing APIs, breaking subclasses, or weakening package boundaries |
| **Outcome** | One verified lifecycle covering planning risks, structural interface design, and contract-test regression prevention |
| **Verification** | verified-ci — ProjectHephaestus issue #1193 |
| **History** | [absorbed planning and implementation sources](./architecture-ocp-dip-abc-protocol-planning-risks.history) |

## When to Use

- Adding `abc.ABC`, `@abstractmethod`, or `typing.Protocol` to an existing Python hierarchy
- A proposed abstract method was inferred from a grep summary rather than direct source inspection
- Some classes need a common interface but do not share an inheritance base
- Existing contract tests contain stub, fake, dummy, or bogus subclasses
- A new interface may tempt an eager export from a lazily loaded package `__init__.py`

## Verified Workflow

### Quick Reference

```bash
# Establish facts before designing the interface.
grep -n "^class\|def run\|def execute\|def __call__" path/to/concrete_subclasses.py
grep -rn "class .*\(TargetBase\)\|TargetBase(" tests/
sed -n '1,180p' package/__init__.py

# Verify implementation and contract coverage synchronously.
pytest tests/path/to/contract_tests.py -q
pytest tests/path/to/interface_tests.py -q
mypy path/to/interfaces.py path/to/base.py
ruff check tests/path/to/interface_tests.py --select D103
```

### Phase 1 — Verify the proposed contract

1. Read every concrete subclass directly and record its actual entry-point name and signature. Grep is a discovery aid, not proof.
2. Map the inheritance graph, including classes with similar names that are standalone. Do not assume a `Reviewer`-like suffix implies a shared base.
3. Search production and test code for direct construction of the target base and for test-only subclasses. An abstract-method change is a public contract change for both.
4. Inspect the package export mechanism before adding interface imports. Preserve lazy loading and layer boundaries unless a public export is explicitly required.
5. Treat a proposed name absent from all concrete subclasses as a new API, not a rename; budget implementations and migrations for every affected class.

### Phase 2 — Choose the smallest enforcement mechanism

| Need | Mechanism |
|------|-----------|
| Enforce implementation for subclasses of one base | `ABC` plus `@abstractmethod` |
| Verify a behavioral shape across classes with mixed inheritance | `@runtime_checkable Protocol` |
| Cover both conditions | Use both: ABC for inheritors and Protocol for structural conformance |

Keep a protocol in a private interface module when package exports are lazy or importing it would violate a dependency boundary. Do not make an unrelated hierarchy abstract merely because it shares a domain term.

### Phase 3 — Implement and verify safely

1. Add the abstract method only after every intended concrete inheritor has a compatible implementation.
2. Give every test-only subclass a minimal implementation of the new abstract method so its test reaches the behavior it was meant to exercise.
3. Add Protocol conformance tests for each required class, including standalone classes that cannot be covered by the ABC.
4. Add required test-function docstrings and run linting before commit when the project enforces them.
5. Run affected contract and interface tests synchronously, then type-check and run the full affected test directory. Do not commit before checking background-task output.

### Worked Example — Mixed reviewer hierarchy

In ProjectHephaestus, `PRReviewer` and `AddressReviewer` inherit `BaseReviewer`, while
`AuditReviewer` and `PlanReviewer` are standalone. `BaseReviewer(ABC)` with an abstract `run()`
enforces the contract for the two inheritors; a runtime-checkable `ReviewerProtocol` gives all four
classes a common structural contract.

```python
@runtime_checkable
class ReviewerProtocol(Protocol):
    def run(self) -> Any: ...


class BaseReviewer(ABC):
    @abstractmethod
    def run(self) -> Any:
        """Execute the review pipeline."""
```

When an existing contract test defines `class BogusSubclass(BaseReviewer): pass`, add a minimal
`run()` stub. Otherwise ABC construction fails before the test can reach the error path it is
supposed to validate.

### Worked Example — Do not generalize a missing downloader method

If concrete downloader classes expose `download_<name>()` methods rather than a shared
`download_dataset()`, the latter is a new interface. Either design and implement it across every
concrete class or leave the hierarchy unchanged; an ABC declaration alone is not a refactor.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Infer entry points from grep | Treated a partial search result as proof that every phase exposed `run()` | Several classes used domain-specific entry points | Read every relevant class before naming an abstract contract |
| Make a base abstract without auditing test stubs | Added an abstract method while contract tests had no-method subclasses | Instantiation raised `TypeError` before tests reached their intended assertions | Audit production and test subclasses together |
| Rely on ABC for a mixed hierarchy | Expected a common base to enforce behavior on standalone classes | Non-inheriting classes are outside ABC enforcement | Pair an ABC with a structural Protocol when the family is mixed |
| Export an interface eagerly | Added imports to a lazy package initializer | It defeated lazy loading or crossed the automation boundary | Keep private interfaces private unless an audited public export is required |
| Verify asynchronously then commit | Started tests in the background and did not inspect their result | A contract regression was committed despite a failing test | Run the final affected suite synchronously and inspect its exit status |

## Results & Parameters

### Completion checklist

- Every method name and concrete signature was read directly.
- Every ABC subclass, including test doubles, implements the new abstract method.
- Protocol tests cover classes outside the ABC hierarchy.
- Lazy exports and import-layer boundaries remain intact.
- Contract tests, interface tests, type checks, and required lint checks pass.

### Expected verification

| Check | Expected result |
|-------|-----------------|
| Contract tests | Test doubles instantiate and reach their intended assertion paths |
| Protocol tests | Every selected concrete and standalone class conforms structurally |
| Type check | Missing abstract implementations are reported before CI |
| Lint | Newly added tests meet repository documentation/style rules |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1193 | ABC/Protocol refactor completed with contract tests, mypy, pre-commit, and CI green. |
