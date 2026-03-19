---
name: cluster-extraction-to-modules
description: Decompose a large Python class file (>1000 lines) by extracting cohesive
  method clusters into dedicated sub-modules with thin delegation wrappers. Use when
  a class file exceeds 1000 lines and contains 3+ independent method clusters.
category: architecture
date: 2026-03-05
version: 1.0.0
user-invocable: false
tier: 2
---
# Cluster Extraction to Modules: Decomposing Large Class Files

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-03-05 |
| **Objective** | Reduce `implementer.py` from 1,221 to <1,000 lines by extracting method clusters into sub-modules |
| **Outcome** | ✅ Success — 1,221 → 837 lines, 3 new modules, 37 new tests, 336 automation tests pass |
| **Root Cause** | `IssueImplementer` class mixed 4 distinct concerns: retrospective lifecycle, follow-up issue creation, git/PR operations, and core orchestration |
| **Solution** | Extract clusters into `retrospective.py`, `follow_up.py`, `pr_manager.py`; keep thin delegation wrappers in parent class |

## Problem Statement

When a class file grows past 1000 lines, it typically contains several independent method clusters:
- Methods that share the same external dependency (e.g., all talk to the GitHub API)
- Methods that share state only via parameters (not `self`)
- Methods that could be unit-tested in isolation if they weren't bound to the class

The challenge: extracting these methods while preserving:
1. The existing public interface (callers use `instance.method()`)
2. Existing tests that patch `module.implementer.run` style paths
3. Type safety across module boundaries

## When to Use This Skill

Use this pattern when:
- A class file exceeds 1,000 lines
- You can identify 3+ clusters where methods share resources within the cluster but not across clusters
- The clusters use different external APIs (one cluster = GitHub API, another = git CLI, another = Claude CLI)
- Existing tests mock at the module level (not method level), making patch paths critical
- You want to reduce file size without changing the class interface at all

## Verified Workflow

### Phase 1: Measure and Map (Read, Don't Write)

```bash
wc -l <target_file>.py  # confirm > 1000
```

Read the file and group methods into clusters:

| Cluster | Methods | Shared resource | Lines |
|---------|---------|-----------------|-------|
| Retrospective | `_run_retrospective`, `_retrospective_needs_rerun` | Claude CLI | ~80 |
| Follow-up | `_run_follow_up_issues`, `_parse_follow_up_items` | Claude CLI + GitHub API | ~150 |
| PR/Git | `_commit_changes`, `_ensure_pr_created`, `_create_pr` | git CLI + GitHub API | ~190 |

**Stop criterion**: Extract until `wc -l` < 1000. Apply YAGNI — stop extracting once the target is met.

### Phase 2: Identify Import Changes Needed

For each cluster, note which imports move from the parent to the new module:

```bash
# Check which symbols each cluster uses
grep -n "gh_issue_create\|gh_issue_comment\|get_follow_up_prompt" implementer.py
```

After extraction, clean up unused imports in the parent file — ruff will catch them.

### Phase 3: Extract Each Cluster (Largest Savings First)

Create the new module **first**, self-contained, with no imports from the parent class:

```python
# scylla/automation/follow_up.py
from .github_api import gh_issue_comment, gh_issue_create
from .git_utils import run
from .prompts import get_follow_up_prompt

def parse_follow_up_items(text: str) -> list[dict[str, Any]]:
    ...

def run_follow_up_issues(
    session_id: str,
    worktree_path: Path,
    issue_number: int,
    state_dir: Path,
    status_tracker: StatusTracker | None = None,
    slot_id: int | None = None,
) -> None:
    ...
```

**Key**: Replace `self.state_dir`, `self.status_tracker` etc. with explicit parameters. This makes the extracted functions independently testable.

### Phase 4: Replace Method Bodies with Delegation Wrappers

In the parent class, keep the method signature but delegate to the extracted function:

```python
# implementer.py — thin wrapper preserves the public interface
def _run_follow_up_issues(
    self,
    session_id: str,
    worktree_path: Path,
    issue_number: int,
    slot_id: int | None = None,
) -> None:
    """Resume Claude session to identify and file follow-up issues."""
    run_follow_up_issues(
        session_id,
        worktree_path,
        issue_number,
        self.state_dir,
        self.status_tracker,
        slot_id,
    )
```

Add the import at the top of the parent file:
```python
from .follow_up import parse_follow_up_items, run_follow_up_issues
```

### Phase 5: Clean Up Parent Imports

After each extraction, check for newly unused imports:

```bash
# Symbols that moved out of implementer.py:
grep -n "gh_issue_create\|gh_issue_comment\|get_follow_up_prompt\|re\." implementer.py
```

Remove them — ruff's `F401` will catch any misses during pre-commit.

