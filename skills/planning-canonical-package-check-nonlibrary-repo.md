---
name: planning-canonical-package-check-nonlibrary-repo
description: "Plan the ecosystem-mandated canonical `package` CI check for a repo whose distributable is NOT a Python library (data/skills marketplace, config repo, doc repo). Use when: (1) a CI-naming convention requires a `package` check-run but the repo has no [build-system] and python -m build fails on flat-layout multi-top-dir, (2) deciding between making pyproject buildable vs defining `package` as the repo's real bundle artifact, (3) mirroring a new job into a workflow_call file whose caller you have not verified, (4) an issue paraphrases an external convention doc you did not fetch."
category: ci-cd
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-naming-convention
  - canonical-check
  - package-check
  - bundle-artifact
  - data-repo
  - workflow-call
  - plan-review-risks
  - yagni
---

# Planning the Canonical `package` Check for a Non-Library Repo

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Plan ProjectMnemosyne issue #2911: emit a canonical `package` check-run (Odysseus CI-naming convention) in a skills-marketplace repo with no buildable Python package |
| **Outcome** | Plan produced: `package` defined as the marketplace bundle tarball built+verified by a tested `scripts/build_package.py`; PyPI-style build rejected with evidence |
| **Verification** | unverified — plan-only, implementation and CI validation pending |

## When to Use

