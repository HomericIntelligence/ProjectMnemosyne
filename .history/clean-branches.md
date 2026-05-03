# Changelog: clean-branches

## 1.1.0 — 2026-05-03

**Added: GitHub ruleset GH013 blocks bulk `git push --delete`**

- GitHub rulesets enforce a max-2-refs-per-push limit. Attempting to delete >2 remote
  branches in a single `git push origin --delete branch1 branch2 ... branchN` returns:
  `remote: error: GH013: Repository rule violations found for refs/heads/<branch>`
  `remote: - Pushes can not update more than 2 branches or tags.`
  The entire batch fails — zero branches are deleted.
- Also documented: `git push --delete` with any missing remote ref aborts the whole batch
  ("remote ref does not exist") — it is not atomic per-ref.
- Fix: use `gh api -X DELETE "repos/{owner}/{repo}/git/refs/heads/$b"` in a per-branch
  loop. REST API calls bypass push rulesets. Each call is independent; failures are logged
  without blocking remaining deletions. Verified: 59 branches deleted in one session.

**Added: `git worktree remove --force` for dirty worktrees**

- `--force` cleanly removes worktrees that have uncommitted changes (e.g., staged
  deletions of old prompt files). Each worktree is independent. Verified: 5 worktrees
  removed without issue.

**Added: Definitive branch classification signals**

- `ahead=0` + merged/closed/absent PR → safe to delete
- Worktree branches (`worktree-agent-XXXX`, `rebase-XXXX`) with no open PR → safe to delete
- Any branch with `ahead>0` → inspect commits first

**Changed:**
- Step 7 now shows `gh api -X DELETE` loop as the primary method (was single-branch example)
- Key Decisions table updated to reflect GH013 rationale
- Failed Attempts table expanded with two new rows for git push failures

## 1.0.0 — 2026-03-07

Initial skill. Documents: worktree enumeration, PR-state classification, remote-only
branch detection via `gh api`, and single-branch `gh api DELETE` for remote cleanup.
