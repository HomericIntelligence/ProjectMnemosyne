---
name: ci-cd-achaean-fleet-ci-cascade-patterns
description: "AchaeanFleet Docker infrastructure CI cascade failure sequence and fixes. Use when: (1) running a myrmidon swarm on HomericIntelligence/AchaeanFleet, (2) diagnosing cascading CI failures in a Docker image build pipeline, (3) fixing base-image ENTRYPOINT, OCI multi-arch build, vendor download URL, YAML column-0, caddy overlay, branch-protection push, or required-signatures ruleset / signed-commit merge-block issues in AchaeanFleet vessels."
category: ci-cd
date: 2026-05-18
version: "2.1.0"
history: ci-cd-achaean-fleet-ci-cascade-patterns.history
user-invocable: false
verification: verified-ci
tags: [achaeanfleet, docker, ci-cascade, multi-arch, oci, opencode, goose, entrypoint, qemu, caddy, yaml, branch-protection, required-signatures, branch-rulesets, signed-commits, force-with-lease, auto-merge-disarm]
---

# CI/CD: AchaeanFleet CI Cascade Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Document the ordered cascade of CI failures encountered in AchaeanFleet myrmidon swarm sessions so future sessions can fix them in sequence without wasted iteration |
| **Outcome** | Successful — 13 open PRs → 0 open PRs; ~10 issues implemented; cascade sequence fully mapped |
| **Verification** | verified-ci |

AchaeanFleet (`HomericIntelligence/AchaeanFleet`) is an infrastructure-only Docker image repo
for the HomericIntelligence agent mesh. It builds 3 base images and 9+ vessel images. When
CI is broken, failures are cascading — fixing one reveals the next. This skill documents the
observed order and exact fix for each layer.

## When to Use

- Starting a myrmidon swarm or implementation sprint on AchaeanFleet
- CI is red and the error message points to Docker build, ENTRYPOINT check, version pin test, or multi-arch build
- A vessel Dockerfile's tool download URL returns 404
- Multi-arch build fails with `oci-layout://` reference errors
- `goose --version || true` is hiding a real build failure
- YAML `ScannerError: could not find expected ':'` in a `run: |` block containing Python or other source at column 0
- `docker compose config` fails with `service "X" depends on undefined service "caddy"`
- GitHub Actions bot cannot push to main due to branch protection (`GH006: Protected branch update failed`)

## Verified Workflow

### Quick Reference

```bash
# 1. Check YAML syntax first (prevents all subsequent failures)
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"

# 2. Check base image references in vessel Dockerfiles
grep "FROM\|ARG BASE_IMAGE" vessels/*/Dockerfile

# 3. Verify all three bases have ENTRYPOINT
grep "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal

# 4. Check OCI output path (must be .tar, then extract to directory)
grep "type=oci,dest=" dagger/pipeline.ts .github/workflows/ci.yml

# 5. Verify opencode download URL
grep -r "opencode" vessels/opencode/Dockerfile

# 6. Check for || true masking real failures
grep "|| true" vessels/*/Dockerfile

# 7. Check all compose commands include caddy overlay
grep "docker compose" .github/workflows/ci.yml | grep -v "docker-compose.caddy.yml"

# 8. When a PR is mergeStateStatus=BLOCKED but all checks pass, inspect rulesets
#    (legacy branch-protection endpoint will look empty — misleading)
gh api repos/HomericIntelligence/AchaeanFleet/rules/branches/main \
  --jq '[.[] | {type, parameters}]'
```

### Detailed Steps

**The cascade failure order** (fix each in sequence — each fix reveals the next):

#### Level 1: YAML Syntax Errors

Immediate failure before any job runs.

```bash
# Fix: validate YAML before pushing
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"
# Also check compose files
python3 -c "import yaml; yaml.safe_load(open('compose/docker-compose.mesh.yml')); print('OK')"
```

#### Level 1.5: YAML Literal Block Scalar Column-0 Bug

When `run: |` blocks contain Python code (or any multiline content) with source lines at
column 0, the YAML parser interprets those lines as new top-level mapping keys and throws
`ScannerError: could not find expected ':'`.

**Example of broken config:**
```yaml
- name: Check something
  run: |
    python3 -c "
import yaml, sys       ← column 0! YAML parser breaks here
d = yaml.safe_load(sys.stdin)
"
```

**The fix** — either collapse to single line:
```yaml
run: python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin)"
```

