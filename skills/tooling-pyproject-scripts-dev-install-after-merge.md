---
name: tooling-pyproject-scripts-dev-install-after-merge
description: "After git pull/merge that touches [project.scripts] in pyproject.toml, re-run editable install (pixi run dev-install / pip install -e .) — the source tree updates but console-script entry points stay stale until re-install. Use when: (1) command not found after git pull/merge, (2) new hephaestus-* CLI not on PATH after merge, (3) [project.scripts] entry not visible after pull, (4) editable install stale entry points, (5) python -m module works but the registered console-script binary does not."
category: tooling
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - python
  - pyproject
  - console-scripts
  - editable-install
  - pip-install-e
  - dev-install
  - entry-points
  - pixi
  - command-not-found
  - post-merge
---

# Re-run Editable Install After Pulling `[project.scripts]` Changes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | Document why a newly-merged `[project.scripts]` entry yields `command not found` after `git pull`, and the one-line fix |
| **Outcome** | Re-running `pixi run dev-install` (or `pip install -e .`) regenerates `*.dist-info/entry_points.txt` and the new binary stub appears on PATH |
| **Verification** | verified-ci — observed end-to-end live in HomericIntelligence/ProjectHephaestus after squash-merging PR #707 (commit `2407884`) which added `hephaestus-ensure-state-labels` to `[project.scripts]` |

## When to Use

- A `git pull` / merge brought in a `pyproject.toml` diff that added or changed a `[project.scripts]` entry
- A new console script (e.g. `hephaestus-ensure-state-labels`) returns `command not found` after pull, even though the source file is on disk and importable as a module
- A teammate just opened a PR that mentions a new CLI binary by name, you pulled, and it isn't on your PATH
- `python -m <module.path>` works but the console-script wrapper does not — telltale sign of stale entry points
- You're triaging a "where is this binary?" question that started right after a pull
- Onboarding a colleague who pulled the repo but can't run a newly-added CLI tool

Do NOT use when:
- The command was already broken BEFORE the pull (look elsewhere — env, PATH, shell config)
- The source file referenced by `[project.scripts]` doesn't exist (real bug — install won't fix a missing module)
- You haven't actually pulled anything that touched `pyproject.toml`'s `[project.scripts]` section (no entry-point change → no stale-entry-points problem)

## Verified Workflow

### Quick Reference

```bash
# After any git pull/merge that touched pyproject.toml [project.scripts]:

# pixi-based project (ProjectHephaestus convention):
pixi run dev-install

# plain pip project:
pip install -e .

# Verify the new binary is registered:
which hephaestus-ensure-state-labels   # should now print a path
hephaestus-ensure-state-labels --help  # should produce usage text
```

### Detailed Steps

**Why this is needed:** Editable installs register console-script names by writing
`<package>-<version>.dist-info/entry_points.txt` (and corresponding stub binaries in
`<env>/bin/`) at install time. A bare `git pull` only updates the working tree — it does
NOT re-run any install step. So the on-disk source has a new `[project.scripts]` entry,
but the package metadata that PATH consults still advertises the OLD entry-point list.

**Step 1: Detect that you're in this situation.** Telltale signs:

```bash
# Source file exists and is importable:
python -c "from hephaestus.automation import ensure_state_labels; print('ok')"
# ok

# Module-level invocation works:
python -m hephaestus.automation.ensure_state_labels --help
# (prints usage)

# But the registered console-script is nowhere to be found:
which hephaestus-ensure-state-labels
# (empty / not found)
hephaestus-ensure-state-labels --help
# bash: hephaestus-ensure-state-labels: command not found
```

If the first two work but the third fails, you have a stale-entry-points problem, NOT a
build/install/PATH problem.

**Step 2: Verify the diff contained `[project.scripts]`.**

```bash
git log -p --since="1 hour ago" -- pyproject.toml | grep -A2 'project.scripts'
# or:
git diff HEAD~1 -- pyproject.toml
```

