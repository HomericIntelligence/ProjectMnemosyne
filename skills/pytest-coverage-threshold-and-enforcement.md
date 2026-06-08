---
name: pytest-coverage-threshold-and-enforcement
description: "Use when: (1) establishing [tool.coverage.report].fail_under as the single source of truth by removing redundant --cov-fail-under from CI and pyproject.toml addopts; (2) configuring multiple coverage report formats (xml, html, lcov) for CI and local use; (3) CI coverage % is lower than local because GitHub computes coverage against the merge-preview tree (PR HEAD merged with main HEAD) — adding entries to coverage.run.omit for files not on the branch IS the correct fix; (4) aggregate coverage gates hide under-tested critical modules — enforce per-file floors via parse_module_coverage() + coverage.toml + CI step; (5) some modules are intentionally omitted from measurement (live CLI/TTY) and need an integration backstop to catch import-time regressions; (6) pytest.importorskip() guards hide easy coverage wins — install optional deps and write targeted branch tests; (7) tuning coverage thresholds to match actual baselines and avoid false CI failures; (8) generate_coverage.sh fails in CI with wrong paths, cmake source dir errors, lcov gcov version mismatch on Ubuntu 24.04, or geninfo 'unable to create link .gcda'; (9) coverage is raised by adding targeted tests for uncovered branches plus unlocking skipped optional-dependency test groups."
category: testing
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: pytest-coverage-threshold-and-enforcement.history
tags:
  - coverage
  - pytest
  - fail-under
  - single-source-of-truth
  - per-module-floors
  - merge-preview
  - integration-backstop
  - optional-deps
  - importorskip
  - lcov
  - gcov
  - ci-cd
---

# Pytest Coverage Threshold and Enforcement

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Configure, tune, and enforce pytest/coverage thresholds — single source of truth, per-module floors, merge-preview reconciliation, integration backstops for omitted modules, optional-dep unlocks, and lcov/geninfo CI fixes |
| **Outcome** | Success — consolidated knowledge for establishing `fail_under` as canonical, raising real coverage, and keeping CI gates green and honest |
| **Verification** | verified-ci |
| **History** | [changelog](./pytest-coverage-threshold-and-enforcement.history) |

## When to Use

- `--cov-fail-under=<N>` appears in `addopts` AND/OR a CI workflow alongside `fail_under = <M>` in `[tool.coverage.report]` — redundant or inconsistent, consolidate to one source
- Coverage floor is cosmetically low (e.g., 9%) and provides no regression protection, or local and CI thresholds diverge
- You need to configure pytest coverage reporting with multiple output formats (term-missing, html, xml, lcov)
- You want to raise coverage requirements from a lower threshold (e.g., 70% → 80%) or add Protocol/abstractmethod exclusions
- CI fails with "Coverage failure: total of X% is less than fail-under=Y%" and you need a realistic baseline
- Local `pytest --cov-fail-under` passes but CI's job fails ("Required test coverage not reached") — CI measures the merge-preview tree
- The CI coverage report mentions a file that does not exist in your branch's `git ls-tree`
- Aggregate coverage gate masks under-tested critical modules — you need per-file floors
- Some modules are intentionally omitted (live CLI/TTY/process spawning) and you need an integration backstop to catch import-time regressions and prevent silent omit-list growth
- Coverage seems low for mature code and `pytest -v` shows many SKIPPED tests guarded by `pytest.importorskip()`
- `generate_coverage.sh` (lcov/geninfo) fails in CI: wrong paths after `cd $BUILD_DIR`, cmake source dir errors, gcov version mismatch on Ubuntu 24.04 + Clang, or geninfo "unable to create link .gcda"

## Verified Workflow

### Quick Reference

