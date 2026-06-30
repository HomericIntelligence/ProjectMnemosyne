---
name: pytest-patch-decorator-to-shared-fixture-conversion
description: "Behavior-preserving conversion of many duplicated stacked @patch(...) decorator pairs into a single opt-in pytest fixture (yield from a context-manager generator returning a small dataclass of started mocks), and the two non-obvious pitfalls that break it. Use when: (1) a test module stacks the SAME 2+ @patch(...) decorators on dozens of methods (DRY smell — '30+ duplicated decorators') and you want one shared fixture instead; (2) you are replacing decorator-injected positional mock args with a pytest fixture parameter and hit `fixture '<mockname>' not found` because a leftover @patch decorator and the fixture parameter collide on the same test; (3) a bulk/scripted signature rewrite silently fails to insert a new first parameter into MULTI-LINE def signatures (params on a continuation line, so `self` is not adjacent to the opening paren); (4) you must decide opt-in (parameter-requested) vs autouse for the new fixture when patch targets differ per module or some test classes must run real subprocesses unmocked; (5) a global text-replace of mock variable names also rewrites decorator-injected param NAMES in unrelated single-decorator methods, producing invalid signatures; (6) you need the correct ordering rule when a @patch decorator survives alongside a fixture param — decorator-injected mocks must come BEFORE fixture params after self."
category: testing
date: 2026-06-29
version: "1.0.0"
user-invocable: false
tags:
  - pytest
  - fixtures
  - mock
  - patch
  - decorator
  - dry
  - refactoring
  - ast
  - subprocess
---
# pytest-patch-decorator-to-shared-fixture-conversion

Behavior-preserving conversion of many duplicated stacked `@patch(...)` decorator pairs into one opt-in pytest fixture. The fixture `yield from`s a context-manager generator that starts the patches and returns a small dataclass of started mocks; tests request the fixture by parameter and read `mocks.run` / `mocks.repo_root` instead of decorator-injected positional args. Two pitfalls dominate: (a) decorator-injected mocks are positional and must come BEFORE any fixture param after `self`, and (b) scripted signature rewrites must use an AST pass, not a `(self,` regex, because multi-line signatures put params on a continuation line.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-06-29 |
| Objective | Replace 30+ duplicated stacked `@patch(...)` decorator pairs across two test files with a single opt-in shared pytest fixture, with zero behavior change |
| Outcome | Success — `git_utils` fully converted (0 residual pairs), `worktree_manager` left 6 intentional `get_repo_root`-only carve-outs; full `tests/unit/automation tests/unit/github` = 2586 passed; ruff + mypy clean |
| Verification | verified-local |

## When to Use

- A test module stacks the SAME 2+ `@patch(...)` decorators on many methods (DRY smell, "30+ duplicated decorators") and you want one shared fixture.
- You are replacing decorator-injected mocks with a pytest fixture (`yield from` a context-manager generator returning a small dataclass of started mocks).
- You mixed a leftover `@patch` decorator with a fixture parameter on the same test and hit `fixture '<mockname>' not found`.
- A bulk/scripted signature rewrite silently fails to insert a new first parameter into MULTI-LINE `def` signatures.
- You must decide opt-in fixture vs `autouse` when patch targets differ per module or some test classes must stay unmocked (real subprocesses).

## Verified Workflow

The recipe is behavior-preserving: the passing test count BEFORE and AFTER must match (plus any net-new tests). Decorator→argument order is **bottom-up**: the innermost (lowest) decorator injects the first positional argument after `self`.

### Quick Reference

```python
# package conftest.py — consolidate imports at top of file:
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class GitMocks:
    run: MagicMock
    repo_root: MagicMock


def _patch_run_and_repo_root(module: str) -> Generator[GitMocks, None, None]:
    with (
        patch(f"{module}.run") as mock_run,
        patch(f"{module}.get_repo_root") as mock_repo_root,
    ):
        yield GitMocks(run=mock_run, repo_root=mock_repo_root)


@pytest.fixture
def git_utils_mocks() -> Generator[GitMocks, None, None]:
    yield from _patch_run_and_repo_root("hephaestus.automation.git_utils")


@pytest.fixture
def worktree_manager_mocks() -> Generator[GitMocks, None, None]:
    yield from _patch_run_and_repo_root("hephaestus.automation.worktree_manager")
```

