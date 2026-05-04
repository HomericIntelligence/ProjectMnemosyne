---
name: ci-cd-broken-main-parallel-fix-wave
description: "Triage and fix broken CI/main across multiple repos simultaneously using Agamemnon task registry + parallel myrmidon fix agents. Use when: (1) 3+ repos have broken main branch CI, (2) need to register tasks in Agamemnon before dispatching agents, (3) CI failures are diverse (conan profile, dependabot config, GitHub Actions auth, BATS helper, Python imports, clang-format violations, annotated-tag SHA pinning, stale pixi.lock, markdownlint CHANGELOG exclusion, release.yml direct push to main, duplicate module re-export, Pydantic model_dump bypass)."
category: ci-cd
date: 2026-05-03
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: ci-cd-broken-main-parallel-fix-wave.history
tags: [ci, broken-main, agamemnon, parallel-agents, myrmidon, conan, dependabot, bats, github-actions, fix-wave, clang-format, monitor, annotated-tags, sha-pinning, pixi-lock, markdownlint, changelog, rebase-onto, transient-vs-reproducible, issue-triage, all-repos, release-workflow, circuit-breaker, pydantic, model-dump, deprecation-shim]
---

# CI Broken-Main Parallel Fix Wave

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Use the HomericIntelligence agent mesh to fix broken CI/main across multiple repositories simultaneously — NATS + Agamemnon task registry + parallel Claude Code sub-agents as myrmidon workers |
| **Outcome** | Successful — all 14 repos triaged, 6 root causes identified across 4 repos, 4 fix PRs opened with auto-merge, 2 issues filed without PRs (non-trivial scope / transient-confirmed network failures) |
| **Verification** | verified-ci — fix PRs opened and auto-merge armed; patterns verified by reproducing failures locally |
| **History** | [changelog](./ci-cd-broken-main-parallel-fix-wave.history) |

## When to Use

- 3 or more HomericIntelligence repos have broken CI on their main branch simultaneously
- Need to register fix tasks in Agamemnon before dispatching agents (audit trail + coordination)
- CI failures span diverse root causes requiring per-failure triage before dispatch
- Want to select agent tier (Haiku vs Sonnet) based on whether the root cause is already known
- Need to restore green main across the ecosystem before a cross-repo feature push
- Full 14-repo health sweep needed (e.g. before a large cross-repo release or audit)
- Release workflow directly pushes version bump to `main` (branch protection violation)
- Duplicate module re-export causing import conflicts in Python packages
- Pydantic models using manual `to_dict()` with field enumerations instead of `model_dump()`

## Verified Workflow

### Quick Reference

```bash
# Step 0 (fast): List all 14 submodule repos from .gitmodules
grep 'url = ' .gitmodules | awk '{print $3}' | sed 's|.*/||'

# Step 1: Triage CI across all repos — use workflow run list (more reliable than commit status)
REPOS="ProjectAgamemnon ProjectNestor ProjectKeystone ProjectCharybdis ProjectArgus ProjectHermes ProjectHephaestus ProjectOdyssey ProjectScylla ProjectMnemosyne ProjectProteus ProjectTelemachy Myrmidons AchaeanFleet"
for repo in $REPOS; do
  echo "=== $repo ==="
  gh run list --repo HomericIntelligence/$repo --branch main --limit 2 \
    --json conclusion,headBranch,workflowName,createdAt \
    --jq '.[] | select(.headBranch=="main") | "\(.workflowName): \(.conclusion)"'
done

# Step 2: Drill into each failure
gh run view <run_id> --repo HomericIntelligence/<repo> --log-failed 2>&1 | \
  grep -E "::error|Error:|FAILED" | head -20

# Step 3: Confirm transient vs reproducible BEFORE filing anything
gh run rerun <run_id> --failed --repo HomericIntelligence/<repo>
gh run watch <new_run_id> --repo HomericIntelligence/<repo>
# If new run also fails → reproducible → file issue + open PR
# If new run passes → transient → no action

# Step 4: Register fix tasks in Agamemnon (use /v1/teams/<teamId>/tasks — NOT /v1/tasks)
TEAM_ID="<your-team-id>"
curl -s -X POST http://localhost:8080/v1/teams/$TEAM_ID/tasks \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"fix-<repo>-<issue>","title":"<description>","status":"pending","priority":"high"}'

# Step 5: Dispatch parallel fix agents (select tier by root cause certainty)
# Known fix + 1-3 file changes → Haiku
# Unknown root cause + investigation required → Sonnet
```

