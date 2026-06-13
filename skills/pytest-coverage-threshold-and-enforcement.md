---
name: pytest-coverage-threshold-and-enforcement
description: "Use when: (1) establishing [tool.coverage.report].fail_under as the single source of truth by removing redundant --cov-fail-under from CI and pyproject.toml addopts; (2) configuring multiple coverage report formats (xml, html, lcov) for CI and local use; (3) CI coverage % is lower than local because GitHub computes coverage against the merge-preview tree (PR HEAD merged with main HEAD) — adding entries to coverage.run.omit for files not on the branch IS the correct fix; (4) aggregate coverage gates hide under-tested critical modules — enforce per-file floors via parse_module_coverage() + coverage.toml + CI step; (5) some modules are intentionally omitted from measurement (live CLI/TTY) and need an integration backstop to catch import-time regressions; (6) pytest.importorskip() guards hide easy coverage wins — install optional deps and write targeted branch tests; (7) tuning coverage thresholds to match actual baselines and avoid false CI failures; (8) generate_coverage.sh fails in CI with wrong paths, cmake source dir errors, lcov gcov version mismatch on Ubuntu 24.04, or geninfo 'unable to create link .gcda'; (9) coverage is raised by adding targeted tests for uncovered branches plus unlocking skipped optional-dependency test groups; (10) planning a coverage threshold consolidation — verify actual coverage %, confirm consistency-checker accepts addopts absence, check whether CI uses --override-ini=addopts= before deciding where the real gate lives; (11) setting per-module branch-rate floor values in coverage.toml — choose margin 3-4pp below actual to avoid brittle thresholds that fail CI on unrelated PRs."
category: testing
date: 2026-06-13
version: "1.2.0"
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
| **Date** | 2026-06-13 |
| **Objective** | Configure, tune, and enforce pytest/coverage thresholds — single source of truth, per-module floors, merge-preview reconciliation, integration backstops for omitted modules, optional-dep unlocks, and lcov/geninfo CI fixes; planning pattern for threshold consolidation |
| **Outcome** | Success — consolidated knowledge for establishing `fail_under` as canonical, raising real coverage, and keeping CI gates green and honest; v1.1.0 adds planning-phase pre-conditions and the --override-ini=addopts= CI pattern; v1.2.0 adds per-module floor margin rule (3-4pp below actual) |
| **Verification** | verified-ci (existing); unverified (v1.1.0 planning additions from ProjectHephaestus issue #1198); verified-ci (v1.2.0 floor margin rule from ProjectHephaestus issue #1197, PR #1288) |
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
- **Planning a threshold consolidation**: project has duplicate `--cov-fail-under` in addopts AND `[tool.coverage.report].fail_under` and you want to eliminate the duplicate — verify actual coverage % before touching either value
- **Determining the real CI gate**: CI uses `--override-ini="addopts="` (clears ALL addopts including `--cov=` and `--cov-report=`) — addopts removal has zero effect on CI; the explicit `--cov-fail-under` flag in the CI workflow is the actual gate
- **Verifying addopts removal is safe**: check that the project's consistency-checker (`check_addopts_cov_fail_under()`) accepts addopts absence before removing the flag
- **Setting per-module floor values in coverage.toml**: use `floor = floor(actual_branch_rate - 3)` to `floor(actual_branch_rate - 4)` — never within 1-2pp of the measured value; a too-tight margin causes CI failures for unrelated PRs that add any uncovered branch

## Verified Workflow

> **Note:** Steps I–II below are planning pre-conditions added in v1.1.0 (ProjectHephaestus issue #1198, unverified). Steps A–H are verified-ci.

### Quick Reference

```bash
# --- 0. Pre-planning: measure actual coverage FIRST ---
pixi run pytest tests/unit --cov=hephaestus --cov-report=term-missing 2>&1 | tail -5
# Record the TOTAL % line before touching any threshold value.

# --- 0b. Identify all threshold locations ---
grep -n "cov-fail-under\|fail_under" pyproject.toml .github/workflows/*.yml

# --- 0c. Determine where CI's real gate lives ---
grep -n "override-ini\|addopts" .github/workflows/*.yml
# If --override-ini="addopts=" is present, CI clears ALL addopts — the real gate
# is the explicit --cov-fail-under flag on the CI pytest line, NOT addopts.

# --- 0d. Verify consistency-checker accepts addopts absence ---
grep -n "check_addopts_cov_fail_under\|cov-fail-under" tests/unit/test_doc_config.py
# Look for an assertion that returns [] when flag is absent — safe to remove.

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

#### I. Planning pre-conditions before changing any threshold (v1.1.0, unverified)

> **Warning:** This section documents a planning session for ProjectHephaestus issue #1198. It has not been validated end-to-end in CI. Treat as a hypothesis until CI confirms.

Before touching `fail_under` or `--cov-fail-under` anywhere:

1. **Measure actual coverage first** — run `pixi run pytest tests/unit --cov=<pkg> --cov-report=term-missing 2>&1 | tail -5` and record the TOTAL % line. Setting any new floor without this number risks flipping CI from passing to failing.

2. **Map all threshold locations** — at minimum: `pyproject.toml addopts`, `[tool.coverage.report] fail_under`, and every CI workflow file. Two locations can drift silently.

3. **Determine where CI's real gate lives** — if CI uses `--override-ini="addopts="`, it clears ALL addopts (including `--cov=<pkg>` and `--cov-report=term-missing`), not just `--cov-fail-under`. In that case:
   - Removing `--cov-fail-under` from addopts has **zero effect on CI**
   - The real CI gate is the explicit `--cov-fail-under=N` flag on the CI pytest invocation line
   - The critical change is updating that CI flag, NOT the addopts line

4. **Verify the consistency-checker accepts addopts absence** — projects may have a `check_addopts_cov_fail_under()` function (often in `test_doc_config.py`) that validates addopts contents. Check whether it requires the flag to be present or merely validates its value when present. In ProjectHephaestus `test_doc_config.py:176`, the assertion checks `check_addopts_cov_fail_under()` returns `[]` when the flag is absent — confirming removal is safe.

5. **Decision table for new floor value**:
   - Actual coverage ≥ target (e.g., ≥ 90%): set `fail_under = target` in `[tool.coverage.report]` and update CI flag to match
   - 80% ≤ actual < 90%: set `fail_under = actual` (rounded down), plan incremental raises
   - Actual < 80% (below existing floor): **do not remove the addopts flag yet**; investigate why coverage dropped first

6. **Check CLAUDE.md** — if a `check_claude_md_threshold()` validator exists, it may require a threshold mention in CLAUDE.md; grep the file before concluding no doc change is needed.

**Key insight for ProjectHephaestus**: The CI `--override-ini="addopts="` in `_required.yml` clears ALL addopts. CI coverage collection is driven entirely by explicit flags on the pytest line in `_required.yml`. Therefore:
- Removing `--cov-fail-under=80` from addopts at `pyproject.toml:201`: no-op for CI
- The real gate change: update `--cov-fail-under=80` at `.github/workflows/_required.yml:585`
- The `fail_under` field in `[tool.coverage.report]` becomes the local gate (runs without `--override-ini`)

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
| Planning without measuring first | Planning to raise fail_under from 80 to 90 before running tests | If actual coverage < new floor, the threshold change flips CI from passing to failing | Always run `pytest --cov` and record total % BEFORE planning any threshold change |
| Assuming addopts removal affects CI | Removing `--cov-fail-under` from addopts assuming CI would notice | CI uses `--override-ini="addopts="` which clears ALL addopts; addopts removal has zero CI effect | Check whether CI uses `--override-ini="addopts="` before concluding addopts removal matters to CI |
| Skipping CLAUDE.md threshold check | Assuming no doc update needed during planning | `check_claude_md_threshold()` may error on missing coverage mention; grep CLAUDE.md before concluding | Trace `check_claude_md_threshold()` end-to-end; if it errors on absence, add threshold mention |
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
| Per-module floor set within 0.75pp of actual | Set `automation/models.py` floor to 68% when measured branch-rate was 68.75% — only 0.75pp margin | PR reviewer rejected immediately: any new uncovered branch in models.py would fail CI for unrelated PRs | Rule: `floor = floor(actual_branch_rate - 3)` to `floor(actual_branch_rate - 4)`; never set a per-module floor within 1-2pp of the measured value |
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

### Per-module floor margin rule (v1.2.0)

**Rule**: `floor = floor(actual_branch_rate - 3)` to `floor(actual_branch_rate - 4)` (3-4 percentage points below measured, rounded down to nearest whole number).

- Never set a floor within 1-2pp of the measured branch-rate — any new uncovered branch will fail CI for unrelated PRs.
- CI enforcer uses `branch_rate if branch_rate > 0 else line_rate` (files with no branches report `branch_rate=0` and fall back to `line_rate`).
- Cobertura XML `<class filename="...">` path format has **no** `hephaestus/` prefix (e.g., `automation/models.py`, NOT `hephaestus/automation/models.py`).

**ProjectHephaestus issue #1197 examples (verified-ci)**:

| Module | Measured branch-rate | Floor set | Margin |
| ------ | -------------------- | --------- | ------ |
| `automation/arming_state.py` | ~100% | 98% | ~2pp |
| `automation/dependency_resolver.py` | ~77% | 74% | ~3pp |
| `automation/models.py` | 68.75% | 65% | 3.75pp |

Note: `automation/models.py` was initially set to 68% (0.75pp margin) — rejected by reviewer; lowered to 65%.

**Apparent inconsistency**: `validation/schema.py` floor is 80% in `coverage.toml` but the module hits 94%+ in CI because CI installs `[dev,schema]` extras (unlocking jsonschema-guarded tests). A local XML without those extras shows ~52%. The floor must be calibrated against the CI measurement, not the local no-extras run.

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
| ProjectHephaestus | Issue #1198 planning (2026-06-13) | **Unverified** — planning session for coverage threshold consolidation (raise enforced floor from 80% to 90%); identified `--override-ini="addopts="` makes addopts removal a CI no-op; confirmed `check_addopts_cov_fail_under()` accepts addopts absence (test_doc_config.py:176); real CI gate is `_required.yml:585`; implementation not run, actual coverage % not measured |
| ProjectHephaestus | Issue #1197, PR #1288 (2026-06-13) | **verified-ci** — per-module floor margin rule: set 3-4pp below actual; `automation/models.py` floor initially 68% (0.75pp margin, reviewer rejected); lowered to 65% (3.75pp margin, merged); three new floors added: `automation/arming_state.py@98`, `automation/dependency_resolver.py@74`, `automation/models.py@65`; confirmed Cobertura XML paths have no `hephaestus/` prefix |
