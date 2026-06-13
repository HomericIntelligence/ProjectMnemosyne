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
  existing patch-based tests without edits (reverse-delegation pattern),
  (7) reducing cyclomatic complexity (CC>15) by extracting helper steps from
  oversized pipeline methods carrying `# noqa: C901`, (8) refactoring a broad
  repository-wide scanner to target a single subdirectory using
  Path.is_relative_to() allow-lists, (9) detecting and fixing double-increment
  bugs caused by incomplete context-manager refactors where callers still hold
  stale manual counter management, (10) safely removing legacy dead-code files
  marked as fallback/reference-only after verifying zero real callers,
  (11) reading the existing substrate code before estimating a large refactor
  to avoid 3-5x LOC over-estimation, (12) finalizing code after parallel phases
  complete by addressing technical debt accumulated during rapid development,
  (13) decomposing a 1000–2000 LoC orchestrator into named pipeline phases
  (PlanPhase, ImplementPhase, ReviewPhase, FollowUpPhase, PRCreatePhase) while
  preserving existing `patch.object(impl, ...)` AND `patch.object(impl.phase_runner, ...)`
  test contracts via reverse-delegation shims and a dual-back-reference StageContext.
category: architecture
date: 2026-06-10
version: "1.4.0"
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
  - cyclomatic-complexity
  - pipeline-extraction
  - scanner-scoping
  - context-manager
  - dead-code
  - estimation
  - phase-cleanup
  - phase-strategy
  - reverse-delegation
  - stage-context
  - orchestration-decomposition
  - patch-preservation
---

# Python Module Decomposition and Refactor Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-05 |
| **Objective** | Decompose oversized Python modules/classes into focused, independently testable units using SRP, TDD, and DRY principles |
| **Outcome** | Synthesized from 13 verified skills; covers function-level extraction, class-based extraction, circular import fixes, immutability refactoring, extensibility-driven decomposition, CLI entry-point extraction with preserved patch routing, top-level symbol extraction to break sibling module cycles, CC>15 pipeline-step extraction, scanner-to-subdirectory scoping, context-manager double-counter fixes, safe legacy-code deletion, substrate-read-before-estimate discipline, and post-parallel phase cleanup |
| **Trigger** | Files >800 lines, circular import errors, mixed-concern methods, C901/CC>15 complexity, extensibility requirements, CLI main() extraction, deferred imports inside function bodies preventing static analysis, broad scanners needing subdirectory scope, stale callers after context-manager refactors, dead fallback files, pessimistic refactor estimates, technical debt after parallel phases |

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
- Sibling modules (e.g., `implementer_cli`, `implementer_phase_runner`) have **deferred back-pointer imports inside function bodies** that mask circular dependencies from static analysis tools and complicate test patching
- A pipeline function runs **4+ sequential stages**, carries a `# noqa: C901` suppression, and has **CC>15** (or above the project threshold)
- A scanner/linter/auditing script uses a **deny-list (`EXCLUDED_PREFIXES`)** and you want to scope it to a single subdirectory via an allow-list
- A counter/semaphore/ref-count test asserting `== 1` now observes `2` **after a context-manager refactor** (stale manual `+1/-1` left in a caller)
- A code file declares itself **"kept for reference / fallback only"** but has zero real callers and leaves stale back-references in production code
- A `TODO.md`/roadmap/audit estimates **"thousands of LOC" or weeks** for a substrate rewrite — read the substrate first to avoid a 3-5x pessimistic estimate
- You are in the **cleanup phase** after parallel Test/Implementation/Package phases and need to address accumulated technical debt before merge
- A **1000–2000 LoC orchestrator class** (e.g. `IssueImplementer`, `ImplementationPhaseRunner`) needs decomposition into named pipeline phases AND existing tests use BOTH `patch.object(impl, "_xxx")` and `patch.object(impl.phase_runner, "_xxx")` against methods you must move (Phase 19)

## Verified Workflow

### Quick Reference

```text
Decision tree:
  >1000-line class with method clusters → Cluster Extraction (function-level)
  >800-line class with method groups    → Collaborator Extraction (TDD, class-based)
  >1000-line module with 4+ functions   → Module Decomposition (re-export or update import sites)
  Single complex method (C901, >100L)   → Single-Responsibility Extraction (collaborator)
  Circular ImportError on startup       → Symbol Extraction to leaf module
  Deferred imports mask cycles          → Top-Level Symbol Extraction (Phase 12)
  Immutable API inconsistency           → Local-variable + early-return fix
  Extensibility blocked by coupling     → Extract-Parameterize-Protocol pattern
  Extract CLI main() while keeping      → Reverse-Delegation Pattern (Phase 11) OR
    existing patch.object tests intact    Top-Level Extraction (Phase 12)
  CC>15 pipeline method (# noqa: C901)  → Pipeline-Step Extraction (Phase 13)
  Broad scanner → one subdirectory      → Allow-list scope helper (Phase 14)
  Counter == 2 after ctx-manager move   → Audit callers, drop stale +1/-1 (Phase 15)
  Dead "fallback only" file, 0 callers  → Safe Legacy Deletion (Phase 16)
  Estimating a big rewrite              → Read substrate FIRST (Phase 17)
  Cleanup after parallel phases         → Finalization checklist (Phase 18)
  Orchestrator → named pipeline phases  → Phase-Strategy w/ Dual-Backref StageContext
    AND tests patch BOTH impl AND         (Phase 19): reverse-delegation shims +
    impl.phase_runner methods             ctx.impl + ctx.runner; phases call
                                          self.ctx.runner._xxx() to preserve both
                                          patch addresses

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

### Phase 12: Top-Level Symbol Extraction — Breaking Sibling-Module Cycles

Use when two sibling modules (e.g., `implementer_cli.py`, `implementer_phase_runner.py`) have
circular dependencies masked by **deferred back-pointer imports inside function bodies**.
This pattern prevents static analysis tools (mypy, ruff, import-graph linters) from detecting
the cycle, and complicates test patching by requiring patches on the wrong lookup site.

**The problem**: Function-local imports like `from . import implementer` inside function bodies
in sibling modules mask the cycle from static analysis:

```python
# implementer_phase_runner.py — BEFORE (deferred import)
def _implement_issue(self):
    from . import implementer as _impl  # ← deferred, inside function body
    _impl.is_plan_review_go(...)        # ← patches must target implementer, not here
