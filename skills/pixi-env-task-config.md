---
name: pixi-env-task-config
description: "Use when: (1) setting up a new Mojo/MAX/Python project with pixi.toml and choosing between nightly/stable channels, (2) wrapping pixi tasks with a justfile for cross-repo convention alignment, (3) eliminating DRY violations by using pixi feature composition (environments = {features = [shared, dev]}) to share dev tools across environments, (4) adding justfile delegation recipes to a meta-repo, (5) auditing pixi task definitions for consistency with CI workflows, (6) a pixi [tasks] entry whose command body is itself `pixi run ...` (nested/recursive pixi invocation smell) — relocate it into the target environment's [feature.<env>.tasks] with a depends-on alias."
category: tooling
date: 2026-06-22
version: "1.2.0"
user-invocable: false
history: pixi-env-task-config.history
tags:
  - pixi
  - justfile
  - mojo
  - max
  - project-setup
  - feature-composition
  - deduplication
  - dry-principle
  - ecosystem
  - convention
  - meta-repo
  - solve-groups
  - depends-on
  - recursive-invocation
---

# Pixi Environment and Task Configuration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Author pixi.toml for Mojo/MAX/Python projects, wrap pixi tasks with a justfile for ecosystem convention alignment, and de-duplicate dev tools via pixi feature composition |
| **Outcome** | Single source covering project scaffolding (pixi/uv/pip/conda), justfile wrapping/delegation, and feature-composition DRY elimination |
| **Verification** | verified-ci |

## When to Use

- Creating a new Mojo, MAX, or Python project from scratch with pixi.toml
- Choosing between environment managers (pixi recommended, uv, pip, conda) and nightly vs stable channels
- A project has `pixi.toml` tasks but no `justfile` (Python library or CI-heavy repo)
- Cross-repo orchestrators (e.g., Odysseus) need to invoke submodule tasks via `just <project>-<task>`
- Six or more conda/PyPI dev tools appear in multiple `[feature.*]` blocks (DRY violation)
- Version floors need to be synchronized across environments (e.g., yamllint matching `.pre-commit-config.yaml`)
- README.md/CLAUDE.md document individual `pixi run` commands instead of `just` recipes
- Auditing pixi task definitions for consistency with CI workflows
- A `[tasks]` entry in `pixi.toml` has a command body that is itself `pixi run --environment <env> <name>` (a nested/recursive pixi invocation) — relocate it into `[feature.<env>.tasks]` with a `depends-on` alias instead
- Before moving or deleting any pixi task, to confirm no real consumer (CI workflows, justfile, docs, code) invokes the bare top-level task name

## Verified Workflow

### Quick Reference

```bash
# --- Project setup (pixi recommended) ---
pixi init <project-name> \
  -c https://conda.modular.com/max-nightly/ -c conda-forge && cd <project-name>
pixi add [max / mojo]
pixi shell

# --- Justfile wrapping pixi tasks ---
# Add `just = ">=1.25.0,<2"` under [feature.dev.dependencies] (optional)
# Create justfile where each recipe delegates to `pixi run <task>`
just --list

# --- Feature composition de-duplication ---
# Create [feature.shared] with common tools, compose via features = ["shared", "dev"]
pixi install --locked
pixi run pytest tests/unit/test_pixi_shared_feature.py -v
```

### Detailed Steps

#### 1. pixi.toml project setup

Infer options from the user's request, then prompt only for what's unspecified:

1. **Project name**
2. **Type** — Mojo or MAX
3. **Environment manager** — Pixi (recommended), uv, pip, or conda
4. **Channel** — nightly (latest) or stable (production)

**Note**: `magic` is no longer supported — Pixi has fully replaced it.

System prerequisites (gcc required for native builds):

| OS | Command |
| --------------- | ---------------------------------------------------------- |
| Ubuntu/Debian | `sudo apt install gcc` |
| Fedora/RHEL | `sudo dnf install gcc` |
| macOS | `xcode-select --install` |
| Windows | WSL2 required (`wsl --install`), then gcc in WSL |

