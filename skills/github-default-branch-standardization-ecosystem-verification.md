---
name: github-default-branch-standardization-ecosystem-verification
description: "Verify, remediate, and document GitHub default-branch standardization across
  a multi-repo fleet. Use when: (1) confirming all repos in an org have migrated from
  `master` to `main` as the default branch, (2) scanning for stale `refs/heads/master`
  orphan branches after a default-branch rename, (3) safely deleting an unprotected orphan
  branch that has no open PRs targeting it and no common ancestor with main, (4) classifying
  `master` literals in workflow YAML to distinguish stale branch refs from legitimate
  third-party action pins or pre-commit guards, (5) verifying a branch-protection ruleset
  is active across all fleet repos after migration, (6) writing migration records in standing
  docs with historical framing that does not drift as point-in-time facts, or (7) a branch
  has 0 commits ahead of main and GitHub refuses to open a PR — forcing a minimal doc artifact
  to give the branch a real commit."
category: tooling
date: 2026-06-20
version: "1.0.0"
user-invocable: false
tags:
  - github
  - default-branch
  - master-to-main
  - branch-standardization
  - ecosystem
  - fleet
  - orphan-branch
  - stale-ref
  - gh-cli
  - branch-protection
  - ruleset
  - false-green
  - documentation-drift
  - multi-repo
---

# GitHub Default-Branch Standardization: Ecosystem Verification

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Verify all 15 HomericIntelligence repos had `main` as their GitHub `defaultBranchRef`, find and delete any stale `refs/heads/master` orphan branches, classify all `master` literals in workflow YAML, confirm the `homeric-main-baseline` branch-protection ruleset was active, and document the migration in `docs/repo-conventions.md` with historical framing |
| **Outcome** | Success — 15/15 repos confirmed `main`; one stale orphan (`ProjectKeystone/refs/heads/master`) found and deleted; 3 legitimate `master` literals classified as non-branch (pre-commit guard + two third-party action pins) and left untouched; ruleset confirmed `active`; migration record added to Odysseus conventions doc |
| **Verification** | verified-ci — all checks run live against GitHub API; deletion confirmed; linked tracking issues closed |

## When to Use

- You are verifying that a GitHub org has completed a `master` → `main` default-branch migration and want authoritative confirmation for all repos.
- After a fleet-wide default-branch rename, you need to find any stale `refs/heads/master` orphan branches left behind and determine whether they are safe to delete.
- You have grep hits for `master` in `.yml`/`.yaml` files and need to determine which are stale branch refs vs legitimate third-party action pins or tool arguments.
- A branch-protection ruleset (`homeric-main-baseline` or similar) needs to be confirmed as `enforcement: active` after migration.
- You need to write a point-in-time migration record into a standing conventions document WITHOUT creating prose assertions that drift (e.g., "all repos are on main" written as present-tense truth).
- A feature branch has 0 commits ahead of `main` (because all work was remote API calls) and GitHub refuses to open a PR. You need a minimal, accurate documentation artifact to give the branch a real commit.

## Verified Workflow

### Quick Reference

```bash
# --- Default-branch check (all repos in the fleet) ---
ORG=HomericIntelligence
REPOS=(AchaeanFleet ProjectAgamemnon ProjectArgus ProjectCharybdis ProjectHephaestus \
        ProjectHermes ProjectKeystone Mnemosyne ProjectNestor ProjectOdyssey \
        ProjectOdyssey ProjectProteus ProjectScylla ProjectTelemachy Myrmidons)

for repo in "${REPOS[@]}"; do
  default=$(gh repo view "$ORG/$repo" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null)
  echo "$repo: $default"
done

# --- Authoritative stale-ref check (false-green-resistant) ---
# GOOD: returns clean boolean; no output on API failure (no false-green masking)
gh api repos/$ORG/$repo/git/refs/heads --jq 'any(.ref=="refs/heads/master")'

# BAD: masks auth errors and rate-limit failures as "Not Found" (false-green)
# gh api repos/$ORG/$repo/git/refs/heads/master 2>&1 | grep -o ... || echo 'Not Found'

# --- Fleet-wide stale master ref scan ---
for repo in "${REPOS[@]}"; do
  has_master=$(gh api "repos/$ORG/$repo/git/refs/heads" \
    --jq 'any(.ref=="refs/heads/master")' 2>/dev/null)
  echo "$repo: master_ref=$has_master"
done

# --- Before deleting a stale master branch: verify it is safe ---
# 1. Check protection status
gh api repos/$ORG/$repo/branches/master --jq '{name, protected}'
# -> {"name":"master","protected":false}   must be false

# 2. Confirm 0 open PRs targeting master
gh pr list --repo "$ORG/$repo" --state open --base master --json number --jq 'length'
# -> 0   must be zero

# 3. Delete the stale ref
gh api -X DELETE "repos/$ORG/$repo/git/refs/heads/master"

# 4. Confirm deletion
gh api "repos/$ORG/$repo/git/refs/heads" --jq 'any(.ref=="refs/heads/master")'
# -> false

# --- Classify master literals in workflow YAML (before editing anything) ---
# Find workflow triggers on master (exit=1 means none found = good)
grep -rnE "branches:\s*\[?\s*[\"']?master" --include='*.yml' --include='*.yaml' .

# Find legitimate non-branch master literals (leave these untouched)
grep -rnE "@master|--branch, master" --include='*.yml' --include='*.yaml' .
# @master  = third-party action pin (e.g. aquasecurity/trivy-action@master)
# --branch, master = pre-commit guard argument, NOT a branch ref

# --- Verify branch-protection ruleset is active ---
gh api "repos/$ORG/$repo/rulesets" \
  --jq '.[] | select(.name=="homeric-main-baseline") | {name, enforcement}'
# -> {"name":"homeric-main-baseline","enforcement":"active"}
```

