# CI Failure Workflow - Notes

## Plugin Overview

This plugin consolidates 2 related CI failure skills into a single coherent workflow:

1. **analyze** - Parse CI logs to identify root causes and error patterns
2. **fix** - Systematic workflow to reproduce, fix, and verify CI issues

## Typical Workflow

```
1. gh pr checks <pr-number>              (check what's failing)
2. gh run view <run-id> --log-failed     (analyze - get logs)
3. grep -i "error\|failed" /tmp/ci.log   (analyze - find errors)
4. [reproduce locally, make fix]
5. git add . && git commit -m "fix: ..."  (fix)
6. git push && gh pr checks --watch       (fix - verify)
```

## Key Insight

The most common mistake is fixing one failure while missing others. Always:
1. Analyze the FULL log
2. Fix ALL failures at once
3. Test locally before pushing

## Consolidated From

This plugin was created by merging:
- `ci-cd/analyze-ci-failure-logs`
- `ci-cd/fix-ci-failures`

Note: `batch-pr-ci-fix` remains separate (distinct multi-PR use case).

## Source

- ProjectOdyssey development workflow
- Date: 2025-12-30