Pixi (recommended):

```bash
# Nightly
pixi init <project-name> \
  -c https://conda.modular.com/max-nightly/ -c conda-forge \
  && cd <project-name>
pixi add [max / mojo]
pixi shell

# Stable
pixi init <project-name> \
  -c https://conda.modular.com/max/ -c conda-forge \
  && cd <project-name>
pixi add "[max / mojo]==0.26.1.0.0.0"
pixi shell

# Python-using projects
pixi add python
pixi add requests           # conda-forge packages
pixi add --pypi some-pkg    # PyPI-only packages
```

uv:

```bash
# Nightly (project)
uv init <project-name> && cd <project-name>
uv add [max / mojo] --index https://whl.modular.com/nightly/simple/ --prerelease allow

# Stable (project)
uv init <project-name> && cd <project-name>
uv add [max / mojo] --extra-index-url https://modular.gateway.scarf.sh/simple/

# Nightly (quick environment)
mkdir <project-name> && cd <project-name>
uv venv
uv pip install [max / mojo] --index https://whl.modular.com/nightly/simple/ --prerelease allow
```

pip / conda:

```bash
# pip nightly
python3 -m venv .venv && source .venv/bin/activate
pip install --pre [max / mojo] --index https://whl.modular.com/nightly/simple/

# conda nightly
conda install -c conda-forge -c https://conda.modular.com/max-nightly/ [max / mojo]
```

Version alignment — MAX and Mojo versions must match when using custom Mojo kernels:

```bash
uv pip show mojo | grep Version   # e.g., 0.26.2
pixi run mojo --version           # Must match major.minor
```

Mismatched versions cause kernel compilation failures. Use the same channel for both.

#### 2. Justfile wrapping pixi tasks

1. **Decide if `just` needs to be a pixi dependency.** If `just` is installed system-wide, skip. Where `just` is the only discovery mechanism, add it under `[feature.dev.dependencies]`.

2. **Create `justfile`** at project root with these conventions:
   - `default` recipe: `@just --list` (ecosystem standard)
   - Each recipe delegates to `pixi run <task>` (single source of truth stays in pixi.toml)
   - Add a comment above each recipe describing what it does
   - **Never use heredocs** in justfile recipes (known `just` pitfall — use `printf` instead)
   - For tasks without a pixi equivalent (e.g., `typecheck`), call the tool directly via `pixi run mypy ...`
   - Use `*ARGS` forwarding for recipes where users commonly pass extra flags (test)
   - Use configurable variables at top of file (`src_dirs`, `test_dir`) to avoid path duplication
   - Include a `bootstrap` recipe for one-command setup and a `check` composite recipe for full CI

**Template A: Python Library Repo (e.g., Hephaestus)**

```just
# ProjectName justfile
# One-command developer experience for the HomericIntelligence ecosystem

# Configurable paths
src_dirs := "<package> scripts tests"
test_dir := "tests/unit"

# List available recipes
default:
    @just --list

# === Setup ===

# Install dependencies and configure pre-commit hooks
bootstrap:
    pixi install
    pixi run pre-commit install

# === Test ===

# Run unit tests (pass extra args: just test -v, just test -k test_slugify)
test *ARGS:
    pixi run pytest {{ test_dir }} {{ ARGS }}

# === Code Quality ===

# Check code with ruff linter
lint:
    pixi run ruff check {{ src_dirs }}

# Format code with ruff formatter
format:
    pixi run ruff format {{ src_dirs }}

# Run mypy type checking
typecheck:
    pixi run mypy <package>/

# Run pre-commit hooks on all files
pre-commit:
    pixi run pre-commit run --all-files

# === Security ===

# Run pip-audit dependency audit
audit:
    pixi run --environment lint pip-audit

# === CI ===

# Run lint, typecheck, and tests (full CI check)
check:
    just lint
    just typecheck
    just test
```