### Detailed Steps

#### Phase 0: Enumerate All Repos

Parse `.gitmodules` for the canonical list — don't hardcode:

```bash
grep 'url = ' .gitmodules | awk '{print $3}' | sed 's|.*/||'
```

#### Phase 1: Triage — Identify Broken Repos

Use `gh run list` (more reliable than `commits/main/status` for fresh runs):

```bash
for repo in $REPOS; do
  echo "=== $repo ==="
  gh run list --repo HomericIntelligence/$repo --branch main --limit 2 \
    --json conclusion,headBranch,workflowName,createdAt \
    --jq '.[] | select(.headBranch=="main") | "\(.workflowName): \(.conclusion)"'
done
```

For each broken repo, drill into the failing log:

```bash
# Get the most recent failed run
gh run list --repo HomericIntelligence/$REPO --branch main --status failure --limit 1 --json databaseId --jq '.[0].databaseId'
# Read the failure log
gh run view $RUN_ID --repo HomericIntelligence/$REPO --log-failed
```

Classify each failure into one of the known patterns (see Results & Parameters below).

#### Phase 1b: Transient vs Reproducible Triage

**CRITICAL**: Re-run every failing job before filing an issue or PR:

```bash
gh run rerun <run_id> --failed --repo HomericIntelligence/<repo>
gh run watch <new_run_id> --repo HomericIntelligence/<repo>
```

- New run also fails with same error → **reproducible** → file issue + open PR
- New run passes → **transient** → no issue, no PR (note in triage log)

