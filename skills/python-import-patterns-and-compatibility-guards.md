---
name: python-import-patterns-and-compatibility-guards
description: "Use when: (1) a child module would create circular dependencies by importing the parent at module level — use function-local imports to defer the lookup and keep the import graph acyclic; (2) extending a public SDK surface with peer classes using lazy-loading __init__.py infrastructure (lazy exports pattern via __getattr__) to prevent eager-load regressions when adding new peers to __all__; (3) code uses a stdlib module added in a later Python version (tomllib in 3.11+, ExceptionGroup in 3.11+) and the CI matrix includes older Python — add a version-gated try/except import guard so the module remains importable; (4) adding cross-OS CI matrix and Windows jobs fail with ModuleNotFoundError for POSIX-only stdlib modules (curses, fcntl, grp, tzdata) — add conditional import guards and ensure tzdata is listed as an optional Windows dependency; (5) a hardcoded surface-pinning test (set(__all__) == literal) fails on CI with 'Extra items in the left set' because a peer export landed on main via an independent PR while your branch was open — fix the stale test literal, not the (correct) source, and use env -i / git stash / grep-the-CI-log to separate real failures from live-session environment noise; (6) a branch widening a lazy SDK surface (_LAZY_EXPORTS/__all__/__getattr__ in __init__.py) goes DIRTY/CONFLICTING on rebase because a sibling PR already landed the identical export — resolve by keeping ONE copy of the shared entry, and FIRST check mergeStateStatus=DIRTY when a PR reads as CI-failing but no test actually failed."
category: architecture
date: 2026-06-11
version: "1.2.0"
user-invocable: false
history: python-import-patterns-and-compatibility-guards.history
tags:
  - import-strategy
  - circular-dependency
  - coupling-avoidance
  - lazy-loading
  - sdk-surface
  - version-guard
  - cross-platform
  - windows-ci
  - stdlib
  - tomllib
  - curses
  - fcntl
  - tzdata
  - compatibility
  - surface-pinning
  - branch-divergence
  - merge-skew
  - test-vs-source
  - environment-noise
  - merge-conflict
  - rebase
  - mergestate-dirty
---

# Python Import Patterns and Compatibility Guards

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Manage the Python import graph and import compatibility across versions and platforms: avoid circular dependencies with function-local imports, extend public SDK surfaces via lazy exports without eager-load regressions, guard stdlib imports that vary by Python version or OS, and keep hardcoded surface-pinning tests from going stale when peers land via parallel PRs |
| **Outcome** | Acyclic import graphs, Windows-importable packages, CI matrices green on older Python and POSIX-only stdlib, lazy SDK surfaces that scale to new peer classes, and a decision procedure for fixing stale pinned-`__all__` tests (test vs source) without chasing live-session environment noise |
| **Verification** | verified-ci (function-local / version-guard / Windows-guard / lazy-exports); verified-local (surface-pin-stale fix — CI re-run confirmation pending) |

## When to Use

- **Function-local imports (coupling avoidance)**: A child module needs ambient state from a parent module (e.g., `logging.utils` already imports `utils.helpers`), and a module-level child-to-parent import would create a circular dependency or import-graph bloat. The import is used in only one or two functions.
- **Lazy exports (SDK surface)**: Extending a public package `__all__` with peer classes from submodules, adding `TYPE_CHECKING` imports, preventing eager-load regressions, or avoiding architectural restructuring when widening the public surface.
- **Version-gated stdlib guard**: A CI matrix includes Python 3.10 and code does a bare import of a 3.11+ stdlib module (`tomllib`, `ExceptionGroup`); `pytest` collection fails with `ModuleNotFoundError` on the lowest Python in the matrix.
- **Windows / POSIX-only stdlib guard**: Adding a cross-OS CI matrix where Windows jobs fail with `ModuleNotFoundError` for `curses`/`fcntl`/`termios`/`grp`/`pwd`, or `zoneinfo.ZoneInfo` raises `ZoneInfoNotFoundError` on Windows (needs `tzdata`).
- **Lazy-export add/add rebase conflict**: A branch widens the lazy SDK surface (`_LAZY_EXPORTS` + `__all__` + `__getattr__`) and goes `DIRTY`/`CONFLICTING` because a *sibling PR already landed the identical export* on main. The PR reads as "CI failing" but the logs show only runner/setup steps and **no test actually failed** — the merge conflict itself is the blocker. Resolve by keeping ONE copy of the shared entry.
- **Stale surface-pin test (branch-divergence / merge-skew)**: A hardcoded surface-pinning test (`assert set(__all__) == {literal}`) fails on CI with `Extra items in the left set: '<Symbol>'`, where `<Symbol>` is a *legitimate* peer export that landed on `main` via an independent PR while your feature branch was open. The production `__init__.py` is correct; the test literal went stale. You need to decide whether the test or the source is wrong, then fix only the stale party — and to do that you must separate the real CI failure from environment noise that only appears when the local suite runs inside a live automation session.