Key decisions for library repos: configurable variables at top avoid path duplication; `bootstrap` combines install + pre-commit setup; `test *ARGS` forwards to pytest; `typecheck` calls `pixi run mypy` directly (no pixi task); `check` is a composite "is everything green?" recipe.

**Bootstrap-in-worktree caveat**: `pixi run pre-commit install` (inside `bootstrap`) refuses to install hooks when git `core.hooksPath` is set — common in worktrees with a custom hook path. This is a git-config issue, not a justfile issue. Workaround: install hooks from the main checkout, or unset / repoint `core.hooksPath` first.

**Template B: CI-Heavy Repo (e.g., Scylla)** — adds CI container recipes:

```just
# Project task runner — delegates to pixi run
default:
    @just --list

test:
    pixi run test

lint:
    pixi run lint

format:
    pixi run format

typecheck:
    pixi run mypy scylla scripts tests

pre-commit:
    pixi run pre-commit run --all-files

ci-build:
    pixi run ci-build

ci-lint:
    pixi run ci-lint

ci-test:
    pixi run ci-test

ci-all:
    pixi run ci-all

audit:
    pixi run audit

test-shell:
    pixi run test-shell
```

**Template C: Meta-Repo Delegation (e.g., Odysseus)** — add `just <prefix>-<recipe>` entries that delegate to submodule justfiles.

**Pre-condition**: The submodule must already have a justfile with the recipes being delegated. Create and merge submodule PRs **first**, then add delegation recipes.

```just
# === AchaeanFleet (infrastructure/AchaeanFleet) ===

# Build AchaeanFleet container images
fleet-build:
    cd infrastructure/AchaeanFleet && just build

# Run AchaeanFleet tests
fleet-test:
    cd infrastructure/AchaeanFleet && just test

# === ProjectMnemosyne (shared/ProjectMnemosyne) ===

# Validate Mnemosyne skill files
mnemosyne-validate:
    cd shared/ProjectMnemosyne && just validate

# Run Mnemosyne tests
mnemosyne-test:
    cd shared/ProjectMnemosyne && just test
```

Conventions for meta-repo delegation:
- **Naming**: `<prefix>-<recipe>` where prefix matches the repo's role (e.g., `fleet`, `proteus`, `mnemosyne`, `hephaestus`)
- **Section headers**: `# === Component Name (RepoName) ===` to group recipes
- **Delegation pattern**: `cd <submodule-path> && just <recipe>` — never invoke pixi/tools directly; each submodule's justfile is the interface
- **Submodule-first ordering**: submodule recipes must exist before Odysseus delegates; otherwise the call fails

For multi-submodule delegation, use a **2-wave myrmidon swarm**: Wave 1 (parallel) creates/verifies submodule justfile PRs, Wave 2 (sequential, single agent) updates submodule pins + adds Odysseus delegation recipes after Wave 1 merges. Never put Wave 1 and Wave 2 in the same agent or PR.

3. **(Optional) BATS sync test** at `tests/shell/justfile/test_justfile.bats`: verify justfile exists, `just --list` succeeds, expected recipes present, no heredocs (`grep -cE '<<\s*[A-Z_]'`), and a sync check that parses `[tasks]` from pixi.toml and verifies each has a matching just recipe.

4. **Update documentation** — replace individual `pixi run` commands in README.md/CLAUDE.md with `just` recipes; add `justfile` to directory structure listings.

#### 3. Feature-composition dedup

When the same dev tools are declared in multiple `[feature.*]` blocks, use feature composition to merge them.

1. **Audit existing duplications**:
   ```bash
   grep -n "ruff\|mypy\|pre-commit\|types-pyyaml\|yamllint\|pip-audit" pixi.toml
   ```

2. **Extract common tools to `[feature.shared]`** — tools appearing in 2+ other features. Set version floors carefully: yamllint must match `.pre-commit-config.yaml` hook version exactly; others use `>=` floor of oldest supported version.

3. **Remove duplicates from other features** — keep only feature-specific tools.

