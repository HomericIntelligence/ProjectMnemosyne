---
name: org-wide-planned-issue-implementation-swarm
description: "Org-wide swarm that implements every open GitHub issue already carrying a `# Implementation Plan` comment across all ~12 HomericIntelligence repos, one signed auto-merge PR per issue, at high parallelism. Use when: (1) implementing the entire planned-issue backlog across many HomericIntelligence repos in one session, (2) the 'has a plan' signal is a `# Implementation Plan` issue comment (not the GitHub `planning` label), (3) deciding whether per-repo dispatcher sub-agents can spawn their own implementer sub-agents (they cannot), (4) deduplicating PRs against already-open issue PRs without substring false positives, (5) arming squash auto-merge org-wide where rebase-merge is disabled, (6) telling implementer agents to reconcile a stale plan against current code."
category: architecture
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - org-wide
  - multi-repo
  - implementation-plan-comment
  - myrmidon
  - swarm
  - l0-fan-out
  - sub-agent-tool-limit
  - pr-dedup
  - closing-keywords
  - squash-auto-merge
  - signed-commits
  - plan-reconciliation
  - homeric-intelligence
---

# Org-Wide Planned-Issue Implementation Swarm (HomericIntelligence)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | Implement every open GitHub issue that already carries a `# Implementation Plan` comment across all ~12 HomericIntelligence repos, producing one signed, squash-auto-merge PR per issue at high parallelism |
| **Outcome** | Detection + dedup + L0 fan-out model proven; pilot of ~51 issues across 5 small repos completed with signed squash-auto-merge PRs. 430 issues carried plans across 12 repos |
| **Verification** | verified-local — PRs created and signature-verified (REST `verification.verified == true`), auto-merge armed (`--auto --squash`); full org-wide CI completion was NOT all observed in-session |

## When to Use

- Implementing the entire **planned-issue** backlog across all HomericIntelligence repos in one session (one PR per issue)
- The "issue has a plan" signal you need is a `# Implementation Plan` **comment** authored in a prior planning pass — NOT the GitHub `planning` label (only ~1 issue ever had the label)
- Designing the fan-out and you must decide whether per-repo dispatcher sub-agents can spawn their own implementer sub-agents (they cannot — only the top-level session has the Agent/Task tool)
- Deduplicating against already-open PRs without `in:body #N` substring false positives (`#4` matching `#44`/`#42`)
- Arming auto-merge org-wide where rebase-merge is disabled (must use `--squash`)
- Instructing implementer agents to EXECUTE a plan but reconcile divergences when the plan predates a refactor

## Verified Workflow

### Quick Reference

```bash
# --- Session start (once): warm gpg-agent for signed commits ---
export GPG_TTY=$(tty)
echo test | gpg --batch --yes --pinentry-mode loopback -as -o /dev/null

# --- Detect "has a plan": issue has a `# Implementation Plan` comment (case-insensitive) ---
gh issue view <N> --repo <owner>/<repo> --json comments \
  --jq '[.comments[] | select(.body | test("(?i)# Implementation Plan"))] | length'
# > 0  => this issue carries a plan; queue it for implementation.
# NOTE: do NOT rely on the `planning` GitHub label — only ~1 issue org-wide had it.

# --- PR dedup: parse closing keywords from OPEN PR bodies (NOT substring search) ---
gh pr list --repo <owner>/<repo> --state open --json number,body \
  --jq '[.[].body | scan("(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\\s+#(\\d+)")] | flatten | unique'
# Skip any issue whose number appears in this list (a PR already closes it).
# Do NOT use:  gh pr list --search "in:body #N"  -> substring false positives.

# --- Confirm org merge policy before arming auto-merge ---
gh api repos/<owner>/<repo> \
  --jq '{rebase:.allow_rebase_merge,squash:.allow_squash_merge,auto:.allow_auto_merge}'
# All 12 HI repos: rebase=false, squash=true, auto=true, required reviews=0.

