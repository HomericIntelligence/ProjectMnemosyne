---
name: ci-cd-broken-main-parallel-fix-wave
description: "Triage and fix broken CI/main across multiple repos simultaneously using Agamemnon task registry + parallel myrmidon fix agents. Use when: (1) 3+ repos have broken main branch CI, (2) need to register tasks in Agamemnon before dispatching agents, (3) CI failures are diverse (conan profile, dependabot config, GitHub Actions auth, BATS helper, Python imports)."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ci, broken-main, agamemnon, parallel-agents, myrmidon, conan, dependabot, bats, github-actions, fix-wave]
---

# CI Broken-Main Parallel Fix Wave

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-24 |
| **Objective** | Use the HomericIntelligence agent mesh to fix broken CI/main across multiple repositories simultaneously — NATS + Agamemnon task registry + parallel Claude Code sub-agents as myrmidon workers |
| **Outcome** | Successful — 5 repos triaged, tasks registered in Agamemnon, 5 parallel fix agents dispatched (mix of Haiku and Sonnet tiers) |
| **Verification** | verified-local — tasks dispatched and agents running; PRs not yet merged at capture time |

## When to Use

- 3 or more HomericIntelligence repos have broken CI on their main branch simultaneously
- Need to register fix tasks in Agamemnon before dispatching agents (audit trail + coordination)
- CI failures span diverse root causes requiring per-failure triage before dispatch
- Want to select agent tier (Haiku vs Sonnet) based on whether the root cause is already known
- Need to restore green main across the ecosystem before a cross-repo feature push

## Verified Workflow

### Quick Reference

```bash
# Step 1: Triage CI across all repos
REPOS="ProjectAgamemnon ProjectNestor ProjectKeystone ProjectCharybdis ProjectArgus ProjectHermes ProjectHephaestus ProjectOdyssey ProjectScylla ProjectMnemosyne ProjectProteus ProjectTelemachy Myrmidons AchaeanFleet"
for repo in $REPOS; do
  state=$(gh api repos/HomericIntelligence/$repo/commits/main/status --jq '.state' 2>/dev/null)
  [ "$state" != "success" ] && echo "BROKEN: $repo ($state)"
done

# Step 2: Register fix tasks in Agamemnon (use /v1/teams/<teamId>/tasks — NOT /v1/tasks)
TEAM_ID="<your-team-id>"
curl -s -X POST http://localhost:8080/v1/teams/$TEAM_ID/tasks \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"fix-<repo>-<issue>","title":"<description>","status":"pending","priority":"high"}'

# Step 3: Dispatch parallel fix agents (select tier by root cause certainty)
# Known fix + 1-3 file changes → Haiku
# Unknown root cause + investigation required → Sonnet
```

### Detailed Steps

#### Phase 1: Triage — Identify Broken Repos

Scan all repos for non-green CI status:

```bash
for repo in $REPOS; do
  # Check latest main commit status
  result=$(gh api repos/HomericIntelligence/$repo/commits/main/status \
    --jq '.state + " (" + (.statuses | length | tostring) + " checks)"' 2>/dev/null)
  echo "$repo: $result"
done
```

For each broken repo, read the failing workflow logs:

```bash
# Get the most recent failed run
gh run list --repo HomericIntelligence/$REPO --branch main --status failure --limit 1 --json databaseId --jq '.[0].databaseId'
# Read the failure log
gh run view $RUN_ID --repo HomericIntelligence/$REPO --log-failed
```

Classify each failure into one of the known patterns (see Results & Parameters below).

#### Phase 2: Register Tasks in Agamemnon

Before dispatching agents, register each fix as a task in Agamemnon for coordination and audit trail:

```bash
TEAM_ID="<your-team-id>"
AGAMEMNON="http://localhost:8080"

# Register one task per repo/failure
curl -s -X POST $AGAMEMNON/v1/teams/$TEAM_ID/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": "fix-odysseus-conan-profile",
    "title": "Odysseus build.yml: add conan profile detect step",
    "status": "pending",
    "priority": "high"
  }'
```

**Critical**: Use `/v1/teams/<teamId>/tasks` — not `/v1/tasks` (returns 404).

#### Phase 3: Dispatch Fix Agents (Tier-Selected)

Select agent tier based on root cause certainty:

| Certainty Level | Agent Tier | Example Failures |
|----------------|-----------|-----------------|
| Known fix, 1-3 file mechanical change | Haiku | conan profile detect, dependabot.yml cleanup, persist-credentials |
| Unknown root cause, investigation required | Sonnet | BATS exit 127, Python import errors, pixi cache 400 |

Dispatch agents in parallel. Each agent should:
1. Read the specific CI failure log
2. Apply the fix (see Known Fix Patterns in Results & Parameters)
3. Push to a feature branch + create PR
4. Update task status in Agamemnon to `in-progress` / `done`

#### Phase 4: Update Agamemnon Task Status

As agents complete their work, update task states:

```bash
curl -s -X PATCH $AGAMEMNON/v1/teams/$TEAM_ID/tasks/fix-odysseus-conan-profile \
  -H 'Content-Type: application/json' \
  -d '{"status": "done"}'
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `/v1/tasks` Agamemnon endpoint | `POST /v1/tasks` to register fix tasks | Returns 404 — endpoint does not exist | Correct endpoint is `/v1/teams/<teamId>/tasks` (team-scoped) |
| `bats-core/bats-action@2` in GitHub Actions | Used `bats-core/bats-action@2` to install BATS | Action version `@2` does not exist on GitHub Marketplace | Use `apt-get install bats` or `bats-core/bats-action@1` |
| `peter-evans/create-pull-request` without `persist-credentials: false` | `actions/checkout` default + `peter-evans/create-pull-request@271a8d0` | "fatal: Duplicate header: Authorization" — both steps configure git credentials independently | Add `persist-credentials: false` to the `actions/checkout` step when using `peter-evans/create-pull-request` |
| Dispatching all agents as Haiku | Used Haiku for BATS exit 127 and Python type error investigation | Haiku lacks the reasoning depth to investigate unknown root causes from log output alone | Escalate to Sonnet for failures where root cause is not already known before dispatch |
| Running `conan` directly after `setup-pixi` | Assumed `setup-pixi` initialized conan profiles | Conan 2.x requires explicit `conan profile detect` — profiles don't auto-initialize | Always add `pixi run conan profile detect` as an explicit step after `setup-pixi`, before build scripts |
| Dependabot docker block with no Dockerfiles | Kept `package-ecosystem: docker` in dependabot.yml despite no Dockerfiles | Dependabot fails hard with "dependency_file_not_found /Dockerfile" — no graceful skip | Remove `package-ecosystem: docker` blocks unless the repo actually contains Dockerfiles |

## Results & Parameters

### Known CI Failure Fix Patterns

#### Pattern 1: Conan 2.x Profile Not Initialized (Odysseus `build.yml`)

**Error**: `"The default build profile '/home/runner/.conan2/profiles/default' doesn't exist"`

**Fix**: Add `pixi run conan profile detect` after `setup-pixi`, before build script:

```yaml
- uses: prefix-dev/setup-pixi@v0.8.1
  with:
    pixi-version: latest

# ADD THIS STEP:
- name: Initialize Conan profile
  run: pixi run conan profile detect

- name: Build
  run: pixi run build
```

**Root cause**: Conan 2.x requires explicit profile initialization once per fresh environment. `setup-pixi` installs the conan binary but does not run `conan profile detect`.

---

#### Pattern 2: Duplicate Authorization Header (ProjectMnemosyne `update-marketplace.yml`)

**Error**: `"fatal: Duplicate header: Authorization"` when `peter-evans/create-pull-request` tries to push

**Fix**: Add `persist-credentials: false` to `actions/checkout`:

```yaml
- uses: actions/checkout@v4
  with:
    persist-credentials: false  # ADD THIS LINE
    fetch-depth: 0