## Verified Workflow

### Quick Reference

```python
# (1) FUNCTION-LOCAL IMPORT — break a circular dep child→parent
# child module (utils/helpers.py); parent (logging/utils.py) already imports this child
def run_subprocess(cmd):
    from hephaestus.logging.utils import get_current_correlation_id  # local, not top-level
    cid = get_current_correlation_id()
    ...
```

```python
# (2) LAZY EXPORTS — extend public SDK surface without eager load
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from hephaestus.automation.ci_driver import CIDriver, CIDriverOptions

__all__ = ["Automation", "CIDriver", "CIDriverOptions"]  # alphabetical, case-sensitive

_LAZY_EXPORTS = {"CIDriver": "hephaestus.automation.ci_driver",
                 "CIDriverOptions": "hephaestus.automation.ci_driver"}
_PHASE_ENTRYPOINTS = ("hephaestus.automation.ci_driver",)  # guards eager-load preload
```

```python
# (3) VERSION-GATED STDLIB GUARD — 3.11+ module on a 3.10 matrix
import sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]
```

```python
# (4) POSIX-ONLY STDLIB GUARD — keep package importable on Windows
try:
    import fcntl
except ModuleNotFoundError:  # Windows: fcntl is POSIX-only
    fcntl = None  # type: ignore[assignment]
```

```toml
# Conditional dependencies for the guards above (pyproject.toml)
[project]
dependencies = [
    "tomli; python_version < '3.11'",       # backport for (3)
    "tzdata; platform_system == 'Windows'", # zoneinfo data for (4)
]
```

```bash
# Audit for unguarded imports before patching
grep -rn "^import tomllib" hephaestus/ scripts/ tests/   # expect 0 after fix
grep -rn "^import \(curses\|fcntl\|termios\|grp\|pwd\)" hephaestus/  # each needs a guard
```

```bash
# (6) LAZY-EXPORT ADD/ADD REBASE CONFLICT — "CI failing" but no test failed
gh pr view <N> --json mergeStateStatus --jq .mergeStateStatus   # DIRTY → conflict, not a test
git fetch origin main && git rebase origin/main                 # conflict localises to __init__.py
git show origin/main:hephaestus/automation/__init__.py | grep PRReviewer  # confirm main has it
#   → keep ONE copy of the shared _LAZY_EXPORTS entry; key ORDER is irrelevant (set()-based tests)
git rebase --continue
pixi run python -m pytest tests/ && pre-commit run --all-files  # ruff-format may reflow old lines
git commit -S -m "..."                                          # GPG (not SSH); key-email committer
git push --force-with-lease origin HEAD:<branch>                # rebase rewrote history
```

### Detailed Steps

#### A. Function-local imports to avoid coupling / circular deps

1. **Diagnose the cycle.** Confirm the parent already imports the child:
   ```bash
   grep -r "^from hephaestus.utils" hephaestus/logging/   # parent imports child?
   grep -r "^from hephaestus.logging" hephaestus/utils/   # child imports parent at top-level? → cycle
   ```
