---
name: logical-model-family-rename-with-storage-exceptions
description: "Rename logical reference surfaces (model-family names, or org/repo names when dropping a prefix) without breaking physical storage paths or package identity, AND execute the deferred breaking package rename correctly. Use when: (1) replacing old names in manifests, docs, tests, scripts, routes, and repo/URL references, (2) preserving real external paths or package names that still contain the old name, (3) splitting a safe reference-only sweep now from a breaking package/source rename deferred to a tracked issue, (4) adding a guard that blocks old logical names while allowing storage references, (5) a rename PR fails coverage/build because refs were renamed but package DIRECTORIES were not git mv'd, (6) completing a projectX->X package rename (git mv dirs + fix post-branch-merged files), (7) rebasing a stale whole-tree rename onto current main."
category: tooling
date: 2026-07-12
version: "1.2.0"
user-invocable: false
verification: verified-ci
tags: [model-family, rename, manifests, h200-slurm, storage-exceptions, ruff, repo-rename, url-sweep, package-rename, deferred-breaking-change, git-mv, whole-tree-rename, rebase, coverage-validator, mojo]
---

# Logical Model Family Rename With Storage Exceptions

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-11 |
| **Objective** | Rename logical reference surfaces (a model-family name, or an org/repo name when dropping a prefix) from an old name to a new name while preserving real physical storage paths and package identity that still contain the old name. |
| **Outcome** | Successful. Logical identifiers, reference/URL surfaces, and tracked filenames moved to the new name; stale logical names were guarded by tests; physical storage paths and package/source identity were intentionally preserved or deferred to a tracked breaking-change issue; source-repository CI passed. |
| **Verification** | verified-ci |
| **Also verified on** | HomericIntelligence/Odyssey (formerly ProjectOdyssey) org/repo rename: safe URL sweep PR #5580 (docs-only, 105 files) passed CI; breaking package rename deferred to issue #5579. The **deferred breaking package rename was then EXECUTED** in PR #5584 (`projectodyssey`->`odyssey`): `git mv` the 3 package dirs, fix post-branch-merged refs, rebase the stale whole-tree rename — previously-failing coverage/build checks passed and PR #5584 MERGED. |

## When to Use

- A user asks to rename all logical naming for a model family, product family, or serving surface.
- **An org/repo is renamed (e.g. dropping a `Project` prefix, `HomericIntelligence/ProjectOdyssey` -> `HomericIntelligence/Odyssey`) and you must update references without breaking the package.** The repo-name change and the package/source change are two different classes: sweep the references now, defer the package rename.
- The change spans H200 Slurm service manifests, docs/runbooks, docs/evaluations, generation scripts, launch scripts, default registries, benchmark examples, tests, and repo/URL references.
- Old logical names must disappear, but real external storage or a published package name still uses old-name segments.
- A bulk rename has started to mutate protected paths, package-identity fields, workflow files, or generated placeholder tokens.
- Ruff reformats a stale-token guard in a way that defeats the guard.
- **A "rename package X->Y" PR fails CI coverage or build** because it rewrote every text *reference* but never `git mv`'d the actual package *directories* — the manifest points at a nonexistent dir and the coverage validator sees the old-path files as "uncovered."
- **You are now executing the previously-deferred breaking package rename** (the atomic PR the issue tracked): move the source/test/python package dirs and fix references in files that merged AFTER the branch was cut.
- **You must rebase a stale whole-tree rename** onto current main: the branch is N commits behind, other work merged inside a renamed dir, and `git rebase` produces content conflicts plus `CONFLICT (file location)` for files added on main inside the renamed tree.

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

### Org/Repo Rename: Split Safe-Now From Deferred-Breaking

When an org renames a repo by dropping a prefix (`HomericIntelligence/ProjectOdyssey` -> `HomericIntelligence/Odyssey`), the same logical-vs-physical discipline applies, but here "physical" means **package/source identity**. Do NOT conflate renaming a repo with renaming its package.

1. **Point your local remote at the canonical URL.** The GitHub rename is usually already live and old URLs redirect, so existing git remotes and `gh` commands keep working through the redirect — but still update to canonical:

   ```bash
   git remote set-url origin git@github.com:HomericIntelligence/Odyssey.git
   ```