Or write the Python to a temp file with `printf`:
```yaml
run: |
  printf '%s\n' \
    'import yaml,sys' \
    'd=yaml.safe_load(sys.stdin)' \
    > /tmp/check.py
  docker compose ... | python3 /tmp/check.py
```

The `printf` approach is also required if the single-line version would exceed 160 chars
(yamllint's line-length limit in this repo).

#### Level 2: Docker Build Failures — Wrong Base Image References

Vessel Dockerfiles may reference a base that was renamed or doesn't match the matrix.

```dockerfile
# Pattern: vessel must declare ARG BASE_IMAGE and use it
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
```

#### Level 3: Version Pin Test Failures

`test_dockerfile_pins.py` and `test_dockerfile_version_pins.py` enforce that every
`apt-get install` line uses `package=version` pins, not bare package names.

```bash
# Find unpinned installs
grep -n "apt-get install" bases/Dockerfile.* vessels/*/Dockerfile | grep -v "=[0-9]"
# Fix: pin every package with =version suffix
```

#### Level 4: Compose Validation Failures

Missing `depends_on`, bad volume mount paths, or unlisted services.

```bash
# Validate compose files (always include caddy overlay — see Level 4.5)
docker compose \
  -f compose/docker-compose.caddy.yml \
  -f compose/docker-compose.mesh.yml \
  config --quiet
```

#### Level 4.5: Compose Caddy Overlay Required

`docker-compose.claude-only.yml` and `docker-compose.mesh.yml` define services with
`depends_on: caddy`, but caddy itself is only defined in `docker-compose.caddy.yml`.
Every `docker compose config` or `docker compose up` command that references either file
MUST include the caddy overlay first, or it fails with:
```
service "X" depends on undefined service "caddy"
```

**Affects ALL of these steps in the `validate` job:**
- `Validate claude-only compose`
- `Validate mesh compose`
- `Validate compose services have logging configured` (both claude-only and mesh calls)
- `Assert security hardening in all compose services` (both calls)
- `Verify secrets not hardcoded in compose config` (both calls)

**Correct pattern:**
```bash
docker compose \
  -f compose/docker-compose.caddy.yml \
  -f compose/docker-compose.claude-only.yml \
  config --quiet
```

When the cap_drop security check reads YAML via Python, also switch from reading raw files
to piping `docker compose config` through stdin — raw files don't merge the caddy overlay:
```bash
docker compose \
  -f compose/docker-compose.caddy.yml \
  -f "$compose_file" \
  config | python3 /tmp/cap_drop_check.py  # reads from stdin
```

#### Level 5: "Verify ENTRYPOINT is set" Failures

**Critical**: All three base images MUST have `ENTRYPOINT`. The CI check runs on ALL bases.

```dockerfile
# All three of these files need this line:
# bases/Dockerfile.node
# bases/Dockerfile.python    ← commonly missing
# bases/Dockerfile.minimal   ← commonly missing
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
# Verify
grep "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal
# Expected: all three should show: ENTRYPOINT ["/entrypoint.sh"]
```

#### Level 6: Multi-Arch Build Failures — OCI Tarball + Extract Pattern

**v1.0.0 was WRONG here.** The `oci-layout://` protocol requires a **directory** with
`index.json` and `blobs/`. `docker/build-push-action` always writes a **tarball** when
`dest` does not end in `/`. Extensionless paths still produce a tarball — not a directory.

**What also fails with trailing slash:** `dest=/tmp/foo/` causes `build-push-action` to
pre-create `/tmp/foo/` as a directory, then buildx tries to write a tarball to that path
→ `open /tmp/foo/: is a directory` error.

**The correct pattern — tarball + explicit extract:**

```yaml
# Step 1: export as tarball (.tar extension is explicit and clear)
- name: Build minimal base (amd64 + arm64)
  uses: docker/build-push-action@...
  with:
    platforms: linux/amd64,linux/arm64
    outputs: type=oci,dest=/tmp/achaean-base-minimal.tar

# Step 2: extract to OCI layout directory
- name: Extract OCI tarball to layout directory
  run: |
    mkdir -p /tmp/achaean-base-minimal
    tar -xf /tmp/achaean-base-minimal.tar -C /tmp/achaean-base-minimal

# Step 3: reference as oci-layout:// pointing at the directory
- name: Build goose vessel (amd64 + arm64)
  uses: docker/build-push-action@...
  with:
    platforms: linux/amd64,linux/arm64
    build-contexts: |
      achaean-base-minimal:latest=oci-layout:///tmp/achaean-base-minimal
```

**Cleanup pattern:**
```yaml
- name: Clean up OCI layout directory
  if: always()
  run: rm -rf /tmp/achaean-base-minimal.tar /tmp/achaean-base-minimal
```

**Additional note — `build-goose-multiarch` is NOT a matrix job:** Any
`${{ matrix.vessel.name }}` references copied from the matrix `build-vessels` job are
stale and will fail. The goose multiarch job builds `achaean-goose:latest` specifically
and does not need a `docker save` + artifact upload (it's a CI verification build, not
an artifact-producing build). Remove all matrix variable references from this job.

QEMU must also be registered before buildx for multi-arch builds:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3   # MUST come before setup-buildx
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```

#### Level 7: opencode Download URL Wrong

The opencode vessel downloads a binary release. The asset name changed between versions.

```dockerfile
# WRONG (asset does not exist):
ARG OPENCODE_VERSION=0.1.x
RUN curl -fsSL "https://github.com/sst/opencode/releases/download/v${OPENCODE_VERSION}/opencode_linux_amd64.tar.gz"

# CORRECT (actual asset name as of 2026-04):
RUN curl -fsSL "https://github.com/sst/opencode/releases/download/v${OPENCODE_VERSION}/opencode-linux-x64.tar.gz"
```

Always verify release asset names:

```bash
gh release view v<VERSION> --repo sst/opencode --json assets --jq '.[].name'
```

#### Level 8: `|| true` Masking Real Failures

`goose --version || true` (and similar patterns) hides build errors on non-amd64 architectures.
Once QEMU is correctly set up, these suppressions must be removed.

```dockerfile
# Before (masks failures):
RUN goose --version || true

# After (correct — binary must work):
RUN goose --version
```

#### Level 9: GitHub Actions Branch Protection — Bot Cannot Push to main

When a GitHub Actions workflow tries to `git push origin main` (or push directly to the
protected branch), it fails with:
```
remote: error: GH006: Protected branch update failed, at least N reviews required.
```

Even bot users (`github-actions[bot]`) cannot bypass branch protection with a direct push.

**The correct pattern — bot opens PR + auto-merges:**
```yaml
- name: Open PR for CHANGELOG update
  if: steps.check_changes.outputs.changed == 'true'
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    BRANCH="chore/changelog-$(date -u +%Y%m%d-%H%M%S)"
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git checkout -b "$BRANCH"
    git add CHANGELOG.md
    git commit -m "docs: update CHANGELOG.md [skip ci]"
    git push -u origin "$BRANCH"
    PR_URL=$(gh pr create \
      --title "docs: update CHANGELOG.md" \
      --body "Automated CHANGELOG update generated by git-cliff." \
      --base main --head "$BRANCH")
    PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
    gh pr merge "$PR_NUMBER" --auto --rebase
```

**Do NOT use `continue-on-error: true`** — that bypasses the problem rather than solving it.

#### Level 10: Required-Signatures Ruleset Blocks Merge of Branches with Unsigned Historical Commits

After commit `77b74ad` ("chore(pre-commit): require GPG/SSH-signed commits on push") landed on
main on 2026-05-16, AchaeanFleet's repository ruleset began enforcing
`required_signatures` plus `pull_request.required_review_thread_resolution: true` on `main`.
Any PR whose branch contains commits authored **before** that date will have unsigned commits
in its history and will be blocked at merge time — even when every status check is green.

The failure mode is especially confusing because the `gh` CLI does not name the failing rule
and the legacy branch-protection endpoint shows no required checks or reviewers.

**Symptoms:**

- `gh pr view N --json mergeStateStatus` returns `BLOCKED` even though `mergeable=MERGEABLE`
  and all status checks are `SUCCESS`.
- `gh pr merge N --squash` (without `--admin` / `--auto`) fails with the generic message:
  `Pull request HomericIntelligence/AchaeanFleet#N is not mergeable: the base branch policy
  prohibits the merge.`
- Legacy `gh api repos/.../branches/main/protection` shows zero required checks and zero
  required reviews — misleading; the actual rule is in the **new rulesets API**.
- The real source of truth is `gh api repos/HomericIntelligence/AchaeanFleet/rules/branches/main`
  which shows a `required_signatures` ruleset plus a `pull_request` ruleset with
  `required_review_thread_resolution: true`.

**Diagnosis steps (verified-ci):**

```bash
# 1. Confirm legacy branch protection is NOT the blocker
gh api repos/HomericIntelligence/AchaeanFleet/branches/main/protection \
  --jq '{required_checks: .required_status_checks.contexts,
         required_reviews: .required_pull_request_reviews}'