2. **Move the import into the function** that needs the ambient state:
   ```python
   def run_subprocess(cmd: list[str]) -> str:
       """Run subprocess, injecting correlation ID into environment.

       Note: import is inside the function to avoid a circular dependency
       with hephaestus.logging (which imports from hephaestus.utils).
       """
       from hephaestus.logging.utils import get_current_correlation_id
       env = os.environ.copy()
       if cid := get_current_correlation_id():
           env["GH_TRACE_ID"] = cid
       ...
   ```
3. **Keep the function where it semantically belongs** — move the *import*, not the function. Do not relocate `get_current_correlation_id()` into `utils` just to dodge the edge (that creates a god-module / SRP violation).
4. **Accept the cost.** First call pays an import lookup (~1–5µs); subsequent calls hit `sys.modules` (negligible). For subprocess spawning the import is ~1,000,000x cheaper than the spawn itself.
5. **Prefer function-local imports over threading a parameter** through intermediate functions that don't use it — that is what ambient context (contextvars/logging/config) is for. Reserve parameters for true call-level arguments.

#### B. Lazy exports to widen an SDK surface safely

1. **Identify peer classes** in submodules that belong in the public SDK but are missing from `__all__` (follow `PeerClass` + `PeerClassOptions` naming).
2. **Extend the `TYPE_CHECKING` block** with conditional imports (alphabetical; import class + Options together) so type hints resolve without eager loading.
3. **Update `__all__`** — add every entry, sorted alphabetically case-sensitively (uppercase first), each appearing exactly once.
4. **Extend `_LAZY_EXPORTS`** — map each name → module path string; the package `__getattr__` resolves these on first access. Keep keys alphabetically sorted.
5. **Guard new phase modules in `_PHASE_ENTRYPOINTS`** — add the module path to the tuple so `_auto_import_on_access()` skips eager preload, preventing eager-load regressions and import-time bloat.
6. **Add a surface-pinning test** (extend the existing `test_package_imports.py`, do not create a parallel file):
   ```python
   def test_public_surface_pins_expected_symbols() -> None:
       from hephaestus.automation import __all__
       expected = {"AddressReviewer", "AddressReviewerOptions", "CIDriver",
                   "CIDriverOptions", "PlanReviewer", "PlanReviewerOptions"}
       missing = expected - set(__all__)
       assert not missing, f"Missing peer classes in __all__: {missing}"
   ```
7. **Validate**: `pixi run pytest tests/unit/automation/ -v && pixi run ruff check ... && pixi run mypy ...`.
8. **Prefer a subset assertion (`expected - set(__all__)`) over strict equality (`set(__all__) == expected`)** for the pin. A subset assertion (`missing = expected - set(__all__); assert not missing`) catches *removed* peers (the regression you care about) but tolerates a new peer being added on `main` via an independent PR. A strict-equality pin breaks every open branch the moment any peer lands elsewhere (see section B′). If you must keep strict equality, treat the literal as a manifest that has to be re-synced on rebase.

#### B2. Resolving a lazy-export add/add rebase conflict (sibling PR landed the same widening first)

Symptom: the PR reads as "CI failing", but `gh run view` shows only runner/setup steps and **no test failure**. The real blocker is a merge conflict, not a test.

