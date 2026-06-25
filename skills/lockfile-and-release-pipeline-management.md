---
name: lockfile-and-release-pipeline-management
description: "Recover drifted lockfiles, resync dependency lockfiles after manifest edits, fix silent release recipe failures, enforce version single-source-of-truth, configure Renovate for multi-ecosystem repos, and stabilize lockfile-backed Dependabot CI gates without deleting tests. Use when: (1) CI rejects a generated lockfile (pixi.lock, Cargo.lock, package-lock.json) and the source manifest is unchanged vs main, (2) editing package.json without regenerating package-lock.json causes npm ci EUSAGE failures, (3) `just release X.Y.Z` exits non-zero with 'nothing to commit' because pyprojects already have the target version, (4) project version is declared in multiple files that can drift and you need a single-source-of-truth strategy with pre-commit guards, (5) adding automated dependency updates (Renovate) to a C++20 repo with Conan, FetchContent, pixi, GHA, and Dockerfiles, (6) `pixi install` fails with `No candidates were found for <pkg> ==<version>` because a pinned nightly/dev-build artifact was garbage-collected from the channel, (7) multiple Dependabot PRs fail because CI contract tests hardcode exact dependency versions or split exact-peer dependency families across separate PRs."
category: ci-cd
date: 2026-06-17
version: "1.2.0"
user-invocable: false
history: lockfile-and-release-pipeline-management.history
verification: verified-ci
tags:
  - lockfile
  - pixi-lock
  - cargo-lock
  - package-lock
  - drift-recovery
  - npm-ci
  - eusage
  - release
  - just
  - bump-version
  - git-tag
  - versioning
  - importlib-metadata
  - pre-commit
  - renovate
  - conan
  - fetchcontent
  - tool-version-skew
  - nightly-build
  - artifact-gc
  - unsolvable-pin
  - mojo
  - pixi-install
  - dependabot
  - angular
  - peer-dependencies
  - pip-audit
  - contract-tests
  - vulnerability-allowlist
---