# 2. Inspect rulesets (this is where required_signatures lives)
gh api repos/HomericIntelligence/AchaeanFleet/rules/branches/main \
  --jq '[.[] | {type, parameters}]'

# 3. Check each commit's signature verification on GH
#    (gh pr view's .commits[].signature field is unreliable — always null)
gh pr view N --json commits --jq '.commits[] | .oid[0:7]' | while read sha; do
  v=$(gh api repos/HomericIntelligence/AchaeanFleet/commits/$sha \
        --jq '.commit.verification.verified')
  echo "$sha verified=$v"
done
```

**Verified fix — sign every commit in the PR via rebase --exec:**

```bash
# Switch to the PR branch
git checkout <branch>

# Find merge-base with main
BASE=$(git merge-base HEAD origin/main)

# Sign every commit in the PR (--amend --no-edit -S applied to each commit)
git rebase --exec 'git commit --amend --no-edit -S' "$BASE"

# Verify all commits are signed locally
# (G = good signature, U = good signature with unknown trust — both acceptable)
git log --format='%h %G? %s' "$BASE"..HEAD

# Force-push — ALWAYS use --force-with-lease, NEVER --force
git push --force-with-lease

# Confirm GH sees verified=true on every commit
git log --format='%h' "$BASE"..HEAD | while read sha; do
  gh api repos/<owner>/<repo>/commits/$sha --jq '.commit.verification.verified'
