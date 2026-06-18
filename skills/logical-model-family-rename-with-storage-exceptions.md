---
name: logical-model-family-rename-with-storage-exceptions
description: "Rename repository logical model-family surfaces without breaking physical checkpoint or benchmark storage paths. Use when: (1) replacing old model-family names in manifests, docs, tests, scripts, and routes, (2) preserving real external paths that still contain the old name, (3) adding a guard that blocks old logical names while allowing storage references."
category: tooling
date: 2026-06-18
version: "1.0.1"
user-invocable: false
verification: verified-ci
tags: [model-family, rename, manifests, h200-slurm, storage-exceptions, ruff]
---

# Logical Model Family Rename With Storage Exceptions

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-18 |
| **Objective** | Rename repository logical model-family surfaces from an old family name to a new family name while preserving real physical storage paths that still contain the old name. |
| **Outcome** | Successful. Tracked filenames and logical identifiers moved to the new name, stale logical names were guarded by tests, physical checkpoint and benchmark storage paths were intentionally preserved, and source-repository CI passed. |
| **Verification** | verified-ci |

## When to Use

- A user asks to rename all logical naming for a model family, product family, or serving surface.
- The change spans H200 Slurm service manifests, docs/runbooks, docs/evaluations, generation scripts, launch scripts, default registries, benchmark examples, and tests.
- Old logical names must disappear, but real external storage still uses old-name path segments.
- A bulk rename has started to mutate protected paths or generated placeholder tokens.
- Ruff reformats a stale-token guard in a way that defeats the guard.

## Verified Workflow

### Quick Reference

```bash
# Work in an isolated branch/worktree.
OLD_FAMILY="oldfamily"
NEW_FAMILY="newfamily"
OLD_FAMILY_UNDERSCORE="old_family"
NEW_FAMILY_UNDERSCORE="new_family"

# Inventory old names in filenames and content before editing.
git ls-files | rg "${OLD_FAMILY}|${OLD_FAMILY_UNDERSCORE}"
rg -n "${OLD_FAMILY}|${OLD_FAMILY_UNDERSCORE}" .

# Rename tracked files with git mv so history follows the new names.
git mv "scripts/generate-${OLD_FAMILY}-manifests.py" \
  "scripts/generate-${NEW_FAMILY}-manifests.py"
git mv "scripts/multi_model_${OLD_FAMILY_UNDERSCORE}_launch.sh" \
  "scripts/multi_model_${NEW_FAMILY_UNDERSCORE}_launch.sh"

# Update logical surfaces to the new name, but do not rewrite physical storage paths.
rg -n "${OLD_FAMILY}|${OLD_FAMILY_UNDERSCORE}" docs manifests scripts tests README.md

# Required post-change checks.
git diff --check
git ls-files | rg "${OLD_FAMILY}|${OLD_FAMILY_UNDERSCORE}" || true
rg -n "${OLD_FAMILY}|${OLD_FAMILY_UNDERSCORE}" .
just validate
```

### Detailed Steps

1. **Rename tracked files first with `git mv`.** Do not rely only on content replacement. Move old-name files across docs/runbooks, docs/evaluations, manifests, and scripts to new-name filenames so `git log --follow` remains useful.

2. **Separate logical identifiers from physical storage.** Logical repo surfaces should move to the new family name: `model_id`, `display_name`, `host`, `slurm_job_name`, route endpoints, `manifest_version`, profile names, default registries, tool README text, and benchmark report examples. Real storage paths should remain unchanged when that is where the data actually lives.

3. **Protect known physical storage references.** Preserve paths like `/workspace/checkpoints/<vendor>/<old-family>-...` and `/shared/benchmarks/<old-family>_single_node_suite/...` unless the backing data has actually moved. Rewriting those paths makes Slurm jobs point at nonexistent checkpoint or benchmark artifacts.

4. **Add or keep a logical-name guard test.** The guard should scan repo surfaces that should be logically renamed and fail on old names while allowlisting only physical storage references. The guard is the durable protection against future examples, docs, or manifests reintroducing old logical names.

5. **Write stale-token constants so Ruff cannot fold them back.** Avoid adjacent string literal tricks in tests because Ruff can collapse them into the exact old token. Use explicit concatenation:

   ```python
   LEGACY_COMPACT_MODEL_PREFIX = "old" + "family"
   LEGACY_UNDERSCORE_PARSER = "old" + "_family"
   ```

6. **Avoid self-matching placeholder tokens during bulk replacement.** If temporarily protecting text before a bulk rewrite, do not use placeholders containing the old or new target names. The replacement pass can mutate the placeholder itself and prevent restoration. Use neutral placeholders, or restore the affected files from `HEAD` and redo the replacement more narrowly.

7. **Verify filenames, content, and CI.** Require `git diff --check` to be clean, tracked filenames to have no old logical names, repo-wide search to show only physical storage exceptions, full local validation to pass, and PR CI to pass before calling the rename done.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rename every old token everywhere | Bulk replacement included checkpoint and benchmark storage strings | External storage paths still physically contained the old name, so rewritten jobs would point at paths that did not exist | Treat logical identifiers and physical storage locations as different classes of data. Preserve real paths unless storage has actually moved. |
| Placeholder tokens containing the old name | Protected strings used placeholders that included the replacement target before a bulk rewrite | The placeholder itself contained the target token and was transformed, making restoration fail | Use neutral placeholder tokens with no old or new name in them, or restore from `HEAD` before continuing. |
| Adjacent string literal stale-token guard | A test tried to avoid embedding the stale token by writing adjacent string literals | Ruff can collapse adjacent string literals back into the exact old token, defeating the guard's intent | Use explicit concatenation, for example `"old" + "family"` and `"old" + "_family"`. |
| Filename audit skipped | Content was updated but old filenames were not checked separately | A repo-wide content grep does not prove tracked filenames were renamed | Run the tracked-filename stale-name audit from Quick Reference and require no matches. |

## Results & Parameters

### Logical Surfaces That Should Move To The New Name

```yaml
logical_identifiers:
  - model_id
  - display_name
  - host
  - slurm_job_name
  - manifest_version
  - profile names
  - route endpoints
repo_surfaces:
  - docs/runbooks
  - docs/evaluations
  - manifests
  - scripts
  - default registries
  - tool README
  - benchmark report examples
```

### Physical References That Should Stay On The Old Path

```text
/workspace/checkpoints/<vendor>/<old-family>-...
/shared/benchmarks/<old-family>_single_node_suite/...
```

These are storage facts, not logical product names. Change them only after storage is moved or a new verified path exists.

### Guard Test Pattern

```python
LEGACY_COMPACT_MODEL_PREFIX = "old" + "family"
LEGACY_UNDERSCORE_PARSER = "old" + "_family"

ALLOWED_PHYSICAL_PATH_FRAGMENTS = (
    "/workspace/checkpoints/<vendor>/<old-family>-",
    "/shared/benchmarks/<old-family>_single_node_suite/",
)
```

The test should scan logical repo surfaces and fail on stale logical tokens unless the match is inside a known physical storage fragment.

### Verification Evidence

```text
git diff --check: clean
tracked-filename search for old logical names: no old filenames
repo-wide search of old tokens: only physical storage paths remained
local validation: passed
source-repository CI: passed
verification: verified-ci
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Logical model-family rename across H200 Slurm manifests, docs, scripts, examples, and tests | Verified with clean diff whitespace check, no stale tracked filenames, stale logical-name grep guard, full local validation, and passing CI. |
