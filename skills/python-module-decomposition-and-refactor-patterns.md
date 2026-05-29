---
name: python-module-decomposition-and-refactor-patterns
description: >-
  Use when: (1) a Python module or class exceeds 800–1000 lines and contains
  identifiable method clusters with distinct responsibilities, (2) extracting
  method groups into dedicated collaborator classes or sub-modules via TDD,
  (3) fixing circular import errors caused by partially-initialized modules or
  eager __init__.py re-exports, (4) refactoring class methods to purely
  functional/immutable style, (5) preparing a codebase for extensibility
  through extraction, parameterization, and protocol-based abstraction,
  (6) extracting a CLI entry point or main() out of a module while preserving
  existing patch-based tests without edits (reverse-delegation pattern).
category: architecture
date: 2026-05-28
version: "1.1.0"
user-invocable: false
history: python-module-decomposition-and-refactor-patterns.history
tags:
  - python
  - refactoring
  - srp
  - tdd
  - dry
  - circular-imports
  - module-decomposition
  - collaborator-extraction
  - extensibility
  - cli-extraction
  - patch-routing
  - entry-point
---

# Python Module Decomposition and Refactor Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-28 |
| **Objective** | Decompose oversized Python modules/classes into focused, independently testable units using SRP, TDD, and DRY principles |
| **Outcome** | Synthesized from 7 verified skills; covers function-level extraction, class-based extraction, circular import fixes, immutability refactoring, extensibility-driven decomposition, and CLI entry-point extraction with preserved patch routing |
| **Trigger** | Files >800 lines, circular import errors, mixed-concern methods, C901 complexity, extensibility requirements, CLI main() extraction |

## When to Use

Apply this skill when any of the following is true:

- A class file exceeds **1000 lines** and contains 3+ independent method clusters
- A class exceeds its **800-line guideline** and has identifiable method groups sharing only a subset of class state
- A Python module has **4+ logical clusters** of functions with distinct responsibilities
- A method has a **`# noqa: C901`** suppression or is >100 lines mixing 3+ distinct logical steps
- Python raises **`ImportError: cannot import name 'X' from partially initialized module`** on startup
- `package/__init__.py` **eagerly re-exports CLI modules** that import back into the same package
- A method **mutates `self.attribute` and also returns it**, breaking an otherwise immutable class API
- You need to **prepare a codebase for a new pluggable feature** requiring protocol-based abstraction

## Verified Workflow

### Quick Reference

```text
Decision tree:
  >1000-line class with method clusters → Cluster Extraction (function-level)
  >800-line class with method groups    → Collaborator Extraction (TDD, class-based)
  >1000-line module with 4+ functions   → Module Decomposition (re-export or update import sites)
  Single complex method (C901, >100L)   → Single-Responsibility Extraction (collaborator)
  Circular ImportError on startup       → Symbol Extraction to leaf module
  Immutable API inconsistency           → Local-variable + early-return fix
  Extensibility blocked by coupling     → Extract-Parameterize-Protocol pattern
  Extract CLI main() while keeping      → Reverse-Delegation Pattern (Phase 11)
    existing patch.object tests intact    (new module calls collaborators THROUGH original)

Universal rule for mock patches after any move:
  Patch where the name is LOOKED UP at call time — not where it was defined.
  WRONG: patch("pkg.old_module.symbol")
  RIGHT: patch("pkg.new_module.symbol")

  EXCEPTION — Reverse-Delegation (CLI extraction):
  When tests already patch.object(original, "helper") and you cannot edit them,
  have the new module resolve helpers THROUGH the original module namespace so
  the lookup site stays on the original. See Phase 11.
```

### Phase 1: Measure and Map (Read, Do Not Write)

```bash
wc -l <target_file>.py   # confirm size
grep -n "^def \|^class " <target_file>.py   # list all functions/classes
# Find largest methods
python3 -c "
import ast
with open('<target_file>.py') as f:
    src = f.read()
tree = ast.parse(src)
funcs = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        end = node.end_lineno or node.lineno
        funcs.append((end - node.lineno + 1, node.lineno, node.name))
for size, lineno, name in sorted(funcs, reverse=True)[:15]:
    print(f'{size:4d} lines  line {lineno:4d}  {name}')
"
```

Group functions/methods by responsibility. Good decomposition boundaries:

