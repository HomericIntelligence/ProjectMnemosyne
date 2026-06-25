---
name: tdd-workflow-and-test-coverage-expansion
description: "Use when: (1) creating tests before implementation or during a TDD phase — generate test files, coordinate red-green-refactor loops, close CLI command-handler test gaps; (2) a Python script in scripts/ has zero test coverage and needs tests added — audit existing tests before writing new ones to avoid duplication; (3) a unit test exposes a latent parsing bug where single-line vs multi-line input shapes behave differently — test-driven bug discovery; (4) a hephaestus/ module has no tests or low coverage and uses subprocess.run or shutil.which — add mock-based unit tests to reach >85% coverage without real command execution; (5) tests fail after a config refactor — fixtures and mocks need updating to match the new config surface; (6) enforcing import layer boundaries using AST-level CI tests to prevent circular import regressions — catch both direct and lazy/function-local imports that violate architecture; (7) annotating hundreds of unannotated test functions in tests/unit/ to satisfy mypy disallow_untyped_defs; (8) running a coverage swarm with one PR per source file or test shard; (9) new tests must be documented and added to CI workflows that enumerate files manually; (10) writing tests that expose latent bugs in text-processing or subprocess-output parsing functions; (11) adding tests for extracted SRP collaborator methods that drive subprocess sessions — mock at consumer namespace, assert cwd via kwargs, match exact return-value shape."
category: testing
date: 2026-06-15
version: "1.2.0"
user-invocable: false
history: tdd-workflow-and-test-coverage-expansion.history
tags:
  - tdd
  - pytest
  - unit-tests
  - coverage
  - mocking
  - subprocess
  - bug-discovery
  - ast
  - import-boundary
  - red-green-refactor
---
# tdd-workflow-and-test-coverage-expansion

## Overview

| Item | Details |
| ------ | --------- |
| Theme | TDD red-green-refactor workflow plus systematic test-coverage expansion: zero-coverage script tests, mock-based package tests, test-driven bug discovery, post-config-refactor repair, and AST import-layer enforcement |
| Language | Python / pytest (TDD cycle also applies to Mojo) |
| Patterns | Write-test-first, class-grouped tests, module-level mocking, tmp_path fixtures, parametrized shape variants, AST walks, coverage swarms |
| Proven Result | scripts/ coverage 29% → 100% over sessions; 99% coverage of a subprocess-heavy module with 65 mocked tests; real parsing bug exposed and fixed; circular-import regression gate; coverage swarm across 7 PRs |
| Verification | verified-ci |
| History | [changelog](./tdd-workflow-and-test-coverage-expansion.history) |

## When to Use

1. Creating tests before implementation during a TDD phase — generate test files, run red-green-refactor, close CLI command-handler gaps (cmd_run/cmd_repair)
2. A Python script in `scripts/` has zero test coverage — audit existing tests first to avoid duplication, then add mock-based tests
3. A unit test should expose a latent parsing bug where single-line vs multi-line input behaves differently (test-driven bug discovery)
4. A `hephaestus/` module (installed package) has no/low coverage and uses `subprocess.run` or `shutil.which` — reach >85% coverage without real command execution
5. Tests fail after a config/structure refactor — fixtures and mocks must be updated to match the new config surface
6. Enforcing import-layer boundaries with AST-level CI tests to prevent circular-import regressions (catch direct AND lazy/function-local imports)
7. Bulk-annotating unannotated test functions to satisfy mypy `disallow_untyped_defs`
8. Running a coverage swarm with one PR per source file or test shard
9. New tests must be documented (What/Executes/Why) and added to CI workflows that enumerate files manually
10. Writing tests that expose latent bugs in text-processing or subprocess-output parsing functions
11. Adding tests for SRP-extracted collaborator methods that drive subprocess sessions (e.g., `run_drive_green_learnings`, `run_drive_green_compact`) — append to the existing `test_*_helpers.py` file, mock at the consumer module namespace, assert `cwd=` via `call_args.kwargs`, and match the exact return-value shape of the underlying session call

