---
name: tooling-pixi-lockfile-churn-self-reference
description: "Stop perpetual `pixi.lock` regeneration in Python projects that combine a self-referential `[pypi-dependencies]` editable path entry with `hatch-vcs` dynamic versioning. Use when: (1) every `pixi install` / `pixi run` rewrites `pixi.lock` even on a clean tree with no manifest edits, (2) pre-commit hooks fail because `pixi.lock` is perpetually dirty, (3) `pixi.toml` declares the package itself under `[pypi-dependencies]` with `path = \".\"` and `editable = true`, and (4) `pyproject.toml` uses `dynamic = [\"version\"]` with `[tool.hatch.version] source = \"vcs\"` (hatch-vcs). The combination makes pixi treat the source-of-truth version as changed on every invocation."
category: tooling
date: 2026-05-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pixi
  - pixi-lock
  - lockfile-churn
  - hatch-vcs
  - dynamic-version
  - editable-install
  - pypi-dependencies
  - self-reference
  - pre-commit
  - no-build-isolation
---

# Pixi Lockfile Churn from Self-Reference + hatch-vcs

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-24 |
| **Objective** | Eliminate perpetual `pixi.lock` churn caused by combining a self-referential editable `[pypi-dependencies]` entry with `hatch-vcs` dynamic versioning in the same Python project. |
| **Outcome** | Removed the self-package entry from `[pypi-dependencies]`; installed the package on demand via a `pixi run dev-install = "pip install -e . --no-deps"` task. Pre-commit workflow runs `pixi install` then `pixi run dev-install`. `pixi.lock` is now stable across invocations; CI is green. |
| **Verification** | verified-ci (PRs #457, #526, #530, #532 merged with CI green) |

## When to Use

- Every `pixi install` or `pixi run <task>` rewrites `pixi.lock` on a clean tree with no manifest edits.
- Pre-commit fails repeatedly because `pixi.lock` shows up as dirty even though no human edited it.
- `pixi.toml` contains a self-referential editable entry like:

  ```toml
  [pypi-dependencies]
  mypackage = { path = ".", editable = true }
  ```

- And `pyproject.toml` declares:

  ```toml
  [project]
  dynamic = ["version"]

  [tool.hatch.version]
  source = "vcs"
  ```

- `git checkout -- pixi.lock` is blocked by a safety/pre-commit hook so manual cleanup fails.
- You considered upgrading Pixi to v0.69 + lockfile v7 (which removes input hashes) but want a localized fix that doesn't ripple through the whole ecosystem.

## Verified Workflow

### Quick Reference

```toml
# pixi.toml — REMOVE this section (or remove the self-entry only):
# [pypi-dependencies]
# mypackage = { path = ".", editable = true }   # ← delete this line

# pixi.toml — ADD a task that installs the package editable on demand:
[tasks]
dev-install = "pip install -e . --no-deps"
```

```bash
# After the change, set up a working environment:
pixi install --environment default
pixi run dev-install                   # one-off editable install of the package itself

# Pre-commit / CI invocation pattern:
pixi install --environment default
pixi run dev-install
pixi run pre-commit run --all-files

# Verify pixi.lock no longer churns:
git status --porcelain pixi.lock       # should be empty after `pixi install`
pixi install && git diff --stat pixi.lock   # should report zero changes
```

### Detailed Steps

1. **Confirm the failure signature.** On a clean tree:

   ```bash
   git status --porcelain pixi.lock      # empty
   pixi install
   git status --porcelain pixi.lock      # NOT empty ⇒ churn confirmed
   ```

2. **Verify the two preconditions both hold:**

   - `pixi.toml` has a `[pypi-dependencies]` entry pointing at `path = "."` with `editable = true`.
   - `pyproject.toml` has `dynamic = ["version"]` plus `[tool.hatch.version] source = "vcs"`.

   If only one holds, this skill does not apply — see the
   `lockfile-and-release-pipeline-management` skill for general drift recovery.

3. **Remove the self-referential entry from `pixi.toml`.** Delete the
   `mypackage = { path = ".", editable = true }` line (and the entire
   `[pypi-dependencies]` table if it becomes empty).

4. **Add a `dev-install` task** that installs the package editable without
   touching the lockfile and without `--no-build-isolation`:

   ```toml
   [tasks]
   dev-install = "pip install -e . --no-deps"
   ```

   `--no-deps` is essential: dependencies are still managed by pixi, the
   `pip` step only registers the editable package itself.

5. **Update CI and pre-commit invocations** to call `pixi install` followed by
   `pixi run dev-install` before running hooks/tests that import the package:

   ```yaml
   - run: pixi install --environment default
   - run: pixi run dev-install
   - run: pixi run pre-commit run --all-files
   ```

6. **Commit the new `pixi.lock` once,** then verify subsequent `pixi install`
   runs produce zero diff:

   ```bash
   pixi install
   git add pixi.toml pixi.lock
   git commit -S -m "fix(tooling): stop pixi.lock churn from self-reference + hatch-vcs"
   pixi install && git diff --exit-code pixi.lock   # must exit 0
   ```

7. **Do NOT try `[pypi-options] no-build-isolation = true`** as a fix —
   see Failed Attempts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Keep the self-package entry in `[pypi-dependencies]` and add `[pypi-options] no-build-isolation = true` | CI (pixi v0.63.2) failed with `BackendUnavailable: Cannot import 'hatchling.build'` — pip's PEP 517 build subprocess could not see hatchling installed in the parent pixi env | `no-build-isolation` requires the build backend to be visible to the pip subprocess; pixi's environment isolation breaks that visibility. Don't reach for this flag to mask the self-reference problem |
| 2 | Upgrade to Pixi v0.69.0 with lockfile v7 (which drops input hashes) | Ecosystem-wide change touching every consumer repo; risk and rollout cost too high for a localized symptom | Defer ecosystem-wide pixi version bumps; fix the root cause (the self-reference) in the affected repo instead |
| 3 | `git checkout -- pixi.lock` on a clean tree to undo the churn | A pre-commit/safety hook blocked the raw checkout | Manual `git checkout` of generated files isn't a reliable workaround when safety hooks are active — eliminate the source of churn rather than papering over it |

## Results & Parameters

### Final `pixi.toml` Snippet

```toml
# No self-reference under [pypi-dependencies]. If the table is otherwise empty,
# remove it entirely.

[tasks]
dev-install = "pip install -e . --no-deps"
# ...other tasks...
```

### Final `pyproject.toml` (unchanged — kept for reference)

```toml
[build-system]
requires = ["hatchling>=1.27.0,<2", "hatch-vcs>=0.4.0,<1"]
build-backend = "hatchling.build"

[project]
name = "mypackage"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
```

### CI / Pre-commit Invocation Order

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0          # hatch-vcs needs full history for git tags
  - uses: prefix-dev/setup-pixi@v0.8.1
  - run: pixi install --environment default
  - run: pixi run dev-install
  - run: pixi run pre-commit run --all-files
```

### Expected Output

- `pixi install` on a clean tree produces zero diff in `pixi.lock`.
- `pre-commit run --all-files` does not flag `pixi.lock`.
- `python -c "import mypackage; print(mypackage.__version__)"` returns the
  git-tag-derived version after `pixi run dev-install`.
- `pip show mypackage` lists the package as editable, installed from the
  repo path.

### Decision Matrix

| Symptom | Self-ref in `[pypi-dependencies]`? | `hatch-vcs` dynamic version? | Apply this skill? |
| --- | --- | --- | --- |
| `pixi.lock` churn on clean tree | yes | yes | **Yes** |
| `pixi.lock` churn on clean tree | yes | no | Partial — removing self-ref alone often suffices |
| `pixi.lock` churn on clean tree | no | yes | No — see `lockfile-and-release-pipeline-management` |
| `pixi.lock` drift vs `main` only | n/a | n/a | No — see `lockfile-and-release-pipeline-management` (section A) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PRs #457, #526, #530, #532 (merged 2026-05) — removed `homericintelligence-hephaestus = { path = ".", editable = true }` from `[pypi-dependencies]`, added `dev-install` task, updated pre-commit workflow | CI green; `pixi.lock` stable across invocations |

## References

- [lockfile-and-release-pipeline-management](lockfile-and-release-pipeline-management.md) — general lockfile drift recovery (different failure mode)
- [hatch-vcs-pyproject-auto-versioning-setup](hatch-vcs-pyproject-auto-versioning-setup.md) — initial hatch-vcs migration
- [pixi-cache-true-unreliable](pixi-cache-true-unreliable.md) — related pixi CI caveat
- [Pixi PyPI options docs](https://pixi.sh/latest/reference/project_configuration/#the-pypi-options-table)
- [hatch-vcs docs](https://github.com/ofek/hatch-vcs)