| Signal | Extraction boundary |
| ------- | -------------------- |
| Methods share a common external dependency (one API only) | Extract together |
| Methods share state only via parameters, not `self` | Extract as module-level functions |
| Functions share a common prefix (`_build_*`, `_finalize_*`) | Extract to one module |
| A method has `# noqa: C901` or is >100 lines | Extract to collaborator class |
| The cluster has 2+ `self` attributes that always travel together | Collaborator class (not functions) |

**Stop criterion (YAGNI)**: Check `wc -l` after each extraction; stop when the target line count is met.

### Phase 2: Choose Extraction Strategy

**Function-level extraction** (preferred when state is passed as parameters):

```python
# New module: package/follow_up.py
def run_follow_up_issues(
    session_id: str, worktree_path: Path, issue_number: int,
    state_dir: Path, status_tracker: StatusTracker | None = None,
) -> None: ...

# Parent: thin delegation wrapper preserves public interface
def _run_follow_up_issues(self, session_id, worktree_path, issue_number, slot_id=None):
    run_follow_up_issues(session_id, worktree_path, issue_number,
                         self.state_dir, self.status_tracker, slot_id)
```

**Class-based extraction** (use when 2+ `self` attributes always travel together):

```python
class TierActionBuilder:
    def __init__(self, tier_id, config, tier_manager, save_tier_result_fn: Callable, ...):
        ...  # receives only what it needs — never the full host reference

# Delegation in host class:
def _build_tier_actions(self, tier_id, ...):
    return TierActionBuilder(tier_id=tier_id, config=self.config, ...).build()
```

**Design rule**: Methods should return `(config, checkpoint)` tuples rather than mutating `self` —
makes unit tests trivial and enables explicit data flow.

### Phase 3: Create New Module (Self-Contained, No Parent Imports)

The new module must be **self-contained** — it cannot import from the original module
(circular import risk). If it needs a type defined in the original, use `TYPE_CHECKING`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from original_module import MyModel  # type-check only

def my_function() -> MyModel:
    from original_module import MyModel  # runtime import (lazy)
    return MyModel(...)
```

**Critical for circular imports**: Use `TYPE_CHECKING` for collaborator type hints that would
create a cycle. Using `object` as the type causes `"object" has no attribute '...'` mypy errors.

### Phase 4: Fix Existing Tests — Update Mock Patch Targets

Every `patch("old.module.func")` must change to `patch("new.module.func")`:

```bash
grep -rn 'patch("package.old_module.' tests/
```

**Common mistake**: Only updating the direct test file but missing patch targets in unrelated
test files that also mock functions from the decomposed module.

```python
# BEFORE: patched where the code lived
patch("scylla.automation.implementer.run")

# AFTER: patch where the code now lives
patch("scylla.automation.follow_up.run")
```

Also update logger patches — warnings logged by an extracted class still target the old module:

```python
# After extracting CheckpointFinalizer, update:
patch("scylla.e2e.runner.logger") → patch("scylla.e2e.checkpoint_finalizer.logger")
```

### Phase 5: Module Decomposition — Re-export vs. Update Import Sites

**Choose "update import sites"** when: import sites are < 20, imports are lazy (inside function
bodies), and you want to avoid the re-export anti-pattern.

**Choose "re-export from original"** when: the module is a public API with many external
consumers or you cannot enumerate all import sites. Use explicit `as X` form (required by mypy):

```python
# In original file — explicit re-export (mypy requires `as X` syntax)
from scylla.e2e.stage_finalization import (
    stage_cleanup_worktree as stage_cleanup_worktree,  # re-exported
    stage_finalize_run as stage_finalize_run,           # re-exported
)
```

Without `as X`, mypy raises `Module does not explicitly export attribute` errors.

### Phase 6: Fix Circular Import Errors

**Step 0**: Check `__init__.py` for eager CLI re-exports — the most common hidden trigger:

```python
# PROBLEMATIC: __init__.py loads CLI modules that import back into the package
from hephaestus.github.fleet_sync import main as fleet_sync

# FIXED: remove eager re-exports; callers import CLI modules directly
```

**Diagnosis flow**:

```text
1. Read the full ImportError traceback — map chain A → B → C → A
2. Identify the shared symbol being imported across the cycle boundary
3. Ask: is this symbol lightweight (no heavy deps)?
   YES → extract to new leaf module
   NO  → consider lazy import OR restructure dependencies
```

**Leaf module pattern**:

```python
# shutdown.py — leaf module with zero heavy deps
import threading
_shutdown_event = threading.Event()

