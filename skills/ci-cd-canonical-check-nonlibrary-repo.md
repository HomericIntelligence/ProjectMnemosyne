---
name: ci-cd-canonical-check-nonlibrary-repo
description: "Implement meaningful canonical CI check-runs for a non-library, content, manifest, dataset, or configuration repository. Use when: (1) an ecosystem status board requires a `package`, `release`, or `install` check that seems inapplicable, (2) the board derives state from live check-runs on main, (3) choosing a real distributable rather than forcing a wheel build or a no-op check, (4) adding hardened artifact, release, or clean-install validation to mirrored workflows."
category: ci-cd
date: 2026-07-17
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: ["canonical-check", "ci-naming", "nonlibrary", "manifest-repo", "dataset-repo", "package", "release", "install", "artifact", "branch-protection"]
history: ci-cd-canonical-check-nonlibrary-repo.history
---

# Canonical CI Checks for Non-Library Repositories

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Give non-library repositories an honest, useful canonical CI check rather than a no-op or a forced Python package build |
| **Outcome** | One decision workflow for package, release, and install check-runs with real artifacts and fail-loud validation |
| **Verification** | verified-local for the reproducible-package branch; release/install branches remain implementation plans |
| **History** | [absorbed package, release, and install sources](./ci-cd-canonical-check-nonlibrary-repo.history) |

## When to Use

- An ecosystem convention or status board requires a canonical CI check such as `package`, `release`, or `install`
- The repository ships manifests, datasets, skills, documents, or configuration rather than an importable library
- An issue proposes documenting a category as “N/A,” but the board is generated from check-runs emitted on `main`
- A workflow forbids silent suppression (`|| true`, `continue-on-error`, advisory-only warnings) and every check must have a real failure signal

## Verified Workflow

### Quick Reference

```bash
# Verify the convention and how the board is populated before designing a job.
rg -n 'package|release|install' path/to/ci-naming-convention.md
gh run list --branch main --limit 20

# Determine whether a traditional Python build is real evidence or cargo cult.
rg -n '^\[build-system\]|^version\s*=' pyproject.toml
python -m build

# Locate actual workflow triggers and callers before mirroring jobs.
rg -n 'push:|pull_request:|workflow_call|uses: ./.github/workflows/' .github/workflows
```

### Decision steps

1. Fetch and read the cited CI-naming convention. Confirm the exact required check-run name and whether the status board reads live check-runs from `main`.
2. Inspect the repository's real distributable. Do not add a build backend merely because the check is named `package`; a content archive can be the honest package.
3. Choose the branch below. Each must produce a meaningful artifact or validation result and run on `push` to `main`, not only pull requests.
4. Reuse pinned action SHAs and hardened workflow conventions already present in the repository. Do not hide failures with skip, warning, or suppression paths.
5. Verify any workflow-call mirror has a real caller before treating it as a check-run emitter. Sync documentation of required contexts.
6. Add a branch-protection context only after the job lands and emits the intended name on `main`; make that registration idempotent and post-merge.

### Worked Example — `package`: reproducible content archive

For a manifest/dataset repository, package the real data directories as a deterministic tarball:

```bash
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 1970-01-01' \
  -czf dist/project-package.tar.gz manifests/ RELEASE_INFO
sha256sum dist/project-package.tar.gz > dist/SHA256SUMS
sha256sum --check dist/SHA256SUMS
```

Round-trip extract the archive, compare the included tree, require a nonzero file count, and upload
the artifact. This branch was verified locally; use a tested script when the repository's normal
quality gates cover scripts rather than hiding complex shell logic in workflow YAML.

### Worked Example — `release`: versioned snapshot and publication

For a repository whose real release is a dataset or manifest snapshot, build the same verified
archive on `main` so the `release` check appears on the board. On a `v*` tag, publish that artifact
with `gh release create` only after confirming workflow token permissions and the organization's
release policy. Derive the tag from `GITHUB_REF_NAME` on shallow checkouts; `git describe` may not
have local tags.

### Worked Example — `install`: clean-environment artifact smoke test

If a package artifact exists, make `install` download or build it, install it into a clean virtual
environment, and import the installed top-level modules. If the prerequisite package job has not
merged, first run `python -m build` as an explicit gate. Either stop as blocked or build inline;
never emit a green “skip if not buildable” result. Derive import targets from the built wheel's
`top_level.txt` rather than guessing a future package layout.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Document the check as N/A | Added prose instead of a job | A board built from main check-runs has no N/A marker | Emit a real, meaningful check-run |
| Force a wheel build | Added packaging metadata to a content repository | The project had no consumable Python library and flat-layout discovery failed | Validate the repository's actual artifact |
| Add a no-op or silent skip | Made the required job green without testing | It gives the status board a false success signal | Fail loudly or remain explicitly blocked |
| Mirror without checking workflow callers | Copied a job into `workflow_call` YAML | An uncalled workflow emits no check-run | Verify execution wiring before mirroring |
| Register branch protection in the same PR | Required a context before it existed on main | It can block the PR or create an impossible requirement | Register the context post-merge |

## Results & Parameters

### Required properties

- The check-run name matches the convention exactly and appears on main.
- The job validates a real package, release, or installation outcome.
- Artifacts are reproducible where feasible, checksummed, and round-trip verified.
- Workflow policy guards remain effective; no suppressed failures are introduced.
- Local simulation covers the workflow's critical run blocks before the first push.

### Branch selection

| Required check | Real proof |
|----------------|------------|
| `package` | Build and verify the repository's actual distributable archive |
| `release` | Produce a versioned snapshot and publish only on a validated tag path |
| `install` | Install a built artifact in a clean environment and import its exported modules |

## Verified On

| Context | Details |
|---------|---------|
| Myrmidons package check | Reproducible archive, checksum, round-trip validation, and local workflow simulation verified. |
| Mnemosyne/Myrmidons install and release plans | Design guidance only; verify action pins, permissions, and CI behavior before claiming CI verification. |
