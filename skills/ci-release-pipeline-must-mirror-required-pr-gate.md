---
name: ci-release-pipeline-must-mirror-required-pr-gate
description: "A required PR gate (integration tests, lint, schema check) only protects the auto-tag-from-merged-PR path — a workflow_dispatch/manual release can target an ARBITRARY commit that never passed that gate, so the release/publish pipeline must run the SAME gate itself. Use when: (1) auditing or hardening a release.yml / publish pipeline and a required PR-gate job (e.g. `_required.yml` `integration-tests`) enforces an invariant the release path does NOT re-run, (2) a workflow has BOTH a tag-push trigger AND a `workflow_dispatch`/manual trigger and you must reason about which commits actually passed the PR gates, (3) you are tempted to justify a missing release-time check with 'the PR gate already covers it' — true only for merged-PR tags, false for dispatch, (4) you are adding the missing check and must decide between a NEW parallel CI job vs a STEP in an existing job, (5) you must mirror the required gate's exact invocation (including addopts overrides like `--override-ini` and marker flags) so the release run cannot drift from the merged-PR guarantee, (6) proving an integration/e2e suite is actually COLLECTED by a new command and that build-backend-dependent tests do not silently skip in the release env."
category: ci-cd
date: 2026-07-01
version: "1.0.0"
user-invocable: false
verification: verified-local
history: ci-release-pipeline-must-mirror-required-pr-gate.history
tags:
  - ci-cd
  - release-pipeline
  - publish
  - pypi
  - workflow-dispatch
  - required-pr-gate
  - integration-tests
  - gate-parity
  - already-wired-gate
  - reuse-existing-job
  - invocation-mirroring
  - override-ini
  - strict-markers
  - collection-proof
  - sdist
  - manual-trigger-bypass
  - hephaestus
---

# CI Release Pipeline Must Mirror the Required PR Gate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-01 |
| **Objective** | Capture the durable rule that a merged-PR safety guarantee does NOT extend to `workflow_dispatch`/manual triggers: a required PR gate (integration tests, lint, schema) only covers commits that came through a merged PR, so a manual/dispatch release against an arbitrary commit BYPASSES it. The release/publish pipeline must therefore run the SAME gate itself — reusing the already-wired publish-gating job, not a new parallel job, and mirroring the gate's EXACT invocation. |
| **Outcome** | Success — added a `Run integration tests` step to the existing `test` job in `release.yml` (which already ran `pixi run dev-install` and is already `needs`-ed by `build-and-publish`), mirroring the required PR gate's exact command `pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers`. Zero new jobs, zero wiring changes; the publish is now gated on integration. Integration suite passed locally exactly as the release step invokes it (372 passed, 1 skipped; sdist-contents test 2 passed, not skipped). CI on the PR pending at capture time. |
| **Verification** | verified-local (CI on the PR pending at capture time — do NOT read as verified-ci) |

## When to Use

