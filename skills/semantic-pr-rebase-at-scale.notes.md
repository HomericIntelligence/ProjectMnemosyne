# Session Notes: Semantic PR Rebase at Scale

## Date: 2026-03-17

## Session Summary

After merging PR #4902 (systemic CI fix for pre-commit, workflows, justfile) to main,
86 open PRs needed rebase. 73 of those had CI failures from the stale branches.

The plan: launch 8 parallel Sonnet sub-agents in worktree isolation, each handling ~9 PRs.
Each agent reads the linked issue context before resolving conflicts to preserve PR intent.

## Key Decisions

1. **Sonnet over Opus** — rebase is mechanical work, doesn't need deep reasoning
2. **Worktree isolation** — required for parallel git operations (can't share working tree)
3. **Semantic resolution** — user explicitly asked "don't blindly resolve conflicts"
4. **Background agents** — all 8 launch simultaneously, report when done

## Conflict Patterns Identified

Most conflicts will be in 4 files that #4902 changed:
- `.pre-commit-config.yaml` — hook fixes (always accept main)
- `.github/workflows/pre-commit.yml` — inline matmul check (always accept main)
- `.github/workflows/comprehensive-tests.yml` — NATIVE=1 fix (always accept main)
- `justfile` — notes/ exclusion (always accept main)

For PR-specific source files, the agent must preserve the PR's changes while
incorporating structural changes from main.

## Safety Net Constraints

- `git checkout --ours` blocked (positional args)
- `git restore --ours` blocked (discards changes)
- `git branch -D` blocked (destructive)
- `git worktree remove --force` blocked (destructive)

Workarounds: edit conflict markers manually, use worktree remove without --force,
ask user to run branch deletion commands.

## Memory Created

- `feedback_semantic_merge.md` — "Don't blindly resolve conflicts; read issue context
  and merge semantically"

## Related PRs

- #4902 — systemic CI fix (merged to main, triggered the rebase need)
- #4900 — blog PR (merged earlier in session)
- #4897 — fix branch PR (rebased in session)
- 73 PRs needing rebase (batched across 8 agents)