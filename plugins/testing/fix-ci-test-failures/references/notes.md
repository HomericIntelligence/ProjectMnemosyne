# References: fix-ci-test-failures

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #191 CI failures | Imported from ProjectScylla .claude-plugin/skills/fix-ci-test-failures |

## Source

Originally created for ProjectScylla to fix tests passing locally but failing in CI.

## Additional Context

This skill documents the systematic approach to fixing 6 tests that passed locally but failed in GitHub Actions:

**Root Causes Identified:**
1. Absolute symlinks breaking in CI (different workspace paths)
2. Mocks on wrong method (bypassed by implementation)
3. Missing Docker images in CI

**Solutions Applied:**
1. Convert absolute symlinks to relative paths
2. Mock the actual method called (not the constructor parameter)
3. Use proper mocking to avoid Docker dependencies

**Key Lessons:**
- Symlinks must be relative for portability
- Mock the actual method called, not what you assume
- Unit tests shouldn't depend on external resources
- Pre-existing CI failures should be fixed, not ignored

## Related Skills

- fix-symlink-issues: General symlink troubleshooting
- mock-testing-patterns: Effective mocking strategies
