# Session Notes: haiku-wave-pr-remediation

## Session Date
2026-03-15

## Objective
Fix 49 failing PRs across 4 HomericIntelligence repos using wave-based haiku sub-agents.

## Repos Covered
- ProjectOdyssey: 46 failing PRs (Mojo AI research platform)
- ProjectScylla: 1 failing PR (#1491, ruff failures)
- ProjectMnemosyne: 1 failing PR (#674, missing YAML frontmatter)
- ProjectKeystone: 1 failing PR (#81, pre-existing CVEs — deferred)

## Root Cause Distribution (Odyssey)
- ruff format/check: ~8 PRs
- mojo format parity (comptime parse): ~18 PRs
- deprecated `List[Int](n)` syntax: ~3 PRs
- missing CI matrix entry: ~2 PRs
- Transient JIT crash: ~8 PRs
- validate-test-file-sizes new hook: ~20 PRs (required remediation)
- `just` not in PATH: 1 PR (#4574)

## Key Discoveries

### 1. snap ruff sandbox
Snap-installed ruff cannot access `/tmp`. Must use `pixi run ruff`.

### 2. mojo format comptime parity
Local Mojo 0.26.1 exits with code 123 on `comptime_assert_stmt` syntax.
The compat script silently passes (exits 0), so local format is skipped.
CI's mojo format succeeds. Workaround: copy from already-CI-formatted branch.

### 3. validate-test-file-sizes new hook
Introduced in PRs #4741/#4746. Flags oversized test files.
20 pre-existing files violated this and required remediation.

### 4. just not in PATH for pre-commit
PR #4574 introduced `entry: just check-matmul-calls` which fails in CI because
`just` is not on PATH in the pre-commit execution environment.
Fix: `entry: pixi run just check-matmul-calls`.

### 5. Safety Net blocks force operations
`git worktree remove --force` and `git reset --hard` are blocked by the Safety Net plugin.
Workaround: use `git worktree remove` (without --force), or create fresh worktree at new path.

### 6. GraphQL timeout on bulk status queries
`gh pr list --json statusCheckRollup` times out with 504 when 40+ CI runs are active.
Use: `gh pr checks <N>` per-PR, or `gh api .../actions/runs?branch=X` REST endpoint.

### 7. Keystone #81 pre-existing failures
The Dependabot GitHub Actions bump PR had pre-existing clang-format violations and
Docker image CVEs unrelated to the Dependabot change. Deferred to separate issue.

## Agent Wave Structure Used
- Wave 0: 3 diagnosis agents (1 per failure category sample)
- Wave 1: 3 agents (non-Odyssey repos: Scylla, Mnemosyne, Keystone)
- Wave 2-8: Groups of ~5 Odyssey agents per wave, background parallel
- Total haiku agents spawned: ~35 across all waves

## PRs That Needed Manual Intervention
- PR #4723: List[Int]() syntax in test_shape_noncontiguous_values.mojo (handled directly)
- PR #4574: just not in PATH — both .pre-commit-config.yaml AND pre-commit.yml needed fixing
- PR #4530: Missing test_int_bitwise_not.mojo in CI matrix
- PR #4730: Missing test_setitem_view.mojo in CI matrix + List[Int]() fixes