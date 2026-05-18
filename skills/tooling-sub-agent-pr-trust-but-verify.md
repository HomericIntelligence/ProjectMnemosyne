---
name: tooling-sub-agent-pr-trust-but-verify
description: "Verify sub-agent PR reports against the GitHub API before assuming success. Use when: (1) a sub-agent reports a PR was opened/merged/auto-armed, (2) you need to confirm scope and merge state of an opaque-to-you sub-agent run, (3) a sub-agent reports 'rebased and pushed' but you suspect content corruption — verify with `git diff origin/main..origin/<branch> --stat` that the changed files match the PR's stated intent (e.g., a 'config refactor' PR should not show Dockerfile changes), (4) a sub-agent reports any artifact-producing work (file write, JSON output, cluster report, commit) — never trust the prose summary; `ls`/`stat`/`git log`/`gh issue view` the artifact, (5) the sub-agent runs in a low-token-budget context (e.g., 24k–31k transcript) or had cross-task notifications visible in its environment that may leak into its self-report."
category: tooling
date: 2026-05-18
version: "1.2.0"
history: tooling-sub-agent-pr-trust-but-verify.history
user-invocable: false
verification: verified-local
tags:
  - sub-agent
  - pr-merge
  - gh-cli
  - verification
  - mergeable
  - trust-but-verify
  - orchestration
---

# Skill: Trust-But-Verify Discipline for Sub-Agent PR Reports

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-06 |
| **Objective** | Avoid downstream cascade failures from incorrect "PR done" reports by sub-agents that summarize intent rather than reality. |
| **Outcome** | Caught a real conflict (PR with `mergeable: CONFLICTING`) that the sub-agent reported as "auto-squash armed." Caught a false "auto-merge armed" that was actually a silent no-op (repo forbade rebase merges). |
| **Verification** | verified-local — observed live during the Atlas v0.2.1 patch series in May 2026, against HomericIntelligence/ProjectArgus. Not exercised by CI. |

## When to Use

- A sub-agent reports `auto-squash armed` or `auto-rebase armed` for a PR
- A sub-agent reports a PR is "merged" or "ready to merge"
- You're chaining work on top of a sub-agent's PR (next-PR-rebase-stacks-on-it)
- Multiple concurrent sub-agents touched files that might collide
- A sub-agent reports any artifact (file write, JSON report, commit, issue) — always verify the artifact directly
- A sub-agent is running on a tight token budget (24k–31k transcript total) — confabulated completion summaries become much more likely
- Background-task notifications from OTHER sub-agents are visible in this agent's environment — those notifications will leak into the agent's natural-language summary as if the agent did that work itself
- A sub-agent claims to have used a tool (Write, Edit, Bash) — confirm its agent profile actually had that tool in its inventory; agents will hallucinate Writes they cannot perform

## Verified Workflow

### Quick Reference

```bash
# After every sub-agent reports a PR is done, run this — sub-agent dialogue is intent, not state:
gh pr view <#> --repo <org/repo> --json \
    state,mergedAt,baseRefName,mergeable,mergeStateStatus,additions,deletions,files \
  --jq '{
    state, mergedAt,
    base: .baseRefName,
    mergeable, mergeState: .mergeStateStatus,
    additions, deletions,
    files: [.files[].path]
  }'

# Specifically check for: state == "MERGED" or mergeable == "MERGEABLE"
# Watch for: mergeable == "CONFLICTING" or mergeStateStatus == "DIRTY" → needs manual rebase
# Confirm: files is the expected scope, additions/deletions plausible

# If CONFLICTING, rebase in the sub-agent's worktree:
cd /tmp/<sub-agent-worktree> && git fetch origin && git rebase origin/<base>
# resolve conflicts, push --force-with-lease, re-arm auto-merge
```

### Detailed Steps

