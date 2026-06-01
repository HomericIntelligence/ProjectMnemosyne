---
name: pixi-env-resolve-drops-editable-install
description: "Pixi silently re-solves the shared `.pixi/envs/default` and wipes the `pip install -e .` editable install whenever a worktree edit to `pyproject.toml` (especially `[project.scripts]`, `[project.dependencies]`, or `[project.optional-dependencies]`) is followed by a `pixi run` invocation. Long-running automation that imports the package then fails with `ModuleNotFoundError: No module named '<pkg>'` starting at the exact env-resolve timestamp. Use when: (1) `ModuleNotFoundError: No module named 'hephaestus'` (or your package) starts mid-run, (2) every repo started AFTER a specific UTC timestamp fails identically while every repo started BEFORE it succeeded, (3) a swarm/parallel agent run touched `pyproject.toml` in any worktree sharing `.pixi/envs/default`, (4) `stat -c '%Y' .pixi/envs/default/conda-meta` is newer than the last `pixi run dev-install`."
category: tooling
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - editable-install
  - pip-install-e
  - dev-install
  - site-packages
  - env-resolve
  - module-not-found
  - pyproject
  - project-scripts
  - swarm-worktree
  - long-running-driver
  - shared-pixi-env
---

# Pixi Env Re-Solve in a Swarm Worktree Silently Drops the Editable Install

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-31 |
| **Objective** | Document the failure mode where a worktree edit to `pyproject.toml` triggers a `pixi` env re-solve that wipes the `pip install -e .` editable install from `.pixi/envs/default/lib/.../site-packages/`, causing any subsequent process that imports the package to die with `ModuleNotFoundError` |
| **Outcome** | Diagnosed live during a 10-PR myrmidon swarm run: env mtime jumped from session start (23:04Z) to mid-run (23:59Z), and every repo started after that timestamp died on import. `pixi run dev-install` restored. A permanent pixi-native editable fix is documented but NOT yet validated. |
| **Verification** | verified-local — root cause and `pixi run dev-install` recovery confirmed from a live ecosystem-driver log; the permanent fix (`[pypi-dependencies] hephaestus = { path = ".", editable = true }`) is documented as a hypothesis only and conflicts with [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md). |
| **History** | First version. |

## When to Use

- A long-running driver (ecosystem driver, automation loop, `scripts/drive_prs_green.py`, watcher) that worked at startup begins emitting `ModuleNotFoundError: No module named '<your-pkg>'` mid-run.
- Every repo / job that started **after** a specific UTC timestamp fails identically; every repo / job that started **before** it succeeded normally. The cliff is sharp — no gradual degradation.
- A myrmidon / parallel-agent swarm is editing `pyproject.toml` inside one or more worktrees that share `.pixi/envs/default` with the driver's parent checkout.
- `stat -c '%Y %n' .pixi/envs/default/conda-meta` shows a timestamp newer than the last time you ran `pixi run dev-install` (or `pip install -e .`).
- A swarm agent recently added a new `[project.scripts]` entry — even with no functional code change, pixi treats this as a manifest change and re-solves.
- `pixi run python -c "import <pkg>"` fails from the parent worktree even though `python -c "import <pkg>"` from outside `pixi run` may or may not work depending on PATH.
- You see two different repo runs in the same session log: earlier runs report `Successfully installed <Pkg>-X.Y.Z.devN+g<sha>` at startup, later runs report `ModuleNotFoundError` — and there is no explicit "uninstall" anywhere in between.

Do NOT use this skill when:

- The package was never installed editable in the first place (run `pixi run dev-install` once and verify; no env-resolve happened).
- The error is `command not found: <pkg>-<cli>` (console-script stale-entry-points instead of full uninstall — see [`tooling-pyproject-scripts-dev-install-after-merge`](tooling-pyproject-scripts-dev-install-after-merge.md)).
- The lockfile is the symptom, not import failure — see [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md).

## Verified Workflow

### Quick Reference

```bash
# 1. CONFIRM env was re-solved during the run:
stat -c '%Y %n' .pixi/envs/default/conda-meta
# Compare against the timestamp where ModuleNotFoundError began.

# 2. CONFIRM the editable install is now missing:
pixi run python -c "import hephaestus; print(hephaestus.__version__)"
# ModuleNotFoundError: No module named 'hephaestus'

# 3. RESTORE immediately (run from the parent worktree, NOT from a swarm worktree):
pixi run dev-install
pixi run python -c "import hephaestus; print(hephaestus.__version__)"
# 0.9.4.dev14+g3fcc2f0fb   (or similar — the SHA from your current HEAD)

# 4. RESTART any long-running drivers that were holding the dead env state.
```

