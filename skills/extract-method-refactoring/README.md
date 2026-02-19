# Extract Method Refactoring Skill

**Category:** Architecture
**Created:** 2026-02-15
**Source:** Issue #639 - ProjectScylla

## Quick Start

Use this skill when you need to decompose large methods (>50 lines) into smaller, focused helper methods.

```
"This method is 85 lines long - can you decompose it?"
→ Use extract-method-refactoring skill
```

## What This Skill Provides

- **Systematic workflow** for Extract Method refactoring pattern
- **Incremental approach** that maintains test pass rate
- **Verification steps** at each stage
- **Real example** from reducing 90 LOC method to 30 LOC main + 2 helpers
- **Failed attempts** section to avoid common pitfalls

## When to Use

Trigger conditions:

- Methods exceeding 50 lines (target threshold)
- Methods exceeding 100 lines (hard requirement per CLAUDE.md)
- High cyclomatic complexity (>15)
- Code review requesting decomposition
- Methods with multiple responsibilities

## Key Results

From the original session (Issue #639):

- **Before:** 1 method, 90 LOC, complex control flow
- **After:** 1 main (30 LOC) + 2 helpers (42 LOC, 25 LOC)
- **Test impact:** 0 regressions (2,145 tests passed)
- **Time:** ~1 hour including verification

## Workflow Overview

1. **Analyze** the method structure (don't touch code yet)
2. **Extract** one helper at a time (not all at once)
3. **Verify** tests pass after each extraction
4. **Commit** with clear metrics

## Key Principles

✅ **Do:**

- Extract one method at a time
- Run tests after each extraction
- Add type hints and docstrings immediately
- Keep error handling in extracted methods

❌ **Don't:**

- Extract all methods simultaneously
- Change behavior while refactoring
- Skip verification steps
- Forget to update docstrings

## Files in This Skill

- `SKILL.md` - Complete workflow with verified steps
- `references/notes.md` - Raw session details and commands
- `README.md` - This file

## Example Output

```python
# Before (90 lines)
def _initialize_or_resume_experiment(self) -> Path:
    # ... 90 lines of checkpoint loading + creation logic ...

# After (30 lines main + 2 focused helpers)
def _load_checkpoint_and_config(self, checkpoint_path: Path) -> tuple[E2ECheckpoint, Path]:
    """Load and validate checkpoint."""
    # ... 42 lines ...

def _create_fresh_experiment(self) -> Path:
    """Create new experiment directory."""
    # ... 25 lines ...

def _initialize_or_resume_experiment(self) -> Path:
    """Initialize or resume (orchestration only)."""
    # ... 30 lines - just coordination logic ...
```

## Success Metrics

- Main method reduced by 60-70%
- Each helper <50 LOC
- 100% test pass rate maintained
- Pre-commit hooks pass (ruff, mypy)
- Single Responsibility per method

## Related Skills

- `quality-complexity-check` - Identify when methods need decomposition
- `refactor-for-extensibility` - When to use Extract-Parameterize-Protocol
- `detect-code-smells` - Identify code smell patterns

## Learn More

See `SKILL.md` for the complete verified workflow with all steps, failed attempts, and detailed examples.