done
```

**Critical gotcha — force-pushing disarms `gh pr merge --auto`:**

GitHub revokes the auto-merge arming on any history rewrite (the head SHA changes). After
**every** force-push to a PR that previously had auto-merge enabled, re-arm it:

```bash
gh pr merge N --squash --auto --repo <owner>/<repo>
```

If you skip this step, the PR will sit indefinitely after CI goes green, because nothing is
listening for the merge trigger anymore.

**Why this is needed:** AchaeanFleet adopted a pre-commit hook requiring signed commits
(commit `77b74ad` on main, "chore(pre-commit): require GPG/SSH-signed commits on push") on
2026-05-16. PRs whose branches contain commits from before that date have unsigned commits
in their history. The `required_signatures` ruleset checks **all commits in the PR branch**,
not just the merge commit — so even though squash-merge would produce a single signed commit
on main, the ruleset still blocks at the merge button. The only remediation is to rewrite the
PR branch so every commit is signed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fix ENTRYPOINT in only Dockerfile.node | Assumed only node base needed ENTRYPOINT since most vessels use it | CI "Verify ENTRYPOINT" check runs on all 3 base images independently | All three bases (node, python, minimal) MUST have ENTRYPOINT |
| `--output type=oci,dest=/tmp/foo.tar` | Assumed .tar suffix creates valid OCI tarball for oci-layout:// | `oci-layout://` protocol reads directory layout, not tarballs | Write .tar then extract with `tar -xf` to a separate directory |
| `opencode_linux_amd64.tar.gz` download URL | Followed naming convention from other tools (amd64) | The opencode release asset is named `opencode-linux-x64.tar.gz` (x64 not amd64) | Always verify release asset names with `gh release view` before hardcoding URLs |
| Keep `goose --version \|\| true` after QEMU fix | Left the suppression in place after adding QEMU setup | Non-amd64 build failures were silently swallowed, masking broken arm64 vessel builds | Remove `\|\| true` once QEMU is available — binary version checks must be hard failures |
| Fixing ci.yml rebase conflicts by keeping PR's version | Multiple swarm branches both modify the validate job's step block | Conflict at lines 260-430; PR's version may duplicate steps already in HEAD | Keep HEAD's version of shared steps; add only genuinely new steps from the PR |
| `outputs: type=oci,dest=/tmp/foo/` (trailing slash) | Added trailing slash to make buildx write OCI directory | `build-push-action` pre-creates `/tmp/foo/` as a directory, then buildx tries to open the directory path as a tar file → `open /tmp/foo/: is a directory` | Never use trailing slash on OCI dest path; always write .tar then extract |
| `outputs: type=oci,dest=/tmp/foo` (no slash, no .tar) | Extensionless path with no slash — expected OCI directory output | Still writes a tarball; `oci-layout:///tmp/foo` then fails with "not a valid OCI layout" because it's a tar | Always write `dest=/tmp/foo.tar` explicitly then `tar -xf` to a directory |
| `continue-on-error: true` on changelog push step | Silence the branch protection failure in changelog workflow | Hides the error but CHANGELOG never actually updates — bot can't push directly either way | Fix by having the bot create a PR + auto-merge instead |
| Python source at column 0 inside `run: \|` | Wrote multi-line `python3 -c "..."` with Python source at column 0 | YAML parser interprets column-0 lines as new mapping keys; `ScannerError: could not find expected ':'` | All lines inside a YAML literal block scalar must be indented to at least the block's indentation level |
| `docker compose config` without caddy overlay | Called `docker compose -f docker-compose.claude-only.yml config` directly | Fails: `service "hi-eris" depends on undefined service "caddy"` because caddy is defined only in docker-compose.caddy.yml | Always prepend `-f compose/docker-compose.caddy.yml` before any claude-only or mesh compose command |
| Trust `gh pr view`'s `.commits[].signature` field | Ran `gh pr view N --json commits --jq '.commits[].signature'` to determine which commits were unsigned | The field returns `null` even for actually-signed commits — it is unreliable | Always cross-check signing via `gh api repos/.../commits/<sha> --jq .commit.verification.verified` |
| Check `branches/main/protection` only | Inspected the legacy branch-protection API and saw "no required checks, no reviews" | Modern repository rulesets are NOT exposed via the legacy protection endpoint — they live at `/rules/branches/main` | When merge is BLOCKED but legacy protection looks empty, always check the rulesets endpoint |
| `gh pr merge N --squash` without `--admin` on a branch with unsigned commits | Tried plain squash-merge expecting it to produce a single signed commit on main | Same generic error: "base branch policy prohibits the merge" — no hint about which rule is failing | The CLI does not name the failing rule; you must inspect rulesets manually and rewrite branch history to sign every commit |
| Forget to re-arm `--auto` after force-pushing the signed branch | Assumed `gh pr merge --auto` survives a force-push | GitHub disarms auto-merge whenever the head SHA changes via force-push | After every force-push to a PR with auto-merge enabled, re-run `gh pr merge N --squash --auto` |