2. **SAFE-NOW — one mechanical docs-only PR: repo/URL references and repo-name prose.** These are pure references; sweeping them is non-breaking.

   ```bash
   # Inventory URL refs and repo-name prose.
   grep -rlE "HomericIntelligence/ProjectOdyssey" --include="*.md" --include="*.toml" --include="*.cfg" --include="*.yaml" --include="*.yml" . \
     | grep -v '^\./\.github/workflows/'
   # Substitute the URL form + repo-name prose ("ProjectOdyssey is one of...", "ProjectOdyssey (this repo)").
   # NEVER touch the package `name = "..."` field.
   ```

   A clean run is a fixed count substitution (this session: 105 files, 445-for-445). This is the layer that ships now and passes CI.

3. **DEFERRED-BREAKING — file a tracked issue, own atomic PR: the package/source rename.** Renaming the repo does NOT rename the package. The Mojo package `projectodyssey` (~546 imports), the pip/pixi/pyproject `name = "ProjectOdyssey"` fields, and `version('ProjectOdyssey')` refs in workflows all encode package identity. Rewriting them inline creates a massive half-renamed breaking change. File a `state:needs-plan` issue that scopes the package rename separately (`git mv` + scripted import rewrite + lockstep downstream update).

4. **EXCLUSIONS when running the URL sweep (keeps blast radius safe):**
   - Exclude `.github/workflows/` — workflow edits are human-review-gated per repo AGENTS.md, and they often carry the *package* name `version('ProjectOdyssey')` (belongs to the deferred package rename).
   - Exclude `.mojo` source and `mojo.toml` / `pixi.toml` `name=` fields (package identity → deferred issue).
   - Distinguish URL refs (`github.com/Org/ProjectRepo`) from the project `name` field: sed the URL form + repo-name prose only; NEVER the `name = "..."` package field.
   - **Verify after:** `git diff --name-only | grep '\.mojo$'` must be EMPTY, and `git diff --name-only | grep '\.github/workflows'` must be EMPTY.

5. **Companion repos:** for package-producing siblings (e.g. Hephaestus) whose rename affects a published package or plugin, file a parallel package-rename issue on each rather than sweeping their source inline.

### Execute the Deferred Breaking Package Rename (git mv the DIRS, then rebase)

This is the atomic PR the deferred issue tracked. A rename PR that rewrites every *reference*
(`mojo.toml` already maps `odyssey = "src/odyssey"`, configs say `odyssey`, `check_coverage.py`
uses `src/odyssey/`) but **never `git mv`s the actual package directories** is half-done and
breaks the build + coverage: the manifest points at a nonexistent `src/odyssey`, and the coverage
validator looks under the renamed path while the code still lives at the old path. Symptom seen:
`precommit-benchmark` -> `Validate Test Coverage` -> "❌ Found 267 uncovered test file(s)" all
under `tests/projectodyssey/...`, plus a ruff-format failure.

**A whole-tree rename PR is ATOMIC and goes stale the instant any other PR merges.** It must
merge before any new PR lands, or you must re-rebase. Complete it in a window with an empty merge
queue. Verify with `git grep -l <oldname>` == 0 AND a build AND the coverage/manifest validator —
not just "references look renamed."

#### Quick Reference

```bash
OLD=projectodyssey; NEW=odyssey

# 1. git mv the ACTUAL package directories (this is the step the half-done PR skipped).
git mv src/${OLD}     src/${NEW}
git mv tests/${OLD}   tests/${NEW}
git mv python/${OLD}  python/${NEW}
# Confirm git detected RENAMES (R), not delete+add:
git status --short | awk '{print $1}' | sort | uniq -c   # expect R's, not D+A

# 2. Fix flagged Python files (avoid a whole-file reformat diff — run the repo's formatter).
pixi run ruff format .

# 3. VERIFY completeness — BOTH must be empty/none:
git grep -l 'projectodyssey\|ProjectOdyssey'      # must print nothing (rc 1)
find . -type d -name '*projectodyssey*'           # must print nothing

# 4. VERIFY it BUILDS from the NEW path (imports must resolve there):
pixi run mojo build -I src tests/${NEW}/base/test_base_imports.mojo -o /tmp/x -Xlinker -lm
/tmp/x                                             # binary runs

# 5. VERIFY the coverage/manifest validator the CI job runs:
python3 scripts/validate_test_coverage.py          # rc 0
```

#### Rebasing the stale whole-tree rename (the critical part)

The branch was 16 commits behind main; other work had merged into `src/projectodyssey/**`
AFTER the branch was cut. `git rebase origin/main` produces two distinct conflict classes:

- **(a) Content conflicts** in files both sides touched. Resolve by taking **main's newer
  content** (`git checkout --ours <file>` during the rebase — during a rebase, "ours" is the
  branch being rebased onto, i.e. main's HEAD), then re-apply the rename to that newer content:
  `sed -i 's/projectodyssey/odyssey/g' <file>`.
- **(b) `CONFLICT (file location)`** for files ADDED on main *inside a renamed dir*. Git literally
  tells you the file "should perhaps be moved to `tests/odyssey/...`". Resolve by moving those new
  files into the renamed tree (`git mv`) and `sed` their imports to the new package name.

After the rebase completes, **re-run `git grep -l 'projectodyssey\|ProjectOdyssey'`** — this
session it surfaced 7 more files (new `*_autograd.mojo` example entrypoints that merged
post-branch) still carrying old refs. `sed` those too, then re-verify build + validator.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rename every old token everywhere | Bulk replacement included checkpoint and benchmark storage strings | External storage paths still physically contained the old name, so rewritten jobs would point at paths that did not exist | Treat logical identifiers and physical storage locations as different classes of data. Preserve real paths unless storage has actually moved. |
| Placeholder tokens containing the old name | Protected strings used placeholders that included the replacement target before a bulk rewrite | The placeholder itself contained the target token and was transformed, making restoration fail | Use neutral placeholder tokens with no old or new name in them, or restore from `HEAD` before continuing. |
| Adjacent string literal stale-token guard | A test tried to avoid embedding the stale token by writing adjacent string literals | Ruff can collapse adjacent string literals back into the exact old token, defeating the guard's intent | Use explicit concatenation, for example `"old" + "family"` and `"old" + "_family"`. |
| Filename audit skipped | Content was updated but old filenames were not checked separately | A repo-wide content grep does not prove tracked filenames were renamed | Run the tracked-filename stale-name audit from Quick Reference and require no matches. |
| Assumed repo rename == package rename | Planned to rewrite the `projectodyssey` Mojo package and all ~546 imports inline in the repo-rename PR | Renaming a repo does not rename its package; conflating them makes a massive breaking change that leaves the tree half-renamed | Defer the package/source rename to its own atomic PR tracked by a `state:needs-plan` issue; the reference sweep and the package rename are different classes of change. |
| Global `\bProjectOdyssey\b` sweep | Substituted the bare word everywhere | Risked hitting `pixi.toml`/`pyproject.toml` `name = "ProjectOdyssey"` and workflow `version('ProjectOdyssey')` — package identity, not references | Scope sed to the URL form (`github.com/Org/ProjectRepo`) plus repo-name prose; exclude `name=` fields, `.github/workflows`, and `.mojo`. |
| Edited workflow files in the sweep | Included `.github/workflows/` in the URL substitution | Workflow edits are human-review-gated per repo AGENTS.md, and they often carry the deferred package name anyway | Exclude `.github/workflows` from the sweep; verify `git diff --name-only \| grep '.github/workflows'` is empty. |
| Renamed references only, not the dirs | Rewrote every `projectodyssey`->`odyssey` reference (`mojo.toml` mapped `odyssey = "src/odyssey"`, configs, `check_coverage.py`) but never `git mv`'d `src/`, `tests/`, `python/` package dirs | `mojo.toml` pointed at a non-existent `src/odyssey`; the coverage validator looked under the renamed path but code was at the old path -> "❌ Found 267 uncovered test file(s)" + build failure | A rename is only half-done until the DIRECTORIES move. `git mv` the package dirs; verify with `git grep -l <old>` == 0 AND `find -type d -name '*<old>*'` == none AND a build AND the coverage validator, not just "references look renamed." |
| Whole-file reformat churn | Let the formatter rewrite whole files (json.dump-style) so the rename diff drowned in reformatting noise | Massive unrelated churn makes the rename PR unreviewable and can hide real changes | Run the repo's own formatter (`pixi run ruff format .`) so only the genuinely-flagged files change; keep the rename diff focused on moves + import lines. |
| Rebased the stale whole-tree rename blind | Ran `git rebase origin/main` on a 16-commits-behind whole-tree rename and tried to auto-resolve | Two conflict classes appeared: content conflicts (files both sides touched) and `CONFLICT (file location)` for files ADDED on main inside a renamed dir; naive resolution dropped main's newer work or left files at the old path | Take main's newer content (`--ours` during rebase) then re-`sed` the rename onto it; `git mv` the file-location conflicts into the renamed tree + sed imports; then re-`git grep` (7 more `*_autograd.mojo` files that merged post-branch still had old refs). |
| Assumed a passed rebase == complete rename | Called the rename done once `git rebase` finished cleanly | Files that merged onto main AFTER the branch was cut carried old refs the branch never touched | A whole-tree rename is atomic and stales on every merge; after rebase, re-run `git grep -l <old>` and expect new hits from post-branch merges. Merge it in an empty-merge-queue window or re-rebase. |

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

### Org/Repo Rename — Sweep vs Defer Checklist

```yaml
safe_now_reference_sweep:        # one mechanical docs-only PR
  - github.com/Org/OldRepo URL references (.md, configs)
  - repo-name prose in docs ("OldRepo is one of...", "OldRepo (this repo)")
  - git remote set-url origin <canonical-url>
deferred_breaking_package_rename:  # own atomic PR, tracked via state:needs-plan issue
  - Mojo/source package name (e.g. projectodyssey, ~546 imports)
  - pip/pixi/pyproject  name = "OldRepo"  fields
  - version('OldRepo') refs in workflows
exclude_from_url_sweep:
  - .github/workflows/            # human-review-gated per AGENTS.md
  - .mojo source files            # package identity
  - mojo.toml / pixi.toml name= fields  # package identity
verify_after_sweep:
  - git diff --name-only | grep '\.mojo$'          # must be EMPTY
  - git diff --name-only | grep '\.github/workflows' # must be EMPTY
companion_repos:
  - file a parallel package-rename issue per package-producing sibling (e.g. Hephaestus)
```

The GitHub repo rename usually goes live before the sweep, so old URLs redirect and existing remotes / `gh` commands keep resolving — the sweep is about canonicalizing references, not unblocking access.

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

### Execute-the-Package-Rename Completion Checklist

```yaml
move_the_dirs:            # the step a half-done rename skips
  - git mv src/<old>    src/<new>
  - git mv tests/<old>  tests/<new>
  - git mv python/<old> python/<new>
  - "git status --short must show R (rename), not D+A"
completeness_verify:      # ALL must be clean before calling it done
  - "git grep -l '<old>\\|<OldCamel>'   -> empty (rc 1)"
  - "find . -type d -name '*<old>*'      -> none"
  - "mojo build -I src tests/<new>/base/test_base_imports.mojo -> binary runs"
  - "python3 scripts/validate_test_coverage.py -> rc 0"
rebase_stale_whole_tree_rename:
  - "content conflict (both sides touched): take main's newer content (--ours during rebase) then sed the rename onto it"
  - "CONFLICT (file location) (file added on main inside renamed dir): git mv it into the renamed tree + sed imports"
  - "AFTER rebase: re-run git grep; expect NEW hits from files merged post-branch (this session: 7 *_autograd.mojo entrypoints)"
merge_window:
  - "atomic: stales on every merge into a renamed dir; merge in an empty-merge-queue window or re-rebase"
```

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
| HomericIntelligence/Odyssey (formerly ProjectOdyssey) | Org/repo rename dropping the `Project` prefix: safe URL/reference sweep separated from the breaking package rename | URL sweep PR #5580 (docs-only, 105 files, 445-for-445 substitution) passed CI; `.mojo`/`.github/workflows`/`name=` fields excluded and verified empty; breaking Mojo-package (`projectodyssey`, ~546 imports) + `name`/`version` rename deferred to `state:needs-plan` issue #5579; companion package-repo (Hephaestus) got its own parallel package-rename issue. |
| HomericIntelligence/Odyssey (Mojo repo) | **Executing** the deferred breaking package rename `projectodyssey`->`odyssey` in PR #5584 | The PR had renamed all *references* but never moved the dirs -> `precommit-benchmark` / `Validate Test Coverage` failed with "❌ Found 267 uncovered test file(s)" under `tests/projectodyssey/...` + a ruff-format failure. Fix: `git mv src/tests/python projectodyssey->odyssey` dirs (git detected renames), `pixi run ruff format .`, verify `git grep -l projectodyssey` == 0 + `find -type d -name '*projectodyssey*'` == none + `mojo build` from new path + `validate_test_coverage.py` rc 0. Then rebased the 16-commits-behind whole-tree rename: content conflicts resolved to main's newer content + re-sed; `CONFLICT (file location)` files `git mv`'d into the renamed tree; post-rebase `git grep` surfaced 7 new `*_autograd.mojo` entrypoints that merged post-branch. Previously-failing checks passed; **PR #5584 MERGED** (`gh pr view 5584 --json state` -> MERGED; `src/odyssey` on main, `src/projectodyssey` gone). |
