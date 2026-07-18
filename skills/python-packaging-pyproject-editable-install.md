---
name: python-packaging-pyproject-editable-install
description: "Use when: (1) migrating a Python project from hardcoded version in pyproject.toml to hatch-vcs dynamic versioning from git tags, (2) a newly-merged [project.scripts] entry yields 'command not found' after git pull because the editable install is stale — re-run 'pixi run dev-install' or 'pip install -e .', (3) a console-script sweep needs to enumerate [project.scripts] in pyproject.toml rather than grep for 'def main' (misses *_main-suffixed callables), (4) migrating from pytest-watch to pytest-watcher to drop the unmaintained docopt transitive dependency, (5) shipping a Python package to PyPI with hatchling/hatch-vcs/pixi.lock and configuring trusted-publishing, (6) code imports a package that loads NON-.py DATA FILES at runtime (Jinja templates, JSON/YAML resources) via importlib.resources / jinja2.PackageLoader and it raises 'could not find a <dir> directory in the <pkg> package' / FileNotFoundError because the data tree is present in the repo but MISSING from the checkout/build the code runs against, (7) a long automation/agent run does a large amount of no-op work because a required runtime resource was absent and nothing failed fast — add a startup preflight."
category: tooling
date: 2026-07-18
version: "1.1.0"
user-invocable: false
history: python-packaging-pyproject-editable-install.history
tags:
  - python-packaging
  - pyproject
  - hatch-vcs
  - hatchling
  - editable-install
  - pip-install-e
  - dev-install
  - console-scripts
  - entry-points
  - dynamic-version
  - git-tags
  - importlib-metadata
  - distribution-name
  - command-not-found
  - pypi
  - trusted-publishing
  - pixi
  - pytest-watcher
  - package-data
  - jinja-templates
  - packageloader
  - importlib-resources
  - runtime-resource-missing
  - startup-preflight
  - fail-fast
---

# Python Packaging: pyproject.toml, hatch-vcs, and Editable Installs

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | One canonical reference for pyproject.toml-centric packaging: hatch-vcs dynamic versioning from git tags, recovering from a stale editable install after a merge adds `[project.scripts]`, enumerating console scripts from `[project.scripts]` (not `grep '^def main'`), replacing the unmaintained `pytest-watch` with `pytest-watcher`, and shipping to PyPI via trusted-publishing with hatchling. |
| **Outcome** | hatch-vcs generates `<pkg>/_version.py` at install time from `git describe`; `__init__.py` looks up the version by **distribution name**; a stale console-script after `git pull` is fixed by re-running the editable install; the full CLI surface is enumerated from `[project.scripts]`; PyPI publishing uses OIDC trusted-publishing on a `v*` tag push. |
| **Verification** | verified-ci |
| **History** | [changelog](./python-packaging-pyproject-editable-install.history) |

## When to Use

- `pyproject.toml` has `version = "X.Y.Z"` hardcoded and you want the version derived automatically from git tags with no file edits and no bot commits on `main`
- After hatch-vcs migration, `import yourpackage` raises `PackageNotFoundError` because `__version__` looks up the import name instead of the distribution name
- A drift / single-source-of-truth script greps `pyproject.toml` for `[project].version`, which no longer exists once `dynamic = ["version"]` is set
- A `git pull` / merge brought in a new `[project.scripts]` entry and the new console script returns `command not found` even though the module is importable (`python -m ...` works but the binary does not)
- You are sweeping a change across every console script (add `--json`, refactor shared CLI infra, write a parametrized integration test) and need the full CLI inventory
- You want to drop the unmaintained `pytest-watch` (pulls in abandoned `docopt`) in favor of `pytest-watcher`
- You are shipping a Python package to PyPI for the first time with hatchling + hatch-vcs + pixi.lock and want OIDC trusted-publishing (no API token)

## Verified Workflow

### Quick Reference

