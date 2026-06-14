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
  (13) planning god-class decomposition — state ownership migration, cross-call
  coupling when only some methods are extracted, delegation stub type loss, constant
  re-export breakage, and test_omit_allowlist.py CI traps,
  (14) extracting a provider-conditional dispatch (two-branch if/else over a bool
  predicate) into a private helper method — choosing a method over a Protocol/Strategy
  when there are exactly two branches, unifying heterogeneous return types at the
  extraction boundary (e.g. AgentRunResult → subprocess.CompletedProcess), wrapping
  BOTH codex calls in try/except CalledProcessError, and verifying all exception contracts
  before documenting which exceptions propagate out of the wrapper,
  (15) planning god-function decomposition (functions > 80L that are oversized per project
  threshold) — arithmetic chain verification per target, docstring budget counting, for-loop
  body sizing (extract if > 40L), return type tracing when a helper absorbs the only call
  site to a data-fetching function, N-tuple completeness for orchestrator helpers, explicit
  parameter audit for captured variables, approach-table completeness (ALL helpers listed),
  and AST-measure-before-planning discipline to avoid stale line numbers,
  (16) god-class delegation pattern planning: shared mutable dict write-back when a discovered
  method moves to a collaborator, methods called by multiple collaborators (assign to host not
  one collaborator), test fixture pre-seeding of cache attributes after extraction (pre-seeding
  driver._cache doesn't affect collaborator._cache), reading method bodies before assigning
  them to collaborators (name-only assignment is insufficient), and verifying __init__.py
  export conditionality before planning conditional export steps,
  (17) executing a god-class decomposition using narrow-callable injection (DIP) — lambda
  wrapping injected callables so patch.object remains effective after extraction, updating
  attribute access in sibling test files after cache migration, updating companions tuples in
  phase-wiring tests when AGENT_* constants move to extracted modules, and patching each
  module's imported run separately when a method chain splits across module boundaries,
  (18) post-extraction DRY and constructor-injection refinement — thin delegation stubs on
  the original class preserve patch.object targets without requiring test edits, __setattr__
  override propagates test-time attribute changes (e.g. state_dir) to collaborators,
  .clear()/.update() preserves shared mutable dict identity so host and collaborator share
  the same object, circular import trap when a utility function imported by a sibling module
  must stay in the original file (define a local copy in the collaborator instead), and
  from __future__ import annotations required in collaborator modules using PEP 604 union types,
  (19) verifying keyword-only method signatures (`*` separator in def line) before writing
  delegation stubs — fabricated positional signatures for keyword-only methods raise TypeError
  at runtime and pass AST name-presence checks silently,
  (20) mapping `_gh_call` patch sites to destination modules via test-class bucket analysis
  when splitting a symbol across 4+ modules — range-grep spot-checks miss sites, class-boundary
  bucketing is the only reliable approach for multi-module splits,
  (21) tracing delegation chains through sub-modules before adding _gh_call patches to a
  migration table — if the existing test already patches a sub-module (e.g. _review_utils._gh_call),
  the patch does not need to move regardless of where the method moves,
  (22) verifying return types of delegation stubs by source-reading the full `def` line
  including the `->` annotation — a stub that lies about its return type fails mypy in the
  host file (not in the collaborator modules) and is invisible to Criterion 9 unless the host
  file is also in the mypy target list,
  (23) confirming whether `acquired_slot` is a real parameter of three specific methods
  (`_recheck_and_arm_after_fix`, `_resolve_dirty_pr`, `_attempt_ci_fixes`) — all three DO
  have `acquired_slot` as a positional parameter with a default on `_attempt_ci_fixes`,
  (24) verifying keyword-only parameter lists for methods that use `*` as a positional
  separator when writing delegation stubs — both the stub def AND the forwarding call must
  use keyword syntax; fabricated positional params and fabricated keyword-only params are
  symmetric failure modes of the same root cause (not reading the actual `def` line),
  (25) recognizing that fabricated method parameters are the #1 planning failure mode across
  multiple consecutive review rounds — the only reliable prevention is running `sed -n` or
  Read on the exact line range for every method before writing any stub, never describing
  signatures from memory, naming similarity, or expected behavior,
  (26) discriminating between methods that take `acquired_slot` and methods that do not by
  their conceptual role: methods that acquire a semaphore slot (rebase/resolve/fix workers)
  have `acquired_slot`; methods that are sub-steps executed INSIDE an already-acquired slot
  do not.
category: architecture
date: 2026-06-13
version: "1.13.0"
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
  - god-class
  - state-ownership
  - cross-call-coupling
  - constant-re-export
  - coverage-omit-allowlist
  - provider-dispatch
  - return-type-unification
  - agentrunresult
  - completedprocess
  - boolean-predicate-dispatch
  - mock-side-effect-exhaustion
  - stopiteration-exception-boundary
  - returncode-guard
  - noqa-c901-removal-verification
  - lambda-injection
  - dip-narrow-callable
  - patch-object-compatibility
  - sibling-test-attribute-access
  - companions-tuple
  - cross-module-patching
  - keyword-only-signature
  - gh-call-patch-migration
  - test-class-bucket-analysis
  - delegation-chain-pre-check
  - review-utils-delegation
  - return-type-verification
  - stub-return-type-drift
  - mypy-host-file-target
  - acquired-slot-positional
  - keyword-only-forwarding-call
  - fabricated-params-failure-mode
  - acquired-slot-mnemonic
  - r7-planning-session
---

# Python Module Decomposition and Refactor Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Decompose oversized Python modules/classes/functions into focused, independently testable units using SRP, TDD, and DRY principles |
| **Outcome** | Synthesized from 15+ verified skills; covers function-level extraction, class-based extraction, circular import fixes, immutability refactoring, extensibility-driven decomposition, CLI entry-point extraction with preserved patch routing, top-level symbol extraction to break sibling module cycles, CC>15 pipeline-step extraction, scanner-to-subdirectory scoping, context-manager double-counter fixes, safe legacy-code deletion, substrate-read-before-estimate discipline, post-parallel phase cleanup, god-class decomposition planning risks (state ownership, cross-call coupling, constant re-export, delegation stub type loss, coverage omit-allowlist traps, shared mutable dict write-back, methods shared across multiple collaborators, test fixture pre-seeding after cache extraction, method body read before assignment, __init__.py export conditionality verification), exception-contract verification before documenting wrapper behavior, three Phase 20 implementation-time traps (exception-boundary removal unmasks StopIteration from exhausted side_effect mocks; returncode-guard obligation at every call site of an absorbed-exception helper; agent mock type determines downstream subprocess.run consumption), god-function decomposition planning rules (arithmetic chain verification, docstring budget, for-loop body sizing, return type tracing, N-tuple completeness, captured variable audit, approach table completeness, AST-measure discipline), god-class narrow-callable DIP execution (lambda wrapping for patch.object compatibility, cross-module import patching when method chains split, sibling test attribute path updates after cache migration, companions tuple updates in phase-wiring tests), post-extraction DRY and constructor-injection refinement (thin delegation stubs, __setattr__ propagation, .clear()/.update() dict identity, circular import avoidance via local copies, from __future__ import annotations in collaborators), keyword-only method signature verification before writing stubs (fabricated positional signatures pass AST checks silently but raise TypeError at runtime), `_gh_call` multi-module split attribution via test-class boundary bucketing (range-grep spot-checks are insufficient for 4+ destination modules; class-boundary bucket analysis is required), delegation-chain pre-check before adding `_gh_call` patches to migration tables (if existing test patches a sub-module like `_review_utils._gh_call`, that patch does not move regardless of where the method relocates), return-type verification for delegation stubs (both parameters AND return types must be source-read; a stub with a wrong return type fails mypy in the host file not the collaborator modules, and is invisible unless the host file is in the mypy target list), acquired_slot parameter confirmation (three specific methods — _recheck_and_arm_after_fix, `_resolve_dirty_pr`, `_attempt_ci_fixes` — all have acquired_slot as a real positional parameter), keyword-only forwarding call verification for methods like _mark_drive_green_learn_result (stub def must include `*` AND forwarding call must use `param=value` keyword syntax), fabricated-param prevention protocol (in 3 consecutive rounds R4/R5/R6 the #1 rejection cause was fabricated signatures — use `sed -n` on the exact line range before writing any stub; never write "confirmed from source" without running the command), and acquired_slot vs no-acquired_slot slot-ownership mnemonic (methods that ACQUIRE a semaphore slot have the param; sub-steps executing INSIDE an acquired slot do not) |
| **Trigger** | Files >800 lines, circular import errors, mixed-concern methods, C901/CC>15 complexity, extensibility requirements, CLI main() extraction, deferred imports inside function bodies preventing static analysis, broad scanners needing subdirectory scope, stale callers after context-manager refactors, dead fallback files, pessimistic refactor estimates, technical debt after parallel phases, planning a multi-collaborator god-class decomposition, extracting a two-branch provider-conditional dispatch with heterogeneous return types, documenting exception contracts for wrapper methods, planning god-function decomposition (individual functions > 80L), planning delegation-stub extraction where extracted methods populate shared dicts or caches read by the host class, executing a god-class decomposition using narrow-callable injection (DIP) where bare bound-method references to injected callables break patch.object, applying post-extraction DRY cleanup and constructor-injection refinement (delegation stubs, __setattr__ propagation, dict identity preservation), writing delegation stubs for methods with keyword-only parameters (`*` separator), planning migration of a symbol patched in 10+ test sites across multiple test classes when the symbol will move to 4+ destination modules, verifying whether an existing test's _gh_call patch already targets a sub-module (making migration unnecessary for that test), source-reading the `->` return annotation for every delegation stub (wrong return types fail mypy in the host file and are invisible if the host file is not in the mypy target list), confirming positional vs keyword-only status of parameters for methods before finalizing stub signatures, verifying the forwarding call uses `param=value` syntax for every keyword-only parameter, applying the fabricated-param prevention protocol (run `sed -n` on each def line range before writing any stub), or distinguishing slot-worker methods (have `acquired_slot`) from sub-step methods (do not) |

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
- You are **planning a god-class decomposition** (3,000+ lines, 40+ methods, multiple collaborator targets) and need to reason about state ownership migration, cross-call coupling, delegation stub typing, constant re-export risks, and CI omit-allowlist traps before writing any code
- A function contains a **two-branch if/else over a boolean predicate** (e.g., `is_codex(agent)`) where each branch invokes a different external agent/subprocess API returning heterogeneous types, and you want to extract it into a unified private helper method without introducing a Protocol/Strategy class
- You are **planning god-function decomposition** — individual functions exceeding the project's line-length threshold (e.g., > 80L) and need arithmetic chain verification, docstring budget accounting, for-loop body sizing, return type tracing for absorbed call sites, N-tuple completeness for orchestrator helpers, captured variable auditing, and approach-table completeness before writing any code
- You are **planning god-class delegation extraction** where methods being moved to a collaborator populate shared mutable state (dicts, caches) that the host class reads elsewhere, where a method is used by multiple collaborator groups (assign to host, not one group), or where test fixtures pre-seed cache attributes on the host that will no longer be in scope after extraction
- You are **executing a god-class decomposition with narrow-callable injection (DIP)** and need to wire collaborators using injected callables — including: using lambda wrapping (not bare method references) to preserve patch.object effectiveness, updating sibling test files that directly access attributes now living on a collaborator, updating companions tuples in phase-wiring tests when AGENT_* constants move to extracted modules, and patching each module's `run` import independently when a pre/post-agent SHA read splits across module boundaries
- A class's **sibling test files access internal attributes directly** (e.g., `driver._viewer_login`) that will move to an extracted collaborator — grep test files before and after extraction to update attribute paths
- You are **refining a completed extraction** (DRY pass / constructor-injection cleanup) and need to add thin delegation stubs to preserve test `patch.object` targets, wire a `__setattr__` override to propagate test-time attribute changes to collaborators, use `.clear()/.update()` to preserve shared mutable dict object identity, detect circular import traps for utility functions imported by sibling modules, or add `from __future__ import annotations` to collaborator files that use PEP 604 union types
- A method being extracted has a **`*` (keyword-only) separator** in its `def` line — the stub def must also use `*`, and the forwarding call must use `keyword=value` for every param; AST name-presence checks pass even for wrong-signature stubs
- A shared symbol (e.g., `_gh_call`) is **patched in 10+ test sites across one file** and will move to **4+ destination modules** — use test-class boundary bucketing (grep `^class` start lines, bucket each patch line) rather than range-grep spot-checks to attribute every patch site to its destination
- An extracted method's **existing test already patches a sub-module** (e.g., `_review_utils._gh_call`) — verify the patch string before adding the site to the migration table; if the patch already targets the sub-module, it does not need to move regardless of where the method relocates
- Writing **delegation stubs** for a set of methods — source-read the `->` return annotation for EVERY stub, not just parameter types; a stub with an incorrect return type (e.g., `-> bool` when the real method returns `WorkerResult | None`) fails mypy in the host file, not in the collaborator modules, and is invisible unless the host file is included in the mypy target list
- Confirming whether **`acquired_slot`** (or any other parameter) is a real parameter of a target method — read the actual `def` line; fabrication risk runs both ways (parameters may exist OR be absent); the three methods `_recheck_and_arm_after_fix`, `_resolve_dirty_pr`, `_attempt_ci_fixes` all DO have `acquired_slot` as a positional parameter
- Writing a delegation stub for a method with **keyword-only params that also appear after `*` in the source** — the stub def must include `*`, the forwarding call must use `keyword=value`; missing the keyword syntax in the forwarding call raises `TypeError` even when the stub def is correct (Phase 30)
- Planning has **failed due to fabricated signatures in three or more consecutive review rounds** — activate the fabricated-param prevention protocol: `sed -n '<start>,<end>p'` for every `def` line before writing any stub; do not write "confirmed from source" without running the command (Phase 31)
- Determining whether a method should receive **`acquired_slot` as a parameter** — use the slot-ownership mnemonic: methods that ACQUIRE a semaphore slot (rebase/resolve/fix workers) have the param; methods that execute AS A SUB-STEP already inside an acquired slot do not (Phase 32)

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
  Planning god-class decomposition      → Planning risk audit (Phase 19)
  Two-branch bool-predicate dispatch    → Provider-dispatch extraction (Phase 20)
  Planning god-function decomposition   → Function-size planning rules (Phase 21)
  God-class delegation w/ shared state → Shared-state write-back rules (Phase 22)
  God-class execution w/ DIP injection → Narrow-callable injection rules (Phase 23)
  Post-extraction DRY / constructor pass → Delegation stub + setattr refinement (Phase 24)
  Keyword-only method stub writing      → Verify `*` in def line before any stub (Phase 25)
  _gh_call split to 4+ modules          → Test-class bucket analysis (Phase 26)
  _gh_call patch already sub-module?   → Delegation chain pre-check (Phase 27)
  Stub return types unverified          → Return-type source-read rule (Phase 28)
  acquired_slot existence uncertain     → Parameter confirmation check (Phase 29)
  Keyword-only forwarding call wrong    → _mark_drive_green_learn_result pattern (Phase 30)
  Fabricated params in consecutive runs → Fabricated-param prevention protocol (Phase 31)
  acquired_slot vs no acquired_slot     → Slot-ownership mnemonic (Phase 32)

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

**Lambda wrapping for test compatibility** (critical when using class-based extraction with `patch.object`):

When injecting host methods into a collaborator, ALWAYS use lambdas, never bare method references:

```python
# WRONG — stored reference captured at init time; patch.object bypassed:
self._fix_orchestrator = CIFixOrchestrator(
    head_advanced=self._head_advanced,  # captured at init, patch won't intercept
)

# RIGHT — lambda re-evaluates self._head_advanced at call time:
self._fix_orchestrator = CIFixOrchestrator(
    head_advanced=lambda *a, **k: self._head_advanced(*a, **k),  # patch works
)
```

This applies to ALL injected callables, not just the "interesting" ones. A bare bound method
is effectively a snapshot; a lambda is a live lookup. `patch.object(driver, "_head_advanced")`
replaces `driver._head_advanced` on the object — the lambda re-reads it at call time while the
bare reference does not.

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

Also update attribute access in tests — when an instance attribute migrates to a collaborator,
sibling test files that access it directly on the host will break with a mypy error or
`AttributeError`:

```python
# After moving self._viewer_login from CIDriver to PRDiscovery:
# WRONG: driver._viewer_login = ""
# RIGHT: driver._pr_discovery._viewer_login = ""
```

Grep all test files for `driver.<attr>` (or `<host_instance>.<moved_attr>`) before and after
every attribute migration. mypy strict mode surfaces these as `"CIDriver" has no attribute
"_viewer_login"` — 6 such errors across test files are typical for a single cache attribute move.

Also update `companions` tuples in phase-wiring tests — when an `AGENT_*` constant moves from
the host module to an extracted collaborator, the test that verifies the import source must add
the collaborator filename to the `companions` tuple:

```python
# test_phase_agent_wiring.py — BEFORE extraction:
("ci_driver.py", "AGENT_CI_DRIVER", ())

# AFTER constant moves to ci_fix_orchestrator.py:
("ci_driver.py", "AGENT_CI_DRIVER", ("ci_fix_orchestrator.py",))
```

The `companions` tuple lists extra files the test scans in addition to the primary module;
an empty tuple means only the primary module is checked.

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

### Phase 19: God-Class Decomposition — Planning Risk Audit

Use when a class exceeds ~3,000 lines and 40+ methods, and you are designing a plan to
extract multiple collaborator classes in one or more PRs. Apply this phase BEFORE writing
any extraction code to catch the six most common planning-time errors.

**Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

#### Step 0: Read the actual substrate files — never trust issue LOC estimates

Issue bodies and audit reports regularly state stale line counts. A prior decomposition
PR (e.g., a method cluster already extracted in a previous PR) may have cut the target
by 30–50% without the issue being updated.

```bash
wc -l <target_file>.py          # authoritative line count
git log --oneline --follow -- <target_file>.py | head -20  # prior decomposition PRs
```

If the file is significantly shorter than the issue body claims, re-scope the plan
to avoid planning unnecessary work. **Always record the actual measured line count
in your plan, not the estimate from the audit.**

#### Step 1: Audit state ownership before proposing extraction boundaries

For every class field referenced by the candidate method group:

```bash
# Find all attribute reads/writes in the file
grep -n "self\.<field_name>" <target_file>.py
```

A field that is **read and written exclusively by the extracted methods** must **migrate**
with those methods to the new collaborator class. If the field stays on the original class
but the collaborator writes to it, you create a split-ownership bug:

```python
# WRONG — field stays on original, collaborator mutates it
class PRDiscovery:
    def __init__(self, driver: CIDriver):
        self._driver = driver   # writes to driver._viewer_login — split ownership

# RIGHT — field migrates to the collaborator
class PRDiscovery:
    def __init__(self):
        self._viewer_login: str | None = None  # owned here, where it's used
```

**Ownership checklist per candidate field:**

| Question | Answer → Action |
|----------|----------------|
| Is the field written ONLY by extracted methods? | Yes → migrate the field |
| Is the field read by both original and extracted methods? | Yes → keep on original, pass as parameter |
| Is the field the cache for a method that's being extracted? | Yes → migrate both |

#### Step 2: Map cross-call coupling before finalizing extraction boundaries

When you extract a method group (e.g., `CIFixOrchestrator`), grep for every method
called BY that group across the whole target file:

```bash
grep -n "self\._<method>" <target_file>.py | grep -v "def _<method>"
```

For each call that lands in a method NOT being extracted:

- Option A: Move the called method too (cleanest)
- Option B: Pass it as a callback/dependency in `__init__`
- Option C: Accept the coupling temporarily and document it with a `# TODO: decouple`

Cross-call coupling defeats the SRP purpose of extraction unless resolved. The highest-risk
coupling is when extracted methods need worktree/push-guard helpers that weren't extracted
with them — the extracted class ends up calling `self._driver._push_changes()` and is
tightly coupled to the original class's internals.

#### Step 3: Verify mypy config before proposing delegation stubs

Before proposing `*args, **kwargs` delegation stubs with `# noqa: ANN002,ANN003`:

```bash
grep -n "strict" pyproject.toml mypy.ini .mypy.ini setup.cfg 2>/dev/null
grep -rn "\[mypy-.*automation" pyproject.toml mypy.ini .mypy.ini 2>/dev/null
```

If `strict = true` and no per-module override exists for the automation package,
typed stubs are required. Propose typed stubs that mirror the exact signature of the
collaborator method, not `*args, **kwargs`:

```python
# AVOID — loses type info under strict mypy
def run_ci_fix_session(self, *args: Any, **kwargs: Any) -> ...:  # noqa: ANN002,ANN003
    return self._orchestrator.run_ci_fix_session(*args, **kwargs)

# PREFER — preserves type info
def run_ci_fix_session(self, session_config: CIFixConfig, timeout: int = 300) -> CIFixResult:
    return self._orchestrator.run_ci_fix_session(session_config, timeout)
```

#### Step 4: Grep external callers before moving constants or module-level symbols

Before proposing to move a constant (e.g., `FAILING_CHECK_CONCLUSIONS`) to a new module:

```bash
grep -rn "from hephaestus.automation.ci_driver import FAILING_CHECK_CONCLUSIONS" .
grep -rn "ci_driver.FAILING_CHECK_CONCLUSIONS" .
grep -rn "FAILING_CHECK_CONCLUSIONS" . --include="*.py" | grep -v "ci_driver.py"
```

If external callers exist, **do not move the constant**. Instead:
- Keep it in the original location and import it from there in the new module
- OR export it from both (`from ci_driver import FAILING_CHECK_CONCLUSIONS as FAILING_CHECK_CONCLUSIONS`
  in the new module), using the explicit `as X` form for mypy compliance

Moving a constant without re-exporting it is a silent breaking change — external callers
get an `ImportError` that CI may not catch until integration tests run.

#### Step 5: Calculate delegation stub overhead in line count projections

Plan estimates frequently undercount lines because they ignore delegation stubs.
Every delegated method in the original class adds ~5 lines (docstring + signature + body):

```python
def run_ci_fix_session(
    self, session_config: CIFixConfig, timeout: int = 300,
) -> CIFixResult:
    """Delegate to CIFixOrchestrator."""
    return self._orchestrator.run_ci_fix_session(session_config, timeout)
```

**Formula for projected final line count:**

```text
projected = original_lines
          - extracted_method_lines        # removed from original
          + delegation_stub_lines         # added (≈ 5 × num_extracted_methods)
          + new_import_lines              # ≈ 4–8 per new module
```

If your extraction target is ≤N lines, verify the projection satisfies it:

```text
e.g., 3,338 lines - 1,200 extracted + (18 methods × 5 stubs) + (4 modules × 6 imports)
    = 3,338 - 1,200 + 90 + 24 = 2,252 lines  →  tight against a ≤2,200 target
```

Adjust extraction boundaries if the projection is within 10% of the threshold.

#### Step 6: Check test_omit_allowlist.py before adding new modules

When a new module will be added to the `hephaestus/automation/` package:

```bash
find tests/ -name "test_omit_allowlist.py" -o -name "*omit*" 2>/dev/null
grep -rn "omit" pyproject.toml | grep -i "coverage\|omit"
```

If `test_omit_allowlist.py` exists, every new module in the omit-guarded package must be:
1. Added to the `[tool.coverage.report]` omit list in `pyproject.toml`
2. Added to the allowlist assertion in `test_omit_allowlist.py`

Missing this step causes CI failures on `test_omit_allowlist.py` even when all other
tests pass. Include the allowlist update in the same PR as the new module — never split it.

#### Planning Risk Audit Checklist

```markdown
## God-Class Decomposition Planning Checklist (Phase 19)

### Pre-plan (do before writing the plan)
- [ ] Read actual file: `wc -l <file>.py` = N lines (not the audit estimate)
- [ ] Check git log for prior decomposition PRs that may have already reduced the file
- [ ] Identify all class fields; for each field used by extraction candidates, determine
      ownership (migrate vs. keep vs. parameter)

### Per extraction boundary
- [ ] Grep for cross-call coupling: what methods in original does the extracted group call?
- [ ] Decision for each cross-call: move together | callback | accept + TODO

### Before proposing stubs
- [ ] Check mypy strict setting + per-module overrides
- [ ] If strict: propose typed stubs, not `*args, **kwargs`

### Before moving constants/exports
- [ ] Grep external callers for every constant/symbol proposed to move
- [ ] If callers exist: keep in place or re-export with explicit `as X` alias

### Line count projection
- [ ] Compute: original - extracted + (stubs × 5) + (new imports × 6) ≤ target?

### CI trap check
- [ ] Does `tests/unit/test_omit_allowlist.py` exist?
- [ ] If yes: plan includes pyproject.toml omit update + test file update in same PR
```

### Phase 20: Provider-Conditional Dispatch Extraction — Two-Branch Bool-Predicate Pattern

Use when a function or method contains a **two-branch `if/else` over a boolean predicate**
(e.g., `is_codex(self.options.agent)`) where each branch calls a different external agent
or subprocess API that returns **heterogeneous types**, and the branching logic is threaded
through an oversized function.

**Decision: method vs. Protocol/Strategy**

| Signal | Decision |
| ------- | ---------- |
| Exactly two branches over a scalar bool | Private helper method (not a Protocol) |
| More than two providers likely in the future | Protocol/Strategy class |
| Both branches accept identical inputs | Method (no dispatch object needed) |
| Branches already tested through existing mocks | Method (tests need no edits) |

A Protocol is over-engineering for exactly two branches tested via existing mocks. The
extract boundary is the only place that knows about the type difference.

**Return-type unification at the extraction boundary**

When the two branches return different types (e.g., `AgentRunResult` for codex vs. an
implicit `None` success for claude), wrap to a common type at the boundary.

**CRITICAL: read the wrapped function's exception contract FIRST.** `run_codex_session`
raises `subprocess.CalledProcessError` on non-zero exit (verified: runtime.py:397–403) and
`subprocess.TimeoutExpired` on timeout. `AgentRunResult` has fields `stdout`, `stderr`,
`session_id` — NO `returncode` field (verified: runtime.py:28–34). This changes the pattern:
both codex calls (fresh and resume) must be wrapped, and `CompletedProcess(returncode=0)` on
the success path is synthetic (only reachable if no exception was raised):

```python
def _invoke_agent_session(
    self,
    session_id: str,
    prompt: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Invoke codex or claude agent; return unified CompletedProcess.

    CalledProcessError from codex is absorbed into returncode.
    TimeoutExpired is the only exception that propagates to callers.
    """
    if is_codex(self.options.agent):
        try:
            result: AgentRunResult = run_codex_session(session_id, prompt, timeout=timeout)
            # returncode=0 is synthetic — only reachable if run_codex_session did not raise
            return subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout=result.stdout or "", stderr=result.stderr or "",
            )
        except subprocess.CalledProcessError as exc:
            return subprocess.CompletedProcess(
                args=[], returncode=exc.returncode, stdout="", stderr="",
            )
        # TimeoutExpired propagates intentionally
    else:
        invoke_claude_with_session(session_id, prompt, timeout=timeout)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
```

**Critical: `CalledProcessError` absorption**

`run_codex_session` DOES raise `CalledProcessError` on non-zero exit — this is verified
behavior, not an assumption. Absorb it into the return code INSIDE the helper — never let
it escape, because callers now treat non-zero returncode as the sole error signal. Wrap
ALL codex calls (both fresh and resume) in `try/except CalledProcessError`:

```python
try:
    result = run_codex_session(session_id, prompt, timeout=timeout)
    return subprocess.CompletedProcess(args=[], returncode=0, ...)
    # returncode=0 synthetic: CalledProcessError would have been raised before this line
except subprocess.CalledProcessError as exc:
    return subprocess.CompletedProcess(args=[], returncode=exc.returncode, ...)
# TimeoutExpired propagates intentionally (caller handles separately)
```

**Docstring must document which exceptions still propagate**

After absorbing `CalledProcessError`, document explicitly in the docstring that
`TimeoutExpired` is the only exception that propagates. This is verified by reading
the wrapped functions — do NOT claim "never raises X" without reading the exception
contracts of every function the wrapper calls.

**Head-advancement as sole success signal (caller contract)**

After extraction, callers that ignore the returned `CompletedProcess` and only check
`_head_advanced()` are correct IF AND ONLY IF head-advancement is the sole success signal.
Verify before assuming this — if the original code checked `CalledProcessError` as a
**distinct** failure mode (not just "non-zero returncode"), the absorbed-error approach
changes semantics.

**Duplicate post-agent block extraction (`_push_ci_fix` pattern)**

When two provider branches share an **identical post-agent block** (e.g., head-advance
check → retry → pushability check → push), extract it to a second private helper:

```python
def _push_ci_fix(self, head_before: str, session_id: str, worktree: Path) -> bool:
    """Shared post-agent push logic; returns True if pushed."""
    if not self._head_advanced(head_before):
        return False
    if not self._retry_no_commit_once(session_id, worktree):
        return False
    if not self._ci_fix_head_is_pushable():
        return False
    self._push_ci_fix_branch()
    return True
```

**Implementation-time traps (verified during execution of Phase 20 for issue #1196)**

Three additional hazards surface only during actual test execution, not during planning:

**Trap 1: Mock `side_effect` exhaustion uncovered by exception-boundary removal**

When the original oversized method had an outer `except Exception` catch-all, exhausted mock
`side_effect` lists caused `StopIteration` to be silently swallowed. After extracting the
helper and removing the outer `except Exception`, pre-existing tests that provided only N-1
`side_effects` start failing with raw `StopIteration` instead of the intended assertion.

```python
# WRONG: pre-existing test only provides 2 side_effects for a path that now calls run 3×
with patch("subprocess.run", side_effect=[result1, result2]):  # StopIteration on 3rd call
    driver._retry_no_commit_once(...)

# RIGHT: count EVERY subprocess.run call including those inside nested helper methods
with patch("subprocess.run", side_effect=[result1, result2, clean_status]):  # all 3 covered
    driver._retry_no_commit_once(...)
```

**Count rule:** every time you modify a function or add a helper it calls, count every
`subprocess.run` (or other mocked call) the test path exercises, including those inside
NEW helper methods the test now reaches transitively. The `except Exception` was masking
`StopIteration`; its removal surfaces the latent miscounting.

**Trap 2: Returncode guard required at every call site**

Because `_invoke_agent_session` absorbs `CalledProcessError` into `returncode != 0` instead
of re-raising, callers MUST check the returncode immediately. Without the guard, execution
continues as if the agent succeeded even when it failed:

```python
# WRONG: caller ignores returncode — continues executing after agent failure
result = self._invoke_agent_session(session_id, prompt, timeout)
# ... continues executing as if agent succeeded

# RIGHT: guard at every call site
result = self._invoke_agent_session(session_id, prompt, timeout)
if result.returncode != 0:
    return False   # abort early; do not write no-commit marker or advance head
```

This is the direct consequence of the "absorbed exception → returncode signal" contract: the
helper cannot both absorb the exception AND raise it. The caller owns the check.

**Trap 3: C901 `# noqa` removal requires re-measurement, not assumption**

After extracting the helpers, the remaining method may still have enough branches (try/except,
if/else, early returns) to exceed the complexity threshold. Remove `# noqa: C901` only after
running:

```bash
ruff check --select C901 hephaestus/automation/ci_driver.py
# Must output "All checks passed!" before removing the annotation
```

Do not assume extraction made the method simple enough; measure it.

**Verification checklist for this pattern**

```markdown
## Provider-Dispatch Extraction Checklist (Phase 20)

- [ ] Confirmed exactly 2 branches (no hidden third provider)
- [ ] Both branches accept identical inputs (no branch-specific parameters)
- [ ] READ the wrapped function's class definition — grep for it; verify actual field names
      (e.g., AgentRunResult has stdout/stderr/session_id but NO returncode field)
- [ ] READ exception contracts of ALL wrapped functions — verify which raise CalledProcessError
      (run_codex_session raises at non-zero exit; resume_codex_session same behavior)
- [ ] BOTH codex calls (fresh and resume) wrapped in try/except CalledProcessError
- [ ] CalledProcessError absorbed into returncode=exc.returncode, not re-raised
- [ ] returncode=0 on codex success path is synthetic (only reachable if no exception raised)
- [ ] TimeoutExpired intentionally propagates (document this in docstring)
- [ ] Docstring states which exceptions propagate; never claim "never raises X" without
      reading every wrapped function's exception contract
- [ ] Caller uses head-advancement as sole success signal (not returncode check)
- [ ] Hardcoded `returncode=0` on claude path is correct (claude raises on failure)
- [ ] Every call site of the new helper has an immediate `if result.returncode != 0: return`
      guard (absorbed exceptions require caller-side returncode check — Trap 2)
- [ ] `# noqa: C901` on the original function can be removed — re-run `ruff --select C901`
      after extraction to confirm (do NOT assume removal is safe without measuring — Trap 3)
- [ ] Duplicate post-agent block is character-identical in both branches (diff them)
- [ ] Test classes `TestInvokeAgentSession` and `TestPushCiFix` added
- [ ] All existing test patches target same module namespace (no patch retargeting needed
      if helpers remain in same file)
- [ ] RECOUNT every mocked call in pre-existing tests that reach the helper transitively;
      remove-outer-except-Exception exposes previously-swallowed StopIteration (Trap 1)
```

### Phase 21: God-Function Decomposition — Function-Size Planning Rules

Use when decomposing individual functions that exceed the project's line-length threshold (> 80L
by convention). This phase is the function-level analogue to Phase 19 (god-class), covering the
eight planning rules that caused reviewer NOGO across the R0→R3 planning cycle for issue #1180
(7 god-functions across 4 files in `hephaestus/automation/`).

**Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

#### Rule 1: Arithmetic chain verification is non-negotiable

Write an explicit arithmetic chain for EVERY target function:

```text
<helper_name>: <X> lines sig+doc + <Y> lines body = <Z> total
```

If any target shows > 80L without a helper covering it, the plan is incomplete.
No marginal waivers ("borderline" or "acceptable overage" are not valid justifications).

**What failed (R0):** Plan waived `_implement_issue` at 128L as "marginal overage" — reviewer gave NOGO.
**What failed (R1):** Plan claimed `_implement_issue` was reduced but included no extraction step — NOGO.

#### Rule 2: Docstring budget counts toward function span

Before computing post-extraction size, check whether the function has a long docstring:

```bash
# Find docstring span for a function
python3 -c "
import ast, pathlib
src = pathlib.Path('<file>.py').read_text()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '<func>':
        print(f'Function starts: {node.lineno}, body[0] ends: {node.body[0].end_lineno}')
"
```

If the docstring exceeds ~15 lines, either:
- Subtract the docstring lines from the post-extraction size estimate, OR
- Plan to trim the docstring explicitly as part of the extraction step.

**Example:** `_address_issue` had a 24-line docstring (lines 477–504). Plans that ignored it
calculated the post-extraction count wrong.

#### Rule 3: For-loop body sizing — extract if > 40L

When a function contains a for/while loop whose body exceeds ~40L, that loop body is a
standalone extraction candidate. Do not plan to extract just the outer scaffold.

**Example:** `_run_ci_fix_session` (250L) needed 5 helpers, not 1–2. The CI polling while-loop
body and the codex/claude dispatch arms were each > 40L.

```text
Decision rule:
  loop body > 40L  → extract the body as a standalone helper
  loop body ≤ 40L  → may inline (but verify with arithmetic chain)
```

#### Rule 4: Return type tracing when helper absorbs the only call site

Before finalizing a helper's return type, trace every call to every function that will be
inside the extracted helper:

```bash
# Find all call sites for a function about to be absorbed
grep -n "<func_name>" <target_file>.py
```

If the helper absorbs the ONLY call site to a data-fetching function (e.g. `fetch_issue_info`),
the CALLER still needs that data. Return it as an extra tuple element — do NOT assume the
caller can re-fetch it.

**Example:** `_prepare_worktree_for_existing_pr` absorbed the only `fetch_issue_info` call.
R0/R1 plans returned `tuple[Path, str]` — the caller then had no `issue.title`/`issue.body`
for the review loop, causing a `NameError`.

#### Rule 5: N-tuple return completeness for complex orchestrators

When extracting a sub-orchestrator that returns multiple values, trace every variable the
slim parent uses AFTER the helper call. All must be in the return tuple.

**Verification procedure:**

```python
# Manually list all variables the slim parent reads after the helper call
# Example: after _process_review_iteration(), what does _run_impl_review_loop() use?
# → last_verdict, last_grade, review_text, posted_thread_ids,
#   go_blocked_by_automation, reopened, should_break
# = 7-tuple; R2 plan had 6 (dropped 'reopened') → NameError in zero-thread continue check
```

**Rule:** draft the tuple skeleton FIRST, then write the helper signature. Never finalize a
helper signature until you have enumerated every consumer variable on the call side.

#### Rule 6: Explicit parameter audit for captured variables

When extracting a helper from a long function, the extracted body may reference variables
from the enclosing scope that are NOT in the proposed parameter list. Audit every name
reference in the extracted body:

```bash
# Quick scope audit: list all names in the extracted block that are not local assignments
python3 -c "
import ast, textwrap
src = '''<paste extracted block here>'''
tree = ast.parse(textwrap.dedent(src))
names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
assigned = {n.targets[0].id for n in ast.walk(tree) if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)}
print('Possibly-captured:', names - assigned)
"
```

Any name that is not a Python builtin and not in the proposed parameter list is a missing parameter.

**Example:** `_build_ci_fix_prompt` used `worktree_path` from the enclosing scope in an f-string.
When extracted, the variable is not in scope — it must be an explicit parameter.

#### Rule 7: Approach table must list ALL helpers per target

The Approach table row for each target function MUST list ALL helpers that will be extracted
from it, not just the first or most obvious one.

| Target | Helpers | Post-extraction size |
|--------|---------|---------------------|
| `_run_impl_review_loop` | `_process_review_iteration`, `_run_address_step_if_needed` | 52L |

**What failed (R2):** Reviewer found `_process_review_iteration` and `_run_address_step_if_needed`
missing from the Approach table for `_run_impl_review_loop`.

**Rule:** After drafting the approach table, re-read each function and ask "what else will be extracted?"
Do not declare a row complete until the arithmetic chain closes at ≤ 80L.

#### Rule 8: AST-measure before planning — never trust issue line numbers

Issue bodies and prior plan drafts regularly state stale line numbers. Always re-measure
at plan time using AST:

```bash
python3 -c "
import ast, pathlib
src = pathlib.Path('<target>.py').read_text()
tree = ast.parse(src)
funcs = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        end = node.end_lineno or node.lineno
        funcs.append((end - node.lineno + 1, node.lineno, node.name))
for size, lineno, name in sorted(funcs, reverse=True)[:20]:
    print(f'{size:4d} lines  line {lineno:4d}  {name}')
"
```

**Example:** Issue #1180 cited `_drive_issue` at line 711 — actual: 731.
`_run_ci_fix_session` cited at 2590 — actual: 2610. These 20-line drifts caused
post-extraction arithmetic chains to be wrong.

**Rule:** Run the AST measurement on the actual file at plan time. Record the measured
line numbers and function sizes explicitly in the plan. Never carry forward issue-cited
or prior-draft numbers without re-verification.

#### God-Function Planning Checklist (Phase 21)

```markdown
## God-Function Decomposition Planning Checklist (Phase 21)

### Pre-plan (do before writing the plan)
- [ ] AST-measure every oversized function: `python3 -c "import ast ..."` (Rule 8)
- [ ] Record measured line numbers and function sizes — never trust issue-cited numbers
- [ ] List every function > 80L as a candidate target

### Per target function
- [ ] Write arithmetic chain: `X lines sig+doc + Y lines body = Z total` (Rule 1)
- [ ] If Z > 80 without a helper listed: plan is incomplete — add an extraction step
- [ ] Check docstring length; if > 15L, subtract from budget or plan to trim (Rule 2)
- [ ] Identify every for/while loop; if body > 40L, add it as a standalone helper (Rule 3)

### Per helper extracted
- [ ] Trace all functions absorbed by the helper — is any the ONLY call site to a
      data-fetching function? If yes, return the fetched data in the tuple (Rule 4)
- [ ] For orchestrator helpers: enumerate ALL variables the slim parent reads after
      the call; all must be in the return tuple (Rule 5)
- [ ] Audit every name reference in the extracted body against the parameter list;
      any captured variable from enclosing scope must be an explicit parameter (Rule 6)

### Approach table review
- [ ] For each target row, confirm ALL helpers are listed (not just the first one) (Rule 7)
- [ ] Arithmetic chain closes at ≤ 80L for every target
```

### Phase 22: God-Class Delegation — Shared-State Write-Back Rules

Use when a method being extracted to a collaborator class populates shared mutable state
(dicts, caches) that the host class reads after the method returns. Apply BEFORE writing
any extraction code.

**Warning:** These rules have been identified in planning sessions but not yet validated
end-to-end with CI. Treat as a design reference, not a verified recipe.

#### Rule 1: Identify every dict/cache written by the candidate method group

```bash
grep -n "self\.<attr>\[" <target_file>.py    # dict population
grep -n "self\.<attr> =" <target_file>.py    # cache writes
```

For each written attribute, check who reads it:

```bash
grep -n "self\.<attr>" <target_file>.py | grep -v "def \|#"
```

If the attribute is read by methods NOT being extracted, you have a write-back problem.

#### Rule 2: Choose a write-back strategy for shared mutable dicts

Three viable patterns — choose before writing the extraction:

**Pattern A: Return and assign in stub**

```python
# Collaborator returns the populated dict
class PRDiscovery:
    def _discover_prs(self, ...) -> dict[int, Any]:
        result: dict[int, Any] = {}
        # ... populate result ...
        return result

# Delegation stub in host captures and assigns
class CIDriver:
    def _discover_prs(self, ...) -> dict[int, Any]:
        result = self._pr_discovery._discover_prs(...)
        self.shared_pr_issues = result   # write-back
        return result
```

**Pattern B: Inject a setter callable**

```python
class PRDiscovery:
    def __init__(self, set_shared_pr_issues: Callable[[dict[int, Any]], None]) -> None:
        self._set_shared_pr_issues = set_shared_pr_issues

    def _discover_prs(self, ...) -> None:
        result: dict[int, Any] = {}
        # ... populate result ...
        self._set_shared_pr_issues(result)

# In CIDriver.__init__:
self._pr_discovery = PRDiscovery(
    set_shared_pr_issues=lambda d: setattr(self, "shared_pr_issues", d)
)
```

**Pattern C: Pass the dict as a mutable parameter**

```python
class PRDiscovery:
    def _discover_prs(self, shared_pr_issues: dict[int, Any], ...) -> None:
        shared_pr_issues.update(...)   # mutates in place

# In delegation stub:
def _discover_prs(self, ...) -> None:
    self._pr_discovery._discover_prs(self.shared_pr_issues, ...)
```

Choose Pattern A when the method fully replaces the dict (not incremental).
Choose Pattern B when you want the collaborator to be fully decoupled from the host.
Choose Pattern C when the dict is populated incrementally across multiple calls.

#### Rule 3: Methods called by multiple collaborator groups stay on the host

If a method is used by TWO OR MORE of the planned collaborator classes, it must stay on
the host class (or be extracted to a separate shared utility). Assigning it to one
collaborator forces the other to call `self._host._shared_method()`, which:

1. Reintroduces tight coupling to the host class internals
2. Makes the "receiving" collaborator unable to be unit-tested without the host
3. Violates the SRP that motivated the extraction

```bash
# For each shared method candidate, check all call sites:
grep -n "self\._tracked_worktree_changes\|self\._head_advanced" <target_file>.py | grep -v "def "
# If the method appears in lines claimed by BOTH CICheckInspector AND CIFixOrchestrator:
# → keep it on CIDriver (delegation stub optional)
```

#### Rule 4: Test fixture pre-seeding after cache extraction

When a cache attribute (e.g., `_viewer_login`) migrates from the host to a collaborator,
existing tests that pre-seed the host attribute will silently stop working:

```python
# Test pre-seeds host attribute — worked before extraction:
driver._viewer_login = "mvillmow"   # pre-seeded

# After extraction: driver._viewer_login doesn't exist; collaborator has its own cache
# driver._pr_discovery._viewer_login is the cache now
# The pre-seeded value never reaches the collaborator
```

**Fix options:**

1. Keep the cache on the host and inject a provider callable into the collaborator:

```python
class PRDiscovery:
    def __init__(self, viewer_login_provider: Callable[[], str]) -> None:
        self._viewer_login_provider = viewer_login_provider

    def _resolve_viewer_login(self) -> str:
        return self._viewer_login_provider()
```

The host keeps `_viewer_login`; tests pre-seed it; the collaborator calls the provider.

2. OR update all test fixtures to pre-seed the collaborator attribute instead.

Option 1 is preferred when tests cannot be edited (e.g., when preserving patch.object targets).

#### Rule 5: Read method bodies before assigning to collaborators

Grep output and method names alone are insufficient to determine which collaborator a
method belongs to. Before finalizing any assignment:

```bash
# Read the actual body (not just the signature line)
sed -n '<start>,<end>p' <target_file>.py
# OR:
python3 -c "
import ast, textwrap
src = open('<target_file>.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '_target_method':
        lines = src.splitlines()[node.lineno-1:node.end_lineno]
        print('\n'.join(lines))
"
```

Any method assigned without reading its body may:

- Reference state owned by a different collaborator than the assignment suggests
- Call methods that belong to a different collaborator group
- Contain conditional logic that makes it a shared utility, not a group-specific method

#### Phase 22 Planning Checklist

```markdown
## God-Class Delegation Shared-State Checklist (Phase 22)

### Per extracted method group
- [ ] List all dict/cache attributes written by the candidate methods
- [ ] For each attribute: grep who reads it outside the candidate group
- [ ] If read outside: choose write-back pattern (A/B/C) BEFORE extraction
- [ ] List all methods called by the candidate methods that are NOT in the group
- [ ] For each cross-group call: check if it's also used by another collaborator
      → if yes, keep it on host class; do not assign it to any one collaborator
- [ ] For each cache attribute migrating out: audit test fixtures that pre-seed it on the host
      → decide: inject provider callable OR update all fixtures
- [ ] Read the body of every method before assigning it to a collaborator (not just signature/grep)

### Pre-plan (do before writing extraction code)
- [ ] Read automation/__init__.py to verify whether CIDriver is already exported
      (do not write conditional "if exported; else skip" without reading first)
- [ ] If line count projection is needed: read top-10 longest method bodies directly
      and sum actual lines rather than using average estimates
```

### Phase 23: God-Class Execution — Narrow-Callable Injection (DIP) Pattern

Use when EXECUTING a god-class decomposition using Dependency Inversion through injected callables.
This phase covers the implementation-time traps discovered during ProjectHephaestus PR #1292
(CIDriver decomposed into 4 collaborators using narrow-callable injection: `pr_discovery.py`,
`ci_check_inspector.py`, `ci_fix_orchestrator.py`, `post_merge_processor.py`).

**Warning:** These rules are derived from a single verified CI execution. Treat as strong
guidance but re-verify on new codebases.

#### Rule 1: Lambda wrapping is mandatory for all injected callables

When the host class injects its own methods into a collaborator via `__init__`, ALWAYS wrap
them as lambdas. Bare bound-method references are captured at construction time; a mock applied
to `driver._method` AFTER construction has no effect on the collaborator's stored reference.

```python
# WRONG — bare bound method is a snapshot; patch.object(driver, "_head_advanced") bypassed:
self._fix_orchestrator = CIFixOrchestrator(
    head_advanced=self._head_advanced,
)

# RIGHT — lambda re-evaluates self._head_advanced at call time; patch works:
self._fix_orchestrator = CIFixOrchestrator(
    head_advanced=lambda *a, **k: self._head_advanced(*a, **k),
)
```

Apply to ALL injected callables without exception — even ones that seem "unlikely to be mocked"
in tests. The cost is negligible; the debugging cost of a missed one is large.

#### Rule 2: Patch each module's `run` import separately when a method chain splits

When a pre-agent SHA snapshot moves to an extracted collaborator but the post-agent SHA
read stays on the host, there are now TWO different lookup sites for `run` (or any shared
utility function):

```text
Pre-agent snapshot:  ci_fix_orchestrator.run   (imported in the collaborator)
Post-agent read:     ci_driver.run             (imported in the host)
```

Patching only `ci_fix_orchestrator.run` leaves the host's `run` unpatched — the second
`run` call hits real git on a tmp_path with no repo and fails with a confusing error.

```python
# WRONG — only patches the orchestrator's run:
with patch("hephaestus.automation.ci_fix_orchestrator.run", ...):
    driver._run_ci_fix_session(...)

# RIGHT — patches both lookup sites:
with (
    patch("hephaestus.automation.ci_fix_orchestrator.run", return_value=pre_sha),
    patch("hephaestus.automation.ci_driver.run", return_value=post_sha),
):
    driver._run_ci_fix_session(...)
```

**General rule**: When a method chain splits across modules, identify every file that has
`from subprocess_utils import run` (or similar) and patch the `run` name in EACH file that
is exercised by the test path.

#### Rule 3: Update attribute access in ALL sibling test files after migration

When an instance attribute migrates from the host to a collaborator (e.g., `_viewer_login`
moves from `CIDriver` to `PRDiscovery`), sibling test files that access it directly on the
host will silently stop working. mypy strict mode surfaces these as attribute errors:

```python
# After moving _viewer_login from CIDriver to PRDiscovery:
# WRONG — driver no longer has this attribute:
driver._viewer_login = ""

# RIGHT — access through the collaborator:
driver._pr_discovery._viewer_login = ""
```

**Grep command** (run before and after each migration):

```bash
grep -rn "driver\._viewer_login\|driver\.<migrated_attr>" tests/
```

A single cache attribute migration typically generates 6 mypy errors across sibling test files.
Fix all of them in the same commit as the migration.

#### Rule 4: Update `companions` tuple in phase-wiring tests when AGENT_* constants move

If the codebase has a test that verifies where `AGENT_*` constants are imported from (a common
pattern for validating agent-wiring), it uses a `companions` tuple to list extra files to scan:

```python
# test_phase_agent_wiring.py
@pytest.mark.parametrize("module,agent_const,companions", [
    ("ci_driver.py", "AGENT_CI_DRIVER", ()),      # BEFORE: constant in ci_driver.py
])
```

When `AGENT_CI_DRIVER` moves to `ci_fix_orchestrator.py`, add the new file to `companions`:

```python
    ("ci_driver.py", "AGENT_CI_DRIVER", ("ci_fix_orchestrator.py",)),  # AFTER
```

The `companions` tuple tells the test to scan both `ci_driver.py` AND `ci_fix_orchestrator.py`
for the constant; without it, the test only scans the primary module and fails.

#### Phase 23 Execution Checklist

```markdown
## God-Class Narrow-Callable DIP Execution Checklist (Phase 23)

### Before wiring collaborators in __init__
- [ ] Every injected callable is wrapped as `lambda *a, **k: self._method(*a, **k)` — no bare `self._method`
- [ ] Verified by: `grep -n "self\._[a-z]" __init__` and confirm none are bare (not in a lambda)

### After each collaborator is extracted
- [ ] Grep all test files for `host_instance.<migrated_attr>` — update to `host._collaborator.<attr>`
- [ ] Run mypy — zero new attribute errors expected after migration
- [ ] Check phase-wiring tests for `companions` tuples — update if AGENT_* moved

### When a pre/post SHA split occurs
- [ ] Identify every file that imports `run` (or the split utility)
- [ ] In each test that exercises the split path, patch each file's `run` independently
- [ ] Verify both mocks are called (assert_called_once on each)

### Final verification
- [ ] All 146+ pre-existing tests pass
- [ ] New collaborator tests pass (22+ for a 4-collaborator extraction)
- [ ] mypy clean (zero attribute errors)
- [ ] ci_driver.py line count meets target (−28% or better)
```

### Phase 24: Post-Extraction DRY / Constructor-Injection Refinement

Use when the initial god-class extraction is complete and merged, and a follow-on PR
applies DRY cleanup, constructor injection improvements, and import ordering. This phase
captures the additional implementation traps discovered during ProjectHephaestus PR #1320
(issue #1289) — the review-addressed refinement of the Phase 23 extraction.

#### Rule 1: Thin delegation stubs preserve `patch.object` targets at zero test-edit cost

After extraction, the original class may have deleted methods entirely. If any test does
`patch.object(OriginalClass, '_method')`, `patch.object` requires the attribute to exist
on the target class at the time the patch is applied. Deleting the method causes:

```
AttributeError: <class 'OriginalClass'> does not have the attribute '_method'
```

The fix is to leave a thin delegation stub on the original class:

```python
# WRONG — method deleted entirely; all patch.object('_method') tests fail:
class CIDriver:
    pass  # _method was removed in extraction

# RIGHT — thin delegation stub; patch.object still works:
class CIDriver:
    def _method(self, *args, **kw):
        return self._collaborator._method(*args, **kw)
```

**Rule:** Move method BODIES to collaborators. Leave thin delegation stubs on the original
class for every method that any test patches via `patch.object(OriginalClass, '_method')`.
Grep before removing any method: `grep -rn "patch.object.*OriginalClass.*'_method'" tests/`.

#### Rule 2: `__setattr__` override propagates test-time attribute changes to collaborators

Tests often do `driver.state_dir = tmp_path` (direct attribute assignment on the host)
to inject a test-specific path. After extraction, if the collaborator stores its own
copy of `state_dir`, the test-time assignment on the host doesn't reach the collaborator.

Add a `__setattr__` override on the original class to propagate specified attributes:

```python
class CIDriver:
    _PROPAGATED_ATTRS: frozenset[str] = frozenset({"state_dir", "dry_run"})

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        # Propagate to collaborators if they are already initialized
        if name in self._PROPAGATED_ATTRS:
            for collab_attr in ("_pr_discovery", "_ci_fix_orchestrator", ...):
                collab = self.__dict__.get(collab_attr)
                if collab is not None and hasattr(collab, name):
                    object.__setattr__(collab, name, value)
```

**Critical guard:** Use `self.__dict__.get(collab_attr)` (not `getattr`) and check
`is not None` before propagating — `__setattr__` is called during `__init__` before
collaborators exist, so `getattr` would trigger infinite recursion via `__init__`'s
own assignments.

#### Rule 3: `.clear()` + `.update()` preserves shared mutable dict object identity

When a dict is shared between the host and collaborators (e.g., `shared_pr_issues`),
do NOT reassign it with `self.shared_pr_issues = new_dict`. Reassignment breaks object
identity — the collaborator still holds a reference to the old dict:

```python
# WRONG — host rebinds; collaborator still references old dict:
self.shared_pr_issues = discovered_prs   # new object; collaborator out of sync

# RIGHT — mutate in place; all holders see the change:
self.shared_pr_issues.clear()
self.shared_pr_issues.update(discovered_prs)
```

Apply this pattern wherever the dict is "replaced wholesale" in collaboration with a
method that has been moved to a collaborator.

#### Rule 4: Circular import trap — utility functions imported by sibling modules must stay in the original file

When a utility function (e.g., `_pr_is_failing`) is:
- Defined in `ci_driver.py`, AND
- Imported at module level by a sibling module (e.g., `loop_runner.py`):
  `from hephaestus.automation.ci_driver import _pr_is_failing`

Moving that function to a collaborator module creates a circular import:

```text
loop_runner.py  →  ci_driver.py (imports CIDriver)
loop_runner.py  →  pr_discovery.py (imports _pr_is_failing)
pr_discovery.py →  ci_driver.py (collaborator)  ← CIRCULAR if ci_driver imports pr_discovery
```

**Resolution:** Keep the function in `ci_driver.py`. When the collaborator also needs it,
define a **local copy** in the collaborator module — do NOT import from `ci_driver.py`:

```python
# pr_discovery.py — local copy to avoid circular import
def _pr_is_failing(pr: dict) -> bool:
    """Local copy; ci_driver.py keeps the authoritative definition for loop_runner.py."""
    return ...  # same implementation
```

**Detection command** before moving any utility function:

```bash
grep -rn "from hephaestus.automation.ci_driver import _pr_is_failing" .
# Any match in a sibling module = circular import risk if function moves
```

#### Rule 5: `from __future__ import annotations` required in collaborator modules with PEP 604 union types

Collaborator modules often use modern union syntax (PEP 604): `dict[int, list[int]] | None`.
On Python 3.10 this works at runtime, but if the module is processed before the runtime
version guard or uses string annotations for forward references, the `|` operator in
annotations may fail.

Add `from __future__ import annotations` at the top of every collaborator module that uses
`X | Y` union type syntax. This is especially important when:
- The module uses `| None` in function signatures
- Type hints reference types from `TYPE_CHECKING`-guarded imports
- Collaborator modules are extracted from a host that already had the import

```python
# At the top of every collaborator module — before all other imports:
from __future__ import annotations
```

#### Rule 6: Pre-commit runs twice — first pass auto-fixes; second pass must be clean

After any extraction or DRY pass:

```bash
pre-commit run --files hephaestus/automation/ci_driver.py \
    hephaestus/automation/pr_discovery.py \
    hephaestus/automation/ci_fix_orchestrator.py \
    ...
# First pass: ruff auto-fixes (import ordering, unused imports, trailing commas)
# Re-run immediately:
pre-commit run --files ...
# Second pass: must be fully clean — "Passed" on every hook
```

Never count a pre-commit run as "clean" if it made changes; only the second pass with
zero auto-fix changes counts as clean.

#### Rule 7: Structural tests that grep source text need companion module parametrization

Tests that grep source files for module-level constants (e.g., `AGENT_CI_DRIVER`,
`from .session_naming import`) fail when those constants or imports move to collaborator
modules, because the test only scans the original file.

The fix is to add collaborator filenames to the `companions` tuple in the test's
parametrization, telling the test to scan both the original module AND collaborators:

```python
# BEFORE — test only scans ci_driver.py:
@pytest.mark.parametrize("module,const,companions", [
    ("ci_driver.py", "AGENT_CI_DRIVER", ()),
])

# AFTER — test also scans ci_fix_orchestrator.py where the constant now lives:
@pytest.mark.parametrize("module,const,companions", [
    ("ci_driver.py", "AGENT_CI_DRIVER", ("ci_fix_orchestrator.py",)),
])
```

**Detection:** Run the full test suite after extraction. Any `test_phase_agent_wiring.py`
or `test_structural_constants.py` failure with "constant not found in module" is a companion
parametrization miss.

**Note:** Relative imports (`from .session_naming import`) MUST be used in collaborators
(not absolute imports) to match the pattern the structural test's regex expects.

#### Phase 24 Checklist

```markdown
## Post-Extraction DRY / Constructor-Injection Checklist (Phase 24)

### Before removing any method from the original class
- [ ] `grep -rn "patch.object.*OriginalClass.*'_method'" tests/` — if match: add thin
      delegation stub BEFORE removing the body
- [ ] Stub form: `def _method(self, *args, **kw): return self._collab._method(*args, **kw)`

### Shared mutable state
- [ ] Every reassignment `self.shared_dict = new_dict` is replaced with
      `.clear(); .update(new_dict)` to preserve object identity for all holders

### Test-time attribute propagation
- [ ] If tests do `driver.<attr> = <value>`, add `__setattr__` override that
      propagates `<attr>` to all collaborators
- [ ] Use `self.__dict__.get(collab_attr)` (not `getattr`) to guard against
      `__init__`-time calls when collaborators don't exist yet

### Circular import check before moving utility functions
- [ ] `grep -rn "from <host_module> import <func>" .` — any sibling module match
      means <func> cannot move without a local copy in the collaborator

### Collaborator module preamble
- [ ] Every collaborator file starts with `from __future__ import annotations`
      if it uses `X | Y` union types in any annotation

### Pre-commit
- [ ] Ran pre-commit twice — second pass is fully clean (first pass may auto-fix)

### Structural tests
- [ ] After any AGENT_* constant or `from .session_naming import` moves:
      update `companions` tuple in `test_phase_agent_wiring.py`
- [ ] Collaborator uses relative import (`from .session_naming import`) not absolute
```

### Phase 25: Keyword-Only Method Signature Verification

**Problem**: During R5 planning for issue #1289, `_retry_no_commit_once` was given a fabricated
positional signature in the plan (including a fabricated `acquired_slot` parameter). The real
method at `ci_driver.py:2296` uses `*` (keyword-only) with params:

```python
def _retry_no_commit_once(
    self,
    *,
    issue_number: int,
    pr_number: int,
    worktree_path: Path,
    pr_head_branch: str,
    pre_agent_sha: str,
    session_id: str,
    max_retries: int = 2,
) -> bool:
```

Forwarding a keyword-only method with positional args raises `TypeError` at runtime.
The AST-check in Criterion 6 (method name presence) only checks whether the method name
exists in the stub — it does **not** verify signature correctness. A wrong-but-present stub
passes the check silently.

**Rule**: For every method being extracted, read the actual `def` line and the complete
parameter list (including whether `*` appears as the first param after `self`) before writing
any stub. Never infer keyword-only status from call-site context alone.

**Stub template for keyword-only methods**:

```python
# In host class (delegation stub):
def _retry_no_commit_once(
    self,
    *,
    issue_number: int,
    pr_number: int,
    worktree_path: Path,
    pr_head_branch: str,
    pre_agent_sha: str,
    session_id: str,
    max_retries: int = 2,
) -> bool:
    return self._collaborator._retry_no_commit_once(
        issue_number=issue_number,
        pr_number=pr_number,
        worktree_path=worktree_path,
        pr_head_branch=pr_head_branch,
        pre_agent_sha=pre_agent_sha,
        session_id=session_id,
        max_retries=max_retries,
    )
```

#### Phase 25 Checklist

```markdown
## Keyword-Only Stub Checklist (Phase 25)

### Before writing any stub
- [ ] Read the actual `def` line in the source file — not a plan summary, the real line
- [ ] Check: does `*` appear as a standalone parameter before named params?
- [ ] If yes: stub def MUST use `*` too; forwarding call MUST use `keyword=value` for every param
- [ ] Verify no fabricated params (params not in the real def) appear in the stub
- [ ] Verify no params from the real def are missing from the stub

### AST check limitation
- [ ] Criterion 6 (name-presence check) passes for wrong-signature stubs — it ONLY checks the method name
- [ ] Signature correctness is your responsibility; the check will not catch it
```

### Phase 26: `_gh_call` Multi-Module Split Attribution via Test-Class Boundaries

**Problem**: When `_gh_call` is patched in 26+ places across one test file, and the symbol
moves to 4+ destination modules, "17-way split" estimates and range-grep spot-checks are
both insufficient. Two range greps only cover 2 of 26 sites — the remaining 24 sites are
unaccounted for.

**Fix**: Map every patch site to its test class by:

1. Get class start lines:

```bash
grep -n "^class " tests/unit/automation/test_ci_driver.py
```

2. Get all patch sites:

```bash
grep -n "ci_driver\._gh_call" tests/unit/automation/test_ci_driver.py
```

3. Bucket each patch line into the class whose start-line is the **largest ≤ the patch line**.
   Each test class tests one method; each method goes to one collaborator module.
   The bucket directly gives the destination module.

4. Verify the total across all buckets equals the total patch count before finalizing.

**Verification after migration**:

```bash
# Only the N lines that stay in ci_driver should remain; all others must be gone
grep -n "ci_driver\._gh_call" tests/unit/automation/test_ci_driver.py | \
  grep -v "^<line1>:\|^<line2>:..." && echo "FAIL" || echo "PASS"
```

**Rule**: Never estimate `_gh_call` migration scope from a count of methods or a range-based
spot-grep. Always bucket every patch line by class boundary to determine its destination.

#### Phase 26 Checklist

```markdown
## _gh_call Multi-Module Split Checklist (Phase 26)

### Before planning migration
- [ ] `grep -n "^class " test_file.py` — record all class name + start-line pairs
- [ ] `grep -n "symbol_being_moved\._gh_call" test_file.py` — collect ALL patch lines with line numbers
- [ ] For each patch line: find the class whose start-line is largest ≤ patch line number
- [ ] Tally sites per bucket (per destination module)
- [ ] Sum all buckets — must equal total patch count; if not, a site was missed

### After migration
- [ ] Re-run the grep — zero sites targeting old module should remain (except intentional ones)
- [ ] Run the full test suite — every test class that had patches must still pass
```

### Phase 27: Delegation Chain Through Sub-Modules — Pre-Check Before Patch Migration

**Finding**: `_find_pr_for_issue` in `ci_driver.py` already delegates internally to
`_review_utils.find_pr_for_issue`, which in turn calls `_review_utils._gh_call` — NOT
`ci_driver._gh_call`. The test (`TestBodySearch`, line 1561) patches
`hephaestus.automation._review_utils._gh_call`.

Moving `_find_pr_for_issue` to a collaborator does **not** require migrating any `_gh_call`
patch for this method's tests — the symbol never lived in `ci_driver`'s namespace at the
test level.

**Rule**: Before adding a method's `_gh_call` patch sites to the migration table, read the
patch string in the test. If the existing test already patches a sub-module (e.g.,
`_review_utils._gh_call`), that patch does not need to move regardless of where the method
moves.

**Pre-check command**:

```bash
# For a method under consideration, find all its test class's patches:
grep -n "ci_driver\._gh_call\|_review_utils\._gh_call\|other_submodule\._gh_call" \
  tests/unit/automation/test_ci_driver.py | \
  awk -F: '$1 >= CLASS_START && $1 <= CLASS_END'
```

If the output shows `_review_utils._gh_call` (not `ci_driver._gh_call`), the patch site
belongs to the sub-module and stays put.

#### Phase 27 Checklist

```markdown
## Delegation Chain Pre-Check Checklist (Phase 27)

### For each method identified for migration
- [ ] Read the method body — does it delegate to a sub-module function (e.g., `_review_utils.X`)?
- [ ] If yes: check the test's patch string — does it patch `ci_driver._gh_call` or `_review_utils._gh_call`?
- [ ] If the test patches the sub-module directly: this patch site does NOT belong in the migration table
- [ ] Only add `ci_driver._gh_call` patches (not sub-module patches) to the migration count for this method
- [ ] Document the delegation chain in the plan: `_find_pr_for_issue → _review_utils.find_pr_for_issue → _review_utils._gh_call`
```

### Phase 28: Return-Type Verification Is as Critical as Parameter Verification

**Problem**: During R5 planning for issue #1289, six delegation stubs were written with
incorrect return types inferred from expected behavior rather than source-read annotations.
Phase 24 established the rule to read parameter signatures; it did not extend to return types.

| Method | Actual return type | Plan had |
|--------|-------------------|----------|
| `_recheck_and_arm_after_fix` (L1149) | `WorkerResult \| None` | `-> bool` |
| `_resolve_dirty_pr` (L1229) | `WorkerResult` | `-> bool` |
| `_attempt_ci_fixes` (L1292) | `WorkerResult \| None` | `-> bool` |
| `_gh_pr_state` (L1625) | `dict[str, Any] \| None` | `-> dict` |
| `_enable_auto_merge` (L2861) | `bool` | `-> None` |
| `_run_drive_green_compact` (L3019) | `bool` | `-> None` |

**Root cause**: Phase 22 only verified *parameters* of three specific methods. Return types
were never independently checked. Inferred return types (e.g., "this method arms a PR,
so it must return `bool`") are frequently wrong.

**Two failure modes for wrong return types**:

1. **Mypy fails in the HOST file** (`ci_driver.py`) containing the stubs, NOT in the new
   collaborator modules. The collaborator method itself is typed correctly; the stub in the
   host is the mismatch.
2. **Invisible to Criterion 9** if mypy only targets the new collaborator modules. Adding
   `ci_driver.py` to the mypy target list is required to catch these errors.

**Rule**: For every delegation stub, source-read the full `def` line including the `->` return
annotation. Do not infer return types from method names, call-site expectations, or analogy.

```python
# Example: source-read confirms these are NOT bool
def _recheck_and_arm_after_fix(
    self, issue_number: int, pr_number: int, acquired_slot: int,
) -> WorkerResult | None:   # NOT bool — must source-read to know this
    ...

def _enable_auto_merge(
    self, pr_number: int,
) -> bool:                   # NOT None — must source-read to know this
    ...
```

**Mypy target list rule**: When writing stubs for methods extracted TO collaborator modules,
include the HOST file (`ci_driver.py`) in the Criterion 9 mypy invocation:

```bash
# INCOMPLETE — only catches errors in collaborator modules:
mypy hephaestus/automation/pr_discovery.py hephaestus/automation/ci_fix_orchestrator.py

# COMPLETE — also catches stub return-type drift in the host:
mypy hephaestus/automation/ci_driver.py \
     hephaestus/automation/pr_discovery.py \
     hephaestus/automation/ci_fix_orchestrator.py \
     hephaestus/automation/ci_check_inspector.py \
     hephaestus/automation/arming_orchestrator.py
```

#### Phase 28 Checklist

```markdown
## Return-Type Verification Checklist (Phase 28)

### For every delegation stub before writing it
- [ ] Read the actual `def` line in the source — locate the `->` annotation
- [ ] Record the exact return type including `| None`, `| None` unions, `dict[str, Any]` vs bare `dict`, etc.
- [ ] Do NOT infer from method name, expected behavior, or analogy with similar methods
- [ ] Stub `->` annotation must exactly match source annotation (including `| None` where present)

### Mypy target list (Criterion 9)
- [ ] Include the HOST file (e.g., `ci_driver.py`) in the mypy invocation alongside collaborator modules
- [ ] Reason: wrong stub return types fail mypy in the host file, not the collaborator modules
- [ ] Verify: `mypy ci_driver.py <collaborator_modules>` shows zero errors before declaring stubs correct
```

### Phase 29: `acquired_slot` Confirmation — Fabrication Risk Runs Both Ways

**Context**: Phase 24 established that fabricated parameters (parameters that do NOT exist)
cause `TypeError` at runtime. A symmetric risk is assuming a parameter does NOT exist when
it actually does.

**Finding for issue #1289 R6**: Three methods all DO have `acquired_slot` as a real
positional parameter:

| Method | Actual signature summary |
|--------|-------------------------|
| `_recheck_and_arm_after_fix(self, issue_number, pr_number, acquired_slot)` | positional, not keyword-only |
| `_resolve_dirty_pr(self, issue_number, pr_number, acquired_slot)` | positional, not keyword-only |
| `_attempt_ci_fixes(self, issue_number, pr_number, acquired_slot, extra_context="")` | positional; `extra_context` has default |

These are distinct from `_retry_no_commit_once` (Phase 24), which does NOT have
`acquired_slot`. The fabrication risk in Phase 24 was about a non-existent parameter; the
confirmation here is that for these three methods, the parameter genuinely exists.

**Dual verification rule**: When uncertain about a specific parameter:

1. **Does the parameter EXIST?** — read the `def` line; confirm the name appears in the signature
2. **Is it positional or keyword-only?** — check whether `*` appears before it
3. **Does it have a default?** — check for `= <value>` after the name

Delegation stubs must preserve the exact positional/keyword-only status and default values.

```python
# Correct stubs reflecting source-read signatures:
def _recheck_and_arm_after_fix(
    self, issue_number: int, pr_number: int, acquired_slot: int,
) -> WorkerResult | None:
    return self._collaborator._recheck_and_arm_after_fix(
        issue_number, pr_number, acquired_slot,  # positional pass-through
    )

def _attempt_ci_fixes(
    self, issue_number: int, pr_number: int, acquired_slot: int, extra_context: str = "",
) -> WorkerResult | None:
    return self._collaborator._attempt_ci_fixes(
        issue_number, pr_number, acquired_slot, extra_context,
    )
```

#### Phase 29 Checklist

```markdown
## Parameter Existence Confirmation Checklist (Phase 29)

### For each parameter whose existence is uncertain
- [ ] Read the actual `def` line — does the parameter name appear?
- [ ] If YES: record positional vs keyword-only (before or after `*`?) and whether it has a default
- [ ] If NO: the parameter is fabricated — remove it from the stub
- [ ] Do NOT assume parameter existence from method name, call-site usage, or similar methods

### Symmetric fabrication risks
- [ ] Phase 25 risk: parameter listed in plan but absent from source → TypeError at runtime
- [ ] Phase 29 risk: parameter absent from plan but present in source → stub drops required arg
- [ ] Both risks resolved by the same fix: source-read the `def` line before writing any stub
```

### Phase 30: Keyword-Only Forwarding Call — `_mark_drive_green_learn_result` Pattern

**Context**: Phase 25 established the rule to check for `*` in the stub def when source uses
keyword-only params. During R6, `_mark_drive_green_learn_result` was given a completely wrong
stub — fabricated positional `pr_number`, missing keyword-only `succeeded`. In R7, the correct
stub was identified but the forwarding call still required fixing.

**Source signature (ci_driver.py:1550–1556)**:

```python
def _mark_drive_green_learn_result(
    self, issue_number: int, record: dict[str, Any], *, succeeded: bool
) -> None:
```

**Wrong stub (R6 failure)**:

```python
def _mark_drive_green_learn_result(self, issue_number: int, pr_number: int, record: dict[str, Any]) -> None:
    # Had fabricated pr_number positional, missing keyword-only succeeded
```

**Correct stub (R7)**:

```python
def _mark_drive_green_learn_result(
    self, issue_number: int, record: dict[str, Any], *, succeeded: bool
) -> None:
    return self._post_merge_processor._mark_drive_green_learn_result(
        issue_number, record, succeeded=succeeded)  # must pass succeeded= as kwarg
```

**Key rule**: A `*` separator in the source signature means ALL params after it are keyword-only.
The forwarding call must pass them as `param=value`, not positionally. The stub def and the
forwarding call are TWO separate places that must both be correct.

**Common mistake**: Fixing the stub def (adding `*`) but passing `succeeded` positionally in
the body. This raises `TypeError` at runtime but passes all static checks.

#### Phase 30 Checklist

```markdown
## Keyword-Only Forwarding Call Checklist (Phase 30)

### For methods with * in their source def line
- [ ] Stub def includes `*` at the correct position
- [ ] Every param after `*` in the stub uses the correct name and type annotation
- [ ] Forwarding call passes EVERY keyword-only param as `param=value` (not positional)
- [ ] No fabricated params appear in the stub (applies to both positional and keyword-only sections)
- [ ] No real params are omitted from the stub

### Two-location check
- [ ] Stub def signature: correct? (includes `*`, correct param names and types)
- [ ] Stub body forwarding call: correct? (every keyword-only param passed as `param=value`)
```

### Phase 31: Fabricated Parameters Are the #1 Planning Failure Mode

**Evidence from R4/R5/R6 rejection history**:

| Round | Fabrication | Source truth |
|-------|-------------|--------------|
| R4 | `_retry_no_commit_once` had fabricated `acquired_slot` | Method is keyword-only with no `acquired_slot` at all |
| R5 | Six stubs had wrong return types inferred from expected behavior | Source had `WorkerResult \| None`, `WorkerResult`, `dict[str, Any] \| None`, `bool` |
| R6 | `_resolve_dirty_pr` had fabricated 4th param `worktree_path` AND false "confirmed from source" claim | Source L1227-1229 shows 3 params; call site L919 confirms 3 args |
| R6 | `_mark_drive_green_learn_result` had fabricated `pr_number`, missing keyword-only `succeeded` | Source L1550-1556: keyword-only `succeeded`, no `pr_number` at all |

**Root cause pattern**: The planner described expected/intuitive signatures based on:
- What the method "should" accept given its name
- Params that appear in nearby methods with similar names
- Return types inferred from "methods like this usually return bool"

None of these are reliable. Method signatures are entirely determined by the actual source.

**Prevention protocol (verified effective in R7)**:

1. For EVERY stub: run `sed -n '<start>,<end>p' ci_driver.py` to get the exact `def` + `->` line range
2. Verify call sites in the source to confirm param count matches (find at least one caller)
3. Do NOT write "confirmed from source" unless the `sed` or Read command was actually run
4. Write the stub by copying the signature characters from the command output, not from memory

**False confirmation anti-pattern**:

When a plan includes "confirmed from source" but the source was not actually read, it gives
reviewers false confidence and causes the same error to persist across multiple rounds. The
phrase "confirmed from source" is only valid if the exact line range was verified during THIS
planning session.

#### Phase 31 Checklist

```markdown
## Fabricated-Param Prevention Checklist (Phase 31)

### Before writing ANY stub in a planning document
- [ ] Run `sed -n '<start>,<end>p' <source_file>.py` for EVERY stub (not just uncertain ones)
- [ ] Record the exact line range used (start, end line numbers)
- [ ] Write the stub signature by copying from the sed output, not from memory
- [ ] Find at least one call site in source and count the args — must match param count

### Prohibited phrases without verification
- [ ] "confirmed from source" — ONLY write this after actually running sed/Read on that line range
- [ ] "similar to nearby method X" — signatures are independent; do not infer from analogies
- [ ] "this type of method usually returns bool" — always source-read the `->` annotation

### Pattern matching to check (common fabrication triggers)
- [ ] Methods named `_resolve_X` near other methods with a `worktree_path` param: check if THIS method has it
- [ ] Methods similar to keyword-only methods: check if THIS method also uses `*`
- [ ] Methods that "sound like" guards: check if the return type is actually `bool` vs `WorkerResult | None`
```

### Phase 32: `acquired_slot` vs No `acquired_slot` — Slot-Ownership Mnemonic

**Problem**: Two similarly-structured methods are easy to confuse when assigning `acquired_slot`:

| Method | `acquired_slot`? | Conceptual role |
|--------|-----------------|-----------------|
| `_attempt_mechanical_rebase(self, issue_number, pr_number, acquired_slot) -> bool` | YES | IS a worker — it acquires a slot before doing rebase work |
| `_retry_no_commit_once(self, *, issue_number, pr_number, worktree_path, ...) -> bool` | NO | Sub-step INSIDE a worker — executes within an already-acquired slot |
| `_recheck_and_arm_after_fix(self, issue_number, pr_number, acquired_slot) -> WorkerResult \| None` | YES | IS a worker — re-enters the arming queue inside an acquired slot context |
| `_resolve_dirty_pr(self, issue_number, pr_number, acquired_slot) -> WorkerResult` | YES | IS a worker — resolves dirty-PR state at the worker level |

**Mnemonic rule**:

> `acquired_slot` belongs to methods that ARE semaphore-slot workers (they receive the slot
> token as evidence they've been dispatched by the slot scheduler).
> Methods that run AS INTERNAL STEPS of a worker — already executing inside a slot —
> do NOT receive `acquired_slot`; they inherit the slot context implicitly.

**Diagnostic check**:

```bash
# Find which methods call _attempt_mechanical_rebase to see the caller pattern:
grep -n "_attempt_mechanical_rebase\|_retry_no_commit_once\|_resolve_dirty_pr" ci_driver.py | grep -v "^.*def "
# Callers of worker methods pass acquired_slot explicitly
# Calls to sub-step methods do not
```

**Why this matters for delegation stubs**: If you add `acquired_slot` to `_retry_no_commit_once`
(which does NOT have it), the stub will fail at runtime with `TypeError: unexpected argument`.
If you omit `acquired_slot` from `_resolve_dirty_pr` (which DOES have it), the stub will fail
with `TypeError: missing required argument`.

Both errors are prevented by the same fix: source-read the `def` line (Phase 25/30). This
phase adds the conceptual mnemonic to help predict which category a method falls into before
reading, reducing the planning error rate in future rounds.

#### Phase 32 Checklist

```markdown
## Slot-Ownership Mnemonic Checklist (Phase 32)

### Classification heuristic (apply BEFORE source-reading to guide focus)
- [ ] Is this method dispatched directly by the slot scheduler? → likely HAS acquired_slot
- [ ] Is this method called FROM WITHIN a worker method? → likely does NOT have acquired_slot
- [ ] Use this as a prior, then VERIFY by reading the actual def line (Phase 25 rule)

### Verification (always required regardless of heuristic)
- [ ] Source-read the def line: does `acquired_slot` appear in the parameter list?
- [ ] If uncertain: find a call site with `grep -n "methodname" ci_driver.py` and count args
```

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
| **Trusting issue LOC estimates for a god-class plan** | Used issue body's "2,633 lines" for `implementer_phase_runner.py` to scope the extraction plan | File was actually 1,308 lines (already decomposed via PR #712) — planned 1,325 unnecessary lines of work | Always `wc -l` the actual substrate file before planning; issue LOC estimates are routinely stale after prior decomposition PRs (Phase 19 Step 0) |
| **Leaving `_viewer_login` on original class after extracting its owner** | Plan extracted `PRDiscovery` but left the `_viewer_login` cache field on `CIDriver` | `PRDiscovery` writes to a field on a different object — split-ownership bug; the collaborator cannot be unit-tested independently | Audit every class field before finalizing extraction boundaries; fields used exclusively by extracted methods must migrate with them (Phase 19 Step 1) |
| **Extracting method group without extracting the methods it calls** | Extracted `CIFixOrchestrator` but left `_head_advanced`, `_ci_fix_head_is_pushable`, `_tracked_worktree_changes` on `CIDriver` | Extracted class must call `self._driver._head_advanced()` — tightly coupled to original class internals; defeats SRP purpose of extraction | Map cross-call coupling before finalizing extraction boundaries; resolve by moving called methods too, using callbacks, or documenting temporary coupling (Phase 19 Step 2) |
| **Proposing `*args, **kwargs` stubs without checking mypy config** | Plan used `# noqa: ANN002,ANN003` delegation stubs assuming per-module mypy relaxation | `pyproject.toml` uses `strict = true` with no `[mypy-hephaestus.automation.*]` override — strict mypy rejects untyped stubs | Check mypy config before proposing delegation stub patterns; if strict, write fully typed stubs mirroring collaborator signatures (Phase 19 Step 3) |
| **Moving a constant to a new module without grepping external callers** | Plan moved `FAILING_CHECK_CONCLUSIONS` from `ci_driver.py` to new `ci_check_inspector.py` | External callers doing `from hephaestus.automation.ci_driver import FAILING_CHECK_CONCLUSIONS` get ImportError; CI may not catch until integration tests run | Grep all external callers before moving any constant; if callers exist, keep in place or re-export with explicit `as X` alias from both locations (Phase 19 Step 4) |
| **Ignoring delegation stub line overhead in line count projections** | Estimated final line count as original minus extracted lines only | 18 extracted methods × 5 stub lines = 90 additional lines not counted; projected 2,200 became 2,252 — tighter than the ≤2,200 criterion | Always add delegation stub overhead (≈ 5 lines × num_extracted_methods) and new import blocks to line count projections (Phase 19 Step 5) |
| **Assuming test_omit_allowlist.py doesn't exist without checking** | Plan mentioned updating coverage omit lists "if the guard exists" without verifying first | `test_omit_allowlist.py` existed and failed CI when new modules weren't added to the omit list | Always `find tests/ -name "test_omit_allowlist.py"` before adding modules; include omit list update in same PR as new module (Phase 19 Step 6) |
| **Hardcoding `returncode=0` on success path without reading `AgentRunResult`** | Plan assumed `run_codex_session` returns `AgentRunResult` and constructed `CompletedProcess(returncode=0)` on success | Verified: `run_codex_session` raises `CalledProcessError` on non-zero exit (runtime.py:397–403); it does NOT return an `AgentRunResult` with a returncode on failure. `returncode=0` on the success path is actually correct AND synthetic (only reachable if no exception was raised) — but the reasoning in the plan was wrong; it should be justified by the exception contract, not by reading `AgentRunResult` | Read the wrapped function's exception contract first (`run_codex_session` raises `CalledProcessError` on failure — never returns); `returncode=0` on the codex success path is correct because exceptions have already been absorbed (Phase 20) |
| **Assuming `AgentRunResult.returncode` field exists without verifying** | Plan annotated wrapper with `subprocess.CompletedProcess[str]` and accessed `result.returncode`, assuming field name from `CompletedProcess` analogy | Verified: `AgentRunResult` (runtime.py:28–34) has fields `stdout`, `stderr`, `session_id` — NO `returncode` field; accessing `result.returncode` would raise `AttributeError` at runtime | Read the actual dataclass definition before accessing any field; grep for `class AgentRunResult` to confirm the exact field names; never infer fields from analogous types (Phase 20) |
| **Docstring claims wrapper never raises X without verifying wrapped functions** | Wrote a docstring claiming `_invoke_agent_session` "never raises CalledProcessError" before verifying the exception contracts of `run_codex_session` and `resume_codex_session` | Reviewer caught POLA violation: `run_codex_session` DOES raise `CalledProcessError` on non-zero exit (runtime.py:397–403); the docstring was factually wrong | Always grep for the implementation of every function the wrapper calls and read its exception contract before writing "never raises X" in a docstring; reviewers will always verify this (Phase 20) |
| **Assuming `# noqa: C901` can be removed without re-measuring complexity** | Plan removed the noqa suppressor as part of extraction, assuming post-refactor CC was below threshold | Outer `try/except` around sync + snapshot + prompt-build still contributes branches; if those remain, ruff re-flags the method | Run `ruff check --select C901 <file>.py` after extraction to confirm removal is safe; do not assume (Phase 20 Step 5) |
| **Treating head-advancement as sole success signal without verifying original code** | After extraction, plan assumed caller only checks `_head_advanced()` after `_invoke_agent_session` | Original codex branch at line 2709 also checked `CalledProcessError` as a distinct failure mode; absorbed-error approach changes semantics if callers relied on that distinct signal | Verify the original error-handling contract before assuming return-value check can be dropped; if the original differentiated `CalledProcessError` from "ran successfully but no head advance", the absorbed approach loses that distinction (Phase 20) |
| **Assuming duplicate post-agent blocks are identical without diffing** | Plan said lines 2722–2743 and 2777–2798 in `_run_ci_fix_session` were "character-identical" based on visual inspection | Even one extra blank line or minor spacing difference invalidates "identical"; extracting non-identical blocks silently changes behavior | Diff the two blocks explicitly (`diff <(sed -n '2722,2743p' ci_driver.py) <(sed -n '2777,2798p' ci_driver.py)`) before claiming they are character-identical (Phase 20) |
| **Left pre-existing test side_effects unchanged after removing outer `except Exception`** | After removing the catch-all `except Exception` from the oversized method, kept old tests that provided N-1 `side_effect` values for mocked `subprocess.run` | `StopIteration` from the exhausted mock bubbled up as a test failure; the outer `except Exception` had been silently swallowing it | Count every `subprocess.run` call the test path exercises — including those inside newly extracted helper methods — after any exception-boundary change (Phase 20, Trap 1) |
| **Did not add `if result.returncode != 0: return False` after calling `_invoke_agent_session`** | Caller continued executing after the helper returned a non-zero `CompletedProcess` because the absorbed `CalledProcessError` didn't re-raise | No-commit marker was written and execution continued as if the agent session succeeded — incorrect behavior | A helper that absorbs exceptions into returncode transfers the error-check responsibility to the caller; add `if result.returncode != 0: return <error_value>` immediately after every call site (Phase 20, Trap 2) |
| **Set mock agent to `return_value=MagicMock()` (success) when testing a path that should fail early** | In `test_returns_false_when_head_not_advanced_and_retry_fails`, mock `invoke_claude_with_session` to return normally (no exception) expecting `_retry_no_commit_once` to fail | Agent succeeded, then `_retry_no_commit_once` consumed more `subprocess.run` side_effects than provided, triggering `StopIteration` | Change the agent mock to raise `CalledProcessError` so `_invoke_agent_session` returns non-zero immediately and the retry loop exits without consuming additional `run` calls (Phase 20, Trap 1+2 interaction) |
| **Assumed `# noqa: C901` could be removed without measuring post-refactor complexity** | Removed the annotation at the same time as the helper extraction, assuming the extraction was sufficient | The extracted method may still exceed the complexity threshold due to remaining try/except, if/else, and early-return branches | Run `ruff check --select C901 <file>.py` after extraction; remove `# noqa: C901` only after confirming "All checks passed!" (Phase 20, Trap 3) |
| **Waiving a 128L function as "marginal overage" without an extraction step (R0)** | Plan for issue #1180 noted `_implement_issue` at 128L was "a marginal overage" and did not include an extraction step | Reviewer gave NOGO: no waivers on the 80L threshold; 128L is not marginal — it requires an extraction plan | Write an explicit arithmetic chain for every target; if any target shows > 80L without a helper, the plan is incomplete. No marginal waivers. (Phase 21, Rule 1) |
| **Claiming a target was reduced without listing the extraction step (R1)** | R1 plan stated `_implement_issue` was reduced but listed no new helper and no arithmetic chain | Reviewer gave NOGO: the reduction was claimed but not demonstrated; no helper = no reduction | Arithmetic chain verification is non-negotiable: `X lines sig+doc + Y lines body = Z total` must appear for every target, with the helper explicitly named (Phase 21, Rule 1) |
| **Ignoring docstring lines when computing post-extraction size** | Plans for `_address_issue` computed post-extraction count without subtracting its 24-line docstring (lines 477–504) | Post-extraction arithmetic chains were wrong; the function appeared to fit when it did not | Before computing post-extraction size, find the docstring span and subtract those lines from the budget, or plan to trim the docstring explicitly (Phase 21, Rule 2) |
| **Planning 1–2 helpers for a 250L function with a 40L+ loop body (R0/R1)** | `_run_ci_fix_session` (250L) was planned with 1–2 helpers; CI polling while-loop body and codex/claude dispatch arms were not counted as extraction candidates | The loop bodies alone exceeded 40L each; reviewers caught that the plan undercounted required helpers | When a for/while loop body exceeds ~40L, that body is a standalone extraction candidate; plan for it explicitly (Phase 21, Rule 3) |
| **Helper return type omitted the absorbed fetch call's data (R0/R1)** | `_prepare_worktree_for_existing_pr` was planned with return type `tuple[Path, str]` despite absorbing the only `fetch_issue_info` call | The caller still needed `issue.title` and `issue.body` for the review loop but had no way to get them — would cause `NameError` at runtime | Trace every function absorbed by a helper; if it absorbs the only call to a data-fetching function, return the fetched data as an extra tuple element (Phase 21, Rule 4) |
| **Orchestrator helper return tuple dropped 'reopened' variable (R2)** | `_process_review_iteration` was specified with a 6-tuple: `(last_verdict, last_grade, review_text, posted_thread_ids, go_blocked_by_automation, should_break)` — `reopened` was omitted | The slim parent's zero-thread continue check used `reopened` — `NameError` at that code path | Enumerate ALL variables the slim parent reads after the helper call; a 7-tuple was needed. Draft the tuple skeleton before writing the helper signature (Phase 21, Rule 5) |
| **Extracted helper body used `worktree_path` from enclosing scope — not in parameter list** | `_build_ci_fix_prompt` extraction plan did not include `worktree_path` in the parameter list, even though the f-string body referenced it | When extracted, `worktree_path` is not in scope — `NameError` at runtime | Audit every name in the extracted body against the proposed parameter list; any captured variable from the enclosing scope must be added as an explicit parameter (Phase 21, Rule 6) |
| **Approach table omitted helpers for `_run_impl_review_loop` (R2)** | The Approach table row for `_run_impl_review_loop` listed only one helper; `_process_review_iteration` and `_run_address_step_if_needed` were missing | Reviewer flagged both helpers as absent from the table; arithmetic chain was therefore also missing | After drafting the approach table, re-read each function and confirm ALL helpers are listed; do not declare a row complete until the arithmetic chain closes at ≤ 80L (Phase 21, Rule 7) |
| **Used issue-cited line numbers without re-measuring (R0–R2)** | Plans carried forward stale line numbers from the issue body: `_drive_issue` at line 711 (actual: 731), `_run_ci_fix_session` at 2590 (actual: 2610) | 20-line drift made post-extraction arithmetic chains wrong; helpers were sized to wrong baselines | Run AST measurement on the actual file at plan time; record measured line numbers explicitly; never trust issue-cited or prior-draft line numbers (Phase 21, Rule 8) |
| **Moving `_discover_prs` to collaborator without designing write-back for `shared_pr_issues`** | Plan extracted `PRDiscovery._discover_prs` but did not address how the populated `shared_pr_issues` dict would reach `CIDriver`'s arming fan-out logic | After extraction the collaborator updates its own local variable, not `CIDriver.shared_pr_issues`; the arming logic reads the host's attribute which is never updated | When extracting a method that populates a dict read by the host class: choose one write-back pattern (return+assign in stub, injected setter callable, or mutable dict parameter) and design it before writing any extraction code (Phase 22, Rule 2) |
| **Assigning `_tracked_worktree_changes` to one collaborator when it is used by two** | Plan assigned `_tracked_worktree_changes` to `CICheckInspector`; `CIFixOrchestrator` also calls it | `CIFixOrchestrator` must call `self._ci_check_inspector._tracked_worktree_changes()` — cross-collaborator coupling that defeats the SRP goal | Methods called by multiple collaborator groups must stay on the host class (or be extracted to a shared utility); do not assign shared methods to any single collaborator (Phase 22, Rule 3) |
| **Pre-seeding `driver._viewer_login` in tests after `PRDiscovery` extraction** | Tests pre-seeded `driver._viewer_login = "mvillmow"` to short-circuit viewer-login resolution | After extraction, the relevant cache lives at `driver._pr_discovery._viewer_login`; pre-seeding the host attribute has no effect — the collaborator still calls `gh api /user` | When extracting a method that maintains a cache: either keep the cache on the host and inject a provider callable, OR update all test fixtures to pre-seed the collaborator's attribute (Phase 22, Rule 4) |
| **Assigning method bodies to collaborators based on name/grep without reading the body** | `_arm_all_unarmed_open_prs`, `_check_arming_on_drive_start`, `_arming_state_path/load/save/clear` were assigned to `ArmingOrchestrator` based on method name and grep output only | Bodies not read; may reference state or call methods that break the injection model | Read every method body before assigning it to a collaborator; grep output and names alone are insufficient — the body may reveal state dependencies or cross-group calls that change the assignment (Phase 22, Rule 5) |
| **Writing conditional `__init__.py` export step without reading `__init__.py`** | Plan said "if `automation/__init__.py` already exports `CIDriver`; otherwise skip" — conditionality not resolved at plan time | `__init__.py` content was not read during planning; whether to add exports and where was left ambiguous | Read `__init__.py` directly before planning any export step; never leave "if/else export" conditionality unresolved in the plan (Phase 22, Phase 22 Checklist) |
| **Estimating line count target achievability without reading method bodies** | Plan estimated 37 methods × ~25 lines avg = ~814 net savings, projecting ci_driver.py to ~2,544 lines with no fallback plan if wrong | Method body lengths were not read; if average is <25 lines, target may not be reached after PRDiscovery alone | For line count projections: read the top-N longest method bodies directly (using AST measurement) and sum actual lines rather than applying an average estimate; if projection is near the threshold, include a fallback plan (Phase 22 Checklist) |
| **Storing direct bound-method references in collaborator init** | Passed `head_advanced=self._head_advanced` (bare bound method) to collaborator constructor | `patch.object(driver, "_head_advanced")` doesn't intercept — the collaborator captured the original reference at init time, bypassing the mock | Always wrap injected callables as `lambda *a, **k: self._method(*a, **k)`; the lambda re-evaluates `self._method` at call time so `patch.object` works (Phase 23, Rule 1) |
| **Single `run` module patch after pre/post SHA split** | Patched only `ci_fix_orchestrator.run` for both pre-agent and post-agent SHA reads after moving pre-agent snapshot to orchestrator | Post-agent SHA read (`_head_advanced`) uses `ci_driver.run` not `ci_fix_orchestrator.run`; second call missed the mock and hit real git on non-repo tmp_path | When a method chain splits across modules, patch each module's `run` import separately; the pre-agent call uses the orchestrator's `run`, the post-agent call uses ci_driver's `run` (Phase 23, Rule 2) |
| **Forgetting `_viewer_login` attribute access in sibling test files** | Moved `_viewer_login` from `CIDriver` to `PRDiscovery` without updating `test_ci_driver_author_scope.py` which accessed `driver._viewer_login` directly | mypy reported `"CIDriver" has no attribute "_viewer_login"`; 6 mypy errors; tests failed | After moving any instance attribute to a collaborator, grep all test files for `driver.<attr>` and update to `driver._collaborator.<attr>` (Phase 23, Rule 3) |
| **`companions=()` not updated in phase-wiring test** | `AGENT_CI_DRIVER` import moved to extracted collaborators (`ci_fix_orchestrator.py`, `post_merge_processor.py`) but `test_phase_agent_wiring.py` still had `("ci_driver.py", "AGENT_CI_DRIVER", ())` with empty companions tuple | Test checks the combined source of module + companions for the AGENT_* import; empty companions meant only `ci_driver.py` was scanned, which no longer has the import | When an `AGENT_*` constant moves to an extracted collaborator, add that collaborator filename to the `companions` tuple in `test_phase_agent_wiring.py` (Phase 23, Rule 4) |
| **Logger patches targeting old module after extraction** | Left `patch("hephaestus.automation.ci_driver.logger")` for a warning that now emits from `pr_discovery.logger` | Mock showed 0 calls — warning emitted from extracted module's logger | After extracting a module, grep all test files for `ci_driver.logger` patches and update to `<new_module>.logger` (Phase 4) |
| **Deleting method from original class without checking for `patch.object` usage** | Removed `_method` body from `CIDriver` after moving to `CIFixOrchestrator` | `patch.object(CIDriver, '_method')` raised `AttributeError: does not have the attribute '_method'`; tests failed | Leave a thin delegation stub `def _method(self, *args, **kw): return self._collab._method(*args, **kw)` on the original class; grep `patch.object.*OriginalClass.*'_method'` before removing any method (Phase 24, Rule 1) |
| **`self.shared_pr_issues = discovered_prs` broke collaborator sync** | Delegation stub reassigned `self.shared_pr_issues = result` instead of mutating in place | Collaborator held a reference to the old dict object; arming fan-out read stale data from host's new dict | Use `.clear(); .update(discovered_prs)` to mutate in place and preserve object identity for all holders (Phase 24, Rule 3) |
| **Moved `_pr_is_failing` to `pr_discovery.py` without checking sibling imports** | Moved the function to the collaborator as it was only called from there | `loop_runner.py` does `from hephaestus.automation.ci_driver import _pr_is_failing` at module level → circular import: `ci_driver` → `pr_discovery` → (would need ci_driver) | Keep the function in `ci_driver.py`; define a local copy in `pr_discovery.py` to avoid the import cycle (Phase 24, Rule 4) |
| **Collaborator module missing `from __future__ import annotations`** | New collaborator modules used `dict[int, list[int]] \| None` without the future import | Runtime `TypeError: unsupported operand type(s) for \|` on Python 3.9 (or unexpected annotation evaluation errors) | Add `from __future__ import annotations` as the first non-comment line of every collaborator module using PEP 604 union types (Phase 24, Rule 5) |
| **Counting first pre-commit run as "clean" when it made auto-fixes** | Ran pre-commit once, saw no hook failures, declared it clean | First pass made ruff auto-fixes (import ordering, trailing commas); second pass would have shown additional issues | Always run pre-commit twice; only the second pass with zero file changes counts as clean (Phase 24, Rule 6) |
| **Structural test failed: constant not found in companions** | `AGENT_CI_DRIVER` moved to `ci_fix_orchestrator.py` but `companions=()` left empty in parametrize | `test_phase_agent_wiring.py` only scanned `ci_driver.py` — constant no longer there; test failed with "constant not found" | Add collaborator filename to `companions` tuple; ensure collaborator uses relative import (`from .session_naming import`) to match test regex (Phase 24, Rule 7) |
| **Fabricated positional signature for keyword-only method** | Plan gave `_retry_no_commit_once` a positional signature including a fabricated `acquired_slot` param; the real method at ci_driver.py:2296 uses `*` (keyword-only) with 7 actual params | Forwarding via positional args raises `TypeError` at runtime; AST Criterion 6 checks name presence only — wrong-but-present stub passes silently | Before writing any stub, read the actual `def` line; if `*` appears, stub def must also use `*` and the forwarding call must use `keyword=value` for every param (Phase 25) |
| **Range-grep spot-check insufficient for multi-module _gh_call split** | Used two range-grep checks to estimate `_gh_call` migration scope when the symbol moved to 4+ destination modules across 26 patch sites | Only 2 of 26 sites were covered; 24 sites were unaccounted for, making the migration table incomplete | Grep all patch sites with line numbers; bucket each line into its test class by finding the largest class-start ≤ patch-line; each class → one method → one destination module; verify bucket totals equal the total site count (Phase 26) |
| **Adding _gh_call patch for delegating method without checking its sub-module chain** | Added `_find_pr_for_issue`'s test to the `ci_driver._gh_call` migration table without reading the test's patch string | The test already patched `_review_utils._gh_call` — not `ci_driver._gh_call`; the symbol never lived in `ci_driver`'s namespace at the test level, so the migration was unnecessary | Before adding any method's patch sites to a migration table, read the actual patch string in the test; if it targets a sub-module, that site does not move regardless of where the method relocates (Phase 27) |
| **R6 return-type drift — six stubs inferred from expected behavior instead of source-read** | Six delegation stubs used `-> bool` / `-> None` / `-> dict` inferred from expected behavior (`_enable_auto_merge` "should return None since it's a side-effect method"; `_recheck_and_arm_after_fix` "should return bool since it's a guard") | Mypy in `ci_driver.py` rejected all six stubs; Criterion 9 only covered collaborator modules — not `ci_driver.py` — so the errors were not caught by the plan-time mypy check | Source-read the `->` annotation for every stub; add `ci_driver.py` (the host file) to the Criterion 9 mypy target list — wrong return types surface in the host, not in collaborator modules (Phase 28) |
| **R6 `_resolve_dirty_pr` stub had fabricated 4th param `worktree_path` with false "confirmed from source"** | Added positional `worktree_path: Path` as a 4th parameter to `_resolve_dirty_pr` with a note claiming it was "confirmed from source" | Source L1227-1229 shows 3 params (`self, issue_number, pr_number, acquired_slot`); call site L919 confirms 3 args; the 4th param did not exist; the false confirmation claim wasted a review round | Never write "confirmed from source" without actually running `sed -n` or Read on that exact line range during the current planning session; this is the same root cause as all prior fabrications (Phase 31) |
| **R6 `_mark_drive_green_learn_result` stub had fabricated `pr_number`, missing keyword-only `succeeded`** | Wrote stub with positional `pr_number` (doesn't exist in source) and omitted the keyword-only `succeeded` parameter entirely | Source L1550-1556: `def _mark_drive_green_learn_result(self, issue_number: int, record: dict[str, Any], *, succeeded: bool) -> None` — no `pr_number`, `succeeded` is keyword-only; forwarding call must use `succeeded=succeeded` | Both the stub def AND the forwarding call must be correct; a method named for "learn result" doesn't need `pr_number`; read the def line to know; pass keyword-only params with `param=value` in the forwarding call (Phase 30) |
| **R4 `_retry_no_commit_once` had fabricated `acquired_slot`** | Added positional `acquired_slot` parameter to `_retry_no_commit_once` based on its presence in similar-looking worker methods | Source: `_retry_no_commit_once` uses `*` (keyword-only) with no `acquired_slot` at all — it is a sub-step executed inside a worker, not a worker itself | Methods that execute AS SUB-STEPS inside an acquired slot do not receive `acquired_slot`; only methods dispatched BY the slot scheduler receive it (Phase 32); source-read the def line to confirm (Phase 25) |

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
| `ci_driver.py` (4 collaborators, narrow-callable DIP) | 3,338 | 2,404 | −28% | `pr_discovery.py` (260L), `ci_check_inspector.py` (130L), `ci_fix_orchestrator.py` (530L), `post_merge_processor.py` (230L) |
| `ci_driver.py` (DRY + constructor-injection refinement) | 2,404 | 1,410 | −41% further (−58% total from 3,358) | Thin delegation stubs, `__setattr__` propagation, `.clear()/.update()` dict identity, `_pr_is_failing` local copy, `from __future__ import annotations` |

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
| ProjectHephaestus | Issue #1179 — planning decomposition of `CIDriver` (ci_driver.py, 3,338 lines, 51 methods) into 4 collaborator modules; substrate read revealed `implementer_phase_runner.py` was 1,308 lines not 2,633 (stale audit); 6 planning risks identified including split-ownership on `_viewer_login`, cross-call coupling in `CIFixOrchestrator`, unverified mypy strict mode for `*args/**kwargs` stubs, ungrepped external callers of `FAILING_CHECK_CONCLUSIONS`, delegation stub LOC overhead tightening line count target, and unverified `test_omit_allowlist.py` (unverified — plan not yet executed) | New Phase 19: God-Class Decomposition Planning Risk Audit (v1.4.0) |
| ProjectHephaestus | Issue #1196 — planning refactor of `_retry_no_commit_once` (164 lines, codex/claude branches threaded through) and `_run_ci_fix_session` (two identical 17-line post-agent blocks); plan: extract `_invoke_agent_session` (not Protocol; two-branch bool-predicate; wraps `AgentRunResult` → `CompletedProcess`) + `_push_ci_fix` (duplicate post-agent block); 5 unverified risks: `AgentRunResult.returncode` field existence, `CalledProcessError` absorption loses codex error signal, head-advancement as sole success signal, `# noqa: C901` removal safety, duplicate block character-identity (unverified — plan not yet executed) | New Phase 20: Provider-Conditional Dispatch Extraction (v1.5.0) |
| ProjectHephaestus | Issue #1196 Phase 20 reviewer NOGO — reviewer verified source: `AgentRunResult` (runtime.py:28–34) has `stdout`/`stderr`/`session_id` fields (NO `returncode`); `run_codex_session` raises `CalledProcessError` at runtime.py:397–403 on non-zero exit; `resume_codex_session` same behavior; POLA violation caught: docstring claimed "never raises CalledProcessError" without verifying wrapped functions; corrected pattern: wrap BOTH codex calls in `try/except CalledProcessError`, use `CompletedProcess(returncode=0)` (synthetic, only reachable without exception), document `TimeoutExpired` as sole propagating exception | Phase 20 correction: exception-contract verification before wrapper docstrings (v1.6.0) |
| ProjectHephaestus | Issue #1196 Phase 20 implementation — extracted `_invoke_agent_session` + `_push_ci_fix` into `ci_driver.py`; removed `# noqa: C901` from `_run_ci_fix_session`; added 11 new tests (`TestInvokeAgentSession` 8 tests, `TestPushCiFix` 3 tests); 157 tests in `test_ci_driver.py` pass; ruff + mypy clean; three implementation traps discovered: (1) outer `except Exception` was masking `StopIteration` from exhausted mock `side_effect` lists — removal exposed latent miscounting in `test_codex_ci_fix_session_skips_push_when_head_did_not_advance` (needed 3rd `run` side_effect for `clean_status`); (2) caller of `_invoke_agent_session` in `_retry_no_commit_once` lacked `if retry_result.returncode != 0: return False` — no-commit marker was being written incorrectly; (3) mock for `invoke_claude_with_session` in retry test had to be changed from `return_value=...` to `raise CalledProcessError` to avoid consuming excess `run` side_effects; CI gate pending (verified-local) | Phase 20 implementation traps: exception-boundary removal unmasks StopIteration, returncode-guard obligation at call sites, agent-mock type determines downstream `run` consumption (v1.7.0) |
| ProjectHephaestus | Issue #1180 — planning decomposition of 7 god-functions across 4 files in `hephaestus/automation/` (R0→R3 planning cycle): R0 NOGO (waived 128L `_implement_issue` as "marginal"); R1 NOGO (claimed reduction with no extraction step); R2 NOGO (6-tuple dropped `reopened`, approach table missing two helpers); R3 approved; 8 planning rules identified: (1) arithmetic chain non-negotiable — no waivers; (2) docstring lines count toward function span; (3) for-loop body > 40L is a standalone extraction candidate; (4) helpers absorbing the only call to a data-fetching function must return the fetched data; (5) orchestrator N-tuple must cover ALL post-call variables; (6) every captured variable in an extracted body is a missing parameter; (7) approach table must list ALL helpers per target; (8) AST-measure before planning — never trust issue-cited line numbers (unverified — plan not yet executed) | New Phase 21: God-Function Decomposition Planning Rules (v1.8.0) |
| ProjectHephaestus | Issue #1289 — planning second decomposition pass of `ci_driver.py` (3,358 lines) using Dependency Inversion + delegation stubs to preserve `patch.object` test targets; 4 collaborators proposed (`PRDiscovery`, `CICheckInspector`, `CIFixOrchestrator`, `ArmingOrchestrator`); 6 additional planning risks identified: (1) `shared_pr_issues` write-back not designed — `_discover_prs` moving to `PRDiscovery` populates dict that arming fan-out reads on CIDriver; (2) `_tracked_worktree_changes` used by both `CICheckInspector` and `CIFixOrchestrator` — cross-collaborator coupling if assigned to one; (3) test fixture pre-seeding of `driver._viewer_login` stops working after cache migrates to collaborator; (4) method bodies not read before assigning to collaborators (`_arm_all_unarmed_open_prs` etc. assigned by name only); (5) conditional `__init__.py` export step not resolved at plan time — `__init__.py` not read; (6) line count projection used 25-line average for method bodies without reading actual lengths — no fallback plan if target not reached after PRDiscovery (unverified — implementation not yet started) | New Phase 22: God-Class Delegation Shared-State Write-Back Rules (v1.9.0) |
| ProjectHephaestus | PR #1292 (Issue #1179) — executed CIDriver god-class decomposition using narrow-callable injection (DIP): ci_driver.py 3,338 → 2,404 lines (−28%); 4 collaborators extracted (`pr_discovery.py` 260L, `ci_check_inspector.py` 130L, `ci_fix_orchestrator.py` 530L, `post_merge_processor.py` 230L); 4 implementation traps discovered: (1) bare bound-method references to injected callables bypass `patch.object` — all injected callables must be lambda-wrapped; (2) pre/post-SHA split after orchestrator extraction requires patching BOTH `ci_fix_orchestrator.run` and `ci_driver.run` independently; (3) `_viewer_login` attribute migration generated 6 mypy errors in sibling test files — all attribute access paths must be updated; (4) `AGENT_CI_DRIVER` move to extracted module broke `test_phase_agent_wiring.py` — companions tuple required update; 146 existing tests + 22 new tests pass; all CI gates passed (verified-ci) | New Phase 23: God-Class Narrow-Callable DIP Execution Pattern (v1.10.0) |
| ProjectHephaestus | PR #1320 (Issue #1289) — DRY + constructor-injection refinement of the Phase 23 extraction; ci_driver.py 2,404 → 1,410 lines (−41% further; −58% total from 3,358); 7 post-extraction patterns identified: (1) thin delegation stubs on original class preserve `patch.object` targets without test edits; (2) `__setattr__` override with `self.__dict__.get()` guard propagates test-time `state_dir` / `dry_run` assignments to collaborators; (3) `.clear()/.update()` preserves `shared_pr_issues` dict object identity across host + collaborators; (4) `_pr_is_failing` must stay in `ci_driver.py` because `loop_runner.py` imports it at module level — define local copy in collaborator to avoid circular import; (5) `from __future__ import annotations` required in collaborator modules using PEP 604 `X \| Y` union types; (6) pre-commit first pass auto-fixes; only second pass counts as clean; (7) structural tests scanning source text for `AGENT_*` constants / relative imports need `companions` tuple updated; 1,600 tests passed; pre-commit clean on both passes (verified-ci) | New Phase 24: Post-Extraction DRY / Constructor-Injection Refinement (v1.11.0) |
| ProjectHephaestus | Issue #1289 R5 planning session — 3 new pre-implementation verification rules discovered: (1) `_retry_no_commit_once` at ci_driver.py:2296 uses keyword-only `*` separator; plan gave it a fabricated positional signature including non-existent `acquired_slot` param — AST Criterion 6 would pass silently but runtime raises `TypeError`; fix: read actual `def` line before any stub; (2) `_gh_call` patched in 26 sites across one test file moving to 4+ destination modules — two range-grep spot-checks only covered 2 of 26 sites; fix: bucket all patch lines by test-class start-line boundary; (3) `_find_pr_for_issue` tests already patch `_review_utils._gh_call` (not `ci_driver._gh_call`) because the method already delegates through `_review_utils`; these sites do not need migration regardless of where the method moves; fix: read the patch string before adding any site to the migration table (plan not yet executed) | New Phases 25–27: Keyword-Only Sig Verification, _gh_call Bucket Analysis, Delegation Chain Pre-Check (v1.13.0) |
| ProjectHephaestus | Issue #1289 R6 planning session — 2 new verification rules discovered: (1) six delegation stubs had wrong return types (`-> bool` or `-> None` or bare `-> dict` instead of `WorkerResult \| None`, `WorkerResult`, `dict[str, Any] \| None`, `bool`); mypy in ci_driver.py rejected all six; Criterion 9 only covered collaborator modules — adding ci_driver.py to the mypy target list is required to surface host-file type errors; fix: source-read `->` annotation for every stub; (2) three methods — `_recheck_and_arm_after_fix` (L1149), `_resolve_dirty_pr` (L1229), `_attempt_ci_fixes` (L1292) — all DO have `acquired_slot` as a real positional parameter (unlike `_retry_no_commit_once` which did NOT); fabrication risk runs both ways: parameters may genuinely exist or be absent; source-read is the only reliable check (plan not yet executed) | New Phases 28–29: Return-Type Verification, acquired_slot Confirmation (v1.13.0) |
| ProjectHephaestus | Issue #1289 R7 planning session — 3 new planning-time rules discovered: (1) `_mark_drive_green_learn_result` (L1550-1556) uses keyword-only `succeeded: bool` with no `pr_number` at all; R6 stub had fabricated `pr_number` and missing `succeeded`; R7 fix: both stub def AND forwarding call must be correct for keyword-only params — stub def needs `*`, forwarding call needs `succeeded=succeeded`; (2) fabricated method signatures were the #1 rejection cause in 3 consecutive rounds (R4 fabricated `acquired_slot` in `_retry_no_commit_once`; R5 had 6 wrong return types; R6 had fabricated `worktree_path` in `_resolve_dirty_pr` and fabricated `pr_number` + missing `succeeded` in `_mark_drive_green_learn_result`); prevention: `sed -n '<start>,<end>p'` for EVERY stub, never use "confirmed from source" without running the command; (3) `acquired_slot` ownership mnemonic: methods that ARE semaphore-slot workers (dispatched by slot scheduler) have the param; sub-steps executing INSIDE an acquired slot do not; use as prior then source-verify (plan not yet executed) | New Phases 30–32: Keyword-Only Forwarding Call, Fabricated-Param Prevention Protocol, acquired_slot Mnemonic (v1.13.0) |