**Trigger phrases**: "write the test first", "X% of scripts lack unit tests", "add tests for untested scripts", "coverage swarm", "one PR per file", "tests fail after refactor", "prevent the circular import from coming back", "tests only cover argument parsing, not behavior".

## Verified Workflow

### Quick Reference

```bash
# --- TDD cycle: Red -> Green -> Refactor ---
python3 -m pytest tests/unit/test_component.py -v   # write test, run -> fails (RED)
# implement minimal code, re-run -> passes (GREEN), then refactor

# --- Coverage expansion: audit BEFORE writing ---
grep -rn "def test_" tests/unit/scripts/ --include="*.py" | wc -l
ls scripts/*.py | grep -v __init__ | wc -l
python3 -m pytest tests/unit/scripts/ -v --tb=short      # baseline

# Import pattern (preferred when pyproject pythonpath = [".", "scripts"])
# from my_script import func_a, func_b
# Fallback: sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

python3 -m pytest tests/unit/scripts/test_my_script.py -v   # fast iteration (NOT pixi)
<package-manager> run python -m pytest tests/unit/scripts/ -v   # final validation

# --- Module-specific mock coverage ---
pixi run python -m pytest tests/unit/validation/test_mod.py -v \
  --cov=pkg.mod --cov-report=term-missing --no-cov-on-fail
```

```python
# AST documentation gate for coverage swarms
import ast
from pathlib import Path
for path in map(Path, ["tests/test_target.py"]):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            doc = ast.get_docstring(node) or ""
            assert all(label in doc for label in ("What:", "Executes:", "Why:")), node.name
```

### Detailed Steps

#### Step 1: TDD Red-Green-Refactor (the core loop)

1. **Write the test first** — define expected behavior before any implementation.
2. **Run the test (RED)** — it must fail because the code doesn't exist yet. Don't skip the red phase; a test that never failed proves nothing.
3. **Implement minimal code (GREEN)** — just enough to pass.
4. **Refactor** — clean up while keeping tests green.
5. **Repeat** for the next behavior.

Python and Mojo patterns follow Arrange-Act-Assert:

```python
import pytest

class TestComponent:
    def test_basic(self):
        data = prepare_data()      # Arrange
        result = process(data)     # Act
        assert result == expected  # Assert
```

```mojo
from testing import assert_equal

fn test_add() raises:
    var a = 1
    var b = 2
    var result = add(a, b)
    assert_equal(result, 3)
```

For generating a test from a spec: analyze inputs/outputs/side-effects, enumerate normal + edge + error cases, write assertions with clear messages, then verify all code paths are exercised.

#### Step 2: Audit Before Writing (coverage expansion)

**Always grep before writing a single test** — avoids duplicating existing tests.

```bash
grep -rl "my_script\|MyClass" tests/ --include="*.py"   # all files touching target
grep -c "def test_" tests/unit/scripts/test_my_script.py
grep -n "^class Test" tests/unit/scripts/test_my_script.py
```

Build a coverage matrix before writing:

| Requirement | Covered? | Test function | File |
| ------------- | ---------- | --------------- | ------ |
| Happy path | yes | `test_happy_path` | `test_my_script.py:45` |
| Missing file | no | — | — |
| Empty input | no | — | — |

**Rank by Testability × Impact (for bulk expansion).** Score each untested script and test the highest-ROI targets first:

| Axis | High (3) | Medium (2) | Low (1) |
| ------ | ---------- | ----------- | --------- |
| **Testability** | Pure functions, no subprocess | Some mocking needed | Subprocess-heavy, no helpers |
| **Impact** | Entry point / pre-commit hook | Frequently invoked | Rarely used utility |

Add the two axis scores; highest sums get tested first. **Minimum viable target = half the total scripts** — when a coverage audit covers a large `scripts/` folder, reaching 50% of scripts is the floor to clear before declaring the session done.