**Example transient**: Agamemnon `schema-validation` failed HTTP 503 from json.schemastore.org. Two re-runs also failed → elevated to "persistent" → filed issue recommending schema vendoring (no PR needed — fix requires deliberate design).

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
| ---------------- | ----------- | ----------------- |
| Known fix, 1-3 file mechanical change | Haiku | conan profile detect, dependabot.yml cleanup, persist-credentials, annotated-tag SHA fix, pixi.lock regen, markdownlint CHANGELOG |
| Unknown root cause, investigation required | Sonnet | BATS exit 127, Python import errors, pixi cache 400, schema validation network errors |

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
| --------- | ---------------- | --------------- | ---------------- |
| `/v1/tasks` Agamemnon endpoint | `POST /v1/tasks` to register fix tasks | Returns 404 — endpoint does not exist | Correct endpoint is `/v1/teams/<teamId>/tasks` (team-scoped) |
| `bats-core/bats-action@2` in GitHub Actions | Used `bats-core/bats-action@2` to install BATS | Action version `@2` does not exist on GitHub Marketplace | Use `apt-get install bats` or `bats-core/bats-action@1` |
| `peter-evans/create-pull-request` without `persist-credentials: false` | `actions/checkout` default + `peter-evans/create-pull-request@271a8d0` | "fatal: Duplicate header: Authorization" — both steps configure git credentials independently | Add `persist-credentials: false` to the `actions/checkout` step when using `peter-evans/create-pull-request` |
| Dispatching all agents as Haiku | Used Haiku for BATS exit 127 and Python type error investigation | Haiku lacks the reasoning depth to investigate unknown root causes from log output alone | Escalate to Sonnet for failures where root cause is not already known before dispatch |
| Running `conan` directly after `setup-pixi` | Assumed `setup-pixi` initialized conan profiles | Conan 2.x requires explicit `conan profile detect` — profiles don't auto-initialize | Always add `pixi run conan profile detect` as an explicit step after `setup-pixi`, before build scripts |
| Dependabot docker block with no Dockerfiles | Kept `package-ecosystem: docker` in dependabot.yml despite no Dockerfiles | Dependabot fails hard with "dependency_file_not_found /Dockerfile" — no graceful skip | Remove `package-ecosystem: docker` blocks unless the repo actually contains Dockerfiles |
| Running local clang-format on C++ PRs | Used system clang-format-14 on Debian 11 dev host to reformat before push | CI uses clang-format-18 on ubuntu-24.04; version differences produce divergent formatting decisions | Always use `podman run ubuntu:24.04` with the exact CI clang-format version — never the local system version |
| Monitor filter emitting only on success | Set monitor `filter="conclusion == 'success'"` for CI polling | If the run fails, filter never emits — silence is indistinguishable from "still running" | Monitor filter MUST include failure: `conclusion == 'failure' OR conclusion == 'success'` |
| 30s monitor poll for release builds | Used 30s poll interval for long-running C++ release CI | Generates 60+ noisy notifications during a 30-minute build; distracts from other work | Use 60s interval for release builds; 30s only for fast checks (lint, pre-commit) |
| `gh api repos/<owner>/<repo>/commits/<tag>` for SHA resolution | Used the `commits` endpoint to resolve an annotated tag to a commit SHA | Returns HTTP 422 — annotated tag object SHA is not a commit SHA; `commits/` endpoint rejects it | Use `git/ref/tags/<tag>` + check `.object.type`; if type=`tag`, dereference via `git/tags/<sha>` |
| `.markdownlintignore` alone for CHANGELOG exclusion | Added CHANGELOG.md to `.markdownlintignore` | Only works when markdownlint discovers files via glob, not when files are passed as explicit args | Must also add `!CHANGELOG.md` directly to workflow glob — see Pattern 8 for three-layer exclusion |
| `ignorePatterns` in `.markdownlint-cli2.jsonc` alone for CHANGELOG | Added CHANGELOG.md to `ignorePatterns` | CI used markdownlint-cli2 v0.17.2 which did not honor `ignorePatterns`; local v0.22.1 did | Always add `!CHANGELOG.md` to workflow globs directly — most reliable across all CLI versions |
| `git rebase origin/main` on a branch with already-merged commits | Used direct rebase when branch contained commits already merged to main | Caused conflicts on the duplicate commits | Use `git rebase --onto origin/main <sha-before-first-unique-commit> <branch>` to replay only unique commits |
| Filing issues without first re-running CI | Filed issues immediately after observing a red CI run | Some failures were transient (network errors, timing); issue was unnecessary | Always re-run the failing job first; only file an issue if the new run also fails |
| Release workflow direct push to `main` | `release.yml` pushed version bump commit directly to `main` | Branch protection rules block direct pushes; workflow fails with 403 | Push version bump to `release/version-bump-${{ env.VERSION }}` branch and open a PR via `gh pr create` + `gh pr merge --auto --rebase`; add `pull-requests: write` permission to the workflow |
| Duplicate circuit-breaker re-export | Had `automation/circuit_breaker.py` as a full duplicate of `scylla.core.circuit_breaker` | Import conflicts when both paths are in scope; maintenance burden of two copies | Convert the duplicate to a DeprecationWarning shim that re-imports from the canonical location |
| Manual `to_dict()` with field enumerations | 14 Pydantic model methods manually enumerated every field in `to_dict()` | Broke when new fields added (silently omitted); no consistency guarantee | Replace manual field enumerations with `self.model_dump(mode='json')`; inject computed `@property` values post-dump; use `exclude=` for ephemeral runtime fields |

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

---

#### Pattern 6: clang-format Version Mismatch (C++ PRs after CI run)

**Error**: CI reports `clang-format: would reformat <file>` after otherwise passing build/test/tidy steps.

**Root cause**: Developer ran `clang-format` locally using a different version (e.g., clang-format-14 on Debian
11) than CI (clang-format-18 on ubuntu-24.04). Version differences produce divergent formatting decisions.

**Fix**: Use `podman run` with the exact CI base image to reformat:

