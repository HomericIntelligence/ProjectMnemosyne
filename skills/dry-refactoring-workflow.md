---
name: dry-refactoring-workflow
description: "Complete TDD-driven workflow for identifying and eliminating code duplication by extracting reusable helper methods. Use when: (1) extracting duplicated helper methods into a shared module using TDD (write a failing test against the canonical, delete the duplicate, run green); (2) creating a private leaf module with leading-underscore naming to centralize a repeated internal call (e.g. importlib.metadata version resolution, path construction) and prevent re-introduction across modules; (3) centralizing hardcoded path constants into a single module to prevent drift when directory structure changes (incl. phase-routed in_progress/completed splits); (4) deduplicating LLM JSON extraction, parser logic, or any call-site pattern copy-pasted across several files; (5) test structure must mirror source structure when extracting helpers; (6) running a full DRY consolidation pass (discovery via grep, classifying true duplicates vs intentional variants, dict-structure consolidation) and refactoring to a single canonical source; (7) extract-method / SRP decomposition of over-long functions (50-LOC) and methods (100-LOC), including converting a mutating closure into a method via a small mutable box; (8) extracting repeated cached lookups into an @lru_cache helper (and clearing the cache so unittest.mock.patch works); (9) removing stale scripts / deprecated stubs (grep callers first) and replacing hardcoded file lists with dynamic Path.rglob discovery; (10) PLANNING a consolidation of two OVERLAPPING but not-identical constant collections (frozensets / keyword lists / error-pattern tuples) — classify true-duplicate vs intentional-variant first, then extract only the shared CORE into one canonical immutable constant and have each consumer compose CORE | its-own-extras, proving anti-drift with CORE.issubset(consumer) parity tests, instead of a flat merge that would violate a deliberate behavioral contract. (11) behavior-preserving duplicate cleanup across test fakes, tiny strategy/kernel modules, and validation wrappers: keep public module exports stable, centralize only identical mechanics, preserve local wrapper names/error messages, and verify with focused + full suites before opening a PR. Also covers cryptographic commit signing requirements in PR workflows. (12) stale issue body in dedup/consolidation tasks: issue 'Evidence:' sections go stale as prior PRs partially resolve them — grep the CURRENT state first; choose inlining over fixtures for pure bytes→str helpers; resolve remote branch divergence by pushing to a new branch rather than force-pushing or rebasing 84 conflicting commits. (13) PLANNING an extraction whose issue claims 'N nearly-identical, M byte-for-byte identical' methods: the COUNT and 'byte-for-byte identical' assertions go STALE exactly like the 'Evidence:' section — count and DIFF every claimed-duplicate body in full before scoping; prior refactors may have already delegated one to a richer printer or changed another's signature/model, and even the truly-similar bodies often hide call-site-varying string args (count noun, header) that a flat merge would silently change — parameterize those as kwargs-with-defaults to guarantee zero behavior change, and place the helper in an EXISTING established-dedup module rather than a new leaf module or base-class method. (14) PLANNING a behavior-preserving method→free-function extraction when the duplicated method is a patched test seam — grep patch.object(.*\"_method\") BEFORE planning any deletion (a method patched at many call sites must be KEPT as a one-line thin wrapper delegating to the new free function, never deleted, or every patch target breaks); read the actual test bodies to confirm which 'near-identical' differences (log level, an extra debug line, exception-message wording) are behavior-bearing vs incidental before collapsing copies (only safe to collapse logging when no test asserts log level/message); match the target module's established convention (free function taking explicit args, not a mixin/base-class method); hedge unverified import assumptions a planner did not execute (is pathlib.Path already imported? is there a 'from ._review_utils import ...' line to extend? is a cross-layer runtime import safe within the automation→library boundary AND absent from the base 'import hephaestus' surface?); and prove a pure extraction with a single-canonical-source grep that must return exactly one hit PLUS the PRE-EXISTING per-class behavioral suites staying green (the real acceptance gate, not the new structural tests). (15) PLANNING a duplicate-bearing standalone SCRIPT → library-shim consolidation when the script duplicates library logic (e.g. get_subpackages()/subpackage-mirror checks) but ALSO carries one unique function — prefer SHIM over DELETE: move the unique function into the library as the canonical source (returning a (ok, error_lines) tuple), export it from the package __init__, and rewrite the script as a thin shim importing the granular library functions — because the script is referenced by docs, a skill, AND auto-discovery smoke tests; the silent risk is OUTPUT-CONTRACT preservation: the shim must reproduce byte-for-byte stdout/stderr (literal arrow → and exact phrasing), calling the GRANULAR functions, NOT the library main()/check_test_structure (which runs extra checks the script never ran); importing a private symbol (_get_subpackages) across the script→library boundary is the most reviewer-contentious choice — offer a fallback (compute from already-returned data); record unverified reliances as explicit risks (is the script NOT wired to CI/pre-commit? does the doc/README line stay accurate once the shim is what's wired? is the single-vs-double-quote glob-marker check copied exactly?); and note the TDD INVERSION gotcha — a library test written AFTER copying the function body is GREEN-first, not RED, so don't claim a RED phase you didn't have. (16) REMOVING a deprecated PUBLIC-API symbol (one that already emits DeprecationWarning) across ALL surfaces — a deprecated symbol lives on far more surfaces than its definition: enumerate and delete from impl, the subpackage __init__ import + __all__, the top-level package lazy-loader map (_LAZY_IMPORTS) + __all__, the deprecation-warning INFRASTRUCTURE (a _DEPRECATED_LAZY dict + the __getattr__ branch that emits the access-time warning — and SIMPLIFY __getattr__ once the last deprecated lazy symbol is gone), tests, and multi-location docs; discovery-first repo-wide grep classifying every hit (def/re-export/lazy-map/deprecation-infra/test/doc) and confirming ZERO runtime callers before treating it as a pure removal; TDD absence-guard tests FIRST (assert `not hasattr`, `symbol not in __all__`, `symbol not in _LAZY_IMPORTS`, `symbol not in dir()`) which FAIL first as a real RED — busting the PEP 562 cache with `pkg.__dict__.pop(symbol, None)` and ignoring DeprecationWarning for the top-level guard; DELETE deprecation-GUARD test files outright (don't trim them) and the per-symbol deprecated test CLASS in mixed files (re-grep before pruning patch/MagicMock imports); repoint integration fixtures that USE the symbol onto a non-deprecated lazy symbol; scrub docs across COMPATIBILITY.md (prose list + callout + table-row annotation + per-subpackage callout), MIGRATION.md (convert to a Removed-symbols table noting the BREAKING ImportError), and ROADMAP.md; verify via a three-tier grep gauntlet (package source / docs-except-MIGRATION / repo-wide-except-tests) then ruff then the full suite above the coverage gate; and treat it as a BREAKING public-API removal — name the exact broken import forms in the PR body and record the rollback path. (17) EXECUTING a consolidation against an APPROVED implementation plan whose exact `file:line` anchors may be stale: a stale anchor can be a wrong FILENAME (not just a wrong line number or stale count), and a plan that passed STRICT review claiming 'verified accurate against disk' does NOT exempt the implementer from re-grepping — the named file may merely CALL the indirection root (a shared helper) where the literal actually lives. Before editing, grep the CURRENT tree for the literal pattern the plan DESCRIBES (`grep -rn '<the literal>' src/`), map the plan's INTENT onto the real call sites, and re-count every occurrence yourself (the per-module count drifts like the 'Evidence:' section); fixing the indirection root transitively fixes the symptom the plan pointed at. (verified-local — ProjectHephaestus #1427, consolidated two log-format strings into `constants.AUTOMATION_LOG_FORMAT`/`LOG_DATEFMT`; the approved plan named `ensure_state_labels.py:189` but the real drifted literal lived at `cli/utils.py:222` in `configure_cli_logging`; full local suite green 5203 passed / 23 skipped, 87.22% coverage, CI pending at capture.) (18) RESOLVING an issue whose TITLE and BODY describe DIFFERENT tasks before implementing a DRY consolidation — in a TASK/PLAN/REVIEW automation pipeline the issue TITLE can be a stale MISLABEL: read `gh issue view <n> --comments` FIRST and treat the issue BODY plus the approved `# Implementation Plan` comment (and its `## 🔍 Plan Review` verdict, e.g. 'A / GO') as the AUTHORITATIVE source of truth for WHAT to build, NOT the title; do not implement the title's task when the body and approved plan describe a different one (e.g. a title saying 'narrow Ruff S102 exec suppressions across scripts/' over a body entirely about consolidating two coexisting CLI log-format strings — the plan review explicitly confirmed the title-vs-body mismatch and graded the body's plan GO). The accompanying worked CLI-log-format DRY consolidation reinforces existing phases: place the shared `CLI_LOG_FORMAT` / `CLI_LOG_DATEFMT` constants in the LIBRARY layer (`hephaestus/constants.py`) because the automation→library boundary forbids library→automation imports but allows automation→library, keeping ONE canonical source reachable from both; classify-don't-blindly-merge a THIRD terse log format (`github/fleet_sync.py` + `github/tidy.py`) as an INTENTIONAL VARIANT left untouched and documented (mirrors the `TRANSIENT_ERROR_CORE` precedent), proven by a grep gauntlet (zero inline CLI literals in `hephaestus/automation/` AND exactly 2 github-terse hits remain); preserve each call site's exact shape — keep a consumer's local `fmt`/`datefmt` names but assign them FROM the constants when a later `setFormatter()` reuses them (`implementer_cli.py`), and do NOT add a `datefmt=` argument to a call site that never had one (`audit_reviewer.py`); and do NOT change the VALUE of the pre-existing library `LOG_FORMAT` (consumed by `logging/utils.py`, asserted in `tests/unit/utils/test_constants.py`) — changing it would alter every library log line for no functional gain. (verified-local — ProjectHephaestus #1428; full automation suite 2238 passed + 29 boundary/constants/import-surface tests passed, ruff check+format clean, mypy clean over 447 files; CI pending at capture.)"
category: architecture
date: 2026-06-30
version: "1.13.0"
user-invocable: false
verification: unverified
history: dry-refactoring-workflow.history
---
# DRY Refactoring Workflow

Complete TDD-driven workflow for identifying and eliminating code duplication by extracting reusable helper methods.

## Overview

