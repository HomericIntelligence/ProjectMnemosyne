---
name: python-import-patterns-and-compatibility-guards
description: "Use when: (1) a child module would create circular dependencies by importing the parent at module level — use function-local imports to defer the lookup and keep the import graph acyclic; (2) extending a public SDK surface with peer classes using lazy-loading __init__.py infrastructure (lazy exports pattern via __getattr__) to prevent eager-load regressions when adding new peers to __all__; (3) code uses a stdlib module added in a later Python version (tomllib in 3.11+, ExceptionGroup in 3.11+) and the CI matrix includes older Python — add a version-gated try/except import guard so the module remains importable; (4) adding cross-OS CI matrix and Windows jobs fail with ModuleNotFoundError for POSIX-only stdlib modules (curses, fcntl, grp, tzdata) — add conditional import guards and ensure tzdata is listed as an optional Windows dependency; (5) a hardcoded surface-pinning test (set(__all__) == literal) fails on CI with 'Extra items in the left set' because a peer export landed on main via an independent PR while your branch was open — fix the stale test literal, not the (correct) source, and use env -i / git stash / grep-the-CI-log to separate real failures from live-session environment noise; (6) a branch widening a lazy SDK surface (_LAZY_EXPORTS/__all__/__getattr__ in __init__.py) goes DIRTY/CONFLICTING on rebase because a sibling PR already landed the identical export — resolve by keeping ONE copy of the shared entry, and FIRST check mergeStateStatus=DIRTY when a PR reads as CI-failing but no test actually failed; (7) adding a DeprecationWarning at ACCESS time (not just call time) for a deprecated lazy shim exposed via a PEP 562 package __getattr__ loader — grep the named symbol against the source first because the issue may misname the mechanism (in _LAZY_IMPORTS vs __all__), keep access-time and call-time warnings as complementary layers (both needed for different access paths), force a fresh resolve in the regression test via module.__dict__.pop(name) because PEP 562 caches into globals, rewrite any stale-tolerant test that documents the current silent behavior, use stacklevel=2 inside __getattr__ (verified: user line → __getattr__ → warn, so stacklevel=2 attributes to user's access line), and update the prose deprecation doc (COMPATIBILITY.md) in the same PR (verified-local, ProjectHephaestus issue #1545); (8) EXECUTING an audit-finding fix that PROMOTES existing public-looking symbols into a package's declared __all__ — scope creep is intentional: when the issue names a subset of affected symbols but the same defect class applies to sibling symbols in the same module, fix ALL of them in one PR (e.g. issue #1511 named add_dry_run_arg + DRY_RUN_HELP_CAVEAT but add_github_throttle_args + configure_github_throttle_from_args had the identical gap; fixing all four so set(utils.__all__) == set(cli.__all__) prevents re-triggering the same audit finding); choose EAGER re-export (plain 'from … import (…)' in __init__.py) when the source module pulls only stdlib — no need for _LAZY_EXPORTS infrastructure; NO COMPATIBILITY.md change is needed when the package has no per-symbol table (only a tier entry); pin the test with a SUBSET ASSERTION (set(submodule.__all__) - set(pkg.__all__) must be empty, not strict equality) so parallel PRs adding new symbols cannot break the pin; do NOT guess the COMPATIBILITY.md 'Added' version from the latest git tag (check RELEASING.md/milestones/roadmap or flag for reviewer), grep the WHOLE test tree (not just the obvious file) for a strict-equality surface pin before widening __all__ because the breakage is non-local, verify the audit's stability-tier premise on disk (audit findings can be factually wrong), assert re-export IDENTITY (pkg.sym is submodule.sym) and grep for existing patch(\"pkg.submodule...\") usages, and include test_import_surface.py/test_automation_boundary.py in the verification set for any __init__.py widening (verified-local, executed end-to-end for ProjectHephaestus issue #1511; planning-guidance for COMPATIBILITY.md version-stamping derived from plan for issue #1513 remains unverified); (9) PLANNING the companion module-level __dir__() for a PEP 562 lazy-loader package whose __getattr__ lazily resolves symbols but whose dir(pkg) shows only eagerly-bound names — define __dir__() returning sorted(set(_LAZY_IMPORTS) | set(__all__) | set(globals())) so the entire lazy public API is discoverable to IPython tab-completion / IDEs / doc generators; CRITICAL: a custom __dir__ REPLACES (does not merge with) the default listing, so you MUST fold set(globals()) in or you silently REMOVE today-visible names (__version__, __author__, dunders, already-cached lazy names); __dir__ returns names only and performs NO attribute access, so a deprecated lazy shim can be listed without firing its DeprecationWarning; pin the contract by SUBSET INVARIANT (set(_LAZY_IMPORTS) <= set(dir(pkg))) not a hardcoded count (the audit's '35 symbols' was already stale at 40); regression-test that dir() does not SHRINK the visible set; extend the existing surface test file, do not create a parallel one (unverified planning-guidance, derived from a plan for ProjectHephaestus issue #1512)."
category: architecture
date: 2026-06-24
version: "1.7.0"
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
  - deprecation-warning
  - access-time-warning
  - pep-562
  - getattr
  - stale-tolerant-test
  - doc-drift
  - stacklevel
  - warnings-warn
  - audit-finding
  - surface-promotion
  - version-stamping
  - stability-docs
  - re-export-identity
  - import-surface-boundary
  - dir
  - __dir__
  - discoverability
  - introspection
---

