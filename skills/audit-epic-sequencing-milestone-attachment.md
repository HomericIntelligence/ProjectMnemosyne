---
name: audit-epic-sequencing-milestone-attachment
description: "Implement a GitHub audit epic that sequences remediation across many child issues in dependency order using GitHub milestones, wave structure, and verify-and-close patterns. Use when: (1) you have a completed strict audit with 20+ findings filed as child issues and need to coordinate their implementation order, (2) you need to attach all child issues to a GitHub milestone in bulk, (3) deciding wave dependency structure (Foundation → Critical → Hygiene), (4) closing child issues that are already fixed before implementing any PR, (5) batching Wave-3 hygiene items by co-located files to prevent merge conflicts, (6) verifying PR policy (body, auto-merge, signature) before declaring an epic done."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [audit, epic, milestone, remediation, wave-structure, gh-api, verify-and-close, batch-pr, dependency-order, file-target-verification, pr-policy, squash-merge]
---

# Audit Epic Sequencing and Milestone Attachment

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Coordinate remediation of 33 child issues from the ProjectProteus STRICT audit (#81) across three dependency waves using GitHub milestones and a structured `docs/audit-*/remediation-plan.md` |
| **Outcome** | Milestone created, all 33 children attached, wave structure documented, #87 verified-and-closed, `docs/audit-2026-04-28/remediation-plan.md` created, `CLAUDE.md` extended with agent checklist |
| **Scope** | GitHub issue tracking, milestone API, CLAUDE.md updates, docs wave plan |

## When to Use

- You are implementing a GitHub tracking/epic issue that resulted from a STRICT audit with 20+ child findings
- You need to attach many child issues to a milestone in a single loop
- You want to close a child issue that grep confirms is already fixed (no PR needed)
- You are designing Wave 1/2/3 dependency order for a remediation sprint
- You need to batch Wave-3 hygiene PRs by co-located files to avoid merge conflicts
- You need to verify three PR policy gates before declaring a child done
- The audit report cited a wrong file target (e.g., "jobs live in ci.yml") and you need to confirm the real location before touching code

## Verified Workflow

### Quick Reference

```bash
# 1. Create a GitHub milestone with a due date
gh api repos/OWNER/REPO/milestones \
  -f title="Audit Remediation 2026-04-28" \
  -f due_on="2026-08-01T00:00:00Z" \
  -f state=open
# Returns JSON — extract the milestone number:
MILESTONE_NUMBER=<n>

# 2. Attach ALL child issues to the milestone in a loop
for n in 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114; do
  gh issue edit "$n" --milestone "Audit Remediation 2026-04-28"
done

# 3. Verify-and-close: grep the repo before writing any PR
grep -nE 'uses: [^@]+@' .github/workflows/*.yml | grep -vE '@[0-9a-f]{40}'
# If output is empty → mutable pins already replaced → close immediately
gh issue close 87 -c "All action pins in .github/workflows/*.yml are already SHA-pinned (verified via grep 2026-06-19). No PR needed."

# 4. Confirm where CI jobs actually live (audit report may cite wrong file)
grep -rn "security\|gitleaks\|trivy\|scan" .github/workflows/ | grep "runs-on\|uses:"
# THEN: grep the specific job name the audit mentions
grep -n "gitleaks" .github/workflows/*.yml

# 5. Three PR policy checks before declaring a child done
#   a. PR body line: "Closes #N" appears alone on its own line
gh pr view N --json body --jq '.body' | grep -E '^Closes #[0-9]+'
#   b. Auto-merge enabled
gh pr merge N --auto --squash   # squash if rebase disabled on repo
#   c. All commits GPG/SSH signed
gh api graphql -f query='{ repository(owner:"OWNER",name:"REPO") { pullRequest(number:N) { commits(last:10) { nodes { commit { signature { isValid } } } } } } }'
```

### Detailed Steps

#### Step 1 — Treat the epic as a sequencer, not an implementer

The epic issue itself ships no code. Its job is:
- Create the GitHub milestone
- Attach all children
- Document the wave dependency graph in `docs/audit-*/remediation-plan.md`
- Update `CLAUDE.md` with an agent checklist
- Close any children that are already fixed

Each child ships its own PR. Link every child PR back to the epic with `Refs #<epic>` in the body.

#### Step 2 — Create the milestone via `gh api`

Use `gh api`, not `gh issue milestone create` (the latter does not exist in all gh versions):

```bash
gh api repos/OWNER/REPO/milestones \
  -f title="Audit Remediation 2026-04-28" \
  -f due_on="2026-08-01T00:00:00Z" \
  -f state=open
```

Note the milestone `number` from the JSON response (e.g., `"number": 5`). You need it if you want to attach by number rather than title. `gh issue edit --milestone` accepts the milestone title as a string.

#### Step 3 — Attach all children in a loop

```bash
for n in <space-separated child issue numbers>; do
  gh issue edit "$n" --milestone "Audit Remediation 2026-04-28"
done
```

Run this as a single shell loop — do NOT use parallel agent dispatching for `gh issue edit` calls. The GitHub API rate-limits concurrent writes.

#### Step 4 — Verify-and-close already-fixed issues

Before implementing any child issue, grep the repo to confirm it is not already fixed:

```bash
# Example: mutable action pins (#87)
grep -nE 'uses: [^@]+@' .github/workflows/*.yml | grep -vE '@[0-9a-f]{40}'
# Empty output → already fully SHA-pinned → close immediately
gh issue close 87 -c "All action pins verified SHA-pinned. No PR needed."
```

Only close as `completed` (default `gh issue close` behavior) when the fix is confirmed live on the default branch. If the fix is only in a PR branch, wait for the PR to merge.

#### Step 5 — Confirm actual file targets (anti-pattern: trusting the audit report)

Audit reports often cite approximate file paths. Before touching any file, grep to verify:

```bash
# Audit says "Gitleaks runs with continue-on-error in ci.yml" — verify:
grep -rn "continue-on-error" .github/workflows/
# Result shows the job is actually in _required.yml, NOT ci.yml
```

File an issue or update the `remediation-plan.md` with the corrected path BEFORE implementing.

#### Step 6 — Design the wave structure

Organize the 33+ children into three waves:

| Wave | Name | Contents | Gate |
| ------ | ------ | ---------- | ------ |
| 1 | Foundation | Test harness, security gates, branch protection, milestone, docs | No gate — run in parallel |
| 2 | Critical bugs | Bug fixes that each need a regression test under `tests/` | Wave 1 test harness must merge first |
| 3 | Hygiene | MINOR/NITPICK items batched by co-located files | No strict gate — can run in parallel after Wave 1 |

Document the wave graph in `docs/audit-*/remediation-plan.md` with a checkbox table:

```markdown
## Wave 1 — Foundation (target: YYYY-MM-DD)

| # | Issue | Title | PR | Status |
|---|-------|-------|----|--------|
| 1 | #88 | Add test harness | — | [ ] |
```

#### Step 7 — Batch Wave-3 items by co-located files

Wave-3 hygiene items are often NITPICK/MINOR and touch many different files. Merge conflicts are likely if each gets its own single-file PR. Batch them:

```
PR-A: justfile + pixi.toml hygiene items (#103, #104, #105)
PR-B: dagger/src/index.ts cleanup items (#106, #107)
PR-C: scripts/*.sh shellcheck fixes (#108, #109, #110)
...
```

Each PR in the batch still closes its specific issues with `Closes #N` lines in the body.

#### Step 8 — Update CLAUDE.md with agent checklist

Add an "Audit Remediation Tracking" section:

```markdown
## Audit Remediation Tracking

The 2026-04-28 STRICT audit (#81) is being remediated in three waves.
See `docs/audit-2026-04-28/remediation-plan.md` for current status.

Agents picking up an audit child issue MUST:
1. Read the audit context in #81 and the relevant child issue.
2. Confirm the file target listed in `remediation-plan.md` matches the
   actual file (grep to verify).
3. Link the child in the PR body via `Refs #81`.
4. Add a regression test under `tests/` for any bug fix.
5. Tick the matching checkbox in `docs/audit-2026-04-28/remediation-plan.md`.
```

#### Step 9 — Three PR policy checks before declaring done

For every PR (your own and Wave-N children) run all three checks:

1. **Closes line**: `gh pr view N --json body --jq '.body' | grep -E '^Closes #[0-9]+'`
2. **Auto-merge**: `gh pr merge N --auto --squash` (use `--squash` if rebase merging is disabled on the repo — check under repo Settings → General → Allow merge commits)
3. **Signed commits**: Use the GraphQL query above or check the GitHub UI Commits tab for the green shield icon

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting audit report file targets | Planned to edit `ci.yml` for Gitleaks/Trivy `continue-on-error` fixes | Grepping revealed the jobs live in `.github/workflows/_required.yml`, not `ci.yml` | Always grep to confirm where a job actually lives before touching any file |
| Assuming test suite recipe exists | Included `just test-suite` in verification commands | The `test-suite` justfile recipe was itself a deliverable of #88 — it didn't exist yet | Check `just --list` before referencing any recipe in a plan; do not assume recipes created by child issues already exist |
| Using `--rebase` for auto-merge | `gh pr merge N --auto --rebase` | Rebase merging was disabled on the repo; command silently fell back or errored | Check repo merge strategy (Settings → General) first; prefer `--squash` as the safe fallback |
| Milestone attachment by number | `gh issue edit N --milestone 5` (numeric) | `gh issue edit --milestone` requires the milestone title string, not the number | Use `--milestone "Title String"` — the `gh api` call returns the number for reference, but `gh issue edit` uses the title |
| Closing issue before verifying on default branch | Closed a child issue immediately after verifying in a local worktree | Fix only existed on a feature branch, not on `main` yet | Only `gh issue close` after the PR is merged to default branch OR when grepping `main` directly confirms the fix is already there |
| Verify-and-close pattern applied to code fixes | Tried to close #83 (tag arithmetic) by grepping for the bug | Code path bugs cannot be verified by grep alone — the grep shows the code exists, not that the logic is correct | Verify-and-close is for binary conditions (SHA pins present/absent, file exists/missing); logic bugs still require a PR with tests |
| Single Criterion 9 path using placeholder | Used `docs/audit-XX-XX/report.md` placeholder in CLAUDE.md checklist | Path didn't resolve — the actual file was named `docs/audit-2026-04-28/remediation-plan.md` | Always use the concrete resolved path when writing checklists; placeholders in CLAUDE.md break agent tooling |

## Results & Parameters

### Milestone creation — copy-paste reference

```bash
# Create milestone
OWNER=HomericIntelligence
REPO=ProjectProteus

gh api repos/$OWNER/$REPO/milestones \
  -f title="Audit Remediation 2026-04-28" \
  -f due_on="2026-08-01T00:00:00Z" \
  -f state=open

# Attach all children (adjust issue numbers to your audit)
MILESTONE_TITLE="Audit Remediation 2026-04-28"
for n in 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114; do
  gh issue edit "$n" --milestone "$MILESTONE_TITLE"
done
```

### SHA-pin verification (supply chain check)

```bash
# Mutable pins: any `uses:` that is NOT @<40-hex>
grep -nE 'uses: [^@]+@' .github/workflows/*.yml | grep -vE '@[0-9a-f]{40}'
# Zero output = all pins are already SHA-locked = close the supply chain issue
```

### Wave structure template

```yaml
# docs/audit-YYYY-MM-DD/remediation-plan.md header
waves:
  wave_1_foundation:
    parallel: true
    gate: none
    issues: [88, 86, 85, 95, 81]
  wave_2_critical:
    parallel: false
    gate: "wave_1 #88 merged"
    issues: [83, 84, 82, 15]
  wave_3_hygiene:
    parallel: true
    gate: none
    batch_by_file: true
    issues: [103-121]
```

### Three PR policy checks

```bash
# 1. Closes line present on its own line
gh pr view N --json body --jq '.body' | grep -E '^Closes #[0-9]+'

# 2. Enable auto-merge (squash for repos with rebase disabled)
gh pr merge N --auto --squash

# 3. Verify commits are signed (GraphQL)
gh api graphql -f query='{
  repository(owner:"OWNER", name:"REPO") {
    pullRequest(number: N) {
      commits(last: 10) {
        nodes { commit { signature { isValid } } }
      }
    }
  }
}'
```

### Expected timeline (33-issue audit, HomericIntelligence CI)

| Phase | Duration | Notes |
| ------- | ---------- | ------- |
| Epic setup (milestone + docs + CLAUDE.md) | 1–2 hours | Can include verify-and-close pass |
| Wave 1 (parallel PRs) | 2–4 days | CI gate per PR |
| Wave 2 (sequential, gated) | 3–5 days | Must wait for Wave 1 test harness |
| Wave 3 (batched hygiene) | 2–3 days | Batching reduces to 6–8 PRs from 20+ issues |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectProteus | Epic #81 — 33-child STRICT audit remediation setup, 2026-06-19 | Milestone created, all children attached, #87 verified-and-closed, `docs/audit-2026-04-28/remediation-plan.md` created, `CLAUDE.md` updated |

## References

- Related skill: [audit-driven-remediation-workflow](audit-driven-remediation-workflow.md) — end-to-end fix implementation across all phases
- Related skill: [planning-epic-verify-live-child-state](planning-epic-verify-live-child-state.md) — re-verify live child state before planning
- ProjectProteus `docs/audit-2026-04-28/remediation-plan.md` — the concrete wave plan this session produced