```bash
# ── hatch-vcs: the four pieces that MUST change together ─────────────────────
# 1. pyproject.toml: dynamic = ["version"]; [tool.hatch.version] source="vcs";
#    [tool.hatch.build.hooks.vcs] version-file="<pkg>/_version.py";
#    add hatch-vcs to [build-system].requires
# 2. <pkg>/__init__.py: _pkg_version("<distribution-name>")  NOT the import name
# 3. drift/consistency scripts: derive from `git describe`, never parse pyproject version
# 4. single-source check: validate the invariant via tomllib, not a string compare
# Also: add <pkg>/_version.py to .gitignore AND [tool.ruff] exclude.

# ── Stale editable install after a merge added [project.scripts] ─────────────
pixi run dev-install        # pixi project (== pip install -e . --no-deps)
pip install -e .            # plain pip project
which <new-binary>          # should now print a path
<new-binary> --help         # should produce usage text

# ── Full CLI inventory: read [project.scripts], do NOT grep for 'def main' ────
python3 -c "import tomllib; \
print('\n'.join(f'{c}\t{t}' for c,t in \
tomllib.loads(open('pyproject.toml','rb').read())['project']['scripts'].items()))" | sort

# ── pytest-watch → pytest-watcher (drop unmaintained docopt) ─────────────────
# pixi.toml: replace  pytest-watch = "..."  with  pytest-watcher = ">=0.4"
# command:   ptw  →  ptw .         (pytest-watcher requires an explicit path arg)

# ── PyPI trusted-publishing (OIDC) ───────────────────────────────────────────
git tag v1.0.0 && git push origin v1.0.0   # release.yml + pypa/gh-action-pypi-publish@release/v1
# pyproject.toml [project].name MUST exactly match the PyPI project name;
# requires id-token: write + environment: pypi + a pending publisher for NEW projects
```

### Detailed Steps

#### 1. hatch-vcs dynamic versioning from git tags

Replace a hardcoded `version` with VCS-derived versioning. All four pieces must change together.

**pyproject.toml:**

```toml
[build-system]
# hatch-vcs is a BUILD-TIME dep — declare it here, NEVER in pixi.toml [pypi-dependencies]
requires = ["hatchling>=1.27.0,<2", "hatch-vcs>=0.4.0,<1"]
build-backend = "hatchling.build"

[project]
name = "YourPackageName"
# Remove:  version = "0.7.0"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "yourpackage/_version.py"
```

Replace `yourpackage` with the actual package directory (the one containing `__init__.py`).

**`.gitignore`** — never commit the generated file (regenerated on every install):

```gitignore
# hatch-vcs generated version file (created at pip install / pixi install time)
yourpackage/_version.py
```

**`[tool.ruff]` exclude** — otherwise ruff lints/formats the generated file and fails CI:

```toml
[tool.ruff]
exclude = [
  "yourpackage/_version.py",   # hatch-vcs generated — not human-authored
]
```

**`<pkg>/__init__.py`** — look up by the **distribution name** (the literal `[project].name`), NOT the import package directory name. `importlib.metadata.version()` does a PEP 503 normalized lookup against installed `*.dist-info` directories; there is no `*.dist-info` for the import name:

```python
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    # CRITICAL: [project].name from pyproject.toml, NOT the import package name.
    __version__ = _pkg_version("HomericIntelligence-Hephaestus")
except PackageNotFoundError:
    __version__ = "unknown"
```

**Key insight — `_version.py` is generated at install time.** When `pip install -e .` / `pixi install` runs, hatch-vcs writes `yourpackage/_version.py` containing the current version. It exists locally after install, does NOT exist in a fresh CI checkout until install runs, must be gitignored, and must be in ruff's exclude.

**Simplify the auto-tag CI workflow** — with hatch-vcs the workflow only pushes a tag; remove every step that read/bumped/rewrote/committed `pyproject.toml`:

```yaml
- name: Compute next patch version and push tag
  shell: bash
  run: |
    LATEST_TAG=$(git tag --list 'v*' --sort=-v:refname | head -1)
    LATEST="${LATEST_TAG#v:-0.7.0}"; LATEST="${LATEST_TAG:+${LATEST_TAG#v}}"; LATEST="${LATEST:-0.7.0}"
    MAJOR=$(echo "$LATEST" | cut -d. -f1); MINOR=$(echo "$LATEST" | cut -d. -f2); PATCH=$(echo "$LATEST" | cut -d. -f3)
    TAG="v${MAJOR}.${MINOR}.$((PATCH + 1))"
    git rev-parse "$TAG" >/dev/null 2>&1 && { echo "Tag $TAG exists"; exit 0; }
    git tag "$TAG" && git push origin "$TAG"
```

**Update downstream drift / single-source checks.** Any tooling that assumed a static `[project].version` breaks. Derive the canonical version from git instead:

```python
import subprocess
from importlib.metadata import PackageNotFoundError, version as _pkg_version

def _get_canonical_version(dist_name: str) -> str:
    """Canonical version: latest git tag, with installed dist metadata fallback."""
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return tag.lstrip("v")
    except subprocess.CalledProcessError:
        pass
    try:
        return _pkg_version(dist_name)
    except PackageNotFoundError:
        return "unknown"
```

For a "single source of truth" check, validate the **invariant** (not a string match) via `tomllib`:

```python
import tomllib
from pathlib import Path

def check_single_source_invariant() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    project = data.get("project", {})
    assert "version" in project.get("dynamic", []), "[project].dynamic must include 'version'"
    assert "version" not in project, "[project] must NOT define a static 'version' field"
    hv = data.get("tool", {}).get("hatch", {}).get("version", {})
    assert hv.get("source") == "vcs", "[tool.hatch.version].source must be 'vcs'"
```

When verifying a check script printed a status line, read the FULL stdout (or grep for the line). Never assert a line is missing from a truncated `tail` — earlier lines get cut and you will report a false regression.

#### 2. Stale editable install after a merge added `[project.scripts]`

A bare `git pull` updates the working tree but does NOT re-run any install step. The on-disk source has a new `[project.scripts]` entry, but the package metadata that PATH consults (`<dist-info>/entry_points.txt` plus stub binaries in `<env>/bin/`) still advertises the OLD list.

**Detect it** — these three together are the smoking gun:

```bash
python -c "from hephaestus.automation import ensure_state_labels; print('ok')"   # ok
python -m hephaestus.automation.ensure_state_labels --help                       # prints usage
which hephaestus-ensure-state-labels                                             # EMPTY → stale entry points
```

If the first two work but `which` fails for ONE binary while every other `hephaestus-*` console script still works, it is stale `entry_points.txt`, NOT a missing/broken install or a PATH problem.

**Confirm the cause and fix:**

```bash
git diff HEAD~1 -- pyproject.toml | grep -A2 'project.scripts'   # confirm a new scripts entry
pixi run dev-install      # pixi project (== pip install -e . --no-deps); fast, reuses cached wheel
pip install -e .          # plain pip project
which hephaestus-ensure-state-labels   # now prints a path
```

**Version-string evidence pattern** (hatch-vcs / setuptools-scm) — the runtime version encodes the git SHA at install time, so it moves when the install picks up the merge:

```bash
OLD=$(python -c "import hephaestus; print(hephaestus.__version__)")  # 0.9.3.dev39+g4f63a5643 (pre-merge)
pixi run dev-install
NEW=$(python -c "import hephaestus; print(hephaestus.__version__)")  # 0.9.3.dev46+g240788441 (post-merge)
# $NEW differing from $OLD (especially the +g<sha> segment) = the install picked up the merge.
```

**Diff-trigger heuristic** — re-run `dev-install` after a pull whenever the `pyproject.toml` diff touches any of: `[project.scripts]` (new entry-point stubs), `[project.optional-dependencies]`, `[project.dependencies]`, `[tool.hatch.build.hooks.vcs]` / `version-file`, or any `[build-system]` change. Cost: a few seconds vs. minutes of "command not found" debugging.

#### 2b. Runtime DATA files (templates/resources) missing from the checkout the code runs against