## Results & Parameters

### Session Outcome

- **Repo**: `HomericIntelligence/AchaeanFleet`
- **Session type**: Multi-session myrmidon swarm
- **Starting state**: 13 open PRs, ~235 issues (prior session had classified 235 → 10 remaining)
- **Ending state**: 0 open PRs, ~10 issues implemented, 3 new PRs created (#547, #548, #549)
- **Issues remaining after session**: ~6 labeled "research" (#421, #353, #325, #305, #302, #277) + #184 (Nomad TLS, requires infrastructure)

### Issues to Leave for Research Sessions

These issues are genuinely hard and should NOT be attempted in a swarm implementation session:

- `#421, #353, #325, #305, #302, #277` — labeled "research", require design/investigation
- `#184` — Phase 6 Nomad TLS cert distribution, requires infrastructure provisioning

### CI Rebase Conflict Resolution for ci.yml

When multiple swarm branches both modify `ci.yml` (adding different validate steps), the
conflict always appears in the validate job's step block (lines 260-430 in AchaeanFleet).

**Resolution strategy**:
1. Keep HEAD's version of all shared/duplicate steps
2. Identify the PR's genuinely new steps (not duplicates of HEAD)
3. Add only those new steps at the appropriate position
4. Validate YAML after resolution: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`

### Classification Accuracy

The prior session's classification of 235 → 10 remaining issues was accurate.
All "easy" issues were successfully implemented. This validates the classification methodology
documented in `batch-low-difficulty-issue-impl`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/AchaeanFleet | Multi-session myrmidon swarm 2026-04 | 13 PRs → 0, cascade sequence fully mapped |
| HomericIntelligence/AchaeanFleet | Follow-up session 2026-04-25 | Level 6 corrected; Levels 1.5, 4.5, 9 added from new cascade failures |
| HomericIntelligence/AchaeanFleet | Required-signatures session 2026-05-18 | Level 10 added. PR #661 (`chore/easy-sweep-bundle-round2-2026-05-16`) — 6 of 7 commits unsigned, blocked with BLOCKED+no-failures pattern. `git rebase --exec 'git commit --amend --no-edit -S' "$BASE"` on commits `2a1f1c5..9ada664` made all 7 `verified=true` on GH; PR auto-merged after re-arming `--auto` and new CI passing. Same procedure applied to PR #664 (single commit `7b06242` → `5ab76a9`). |