# --- Arm auto-merge (squash, NOT rebase) ---
gh pr merge <PR#> --auto --squash --repo <owner>/<repo>

# --- Authoritative signature verification (REST, not the GraphQL commits field) ---
gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified   # expect: true
gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.reason      # expect: "valid"
```

### Detailed Steps

**Step 0 — Session prep (L0 / top-level session).**
Export `GPG_TTY` and pre-warm gpg-agent ONCE so every later signed commit succeeds without an
interactive pinentry. Confirm org merge policy: all 12 HI repos disable rebase-merge
(`allow_rebase_merge=false`, `allow_squash_merge=true`, `allow_auto_merge=true`, required
reviews = 0). Branch protection requires CI checks but 0 approvals, so a green PR with auto-merge
armed merges itself.

**Step 1 — TRIAGE per repo (read-only; safe for sub-agents).**
You MAY dispatch one read-only "dispatcher" agent per repo to TRIAGE: for each open issue,
detect whether it carries a `# Implementation Plan` comment, and build the per-repo dedup set of
already-closed issue numbers. Dispatcher agents do triage ONLY — they return a list of
implementable issues. They must NOT try to spawn implementers (see Failed Attempts).

Detection (per issue): count comments matching case-insensitive `# Implementation Plan`. Dedup:
collect closing-keyword issue numbers from open PR bodies (see Quick Reference) and exclude them.

**Step 2 — L0 FANS OUT THE IMPLEMENTERS ITSELF, IN WAVES.**
The top-level (L0) session — not the dispatcher sub-agents — spawns the implementer agents,
because sub-agents have no Agent/Task tool and cannot create a second level of agents. Spawn
implementers in waves with:

- `run_in_background: true`
- `isolation: "worktree"`
- `model: "sonnet"`

One implementer per issue. Branch each worktree from FRESH `origin/main`
(`git fetch origin main` then create the worktree/branch off `origin/main`), never from a
submodule's pinned detached HEAD.

**Step 3 — Implementer agent contract.**
Each implementer must:
1. Read the issue's `# Implementation Plan` comment.
2. EXECUTE the plan — but RECONCILE divergences against current code (plans predate refactors:
   wrong ADR numbers, a Docker `--filter id="$cid"` quoting bug, phantom "already done"
   verdicts). Document every reconciliation in the PR body.
3. Commit signed: `git commit -S` (gpg-agent already warm from Step 0).
4. Open one PR with a closing keyword on its own line: `Closes #<N>`.
5. Arm auto-merge: `gh pr merge <PR#> --auto --squash` (NEVER `--rebase`).