**All-covered audit path (write NO new tests).** A "test coverage audit" issue often resolves to *nothing to write* — the audit shows every required case already exists. Do not invent redundant tests to justify the issue. Instead, add a coverage-mapping comment block that links each requirement to the test that already proves it, then close the issue with **zero new tests**:

```python
# ============================================================================
# Test __hash__
# Coverage (issue #NNNN):
#   (1) identical tensors produce equal hashes      -> test_hash_immutable
#   (2) different shape produces different hash     -> test_hash_different_shapes_differ
# ============================================================================
```

The "add any missing cases" wording in an audit issue *implies audit first*; trusting the title and writing blind would duplicate existing tests.

#### Step 3: Set Up Imports

If `pyproject.toml` has `[tool.pytest.ini_options]` with `pythonpath = [".", "scripts"]`, import directly: `from generate_changelog import parse_commit`. Otherwise add `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))` at the top of the test file.

Read each script/module fully first to classify functions: pure (no mocking), subprocess-calling (mock at module level), argparse `main()` (mock `sys.argv`), module-level constants, class-based. Verify assumptions with `python3 -c` one-liners before encoding them as assertions.

#### Step 4: Choose the Mock-Only Pattern by Type

**Pure functions** — no mocking:

```python
from fix_table_underscores import fix_table_underscores

def test_escapes_bare_underscore():
    assert r"column\_name" in fix_table_underscores("column_name & value\n")
```

**Subprocess-heavy** — mock at the module import path, never at stdlib:

```python
from unittest.mock import MagicMock, patch

def test_successful_merge_returns_true():
    mock_result = MagicMock(returncode=0)
    with patch("merge_prs.subprocess.run", return_value=mock_result):  # NOT "subprocess.run"
        assert merge_pr(42) is True
```

Sequential calls use `side_effect=[...]`. For installed packages mock the package path: `@patch("hephaestus.validation.readme_commands.subprocess.run")`. Cover error paths — `TimeoutExpired`, `OSError`, non-zero return codes. On Python 3.14 build the timeout with positional kwargs only: `subprocess.TimeoutExpired(cmd="bash", timeout=5)`. Mock `shutil.which` for availability checks; stack multiple `@patch` decorators when a method needs several deps.

**Filesystem-heavy** — `tmp_path` fixture:

```python
def test_detects_violation(tmp_path: Path) -> None:
    f = tmp_path / "test.py"; f.write_text("Result = DomainResult\n")
    assert len(detect_shadowing(f)) == 1
```

**Class-based** — instantiate in a fixture, test each method. **Module-level constants** — `patch("mod._REPO_ROOT", tmp_path)` (replicate the exact subdir structure the function expects), or use a dynamic `importlib` loader + `patch.object(mod, "GLOBAL", fake)`.

Standard test-file header: `from __future__ import annotations` first; one class per function; docstrings on new methods; `pytest.CaptureFixture[str]` for capsys (not `object`).

#### Step 5: CLI Handler Gap Pattern (cmd_run / cmd_repair)

When an existing file tests the parser but not the handlers: patch at the **definition site** matching the handler's `from ... import` (e.g. `patch("scylla.e2e.runner.run_experiment")`), capture the config via a closure to assert on it, use flags like `--skip-judge-validation` to drop extra mocks, and test the exception-continue path with invalid JSON (`assert result == 0`, must not crash).

**Curses / thread-timing already-running state.** When a `main()` runs a curses UI on a background thread, a mocked `curses.wrapper` returns instantly, so the worker thread finishes and `ui.running` flips back to `False` before your assertion runs. Calling `ui.start()` twice and asserting the second call is a no-op then fails because no thread is actually alive. Do **not** rely on the real timing — manually simulate the already-running state instead:

```python
def test_start_is_idempotent(self) -> None:
    ui = CursesUI()
    ui.running = True                # simulate "already running"
    ui.thread = MagicMock(is_alive=lambda: True)
    ui.start()                       # second start must be a no-op
    # assert no new thread spawned / wrapper not re-invoked
```

#### Step 5a: Agent Subdirectory Scripts

If the repo has `scripts/agents/*.py`, mirror that layout under tests with a **parallel subdirectory**:

```text
tests/unit/scripts/agents/__init__.py            # REQUIRED for pytest discovery
tests/unit/scripts/agents/test_agent_utils.py
tests/unit/scripts/agents/test_validate_agents.py
```

The `__init__.py` is required — without it pytest will not discover tests in the nested `agents/` package and the agent scripts silently stay uncovered.

#### Step 6: Test-Driven Bug Discovery (parsing edge cases)

`str.strip().split("\n")` is subtly wrong for line-oriented text with significant leading whitespace: `stdout.strip()` removes the leading space of the first line. For `git status --porcelain`, a leading space at position 0 is semantically significant (`" M file"` = modified in worktree), and `line[3:]` relies on it.

```python
# BUG
lines = " M \"path/file.py\"\n".strip().split("\n")  # -> ['M "path/file.py"'] leading space gone
# FIX
lines = " M \"path/file.py\"\n".splitlines()         # -> [' M "path/file.py"'] preserved
```

Workflow: (1) read the parsing logic, not the docstring — note field positions and pre-split string ops; (2) write parametrized tests over shape variants (single-line, multi-line, unicode, untracked):

```python
@pytest.mark.parametrize("porcelain_line, expected_path", [
    (' M "path with spaces/file.py"', "path with spaces/file.py"),
    (' M "répertoire/fichier.py"', "répertoire/fichier.py"),
    ('?? "dir with spaces/new file.py"', "dir with spaces/new file.py"),
])
def test_quoted_filename_is_unquoted(self, tmp_path, porcelain_line, expected_path):
    status_result = MagicMock(); status_result.stdout = porcelain_line + "\n"  # single-line
    with patch("<module>.run", side_effect=[status_result, MagicMock(), MagicMock()]) as mock_run, \
         patch("<module>.fetch_issue_info", return_value=mock_issue):
        commit_changes(42, tmp_path)
    staged = mock_run.call_args_list[1][0][0]
    assert expected_path in staged
    assert f'"{expected_path}"' not in staged  # no surrounding quotes
```

(3) assert both positive (unquoted path present) and negative (quoted form absent); (4) on failure, inspect the actual arg list character-by-character; (5) fix by swapping `strip().split("\n")` → `splitlines()`. Existing multi-line tests passed because `.strip()` only ate the trailing newline — always test single-line AND multi-line shapes.

#### Step 7: Fix Tests After a Config/Structure Refactor

Symptoms: tests pass on old commits, fail after pull; `assert 0 == 1` / `assert len([]) == 1`; discovery methods returning empty; multiple unrelated PRs failing identically.

1. **Confirm pre-existing** — run the failing test on `main` (`git switch main && git pull`). Fails on main → introduced by a merged refactor, not your PR.
2. **Find the breaking commit** — `git log --oneline -10`, look for `refactor:`/`feat(architecture):`.
3. **Compare structures** — e.g. old `t0/00-empty/config.yaml` vs new `t0/00-empty.yaml` (centralized vs distributed; `NN-name.yaml` vs `NN-name/config.yaml`).
4. **Trace path resolution** — when code navigates with `.parent` chains, the test must recreate the full realistic structure *inside* `tmp_path`:

```python
def test_root_level_tools_mapped(self, tmp_path: Path) -> None:
    tiers_dir = tmp_path / "tests" / "fixtures" / "tests" / "test-001"
    tiers_dir.mkdir(parents=True)
    shared_dir = tmp_path / "tests" / "claude-code" / "shared" / "subtests" / "t5"
    shared_dir.mkdir(parents=True)
    (shared_dir / "01-test.yaml").write_text(yaml.safe_dump({"tools": {"enabled": "all"}}))
    manager = TierManager(tiers_dir)                       # proper tiers_dir, not tmp_path
    subtests = manager._discover_subtests(TierID.T5, tiers_dir / "t5")
    assert len(subtests) == 1
```