```python
# Test BEFORE — stacked decorators inject positional args (bottom-up)
@patch("hephaestus.automation.git_utils.get_repo_root")
@patch("hephaestus.automation.git_utils.run")
def test_something(self, mock_run, mock_get_root):  # run=innermost=first
    ...

# Test AFTER — request the fixture by parameter, read its dataclass fields
def test_something(self, git_utils_mocks: Any):
    git_utils_mocks.run.return_value = ...
    git_utils_mocks.repo_root.return_value = ...
```

```python
# AST param insertion (multi-line-safe) — NEVER use re.sub(r"\(self,", ...)
import ast

def insert_fixture_param(src: str, fixture: str = "git_utils_mocks") -> str:
    tree = ast.parse(src)
    edits = []  # (offset, text), applied bottom-to-top
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.args.args:
            self_arg = node.args.args[0]
            if self_arg.arg != "self":
                continue
            # insert right after `self`'s end column on its own line
            line = self_arg.lineno - 1
            col = self_arg.end_col_offset
            edits.append((line, col, f", {fixture}: Any"))
    # apply edits bottom-to-top so earlier offsets stay valid
    lines = src.splitlines(keepends=True)
    for line, col, text in sorted(edits, reverse=True):
        lines[line] = lines[line][:col] + text + lines[line][col:]
    return "".join(lines)
```

```bash
# Audit: residual stacked pairs should drop to ~0 for fully converted files
grep -cE '@patch\("[^"]*\.(run|get_repo_root)"\)' tests/unit/automation/test_git_utils.py
```

### Detailed Steps

