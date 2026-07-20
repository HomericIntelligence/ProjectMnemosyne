---
name: release-workflow-stagewise-failure-debugging
description: "A tag-triggered PyPI release workflow fails one job at a time — each fix only exposes the next latent bug, because a release is the first time the publish path actually runs end-to-end. Use when: (1) a release.yml / publish pipeline fails at type-check, test, publish-testpypi, or build-and-publish and you must fix stage-by-stage, (2) a fix you merged to main does NOT take effect in the release run — because resolve-release checks out the TAG's tree, not main's HEAD, so the fix must be AT the tagged commit (retag onto the fixed HEAD), (3) `uv run mypy` fails with 'Missing target module, package, files, or command' in the release but the required PR gate passes (the PR gate's pre-commit hook passes explicit targets), (4) tests fail on the release runner with 'No supported agent backend found on PATH' (claude/codex/pi) though they pass on dev/CI where an agent binary exists, (5) a PyPI/TestPyPI publish fails with `invalid-publisher: valid token, but no corresponding publisher` (a trusted-publisher config gap, not code), (6) deciding whether a TestPyPI staging gate earns its keep vs. having build-and-publish build its own dist."
category: ci-cd
date: 2026-07-19
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - ci-cd
  - release-pipeline
  - pypi
  - trusted-publisher
  - testpypi
  - resolve-release
  - release-tag-tree
  - retag
  - hatch-vcs
  - mypy-no-target
  - agent-backend-on-path
  - conftest-stub
  - stagewise-failure
  - homericintelligence
  - hephaestus
---

