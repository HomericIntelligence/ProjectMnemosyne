---
name: fleet-sync-package-refactor-planning-risks
description: "Planning-risk checklist for converting ProjectHephaestus hephaestus/github/fleet_sync.py from a flat module into a package while preserving console-script, import facade, shared logger, and monkeypatch compatibility. Use when: (1) planning a module-to-package refactor with installed entry points, (2) reviewing facade wrappers after decomposition, (3) validating tests that patch historical module names."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - projecthephaestus
  - fleet-sync
  - module-to-package
  - package-facade
  - console-script
  - monkeypatch
  - logger-identity
  - planning-risks
  - issue-1407
---

# Fleet Sync Package Refactor Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the unexecuted planning risks for refactoring `hephaestus/github/fleet_sync.py` from one flat module into a `hephaestus.github.fleet_sync` package with focused submodules for config/models, GPG identity, git operations, conflict resolution, and sync orchestration. |
| **Outcome** | Implementation plan produced for ProjectHephaestus issue #1407, but the plan itself was not executed during this learning capture. Treat every compatibility claim as a hypothesis until import, packaging, CLI, and monkeypatch tests prove it. |
| **Verification** | `unverified` - no code was written, no packaging build was run, no installed console script was smoked, and GitHub issue #1407 was not reopened during this capture. |

## When to Use

- Planning or reviewing a Python refactor that replaces a live `module.py` with a same-named package directory.
- The old module is an installed console-script target such as `hephaestus-fleet-sync = "hephaestus.github.fleet_sync:main"`.
- Existing tests or downstream callers patch historical facade names like `process_repo`, `_git`, `_gh`, `subprocess.run`, `_find_default_config`, or `get_resign_exec`.
- The plan assumes `__init__.py` facade wrappers and dependency injection are enough to preserve behavior.
- Reviewers need a checklist for logger identity, package build inclusion, import-cycle checks, CLI smoke tests, and conflict-resolution return contracts.
- Issue-cited function sizes or line references may be stale and should be replaced with AST-measured facts from disk.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

<!-- Validator compatibility marker for legacy ProjectMnemosyne validation: ## Verified Workflow. This unverified skill intentionally uses the rendered heading "## Proposed Workflow". -->

### Quick Reference

```bash
# Run from a fresh ProjectHephaestus checkout before implementing the refactor.

# 1. Re-open the issue and current code instead of trusting stale line references.
gh issue view 1407 --repo HomericIntelligence/ProjectHephaestus --json title,body,comments

python3 - <<'PY'
import ast
from pathlib import Path

path = Path("hephaestus/github/fleet_sync.py")
tree = ast.parse(path.read_text())
targets = {"main", "list_prs", "process_repo", "resolve_conflict_with_agent"}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in targets:
        print(f"{node.name}: {node.lineno}-{node.end_lineno} ({node.end_lineno - node.lineno + 1} lines)")
PY

# 2. Find every compatibility seam that must survive the module-to-package conversion.
rg -n "fleet_sync|hephaestus-fleet-sync|process_repo|_find_default_config|get_resign_exec|_git|_gh|subprocess.run" \
  pyproject.toml hephaestus tests scripts

# 3. Prove installed entry point and package import behavior, not just in-repo imports.
python -m build
python - <<'PY'
from importlib.metadata import entry_points

eps = entry_points(group="console_scripts")
target = next(ep for ep in eps if ep.name == "hephaestus-fleet-sync")
loaded = target.load()
assert callable(loaded)
print(target.value)
PY
hephaestus-fleet-sync --help

# 4. Run the focused compatibility tests and import-cycle checks.
pixi run pytest \
  tests/unit/github/test_fleet_sync.py \
  tests/unit/github/test_fleet_sync_config.py \
  tests/unit/automation/test_provider_neutral_direct_dispatch.py \
  tests/unit/utils/test_no_import_cycles.py \
  tests/integration/test_cli_entry_points.py
```

### Detailed Steps

