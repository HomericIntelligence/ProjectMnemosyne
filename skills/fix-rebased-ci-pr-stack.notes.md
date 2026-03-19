# Session Notes: Fix Rebased CI PR Stack

**Date**: 2026-03-15
**Project**: ProjectScylla
**PRs Fixed**: #1494, #1496, #1497, #1498

## Context

7-PR CI containerization effort. PRs #1492, #1493, #1495 merged successfully.
Remaining 4 PRs had CI failures. All were 3 commits behind main.

## Failures Encountered

### PR #1494 (ci-image-workflow)
- **Check**: `Build, scan, and push CI image: FAILURE`
- **Log**: `stat /home/runner/work/ProjectScylla/ProjectScylla/ci/Containerfile: no such file or directory`
- **Root cause**: `ci/Containerfile` was added by PR #1493 which merged AFTER #1494 branched
- **Fix**: `git rebase origin/main` — Containerfile now present in rebase

### PR #1496 (ci-security-hardening)
Three separate failures:

1. **Check**: `Secrets scan (gitleaks): FAILURE`
   - **Log**: `[HomericIntelligence] is an organization. License key is required.`
   - **Fix**: Replace `gitleaks/gitleaks-action@v2` with CLI download + run

2. **Check**: `docker-validation: FAILURE`
   - **Log**: `node:20-slim@sha256:65b1bbfe...: not found`
   - **Fix**: `docker manifest inspect node:20-slim` → new digest `eef3816...`

3. **Check**: `test (unit): FAILURE`
   - **Log**: `AssertionError: Expected exactly 2 FROM lines in docker/Dockerfile, found 3`
   - Also: `AssertionError: Could not find 'Node.js setup (nodesource)' in docker/Dockerfile`
   - **Root cause**: PR changes Dockerfile from 2-stage to 3-stage (adds `AS node-source`),
     replaces `curl | bash nodesource` with `COPY --from=node-source`
   - **Fix**: Update `tests/unit/docker/test_dockerfile_layer_ordering.py`

### PR #1498 (ci-robustness)
- **Check**: `test (unit, integration): FAILURE`
- **Log**: `BaseRunMetrics usage count: 1` → `./scylla/reporting/result.py:42: - BaseRunMetrics (core/results.py) - Legacy dataclass (deprecated)`
- **Root cause**: Deprecation grep filtered `# deprecated` but not `(deprecated)` in docstrings
- **Fix**: Add `| grep -v "(deprecated)"` to both count and display greps in test.yml

### PR #1497 (ci-container-workflows)
- **Check**: All checks fail (`test`, `pre-commit`, `bats`, `integration`)
- **Root cause**: Workflows use `container: image: ghcr.io/.../scylla-ci:latest` — image doesn't exist yet
- **Fix**: Can only be resolved after PR #1494 merges and ci-image.yml workflow runs to push image
- **Rebase conflict**: `test.yml` conflicted between composite `setup-pixi` action (main) vs inline steps (PR)
  - Resolved by keeping HEAD (composite action)
  - Python-based conflict resolution used (sed unsafe for `${{ }}` expressions)

## Execution Notes

- All 4 branches rebased to main in sequence (ci-image-workflow had clean rebase, others needed fixes)
- Used Python `str.replace()` for all file modifications involving `${{ }}` expressions
- GitHub Actions runners were heavily queued (29 queued, 0 in progress) — infrastructure issue, not code
- ci-image-workflow push was force-with-lease (diverged after rebase)
- ci-security-hardening: 3 commits total (original + 2 fix commits)
- ci-robustness: 2 commits total (original + 1 fix commit)
- ci-container-workflows: 1 commit (conflict-resolved rebase)

## Verification

Local tests confirm fixes:
- BaseRunMetrics grep returns 0 on ci-robustness branch
- 17/17 Docker layer ordering tests pass on ci-security-hardening branch
- ci/Containerfile exists on ci-image-workflow after rebase
- security.yml gitleaks section uses CLI approach