**Step 4 — Verify (L0).**
Do NOT read the sub-agent transcript `.output` file via shell to gauge progress — it overflows
context. Rely on task-completion notifications. For each finished PR, verify signature via REST:
`gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified` == `true` and
`.reason` == `"valid"`. Squash-merge commits are GitHub-signed automatically; the GraphQL
`commits[].signature.state` field can read `null` even when the commit is validly signed — REST
is authoritative.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Two-level swarm (dispatcher sub-agents spawn implementers) | Documented myrmidon "dispatcher-per-repo → implementers" two-level fan-out | Sub-agents have no Agent/Task tool at the second level — they cannot spawn their own sub-agents | Per-repo dispatcher agents do read-only TRIAGE only; the L0 session itself fans out the implementers, in waves |
| Use the GitHub `planning` label as the "has a plan" signal | Filtered issues by the `planning` label | Only ~1 issue org-wide carried the label; the real planning pass wrote a `# Implementation Plan` comment, not a label | Detect via comment body: `[.comments[]\|select(.body\|test("(?i)# Implementation Plan"))]\|length > 0` |
| `gh pr list --search "in:body #N"` for PR dedup | Searched open PR bodies for the literal issue reference | Substring match gives false positives: `#4` matches `#44` and `#42`, so unrelated issues looked "already covered" | Parse closing keywords with a regex: `scan("(?i)(?:close[sd]?\|fix(?:e[sd])?\|resolve[sd]?)\\s+#(\\d+)")`, flatten, unique |
| `gh pr merge --auto --rebase` (per myrmidon-swarm template) | Armed auto-merge with `--rebase` as the skill template suggests | All 12 HI repos disable rebase-merge (`allow_rebase_merge=false`); `--rebase` never arms auto-merge | Always `--auto --squash`; verify merge policy first via `gh api repos/<owner>/<repo>` |
| Reading the sub-agent transcript `.output` file to check progress | `cat`/tail the background agent's transcript file from the shell | The transcript overflows the L0 context window | Rely on task-completion notifications, not raw transcript reads |
| Branching from a submodule's pinned detached HEAD | Created the worktree/branch from current `HEAD` inside an Odysseus submodule | The pin is a stale detached HEAD, not latest main — implementers built on old code | Always `git fetch origin main`, then branch/worktree from `origin/main` |
| Treating stale plans as ground truth | Implementers executed plan steps verbatim | Plans predated refactors (wrong ADR numbers, a Docker `--filter id="$cid"` quoting bug, phantom "already done" verdicts) | Implementers must EXECUTE but RECONCILE divergences against current code and document them in the PR body |
| Trusting GraphQL `commits[].signature.state` for signing | Checked the PR's GraphQL commit signature field | It can read `null` even when the commit is validly signed | Authoritative check is REST `gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified` (expect `true`, reason `"valid"`) |

## Results & Parameters

**Implementer agent dispatch parameters (L0 spawns these):**

```text
run_in_background: true
isolation:         worktree
model:             sonnet
fan-out level:     L0 ONLY (sub-agents cannot spawn sub-agents)
one implementer per issue; branch from fresh origin/main
commit:  git commit -S        (gpg-agent pre-warmed at session start)
PR body: Closes #<N>          (closing keyword on its own line)
merge:   gh pr merge <PR#> --auto --squash   (NEVER --rebase)
```

**Org merge policy (all 12 HomericIntelligence repos):**

```json
{ "allow_rebase_merge": false, "allow_squash_merge": true, "allow_auto_merge": true, "required_approving_review_count": 0 }
```

Branch protection requires CI checks but 0 approvals → a green PR with auto-merge armed merges automatically.

**Scale data — issues carrying a `# Implementation Plan` comment (430 total across 12 repos):**

| Repo | Planned issues |
|------|----------------|
| ProjectArgus | 112 |
| ProjectCharybdis | 59 |
| ProjectHermes | 52 |
| ProjectAgamemnon | 52 |
| ProjectTelemachy | 33 |
| ProjectOdyssey | 31 |
| ProjectProteus | 26 |
| ProjectNestor | 21 |
| ProjectKeystone | 16 |
| AchaeanFleet | 12 |
| ProjectScylla | 9 |
| Odysseus | 7 |
| ProjectHephaestus | 0 |

Pilot: ~51 issues across 5 small repos completed with signed squash-auto-merge PRs.

**Expected outputs:**

```bash
# plan-comment detection
$ gh issue view 123 --repo HomericIntelligence/ProjectArgus --json comments \
    --jq '[.comments[]|select(.body|test("(?i)# Implementation Plan"))]|length'
1

# signature verification (post-merge / post-commit)
$ gh api repos/HomericIntelligence/ProjectArgus/commits/<sha> --jq .commit.verification.verified
true
$ gh api repos/HomericIntelligence/ProjectArgus/commits/<sha> --jq .commit.verification.reason
valid
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| 12 HomericIntelligence repos | 2026-05-29 org-wide planned-issue swarm | 430 plan-carrying issues detected; pilot of ~51 issues across 5 small repos merged via signed squash-auto-merge PRs; L0-only fan-out + closing-keyword dedup + plan reconciliation proven (verified-local) |