1. **Verify the live issue and live file first.** The plan relied on issue #1407 and on AST-measured disk line counts for `main`, `list_prs`, `process_repo`, and `resolve_conflict_with_agent`. Re-run those measurements before implementation. Treat issue line references as hints, not anchors.
2. **Classify the refactor as an API and packaging change, not a pure move.** Replacing `fleet_sync.py` with `fleet_sync/` can affect Python import resolution, package build contents, sdist/wheel inclusion, installed console script metadata, and downstream monkeypatch seams. Add explicit verification for each surface.
3. **Design the facade before moving implementation.** `hephaestus/github/fleet_sync/__init__.py` must preserve the public and test-facing names that existed on the flat module. For patch-sensitive functions, prefer thin wrappers that look up facade-level dependencies at call time, then delegate into submodules through injected callables.
4. **Prove wrapper injection, do not assume it.** Existing tests patch facade names such as `process_repo`, `_git`, `_gh`, `subprocess.run`, and `_find_default_config`. A passing facade-level unit test can still hide direct submodule drift. Add focused tests that patch the facade and then exercise the actual CLI path and the direct delegated path.
5. **Keep logger identity stable.** If tests capture `fleet_sync_module.logger`, submodules must not fragment loggers by doing unrelated `logging.getLogger(__name__)` calls for behavior under test. Either import the shared logger from the facade carefully, pass it as a dependency, or use one canonical logger name and prove identity with a unit test.
6. **Keep `tidy.py` out of scope unless #1407 says otherwise.** The plan intentionally did not refactor `hephaestus/github/tidy.py`. Reviewers should confirm that this is consistent with the issue acceptance criteria rather than silently expanding the task.
7. **Treat conflict resolution as a contract, not a boolean.** `resolve_conflict_with_agent` has sentinel behavior around dry-run, missing backend, agent failure, and branch-push verification. Refactoring it across modules can blur `True`, `False`, and cleanup-needed states. Preserve and test every branch explicitly.
8. **Use rollback criteria that are operational, not aesthetic.** A rollback to `_fleet_sync.py` plus a thin flat shim was only theoretical in the plan. Trigger rollback only when import behavior, installed console smoke, or monkeypatch compatibility cannot be made green in the package form.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat module-to-package conversion as a filesystem-only refactor | Plan assumed moving `fleet_sync.py` into `fleet_sync/` plus a facade would preserve behavior | Python import resolution, build inclusion, installed entry point metadata, and downstream patch paths can all change even when local imports pass | Verify importlib entry point loading, installed `--help`, package build artifacts, and direct package import after the conversion |
| Trust facade wrappers without exercising real paths | Existing tests patch `process_repo`, `_git`, `_gh`, `subprocess.run`, and `_find_default_config`, and the plan assumed wrapper injection would keep them working | A facade test can pass while submodule imports bypass the facade-patched dependency in real CLI execution | Test both facade-patched calls and the installed CLI path; submodules must receive dependencies from the facade or a proven injection seam |
| Let submodules create independent loggers | Decomposition naturally suggests each submodule calls `logging.getLogger(__name__)` | Tests and downstream observers may capture `fleet_sync_module.logger`; fragmented logger names can make assertions or operational filtering drift | Preserve one shared logger identity or canonical logger name, and assert it after the package split |
| Scope-creep into sibling `tidy.py` | A large `github/` refactor tempts reviewers to fold in `hephaestus/github/tidy.py` | The issue #1407 plan intentionally excluded `tidy.py`; expanding scope makes review and rollback harder | Confirm issue acceptance criteria before touching sibling modules; leave `tidy.py` out unless the issue explicitly requires it |
| Rely on stale issue line references | Plan cited issue context but used AST-measured disk counts for key functions | Issue line numbers drift after unrelated edits, so line-based extraction instructions can target the wrong code | Measure functions from the current tree with AST and anchor edits to symbols, not old offsets |
| Present rollback as proven | Plan mentioned `_fleet_sync` plus a thin flat shim as a rollback path | The rollback path was not executed, packaged, or tested; it may have its own import and entry point problems | Treat rollback as a hypothesis and define concrete triggers: import failure, console smoke failure, or unfixable monkeypatch compatibility |
| Review unit monkeypatches only | Focused only on tests that patch historical names | Direct submodule imports and installed console script behavior can drift while those tests still pass | Pair monkeypatch tests with package build, `importlib.metadata` entry point load, CLI smoke, and import-cycle checks |