### Detailed Steps

#### 1. Full fleet scan — scan ALL repos, not just the ones named in the issue

The instinct is to check only the repos explicitly mentioned in the issue or ticket. This produces false confidence: a 5-repo scan missed ProjectKeystone's stale `master` ref. Always enumerate the complete fleet.

Build the full repo list from `gh repo list` or an authoritative source (e.g., Odysseus `.gitmodules`):

```bash
# List all repos in the org (if the fleet is large)
gh repo list HomericIntelligence --json name --jq '.[].name' | sort
```

#### 2. Default-branch verification

Use `gh repo view --json defaultBranchRef` — reliable and returns the GitHub `defaultBranchRef` object, not just the local checkout's config:

```bash
gh repo view "HomericIntelligence/$repo" --json defaultBranchRef --jq .defaultBranchRef.name
# returns "main" or "master" (or other)
```

Do NOT use `git remote show origin | grep 'HEAD branch'` from a local clone — this reflects the local remote-tracking state and may be stale after a rename.

#### 3. Stale-ref detection — use `/git/refs/heads`, not `/branches/<name>`

Two endpoint hazards:

**Hazard A — `|| echo 'Not Found'` false-green masking:**
```bash
# WRONG — masks auth errors, rate-limit 403s, and network failures as "Not Found"
gh api "repos/$ORG/$repo/git/refs/heads/master" 2>&1 | grep -o ... || echo 'Not Found'
```
If the API call fails for any reason (auth, rate-limit, network), the `||` branch fires and reports "Not Found", giving a false negative that the stale ref doesn't exist.

**Hazard B — `/branches/<name>` redirect:**
The `/branches/<name>` endpoint can redirect for renamed branches and return stale results. The authoritative endpoint is `/git/refs/heads`, filtered with a `jq` `any()`:

```bash
# CORRECT — returns false (not "Not Found") on non-existence; no output on API failure
gh api "repos/$ORG/$repo/git/refs/heads" --jq 'any(.ref=="refs/heads/master")'
```

#### 4. Safety checks before deletion

A stale orphan branch is safe to delete when ALL three conditions hold:
1. **Unprotected** — `protected: false` from `/branches/<name>`
2. **No open PRs target it** — `gh pr list ... --base master --jq 'length'` returns `0`
3. **No common ancestor with main** — the orphan has diverged or is entirely separate (optional but informative: `git merge-base origin/master origin/main` returns nothing)

```bash
# Full pre-deletion checklist
REPO=ProjectKeystone
ORG=HomericIntelligence

protected=$(gh api "repos/$ORG/$REPO/branches/master" --jq '.protected')
pr_count=$(gh pr list --repo "$ORG/$REPO" --state open --base master --json number --jq 'length')

echo "protected=$protected pr_count=$pr_count"
# safe to delete only if: protected=false AND pr_count=0
```

#### 5. Classify `master` literals before editing anything

After checking for stale branch refs, you may grep for `master` in `.yml` files and find hits. Before editing, classify each hit:

| Pattern | Example | Classification | Action |
| ------- | ------- | -------------- | ------ |
| `@master` in a `uses:` line | `aquasecurity/trivy-action@master` | Third-party action pin — points to upstream's `master` branch | Leave untouched |
| `@master` in a `uses:` line | `ludeeus/action-shellcheck@master` | Third-party action pin | Leave untouched |
| `--branch, master` in a `run:` or `args:` | `pre-commit run --branch, master` | Tool argument string, not a branch ref | Leave untouched |
| `branches: [master]` in a trigger | `on: push: branches: [master]` | Stale workflow trigger | Edit to `main` |
| `base: master` in a PR config | `base: master` | Stale PR target | Edit to `main` |

```bash
# Find the legitimate non-branch literals (do NOT edit these)
grep -rnE "@master|--branch, master" --include='*.yml' --include='*.yaml' .
```

#### 6. Branch-protection ruleset verification

After migration, confirm the ruleset is enforcing — not in evaluate mode:

```bash
gh api "repos/$ORG/$REPO/rulesets" \
  --jq '.[] | select(.name=="homeric-main-baseline") | {name, enforcement, id}'
# enforcement must be "active", not "evaluate"
```

If multiple repos should all have this ruleset active, loop the check:

```bash
for repo in "${REPOS[@]}"; do
  enforcement=$(gh api "repos/$ORG/$repo/rulesets" \
    --jq '.[] | select(.name=="homeric-main-baseline") | .enforcement' 2>/dev/null)
  echo "$repo: $enforcement"
done
```

#### 7. Writing migration records in standing docs — historical framing

Standing documents (conventions guides, ADRs, onboarding docs) are read indefinitely. Writing present-tense facts that become false creates drift:

```markdown
<!-- WRONG — becomes false when a new repo is added without following the migration -->
All 15 HomericIntelligence repos are verified on `main`. The ruleset is active.

<!-- CORRECT — historical framing; point-in-time truth that doesn't become false -->
As of issue #24 (2026-06), all 15 HomericIntelligence repos in the fleet at that
time were verified to have `main` as their default branch. One stale orphan
(`ProjectKeystone/refs/heads/master`) was found and deleted.

To verify the current state, run:
  gh repo list HomericIntelligence --json name,defaultBranchRef \
    --jq '.[] | select(.defaultBranchRef.name != "main") | .name'
```

Key rules:
- Prefix assertions with "As of `<issue>` (`<date>`)..."
- Remove volatile IDs (ruleset numeric IDs) from prose — they rotate and confuse
- Let runbook verification commands be the source of current truth
- Do not write "is active" as a permanent fact — write "was confirmed active at <date>; verify with `<command>`"

#### 8. Producing a minimal doc commit when branch has 0 commits ahead of main

When the entire implementation is remote API operations (no local file edits), the feature branch has 0 commits ahead of `main` and `gh pr create` fails with "nothing to compare."

Fix: produce a minimal, accurate documentation artifact that:
- Records the migration as a historical fact (not a permanent assertion)
- Adds runbook-style verification commands so readers can confirm current state
- Is genuinely useful (not padding)

The conventions doc is a natural home for this artifact. A migration record section fits naturally in `docs/repo-conventions.md` or an equivalent.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| False-green masking with `\|\| echo 'Not Found'` | Used `gh api .../refs/heads/master 2>&1 \| grep -o ... \|\| echo 'Not Found'` to check for stale refs | Auth errors, rate-limit 403s, and network failures all fire the `\|\|` branch and report "Not Found", producing a false negative — the stale ref looks absent when it may actually exist | Use `gh api .../git/refs/heads --jq 'any(.ref=="refs/heads/master")'` which returns `false` on non-existence and emits no output (not "Not Found") on API failure |
| 5-repo scan missed a stale ref | Scanned only the 5 repos named in the issue body | ProjectKeystone's stale `refs/heads/master` was in one of the 10 unchecked repos; the 5-repo scan reported "all clear" | Always scan ALL repos in the fleet, not just the ones named in the issue — the issue body is a claim about which repos are affected, not an exhaustive list |
| `/branches/<name>` endpoint for stale-ref check | Used `gh api repos/$ORG/$REPO/branches/master` to check existence | The `/branches/<name>` endpoint can redirect for renamed branches and may return stale results; it is not authoritative for ref existence | Use `/git/refs/heads` with `any(.ref=="refs/heads/master")` for authoritative ref existence checks |
| Editing `@master` action pin lines | Grep for `master` in `.yml` files returned hits including `aquasecurity/trivy-action@master` and `ludeeus/action-shellcheck@master` | These are third-party action pins pointing to the upstream project's `master` branch — editing them to `@main` would break the action (the upstream may not have a `main` branch) | Classify each `master` hit before editing: `@master` in a `uses:` line = third-party pin, leave untouched; `branches: [master]` in a trigger = stale ref, edit |
| Present-tense migration facts in standing docs | Wrote "All 15 repos are verified on `main`" and "The ruleset is active" as permanent assertions | These become false when new repos are added without following the convention, or when a ruleset is accidentally set to `evaluate` mode; readers treat present-tense prose as live truth indefinitely | Use historical framing: "As of issue #24 (2026-06), 15 repos were verified..."; let runbook verification commands be the source of current truth; remove volatile ruleset IDs from prose |
| Trying to open a PR with 0 commits ahead of main | All implementation was remote API calls with no local file edits; tried `gh pr create` | GitHub refuses to create a PR when a branch has no commits that differ from the base ("nothing to compare") | Produce a minimal, accurate documentation artifact (migration record + runbook commands) in the relevant conventions doc to give the branch a real, useful commit |

