---
name: dependency-update-automation-bot-prs
description: "Use when: (1) a repo uses pixi.toml for conda-forge deps but Dependabot only covers pip/github-actions — add Renovate to automate conda dep updates, (2) reviewing ANY bot-authored PR (Dependabot, Renovate) — run gh pr diff --name-only first because bot PRs frequently carry silent lockfile-format upgrades or maintainer fixup commits that the title doesn't mention, (3) a Dependabot PR title describes a single bump but the diff includes a pixi.lock v6->v7 format migration or unrelated files stacked on the bot branch, (4) a repo declares a centralized versions.yml/versions.json as single source of truth but automated bumps (Dependabot, weekly cron, hand-edits) update only the consumer files (Dockerfiles, workflow pins) while bypassing the manifest — causing silent drift."
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: dependency-update-automation-bot-prs.history
tags:
  - dependabot
  - renovate
  - pixi
  - conda-forge
  - bot-prs
  - pr-review
  - scope-bloat
  - lockfiles
  - pixi-lock
  - manifests
  - drift
  - single-source-of-truth
  - dockerfile
  - github-actions
  - dependency-automation
  - supply-chain
---

# Dependency Update Automation and Bot PR Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Automate dependency updates Dependabot can't parse (conda/pixi via Renovate) and review bot-authored PRs safely — catching silent lockfile-format cascades, maintainer-fixup pile-ons, and central-manifest drift before they land on main |
| **Outcome** | Renovate config merged for conda/pixi (PR #667); 2/11 Dependabot PRs flagged for scope contamination and 3/11 flagged for manifest drift in one HomericIntelligence/AchaeanFleet review session |
| **Verification** | verified-ci |

## When to Use

- A repo uses `pixi.toml` for conda-forge deps but Dependabot only covers `pip`/`github-actions` — conda deps drift with no automated PRs; add Renovate with the `:pixi` preset.
- Reviewing ANY bot-authored PR (Dependabot, Renovate, Lychee, Sweep) — `user.type == "Bot"`. About to APPROVE a "small" bump where the only thing you read was the title.
- A Dependabot PR title describes a single bump but the diff may include a `pixi.lock` v6→v7 format migration, a `package-lock.json` v2→v3 bump, or unrelated files stacked on the bot branch.
- A bot PR has been open >24h and a maintainer may have pushed a fixup commit onto the bot's branch; or `gh pr checks N` shows a red check whose name has nothing to do with the title.
- A repo declares `versions.yml`/`versions.json`/`versions.toml`/`pins.yaml`/`tool-versions.yaml`/`.versions/` as single source of truth, and you're reviewing a base-image / pinned-tool bump.
- A weekly "digest-bump" / "update-pins" cron has gone quiet (no PRs for several cycles).
- Writing or modernizing an update workflow that touches Dockerfiles, install scripts, or `FROM` pins.
- About to arm `gh pr merge --auto` on a bot PR — verify scope NOW, because once auto-merge fires the contamination ships.

## Verified Workflow

> **Warning:** The Renovate config below is confirmed by JSON parse and pre-commit; Renovate app first-run validation is pending CI integration. The review heuristics are verified-local against real bot PRs.

### Quick Reference

```bash
# === Phase 1: scope check — MANDATORY before any verdict on a bot PR. ===
N=691
REPO=HomericIntelligence/AchaeanFleet

# 1. Title + base/head + commit log with authors.
gh pr view $N --repo $REPO --json title,baseRefOid,headRefOid,commits --jq \
  '"title: \(.title)\nbase: \(.baseRefOid[0:8]) head: \(.headRefOid[0:8])\ncommits:\n" + ([.commits[] | "  \(.oid[0:8]) by \(.authors[0].login) \(.messageHeadline)"] | join("\n"))'

# 2. Actual file scope — the ground truth.
gh pr diff $N --repo $REPO --name-only

# 3. Per-file numstat — catch large adds/dels behind innocuous filenames.
gh pr diff $N --repo $REPO | git apply --numstat -

# 4. CI checks.
gh pr checks $N --repo $REPO

# Decision tree:
#   commits length > 1            → Pattern B candidate; check commit authors
#   any commit author != bot      → Pattern B confirmed; REQUEST_CHANGES
#   lockfile in diff not in scope → Pattern A (format cascade); REQUEST_CHANGES
#   numstat 200+ on unmentioned file → Pattern A
#   repo has versions.yml NOT in diff → manifest drift; REQUEST_CHANGES
```

```json
// renovate.json — automate conda/pixi deps Dependabot cannot parse
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", ":pixi"],
  "labels": ["dependencies"],
  "schedule": ["every week on monday"],
  "prConcurrentLimit": 5,
  "packageRules": [
    {
      "description": "Group all conda-forge / pixi deps into one PR",
      "matchManagers": ["pixi"],
      "groupName": "conda-pixi-dependencies",
      "labels": ["dependencies"],
      "commitMessagePrefix": "chore(deps):"
    },
    {
      "description": "Group GitHub Actions updates",
      "matchManagers": ["github-actions"],
      "groupName": "github-actions",
      "labels": ["dependencies", "ci/cd"],
      "commitMessagePrefix": "chore(deps):"
    }
  ]
}
```

```bash
# Validate renovate.json parses before committing.
python3 -c "import json; json.load(open('renovate.json')); print('valid')"
```

### Detailed Steps

#### Example 1 — Renovate for conda/pixi (what Dependabot can't do)

Dependabot's `package-ecosystem: pip` cannot parse `pixi.toml`; conda deps are silently skipped. Renovate's `:pixi` preset reads `pixi.toml` natively.

1. **Read `.github/dependabot.yml`** to note existing cadence (weekly), grouping, labels, and commit-message prefix.
2. **Create `renovate.json`** at the repo root using `config:recommended` + `:pixi` presets (see Quick Reference).
3. **Mirror Dependabot cadence**: set `schedule` to `"every week on monday"`.
4. **Set `prConcurrentLimit: 5`** to avoid a PR flood on the first Renovate run.
5. **Add `packageRules`**: group `matchManagers: ["pixi"]` into one PR; add an explicit `github-actions` rule with the SAME `groupName` Dependabot uses, so Renovate doesn't open duplicate GHA PRs alongside Dependabot.
6. **Validate**: `python3 -c "import json; json.load(open('renovate.json'))"`.
7. **Update `CONTRIBUTING.md`** Dependency Updates section — replace the manual-update note with Renovate coverage; keep `pixi update` for out-of-cycle manual refreshes.
8. **Commit**: `chore(deps): add Renovate config for conda/pixi dependencies` + `Closes #<issue>`.

#### Example 2 — Dependabot PR scope contamination (review the diff, not the title)

The title is the BOT'S INTENT, not the PR's actual scope. Two mutations contaminate bot PRs between title-write and your review:

**Pattern A — silent lockfile/format cascade.** When the resolver re-writes a lockfile, a newer lockfile-tool version on the runner can silently upgrade the format: `pixi.lock` v6→v7, `package-lock.json` v2→v3, `poetry.lock` v1→v2. The bot doesn't mention it (the bot didn't cause it — the resolver did).