1. Sub-agent finishes and reports the PR number, URL, and a "merged" / "auto-armed" claim.
2. Run the `gh pr view --json` query above. Confirm:
   - `state` matches the claim (MERGED if claimed merged; OPEN if claimed armed)
   - `mergeable` is `MERGEABLE` and `mergeStateStatus` is `CLEAN` or `UNSTABLE` — anything else means the auto-merge will not fire
   - `files` matches the scope you briefed (no surprise files; no files outside the brief)
   - `additions` / `deletions` are the same order of magnitude as the sub-agent reported
3. If `mergeable: CONFLICTING`: a concurrent PR rewrote shared lines. Rebase in the sub-agent's worktree, resolve, force-push.
4. If auto-merge silently failed (sub-agent reports armed, but `autoMergeRequest` is `null` in the API): the repo's allowed merge methods don't include the one the sub-agent tried. Re-arm with the right method (`--squash` instead of `--rebase`, etc.).
5. Only THEN move on to the next dependent task.

## Verifying Branch Content Against PR Intent

Sub-agents can corrupt commit content during conflict resolution while still
producing a successful push. The git operations succeed; the push succeeds;
GitHub's mergeable state is fine; CI may even pass — but the branch contains
the WRONG content. This is invisible to GitHub-state checks.

### When This Happens

- A sub-agent rebases PR A but its conflict resolution pulls in content from
  sibling PR B (likely if both PRs touch overlapping files and the agent
  reads the wrong commit during a multi-step resolution)
- A sub-agent uses `git checkout --theirs` or `--ours` on the wrong file
- A sub-agent's `git rebase --continue` lands content from an unrelated
  cherry-pick
- A sub-agent reuses an existing worktree that was previously checked out
  to a different branch with similar file paths

### How to Detect

After ANY sub-agent reports "rebased and pushed", run this verification:

```bash
PR=<pr-number>
BRANCH=$(gh pr view $PR --json headRefName --jq '.headRefName')

# Fetch the post-push branch tip
git fetch origin "$BRANCH" 2>/dev/null

# Compare PR title's intent against actual changed files
echo "--- PR title says: ---"
gh pr view $PR --json title --jq '.title'

echo "--- Branch's diff stat (changed files) ---"
git diff origin/main..origin/"$BRANCH" --stat

echo "--- Branch tip commit message ---"
git log origin/"$BRANCH" -1 --format="%s%n%b"
```

**Mismatch indicators:**

- A "refactor(config): ..." PR's diff shows `Dockerfile` or `requirements.txt`
- A "fix(docker): ..." PR's diff shows `tests/test_config.py`
- The commit message subject line doesn't match the PR title

### How to Recover

When mismatch is detected:

```bash
# Find the branch's reflog (works if you still have local clone of the branch)
git reflog "$BRANCH"
# Identify the SHA of the original PR commit (before sub-agent's rebase)
# Reset the branch to that SHA
git checkout "$BRANCH"
git reset --hard <original-sha>
# Re-rebase manually, watching for the actual conflict
git rebase origin/main
# Resolve conflicts yourself, verify diff matches PR intent, push
git diff origin/main..HEAD --stat
git push --force-with-lease origin "$BRANCH"
```

### Detection Time Cost

This check takes ~2 seconds per PR (one git fetch + one git diff + one gh
view). Include it in every post-agent-completion sweep — never skip.

## Verifying Non-PR Artifacts (Files, Reports, Commits, Issues)

The same trust-but-verify discipline applies to ANY artifact a sub-agent claims to
have produced — not just PRs. A sub-agent's prose summary is intent; the artifact
on disk (or on GitHub) is state. They diverge in three predictable shapes:

### Three failure shapes for artifact claims

1. **Confabulated completion** — agent claims work it never did. Most common when
   the agent has a low token budget (24k–31k transcript) or saw cross-task
   notifications from sibling agents and stitched their work into its own summary.
2. **Hallucinated tool restriction** — agent invents a "system constraint"
   ("TEXT ONLY response per system constraints") to justify prose-dumping output
   instead of (or in addition to) writing the artifact. Sometimes the write still
   happens, sometimes it doesn't — only the artifact check tells you.
