# Centralized Path Constants - Implementation Notes

## Context

ProjectScylla E2E runner had hardcoded path construction scattered across files:
- `subtest_executor.py`: `run_dir / "agent"`, `agent_dir / "result.json"`
- Multiple occurrences of `"agent"`, `"judge"`, `"result.json"` strings
- Risk of typos causing silent failures during resume

## Solution

Created `src/scylla/e2e/paths.py` with:

```python
# Constants
AGENT_DIR = "agent"
JUDGE_DIR = "judge"
RESULT_FILE = "result.json"

# Helper functions
def get_agent_dir(run_dir: Path) -> Path
def get_judge_dir(run_dir: Path) -> Path
def get_agent_result_file(run_dir: Path) -> Path
def get_judge_result_file(run_dir: Path) -> Path
```

## Files Updated

- `src/scylla/e2e/paths.py` (NEW - 64 lines)
- `src/scylla/e2e/subtest_executor.py`:
  - Added import
  - Replaced `run_dir / "agent"` with `get_agent_dir(run_dir)`
  - Replaced `run_dir / "judge"` with `get_judge_dir(run_dir)`
  - Replaced `agent_dir / "result.json"` with `agent_dir / RESULT_FILE`
  - Replaced `judge_dir / "result.json"` with `judge_dir / RESULT_FILE`

## Benefits

1. **Foundation for #132**: Skip completed runs needs consistent path validation
2. **Prevents typos**: `"agent"` vs `"agents"` caught at import time
3. **Easy refactoring**: Change directory name in one place
4. **Self-documenting**: `get_agent_result_file()` clearer than `run_dir / "agent" / "result.json"`

## Testing

- Pre-commit hooks passed
- No functional changes - pure refactor
- Existing E2E tests pass unchanged

## PR Details

- **Branch**: `133-standardize-result-paths`
- **Files Changed**: 2 (1 new, 1 modified)
- **Lines**: +78, -7
- **Status**: Merged to main