```

**Why this is problematic**:

1. **Static analysis blind**: AST-based import graph tools don't see `from . import implementer`
   because it's inside a function. The cycle remains invisible.
2. **Test patching mismatch**: Tests must patch `implementer.is_plan_review_go()`, but the
   call site is in `implementer_phase_runner.py`. This breaks encapsulation.
3. **Brittle AST guards**: Regression tests must use AST walking + ID tracking to catch
   future deferred imports, adding maintenance burden.

**Solution: Extract patchable symbols to module-level imports with `# noqa: F401`**:

Instead of deferring imports, import directly from the true source module at the top of the
file. Use `# noqa: F401` for symbols that are imported purely for test patchability (not used
in code):

```python
# implementer_phase_runner.py — AFTER (top-level extraction)
from .review_state import is_plan_review_go  # ← top-level, visible to static analysis
from .session_naming import (               # ← patchable in tests
    AGENT_ADVISE,
    AGENT_IMPLEMENTER,
    current_trunk_githash,
)  # noqa: F401  # ← used only in tests; re-export for patch routing

# Later, inside _implement_issue:
def _implement_issue(self):
    if is_plan_review_go(...):  # ← direct import, clean code
        ...
```

**Key decisions**:

1. **Where to extract from**: Import from the **true source module** (`review_state.py`,
   `session_naming.py`), not from an intermediate re-export.
2. **Patching location**: Tests patch at `implementer_phase_runner.is_plan_review_go` because
   that's where the name is **looked up at call time**.
3. **noqa usage**: Use `# noqa: F401` only for symbols that are re-exported purely for test
   patchability. If the symbol is used in the module, omit the noqa.

**Implementation steps**:

1. **Identify patchable symbols**: Grep test files for `patch("module.symbol")` to find what
   needs to be patchable.
2. **Extract to top-level imports**: Move deferred imports from function bodies to module-level.
3. **Remove the `_impl_module` property** (if used): Dynamic lookup via `self._impl.symbol` is
   no longer needed; use direct imports.
4. **Add regression test with AST guards**: Create a test that verifies no runtime back-pointer
   imports exist in sibling modules (prevents future deferred imports).
5. **Retarget existing test patches**: Update any patches that target the old location.

**Regression test (AST-based guard)**:

```python
# test_implementer_no_cycle.py
import ast
from pathlib import Path

def _is_backpointer_import(node: ast.AST) -> bool:
    """Detect deferred imports that would re-introduce #714 cycle."""
    if isinstance(node, ast.ImportFrom):
        if node.module is None and node.level == 1:
            return any(a.name == "implementer" for a in node.names)
        if node.module == "implementer" and node.level == 1:
            return True
    return False

def test_no_runtime_backpointer_to_implementer() -> None:
    """Verify no deferred back-pointer imports inside function bodies."""
    src = (Path(__file__).parent / "implementer_phase_runner.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                assert not _is_backpointer_import(sub), (
                    f"Deferred import re-introduces #714 cycle"
                )
```

**Comparison: Reverse-Delegation (Phase 11) vs. Top-Level Extraction (Phase 12)**

| Aspect | Reverse-Delegation (Phase 11) | Top-Level Extraction (Phase 12) |
|--------|-------------------------------|--------------------------------|
| **Deferred imports** | Yes (`from . import X` in function body) | No (all imports at module-level) |
| **Static analysis visibility** | No — cycle is hidden from AST tools | Yes — cycle visible, detectable |
| **Test patching** | Patches on original module (preserved test compatibility) | Patches on runner module (cleaner separation) |
| **Code readability** | Less clear: symbol resolution via `_impl.X` | More clear: direct `symbol` use |
| **Maintenance burden** | Low (works for CLI extraction) | Low (top-level is standard Python) |
| **Use case** | Extracting `main()` when tests already patch original | Breaking sibling-module cycles with function-local dispatch |
| **Example** | `implementer_cli.main()` imports `implementer` to resolve helpers | `implementer_phase_runner` imports symbols directly from source modules |