class ShutdownInterruptedError(Exception): ...
def is_shutdown_requested() -> bool: ...
def request_shutdown() -> None: ...
```

**Backward-compat re-export in the original module** (use `# noqa: F401`):

```python
# runner.py
from scylla.e2e.shutdown import (  # noqa: F401
    ShutdownInterruptedError,
    is_shutdown_requested,
    request_shutdown,
)
```

### Phase 7: Immutable Method Refactor

When a method mutates `self.attribute` but all sibling methods return updated tuples:

```python
# BEFORE — dual-write pattern (mutation + return)
self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
return self.config, self.checkpoint

# AFTER — local variable + early return (immutable)
if is_zombie(...):
    reset_checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
    return self.config, reset_checkpoint   # early return, self.checkpoint untouched
return self.config, self.checkpoint
```

Lock in the contract with a test assertion:

```python
original_checkpoint = rm.checkpoint
config, checkpoint = rm.handle_zombie(checkpoint_path, experiment_dir)
assert rm.checkpoint is original_checkpoint  # self must NOT change
```

### Phase 8: Extensibility via Extract-Parameterize-Protocol

```python
# Protocol for pluggable behavior
class SubtestProvider(Protocol):
    def discover_subtests(self, tier_id: TierID) -> list[SubTestConfig]: ...

# Default implementation (backward-compatible)
class FileSystemSubtestProvider:
    def __init__(self, shared_dir: Path) -> None:
        self.shared_dir = shared_dir
    def discover_subtests(self, tier_id, ...) -> list[SubTestConfig]: ...

# Client accepts protocol, defaults to existing behavior
class TierManager:
    def __init__(self, tiers_dir: Path, subtest_provider: SubtestProvider | None = None):
        if subtest_provider is None:
            subtest_provider = FileSystemSubtestProvider(shared_dir)
        self.subtest_provider = subtest_provider
```

**Extract Before Delete** (never delete until extraction is complete and merged):

```text
PR1: Create library with reusable logic  (extraction)
PR2: Delete old code                     (only after PR1 merged)
PR3: Consolidate duplication
PR4: Extract protocol interface
```

### Phase 9: Run Pre-commit (Expect Two Passes)

```bash
SKIP=audit-doc-policy pre-commit run --files \
  <package>/implementer.py \
  <package>/follow_up.py \
  tests/unit/<package>/test_follow_up.py

# First run: ruff auto-fixes imports and ordering
# Second run: all hooks pass — this is normal
```

**Common mypy issues after extraction**:

| Error | Fix |
| ------- | ----- |
| `"object" has no attribute "update_slot"` | Import the concrete type; use `TYPE_CHECKING` guard |
| `Missing type parameters for generic type "dict"` | Use `dict[str, Any]` not bare `dict` |
| `Item "None" of "X \| None" has no attribute "Y"` | Add `assert obj is not None` before access |
| `Unexpected keyword argument "cost_of_pass"` | It's a `@property` — remove from constructor |
| `Module does not explicitly export attribute` | Use `from module import X as X` for re-exports |
| `F841 Local variable assigned to but never used` | Remove the unused variable entirely |
| `Module "original" does not explicitly export attribute "SYMBOL"` (after reverse-delegation) | The new module accesses `_impl.SYMBOL` but SYMBOL was a plain `from x import SYMBOL` in original — add `from x import SYMBOL as SYMBOL` to original |

### Phase 10: Verify

```bash
wc -l <package>/<file>.py            # must meet target
python -c "from <package>.<module> import <cls>; print('OK')"
pytest tests/unit/<package>/ -q      # all tests pass
```

### Phase 11: CLI Entry-Point Extraction — Reverse-Delegation Pattern

Use when extracting `main()` / `_parse_args()` / CLI helpers out of a module into a new
sibling module, **but existing tests already call `original.main()` and patch collaborators
on the original module** (e.g. `patch.object(implementer, "gh_list_open_issues")`). Editing
those tests is not acceptable (they serve as characterization tests).

**The problem with a naive move**: The moved `main` looks up its collaborators in the NEW
module's namespace. Patches applied on `original` no longer intercept — the mock is never
triggered.

**Reverse-delegation fix (zero test edits)**:

In the new CLI module, have `main` resolve its patchable collaborators THROUGH the original
module's namespace — a lazy import inside the function body avoids import cycles and keeps the
lookup site on the original:

```python
# new_module.py (e.g. implementer_cli.py)
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    # Import lazily to avoid cycles; keeps lookup site on original module
    # so patch.object(implementer, "helper") keeps intercepting these calls.
    from . import implementer as _impl

    args = _impl._parse_args(argv)        # resolved on original → patches work
    repo_root = _impl.get_repo_root()     # resolved on original → patches work
    issues = _impl.gh_list_open_issues(repo_root)
    ui = _impl.CursesUI(issues)
    return _impl.IssueImplementer(ui).run()
```

**Re-export with explicit `as` aliases in the original module**:

Re-export the moved callables from the original with `as X` (redundant alias form). This:
1. Keeps `pkg.original:main` console-script entry point resolving (setuptools looks up
   `original.main`, which now re-exports it).
2. Satisfies mypy `implicit_reexport=false` — the `as X` form is the recognized explicit
   re-export idiom; ruff treats it as intentional so no `# noqa` is needed.
3. Keeps `original.main` / `original._parse_args` importable for existing test `import`
   statements.

```python
# original module (e.g. implementer.py) — add at the bottom of imports
from .implementer_cli import (
    main as main,
    _parse_args as _parse_args,
    _setup_logging as _setup_logging,
)
```

**Corollary mypy gotcha — re-exporting transitive symbols**:

If the moved function accesses `original.SYMBOL` where `SYMBOL` was a plain
`from x import SYMBOL` in the original, mypy raises:
`Module "original" does not explicitly export attribute "SYMBOL"`.

Fix by re-importing those symbols in the original with explicit `as` aliases:

```python
# implementer.py — make implicitly-used symbols explicit re-exports too
from .git_utils import get_repo_root as get_repo_root
from .github_api import gh_list_open_issues as gh_list_open_issues
```

**Coverage omit-allowlist guard**:

If the project has a frozen coverage omit-allowlist guarded by tests (e.g.
`tests/unit/validation/test_omit_allowlist.py` and `tests/integration/test_orchestration_smoke.py`),
adding a new orchestration/entry-point module requires updating BOTH the pyproject omit list
AND those guard tests (counts + module lists) in the same PR, or CI fails.

**Issue-scoping gotcha**:

When the umbrella issue (e.g. "decompose God Class") is mostly done and the PR only covers one
slice, the required pr-policy CI gate hard-requires `Closes #N` on its own line — `Refs #N` alone
blocks CI. Resolution: file a narrow tracking sub-issue for the specific slice, put
`Closes #<sub-issue>` + `Refs #<umbrella>` in the PR body. The umbrella stays open; CI passes.

**Verification checklist for reverse-delegation extraction**:

```bash
# 1. Run pre-existing tests UNCHANGED — they ARE the characterization tests
pytest tests/unit/<package>/test_<original>.py -v   # all N tests pass

# 2. Import-cycle guard
python -c "from <package>.<new_cli_module> import main; print('OK')"
python -c "from <package>.<original> import main; print('OK')"

# 3. Console-script entry-point smoke test
<package>-cli --help   # or: python -m <package>.<original> --help

# 4. Full suite
pytest tests/ -q
```