### Detailed Steps

**Why this happens.** ProjectHephaestus (and any pixi project using the
`Approach A` pattern from [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md))
configures pixi so the package is NOT in `[pypi-dependencies]`. Instead, an
explicit `pixi run dev-install` task runs `pip install -e . --no-deps`, dropping
`<pkg>.egg-link` / `<pkg>.pth` files into `.pixi/envs/default/lib/python3.X/site-packages/`.

This editable install is invisible to pixi's solver. The moment pixi decides it
needs to re-create `.pixi/envs/default` (because `pyproject.toml` was touched in
a way it deems significant), it nukes the env and rebuilds it from
`pixi.lock` — and the editable install is gone, because it was never in the
lockfile.

Concretely, `pixi run` will re-solve when any of these happen in `pyproject.toml`:

- `[project.scripts]` add / remove / rename
- `[project.dependencies]` change
- `[project.optional-dependencies]` change
- `[build-system]` change
- `[tool.hatch.version]` change

Worktrees inherit the parent checkout's `.pixi/envs/default` because the pixi env
directory is determined by the workspace path **as resolved by `pixi`** — when a
worktree's `pixi.toml` points at the same workspace (or is identical), the same
`.pixi/envs/default` is used. One worktree mutating `pyproject.toml` then
invoking `pixi run` re-solves the env that ALL worktrees (and the parent) share.

**Step 1 — Detect the failure cliff in your log.**

```bash
# Grep your driver log for the boundary:
grep -E "ModuleNotFoundError: No module named '<pkg>'|Successfully installed <Pkg>-" driver.log | head
```

You should see a clean before/after split — the last `Successfully installed`
line marks the last good install; every subsequent run that needs to import the
package will fail.

**Step 2 — Confirm pixi re-solved the env.**

```bash
# The conda-meta mtime is the fingerprint of the last env-resolve.
stat -c '%Y %n' .pixi/envs/default/conda-meta
# Convert to UTC if needed:
date -u -d @"$(stat -c '%Y' .pixi/envs/default/conda-meta)"
```

If that timestamp lies between your last successful run and the first
`ModuleNotFoundError`, the env was re-solved mid-session.

**Step 3 — Identify the trigger.**

```bash
# Check every worktree for recent pyproject.toml writes:
for wt in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  echo "=== $wt ==="
  stat -c '%y %n' "$wt/pyproject.toml" 2>/dev/null
done
```

The most-recently-modified `pyproject.toml` is your trigger. Inspect the diff —
if it contains anything in the bullet list above (especially `[project.scripts]`),
you've found the cause.

**Step 4 — Restore the editable install from the parent worktree.**

```bash
# From the parent / main checkout (NOT from a swarm worktree):
pixi run dev-install
```

This re-runs `pip install -e . --no-deps` and re-creates the `.pth` /
`.egg-link` entry in the freshly-solved env. The command is idempotent and
fast.

**Step 5 — Verify with the version-string evidence pattern.**

```bash
pixi run python -c "import hephaestus; print(hephaestus.__version__)"
# Before:  ModuleNotFoundError: No module named 'hephaestus'
# After:   0.9.4.dev14+g3fcc2f0fb
```

The version string for hatch-vcs projects is `<base>.devN+g<sha>` — if the SHA
matches your current `git rev-parse --short HEAD`, the install is current.

**Step 6 — Restart any long-running drivers** that were started before the
re-solve. They almost certainly cached a now-stale `sys.path` or process
environment.

**Step 7 (recommended) — Add a pre-flight check to long-running drivers.**

Make your ecosystem driver assert importability at the top of each repo loop:

```python
import importlib

def _assert_editable_install_present():
    try:
        importlib.import_module("hephaestus")
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "FATAL: hephaestus is not importable. The pixi env was likely "
            "re-solved by a worktree edit. Run `pixi run dev-install` from "
            "the parent worktree and restart the driver."
        ) from exc

# Call this at the top of every loop iteration:
_assert_editable_install_present()
```