```bash
# --- 1. Single source of truth: find & remove redundant flags ---
grep -rn "cov-fail-under" pyproject.toml .github/workflows/
grep -n "fail_under" pyproject.toml
# Remove --cov-fail-under from addopts and CI; keep [tool.coverage.report].fail_under only.
# Update any consistency-check script that asserted the flag was present.

# --- 2. Measure actual coverage, then set floor 2% below baseline ---
pixi run pytest tests/ -v --tb=no -q 2>&1 | tail -5
# fail_under = floor(actual - 2%)  (e.g. actual 77.42% -> fail_under = 75)

# --- 3. Configure report formats in pyproject.toml ---
# addopts: --cov=<pkg> --cov-report=term-missing --cov-report=html --cov-report=xml

# --- 4. Diagnose CI-vs-local divergence (merge-preview tree) ---
gh pr view <N> --json headRefOid --jq '.headRefOid'   # CI's PR-branch SHA
# Get CI per-file table, diff vs your tree:
git ls-tree -r HEAD <src-dir>/   # any CI file NOT here is a main-only/merge-preview file
# Fix: add that main-only file to [tool.coverage.run].omit (no-op locally, effective post-merge)

# --- 5. Per-module floors ---
# parse_module_coverage() reads Cobertura XML <class> elements -> {file: {branch_rate, line_rate}}
# coverage.toml lists per-file minimums; CI step fails if module missing or below floor.
hephaestus-check-coverage --config coverage.toml

# --- 6. Integration backstop for omitted modules ---
pytest tests/integration/test_orchestration_smoke.py -v   # import + `--help` smoke
pytest tests/integration/test_omit_allowlist.py -v        # freeze omit list

# --- 7. Unlock optional-dep skipped tests ---
grep -n "pytest.importorskip\|pytest.mark.skip" <module>
# Install the optional group in CI:  pip install .[dev,<group>]   then add targeted branch tests

# --- 8. lcov/geninfo CI fixes (canonicalize BUILD_DIR, explicit PROJECT_ROOT, ignore-errors) ---
lcov --capture --directory . --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

### Detailed Steps

#### A. Establish `fail_under` as the single source of truth

pytest-cov has two ways to set a minimum: the CLI flag `--cov-fail-under=N` (in the command or `addopts`) and `fail_under = M` in `[tool.coverage.report]`. **When both are present the CLI flag wins**, so the config value is silently ignored.

| Location | Precedence | Scope |
| -------- | ---------- | ----- |
| `--cov-fail-under` in `addopts` | Highest (local) | All local `pytest` runs |
| `--cov-fail-under` in CI workflow | Highest (CI) | CI runs only |
| `fail_under` in `[tool.coverage.report]` | Fallback | Any run without a CLI override |

Fix: remove `--cov-fail-under` from `addopts` and from CI, leaving `[tool.coverage.report].fail_under` as canonical. pytest-cov reads it automatically. Then:

1. **Update consistency-check scripts** that validated `addopts` contained the flag — change "absent = error" to "absent = OK". This is a hidden dependency that will fail pre-commit otherwise.
2. **Add a local `test-unit` task** mirroring the CI invocation so developers get the same feedback.
3. **Update docs** (CLAUDE.md, CONTRIBUTING.md) that referenced the old floor.

Caveat: if CI uses `--override-ini="addopts="` (clears all addopts), it bypasses the config and **must specify its own** `--cov-fail-under`.

#### B. Configure report formats and exclusions

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=<package>",            # replace with your package
    "--cov-report=term-missing",  # CLI feedback (missing lines)
    "--cov-report=html",          # htmlcov/index.html for analysis
    "--cov-report=xml",           # coverage.xml for Codecov / per-module parse
]

[tool.coverage.run]
branch = true
source = ["<package>"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 75          # single source of truth
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",   # exclude typing.Protocol class bodies
    "@(abc\\.)?abstractmethod",  # exclude abstract methods
]
```

Add `.coverage`, `htmlcov/`, `coverage.xml`, `.pytest_cache/` to `.gitignore`. Validate syntax: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.

#### C. Tune the threshold to the real baseline