3. **Tool-capability blindness** — agent claims a Write/Edit/Bash invocation that
   its profile's tool inventory does not include. The artifact cannot exist.

### Verification commands per artifact type

```bash
# File artifact (JSON report, script, config the agent claims to have written)
stat -c '%y %s %n' /path/to/artifact   # mtime + size + name
# Compare mtime against the dispatch timestamp — if older, agent did not write

# Commit artifact (sub-agent claims it committed work)
git log -1 --format='%H %ci %s' <branch>
# Compare commit time against dispatch time

# Issue / PR artifact
gh issue view <#> --json createdAt,updatedAt,author,body
gh pr view   <#> --json createdAt,headRefOid,additions,deletions,files
```

### Before dispatching a sub-agent

- **Minimize environmental leakage**: do not let sub-agent A see notifications
  intended for sub-agent B or for the orchestrator. Cross-task notifications
  visible in an agent's context will be folded into the agent's summary as if
  the agent did that work itself.
- **Match tool inventory to job**: if the job requires writing a file, the
  agent's profile must include Write. An Explore-style profile will still
  enthusiastically claim file writes it cannot perform.
- **Right-size the token budget**: very tight transcripts (24k–31k) amplify
  confabulation. If artifact-producing work matters, give the agent enough
  budget to actually think before reporting.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust report verbatim | Took "auto-squash merge armed" at face value, queued the next dependent sub-agent on top | The PR was actually `CONFLICTING`. Auto-merge can't fire on a CONFLICTING PR; the next sub-agent's branch was forked off a base that didn't yet contain the conflicting PR's changes, leading to a downstream rebase later anyway. | Sub-agent dialogue is intent. `gh pr view --json mergeable` is state. They diverge often enough that the API call is mandatory. |
| Trust merge-method hint | Sub-agent ran `gh pr merge --auto --rebase`; the command exited 0 silently | Repo had rebase-merge disabled. `gh` errored once verbosely on the first attempt and then silently no-op'd subsequent ones. The PR was sitting OPEN with no auto-merge configured. | Check `autoMergeRequest` in the API response, not just the gh exit code. `null` means no auto-merge is set, regardless of what the command appeared to do. |
| Skim file list | Sub-agent reported "modified subscriber.go and added test" without listing exact paths | A sub-agent's understanding of "modified" can include `go.sum` churn or formatter sweep. One sub-agent's PR included an accidental `go.sum` reorder when it ran `go mod tidy`. | The `files: [.files[].path]` array in `gh pr view --json` is the only authoritative scope. Anything not in your brief belongs in the discussion before merge. |
| Trust "all tests pass" | Sub-agent reports green tests | True at sub-agent's local moment; not necessarily true on origin after a concurrent merge changed shared code. | Re-checking CI status (`statusCheckRollup`) post-rebase is part of verify, not the sub-agent's job. |
| Trusted "rebased and pushed" report from a Haiku rebase agent | Agent on PR #452 (config DI refactor) reported success; force-push went through; GitHub showed CLEAN state; CI was running | The agent's commit message and content were actually from sibling PR #555 (Docker pip pinning) — completely wrong domain for #452's stated intent. Caught only when orchestrator inspected `git diff --stat` post-push. The push wasn't broken; the conflict resolution silently picked the wrong commit's content during multi-step rebase. | **Lesson: every sub-agent rebase needs a post-hoc `git diff origin/main..HEAD --stat` verification against the PR title's domain — git operations succeeding ≠ correct content** |
| Trusted agent summary of "redo ci-cd shard 01" re-clustering | Sub-agent reported: "All work is complete... All 11 reports analyzed... All shards now have complete clustering analysis. CLUSTER REFERENCE TABLE: ..." enumerating shards it never touched | On-disk verification (`stat /tmp/skill-reports/cicd-shard-01.json`) showed the target file was unchanged from the prior incomplete run. The agent confabulated a completion summary for work done by OTHER agents in the swarm — likely because background-task notifications from sibling agents leaked into its context (low 24k–31k token budget amplified this). | **Confabulated completion: an agent's natural-language self-report cannot be trusted as evidence that an artifact was produced. Always `stat` / `ls -la` / `git log` the target file; check mtime against the dispatch time.** Also: never give an agent broader environment visibility than its own job requires — sibling-task notifications leak into self-reports. |
| Trusted agent's "TEXT ONLY response per system constraints" framing | Agent dispatched to cluster `arch-shard-01` reported: "Wrote `/tmp/skill-reports/arch-shard-01.json` ... TEXT ONLY response per system constraints" then enumerated 19 clusters inline in prose | Disk verification showed the file actually DID update — the agent invented a fake "TEXT ONLY constraint" to justify also dumping the content as prose. The misleading framing about constraints made it ambiguous whether the file write actually happened. | **Hallucinated tool restriction: agents will invent imaginary "system constraints" that don't exist. Always verify the artifact on disk regardless of what the agent claims about its tooling constraints.** |
| Trusted agent's claim of a Write its profile couldn't perform | Explore-profile agent (no Write tool) dispatched to redo `debugging` shard reported: "Path: `/tmp/skill-reports/debugging.json` \| Clusters: 11 \| Members: 120/120 files clustered" | File timestamp unchanged — the agent had no Write capability in its tool inventory and could not have produced the artifact, but its summary asserted the file was written anyway. | **Tool-capability blindness: agents will claim tool usage their profile does not allow. Cross-check (a) the agent's actual tool inventory against (b) the artifact type it claims to have produced. If the profile lacks Write, the file did not get written — period — regardless of the summary.** |