# Python Import Patterns and Compatibility Guards

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Manage the Python import graph and import compatibility across versions and platforms: avoid circular dependencies with function-local imports, extend public SDK surfaces via lazy exports without eager-load regressions, guard stdlib imports that vary by Python version or OS, keep hardcoded surface-pinning tests from going stale when peers land via parallel PRs, and emit an access-time `DeprecationWarning` across the PEP 562 lazy-loader seam |
| **Outcome** | Acyclic import graphs, Windows-importable packages, CI matrices green on older Python and POSIX-only stdlib, lazy SDK surfaces that scale to new peer classes, a decision procedure for fixing stale pinned-`__all__` tests (test vs source) without chasing live-session environment noise, and a verified workflow for emitting a deprecation warning at `__getattr__` access time — confirming `stacklevel=2` is correct, `module.__dict__.pop(name)` busts the PEP 562 cache, both access-time and call-time warning layers are needed, the stale-tolerant test must be rewritten not supplemented, and `COMPATIBILITY.md` must be updated in the same PR |
| **Verification** | verified-ci (function-local / version-guard / Windows-guard / lazy-exports); verified-local (surface-pin-stale fix, access-time deprecation-warning implementation — section F executed end-to-end with all tests passing locally; section G — __all__ alignment / eager re-export / subset-assertion pin executed end-to-end for ProjectHephaestus issue #1511, all tests passing locally; CI pending after ProjectHephaestus PRs merge); **unverified** planning-guidance (COMPATIBILITY.md version-stamping within section G derived from a plan for ProjectHephaestus issue #1513, not yet executed in CI; section H — adding the companion `__dir__()` to a PEP 562 lazy-loader package; derived from a plan for ProjectHephaestus issue #1512, not yet executed in CI) |

## When to Use

- **Function-local imports (coupling avoidance)**: A child module needs ambient state from a parent module (e.g., `logging.utils` already imports `utils.helpers`), and a module-level child-to-parent import would create a circular dependency or import-graph bloat. The import is used in only one or two functions.
- **Lazy exports (SDK surface)**: Extending a public package `__all__` with peer classes from submodules, adding `TYPE_CHECKING` imports, preventing eager-load regressions, or avoiding architectural restructuring when widening the public surface.
- **Version-gated stdlib guard**: A CI matrix includes Python 3.10 and code does a bare import of a 3.11+ stdlib module (`tomllib`, `ExceptionGroup`); `pytest` collection fails with `ModuleNotFoundError` on the lowest Python in the matrix.
- **Windows / POSIX-only stdlib guard**: Adding a cross-OS CI matrix where Windows jobs fail with `ModuleNotFoundError` for `curses`/`fcntl`/`termios`/`grp`/`pwd`, or `zoneinfo.ZoneInfo` raises `ZoneInfoNotFoundError` on Windows (needs `tzdata`).
- **Lazy-export add/add rebase conflict**: A branch widens the lazy SDK surface (`_LAZY_EXPORTS` + `__all__` + `__getattr__`) and goes `DIRTY`/`CONFLICTING` because a *sibling PR already landed the identical export* on main. The PR reads as "CI failing" but the logs show only runner/setup steps and **no test actually failed** — the merge conflict itself is the blocker. Resolve by keeping ONE copy of the shared entry.
- **Stale surface-pin test (branch-divergence / merge-skew)**: A hardcoded surface-pinning test (`assert set(__all__) == {literal}`) fails on CI with `Extra items in the left set: '<Symbol>'`, where `<Symbol>` is a *legitimate* peer export that landed on `main` via an independent PR while your feature branch was open. The production `__init__.py` is correct; the test literal went stale. You need to decide whether the test or the source is wrong, then fix only the stale party — and to do that you must separate the real CI failure from environment noise that only appears when the local suite runs inside a live automation session.
- **Access-time deprecation warning across the lazy-loader seam (verified-local)**: You need to make a deprecated lazy shim (e.g. `retry_with_jitter`) warn at *attribute-access* time, not only when called, by adding a `warnings.warn(...)` inside the package `__getattr__` / `_LAZY_IMPORTS` resolver. Key verified facts: the issue may misname *where* the symbol lives (`_LAZY_IMPORTS` vs `__all__`) — grep first; the existing call-time warning is a *different* layer covering a different access path (keep both); PEP 562 caches the resolved name into module globals so the access warning fires once per process — the test must `module.__dict__.pop(name, None)` to re-trigger `__getattr__`; `stacklevel=2` IS correct inside `__getattr__` (call stack: user access line → `__getattr__` → `warnings.warn`); an existing regression test that documents the current silent resolve must be *rewritten*, not supplemented; and a prose doc (`COMPATIBILITY.md`) describing the warning as firing "when called" must be updated in the same PR.
- **Promoting undeclared public-looking symbols to the package surface — audit-finding fix (verified-local for __all__ alignment; unverified for COMPATIBILITY.md version-stamping)**: One or more existing, public-looking functions are present in a submodule but absent from the package `__init__.py`'s `__all__`, so `from pkg import sym` fails for external users while internal callers work around it by importing from the submodule directly. Key verified patterns from ProjectHephaestus issue #1511 (`hephaestus/cli/__init__.py` aligned with `hephaestus/cli/utils.py`): **expand scope** from the named symbols to ALL missing symbols when the same defect class applies — fixing all four (`DRY_RUN_HELP_CAVEAT`, `add_dry_run_arg`, `add_github_throttle_args`, `configure_github_throttle_from_args`) prevented re-triggering the same audit finding; choose **eager re-export** (`from hephaestus.cli.utils import (…)` in `__init__.py`) when the source module pulls only stdlib — no `_LAZY_EXPORTS` infrastructure needed; **no COMPATIBILITY.md change** is needed when the package has no per-symbol table (only a tier-level entry at the package level); pin the test with a **subset assertion** (`set(utils.__all__) - set(cli.__all__)`) so parallel PRs adding new symbols cannot break it; always include `test_import_surface.py`/`test_automation_boundary.py` in the verification set. Additional planning traps (from a plan for ProjectHephaestus issue #1513 — still unverified): stamping the COMPATIBILITY.md "Added" version by guessing from the latest git tag; missing a non-local strict-equality surface-pin test; building on an unverified stability-tier premise; getting the re-export binding wrong for `monkeypatch`/`mock.patch` paths. See section G.
- **Adding the companion `__dir__()` to a PEP 562 lazy-loader package — discoverability fix (unverified planning-guidance)**: A package defines a module-level `__getattr__` for lazy loading (PEP 562), but defines no module-level `__dir__()`, so `dir(pkg)` shows only the eagerly-bound names (~4: `__version__`, `__author__`, dunders) and the entire lazy public API (everything in `_LAZY_IMPORTS` / `__all__`) is invisible to IPython tab-completion, IDEs, and doc generators. This is a POLA/discoverability defect, not a correctness bug. The fix adds `def __dir__() -> list[str]: return sorted(set(_LAZY_IMPORTS) | set(__all__) | set(globals()))` and pins it with a surface test. The planning traps: a custom `__dir__` REPLACES the default listing (it does not auto-union module globals), so you MUST fold `set(globals())` in or you silently SHRINK the visible set; `__dir__` returns names only (no attribute access), so listing a deprecated lazy shim does NOT fire its `DeprecationWarning`; pin by a SUBSET INVARIANT (`set(_LAZY_IMPORTS) <= set(dir(pkg))`), never a hardcoded count (the audit's "35 symbols" was already stale at 40 on disk); and regression-test that `dir()` does not SHRINK vs today (`__version__`/`__author__` must remain). See section H. (Derived from a plan for ProjectHephaestus issue #1512; this guidance is `unverified` — the plan has not been executed in CI.)

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

#### F. Verified Workflow — adding an access-time DeprecationWarning across the PEP 562 lazy-loader seam (verified-local)

> **Verification:** This workflow was executed end-to-end for ProjectHephaestus issue #1545 (warn at *access* time, not only call time, for the deprecated `retry_with_jitter` shim exposed via `hephaestus/__init__.py`'s PEP 562 `__getattr__` loader). All steps below are verified locally — tests pass, ruff and mypy clean. CI confirmation pending after the ProjectHephaestus PR merges. Verification level = `verified-local`.

1. **Grep the named symbol against the source BEFORE trusting the issue's structural claim.** Issue #1545 said the shim was "in `__all__`", but `retry_with_jitter` is actually only in `_LAZY_IMPORTS` (the lazy resolver map), not `__all__`. The fix location — the `__getattr__` lazy-loader seam — is the same either way, but you must understand where the symbol actually lives before editing.
   ```bash
   grep -n "retry_with_jitter" hephaestus/__init__.py   # is it in _LAZY_IMPORTS or __all__? (here: _LAZY_IMPORTS only)
   grep -rn "def retry_with_jitter" hephaestus/         # where the real impl + any call-time warning lives
   ```

2. **Treat access-time and call-time warnings as COMPLEMENTARY layers, not duplicates — keep both.** A deprecated shim may already warn *inside its function body* (fires on `hephaestus.utils.X` direct call). Adding a warning in the package `__getattr__` covers a *different* access path — binding `hephaestus.X` via attribute lookup, even if the symbol is never called. Different users hit different paths; do NOT "dedup" them.

3. **Add a `_DEPRECATED_LAZY` dict alongside `_LAZY_IMPORTS` and check it inside `__getattr__`.** The warning message should name the canonical replacement. Defer the `import warnings` inside the condition — it is stdlib, safe, and does not breach the automation boundary (`test_automation_boundary.py` confirmed):
   ```python
   # hephaestus/__init__.py — add after _LAZY_IMPORTS closes
   _DEPRECATED_LAZY: dict[str, str] = {
       "retry_with_jitter": (
           "hephaestus.retry_with_jitter is deprecated; use "
           "retry_with_backoff(jitter=True, max_delay=...) instead. "
           "It will be removed no earlier than the next major version after 1.0."
       ),
   }

   def __getattr__(name: str) -> Any:
       """Lazy-load public symbols on first access (PEP 562)."""
       if name in _LAZY_IMPORTS:
           if name in _DEPRECATED_LAZY:
               import warnings
               warnings.warn(_DEPRECATED_LAZY[name], DeprecationWarning, stacklevel=2)
           module_name, attr = _LAZY_IMPORTS[name]
           import importlib
           module = importlib.import_module(module_name)
           value = getattr(module, attr)
           globals()[name] = value
           return value
       raise AttributeError(f"module 'hephaestus' has no attribute {name!r}")
   ```

4. **`stacklevel=2` IS correct for `__getattr__` — verified.** The call stack when a user writes `hephaestus.retry_with_jitter` is: (1) user's access line → (2) `__getattr__` → (3) `warnings.warn`. `stacklevel=2` skips `__getattr__` (frame 2) and attributes the warning to frame 1 (the user's line). Confirmed by asserting `access_warnings[0].filename == __file__` in the test.

5. **Force a fresh resolve in the regression test — PEP 562 `__getattr__` caches into module globals.** After the first `hephaestus.retry_with_jitter` access, the resolved name is written into the module's `__dict__`, so `__getattr__` (and the access warning) never runs again that process. A prior test that already touched the symbol makes the warning assertion a false-negative. Pop it first:
   ```python
   def test_retry_with_jitter_access_emits_deprecation_warning(self) -> None:
       import hephaestus

       # Bust PEP 562 cache — force __getattr__ to re-run
       hephaestus.__dict__.pop("retry_with_jitter", None)

       with warnings.catch_warnings(record=True) as caught:
           warnings.simplefilter("always")
           symbol = hephaestus.retry_with_jitter  # ACCESS only, do not call

       assert callable(symbol)
       access_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
       assert access_warnings, "Accessing hephaestus.retry_with_jitter must emit DeprecationWarning"
       assert "retry_with_jitter" in str(access_warnings[0].message)
       # stacklevel=2 must attribute the warning to the caller's file
       assert access_warnings[0].filename == __file__, (
           f"DeprecationWarning should be attributed to the caller's file "
           f"({__file__}); got {access_warnings[0].filename}. Check stacklevel."
       )
   ```

6. **Grep for stale-tolerant tests that ASSERT the about-to-change behavior, then REWRITE them — a change is not "additive" if a passing test documents the old contract.** The existing test `test_retry_with_jitter_reachable_from_top_level_lazy_loader` explicitly documented and tolerated the silent lazy resolve ("the lazy resolve itself is silent; only CALLING warns"). It had to be replaced, not supplemented — its docstring said the old behavior was intentional.
   ```bash
   grep -rn "silent\|lazy resolve\|only CALLING\|does not warn" tests/ | grep -i deprecat
   ```

7. **Update the prose deprecation doc in the SAME PR — behavior/doc drift is a review trap.** `COMPATIBILITY.md` had a bullet stating the warning fires "when called". Update it to reflect that the warning now fires both when accessed via `hephaestus.retry_with_jitter` AND when called.

8. **Re-confirm the import-surface boundary still holds.** Adding `import warnings` inside `__getattr__` is low-risk (`warnings` is stdlib, deferred inside the condition), but run `test_import_surface.py` and `test_automation_boundary.py` after the change — both passed for issue #1545.

#### G. Promoting undeclared public-looking symbols to the package surface (audit-finding fix) — verified-local for __all__ alignment; unverified for COMPATIBILITY.md version-stamping

> **Verification:** `verified-local` for `__all__` alignment, eager re-export, subset-assertion pin, and import-surface/boundary boundary checks — these steps were executed end-to-end for ProjectHephaestus issue #1511 (`hephaestus/cli/__init__.py` aligned with `hephaestus/cli/utils.py`; 79 tests passed; mypy/ruff/test_import_surface/test_automation_boundary all clean). COMPATIBILITY.md version-stamping guidance remains `unverified` — derived from a plan for ProjectHephaestus issue #1513, not yet executed in CI.

When you fix a defect where symbols are declared in a submodule `__all__` but not re-exported from the package `__init__.py`, the symbol-level diff is tiny but the verification blast radius is not. Work through these checks BEFORE writing the plan as fact:

**Verified concrete example (ProjectHephaestus issue #1511 — `hephaestus/cli/__init__.py`):**

```python
# hephaestus/cli/__init__.py — BEFORE (missing 4 symbols from utils.py __all__)
from hephaestus.cli.utils import (
    Colors,
    add_json_arg,
    # ... other symbols already present
)
__all__ = ["Colors", "add_json_arg", ...]

# hephaestus/cli/__init__.py — AFTER (eager re-export; stdlib-only module → no lazy machinery)
from hephaestus.cli.utils import (
    Colors,
    DRY_RUN_HELP_CAVEAT,          # string constant
    add_dry_run_arg,               # argparse helper
    add_github_throttle_args,      # argparse helper
    add_json_arg,
    configure_github_throttle_from_args,  # argparse helper
    # ... other symbols
)
__all__ = [
    "Colors",
    "DRY_RUN_HELP_CAVEAT",
    "add_dry_run_arg",
    "add_github_throttle_args",
    "add_json_arg",
    "configure_github_throttle_from_args",
    # ...
]
```

```python
# tests/unit/cli/test_utils.py — AFTER: subset-assertion pin + identity check
import hephaestus.cli as cli
import hephaestus.cli.utils as utils

def test_cli_all_covers_module_all() -> None:
    """Subset assertion: every symbol in utils.__all__ must appear in cli.__all__."""
    missing = set(utils.__all__) - set(cli.__all__)
    assert not missing, f"cli.__all__ is missing symbols from utils.__all__: {missing}"

def test_dry_run_symbols_reexport_identity() -> None:
    """Re-exported symbols must be the SAME object (identity, not just equality)."""
    assert cli.add_dry_run_arg is utils.add_dry_run_arg
    assert cli.DRY_RUN_HELP_CAVEAT is utils.DRY_RUN_HELP_CAVEAT
```

Key verified decisions from issue #1511:

- **Scope expansion is intentional**: the issue named 2 symbols; audit found the SAME defect class applied to 4. Fix all 4 so `set(utils.__all__) == set(cli.__all__)` — a partial fix re-triggers the same audit finding for the skipped symbols.
- **Eager re-export beats lazy when the module is stdlib-only**: `cli/utils.py` imports only `argparse`, `json`, `math`, `sys`, `hephaestus._version_lookup`. No `_LAZY_EXPORTS` infrastructure needed; plain `from hephaestus.cli.utils import (…)` in `__init__.py` is correct.
- **No COMPATIBILITY.md change**: `hephaestus.cli` appears only as a tier-level Stable entry at line 53; there is no per-symbol table. Nothing to update.
- **Subset assertion, not strict equality**: `set(utils.__all__) - set(cli.__all__)` catches regressions (removed symbols) but tolerates parallel PRs that add new symbols. A strict-equality pin would break the moment any sibling PR lands a new symbol.
- **Verify import-surface/boundary after any `__init__.py` widening**: `test_import_surface.py` and `test_automation_boundary.py` both passed after widening `cli/__init__.py` (no heavyweight or boundary-crossing imports were introduced).

Additional planning steps (from a plan for ProjectHephaestus issue #1513 — unverified for COMPATIBILITY.md version-stamping):

1. **Verify the COMPATIBILITY.md "Added" version against the ACTUAL next release — never guess it from the latest tag.** `git describe --tags --abbrev=0` returning `v0.9.7` does NOT mean the next release is `0.9.8`; the next version could be `0.9.8`, `0.10.0`, or `1.0.0` depending on cadence/roadmap. Stamping the wrong version silently mis-documents the stability contract. Either resolve the real target version, or flag it explicitly for the reviewer:
   ```bash
   git -C <repo> describe --tags --abbrev=0          # latest tag — NOT necessarily next version
   sed -n '1,80p' docs/RELEASING.md                  # documented release cadence / next-version policy
   gh api repos/:owner/:repo/milestones --jq '.[].title'  # an open milestone often names the target version
   ```
   If none of these resolve the next version unambiguously, write the plan with an explicit "**reviewer must confirm the target release version for the COMPATIBILITY.md 'Added' column**" callout rather than asserting a guessed number.

2. **Grep the WHOLE test tree for an existing strict-equality surface pin BEFORE widening `__all__` — the breakage is non-local.** A strict-equality pin (`assert set(pkg.__all__) == {literal}`) for the target package may live in a *different* test file than the one you are editing. If it exists, adding three symbols to `__all__` breaks THAT test, and a plan that only touches the obvious test file misses it. Grep by package name AND `__all__` AND surface/pin/expected markers across all of `tests/`:
   ```bash
   grep -rn "logging" tests/ | grep -iE "__all__|surface|pin|expected"   # find ANY pin for this package
   grep -rn "__all__" tests/ | grep -iE "==|expected|surface|pin"        # strict-equality pins anywhere
   ```
   A widening change has a non-local test blast radius — enumerate every pin that references the package, not just the test file you planned to edit.

3. **Verify the audit's stability-tier premise on disk — an audit finding's premise is itself a claim to check.** The whole fix here rests on "`hephaestus.logging` is Stable (COMPATIBILITY.md:56)". Read the actual stability-tier source and confirm the tier before building the fix around it; audit findings are sometimes factually wrong (team KB has prior cases of 3/29 strict-audit findings being factually wrong). If the subpackage is NOT actually a Stable tier, the entire "promote to stable surface" framing is wrong.
   ```bash
   grep -n "logging" COMPATIBILITY.md | grep -iE "stable|tier|experimental|deprecated"  # confirm the tier
   ```

4. **Assert re-export IDENTITY and grep for existing submodule patch paths.** When re-exporting symbols that existing tests `monkeypatch`/`mock.patch` via the submodule path, the package-root re-export MUST be the SAME object so either patch path works. Add a test asserting identity (`pkg.set_correlation_id is utils.set_correlation_id`) and grep for any test that patches the submodule path to confirm none rely on a divergent binding:
   ```bash
   grep -rn 'patch("hephaestus.logging.utils' tests/    # any monkeypatch on the submodule path?
   grep -rn "set_correlation_id\|get_current_correlation_id\|correlation_id_scope" tests/
   ```

5. **Include the import-surface/boundary tests in the verification set for ANY `__init__.py` widening — even a "pure re-export".** Adding eager re-exports to a package `__init__.py` can regress an enforced import-surface or boundary test (`test_import_surface.py`, `test_automation_boundary.py`) if the re-exported submodule pulls a heavyweight or boundary-crossing import. The plan reasoned `utils.py` only pulls stdlib + `hephaestus.constants` + formatters, which is safe — but that reasoning is a hypothesis until those tests run. Always run them after touching an `__init__.py`:
   ```bash
   pixi run pytest tests/unit/validation/test_import_surface.py tests/unit/validation/test_automation_boundary.py -q
   ```

Note on the pin choice: when ADDING the surface-pin test for the promoted symbols, prefer a subset assertion (`expected - set(__all__)`, see section B step 8) over a strict-equality pin, so this same widening pattern doesn't break future parallel branches.

#### H. Adding the companion `__dir__()` to a PEP 562 lazy-loader package — UNVERIFIED planning-guidance

> **Verification:** `unverified`. These steps were derived from an implementation *plan* for ProjectHephaestus issue #1512 — an `[S14 API Design]` audit finding that `hephaestus/__init__.py` implements PEP 562 `__getattr__` for lazy loading but omits the companion `__dir__()`, so `dir(hephaestus)` shows only ~4 eagerly-bound names and the entire lazily-loaded public API is invisible to introspection tools (IPython tab-completion, IDEs, doc generators). The plan adds a module-level `__dir__()` returning `sorted(set(_LAZY_IMPORTS) | set(__all__) | set(globals()))` and pins it with a `TestDirDiscoverability` class in the existing `tests/integration/test_package_import.py`. The plan has **not** been executed in CI; treat every step below as a checklist to confirm, not a verified outcome.

PEP 562 pairs `__dir__` with `__getattr__` for discoverability. A package that defines a module-level `__getattr__` for lazy loading should also define a module-level `__dir__() -> list[str]`, or `dir(pkg)` shows only the eagerly-bound names and the entire lazy public API is invisible to tab-completion, IDEs, and doc generators. This is a POLA/discoverability defect, not a correctness bug — the symbols still *resolve* on access; they are just not *listed*. Work through these checks BEFORE writing the plan as fact:

1. **A custom module `__dir__` REPLACES the default listing — it does NOT merge.** `dir(module)` uses ONLY the value your `__dir__` returns; it does not auto-union the module globals the way the default `dir()` does. So you MUST explicitly fold `globals()` into the return, or you will REMOVE names that are visible today (`__version__`, `__author__`, dunders, and any already-resolved-and-cached lazy names that PEP 562 wrote into `__dict__`) — a silent regression. This is the single most important and most easily-missed point. The correct return is the UNION of all three sources:
   ```python
   # hephaestus/__init__.py — add alongside __getattr__
   def __dir__() -> list[str]:
       """List lazily-loaded public symbols for tab-completion / introspection (PEP 562)."""
       return sorted(set(_LAZY_IMPORTS) | set(__all__) | set(globals()))
   ```
   Returning only `sorted(set(_LAZY_IMPORTS) | set(__all__))` (forgetting `globals()`) is the classic bug — it drops `__version__`, `__author__`, dunders, and already-cached lazy names, so `dir()` SHRINKS versus today.

2. **`__dir__` returns names (strings) only — it performs NO attribute access — so it triggers no lazy import and fires no access-time warning.** Critically, a deprecated lazy shim (e.g. `retry_with_jitter`, the section F symbol) can be SAFELY listed in `__dir__` output WITHOUT emitting its `DeprecationWarning`, because listing a name ≠ accessing it. The plan asserts this in a test: `dir()` emits no `DeprecationWarning` AND does not populate the symbol into `__dict__`. This connects directly to section F — the access-time warning fires only on attribute *access* through `__getattr__`, and `__dir__` never goes through `__getattr__`.
   ```python
   def test_dir_does_not_emit_deprecation_warning(self) -> None:
       import hephaestus
       hephaestus.__dict__.pop("retry_with_jitter", None)  # ensure not pre-cached
       with warnings.catch_warnings(record=True) as caught:
           warnings.simplefilter("always")
           names = dir(hephaestus)
       assert "retry_with_jitter" in names                 # listed
       assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]
       assert "retry_with_jitter" not in hephaestus.__dict__  # listing did not resolve it
   ```

3. **Pin the contract by SUBSET INVARIANT, not by count.** The audit snapshot said "35 symbols"; the live surface had already grown to 40 `_LAZY_IMPORTS` entries by fix-time. Assert the subset invariant (`set(_LAZY_IMPORTS) <= set(dir(pkg))` and `set(__all__) <= set(dir(pkg))`), never a hardcoded count — counts go stale exactly like the strict-equality `__all__` pins warned about in sections B / B′. Extend the existing surface test file (`tests/integration/test_package_import.py`); do NOT create a parallel one.
   ```python
   def test_dir_exposes_all_lazy_symbols(self) -> None:
       import hephaestus
       visible = set(dir(hephaestus))
       assert set(hephaestus._LAZY_IMPORTS) <= visible   # subset invariant, not == count
       assert set(hephaestus.__all__) <= visible
   ```

4. **Regression-test that `dir()` does not SHRINK the visible set** — assert previously-visible names like `__version__` / `__author__` remain. Because the replace-not-merge behavior in step 1 makes accidental shrinkage the primary failure mode, this guard is what catches a future refactor that drops `set(globals())` from the return:
   ```python
   def test_dir_does_not_shrink_visible_surface(self) -> None:
       import hephaestus
       visible = set(dir(hephaestus))
       assert {"__version__", "__author__"} <= visible   # eagerly-bound names must stay listed
   ```

5. **Audit-snapshot counts drift between finding-time and fix-time — verify the live surface on disk before quoting any count.** The "35 symbols" in the audit finding was already stale (real = 40 `_LAZY_IMPORTS` entries). An audit finding's premise is itself a claim to check (consistent with section G step 3 and the team-KB lesson that strict-audit findings are sometimes factually wrong). Confirm the live count before relying on it, and never bake it into a test:
   ```bash
   python3 -c "import hephaestus; print(len(hephaestus._LAZY_IMPORTS), len(hephaestus.__all__))"
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue's "in `__all__`" claim about the deprecated shim | Issue #1545 stated `retry_with_jitter` was exposed via `__all__`; planned the fix from that structural claim | The symbol is actually only in `_LAZY_IMPORTS`, not `__all__`. The fix seam (`__getattr__`) is the same either way, but the implementation differs slightly | Grep the named symbol against the source before trusting an issue's structural claim; don't assume `__all__` and `_LAZY_IMPORTS` always overlap. `verified-local` |
| Assume the access-time warning duplicates the existing call-time warning | Considered "deduping" by relying on the function-body warning alone | Access-time (`hephaestus.X` binding) and call-time (`hephaestus.utils.X(...)`) are DIFFERENT access paths firing for different users; dropping either silently loses coverage | Keep both warnings — they are complementary layers, not duplicates. `verified-local` |
| Write a one-shot warning-assertion test without resetting the cache | `with pytest.warns(DeprecationWarning): _ = hephaestus.retry_with_jitter` | PEP 562 caches the resolved name into module globals on first access; a prior test that touched the symbol means `__getattr__` never re-runs → false-negative / flaky | Call `module.__dict__.pop(name, None)` before asserting, to force a fresh `__getattr__` resolve. `verified-local` |
| Treat the change as purely additive (new test only) | Planned to add a new warning-assertion test and leave existing tests alone | The existing test `test_retry_with_jitter_reachable_from_top_level_lazy_loader` explicitly documented and tolerated the silent lazy resolve; the new behavior contradicts that green test's documented contract | Grep for tests asserting the CURRENT (about-to-change) behavior; REWRITE the stale-tolerant one (don't just append a new test next to it). `verified-local` |
| Change the behavior without touching the prose doc | Planned source + test edits only | `COMPATIBILITY.md` said the warning fires "when called"; a doc-cross-check test or reviewer catches the drift after access-time firing is added | Update the prose deprecation doc that describes the deprecation in the same PR. `verified-local` |
| Assume `stacklevel=2` might be wrong for `__getattr__` indirection | Worried that attribute-lookup indirection might need a different stacklevel than the call-time warning | Not actually wrong — `stacklevel=2` IS correct. Call stack: user access line (frame 1) → `__getattr__` (frame 2) → `warnings.warn`. `stacklevel=2` skips `__getattr__` and correctly attributes the warning to the user's access line. Verified by `access_warnings[0].filename == __file__` assertion passing | `stacklevel=2` is correct for `__getattr__`. The attribute-lookup indirection has the same two-frame depth as a direct one-level helper call. `verified-local` |
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
| Guessed the COMPATIBILITY.md "Added" version from the latest git tag | Stamped the stable-symbol table "Added" column `0.9.8` purely because `git describe --tags --abbrev=0` returned `v0.9.7` | The next release may be `0.9.8`, `0.10.0`, or `1.0.0` depending on cadence/roadmap; a guessed number silently mis-documents the stability contract | Resolve the target version from `docs/RELEASING.md` / open milestones / roadmap, or flag it explicitly for the reviewer to confirm — never infer it from the latest tag. `unverified` (plan for ProjectHephaestus #1513) |
| Grepped only the obvious test file for `__all__` pins | Planned to add the surface-pin test to `tests/unit/logging/test_utils.py` and assumed no other pin existed | A strict-equality surface pin (`set(pkg.__all__) == literal`) can live in a DIFFERENT test file and breaks the moment you widen `__all__`; the plan would miss it | Grep the WHOLE test tree for package name + `__all__` + surface/pin/expected (`grep -rn "logging" tests/ \| grep -iE "__all__\|surface\|pin\|expected"`) before widening — a widening change has a non-local test blast radius. `unverified` (plan for ProjectHephaestus #1513) |
| Took the audit finding's "Stable subpackage" premise as given | Built the whole "promote to stable surface" fix on "`hephaestus.logging` is Stable (COMPATIBILITY.md:56)" without re-reading the tier source | An audit finding's premise is itself a claim; if the tier were actually Experimental/Deprecated the entire framing would be wrong (team KB: 3/29 strict-audit findings were factually wrong) | Verify the stability-tier premise on disk before building the fix around it: `grep -n "logging" COMPATIBILITY.md \| grep -iE "stable\|tier"`. `unverified` (plan for ProjectHephaestus #1513) |
| Assumed any re-export binding satisfies submodule patch paths | Re-exported the symbols from `__init__.py` without asserting they are the SAME object as the submodule's | Existing tests that `mock.patch("hephaestus.logging.utils.X")` rely on identity; a divergent package-root binding makes one patch path silently ineffective | Assert re-export identity (`pkg.X is utils.X`) and grep for existing `patch("hephaestus.logging.utils...")` usages to confirm none depend on a divergent binding. `unverified` (plan for ProjectHephaestus #1513) |
| Treated an `__init__.py` re-export widening as boundary-risk-free | Reasoned the eager re-exports were safe because `utils.py` only pulls stdlib + `hephaestus.constants` + formatters, and skipped the surface/boundary tests | That reasoning is a hypothesis until the enforced tests run; any `__init__.py` import addition can regress `test_import_surface.py` / `test_automation_boundary.py` | Always include `test_import_surface.py` and `test_automation_boundary.py` in the verification set when touching a package `__init__.py`, even for a "pure re-export". `unverified` (plan for ProjectHephaestus #1513) |
| Fixed only the 2 symbols named in the issue | Issue #1511 named `add_dry_run_arg` + `DRY_RUN_HELP_CAVEAT`; considered fixing just those two | `add_github_throttle_args` + `configure_github_throttle_from_args` had the identical defect — fixing only the named symbols would re-trigger the same `[S14 API Design]` audit finding for the skipped ones | When an audit finding names a subset of a defect class, fix the WHOLE defect class in one PR (check `set(submodule.__all__) - set(pkg.__all__)` to enumerate all missing symbols, not just the named ones). `verified-local` (ProjectHephaestus #1511) |
| Considered using `_LAZY_EXPORTS` for a stdlib-only module | `cli/utils.py` pulls only `argparse`, `json`, `math`, `sys` + `hephaestus._version_lookup`; still reached for the lazy export pattern | Lazy export infrastructure is only justified when the submodule has heavyweight or boundary-crossing imports (e.g. `pydantic`, `curses`, `hephaestus.automation.*`). For a stdlib-only module, eager `from … import (…)` in `__init__.py` is simpler, faster, and avoids indirection | Use eager re-export when the source module is stdlib-only; reserve `_LAZY_EXPORTS`/`__getattr__` for modules that must stay unloaded at package import time. `verified-local` (ProjectHephaestus #1511) |
| Used a strict-equality pin for the surface test | Considered `assert set(cli.__all__) == set(utils.__all__)` | A strict-equality pin breaks every open branch the moment any sibling PR adds a new symbol to either module | Use a subset assertion (`set(utils.__all__) - set(cli.__all__)`) — it catches regressions (symbols removed from `cli.__all__` that remain in `utils.__all__`) without blocking parallel additions. `verified-local` (ProjectHephaestus #1511) |
| Returned only `sorted(set(_LAZY_IMPORTS) \| set(__all__))` from `__dir__` | Built the companion `__dir__` from just the lazy map and `__all__`, omitting `globals()` | A custom module `__dir__` REPLACES the default listing — it does NOT auto-union module globals. The return dropped `__version__`, `__author__`, dunders, and already-cached lazy names, so `dir()` SHRANK versus today (a silent regression) | Always fold `set(globals())` into the return: `sorted(set(_LAZY_IMPORTS) \| set(__all__) \| set(globals()))`. `unverified` (plan for ProjectHephaestus #1512) |
| Trusted the audit finding's "35 symbols" count | Planned to assert `dir()` exposes exactly 35 lazy symbols, taking the audit snapshot at face value | The live `_LAZY_IMPORTS` had already grown to 40 entries by fix-time; a hardcoded-count test would have been born stale (same failure mode as the strict-equality `__all__` pins in sections B/B′) | Pin by SUBSET invariant (`set(_LAZY_IMPORTS) <= set(dir(pkg))`) and verify the live count on disk; audit-snapshot counts drift between finding-time and fix-time. `unverified` (plan for ProjectHephaestus #1512) |
| Worried that listing a deprecated shim in `__dir__` would fire its `DeprecationWarning` | Considered excluding `retry_with_jitter` from the `__dir__` output to avoid emitting the section-F access-time warning during tab-completion | It doesn't fire — `__dir__` returns names (strings) only and performs NO attribute access, so it never routes through `__getattr__` where the warning lives | Safe to list deprecated lazy symbols in `__dir__`; only ACCESS warns. Assert in a test that `dir()` emits no `DeprecationWarning` and does not populate the symbol into `__dict__`. `unverified` (plan for ProjectHephaestus #1512) |

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

### Access-time DeprecationWarning across the lazy-loader seam — verified pattern (verified-local)

Executed end-to-end for ProjectHephaestus issue #1545. All tests listed below passed.

```python
# hephaestus/__init__.py — _DEPRECATED_LAZY dict + modified __getattr__
# retry_with_jitter lives in _LAZY_IMPORTS (NOT __all__ — the issue misnamed this).

_DEPRECATED_LAZY: dict[str, str] = {
    "retry_with_jitter": (
        "hephaestus.retry_with_jitter is deprecated; use "
        "retry_with_backoff(jitter=True, max_delay=...) instead. "
        "It will be removed no earlier than the next major version after 1.0."
    ),
}

def __getattr__(name: str) -> Any:
    """Lazy-load public symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        if name in _DEPRECATED_LAZY:
            import warnings
            warnings.warn(_DEPRECATED_LAZY[name], DeprecationWarning, stacklevel=2)
        module_name, attr = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'hephaestus' has no attribute {name!r}")
```

```python
# Regression test — replaces stale-tolerant test_retry_with_jitter_reachable_from_top_level_lazy_loader
def test_retry_with_jitter_access_emits_deprecation_warning(self) -> None:
    import hephaestus

    # Bust PEP 562 cache — force __getattr__ to re-run
    hephaestus.__dict__.pop("retry_with_jitter", None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        symbol = hephaestus.retry_with_jitter  # ACCESS only, do not call

    assert callable(symbol)
    access_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert access_warnings, "Accessing hephaestus.retry_with_jitter must emit DeprecationWarning"
    assert "retry_with_jitter" in str(access_warnings[0].message)
    # stacklevel=2 must attribute the warning to the caller's file
    assert access_warnings[0].filename == __file__, (
        f"DeprecationWarning should be attributed to the caller's file "
        f"({__file__}); got {access_warnings[0].filename}. Check stacklevel."
    )
```

Tests that passed:

```text
tests/unit/utils/test_deprecation_warnings.py — 3 passed
tests/unit/utils/test_retry.py -k jitter — 7 passed
tests/unit/validation/test_import_surface.py — passed
tests/unit/validation/test_automation_boundary.py — passed
ruff check hephaestus/__init__.py tests/unit/utils/test_deprecation_warnings.py — all checks passed
ruff format --check — 2 files already formatted
mypy — clean
```

Key confirmed values: `stacklevel=2` inside `__getattr__` correctly points at the user's access line
(confirmed by `access_warnings[0].filename == __file__` assertion passing). `import warnings` deferred
inside the `if name in _DEPRECATED_LAZY:` block does not breach `test_automation_boundary.py`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — correlation_id propagation | Function-local import of `get_current_correlation_id` in `hephaestus/utils/helpers.py:170-172`; lint passes with no `noqa` |
| ProjectHephaestus | Issue #799 / PR #988 — lazy-export add/add rebase conflict | Branch `799-auto-impl` widened `_LAZY_EXPORTS`/`__all__` in `hephaestus/automation/__init__.py`; main had already added the same `"PRReviewer"` entry via #968/#775 → PR read CI-failing but `mergeStateStatus=DIRTY` was the real blocker. Rebased onto origin/main (only `__init__.py` conflicted; `test_package_imports.py` rebased clean), kept ONE `"PRReviewer"` copy, set()-based surface tests ignored key order. Full suite 4136 passed / 19 skipped; pre-commit reflowed one f-string line; GPG-signed. **verified-local** |
| ProjectHephaestus | Issue #775 / PR #968 — widen automation SDK surface | Exposed PlanReviewer, AddressReviewer, CIDriver (+Options) via `__all__`/`_LAZY_EXPORTS`/`_PHASE_ENTRYPOINTS`; surface-pinning test; 1081 automation tests pass |
| ProjectHephaestus | Issue #775 / PR #968 vs #1067 — stale surface-pin repair | `test_public_surface_pins_expected_symbols` failed on every Py leg with `Extra items in the left set: 'AuditReviewer'`; `AuditReviewer` was a legitimate peer added on `main` by independent PR #1067. Fixed the stale test literal (one-line add, alphabetised), zero source change. `verified-local` — CI re-run confirmation pending. 2 sibling local failures (`HEPH_*_MODEL` env leak; live `gh` auth past a mock) proven environmental via `env -i` + `git stash` + grep-the-CI-log |
| ProjectHephaestus | PR #657 — fix broken main CI | `sys.version_info` guard for `tomllib`/`tomli` in `tests/unit/ci/test_bandit_config.py`; conditional deps in `pyproject.toml`/`pixi.toml`; 2590 tests pass |
| ProjectHephaestus | PRs #534, #536, #538 (issue #539 tracks full port) — Windows-importability | curses guard in `CursesUI`, fcntl guard in `planner.py`, `tzdata` for `hephaestus.github.rate_limit` |
| ProjectHephaestus | Issue #1545 — access-time DeprecationWarning for `retry_with_jitter` | Executed end-to-end: added `_DEPRECATED_LAZY` dict + modified `__getattr__` in `hephaestus/__init__.py`; replaced stale-tolerant `test_retry_with_jitter_reachable_from_top_level_lazy_loader` with `test_retry_with_jitter_access_emits_deprecation_warning` (including `__dict__.pop` cache-bust and `stacklevel=2` filename assertion); updated `COMPATIBILITY.md` bullet. Symbol is in `_LAZY_IMPORTS`, not `__all__` (issue misnamed it). All tests passed: 3 in `test_deprecation_warnings.py`, 7 in `test_retry.py -k jitter`, `test_import_surface.py`, `test_automation_boundary.py`. Ruff + mypy clean. **verified-local** — CI pending after PR merges |
| ProjectHephaestus | Issue #1511 — `[S14 API Design]` align `hephaestus/cli/__init__.py __all__` with `cli/utils.py __all__` | **verified-local** (section G). Added 4 missing symbols (`DRY_RUN_HELP_CAVEAT`, `add_dry_run_arg`, `add_github_throttle_args`, `configure_github_throttle_from_args`) to both the import block and `__all__` in `hephaestus/cli/__init__.py`. Eager re-export (`cli/utils.py` is stdlib-only). No COMPATIBILITY.md change (no per-symbol table for `hephaestus.cli`). Added `test_cli_all_covers_module_all` (subset assertion) + `test_dry_run_symbols_reexport_identity` (identity check) in `tests/unit/cli/test_utils.py`. All 79 tests in `tests/unit/cli/` passed; `test_import_surface.py` + `test_automation_boundary.py` passed; mypy clean (423 source files); ruff clean. CI pending after PR merges |
| ProjectHephaestus | Issue #1513 — `[S14 API Design]` promote correlation-ID functions to the stable surface | **PLAN ONLY / unverified** (COMPATIBILITY.md version-stamping in section G). Plan re-exports `set_correlation_id` / `get_current_correlation_id` / `correlation_id_scope` from `hephaestus/logging/__init__.py`, adds them to `__all__`, documents them in the `COMPATIBILITY.md` stable-symbol table (stamped `0.9.8` purely because latest tag is `v0.9.7` — flagged as an UNVERIFIED guess that the reviewer must confirm against roadmap), and adds a subset-assertion surface-pin test. Five planning traps captured: version-stamp must be verified not guessed; grep the WHOLE test tree for a non-local strict-equality `__all__` pin before widening; verify the "Stable subpackage" premise on disk; assert re-export identity for `patch("hephaestus.logging.utils...")` paths; include `test_import_surface.py`/`test_automation_boundary.py` for the `__init__.py` widening. Not executed in CI |
| ProjectHephaestus | Issue #1512 — `[S14 API Design]` add companion `__dir__()` to the PEP 562 lazy-loader package | **PLAN ONLY / unverified** (section H). Plan adds a module-level `__dir__()` returning `sorted(set(_LAZY_IMPORTS) \| set(__all__) \| set(globals()))` to `hephaestus/__init__.py` (which already defines `__getattr__` for lazy loading but no `__dir__`, so `dir(hephaestus)` shows only ~4 eager names) and pins it with a `TestDirDiscoverability` class in the existing `tests/integration/test_package_import.py`. Durable lessons captured: a custom `__dir__` REPLACES (does not merge) the default listing, so `set(globals())` MUST be folded in or `dir()` SHRINKS; `__dir__` returns names only (no attribute access) so a deprecated lazy shim is listed without firing its `DeprecationWarning`; pin by SUBSET invariant not a hardcoded count (the audit's "35 symbols" was already stale at 40 `_LAZY_IMPORTS` on disk); regression-test that `dir()` does not shrink the visible set; extend the existing surface test file, not a parallel one. Not executed in CI |