### Phase 6: Fix Existing Tests (Critical)

Existing tests that patch at the module level will break because the code moved:

```python
# BEFORE: patched in implementer, where the code lived
patch("scylla.automation.implementer.run")
patch("scylla.automation.implementer.gh_issue_create")

# AFTER: patch in the module where the code now lives
patch("scylla.automation.follow_up.run")
patch("scylla.automation.follow_up.gh_issue_create")
```

**How to find all affected tests**: Run the test suite and look for `AssertionError: Expected 'run' to have been called once. Called 0 times.` — this is the signature of a wrong patch path.

### Phase 7: Write New Unit Tests

Write tests for the extracted functions, not the delegation wrappers:

```python
# tests/unit/automation/test_follow_up.py
from scylla.automation.follow_up import parse_follow_up_items, run_follow_up_issues

class TestParseFollowUpItems:
    def test_parses_json_in_code_block(self) -> None:
        text = '```json\n[{"title": "T1", "body": "B1"}]\n```'
        items = parse_follow_up_items(text)
        assert items[0]["title"] == "T1"

class TestRunFollowUpIssues:
    def test_creates_issues_and_posts_summary(self, tmp_path: Path) -> None:
        with (
            patch("scylla.automation.follow_up.run", return_value=mock_result),
            patch("scylla.automation.follow_up.gh_issue_create", side_effect=[101, 102]),
            patch("scylla.automation.follow_up.gh_issue_comment") as mock_comment,
        ):
            run_follow_up_issues("sess", worktree_path, 42, tmp_path)
        mock_comment.assert_called_once()
```

### Phase 8: Run Pre-commit (Twice Expected)

```bash
SKIP=audit-doc-policy pre-commit run --files \
  <package>/implementer.py \
  <package>/follow_up.py \
  <package>/retrospective.py \
  <package>/pr_manager.py \
  tests/unit/<package>/test_follow_up.py \
  tests/unit/<package>/test_pr_manager.py \
  tests/unit/<package>/test_retrospective.py
```

First run: ruff auto-fixes imports. Second run: all hooks pass.

**Common mypy issues**:
- `"object" has no attribute "update_slot"` — use the concrete type (`StatusTracker | None`) instead of `object | None`
- `Missing type parameters for generic type "dict"` — use `dict[str, Any]` not bare `dict`

### Phase 9: Verify