# Release Workflow: Debug Stage-by-Stage, and Fix AT the Tagged Commit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-19 |
| **Objective** | Get a tag-triggered PyPI release (Hephaestus v0.10.0) to publish after it failed repeatedly, each time at a later job than the last. |
| **Outcome** | Each stage-specific latent bug was fixed and verified by the release progressing to the next job: type-check → test → (removed) publish-testpypi → build-and-publish. The decisive insight was that the fixes had to be present AT THE TAGGED COMMIT, not merely on main. |
| **Verification** | verified-ci (each fix was confirmed by the live release run clearing the previously-failing job; every fix was also reproduced/verified locally under the release's exact condition). |

## When to Use

A tag-triggered release keeps failing, and each fix reveals the next failure —
because a release is often the FIRST time the whole publish path runs against a
real tag on a real (differently-provisioned) runner. Also use when a fix you
merged to main "didn't take" in the release run.

## Verified Workflow

### The load-bearing insight: resolve-release checks out the TAG's tree

A release workflow's `resolve-release` job resolves the release **tag → SHA**,
and every downstream job checks out `ref: needs.resolve-release.outputs.sha` —
i.e. **the tagged commit's tree**. The workflow *file* used is whatever ref
triggered the run (main's HEAD for a tag push / dispatch), but the **code and
tests that run are the tag's tree**.

Consequence: **merging a fix to main does NOT fix the release** if the tag still
points at a commit without the fix. Symptom — the release-run *workflow* shows
your fix (e.g. type-check passes) but a *later* job that checks out the tag tree
still fails on the old code. Fix: **retag onto the commit that contains the
fix** (delete the stale tag, re-create it on the fixed HEAD, push). Verify the
target commit actually contains every fix before retagging.

```bash
# Prove the retag target has the fix BEFORE moving the tag
git show <target-sha>:tests/conftest.py | grep -c resolve_agent   # expect the fixed count
git show <target-sha>:.github/workflows/release.yml | grep -c testpypi   # expect 0 if removed
# Retag (tag deletion is often blocked by local safety nets — the human runs these)
git tag -d vX.Y.Z; git push origin :refs/tags/vX.Y.Z
git tag -s vX.Y.Z -m "Release vX.Y.Z" <target-sha>; git push origin vX.Y.Z
```

Reusing a version is only safe if it was never published — confirm:
`curl -s https://pypi.org/pypi/<dist>/json | jq '.releases | has("X.Y.Z")'` → false.

### The stage-by-stage latent bugs (each masked the next)

- **type-check: bare `uv run mypy` → "Missing target module, package, files, or
  command."** `pyproject.toml` has no default mypy `files`, so bare `mypy` has
  nothing to check. The required PR `lint` gate passed because its pre-commit
  hook passes explicit targets. Fix the release step to match:
  `uv run mypy hephaestus/ scripts/ tests/`.

- **test: "No supported agent backend found on PATH."** Tests that call a CLI
  `main()` hit `resolve_agent()`, which probes PATH for `claude`/`codex`/`pi`
  and RAISES when none is installed. They pass on dev/CI machines (agent on
  PATH) but fail on the agent-free release runner. This is deliberate — you do
  NOT want CI to install agent accounts or spend tokens. Fix at the ROOT: extend
  the autouse `conftest.py` fixture to stub `resolve_agent` (not just
  `is_agent_authenticated`) suite-wide, returning a default backend with no PATH
  probe. Verify with agent binaries removed from PATH:
  `PATH="$(dirname $(which uv)):/usr/bin:/bin" uv run pytest ...`.

- **publish-testpypi / build-and-publish: `invalid-publisher: valid token, but
  no corresponding publisher`.** OIDC trusted publishing failed because the
  index has no publisher whose claims match this repo/workflow/environment. This
  is a PyPI-side ACCOUNT CONFIG gap, not code — only the project owner can add
  the trusted publisher (owner, repo, workflow filename, environment name).
  Production PyPI often already has one (a prior version published); TestPyPI
  frequently does not.

- **Decide whether a TestPyPI staging gate earns its keep.** A `publish-testpypi`
  job that builds → publishes to TestPyPI → smoke-installs, feeding its artifact
  to `build-and-publish`, tests industry-standard packaging tooling, not your
  source — and needs a whole extra trusted-publisher config. If unwanted, delete
  the job and have `build-and-publish` BUILD ITS OWN dist (it previously reused
  the TestPyPI job's `release-dist` artifact). Update `needs:`, drop the
  `download-artifact` step for a build step, and remove the doc section.

### General method

1. Read the FAILED job's log only after the whole run completes — GitHub serves
   job logs after run completion, not mid-run (`gh run view --job <id> --log`).
2. Find the exact failing step + assertion; reproduce it LOCALLY under the
   release's condition (agent-free PATH, bare command, tagged tree).
3. Fix the smallest thing; land it via PR; then **retag onto the fixed HEAD** so
   the tag tree carries the fix.
4. Re-run and watch the NEXT job — expect a new, later failure; repeat.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Merged the type-check/test fixes to main, then re-ran the SAME release run | The tag still pointed at the pre-fix commit; `resolve-release` checked out the OLD tag tree, so the test job failed on the old code even though main was fixed | The fix must be AT the tagged commit — retag onto the fixed HEAD, don't just fix main. |
| 2 | Mocked `resolve_agent` in only the two failing tests | Worked for those two, but any other test (now or future) calling a CLI `main()` would hit the same PATH probe on an agent-free runner | Fix agent-backend dependence at the ROOT (autouse conftest stub), not per test. |
| 3 | Assumed the repeated release failures were GitHub runner starvation (as an earlier phase genuinely was) | Runners had recovered; the failures were real latent bugs surfacing one stage at a time | Read the completed job log and reproduce locally before blaming infra. |
| 4 | Tried to fix `invalid-publisher` in the workflow / retag | It is a PyPI ACCOUNT trusted-publisher config, not code or tag state — no repo change resolves it | Distinguish PyPI-side config gaps from code bugs; escalate account config to the project owner (or remove the gate that needs it). |
| 5 | `git tag -d` / retag from the agent shell | Local safety nets block tag deletion | Hand the retag commands to the human; verify the target SHA carries every fix first. |

## Results & Parameters

- **Reproduce the release's `test` condition locally (agent-free):**
  `PATH="$(dirname $(which uv)):/usr/bin:/bin" uv run pytest tests/unit ...` —
  strips `~/.local/bin` (where the agent CLI lives) so the PATH probe fails as it
  does on the release runner.
- **mypy release invocation must match the required lint hook:**
  `uv run mypy hephaestus/ scripts/ tests/` (bare `uv run mypy` errors when
  pyproject has no default `files`).
- **Trusted-publisher claims to register on (Test)PyPI:** project name, owner,
  repository, workflow filename (`release.yml`), environment name
  (`pypi` / `testpypi`). `invalid-publisher` == no matching publisher.
- **Job logs are only downloadable after the whole run completes**, not while a
  sibling job is still in progress.

### Related skills (cross-links)

- `ci-release-pipeline-must-mirror-required-pr-gate` — a release/dispatch can
  target an arbitrary commit that never passed the required PR gate, so the
  release must re-run the same gate; complements this entry's "fix must be at the
  tagged commit" insight.
- `gha-release-package-workflow-patterns` — general release/publish workflow
  patterns (hatch-vcs versioning, PyPI publish steps).
- `rebase-stale-automation-pr-onto-refactored-main` — the sibling "a fix must be
  present at the exact evaluated tree" theme for stale-base PR rebases.
