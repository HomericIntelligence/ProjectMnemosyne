## 2026-02-27: docker-ci-dead-step-cleanup (ProjectScylla #1114)

Session resolved a CI workflow referencing a non-existent test directory.

Key insight: When a CI step tests Docker integration and requires API keys,
Option B (remove + ADR) is almost always the right choice over Option A
(implement heavyweight integration tests in standard PR CI).

The pre-commit hook that runs all tests before `git push` caught any regressions:
3185 tests, 78.36% coverage, push succeeded.