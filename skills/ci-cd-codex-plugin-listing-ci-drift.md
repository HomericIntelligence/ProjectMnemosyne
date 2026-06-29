---
name: ci-cd-codex-plugin-listing-ci-drift
description: "Fix CI failures in Codex plugin directory/listing PRs where branch policy, materialized marketplace wrappers, scanner configuration, and no-isolation sdist tests drift from the source plugin payload. Use when: (1) a Codex plugin listing PR fails after adding catalog metadata or scanner workflow files, (2) a materialized plugins/PLUGIN_NAME wrapper may be stale relative to the root .codex-plugin payload, (3) sdist tests build with --no-isolation and backend dependencies are missing from dev extras."
category: ci-cd
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [codex, plugin, ci, scanner, sdist, signed-commits, manifest-drift, symlink]
---

# Codex Plugin Listing CI Drift

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-29 |
| **Objective** | Drive a Codex plugin directory/listing PR green when CI fails on policy and packaging drift rather than application logic. |
| **Outcome** | Successful: the fix re-signed commits, removed stale wrapper symlinks, synced root and wrapper plugin payloads, configured the plugin scanner, and made no-isolation sdist backend deps explicit. |
| **Verification** | verified-ci. GitHub API checks were unavailable during capture, but local history contains merged ProjectHephaestus PR #1609 commit `e57edb6f1facf5c2f02ba925cfc8e083b6aa2118` on `origin/main`, and the session evidence states the PR was driven to green CI. |

## When to Use

- A Codex plugin listing or directory-readiness PR adds `.codex-plugin`, `.codexignore`, scanner workflow, catalog icon, marketplace wrapper, or sdist coverage and CI fails.
- The repository has a materialized local marketplace wrapper such as `plugins/PLUGIN_NAME` that mirrors root plugin files instead of symlinking them.
- Branch protection or `pr-policy` can reject otherwise-correct code because commits are unsigned or not verified.
- Tests build an sdist with `python -m build --sdist --no-isolation`, so build backend requirements must already exist in the active dev environment.
- A scanner runs against the repo root and needs explicit, narrow ignores for non-plugin fixtures.

## Verified Workflow

### Quick Reference

```bash
# Policy gate: every PR commit must be signed/verified for repos with pr-policy.
git log origin/main..HEAD --pretty=format:'%h %G? %an <%ae> %s'

# Materialized wrapper gate: root and wrapper payloads must match by content.
cmp .codex-plugin/plugin.json plugins/PLUGIN_NAME/.codex-plugin/plugin.json
cmp assets/icon.svg plugins/PLUGIN_NAME/assets/icon.svg
find plugins/PLUGIN_NAME -xtype l -print

# Listing/scanner and wrapper regression coverage.
python3 -m pytest tests/unit/plugins/test_codex_plugin_manifest.py -q --no-cov
python3 -m pytest tests/unit/validation/test_codex_plugin_packaging.py -q --no-cov
python3 -m pytest tests/integration/test_sdist_contents.py -q --no-cov

# No-isolation sdist tests require build backends in dev extras.
python -m build --sdist --no-isolation --outdir /tmp/sdist-check .
```

### Detailed Steps

1. Separate policy failures from code failures first. Query PR checks when GitHub is available; if `pr-policy` or required signatures are involved, verify every branch commit has a good signature before chasing packaging logic.
2. Treat a materialized marketplace wrapper as a second shipped artifact. Any root plugin change, such as adding `interface.composerIcon`, must be copied into `plugins/PLUGIN_NAME/.codex-plugin/plugin.json`.
3. Remove stale or dangling symlinks inside `plugins/PLUGIN_NAME`. Once the wrapper is materialized, catalog assets such as `assets/icon.svg` should be real files and byte-equal to the canonical root asset.
4. Write regression tests for content equality, not symlink identity. The durable invariant is that the wrapper manifest and assets match the root payload; the implementation can be materialized without being a symlink.
5. Configure the plugin scanner deliberately. Pin the scanner action by SHA, point it at a checked-in config file, set the score/severity thresholds explicitly, and ignore only known non-plugin fixtures that trigger false positives.
6. If an sdist test uses `--no-isolation`, add every `build-system.requires` package to the dev extra used by CI. Add a regression test that normalizes requirement names and asserts build requirements are a subset of dev dependencies.
7. Re-run the targeted plugin/listing tests plus the repository's required CI gates before pushing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix packaging while leaving commits unsigned | Code changes addressed scanner and wrapper failures, but the PR still had commits that did not satisfy the signed-commit policy | `pr-policy` can block independently of test logic | Check signatures before and after every rebase or commit rewrite on protected repos |
| Update only the root Codex manifest | Added catalog metadata such as `composerIcon` to `.codex-plugin/plugin.json` but not to the materialized wrapper manifest | The marketplace wrapper is what local catalog installs consume, so root/wrapper drift breaks listing readiness | Keep root and wrapper manifests byte-equal with a regression test |
| Keep dangling symlinks in a materialized wrapper | Left wrapper paths such as `.codexignore` or `assets` as stale symlinks after the wrapper was converted to real files | The wrapper no longer had a coherent materialized payload and tests/scanners observed different shapes | Once materialized, wrapper assets must be real files and checked by content |
| Assert symlink identity in tests | Tested that wrapper paths were symlinks to canonical root files | The correct post-materialization invariant is content equality, not path identity | Tests should compare bytes and reject missing files or stale content |
| Use `--no-isolation` sdist build without backend deps | The sdist test disabled build isolation but the dev extra omitted backend requirements such as `hatchling` and `hatch-vcs` | The build subprocess could not import the backend from the active environment | Mirror `build-system.requires` into the CI/dev extra when disabling build isolation |
| Run the scanner without scoped ignores | The scanner evaluated repo tooling fixtures as if they were plugin payload content | Non-plugin test fixtures can trigger false positives and fail the listing gate | Keep false-positive ignores explicit, narrow, and covered by a test that reads the scanner config |

## Results & Parameters

### Guardrail Checklist

| Guardrail | Expected Result |
|-----------|-----------------|
| Signed commits | `git log origin/main..HEAD --pretty=format:'%G?'` shows `G` for every PR commit on protected repos |
| Root manifest | `.codex-plugin/plugin.json` includes catalog metadata such as `interface.composerIcon` |
| Wrapper manifest | `plugins/PLUGIN_NAME/.codex-plugin/plugin.json` is byte-equal to the root manifest |
| Catalog icon | Root and wrapper `assets/icon.svg` files are real files, non-placeholder SVGs, and byte-equal |
| Symlink check | The materialized wrapper contains no symlinks that a plugin installer/scanner must dereference |
| Scanner workflow | Scanner action is SHA-pinned, uses a checked-in config, and sets explicit score/severity thresholds |
| Scanner config | Ignores are narrow and limited to known non-plugin fixtures |
| Sdist no-isolation | Build backend requirements are present in the dev extra used by CI |

### Related Skills

- `tooling-codex-plugin-symlink-empty-cache-fix.md` covers the original empty-cache failure caused by symlinked marketplace wrappers.
- `git-commit-signing-failures-and-setup.md` covers the general signed-commit diagnosis and re-signing workflow for `pr-policy` failures.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1609, merge commit `e57edb6f1facf5c2f02ba925cfc8e083b6aa2118`; local commit message says it closes #1521 | CI fix list included GPG re-signing, removing dangling `plugins/hephaestus` symlinks, syncing wrapper and root manifests with `composerIcon`, materializing the wrapper icon, switching tests to content equality, adding scanner config coverage, and adding no-isolation sdist backend deps |