4. **Compose environments using feature lists**, each with its own `solve-group` for independent resolution:
   ```toml
   [environments.default]
   features = ["shared", "dev"]
   solve-group = "default"

   [environments.lint]
   features = ["shared", "lint"]
   solve-group = "lint"
   ```

5. **Create a regression test** (`tests/unit/test_pixi_shared_feature.py`) to guard the de-duplication contract.

6. **Verify resolution** — confirm shared tools resolve identically across environments:
   ```bash
   pixi install --locked
   VERSION_DEFAULT=$(pixi run -e default python -c "import ruff; print(ruff.__version__)")
   VERSION_LINT=$(pixi run -e lint python -c "import ruff; print(ruff.__version__)")
   test "$VERSION_DEFAULT" = "$VERSION_LINT" && echo "All versions match"
   ```

### Observed: the nested `pixi run` task smell (verified-local)

These facts were directly observed while planning ProjectHephaestus issue #1554
(reading `pixi.toml`, running `pixi run audit --help`, and grepping for consumers).
They are not theory — they were checked on disk.

**SYMPTOM.** A `[tasks]` entry whose command body is *itself* a `pixi run`:

```toml
[tasks]
audit = "pixi run --environment lint pip-audit"
```

Running this task spawns a **nested pixi process**: the outer `pixi run audit`
shells out, and the command body launches a *second* `pixi run` that re-resolves
an environment and a task/binary. It is wasteful indirection and reads as
confusing — a task pretending to be an alias.

**ROOT-CAUSE INSIGHT — resolution order.** `pixi run <name>` resolves `<name>`
against **TASKS first, then binaries**. So `pixi run --environment lint pip-audit`
resolves to the lint-env **task** named `pip-audit` *if one exists*, NOT the bare
binary — this is easy to misread when auditing. (Confirmed by running
`pixi run audit --help` and watching the nested resolution.)

**CONSUMER AUDIT — before touching the task.** Distinguish "the task exists" from
"anyone invokes it." Grep the whole repo for real consumers of the **bare** task
name before relocating or deleting it:

```bash
# Look for `pixi run audit` (the top-level alias) across CI, justfile, docs, code.
grep -rni 'pixi run audit' .github/ justfile *.md *.py \
  --exclude-dir=.pixi --exclude-dir=build
```

In #1554 this came back empty for the *top-level* `audit` task: CI
(`_required.yml`) and the `justfile` both called
`pixi run --environment lint pip-audit` **directly** (the binary path, not the
top-level alias), so the top-level `audit` task had **ZERO real consumers** and
was safe to relocate. Exclude `.pixi/` (vendored env) and `build/` worktrees of
*other* repos — both produced false-positive hits here.

### Proposed Workflow: relocate the nested task with a `depends-on` alias

> ⚠️ **PROPOSED, not executed/CI-confirmed.** This fix was authored in an
> implementation plan for ProjectHephaestus issue #1554 but had **not** been run
> or merged at capture time. Treat the relocation as a recommended pattern, not a
> CI-verified procedure. The SYMPTOM, resolution-order, and consumer-grep facts
> above ARE verified-local.

Define the task **inside the target environment's** `[feature.<env>.tasks]`
table and expose a top-level alias via `depends-on` — no nested `pixi run`:

```toml
# BEFORE (nested pixi run — the smell)
[tasks]
audit = "pixi run --environment lint pip-audit"

# AFTER (native resolution in the lint env, plus a depends-on alias)
[feature.lint.tasks]
pip-audit = "pip-audit"          # the real binary, native to the lint env
audit = { depends-on = ["pip-audit"] }
```

The `audit` task now resolves natively in the `lint` environment and runs
`pip-audit` with **no nested pixi process**.

**Machine-checkable verification (no pixi needed)** — parse `pixi.toml` with
`tomllib` and assert the new body contains no `'pixi run'` substring and that the
old top-level task is gone:

```bash
python3 -c "import tomllib;d=tomllib.load(open('pixi.toml','rb'));t=d['feature']['lint']['tasks']['audit'];assert 'pixi run' not in str(t);assert 'audit' not in d.get('tasks',{})"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `magic` for project setup | `magic init` / `magic add` | `magic` is deprecated; Pixi replaced it | Always use `pixi` — do not look for or use `magic` |
| Heredocs in justfile recipes | Multi-line heredoc inside a `just` recipe | `just` mishandles heredocs | Use `printf` instead of heredocs in justfile recipes |
| `bootstrap` in a git worktree | `pixi run pre-commit install` (via `just bootstrap`) inside a worktree with git `core.hooksPath` set | pre-commit refuses to install hooks when `core.hooksPath` is set; it's a git-config issue, not a justfile issue | Install hooks from the main checkout, or unset / repoint `core.hooksPath` first — `bootstrap` works fine in normal clones |
| YAML anchors for tool sharing | `&common_tools` aliases to share tool blocks | pixi.toml is TOML, not YAML — no anchor/alias syntax | Feature composition is the correct pixi idiom, not YAML tricks |
| Manual sync of versions across blocks | Kept six tools in both `[feature.dev]` and `[feature.lint]`, hand-syncing versions | Error-prone; versions drifted within weeks | Use feature composition to centralize the source of truth — DRY eliminates sync burden |
| Single `[feature.all]` instead of `[feature.shared]` | Named the shared feature `[feature.all]` | Reviewers read "all tools" as all dev tools, not shared tools | Name shared features explicitly: `[feature.shared]`/`[feature.common]` |
| NATS-based containerized pipeline for meta-repo delegation | claude-myrmidon-multi.py with 18 NATS consumers, fan-out/fan-in coordination | Massively overengineered for what is fundamentally "edit justfiles in N repos" | Use a simple myrmidon swarm with worktrees for file-edit-and-PR work |
| All agents modify Odysseus justfile in the same wave | Submodule + Odysseus agents ran in parallel | Concurrent writes to the same file caused conflicts; delegation referenced recipes not yet merged | Serialize writes to shared files; submodule PRs merge first (Wave 1), Odysseus delegation second (Wave 2) |
| pixi `[tasks]` entry that shells out to `pixi run` | `audit = "pixi run --environment lint pip-audit"` in `[tasks]` | Spawns a nested pixi process (task → `pixi run` → re-resolve env+task); wasteful indirection. `pixi run <name>` resolves TASKS-first then binaries, so it's easy to misread which thing runs | Define the task in `[feature.<env>.tasks]` and use `audit = { depends-on = ["pip-audit"] }` — native resolution, no nested process |
| Deleting/moving a task because "it exists" without a consumer grep | Assumed the top-level `audit` task was load-bearing | "The task exists" ≠ "anyone invokes it" — CI and justfile actually called `pixi run --environment lint pip-audit` directly, so the top-level alias had zero real consumers | Grep `.github/ justfile *.md *.py` for the **bare** task name first (exclude `.pixi/` and `build/` worktrees → false positives); relocate freely only when the grep is empty |
| Trusting an issue-body file path | Issue said "MIGRATION.md not linked from README" implying a root file | The file actually lived at `docs/MIGRATION.md`; issue-body paths are frequently approximate | `grep -rni "migration.md"` to find the real path before writing the link |
| Assuming a documented-gap is uniformly absent | Audit item "document macOS/Windows CI absence" was already DONE in `.github/workflows/test.yml` but missing in the sibling gate `_required.yml` | A doc/gap can be present in one of two authoritative files and absent in the other | Read BOTH sibling files before planning the change; don't assume a gap is uniform across mirrored configs |

## Results & Parameters

### Channel URLs

| Channel | Conda URL | PyPI Index |
| --------- | ----------- | ------------ |
| Nightly | `https://conda.modular.com/max-nightly/` | `https://whl.modular.com/nightly/simple/` |
| Stable | `https://conda.modular.com/max/` | `https://modular.gateway.scarf.sh/simple/` |

