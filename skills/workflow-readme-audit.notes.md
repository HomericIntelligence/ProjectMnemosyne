# Session Notes: workflow-readme-audit

## Session Context

- **Date**: 2026-03-07
- **Repository**: ProjectOdyssey
- **Issue**: #3344 — "Add workflow count badge or comment tracking remaining duplication"
- **Branch**: `3344-auto-impl`
- **PR**: #3978

## What the Issue Asked For

> The `.github/workflows/README.md` exists but may not reflect the current state after the
> consolidation (3 workflows deleted, 1 added). Update the README to reflect the new workflow
> inventory, composite actions created, and any remaining duplication that was intentionally
> left (e.g. the 10 single-setup-pixi workflows not yet migrated).

The reference consolidation was PR #3149.

## Actual File State Found

22 workflow files on disk:

```text
benchmark.yml
claude-code-review.yml
claude.yml
comprehensive-tests.yml
coverage.yml
docker.yml
docs.yml
link-check.yml
mojo-version-check.yml
notebook-validation.yml
paper-validation.yml
pre-commit.yml
readme-validation.yml
release.yml
script-validation.yml
security.yml
simd-benchmarks-weekly.yml
test-agents.yml
test-data-utilities.yml
test-gradients.yml
type-check.yml
validate-configs.yml
```

## What the Old README Had (Before This Session)

The old README documented these workflows:

| Listed in README | Exists on Disk? |
| ------------------ | ----------------- |
| `unit-tests.yml` | NO — deleted in #3149 |
| `integration-tests.yml` | NO — deleted in #3149 |
| `comprehensive-tests.yml` | YES |
| `test-gradients.yml` | YES |
| `test-data-utilities.yml` | YES |
| `script-validation.yml` | YES |
| `validate-configs.yml` | YES |
| `test-agents.yml` | YES |
| `pre-commit.yml` | YES |
| `security-scan.yml` | NO — renamed to `security.yml` |
| `dependency-audit.yml` | NO — merged into `security.yml` |
| `mojo-version-check.yml` | YES |
| `link-check.yml` | YES |
| `simd-benchmarks-weekly.yml` | YES |

Undocumented workflows (existed on disk but not in README):
- `benchmark.yml`
- `claude.yml`
- `claude-code-review.yml`
- `coverage.yml`
- `docker.yml`
- `docs.yml`
- `notebook-validation.yml`
- `paper-validation.yml`
- `readme-validation.yml`
- `release.yml`
- `type-check.yml`

## Inline setup-pixi Duplication

13 workflows use `prefix-dev/setup-pixi` inline (no composite action exists yet):

```
benchmark.yml
comprehensive-tests.yml
mojo-version-check.yml
paper-validation.yml
pre-commit.yml
readme-validation.yml
release.yml
script-validation.yml
security.yml
simd-benchmarks-weekly.yml
test-data-utilities.yml
test-gradients.yml
type-check.yml
```

The issue mentioned "10 single-setup-pixi workflows" but the actual count was 13.
Always run `grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml | wc -l` to get the real count.

## markdownlint Errors Encountered

```text
.github/workflows/README.md:59:121 MD013/line-length Line length [Expected: 120; Actual: 125]
.github/workflows/README.md:347:1 MD029/ol-prefix Ordered list item prefix [Expected: 1; Actual: 4; Style: 1/2/3]
.github/workflows/README.md:348:1 MD029/ol-prefix Ordered list item prefix [Expected: 2; Actual: 5; Style: 1/2/3]
.github/workflows/README.md:349:1 MD029/ol-prefix Ordered list item prefix [Expected: 3; Actual: 6; Style: 1/2/3]
```

Fix 1: Shorten a blockquote note from 125 chars to ≤120.
Fix 2: The "Scanning Jobs (scheduled weekly)" list continued numbering (4/5/6) from the
"Scanning Jobs (PR/push)" list above it. Reset to 1/2/3 since they are separate lists.

## Files Changed

```text
.github/workflows/README.md | 477 ++++++++++++++++++++++++++++++-----
 1 file changed, 315 insertions(+), 162 deletions(-)
```

## Commit Hash

`a5901eeb` (on branch `3344-auto-impl`, PR #3978)