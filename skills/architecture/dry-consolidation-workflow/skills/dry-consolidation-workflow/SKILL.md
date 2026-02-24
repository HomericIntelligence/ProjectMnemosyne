---
name: dry-consolidation-workflow
description: Complete workflow for analyzing codebase duplications and implementing DRY consolidation
category: architecture
date: 2026-01-20
tags: [dry-principle, refactoring, deduplication, code-quality, centralization]
---

# DRY Consolidation Workflow

Complete workflow for analyzing codebase duplications and implementing DRY (Don't Repeat Yourself) consolidation with centralized modules and single sources of truth.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-20 |
| **Objective** | Systematically find and eliminate code duplications while establishing centralized modules |
| **Outcome** | ✅ Eliminated 48 lines of duplicate code, fixed 2 path violations, merged PR #201 |
| **Project** | ProjectScylla |
| **PR** | [#201](https://github.com/HomericIntelligence/ProjectScylla/pull/201) |

## When to Use

Use this workflow when:
- Starting codebase cleanup initiative
- Noticing duplicate functions or constants across files
- Creating single sources of truth for shared logic
- Standardizing path, config, or constant usage
- Improving code maintainability and consistency
- Implementing DRY principles systematically

**Trigger phrases**: "analyze duplicates", "DRY consolidation", "eliminate duplicate code", "centralize constants", "single source of truth"

## Verified Workflow

### Phase 0: Search Team Knowledge First

**CRITICAL**: Always start by searching existing skills to avoid repeating work.

```bash
# Use /advise to search team knowledge
/skills-registry-commands:advise analyze codebase for duplicates DRY
```

**What this does**:
- Searches ProjectMnemosyne skills marketplace
- Returns prior learnings about consolidation patterns
- Provides verified approaches and known failures
- Saves time by building on team knowledge

**Session finding**: Found `codebase-consolidation` and `centralized-path-constants` skills with proven workflows.

### Phase 1: Discovery - Find Duplicates

**1.1 Check for duplicate files by content hash**:
```bash
find src/ -type f \( -name "*.py" -o -name "*.mojo" \) -exec md5sum {} + | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -20
```

**Expected output**: Count of files with identical content
- Count = 1: All files unique (good!)
- Count > 1: Multiple files with same content (investigate)

**1.2 Find duplicate class names**:
```bash
grep -rh "^class [A-Z][a-zA-Z0-9_]*" src/ --include="*.py" | \
  sed 's/(.*//' | sed 's/://' | sort | uniq -c | sort -rn | head -30
```

**1.3 Find duplicate function names**:
```bash
grep -rh "^def [a-z_][a-zA-Z0-9_]*" src/ --include="*.py" | \
  sed 's/(.*//' | sed 's/://' | sort | uniq -c | sort -rn | head -30
```

**1.4 Find specific duplicates**:
```bash
# After identifying duplicate names, find their locations
grep -rn "^class RunResult" src/ --include="*.py"
grep -rn "^def _calculate_composite_score" src/ --include="*.py"
```

**1.5 Search for hardcoded strings**:
```bash
# Find hardcoded paths, configs, or constants
grep -rn '"agent"\|"judge"\|"result\.json"' src/ --include="*.py" | \
  grep -v "^[[:space:]]*#"  # Exclude comments
```

### Phase 2: Categorization - True vs Intentional

For each duplicate found, read the implementations and categorize:

**True Duplicates** (consolidate):
- Identical or near-identical code
- Same purpose, same logic
- No reason for separate implementations
- **Action**: Create centralized module

**Intentional Variants** (document):
- Different fields for different domains
- Different stages of processing pipeline
- Valid architectural separation
- **Action**: Add cross-reference docstrings

**Example categorization**:
```python
# True duplicate - consolidate
# File 1: src/module_a.py
def _is_test_config_file(file_path: str) -> bool:
    return path == "CLAUDE.md" or path.startswith(".claude/")

# File 2: src/module_b.py
def _is_test_config_file(file_path: str) -> bool:
    return path == "CLAUDE.md" or path.startswith(".claude/")

# Intentional variant - document
# File 1: src/executor/runner.py
class ExecutionInfo(BaseModel):  # Pydantic with validation
    container_id: str
    exit_code: int

# File 2: src/reporting/result.py
@dataclass
class ExecutionInfo:  # Lightweight for persistence
    exit_code: int
    duration_seconds: float
```

### Phase 3: Analysis Report - Communicate Findings

Generate a structured report documenting all findings:

**Report structure**:
```markdown
## Codebase Duplication Analysis

### Summary
- Files analyzed: X
- Duplicate files by hash: Y
- Duplicate class names: Z
- Duplicate function names: W

### True Duplicates (Consolidation Recommended)
1. **function_name()** - EXACT DUPLICATE
   - Locations: [file1:line, file2:line]
   - Implementation: [describe]
   - Recommendation: [consolidation approach]

### Intentional Variants (Documentation Needed)
1. **ClassName** - Different purposes
   - Locations: [file1:line, file2:line]
   - Analysis: [explain why different]
   - Recommendation: [add cross-refs]

### Hardcoded Violations
1. **Path strings** - Should use centralized module
   - Locations: [file:line]
   - Current: `run_dir / "agent"`
   - Recommended: `get_agent_dir(run_dir)`
```

### Phase 4: Implementation - Create Centralized Modules

**4.1 Create centralized module** for true duplicates:

```python
# Example: src/package/filters.py (NEW FILE)
"""Filtering utilities for [purpose].

This module provides functions to [describe shared functionality]
that should not be counted as [context].
"""

def is_test_config_file(file_path: str) -> bool:
    """Check if a file is part of test configuration.

    Args:
        file_path: Relative file path

    Returns:
        True if file should be ignored.
    """
    path = file_path.strip()
    return path == "CLAUDE.md" or path.startswith(".claude/")
```

**4.2 Update imports** in original files:

```python
# Before:
# (no import, function defined inline)

# After:
from package.filters import is_test_config_file
```

**4.3 Remove duplicate functions**:

```python
# Delete the old function definition entirely
# def _is_test_config_file(file_path: str) -> bool:
#     """..."""
#     return ...
```

**4.4 Update all call sites**:

```python
# Before:
if _is_test_config_file(file_path):
    continue

# After:
if is_test_config_file(file_path):  # Now uses centralized function
    continue
```

**4.5 Use existing centralized modules** for hardcoded violations:

```python
# Before:
agent_dir = run_dir / "agent"  # Hardcoded string

# After:
from package.paths import get_agent_dir
agent_dir = get_agent_dir(run_dir)  # Uses centralized helper
```

### Phase 5: Documentation - Add Cross-References

For intentional variants, add cross-reference docstrings:

```python
# In executor/runner.py
class ExecutionInfo(BaseModel):
    """Execution details with Pydantic validation.

    This is the executor's detailed execution info.
    For persistence variant, see: reporting/result.py:ExecutionInfo
    """

# In reporting/result.py
@dataclass
class ExecutionInfo:
    """Execution details for persistence.

    This is the minimal execution info for storage.
    For detailed variant, see: executor/runner.py:ExecutionInfo
    """
```

### Phase 6: Verification - Test Changes

**6.1 Verify imports** (with proper environment):

```bash
# Use project's environment manager
pixi run python -c "from package.filters import function_name; print('OK')"
pixi run python -c "import package.module; print('OK')"
```

**6.2 Run full test suite**:

```bash
pixi run pytest tests/ -v --tb=short -x
```

**6.3 Check for test failures**:
- ✅ All imports successful: Good!
- ✅ Tests passing: No regressions
- ❌ Test failures: Check if related to changes

### Phase 7: Commit - Follow Git Workflow

**7.1 Create feature branch**:

```bash
git checkout -b refactor-dry-consolidation
```

**7.2 Run pre-commit hooks**:

```bash
pre-commit run --all-files
```

**7.3 Stage and commit**:

```bash
git add src/package/filters.py src/package/module1.py src/package/module2.py
git commit -m "refactor(scope): Consolidate duplicate functions and centralize constants"
```

**7.4 Push and create PR**:

```bash
git push -u origin refactor-dry-consolidation
gh pr create --title "refactor: DRY consolidation" \
  --body "[detailed summary]" \
  --label "refactor"
```

**7.5 Enable auto-merge**:

```bash
gh pr merge --auto --rebase [PR-NUMBER]
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Running Python imports without pixi | `ModuleNotFoundError` - must use project's environment manager |
| Skipping /advise at start | Missed valuable team knowledge from prior consolidation sessions |
| Not categorizing duplicates first | Risk of consolidating intentional variants incorrectly |

## Results & Parameters

### Discovery Commands (Copy-Paste Ready)

```bash
# Find duplicate files by content
find src/ -type f -name "*.py" -exec md5sum {} + | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# Find duplicate class names
grep -rh "^class [A-Z]" src/ --include="*.py" | \
  sed 's/(.*//' | sed 's/://' | sort | uniq -c | sort -rn

# Find duplicate function names
grep -rh "^def [a-z_]" src/ --include="*.py" | \
  sed 's/(.*//' | sed 's/://' | sort | uniq -c | sort -rn

# Find hardcoded strings
grep -rn '"specific_string"' src/ --include="*.py" | grep -v "^[[:space:]]*#"
```

### Centralized Module Template

```python
# src/package/shared_module.py
"""[Purpose] utilities for [context].

This module centralizes [what functionality] to ensure
[what benefit - consistency/maintainability/etc].
"""

def shared_function(param: type) -> type:
    """[What it does].

    Args:
        param: [Description]

    Returns:
        [What is returned]
    """
    # Implementation
    pass

# Constants (UPPERCASE)
CONSTANT_NAME = "value"
```

### Import Update Pattern

```python
# 1. Add import at top of file
from package.shared_module import shared_function, CONSTANT_NAME

# 2. Remove old duplicate function
# (delete old def entirely)

# 3. Update all call sites
# Before: _old_function(arg)
# After:  shared_function(arg)
```

### Verification Commands

```bash
# Verify imports
pixi run python -c "from package.module import function; print('OK')"

# Run tests
pixi run pytest tests/ -v --tb=short -x

# Check git status
git status

# Create PR
gh pr create --title "refactor: [description]" \
  --body "[summary]" --label "refactor"
```

### Session Metrics

| Metric | Before | After | Result |
|--------|--------|-------|--------|
| Duplicate functions | 1 pair | 0 | ✅ 100% eliminated |
| Path violations | 2 | 0 | ✅ 100% fixed |
| Centralized module usage | 66% | 100% | ✅ +34% |
| Lines of code | Baseline | -15 | ✅ Reduction |
| Tests passing | 1,051 | 1,051 | ✅ No regressions |

### Commit Message Template

```
refactor(scope): Consolidate duplicate functions and centralize constants

## Changes

### 1. Created centralized [module name]
- **New file**: src/package/module.py
- Consolidates [function] used in N locations
- Single source of truth for [purpose]

### 2. Eliminated duplicate [type]
- Removed duplicate [name] from:
  - src/file1.py (X lines)
  - src/file2.py (Y lines)
- Updated all call sites

### 3. Standardized [pattern] usage
- Updated src/file.py to use centralized helper
- Ensures consistent use of [module]

## Benefits
- **DRY compliance**: X lines eliminated
- **Single source of truth**: [what] centralized
- **Maintainability**: Future changes touch one file
- **Type safety**: Helpers prevent [what errors]

## Testing
- ✅ All imports verified
- ✅ N tests passed
- No regressions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Key Learnings

1. **Always search team knowledge first**: Use `/advise` before starting - saved time by finding proven workflows
2. **Categorize before consolidating**: Distinguish true duplicates from intentional variants to avoid incorrect consolidation
3. **Verify with proper environment**: Always use project's environment manager (pixi/poetry/etc) for imports
4. **Test immediately**: Run full test suite to catch regressions early
5. **Document intentional variants**: Cross-reference docstrings prevent future confusion
6. **Follow Git workflow**: Feature branch → pre-commit → PR → auto-merge ensures quality

## Related Skills

- `codebase-consolidation` - Systematic consolidation patterns (ProjectMnemosyne)
- `centralized-path-constants` - Path centralization specifics (ProjectMnemosyne)
- `shared-fixture-migration` - Config deduplication patterns (ProjectMnemosyne)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #201 - E2E framework DRY consolidation | Eliminated 48 LOC duplicates, standardized paths |
