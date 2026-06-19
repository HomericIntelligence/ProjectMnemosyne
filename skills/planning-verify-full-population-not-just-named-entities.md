---
name: planning-verify-full-population-not-just-named-entities
description: "When an issue scopes work to an ENTIRE population ('across the ecosystem', 'all repos', 'every X') but names only a subset, enumerate the full set YOURSELF and loop your verification over ALL of it — the items the issue names are usually NOT where the residue hides. Verifying only the named subset structurally cannot find defects in the unnamed members, which is exactly where a reviewer flags 'uneven coverage' and where real migration residue survives. Use when: (1) an issue/ticket says 'across the ecosystem / all repos / every X' but lists only some entities, (2) declaring a migration/standardization complete based on checking only the named entities, (3) any verification whose conclusion ('done') depends on NOT finding residue anywhere in a population."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Planning: Verify the Full Population, Not Just Named Entities

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | When an issue scopes work to an entire population ("standardize the default branch across the ecosystem") but names only a subset (5 of 15 repos), scope the verification loop to the WHOLE population so residue in unnamed members is actually found before declaring the work complete |
| **Outcome** | Successful: re-planning issue #24 after a NOGO, extending the live-state check from the 5 named repos to all 15 surfaced `ProjectKeystone` (NOT one of the named 5) still carrying a stale unprotected orphan `refs/heads/master` — the one real migration residue. The 5-repo scan structurally could not find it. |
| **Verification** | verified-local (all gh/grep commands below were run this session and produced the cited outputs; not validated in ProjectMnemosyne CI) |
| **History** | (initial version) |

## When to Use

- An issue/ticket says "across the ecosystem," "all repos," "every X," or "ecosystem-wide" but lists only a subset of the entities by name.
- You are about to declare a migration or standardization **complete** based on having checked only the entities the issue explicitly named.
- Any verification whose conclusion ("done" / "no residue") depends on NOT finding something — a negative claim is only as strong as the population it scanned.
- Re-planning after a reviewer flags "uneven coverage" or "you only checked the named ones."

## Verified Workflow

The named entities are a snapshot of where the filer *believed* the problem was. The actual scope
is the population phrase ("all," "every," "across the ecosystem"). Enumerate the full population
yourself, then loop every check over ALL of it. Write each check to **fail loud** so an API
failure can never masquerade as a clean "no residue" result.

### Quick Reference

```bash
ORG=HomericIntelligence

# 0. Enumerate the FULL population yourself (do not trust the issue's subset list)
REPOS=$(gh repo list "$ORG" --limit 200 --json name --jq '.[].name')

# 1. Default branch for EVERY repo (authoritative; not the issue's table)
for R in $REPOS; do
  printf '%s\t' "$R"
  gh repo view "$ORG/$R" --json defaultBranchRef --jq .defaultBranchRef.name
done

# 2. Fail-LOUD orphan-ref check across ALL repos — clean boolean, emits nothing on API failure.
#    Do NOT use `gh api .../branches/master 2>&1 | grep 'Not Found' || echo 'Not Found'`:
#    it masks auth errors / rate-limits as a false-green "Not Found".
for R in $REPOS; do
  printf '%s\t' "$R"
  gh api "repos/$ORG/$R/git/refs/heads" --jq 'any(.ref=="refs/heads/master")'
done

# 3. For any repo that DOES have refs/heads/master, prove it is a safe-to-delete orphan:
R=ProjectKeystone
gh api "repos/$ORG/$R/branches/master" --jq .protected            # expect: false (unprotected)
gh pr list --repo "$ORG/$R" --base master --json number --jq length # expect: 0  (no PRs target it)
gh api "repos/$ORG/$R/compare/main...master" --jq .status 2>&1      # "No common ancestor" => orphan
# Then delete:
gh api -X DELETE "repos/$ORG/$R/git/refs/heads/master"

# 4. Verify "already-applied" governance by DIRECT live read — never infer from config files.
gh api "repos/$ORG/Odysseus/rulesets" \
  --jq '.[]|{name,target,enforcement,id}'
#   NOTE: org-level `gh api orgs/$ORG/rulesets` 404s on the FREE plan (needs admin:org).
#   The repo-level rulesets read is authoritative.
```

### Detailed Steps

1. **Read the population phrase, not the example list.** "Standardize X across the ecosystem"
   means *every* member. The 5 (or N) repos the issue names are illustrative, not the scope.