A package can be **importable** yet **broken at runtime** because its non-`.py`
data tree (Jinja templates, packaged JSON/YAML) is absent from the tree the code
actually executes against. Verified failure (ProjectHephaestus, 2026-07-17): a
2.25h `hephaestus-automation-loop` run produced **0 commits / 0 PRs** because
`hephaestus.prompts.catalog` (a `jinja2.PackageLoader(..., "templates/default")`)
raised on **every** agent-prompt render — plan, implement, review, AND the
`commit_push` commit-message generation — **172 times**:

```text
ValueError: PackageLoader could not find a 'templates/default' directory
in the 'hephaestus.prompts' package.
```

**Why it happened:** the loop ran from a checkout at an off-`main` WIP commit that
had the catalog `catalog.py` **code** but **zero committed** `templates/*.j2`
files (a stray `hephaestus/prompts/__pycache__/` made the module importable with
no templates). `origin/main` had all 55 templates committed. Downstream symptoms
MASKED the cause: "no commits vs base → state:skip", "poisoned at implementation",
and reviewer "zero-thread NOGO" were all consequences, not the disease.

**Two independent guards — do BOTH:**

1. **Declare the data as package data** so an installed/built artifact can never
   be resource-less. With hatchling, `[tool.hatch.build.targets.wheel]
   packages = ["<pkg>"]` includes non-`.py` files under the package, but ADD an
   sdist/wheel content test that asserts the data ships:

```python
# tests/integration/test_sdist_contents.py style — fail if templates are dropped
import tarfile, subprocess, glob
subprocess.run(["python", "-m", "build", "--sdist", "--no-isolation"], check=True)
sdist = sorted(glob.glob("dist/*.tar.gz"))[-1]
names = tarfile.open(sdist).getnames()
assert any(n.endswith("prompts/templates/default/implementation/implementation.j2")
           for n in names), "prompt templates missing from sdist"
```

2. **Fail fast with a startup preflight** — a long agent/automation run must NOT
   dispatch work when a required runtime resource is absent. Render one prompt (or
   probe the resource) BEFORE the first job; abort with a clear remediation:

```python
def preflight_prompt_catalog() -> None:
    """Abort fast if the prompt templates are missing (packaging regression)."""
    try:
        from mypkg.prompts.catalog import current
        current()  # constructs the PackageLoader -> raises here if templates absent
    except Exception as exc:
        raise SystemExit(
            f"prompt templates unavailable ({exc}); the checkout/install is "
            f"missing package data - run `uv sync` (or reinstall) and retry"
        ) from exc
```

**Detect it after the fact:** grep the run log for a single repeated
resource-loader error (`PackageLoader could not find`, `FileNotFoundError`,
`importlib.resources`), then confirm on disk that the data tree is absent from
the RUNNING checkout while present on `main`:

```bash
git ls-tree -r origin/main --name-only | grep -c '<pkg>/prompts/templates/'   # e.g. 55
find <running-checkout>/<pkg>/prompts/templates -name '*.j2' | wc -l          # 0 == broken
git -C <running-checkout> rev-parse --short HEAD    # is it even an on-main commit?
```

The classifier bug (an infra "cannot build a prompt" routed to `finished(fail)`
as if the work item were *poison*) is a related smell: distinguish "the harness
could not build a prompt" from "the agent produced bad output" so a packaging
regression fails fast instead of silently burning items.

#### 3. Enumerate `[project.scripts]` — do NOT `grep '^def main'`

`grep -rln '^def main'` only finds entry points named `module:main`. It silently misses suffixed callables like `check_version_consistency_main`, `bench_precommit_main`, `validate_agents_main`. In one verified session this missed **10 of 41 console_scripts (24%)**. Suffixed names are correct and idiomatic — a module can host several CLIs (e.g. `validation/markdown.py` exposes both `main` and `check_readmes_main`).

The source of truth is `[project.scripts]` — by definition every binary the package ships is listed there. Use a parametrized integration test so the inventory maintains itself:

```python
# tests/integration/test_cli_entry_points.py
import tomllib
from pathlib import Path

def _load_entry_points() -> list[tuple[str, str, str]]:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    return [(cmd, *target.partition(":")[::2]) for cmd, target in sorted(data["project"]["scripts"].items())]

ENTRY_POINTS = _load_entry_points()

@pytest.mark.parametrize("command,module_path,attr", ENTRY_POINTS)
def test_advertises_json_flag(command, module_path, attr):
    binary = shutil.which(command) or pytest.skip(f"{command} not on PATH")
    result = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=30)
    assert "--json" in result.stdout + result.stderr, f"{command} missing --json"
```

Recipe for "add flag F to every CLI": inventory `[project.scripts]` (bucket by module to find co-located `*_main` siblings) → add a shared `add_F_arg(parser)` helper → edit EACH entry point (every `*_main` in a multi-CLI module) → parametrize the test → iterate until 100%.

#### 4. pytest-watch → pytest-watcher (drop unmaintained docopt)

`pytest-watch` (`ptw`) is unmaintained and pulls in the abandoned `docopt`, which surfaces in dependency/CVE audits. Replace it with the maintained `pytest-watcher`:

```toml
# pixi.toml — replace the dev dependency
# pytest-watch = "..."          # remove
pytest-watcher = ">=0.4"        # add
```

Command change: `pytest-watcher` requires an explicit path argument — `ptw` becomes `ptw .` (watch the current directory). Update any task aliases and docs accordingly.

#### 5. PyPI trusted-publishing with hatchling + hatch-vcs

Checklist:

1. `pyproject.toml [project].name` must **exactly** match the PyPI project name (wheel filenames are PEP 625 lowercase-normalized, e.g. `orgname_projectname-*.whl`).
2. GitHub environment `pypi` with deployment tag pattern `v*`.
3. Workflow has top-level `permissions: id-token: write`.
4. **New projects**: add a *pending publisher* at pypi.org/manage/account/publishing/ (existing projects: add a trusted publisher in project settings).
5. Use `pypa/gh-action-pypi-publish@release/v1` with `verbose: true` while debugging.

```yaml
# .github/workflows/release.yml (minimal verified pattern)
name: Release
on:
  push:
    tags: ["v*"]
permissions:
  contents: write
  id-token: write
jobs:
  build-and-publish:
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-pixi
      - run: pixi run python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          verbose: true
```