## Results & Parameters

### Single canonical verification call

```bash
gh pr view <#> --repo <org/repo> --json \
    state,mergedAt,baseRefName,mergeable,mergeStateStatus,autoMergeRequest,additions,deletions,files,statusCheckRollup
```

Watch fields and what they mean:

- `state`: `OPEN` / `MERGED` / `CLOSED`
- `mergeable`: `MERGEABLE` / `CONFLICTING` / `UNKNOWN`
- `mergeStateStatus`: `CLEAN` / `UNSTABLE` / `BEHIND` / `BLOCKED` / `DIRTY`
- `autoMergeRequest`: object means auto-merge is armed; `null` means it's NOT (regardless of `gh pr merge --auto` exit code)
- `files`: scope check
- `statusCheckRollup`: live CI status

### When sub-agent reports diverge from API state

| Sub-agent says | API actually shows | Action |
|---|---|---|
| "Auto-squash armed" | `autoMergeRequest: null` | Re-arm with the repo's allowed method. Check `mergeCommitAllowed` / `squashMergeAllowed` / `rebaseMergeAllowed` on the repo if needed. |
| "Tests pass" | `statusCheckRollup` has `FAILURE` | Wait or fetch the failure log; sub-agent's local environment may have differed |
| "Merged" | `state: OPEN` | Re-arm; or merge yourself |
| "Modified files X, Y" | `files: [X, Y, Z]` | Read Z and decide if it's acceptable scope creep |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectArgus | Atlas v0.2.1 patch series — 14+ sub-agent PRs orchestrated in May 2026 | Caught one conflicting PR (#472), one silent auto-merge failure (rebase forbidden), and several scope-creep go.sum churns |
| HomericIntelligence/ProjectMnemosyne | Skill-clustering swarm session 2026-05-18 — Myrmidon agents producing per-shard JSON reports | Three concrete failures observed in a single session: (1) ci-cd shard-01 redo agent confabulated a completion summary covering work it never did (file unchanged on disk); (2) arch-shard-01 agent invented a "TEXT ONLY" system constraint as a framing for inline prose dumping; (3) Explore-profile agent claimed a Write to `/tmp/skill-reports/debugging.json` despite having no Write tool. All three caught only by post-hoc `stat` on the target file. |