```bash
# Install exact CI clang-format version via ubuntu-24.04 container
podman run --rm -v $(pwd):/src ubuntu:24.04 bash -c "
  apt-get update -qq && apt-get install -y clang-format-18 2>/dev/null
  cd /src
  clang-format-18 -i \$(git diff --name-only origin/main..HEAD | grep -E '\.(cpp|cc|h|hpp)$')
"

# Commit the style fix and push to the existing branch
git add -u
git commit -m "style: apply clang-format to <feature-name>"
git push  # No new PR needed — existing PR picks up the new commit
```

**Agent tier**: Haiku — once pattern is identified from CI logs, the fix is mechanical.

---

#### Pattern 7: Annotated Tag SHA Pinning Failure (any workflow with `uses: owner/repo@<bad-sha>`)

**Error**: HTTP 422 from GitHub when resolving a `uses:` SHA that is a tag object SHA, not a commit SHA.

**Root cause**: Annotated tags require two-step resolution. The `git/ref/tags/<tag>` API returns the tag object SHA (type `"tag"`), not the commit SHA. Using the tag object SHA in `uses:` causes GitHub to reject it.

**Fix** (Haiku-tier — exact pattern):

```bash
# Step 1: Resolve tag
TAG_INFO=$(gh api "repos/<owner>/<repo>/git/ref/tags/<tag>" --jq '.object | {sha, type}')
SHA=$(echo "$TAG_INFO" | jq -r '.sha')
TYPE=$(echo "$TAG_INFO" | jq -r '.type')

# Step 2: If annotated (type=tag), dereference to commit SHA
if [ "$TYPE" = "tag" ]; then
  SHA=$(gh api "repos/<owner>/<repo>/git/tags/$SHA" --jq '.object.sha')
fi

echo "Pin to: uses: <owner>/<repo>@$SHA  # <tag>"
```

**Example**: `prefix-dev/setup-pixi@v0.8.1` → type=tag (annotated) → dereference → `ba3bb36eb2066252b2363392b7739741bb777659`

**Failed approach**: `gh api repos/<owner>/<repo>/commits/<tag>` — returns HTTP 422 for annotated tags.

---

#### Pattern 8: markdownlint CHANGELOG.md Exclusion

**Error**: markdownlint CI fails on CHANGELOG.md due to MD024 (duplicate headings: "Added", "Changed", "Fixed" repeat across version sections) and MD013 (long URLs).

**Root cause**: CHANGELOGs intentionally repeat section headings across version blocks. markdownlint does not know the difference between a CHANGELOG structure and a duplicate heading mistake.

**Fix** — Three-layer exclusion for reliability:

**`.markdownlintignore`** (works for glob-discovered files only):
```
CHANGELOG.md
```

**`.markdownlint-cli2.jsonc`** (works for some CLI versions):
```json
{
  "ignorePatterns": [
    "CHANGELOG.md",
    ".pixi/**"
  ]
}
```

**Workflow glob** (most reliable — always add this):
```yaml
- uses: DavidAnson/markdownlint-cli2-action@<sha>  # v<version>
  with:
    globs: |
      **/*.md
      !CHANGELOG.md
      !.pixi/**
      !.claude/**
```

**Key lesson**: Always add `!CHANGELOG.md` directly to the workflow glob. `.markdownlintignore` only works when markdownlint discovers files via glob; it does NOT apply when files are passed as explicit arguments. Local CLI v0.22.1 honors `ignorePatterns`; CI version v0.17.2 did not.

**Agent tier**: Haiku — three-layer exclusion pattern is mechanical once identified.

---

#### Pattern 9: Stale pixi.lock After pixi.toml Update

**Error**: `pixi install --locked` fails in CI with "lock-file not up-to-date with the workspace"

**Root cause**: `pixi.toml` was updated (new deps added, versions changed) but `pixi.lock` was never regenerated.

**Fix**:
```bash
cd <repo>
pixi install         # regenerates pixi.lock without --locked
git add pixi.lock
git commit -m "fix(ci): regenerate pixi.lock to sync with pixi.toml"
git push
```