Note: mojo version strings use a `0.` prefix (e.g., `0.26.1.0.0.0`); max does not (e.g., `26.1.0.0.0`).

### Pixi.toml feature composition (exact format)

```toml
[feature.shared]
dependencies = [
  "ruff>=0.1.0",
  "mypy>=1.8.0",
  "pre-commit>=3.0",
  "types-pyyaml>=6.0.12",
  "yamllint>=1.38.0",
]
pypi-dependencies = [
  "pip-audit>=2.7",
]

[feature.dev]
dependencies = []
pypi-dependencies = [
  "pytest>=8.0",
  "pytest-cov>=6.0",
]

[feature.lint]
dependencies = []
pypi-dependencies = [
  "safety>=3.0",
]

[environments.default]
features = ["shared", "dev"]
solve-group = "default"

[environments.lint]
features = ["shared", "lint"]
solve-group = "lint"
```

### Shared tools with version floors

| Tool | Conda Version | PyPI Version | Rationale |
|------|---------------|--------------|-----------|
| ruff | `>=0.1.0` | — | Code formatter and linter |
| mypy | `>=1.8.0` | — | Static type checker |
| pre-commit | `>=3.0` | — | Hook framework |
| types-pyyaml | `>=6.0.12` | — | Type stubs for PyYAML |
| yamllint | `>=1.38.0` | — | YAML linter (**must match** `.pre-commit-config.yaml`) |
| pip-audit | — | `>=2.7` | PyPI vulnerability scanner |

### Justfile recipe-to-pixi mapping (library repo)

| Recipe | Delegates To | Notes |
| -------- | ------------- | ------- |
| `default` | `@just --list` | Ecosystem standard |
| `bootstrap` | `pixi install` + `pixi run pre-commit install` | One-command setup |
| `test *ARGS` | `pixi run pytest {{ test_dir }} {{ ARGS }}` | Forwards args |
| `lint` / `format` | `pixi run ruff check/format {{ src_dirs }}` | Configurable variable |
| `typecheck` | `pixi run mypy <package>/` | No pixi task; calls mypy directly |
| `audit` | `pixi run --environment lint pip-audit` | pip-audit in lint env |
| `check` | `just lint && just typecheck && just test` | Composite CI recipe |

### Optional pixi.toml addition for justfile

```toml
[feature.dev.dependencies]
just = ">=1.25.0,<2"
```

### Key metrics (feature composition)

- 6 tools consolidated into `[feature.shared]`; 2 environments both pull them
- 24 pixi-related tests pass post-refactor; 0 version conflicts
- 1 regression test (`test_pixi_shared_feature.py`) guards future drift

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (upstream) | Modular official skills repo | Authoritative project setup reference (pixi/uv/pip/conda) |
| ProjectScylla | Issue #1506 — ecosystem convention alignment | PR #1550 (CI-heavy justfile, 12 recipes) |
| ProjectHephaestus | Issues #35, #48, #49 — justfile + bootstrap/check/variables + src-layout | PRs #72, #77, #83 (library justfile, 9 recipes) |
| ProjectHephaestus | Issue #747 — pixi dependency de-duplication | Six dev tools into `[feature.shared]`, regression test, 24 pixi tests pass |
| Odysseus (meta-repo) | 4-submodule delegation via 2-wave myrmidon swarm, 2026-04-05 | Wave 1: 3 Sonnet agents (~70s); Wave 2: 1 Sonnet agent (~120s); verified `just --list` |
| ProjectHephaestus | Issue #1554 (4-item packaging/DX nitpick bundle) — PLANNING only, 2026-06-22 | Observed nested `pixi run` task smell (`audit = "pixi run --environment lint pip-audit"`); confirmed TASKS-first resolution via `pixi run audit --help`; consumer grep showed top-level `audit` had ZERO real consumers. Proposed `depends-on` relocation NOT yet executed/CI-confirmed |

---
*Project setup content adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0. Copyright (c) Modular Inc.*