5. Apply to every test in the class; extract a `create_*_structure(tmp_path)` helper for reuse. Cherry-pick the fix across all affected PR branches.

#### Step 8: AST Import-Layer Enforcement (regression gate)

After fixing a circular import, add a CI test that fails if the forbidden edge returns. Four-test pattern:

```python
import ast, pathlib, subprocess, sys
import hephaestus.github

def test_planner_imports_cleanly() -> None:
    r = subprocess.run([sys.executable, "-c", "from hephaestus.automation.planner import main"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_packages_import_in_either_order() -> None:
    for code in ["import hephaestus.github, hephaestus.automation",
                 "import hephaestus.automation, hephaestus.github"]:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

def test_github_package_does_not_import_automation() -> None:
    github_dir = pathlib.Path(hephaestus.github.__file__).parent
    offenders: list[str] = []
    for py in sorted(github_dir.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):  # ast.walk catches function-local/lazy imports too
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("hephaestus.automation"):
                offenders.append(f"{py}:{node.lineno} from {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("hephaestus.automation"):
                        offenders.append(f"{py}:{node.lineno} import {alias.name}")
    assert not offenders, "forbidden import edge reintroduced:\n" + "\n".join(offenders)
```

Key properties: run each import in a **fresh subprocess** (clean `sys.modules`, real cold-boot behavior); test **both import orders** (order-dependent cycles); use `ast.walk` not `tree.body` (catches nested imports); locate the package via `__file__` (portable across install layouts). Adapt to any boundary by swapping the package import and `forbidden_prefix`.

#### Step 9: Coverage Swarm + Documentation Gate (broad expansion)

For coverage work too large for one PR: target the **current** worktree baseline (verify files exist with `rg --files`, ignore stale reports); give each worker a dedicated worktree/branch (`codex/coverage-<slug>`) owning one file/shard; check whether CI workflows manually enumerate test files and add new files to the right shard; require `What:`/`Executes:`/`Why:` docstrings only on **new** tests; move shared `_helper` functions into documented base classes; run the AST audit (Step Quick Ref) before pushing; validate in the worker worktree with `--override-ini="addopts="` and `git diff --check`.

#### Step 10: Run, Fix Pre-commit, Commit