2. **Enumerate the full population yourself** (`gh repo list "$ORG"`), and build your loop over
   that list — never over the issue's hand-picked subset.
3. **Loop every check over ALL members.** The unnamed members are precisely where the filer was
   not looking, so they are the most likely home of surviving residue.
4. **Make each check fail-loud.** Use a clean boolean (`--jq 'any(...)'`) that emits nothing on
   API failure instead of a `grep ... || echo 'Not Found'` pattern that turns failures into
   false greens.
5. **Run each verification command and paste its REAL output as the expected value.** Do not
   annotate a check with a guessed count; a wrong expected value makes a reviewer running the
   exact command conclude the check FAILED.
6. **Verify "already-applied" claims by direct live read, never by inference.** A justfile +
   config file is intent, not state. Read the live API (`gh api .../rulesets`).
7. **For each residue you find, prove it is safe to remediate before acting** (orphan-branch
   triad below), then remediate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Verify only the 5 named repos | Ran the live-state loop over only the 5 repos the issue listed as "on master," then declared the ecosystem migration complete | The issue scope was ecosystem-wide ("all repos"); a 5-of-15 scan structurally cannot find residue in the other 10. Reviewer flagged "uneven coverage." Extending to all 15 surfaced `ProjectKeystone` (NOT one of the 5) still carrying an orphan `refs/heads/master`. | Enumerate the FULL population yourself and loop every check over all of it; the named items are usually NOT where residue hides |
| Assert a grep count without running it | Annotated a verification step "this grep returns count 4" from eyeballing the tree | Running it returned `3` — the 4th `master` literal was a trailing `# master` comment that the `@master\|--branch, master` regex provably cannot match. A wrong expected value makes a reviewer running the command conclude the check FAILED. | Always run the verification command and paste its real output as the expected value |
| Fail-green existence check | `gh api repos/ORG/REPO/branches/master 2>&1 \| grep -o 'Not Found' \|\| echo 'Not Found'` to test branch absence | Masks auth errors / rate-limits / any non-"Not Found" failure as a false-green "Not Found" — a silent false negative across a population loop | Use `gh api .../git/refs/heads --jq 'any(.ref=="refs/heads/master")'` — a clean boolean that emits nothing on API failure (fail-loud) |
| Infer "ruleset applied" from config files | Claimed branch protection was active by reading `justfile` + `configs/github/org-ruleset.json` | Reviewer rejected inference-as-evidence; config is intent, not live state. (Org-level `gh api orgs/ORG/rulesets` also 404'd on the FREE plan.) | Verify "already-applied" via a DIRECT live read — `gh api repos/ORG/REPO/rulesets` is authoritative on the FREE plan |

## Results & Parameters

**Org plan constraint:** `HomericIntelligence` is on the **FREE** plan.
`gh api orgs/HomericIntelligence/rulesets` returns 404 (needs `admin:org` scope, unavailable on
free). The **repo-level** read `gh api repos/HomericIntelligence/<REPO>/rulesets` is authoritative.

**Live ruleset value confirmed by direct read (2026-06-19):**

```json
{ "name": "homeric-main-baseline", "target": "branch", "enforcement": "active", "id": 15556483 }
```

**`ProjectKeystone` orphan-master residue (the find a 5-repo scan missed):**
- Default branch was already `main` — which is exactly why it was NOT in the issue's named 5.
- `refs/heads/master` still present.
- `branches/master --jq .protected` → `false` (unprotected).
- `gh pr list --base master --json number --jq length` → `0` (no PRs target it).
- `compare/main...master` → "No common ancestor" → orphan.
- All three conditions met ⇒ safe to delete via
  `gh api -X DELETE repos/HomericIntelligence/ProjectKeystone/git/refs/heads/master`.

**Safe-to-delete orphan-branch triad (all three must hold):**

1. Unprotected: `gh api repos/ORG/REPO/branches/<name> --jq .protected` → `false`
2. No PRs target it: `gh pr list --repo ORG/REPO --base <name> --json number --jq length` → `0`
3. Orphan: `gh api repos/ORG/REPO/compare/main...<name>` → "No common ancestor"

**Related skill:** `planning-verify-live-state-before-assuming-work-remains` — verify live external
state before assuming work remains (the per-entity check this skill scopes to the whole population).