## Results & Parameters

**Verification level:** `unverified`. This skill records planning risks from an implementation plan for ProjectHephaestus issue #1407. The plan was not executed during learning capture.

**Proposed target topology from the plan:**

```text
hephaestus/github/fleet_sync/
  __init__.py          # compatibility facade; preserves main and historical patch names
  models.py            # dataclasses / simple value models
  config.py            # config discovery and parsing
  identity.py          # GPG signing identity and resign command helpers
  git_ops.py           # git and gh subprocess helpers
  conflicts.py         # conflict-resolution agent flow
  orchestration.py     # list/process/sync orchestration
```

**Compatibility surfaces to prove before merge:**

| Surface | Risk | Required proof |
|---------|------|----------------|
| Console script | `pyproject.toml` entry point may still point at `hephaestus.github.fleet_sync:main`, but installed metadata can drift after package conversion | Build/install artifact, load the entry point through `importlib.metadata`, run `hephaestus-fleet-sync --help` |
| Facade imports | `import hephaestus.github.fleet_sync as fleet_sync_module` must expose historical names | Assert facade exports and direct `main` import after conversion |
| Monkeypatch seams | Tests patch facade names like `_git`, `_gh`, `subprocess.run`, `_find_default_config`, and `process_repo` | Patch the facade, exercise delegated code, and prove submodules do not bypass those patched dependencies |
| Logger identity | `fleet_sync_module.logger` is captured by tests and may be operationally filtered | Assert the facade logger and the logger used by delegated paths are the same object or same canonical name |
| Packaging | A package directory can be omitted or partially included in sdist/wheel configuration | Inspect build artifacts or install from wheel before the CLI smoke |
| Conflict resolution | Dry-run, missing backend, agent failure, push verification, and cleanup can collapse into ambiguous booleans | Preserve one explicit test per sentinel branch and assert cleanup behavior |

**External sources, files, and APIs relied on without end-to-end verification during this learning capture:**

- GitHub issue #1407 and any stated acceptance criteria were not reopened or verified during capture.
- The cited console script target `hephaestus-fleet-sync = "hephaestus.github.fleet_sync:main"` came from the plan and should be rechecked in current `pyproject.toml`.
- Specific test line references and monkeypatch behaviors in `tests/unit/github/test_fleet_sync.py`, `tests/unit/github/test_fleet_sync_config.py`, `tests/unit/automation/test_provider_neutral_direct_dispatch.py`, `tests/unit/utils/test_no_import_cycles.py`, and `tests/integration/test_cli_entry_points.py` came from the plan and should be treated as assumptions until the repo is inspected.
- Python packaging behavior for replacing a module with a package must be validated through an installed entry point help command, `importlib.metadata` entry point loading, package build/sdist coverage, and import-cycle checks.
- `gh` CLI behavior, GitHub mergeability status fields, and subprocess-based git/gh helpers were part of planned behavior but were not exercised.

**Reviewer focus checklist:**

- Verify the current issue #1407 acceptance criteria before accepting the refactor scope.
- Require package build/install evidence, not just in-tree `pytest`.
- Inspect every facade wrapper that passes `_git`, `_gh`, `subprocess.run`, `_find_default_config`, or `get_resign_exec` into a submodule.
- Check that direct submodule imports cannot drift from CLI behavior hidden behind facade-patched tests.
- Confirm function-size decomposition with AST measurements from the current tree.
- Keep rollback criteria explicit and narrow: import failure, installed console smoke failure, or unfixable monkeypatch compatibility.