1. **Baseline.** Run the target test files and RECORD the passing count. This is the invariant the conversion must preserve.
2. **Add the fixture infra** to the PACKAGE `conftest.py`: a small `@dataclass` of the started mocks, a `_patch_run_and_repo_root(module)` context-manager generator, and one opt-in `@pytest.fixture` per module (each binds the helper to that module's patch target). Consolidate imports at the top (`Generator`, `dataclass`, `MagicMock`, `patch`).
3. **Convert ONLY methods that stack BOTH targeted decorators.** Delete the two decorators, add the fixture parameter, and rewrite body references from `mock_run`/`mock_get_root` to `mocks.run`/`mocks.repo_root`. Decorator→arg order is bottom-up — confirm which decorator-injected name maps to which mock before renaming.
4. **Methods with an extra unrelated decorator:** KEEP that decorator and order the params `(self, <decorator-mock>, <fixture>, ...)`. The decorator's mock is injected positionally into the first slot after `self`, so it MUST precede the fixture.
5. **Leave single-symbol methods UNCHANGED.** A method that patches only one of the two symbols (and patches the other via an inner `with patch(...)`) is NOT a target. If a bulk pass touched it, restore its original parameter names.
6. **If scripting the rewrite,** insert the new first param via AST (find the `self` arg node, insert `, <fixture>: Any` right after its `end_col_offset`), applying edits bottom-to-top so offsets stay valid. Then `ruff format` to re-wrap.
7. **Audit** with `grep -cE '@patch\("[^"]*\.(run|get_repo_root)"\)' <file>`: it should drop to ~0 for fully converted files. Document any intentional residual (the single-decorator carve-outs).
8. **Gates:** `ruff format`, `ruff check`, `mypy`, then re-run the suites. The passing count MUST equal the baseline (+N for any net-new tests).

#### Opt-in vs autouse

Choose **opt-in** (parameter-requested) NOT `autouse` when:

- Different modules need different patch targets (`git_utils.run` vs `worktree_manager.run`) — autouse can't parameterize the target per test.
- Some test classes must run REAL subprocesses unmocked (e.g. a `TestRun` class that exercises the actual `run` helper). An autouse fixture would silently mock them and invalidate the test.

Opt-in keeps the conversion surgical: only the methods that previously stacked both decorators request the fixture.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Global text-replace of mock var names | Replaced `mock_run`/`mock_get_root` → `worktree_mocks.run`/`.repo_root` across the WHOLE file | It also rewrote the DECORATOR-injected param NAMES in unrelated single-decorator methods (e.g. `TestBaseBranchDetectionRaisesOnFailure`, which patched only `get_repo_root` via a sole decorator and patched `run` via an inner `with patch(...)`), producing invalid signatures like `def test(self, worktree_mocks.repo_root: Any, ...)` | Only convert methods that stack BOTH targeted decorators; carve out single-decorator / `with patch` methods and restore their original param names |
| `re.sub(r"\(self,", "(self, worktree_mocks: Any,", sig)` to insert the fixture param | Regex-anchored the insertion on the `(self,` text | For MULTI-LINE signatures the params live on a continuation line (`        self, mock_get_root: Any, ...`), so `self` is NOT adjacent to `(` and the regex never matched → 35 methods used `worktree_mocks` in the body without declaring it as a parameter | Don't anchor parameter insertion on `(self,`; use an AST pass to find the `self` arg node and insert `, worktree_mocks: Any` right after its `end_col_offset`, applying edits bottom-to-top so offsets stay valid |
| Fixture param placed FIRST after `self` while a `@patch` decorator survived | On methods like `is_clean_working_tree` / `rebase_worktree_onto`, wrote `(self, worktree_mocks, mock_clean, tmp_path)` with `@patch(...)` still present | `@patch` injects its mock POSITIONALLY into the first arg after `self`, so that slot got the fixture object and `mock_clean` was then resolved as a (nonexistent) fixture → setup failed with `fixture 'mock_clean' not found` | Any surviving `@patch`-decorator mock params MUST come BEFORE fixture params: order is `(self, <decorator-mocks bottom-up>, <fixtures>, ...)` |
| Trusting a plain count parity to scope the work | Compared `grep -c run` (39) vs `grep -c get_repo_root` (45) expecting them equal | The 6-count gap was NOT noise — it correctly flagged the 6 `get_repo_root`-only methods that must be left alone | Count asymmetry between the two patch targets is a SIGNAL: it pinpoints the single-decorator carve-outs, not a miscount to be ignored |

## Results & Parameters

- Files touched: `tests/unit/automation/conftest.py` (the fixtures), `tests/unit/automation/test_git_utils.py`, `tests/unit/automation/test_worktree_manager.py`.
- Fixture shape: a `@dataclass` of started `MagicMock`s + a `_patch_run_and_repo_root(module)` generator (`with (patch(...), patch(...))`) + one opt-in `@pytest.fixture` per module that `yield from`s the helper bound to that module's target.
- Param-ordering rule: `(self, <decorator-injected mocks, bottom-up>, <fixtures>, ...)`. Decorator mocks are positional; fixtures are keyword-resolved by name.
- AST insertion idiom: locate `node.args.args[0]` (the `self` arg), insert `, <fixture>: Any` at its `end_col_offset`, apply edits bottom-to-top, then `ruff format`.
- Audit grep: `grep -cE '@patch\("[^"]*\.(run|get_repo_root)"\)' <file>` → ~0 for fully converted files; residual = intentional single-decorator carve-outs.
- Verify outcome: `git_utils` fully converted (0 residual pairs); `worktree_manager` left 6 intentional `get_repo_root`-only methods; full `tests/unit/automation tests/unit/github` = 2586 passed; ruff + mypy clean. (The same PR also migrated one `timeout=2400` literal to `agent_rebase_timeout()` in `hephaestus/github/tidy.py` — a separate, already-covered pattern, mentioned only in passing.)
- Cross-links: `dry-refactoring-workflow` (general DRY / test-fake dedup workflow), `architecture-defer-env-coercion-lazy-resolver` (if the patch-target module also needs lazy env resolution).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | issue #1417 / branch 1417-auto-impl | conftest opt-in fixtures replaced 30+ stacked `@patch` pairs across `test_git_utils.py` + `test_worktree_manager.py`; 2586 tests pass locally, ruff + mypy clean; CI pending at capture time (verified-local) |
