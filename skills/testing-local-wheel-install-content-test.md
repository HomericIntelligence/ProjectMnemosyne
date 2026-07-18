---
name: testing-local-wheel-install-content-test
description: "Committed local integration test for built-wheel contents and install behavior, mirroring the CI wheel smoke step. Use when: (1) packaging tests cover the sdist and CI smoke-installs the wheel but no committed local test exercises wheel install/content, (2) a hatch-vcs project must prove the generated _version.py ships in the wheel and the installed __version__ matches the wheel filename, (3) entry_points.txt console_scripts must be asserted equal to [project.scripts] in pyproject.toml, (4) an optional-extra boundary (base import must not pull the product-layer package or its heavy deps) must be proven from the installed artifact rather than the editable install, (5) the wheel must be proven free of repo scaffolding (tests/, scripts/, docs/, .github/)."
category: testing
date: 2026-07-17
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - python-packaging
  - wheel
  - integration-test
  - hatch-vcs
  - dist-info
  - entry-points
  - console-scripts
  - uv-venv
  - smoke-install
  - import-surface
  - optional-extras
  - build-no-isolation
  - ci-parity
---

# Local Wheel Install and Content Integration Test

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Close the packaging-test gap where sdist contents and CI wheel smoke-install are covered but no committed local test builds the wheel, inspects its contents, and installs it (Hephaestus issue #2165). |
| **Outcome** | Reviewed implementation plan producing one new integration test module that mirrors two already-CI-proven patterns (sdist-contents test + CI wheel smoke step) as a single build-once pytest module. |
| **Verification** | unverified — both source patterns (sdist test, CI smoke step) are green on the target repo's `main`, but the composed test module itself lands via the issue's PR; this entry records the design-stage pattern, not a measured local run. |

## When to Use

- A Python repo has `tests/integration/test_sdist_contents.py`-style sdist coverage and a CI job that smoke-installs the wheel, but nothing committed reproduces the wheel check locally.
- The project uses hatch-vcs (`[tool.hatch.build.hooks.vcs]` `version-file`), so `_version.py` exists only in build output — its presence in the wheel and version parity with the wheel filename are wheel-unique failure modes no source-tree test can catch.
- The project declares console scripts under `[project.scripts]` and drift between pyproject and the built `entry_points.txt` would ship silently.
- The repo enforces a library/product-layer import boundary (base `import pkg` must not pull the heavy optional extra) and that boundary is only tested against the editable install today.

## Verified Workflow

Structure: one module `tests/integration/test_wheel_contents.py`, marked `@pytest.mark.integration`, four tests sharing one module-scoped wheel build.

1. **Build once per module.** A `scope="module"` fixture using `tmp_path_factory` runs
   `[sys.executable, "-m", "build", str(REPO_ROOT), "--wheel", "--outdir", str(outdir), "--no-isolation"]`
   with `cwd=REPO_ROOT.parent`. `--no-isolation` avoids network fetching; it is safe only because the
   dev dependency group is asserted (by an existing test) to contain the build backend
   (`hatchling`, `hatch-vcs`). Probe-and-skip first:
   run `python -m build --help`; on `b"No module named build"` in stderr, `pytest.skip`, mirroring the
   sdist test. Glob the normalized distribution name (`homericintelligence_hephaestus-*.whl` — PyPI
   name lowercased, hyphens→underscores) and assert exactly one wheel.
2. **Content assertions via `zipfile.ZipFile(...).namelist()`** — assert only what the wheel can
   uniquely get wrong:
   - package files present: `pkg/__init__.py`, sample subpackages, and the build-generated
     `pkg/_version.py`;
   - dist-info metadata present: `<dist_info>/METADATA`, `entry_points.txt`, `licenses/LICENSE`
     (hatchling places license files under `licenses/`); derive `<dist_info>` by asserting exactly one
     top-level `*.dist-info` prefix;
   - scaffolding excluded: no member startswith `("tests/", "scripts/", "docs/", ".github/", ".claude/")` —
     guards `[tool.hatch.build.targets.wheel] packages = [...]` regressions.
3. **Entry-point parity:** read `entry_points.txt` from the zip, parse with
   `configparser.ConfigParser().read_string(...)`, and assert
   `dict(parser["console_scripts"]) == pyproject["project"]["scripts"]` (pyproject loaded with
   `tomllib`/`tomli` under the `sys.version_info >= (3, 11)` guard).
4. **Install smoke with CI parity:** skip when `shutil.which("uv")` is None; then
   `uv venv <tmp>/venv`, `uv pip install --python <venv-python> <wheel>`, and one `-c` probe that
   (a) imports the package and its public re-exports, (b) asserts the optional-extra boundary from the
   installed artifact (`'pydantic' not in sys.modules` and `'pkg.automation' not in sys.modules` after
   base import), and (c) prints `__version__`. Assert
   `wheel_path.name.split("-")[1] == printed_version` — filename version and installed metadata
   version must agree. Handle Windows venv layout (`Scripts/python.exe` vs `bin/python`).
5. **Prove each assertion can fail** before committing: temporarily assert a bogus member and watch the
   test fail, then restore (guards against vacuous zip-glob assertions).

### Key decisions

- Mirror, do not invent: copy the repo's existing sdist-contents test shape (probe-skip, `--no-isolation`
  rationale comment, member-set assertions) and the CI smoke step commands verbatim so local and CI
  checks cannot drift apart.
