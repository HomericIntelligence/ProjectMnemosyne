# References: fix-ci-failures

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | CI/CD workflows | Imported from ProjectOdyssey .claude/skills/fix-ci-failures |

## Source

Originally created for ProjectOdyssey to systematically fix CI/CD failures.

## Additional Context

This skill provides a complete workflow for:
1. Checking PR checks status with `gh pr checks`
2. Viewing failure details with `gh run view`
3. Reproducing issues locally
4. Applying fixes
5. Verifying locally before pushing
6. Monitoring CI after fix

## Common Failure Types

- Trailing whitespace (pre-commit hooks)
- Test failures (Mojo tests)
- Markdown linting errors
- Build errors (imports/dependencies)

## Related Skills

- analyze-ci-failure-logs: For log analysis
- run-precommit: For running pre-commit hooks
- quality-run-linters: For linting checks
