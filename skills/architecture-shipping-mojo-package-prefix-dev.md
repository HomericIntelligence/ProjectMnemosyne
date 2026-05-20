---
name: architecture-shipping-mojo-package-prefix-dev
description: "End-to-end pattern for making a Mojo library installable via `pixi add <pkg>` from the modular-community channel: idiomatic `src/<package_name>/` layout, `conda.recipe/recipe.yaml` (rattler-build), PR to `modular/modular-community`, and optional Python wheel that bundles the `.mojopkg`. Use when: (1) planning to publish a Mojo library, (2) converting an in-tree `shared/` directory into a distributable package, (3) replacing fictional `mojo install`/`mojo publish` CLI references in docs, (4) deciding between conda channel vs Python wheel vs git dependency for distribution."
category: architecture
date: 2026-05-19
version: "2.0.0"
user-invocable: false
verification: verified-local
history: architecture-shipping-mojo-package-prefix-dev.history
tags: [mojo-packaging, prefix-dev, modular-community, rattler-build, mojopkg, python-wheel, conda, org-fork, upstream-pr]
---

# Shipping a Mojo Package via prefix.dev (modular-community)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Document the actual, end-to-end pattern for shipping a Mojo library so downstream consumers can `pixi add <pkg>` from the modular-community channel and `from <pkg>.<mod> import <symbol>` in Mojo |
| **Outcome** | Executed end-to-end in ProjectOdyssey (issue #5413): `src/projectodyssey/` layout, `conda.recipe/recipe.yaml`, `.mojopkg` build, install-local, Python wheel, and release-artifact attachment all verified. The modular-community PR (modular/modular-community#274) is open but **not yet merged**, so the channel-install end is still unverified. |
| **Verification** | verified-local — recipe build / install-local / wheel / release artifacts verified locally and in the release run; modular-community channel install pending modular/modular-community#274 merge |
| **History** | [changelog](./architecture-shipping-mojo-package-prefix-dev.history) |

## When to Use

- Planning to publish a new Mojo library so others can install it with `pixi add`
- Converting an in-tree `shared/` (or similar) directory into a distributable package
- Replacing references to the **fictional** `mojo install` / `mojo publish` / `mojo list` / `mojo uninstall` CLI commands in docs or scripts
- Choosing between three distribution channels for a Mojo library:
  - **Conda channel** (modular-community on prefix.dev) — recommended default
  - **Python wheel** (pip-installable) — adds Python interop or loader-only access
  - **Git dependency** (via `pixi-build` preview or `pixi add -g <git-url>`) — fastest iteration, less discoverable

## CRITICAL — Fictional CLI Commands

These commands **do not exist** in Mojo 1.0 (May 2026). Many tutorials and old INSTALL docs reference them — replace before users try them:

| Old (fictional) | Real (Mojo 1.0, May 2026) |
|-----------------|---------------------------|
| `mojo package ... --install` | `pixi add <pkg>` from modular-community channel |
| `mojo install <file.mojopkg>` | Drop the `.mojopkg` next to `main.mojo`, OR pass `-I /path/to/dir` containing it |
| `mojo publish` | Open a PR to `modular/modular-community` adding `recipes/<pkg>/recipe.yaml` |
| `mojo list` | `pixi list` |
| `mojo uninstall <pkg>` | `pixi remove <pkg>` |

## Verified Workflow

> **Verification status: VERIFIED-LOCAL.** ProjectOdyssey (issue #5413) executed this workflow
> end-to-end: the `src/projectodyssey/` layout, `conda.recipe/recipe.yaml`, local `.mojopkg`
> build, install-local, the Python wheel, and the release-artifact attachment are all verified
> locally / in the release run. The **one remaining unverified step** is the modular-community
> *channel install*: modular/modular-community#274 is open but not yet merged, so consumers
> cannot yet `pixi add projectodyssey` from the channel. Treat steps 1–4 and 7 as verified;
> treat step 5 (publish) as verified-up-to-PR-open and the consumer experience (step 6) as
> pending the upstream merge.

### Quick Reference

```bash
# 1. Idiomatic layout
mkdir -p src/<package_name>
mv old/dir/* src/<package_name>/
# ensure src/<package_name>/__init__.mojo exists

# 2. Build the .mojopkg locally
mojo package -I src src/<package_name> -o <package_name>.mojopkg

# 3. Test the recipe locally (no network publish)
pixi exec --spec rattler-build -- rattler-build build \
  --recipe conda.recipe/recipe.yaml \
  -c conda-forge \
  -c https://conda.modular.com/max \
  -c https://repo.prefix.dev/modular-community

# 4. Publish via an ORG FORK (you have no push access to modular/modular-community)
gh repo fork modular/modular-community --org <ORG> --clone=false   # one-time
gh repo clone <ORG>/modular-community /tmp/mc                       # auto-adds `upstream`
cd /tmp/mc && git fetch upstream && git checkout main && git reset --hard upstream/main
git checkout -b add-<pkg>-recipe   # add recipes/<pkg>/, commit
git push -u origin add-<pkg>-recipe
gh pr create --repo modular/modular-community --head <ORG>:add-<pkg>-recipe --title "Add <pkg> recipe"
#    prefix.dev builds & publishes automatically on merge
```

### Detailed Steps

#### 1. Layout (Modular's official recommendation)

```text
<repo>/
├── src/
│   └── <package_name>/         # NOT a generic name like "shared/" — prefix.dev names are global
│       ├── __init__.mojo
│       └── ...
├── conda.recipe/
│   └── recipe.yaml             # rattler-build format
├── mojo.toml                   # [package] name = "<package_name>"; [packages] <package_name> = "src/<package_name>"
├── pixi.toml                   # workspace + tasks; channels include https://repo.prefix.dev/modular-community
└── tests/
    └── <package_name>/
```

**Reference layouts surveyed (May 2026):**

- decimojo (canonical): `src/decimo/` + `conda.recipe/recipe.yaml` + wheel — <https://github.com/forfudan/decimojo>
- argmojo: `src/argmojo/` + recipe + GitHub-releases `.mojopkg` fallback — <https://github.com/forfudan/argmojo>
- NuMojo (older, non-canonical): flat `numojo/` (no `src/`) — works fine but doesn't follow current guidance — <https://github.com/Mojo-Numerics-and-Algorithms-group/NuMojo>
- mist: uses `pixi add -g <git-url>` + the `pixi-build` preview feature instead of conda channel — <https://github.com/thatstoasty/mist>
- Modular community recipes repo: <https://github.com/modular/modular-community>

#### 2. Build the `.mojopkg`

```bash
mojo package -I src src/<package_name> -o <package_name>.mojopkg
```

In a rattler-build recipe, write the artifact to `$PREFIX/lib/mojo/<package_name>.mojopkg`. The Mojo compiler auto-discovers `.mojopkg` files in `$CONDA_PREFIX/lib/mojo/` when the conda env is activated, so no `-I` flag is needed by consumers.

#### 3. Write `conda.recipe/recipe.yaml`

Use decimojo's recipe as a reference. The `tests:` section must run a one-liner Mojo file that does `from <package_name>.<module> import <symbol>` and `fn main(): pass` — this proves the `.mojopkg` is importable from a fresh env.

**Note on import tests:** Only *positive* import tests work in Mojo. Import failures are compile-time errors that cannot be caught at runtime, so there is no negative-import-test equivalent of `pytest.raises(ImportError)`.

#### 4. Test the recipe locally

```bash
pixi exec --spec rattler-build -- rattler-build build \
  --recipe conda.recipe/recipe.yaml \
  -c conda-forge \
  -c https://conda.modular.com/max \
  -c https://repo.prefix.dev/modular-community
```

#### 5. Publish — via an org fork (NOT a direct push)

You almost certainly do **not** have push access to `modular/modular-community`. Publishing is an
**upstream-fork contribution workflow**. A script (or human) must fork the repo into the publishing
org once, then always push branches to the *fork* and open PRs against *upstream*.

```bash
# 5a. ONE-TIME: fork modular/modular-community into your org
gh repo fork modular/modular-community --org <ORG> --clone=false

# 5b. Clone the FORK as `origin`. `gh repo clone` of a fork AUTO-ADDS `upstream`.
gh repo clone <ORG>/modular-community /tmp/mc
cd /tmp/mc
# DO NOT run `git remote add upstream ...` — it already exists; double-adding errors (exit 3).
git remote -v   # origin = your fork, upstream = modular/modular-community

# 5c. Hard-sync the fork's main to upstream BEFORE branching (forks drift)
git fetch upstream
git checkout main
git reset --hard upstream/main
git push origin main

# 5d. Branch, add recipes/<pkg>/, push to the FORK
git checkout -b add-<pkg>-recipe
mkdir -p recipes/<pkg>
cp /path/to/recipe.yaml recipes/<pkg>/recipe.yaml
cp /path/to/smoke.mojo  recipes/<pkg>/smoke.mojo
git add recipes/<pkg>
git commit -m "Add <pkg> recipe"
git push -u origin add-<pkg>-recipe

# 5e. Open the PR against UPSTREAM with a cross-fork head ref
gh pr create --repo modular/modular-community \
  --head <ORG>:add-<pkg>-recipe \
  --title "Add <pkg> recipe" \
  --body "Adds recipes/<pkg>/ ..."
```

Once merged, prefix.dev's build infrastructure builds and publishes automatically. No further action
needed.

**`--dry-run` trap:** if a publish script has a `--dry-run` mode that skips the `git push`, dry-run
will report success even when the script is mis-wired to push directly to `modular/modular-community`
(which has no push access). Always do at least one **real** (non-dry-run) execution against the fork
before trusting the script.

#### 6. Consumer experience

```toml
# consumer's pixi.toml
[workspace]
channels = [
  "conda-forge",
  "https://conda.modular.com/max",
  "https://repo.prefix.dev/modular-community",
]

[dependencies]
<package_name> = "*"
```

```mojo
# consumer's main.mojo
from <package_name>.tensor import Tensor
fn main(): print("ok")
```

#### 7. Optional: Python wheel (for `pip install`)

decimojo demonstrates a working pattern. Two flavors:

**Flavor A — Loader-only wheel (recommended starting point):**

- No Python bindings; bundle the `.mojopkg` as package data under `python/<pkg>/_data/`
- Expose a `mojopkg_path()` helper that returns the bundled path
- Consumers `pip install <pkg>` then feed the returned path to `mojo run -I <path>`
- Pure-Python wheel — trivially maintainable, no platform-specific build matrix

**Flavor B — Native bindings wheel:**

- `mojo build --emit shared-lib` produces a `.so`
- Use `@export def PyInit_<pkg>(): m = PythonModuleBuilder(...)` to expose Mojo functions as Python callables
- **Caveat:** most Mojo stdlib types (Tensor, List, custom structs) are not yet `ConvertibleFromPython` (as of May 2026). Each exported symbol needs manual `PythonObject` plumbing. decimojo does this for its decimal types — works for scalars and strings, painful for everything else.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Believing `mojo install` / `mojo publish` exist | ProjectOdyssey's pre-May-2026 `shared/INSTALL.md` told users to run `mojo install <pkg>.mojopkg` and `mojo publish` | These commands do not exist in Mojo 1.0. They appear in older tutorials and AI-generated docs but have no implementation. Users hit "command not found" or silent no-ops. | Always verify CLI commands against `mojo --help` (Mojo 1.0, May 2026). The real distribution path is conda/prefix.dev via rattler-build — there is no first-party `mojo` publish UX. |
| Shipping a flat `shared/` directory as the package root | Tried `mojo package shared/ -o shared.mojopkg` and proposing `shared` as the package name | (a) Non-idiomatic — Modular's docs and every major package (decimojo, argmojo) use `src/<package_name>/`. (b) `shared` is a generic name that would collide on prefix.dev's global namespace. (c) Imports become `from shared.x import y` which is ambiguous across projects. | Always use `src/<unique_package_name>/`. The directory name IS the import name AND the prefix.dev package name — they must all match and must be unique globally. |
| Full Python native-bindings wheel as first attempt | Tried `mojo build --emit shared-lib` with `@export def PyInit_<pkg>` exposing tensor and layer types | Most Mojo stdlib types (Tensor, List, struct types) are not `ConvertibleFromPython` in Mojo 1.0 (May 2026). Bindings work for scalars (`Int`, `Float64`, `String`) but fail to compile or silently lose data for Tensor/List/custom structs without manual `PythonObject` packing/unpacking on every call site. | Start with the loader-only wheel pattern: bundle the `.mojopkg` as package data and expose `mojopkg_path()`. Add native bindings incrementally, per-symbol, only after confirming `ConvertibleFromPython` is implemented for every parameter and return type involved. |
| Publish script pushed directly to `modular/modular-community` | `scripts/publish_modular_community.py` cloned `modular/modular-community` and ran `git push -u origin <branch>` against it | No push access to Modular's repo — `git push` is rejected (403 / permission denied). Publishing to an upstream you do not own is always a fork-and-PR workflow. | Fork `modular/modular-community` into the publishing org (`gh repo fork --org <ORG>`), clone the FORK as `origin`, push the branch to the fork, and `gh pr create --repo modular/modular-community --head <ORG>:<branch>`. |
| `git remote add upstream` after `gh repo clone` of a fork | The script ran `git remote add upstream https://github.com/modular/modular-community` to set up the upstream remote | `gh repo clone` of a *fork* already adds an `upstream` remote automatically; adding it again fails with `fatal: remote upstream already exists` (exit 3) and aborts the script | After `gh repo clone <ORG>/<fork>`, the `upstream` remote already exists — do NOT add it. Just `git fetch upstream`. Only add `upstream` manually if you cloned with plain `git clone`. |
| `--dry-run` masked the broken push | The publish script was exercised only with `--dry-run`, which reported success | Dry-run skips the actual `git push`, so it never exercised the (broken) direct-push-to-upstream code path. The push-access failure only appeared on the first real run. | A `--dry-run` that skips the push gives false confidence. Do at least one real (non-dry-run) execution against the fork before trusting a publish script. |

## Results & Parameters

### Reference recipe.yaml skeleton (rattler-build format)

```yaml
# conda.recipe/recipe.yaml
context:
  name: <package_name>
  version: "0.1.0"

package:
  name: ${{ name }}
  version: ${{ version }}

source:
  path: ..

build:
  number: 0
  noarch: generic
  script:
    - mkdir -p $PREFIX/lib/mojo
    - mojo package -I src src/${{ name }} -o $PREFIX/lib/mojo/${{ name }}.mojopkg

requirements:
  build:
    - max  # provides the mojo compiler
  run:
    - max

tests:
  - script:
      - mojo run tests/smoke.mojo
    files:
      source:
        - tests/smoke.mojo

about:
  homepage: https://github.com/<org>/<repo>
  summary: Short description
  license: Apache-2.0
```

### Reference smoke test (tests/smoke.mojo)

```mojo
from <package_name>.<some_module> import <some_symbol>

fn main():
    print("import ok")
```

### Channels needed by consumers

```toml
channels = [
  "conda-forge",
  "https://conda.modular.com/max",
  "https://repo.prefix.dev/modular-community",
]
```

### Real-world references checked May 2026

| Project | Layout | Distribution | URL |
|---------|--------|--------------|-----|
| NuMojo | flat `numojo/` | git / pixi, no modular-community publish | <https://github.com/Mojo-Numerics-and-Algorithms-group/NuMojo> |
| decimojo | `src/decimo/` | conda channel + wheel + recipe | <https://github.com/forfudan/decimojo> |
| argmojo | `src/argmojo/` | recipe + GitHub Releases `.mojopkg` fallback | <https://github.com/forfudan/argmojo> |
| mist | varies | `pixi add -g <git-url>` + `pixi-build` preview | <https://github.com/thatstoasty/mist> |
| modular-community | (registry) | recipe PRs | <https://github.com/modular/modular-community> |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 4-PR implementation merged: rename `shared/` → `src/projectodyssey/` (#5414), conda recipe (#5415), Python wheel (#5416), release.yml (#5417) | Implementation landed; verification done separately under issue #5413 |
| ProjectOdyssey | Issue #5413 end-to-end verification — recipe build, install-local, wheel, release artifacts all run successfully | 12 follow-up fix PRs (#5419–#5433); release pipeline reached `create-release` for the first time |
| ProjectOdyssey | modular-community publish via org fork | `gh repo fork` into HomericIntelligence; modular/modular-community#274 opened (not yet merged — channel install unverified) |

## See Also

- `mojo-build-package` — covers the lower-level `mojo package` CLI mechanics that this skill builds on top of
- `tooling-modular-project-setup-wizard` — covers initial project scaffolding (pixi/uv/channels) for *new* projects, complementary to this skill's *publishing* focus