- `uv` as the venv/install driver with a `which`-skip, because the CI step uses `uv venv` + `uv pip
  install --python`; `python -m venv` + ensurepip would test a different code path.
- Version parity via the wheel filename, not a second metadata parse — hatch-vcs stamps both from the
  same build, so any mismatch means a corrupted build pipeline.
- No new pytest markers or config when `integration` is already registered and `testpaths` already
  includes `tests/integration`.

## Failed Attempts

- None technical. One plan-review round NOGO'd solely because the plan artifact reached the reviewer
  empty (pipeline delivery fault, grade F "empty artifact"); the remedy was re-emitting the full plan
  inline as the final message rather than any content change.

## Results & Parameters

- Result: a single new test module (four tests, one shared build) covers the issue's whole criterion;
  zero changes to pytest config, CI workflows, or packaging metadata were needed.
- Distribution glob: normalized (PEP 503 → wheel filename) project name, e.g.
  `homericintelligence_hephaestus-*.whl` for PyPI name `HomericIntelligence-Hephaestus`.
- Forbidden prefixes and expected package files are per-repo constants; keep them small and
  wheel-unique (the sdist test owns sdist-only concerns like NOTICE/COMPATIBILITY files).
- Boundary probe modules (`pydantic`, `pkg.automation`) come from the repo's documented
  library/product-layer rule.

## Evidence

- Hephaestus issue #2165 (Section 12 MINOR audit finding) and its reviewed implementation plan.
- Source patterns proven on Hephaestus `main`: `tests/integration/test_sdist_contents.py:54-96`
  (sdist member assertions, probe-skip at lines 56-63, backend-in-dev-group guard at lines 39-50) and
  `.github/workflows/_required.yml:622-629` (CI `uv venv` + `uv pip install` + import probes).
- Packaging facts from `pyproject.toml`: `[tool.hatch.build.targets.wheel] packages`,
  `[tool.hatch.build.hooks.vcs]` version-file, 15 `[project.scripts]` entries.

## Related

- [[python-packaging-pyproject-editable-install]] — hatch-vcs setup, editable installs, console-script
  enumeration; this entry covers the built-artifact test side.
- [[testing-source-package-asset-contract-mirroring]] — source↔package asset drift for package data;
  this entry covers wheel membership/metadata/install behavior.
- [[git-dco-signoff-distinct-from-gpg-sign]] — the delivering PR still needs `-S` and `-s`.
