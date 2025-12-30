---
name: build-run-local
description: "Run local builds with proper environment setup matching CI pipeline"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-30
---

# Build and Run Local

Execute local builds with environment setup matching CI pipeline.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Local verification before push | Catch issues before CI, faster iteration |

## When to Use

- (1) Building code locally before pushing
- (2) Verifying changes work before creating PR
- (3) Debugging build issues in isolation
- (4) Running tests in local environment

## Verified Workflow

1. **Activate environment**: Use environment manager to setup
2. **Verify environment**: Check tool versions and dependencies
3. **Build locally**: Run build with proper flags
4. **Run tests**: Execute test suite locally
5. **Check warnings**: Verify zero-warnings compliance
6. **Run pre-commit**: Validate formatting and linting
7. **Commit changes**: Only after local verification passes

## Results

Copy-paste ready commands:

```bash
# Activate environment (example with pixi)
eval "$(pixi shell-hook)"

# Verify environment
which python && python --version
which mojo && mojo --version

# Build project (Mojo example)
mojo build -I . src/main.mojo

# Run tests
pytest tests/
# or for Mojo
mojo test -I . tests/

# Run specific test
pytest tests/test_specific.py -v
# or for Mojo
mojo test -I . tests/test_specific.mojo

# Format code
black .  # Python
mojo format .  # Mojo

# Run all pre-commit checks
pre-commit run --all-files
```

### Build Flags

- `-I .` includes current directory in path
- `-O` enables optimizations for release builds
- `-v` for verbose output
- `-k "pattern"` to run specific tests

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Built without activating environment | Missing dependencies, wrong tool versions | Always activate environment first |
| Skipped `-I .` flag | Module imports failed | Include current directory in path for local builds |
| Tested only changed files | Missed breaking changes in dependencies | Run full test suite before pushing |
| Pushed without running pre-commit | CI failed on formatting | Always run pre-commit before committing |

## Error Handling

| Problem | Solution |
|---------|----------|
| Environment not found | Activate environment manager (pixi, conda, venv) |
| Module not found | Verify `-I .` flag and correct paths |
| Permission denied | Check file permissions and ownership |
| Out of memory | Reduce parallel jobs or simplify test |
| Timeout | Check for infinite loops or long operations |

## Build Verification Checklist

- [ ] Environment activated
- [ ] Build succeeds with no errors
- [ ] Zero warnings (if required by project)
- [ ] All tests pass
- [ ] Pre-commit hooks pass
- [ ] No new lint errors

## References

- See run-precommit for pre-commit hooks
- See fix-ci-failures for debugging CI issues
- See validate-workflow for workflow validation