## Results & Parameters

### Fleet scan — expected output when migration is complete

```text
AchaeanFleet: main
ProjectAgamemnon: main
ProjectArgus: main
ProjectCharybdis: main
ProjectHephaestus: main
ProjectHermes: main
ProjectKeystone: main        ← stale master REF existed but defaultBranchRef was already main
Mnemosyne: main
ProjectNestor: main
ProjectOdyssey: main
ProjectProteus: main
ProjectScylla: main
ProjectTelemachy: main
Myrmidons: main
Odysseus: main
```

### Stale-ref deletion confirmation

```bash
# Delete
gh api -X DELETE "repos/HomericIntelligence/ProjectKeystone/git/refs/heads/master"
# -> (empty response = success, HTTP 204)

# Confirm gone
gh api "repos/HomericIntelligence/ProjectKeystone/git/refs/heads" \
  --jq 'any(.ref=="refs/heads/master")'
# -> false
```

### Ruleset verification — active enforcement

```bash
gh api "repos/HomericIntelligence/Mnemosyne/rulesets" \
  --jq '.[] | select(.name=="homeric-main-baseline") | {name, enforcement}'
# -> {"name":"homeric-main-baseline","enforcement":"active"}
```

### Migration record template for docs/repo-conventions.md

```markdown
## Default Branch

All new HomericIntelligence repositories must use `main` as the default branch.

### Migration Record

**As of issue #24 (2026-06):** All 15 HomericIntelligence repositories in the fleet
at that time were verified to have `main` as their GitHub `defaultBranchRef`. One
stale orphan branch (`ProjectKeystone/refs/heads/master`, unprotected, no open PRs,
no common ancestor with `main`) was discovered during a full fleet scan and deleted.
The `homeric-main-baseline` branch-protection ruleset was confirmed `enforcement: active`.

> Note: The fleet composition changes over time. The verification above covers the
> repos that existed as of that issue. To confirm current state, run:
>
> ```bash
> gh repo list HomericIntelligence --json name,defaultBranchRef \
>   --jq '.[] | select(.defaultBranchRef.name != "main") | .name'
> # An empty result means all repos are on main.
>
> gh api repos/HomericIntelligence/<REPO>/git/refs/heads \
>   --jq 'any(.ref=="refs/heads/master")'
> # false = no stale master ref
> ```
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence (15 repos) | Issue #24 (2026-06-20) — default-branch standardization audit | All 15 repos confirmed `main`; ProjectKeystone stale `refs/heads/master` deleted; 3 legitimate `@master`/`--branch, master` literals classified and left untouched; `homeric-main-baseline` ruleset confirmed active; migration record added to Odysseus `docs/repo-conventions.md` |

## References

- [GitHub REST: Get a repository](https://docs.github.com/en/rest/repos/repos#get-a-repository) — `defaultBranchRef` field
- [GitHub REST: List matching references](https://docs.github.com/en/rest/git/refs#list-matching-references) — authoritative `/git/refs/heads` endpoint
- [GitHub REST: Delete a reference](https://docs.github.com/en/rest/git/refs#delete-a-reference) — ref deletion
- [gha-required-checks-branch-protection](gha-required-checks-branch-protection.md) — related skill for branch-protection ruleset management
- [git-branch-state-triage-and-recovery](git-branch-state-triage-and-recovery.md) — related skill for orphan-branch state diagnosis