Concrete: PR #691 titled `chore(dagger): bump @types/node from 25.6.0 to 25.9.1 in /dagger` was a 4-line devDep change, but also modified `pixi.lock` at the repo root with **226 add / 228 del** — format `version: 6`→`7`, new `linux-64` platform, `pypi-prerelease-mode` removed. Approving it lands `pixi.lock v7` on main; every developer then fails `pixi install` until they upgrade pixi.

```bash
# Detector: does the diff touch a lockfile NOT named by the title's scope?
gh pr diff $N --repo $REPO --name-only | grep -iE 'lock$|\.lock\.|lockfile'
# A CI check green on main but red on the PR, with an unrelated name (e.g. pixi-check
# on a /dagger npm bump) is the format-version mismatch tripping the gate.
gh pr checks $N --repo $REPO | grep -E 'pending|failing'
```

**Pattern B — maintainer fixup stacked on the bot branch.** A maintainer pushes a "fix CI" commit onto `dependabot/<branch>`. The PR-level author still reads `dependabot[bot]`, but commit-level authorship reveals the human.

Concrete: PR #681 titled `chore(docker): bump python ... in /bases` (1-line digest bump) had a second commit `a2c372a4` titled `fix: Address CI failures for PR #681`, **authored by the maintainer**, adding 12 unrelated files (issue templates, PR template, a `validate-claude-caps` CI job, `CLAUDE.md` edits, nomad docs, three test files). Squash makes arrival atomic but NOT reversal: reverting the digest bump later also reverts all 12 files.

