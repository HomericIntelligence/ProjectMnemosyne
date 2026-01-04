---
name: centralized-path-constants
description: Create central path constants module to prevent hardcoded path inconsistencies
category: architecture
date: 2026-01-04
tags: [paths, refactoring, consistency, constants, dry-principle]
---

# Centralized Path Constants

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Eliminate hardcoded path construction and create single source of truth for directory structure |
| **Outcome** | ✅ Created paths module with constants and helpers, preventing inconsistencies |
| **Project** | ProjectScylla |
| **PR** | [#137](https://github.com/HomericIntelligence/ProjectScylla/pull/137) |

## When to Use

Use this pattern when:
- Multiple files construct the same paths with hardcoded strings
- Path logic is duplicated across modules
- Refactoring directory structure requires changes in many places
- Resume/checkpoint logic needs to validate path existence
- Risk of typos in path strings (e.g., `"agent"` vs `"agents"`)

## Problem

**Scattered Path Construction**:
```python
# File 1:
agent_dir = run_dir / "agent"
result_file = agent_dir / "result.json"

# File 2:
agent_results = run_dir / "agent" / "result.json"  # Typo risk

# File 3:
if (run_dir / "agents" / "result.json").exists():  # BUG: wrong dir name!
```

**Issues**:
1. No single source of truth
2. Typos cause silent failures
3. Refactoring requires finding all string occurrences
4. Testing path logic is difficult

## Verified Workflow

### 1. Create Paths Module

**File**: `src/<package>/paths.py`

```python
"""Path constants and helpers for directory structure.

Centralizes all path logic to ensure consistency.
"""
from pathlib import Path

# Directory name constants
AGENT_DIR = "agent"
JUDGE_DIR = "judge"
RESULT_FILE = "result.json"

def get_agent_dir(run_dir: Path) -> Path:
    """Get agent artifacts directory for a run."""
    return run_dir / AGENT_DIR

def get_judge_dir(run_dir: Path) -> Path:
    """Get judge artifacts directory for a run."""
    return run_dir / JUDGE_DIR

def get_agent_result_file(run_dir: Path) -> Path:
    """Get agent result.json file path."""
    return get_agent_dir(run_dir) / RESULT_FILE

def get_judge_result_file(run_dir: Path) -> Path:
    """Get judge result.json file path."""
    return get_judge_dir(run_dir) / RESULT_FILE
```

### 2. Update Imports

```python
# Old:
# (no imports, paths hardcoded inline)

# New:
from <package>.paths import (
    RESULT_FILE,
    get_agent_dir,
    get_agent_result_file,
    get_judge_dir,
    get_judge_result_file,
)
```

### 3. Replace Hardcoded Paths

```python
# Before:
agent_dir = run_dir / "agent"
judge_dir = run_dir / "judge"
agent_result_file = agent_dir / "result.json"

# After:
agent_dir = get_agent_dir(run_dir)
judge_dir = get_judge_dir(run_dir)
agent_result_file = get_agent_result_file(run_dir)
```

### 4. Use Constants for Literals

```python
# Before:
with open(agent_dir / "result.json", "w") as f:
    json.dump(data, f)

# After:
with open(agent_dir / RESULT_FILE, "w") as f:
    json.dump(data, f)
```

### 5. Verify with Tests

```python
def test_path_consistency():
    """Ensure all path helpers return consistent results."""
    run_dir = Path("/tmp/run_01")

    # Agent paths
    assert get_agent_dir(run_dir) == run_dir / "agent"
    assert get_agent_result_file(run_dir) == run_dir / "agent" / "result.json"

    # Judge paths
    assert get_judge_dir(run_dir) == run_dir / "judge"
    assert get_judge_result_file(run_dir) == run_dir / "judge" / "result.json"
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Using environment variables | Runtime configuration not appropriate for structural constants |
| Dataclass for paths | Overkill for simple directory names, harder to use |
| Class with static methods | More verbose than module-level functions |
| Config file (YAML/JSON) | Adds unnecessary I/O for constants that never change |

## Results & Parameters

### Pattern Template

```python
# paths.py structure:

# 1. Constants (uppercase)
SUBDIR_NAME = "subdirectory"
FILE_NAME = "file.json"

# 2. Directory getters
def get_subdir(parent: Path) -> Path:
    return parent / SUBDIR_NAME

# 3. File path getters
def get_file(parent: Path) -> Path:
    return get_subdir(parent) / FILE_NAME

# 4. Optional: Validation helpers
def has_valid_structure(parent: Path) -> bool:
    return get_file(parent).exists()
```

### Migration Checklist

- [x] Create `paths.py` module
- [x] Define directory name constants
- [x] Create helper functions for each path type
- [x] Import in files that construct paths
- [x] Replace hardcoded strings with helpers
- [x] Replace file name strings with constants
- [x] Run tests to verify no regressions
- [x] Update documentation if paths change

### Benefits Achieved

1. **Single Source of Truth**: One place to update directory structure
2. **Type Safety**: Path objects instead of strings reduce bugs
3. **Consistency**: Impossible to have typos across files
4. **Refactoring**: Change directory name once, all code updates
5. **Testing**: Easy to mock/test path logic
6. **Documentation**: Self-documenting helper function names

## Key Learnings

1. **Centralize Early**: Add paths module at project start, not after bugs appear
2. **Helper Functions Over Constants**: `get_agent_dir()` > `AGENT_DIR` for complex paths
3. **Compose Helpers**: Build complex paths from simple ones (`get_agent_result_file` uses `get_agent_dir`)
4. **No Magic Strings**: Even file names should be constants
5. **Foundation for Validation**: Centralized paths enable centralized validation logic

## Related Skills

- `architecture/dry-principle` - Don't Repeat Yourself patterns
- `refactor/extract-module` - When to create new modules
- `testing/path-mocking` - Testing code with file system dependencies

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #137 - Path standardization foundation for resume logic | [notes.md](../../references/notes.md) |
