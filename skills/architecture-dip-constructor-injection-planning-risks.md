---
name: architecture-dip-constructor-injection-planning-risks
description: "Planning risks when replacing module-level importlib monkeypatching with constructor injection in a class hierarchy. Use when: (1) planning a DIP refactor that removes _PATCHABLE_DEPENDENCIES / importlib test-seams, (2) reviewing an implementation plan that uses **kwargs forwarding in subclass __init__, (3) assessing risk before migrating 20+ test patch sites to direct injection."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [DIP, dependency-injection, constructor-injection, importlib, test-seam, monkeypatch, mypy, BaseReviewer, SOLID]
---

# DIP Refactor: Constructor Injection to Replace importlib Test-Seams

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Replace `_resolve_from_subclass_module` + `_PATCHABLE_DEPENDENCIES` importlib test-seam in `BaseReviewer` with keyword-only factory parameters in `__init__` that default to the real collaborators |
| **Outcome** | Plan only — not yet implemented (verification: unverified) |
| **Verification** | unverified |

## When to Use

- Planning a DIP refactor that replaces module-level monkeypatching (`unittest.mock.patch("module.ClassName")`) with constructor injection
- The class under refactor uses `importlib.import_module(cls.__module__)` + `getattr` to pull collaborators at runtime
- A `_PATCHABLE_DEPENDENCIES` tuple enumerates the names of injectable collaborators
- Subclasses re-export the collaborators in their own `__all__` so `patch("subclass_module.ClassName")` resolves correctly
- You need to migrate 20+ test patch sites to direct injection in a single PR
- Reviewing any plan that uses `**kwargs` forwarding to pass injection parameters through a subclass `__init__`

## Verified Workflow

> **Status**: Planning-only — the steps below are planned but not yet executed. Treat as a design reference, not a verified recipe.

### Quick Reference

```python
# BaseReviewer injection signature (planned)
def __init__(
    self,
    options: Any,
    *,
    get_repo_root: Callable[[], Any] = _default_get_repo_root,
    worktree_manager_factory: Callable[[], WorktreeManager] = WorktreeManager,
    status_tracker_factory: Callable[[int], StatusTracker] = StatusTracker,
    log_manager_factory: Callable[[], ThreadLogManager] = ThreadLogManager,
) -> None: ...

# Shared test fixture (planned)
@pytest.fixture
def base_deps(tmp_path):
    return dict(
        get_repo_root=lambda: tmp_path,
        worktree_manager_factory=MagicMock(return_value=MagicMock()),
        status_tracker_factory=MagicMock(return_value=MagicMock()),
        log_manager_factory=MagicMock(return_value=MagicMock()),
    )

# Subclass __init__ explicit forwarding (safer than **kwargs)
class PRReviewer(BaseReviewer):
    def __init__(
        self,
        options: Any,
        *,
        get_repo_root: Callable[[], Any] = _default_get_repo_root,
        worktree_manager_factory: Callable[[], WorktreeManager] = WorktreeManager,
        status_tracker_factory: Callable[[int], StatusTracker] = StatusTracker,
        log_manager_factory: Callable[[], ThreadLogManager] = ThreadLogManager,
    ) -> None:
        super().__init__(
            options,
            get_repo_root=get_repo_root,
            worktree_manager_factory=worktree_manager_factory,
            status_tracker_factory=status_tracker_factory,
            log_manager_factory=log_manager_factory,
        )
```

### Planned Steps

1. **Verify subclass body usage before removing imports**: Read the complete body of both `pr_reviewer.py` and `address_review.py` to confirm that `WorktreeManager`, `StatusTracker`, and `ThreadLogManager` are only used at construction time (passed to `super().__init__`) and not called directly in body methods. Skipping this step risks `AttributeError` at runtime.

2. **Add factory parameters to `BaseReviewer.__init__`**: Use keyword-only parameters with class-as-default (e.g., `worktree_manager_factory: Callable[[], WorktreeManager] = WorktreeManager`). This preserves production call sites because the defaults behave identically to the old `importlib` resolution.

3. **Delete `_resolve_from_subclass_module` and `_PATCHABLE_DEPENDENCIES`**: Remove the importlib machinery only after step 2 is in place and all subclasses forward the new parameters.

4. **Update subclass `__init__` signatures**: Add explicit keyword-only parameters rather than `**kwargs` — explicit forwarding is mypy-transparent. If `--strict` mypy is in use, `**kwargs` forwarding will fail type-checking without `@overload`.

5. **Rewrite `test_reviewer_base_contract.py`**: The existing contract tests assert `_PATCHABLE_DEPENDENCIES` is exact and that re-exports exist on subclass modules. Both assertions become invalid after the refactor. Replace with tests that verify the injection API: that factories default to real classes, that injected mocks propagate to the constructed collaborators.

6. **Migrate 20+ test patch sites**: Replace `patch("hephaestus.automation.address_review.WorktreeManager")` etc. with direct injection via the `base_deps` fixture. Read ALL test files fully before migration — some patch sites target method calls on the instance, not just construction; those are unaffected by injection alone.