**When to choose Phase 12 over Phase 11**:

- The cycle is between **sibling modules** (not parent→child as with CLI extraction)
- Tests already patch the **runner/executor module**, not the original
- **Static analysis** must detect the import graph (for linting, dependency audit)
- You want to **eliminate function-local imports entirely** for clarity

**Results (ProjectHephaestus PR #714)**:

| Metric | Value |
| -------- | ------- |
| `implementer_phase_runner.py` deferred imports removed | 3 locations (lines ~843, ~1302, ~1576) |
| Patchable symbols extracted to top-level | 9 symbols (is_plan_review_go, fetch_issue_info, invoke_claude_with_session, get_repo_slug, AGENT_ADVISE, AGENT_IMPLEMENTER, review_state, find_pr_for_issue, current_trunk_githash) |
| `_impl_module` property removed | Yes |
| Test patches retargeted | 6+ patches (from implementer.*to implementer_phase_runner.*) |
| Regression test added | test_implementer_no_cycle.py with AST guards |
| All automation tests pass | Yes (verified-ci) |
| CI gates pass | Yes |
| Verification level | verified-ci |

### Phase 13: Pipeline-Step Extraction — CC>15 Reduction

Use when a module-level function runs **4+ sequential pipeline stages** (each with an
"if tool not installed → skip" and "if step failed → return" branch), carries a
`# noqa: C901` suppression, and exceeds the project's complexity threshold.

**1. Identify the repeated step shape** — each inline stage is a 6–10 line "if tool missing →
return na; run subprocess; if failed → return" block inside the pipeline function.

**2. Extract each step into a `_run_<pipeline>_<stage>_step` helper returning a 3-tuple**:

```python
def _run_mojo_build_step(workspace: Path, is_modular: bool) -> tuple[bool, bool, str]:
    if not shutil.which("magic" if is_modular else "mojo"):
        return False, True, ""          # passed, na, output
    result = _run_subprocess(["mojo", "build", ...], workspace)
    return result.passed, False, result.output
```

The 3-tuple contract is consistent everywhere: `(passed: bool, na: bool, output: str)`.
The pipeline function unpacks and early-returns:

```python
passed, na, output = _run_mojo_build_step(workspace, is_modular)
if na:
    return BuildPipelineResult(build=StepResult(passed=False, output="", na=True), ...)
if not passed:
    return BuildPipelineResult(build=StepResult(passed=False, output=output), ...)
```

**3. Extract shared steps once** (no pipeline prefix) when two pipelines share an identical
stage such as pre-commit — one `_run_precommit_step(workspace, env=None) -> (bool, bool, str)`
helper, not one per pipeline.

**4. Split large orchestrators into two phases** — context gathering vs. retry execution:

```python
def run_llm_judge(...) -> JudgeResult:
    judge_start = time.time()
    judge_prompt, _pipeline_result = _gather_judge_context(...)   # file reads, rubric, pipeline
    return _execute_judge_with_retry(judge_prompt, model, workspace, judge_dir, judge_start, language)
```

**5. Promote inline imports to module level** before extracting — otherwise each extracted
helper needs its own inline import. **6. Verify** with
`ruff check --select C901 <file>.py` → "All checks passed!", then remove `# noqa: C901`.
**7. Fix RUF059** by prefixing unused unpacked tuple fields with `_`
(`passed, _na, _output = ...`); keep the name un-prefixed when it IS used in an assertion.
**8. Each step helper gets 3 unit tests**: tool-not-installed (`na=True`),
tool-installed-fails, tool-installed-passes.

### Phase 14: Scope a Broad Scanner to a Single Subdirectory

Use when a scanner/linter/auditing script uses a growing deny-list (`EXCLUDED_PREFIXES`)
and you want to restrict it to one directory. **Allow-list beats deny-list**: deny-lists
grow forever (`.pixi/`, `build/`, `node_modules/`, …) and break on every new top-level dir.

```python
# BEFORE: deny-list (fragile, grows over time)
EXCLUDED_PREFIXES = (".pixi/", "build/", "node_modules/", "tests/claude-code/")
def scan_repository(repo_root: Path) -> list[Finding]:
    for py in sorted(repo_root.rglob("*.py")):
        rel = str(py.relative_to(repo_root)).replace("\\", "/")
        if any(rel.startswith(p) for p in EXCLUDED_PREFIXES):
            continue
        ...

# AFTER: allow-list helper (correct by construction, independently testable)
def _is_scylla_file(path: Path, root: Path) -> bool:
    """Return True if path is a .py file under the scylla/ directory."""
    return path.suffix == ".py" and path.is_relative_to(root / "scylla")

def scan_repository(repo_root: Path) -> list[Finding]:
    for py in sorted(repo_root.rglob("*.py")):
        if not _is_scylla_file(py, repo_root):
            continue
        ...
```

`Path.is_relative_to()` needs Python 3.9+. For older runtimes, wrap `relative_to()` in
`try/except ValueError`. **Export the helper** so tests import it directly. Add
`TestIsScyllaFile` (accept in-scope `.py`, reject out-of-scope dir, reject non-`.py`) and
`TestScanRepositoryScope` (in-scope file with a fragment is found; out-of-scope file is not).

**Critical migration step**: existing tests that wrote fixtures at `tmp_path / "bad.py"` now
return zero findings (root is outside scope). Move fixtures into the scoped dir and update
hard-coded path assertions (`"bad.py"` → `"scylla/bad.py"`).

### Phase 15: Fix Double-Counter from a Stale Caller After a Context-Manager Refactor

Use when a counter/semaphore/ref-count test asserting `== 1` now observes `2` after a
refactor introduced a context manager that owns the lifecycle. This is an **incomplete
migration** sub-case: the context manager owns the `+1/-1`, but a caller still does it manually.

```python
# Context manager owns lifecycle (correct):
@contextmanager
def _inflight_context(self):
    self._inflight += 1
    try:
        yield
    finally:
        self._inflight -= 1

# Callee adopts it (correct):
def _handle_webhook(self, ...):
    with self._inflight_context():
        ...

# STALE caller — double-increment bug:
def receive_webhook(self, ...):
    self._inflight += 1          # BUG: duplicates context manager → REMOVE
    self._handle_webhook(...)
    self._inflight -= 1          # BUG: duplicates context manager → REMOVE
```

**Workflow**: (1) find the new `@contextmanager`; (2) confirm the callee uses it;
(3) `grep -rn "_handle_webhook" src/ tests/` to find **every** caller; (4) audit each for
manual `self._inflight [+-]= 1` pairs; (5) delete the stale lines; (6) re-run
`pytest -k inflight -v`. **General principle**: a refactor that moves lifecycle into a
context manager / RAII / try-finally is INCOMPLETE until you grep the whole codebase for
prior manual lifecycle code in callers. Search production code, not just the failing test.

### Phase 16: Safe Legacy Dead-Code Deletion

Use after extraction is complete and a file declares itself "kept for reference / fallback
only" but has zero real callers (the completion step of any decomposition). Never delete
before the replacement is verified — follow Extract → Verify → Delete.

1. **Confirm the legacy declaration** (`head -20 <file>`: "kept for reference / fallback
   only" or "Deprecated in favor of `<replacement>`") and **identify the tested replacement**.
2. **Verify zero real callers** (the critical step) — grep invocations across `*.py`, `*.sh`,
   `*.md`, `.github/`; expect zero matches except the file itself and its own tests:
   ```bash
   grep -r "run_automation_loop\.sh" --include="*.py" --include="*.sh" --include="*.md" .
   grep -r "from legacy_module import\|import legacy_module" --include="*.py" .
   ```
3. **Rewrite stale back-references** — comments that point at the file (without calling it)
   become self-contained explanations of *why* the code works, not *where* to read more.
4. **Delete the file and its exclusive tests**; update README/docs that list it.
5. **Comprehensive verification** — full unit + integration + shell suites, ruff, mypy, and a
   final grep proving zero remaining references. **Commit with rationale** quoting the file's
   own "fallback only" header (a YAGNI anti-pattern) and listing deleted files + scrubbed refs.

### Phase 17: Read the Substrate Before Estimating a Rewrite

Use before estimating a large refactor — TODO.md / roadmap / audit LOC estimates are
commonly **3-5x pessimistic** because they don't credit infrastructure that already exists.
This is a prerequisite to any module-decomposition decision.

1. **Resist trusting the TODO.** Treat "Phase X: ~N000 LOC" as a pessimistic upper bound,
   not a target.
2. **Inventory the substrate** — `find src/ -path "*<subsystem>*" | xargs wc -l`.
3. **Read each substrate file in full** (not skim). Record, with `file.ext:line` citations:
   public functions that already work, invariants relied on (e.g., "forward execution order
   = topo order"), state already polymorphic enough for the extension, and existing dispatch
   tables/registries.
4. **Cite line numbers as evidence** — no "X already works" without a citation.
5. **List actual gaps** with the minimum-needed signature each — separates real new code
   from wiring.
6. **Revised estimate = new code only.** If existing infra handles 70%, estimate is ~30% of
   the TODO number. Re-classify audit "CRITICAL: missing" as "incomplete, N% gap" when the
   substrate exists.
7. **Validate by landing** the smallest end-to-end slice and comparing actual LOC to the
   revised estimate (verified case: TODO said "~5000 LOC", revised ~1400, actual +937).

### Phase 18: Cleanup / Finalization After Parallel Phases

Use as the finalization phase after parallel Test/Implementation/Package work completes,
to address technical debt accumulated during rapid parallel development before merge.

**Workflow**: (1) collect TODOs/FIXMEs/bugs from all parallel outputs; (2) refactor —
remove duplication (DRY), simplify complexity (KISS), improve naming; (3) update docs to
match implementation; (4) final quality gates (format, lint, test, coverage); (5) verify
merge-ready.

```bash
grep -r "TODO\|FIXME\|HACK" src/         # collect debt
<formatter> <src> <tests>                # format
<test-runner> <tests>                    # all green
<build> 2>&1 | grep -i warning && echo "WARN" || echo "clean"   # zero-warnings policy
git status                               # no uncommitted changes
```

**Cleanup checklist**: no TODOs/FIXMEs (or tracked in an issue), duplication removed,
complex functions simplified, naming consistent, docs updated, all tests passing, code
formatted, zero compiler warnings, coverage at/above floor, ready for review. Cleanup is the
final polishing gate before PR approval and merge.

### Phase 19: Phase-Strategy Decomposition with Dual-Back-Reference StageContext

Use when a 1,000–2,000 LoC orchestrator class needs to be decomposed into a small
set of named pipeline phases (the issue often names them explicitly:
`PlanPhase`, `ImplementPhase`, `ReviewPhase`, `FollowUpPhase`, `PRCreatePhase`)
AND existing tests already pin internal method names on TWO different objects:
`patch.object(impl, "_xxx")` AND `patch.object(impl.phase_runner, "_xxx")`.

This is the case Phases 11 and 12 don't cover: CLI extraction (Phase 11) preserves
patches on the original module; sibling-cycle extraction (Phase 12) retargets
patches to the runner. Phase 19 must preserve BOTH patch addresses simultaneously
because both are exercised by the test suite, on the same set of methods.

**Core idea**:

1. Each phase exposes ONE public `run(...)` method and N private `_xxx_impl` methods
   that hold the real bodies lifted from the runner.
2. The coordinator (`ImplementationPhaseRunner`) keeps EVERY name that tests patch
   as a one-line shim: `def _xxx(self, *a, **kw): return self.review_phase._xxx_impl(*a, **kw)`.
3. Phases dispatch back via `self.ctx.runner._xxx(...)` — NOT `self.ctx.impl._xxx(...)`.
   The runner is the patchable surface; `impl` only exists for the small set of
   methods that tests pin directly on the implementer.
4. `StageContext` is a frozen dataclass carrying BOTH back-references:

```python
@dataclass(frozen=True)
class StageContext:
    impl: IssueImplementer            # preserves patch.object(impl, "_xxx")
    runner: ImplementationPhaseRunner  # preserves patch.object(impl.phase_runner, "_xxx")
    state_mgr: ImplementerStateManager
    # ... other already-initialized collaborators

    def __post_init__(self):
        assert self.impl.state_mgr is not None, (
            "StageContext built before IssueImplementer finished __init__ — "
            "construct phases AFTER state_mgr is wired"
        )
```

**Why both references?**

A naive single back-reference (just `impl`) causes a subtle test break: when a
test does `patch.object(impl.phase_runner, "_fetch_plan_and_review")`, it patches
the runner shim. But if the phase dispatched via `self.ctx.impl._fetch_plan_and_review`,
the call goes through the implementer's pass-through, NOT through the runner shim
the test patched — so the patch never fires. Holding `runner` directly on the
context and routing through `self.ctx.runner.<name>` keeps the lookup site on
the patched object.

**Workflow**:

1. **Audit ALL patch sites BEFORE moving code.** The union of patches is the
   contract; every name must remain callable on its original object:
   ```bash
   grep -rn 'patch.object(.*impl\b' tests/ | grep -v 'phase_runner'
   grep -rn 'patch.object(impl\.phase_runner' tests/
   ```
2. **Create `_stage_context.py` first** — frozen dataclass with `impl` AND `runner`
   back-references and a `__post_init__` init-order assertion.
3. **Extract phases simplest-first** (Plan → PRCreate → Implement → FollowUp → Review),
   one per TDD cycle. For each: write the phase's per-class test file RED, lift the
   body from the runner into `_xxx_impl`, wire the runner shim, verify the whole
   suite stays green BEFORE moving on.
4. **Name-collision resolution**: if a phase class name collides with an existing
   enum value (e.g., `models.ReviewPhase` enum vs new `ReviewPhase` class), alias
   at the import site: `from .models import ReviewPhase as ReviewState`. Don't
   rename either type.
5. **Decompose C901-flagged methods structurally**. As you lift each body, split
   it into smaller helpers (`_iterate`, `_check_termination`, `_address`,
   `_warn_if_unresolved`) so each fragment has CC ≤ 8. Remove the `# noqa: C901`.
6. **Use `impl_module()` as a method, not a property.** A property triggering an
   import on attribute access violates POLA (readers don't expect side effects).
7. **Module imports stay at module scope.** Never defer imports inside lock-held
   regions — holding any lock while acquiring Python's import lock creates a
   deadlock risk.
8. **Filter chains must enumerate ALL required fields explicitly**, including
   Optional ones. If a downstream action needs `state.session_id` and `session_id`
   is `Optional[str]`, add `if not state.session_id: continue` BEFORE calling the
   action — defense-in-depth over "the filter probably caught it."
9. **Verification gates** (run after each phase extraction, not at the end):
   ```bash
   # exactly one public method per phase
   pixi run python -c "import inspect; from hephaestus.automation._review_phase \
     import ReviewPhase; print([n for n,_ in inspect.getmembers(ReviewPhase, \
     inspect.isfunction) if not n.startswith('_')])"
   # coordinator under 500 lines
   test "$(wc -l < hephaestus/automation/implementer_phase_runner.py)" -le 500
   # C901 noqa removed cleanly
   pixi run ruff check hephaestus/automation/ --select=C901
   ```
10. **"Implement or remove" is binary.** Never check in `raise NotImplementedError()`
    stubs reachable through runner shims. Either implement fully or delete the
    stub AND its runner shim in the same change. Half-completed extraction with
    stubs guarantees an unbounded review loop (every direct caller crashes; every
    `patch.object` test crashes; reviewers reopen the same threads each iteration).

**Pattern in code**:

```python
# implementer_phase_runner.py (the coordinator)
class ImplementationPhaseRunner:
    def __init__(self, impl):
        self.impl = impl
        self.ctx = StageContext(impl=impl, runner=self, state_mgr=impl.state_mgr, ...)
        self.review_phase = ReviewPhase(self.ctx)
        self.plan_phase   = PlanPhase(self.ctx)
        # ...

    # One-line shim — exists ONLY so patch.object(impl.phase_runner, "_fetch_plan_and_review") works
    def _fetch_plan_and_review(self, n):
        return self.review_phase._fetch_plan_and_review_impl(n)

    # Same for every patched name:
    def _run_impl_review_step(self, *a, **kw):
        return self.review_phase._run_impl_review_step_impl(*a, **kw)

# _review_phase.py
class ReviewPhase:
    def __init__(self, ctx): self.ctx = ctx

    def run(self, **kw) -> ReviewOutcome:        # SINGLE public entry point
        return self._iterate(**kw)

    def _iterate(self, **kw) -> ReviewOutcome:
        # CRITICAL: route through ctx.runner, not ctx.impl —
        # so patch.object(impl.phase_runner, "_fetch_plan_and_review") intercepts
        plan, review = self.ctx.runner._fetch_plan_and_review(kw["issue_number"])
        ...
        outcome = self.ctx.runner._run_impl_review_step(...)
        ...

    def _fetch_plan_and_review_impl(self, n):    # real body lifted from runner
        ...

    def _run_impl_review_step_impl(self, *a, **kw):
        ...
```

**The shim is NOT free — it's load-bearing.** Removing the shim breaks every
test that did `patch.object(impl.phase_runner, "_xxx")` AND every direct call
site like `implementer.phase_runner._xxx(...)`. Treat shims as part of the public
contract during the lifetime of those tests.

**Results & numbers (verified-local, ProjectHephaestus PR #998)**:

| Metric | Value |
|--------|-------|
| Source class (`ImplementationPhaseRunner`) | ~1,712 LoC, CC>15 in 4 methods |
| Phase modules created | 5 (Plan/Implement/Review/FollowUp/PRCreate) |
| Phase modules total LoC | ~1,150 (avg 230 per phase) |
| Reverse-delegation shims on the runner | ~30 one-line methods |
| Per-test mock count for new phase tests | 3–5 (vs 20+ for the original) |
| CC budget per extracted helper | ≤ 8 decision points |
| StageContext fields | `impl`, `runner`, plus already-wired collaborators |
| Init-order guard | `assert impl.state_mgr is not None` in `__post_init__` |

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
| **Using reverse-delegation for sibling-module cycles** | Applied Phase 11 (lazy `from . import implementer as _impl` in function bodies) to break cycle between `implementer_phase_runner` and `implementer` | Deferred imports inside function bodies mask the cycle from static analysis tools (AST-based linters, import-graph audits); regression tests need fragile AST ID-tracking to detect reintroduction | For sibling-module cycles (not parent→child), use Phase 12 (top-level imports with `# noqa: F401`) instead; static analysis visibility + simpler code is worth retargeting a few test patches |
| **Assuming the context manager refactor was complete** | Introduced `_inflight_context()` in `_handle_webhook` and opened the PR without auditing callers | `receive_webhook()` still did manual `self._inflight += 1 / -= 1`, double-incrementing; `test_inflight_increments_during_publish` saw `[2]` not `[1]` | A refactor that moves lifecycle into a context manager is INCOMPLETE until every caller is grepped and stale manual `+1/-1` is removed (Phase 15) |
| **Debugging a doubled counter only in the test file** | Searched the test for the assertion failure to find the root cause | The bug was in production code (`receive_webhook`), not the test | When counter values are unexpectedly doubled, grep production code for stale lifecycle management, not just tests |
| **Deny-list to scope a scanner** | Kept adding directories to `EXCLUDED_PREFIXES` to narrow a repo-wide scan | Deny-lists grow forever and break on every new top-level dir; root-level test fixtures also slipped through | Use a `Path.is_relative_to()` allow-list helper (Phase 14); it's smaller, correct-by-construction, and independently testable |
| **Forgetting fixture migration after scoping a scanner** | Scoped the scanner to `scylla/` but left existing tests writing fixtures at `tmp_path/"bad.py"` | Root-level fixtures are now out of scope — tests returned zero findings and failed | After narrowing scanner scope, move every test fixture into the scoped dir and update hard-coded path assertions (`"bad.py"` → `"scylla/bad.py"`) |
| **Trusting a TODO/audit LOC estimate without reading the substrate** | Took `TODO.md` "Phase 2: ~5000 LOC" and an audit's "CRITICAL: autograd missing" as authoritative effort | Existing tape/registry/SavedTensors infra already covered ~70%; estimate was 3-5x too high and conflated "documented" with "missing" | Read every substrate file in full with line-cited evidence BEFORE estimating (Phase 17); re-classify "missing" as "incomplete, N% gap" |
| **Deleting legacy code before verifying zero callers** | Assumed a "fallback only" file was dead and considered deleting it on the strength of its header alone | "Fallback only" claims are not self-enforcing — the codebase may still depend on it in non-obvious ways; dead code passes all CI | Systematically grep all callers across `*.py/*.sh/*.md/.github/` first, rewrite stale back-references as self-contained comments, then delete and run full suites (Phase 16) |
| **Single back-reference (only `impl`) in StageContext** | Initial Phase 19 design held only `impl`; phases dispatched via `self.ctx.impl._xxx(...)` | `patch.object(impl.phase_runner, "_xxx")` patches the runner shim, but phases called through `impl._xxx` which forwards via the *real* coordinator — the patch on the runner never intercepted; ~6 tests silently passed `Mock not called` | `StageContext` MUST carry BOTH `impl` AND `runner`; phases call back via `self.ctx.runner._xxx(...)` so the lookup site stays on the patched object (Phase 19) |
| **Naive symbol move without keeping runner shims** | Moved `_fetch_plan_and_review` into the phase class and deleted it from the runner | Six direct `patch.object(implementer.phase_runner, "_fetch_plan_and_review")` sites AND two direct call sites (`implementer.phase_runner._fetch_plan_and_review(1)`) broke with `AttributeError` | Keep every patched method as a one-line shim on the original class for the lifetime of the tests; phases own the implementation in `_xxx_impl` (Phase 19) |
| **Checking in `raise NotImplementedError()` stubs** | Created `_run_impl_review_impl`, `_run_impl_review_step_impl`, `_run_address_review_step_impl`, `_resume_impl_with_feedback_impl` as bare stubs to mark unfinished extraction | PR review surfaced 21 review threads (12 reopens) because runner shims delegated directly to the stubs — every direct caller and `patch.object(phase_runner, "_xxx")` test crashed; reviewers will not accept "architectural placeholder" framing | Never check in `raise NotImplementedError()` stubs reachable through runner shims. Either implement fully or delete both the stub AND its runner shim in the same commit (Phase 19) |
| **Keeping the original 1,712-LoC body AND adding shims** | Appended ~130 lines of shims + 5 phase classes without removing any original orchestration logic | Coordinator file grew to ~1,840 LoC, blowing past the AC ≤500 LoC target; `# noqa: C901` waivers stayed because original methods stayed | Phase-strategy extraction is a MOVE, not an additive ADD. Each phase's `_xxx_impl` MUST contain the real body lifted from the runner; check `wc -l < 500` after each phase, not at the end (Phase 19) |
| **Reverse-delegation contract break inside the phase** | `ReviewPhase._iterate` called `self.ctx.impl._run_impl_review_step(...)` instead of `self.ctx.runner._run_impl_review_step(...)` | `patch.object(impl.phase_runner, "_run_impl_review_step")` no longer intercepted — the phase routed through `impl`, which forwards but doesn't re-enter the patched shim | When inside a phase, ALWAYS dispatch through `self.ctx.runner._xxx(...)` for any method tests patch on the runner. Reserve `self.ctx.impl._xxx` for the small set tests pin directly on the implementer (Phase 19) |
| **`hasattr(self, 'plan_phase')` guard with `__import__` fallback in `impl_module()`** | Defensive coding for "called before `__init__` completes" scenarios | Reviewer flagged POLA: "hidden import-fallback path is astonishing to callers; pick one — either remove the guard, or document the scenario it protects against" | Either commit to one path with a `__post_init__` assertion enforcing the invariant, or document the actual failure mode. Defensive `hasattr` checks without a real failure scenario create a dead branch readers must reason about (Phase 19) |
| **Module import deferred inside `with state_lock` block** | Kept `from .models import ImplementationPhase` inside `with self.ctx.state_lock:` at the top of `PRCreatePhase.ensure` to "minimize import surface" | Holding `state_lock` while acquiring Python's global import lock creates a deadlock risk against any other thread holding the import lock while waiting on `state_lock` | Module imports MUST be at module scope. Never defer imports inside lock-held regions (Phase 19) |
| **Filter chain missed None case for an Optional field** | `rerun_failed_learns` filtered `state.phase != COMPLETED or state.learn_completed or not session_agent_matches(...)`, then called `run_learn(state.session_id, ...)` without a None guard | The filter didn't exclude states with `session_id is None`; downstream `run_learn` either crashed or silently no-op'd | When a filter chain decides "process this row", enumerate ALL required fields, including Optionals. Add `if not state.session_id: continue` BEFORE the action — defense-in-depth over filter trust (Phase 19) |
| **Shared mutable dict write-back lost after extraction** | Planned to move `_discover_prs` (writes `self.shared_pr_issues`) to `PRDiscovery` and `_arm_drive_green` (reads `self.shared_pr_issues`) to `PostMergeProcessor` without a write-back contract | After extraction the dict lives nowhere both collaborators can see; `_arm_drive_green` silently gets an empty dict and post-merge arming fan-out (#840 behavior) breaks | Inject `shared_pr_issues_setter: Callable[[dict], None]` into the writing collaborator and `shared_pr_issues_provider: Callable[[], dict]` into the reading collaborator; both lambdas close over the *parent's* dict at call-time. Setter must use `.clear() + .update()` (not `=`) to preserve dict object identity so the provider always returns the same live object (Phase 20) |
| **`_viewer_login` cache claimed to live in two places** | Plan stated cache "stays on CIDriver" AND said "keep `self._viewer_login` as instance attribute on `PRDiscovery`" simultaneously | Two separate caches diverge: test fixture pre-seeds `driver._viewer_login = "mvillmow"` but the collaborator reads its own `PRDiscovery._viewer_login` — fixture is bypassed and tests break silently while the "no test changes" claim is wrong | Pick ONE source of truth: move the cache entirely to the collaborator (`PRDiscovery._viewer_login`), update the one test fixture line accordingly, and let the CIDriver delegation stub route through the collaborator (Phase 20) |
| **Method assigned to wrong collaborator by name inference** | Assigned `_tracked_worktree_changes` to `CICheckInspector` because the name sounds like inspection | Only call site is inside `_retry_no_commit_once` (a `CIFixOrchestrator` method, line 2343); its dependency `_git_stdout_for_push_guard` is also in `CIFixOrchestrator` — cross-collaborator coupling undeclared in plan | Always grep ALL call sites (`grep -n "_method_name"`) and read the method's dependency chain before assigning to a collaborator; assign to where both the caller and the callee's dependencies live (Phase 20) |

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
pipeline-step extraction (llm_judge): 28 new tests; 4,591 pass; 3 # noqa: C901 removed
scanner-scoping (check_docstring_fragments): 12 scope tests; 4,333 pass
context-manager double-counter (Hermes): test went [2]→[1] after dropping stale +1/-1
legacy-code deletion: 587-LOC bash driver + 480 LOC tests removed; 1,093 + 26 tests pass
substrate-read estimate (Odyssey #5457): TODO ~5000 LOC → revised ~1400 → actual +937
```

### Pipeline-step return-tuple contract (Phase 13)

```text
(passed: bool, na: bool, output: str)
  na=True  → tool not installed (step skipped)
  passed=False, na=False → step ran and failed (output has stderr)
  passed=True  → step succeeded
```

### Substrate-read checklist before estimating (Phase 17)

```markdown
## Phase 0 — Substrate Read (complete BEFORE estimating)
Files read in full: path/to/substrate.ext (N LOC) — what works: …
What already works (with line citations): substrate.ext:123 — feature A
What is actually missing (min signatures only): op_foo(x) -> y — not implemented
Revised LOC estimate: ~X (vs TODO "~Y"); justification: ~Z% already in substrate.
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
| ProjectHephaestus | PR #714 — `implementer_phase_runner.py` breaks cycle with top-level symbol extraction; 9 patchable symbols extracted; 3 deferred imports removed; regression test added (test_implementer_no_cycle.py with AST guards); all automation tests pass; CI gates pass (verified-ci) | Top-level symbol extraction for sibling-module cycles (Phase 12); comparison with reverse-delegation approach |
| ProjectScylla | PR #1457 (Issue #1430) — three `llm_judge.py` functions CC>15→CC≤8 via pipeline-step extraction; 3 `# noqa: C901` removed; 28 new tests; 4591 tests pass | Superseded `pipeline-step-extraction` (Phase 13) |
| ProjectScylla | PR #1440 (Issue #1399) — docstring-fragment scanner scoped to `scylla/` via `_is_scylla_file()` allow-list; 12 scope tests; 4333 tests pass | Superseded `scope-scanner-to-subdirectory` (Phase 14) |
| ProjectHermes | PR #522 — `receive_webhook()` double-incremented `_inflight` after `_handle_webhook` adopted `_inflight_context()`; test expected `[1]` got `[2]`; fix removed stale manual counter management | Superseded `refactor-context-manager-double-counter-stale-caller` (Phase 15) |
| ProjectHephaestus | PR #745 — deleted 587-line legacy `run_automation_loop.sh` + helper + 480 lines of tests; scrubbed 8 stale back-references across 4 files; 1093 tests + 26 shell tests pass | Superseded `legacy-code-deletion-safe-removal-pattern` (Phase 16) |
| ProjectOdyssey | PR #5457 — Phase 0 substrate read revised a TODO "~5000 LOC" estimate to ~1400; actual landed +937 LOC (CI green) | Superseded `architecture-estimate-rewrite-read-substrate-first` (Phase 17) |
| HomericIntelligence ecosystem | Cleanup-phase coordination after parallel Test/Implementation/Package phases (KISS/DRY/SOLID finalization before merge) | Superseded `phase-cleanup` (Phase 18) |
| ProjectHephaestus | PR #998 (issue #712) — `IssueImplementer`/`ImplementationPhaseRunner` decomposition into 5 named phase modules (Plan/Implement/Review/FollowUp/PRCreate) with `_stage_context.StageContext` carrying both `impl` and `runner`; ~30 reverse-delegation shims preserve `patch.object(impl, ...)` AND `patch.object(impl.phase_runner, ...)` contracts; verified-local (test suite green; review iterations identified the dual-back-reference fix and the "no NotImplementedError stubs" rule) | Phase 19: Phase-Strategy with Dual-Back-Reference StageContext |