1. **Diagnose before touching CI.** When a PR is reported CI-failing with no failing test in the logs, run `gh pr view <N> --json mergeStateStatus` FIRST. `DIRTY` (or `CONFLICTING`) means a merge conflict — not a test — blocks the merge. Don't re-run CI; rebase.
2. **Fetch and rebase** onto the advanced main: `git fetch origin main && git rebase origin/main`. The conflict localises to `__init__.py`'s `_LAZY_EXPORTS` dict where both branches added the *same* export line (e.g. both added `"PRReviewer": "hephaestus.automation.pr_reviewer"`).
3. **Keep ONE copy.** Both sides want the identical line — delete the duplicate, keep a single entry. Verify main already carries it: `git show origin/main:hephaestus/automation/__init__.py | grep PRReviewer`.
4. **Don't fight dict key ORDER.** The surface-pinning tests use `set()` equality and `<=` subset checks (see `test_public_surface_pins_expected_symbols`), so `_LAZY_EXPORTS` / `__all__` key order does not affect pass/fail. A richer branch-side `EXPECTED_PUBLIC_SYMBOLS` identity test coexists with main's test — no dedup needed.
5. **Continue and re-verify**: `git rebase --continue`, then run the FULL suite (`pixi run python -m pytest tests/`) — a surface change can ripple. Then `pre-commit run --all-files`: **ruff-format may reformat a line that was fine on the old base** (e.g. collapse a multi-line f-string assertion). Re-run pre-commit until clean and commit the format fix with `git commit -S` (committer email MUST be the GPG key's email, e.g. `4211002+mvillmow@users.noreply.github.com`, or pr-policy signing fails; use the default GPG format, NOT SSH — SSH-signed commits can trip a false-NOGO in the automation reviewer when local git can't verify them without an `allowedSignersFile`).
6. **Push needs `--force-with-lease`** because the rebase rewrote history.
7. **Stale/duplicate-issue smell**: if main *already* contains the change your branch was trying to make, the branch may be partly redundant — but its test improvements can still be worth keeping. Keep the richer tests, drop only the now-duplicate production change.

#### B′. Repairing a stale surface-pin test after a parallel-PR peer landed

A strict-equality surface pin (`assert set(automation.__all__) == expected`) fails on CI with `Extra items in the left set: '<Symbol>'` when `<Symbol>` was added to `__all__` on `main` by an independent PR while your branch was open. The source is correct; the *test literal* is the stale party. Procedure:

1. **Confirm the failure is real and isolate the symbol.** `gh pr view <pr> --json state,statusCheckRollup` to confirm OPEN + which checks fail (here: `unit-tests` on every Python leg). Then `gh run view --job <id> --log-failed | grep -iE "FAILED|AssertionError"` to find the single failing test among thousands. The pytest set-diff (`Extra items in the left set: '<Symbol>'`) names the exact symbol.
2. **Decide test-vs-source before editing either** — the critical step. Prove whether `<Symbol>` is a legitimate export or an accidental addition:
   ```bash
   git log --oneline -- hephaestus/automation/__init__.py     # when/how did <Symbol> enter __all__?
   git log -p -1 -- hephaestus/automation/__init__.py          # the landing commit + its PR/message
   ```
   If `<Symbol>` landed via a separate, legitimate feature PR on `main` (e.g. `AuditReviewer` via #1067), the **test is stale, not the source**. Do NOT remove `<Symbol>` from `__all__` — that would silently shrink the public surface.
3. **Fix the test literal only.** Add `<Symbol>` to the `expected` set, alphabetically placed. Zero production code changes.
4. **Discriminate real CI failures from live-session environment noise.** A full *local* suite run inside a live Claude Code automation session can show extra failures that CI does not. Two cheap discriminators:
   ```bash
   # (a) env-var leakage (e.g. HEPH_*_MODEL set in the live session):
   env -i HOME="$HOME" PATH="$PATH" pixi run pytest <path>::<test> -q   # PASS under env -i ⇒ environmental
   # (b) your-change-vs-pre-existing: stash your diff, re-run on the clean base:
   git stash && pixi run pytest <path> -q ; git stash pop            # still fails ⇒ pre-existing, not yours
   ```
   Decisive tiebreaker: `gh run view --job <id> --log | grep <testname>` — if the test **PASSED in CI**, the local failure is environment-only (CI has no live `gh` auth and no `HEPH_*_MODEL` env vars). Lesson: when the local suite shows MORE failures than CI, verify each against the CI log before attributing any of them to your change.
5. **Harden the pin** so the next parallel PR doesn't re-break it: switch the assertion to a subset check (step 8 above), or accept that the strict literal is a manifest requiring a rebase-time re-sync.

#### C. Version-gated stdlib import guard (newer-Python module on older matrix)

1. **Audit**: `grep -rn "^import tomllib" hephaestus/ scripts/ tests/`.
2. **Replace each bare import** with a `sys.version_info` guard (mypy narrows on this; a bare `try/except` does not):
   ```python
   import sys
   if sys.version_info >= (3, 11):
       import tomllib
   else:
       import tomli as tomllib  # type: ignore[no-redef]
   ```
3. **Declare the backport** as a conditional dependency in `pyproject.toml` (`"tomli; python_version < '3.11'"`) and, if used, `pixi.toml` (`tomli = { version = ">=2.0", python = "<3.11" }`).
4. **Run** `pixi run pytest tests/unit` and confirm collection succeeds on both the lowest and highest Python in the matrix.
5. **If mypy on 3.11+ flags the redefinition or an unused ignore**, use `# type: ignore[no-redef, unused-ignore]` on the `else`-branch import.

General pattern + known backports:

| Module | Added in | Backport package |
|--------|----------|-----------------|
| `tomllib` | 3.11 | `tomli` |
| `ExceptionGroup` | 3.11 | `exceptiongroup` |
| `importlib.resources` (new API) | 3.9 | `importlib_resources` |
| `zoneinfo` | 3.9 | `backports.zoneinfo` |
| `graphlib` | 3.9 | `graphlib_backport` |

#### D. POSIX-only stdlib guards for Windows CI

1. **Find every POSIX-only import**: `curses`, `fcntl`, `termios`, `grp`, `pwd`, `resource`, `syslog`, `readline`. Each needs a guard.
2. **Wrap at module top-level** with `try/except ModuleNotFoundError` (only this exception — never bare `except:`) and assign `None`:
   ```python
   try:
       import curses
   except ModuleNotFoundError:  # Windows: curses not bundled with CPython
       curses = None  # type: ignore[assignment]
   ```
3. **Move the "unavailable" error to runtime** (class `__init__` / function entry), not import time, so the package imports cleanly on Windows and only the POSIX path raises.
4. **Guard every call site** with `if <module> is not None:`; treat absent locks as best-effort no-ops:
   ```python
   def _acquire_lock(fp) -> None:
       if fcntl is not None:
           fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
       # else: cross-process locking is a best-effort no-op on Windows
   ```
5. **For `zoneinfo`**: add `"tzdata; platform_system == 'Windows'"` to `[project].dependencies`; `ZoneInfo` discovers the wheel automatically.
6. **Scope tests honestly**: runtime guards make the package *importable* on Windows, not the POSIX-only CLIs *functional*. Skip those tests on Windows via `pytest.skip(...)` rather than scattering inline `if sys.platform == "win32"` assertions.
7. **Track the full cross-OS port as a separate issue** (file-mode bits, path encoding, coredump handlers). Keep the matrix ubuntu-only until that lands; keep the import guards so downstream consumers stay Windows-importable.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Module-level child→parent import | `from hephaestus.logging.utils import get_current_correlation_id` at top of `helpers.py` | `CircularImportError`/`ImportError` at startup because `logging.utils` already imports `utils.helpers` | Any child-to-parent import at module level creates a cycle if the parent imports the child; use a function-local import |
| Thread correlation ID as a parameter | `run_subprocess(cmd, cid=None)` plumbed through the call chain | Intermediate functions must accept a param they never use; refactor becomes painful | Reserve parameters for true call-level args; use ambient context (contextvars) for ambient state |
| Move the helper function to dodge the edge | Relocate `get_current_correlation_id()` into `utils` | Creates a god-module, couples `utils.helpers` to logging concerns, violates SRP | Move the import, not the function — keep it where it semantically belongs |
| Eager-load new phase modules in `__init__.py` | `from .address_reviewer import AddressReviewer` directly | Defeats lazy loading, increases import time, breaks the established pattern | Use `_LAZY_EXPORTS` + `__getattr__` and add the module to `_PHASE_ENTRYPOINTS` |
| Create a parallel surface test file | New `test_package_surface.py` to pin `__all__` | DRY violation — existing `test_package_imports.py` already iterates `__all__` | Extend existing test coverage; don't duplicate iteration logic |
| Pin the surface with strict equality | `assert set(automation.__all__) == {hardcoded literal}` authored on the feature branch | `AuditReviewer` landed on `main` via independent PR #1067 while the branch was open; CI failed on ALL Py legs with `Extra items in the left set: 'AuditReviewer'`. The source `__all__` was correct; the test literal went stale (branch-divergence / merge-skew) | A strict-equality pin breaks every open branch the instant a peer lands elsewhere. Prefer a subset assertion (`expected - set(__all__)`) that catches removals but tolerates parallel additions; if you keep equality, re-sync the literal on rebase |
| "Fix" the stale pin by editing the source | Considered removing `AuditReviewer` from `__all__` to satisfy the failing equality assertion | Would have silently shrunk the public SDK surface — `AuditReviewer` is a legitimate peer export added by #1067 | Decide test-vs-source BEFORE editing: `git log -p -1 -- __init__.py` proved the symbol was a real, separately-landed export. Fix the stale TEST literal, never the correct source |
| Trust the local suite over the CI log | Saw 3 local failures and assumed all 3 were caused by my change | 2 were live-session environment noise: `HEPH_*_MODEL` env vars set in the session, and live `gh` auth leaking real PR data past a mock. Only 1 (`test_public_surface_pins_expected_symbols`) was the genuine CI failure | When local shows MORE failures than CI, verify each against the CI log. `env -i HOME=$HOME PATH=$PATH pytest` isolates env-var leakage; `git stash` isolates pre-existing failures; `gh run view --log \| grep <test>` is the decisive tiebreaker (those 2 PASSED in CI) |
| Re-run CI on a "CI failing" lazy-export PR with no failing test | Assumed a flaky/red check and triggered `gh run rerun` | The blocker was a merge conflict (`mergeStateStatus=DIRTY`), not a test; logs showed only runner setup | When a PR reads CI-failing but no test failed, check `gh pr view <N> --json mergeStateStatus` FIRST — `DIRTY` means rebase, not re-run |
| Treat the duplicated `_LAZY_EXPORTS` entry as a real merge of two different lines | Tried to keep both sides of the add/add conflict | Both branches added the *identical* export (sibling PR #968 landed it first); keeping both yields a duplicate key | Keep ONE copy; verify with `git show origin/main:<__init__> \| grep <symbol>` |
| Reorder `_LAZY_EXPORTS`/`__all__` keys to "match main" during the conflict | Fought over dict key ordering to make tests pass | Surface tests use `set()` equality / `<=` subset, so order never affected pass/fail — wasted effort | Order-insensitive surface tests mean you only need set-membership correct, not key order |
| Commit the resolved rebase without re-running pre-commit | Assumed code clean on the old base stays clean post-rebase | `ruff-format` reflowed a multi-line f-string assertion onto one line on the new base → pre-commit failed | Always re-run `pre-commit run --all-files` after a rebase; ruff-format is base-sensitive |
| `git push` the rebased branch normally | Plain push after a history-rewriting rebase | Non-fast-forward rejection (rebase rewrote history) | Push rebased branches with `--force-with-lease` |
| Bare `import tomllib` assuming 3.11+ matrix | Used stdlib `tomllib` directly | Matrix also ran 3.10; collection failed with `ModuleNotFoundError: No module named 'tomllib'` | Always check the lowest Python in the matrix before using newer stdlib modules |
| `try/except ImportError` instead of version guard | `try: import tomllib except ImportError: import tomli as tomllib` | Works at runtime but mypy cannot statically narrow the type; false positive on 3.11+ | Use `sys.version_info >= (3, 11)` — mypy treats it as a narrowing predicate |
| Skip declaring the backport dependency | Did not add `tomli; python_version < '3.11'` | `tomli` absent in fresh CI env → `ModuleNotFoundError: No module named 'tomli'` | Declare backports as conditional deps in both `pyproject.toml` and `pixi.toml` |
| Leave POSIX-only imports bare on Windows | `import curses`/`import fcntl` at top level, let CI surface it | `ModuleNotFoundError` broke the whole subpackage at import time, cascading into unrelated-looking entry-point/integrity checks | stdlib ≠ always available; POSIX-only stdlib needs the same guard as any optional dep |
| Enable full OS matrix after only fixing imports | `[ubuntu, macos, windows]` after curses/fcntl/tzdata fixes | Windows still failed on file-mode bits, path encoding, POSIX-only signal/coredump tests | Runtime import guards don't fix tests that encode POSIX assumptions; full port is multi-session |
| Inline per-test Windows skips | Ad-hoc `if sys.platform == "win32"` branches in each failing test | Death-by-a-thousand-cuts; sprawling diff, obscured scope | Track cross-OS port as a dedicated issue; revert matrix to ubuntu-only; keep the import guards |

## Results & Parameters

### Function-local import — before/after and cost

```python
# AFTER (acyclic): parent imports child at top-level (OK); child imports parent locally
# hephaestus/utils/helpers.py
def run_subprocess(cmd):
    from hephaestus.logging.utils import get_current_correlation_id  # ✅ LOCAL
    cid = get_current_correlation_id()
    ...
```

| Strategy | Circular Dep Risk | Startup Time | Per-Call Cost | Best For |
|----------|------------------|--------------|---------------|----------|
| Module-level | High (creates cycle) | Slower | O(1) cache | Non-circular dependencies |
| Function-local | None | Faster | O(1) cache (after first ~3–5µs) | Ambient state, one-off imports |
| Parameter passing | None | Faster | O(1) | True call-level arguments |

### Lazy exports — expected test output

```text
tests/unit/automation/test_package_imports.py::test_can_import_all_exports PASSED
tests/unit/automation/test_package_imports.py::test_lazy_exports_dict_sorted PASSED
tests/unit/automation/test_package_imports.py::test_all_in_lazy_exports PASSED
tests/unit/automation/test_package_imports.py::test_no_circular_imports PASSED
tests/unit/automation/test_package_imports.py::test_public_surface_pins_expected_symbols PASSED
======================== 9 passed in 0.45s ========================
```

`__all__`, `_LAZY_EXPORTS` keys, and `TYPE_CHECKING` imports must all be alphabetically sorted (case-sensitive, uppercase first). `_PHASE_ENTRYPOINTS` order does not matter (membership check only).

### Stale surface-pin — failure signature, diagnosis, and fix

CI failure signature (every Python leg, exactly one failing test):

```text
FAILED tests/unit/automation/test_package_imports.py::test_public_surface_pins_expected_symbols
    assert set(automation.__all__) == expected
E   Extra items in the left set:
E     'AuditReviewer'
```

Diagnose test-vs-source, then fix the test (not the source):

```bash
# 1. Confirm OPEN + which checks fail
gh pr view 968 --json state,statusCheckRollup

# 2. Find the single failing test among thousands
gh run view --job <job-id> --log-failed | grep -iE "FAILED|AssertionError"

# 3. Reproduce locally — the set-diff names the exact symbol
pixi run python -m pytest tests/unit/automation/test_package_imports.py::test_public_surface_pins_expected_symbols -v

# 4. PROVE the symbol is a legitimate, separately-landed export (decides test-vs-source)
git log --oneline -- hephaestus/automation/__init__.py   # AuditReviewer entered via PR #1067 on main
git log -p -1 -- hephaestus/automation/__init__.py        # "feat(automation): add audit reviewer..."
```

The fix is one line in the TEST, alphabetically placed, with zero source change:

```python
expected = {
    "AddressReviewer",
    "AuditReviewer",   # ← added: legitimate peer that landed on main via #1067
    "CIDriver",
    # ...
}
```

Separating the real CI failure from live-session environment noise (3 local failures, only 1 genuine):

```bash
# env-var leak (HEPH_PLANNER_MODEL / HEPH_IMPLEMENTER_MODEL / HEPH_REVIEWER_MODEL set in the live session)
env -i HOME="$HOME" PATH="$PATH" pixi run pytest \
    tests/unit/automation/test_loop_runner.py::test_phase_env_model_vars_only_when_non_empty -q   # PASS ⇒ environmental

# pre-existing vs your-change (live gh auth leaked 24/40 real PRs past the mock)
git stash && pixi run pytest tests/unit/automation/test_ci_driver_prs_mode.py -q ; git stash pop  # same fail ⇒ not yours

# decisive tiebreaker: all 3 noise tests PASSED in CI (no live gh auth, no HEPH_*_MODEL there)
gh run view --job <job-id> --log | grep -E "test_phase_env_model_vars_only_when_non_empty|test_ci_driver_prs_mode"
```

### Version-gated guard — expected output & type-ignore

```text
$ pixi run pytest tests/unit -q --tb=no
2590 passed, 2 skipped in 168.87s
```

Collection must succeed on both 3.10 and 3.11+ legs. On 3.11+ mypy knows the `else` is unreachable, so suppress with both codes:

```python
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef, unused-ignore]
```

### POSIX-only guard — verified-passing pattern

```python
try:
    import fcntl
except ModuleNotFoundError:  # Windows: fcntl is POSIX-only
    fcntl = None  # type: ignore[assignment]

def _acquire_lock(fp) -> None:
    if fcntl is not None:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
    # cross-process locking is best-effort no-op on Windows

def _release_lock(fp) -> None:
    if fcntl is not None:
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
```

```python
# tests/integration/test_entry_points.py
POSIX_ONLY_SUBPACKAGES = ("automation",)

def test_entry_point_importable(module_path: str) -> None:
    if sys.platform == "win32" and any(p in module_path for p in POSIX_ONLY_SUBPACKAGES):
        pytest.skip("automation CLIs require POSIX stdlib (curses/fcntl)")
    importlib.import_module(module_path)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — correlation_id propagation | Function-local import of `get_current_correlation_id` in `hephaestus/utils/helpers.py:170-172`; lint passes with no `noqa` |
| ProjectHephaestus | Issue #799 / PR #988 — lazy-export add/add rebase conflict | Branch `799-auto-impl` widened `_LAZY_EXPORTS`/`__all__` in `hephaestus/automation/__init__.py`; main had already added the same `"PRReviewer"` entry via #968/#775 → PR read CI-failing but `mergeStateStatus=DIRTY` was the real blocker. Rebased onto origin/main (only `__init__.py` conflicted; `test_package_imports.py` rebased clean), kept ONE `"PRReviewer"` copy, set()-based surface tests ignored key order. Full suite 4136 passed / 19 skipped; pre-commit reflowed one f-string line; GPG-signed. **verified-local** |
| ProjectHephaestus | Issue #775 / PR #968 — widen automation SDK surface | Exposed PlanReviewer, AddressReviewer, CIDriver (+Options) via `__all__`/`_LAZY_EXPORTS`/`_PHASE_ENTRYPOINTS`; surface-pinning test; 1081 automation tests pass |
| ProjectHephaestus | Issue #775 / PR #968 vs #1067 — stale surface-pin repair | `test_public_surface_pins_expected_symbols` failed on every Py leg with `Extra items in the left set: 'AuditReviewer'`; `AuditReviewer` was a legitimate peer added on `main` by independent PR #1067. Fixed the stale test literal (one-line add, alphabetised), zero source change. `verified-local` — CI re-run confirmation pending. 2 sibling local failures (`HEPH_*_MODEL` env leak; live `gh` auth past a mock) proven environmental via `env -i` + `git stash` + grep-the-CI-log |
| ProjectHephaestus | PR #657 — fix broken main CI | `sys.version_info` guard for `tomllib`/`tomli` in `tests/unit/ci/test_bandit_config.py`; conditional deps in `pyproject.toml`/`pixi.toml`; 2590 tests pass |
| ProjectHephaestus | PRs #534, #536, #538 (issue #539 tracks full port) — Windows-importability | curses guard in `CursesUI`, fcntl guard in `planner.py`, `tzdata` for `hephaestus.github.rate_limit` |