7. **Decide on `__all__` re-exports**: If `WorktreeManager` etc. appear in `pr_reviewer.__all__` only to support `patch("...pr_reviewer.WorktreeManager")` and there are no external callers doing `from hephaestus.automation.pr_reviewer import WorktreeManager`, remove the re-exports. Search for external importers before removing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `**kwargs` forwarding in subclass `__init__` | Pass `**kwargs` from `PRReviewer.__init__` to `super().__init__()` instead of enumerating parameters | mypy `--strict` infers `kwargs: dict[str, Any]`, which does not satisfy the typed keyword-only signature of `BaseReviewer.__init__`; requires `@overload` stubs or explicit params | Use explicit keyword-only parameter forwarding; `**kwargs` is opaque to type checkers and adds signature debt |
| Removing `__all__` without verifying external callers | Drop `WorktreeManager`/`StatusTracker`/`ThreadLogManager` from submodule `__all__` as part of the refactor | External code doing `from hephaestus.automation.pr_reviewer import WorktreeManager` would break silently; the import surface is part of the public API | Grep for all import sites across the codebase (and any downstream repos) before removing re-exports; keep `__all__` entries if any non-test callers exist |
| Skipping full body read of subclasses | Assumed collaborators were only used at construction time based on reading `__init__` only | Collaborators may appear in body methods (e.g., `self._worktree_manager.do_something()`) — their removal from the module namespace would cause `NameError` at call sites | Always read the complete file before removing module-level imports or re-exports |
| Not scanning for a third subclass | Assumed only `PRReviewer` and `AddressReviewer` exist | A third subclass that overrides `__init__` without forwarding the new parameters would silently use the old importlib path (if not deleted) or crash (if deleted) | Run `grep -r "BaseReviewer" --include="*.py"` exhaustively before assuming the subclass count is known |

## Results & Parameters

### Verified Code Locations (grep-confirmed)

| Symbol | File | Lines |
| -------- | ------ | ------- |
| `_resolve_from_subclass_module` | `hephaestus/automation/_reviewer_base.py` | 34–58 |
| `_PATCHABLE_DEPENDENCIES` | `hephaestus/automation/_reviewer_base.py` | 90–96 |
| `__all__` re-export block | `hephaestus/automation/pr_reviewer.py` | 49, 55, 57–58 |
| `__all__` re-export block | `hephaestus/automation/address_review.py` | 51–55 |
| `WorktreeManager.__init__` | `hephaestus/automation/worktree_manager.py` | 67 (no required args) |
| `StatusTracker.__init__` | `hephaestus/automation/status_tracker.py` | 19 (`num_slots: int` required) |
| `ThreadLogManager.__init__` | `hephaestus/automation/curses_ui.py` | 84 (no args) |

### Uncertain Assumptions (Not Verified at Planning Time)

1. `WorktreeManager`, `StatusTracker`, `ThreadLogManager` are NOT used directly in `pr_reviewer.py` or `address_review.py` body methods beyond the re-export — plan says "keep if used" but did not scan full body of both files
2. `**kwargs` forwarding on `PRReviewer.__init__` is compatible with mypy `--strict` — not verified against the mypy config
3. `state_dir.mkdir(parents=True, exist_ok=True)` in `__init__` is safe to call during test construction with `tmp_path` — not verified that fixtures don't assert on unexpected directory creation
4. Only 2 subclasses exist (`PRReviewer` and `AddressReviewer`) — not confirmed exhaustively via grep

### Key Risks for Plan Reviewer

1. **mypy `--strict` + `**kwargs` incompatibility**: If `pixi run mypy` runs with `--strict` and subclasses use `**kwargs` forwarding, type checking will fail. Use explicit parameter forwarding or add `@overload` stubs.
2. **20+ patch sites — read all tests in full**: `test_address_review.py` and `test_pr_reviewer_posting.py` have 20+ sites but were not read completely during planning. Some patches may target instance method calls, not just construction, making injection alone insufficient.
3. **`__all__` removal breaks external API surface**: `from hephaestus.automation.pr_reviewer import WorktreeManager` is a valid import path after the current re-exports; removing `__all__` entries without verifying downstream usage is a silent breaking change.
4. **Third subclass risk**: If any third `BaseReviewer` subclass exists and is not updated, it will silently revert to the old importlib path (if `_resolve_from_subclass_module` is kept) or crash at construction (if deleted).
5. **`StatusTracker` requires `num_slots: int`**: The default factory `StatusTracker` (no-arg) will crash at call time because `StatusTracker.__init__` requires `num_slots`. The factory signature must be `Callable[[int], StatusTracker]` and tests must pass a mock that accepts positional args.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1194 planning session — DIP violation fix in BaseReviewer | Plan only; implementation not started |

## References

- [SOLID Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Python unittest.mock.patch documentation](https://docs.python.org/3/library/unittest.mock.html#patch)
- [ProjectHephaestus Issue #1194](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1194)