- You are auditing or hardening a `release.yml` / publish pipeline and discover a **required PR-gate job** (e.g. `_required.yml`'s `integration-tests`) enforces an invariant — integration tests, lint, a schema check — that the **release/publish path does NOT re-run**.
- A workflow has BOTH a **tag-push** (or auto-tag-from-merge) trigger AND a **`workflow_dispatch`/manual** trigger, and you must reason about **which commits actually passed the PR gates**. The auto-tag path is safe (the tag came from a merged, gate-passing PR); the dispatch path is not (it can target ANY commit or branch).
- You are about to justify a missing release-time check with **"the PR gate already covers it."** That is true ONLY for the auto-tag-from-merged-PR path. A `workflow_dispatch` run against an arbitrary commit never passed that gate — the justification is false for the manual path.
- You are adding the missing check and must decide between a **NEW parallel CI job** vs a **STEP inside an existing job**. Prefer the step when an existing job is already `needs`-ed by the publish job and already performs the required setup (editable install, env provisioning).
- You must **mirror the required gate's exact invocation** — including any addopts overrides (`--override-ini="addopts="`), marker strictness (`--strict-markers`), and verbosity — so the release run cannot behaviorally drift from the merged-PR guarantee.
- You must **prove an integration/e2e suite is actually COLLECTED** by the new command, and that any build-backend- or environment-dependent test does not silently SKIP in the release env.

**Key trigger:** you find yourself writing (or reading a reviewer write) "the PR gate covers integration, so the release doesn't need to" — and the workflow ALSO has a `workflow_dispatch:` trigger. That combination is exactly the bypass this skill guards.

## Verified Workflow

> Verification level: **verified-local**. The integration suite passed locally exactly as the new release step invokes it (372 passed, 1 skipped; the sdist-contents build-backend test 2 passed, NOT skipped). CI on the PR was pending at capture time — do NOT claim `verified-ci`.

### Quick Reference

```bash
# 1. Find the required PR gate that enforces the invariant, and its EXACT invocation.
grep -rn "pytest tests/integration" .github/workflows/
#   e.g. _required.yml `integration-tests` job:
#     pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers

# 2. Confirm the release workflow can reach that gate WITHOUT the PR:
grep -nE "workflow_dispatch|on:|tags:" .github/workflows/release.yml
#   BOTH `push.tags` (auto-tag, gate-covered) AND `workflow_dispatch` (arbitrary commit, NOT covered)
#   => the dispatch path bypasses the merged-PR guarantee.

# 3. Find the job the publish already depends on (reuse it — do NOT add a new job).
grep -nE "needs:|jobs:|dev-install|Run tests" .github/workflows/release.yml
#   build-and-publish: needs: [test, type-check]
#   test job already runs `pixi run dev-install` (the editable install integration needs)

# 4. PROVE the named integration guards are actually COLLECTED by the mirrored command.
pixi run pytest tests/integration --override-ini="addopts=" --collect-only -q \
  | grep -E "test_sdist_contents|test_package_import|test_cli_entry_points"

# 5. PROVE the build-backend-dependent sdist test does NOT skip in the release env.
pixi run pytest tests/integration/test_sdist_contents.py --override-ini="addopts=" -v
#   expect: 2 passed (NOT skipped) — the build backend is present in the pixi env.
```

```yaml
# release.yml — add a STEP to the EXISTING `test` job (already needs-ed by build-and-publish
# and already runs dev-install). Rename the prior "Run tests" -> "Run unit tests" for clarity.
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20            # bumped 15 -> 20: a first-run integration slowdown must
                                   # never abort a publish pipeline (cheap insurance).
    steps:
      # ... checkout, pixi setup, dev-install (already present) ...
      - name: Run unit tests                       # was "Run tests"
        run: pixi run pytest tests/unit
      - name: Run integration tests                # NEW — mirrors the required PR gate VERBATIM
        run: pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers

  build-and-publish:
    needs: [test, type-check]      # UNCHANGED — gating integration inside `test`
                                   # blocks the publish with zero wiring changes.
```

### Detailed Steps

1. **Identify the invariant the required PR gate enforces, and locate its exact command.** Grep the required workflow (`_required.yml`, `_ci.yml`, whatever gates PRs) for the job — here `integration-tests` running `pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers`. Copy the command VERBATIM; it is the contract you must reproduce on the release path.

2. **Confirm the release workflow has a bypass trigger.** Grep `release.yml` for `on:`. If it has BOTH `push.tags` (or an auto-tag path) AND `workflow_dispatch:` (or any manual/scheduled trigger), then a release can be cut against an **arbitrary commit** that never went through a PR — the required gate does NOT cover it. This is the whole reason the release must self-enforce. "The PR gate covers it" is true only for the auto-tag-from-merged-PR path.

3. **Reuse the already-wired publish-gating job; do NOT add a new job.** Grep the publish job's `needs:`. If it already `needs: [test, ...]` and that `test` job already performs the required setup (here `pixi run dev-install`, the editable install the integration tests need), add a STEP to `test` rather than a parallel `integration` job. Because `build-and-publish` already `needs: [test]`, gating integration INSIDE `test` blocks the publish with ZERO wiring changes. Adding a new job would require new `needs:` wiring and re-do the `dev-install` setup — more surface, no benefit. (This is the "reuse the already-wired gate" convention.)

4. **Mirror the required gate's invocation VERBATIM — do NOT invent a variant.** Copy the flags exactly:
   - `--override-ini="addopts="` clears the repo's default coverage `addopts` so the integration run is NOT subject to the unit-coverage gate (integration tests don't produce the unit coverage the addopts expect).
   - `--strict-markers` is SAFE only because the `integration` marker is registered in `pyproject.toml` — confirm that before copying the flag. A variant invocation risks behavioral drift from the merged-PR guarantee (e.g. dropping `--override-ini` would make the release run fail the coverage gate the PR run intentionally escapes).