**Note**: `pixi install` (no flags) always regenerates. Never use `--locked` in the local fix command — it hard-fails if out of sync.

**Agent tier**: Haiku — once the symptom is matched, the fix is one command.

---

### Transient vs Reproducible Decision Tree

```
CI run is red on main
   │
   ▼
gh run rerun <id> --failed --repo <org>/<repo>
   │
   ├─ New run PASSES → TRANSIENT → no action (note in triage log)
   │
   └─ New run FAILS with same error → REPRODUCIBLE
         │
         ├─ Fix is trivial (1-3 files, known pattern) → open PR
         └─ Fix requires design (network deps, schema vendoring) → file issue only
```

**Known persistent non-code failures**: External service HTTP 503 (json.schemastore.org, registry endpoints). These persist across re-runs but are infrastructure issues — file issues recommending vendoring or mirroring, do not attempt to "fix" the workflow.

---

### Ecosystem Health Check (All 14 Repos)

Full 14-repo triage pattern for a HomericIntelligence audit:

```bash
# Parse canonical repo list from .gitmodules
REPOS=$(grep 'url = ' .gitmodules | awk '{print $3}' | sed 's|.*/||')

# Check each repo — quick pass
for repo in $REPOS; do
  echo "=== $repo ==="
  gh run list --repo HomericIntelligence/$repo --branch main --limit 2 \
    --json conclusion,headBranch,workflowName,createdAt \
    --jq '.[] | select(.headBranch=="main") | "\(.workflowName): \(.conclusion)"'
done

# Drill into a failure
gh run view <run_id> --repo HomericIntelligence/<repo> --log-failed 2>&1 | \
  grep -E "::error|Error:|FAILED" | head -20
```

---

### git rebase --onto for Branches with Already-Merged Commits

When a PR branch contains commits already merged to main (from a predecessor PR), direct `git rebase origin/main` causes conflicts on the duplicate commits. Use `--onto`:

```bash
# Show which commits are unique (not on main)
git log --oneline origin/main..HEAD

# Find the SHA of the last commit that is NOT unique (last shared commit)
git log --oneline <branch>  # find the SHA just before the first unique commit

# Replay only the unique commits onto main
git rebase --onto origin/main <sha-before-first-unique-commit> <branch-name>
```

**When to use**: Branch has N commits already merged to main + M additional unique commits. `--onto` replays only the M unique commits.

---

### GitHub Issue Filing Template

For each confirmed reproducible root cause:

```bash
gh issue create --repo HomericIntelligence/<repo> \
  --title "ci(main): <one-line summary>" \
  --label "bug,ci" \
  --body "$(cat <<'EOF'
## Symptom

Run <link>: \`<error message>\`

## Reproduction

\`\`\`bash
<exact local reproduction command>
\`\`\`

## Root cause

<1-3 sentences>

## Proposed fix

<description or link to PR>

## Affected workflows

- \`<workflow file>\` → \`<job name>\`
EOF
)"
```

**Labels**: Create `ci` label if missing:
```bash
gh label create ci --color 0075ca --repo HomericIntelligence/<repo>
```

---

---

#### Pattern 10: Release Workflow Direct Push to Main (ProjectScylla #1878)

**Error**: Release workflow fails with 403 -- branch protection blocks direct push to `main`

**Root cause**: The workflow commits a version bump directly to `main` rather than opening a PR.

**Fix**: Push version bump to a release branch and open a PR with auto-merge:

```yaml
# In release.yml -- replace direct push with PR flow
- name: Push version bump
  run: |
    git checkout -b release/version-bump-${{ env.VERSION }}
    git add pyproject.toml
    git commit -m "chore: bump version to ${{ env.VERSION }}"
    git push -u origin release/version-bump-${{ env.VERSION }}

- name: Open and auto-merge version bump PR
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    gh pr create \
      --title "chore: bump version to ${{ env.VERSION }}" \
      --body "Automated version bump from release workflow." \
      --base main \
      --head release/version-bump-${{ env.VERSION }}
    PR_NUM=$(gh pr list --head release/version-bump-${{ env.VERSION }} --json number --jq '.[0].number')
    gh pr merge "$PR_NUM" --auto --rebase
```

