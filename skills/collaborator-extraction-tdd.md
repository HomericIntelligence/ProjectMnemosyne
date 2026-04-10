---
name: collaborator-extraction-tdd
description: 'TRIGGER CONDITIONS: Extracting method groups from an oversized class
  (>800 lines) into dedicated collaborator classes using TDD. Use when: (1) a class
  has grown beyond its target line count and contains identifiable method groups with
  shared state, (2) extracting without behavior change (pure structural refactoring),
  (3) avoiding circular imports between the host class and extracted collaborators.'
category: architecture
date: 2026-02-28
version: 1.0.0
user-invocable: false
---
# collaborator-extraction-tdd

TDD-first pattern for extracting method groups from a large class into dedicated collaborator classes, with explicit dependency injection and zero behavior change.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-28 |
| Objective | Reduce `runner.py` from 1527 lines to <1000 lines by extracting three method groups into collaborator classes |
| Outcome | Success — 1105 lines (-422 lines, -28%). All 3326 tests pass. All pre-commit hooks pass. |

## When to Use

- A class exceeds its target line count (e.g. 800-line guideline) and has identifiable method groups
- The method groups share only a subset of the class's state (not the full `self`)
- You want zero behavior change — pure structural extraction
- You need to avoid circular imports between the extracted class and its host
- The host class uses closures or callbacks that can be injection-injected instead

## Verified Workflow

### 1. Measure and Identify Method Groups

```bash
# Measure current size
wc -l scylla/e2e/runner.py

# Find largest methods
python3 -c "
import ast
with open('scylla/e2e/runner.py') as f:
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

Identify groups where:
- Methods share a focused subset of the host class's state
- The group has a clear single responsibility
- Methods call each other but not the rest of the host class

### 2. Design the Collaborator Interface (Dependency Injection)

Each collaborator receives **only what it needs** as explicit constructor args — never the full host class reference. Map host `self.X` → explicit arg `X`:

```python
class TierActionBuilder:
    def __init__(
        self,
        tier_id: TierID,
        config: ExperimentConfig,       # was self.config
        tier_manager: TierManager,      # was self.tier_manager
        save_tier_result_fn: Callable,  # was self._save_tier_result (injected callback)
        ...
    ) -> None: ...
```

**Key rule**: For callbacks that would cause circular coupling (host method passed to collaborator), inject them as `Callable` parameters rather than passing a host reference.

### 3. Write Failing Tests First (Red Phase)

```bash
# Create test file and run - expect ImportError (module doesn't exist yet)
pixi run python -m pytest tests/unit/e2e/test_tier_action_builder.py -x
```

**Critical test patterns:**

```python
# Always create real Pydantic models — MagicMock won't pass validation
def _make_subtest_result(subtest_id: str = "00", **kwargs) -> SubTestResult:
    return SubTestResult(
        subtest_id=subtest_id,
        tier_id=TierID.T0,
        runs=[],
        pass_rate=0.5,
        mean_cost=0.01,
        total_cost=0.02,
        token_stats=TokenStats(),
        **kwargs,
    )

# ExperimentConfig requires ALL fields: experiment_id, task_repo, task_commit,
# task_prompt_file, language — omitting any causes pydantic ValidationError
config = ExperimentConfig(
    experiment_id="test-exp",
    task_repo="https://github.com/test/repo",
    task_commit="abc123",
    task_prompt_file=Path("/tmp/prompt.md"),
    language="python",
)
```

### 4. Create the Collaborator Module (Green Phase)

Move closures and methods verbatim. Replace `self.X` with constructor-injected equivalents.

**Circular import avoidance** — if the collaborator needs a function from the host module, use a lazy local import inside the method body:

```python
# In parallel_tier_runner.py — avoids circular import with runner.py
def execute_tier_groups(self, ...) -> dict:
    from scylla.e2e.runner import is_shutdown_requested  # lazy import
    for group in tier_groups:
        if is_shutdown_requested():
            break
        ...
```

### 5. Wire Back with Thin Delegation

Replace extracted method bodies in the host class with 1-line delegation:

```python
def _build_tier_actions(self, tier_id, baseline, scheduler, tier_ctx):
    return TierActionBuilder(
        tier_id=tier_id,
        config=self.config,
        tier_manager=self.tier_manager,
        save_tier_result_fn=self._save_tier_result,
        ...
    ).build()
```

### 6. Update Affected Tests

When methods move, update:
- **Patch targets**: `scylla.e2e.runner.run_tier_subtests_parallel` → `scylla.e2e.tier_action_builder.run_tier_subtests_parallel`
- **Direct method calls**: `runner._select_best_baseline_from_group()` → `ParallelTierRunner(...).select_best_baseline_from_group()`
- **Test class rewrites**: If a test class tests a method that moved, rewrite it to instantiate the collaborator directly

### 7. Fix Mypy Issues in Tests

Common mypy errors after extraction:

| Error | Fix |
|-------|-----|
| `Item "None" of "X \| None" has no attribute "Y"` | Add `assert obj is not None` before accessing attributes |
| `Unexpected keyword argument "cost_of_pass"` for `TierResult` | `cost_of_pass` is a `@property`, not a field — remove from constructor |
| `Argument "run_tier_fn" has incompatible type "Callable"` | Broaden type hint: `Callable[..., TierResult] \| MagicMock \| None` |
| `F841 Local variable assigned to but never used` | Remove the unused variable entirely |

### 8. Verify

```bash
# Import smoke test
pixi run python -c "from scylla.e2e.runner import E2ERunner; print('OK')"
pixi run python -c "from scylla.e2e.tier_action_builder import TierActionBuilder; print('OK')"

# Full test suite
pixi run python -m pytest tests/ -x -q --tb=short

# Pre-commit (mypy, ruff, black)
pre-commit run --all-files

# Final line count
wc -l scylla/e2e/runner.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

```text
# Extraction results for runner.py → 3 collaborators
runner.py baseline:  1527 lines
After PR-A (TierActionBuilder):   -~175 lines (includes 34-line stub + docstring)
After PR-B (ParallelTierRunner):  -~170 lines (includes 24-line stub)
After PR-C (ExperimentResultWriter): -~77 lines (includes delegation stubs)
Final runner.py: 1105 lines (-422 lines, -28%)

# Test impact
New test files: 3
New tests added: 69 (27 + 19 + 23)
Total tests: 3326 (was 3257)
Coverage: 79.27% (threshold: 75%)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1146, PR #1230 | [notes.md](collaborator-extraction-tdd.notes.md) |

## References

- Related skills: `extract-method-refactoring`, `dry-refactoring-workflow`, `state-machine-wiring`
- Issue: HomericIntelligence/ProjectScylla#1146
- PR: HomericIntelligence/ProjectScylla#1230