If you see a new line like `hephaestus-ensure-state-labels = "hephaestus.automation.ensure_state_labels:main"`,
you confirmed the cause.

**Step 3: Re-run the editable install.**

For pixi-based projects (ProjectHephaestus convention):

```bash
pixi run dev-install
```

For plain pip projects:

```bash
pip install -e .
```

For projects using `--no-deps` to avoid lockfile churn:

```bash
pip install -e . --no-deps
```

The install is idempotent and fast — it re-uses cached wheel data, and the only
meaningful change is `entry_points.txt` regeneration plus binary stub creation.

**Step 4: Verify with the package-version-string evidence pattern.**

```bash
python -c "import hephaestus; print(hephaestus.__version__)"
# Before re-install: 0.9.3.dev39+g4f63a5643 (pre-merge tag)
# After  re-install: 0.9.3.dev46+g240788441 (post-merge tag)
```

The version string is `<base>.devN+g<git-sha>` for hatch-vcs projects — the SHA segment
moves when you re-install, because hatch-vcs re-reads `git describe` at install time.
If the SHA matches your current HEAD, the install picked up the merge.

Then:

```bash
which hephaestus-ensure-state-labels
# /home/.../envs/default/bin/hephaestus-ensure-state-labels  (now exists)
```

**Step 5: Bake it into your post-pull habit.** Any time `pyproject.toml` is in the diff —
especially `[project.scripts]`, `[project.optional-dependencies]`, or `[tool.hatch.build.hooks.vcs]` —
re-run `pixi run dev-install` / `pip install -e .`. Cost: a few seconds. Cost of
debugging "command not found": noticeably more.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `which hephaestus-ensure-state-labels` returns nothing → assume package is uninstalled | Initial diagnosis: "the package isn't installed" | Misleading — every other `hephaestus-*` console script was still on PATH, proving the package WAS installed; only the new entry was missing | `which` not finding ONE binary while other binaries from the same package work is a smoking gun for stale `entry_points.txt`, not for missing install |
| Run `pixi install` (environment-level install) | Heavier reinstall to "make sure everything is fresh" | May help but is overkill — it rebuilds the whole pixi environment when the only thing that needed regeneration was `<dist-info>/entry_points.txt` | Use the targeted `pixi run dev-install` (= `pip install -e . --no-deps`); much faster, fixes the actual issue |
| Modify `PATH` to add a directory where the binary "should" live | Suspected a PATH ordering problem | Wrong layer — the binary stub doesn't exist anywhere on disk yet; no amount of PATH manipulation can find a file that hasn't been created | The fix is to CREATE the stub via install, not to ADJUST PATH |
| Invoke via `python -m hephaestus.automation.ensure_state_labels` | Workaround that doesn't require entry-point registration | Works as a one-off, but defeats the console-script convention; scripts/automation that hard-codes the binary name still breaks | OK as a 30-second workaround; NOT a fix. Re-install to make the registered name available |
| Add the script entry manually to `<env>/bin/hephaestus-ensure-state-labels` | Hand-craft the stub | Possible in theory, error-prone in practice; also rewritten on next install; doesn't update `entry_points.txt` so `pip show` and other introspection still report stale state | Don't fight the package machinery — run the install command it was designed for |
| Restart the shell (`exec bash`) | Suspect shell hash table cache | Doesn't help — the binary genuinely doesn't exist on disk yet. `exec bash` only fixes the case where the file exists but bash has cached its absence | Shell rehash only matters when the file already exists. For stale-entry-points, the file is missing |

## Results & Parameters

### The package-version-string evidence pattern

For hatch-vcs / setuptools-scm projects, the runtime version string encodes the git
state at install time:

```text
0.9.3.dev39+g4f63a5643   ← pre-merge install (39 dev commits past the v0.9.3 tag; SHA 4f63a5643)
0.9.3.dev46+g240788441   ← post-merge install (46 dev commits; SHA 240788441 = the merge commit)
```