**Also required**: Add `pull-requests: write` to the workflow permissions block:

```yaml
permissions:
  contents: write
  pull-requests: write  # ADD THIS
```

**Tag push** (`git push origin "${{ env.VERSION }}"`) is fine to keep as-is -- tags bypass branch protection.

**Agent tier**: Haiku -- exact pattern once the 403 error is identified.

---

#### Pattern 11: Duplicate Module Re-Export (Python -- DeprecationWarning Shim)

**Error**: Two modules export the same class from different paths, causing import conflicts or
maintenance burden when one is updated.

**Root cause**: `automation/circuit_breaker.py` was a full copy of `scylla.core.circuit_breaker`,
not a re-export. Updates to the canonical location were not reflected in the duplicate.

**Fix**: Convert the duplicate to a DeprecationWarning shim:

```python
# automation/circuit_breaker.py  -- shim, not a copy
import warnings
from scylla.core.circuit_breaker import CircuitBreaker, CircuitBreakerError  # noqa: F401

warnings.warn(
    "Import from 'automation.circuit_breaker' is deprecated. "
    "Use 'scylla.core.circuit_breaker' instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Rules**:
- Keep the shim in place for at least one release cycle to avoid breaking callers
- Only re-export names that are part of the public API (use `__all__` if needed)
- The canonical location owns the implementation; the shim owns nothing

**Agent tier**: Haiku -- pattern is mechanical once the duplicate is identified.

---

#### Pattern 12: Pydantic model_dump() Replacing Manual to_dict()

**Error**: Manual `to_dict()` methods silently omit new fields when the model grows; consistency
breaks across the codebase.

**Root cause**: 14 Pydantic model methods manually enumerated every field:

```python
# Before (brittle):
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "name": self.name,
        "status": self.status,
        # ... 11 more fields, easily forgotten when model grows
    }
```

**Fix**: Replace with `model_dump()`:

```python
# After (complete and consistent):
def to_dict(self) -> dict:
    base = self.model_dump(mode='json')

    # Inject computed @property values not in model fields:
    base["display_name"] = self.display_name

    return base
```

**Special cases**:
- Computed `@property` values not stored as model fields: inject post-dump
- Ephemeral runtime fields that should NOT be serialized: use `exclude={"_lock", "_connection"}`

```python
base = self.model_dump(mode='json', exclude={"_lock", "_connection"})
```

**Agent tier**: Haiku -- once the pattern is identified, the replacement is mechanical.
Use `grep -r "def to_dict" --include="*.py"` to find all instances.

---

### Monitor Noise Reduction Pattern

When polling CI status for long-running release builds, 30-second poll intervals cause excessive
notifications. Recommended approach:

```bash
# Stop a noisy monitor
TaskStop <monitor-id>