```bash
wc -l <package>/implementer.py           # must be < 1000
pixi run python -c "from <package>.implementer import IssueImplementer; print('OK')"
pixi run python -c "from <package>.follow_up import parse_follow_up_items; print('OK')"
pixi run python -m pytest tests/unit/<package>/ -q  # all tests pass
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| **`object` type for status_tracker** | Used `status_tracker: object \| None` to avoid importing `StatusTracker` | mypy error: `"object" has no attribute "update_slot"` — `object` is too broad | Import the concrete type; the module already imports from the same package so there's no circular import risk |
| **Bare `dict` in test helper** | Wrote `def _make_output(items: list[dict]) -> str` | mypy `type-arg` error: generic type needs params | Use `list[dict[str, Any]]` consistently |
| **Forgetting to update existing test patch paths** | Left `patch("scylla.automation.implementer.run")` for methods that moved to `follow_up.py` | Test passes Python import but mock is never triggered — `AssertionError: Called 0 times` | Always grep for module-level patches in existing tests when extracting code to a new module |
| **Extracting all clusters before checking line count** | Planned to extract all 3 clusters unconditionally | Premature — checking after each extraction shows whether target is met; avoids over-engineering | Apply YAGNI: check `wc -l` after each cluster extraction; stop when < 1000 |
| **Using `object` type for collaborator param** | Typed workspace_manager as `object` to avoid circular imports | mypy: `"object" has no attribute "create_worktree"` — `object` is too permissive | Use `TYPE_CHECKING` guard: `if TYPE_CHECKING: from .workspace_manager import WorkspaceManager`; then use `WorkspaceManager` as the type annotation |
| **Inlining delegation shells that tests mock** | Removed `_write_pid_file` and `_cleanup_pid_file` methods to reduce line count | Existing tests used `patch.object(runner, "_write_pid_file")` — removing the method broke 9 tests with `AttributeError: does not have the attribute '_write_pid_file'` | Retain thin delegation wrappers when existing tests mock them by name; the 6-line cost is worth the compatibility |
| **Patching wrong logger after extraction** | Left `patch("scylla.e2e.runner.logger")` in test for warnings now logged by the extracted class | Test failed: mock showed 0 warning calls because warning was emitted from `scylla.e2e.checkpoint_finalizer.logger` | After each extraction, grep existing tests for `patch("…old_module.logger")` and update to the new module's logger |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Keep thin delegation wrappers** | Preserves the existing public interface — callers and tests that use `instance._run_retrospective()` continue to work unchanged |
| **Extract to module-level functions, not classes** | Methods only used `self.state_dir` and `self.status_tracker` — passing these as parameters is simpler than creating a new class |
| **Explicit parameters over `self`** | `run_retrospective(session_id, worktree_path, issue_number, state_dir, slot_id)` is independently unit-testable; no need to construct a full `IssueImplementer` |
| **Largest savings first** | Extract the cluster that saves the most lines first; stop when the target line count is met |
| **Don't re-export extracted symbols** | Only the delegation wrappers exist in the parent — no need for `from .follow_up import run_follow_up_issues as run_follow_up_issues` public re-exports since the symbols were always private |

## Implementation Checklist

- [ ] `wc -l` confirms file exceeds target (e.g., 1000 lines)
- [ ] Identify 2+ method clusters with clear ownership boundaries
- [ ] For each cluster (largest savings first):
  - [ ] Create new module with no imports from parent
  - [ ] Convert `self.X` references to explicit parameters
  - [ ] Add import in parent and replace method body with delegation wrapper
  - [ ] Run smoke test: `python -c "from <package>.<module> import <fn>; print('OK')"`
  - [ ] Check `wc -l` — stop if target reached (YAGNI)
- [ ] Remove unused imports from parent (ruff catches misses)
- [ ] Update existing test patch paths for moved code
- [ ] Write new unit tests for extracted functions (patch at new module location)
- [ ] Run pre-commit twice; fix mypy type annotation issues
- [ ] Run full test suite; verify coverage threshold passes

## Results & Parameters

**Files created** (3 new modules):
- `<package>/retrospective.py` — `run_retrospective()`, `retrospective_needs_rerun()`
- `<package>/follow_up.py` — `run_follow_up_issues()`, `parse_follow_up_items()`
- `<package>/pr_manager.py` — `ensure_pr_created()`, `create_pr()`, `commit_changes()`

**Files modified**:
- `<package>/implementer.py` — 1,221 → 837 lines (−384); thin delegation wrappers only
- `tests/unit/<package>/test_implementer.py` — 10 patch paths updated to new module locations

**New tests**: 37 unit tests across 3 new test files, all passing

**Pre-commit**: All hooks pass after 2 runs (ruff auto-fixes on first)

## Variant: Class-Based Extraction with Factory Methods

When the extracted cluster needs access to multiple `self` attributes that form a natural object
(e.g., `self.config` + `self.results_base_dir`), extract into a **collaborator class** instead
of module-level functions.

```python
# New collaborator class
class ExperimentSetupManager:
    def __init__(self, config: ExperimentConfig, results_base_dir: Path) -> None:
        self.config = config
        self.results_base_dir = results_base_dir

    def create_experiment_dir(self) -> Path: ...
    def copy_grading_materials(self, experiment_dir: Path) -> None: ...
    def save_config(self, experiment_dir: Path) -> None: ...
    def capture_baseline(self, experiment_dir: Path, workspace_manager: WorkspaceManager) -> None: ...
    def write_pid_file(self, experiment_dir: Path) -> None: ...
    def cleanup_pid_file(self, experiment_dir: Path) -> None: ...

# Factory method in parent class
def _setup_manager(self) -> ExperimentSetupManager:
    """Create an ExperimentSetupManager bound to current state."""
    return ExperimentSetupManager(self.config, self.results_base_dir)

# Delegation in parent (retains method for backward compat with test mocks)
def _write_pid_file(self) -> None:
    """Write PID file for status monitoring."""
    if self.experiment_dir:
        self._setup_manager().write_pid_file(self.experiment_dir)
```

**When to choose class-based over function-based**:
- The cluster needs 2+ `self` attributes that always travel together
- The extracted methods form a coherent lifecycle (init → use → cleanup)
- Existing tests mock the parent's delegation methods by name (keep them for compat)

**Critical: `TYPE_CHECKING` for collaborator type hints** — if the collaborator accepts a type
from a module that would create a circular import, use `TYPE_CHECKING`:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scylla.e2e.workspace_manager import WorkspaceManager

def capture_baseline(self, experiment_dir: Path, workspace_manager: WorkspaceManager) -> None:
    ...
```

Using `object` as the type causes `"object" has no attribute 'create_worktree'` mypy errors.

**Delegation method retention** — if existing tests patch `patch.object(runner, "_write_pid_file")`,
keep the delegation shell. Removing it to inline the call breaks those tests.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1444 — decompose `scylla/automation/implementer.py` 1221→837 lines | [notes.md](../references/notes.md) |
| ProjectScylla | PR #1468 — decompose `scylla/e2e/runner.py` 1230→999 lines (class-based variant) | [runner-notes.md](../references/runner-notes.md) |