Use this as your fastest sanity check:

```bash
# Step A: capture the version BEFORE re-install
OLD=$(python -c "import hephaestus; print(hephaestus.__version__)")

# Step B: re-install
pixi run dev-install

# Step C: capture the version AFTER re-install
NEW=$(python -c "import hephaestus; print(hephaestus.__version__)")

echo "before: $OLD"
echo "after:  $NEW"
# If $NEW differs from $OLD (especially the SHA portion), the install picked up the merge.
# If they're identical, you may not actually be on the merged commit — check `git log -1`.
```

### The diff-trigger heuristic

Run `pixi run dev-install` (or `pip install -e .`) whenever ANY of these appear in a
post-pull `git diff`:

| Diff signal | Why it triggers re-install |
|-------------|----------------------------|
| `[project.scripts]` add/remove/rename | New/removed entry points need stub binaries on PATH |
| `[project.optional-dependencies]` change | Extras-driven imports may now fail/succeed differently |
| `[project.dependencies]` change | Runtime imports may have new/removed deps; needs to install/uninstall packages |
| `[tool.hatch.build.hooks.vcs]` or `version-file` | The generated `_version.py` may have moved |
| Any `pyproject.toml` `[build-system]` change | Build backend or its config changed; safest to re-install |

Quick check: `git diff HEAD~1 pyproject.toml | head -50` after pull — if you see any
of the above, just run `pixi run dev-install` and move on.

### Why this is easy to miss

| Misleading observation | Why it tricks you |
|------------------------|-------------------|
| `import hephaestus.automation.ensure_state_labels` works fine | Python re-reads source files on next import — no install step required for `import` to succeed |
| Pre-existing console scripts (e.g. `hephaestus-merge-prs`) keep working | They were already registered at the last install; their stubs are still on PATH |
| The error `command not found` looks like a build/install bug | It IS an install issue — just a targeted one (stale `entry_points.txt`), not "the package is broken" |
| `pip show hephaestus` reports the package as installed | True — it IS installed; just with the old entry-points list |
| `pip list \| grep hephaestus` shows the editable install | Same — the listing comes from `dist-info/`, which is stale |

### Concrete observation log (HomericIntelligence/ProjectHephaestus, 2026-05-29)

```text
PR #707 squash-merged as commit 2407884; adds:
  [project.scripts]
+ hephaestus-ensure-state-labels = "hephaestus.automation.ensure_state_labels:main"

$ git pull --ff-only origin main
$ hephaestus-ensure-state-labels --org HomericIntelligence
bash: hephaestus-ensure-state-labels: command not found

$ pixi run hephaestus-ensure-state-labels --org HomericIntelligence
hephaestus-ensure-state-labels: command not found

$ python -c "import hephaestus; print(hephaestus.__version__)"
0.9.3.dev39+g4f63a5643      ← pre-merge

$ pixi run dev-install
# (a few seconds; reuses cached wheel data)

$ python -c "import hephaestus; print(hephaestus.__version__)"
0.9.3.dev46+g240788441      ← post-merge

$ which hephaestus-ensure-state-labels
/home/mvillmow/Projects/ProjectHephaestus/.pixi/envs/default/bin/hephaestus-ensure-state-labels

$ hephaestus-ensure-state-labels --org HomericIntelligence
# runs as expected
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-29 — PR #707 (`2407884`) added `hephaestus-ensure-state-labels` to `[project.scripts]` | After `git pull --ff-only`, the new binary was `command not found` despite the source module being importable. `pixi run dev-install` regenerated `entry_points.txt`; version string moved from `0.9.3.dev39+g4f63a5643` (pre-merge tag) to `0.9.3.dev46+g240788441` (post-merge tag, matching the squash-merge SHA); `which` then found the binary; the CLI ran correctly. Both the failure mode AND the fix were demonstrated live in the same session — hence `verified-ci`. |