Wheel-only build: add `[tool.hatch.build] targets = ["wheel"]` ABOVE the `[tool.hatch.build.targets.wheel]` section. If all source paths are under `packages = ["src/pkg"]`, do NOT add `[tool.hatch.build.targets.wheel.force-include]` — it is redundant and breaks the two-step sdist→wheel build (`force-include` paths resolve relative to the unpacked sdist root, not the repo root).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | --------------- | --------------- | ---------------- |
| Ran the loop against an importable-but-resource-less package | Launched `hephaestus-automation-loop` from a checkout whose `prompts` package had `catalog.py` but no committed `templates/*.j2` (only `__pycache__`) | `jinja2.PackageLoader(..., "templates/default")` raised on every prompt render — 172x — so 0 commits/PRs across a 2.25h run; symptoms ("no commits->skip", "poisoned") masked the cause | Declare runtime data as package data + ship-test it; add a startup preflight that renders one prompt and aborts fast; verify the running checkout has the data tree (and is an on-`main` commit) before launching |
| Use the **import name** with `importlib.metadata.version()` | `__version__ = _pkg_version("hephaestus")` when the distribution is `HomericIntelligence-Hephaestus` | `PackageNotFoundError`: the lookup is a PEP 503 normalized match against installed `*.dist-info`; there is no `hephaestus-*.dist-info`. `__version__` silently becomes `"unknown"` | `importlib.metadata.version()` requires the **distribution name** (literal `[project].name`), not the import package directory name |
| Parse `pyproject.toml` for `[project].version` in a drift check | `tomllib.load(...)["project"]["version"]` after the migration | `KeyError` — once `dynamic = ["version"]` is set, `[project].version` no longer exists; hatch-vcs removes it | Derive the canonical version from `git describe --tags --abbrev=0 --match 'v[0-9]*'` with `importlib.metadata` fallback |
| Add `hatch-vcs` to `pixi.toml [pypi-dependencies]` | `hatch-vcs = ">=0.4.0,<1"` under `[pypi-dependencies]` | Unnecessary; pip resolves it from `[build-system].requires`. Adds lockfile noise | `hatch-vcs` is build-time only — declare it in `[build-system].requires` only |
| Omit `_version.py` from `.gitignore` / ruff `exclude` | Left the generated file untracked-but-lintable | It gets staged/committed, and ruff reformats it → spurious diffs / CI failures | Add `<pkg>/_version.py` to BOTH `.gitignore` and `[tool.ruff] exclude` when enabling hatch-vcs |
| Keep auto-tag workflow with `pyproject.toml` bump steps | Left CI steps that read/incremented/rewrote/committed the version to `main` | Creates a bot commit on `main` every CI pass → infinite-loop potential; defeats auto-versioning | With hatch-vcs the workflow only pushes a git tag; remove all file-edit/commit steps |
| `which <binary>` empty → assume the package is uninstalled | Diagnosed "package not installed" when one console script was missing | Misleading — every other `hephaestus-*` script was still on PATH, proving it WAS installed; only the new entry was missing | One missing binary while siblings work = stale `entry_points.txt`, not a missing install |
| Run `pixi install` (environment-level) to fix the missing binary | Heavier reinstall to "make everything fresh" | Overkill — rebuilds the whole pixi env when only `entry_points.txt` needed regenerating | Use targeted `pixi run dev-install` (= `pip install -e . --no-deps`); faster, fixes the actual issue |
| Modify `PATH` / hand-craft the stub / `exec bash` | Suspected PATH ordering or shell hash-cache; tried creating the stub by hand | The stub binary does not exist on disk yet; no PATH/rehash/manual stub fixes that, and a hand-made stub is overwritten on next install and leaves `entry_points.txt` stale | Re-install to CREATE the stub; don't fight the package machinery |
| `python -m <module>` as the "fix" | Invoked the CLI by module path to dodge entry-point registration | Works as a one-off but breaks scripts/automation that hard-code the binary name | OK as a 30-second workaround; NOT a fix — re-install to register the name |
| `grep '^def main'` for full CLI inventory | Find every CLI by `def main` | Missed 10 of 41 (24%) — any `*_main`-suffixed callable is invisible to the regex | Source of truth is config, not convention — read `[project.scripts]`; back it with a parametrized test |
| Broaden the regex / `ls venv/bin/*` / manual checklist | `def .*_main\|def main`, list installed binaries, maintain a doc | Regex still convention-bound and matches non-CLI helpers; `ls bin/` only shows what got installed (misses forgotten config); checklists rot within one PR | Parametrize a test over `[project.scripts]` — the test list IS the always-current inventory |
| `force-include` to fix the sdist→wheel build (relative path) | Changed `"src/pkg/path"` to `"path"` in `force-include` | Still fails — hatchling's CWD during wheel-from-sdist is the sdist root | Remove `force-include` entirely if paths are already under `packages` |
| `tail -3` to verify a check script's output | Claimed a status line was missing based on the last 3 lines | The line was earlier and got truncated → false regression report | Read the FULL stdout or grep for the expected line; quote the actual matching line |

## Results & Parameters

### Key Parameters

| Parameter | Description | Example |
| ----------- | ------------- | --------- |
| `yourpackage` | Package directory containing `__init__.py` | `hephaestus` |
| `your-dist-name` | `[project].name` — the literal value passed to `importlib.metadata.version()` | `HomericIntelligence-Hephaestus` |
| Bootstrap version | Last known release for the tag-list fallback | `"0.7.0"` |
| `hatchling` pin | Tested range | `>=1.27.0,<2` |
| `hatch-vcs` pin | Tested range | `>=0.4.0,<1` |
| Canonical version source (post-migration) | `git describe --tags --abbrev=0 --match 'v[0-9]*'` | `v0.7.1` → `0.7.1` |
| `dev-install` (pixi) | Targeted editable reinstall | `pip install -e . --no-deps` |
| Runtime version string (hatch-vcs) | `<base>.devN+g<sha>` — the SHA moves on re-install | `0.9.3.dev46+g240788441` |