This converts a silent mid-run `ModuleNotFoundError` into a loud, single,
actionable message.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Continue the swarm run after the first `ModuleNotFoundError`, assuming it was a flaky import | Every repo started after the env-resolve timestamp failed identically; the loss compounded | A sharp before/after cliff at one timestamp is structural, not flaky — stop and investigate the env state |
| 2 | Re-run `pixi install` alone | `pixi install` reads `pixi.lock` and builds the env, but does NOT run the `dev-install` task; the editable install stays missing | `pixi install` and `pixi run dev-install` are different operations; you need the latter after any env-resolve event |
| 3 | Run `pixi run dev-install` from inside a swarm worktree | The worktree's `pyproject.toml` was the trigger — running install from there can re-trigger another re-solve | Always run `pixi run dev-install` from the parent / clean worktree |
| 4 | Tail-grep `pip install` lines in the log to look for an explicit uninstall | There was no explicit uninstall — pixi's env-resolve wipes the whole `.pixi/envs/default` and rebuilds; uninstall is implicit | The fingerprint is `stat .pixi/envs/default/conda-meta` mtime, not an `Uninstalled` log line. Pixi doesn't announce that it nuked the env |
| 5 | Add `pip install -e .` to a CI / pre-commit hook to "guarantee" it's always installed | Helps for fresh checkouts, but doesn't help long-running drivers that started BEFORE the re-solve; the in-memory process is already dead | The reactive fix is `pixi run dev-install`; the preventive fix is the structural one (Step 7 pre-flight check + the deferred permanent fix below) |
| 6 | Switch immediately to `[pypi-dependencies] hephaestus = { path = ".", editable = true }` as the "obvious" permanent fix | This is exactly the configuration that [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md) Approach A removed because it caused perpetual lockfile churn. Re-adding it without first migrating to pixi lockfile v7 (Approach B) will re-introduce the churn | Permanent fix requires lockfile v7 (Pixi >=0.68.0) in place first — see the Permanent Fix section below |

## Results & Parameters

### Failure-Cliff Detection Pattern

The diagnostic evidence from the live failure (extracted from the user's
ecosystem driver log):

```text
23:04:26Z  ecosystem driver starts; "Successfully installed Pkg-0.9.4.dev14+g3fcc2f0fb"
23:59:47Z  .pixi/envs/default/conda-meta mtime — env re-solved
           (verified via `stat -c '%Y' .pixi/envs/default/conda-meta`)
23:59:48Z  6 repos that begin their work loop fail with
           "ModuleNotFoundError: No module named 'hephaestus'"
```

The two timestamps you correlate are:

1. **Driver-log "Successfully installed"** — last known good editable install.
2. **`stat -c '%Y' .pixi/envs/default/conda-meta`** — last env-resolve.

If (2) > (1) and any process started before (2) tried to import after (2), the
process is now running in a dead env.

### Immediate Recovery (Verified)

```bash
# From the parent worktree, NOT from a swarm worktree:
pixi run dev-install

# Verify:
pixi run python -c "import hephaestus; print(hephaestus.__version__)"
```

Recovery is O(seconds) — pip re-uses cached wheel data and only writes the
`.pth` / `.egg-link`.

### Permanent Fix (Proposed — NOT yet validated)

Switch from `pip install -e . --no-deps` (as a task) to a pixi-native editable
declaration:

```toml
# pixi.toml
[pypi-dependencies]
hephaestus = { path = ".", editable = true }
```

This puts the editable install into `pixi.lock`, so every env-resolve preserves
it. **However**, this conflicts with the historical reason this entry was
removed: [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md)
Approach A removed exactly this entry because it caused perpetual `pixi.lock`
churn when combined with `hatch-vcs` dynamic versioning.

**The combined permanent fix is therefore:**

1. First ensure the project is on **pixi lockfile v7** (Pixi >=0.68.0) — see
   Approach B of [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md).
   Lockfile v7 removes the source-dependency input hashes that caused the
   churn, so the self-reference can safely return.
2. Then re-add the self-reference under `[pypi-dependencies]`.
3. Drop the `[tasks] dev-install = "pip install -e . --no-deps"` line.
4. Verify on a clean tree: `pixi install && git diff --exit-code pixi.lock`
   must exit 0; and `pixi run python -c "import <pkg>"` must succeed without
   any preceding `dev-install`.

Until this combined migration is validated end-to-end, the recommended posture
is: **keep the `dev-install` task AND add the Step 7 pre-flight check**.

### Reproduction Recipe (Worth Running Once)