# Lockfile and Release Pipeline Management

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-17 |
| **Objective** | Canonical skill covering the full gap between "dependency declared" and "lockfile/version consistent in CI": verbatim lockfile restoration from main, npm lockfile resync, release recipe no-op diagnosis, version single-source-of-truth enforcement, Renovate setup for heterogeneous C++ repos, recovery from pinned nightly/dev-build artifact GC, and lockfile-backed Dependabot CI contract stabilization |
| **Outcome** | Merged from 5 verified skills; patterns confirmed across ProjectAgamemnon, ProjectProteus, ProjectScylla; v1.1.0 added the GC'd-nightly failure mode; v1.2.0 adds the Radiance Dependabot contract case |
| **Verification** | verified-ci (lockfile restore, npm resync, Radiance Dependabot contract stabilization); verified-local (release recipe, versioning, GC'd-nightly recovery); unverified (Renovate - app install in progress) |
| **History** | Previous v1.1.0 snapshot archived in `lockfile-and-release-pipeline-management.history` |

## When to Use

- A generated lockfile (`pixi.lock`, `Cargo.lock`, `poetry.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `go.sum`) is rejected by CI and the matching source manifest is **identical** to `origin/main`
- You've already tried local regeneration once and CI still rejects the result (tool-version skew between dev machine and CI runner)
- A `package.json` edit was committed without regenerating its sibling `package-lock.json`; CI fails with `npm error code EUSAGE`
- `just release X.Y.Z` ends with "nothing added to commit" / "Recipe `release` failed with exit code 1" even though no real problem exists
- Project declares `__version__` or version strings in multiple files (`pyproject.toml`, `pixi.toml`, `__init__.py`, CLI) that can drift
- CHANGELOG references phantom future versions that don't exist yet as tags
- Adding Renovate bot to a C++20 repo using Conan, CMake FetchContent, pixi, GitHub Actions, and Dockerfiles
- A pinned nightly or dev-build dependency (`==X.Y.Zb2.devYYYYMMDD`-style) can no longer be resolved because the artifact was GC'd from the package channel; you need to repin and lock
- Multiple Dependabot PRs fail because a contract test hardcodes exact dependency versions instead of checking that manifest and lockfile entries remain pinned and internally consistent
- Single-package frontend PRs fail `npm ci` because the ecosystem has exact peer dependencies (for example Angular packages) and the bot opened each peer-package bump separately
- A dependency-audit gate blocks on a vulnerability with no fixed version and the correct action is a narrow, expiring allowlist with tests, not disabling the audit or deleting tests

## Verified Workflow

### Quick Reference

```bash
# ── A. Verbatim lockfile restore from main ──────────────────────────────────
# Confirm source manifest matches main (empty output = safe to copy)
git diff origin/main..HEAD -- <path/to/manifest>

# Confirm main is GREEN on the same source SHA
gh run list --workflow=<workflow>.yml --branch=main --limit=3 \
  --json conclusion,headSha,displayTitle

# Restore generated file verbatim
git checkout origin/main -- <path/to/lockfile>

# Verify zero diff vs main on the restored file
git diff origin/main -- <path/to/lockfile> | wc -l   # must be 0

# Commit — DO NOT run install tools locally afterward
pre-commit run --files <path/to/lockfile>
git commit -S -m "fix(ci): align <lockfile> with main verbatim"
git push --force-with-lease

# ── B. npm lockfile resync after package.json edit ───────────────────────────
cd <pkg-dir>                   # MUST be same directory as the edited package.json
npm install                    # rewrites package-lock.json
git add package-lock.json
rm -rf node_modules && npm ci  # verify same command CI runs
git commit -m "chore(<pkg-dir>): regenerate package-lock.json after <dep> change"

# ── C. Release recipe no-op recovery ─────────────────────────────────────────
# Diagnose: git status clean + all pyprojects already at target version
git status
grep -H '^version = ' clients/python/pyproject.toml agamemnon/pyproject.toml
git log --oneline -5
git tag --list 'v*' --sort=-v:refname | head -5

# Manual recovery: skip the broken recipe, tag directly
git tag -s vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
git tag --verify vX.Y.Z
gh run list --workflow=<release-workflow>.yml --limit=2

# ── D. Version single-source-of-truth setup ──────────────────────────────────
# In package/__init__.py — read version from installed metadata
# from importlib.metadata import PackageNotFoundError, version as _get_version
# try:
#     __version__: str = _get_version("mypackage")
# except PackageNotFoundError:
#     __version__ = "0.0.0"

# Run consistency check
python3 scripts/check_package_version_consistency.py --verbose

# ── E. Renovate setup for C++20 repo ─────────────────────────────────────────
# Create renovate.json in repo root (see Results & Parameters)
# Install Renovate GitHub App at https://github.com/apps/renovate

# ── F. Pinned nightly artifact garbage-collected ─────────────────────────────
# Diagnosis: pixi install fails with
#   × failed to solve the conda requirements of 'default' 'linux-64'
#   ╰─▶ Cannot solve the request because of:
#       No candidates were found for <pkg> ==<exact-version>.
# Confirm the artifact is GC'd (pinned version absent from search results):
pixi search <pkg> -c <channel>          # e.g. -c https://conda.modular.com/max
# NOTE: pixi (<= 0.39.x) has NO `pixi lock` subcommand — the lock is a side
# effect of `pixi install`. `pixi lock` errors: unrecognized subcommand 'lock'.
# Recovery: repin manifest to the newest still-available build, then lock:
#   edit pixi.toml  →  <pkg> = "==<newest-available-build>"
pixi install                            # generates pixi.lock against the new pin
git add pixi.toml pixi.lock
git commit -S -m "fix(deps): repin <pkg> to <build> after nightly GC; commit pixi.lock"

# ── G. Lockfile-backed Dependabot CI contract stabilization ─────────────────
# Enumerate failing bot PRs and group by failure signature.
gh pr list --state open --author app/dependabot --json number,title,statusCheckRollup
gh pr checks <PR> --repo <owner/repo>

# Prefer structural contract checks over current-version literals:
# - manifest requires an exact pin where policy demands one
# - lockfile root/package entries match the manifest
# - related package entries remain internally consistent

# Exact-peer families must usually move together, then the lockfile is regenerated.
cd vendor/model_explorer/src/ui
npm install --package-lock-only
npm ci

# After the stabilization PR lands, update still-open Dependabot PR branches.
gh api -X PUT repos/<owner>/<repo>/pulls/<PR>/update-branch \
  -f expected_head_sha=<current-head-sha>
```

### Detailed Steps

#### A — Verbatim Lockfile Restore

1. **Confirm source manifests match main.** If `pixi.toml`/`Cargo.toml`/`package.json` differs, this approach does NOT apply — regenerate properly.

   ```bash
   git fetch origin
   git diff origin/main..HEAD -- <path/to/manifest>
   # Empty output = source files match; generated file is the only drift
   ```

2. **Confirm main is GREEN** on this source-file SHA. Check the latest CI run on main via `gh run list`.

3. **Restore the generated file verbatim:**

   ```bash
   git checkout origin/main -- <path/to/lockfile>
   # Multiple files at once if needed:
   git checkout origin/main -- clients/python/pixi.lock clients/python/tests/test_bump_version.py
   ```

4. **Verify zero diff vs main:**

   ```bash
   git diff origin/main -- <path/to/lockfile> | wc -l   # must be 0
   ```

5. **Commit and push — CRITICAL: do NOT run `pixi install` / `cargo update` / `npm install` locally afterward.** Local tool invocations re-write the lock based on the local binary version, undoing the alignment.

   ```bash
   pre-commit run --files <path/to/lockfile>
   git commit -S -m "fix(ci): align <lockfile> with main verbatim"
   git push --force-with-lease
   ```

**When this approach is WRONG:** The generated file SHOULD differ from main because your PR adds/removes/changes dependencies; the source manifest has changes not yet propagated to the lock; main itself is RED (copying its lock propagates the bug).

#### B — npm Lockfile Resync

1. **Identify the directory owning the edited `package.json`.** Running `npm install` from repo root regenerates the WRONG lockfile or none at all.

2. **Confirm a lockfile exists** before assuming it's absent:

   ```bash
   ls <pkg-dir>/package-lock.json <pkg-dir>/npm-shrinkwrap.json 2>/dev/null
   ```

3. **Run `npm install` in that directory.** This rewrites `package-lock.json` to match the new `package.json` and creates `node_modules/` (which must NOT be committed — verify `.gitignore`).

4. **Stage ONLY the lockfile** and verify with CI's exact command:

   ```bash
   git add <pkg-dir>/package-lock.json
   cd <pkg-dir> && rm -rf node_modules && npm ci   # must succeed with no EUSAGE
   ```

5. **Both `package.json` and `package-lock.json` MUST land in the same PR.** Never split them across two PRs.

**Sub-agent dispatch template addition** — append to any brief touching `package.json`:

```text
If you edit any package.json:
  1. cd into the SAME directory as that package.json.
  2. Run `npm install` to regenerate package-lock.json.
  3. Run `rm -rf node_modules && npm ci` to verify the lockfile is in sync.
  4. Stage and commit ONLY package.json AND package-lock.json (NOT node_modules/).
  5. Both files MUST land in the same PR.
```

#### C — Release Recipe No-op Recovery

1. **Confirm this is the no-op trap, not a real failure.** `git status` should be clean. Grep every source-of-truth pyproject file for the target version. If they all already show `version = "X.Y.Z"`, the recipe failed because `bump-version.py` had nothing to do.

2. **Skip the recipe; tag manually:**

   ```bash
   git tag -s vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z   # NOT --follow-tags (no commit alongside it)
   ```

3. **Verify the tag is signed** and the release workflow fired (most trigger on `push.tags: ["v*"]`, not PR merge).

4. **File a follow-up PR** applying the justfile fix in Results & Parameters so future release runs aren't fragile.

#### D — Version Single-Source-of-Truth

1. **Switch `__init__.py` to `importlib.metadata`** so `pyproject.toml` is the only declaration site.

2. **Eliminate hardcoded CLI version** — import `__version__` from the package's `__init__.py`.

3. **Create a pre-commit consistency checker** using `tomllib` (not regex) that validates `pixi.toml`, `pyproject.toml`, `__init__.py`, and `CHANGELOG.md`.

4. **Fix CHANGELOG phantom versions** — replace aspirational version references with `[Unreleased]` or "a future major version."

5. **Release workflow**: trigger on `push.tags: ["v*"]`; validate tag version matches `pyproject.toml`; use `gh release create --generate-notes`.

#### E — Renovate for C++20 Repos

1. Create `renovate.json` in each repo root (see config in Results & Parameters).
2. Install the Renovate GitHub App at `https://github.com/apps/renovate` for the org.
3. For meta-repos with submodules, use `ignorePaths` in the root config; each submodule gets its own `renovate.json`.
4. CMake FetchContent `GIT_TAG` has no native Renovate manager — use the custom `regex` manager.

#### F — Pinned Nightly Artifact Garbage-Collected

This is a **distinct, higher-severity failure** from lockfile drift (section A). In
section A the dependency is still solvable — only the *generated* lockfile is out of
sync. Here the **pinned dependency itself is unsolvable** because its artifact no
longer exists on the package channel. Nightly / dev / dated-snapshot builds are
**garbage-collected** from channels on a rolling window (often weeks). A pin to a
version like `==1.0.0b2.dev2026050805` will eventually become unsolvable.

1. **Recognize the diagnosis signature.** `pixi install` fails with:

   ```text
   × failed to solve the conda requirements of 'default' 'linux-64'
   ╰─▶ Cannot solve the request because of: No candidates were found for mojo
       ==1.0.0b2.dev2026050805.
   ```

   `No candidates were found for <pkg> ==<exact-version>` means the **artifact is
   unavailable**, NOT that the manifest drifted. This is distinct from the
   lockfile-drift failures in section A (where CI rejects a *generated* file but the
   dependency is still solvable).

2. **Confirm the artifact is GC'd** — search the channel for what remains:

   ```bash
   pixi search mojo -c https://conda.modular.com/max
   ```

   If the pinned version is **absent from the search results**, the artifact is gone.
   The channel typically retains only the release build and a few older stable
   versions; dated nightlies are not retained.

3. **Note: `pixi` (≤ 0.39.x) has no standalone `pixi lock` subcommand.** The lockfile
   is generated only as a side effect of `pixi install`. Verified: `pixi 0.39.5`
   responds to `pixi lock` with `unrecognized subcommand 'lock'`.

4. **Recover by repinning to the newest still-available build.** Pick the newest
   version from the `pixi search` output (prefer a release build over another
   nightly), edit the manifest, regenerate the lock, and **commit `pixi.lock`
   immediately** — while the artifact still exists:

   ```bash
   # edit pixi.toml: mojo = "==1.0.0b1"   (newest still-available build)
   pixi install
   git add pixi.toml pixi.lock
   git commit -S -m "fix(deps): repin mojo to 1.0.0b1 after nightly GC; commit pixi.lock"
   ```

5. **If a transitive/upstream dependency also pins the GC'd version**, the repin is a
   **deliberate divergence** from upstream — bumping to match upstream is not an
   option because upstream is equally broken. Document the divergence in the project's
   dependency notes / failure-cascade matrix, and flag downstream code for
   re-verification against the new toolchain version.

**Prevention (the load-bearing lesson):** Generate and commit the lockfile the moment
a dependency is pinned — especially for nightly/dev builds. The lockfile is the only
durable record of the resolved artifact. Once the nightly is GC'd, a committed
`pixi.lock` may still let `pixi install --locked` succeed (the lock references the
artifact by content hash + URL); with no lockfile, the pin is unrecoverable. The
window to lock is "while the artifact still exists" — "lock it later" is not a plan.
Prefer pinning a release build over a dated nightly when reproducibility matters.

#### G - Lockfile-backed Dependabot CI Contract Stabilization

1. **Enumerate failing bot PRs and group by failure signature.** Use the PR check
   rollups and logs to separate deterministic contract failures from runner flakes.
   Multiple PRs failing the same test usually means the contract is too literal, not
   that every PR is independently broken.

2. **Replace hardcoded current versions with structural checks.** If a test asserts
   "dev extra X must equal version Y" or "lockfile package Z must equal version Y",
   check the invariant instead: exact pins where policy requires them, manifest and
   lockfile agreement, and internal consistency across related lockfile entries.
   Do not delete the test; make it express the dependency contract that survives a
   legitimate Dependabot bump.

3. **Group exact-peer dependency families.** For ecosystems with exact peer ranges
   (Angular is the common case), a one-package Dependabot PR can be impossible to
   install. Move the exact-peer family together in one stabilization PR, regenerate
   the lockfile from the package directory, and let superseded bot PRs close.

4. **Use narrow allowlists for no-fixed-version advisories.** If an audit gate fails
   on an advisory with no fixed versions, allow exactly the affected package,
   version, and advisory, with an expiry and a condition that fixed versions remain
   empty. Add tests that fail when the advisory becomes fixable or the allowlist
   expires.

5. **Verify the same gates that failed.** Run focused contract tests, `npm ci`,
   package/build validation, and the security policy script locally where feasible,
   then require a fresh CI pass on the stabilization PR.

6. **Update original bot PR branches after the stabilization lands.** For still-open
   Dependabot PRs, call the update-branch API with the current head SHA so the bot
   branch picks up the generalized tests. Let branches that are now no-ops close
   naturally rather than hand-editing every bot branch.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Install pixi v0.39.5 locally (matching CI pin) and regenerate lock | Pinned developer pixi to CI's version, regenerated `pixi.lock` from branch | Produced another divergent format: "lock-file not up-to-date with the project". OS/glibc/conda channel cache differences still cause drift | Pinning dev pixi to CI's version is necessary but not sufficient — use verbatim copy from main when source manifest is unchanged |
| Regenerate with dev pixi v0.67.2 and accept format drift | Ran newer local pixi, committed output | Newer pixi writes a lock format the older CI pixi rejects; v0.39.5 vs v0.67.2 binary skew | Newer-to-older pixi lockfile compatibility is NOT guaranteed |
| Copy verbatim then run `pixi install` locally to "sync" environment | `git checkout origin/main -- pixi.lock` then ran `pixi install` | `pixi install` immediately re-wrote the lock based on the local binary, reintroducing exact drift | Once you copy verbatim, do NOT touch the file with any install tool |
| Easy-issue sweep agent edited `package.json`, claimed no lockfile present | Ran `find . -name package-lock.json` from repo root with wrong CWD depth, missed `dagger/package-lock.json` | CI failed with `npm error code EUSAGE`: `Invalid: lock file's @types/node@25.6.2 does not satisfy @types/node@20.19.40` | Always run `ls <pkg-dir>/package-lock.json` from the same directory as the edited file; never trust a `find` result as proof of absence |
| Edit `package.json` and push without `npm install` | Hoped local `node_modules/` was fresh enough | Local builds use `npm install` masking the problem; CI uses `npm ci` (strict) and refuses any mismatch | Use the same command CI uses: `npm ci` after `rm -rf node_modules` |
| Run `npm install` from repo root when `package.json` is nested | Assumed npm would auto-discover the nested package | npm only operates on CWD's `package.json`; from repo root with no root `package.json` the command errors | Always `cd <pkg-dir>` first |
| Re-run `just release X.Y.Z` after seeing "nothing to commit" error | Assumed transient issue | `bump-version.py` is still a no-op; re-running cannot escape the trap — recipe is deterministic | Recipe failure is deterministic when bump is a no-op; recover the tag manually instead |
| `git commit --allow-empty` before re-running the release recipe | Tried to satisfy the commit step | Doesn't fix the recipe-flow problem and pollutes history with a meaningless empty commit | Don't paper over recipe bugs with manual side-commits |
| Edit pyprojects down to `0.0.1` then run `just release X.Y.Z` | Forced bump-version to have work to do | Adds a useless version-down-then-up cycle to git history; reviewers will question it | Manipulating source files to satisfy a broken recipe pollutes history |
| Release recipe stages only one of N pyproject files | Pre-existing justfile only `git add`s `clients/python/pyproject.toml` | Silently drops bump to `agamemnon/pyproject.toml` — ships with one file bumped, other dangling in working tree | Whenever `bump-version.py` writes to N files, `git add` must list all N |
| Test file at `tests/unit/test_version_consistency.py` | Placed test directly under `tests/unit/` | Pre-commit hook `check-unit-test-structure` requires tests in sub-packages | Check project test structure conventions before placing new test files |
| Regex-based TOML parsing in consistency script | Used `re.match(r'^version\s*=\s*"([^"]+)"')` | Fragile: breaks on inline comments, multi-line strings, non-standard formatting | Use `tomllib` (stdlib since Python 3.11) for reliable TOML parsing |
| Dependabot for Conan \| pixi \| FetchContent | Considered GitHub Dependabot as Renovate alternative | Dependabot has no native Conan, pixi, or FetchContent support | Renovate is the correct choice for C++ ecosystems |
| Single Renovate config at meta-repo root covering all submodules | One `renovate.json` at Odysseus root | Submodules are separate git repos — Renovate needs a config per repo to open PRs | Use `ignorePaths` in the meta-repo config; put individual configs in each submodule |
| Pinned a Mojo nightly (`==1.0.0b2.dev2026050805`) and deferred generating the lockfile | Left `pixi.lock` ungenerated for weeks after pinning the nightly toolchain build | The nightly was garbage-collected from `conda.modular.com/max`; `pixi install` then failed with `No candidates were found`. With no committed lockfile, the pin was unrecoverable — had to repin to a different build | Nightly/dev-build artifacts are GC'd from channels. Generate and commit the lockfile the moment the dependency is pinned, while the artifact still exists. Prefer pinning a release build over a dated nightly when reproducibility matters |
| Delete or relax flaky-looking dependency contract tests | Removed hardcoded version assertions from the failing path | The failures were deterministic contract drift, not flaky tests; deleting them would hide future manifest/lockfile mismatches | Keep the tests and generalize them to structural invariants: exact pins, manifest/lockfile agreement, and internal consistency |
| Let single Angular package PRs update independently | Trusted Dependabot's one-package bumps for an exact-peer Angular family | `npm ci` could not resolve the split exact-peer set because related Angular packages must move together | Group exact-peer packages in one PR and regenerate the lockfile from the owning package directory |
| Add an empty or broad `pip-audit` allowlist | Suppressed the audit failure without package/version/advisory scope or expiry | A broad allowlist would hide unrelated vulnerabilities or remain after a fixed version became available | Scope allowlists to package, version, advisory, expiry, and "no fixed versions"; test stale and now-fixable behavior |

## Results & Parameters

### A. Lockfile Restore — Decision Flowchart

```
Generated file CI failure on feature branch
  │
  ├─ Source manifest differs from main?  ──► Regenerate (different skill)
  ├─ Branch adds new deps to source?     ──► Regenerate (different skill)
  ├─ main is RED on same source SHA?     ──► Fix main first (different skill)
  └─ Source matches main, main is GREEN, no new deps
        └─► THIS SKILL: git checkout origin/main -- <generated-file>
                         commit, push, DO NOT run install tool locally
```

Applies to: `pixi.lock`, `Cargo.lock`, `poetry.lock`, `package-lock.json`, `yarn.lock`,
`pnpm-lock.yaml`, `go.sum`, `requirements.txt` (pip-compile), vendored JSON/YAML.

### B. npm Resync — Sub-Agent Brief Expansion

When an easy-issue brief says "change `<dep>`'s version in `package.json`", expand to:

> "Change `<dep>`'s version in `<pkg-dir>/package.json` AND regenerate `<pkg-dir>/package-lock.json`
> by running `npm install` in `<pkg-dir>/`. Commit both files in the same PR."

### C. Justfile Fix for No-op Bump Trap

```diff
 release VERSION push='true':
   #!/usr/bin/env bash
   set -euo pipefail
   python3 scripts/bump-version.py "{{VERSION}}"
-  git add clients/python/pyproject.toml
-  git commit -S -m "chore: bump version to v{{VERSION}}"
+  git add clients/python/pyproject.toml agamemnon/pyproject.toml
+  if ! git diff --cached --quiet; then
+    git commit -S -m "chore: bump version to v{{VERSION}}"
+  else
+    echo "Version already at {{VERSION}}; skipping no-op bump commit"
+  fi
   git tag -s "v{{VERSION}}" -m "v{{VERSION}}"
   if [ "{{push}}" = "true" ]; then
     git push --follow-tags
   fi
```

Two required changes: (1) stage ALL source-of-truth pyproject files; (2) gate the commit on
`git diff --cached --quiet` so no-op bumps don't abort the recipe before tagging.

### D. importlib.metadata Pattern

```python
# package/__init__.py — read version from installed metadata
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

try:
    __version__: str = _get_version("mypackage")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback when package is not installed
```

```python
# Consistency script — use tomllib, not regex
import tomllib  # Python 3.11+; use tomli as fallback for 3.10

def get_pyproject_version(path: Path) -> str:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def check_init_uses_importlib(path: Path) -> bool:
    content = path.read_text()
    return not re.search(r'^__version__\s*=\s*["\'][\d.]+["\']', content, re.MULTILINE)
```

```yaml
# Pre-commit hook registration
- id: check-package-version-consistency
  name: Check Package Version Consistency
  entry: pixi run python scripts/check_package_version_consistency.py
  language: system
  files: ^(pyproject\.toml|pixi\.toml|package/__init__\.py|CHANGELOG\.md)$
  pass_filenames: false
```

### E. Renovate Config for C++20 Repo

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "schedule": ["before 5am on Monday"],
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["CMakeLists\\.txt$"],
      "matchStrings": [
        "FetchContent_Declare\\([\\s\\S]*?GIT_REPOSITORY\\s+https://github\\.com/(?<depName>[^/]+/[^.]+)\\.git\\s+GIT_TAG\\s+(?<currentValue>v?[\\d.]+)"
      ],
      "datasourceTemplate": "github-tags",
      "versioningTemplate": "semver"
    }
  ],
  "packageRules": [
    { "matchManagers": ["conan"], "groupName": "C++ Conan dependencies" },
    { "matchManagers": ["pixi"], "groupName": "pixi build tools",
      "schedule": ["before 5am on the first day of the month"] },
    { "matchManagers": ["github-actions"], "groupName": "GitHub Actions", "automerge": true }
  ]
}
```

Meta-repo config (root with submodules): add `"ignorePaths": ["control/**", "testing/**", ...]`
to prevent scanning submodule directories — each submodule owns its own `renovate.json`.

| Ecosystem | Renovate Manager | Native? |
|-----------|-----------------|---------|
| Conan 2.x (`conanfile.py`) | `conan` | Yes |
| pixi.toml (conda-forge) | `pixi` | Yes |
| CMake FetchContent (`GIT_TAG`) | `regex` (custom) | No |
| GitHub Actions (`uses:`) | `github-actions` | Yes |
| Dockerfile (`FROM`) | `dockerfile` | Yes |
| Python (`pyproject.toml`) | `pep621` | Yes |

### F. Pinned Nightly Artifact GC — Verified Facts

| Fact | Detail |
|------|--------|
| No `pixi lock` subcommand | `pixi` (≤ 0.39.x) has no standalone `pixi lock` — verified: `pixi 0.39.5` → `pixi lock` errors with `unrecognized subcommand 'lock'`. The lockfile is generated only as a side effect of `pixi install` |
| GC diagnosis signature | `pixi install` failing with `No candidates were found for <pkg> ==<exact-version>` means the *artifact* is unavailable, NOT that the manifest drifted (distinct from section A lockfile drift) |
| Confirmation command | `pixi search <pkg> -c <channel>` — if the pinned version is absent from the search results, the artifact has been GC'd from the channel |
| Recovery | Repin the manifest to the newest still-available build from `pixi search`, run `pixi install` to regenerate `pixi.lock`, commit the lockfile immediately |

**Prevention rule:** generate and commit the lockfile the moment a dependency is
pinned — especially for nightly/dev builds. The lockfile is the only durable record
of the resolved artifact; once the nightly is GC'd, "lock it later" is no longer
possible. Prefer pinning a release build over a dated nightly when reproducibility
matters.

### G. Radiance Dependabot Contract Stabilization - Verified Facts

| Fact | Detail |
|------|--------|
| Original scope | 10 failing Dependabot PRs (#886-#895) across Python and frontend dependency updates |
| Contract fix | Replaced a concrete dev-extra version expectation with exact-pin checks; later generalized the frontend Playwright lock contract so expected versions are derived from `package.json` and validated across `package-lock.json` root, `node_modules/playwright`, `playwright` -> `playwright-core`, and `node_modules/playwright-core` |
| Security fix | Added a narrow, expiring allowlist for `torch==2.11.0` / `CVE-2025-3000`, limited to the advisory's no-fixed-version state, with tests for expiry and fixable-advisory behavior |
| Frontend fix | Grouped exact-peer Angular package updates, regenerated `vendor/model_explorer/src/ui/package-lock.json`, and left unsupported semver-major `@angular-devkit/*` updates out of scope |
| Verification | Stabilization PR #897 reached green CI and merged; follow-up PR #904 reached green CI and merged; original Python Dependabot PRs #886-#890 passed after branch updates; #902 passed after #904; superseded Angular PRs #891-#895 closed automatically |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | PR #400 — `clients/python/pixi.lock` verbatim restore, 2026-05-18; 3 failed regeneration attempts; v0.1.0 tag cut shortly after | See `git log --grep="align clients/python/pixi.lock with main verbatim"` in ProjectAgamemnon |
| ProjectAgamemnon | Phase F-6 v0.1.0 release cut, 2026-05-18 — `just release 0.1.0` no-op trap; manual `git tag -s v0.1.0 && git push origin v0.1.0` triggered `python-client-release.yml` | Both `clients/python/pyproject.toml` and `agamemnon/pyproject.toml` already at 0.1.0 |
| ProjectProteus | PR #135 (regression) — `@types/node` downgraded in `dagger/package.json` only; `npm ci` EUSAGE failure | Easy-issue sweep agent missed `dagger/package-lock.json` |
| ProjectProteus | PR #136 (fix) — regenerated `dagger/package-lock.json` via `npm install` in `dagger/`, CI green | Validates the regen-and-commit pattern end-to-end |
| ProjectScylla | Issue #1527 (PR #1557) — versioning remediation; 35 tests passing, all pre-commit hooks green | `importlib.metadata` + `tomllib` consistency checker |
| ProjectScylla | Issue #1535 (PR #1562) — reconcile CHANGELOG aspirational versions; 4808 total tests passing | Phantom version refs replaced with `[Unreleased]` convention |
| Odysseus / ProjectAgamemnon / ProjectNestor / ProjectCharybdis | Renovate multi-ecosystem C++20 config — Conan + FetchContent regex + pixi + GHA + Dockerfile | Unverified: app installation in progress |
| predictive-coding research project | Mojo nightly `1.0.0b2.dev2026050805` GC'd from `conda.modular.com/max`; repinned to `1.0.0b1` and locked, 2026-05-19 | First `pixi install` failed with `No candidates were found`; no `pixi.lock` had ever been committed. Upstream dep (pinned git SHA) also pinned the GC'd nightly — repin was a documented deliberate divergence |
| Radiance | Issues #896/#903, PRs #897/#904, 2026-06-17 | Generalized lockfile-backed Dependabot contract tests, grouped exact-peer Angular updates, added a narrow no-fixed-version `pip-audit` allowlist, and updated original bot PRs until CI passed |