| Attribute | Details |
| ----------- | --------- |
| **Date** | 2026-06-20 |
| **Objective** | TDD-driven extraction of duplicated code into reusable helper modules, with emphasis on private module placement, test structure mirroring, and cryptographic commit signing |
| **Outcome** | ✅ v1.0.0 (Feb 2026): Eliminated token aggregation duplication. v1.1.0 (Jun 2026): Extended with private module patterns, test mirroring enforcement, signing requirements. v1.3.0 (Jun 2026): Absorbed centralized path constants, LLM JSON extraction dedup, full DRY consolidation discovery/classify pass, and canonical-source refactor patterns (Pydantic type hierarchy, dict-structure consolidation, orphan relocation). v1.4.0 (Jun 2026): Restored SRP/extract-method (mutable-box closure), @lru_cache detection util (mock.patch/cache_clear gotcha), stale-script/stub cleanup, and dynamic Path.rglob discovery patterns from the nuance audit. ⚠️ v1.5.0 (Jun 2026, **planning-only / unverified**): Added Phase 10 — planning a consolidation of OVERLAPPING constant collections via the core/extras split (CORE \| consumer-extras) with subset parity anti-drift tests, classifying intentional-variant-with-overlap separately from "do not consolidate". v1.6.0 (Jun 2026): Added Radiance behavior-preserving duplicate cleanup pattern for route-test fakes, layout-only metric kernels, validation field wrappers, and stale tool deletion; verified locally with Ruff, full pytest, compileall, diff check, and pre-push pytest; PR CI pending. v1.7.0 (Jun 2026): Added Phase 12 — stale issue body in dedup tasks (grep current state, don't trust 'Evidence:' section); inline vs fixture decision for pure bytes→str helpers; remote branch divergence resolution (new branch vs force-push). Verified CI via ProjectHermes PR #652. ⚠️ v1.8.0 (Jun 2026, **planning-only / unverified**): Added Phase 13 — stale 'N identical duplicates' claims in extraction issues: count and DIFF every claimed-duplicate body before scoping (the duplicate COUNT and 'byte-for-byte identical' assertion go stale like 'Evidence:'); parameterize call-site-varying string args (count noun, failed-header) as kwargs-with-defaults to guarantee zero behavior change instead of flattening; prefer an EXISTING established-dedup home over a new leaf module. Captured from planning ProjectHephaestus issue #1381; NOT executed (no code, no tests, no CI). ⚠️ v1.9.0 (Jun 2026, **planning-only / unverified**): Added Phase 14 — planning a method→free-function extraction when the duplicated method is a patched test seam (#1383, `_load_impl_session_id` → `load_impl_session_id` in `_review_utils.py`): grep `patch.object` before any deletion and keep each method as a thin wrapper; read tests to separate behavior-bearing diffs (log level/message) from incidental ones before collapsing; match the target module's free-function convention; hedge unverified import/boundary assumptions; verify by single-hit canonical grep + EXISTING behavioral suites green. NOT executed end-to-end. ⚠️ v1.10.0 (Jun 2026, **planning-only / unverified**): Added Phase 15 — planning a duplicate-bearing standalone SCRIPT → library-shim consolidation (#1504, `scripts/check_unit_test_structure.py` duplicates `get_subpackages()`/subpackage-mirror logic in `hephaestus/validation/test_structure.py` but uniquely owns `check_scripts_coverage()`): SHIM over DELETE (the script is referenced by docs, a skill, and auto-discovery smoke tests); move the unique function into the library as canonical `(ok, error_lines)`, rewrite the script as a thin shim over the GRANULAR library functions while preserving byte-for-byte stdout/stderr (the silent output-contract risk); hedge the private-symbol import across the script→library boundary with a data-derived fallback; record unverified CI/pre-commit-wiring and doc-accuracy reliances; flag the TDD GREEN-first inversion (test written after copying the body is not RED). NOT executed (no code, no tests, no CI). v1.11.0 (Jun 2026, **verified-local**): Added Phase 16 — deprecated public-API symbol removal across ALL surfaces (impl, subpackage `__init__` + `__all__`, top-level `_LAZY_IMPORTS` + `__all__`, `_DEPRECATED_LAZY`/`__getattr__` deprecation infra, deleted deprecation-guard test files, multi-location docs), captured from an EXECUTED ProjectHephaestus #1420 session (removed `get_config_value()`/`retry_with_jitter()`); full local suite green (5535 passed / 24 skipped, 87.18% ≥ 83% gate), ruff clean, three-tier repo-wide stale-ref grep gauntlet empty; PR CI not yet merged at capture time (verified-local, NOT verified-ci). v1.12.0 (Jun 2026, **verified-local**): Added Phase 12d — an APPROVED, strict-reviewed plan ("A / GO", "verified against disk") can carry a stale anchor whose FILENAME is wrong, not just its line number: the named file may merely CALL the indirection root where the literal lives. Captured from an EXECUTED ProjectHephaestus #1427 session (consolidated `LOG_FORMAT` + the automation `[LEVEL] name:` format into `constants.AUTOMATION_LOG_FORMAT`/`LOG_DATEFMT`); the plan named `ensure_state_labels.py:189` but the drifted literal lived at `cli/utils.py:222` in `configure_cli_logging` (which `ensure_state_labels.main()` calls indirectly) — fixing that root transitively fixed the symptom, and the plan also under-counted the literals. Re-grep the literal the plan DESCRIBES on the current tree and map INTENT onto real call sites. Full unit suite green (5203 passed / 23 skipped, 87.22% ≥ 83% gate), ruff clean, single-source grep returns only the canonical `constants.py` definition, anti-drift parity tests + import-surface/automation-boundary guards green; PR CI not yet merged at capture time (verified-local, NOT verified-ci). v1.13.0 (Jun 2026, **verified-local**): Added Phase 17 — resolving an issue whose TITLE and BODY describe DIFFERENT tasks in a TASK/PLAN/REVIEW automation pipeline: the title can be a stale MISLABEL, so read `gh issue view <n> --comments` FIRST and treat the issue BODY plus the approved `# Implementation Plan` comment and its `## 🔍 Plan Review` verdict as the authoritative source of WHAT to build, never the title. Captured from an EXECUTED ProjectHephaestus #1428 session — a title saying "narrow Ruff S102 exec suppressions across scripts/" over a body entirely about DRY-consolidating two coexisting CLI log-format strings; the plan review explicitly confirmed the mismatch and graded the body's plan "A / GO". The worked CLI-log-format consolidation (new `CLI_LOG_FORMAT`/`CLI_LOG_DATEFMT` constants in the LIBRARY-layer `constants.py`; a THIRD terse github format left as a documented intentional variant; per-call-site preservation of local `fmt`/`datefmt` names and absent `datefmt=`; the pre-existing `LOG_FORMAT` value left unchanged) reinforces the boundary-placement and intentional-variant phases. Full automation suite green (2238 passed + 29 boundary/constants/import-surface tests), ruff + mypy clean (447 files); PR CI not yet merged at capture time (verified-local, NOT verified-ci). |
| **Primary Issues** | #642 (original), #739 (private module extraction), #917 (pr-policy signing), #503 (LLM JSON dedup) |
| **Primary PRs** | #714 (original), #900+ (refactoring), #137/#1738 (path constants), #505 (JSON dedup), #201 (DRY consolidation) |
| **History** | [changelog](./dry-refactoring-workflow.history) |

## When to Use This Skill

Use this workflow when you encounter:

- **Code duplication**: Same logic appears in 2+ methods
- **DRY violations**: Identical patterns that should be abstracted
- **Refactoring tasks**: Need to improve code maintainability
- **Follow-up issues**: Code review identified duplication to fix

**Trigger phrases**:

- "Extract duplicate [X] logic"
- "Consolidate [X] code"
- "DRY violation in [method names]"
- "Create helper method for [pattern]"
- "Extract duplicated function calls into a helper module"
- "Private helper module placement — where should `_helper.py` go?"
- "How to structure tests for root-level private modules?"
- "Duplicated `importlib.metadata.version()` calls — consolidate into helper"
- "Centralize hardcoded path strings into a single `paths.py`"
- "Same JSON/LLM-response extraction logic copy-pasted across files"
- "Run a full DRY consolidation pass — find and classify duplicates"
- "Consolidate duplicate Pydantic models / type aliases into a base hierarchy"
- "Same dict structure built in multiple call sites — extract a shared helper"
- "This function/method is too long — extract methods / decompose by responsibility"
- "Convert a mutating closure into a standalone method"
- "Extract repeated cached lookups into an `@lru_cache` helper"
- "`@lru_cache` is breaking my `mock.patch` test — how to clear the cache?"
- "Remove stale scripts / deprecated stubs as part of consolidation"
- "Replace a hardcoded file list with dynamic `Path.rglob` discovery"
- "Two error-pattern / keyword lists overlap — should I merge them into one frozenset?"
- "Consolidate `TRANSIENT_ERROR_PATTERNS` and `NETWORK_ERROR_KEYWORDS` / two near-duplicate constant collections"
- "These two constant lists are 80% the same but one has extras — DRY them up"
- "Plan a DRY merge of overlapping constants without changing either matcher's behavior"
- "Consolidate duplicated server test fake apps / fake requests without changing route assertions"
- "Replace repeated tiny metric/operator kernel classes with one parameterized kernel while keeping module-level `KERNEL` exports stable"
- "Share validation type checks but preserve each module's exception class, wrapper function names, and error message text"
- "Remove an obsolete script and its Ruff exception after `rg` proves no first-party callers remain"
- "The issue says 4 files have the duplicate but only one actually does — how to discover the current state?"
- "Should I add a pytest fixture or just inline the shared helper call at each call site?"
- "Remote rejected my push with non-fast-forward — the remote branch has a different solution; what now?"
- "Extract a duplicated method into a shared free function, but the method is patched in tests — can I delete it?"
- "Two near-identical methods differ only in log level / an extra debug line — safe to collapse into one helper?"
- "Where should a shared cross-reviewer helper live — new leaf module, base class, or the existing `_review_utils.py`?"
- "I'm planning a refactor but haven't run anything — which import/boundary assumptions must the reviewer double-check?"
- "This standalone script duplicates library logic but has one unique function — delete it or shim it to the library?"
- "Plan a DRY shim: move the script's unique function into the library and rewrite the script as a thin delegating shim"
- "The script prints its own ERROR/OK lines — how do I preserve byte-for-byte stdout when delegating to the library?"
- "Is it OK to import a private `_get_subpackages` from the library into a sibling product script?"
- "I copied the function body into the library, then wrote a test — is that a real RED phase?"
- "Should the shim call the library's `main()`/`check_test_structure`, or the granular `check_*` functions?"
- "Remove a deprecated public function/class that already emits a `DeprecationWarning`"
- "What are ALL the surfaces a deprecated public symbol lives on before I delete it?"
- "The symbol still resolves via `hephaestus.<name>` after I deleted its definition — what did I miss?"
- "How do I write an absence-guard test that the deprecated symbol is gone (bust the PEP 562 cache)?"
- "Should I edit or delete `test_deprecation_warnings.py` / `test_docs_deprecation_sync.py` after removing the symbol?"
- "An integration test pops the deprecated symbol from `__dict__` — how do I repoint it after removal?"
- "Which docs (COMPATIBILITY.md / MIGRATION.md / ROADMAP.md) need scrubbing when I remove a deprecated symbol?"
- "Treat a deprecated-symbol removal as a breaking change — what do I put in the PR body and rollback?"

## Verified Workflow

### Quick Reference

```bash
# --- DISCOVERY: find duplicate symbols / hardcoded strings ---
grep -rh "^def [a-z_]"  src/ --include="*.py" | sed 's/(.*//' | sort | uniq -c | sort -rn | head -30
grep -rh "^class [A-Z]" src/ --include="*.py" | sed 's/(.*//;s/://' | sort | uniq -c | sort -rn | head -30
grep -rn '"agent"\|"judge"\|"result\.json"' src/ --include="*.py" | grep -v "^[[:space:]]*#"

# --- PATH-CONSTANT BYPASS AUDIT (run before merging dir-structure changes) ---
grep -rn "experiment_dir / \|experiment_dir/" src/ scripts/ | grep -v "paths.py" | grep -v __pycache__

# --- VERIFY no orphaned refs after migration (must be empty) ---
grep -rn "old_module\.\|_old_function_name" src/ tests/ --include="*.py"

# --- RADIANCE-STYLE behavior-preserving duplicate cleanup ---
rg -n "class _FakeRequest|class _FakeApp|def route\(" tests/radiance/server tests/project/release -g "*.py"
rg -n "class (Flatten|Reshape|Permute|Transpose|View)Kernel|estimate_layout_reindex" radiance/metrics/ops -g "*.py"
rg -n "def _required_mapping|def _required_list|def _required_string|def _as_mapping" radiance/*validation.py
./.venv/bin/python -m ruff check radiance scripts tests --no-cache
./.venv/bin/pytest -q

# --- TDD loop: write failing test, implement helper, go green ---
<package-manager> run pytest tests/unit/<module>/test_<file>.py -v   # RED then GREEN
<package-manager> run pytest tests/ -q                              # no regressions
pre-commit run --files <changed-files>
git commit -S -m "refactor(scope): consolidate <X> into canonical helper"  # -S if pr-policy gate
```

Core loop: **discover → classify (true duplicate vs intentional variant) → write failing test → extract canonical → migrate call sites one at a time → verify green → signed commit + auto-merge PR.**

### Phase 1: Analysis & Planning

1. **Identify duplication** - Find exact duplicate code blocks

   ```bash
   # Search for the pattern
   grep -n "pattern" path/to/file.py
   ```

2. **Verify identical logic** - Confirm both instances do the same thing
   - Check for any subtle differences
   - Note any conditional variations

3. **Choose placement** - Place helper near related private methods
   - After similar helper methods
   - Before the methods that will use it
   - Maintain logical grouping

### Phase 2: Test-Driven Development

**IMPORTANT**: Always write tests BEFORE implementing the helper method.

1. **Create test file** if it doesn't exist

   ```python
   # tests/unit/<module>/test_<class>.py
   from pathlib import Path
   from unittest.mock import MagicMock
   import pytest

   @pytest.fixture
   def mock_config() -> ConfigClass:
       """Create mock config for testing."""
       return ConfigClass(
           required_field="value",
           # Add all required fields
       )
   ```

2. **Write comprehensive tests**
   - Empty/None input case
   - Single item case
   - Multiple items case
   - Edge cases (zeros, special values)

3. **Run tests to verify they fail**

   ```bash
   pixi run python -m pytest tests/unit/<module>/test_<class>.py -v
   ```

   - Confirm `AttributeError: object has no attribute '<method>'`

### Phase 3: Implementation

1. **Extract helper method**

   ```python
   def _helper_method(self, input_data: dict[K, V]) -> Result:
       """Brief description of what this does.

       Args:
           input_data: Description of the input

       Returns:
           Description of the return value. Explain edge case behavior
           (e.g., "Returns empty Result if input_data is empty").
       """
       from functools import reduce  # Import at function level if needed

       if not input_data:
           return Result()  # Handle empty case

       return reduce(
           lambda a, b: a + b,
           [v.attribute for v in input_data.values()],
           Result(),  # Identity element
       )
   ```

2. **Run tests to verify implementation**

   ```bash
   pixi run python -m pytest tests/unit/<module>/test_<class>.py -v
   ```

   - All new tests should pass

### Phase 4: Refactoring

1. **Update first call site**

   ```python
   # Before:
   from functools import reduce
   result = reduce(
       lambda a, b: a + b,
       [v.attribute for v in data.values()],
       Result(),
   ) if data else Result()

   # After:
   result = self._helper_method(data)
   ```

2. **Update second call site** - Same transformation

3. **Run full test suite**

   ```bash
   pixi run python -m pytest tests/unit/<module>/ -v --tb=short -x
   ```

   - Verify no regressions

### Phase 5: Quality Checks

1. **Run pre-commit hooks**

   ```bash
   pre-commit run --files path/to/modified/files
   ```

   - Fix any formatting issues
   - Address type checking errors

2. **Verify all checks pass**

   ```bash
   pre-commit run --files path/to/modified/files
   ```

### Phase 6: Commit & PR

1. **Stage changes**

   ```bash
   git add path/to/implementation.py tests/unit/path/test_file.py
   ```

2. **Create descriptive commit**

   ```bash
   git commit -m "$(cat <<'EOF'
   refactor(module): Extract duplicate [X] logic

   Extract duplicate [description] from method1() and method2()
   into a new helper method _helper_name().

   This refactoring:
   - Eliminates code duplication (DRY principle)
   - Improves maintainability
   - Provides comprehensive test coverage
   - Maintains identical functionality

   Changes:
   - Add _helper_name() helper method in file.py:LINE1-LINE2
   - Refactor method1() to use new helper (line N)
   - Refactor method2() to use new helper (line M)
   - Add comprehensive unit tests in test_file.py

   All X tests pass with no regressions.

   Closes #ISSUE

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
   EOF
   )"
   ```

3. **Push and create PR**

   ```bash
   git push -u origin BRANCH-NAME

   gh pr create \
     --title "refactor(module): Extract duplicate [X] logic" \
     --body "PR_BODY" \
     --label "refactoring"

   gh pr merge --auto --rebase PR_NUMBER
   ```

### Phase 7: Private Module Extraction (NEW in v1.1.0)

When extracting duplicates spans multiple modules, create a **private helper module** with leading-underscore naming:

1. **Place as a leaf module at package root** to avoid circular imports:

   ```text
   hephaestus/
   ├── __init__.py
   ├── _version_lookup.py          # Private helper — leaf module, not a package
   ├── agents/
   ├── utils/
   └── ...
   ```

   **Why not a package?** Private packages (`_internal/`) with `__init__.py` can trigger circular imports if imported from multiple sibling modules that also depend on the package.
   Leaf modules (`_version_lookup.py`) avoid this by having no sub-modules.

2. **Store module-level constants in the helper** — especially PyPI distribution names that must NOT be guessed or normalized:

   ```python
   # hephaestus/_version_lookup.py
   """Internal helper for version resolution via importlib.metadata."""

   from importlib.metadata import PackageNotFoundError, version as _pkg_version

   # CRITICAL: This is the literal [project].name from pyproject.toml
   # importlib.metadata does NOT normalize between distribution and import names
   _DIST_NAME = "HomericIntelligence-Hephaestus"

   def lookup_version() -> str:
       """Resolve package version from installed metadata.

       Returns:
           Version string from most recent git tag, or "unknown" if not found.
       """
       try:
           return _pkg_version(_DIST_NAME)
       except PackageNotFoundError:
           return "unknown"
   ```

3. **Test structure mirroring** — Root-level private modules must have tests in a logical sub-package:

   ```text
   tests/unit/
   ├── version/
   │   ├── __init__.py
   │   └── test_version_lookup.py    # Test for hephaestus/_version_lookup.py
   └── ...
   ```

   **Pre-commit enforcement:** `test_*.py` files CANNOT live directly under `tests/unit/`. They must be in sub-directories that mirror the package structure. This enforces organization and catches orphaned test files.

4. **Cryptographic commit signing requirement** — All commits in PRs must be signed:

   ```bash
   # Commit with mandatory -S flag
   git commit -S -m "refactor: consolidate duplicate version resolution

   Extract duplicated importlib.metadata.version() calls into
   _version_lookup helper module.

   Key learnings:
   - Private modules use leading underscore (_module.py)
   - Store PyPI dist name as module constant (not guessed at runtime)
   - Root-level helpers go in tests/unit/category/ for test organization
   - All commits must be cryptographically signed (-S)
   - pr-policy CI gate validates every commit at GraphQL layer

   Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

   # Verify commit was actually signed
   git log -1 --pretty=format:'%G?'   # Must print 'G', not 'N' or 'B'
   ```

   **CI validation:** The `pr-policy` required-check gate validates commit signatures at the GraphQL layer before allowing merge. Unsigned commits block auto-merge even if all other checks pass.

### Phase 8: Specific Consolidation Patterns (NEW in v1.3.0)

These are concrete instances of the workflow above, absorbed from dedicated skills.

#### 8a. Centralized Path Constants

Eliminate hardcoded path strings by routing every path through one `paths.py` module. Critical when a directory structure has phases (e.g. `in_progress/` vs `completed/`) — routing must live at a single point or bypass violations appear at every construction site.

```python
# paths.py — single source of truth
from pathlib import Path
import shutil

IN_PROGRESS_DIR = "in_progress"
COMPLETED_DIR = "completed"
AGENT_DIR = "agent"
RESULT_FILE = "result.json"

def get_agent_dir(run_dir: Path) -> Path:
    return run_dir / AGENT_DIR

# Phase-routed: keyword-only completed= keeps active-work callers unchanged
def get_tier_dir(experiment_dir: Path, tier_id: str, *, completed: bool = False) -> Path:
    phase = COMPLETED_DIR if completed else IN_PROGRESS_DIR
    return experiment_dir / phase / tier_id

def promote_run_to_completed(experiment_dir, tier_id, subtest_id, run_num) -> Path:
    src = get_run_dir(experiment_dir, tier_id, subtest_id, run_num, completed=False)
    dst = get_run_dir(experiment_dir, tier_id, subtest_id, run_num, completed=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    # copy (NOT move) shared baseline so sibling runs can also be promoted
    baseline = src.parent / "pipeline_baseline.json"
    if baseline.exists():
        shutil.copy2(str(baseline), str(dst.parent / "pipeline_baseline.json"))
    return dst
```

**Pre-merge bypass audit** (run before merging any directory-structure change — must return zero hits):

```bash
grep -rn "experiment_dir / \|experiment_dir/" src/ scripts/ \
  | grep -v "paths.py" | grep -v "# noqa" | grep -v "__pycache__" | grep -v ".pyc"
```

`completed=` routing decision: `False` for in-flight execution; `True` for judging, reporting, rehydration/resume, aggregation; pass both only for repair/reconcile commands. In one ProjectScylla split, skipping this audit left 17 silent wrong-dir reads post-merge — the grep would have found them in 5 seconds.

#### 8b. Deduplicate LLM JSON Extraction

When the same JSON-extraction-from-LLM-output logic is copy-pasted across 3+ files (and a bug lives in only one copy), extract the **most robust** copy into a shared utility rather than fixing one place and creating a 4th variant.

```python
# <module>/utils.py — keep the version that handles the most formats
def extract_json_from_llm_response(output: str) -> dict[str, Any] | None:
    r"""Extract a JSON object from LLM output.

    Handles raw JSON, ```json``` / ``` code blocks, XML-tag-wrapped JSON with
    preamble, and JSON surrounded by explanatory text via brace-matching.

    Returns parsed dict, or None if no valid JSON object found.
    """
    ...  # paste the most robust brace-matching implementation
```

Selection criteria for the canonical copy: most robust (handles most edge cases) > best tested > most recent > clearest. Export it from `<module>/__init__.py`, then replace every duplicate with a one-line delegation. Add a regression test for the originally-failing input (e.g. XML-wrapped JSON with preamble). Use `r"""` for docstrings containing backslashes (ruff `D301`). Verify any "new" full-suite failures pre-exist on `main` via `git stash` before blaming your change.

#### 8c. Full DRY Consolidation Discovery + Classification Pass

For a whole-codebase cleanup, discover systematically then classify before touching anything.

```bash
# Discovery
find src/ -type f \( -name "*.py" -o -name "*.mojo" \) -exec md5sum {} + \
  | awk '{print $1}' | sort | uniq -c | sort -rn | head -20          # identical files
grep -rh "^def [a-z_]"  src/ --include="*.py" | sed 's/(.*//' | sort | uniq -c | sort -rn  # dup funcs
grep -rh "^class [A-Z]" src/ --include="*.py" | sed 's/(.*//;s/://' | sort | uniq -c | sort -rn  # dup classes
```

| Type | Criteria | Action |
| ------ | --------- | ------- |
| **True duplicate** | Identical/near-identical logic, same purpose | Create/extend canonical module; delete copies; update callers |
| **Intentional variant** | Different fields/domain/pipeline stage | Add cross-reference docstrings (`see: other/module.py:Name`); do NOT consolidate |
| **Weaker vs stronger** | Same intent, one validates content, one only checks existence | Keep stronger; update callers and test fixtures |

Search team knowledge first (`/advise`), read both implementations in full before acting, verify imports with the project package manager, and run the full suite before/after.

#### 8d. Pydantic Type-Alias Hierarchy Consolidation

Unify duplicate Pydantic models into a base + domain subtypes, keeping a backward-compat alias so old imports keep working:

```python
class ExecutionInfoBase(BaseModel):
    model_config = ConfigDict(frozen=True)
    exit_code: int = Field(...)
    duration_seconds: float = Field(default=0.0)   # default, not required

class ExecutorExecutionInfo(ExecutionInfoBase):
    container_id: str = Field(...)

ExecutionInfo = ExecutorExecutionInfo               # old imports still work
result = result.model_copy(update={"duration_seconds": elapsed})  # frozen → model_copy, not assignment
```

#### 8e. Dict-Structure Consolidation (Shared Payload)

When the same dict shape is built in multiple call sites (format function + CLI output), extract one private helper so the shape can't drift:

```python
def _serializable_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Canonical JSON-serializable shape for agent stats."""
    return {
        "agent_type": stats.get("agent_type"),
        "total_delegations": stats.get("total_delegations", 0),
        "skill_refs": stats.get("skill_refs", []),
        "timestamp": stats.get("timestamp"),
    }

def format_stats_json(stats): return json.dumps(_serializable_stats(stats))
def main(): cli_output = json.dumps(_serializable_stats(stats))
```

Add a regression test asserting shape parity between the call sites so future fields stay in sync.

#### 8f. Orphan Module Relocation (Preserve History)

```bash
cp package/orphan.py package/subpackage/orphan.py          # prefer existing sub-package (KISS)
grep -rn "from package\.orphan\|import package\.orphan" --include="*.py" .  # find consumers
<package-manager> run python -c "from package.subpackage.orphan import Class; print('OK')"
git rm package/orphan.py                                    # git rm (not rm) → records a rename
grep -rn "from package\.orphan" .                           # must be empty before commit
```

### Phase 9: Additional DRY-Consolidation Patterns (NEW in v1.4.0)

Further consolidation patterns restored from `dry-consolidate-to-canonical-refactor`.

#### Detailed Steps

**9a. Extract-method / SRP decomposition.** Long functions/methods both violate Single Responsibility and hide duplication. Treat size as a smell trigger, not a hard rule: **functions > ~50 LOC** and **methods > ~100 LOC** are extraction candidates. Pull each distinct responsibility into its own named helper.

A common snag: a closure that mutates a variable captured from the enclosing scope cannot be lifted into a standalone method as-is (Python rebinding makes the captured name local). Wrap the mutable state in a small **mutable box** — a one-field dataclass or a single-element `list` cell — and pass it in:

```python
# Before: closure mutates captured `total` — can't be extracted cleanly
def process(items):
    total = 0
    def add(x):            # `nonlocal` ties this to the enclosing frame
        nonlocal total
        total += x
    for i in items:
        add(i)
    return total

# After: mutable box makes the helper a free-standing, testable method
from dataclasses import dataclass

@dataclass
class _Accumulator:
    total: int = 0

def _add(box: _Accumulator, x: int) -> None:
    box.total += x          # mutates the box's field, not a captured local

def process(items: list[int]) -> int:
    box = _Accumulator()
    for i in items:
        _add(box, i)
    return box.total
# (a single-element list `box = [0]` / `box[0] += x` works too for trivial cases)
```

**9b. LRU-cache detection util.** When the same expensive lookup is recomputed at many call sites (config resolution, path discovery, metadata reads), extract it into one `@lru_cache`-decorated helper so it is computed once:

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def resolve_root() -> Path:
    """Locate project root once; cached for the process lifetime."""
    ...  # expensive walk / import
```

**Gotcha — `@lru_cache` conflicts with `unittest.mock.patch`.** The cache holds the value computed *before* the patch was applied, so the mock is never seen. Call `helper.cache_clear()` in the test (and between successive patches):

```python
def test_resolve_root(monkeypatch):
    resolve_root.cache_clear()           # drop any pre-patch cached value
    monkeypatch.setattr(module, "_walk", fake_walk)
    resolve_root.cache_clear()           # ensure the patched impl is used
    assert resolve_root() == expected
```

Prefer a `cache_clear()` in setup/teardown (or an autouse fixture) for any module exposing `@lru_cache` helpers.

**9c. Stale-script removal & deprecated-stub cleanup.** Consolidation leaves behind stale scripts and deprecated stubs — remove them as part of the pass, but **grep for callers first**; a deletion is only safe once nothing references it:

```bash
grep -rn "stale_script\.py\|deprecated_stub\|old_entrypoint" \
  --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" .
```

If a file you are keeping holds a **stale back-reference** to something being deleted, rewrite that file to be **self-contained first** (inline the still-needed logic / update the docstring), commit and verify, and only then delete the stale target. Deleting first leaves a dangling reference that breaks imports or docs.

**9d. Dynamic discovery via `Path.rglob`.** Replace hardcoded file lists (which silently rot as files are added/removed) with dynamic discovery so the set is always current:

```python
# Before: hardcoded list drifts out of sync with the tree
SKILL_FILES = ["a.md", "b.md", "c.md"]

# After: discovered at runtime — new/removed files are picked up automatically
from pathlib import Path
skill_files = sorted(Path("skills").rglob("*.md"))
```

Sort the result for deterministic ordering and filter excludes explicitly (e.g. skip `*.notes.md` / `__pycache__`) rather than re-introducing a hardcoded allowlist.

### Phase 10: Overlapping Constant Collections — Core/Extras Split (NEW in v1.5.0, PLANNING-ONLY)

> **Warning:** This phase is a **proposed workflow** captured from PLANNING ProjectHephaestus
> issue #1205. It was **NOT validated end-to-end** — no code was written, no tests were run,
> and no CI confirmed it. Treat every step below as a hypothesis until CI confirms it on a
> real PR. The rest of this skill is `verified-ci`; this phase alone is unverified.

**The trap this phase exists to avoid:** when two duplicate-*looking* constant collections
(frozensets, keyword lists, error-pattern tuples) are flagged for DRY consolidation, the
naive move is a flat merge into one shared frozenset. But "looks duplicated" is not
"is duplicated." Two collections can overlap heavily yet carry **deliberate,
behavior-bearing differences** — an *intentional variant with overlap*. A flat merge
silently violates one consumer's contract or breaks one consumer's test.

This is a **refinement of the Phase 8c classification table.** Phase 8c offered two
end-states for an intentional variant: "do NOT consolidate" (cross-reference docstrings)
vs full consolidation. Phase 10 adds a **third, middle path** for the overlapping case:
consolidate *only the shared CORE*, keep each consumer's extras local.

#### Quick Reference

```text
discover two duplicate-looking collections
  └─ CLASSIFY: true-duplicate (same intent) ── or ── intentional-variant (deliberate diffs)?
       ├─ true duplicate            → flat-merge into one canonical constant (Phase 8c)
       ├─ variant, NO overlap       → do NOT consolidate; cross-reference docstrings (Phase 8c)
       └─ variant WITH overlap      → CORE/EXTRAS split (THIS phase):
             1. extract genuinely-shared CORE into ONE canonical immutable frozenset
             2. each consumer = CORE | <its own layer-specific extras>
             3. add parity tests: CORE.issubset(consumer_A) AND CORE.issubset(consumer_B)
             4. keep PUBLIC NAMES + iterable types; recompose only their VALUES
             5. real acceptance gate = the EXISTING behavioral suites stay green
```

#### The #1205 worked example

`TRANSIENT_ERROR_PATTERNS` (resilience layer) and `NETWORK_ERROR_KEYWORDS` (retry layer)
overlapped on transient-failure substrings. But `NETWORK_ERROR_KEYWORDS` *additionally*
held `"rate limit"` / `"throttle"`, which the resilience layer **deliberately omits** —
its documented contract is *"rate limit error passthrough (not retried)"*. A naive shared
frozenset would either (a) make the resilience layer retry rate-limit errors (contract
violation) or (b) drop rate-limit/throttle from the network tagger (breaks an existing
test). Neither is acceptable. The core/extras split preserves both contracts.

#### Detailed Steps

1. **Discover, then CLASSIFY before touching anything.** Read BOTH collections and their
   surrounding docstrings/tests in full. Ask: is every element shared by *intent*, or does
   one collection carry elements the other *deliberately excludes*? A module docstring
   contract line ("rate limit error passthrough — not retried") or an existing test that
   asserts an exclusion is your signal that you are looking at an intentional variant, not
   drift. **If you cannot confirm the difference is deliberate, stop and confirm it** —
   the whole split is mis-scoped if the "intentional" difference is actually stale.

2. **Extract only the genuinely-shared CORE** into one canonical immutable constant. Use a
   `frozenset` (immutable, set-algebra-friendly). Put it in a **leaf module both consumers
   can import with no cycle, respecting the architecture boundary** — in Hephaestus this was
   the pre-existing `hephaestus/constants.py` (stdlib-only, already holds shared frozensets).
   **Never** place it in the product/automation layer (the library may not import automation),
   and avoid sub-package `__init__.py` (circular-import risk).

   ```python
   # hephaestus/constants.py  (leaf, stdlib-only, no cycle)
   # Shared CORE of transient-failure substrings used by BOTH the resilience
   # retry matcher and the network-error tagger. Lowercase; matched as substrings.
   TRANSIENT_ERROR_CORE: frozenset[str] = frozenset({
       "timeout", "timed out", "connection", "network", "temporarily",
       "unavailable", "reset by peer", "broken pipe",
   })
   ```

3. **Each consumer composes its full collection as `CORE | <its own extras>`** —
   keeping the **public names and existing iterable types** so call sites that iterate
   them (`any(p in err for p in NAME)`) and exported-symbol consumers keep working. Only
   the *values* are recomposed from the core.

   ```python
   # resilience layer — intentionally does NOT include rate-limit/throttle
   from hephaestus.constants import TRANSIENT_ERROR_CORE
   # exact phrases kept as explicit extras (see trap #2 below)
   _RESILIENCE_EXTRAS = frozenset({"connection refused", "connection reset"})
   TRANSIENT_ERROR_PATTERNS = tuple(sorted(TRANSIENT_ERROR_CORE | _RESILIENCE_EXTRAS))

   # retry/network layer — ADDS rate-limit/throttle by deliberate contract
   from hephaestus.constants import TRANSIENT_ERROR_CORE
   _NETWORK_EXTRAS = frozenset({"rate limit", "throttle"})
   NETWORK_ERROR_KEYWORDS = tuple(sorted(TRANSIENT_ERROR_CORE | _NETWORK_EXTRAS))
   ```

4. **Add subset parity (anti-drift) tests** so the shared signals can never silently drift
   out of either consumer — this is what makes the plan *reviewable*:

   ```python
   from hephaestus.constants import TRANSIENT_ERROR_CORE
   from hephaestus.resilience import TRANSIENT_ERROR_PATTERNS
   from hephaestus.retry import NETWORK_ERROR_KEYWORDS

   def test_core_present_in_both_consumers():
       assert TRANSIENT_ERROR_CORE.issubset(set(TRANSIENT_ERROR_PATTERNS))
       assert TRANSIENT_ERROR_CORE.issubset(set(NETWORK_ERROR_KEYWORDS))
   ```

   Plus standard constants-module tests (see the `testing-python-constants-module` skill):
   `isinstance(CORE, frozenset)`, all-lowercase, immutability (`AttributeError` on `.add()`),
   and parametrized membership of each expected substring.

5. **TDD RED → GREEN.** The parity + constants tests fail first with `ImportError`
   (`TRANSIENT_ERROR_CORE` does not exist yet); create the constant to go green.

6. **Grep ALL file types for orphaned refs** to the old literals after recomposing.

7. **The REAL acceptance gate is the EXISTING behavioral suites, not the new constant
   tests.** Run `test_retry.py`, `test_subprocess_resilience.py`, etc. — every behavioral
   matcher test must stay green. New constant tests proving structure are necessary but
   insufficient; behavior is the contract.

8. Signed commit + auto-merge per the standard PR workflow above.

### Phase 11: Behavior-Preserving Duplicate Cleanup Across Tests, Kernels, and Validation Wrappers (NEW in v1.6.0)

Use this when an audit finds several low-risk duplicate surfaces in one Python repository, but
runtime behavior must remain stable.

#### Quick Reference

```bash
# Find repeated fake app/request route scaffolding.
rg -n "class _FakeRequest|class _FakeApp|def route\(" tests/radiance/server tests/project/release -g "*.py"

# Find repeated tiny kernel classes delegating to the same estimator.
rg -n "class (Flatten|Reshape|Permute|Transpose|View)Kernel|estimate_layout_reindex" radiance/metrics/ops -g "*.py"

# Find repeated validation field wrappers.
rg -n "def _required_mapping|def _required_list|def _required_string|def _as_mapping" radiance/*validation.py

# Behavior-preserving verification gate.
./.venv/bin/python -m ruff check radiance scripts tests --no-cache
./.venv/bin/pytest -q
./.venv/bin/python -m compileall radiance scripts tests
git diff --check
```

#### Detailed Steps

1. **Centralize test-only HTTP fakes in tests, not production.** If several route tests define
   `_FakeRequest`, `_FakeApp`, and identical `route()` decorators, create a local test support
   module. Keep variants explicit by storage shape: rule -> handler, rule -> list[handler],
   `(rule, method) -> handler`, `(method, rule) -> handler`, or registration-order list.
   This removes decorator duplication without making assertions harder to read.
2. **Extract only the invariant mechanics.** For fake route apps, share the decorator and route
   method normalization once, then let tiny subclasses/adapters record routes in the shape each
   test already expects. Do not force every test into one awkward route index.
3. **Replace repeated tiny strategy classes with one parameterized instance.** If modules differ
   only by `supported_ops` and call the same estimator, keep each module's public `KERNEL` export
   but construct it from the shared class, e.g. `KERNEL = LayoutReindexKernel(("flatten", ...))`.
   This preserves provider registration behavior while deleting boilerplate classes.
4. **Preserve validation API/error contracts with local wrappers.** When modules use different
   exception classes or message wording, do not import one module's helper into another. Instead,
   create generic low-level checks that accept `error_type` and exact message strings, then keep
   the existing `_required_mapping` / `_required_string` wrappers in each module.
5. **Delete stale large scripts only after a caller audit.** Run `rg` for the filename, import
   name, CLI reference, docs, and CI exception. Remove the file and remove only the specific lint
   exception/test expectation tied to it.
6. **Run focused tests first, then full gates.** Execute the touched server tests, touched
   validation tests, metric alias tests, then full Ruff/pytest/compileall/diff-check. If the repo
   has a pre-push hook, treat its full pytest rerun as an additional local signal, not CI.

### Phase 12: Stale Issue Body, Inline vs Fixture, and Remote Branch Divergence (NEW in v1.7.0)

Concrete lessons from ProjectHermes issue #329 — deduplicating a `_sign()` HMAC-SHA256 test
helper across 4 files.

#### 12a. Grep FIRST — issue "Evidence:" sections go stale

Issue bodies list the *original* state of the codebase. Prior PRs may have partially resolved
the duplication without closing the issue. The evidence in the body reflects the state at issue
creation, not the current HEAD.

```bash
# ALWAYS do this BEFORE reading the issue "Evidence:" list:
grep -rn "def _sign\|def sign_body\|from tests.helpers import" tests/ --include="*.py"
```

In #329, the body listed 4 files with a copy-pasted `_sign()`. By the time the work began:
- A canonical `sign_body(body, secret)` already lived in `tests/helpers.py`
- Three of the four files already imported and used `sign_body`
- Only one file (`test_integration.py`) still had a thin local wrapper

**Rule:** grep for the current call count/definition count before scoping the work. An "N-file
dedup" issue may be a "1-file cleanup" when you get there.

#### 12b. Inline vs fixture decision for pure test helpers

When a thin wrapper is a pure `bytes → str` function that:
- Closes over a **module-local** constant (e.g. `INTEGRATION_TEST_SECRET`, different from the shared `TEST_SECRET` in helpers.py)
- Has a small number of call sites (< ~10)
- Does no setup/teardown

**Prefer inlining** the canonical call directly at each site (`sign_body(body_bytes, SECRET)`)
over:
- Adding a new pytest **fixture** — overkill for a pure function, leaks the fixture name into unrelated test function signatures
- Adding a new entry in **conftest.py** — unnecessary indirection when the function is already importable

Decision table for deduplicating a test helper:

| Helper type | Call pattern | Preferred approach |
|-------------|--------------|-------------------|
| Pure function, module-local secret | `fn(body, LOCAL_SECRET)` | **Inline** the canonical call |
| Pure function, shared secret | `fn(body, SHARED_SECRET)` | Import from `tests/helpers.py`, inline |
| Stateful / async setup | fixture or async_generator | pytest fixture in conftest |
| Complex parametrized prep | multiple args, reused shape | pytest fixture |

#### 12c. Remote branch divergence — push to a new branch

When `git push` is rejected (non-fast-forward) because the remote branch has diverged with a
different solution:

```bash
# DON'T: force-push — overwrites the remote solution entirely
git push --force  # NO

# DON'T: rebase onto a conflicting remote — may produce 80+ conflict-laden commits
git pull origin <remote-branch>  # triggers merge/rebase with 84 commits and multiple conflicts
git rebase --abort               # bail out

# DO: push as a new branch and open a PR against main
git checkout -b <new-branch-name>          # e.g. 329-inline-sign-calls
git push -u origin <new-branch-name>
gh pr create --title "..." --body "..."
```

The remote branch's competing solution becomes a sibling PR. The project maintainer merges
whichever approach is preferred. This is safer than force-pushing because it preserves both
solutions for review.

#### 12d. A stale anchor can be a wrong FILENAME — and a strict-reviewed "verified against disk" plan is NOT exempt (verified-local, ProjectHephaestus #1427)

Phase 12a established that an issue's `Evidence:` section goes stale. The same rot infects an
**approved implementation plan's exact `file:line` anchors** — and not just the line number:
the **filename itself can be wrong**, because a plan that names a file may actually be pointing
at logic that lives in an **indirection root** (a shared helper the named file merely *calls*).

A plan passing **strict review** — graded "A / GO", with the reviewer explicitly claiming
"Verified accurate against disk" — does **not** exempt the implementer from re-grepping the
current tree. The review verifies the *plan's internal reasoning*, not that every anchor still
resolves on today's HEAD.

In #1427 (consolidate two coexisting log-format strings into named constants in
`hephaestus/constants.py`), the approved plan named a specific stale anchor:

> the "drifted no-brackets variant" lives at `hephaestus/automation/ensure_state_labels.py:189`
> with format `"%(asctime)s %(levelname)s %(name)s: %(message)s"`.

On disk:

- `ensure_state_labels.py` had **no `format=` line at all**.
- The real drifted no-brackets literal lived in `hephaestus/cli/utils.py:222`, inside
  `configure_cli_logging()` — which `ensure_state_labels.main()` calls **indirectly**.
- Both the line number **and the filename** were stale; only the described *symptom*
  ("a no-brackets drift variant exists somewhere") was real.

Fixing the **indirection root** (`configure_cli_logging`) transitively fixed the
`ensure_state_labels` concern the plan was actually pointing at.

**Rule:** before editing, run the discovery grep yourself over the CURRENT tree for the
**literal pattern** the plan describes — not the file it names — then map the plan's INTENT
onto the real call sites:

```bash
# grep for WHAT the plan describes (the literal), not WHERE it claims it lives:
grep -rn '%(asctime)s %(levelname)s %(name)s: %(message)s' hephaestus/
# the real hit is in cli/utils.py:222 (configure_cli_logging), not ensure_state_labels.py:189
```

The discovery grep also **re-counts** every occurrence. As in Phase 13, a plan's per-module
enumeration of literals goes stale exactly like its anchors — the COUNT drifts too. Count and
locate every occurrence yourself with grep before scoping the edits; the plan under-counted in
#1427.

**Verification that proved the consolidation** (verified-local): a single-source grep returning
only the ONE canonical definition in `constants.py` (zero remaining literals in the consumer
modules), anti-drift parity tests asserting each consumer reads
`constants.AUTOMATION_LOG_FORMAT` / `constants.LOG_DATEFMT` rather than a literal, and the
PRE-EXISTING behavioral suites staying green — full unit suite 5203 passed / 23 skipped, 87.22%
coverage ≥ 83% gate, ruff clean, import-surface + automation-boundary guards green. Verified
locally only; CI not yet merged at capture time.

### Phase 13: Stale "N identical duplicates" claims in extraction issues — count and DIFF before scoping (NEW in v1.8.0, PLANNING-ONLY)

> **Warning:** This phase is a **proposed workflow** captured from PLANNING ProjectHephaestus
> issue #1381 ("Extract shared `print_worker_summary` helper"). It was **NOT validated
> end-to-end** — no code was written, no tests were run, and no CI confirmed it. Treat every
> step below as a hypothesis until CI confirms it on a real PR. The rest of this skill is
> `verified-ci` (except Phase 10, which is also planning-only); this phase alone is unverified.

**The trap this phase exists to avoid:** an extraction issue confidently states a duplicate
COUNT and a strength claim ("6 nearly-identical methods, 5 byte-for-byte identical"). That
count and the "byte-for-byte identical" assertion go **stale exactly like the issue's
'Evidence:' section** (Phase 12a). Prior refactors silently erode them: one duplicate may
have already been delegated to a richer printer class, another may operate on a different
model with a different signature. And even the bodies that *are* still similar often hide
call-site-varying string literals that a naive flat merge would silently change. This phase
is a **refinement of Phase 12a** (stale Evidence) applied to the *duplicate count and
identical-ness claim* specifically, plus a **refinement of Phase 8c classify-before-merge**
applied to a *shared function's call-site-varying string args* rather than to constant
collections.

#### Quick Reference

```text
issue claims "N nearly-identical, M byte-for-byte identical" methods
  └─ DON'T trust the count. For EACH claimed duplicate:
       1. grep its definition + READ the full body
       2. DIFF the bodies against each other (not just eyeball them)
       3. drop out-of-scope ones: already-delegated to a richer printer,
          different signature, different model (e.g. PlanResult vs WorkerResult)
  └─ among the REAL duplicates, find call-site-varying literals
       (e.g. "Total PRs:" vs "Total issues:"; leading-newline header vs none)
       └─ PARAMETERIZE them as kwargs-with-defaults (count_noun=, failed_header=)
          → guarantees ZERO behavior change, vs a flat merge that flattens them away
  └─ PLACEMENT: prefer an EXISTING established-dedup module that already fits the
       boundary over a new leaf module or a new base-class method
```

#### The #1381 worked example

The issue claimed **6** `_print_summary` methods, "5 byte-for-byte identical." Grepping and
reading all 6 bodies in full showed only **4** were true duplicates:

- `IssueImplementer._print_summary` had already been refactored to delegate to a richer
  printer class (`ImplementationSummaryPrinter`) — out of scope.
- `Planner._print_summary` had a different signature and operated on a different model
  (`PlanResult` vs `WorkerResult`) — out of scope.

So an issue scoped as "6 methods, ~100 lines removed" was really "4 methods, ~70 lines."
Even among the 4 "identical" methods, two real behavioral differences would have been
silently changed by a flat merge:

1. one logged `"Total PRs:"` where the other three logged `"Total issues:"`;
2. two used a leading-newline header `"\nFailed issues:"` and two did not.

The fix is to **parameterize** these as keyword arguments with defaults
(`count_noun="issues"`, `failed_header="Failed issues:"`) so each call site reproduces its
exact prior output — guaranteeing zero behavior change — rather than flattening four call
sites onto one hard-coded string. "Looks identical in a review" is **not** "is identical";
only a literal diff of the bodies proves it.

#### Placement decision

Put the helper as a **module-level function in the EXISTING `_review_utils.py`** (which
already houses the reviewer-trio dedup from #599 and already exposes a module `logger`) —
not a new leaf module, and not a base-class method. **Lesson:** prefer an existing
established-dedup home that already fits the architecture boundary (automation-layer helper,
no upward library import) over creating a new module. A `TYPE_CHECKING`-only import of
`WorkerResult` keeps the helper light (the plan confirmed via `models.py:110-133` that the
helper only needs `.success` and `.error`).

#### Most-uncertain assumptions (recorded honestly as risks — this is a PLAN)

These were relied on WITHOUT full verification during planning and must be checked before/during implementation:

- Assumed each of the 4 worker files already has a `from ._review_utils import (...)` group
  to extend — `_review_utils.py` was confirmed to exist and to be imported by reviewers, but
  the exact import-statement shape in each of the 4 files was **not** opened/confirmed.
- Assumed no unit test asserts on `_print_summary` output or logger name (a `tests/` grep for
  `_print_summary` returned only unrelated validation tests) — **the suites were not run**.
- Assumed emitting through `_review_utils`'s `logger` (record `name` =
  `hephaestus.automation._review_utils`) instead of each class's own logger causes no
  regression. No test asserts logger name, but this is an **unverified behavioral change** to
  the log record's `name` field.
- The "~100 lines removed" figure is the issue's number; the actual removal is **~70 lines**
  (4 methods), since 2 of the 6 are out of scope.

### Phase 14: Planning a behavior-preserving method→free-function extraction when the method is a patched test seam (NEW in v1.9.0, PLANNING-ONLY)

> **Warning:** This phase is a **proposed workflow** captured from PLANNING ProjectHephaestus
> issue #1383. It was **NOT validated end-to-end** — no code was written, no tests were run,
> and no CI confirmed it. Treat every step below as a hypothesis until CI confirms it on a
> real PR. The rest of this skill is `verified-ci`; this phase alone is unverified.

The #1383 plan extracts a duplicated `_load_impl_session_id` method (present on both `CIDriver`
and `AddressReviewer`) into a shared free function
`load_impl_session_id(state_dir, issue_number, agent)` in
`hephaestus/automation/_review_utils.py`, with both classes delegating to it. The durable
lessons below are about **planning** such an extraction safely, not the mechanics of writing it.
(Sibling to Phase 13: that phase is about stale *count* claims; this one is about preserving a
*patched test seam* and separating behavior-bearing from incidental method differences.)

#### 14a. Patch-by-name test seams force you to KEEP the method, not delete it

When a duplicated method is patched via `patch.object(obj, "_method", ...)` at many call sites,
deleting it during extraction breaks **every** patch target. In #1383 the method was patched at
`test_ci_driver.py:789,830,848,884,2344,2358` and `test_address_review.py:680,714`. The correct
move is to keep each method as a **one-line thin wrapper** that delegates to the new free
function, preserving the seam:

```python
class CIDriver:
    def _load_impl_session_id(self, issue_number: int, agent: str) -> str | None:
        # Thin wrapper preserves the patch.object(...) test seam; logic lives in the free fn.
        return load_impl_session_id(self.state_dir, issue_number, agent)
```

**Grep for `patch.object(.*"_method_name"` BEFORE planning the deletion.** This is the single
most uncertain, highest-leverage assumption in such a plan — if any test patches the method by
name, deletion is off the table.

#### 14b. "Near-identical" methods usually differ in non-asserted ways — verify the test contract before collapsing

The two #1383 copies were *not* byte-for-byte identical: they differed in the **log level** on
the no-file branch (`logger.debug` vs `logger.warning`), one had an extra truncated-session debug
line, and the exception-message wording differed. The plan chose to collapse to **one** logging
style in the shared helper. That is only safe because **no unit test asserts log level or
message** — verified by reading the actual test bodies (`test_ci_driver.py:126-132`,
`test_address_review.py:103-111` assert only the `None` return value).

**Lesson:** when consolidating "near-identical" code, *the differences are the risk*. Read the
tests to confirm which differences are behavior-bearing vs incidental, and state explicitly in
the plan what you collapsed and why it is safe.

#### 14c. Reuse the target module's established convention

`_review_utils.py` already houses cross-reviewer helpers as **free functions taking explicit
args** (`find_pr_for_issue`, `instance_log`, `parse_json_block`). Matching that convention (a
free function, not a new mixin or base-class method) is lower-risk than introducing a new sharing
mechanism. **Grep the target module's existing helpers before choosing the extraction shape** —
the module already tells you the idiom.

#### 14d. Hedge the unverified external assumptions a planner did not execute

A planning-only plan must flag the assumptions it relied on **without running anything**, so the
reviewer/implementer double-checks them:

- **Imports:** `_review_utils.py` may not already import `pathlib.Path` — say "add if not
  present" rather than asserting it exists.
- **Existing import lines:** both `ci_driver.py` and `address_review.py` are assumed to already
  have a `from ._review_utils import ...` line to extend — say "verify and extend, else add".
- **Cross-layer import safety:** the helper uses `session_agent_matches` from
  `hephaestus.agents.runtime`. `_review_utils.py` is in the **automation** layer, so importing
  from the **library** (`hephaestus.agents.runtime`) is the *allowed* direction
  (automation → library). Confirm it does not create a circular import.
- **Import-surface boundary:** `test_import_surface.py` / `test_automation_boundary.py` enforce
  that base `import hephaestus` stays clean. Adding a runtime import to an automation-layer module
  is fine, but the planner must confirm the new helper is **not** pulled into the base import
  surface.

#### 14e. Verification-by-criterion for a pure extraction

Prove the two acceptance criteria explicitly:

- **Single canonical source** — a grep that must return exactly **one** hit:

  ```bash
  grep -rn 'state_dir / f"issue-{issue_number}.json"' hephaestus/automation/   # expect: 1
  ```

- **Zero behavioral change** — run the **PRE-EXISTING per-class test suites unchanged**
  (`test_ci_driver.py`, `test_address_review.py`), not just the new helper tests. The real
  acceptance gate for a behavior-preserving refactor is the EXISTING behavioral tests staying
  green; new structural tests for the free function are necessary but insufficient.

### Phase 15: Planning a duplicate-bearing standalone script → library-shim consolidation with output-contract preservation (NEW in v1.10.0, PLANNING-ONLY)

> **Warning:** This phase is a **proposed workflow** captured from PLANNING ProjectHephaestus
> issue #1504. It was **NOT validated end-to-end** — no code was written, no tests were run, and
> no CI confirmed it. Treat every step below as a hypothesis until CI confirms it on a real PR.
> The rest of this skill is `verified-ci` (except Phases 10, 13, 14, which are also planning-only);
> this phase alone is unverified.

The #1504 plan targets `scripts/check_unit_test_structure.py`, which **duplicates**
`get_subpackages()` + the subpackage-mirror logic that already lives canonically in the library at
`hephaestus/validation/test_structure.py`. The script's **only unique** function is
`check_scripts_coverage()`. The durable lessons below are about **planning** this kind of
"shim the script to the library" DRY consolidation, not the mechanics of writing it. (Sibling to
Phases 13/14: those preserve a *patched test seam* and a *stale duplicate count*; this one preserves
an *stdout/stderr output contract* and disposes of a *duplicate-bearing script with one unique
function*.)

#### 15a. "Shim vs delete" disposition for a duplicate-bearing script with one unique function

When a standalone script duplicates library logic but **also** carries one unique function, prefer:
**move the unique function into the library** (canonical source), then **rewrite the script as a thin
shim** — rather than deleting the script. In #1504 the disposition was: move `check_scripts_coverage`
INTO the library as a new pure function returning `(ok, error_lines)`, export it from
`hephaestus/validation/__init__.py`, and rewrite the script to import `_get_subpackages`,
`check_scripts_coverage`, and `check_test_directory_mirrors` from the library.

**Why shim, not delete:** the script was referenced by **docs** (`scripts/README.md`), a **skill**
(`python-repo-modernization`), AND it is **smoke-tested via auto-discovery**
(`tests/unit/scripts/conftest.py` globs `scripts/*.py`). Deleting it breaks those references and a
documented invocation. The shim keeps the public surface stable (**POLA**) while removing the
duplication (**DRY**). This is a concrete instance of the Phase 8c classification — "true duplicate →
canonical source + delete copies," refined for the case where the copy-bearing file *also* owns
unique behavior worth preserving.

#### 15b. Output-contract preservation is the silent risk in a shim rewrite

The library functions return **data tuples**; the script **prints** its own ERROR/OK lines, including
a literal `→` arrow and exact phrasing. The shim must **REPRODUCE the byte-for-byte stdout/stderr**,
NOT merely call the library. A flat "call the library `main()`" would change the output and break the
smoke test (and any human reader relying on the wording).

Critically, the library's `check_test_structure` ALSO runs **extra checks** (no-loose-files,
no-unsanctioned-dirs) that the script never ran. So the shim must call the **granular** functions
(`check_test_directory_mirrors` + `check_scripts_coverage`), **NOT** the library's `main()` /
`check_test_structure`, or behavior changes (the script would suddenly fail on conditions it never
checked before).

```python
# Shim: delegate to GRANULAR library fns, reproduce the script's exact lines yourself.
from hephaestus.validation import check_scripts_coverage, check_test_directory_mirrors
from hephaestus.validation.test_structure import _get_subpackages  # see 15c for the boundary risk

ok_mirrors, mirror_errors = check_test_directory_mirrors(...)
ok_scripts, script_errors = check_scripts_coverage(...)
for line in mirror_errors + script_errors:
    print(f"ERROR: {line}", file=sys.stderr)   # preserve exact prefix/phrasing/→ arrow
# DO NOT call check_test_structure()/main() — they run no-loose-files/no-unsanctioned-dirs too.
```

#### 15c. Importing a private symbol across the script→library boundary is the reviewer-contentious choice

Importing a private symbol (`_get_subpackages`) from the library into a sibling **product script** is
the **most reviewer-contentious** choice in this plan. It is defensible as "a shim delegating to the
canonical source," but a reviewer may reject the leading-underscore import across the
script/library boundary. **Offer a fallback** so the reviewer has an out: compute the subpackage count
from data already returned by the public functions, rather than importing the private helper. State
both options in the plan and let the reviewer pick.

#### 15d. Record the unverified reliances explicitly (this is a PLAN)

The #1504 plan relied on these **without full verification** — flag each so the reviewer/implementer
re-confirms:

- **(a) The script is NOT wired to CI/pre-commit.** Claimed verified via grep:
  `.pre-commit-config.yaml:158`, `_required.yml:574`, and `test.yml:105` all call the console entry
  `hephaestus-check-test-structure`, **not** the script. The reviewer should re-confirm — if the
  script *were* wired, the output contract becomes a CI gate, not just a smoke test.
- **(b) `scripts/README.md` needs NO edit** because its "Wired into pre-commit" line still describes
  equivalent behavior. This is a **judgment call** a reviewer may flag as now-inaccurate, since after
  the change the *shim* is what's wired (transitively, via the console entry), not the original
  script. Be ready to update the doc if the reviewer disagrees.
- **(c) The `check_scripts_coverage` body was COPIED** from the existing script into a
  `(ok, errors)`-returning shape. The single-quote-vs-double-quote glob-marker check
  (`glob("*.py")` AND `glob('*.py')`) **must be preserved exactly**, or the broken-glob test gives a
  **false pass**. Diff the copied body against the original line-by-line.

#### 15e. TDD inversion gotcha — a test written after copying the body is GREEN-first, not RED

The new library test class for `check_scripts_coverage` is **GREEN-first, not RED** — because the
function body **already exists** (copied verbatim from the script). Writing the test *after* adding the
function means it passes immediately; there is no genuine RED phase. **Note this honestly** so future
planners (and the implementer) don't claim a RED→GREEN cycle they didn't actually perform. If a true
RED is wanted, write the library test (and an assertion on the exact `(ok, error_lines)` contract)
*before* pasting the body.

### Phase 16: Deprecated public-API symbol removal across ALL surfaces (NEW in v1.11.0, VERIFIED-LOCAL — ProjectHephaestus #1420)

> **Verification — `verified-local`:** This phase was **EXECUTED end-to-end** in a worktree, not
> just planned. The full local suite passed (**5535 passed / 24 skipped, 87.18% coverage** ≥ the
> 83% gate), `ruff check` was clean, and the repo-wide stale-reference greps returned empty. The
> PR's CI had **not yet merged** at capture time, so this phase is `verified-local`, NOT
> `verified-ci` — do not over-claim. (The rest of the skill remains `verified-ci`, except the
> planning-only Phases 10/13/14/15.)

This is the **removal counterpart** of Phase 9c (stale-script/deprecated-stub cleanup): the same
"grep callers first, then delete" discipline, but for a **deprecated public symbol** that already
emits a `DeprecationWarning` and now graduates to a **breaking removal**. The #1420 worked example
removed two deprecated functions — `get_config_value()` (in `hephaestus/config`) and
`retry_with_jitter()` (in `hephaestus/utils`) — from every surface. The non-obvious lesson:
**a deprecated public symbol lives on far MORE surfaces than its definition**, and a grep that only
checks the module source will leave half of them behind.

#### 16a. Enumerate ALL surfaces before claiming the symbol is removed

A deprecated public symbol must be deleted from **every** one of these — missing any one leaves the
symbol resolvable (or leaves a test/doc asserting a now-false fact):

1. **(a) The implementation** in its module (the `def`/`class` body).
2. **(b) The subpackage `__init__.py`** — both the import line AND the `__all__` entry.
3. **(c) The top-level package lazy-loader map** (`hephaestus/__init__.py`'s `_LAZY_IMPORTS`) and any
   top-level `__all__`.
4. **(d) Deprecation-warning *infrastructure*** — e.g. a `_DEPRECATED_LAZY` dict plus the
   `__getattr__` branch that emits the access-time `DeprecationWarning`. **Once the last deprecated
   lazy symbol is gone, SIMPLIFY `__getattr__`** (drop the now-dead deprecation branch entirely).
5. **(e) Tests** — including dedicated deprecation-guard files (see 16d).
6. **(f) Docs** — multiple sub-locations (see 16f).

```bash
# A module-source-only grep MISSES (b)-(f). This is the trap.
rg -n "\bget_config_value\b" hephaestus/config/config.py     # finds only surface (a)
```

#### 16b. Discovery-first, classify every hit, confirm ZERO runtime callers

Run a **repo-wide** grep BEFORE deleting and classify every hit:

```bash
rg -n "\b(get_config_value|retry_with_jitter)\b" .
```

Classify each as **definition / re-export / lazy-map / deprecation-infra / test / doc**. Only treat
it as a pure removal once you have confirmed **ZERO runtime callers** (every hit is a def, re-export,
lazy entry, test, or doc — nothing actually *invokes* it in product code).

#### 16c. TDD removal guards FIRST — the RED is an ABSENCE assertion (the inversion to watch)

The TDD inversion here: you write tests that assert the symbol is **GONE**, and they **FAIL first**
because the symbol is still present — that is a real RED. Then delete, then green.

```python
# RED while the symbol still exists; GREEN after removal.
def test_get_config_value_removed():
    import hephaestus.config as cfg
    assert not hasattr(cfg, "get_config_value")
    assert "get_config_value" not in cfg.__all__

def test_top_level_symbol_removed():
    import hephaestus
    # Bust the PEP 562 module cache so a stale binding doesn't mask the removal:
    hephaestus.__dict__.pop("retry_with_jitter", None)
    assert "retry_with_jitter" not in hephaestus._LAZY_IMPORTS
    assert "retry_with_jitter" not in dir(hephaestus)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert not hasattr(hephaestus, "retry_with_jitter")
```

Two gotchas for the **top-level** absence guard: (1) **bust the PEP 562 cache** with
`pkg.__dict__.pop(symbol, None)` first, or a previously-resolved attribute masks the removal; and
(2) wrap the `hasattr`/`dir` checks in `warnings.catch_warnings()` + `simplefilter("ignore",
DeprecationWarning)` so the access itself doesn't raise under `-W error`.

#### 16d. Deprecation-GUARD test files must be DELETED, not edited

A repo often has files whose **sole purpose** is to assert "this symbol still emits
`DeprecationWarning`" and "the docs still list it as deprecated" — e.g.
`test_deprecation_warnings.py`, `test_docs_deprecation_sync.py`. When the symbol is removed those
guards **INVERT** (they now assert a false fact). **Delete the files entirely** — a trimmed version
that drops the warning assertion asserts nothing and rots.

Also: delete the **per-symbol deprecated test CLASS** inside otherwise-still-valid mixed test files
(e.g. `TestGetConfigValue`, `TestRetryWithJitter`), and **prune the symbol from those files' import
blocks**.

> **GOTCHA:** after deleting `@patch("time.sleep")`-style deprecated tests, **re-grep the file** to
> confirm `patch` / `MagicMock` imports are still used elsewhere BEFORE removing them — they usually
> still are, and a blind import removal breaks the surviving tests.

#### 16e. Repoint integration fixtures off the removed symbol — don't just trim them

An integration test may use the deprecated symbol as a **fixture/probe**, not as the subject. In
#1420, a `test_dir_does_not_import_or_warn` test popped `retry_with_jitter` from `__dict__` to prove
`dir()` doesn't warn. After removal, **repoint it to a non-deprecated lazy symbol** (e.g.
`retry_with_backoff`) so the test still exercises the cache-bust path — don't just delete the
assertion. Add a **parametrized `REMOVED_DEPRECATED_SYMBOLS`** absence guard alongside the existing
`TOP_LEVEL_SYMBOLS` / subpackage-symbol lists, and **remove the symbol from those positive lists**.

#### 16f. Docs are a first-class surface with MULTIPLE sub-locations

A single deprecated symbol can appear in many doc places — scrub **all** of them:

- **COMPATIBILITY.md:** a flat lazy-symbol prose list, a "Deprecated lazy-loaded symbols" callout, a
  per-subpackage **table ROW** with a `**(deprecated)**` annotation, AND a per-subpackage "Deprecated
  symbols" callout. Each must be removed.
- **MIGRATION.md:** convert the "Deprecated symbols" section into a **"Removed deprecated symbols"**
  section with a removed→replacement table and an explicit note that `from pkg import symbol` now
  raises `ImportError`/`AttributeError` (it is a **BREAKING** removal).
- **ROADMAP.md:** scrub any stale example that named the symbol.

#### 16g. The verification gauntlet — three-tier grep, then tests, then the full suite

This is the real acceptance gate (the reviewer's "repo-wide stale-reference" ask):

```bash
# Tier 1 — package source clean
rg -n "\b(get_config_value|retry_with_jitter)\b" hephaestus --glob "*.py"        # → empty

# Tier 2 — docs clean EXCEPT intentional migration guidance
rg -n "\b(get_config_value|retry_with_jitter)\b" COMPATIBILITY.md README.md docs -g "*.md" \
  | rg -v "^docs/MIGRATION.md:"                                                   # → empty

# Tier 3 — repo-wide, excluding tests + MIGRATION.md (catches scripts/skills/configs the
# narrow grep misses — THIS is the reviewer's repo-wide stale-reference check)
rg -n "\b(get_config_value|retry_with_jitter)\b" . -g "!tests/**" -g "!docs/MIGRATION.md"  # → empty

# Then: focused tests green → ruff check → FULL suite green with coverage above the gate.
pixi run pytest tests/unit/config tests/unit/utils -q
pixi run ruff check hephaestus tests
pixi run pytest tests/unit -q   # 5535 passed / 24 skipped, 87.18% ≥ 83% gate
```

#### 16h. Treat it as a BREAKING public-API removal — say so in the PR body, record the rollback

Name the **exact broken import forms** in the PR body so consumers know what to fix:
`from pkg.config import get_config_value`, `from pkg.utils import retry_with_jitter`,
`pkg.get_config_value`, `pkg.retry_with_jitter`. Record the **rollback path**: restore the function
shims, re-add the `__init__` exports + lazy-map entries + deprecation infrastructure
(`_DEPRECATED_LAZY` + the `__getattr__` branch), restore the deletion-guard test files, and revert
the doc changes.

### Phase 17: Issue TITLE vs BODY mismatch — read the BODY + approved plan, treat the title as a possibly-stale label (NEW in v1.13.0, VERIFIED-LOCAL — ProjectHephaestus #1428)

> **Verification — `verified-local`:** This phase was **EXECUTED end-to-end** in a worktree, not
> just planned. The full automation suite passed (**2238 passed**) plus the **29**
> constants / import-surface / automation-boundary tests; `ruff check` + `ruff format` were
> clean and `mypy` was clean over **447 files**. The PR's CI had **not yet merged** at capture
> time, so this phase is `verified-local`, NOT `verified-ci` — do not over-claim. (The rest of
> the skill remains `verified-ci`, except the planning-only Phases 10/13/14/15 and the
> verified-local Phases 16/12d.)

This is the **upstream sibling** of Phase 12a/12d (stale `Evidence:` sections and stale plan
anchors). Those phases assume you already know the right task and are only fighting stale
*locations*. Phase 17 fires one step earlier: when the issue's **TITLE and BODY describe two
DIFFERENT tasks**, you must first decide *which task is even real* before any DRY work begins.

#### 17a. In a TASK/PLAN/REVIEW pipeline, the TITLE is the least-trustworthy field

ProjectHephaestus's automation runs issues through a **TASK → `# Implementation Plan` →
`## 🔍 Plan Review`** pipeline. The issue title is a label that can drift independently of the
body — a stale or mis-applied label from triage. In #1428:

- The **TITLE** said: *"[security] Ruff S102 (exec) suppression blanket across all scripts/ —
  narrow to specific files."*
- The **BODY** was entirely about something **unrelated**: standardizing / consolidating two
  coexisting CLI log-format strings (the library `LOG_FORMAT` ` - `-separated format vs the
  automation `[LEVEL] name:` CLI format).

These are two unrelated tasks. The title was a **mislabel**. Implementing the title's task
("narrow scripts/ S102 suppressions") would have shipped the wrong change entirely.

#### 17b. Resolution rule — BODY + approved plan + plan-review verdict are authoritative

```bash
# BEFORE writing any code, read the full thread — body AND comments:
gh issue view <n> --comments
```

When the title and body disagree, the **issue BODY** and the **approved `# Implementation Plan`
comment** (together with its `## 🔍 Plan Review` verdict) are the **authoritative source of
truth for WHAT to build** — *not* the title. In #1428 the plan review explicitly graded the plan
**"A / GO"** and **confirmed the title-vs-body mismatch was correctly resolved in favor of the
body**. So the title was treated as a possibly-stale label and the body's task was implemented.

**Rule:** in this TASK/PLAN/REVIEW model, read `gh issue view <n> --comments` FIRST, implement
the approved plan against the BODY, and do **not** "fix the title's task" just because the title
says so. (This is the same stale-source discipline as Phase 12a, lifted from the `Evidence:`
list up to the title/body level.)

#### 17c. Worked example — the CLI log-format DRY consolidation (reinforces Phases 8/10/12d)

The body's actual task was a pure DRY + documentation refactor. It reinforces existing phases
rather than introducing new mechanics:

- **Boundary-placement (reinforces Phase 10 step 2 / Phase 14d).** Two CLI log literals —
  `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"` plus the companion
  `datefmt="%Y-%m-%d %H:%M:%S"` — were copy-pasted verbatim across **6** automation modules
  (`_review_utils.py`, `planner.py`, `ci_driver.py`, `audit_reviewer.py`, `plan_reviewer.py`,
  `implementer_cli.py`). The fix added two named constants `CLI_LOG_FORMAT` / `CLI_LOG_DATEFMT`
  to `hephaestus/constants.py` (the **LIBRARY** layer) with a docstring documenting *why* two
  formats coexist. The constants **MUST** live in the library layer: the automation→library
  boundary forbids library code importing `hephaestus.automation`, but allows
  automation → library — so `constants.py` keeps ONE canonical source reachable from both layers
  without violating ADR-0001.

- **Intentional-variant carve-out (reinforces Phase 8c / Phase 10 classify-don't-merge).** A
  **THIRD**, terser log format `"%(asctime)s %(levelname)-7s %(message)s"` lives in
  `github/fleet_sync.py` + `github/tidy.py`. It was deliberately **LEFT UNTOUCHED** and
  documented as an intentional variant — consolidating it would change its output. This mirrors
  the `TRANSIENT_ERROR_CORE` core/extras precedent (Phase 10). The anti-drift acceptance gate was
  a **grep gauntlet**: zero inline CLI literals remain in `hephaestus/automation/` AND the github
  terse variant still shows exactly **2** hits.

  ```bash
  # zero inline CLI literals left in the automation layer:
  grep -rn '%(asctime)s \[%(levelname)s\] %(name)s' hephaestus/automation/   # → empty
  # the intentional github terse variant is preserved (exactly 2 hits):
  grep -rn '%(levelname)-7s' hephaestus/github/                              # → 2
  ```

- **Per-call-site preservation gotcha (reinforces Phase 12 "differences are the risk").** One
  consumer (`implementer_cli.py`) reuses its local `fmt` / `datefmt` names in a later
  `setFormatter()` call, not just `basicConfig`. The minimal behavior-preserving edit was to
  **keep the local names but assign them FROM the constants** (`fmt = CLI_LOG_FORMAT`), rather
  than inlining the constant only at the `basicConfig` call. And one consumer
  (`audit_reviewer.py`) had **no `datefmt=` argument at all** — correctly left without one; do
  **not** add an argument a call site never had.

- **Risk avoided — do NOT change the VALUE of the existing `LOG_FORMAT`.** The pre-existing
  library `LOG_FORMAT` is consumed by `logging/utils.py` and asserted in
  `tests/unit/utils/test_constants.py`; changing its value would alter every library log line and
  break those assertions for no functional gain. Its value was verified **unchanged** as an
  acceptance check — the new `CLI_LOG_FORMAT` is a *separate* constant, not a redefinition.

- **TDD RED-first.** Added the `TestCliLogFormat` constants test and confirmed it failed with
  `ImportError` (the constants did not exist yet) **before** defining them, then went GREEN.

#### 17d. Verification gate (verified-local)

```bash
pixi run pytest tests/unit/automation -q                 # 2238 passed
pixi run pytest tests/unit/utils/test_constants.py \
  tests/unit/test_import_surface.py \
  tests/unit/test_automation_boundary.py -q               # 29 passed (constants + boundary)
pixi run ruff check hephaestus tests && pixi run ruff format --check hephaestus tests
pixi run mypy                                             # clean, 447 files
```

Full automation suite green (2238 passed) + 29 boundary/constants/import-surface tests, ruff
check + format clean, mypy clean over 447 files. Verified locally only; PR CI not yet merged at
capture time (hence `verified-local`, NOT `verified-ci`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Place private helper in a sub-package (`_internal/__init__.py`) | Created `hephaestus/_internal/_version_lookup.py` to group private modules | Triggers circular imports when multiple sibling modules try to import from `_internal`, each bringing their own transitive dependencies that refer back to `_internal` | Use **leaf modules** for private helpers: `_version_lookup.py` (no sub-modules). Packages add layers that create circular paths. |
| Guess PyPI distribution name at runtime from `__name__` or import path | Tried `_dist_name = __name__.split(".")[0]` or `__package__.replace("_", "-").title()` | `importlib.metadata` does NOT normalize distribution names. The name must match the literal `[project].name` value from pyproject.toml exactly. Guessing produced `KeyError` or `PackageNotFoundError`. | Store the PyPI distribution name as a module-level constant in the helper. Do not derive it; it is arbitrary and may differ from the import path. Document the dependency: "Update this constant if [project].name changes in pyproject.toml". |
| Place test for `_version_lookup.py` directly under `tests/unit/` | Created `tests/unit/test_version_lookup.py` | Pre-commit hook `test-file-placement` rejected it — `test_*.py` files cannot live directly under `tests/unit/`. They must be in logical sub-directories that mirror the package structure. | Create `tests/unit/version/` sub-directory and place the test there. This enforces test organization and makes it clear which part of the codebase the test covers. |
| Omit the `-S` flag when committing in a sub-agent dispatch | Ran `git commit -m "..."` without `-S` in a sub-agent shell | The pr-policy CI gate validates commit signatures at the GraphQL layer (via GitHub's `/graphql` API). Commits without valid signatures are flagged as `verification.reason: "unsigned"`, which blocks auto-merge even if all other checks pass. | **Always** use `git commit -S` when creating commits that will be pushed to a PR. The pr-policy gate is non-negotiable for ProjectHephaestus and similar repos. Pre-warm GPG by signing a test commit before agent dispatch if needed. |
| Compare version strings across files to assert "single source" | Wrote drift-check that compared `pyproject.toml` version to `__init__.py` version as strings | After hatch-vcs, `pyproject.toml` no longer has a static `[project].version` field — it declares `dynamic = ["version"]`. String comparisons fail because the field doesn't exist. | Validate the **invariant** (hatch-vcs is configured correctly), not string equality. Check: `dynamic = ["version"]` is present, `[tool.hatch.version].source == "vcs"`. See `hatch-vcs-pyproject-auto-versioning-setup.md` skill. |
| Phase-split directory structure without auditing callers | Added `in_progress`/`completed` split but didn't grep for direct path construction | 17 files still used `experiment_dir / tier_id` directly — silent wrong-dir reads post-merge | ALWAYS run the pre-merge bypass-audit grep before merging any directory-structure change |
| `shutil.move` for a baseline file shared across sibling runs | Moved `pipeline_baseline.json` with the first run during promotion | The second run in the same subtest could no longer find the baseline — it had been moved away | Use `shutil.copy2` for files shared across siblings; only `move` the run directory itself |
| Fix only the broken copy of duplicated JSON-extraction logic | Considered copying the brace-matching fix into the one buggy file | Would have created a 4th duplicate; future bugs need fixing in 4 places | When a bug surfaces duplication, deduplicate to a shared utility FIRST, then the fix lives in one place |
| Plain `"""` docstring containing backslash examples (`\n`) | Wrote extraction-utility docstring with literal backslashes | ruff `D301` failed: "Use r\"\"\" if any backslashes in a docstring" | Use `r"""` for any docstring containing backslashes, even in examples |
| Implement the issue TITLE's task when title and body disagree (#1428) | The title said "narrow Ruff S102 (exec) suppressions across scripts/"; treating the title as the task would have shipped an unrelated security change | In a TASK/PLAN/REVIEW pipeline the title is a label that drifts independently of the body — here the BODY (and the "A / GO" plan review) were entirely about consolidating two coexisting CLI log-format strings. Implementing the title would have been the wrong task. | Read `gh issue view <n> --comments` FIRST; treat the BODY + approved `# Implementation Plan` + `## 🔍 Plan Review` verdict as authoritative for WHAT to build, never the title. |
| Inline the shared CLI log constant only at the `basicConfig` call (#1428) | Replaced the local `fmt`/`datefmt` names with the constant at `basicConfig`, but `implementer_cli.py` reuses those local names in a later `setFormatter()` call | Inlining only at `basicConfig` would leave the later `setFormatter()` referencing now-undefined names (or a stale value), changing behavior | Keep each call site's local `fmt`/`datefmt` names but assign them FROM the constants (`fmt = CLI_LOG_FORMAT`); and never add a `datefmt=` argument to a call site (e.g. `audit_reviewer.py`) that never had one. |
| Consolidate ALL log-format literals, including the github terse variant (#1428) | Tempted to also fold `github/fleet_sync.py` + `tidy.py`'s `"%(levelname)-7s %(message)s"` into the shared constant | That terser format is an INTENTIONAL variant — merging it would change its output | Classify-don't-blindly-merge (Phase 8c/10): leave the intentional variant untouched and documented; prove it with a grep gauntlet (zero automation inline literals AND exactly 2 github-terse hits remain). Also: do NOT change the VALUE of the pre-existing library `LOG_FORMAT` — it's asserted in `test_constants.py` and consumed by `logging/utils.py`. |
| Make `Field(...)` required for an optional-by-usage Pydantic field | Marked `duration_seconds` required in the consolidated base model | Broke existing callers that constructed the object without it | Provide `Field(default=X)` for fields not universally supplied by all callers |
| Mutate a frozen Pydantic model directly | `info.started_at = value` on a `frozen=True` model | Raised `FrozenInstanceError` | Use `model_copy(update={...})` for all field updates on frozen models |
| Rename a class globally without a backward-compat alias | One-pass global rename | Broke external consumers importing the old name | Add `OldName = NewName` alias; old imports keep working |
| Grep only source files for references before deleting/relocating | `--include="*.py"` only | Missed references in `CLAUDE.md`, `docs/`, `scripts/*.py`, `*.yaml` | Grep ALL file types (`.py`, `.mojo`, `.md`, `.yaml`, `.yml`) and use `git rm` to preserve history |
| Leave the same dict structure built in multiple call sites | Kept identical dict construction in a format function and `main()` | Shapes drift independently when new fields are added later | Extract a `_serializable_*()` helper; add a regression test pinning shape parity |
| Lift a mutating closure into a standalone method unchanged | Cut a `nonlocal`-mutating inner function out into a module-level helper as-is | The captured variable became a plain local in the new scope; the caller's value was never updated | Wrap the mutated state in a small mutable box (one-field dataclass or single-element `list` cell) and pass it into the extracted helper |
| Mock a value behind an `@lru_cache` helper without clearing the cache | `unittest.mock.patch` / `monkeypatch.setattr` on the underlying function, then called the cached helper | The cache held the pre-patch value, so the mock was never exercised and the test asserted stale data | Call `helper.cache_clear()` in the test before (and between) patches — ideally via setup/teardown or an autouse fixture |
| Delete a stale script before checking for callers | `git rm old_entrypoint.py` as part of consolidation without grepping first | A kept file still imported / documented it → broken import and dangling doc reference post-merge | Grep all file types for callers FIRST; if a kept file back-references the target, rewrite it self-contained and verify before deleting |
| Keep a hardcoded file list after consolidating the tree | Left `SKILL_FILES = [...]` enumerating discovered files by hand | The list silently rotted as files were added/removed — discovery missed new files and pointed at deleted ones | Discover dynamically with `sorted(Path(...).rglob("*.ext"))` and filter excludes explicitly instead of maintaining an allowlist |
| (PLANNING #1205) Assume two duplicate-*looking* constant lists are pure duplicates and flat-merge them | Planned a single shared frozenset for `TRANSIENT_ERROR_PATTERNS` + `NETWORK_ERROR_KEYWORDS` | The resilience layer's documented contract DELIBERATELY omits `"rate limit"`/`"throttle"` ("rate limit error passthrough — not retried"). A flat merge would make it retry rate-limit errors (contract violation) OR drop them from the network tagger (breaks an existing test) | CLASSIFY first: true-duplicate vs intentional-variant-WITH-overlap. For overlap, extract only the shared CORE into one frozenset and have each consumer compose `CORE \| its-own-extras`. Confirm the "intentional" difference is a real, current contract (docstring + test), not stale drift, before scoping the split |
| (PLANNING #1205) Drop exact phrases "because a broad substring in CORE already covers them" | Considered removing `"connection refused"`/`"connection reset"` from the resilience extras since CORE held the broader `"connection"` | `"connection"` MATCHES `"connection refused"` at runtime, but the resilience test `test_essential_patterns_present` asserts EXACT MEMBERSHIP of the phrase `"connection refused"` — matching-equivalence is NOT membership-equivalence. Dropping the phrase passes behavior but fails the membership assertion | Keep the exact phrases as explicit per-consumer extras even when a broad CORE substring would match them. A flat dedupe that elides "covered" phrases silently breaks membership tests |
| (PLANNING #1205) Change a list literal to `sorted(frozenset \| frozenset)` without checking how callers use it | Planned to recompose `TRANSIENT_ERROR_PATTERNS`/`NETWORK_ERROR_KEYWORDS` as `sorted(CORE \| extras)` | That changes element ORDER and the source TYPE. Any caller relying on original ordering, on `.append()`/mutation, or on index access would break; and the looser `is_network_error` substrings (`"connection"`,`"timeout"`,`"network"`) must not be accidentally tightened/loosened | Before recomposing, grep callers to confirm ONLY iteration is used (no mutation, no indexing, no order dependence). Keep public names + iterable types; treat each behavioral matcher suite (`test_retry.py`, `test_subprocess_resilience.py`) as the real acceptance gate, not the new constant tests |
| Replacing repeated validation wrappers directly with one module-specific helper | Considered importing one validation module's `_required_*` helpers into the others | Each validation module has its own exception class and message wording; sharing a wrapper would leak the wrong exception/message contract | Share only the primitive type checks and keep local wrappers that pass `error_type` plus exact message text |
| Forcing all fake route apps into one route dictionary shape | A single fake app abstraction looked attractive for all server route tests | Tests intentionally index registered routes differently: by rule, by ordered list, by `(rule, method)`, or by `(method, rule)` | Share the decorator mechanics in a base helper, then keep explicit small storage adapters so test assertions remain clear |
| Reusing a merged feature branch for a follow-up cleanup PR | Current branch already had a merged PR, so committing on it would have produced a confusing branch/PR relationship | GitHub reported the branch's prior PR as `MERGED`; a new PR needed a new branch from current trunk | Stash uncommitted work, fetch current trunk, create a fresh branch from `origin/<trunk>`, pop the stash, re-verify, sign, push, and open the new PR |
| Trusting the issue body's "Evidence:" file list for a dedup scope | Assumed 4 files had `_sign()` per the issue; started planning a 4-file refactor | Prior PRs had partially resolved the issue — 3 of the 4 files had already migrated to the canonical `sign_body()`. Only 1 file had the wrapper remaining | **Grep first.** `grep -rn "def _sign"` shows current truth; the issue Evidence section reflects creation-time state, not current HEAD. |
| Added a pytest fixture to conftest.py for a pure `bytes→str` HMAC helper | Wrapped `sign_body(body, INTEGRATION_TEST_SECRET)` as a pytest fixture so tests could receive it via DI | Introduced unnecessary indirection — the helper takes two args, one of which is a module-local constant, making the fixture callers less readable than just calling the function directly | For a pure `bytes→str` function closing over a local constant, **inline** the call (`sign_body(body_bytes, LOCAL_SECRET)`) at each call site; save fixtures for stateful or async setup |
| Rebased onto the diverged remote branch that had a competing solution | `git pull origin 329-auto-impl` triggered a rebase with 84 commits and multiple conflicts | The remote had taken a different architectural approach; rebasing imported 84 unrelated commits and produced conflicts at every differing point | `git rebase --abort`; create a fresh local branch from current state; push as a new branch; open a new PR. The remote's competing solution becomes a sibling PR for maintainer review — don't overwrite it |
| (PLANNING #1381) Trust the issue's duplicate COUNT and "byte-for-byte identical" claim | Issue stated "6 nearly-identical `_print_summary` methods, 5 byte-for-byte identical"; planned a 6-method extraction removing ~100 lines | Stale. Only 4 were true duplicates: `IssueImplementer` had already been refactored to delegate to a richer `ImplementationSummaryPrinter`; `Planner` had a different signature and operated on a different model (`PlanResult` vs `WorkerResult`). Real scope was 4 methods / ~70 lines | The duplicate COUNT and "byte-for-byte identical" assertion go stale exactly like the "Evidence:" section (extends Phase 12a). DIFF every claimed-duplicate body in full before scoping — don't trust the count |
| (PLANNING #1381) Flat-merge the 4 "identical" methods into one hard-coded helper | The 4 bodies looked identical in review, so a single helper with fixed strings seemed safe | Two real behavioral diffs would have been silently changed: (a) one logged `"Total PRs:"` vs the others' `"Total issues:"`; (b) two used a leading-newline `"\nFailed issues:"` header, two did not | "Looks identical in review" != "is identical." Parameterize call-site-varying string args as kwargs-with-defaults (`count_noun=`, `failed_header=`) to guarantee zero behavior change — an application of Phase 8c classify-before-merge to a shared function's varying string args |
| (PLANNING #1381) Put the new helper in a new leaf module or a base-class method | Considered a fresh `_summary_printing.py` module or a mixin/base-class `_print_summary` | A new module/base class adds a layer when an established-dedup home already fits the boundary; `_review_utils.py` already houses reviewer-trio dedup (#599) and a module `logger`, and is an automation-layer helper with no upward library import | Prefer an EXISTING established-dedup module that already fits the architecture boundary over creating a new leaf module or base-class method |
| (PLANNING #1383) Delete the duplicated method after extracting it to a free function | Planned to remove `_load_impl_session_id` from both `CIDriver` and `AddressReviewer` once `load_impl_session_id` existed | The method is a **patched test seam** — `patch.object(obj, "_load_impl_session_id", ...)` at `test_ci_driver.py:789,830,848,884,2344,2358` and `test_address_review.py:680,714`. Deleting it breaks every patch target | Grep `patch.object(.*"_method"` BEFORE planning deletion. Keep each method as a one-line thin wrapper delegating to the new free function so the seam survives |
| (PLANNING #1383) Collapse two "near-identical" methods' logging without checking the tests | The copies differed in log level (`logger.debug` vs `logger.warning`), an extra truncated-session debug line, and exception wording; plan collapsed to one logging style | "Near-identical" hides behavior-bearing diffs; collapsing logging is only safe if no test asserts log level/message | Read the actual test bodies (`test_ci_driver.py:126-132`, `test_address_review.py:103-111` assert only the `None` return) to confirm which diffs are incidental; state explicitly in the plan what you collapsed and why it's safe |
| (PLANNING #1383) Invent a new sharing mechanism for the shared helper | Considered a mixin / base class for `load_impl_session_id` | The target module `_review_utils.py` already houses cross-reviewer helpers as free functions with explicit args (`find_pr_for_issue`, `instance_log`, `parse_json_block`); a new mechanism is higher-risk | Grep the target module's existing helpers and match its established convention (free function, explicit args) rather than introducing a mixin/base-class method |
| (PLANNING #1383) Assert un-run imports/boundary facts as true in the plan | Wrote "Path is imported", "the `from ._review_utils import ...` line exists", "no boundary violation" without executing | A planning-only plan ran nothing; stating unverified facts as certain misleads the implementer/reviewer | Hedge: "add `pathlib.Path` if not present"; "verify-and-extend the existing import line, else add"; confirm the automation→library import (`hephaestus.agents.runtime`) is the allowed direction with no cycle and that the new helper stays out of the base `import hephaestus` surface (`test_import_surface.py` / `test_automation_boundary.py`) |
| (PLANNING #1383) Accept new structural helper tests alone as proof of a behavior-preserving refactor | Planned to add tests for `load_impl_session_id` and call the refactor done | New structural tests prove the helper exists, not that behavior is unchanged | The real acceptance gate is the PRE-EXISTING per-class suites (`test_ci_driver.py`, `test_address_review.py`) staying green, plus a single-canonical-source grep that returns exactly one hit (`grep -rn 'state_dir / f"issue-{issue_number}.json"' hephaestus/automation/`) |
| (PLANNING #1504) Delete the duplicate-bearing script instead of shimming it | Considered `git rm scripts/check_unit_test_structure.py` since its mirror logic duplicates the library | The script is referenced by `scripts/README.md`, the `python-repo-modernization` skill, AND smoke-tested via auto-discovery (`tests/unit/scripts/conftest.py` globs `scripts/*.py`); deletion breaks those references and a documented invocation | When a duplicate-bearing script ALSO owns one unique function, SHIM not DELETE: move the unique fn into the library as canonical, rewrite the script as a thin shim. Keeps the public surface stable (POLA) while removing duplication (DRY) |
| (PLANNING #1504) Make the shim call the library's `main()`/`check_test_structure` | Looked simplest to delegate the whole script to one library entry point | `check_test_structure` ALSO runs no-loose-files / no-unsanctioned-dirs checks the script NEVER ran — the shim would suddenly fail on conditions outside its contract — and the library returns data tuples while the script prints its own ERROR/OK lines (literal `→` arrow, exact phrasing) | Call the GRANULAR functions (`check_test_directory_mirrors` + `check_scripts_coverage`) and REPRODUCE the byte-for-byte stdout/stderr in the shim; do not route through `main()`/`check_test_structure` |
| (PLANNING #1504) Import the private `_get_subpackages` from the library without a fallback | Planned `from hephaestus.validation.test_structure import _get_subpackages` in the product script | A leading-underscore import across the script→library boundary is the most reviewer-contentious choice; a reviewer may reject it outright | Offer a fallback (compute the subpackage count from data the PUBLIC functions already return) and present both options so the reviewer has an out |
| (PLANNING #1504) Claim a RED→GREEN TDD cycle for the new library test | The plan added a test class for `check_scripts_coverage` after copying its body into the library | The function body already existed (copied verbatim from the script), so the test passes immediately — it is GREEN-first, there was no genuine RED phase | Note the inversion honestly; if a real RED is wanted, write the library test + exact `(ok, error_lines)` contract assertion BEFORE pasting the body |
| (PLANNING #1504) Assume `scripts/README.md` and the not-wired-to-CI claim need no re-check | Plan asserted the script is not in CI/pre-commit (only `hephaestus-check-test-structure` is wired) and the README line stays accurate | These were grep-claimed but un-run reliances; once the shim is what's transitively wired, the README "Wired into pre-commit" line may read as inaccurate, and a CI-wired script would make the output contract a gate not a smoke test | Record un-run reliances as explicit RISKS for the reviewer: re-confirm the script is not CI/pre-commit-wired, re-judge the README accuracy, and diff the copied glob-marker check (`glob("*.py")` AND `glob('*.py')`) line-by-line or the broken-glob test gives a false pass |
| (VERIFIED-LOCAL #1420) Removed only the function definition and the module `__all__` for a deprecated public symbol | Deleted `get_config_value`/`retry_with_jitter` from their module body and the subpackage `__init__.__all__`, then claimed removal | The top-level `hephaestus.<symbol>` STILL resolved via `_LAZY_IMPORTS`; the `_DEPRECATED_LAZY` dict + `__getattr__` deprecation branch still emitted a warning; `dir(hephaestus)`/import guards still listed it; docs still annotated it `**(deprecated)**` | Enumerate ALL surfaces before claiming removal: impl, subpackage `__init__` import + `__all__`, top-level `_LAZY_IMPORTS` + `__all__`, deprecation infrastructure (`_DEPRECATED_LAZY` + `__getattr__` branch, then SIMPLIFY `__getattr__`), tests, and docs. A module-source-only grep finds surface (a) and misses the other five |
| (VERIFIED-LOCAL #1420) Edited the deprecation-guard test to drop the warning assertion | Trimmed `test_deprecation_warnings.py` / `test_docs_deprecation_sync.py` to remove the now-failing `pytest.warns(DeprecationWarning)` line instead of deleting the file | The file's SOLE purpose is guarding the deprecation; a trimmed version asserts nothing and rots as dead scaffolding. The same trap hit the per-symbol deprecated test CLASS (`TestGetConfigValue`/`TestRetryWithJitter`) inside otherwise-valid mixed files | DELETE deprecation-guard files outright; delete the per-symbol deprecated test class in mixed files and prune the symbol from those files' imports — but RE-GREP first to confirm `patch`/`MagicMock` are still used elsewhere before removing them (they usually are) |
| (VERIFIED-LOCAL #1420) Ran only the module-source grep to verify the removal | `rg get_config_value hephaestus/config/config.py` came back empty, so declared done | Missed the COMPATIBILITY.md per-subpackage table row + "Deprecated symbols" callout + flat lazy-symbol prose list, a ROADMAP.md example, and an integration test that popped the symbol from `__dict__` as a `dir()`-no-warn probe | Run the three-tier grep gauntlet: (1) `rg <syms> hephaestus -g "*.py"` empty; (2) `rg <syms> COMPATIBILITY.md README.md docs -g "*.md" | rg -v "^docs/MIGRATION.md:"` empty (intentional migration guidance excepted); (3) repo-wide `rg <syms> . -g "!tests/**" -g "!docs/MIGRATION.md"` empty. Repoint fixtures that USE the symbol (e.g. to `retry_with_backoff`) rather than deleting them |
| (VERIFIED-LOCAL #1427) Trusted the approved plan's exact `file:line` anchor (`ensure_state_labels.py:189`) | The plan — graded "A / GO" with a strict review claiming "Verified accurate against disk" — said the drifted no-brackets log format lived at `hephaestus/automation/ensure_state_labels.py:189` | That file had **no `format=` line at all**; both the line number AND the filename were stale. The literal actually lived in `hephaestus/cli/utils.py:222` inside `configure_cli_logging()`, which `ensure_state_labels.main()` calls indirectly. Only the described symptom (a no-brackets variant exists somewhere) was real; the plan also under-counted the per-module literals | A stale anchor can be a wrong FILENAME, not just a wrong line number or stale count — and a strict-reviewed "verified against disk" plan does NOT exempt you. Grep the CURRENT tree for the literal pattern the plan DESCRIBES (`grep -rn '<the literal>' hephaestus/`), map the plan's INTENT onto the real call sites, and re-count every occurrence yourself. The real fix may live at an indirection root (a shared helper the named file merely calls) — fixing `configure_cli_logging` transitively fixed the `ensure_state_labels` concern |

## Results & Parameters

### Radiance v1.6.0 Local Verification

| Check | Result |
| ----- | ------ |
| Ruff | `./.venv/bin/python -m ruff check radiance scripts tests --no-cache` passed |
| Full pytest | `1249 passed, 6 skipped` locally and again in the pre-push hook |
| Compileall | `./.venv/bin/python -m compileall radiance scripts tests` passed |
| Diff hygiene | `git diff --check` passed |
| PR | LLM360/Radiance PR #908 opened; CI pending at capture time |

### Code Changes

**Files Modified**: 2

- `scylla/e2e/runner.py` - Implementation
- `tests/unit/e2e/test_runner.py` - Tests

**Lines Changed**: +173 / -18

### Test Coverage

**New Tests**: 4 unit tests

- `test_empty_tier_results()` - Empty dict handling
- `test_single_tier_result()` - Single item aggregation
- `test_multiple_tier_results()` - Multi-item aggregation
- `test_zero_token_stats()` - Zero value handling

**Regression Tests**: 467 E2E tests passed

### Helper Method Pattern

```python
def _aggregate_token_stats(self, tier_results: dict[TierID, TierResult]) -> TokenStats:
    """Aggregate token statistics from all tier results.

    Args:
        tier_results: Dictionary mapping tier IDs to their results

    Returns:
        Aggregated token statistics across all tiers. Returns empty
        TokenStats if tier_results is empty.
    """
    from functools import reduce

    if not tier_results:
        return TokenStats()

    return reduce(
        lambda a, b: a + b,
        [t.token_stats for t in tier_results.values()],
        TokenStats(),
    )
```

### Key Implementation Details

1. **Import placement**: `from functools import reduce` inside method
2. **Empty handling**: Explicit check with early return
3. **Identity element**: Empty `TokenStats()` as third parameter to `reduce`
4. **Type hints**: Complete signature with proper types
5. **Docstring**: Clear description with Args and Returns sections

## Success Metrics

| Metric | Value |
| -------- | ------- |
| Duplication eliminated | 2 instances → 1 helper |
| Lines saved | ~15 lines per call site |
| Test coverage | 4 comprehensive tests |
| Regression tests | 467 tests pass |
| Pre-commit checks | All pass |
| Time to implement | ~30 minutes |

## Verified On

| Project | Issue/PR | Scope | Verification |
| --------- | ---------- | ------- | -------------- |
| ProjectHephaestus | #739 | Private module extraction | verified-ci |
| ProjectScylla | dir-structure split | Path-constant bypass audit | verified-ci |
| ProjectHephaestus | #1205 | Phase 10 core/extras split for overlapping `TRANSIENT_ERROR_PATTERNS` / `NETWORK_ERROR_KEYWORDS` | ⚠️ **unverified — planning only, NOT executed** (no code, no tests, no CI) |
| LLM360/Radiance | PR #908 | Consolidated route-test fakes, layout-only metric kernels, validation field checks, and removed stale `hf_checkpoint_architecture_html.py` | verified-local — full local/pre-push test suite passed; PR CI pending at capture time |
| ProjectHermes | #329 / PR #652 | Phase 12 — stale issue body (3 of 4 files already migrated), inline over fixture for pure HMAC helper, new-branch resolution for diverged remote | verified-ci — all pytest passed, signed commit, PR opened |
| ProjectHephaestus | #1381 | Phase 13 — stale "6 methods / 5 byte-for-byte identical" claim (only 4 real duplicates), parameterize call-site-varying `count_noun`/`failed_header` instead of flat-merge, place helper in existing `_review_utils.py` | ⚠️ **unverified — planning only, NOT executed** (no code, no tests, no CI) |
| ProjectHephaestus | #1383 | Phase 14 — planning a method→free-function extraction (`_load_impl_session_id` → `load_impl_session_id` in `_review_utils.py`) where the method is a patched test seam | ⚠️ **unverified — planning only, NOT executed** (no code, no tests, no CI) |
| ProjectHephaestus | #1504 | Phase 15 — planning a duplicate-bearing script → library-shim consolidation (`scripts/check_unit_test_structure.py` → shim over `hephaestus/validation/test_structure.py`); move unique `check_scripts_coverage` into the library, preserve byte-for-byte stdout/stderr via granular fns | ⚠️ **unverified — planning only, NOT executed** (no code, no tests, no CI) |
| ProjectHephaestus | #1420 | Phase 16 — deprecated public-API symbol removal across ALL surfaces (`get_config_value()` in `hephaestus/config`, `retry_with_jitter()` in `hephaestus/utils`): impl + subpackage `__init__`/`__all__` + top-level `_LAZY_IMPORTS` + `_DEPRECATED_LAZY`/`__getattr__` deprecation infra + deleted guard test files + multi-location docs; three-tier stale-ref grep gauntlet | **verified-local** — full local suite green (5535 passed / 24 skipped, 87.18% ≥ 83% gate), ruff clean, repo-wide greps empty; PR CI not yet merged at capture time |
| ProjectHephaestus | #1427 | Phase 12d — an APPROVED, strict-reviewed plan ("A / GO", "verified against disk") named a stale anchor `ensure_state_labels.py:189`; the real drifted log-format literal lived at the indirection root `cli/utils.py:222` (`configure_cli_logging`). Re-grepped the literal on the CURRENT tree, mapped plan INTENT onto real call sites, consolidated to `constants.AUTOMATION_LOG_FORMAT` / `LOG_DATEFMT` with anti-drift parity tests | **verified-local** — single-source grep returns only the canonical `constants.py` definition, full unit suite 5203 passed / 23 skipped, 87.22% ≥ 83% gate, ruff clean, import-surface + automation-boundary guards green; PR CI not yet merged at capture time |
| ProjectHephaestus | #1428 | Phase 17 — issue TITLE vs BODY mismatch: a title saying "narrow Ruff S102 exec suppressions across scripts/" over a body entirely about consolidating two coexisting CLI log-format strings; read `gh issue view --comments` FIRST and implement the BODY + approved plan ("A / GO" review confirmed the mismatch), not the title. Worked DRY consolidation: new `CLI_LOG_FORMAT`/`CLI_LOG_DATEFMT` in the LIBRARY-layer `constants.py` across 6 automation modules, github terse format left as a documented intentional variant, per-call-site `fmt`/`datefmt` preserved, `LOG_FORMAT` value unchanged | **verified-local** — full automation suite 2238 passed + 29 boundary/constants/import-surface tests, grep gauntlet (0 automation inline literals / exactly 2 github-terse hits), ruff + mypy clean (447 files); PR CI not yet merged at capture time |

## Related Skills

- `token-stats-aggregation` (evaluation) - Token aggregation pattern
- `codebase-consolidation` (architecture) - Finding duplicates
- `testing-python-constants-module` (testing) - frozenset/immutability/membership tests referenced by Phase 10

## Tags

`refactoring`, `dry-principle`, `helper-methods`, `radiance`, `test-fakes`, `validation-wrappers`, `layout-kernels`, `tdd`, `code-quality`, `python`, `pytest`, `private-modules`, `test-structure`, `git-signing`, `importlib-metadata`, `srp`, `extract-method`, `lru-cache`, `mock-patch`, `rglob`, `dead-code-removal`, `constants`, `frozenset`, `drift`, `intentional-variant`, `core-extras-split`, `planning`, `stale-issue-body`, `inline-vs-fixture`, `remote-branch-divergence`, `hmac`, `test-helper-dedup`, `stale-duplicate-count`, `diff-before-merge`, `parameterize-defaults`, `print-summary`, `existing-dedup-home`, `patched-test-seam`, `thin-wrapper`, `free-function-extraction`, `automation-library-boundary`, `script-to-library-shim`, `shim-vs-delete`, `output-contract-preservation`, `byte-for-byte-stdout`, `granular-vs-main`, `private-import-boundary`, `tdd-green-first-inversion`, `duplicate-bearing-script`, `deprecated-api-removal`, `breaking-change`, `lazy-loader`, `lazy-imports`, `deprecation-guard-test`, `pep-562`, `all-surfaces`, `absence-guard-test`, `repo-wide-grep-gauntlet`, `compatibility-doc`, `migration-doc`, `stale-plan-anchor`, `wrong-filename-anchor`, `indirection-root`, `grep-current-state`, `verified-against-disk-not-exempt`, `log-format-constants`, `configure-cli-logging`, `title-body-mismatch`, `stale-issue-title`, `task-plan-review-pipeline`, `authoritative-source-of-truth`, `approved-plan`, `cli-log-format`, `boundary-placement`, `intentional-variant-carveout`, `grep-gauntlet`

## Version History

- **v1.13.0** (2026-06-30, **verified-local for the new phase**): Added Phase 17 — issue TITLE vs BODY mismatch in a TASK/PLAN/REVIEW automation pipeline. Captured from an EXECUTED ProjectHephaestus #1428 session: the issue title said "[security] narrow Ruff S102 (exec) suppressions across scripts/" while the body was entirely about DRY-consolidating two coexisting CLI log-format strings — two unrelated tasks. (17a) In this pipeline the title is the least-trustworthy field — a label that drifts independently of the body. (17b) Resolution rule: read `gh issue view <n> --comments` FIRST and treat the BODY + the approved `# Implementation Plan` comment + its `## 🔍 Plan Review` verdict as authoritative for WHAT to build, never the title (the #1428 review graded the plan "A / GO" and explicitly confirmed the title-vs-body mismatch was resolved in favor of the body) — the same stale-source discipline as Phase 12a, lifted up to the title/body level. (17c) Worked CLI-log-format consolidation reinforcing Phases 8/10/12d: new `CLI_LOG_FORMAT`/`CLI_LOG_DATEFMT` constants placed in the LIBRARY-layer `hephaestus/constants.py` (automation→library boundary forbids library→automation but allows automation→library) replacing literals copy-pasted across 6 automation modules; a THIRD terse github format (`fleet_sync.py`/`tidy.py`) left as a documented intentional variant (mirrors `TRANSIENT_ERROR_CORE`), proven by a grep gauntlet (0 automation inline literals AND exactly 2 github-terse hits); per-call-site preservation (keep `implementer_cli.py`'s local `fmt`/`datefmt` names assigned FROM the constants for its later `setFormatter()`; do NOT add a `datefmt=` arg to `audit_reviewer.py` which never had one); and the pre-existing library `LOG_FORMAT` value left UNCHANGED (consumed by `logging/utils.py`, asserted in `test_constants.py`). (17d) TDD RED-first via `TestCliLogFormat`. Added 3 Failed Attempts rows, a Verified On entry, an Outcome entry, a description item (18), and tags. Bumped frontmatter `version` to 1.13.0; `date` stays 2026-06-30; frontmatter `verification` stays `unverified` (per the v1.10.0+ convention), with Phase 17 carrying its own inline `verified-local` label. EXECUTED end-to-end: full automation suite green (2238 passed) + 29 boundary/constants/import-surface tests, ruff check+format clean, mypy clean (447 files); PR CI not yet merged at capture time (hence verified-local, NOT verified-ci). Prior v1.12.0 snapshot archived to history.
- **v1.12.0** (2026-06-30, **verified-local for the new sub-section**): Added Phase 12d — a stale anchor in an APPROVED implementation plan can be a wrong FILENAME (not just a wrong line number or stale count), and a plan that passed STRICT review claiming "verified accurate against disk" does NOT exempt the implementer from re-grepping the current tree. Captured from an EXECUTED ProjectHephaestus #1427 session (consolidate two coexisting log-format strings — `LOG_FORMAT` and the automation `[LEVEL] name:` format — into named constants `AUTOMATION_LOG_FORMAT`/`LOG_DATEFMT` in `hephaestus/constants.py`). The approved plan (and its "A / GO" review) named the drifted no-brackets variant at `hephaestus/automation/ensure_state_labels.py:189`, but that file had no `format=` line; the literal lived at the indirection root `hephaestus/cli/utils.py:222` inside `configure_cli_logging()`, which `ensure_state_labels.main()` calls indirectly. Both line number AND filename were stale; the plan also under-counted the per-module literals. Lesson: grep the CURRENT tree for the literal pattern the plan DESCRIBES (`grep -rn '<the literal>' src/`), map plan INTENT onto real call sites, re-count occurrences yourself, and fix the indirection root (which transitively fixed the symptom). Added one Failed Attempts row, a Verified On entry, an Outcome entry, a description item (17), and tags. Bumped frontmatter `version` to 1.12.0; `date` stays 2026-06-30; frontmatter `verification` stays `unverified` (per the v1.10.0+ convention), with Phase 12d carrying its own inline `verified-local` label. EXECUTED end-to-end: full unit suite green (5203 passed / 23 skipped, 87.22% coverage ≥ 83% gate), ruff clean, single-source grep returns only the canonical `constants.py` definition, anti-drift parity + import-surface/automation-boundary guards green; PR CI not yet merged at capture time (hence verified-local, NOT verified-ci). Prior v1.11.0 snapshot archived to history.
- **v1.11.0** (2026-06-30, **verified-local for the new phase**): Added Phase 16 — deprecated public-API symbol removal across ALL surfaces, captured from an EXECUTED ProjectHephaestus #1420 session (removed `get_config_value()` from `hephaestus/config` and `retry_with_jitter()` from `hephaestus/utils`). Eight sub-sections: (16a) enumerate ALL surfaces before claiming removal — impl, subpackage `__init__` import + `__all__`, top-level `_LAZY_IMPORTS` + `__all__`, deprecation infrastructure (`_DEPRECATED_LAZY` + `__getattr__` branch, then SIMPLIFY `__getattr__`), tests, docs (a module-source-only grep misses five of six); (16b) discovery-first repo-wide grep, classify every hit, confirm ZERO runtime callers; (16c) TDD absence-guard tests FIRST (real RED) — bust the PEP 562 cache via `pkg.__dict__.pop(symbol, None)` and wrap `hasattr`/`dir` in `catch_warnings()`/`simplefilter("ignore", DeprecationWarning)`; (16d) DELETE deprecation-guard test files outright (don't trim them) and the per-symbol deprecated test CLASS, re-grep before pruning `patch`/`MagicMock` imports; (16e) repoint integration fixtures off the removed symbol (e.g. to `retry_with_backoff`) and add a parametrized `REMOVED_DEPRECATED_SYMBOLS` absence guard; (16f) docs are multi-location — COMPATIBILITY.md (prose list + callout + table-row `**(deprecated)**` + per-subpackage callout), MIGRATION.md (convert to a "Removed deprecated symbols" table noting the BREAKING `ImportError`), ROADMAP.md example; (16g) three-tier grep gauntlet (package source / docs-except-MIGRATION / repo-wide-except-tests) then focused tests → ruff → full suite; (16h) treat as a BREAKING removal — name the exact broken import forms in the PR body and record the rollback path. Added 3 Failed Attempts rows, a Verified On entry, and tags. Bumped frontmatter `version` to 1.11.0 and `date` to 2026-06-30; `verification` stays `unverified` at the frontmatter level (per the prior v1.10.0 convention), with Phase 16 carrying its own inline `verified-local` label. EXECUTED end-to-end: full local suite green (5535 passed / 24 skipped, 87.18% coverage ≥ 83% gate), ruff clean, repo-wide stale-ref greps empty; PR CI not yet merged at capture time (hence verified-local, NOT verified-ci). Prior v1.10.0 snapshot archived to history.
- **v1.10.0** (2026-06-26, **planning-only for the new phase / unverified**): Added Phase 15 — planning a duplicate-bearing standalone script → library-shim consolidation with output-contract preservation, captured from ProjectHephaestus #1504 (`scripts/check_unit_test_structure.py` duplicates `get_subpackages()`/subpackage-mirror logic in `hephaestus/validation/test_structure.py` but uniquely owns `check_scripts_coverage()`). Five sub-sections: (15a) SHIM over DELETE — move the unique function into the library as canonical `(ok, error_lines)`, export from `hephaestus/validation/__init__.py`, rewrite the script as a thin shim, because the script is referenced by `scripts/README.md`, the `python-repo-modernization` skill, and auto-discovery smoke tests (`tests/unit/scripts/conftest.py`); (15b) output-contract preservation — reproduce byte-for-byte stdout/stderr (literal `→` arrow, exact phrasing) by calling the GRANULAR functions (`check_test_directory_mirrors` + `check_scripts_coverage`), NOT `main()`/`check_test_structure` which run extra no-loose-files/no-unsanctioned-dirs checks the script never ran; (15c) the private `_get_subpackages` import across the script→library boundary is the reviewer-contentious choice — offer a data-derived fallback; (15d) record un-run reliances as explicit risks (not-CI/pre-commit-wired claim, README accuracy judgment call, exact single-vs-double-quote glob-marker check copied verbatim); (15e) TDD GREEN-first inversion — a library test written after copying the body is not RED, don't claim a cycle you didn't have. Added 5 Failed Attempts rows, a Verified On entry, trigger phrases, and tags. Bumped frontmatter `version` to 1.10.0, `date` to 2026-06-26, and `verification` to `unverified`. NOT executed end-to-end (no code, no tests, no CI). Sibling to the planning-only Phases 10/13/14. Prior v1.9.0 snapshot archived to history.
- **v1.9.0** (2026-06-20, **planning-only for the new phase / unverified**): Added Phase 14 — planning a behavior-preserving method→free-function extraction when the duplicated method is a patched test seam, captured from ProjectHephaestus #1383 (extract `_load_impl_session_id` → `load_impl_session_id(state_dir, issue_number, agent)` in `hephaestus/automation/_review_utils.py`). Five sub-sections: (14a) grep `patch.object` before deletion — keep each method as a thin wrapper to preserve the seam; (14b) read tests to separate behavior-bearing diffs (log level/message) from incidental ones before collapsing "near-identical" copies; (14c) match the target module's free-function convention rather than a mixin/base class; (14d) hedge unverified import/boundary assumptions (Path import, existing import line, automation→library direction, base-import-surface cleanliness); (14e) prove a pure extraction via a single-hit canonical grep + EXISTING per-class behavioral suites staying green. Added 5 Failed Attempts rows, a Verified On entry, new trigger phrases, and tags. NOT executed end-to-end (no code, no tests, no CI). The rest of the skill stays `verified-ci`; Phase 14 carries its own unverified warning. Sibling to the #1381 Phase 13 (stale-count) added the same day. Prior v1.8.0 snapshot archived to history.
- **v1.8.0** (2026-06-20, **planning-only / unverified**): Added Phase 13 — stale "N identical duplicates" claims in extraction issues. Captured from PLANNING ProjectHephaestus issue #1381 ("Extract shared `print_worker_summary` helper"); NOT executed end-to-end (no code, no tests, no CI). Lessons: (1) an issue's duplicate COUNT and "byte-for-byte identical" assertion go stale exactly like its "Evidence:" section (extends Phase 12a) — an issue claiming "6 methods, 5 byte-for-byte identical" had only 4 true duplicates (one already delegated to a richer `ImplementationSummaryPrinter`, one with a different signature/model `PlanResult` vs `WorkerResult`); count and DIFF every claimed-duplicate body before scoping. (2) Even the 4 "identical" bodies hid two call-site-varying literals (`"Total PRs:"` vs `"Total issues:"`; leading-newline `"\nFailed issues:"` header vs none) — parameterize as kwargs-with-defaults (`count_noun=`, `failed_header=`) to guarantee zero behavior change, an application of Phase 8c classify-before-merge to a shared function's string args. (3) Placement: prefer an EXISTING established-dedup module (`_review_utils.py`, already houses #599 reviewer-trio dedup + a module `logger`) over a new leaf module or base-class method. Added 3 Failed Attempts rows and a Verified On row. Recorded most-uncertain planning assumptions as explicit risks. Prior v1.7.0 snapshot archived to history.
- **v1.7.0** (2026-06-19): Added Phase 12 — three concrete lessons from ProjectHermes #329 (HMAC `_sign()` dedup): (1) grep the CURRENT state before trusting issue body "Evidence:" sections (prior PRs may have partially resolved it); (2) inline a pure `bytes→str` helper over adding a pytest fixture or conftest entry when the function closes over a module-local constant; (3) when a remote branch has diverged with a competing solution, push as a new branch rather than force-pushing or rebasing 84 conflicting commits. Added 3 Failed Attempts rows. Updated Verified On table. Verification: verified-ci via ProjectHermes PR #652. Prior v1.6.0 snapshot archived to history.
- **v1.6.0** (2026-06-18): Added Phase 11, a locally verified Radiance behavior-preserving duplicate cleanup workflow. Captures shared server route test fakes, parameterized layout-only metric kernels via `LayoutReindexKernel`, shared primitive validation field checks with local wrappers preserving exception/message contracts, stale script deletion after caller audit, and the fresh-branch PR workflow when the current branch's old PR is already merged. Verification was local/pre-push only; PR #908 CI was pending at capture time. Prior v1.5.0 snapshot archived to history.
- **v1.5.0** (2026-06-12): Added Phase 10 (PLANNING-ONLY, **unverified**) — the core/extras split for consolidating OVERLAPPING constant collections that are intentional-variants-with-overlap, not pure duplicates. Refines the Phase 8c classification table with a third middle path: extract only the shared CORE into one immutable frozenset, compose each consumer as `CORE | extras`, and prove anti-drift with `CORE.issubset(consumer)` parity tests while keeping public names/types. Added 3 Failed Attempts rows (flat-merge-violates-contract, drop-phrases-because-broad-substring-covers-them, recompose-changes-order/type) and a `## Verified On` table. Captured from planning ProjectHephaestus issue #1205; NOT executed end-to-end (no code, no tests, no CI). Prior v1.4.0 snapshot archived to history.
- **v1.4.0** (2026-06-07): Restored SRP/LRU-cache/stale-script DRY patterns lost in the v1.3.0 absorption (nuance audit). Added Phase 9 + `### Detailed Steps`: extract-method/SRP decomposition with mutable-box closure conversion, `@lru_cache` detection util with the `mock.patch`/`cache_clear()` gotcha, stale-script/deprecated-stub cleanup (grep callers first, rewrite back-references self-contained), and dynamic `Path.rglob` discovery. Added 4 Failed Attempts rows.
- **v1.3.0** (2026-06-07): Absorbed 5 skills — `centralized-path-constants`, `private-module-extraction-helper-pattern`, `deduplicate-llm-json-extraction`, `dry-consolidation-workflow`, `dry-consolidate-to-canonical-refactor`. Added Quick Reference h3 and Phase 8 (path constants, LLM JSON dedup, discovery/classify pass, Pydantic type hierarchy, dict-structure consolidation, orphan relocation). Extended description and Failed Attempts. Full originals preserved in history.
- **v1.1.0** (2026-06-04): Added Phase 7 covering private module extraction patterns, test structure mirroring enforcement, cryptographic commit signing, PyPI distribution name handling. Verified via ProjectHephaestus issue #739.
- **v1.0.0** (2026-02-15): Initial release covering token aggregation extraction with TDD workflow.