```bash
# Prereqs: pixi project using `pip install -e .` pattern (NOT pypi-deps self-ref).

# 1. Set up a worktree:
git worktree add /tmp/repro-wt -b repro-branch HEAD

# 2. Confirm editable install works from the parent:
pixi run python -c "import hephaestus; print('ok')"
# ok

# 3. Capture the env mtime:
T0=$(stat -c '%Y' .pixi/envs/default/conda-meta)

# 4. In the worktree, edit pyproject.toml to add a new [project.scripts] entry:
cd /tmp/repro-wt
python -c "
import tomli, tomli_w
p = tomli.load(open('pyproject.toml','rb'))
p.setdefault('project',{}).setdefault('scripts',{})['hephaestus-repro-script'] = 'hephaestus.__init__:__name__'
tomli_w.dump(p, open('pyproject.toml','wb'))
"

# 5. Invoke pixi run from the worktree (this triggers the re-solve):
pixi run python -c "print('hi')"

# 6. Capture the new env mtime:
T1=$(stat -c '%Y' .pixi/envs/default/conda-meta)
echo "Before: $T0 / After: $T1"
# T1 > T0 confirms re-solve.

# 7. From the parent, confirm import now fails:
cd -
pixi run python -c "import hephaestus; print('still works')"
# ModuleNotFoundError: No module named 'hephaestus'

# 8. Restore:
pixi run dev-install
```

### Detection Heuristic

| Signal | Means |
|--------|-------|
| `ModuleNotFoundError: No module named '<pkg>'` mid-run | Editable install lost — start investigating env-resolve |
| Sharp before/after cliff in driver log at ONE timestamp | Structural, not flaky |
| `stat -c '%Y' .pixi/envs/default/conda-meta` > last `dev-install` time | Env was re-solved |
| Any worktree's `pyproject.toml` mtime > last `dev-install` time | Likely trigger |
| `pixi run python -c "import <pkg>"` fails but `python -c "import <pkg>"` from outside pixi works | The site-packages of the pixi env was wiped; the system Python may have its own copy |
| `pixi run pip show <pkg>` returns nothing (`Package(s) not found`) | Editable install is gone — re-run `pixi run dev-install` |

### Why this Bug Is a CLASS, Not a One-Off

Any long-running process that depends on the package being importable will
fail silently mid-run if a swarm worktree touches `pyproject.toml` in any way
pixi considers re-solve-worthy. This includes:

- The ecosystem driver (`scripts/drive_prs_green.py`)
- Automation loops (`scripts/loop_runner.py` / `hephaestus-automation-loop`)
- Long-running myrmidon swarm coordinators
- Local watchers (`watchdog` / `pytest-watch`) inside `pixi run`
- Any `pixi run` task that is itself a long-running daemon

If your project has ANY of the above AND uses the `dev-install` task pattern
AND runs swarm agents in worktrees, you are exposed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-31 — 10-PR myrmidon swarm run | Ecosystem driver started 23:04:26Z with `Successfully installed HomericIntelligence-Hephaestus-0.9.4.dev14+g3fcc2f0fb`. At 23:59:47Z `.pixi/envs/default/conda-meta` mtime jumped (env re-solved). From 23:59:48Z onwards, 6 separate repo runs of `scripts/drive_prs_green.py` failed with `ModuleNotFoundError: No module named 'hephaestus'`. Trigger: one swarm worktree had added a new entry to `[project.scripts]` (`hephaestus-check-skill-catalog`) and then invoked `pixi run pytest`. Recovery via `pixi run dev-install` from the parent worktree restored importability immediately. The pixi-native editable self-reference (`[pypi-dependencies] hephaestus = { path = ".", editable = true }`) is documented as the proposed permanent fix but not yet validated; it must be combined with lockfile v7 migration to avoid re-introducing the churn that PR #675 removed. |

## References

- [`tooling-pixi-lockfile-churn-self-reference`](tooling-pixi-lockfile-churn-self-reference.md) — companion skill; explains why the self-reference was removed and the v7 lockfile migration that would let it return safely
- [`tooling-pyproject-scripts-dev-install-after-merge`](tooling-pyproject-scripts-dev-install-after-merge.md) — related but DIFFERENT failure mode (stale console-script entries after `git pull`, not a full env-resolve wipe)
- [`dependency-consolidation-pixi-single-source`](dependency-consolidation-pixi-single-source.md) — single-source-of-truth pattern that this skill's env-resolve fingerprint relies on
- [Pixi `[pypi-dependencies]` docs](https://pixi.sh/latest/reference/project_configuration/#the-pypi-dependencies-table)
- [pip editable install reference](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs)