5. **Rename the existing test step for clarity when you add a sibling.** The prior single `Run tests` step becomes `Run unit tests`, and the new step is `Run integration tests`. Two clearly-named steps beat one ambiguous one once the job runs two suites.

6. **Bump the job `timeout-minutes` as cheap insurance for a publish pipeline.** Adding a second suite to a job that gates a PUBLISH means a first-run integration slowdown (cold caches, extra collection) must never abort the pipeline. Bump `timeout-minutes` (here 15 → 20). This is free insurance — a publish pipeline aborting on a timing hiccup is far worse than a slightly longer wall-clock ceiling.

7. **PROVE collection, not just a green run (verification proof pattern).** A green run does not prove the intended guards RAN — a mis-scoped path or a silent skip can pass vacuously. Two proofs:
   - **Collection proof:** `pytest tests/integration --override-ini="addopts=" --collect-only -q | grep -E "NAMED_GUARDS"` must list the specific integration guards you care about (here `test_sdist_contents`, `test_package_import`, `test_cli_entry_points`).
   - **No-silent-skip proof:** run the environment-dependent test alone and confirm it does NOT skip. The sdist-contents test needs a build backend; in a lean release env it could `pytest.skip`, silently gutting the check. Run it and assert `2 passed` (not skipped) — the build backend is present in the pixi env.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusting the required PR gate to cover the release | Left `release.yml` running only `pixi run pytest tests/unit` before publishing, on the logic that the `_required.yml` `integration-tests` job already runs integration on every PR | The required PR gate only covers the auto-tag-from-merged-PR path; `release.yml` ALSO has a `workflow_dispatch` trigger that can publish an ARBITRARY commit which never passed that gate — so integration was never guaranteed on the manual release path | A merged-PR safety guarantee does NOT extend to `workflow_dispatch`/manual triggers; the release pipeline must run the SAME required gate itself |
| Adding a new parallel `integration` job to `release.yml` | Considered a standalone job to run the integration suite alongside `test`/`type-check` | A new job needs new `needs:` wiring on `build-and-publish` AND must re-do the `pixi run dev-install` editable install that the `test` job already performs — more surface, no benefit; the `test` job is already `needs`-ed by the publish job | Reuse the already-wired gate: add a STEP to the existing publish-gating job that already does the setup, not a parallel job |
| Inventing a simpler integration invocation | Tempted to run `pixi run pytest tests/integration` without the PR gate's `--override-ini="addopts="` and `--strict-markers` flags | Dropping `--override-ini="addopts="` subjects the integration run to the unit-coverage `addopts` (it would fail the coverage gate the PR run intentionally escapes), and dropping `--strict-markers` diverges from the gate; either way the release run behaviorally DRIFTS from the merged-PR guarantee | Mirror the required gate's invocation VERBATIM, including addopts overrides and marker flags; verify the `integration` marker is registered before relying on `--strict-markers` |
| Assuming a green run proves the guards ran | Planned to rely on the integration suite exiting 0 as sufficient evidence | A green run can pass vacuously — a mis-scoped path collects nothing, and a build-backend-dependent test (`test_sdist_contents`) can silently `pytest.skip` in a lean env, gutting the check while still exiting 0 | Prove COLLECTION (`--collect-only -q | grep NAMED_GUARDS`) AND prove the env-dependent test does NOT skip (run it alone, assert `2 passed`, not skipped) |
| Leaving the publish job's timeout at 15 min | Kept `timeout-minutes: 15` on the `test` job after adding a second (integration) suite | Adding a second suite raises the risk a first-run slowdown (cold caches, extra collection) hits the ceiling and ABORTS a publish pipeline — a far worse outcome than a longer wall-clock ceiling | Bump `timeout-minutes` (15 → 20) as cheap insurance; a publish must never abort on a timing hiccup |