- An ecosystem CI-naming convention demands a canonical check (`package`, `build`, `test`) whose literal meaning (sdist/wheel) does not apply to the repo's content type
- `pyproject.toml` exists but has no `[build-system]`, and setuptools auto-discovery fails with "Multiple top-level packages discovered in a flat-layout"
- You must decide: make the package pip-buildable (add build backend + explicit packages) vs define `package` as the repo's real distributable (bundle tarball)
- You are about to mirror a new job into a `workflow_call` workflow file without having verified any workflow actually calls it
- The issue you are planning against paraphrases an external convention doc (another repo's `ci-naming-convention.md`) that you have not fetched

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Establish the repo has no real Python distributable before choosing the bundle route
grep -n "build-system" pyproject.toml                 # absent -> nothing declares a build backend
grep -rn "cov=scripts" pyproject.toml                 # scripts/ is tooling, not a shipped library
# The live "submit-pypi" style check may be GitHub dependency-graph auto-submission, NOT a publish

# 2. Verify a workflow_call file actually has a caller before mirroring jobs into it
grep -rn "uses: ./.github/workflows/_checks.yml" .github/workflows/   # no hits -> mirrored job is dead code

# 3. Keep the CI job thin; put build+verify in a tested script
python3 scripts/build_package.py --output-dir dist    # exit 0 built+verified, 1 failure, 2 argparse usage

# 4. Version parse that honors requires-python >= 3.9 (tomllib is 3.11+)
python3 -c "import re,pathlib; print(re.search(r'^version\s*=\s*\"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(), re.M).group(1))"
```

### Detailed Steps

1. **Decide the distribution model from repo evidence, not the check's name.** If the repo is a data/skills marketplace (content = markdown + JSON, Python is repo tooling only), define `package` as the bundle artifact: a versioned tarball of the content dirs (e.g. `.claude-plugin/`, `skills/`, `plugins/`, `schemas/`, `templates/`). Adding a build backend to ship tooling scripts to a registry nobody publishes to violates YAGNI/KISS.

2. **Library-first: build + verify logic lives in a tested script, the CI job is a thin invocation.** `build_package(repo_root, output_dir) -> Path` plus a read-only `verify_package(tarball) -> list[str]` that re-opens the artifact and checks required members (marketplace.json present AND parseable, at least one `skills/*.md`). If the repo lints/type-checks `scripts/` and `tests/` already, the new files enter the existing gates with zero config changes.

3. **Verify job-emission wiring before mirroring.** If the repo duplicates jobs across a directly-triggered workflow (`on: pull_request/push`) and a `workflow_call` file, grep for the caller (`uses: ./.github/workflows/<file>.yml`) before claiming the mirrored job emits a check-run. A `workflow_call` file with no caller emits nothing — the mirror is dead code and the plan must say so or drop it.

4. **Fetch the external convention doc the issue cites.** Exact requirements (must the check upload an artifact? is `twine check` semantics expected? exact check-run name casing?) come from the convention doc, not the issue's paraphrase. If unfetchable at planning time, list it explicitly as an unverified assumption for the reviewer.

5. **Honor repo-local CI constraints when authoring the job**: pinned action SHAs copied from existing jobs, no `|| true` / `continue-on-error` (repos may have a forbid-suppressions gate), yamllint line-length limits, canonical-check comment pattern matching the existing aggregate `test` job.

6. **Give the script collision-free exit codes** (0 built+verified, 1 build/verify failure, argparse's own 2 for usage errors) and one dedicated negative test per verify error kind, plus a real-repo ships-green test so the new gate is green on the current tree.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Option 1: make pyproject pip-buildable | Considered adding `[build-system]` + explicit packages to run `python -m build` + `twine check` | Flat layout with `skills/ plugins/ schemas/ templates/` top-level dirs breaks auto-discovery; the only Python is repo tooling under `scripts/`; the existing `submit-pypi` check is dependency-graph auto-submission, not a publish path — nothing would ever consume the wheel | Define the canonical check around the repo's REAL distributable; do not force-fit a library build onto a data repo |
| Inline tar command in the workflow YAML | Considered `tar czf dist/... .claude-plugin skills ...` directly in the job step | Untestable, no verify step, invisible to ruff/mypy/pytest; violates the library-first executable-convention-guard pattern | Build+verify logic goes in a tested script; the CI job stays a one-line invocation |
| `tomllib` for version parsing | Considered `tomllib.load()` to read `[project] version` | `tomllib` is Python 3.11+ but the repo declares `requires-python = ">=3.9"` — the script would break for local 3.9/3.10 users even though CI pins 3.11 | Regex-parse the version line (or read from a format available at the floor version); match the repo's declared floor, not CI's pin |
| Mirroring the job into `_checks.yml` without verifying its caller | Plan mirrors the `package` job into a `workflow_call` file because every other job is duplicated there | No caller of `_checks.yml` was ever verified by grep — if nothing calls it, the mirrored job emits no check-run and the "mirror" rationale is cargo-culting an existing (possibly dead) pattern | Grep for `uses: ./.github/workflows/<file>.yml` BEFORE citing job mirroring as load-bearing; flag it as an assumption otherwise |
| Trusting the issue's paraphrase of the convention doc | Planned `package` semantics from the issue body's summary of Odysseus `ci-naming-convention.md` | The doc itself was never fetched; exact requirements (artifact upload mandatory? naming casing? verify semantics?) are unconfirmed | External convention docs must be fetched during planning, or explicitly listed as unverified inputs for the reviewer |

## Results & Parameters

### Canonical `package` job for a bundle-artifact repo (GitHub Actions)

```yaml
  package:
    name: package
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@<same-pinned-sha-as-sibling-jobs>
      - uses: actions/setup-python@<same-pinned-sha-as-sibling-jobs>
        with:
          python-version: '3.11'
      - name: Build and verify marketplace bundle
        run: python3 scripts/build_package.py --output-dir dist
      - name: Upload package artifact
        uses: actions/upload-artifact@<same-pinned-sha-as-sibling-jobs>
        with:
          name: <project>-package
          path: dist/*.tar.gz
          retention-days: 90
```

### Script contract

- `build_package(repo_root, output_dir) -> Path` — tarball named `<project>-<version>.tar.gz`; hard-fails (`FileNotFoundError`) if any declared bundle dir is missing; excludes `__pycache__`/`*.pyc`; sorted members for near-determinism (gzip mtime still varies — fine for a check, not for release signing)
- `verify_package(tarball) -> list[str]` — read-only; reopens the tarball; returns problem strings (missing manifest, unparseable JSON, zero content files)
- Exit codes: 0 built+verified, 1 failure, 2 argparse usage

### Reviewer risk checklist (what to verify before GO)

- [ ] Does anything call the `workflow_call` file the job was mirrored into? (`grep -rn "uses: ./.github/workflows/" .github/workflows/`)
- [ ] Does the ecosystem convention doc impose requirements beyond "emit a check named `package`"? Fetch it.
- [ ] Coverage interaction: if pytest `addopts` has `--cov=scripts`, the new script joins the coverage report — confirm no global `fail-under` makes partially-covered branches a gate failure
- [ ] Line numbers cited in the plan (`_required.yml:305` etc.) drift — re-grep, don't trust
- [ ] Hard-required bundle dirs (`schemas/`, `templates/`) make the check fail if a dir is later removed — confirm that is intended coupling

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | Issue #2911 planning (plan-only, not yet implemented) | Plan posted to the issue; implementation PR pending |