Set the floor **below** measured coverage to avoid false failures. If actual is 72.89%, set `fail_under = 72` (not 73 — that's an off-by-one CI failure). Document an incremental path (e.g., 72% → 75% → 80%) rather than jumping straight to an aspirational target. If you edited `pixi.toml`, regenerate the lock: `pixi install` (an out-of-sync lock fails `pixi install --locked` with "lock-file not up-to-date").

#### D. Reconcile CI-vs-local divergence (merge-preview tree)

On `pull_request`, GitHub checks out an ephemeral merge commit (`git merge --no-commit origin/main <pr-branch>`). The test job sees the **union** of files from both sides. A file that exists on `main` but not your branch is still measured. If it has low coverage it drags the merged-tree % below the gate — even though your local `pytest` (branch tree only) passes.

The counterintuitive fix: **add the main-only file to your branch's `[tool.coverage.run].omit`** even though it isn't in your tree. Locally it's a no-op; after squash-merge the merged tree has both the omit entry and the file, so the omit takes effect and CI passes. omit-list entries are declarations, not file references — they may name files that don't yet exist locally.

```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/__init__.py",
    # Integration-only; pure-function helpers are tested in tests/unit/automation/.
    "<pkg>/automation/loop_runner.py",  # may be no-op locally, effective post-merge
]
```

Checklist when CI fails but local passes: (1) get CI's per-file table; (2) diff against `git ls-tree -r HEAD <src>/`; (3) any file in CI but not local is merge-preview-only; (4) omit it (if integration-only) or land a tested version; (5) push the omit change so CI re-runs the preview.

#### E. Enforce per-module floors

Aggregate gates (e.g., 85%) hide individual under-tested files (e.g., `schema.py` at 56%). Enforce per-file minimums:

1. **`parse_module_coverage(coverage_xml)`** — read Cobertura XML `<class>` elements (each is a file), extract `filename`, `branch-rate`, `line-rate`; return `{filename: {"branch_rate": float, "line_rate": float}}`. Compare with `branch_rate > 0 else line_rate` (files with no branches report `line_rate=100, branch_rate=0` and would otherwise falsely pass).
2. **`coverage.toml`** with per-file minimums. CRITICAL: use the path format the XML emits (relative, e.g. `validation/schema.py`), NOT the full package path — a mismatch silently skips the check. Verify by setting a floor to 99% and confirming exit 1.

   ```toml
   [module_floors]
   "validation/schema.py" = 80
   ```
3. **CI step** after pytest generates `coverage.xml`: read the toml, compare actual rates, print PASS/FAIL per module, exit 1 if any configured module is missing from the report (regression signal) or below floor.

   ```yaml
   - name: Check per-module coverage floors
     run: <tool>-check-coverage --config coverage.toml
   ```

The check **must run after the full test suite** — a unit-only subset can falsely pass per-module floors.

#### F. Integration backstop for intentionally-omitted modules

Modules omitted because they need live CLI/TTY/process spawning still need proof they import and their entry points work, plus a guard against silent omit-list growth:

- `test_orchestration_smoke.py`: parametrize over the omitted modules. (1) import each (catches import-time regressions); (2) for console-script modules run `<script> --help` via `subprocess.run(..., timeout=5)` and assert exit 0 — `--help` only, never full execution (live TTY hangs the subprocess); (3) for script-less modules assert a callable `main()`.
- `test_omit_allowlist.py`: read `[tool.coverage.run].omit` and assert it equals a frozen known-good set. Any addition fails the test, forcing explicit review.
- When unit tests load the repo-level `coverage.toml` with floors, isolate them with an `empty_config` fixture so the real floors don't interfere with test scenarios.

#### G. Raise real coverage via optional-dep unlock + targeted branches

1. Spot `pytest.importorskip("<pkg>")` guards — these silently skip tests when the optional dep is absent, so coverage stays low.
2. Install the optional group in CI: change `pip install .[dev]` → `pip install .[dev,<group>]`. Skipped tests now run.
3. Confirm skips dropped: `pytest ... -v 2>&1 | grep -c SKIPPED` (e.g., 9 → 0).
4. For remaining uncovered branches, write targeted tests (mock `open()` for OSError, pass malformed JSON for JSONDecodeError, exercise `--verbose`/`--json` flags). Use `--cov-report=term-missing` rather than hand-parsing `coverage.xml`. Accept ~5-10% unreachable (ImportError guards, platform-specific). Result on `schema.py`: 56% → 94.81%.

#### H. Fix lcov/geninfo coverage scripts in CI (4 sequential bugs)

Each bug masks the next, so fix all together. Environment: Ubuntu 24.04, lcov 2.0, Clang 18.

1. **Relative `BUILD_DIR`** breaks every derived path after `cd "$BUILD_DIR"`. Canonicalize to absolute at startup:

   ```bash
   _raw_build="${BUILD_DIR:-$PROJECT_ROOT/build/coverage}"
   if [[ "$_raw_build" = /* ]]; then BUILD_DIR="$_raw_build"; else BUILD_DIR="$PROJECT_ROOT/$_raw_build"; fi
   unset _raw_build
   COVERAGE_DIR="$BUILD_DIR/reports/coverage"; COVERAGE_INFO="$COVERAGE_DIR/coverage.info"
   ```
2. **Wrong cmake source dir**: after `cd "$BUILD_DIR"`, `..` points to BUILD_DIR's parent, not the repo. Pass `"$PROJECT_ROOT"` explicitly (`PROJECT_ROOT="$(git rev-parse --show-toplevel)"`).
3. **gcov version mismatch**: Clang's `--coverage` emits format `4.8*`; Ubuntu 24.04 system gcov reports `B33*`; lcov 2.0 treats it as fatal. Add `version` to `--ignore-errors`.
4. **gcda symlink collision**: when multiple test targets compile the same source basename, geninfo fails to create the duplicate `.gcda` symlink. Add `gcov` to `--ignore-errors`.

Final working capture:

```bash
lcov --capture --directory . --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Removing the flag only | Removed `--cov-fail-under` from `addopts` without raising `fail_under` or updating checks | A pre-commit consistency-check script expected the flag in `addopts` | Always update consistency-check scripts that validate `addopts` contents |
| Setting a floor without measuring | Would have set `fail_under=50` per an issue suggestion | Left a 27% gap below actual 77.42% — no real protection | Measure actual coverage first, then set the floor ~2% below baseline |
| Off-by-one threshold | Set `fail_under=73` when actual was 72.89% | CI failed immediately by 0.11% | Set the floor strictly below measured coverage, not equal to it |
| "Local is 80.84%, CI must be wrong" | Re-ran pytest locally repeatedly, blamed CI flakiness | CI measures the merge-preview tree; both numbers are correct for their own tree | Coverage = f(test set, source tree); different trees give different numbers |
| "File isn't on my branch, omitting is pointless" | Skipped omitting a main-only file because `ls` showed it missing | omit is forward-compatible: no-op locally, effective after squash-merge | omit entries are declarations, not file references; they may name not-yet-local files |
| Rebase, run pytest, then decide on omit | Rebased onto main, saw same local number, concluded the theory was wrong | Post-rebase local pytest still tests the branch tree, not the merge preview | Even post-rebase the divergence persists for files newly added to main |
| Lower the gate locally | Added `--cov-fail-under=78` hoping to mask the gap | CI uses pyproject's `fail_under=80`, not the local override | Don't hide the divergence — understand and fix the omit policy |
| Reusing aggregate parser for per-module | Reused a function returning a single `{line, branch}` dict | It was repo-wide; can't produce per-file breakdown | Per-file logic needs a dict-of-dicts; check return type before reuse |
| Per-module check as a unit test | Wrote a test reading coverage.xml to validate floors | Ran on partial/unit-only suites → false pass | The floor check must run after the full suite, as a CI step |
| line_rate for all files | Compared only `line_rate` | Files with no branches show `line_rate=100, branch_rate=0` → false pass | Use `branch_rate > 0 else line_rate`; branch coverage is stricter |
| Full package paths in coverage.toml | Used `pkg/validation/schema.py` | Cobertura XML uses relative `validation/schema.py`; mismatch silently skipped the check | Match config paths to the exact XML format; verify by setting floor=99% |
| Repo config leaking into coverage unit tests | Tests loaded the repo `coverage.toml` with real floors | Interference between real thresholds and test scenarios | Isolate with an `empty_config` fixture; never let repo config leak in |
| Full script execution in smoke tests | `subprocess.run(["python","-m","pkg.script"])` end-to-end | Live CLI/TTY hung the subprocess → timeouts | Use `--help` only; importability is enough for live modules |
| No omit-list guard | Relied on manual coverage-report review | A module was added to the omit list silently; report still looked fine | Add a frozen-set guard test; allowlist growth must require explicit review |
| Tests without installing the optional dep | Wrote tests assuming `jsonschema` was importable | `pytest.importorskip` still skipped them; coverage unchanged | Install the optional dep in CI first; guards block unguarded runs |
| Assuming all uncovered code is reachable | Tried to hit every uncovered line | Some branches are genuinely unreachable (ImportError guards, conditional jumps) | Distinguish "unreachable" from "unexecuted"; don't chase impossible paths |
| Relative BUILD_DIR in lcov script | Used `BUILD_DIR=build/x86.coverage.debug` directly | After `cd`, all derived coverage paths were wrong | Canonicalize BUILD_DIR to absolute at script startup |
| `cmake ... ..` after cd | Used `..` as the cmake source dir inside BUILD_DIR | `..` resolved to BUILD_DIR's parent, not PROJECT_ROOT | Pass `"$PROJECT_ROOT"` explicitly |
| `--ignore-errors negative,mismatch` only | Added `mismatch` to suppress the gcov format error | `B33*` vs `4.8*` still fatal with lcov 2.0 | Add `version` to the ignore list |
| `--ignore-errors negative,mismatch,version` | Fixed version error, script ran further | Shared source basenames across targets caused gcda symlink collisions | Add `gcov` to the ignore list as well |

## Results & Parameters

### Threshold consolidation outcomes

| Scenario | Before | After |
| -------- | ------ | ----- |
| Single source (raise floor) | `fail_under=9` + `--cov-fail-under=9` in addopts | `fail_under=75` (single source); actual 77.42% (2.42% buffer) |
| Remove redundant CI flag | `--cov-fail-under=72` in CI vs `fail_under=73` in toml | CI inherits `fail_under=73` from `[tool.coverage.report]` |
| Tune to baseline | `fail_under=80` (CI fails at 72.89%) | `fail_under=72` (0.89% margin), path 72→75→80 |
| Raise to standard | 70% | 80% with Protocol/abstractmethod exclusions |

### Report formats

| Format | Purpose | Location |
| ------ | ------- | -------- |
| term-missing | CLI feedback with missing line numbers | stdout |
| html | Detailed local analysis | `htmlcov/index.html` |
| xml | Codecov + per-module Cobertura parsing | `coverage.xml` |
| lcov `.info` | C/C++ coverage via lcov/geninfo | `$COVERAGE_INFO` |

### Per-module floor config & expected output

```toml
# coverage.toml — relative paths matching Cobertura XML
[module_floors]
"validation/schema.py" = 80
```

```text
✓ validation/schema.py: 94.81% (minimum 80%)   # PASS, exit 0
✗ cli/main.py: 82.1% (minimum 85%) — BELOW FLOOR
✗ validation/schema.py: Missing from coverage report   # FAIL, exit 1
```

Cobertura element: `<class filename="validation/schema.py" branch-rate="0.56" line-rate="0.72">` (rates are 0.0-1.0; ×100 for percent).

### Integration backstop parameters

- Console-script smoke: `<script> --help`, `subprocess.run(..., timeout=5)`, assert exit 0.
- Parametrize import test over every omitted module.
- Freeze the omit set in `test_omit_allowlist.py`; additions must update the frozen set (review-gated).

### Optional-dep unlock results

- `pip install .[dev,<group>]` unlocked `pytest.importorskip` tests (SKIPPED 9 → 0).
- `schema.py`: 56% → 94.81% after dep unlock + 5 targeted branch tests.
- Accept ~5-10% unreachable (ImportError guards, platform-specific).

### lcov final invocation & environment

```bash
lcov --capture --directory . --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

| Component | Version |
| --------- | ------- |
| OS | Ubuntu 24.04 |
| lcov | 2.0-4ubuntu2 |
| Clang | 18.1.3 |
| gcov format (Clang) | 4.8* |
| gcov format (system) | B33* |

Diagnostic order (each bug masks the next): (1) BUILD_DIR absolute vs relative; (2) cmake source `"$PROJECT_ROOT"` not `..`; (3) gcov version mismatch in lcov stderr; (4) geninfo symlink collision in lcov stderr.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | Issue #1511, PR #1554 | Raised floor 9% → 75%, added `test-unit` task (single source of truth) |
| ProjectScylla | Issue #754, PR #868 | Removed CI `--cov-fail-under`, aligned to pyproject `fail_under` |
| ProjectScylla | Issue #671, PR #689 | Configured 80% threshold + report formats; tuned to 72% baseline |
| ProjectHephaestus | Issue #623, PR #643 | Per-module floors + parse_module_coverage(); 16 integration smoke tests; omit-list guard; verified-ci auto-merged |
| ProjectHephaestus | Issue #623 | Optional-dep unlock `[dev,schema]` + targeted tests; schema.py 56% → 94.81% |
| ProjectHephaestus | PR #603, PR #606 (2026-05-27) | Merge-preview coverage gate diagnosis; omit-list entry for main-only `loop_runner.py` unblocked CI |
| ProjectKeystone | PR #340 (2026-04-24) | Fixed all 4 sequential lcov/geninfo CI bugs; coverage script ran to completion |