### Diff-trigger heuristic (re-run `dev-install` after pull)

| Diff signal | Why it triggers re-install |
| ------------- | ---------------------------- |
| `[project.scripts]` add/remove/rename | New/removed entry points need stub binaries on PATH |
| `[project.optional-dependencies]` change | Extras-driven imports may now fail/succeed differently |
| `[project.dependencies]` change | Runtime imports may have new/removed deps |
| `[tool.hatch.build.hooks.vcs]` / `version-file` | Generated `_version.py` may have moved |
| Any `[build-system]` change | Build backend or its config changed; re-install to be safe |

### Why the stale-install bug is easy to miss

| Misleading observation | Why it tricks you |
| ------------------------ | ------------------- |
| `import <module>` works fine | Python re-reads source on next import — no install step needed for `import` |
| Pre-existing console scripts keep working | Their stubs were registered at the last install and are still on PATH |
| `command not found` looks like a build/install bug | It IS an install issue — a targeted one (stale `entry_points.txt`), not "package broken" |
| `pip show` / `pip list` report the package installed | True — it IS installed, just with the old entry-points list (read from stale `dist-info/`) |

### Console-script enumeration outcome

- Observed miss rate of `grep '^def main'`: 10 of 41 (24%) in one ProjectHephaestus session
- pyproject parse + inventory fixture: ~20 LOC; parametrized test class: ~30 LOC
- Catch rate on first sweep: 76% (31/41); the parametrized test caught the remaining 24% loudly, naming each missed CLI

### Expected outcomes (hatch-vcs migration)

- `pyproject.toml` has `dynamic = ["version"]` and no static `version = "X.Y.Z"`
- `[tool.hatch.version]` (`source = "vcs"`) and `[tool.hatch.build.hooks.vcs]` present
- `<pkg>/_version.py` exists locally after install but is NOT committed
- `importlib.metadata.version("<dist-name>")` and `<pkg>.__version__` both return the latest git tag's version (NOT `"unknown"`)
- Auto-tag CI workflow only pushes a tag — no commit to `main`
- `hatch-vcs` absent from `pixi.toml [pypi-dependencies]`
- Drift/single-source checks derive from `git describe` / validate the invariant via `tomllib`

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Branch `5047-separate-dev-production-deps` | `version = "0.7.0"` removed; `dynamic = ["version"]` added; auto-tag workflow simplified to tag-push; pre-commit passes |
| ProjectHephaestus | PR #434 | Fixed `hephaestus/__init__.py` to use distribution name `"HomericIntelligence-Hephaestus"` in `importlib.metadata.version()`; resolved `PackageNotFoundError` |
| ProjectHephaestus | PR #436 | Rewrote `scripts/check_version_single_source.py` to validate the hatch-vcs invariant via `tomllib` instead of comparing version strings |
| ProjectHephaestus | PR #438 | Replaced `_get_pyproject_version` with `_get_canonical_version` deriving from `git describe ... --match 'v[0-9]*'` with `importlib.metadata` fallback |
| ProjectHephaestus | 2026-05-29 — PR #707 (`2407884`) added `hephaestus-ensure-state-labels` to `[project.scripts]` | After `git pull --ff-only`, the new binary was `command not found` despite the module being importable; `pixi run dev-install` regenerated `entry_points.txt`; version moved `0.9.3.dev39+g4f63a5643` → `0.9.3.dev46+g240788441`; `which` then found the binary |
| ProjectHephaestus | 2026-05-26 — `--json` sweep across 41 console_scripts (PR #603) | `grep '^def main'` found 33; a parametrized `TestCLIJsonFlag` test caught 10 missing CLIs from `*_main`-suffixed callables; final pass reached 41/41 |
| HomericIntelligence/ProjectScylla | PRs #1905, #1741–1744 | hatchling wheel/sdist build, cross-repo dep publish, PyPI trusted-publishing |