```bash
# Commit count > 1 on a Dependabot PR is suspicious.
gh pr view $N --repo $REPO --json commits --jq '.commits | length'
# Any non-bot commit author?
gh pr view $N --repo $REPO --json commits --jq \
  '.commits[] | select((.authors[0].login | test("\\[bot\\]$")) | not) | {oid, author: .authors[0].login, headline: .messageHeadline}'
```

**Distinguish legitimate cascades from contamination.** A `package.json` change SHOULD update its sibling `package-lock.json`; a `pyproject.toml` change SHOULD update `pixi.lock` for the affected platform. Contamination is when the lockfile diff is *structurally different* from what the bump requires:

| Legitimate cascade | Contamination |
|--------------------|---------------|
| 1 dep added → 5-20 lines under that dep's section | 4-line npm bump → 226 add/228 del across the whole pixi.lock |
| Lockfile diff scoped to the bumped dep | Format header change (`version: 6` → `version: 7`) |
| Subdirectory's local lockfile matching the change | Lockfile diff at REPO ROOT for a subdir-scoped change |
| Matches the resolver's expected output | Removes/adds platform sections (`linux-64`, `osx-64`) |

Shortcut test: lockfile diff length should be proportional to the dependency change. 226 lines of lockfile for 4 lines of dep is a 50× signal — contamination.

**Verdict rule** (one-way — contamination is REQUEST_CHANGES, never APPROVE-with-comment, because APPROVE leaves the PR auto-mergeable):

| Condition | Verdict |
|-----------|---------|
| Diff title-aligned (only in-scope files, all commits by the bot, no cascade) | Proceed with normal review |
| Lockfile format upgrade not explained by the bump | **REQUEST_CHANGES** — revert the lockfile change or scope the format upgrade to its own PR |
| Maintainer fixup commits unrelated to the title | **REQUEST_CHANGES** — split unrelated changes into separate PRs |
| Both (rare but real) | **REQUEST_CHANGES** — mark the lockfile cascade first (harder revert) |

#### Example 3 — Central versions manifest drift from automation bypass

When a repo declares a `versions.*` manifest as single source of truth, automated bumps often touch only the consumer files (Dockerfiles, workflow pins) and bypass the manifest — leaving it lying about the files it claims to govern.

```bash
OWNER_REPO="HomericIntelligence/AchaeanFleet"; PR="682"

# 1. Does the repo claim a central versions manifest?
ls versions.yml versions.json versions.toml .versions/ pins.yaml tool-versions.yaml 2>/dev/null

# 2. If yes, does the PR diff include it?
gh pr diff "$PR" --repo "$OWNER_REPO" --name-only | grep -E '^(versions\.(yml|json|toml)|pins\.yaml|tool-versions\.yaml)$'
# Empty output + step 1 hit => manifest update missing => REQUEST_CHANGES

# 3. Does any workflow hardcode the OLD version/digest in grep/sed?
OLD_VERSION="25-slim"; OLD_DIGEST="sha256:67134eb"   # extract from the PR's "before" side
grep -rn -E "$OLD_VERSION|$OLD_DIGEST" .github/workflows/
# Matches => bump-automation will silently no-op after merge => flag as follow-up

# 4. Is used_by: (if present) actually accurate?
yq '.base_images.*.used_by[]' versions.yml | sort -u > /tmp/manifest_consumers.txt
git ls-files 'bases/Dockerfile.*' 'vessels/**/Dockerfile' 'images/**/Dockerfile' | sort -u > /tmp/actual.txt
diff /tmp/manifest_consumers.txt /tmp/actual.txt
# Any Dockerfile in actual.txt but not the manifest is a hidden consumer.
```

