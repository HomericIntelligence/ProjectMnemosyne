---
name: architecture-shipping-mojo-package-prefix-dev
description: "End-to-end pattern for making a Mojo library installable via `pixi add <pkg>` from the modular-community channel: idiomatic `src/<package_name>/` layout, `conda.recipe/recipe.yaml` (rattler-build), PR to `modular/modular-community`, and optional Python wheel that bundles the `.mojopkg`. Use when: (1) planning to publish a Mojo library, (2) converting an in-tree `shared/` directory into a distributable package, (3) replacing fictional `mojo install`/`mojo publish` CLI references in docs, (4) deciding between conda channel vs Python wheel vs git dependency for distribution."
category: architecture
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo-packaging, prefix-dev, modular-community, rattler-build, mojopkg, python-wheel, conda]
---

# Shipping a Mojo Package via prefix.dev (modular-community)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | Document the actual, end-to-end pattern for shipping a Mojo library so downstream consumers can `pixi add <pkg>` from the modular-community channel and `from <pkg>.<mod> import <symbol>` in Mojo |
| **Outcome** | Synthesized plan from surveying NuMojo, decimojo, argmojo, mist, and mojolang.org docs (May 2026). Not yet executed end-to-end in any project the author controls. |
| **Verification** | unverified |

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

> **Verification status: UNVERIFIED — treat this as a "Proposed Workflow".** This workflow has not been validated end-to-end. It is synthesized from reading real published Mojo packages (decimojo, argmojo, NuMojo, mist) and the official Modular docs at <https://mojolang.org/docs/tools/packaging/>. ProjectOdyssey is partway through implementing it (PR #5414 in flight; recipe + release workflow + wheel PRs queued). Treat as a hypothesis until at least one project completes the full conda-channel publish end-to-end.

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

# 4. Publish: PR to modular/modular-community
#    Add recipes/<pkg>/recipe.yaml + a test .mojo file
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

#### 5. Publish

Open a PR to <https://github.com/modular/modular-community>. The README's three required steps:

1. Fork `modular/modular-community`
2. Add `recipes/<pkg>/` folder containing `recipe.yaml` + the test `.mojo` file
3. Open the PR

Once merged, prefix.dev's build infrastructure builds and publishes automatically. No further action needed.

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
| ProjectOdyssey | 4-PR plan: rename `shared/` → `src/projectodyssey/` (PR #5414 in flight), then conda.recipe + release workflow + wheel | Plan synthesized from May 2026 survey; end-to-end conda-channel publish not yet completed |

## See Also

- `mojo-build-package` — covers the lower-level `mojo package` CLI mechanics that this skill builds on top of
- `tooling-modular-project-setup-wizard` — covers initial project scaffolding (pixi/uv/channels) for *new* projects, complementary to this skill's *publishing* focus
