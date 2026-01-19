# References: analyze-ci-failure-logs

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | CI/CD workflows | Imported from ProjectOdyssey .claude/skills/analyze-ci-failure-logs |

## Source

Originally created for ProjectOdyssey to help diagnose CI failures in GitHub Actions workflows.

## Additional Context

This skill works with GitHub Actions workflows and can be used to:
- Parse CI logs from `gh run view` or `gh run download`
- Identify error patterns (compilation, test, timeout, dependency, environmental)
- Categorize failures systematically
- Provide actionable remediation steps

## Related Skills

- fix-ci-failures: For implementing fixes after analysis
- gh-get-review-comments: For understanding PR review context
