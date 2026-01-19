# References: fix-directory-not-created-before-write

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Parallel execution bug | Imported from ProjectScylla .claude-plugin/skills/fix-directory-not-created-before-write |

## Source

Originally created for ProjectScylla to fix intermittent FileNotFoundError in parallel execution.

## Additional Context

This skill documents a subtle race condition bug:

**Problem Pattern:**
- Directory path assigned but `mkdir()` never called
- Works when child operations create parent directory implicitly
- Fails when child operations are skipped (checkpoint, early exit)

**Root Cause:**
- Directory assignment != directory creation in Python pathlib
- Implicit creation by subdirectories masked the bug
- Parallel execution + checkpoints exposed the race condition

**Solution:**
- Single line fix: Add `tier_dir.mkdir(parents=True, exist_ok=True)`
- Ensure directory exists before any write operations

**Key Insight:**
Directory assignment is not directory creation - always explicitly create directories before writing.

## Related Skills

- e2e-path-resolution-fix: Path handling issues
- parallel-execution-patterns: Concurrent execution best practices