```

**Root cause**: Both `actions/checkout` (by default) and `peter-evans/create-pull-request` configure git HTTP credentials. When both are active simultaneously, git sees duplicate Authorization headers on push. `persist-credentials: false` tells checkout not to configure credentials, letting the PR action manage them exclusively.

---

#### Pattern 3: Dependabot Docker Block with No Dockerfiles (ProjectArgus `dependabot.yml`)

**Error**: `"dependency_file_not_found /Dockerfile"`

**Fix**: Remove the `package-ecosystem: docker` block:

```yaml
# REMOVE this block if no Dockerfiles exist in the repo:
# - package-ecosystem: docker
#   directory: /
#   schedule:
#     interval: weekly
```

**Root cause**: Dependabot fails hard rather than gracefully skipping when configured to scan for Dockerfiles but none are present in the repository.

---

#### Pattern 4: BATS `run_validate` Exits 127 (Myrmidons `test_validate.bats`)

**Error**: Tests 197, 201, 203 fail with exit code 127 (command not found) for `run_validate`

**Investigation path** (Sonnet required):
1. Read `test_validate.bats` — check `load` directives at top of file
2. Verify the helper file defining `run_validate` exists at the referenced path
3. Check PATH inside the test environment (BATS `setup()` function)
4. Ensure the helper script is executable and `load` path is relative to `$BATS_TEST_DIRNAME`

**Root cause**: BATS helper function not in scope — likely bad `load` directive path or missing helper source.

---

#### Pattern 5: Python Type Errors + Import Failures (ProjectTelemachy)

**Error**: Python type errors, pixi cache 400, `telemachy.agamemnon_client` import resolution failure

**Investigation path** (Sonnet required):
1. Check for missing `__init__.py` files in the package directory
2. Verify `pyproject.toml` `[tool.setuptools.packages.find]` includes the correct source directory
3. Clear pixi cache: `pixi clean` then `pixi install`
4. Check if the module path changed (e.g., `telemachy/agamemnon_client.py` vs `src/telemachy/agamemnon_client.py`)

**Root cause**: Likely package structure issue — missing `__init__.py`, wrong module path, or stale pixi cache key causing 400 on cache fetch.

### Agent Tier Selection Table

| Failure Type | Agent Tier | Why |
|-------------|-----------|-----|
| conan profile detect missing | Haiku | Exact fix known: add 1-line step to workflow YAML |
| dependabot.yml docker block cleanup | Haiku | Exact fix known: remove block from YAML |
| persist-credentials: false missing | Haiku | Exact fix known: add 1 attribute to checkout step |
| BATS exit 127 (run_validate not found) | Sonnet | Root cause unknown — requires reading test file + load directives |
| Python type errors + import failures | Sonnet | Root cause unknown — requires package structure investigation |
| Pixi cache 400 errors | Sonnet | Environment-dependent, requires cache invalidation + diagnosis |

### Agamemnon Task Registration Template

```bash
# Template for registering a CI fix task
curl -s -X POST http://localhost:8080/v1/teams/$TEAM_ID/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": "fix-<repo-slug>-<issue-slug>",
    "title": "<Repo>: <brief description of CI failure and fix>",
    "status": "pending",
    "priority": "high",
    "metadata": {
      "repo": "HomericIntelligence/<repo>",
      "failure_type": "<conan-profile|persist-credentials|dependabot-docker|bats-exit-127|python-import>",
      "agent_tier": "<haiku|sonnet>"
    }
  }'
```

### Session Scale Reference

| Scale | Haiku Agents | Sonnet Agents | Estimated Time |
|-------|-------------|--------------|----------------|
| 1-2 repos, known fix patterns | 2 Haiku | 0 | ~10-15 min |
| 3-5 repos, mixed known/unknown | 2-3 Haiku | 2-3 Sonnet | ~30-60 min (+ CI wait) |
| 10+ repos, diverse failures | 5+ Haiku | 4+ Sonnet | ~2-4 hours (+ CI wait) |
| This session (5 repos) | 3 Haiku | 2 Sonnet | ~45-90 min |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence ecosystem | 5 repos with broken main: Odysseus, Myrmidons, ProjectMnemosyne, ProjectArgus, ProjectTelemachy — 2026-04-24 | 5 fix tasks registered in Agamemnon, 5 parallel agents dispatched (3 Haiku + 2 Sonnet); PRs in flight at capture time |

## References

- [multi-repo-pr-orchestration-swarm-pattern](multi-repo-pr-orchestration-swarm-pattern.md) — Full PR merge orchestration after fixes land
- [conan-ci-github-actions-missing-install](conan-ci-github-actions-missing-install.md) — Deep dive on conan install patterns for cmake matrix builds
- [bats-shell-testing](bats-shell-testing.md) — BATS test patterns and common failure modes
- [ci-cd-dependabot-conflict-resolution-pattern](ci-cd-dependabot-conflict-resolution-pattern.md) — Dependabot configuration patterns