The deeper bug: the bump workflow often hardcodes the old version in grep/sed (`grep -l 'node:25-slim' bases/`, `sed -i "s|node:25-slim@sha256:[a-f0-9]*|...|"`). After the Dockerfile moves to `node:26-slim`, those lines match zero and the job exits 0 — a workflow that succeeds with zero work is indistinguishable from one that did real work.

**Root-cause fix** — invert the data flow so the manifest is the source and Dockerfiles are derived (drift becomes structurally impossible):

```bash
yq eval ".base_images.node.tag = \"$NEW_TAG\"" -i versions.yml
yq eval ".base_images.node.digest = \"$NEW_DIGEST\"" -i versions.yml
for f in $(yq '.base_images.node.used_by[]' versions.yml); do
  new_from="FROM node:$(yq '.base_images.node.tag' versions.yml)@$(yq '.base_images.node.digest' versions.yml)"
  sed -i "s|^FROM node:.*|$new_from|" "$f"
done
```

**Audit historical drift** before approving any new manifest change:

```bash
git log --format="%h %s" --since="6 months ago" -- bases/Dockerfile.* \
  | while read sha msg; do
      git show --name-only --format= "$sha" | grep -q '^versions\.yml$' || echo "DRIFT: $sha $msg"
    done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use Dependabot for pixi deps | `package-ecosystem: pip` in dependabot.yml | pip ecosystem cannot parse pixi.toml; pixi deps silently skipped | Use Renovate with the `:pixi` preset; add an explicit `github-actions` rule sharing Dependabot's groupName to avoid duplicate GHA PRs, and set `prConcurrentLimit: 5` to prevent a first-run PR flood |
| Approve PR #691 because "the npm bump in /dagger is clean" | Read the title, glanced at the 4-line package.json change, prepared to APPROVE | Would land an unrelated `pixi.lock` v6→v7 cascade (linux-64 added, pypi-prerelease-mode removed) on main; every dev would fail `pixi install` until upgrading pixi | The title is the bot's intent, not the scope. `gh pr diff --name-only` is mandatory before APPROVE even when the bump is obviously clean |
| Trust the PR author tag to mean "no human touched this branch" | Saw `dependabot[bot]` as PR author, assumed all commits were bot-authored | The author field reflects who OPENED the PR, not who committed since. PR #681's `a2c372a4` was maintainer-authored but the PR author still read `dependabot[bot]` | Check commit-level authors (`--json commits --jq '.commits[].authors[0].login'`), not the PR-level author cover page |
| Approve PR #682 because the new `node:26-slim` digest was itself correct | Spot-check the digest, confirm it pins a real published image, APPROVE | Leaves `versions.yml` declaring `tag: "25-slim"` — the manifest now lies; and `digest-bump.yml` greps the OLD string and silently no-ops on the next run | A bump PR is judged on every file the value SHOULD be set in; manifest drift and workflow grep-fragility are the same bug — fix both or fix neither. Add a guard that fails when expected substitutions return 0 hits |

## Results & Parameters

### Renovate config parameters

- `extends: ["config:recommended", ":pixi"]` — the `:pixi` preset enables native pixi.toml parsing.
- `schedule: ["every week on monday"]` — matches Dependabot weekly cadence.
- `prConcurrentLimit: 5` — prevents PR flood on first run.
- `matchManagers: ["pixi"]` in packageRules — targets only pixi.toml entries.
- `commitMessagePrefix: "chore(deps):"` — matches Dependabot convention.

### Manifest-drift verdict table

```yaml
verdict_table:
  manifest_exists_and_in_diff: APPROVE
  manifest_exists_and_NOT_in_diff: REQUEST_CHANGES
  no_manifest_but_workflow_has_hardcoded_old_version: APPROVE + follow-up issue
  manifest_exists_AND_workflow_hardcodes_old_version: REQUEST_CHANGES + follow-up issue