## Results & Parameters

**The required-gate command mirrored onto the release path (verbatim):**

```bash
pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers
```

| Flag | Why it is REQUIRED (and must be copied verbatim) |
| ---- | ------------------------------------------------ |
| `tests/integration` | The integration-only suite (`test_sdist_contents.py`, `test_package_import.py`, `test_cli_entry_points.py`) that never runs under `pytest tests/unit` |
| `--override-ini="addopts="` | Clears the repo's default coverage `addopts` so the integration run is NOT subject to the unit-coverage gate |
| `-v` | Verbose — matches the required gate's invocation |
| `--strict-markers` | Fails on unregistered markers; SAFE only because the `integration` marker is registered in `pyproject.toml` |

**Wiring decision (reuse, do not add a job):**

| Option | Cost | Chosen? |
| ------ | ---- | ------- |
| STEP in existing `test` job | Zero new wiring — `test` already runs `dev-install` and is already `needs`-ed by `build-and-publish` | YES |
| NEW parallel `integration` job | New `needs:` on the publish job + re-do `dev-install` setup | No |

**Verification proof commands and expected results:**

```bash
# Collection proof — the three named integration guards must be listed:
pixi run pytest tests/integration --override-ini="addopts=" --collect-only -q \
  | grep -E "test_sdist_contents|test_package_import|test_cli_entry_points"

# No-silent-skip proof — the build-backend-dependent sdist test must PASS, not skip:
pixi run pytest tests/integration/test_sdist_contents.py --override-ini="addopts=" -v
# expected: 2 passed  (NOT skipped)

# Full integration suite as the release step invokes it:
pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers
# observed (verified-local): 372 passed, 1 skipped
```

**Reasoning checklist — is a merged-PR guarantee actually sufficient for the release?**

| Question | If NO → the release must self-enforce |
| -------- | ------------------------------------- |
| Does the release workflow ONLY run on auto-tags from merged PRs? | A `workflow_dispatch`/manual/scheduled trigger can target an arbitrary commit → gate bypassed |
| Does every commit a release can target provably pass the required gate? | A dispatch against a non-default branch or unmerged commit never passed it |
| Is the release-time check the SAME invocation as the required gate? | A variant invocation drifts from the merged-PR guarantee |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHephaestus | Issue #1499 — audit finding [S12 Packaging]; `release.yml` ran only `pixi run pytest tests/unit` before publishing to PyPI | Added a `Run integration tests` step to the existing `test` job (already `needs`-ed by `build-and-publish`, already runs `pixi run dev-install`), mirroring the required PR gate's exact command `pixi run pytest tests/integration --override-ini="addopts=" -v --strict-markers`; renamed prior `Run tests` → `Run unit tests`; bumped `test` `timeout-minutes` 15 → 20. Integration suite: 372 passed, 1 skipped; sdist-contents test 2 passed (not skipped). **verified-local** (CI on the PR pending at capture time). |

## References

- [ci-hygiene-and-validation-gates.md](ci-hygiene-and-validation-gates.md) — the "reuse the already-wired gate; no new workflow" convention and dead-gate detection.
- [ci-gate-verify-artifact-is-consumed-before-guarding.md](ci-gate-verify-artifact-is-consumed-before-guarding.md) — the sibling "does this gate actually protect a real failure path" reviewer question.
- [gha-release-package-workflow-patterns.md](gha-release-package-workflow-patterns.md) — tag-triggered release workflow, manifest/CHANGELOG consistency, and signed-tag gating patterns.
- [architecture-executable-convention-guard-pattern.md](architecture-executable-convention-guard-pattern.md) — turning a prose invariant into an executable, already-wired-gate check.