**Results (ProjectHephaestus PR #674)**:

| Metric | Value |
| -------- | ------- |
| `implementer.py` before | 872 lines |
| `implementer.py` after | 702 lines (−19%) |
| New `implementer_cli.py` | 236 lines |
| Pre-existing tests unchanged | 45 pass |
| New tests added | 6 |
| Full automation suite | 780 tests pass |
| ruff + mypy | clean (288 files) |
| Verification level | verified-local |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| **`object` type for status_tracker** | Used `status_tracker: object \| None` to avoid importing `StatusTracker` | mypy: `"object" has no attribute "update_slot"` — `object` is too broad | Import the concrete type; use `TYPE_CHECKING` guard for circular-import risk |
| **Bare `dict` in type annotations** | Wrote `list[dict]` in helper function signatures | mypy `type-arg` error: generic type needs params | Use `list[dict[str, Any]]` consistently; add `from typing import Any` |
| **Forgetting to update existing test patch paths** | Left old `patch("pkg.implementer.run")` for methods moved to `follow_up.py` | Mocks never triggered: `AssertionError: Called 0 times` | Always grep for module-level patches in existing tests when extracting code |
| **Extracting all clusters before checking line count** | Planned to extract all clusters unconditionally | Premature — target met after first extraction; over-engineered the rest | Apply YAGNI: check `wc -l` after each extraction; stop when target is met |
| **Using `object` type for collaborator type hints** | Typed workspace_manager as `object` to avoid circular imports | mypy: `"object" has no attribute "create_worktree"` | Use `TYPE_CHECKING` guard: `if TYPE_CHECKING: from .module import Type` |
| **Inlining delegation shells that tests mock** | Removed thin delegation wrappers to reduce line count | Tests used `patch.object(runner, "_write_pid_file")` — `AttributeError` on 9 tests | Retain thin delegation wrappers when existing tests mock them by name |
| **Patching old logger after extraction** | Left `patch("pkg.runner.logger")` after warning moved to extracted class | Mock showed 0 calls — warning emitted from extracted module's logger | After each extraction, grep tests for old module logger patches and update |
| **Mutating self instead of returning** | Initial collaborator design modified `self.config` / `self.checkpoint` in place | Hard to test — must inspect object internals; creates hidden coupling | Return `(config, checkpoint)` tuples for clean, testable API |
| **Lazy imports inside function bodies (circular fix)** | Moved `from pkg.runner import is_shutdown_requested` inside function bodies | Did not fix error — symbol referenced during module-level code in intermediate module | Lazy imports only help if symbol is used at call time; use leaf module extraction instead |
| **Patching old module location after symbol move** | Left `patch("pkg.runner.is_shutdown_requested")` after moving to `shutdown.py` | Patches registered on old location; callers looked up new location — mock never invoked | After moving a symbol, update ALL patches to target the new module |
| **Deleting only `__init__.py` re-exports without moving symbol** | Removed CLI entries from `__init__.py` but left import edge in `fleet_sync.py` | Import edge remained intact; future code paths can re-trigger the same cycle | Eliminate the layering violation at the source (move to leaf module) |
| **Trying to refactor everything in one PR** | Single large PR with all extraction changes | Too many changes to review; hard to isolate breaks; difficult rollback | Split into focused PRs following dependency order (extract → verify → delete) |
| **Deleting scripts before creating library** | Considered deleting old code first, then extracting | Would break workflows during transition; no way to verify extraction matches original | Always follow: Extract → Verify → Delete pattern |
| **Linter reverting collaborator changes** | Committed SubtestProvider extraction without checking linter state | Black ran between commit and next work session; reverted changes | Always `git status` before starting new work; verify imports immediately after refactoring |
| **Naive move of main() breaks patch.object tests** | Moved `main()` directly to new CLI module; existing tests used `patch.object(implementer, "gh_list_open_issues")` | New `main` looked up `gh_list_open_issues` in new module namespace — patch on old module never intercepted; mocks showed 0 calls | Use Reverse-Delegation: new `main` imports original lazily (`from . import implementer as _impl`) and calls `_impl.helper()` so lookup stays on the original (Phase 11) |
| **Bare re-export without `as` alias in original** | Added `from .implementer_cli import main` (no `as main`) to original module | mypy `implicit_reexport=false`: `Module "implementer" does not explicitly export attribute "main"`; console-script entry-point also failed to resolve | Use `from .implementer_cli import main as main` — the redundant alias is the recognized re-export idiom for both mypy and ruff |
| **Forgetting transitive symbol re-exports** | Moved `main` called `_impl.get_repo_root()` but `get_repo_root` was a plain `from .git_utils import get_repo_root` in original | mypy: `Module "implementer" does not explicitly export attribute "get_repo_root"` | Re-import every symbol the new module accesses via `_impl.X` with explicit `as X` alias in the original: `from .git_utils import get_repo_root as get_repo_root` |
| **Missing coverage omit-allowlist update** | Added new `implementer_cli.py` orchestration module without updating pyproject omit list or guard tests | `test_omit_allowlist.py` and `test_orchestration_smoke.py` failed: counts mismatch + module not in expected list | Update the omit list in `pyproject.toml` AND both guard test files in the same PR as the new module |
| **Using `Refs #N` only on partial-fix PR** | Opened PR for one CLI-extraction slice with `Refs #468` (umbrella) but no `Closes #N` | pr-policy CI gate hard-requires literal `Closes #N` line; PR was blocked | File a narrow sub-issue for the specific slice, put `Closes #<sub>` + `Refs #<umbrella>` in PR body — umbrella stays open, CI passes |

## Results & Parameters

### Extraction outcome benchmarks

| Source | Before | After | Reduction | New files |
| ------- | ------- | ------- | --------- | --------- |
| `implementer.py` (function-level) | 1,221 | 837 | −31% | `retrospective.py`, `follow_up.py`, `pr_manager.py` |
| `implementer.py` (CLI extraction, reverse-delegation) | 872 | 702 | −19% | `implementer_cli.py` (236 lines) |
| `runner.py` (class-based, 3 collaborators) | 1,527 | 1,105 | −28% | `TierActionBuilder`, `ParallelTierRunner`, `ExperimentResultWriter` |
| `runner.py` (single method → `ResumeManager`) | 1,638 | 1,509 | −8% | `resume_manager.py` (175 lines, 98.5% coverage) |
| `llm_judge.py` (module decomposition) | 1,488 | 142 | −90% | `build_pipeline.py`, `judge_context.py`, `judge_execution.py`, `judge_artifacts.py` |
| `stages.py` + `run_report.py` (re-export) | 1,534 + 1,385 | 855 + 289 | −44% / −79% | 4 new modules |
| Extensibility refactor (6 PRs) | — | — | −415 net | `discovery/`, `subtest_provider.py`, `TestFixture` |

### New test benchmarks

```text
cluster-extraction (implementer.py): 37 new unit tests, 336 automation tests pass
collaborator-extraction (runner.py):  69 new unit tests (27 + 19 + 23); 3,326 total pass
single-responsibility (ResumeManager): 26 new unit tests; 3,211 total pass
circular-import fix:   4 mock patches updated; CI passed (ProjectScylla + ProjectHephaestus)
immutable refactor:    3 lines changed; 30 tests pass
```

### Leaf module template (circular import fix)

```python
# package/shutdown.py — leaf module
"""Shutdown coordination primitives (extracted to break circular imports)."""
import threading

_shutdown_event = threading.Event()

class ShutdownInterruptedError(Exception): ...

def is_shutdown_requested() -> bool:
    return _shutdown_event.is_set()

def request_shutdown() -> None:
    _shutdown_event.set()
```

### Explicit re-export form required by mypy

```python
# WRONG (mypy: "Module does not explicitly export attribute"):
from hephaestus.github.gh_subprocess import _gh_call

# RIGHT (mypy accepts):
from hephaestus.github.gh_subprocess import _gh_call as _gh_call
```

### Extract-Parameterize-Protocol pattern (canonical)

```python
# Old: Hardcoded logic in _private_method()
#   ↓
# New: Reusable function(source_dir: Path)
#   ↓
# Protocol: class Provider(Protocol): def discover(...): ...
#   ↓
# Client: accepts Provider, defaults to FileSystemProvider

# Optional parameter with smart default (backward-compatible):
def __init__(self, required: Path, optional: Path | None = None):
    if optional is None:
        optional = self._compute_default()
    self._value = optional
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1444 — `implementer.py` 1221→837 (function-level cluster extraction) | Superseded `cluster-extraction-to-modules` |
| ProjectScylla | PR #1230 — `runner.py` 1527→1105 (3 collaborator classes, TDD) | Superseded `collaborator-extraction-tdd` |
| ProjectScylla | PR #1145 — `runner.py` `ResumeManager` single-method extraction | Superseded `single-responsibility-extraction` |
| ProjectScylla | PR #1446 — `llm_judge.py` 1488→142 module decomposition | Superseded `module-decomposition-pattern` |
| ProjectScylla | PR #1850 — circular import fix (`shutdown.py` leaf extraction) | Superseded `python-circular-import-symbol-extraction` |
| ProjectHephaestus | PR #308 — `__init__.py` eager re-export circular import fix | Superseded `python-circular-import-symbol-extraction` |
| ProjectScylla | PR #1311 — `ResumeManager.handle_zombie` immutable refactor | Superseded `immutable-method-refactor` |
| ProjectScylla | PRs #356–#361 — extensibility refactor (discovery lib, SubtestProvider, TestFixture) | Superseded `refactor-for-extensibility` |
| ProjectHephaestus | PR #674 — `implementer.py` 872→702 lines; new `implementer_cli.py` (236 lines); reverse-delegation preserves 45 pre-existing tests unchanged; 780 automation tests pass; ruff+mypy clean (verified-local) | CLI entry-point extraction with preserved patch routing (Phase 11) |