manifest_files: [versions.yml, versions.json, versions.toml, pins.yaml, tool-versions.yaml, .versions/]
fragile_workflow_patterns:
  - "grep -l '<tool>:<exact-version>' bases/"
  - "sed -i 's|<tool>:<exact-version>@sha256:[a-f0-9]*|...|' \"$f\""
```

### Verdict templates (copy-paste)

```markdown
<!-- Pattern A: lockfile format cascade -->
REQUEST_CHANGES
The diff modifies `<lockfile-path>` with `<N> add / <M> del`, not explained by the
dependency bump in the title (`<title-scope>`). It includes a format-version change
(`<v6 → v7>`) and `<platform/section changes>`. Either revert the lockfile changes so
this PR is scoped to the bump only, OR re-open the format upgrade as its own PR.

<!-- Pattern B: maintainer fixup stacked on bot branch -->
REQUEST_CHANGES
Commits `<sha1>`, `<sha2>` add files unrelated to the title (`<title>`): `<file list>`.
Per SRP this PR does more than one thing. Split the unrelated changes into separate
PRs so each can be reviewed, merged, and reverted atomically.

<!-- Manifest drift -->
REQUEST_CHANGES
This PR bumps `<dockerfile-path>` to `<tool>:<new-tag>` but `versions.yml` still declares
`.base_images.<tool>.tag: "<old-tag>"`. Per the manifest header ("single source of truth"),
update `.base_images.<tool>.tag`/`.digest` and `used_by[]` in this same PR. Note that
`.github/workflows/<bump-workflow>.yml` hardcodes the OLD version in grep/sed — it will
silently no-op after merge until parameterised from `versions.yml`.
```

### Pre-flight batch script

```bash
#!/usr/bin/env bash
# bot-pr-scope-check.sh <owner/repo> <pr-1> [<pr-2> ...]
set -euo pipefail
REPO="$1"; shift
for N in "$@"; do
  echo "=== PR #$N ==="
  gh pr view "$N" --repo "$REPO" --json title,commits --jq \
    '"title: \(.title)\ncommit count: \(.commits | length)\nauthors: " + ([.commits[].authors[0].login] | unique | join(","))'
  echo "files:";   gh pr diff "$N" --repo "$REPO" --name-only | sed 's/^/  /'
  echo "numstat:"; gh pr diff "$N" --repo "$REPO" | git apply --numstat - 2>/dev/null | sed 's/^/  /'
  echo "checks:";  gh pr checks "$N" --repo "$REPO" | sed 's/^/  /'
done
```

Grep the output for `commit count: [^1]$` (Pattern B candidates) and lockfile names outside the bumped scope (Pattern A candidates) before reviewing.

### Observed rates (verified-local, HomericIntelligence/AchaeanFleet 2026-05-31, 11 Dependabot PRs)

- Scope contamination: 2/11 (18%) — #691 Pattern A (pixi.lock v6→v7), #681 Pattern B (12 fixup files).
- Manifest drift: 3/11 (27%) — #681 python, #682 node, #683 debian bumped the Dockerfile only, leaving `versions.yml` stale.
- Phase-1 scope check costs ~30s/PR vs ~10s title-glance; the ~3.5 extra minutes per 11-PR batch prevents days of post-merge cleanup.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #484 — Renovate for conda/pixi, PR #667 | renovate.json valid; pre-commit passed; Renovate app first run pending |
| HomericIntelligence/AchaeanFleet | 2026-05-31 bot-PR review session (11 Dependabot PRs) | #691 Pattern A (pixi.lock 226/228, format v6→v7, linux-64 added; `pixi-check` red on PR/green on main); #681 Pattern B (maintainer commit `a2c372a4` added 12 unrelated files on a 1-line digest bump); #681/#682/#683 also left `versions.yml` stale while `digest-bump.yml` grep/sed hardcoded the old version, would silently no-op after merge |