Iterate with `python3 -m pytest <file> -v` (fast), validate the full suite with `<package-manager> run python -m pytest`, then commit. Common pre-commit fixes: F841 unused vars (drop `as mock_fh`), `var-annotated` (annotate `config: dict[str, object] = {}`), capsys type, E501 docstrings ≤100 chars. Pre-commit auto-fixes ruff formatting — re-stage and re-commit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running tests via `pixi run python -m pytest` during dev | Used pixi for iteration | Env activation timed out (>2 min) | Use `python3 -m pytest` for iteration; pixi only for final validation |
| Background pytest task | Launched pytest in background to avoid blocking | Output file empty for minutes | Background tasks don't stream — run pytest synchronously in foreground |
| Importing unused constants for "documentation" | Imported `BLOCKED_PATTERNS`/`SKILL_CATEGORY_OVERRIDE` but never asserted | ruff F401/F841 auto-removed them, breaking the commit | Only import symbols you assert on; ruff runs in pre-commit |
| Editing a file without reading it | Wrote new test classes blind | Edit tool rejects unread files | Always read the target before editing |
| Writing tests before auditing | Drafted test functions before grepping | Would have duplicated 8+ existing tests / one search missed a sibling file | Grep all of `tests/` recursively before writing; "add missing cases" implies audit first |
| Global subprocess mock | `patch("subprocess.run", ...)` | Mock at stdlib level; module had its own import binding | Always patch at module level: `patch("<module>.subprocess.run", ...)` |
| Wrong patch path for imported funcs | Patched `<pkg>.curses_ui.restore_terminal` | Module does `from scylla.utils.terminal import restore_terminal` inline | Patch at the definition site |
| Coverage without `--no-cov-on-fail` | Used default `--cov=hephaestus` for one module | Overall coverage failed at 12%, hiding module result | Use `--cov=<module> --no-cov-on-fail` for module-specific runs |
| Mocking `multiprocessing.Manager` | Mocked Manager for coordinator tests | Mock didn't replicate event/dict semantics | Use a real `with Manager() as mgr:` context |
| Multi-line strings in fixtures | Hand-formatted multi-line markdown | ruff format collapsed them | Let ruff format; single-line equivalent passes |
| Shared checkout for multiple swarm workers | Started before separating branches | Branch collisions, mixed staged changes, salvage stash needed | One worktree per worker before any edits; explicit file ownership |
| Local discovery only | Added pytest files without updating CI's manual list | New tests passed locally but didn't affect CI coverage | Inspect `.github/workflows/*.yml`; add files to the shard |
| Generic docstrings everywhere | Applied What/Executes/Why to pre-existing tests too | Created noisy churn | AST audit requires labels only on new tests; restore existing docstrings |
| Testing one import order | `import github, automation` only | Order-dependent cycles pass when the lower layer loads first | Test both A→B and B→A orderings |
| `importlib.import_module` inside the test process | Re-imported in-process instead of subprocess | Cached partial module in `sys.modules` made re-import succeed silently | Use `subprocess.run([sys.executable, "-c", ...])` for a clean `sys.modules` |
| AST walk at top-level only | `for node in tree.body` | Missed function-local/class-body imports | Use `ast.walk(tree)` to catch imports at any depth |
| Thread-timing test without state setup | Called `ui.start()` twice expecting the second to be a no-op | Mocked `curses.wrapper` returned instantly, so the worker thread finished and `ui.running` flipped back to `False` before the assertion | Manually set `ui.running = True` and `ui.thread` to simulate the already-running state; don't depend on real thread timing |
| Trusting the issue title on a coverage audit | Assumed "add tests" meant tests were missing and started writing | All required cases already existed; new tests would duplicate them | "Add any missing cases" implies audit first — when all-covered, write zero tests and add a `# Coverage (issue #NNNN)` requirement->test comment block, then close the issue |
| Flat agent-script tests without a package dir | Dropped `test_agent_*.py` straight in `tests/unit/scripts/` for `scripts/agents/*.py` | pytest did not discover the nested package; agent scripts stayed uncovered | Mirror `scripts/agents/` with `tests/unit/scripts/agents/` and add the required `__init__.py` for discovery |
| Testing every untested script in arbitrary order | Worked scripts top-to-bottom with no prioritization | Burned time on subprocess-heavy, rarely-used utilities while high-value pure functions stayed uncovered | Rank by Testability × Impact (High=3/Med=2/Low=1) and clear at least half the scripts as the minimum viable target |
| Trusting issue's sketch filename without checking | Issue #1362 named `test_post_merge_processor_helpers.py` as the target | `test_post_merge_helpers.py` already existed and covered the same class — creating the new file would duplicate tests and violate DRY | Always grep for existing test files touching the same class before creating a new file |
| Mutating `_options()` return to set `agent="codex"` | Called `_options().agent = "codex"` before passing to the processor | The assignment modified the ephemeral MagicMock returned by the call, not the object the processor later sees; `is_codex(options.agent)` saw the wrong value | Build a dedicated factory `_make_codex_processor(tmp_path)` with `options = MagicMock(dry_run=False, agent="codex")` wired directly at construction |
| Generator-throw lambda for exception injection | Sketched `get_worktree_path=lambda i, p: (_ for _ in ()).throw(RuntimeError("gone"))` | Obscure, violates POLA, and confuses readers unfamiliar with the generator-throw trick | Replace with a named module-level helper: `def _raise_no_worktree(issue, pr): raise RuntimeError("worktree gone")` |
| Asserting positional arg index for `cwd` | Used `call_args.args[N]` to assert the working directory | `cwd=` is always keyword-passed in `run_drive_green_*`; positional indexing always returns `None` | Assert via `call_args.kwargs["cwd"]` for any keyword-passed argument |
| Mocking `invoke_claude_with_session` with a bare string | Used `return_value="stdout"` | Source does `stdout, _ = invoke_claude_with_session(...)` — unpacking a string raises `ValueError: too many values` | Mock as a 2-tuple: `return_value=("stdout", None)` |
| Mocking `compact_session` with a 2-tuple | Used `return_value=(True, None)` by analogy | `compact_session` returns its value directly; method returns `compact_session(...)` without wrapping | Mock with `return_value=True`; the unwrapped value IS the return value |
| Local `MagicMock` import inside factory function | Existing `_make_processor` imported `MagicMock` inside its body | New helpers at module scope (`_make_codex_processor`, test classes) need `MagicMock` and can't see a function-local import | Promote `from unittest.mock import MagicMock` to module-top-level when any module-scope helper uses it |

