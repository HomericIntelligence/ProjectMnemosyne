# Clean Branches — Session Notes (2026-03-07)

## Context

ProjectScylla, post wave-execution cleanup. After multiple parallel waves of auto-impl PRs,
remote branches accumulated without local counterparts.

## Branches Found

| Branch | Local | Remote | PR | PR State | Action |
|--------|-------|--------|----|----------|--------|
| `1359-auto-impl` | No | Yes | #1392 | MERGED | Deleted remote |
| `1395-auto-impl` | No | Yes | #1444 | MERGED | Deleted remote |
| `998-auto-impl` | No | Yes | #1172 | MERGED | Deleted remote |
| `1427-auto-impl` | Yes | Yes | #1452 | OPEN | Kept |
| `1431-auto-impl` | Yes | Yes | none | — | Kept (issue #1431 open) |
| `1434-auto-impl` | Yes | Yes | #1460 | OPEN | Kept |
| `1436-auto-impl` | Yes | Yes | #1462 | OPEN | Kept |
| `skill/ci-cd/bounded-regex-tier-label-check` | Yes | No | none | — | Kept (points to main) |

## Worktrees

Only `main` worktree existed — no worktree cleanup needed.

## Commands Run

```bash
# Enumerate local
git worktree list --porcelain
git branch -vv

# Get repo name
gh repo view --json nameWithOwner -q .nameWithOwner
# => HomericIntelligence/ProjectScylla

# List remote branches
gh api repos/HomericIntelligence/ProjectScylla/git/refs/heads --paginate --jq '.[].ref' | sed 's|refs/heads/||' | grep -v '^main$'
# => 1359-auto-impl, 1395-auto-impl, 1427-auto-impl, 1431-auto-impl, 1434-auto-impl, 1436-auto-impl, 998-auto-impl

# Classify via PR state
gh pr list --head 1359-auto-impl --state all --json number,state,title
# => [{"number":1392,"state":"MERGED","title":"refactor(e2e): ..."}]

# Verify merge ancestry (double-check)
git merge-base --is-ancestor origin/1359-auto-impl origin/main && echo MERGED
# => MERGED (for 1359, 1395, 998)

# Delete stale remotes
gh api --method DELETE "repos/HomericIntelligence/ProjectScylla/git/refs/heads/1359-auto-impl"
gh api --method DELETE "repos/HomericIntelligence/ProjectScylla/git/refs/heads/1395-auto-impl"
gh api --method DELETE "repos/HomericIntelligence/ProjectScylla/git/refs/heads/998-auto-impl"

# Prune
git worktree prune
git remote prune origin
# => [pruned] origin/1359-auto-impl, origin/1395-auto-impl, origin/998-auto-impl
```

## Interruption Note

The user interrupted a batch `gh issue view` call mid-flow. The lesson: checking issue state is
redundant when `gh pr list --state all` already returns `MERGED`. Do not add the issue-state
check unless there is literally no PR for the branch.

## 1431-auto-impl Special Case

Branch `1431-auto-impl` had no PR and was not merged into main. It had 2 commits beyond main:
- `310dcef1 chore(lock): regenerate pixi.lock after pyproject.toml change`
- `1e2169ad feat(complexity): lower max-complexity threshold from 12 to 10 in scylla/`

Issue #1431 ("Lower max-complexity threshold from 12 to 10 incrementally") was OPEN.
Branch was kept — active work in progress.