# Re-arm with tighter filter (emit on FAILURE too, not just success)
# and longer poll interval for release builds
Monitor(
    filter="conclusion == 'failure' OR conclusion == 'success'",
    interval_seconds=60
)
```

**Rules:**
- Use 30s poll for fast checks (lint, pre-commit). Use 60s for release/build CI runs.
- Monitor filter MUST emit on FAILURE too — `conclusion == 'success'` only causes silent misses
  if the run fails. Silence does NOT mean "still running".
- If a monitor produces too much noise: `TaskStop` the old one, re-arm with longer interval.

### Agent Tier Selection Table

| Failure Type | Agent Tier | Why |
| ------------- | ----------- | ----- |
| conan profile detect missing | Haiku | Exact fix known: add 1-line step to workflow YAML |
| dependabot.yml docker block cleanup | Haiku | Exact fix known: remove block from YAML |
| persist-credentials: false missing | Haiku | Exact fix known: add 1 attribute to checkout step |
| clang-format violations | Haiku | Once CI version identified, fix is mechanical: podman reformat + `style:` commit |
| annotated-tag SHA pinning (HTTP 422) | Haiku | Exact two-step resolution pattern known |
| pixi.lock stale after pixi.toml update | Haiku | One command to regenerate: `pixi install` |
| markdownlint CHANGELOG exclusion | Haiku | Three-layer exclusion pattern is mechanical |
| BATS exit 127 (run_validate not found) | Sonnet | Root cause unknown — requires reading test file + load directives |
| Python type errors + import failures | Sonnet | Root cause unknown — requires package structure investigation |
| Pixi cache 400 errors | Sonnet | Environment-dependent, requires cache invalidation + diagnosis |
| External service HTTP 5xx (schema, registry) | Issue only | Infrastructure dependency -- not a code fix |
| Release workflow direct push to main (403) | Haiku | Exact PR flow known: release branch + gh pr create + auto-merge |
| Duplicate module re-export (DeprecationWarning shim) | Haiku | Shim pattern is mechanical once duplicate identified |
| Manual to_dict() with field enumerations | Haiku | Replace with model_dump(mode='json') -- exact pattern known |

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
      "failure_type": "<conan-profile|persist-credentials|dependabot-docker|bats-exit-127|python-import|clang-format|annotated-tag-sha|pixi-lock|markdownlint-changelog|external-service>",
      "agent_tier": "<haiku|sonnet>"
    }
  }'
```

### Session Scale Reference

| Scale | Haiku Agents | Sonnet Agents | Estimated Time |
| ------- | ------------- | -------------- | ---------------- |
| 1-2 repos, known fix patterns | 2 Haiku | 0 | ~10-15 min |
| 3-5 repos, mixed known/unknown | 2-3 Haiku | 2-3 Sonnet | ~30-60 min (+ CI wait) |
| 10+ repos, diverse failures | 5+ Haiku | 4+ Sonnet | ~2-4 hours (+ CI wait) |
| 5 repos (2026-04-24 session) | 3 Haiku | 2 Sonnet | ~45-90 min |
| 14 repos / 4 broken (2026-05-01 session) | 4 Haiku | 0 Sonnet | ~2 hours (+ CI wait) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence ecosystem | 5 repos with broken main: Odysseus, Myrmidons, ProjectMnemosyne, ProjectArgus, ProjectTelemachy — 2026-04-24 | 5 fix tasks registered in Agamemnon, 5 parallel agents dispatched (3 Haiku + 2 Sonnet); PRs in flight at capture time |
| HomericIntelligence ecosystem | All 14 repos triaged -- 2026-05-01 | 4 repos red, 6 root causes identified, 4 fix PRs opened with auto-merge, 2 issues filed (non-trivial: schema vendoring, transient-confirmed); verified-ci |
| HomericIntelligence/ProjectScylla | Issues #1878, #1868, #1869 -- 2026-05-03 | release.yml direct-push fix (PR flow + auto-merge); circuit-breaker DeprecationWarning shim; 14 model_dump() replacements; verified-ci |

## References

- [multi-repo-pr-orchestration-swarm-pattern](multi-repo-pr-orchestration-swarm-pattern.md) — Full PR merge orchestration after fixes land
- [conan-ci-github-actions-missing-install](conan-ci-github-actions-missing-install.md) — Deep dive on conan install patterns for cmake matrix builds
- [bats-shell-testing](bats-shell-testing.md) — BATS test patterns and common failure modes
- [ci-cd-dependabot-conflict-resolution-pattern](ci-cd-dependabot-conflict-resolution-pattern.md) — Dependabot configuration patterns
- [ci-cd-github-actions-sha-pinning](ci-cd-github-actions-sha-pinning.md) — Deep dive on annotated vs lightweight tag resolution
- [markdownlint-troubleshooting](markdownlint-troubleshooting.md) — markdownlint CI unblocking patterns
- [ci-cd-pixi-lock-stale-multi-pr-triage](ci-cd-pixi-lock-stale-multi-pr-triage.md) — Cross-repo pixi.lock remediation at scale