## Results & Parameters

### Verified Coverage Outcomes

| Session | Before | After | New Tests | Files |
| --------- | -------- | ------- | ----------- | ------- |
| ProjectScylla #1162 | 10/34 (29%) | 22/34 (65%) | 453 | 13 |
| ProjectScylla #1358 | 22/34 (65%) | 34/34 (100%) | 130 | 12 |
| ProjectScylla #850 | ~73% | 74.93% | 106 | 5 |
| ProjectScylla #1113 | 114 tests | 119 tests | 5 | 1 (extended) |
| ProjectHephaestus #51 (readme_commands.py) | ~0% | 99% | 65 (all mocked) | 1 |
| Eval360-V2 coverage swarm | 60% baseline | 7 focused PRs (#290-#296) | 518+ | per-file, verified locally |

### pyproject.toml pytest configuration

```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
addopts = ["--cov=hephaestus", "--cov-report=term-missing", "--cov-fail-under=80"]
```

Module-specific override: `pixi run python -m pytest tests/unit/.../test_mod.py --cov=pkg.mod --cov-report=term-missing --no-cov-on-fail`.

### Mock templates (subprocess)

```python
@patch("pkg.mod.subprocess.run")
def test_valid(self, mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
    assert Validator().validate_syntax("echo hello").passed is True

@patch("pkg.mod.subprocess.run")
def test_timeout(self, mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="bash", timeout=5)  # py3.14: positional kwargs
    assert "timed out" in (Validator().validate_syntax("echo hang").error_message or "").lower()
```

### Mock templates (SRP collaborator session drivers)

For methods that drive Claude/Codex sessions (e.g., `run_drive_green_learnings`, `run_drive_green_compact`) extracted into an SRP collaborator via `from .X import Y` re-imports:

```python
# 1. Always patch at the CONSUMER module namespace (not definition site)
#    because `from .X import Y` rebinds the name inside the consuming module.
MODULE = "hephaestus.automation.post_merge_processor"

# 2. invoke_claude_with_session returns a 2-tuple — mock must match
#    the `stdout, _ = invoke_claude_with_session(...)` destructuring.
with patch(f"{MODULE}.invoke_claude_with_session", return_value=("stdout", None)):
    result = processor.run_drive_green_learnings(issue=1, pr=2)

# 3. run_codex_session returns an object with .stdout attribute.
with patch(f"{MODULE}.run_codex_session", return_value=MagicMock(stdout="codex-out")):
    result = processor.run_drive_green_learnings(issue=1, pr=2)

# 4. compact_session returns its value directly (no wrapping).
with patch(f"{MODULE}.compact_session", return_value=True):
    result = processor.run_drive_green_compact(issue=1, pr=2)

# 5. cwd= is keyword-passed — assert via call_args.kwargs, not args[N].
mock_invoke.assert_called_once()
assert mock_invoke.call_args.kwargs["cwd"] == expected_worktree_path

# 6. Exception-swallow boundary: side_effect proves the broad except swallows it.
with patch(f"{MODULE}.invoke_claude_with_session", side_effect=RuntimeError("gone")):
    assert processor.run_drive_green_learnings(issue=1, pr=2) is False

# 7. Short-circuit guard: assert downstream call was NOT made.
with patch(f"{MODULE}.compact_session") as mock_compact:
    processor_codex.run_drive_green_compact(issue=1, pr=2)
    mock_compact.assert_not_called()

# 8. Dedicated factory for variant processors (don't mutate _options() return value).
def _make_codex_processor(tmp_path: Path) -> PostMergeProcessor:
    options = MagicMock(dry_run=False, agent="codex")
    return PostMergeProcessor(options=options, get_worktree_path=lambda i, p: tmp_path)

# 9. Named helper over generator-throw lambda for exception injection.
def _raise_no_worktree(issue: int, pr: int) -> Path:
    raise RuntimeError("worktree gone post-merge")
```

### Parametrize for mapping tables

```python
@pytest.mark.parametrize("commit_type,category", [("feat", "Features"), ("fix", "Bug Fixes"), ("perf", "Performance")])
def test_type_to_category_mapping(self, commit_type, category):
    assert category in categorize_commits([f"abc|{commit_type}: msg|Author"])
```

### Reusable subprocess runner (import tests)

```python
def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
```

### Coverage swarm parameters (Eval360-V2)

| Parameter | Value |
| --------- | ----- |
| Worker isolation | One git worktree per branch under `/private/tmp/eval360-<module>` |
| Branch naming | `codex/coverage-<module-slug>` |
| CI quirk | `.github/workflows/tests.yml` manually enumerates test files |
| Documentation gate | New `Test*`/`test_*` carry `What:`/`Executes:`/`Why:`; existing tests keep base docstrings |
| Helper gate | No module-level standalone `_helper` functions in touched files |
| Local validation | Per-branch pytest files passed; PR #291 rebased file passed `39 passed` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1162, PR #1343 — scripts/ 29% → 65% | extend-script-test-coverage |
| ProjectScylla | Issue #1358, PR #1383 — 12 additional scripts | script-unit-test-coverage |
| ProjectScylla | Issue #850, PR #975 — source modules 74.93% | unit-tests-untested-modules |
| ProjectScylla | Issue #1113 — cmd_run/cmd_repair handler gap | close-script-test-gap-cmd-run-repair |
| ProjectScylla | PR #1467, issue #1447 — git-quoted filename parsing bug | `pr_manager.py::commit_changes` (test-driven bug discovery) |
| ProjectScylla | PRs #186/#187 — tier_manager tests after config unification | fix-tests-after-config-refactor |
| ProjectHephaestus | Issue #51, PR #94 — readme_commands.py 99% coverage | testing-package-module-mock-coverage |
| ProjectHephaestus | PR #308 — `hephaestus.github` → `hephaestus.automation` circular import | testing-ast-import-layer-enforcement |
| ProjectHephaestus | Issue #1362, PR #1363 — `PostMergeProcessor.run_drive_green_learnings` + `run_drive_green_compact` (11 tests, verified-ci) | srp-collaborator-session-driver-coverage |
| ProjectMnemosyne | Issue #3309, PR #3927 — migrate_odyssey_skills.py | add-unit-tests-for-existing-script |
| ProjectOdyssey | Issue #4051, PR #4859 — hash coverage audit | test-coverage-audit |
| Eval360-V2 | PRs #290-#296 — coverage swarm (518+ tests) | coverage-swarm |
