---
name: planning-canonical-package-check-nonlibrary-repo
description: "Plan the ecosystem-mandated canonical `package` CI check for a repo whose distributable is NOT a Python library (data/skills marketplace, config repo, doc repo, manifest/dataset repo). Use when: (1) a CI-naming convention requires a `package` check-run but the repo has no [build-system] and python -m build fails on flat-layout multi-top-dir, (2) deciding between making pyproject buildable vs defining `package` as the repo's real bundle artifact, (3) mirroring a new job into a workflow_call file whose caller you have not verified, (4) an issue paraphrases an external convention doc you did not fetch, (5) a canonical category 'seems N/A' for the repo — the ecosystem board is generated from live check-runs on main and has no N/A marker, so the only way to fill the cell is a real check-run, (6) the workflow you would add the job to is PR-only (the check-run would never appear on main), (7) the target workflow has policy-guard jobs (forbid-suppressions) that reject || true / continue-on-error / ::warning::, (8) sequencing branch-protection registration of the new required context."
category: ci-cd
date: 2026-07-03
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-canonical-package-check-nonlibrary-repo.history
tags:
  - ci-naming-convention
  - canonical-check
  - package-check
  - bundle-artifact
  - data-repo
  - manifest-repo
  - release-archive
  - deterministic-tar
  - workflow-call
  - board-check-runs
  - branch-protection
  - policy-guards
  - plan-review-risks
  - yagni
---

# Planning the Canonical `package` Check for a Non-Library Repo

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-03 (v1.1.0; original 2026-07-02) |
| **Objective** | Plan the canonical `package` check-run (Odysseus CI-naming convention) for non-library repos: Mnemosyne #2911 (skills marketplace, v1.0.0) and Myrmidons #749 (agent-manifest/dataset repo, v1.1.0) |
| **Outcome** | Plans produced: `package` defined as the repo's REAL bundle/release archive (tarball of content dirs + SHA256SUMS), built and round-trip verified; PyPI-style build and "document as N/A" both rejected with evidence |
| **Verification** | unverified — plan-only, implementation and CI validation pending |

## When to Use

- An ecosystem CI-naming convention demands a canonical check (`package`, `build`, `test`) whose literal meaning (sdist/wheel) does not apply to the repo's content type
- `pyproject.toml` exists but has no `[build-system]`, and setuptools auto-discovery fails with "Multiple top-level packages discovered in a flat-layout"
- You must decide: make the package pip-buildable (add build backend + explicit packages) vs define `package` as the repo's real distributable (bundle tarball)
- You are about to mirror a new job into a `workflow_call` workflow file without having verified any workflow actually calls it
- The issue you are planning against paraphrases an external convention doc (another repo's `ci-naming-convention.md`) that you have not fetched
- A canonical category (e.g. `package`) "seems N/A" for a manifest/dataset repo and the issue offers a "document as N/A" option — the ecosystem board is generated from live check-runs on `main`, so that option is usually a dead end
- You are choosing which workflow file hosts the new job — a PR-only workflow never emits the check-run on `main` and leaves the board cell empty
- The hardened workflow you are adding to has policy-guard jobs (e.g. a `forbid-suppressions` job rejecting `|| true`, `continue-on-error: true`, `::warning::`)
- You must sync every documented home of the required-check list and sequence branch-protection registration of the new context (post-merge, never in the same PR)

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

# 5. Category "seems N/A"? Fetch the convention doc FIRST — the definition usually admits a real artifact
#    (Odysseus defines `package` as "sdist/wheel, container image, or release archive")
# 6. Find the nearest sibling repo's canonical job shape via org-wide code search
gh api "search/code?q=org:<org>+package+in:file+filename:_required.yml"

# 7. Before adding a job to a hardened workflow, read its policy-guard jobs
grep -n "forbid-suppressions\|continue-on-error\|::warning::" .github/workflows/_required.yml

# 8. Deterministic tar for a manifest/dataset release archive (GNU tar; ubuntu-latest OK, BSD tar fails)
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-01-01 00:00:00Z' \
  -czf dist/<project>-<version>.tar.gz agents/ fleets/ schemas/
( cd dist && sha256sum *.tar.gz > SHA256SUMS )
```

### Detailed Steps

1. **Decide the distribution model from repo evidence, not the check's name.** If the repo is a data/skills marketplace (content = markdown + JSON, Python is repo tooling only), define `package` as the bundle artifact: a versioned tarball of the content dirs (e.g. `.claude-plugin/`, `skills/`, `plugins/`, `schemas/`, `templates/`). Adding a build backend to ship tooling scripts to a registry nobody publishes to violates YAGNI/KISS.

2. **Library-first: build + verify logic lives in a tested script, the CI job is a thin invocation.** `build_package(repo_root, output_dir) -> Path` plus a read-only `verify_package(tarball) -> list[str]` that re-opens the artifact and checks required members (marketplace.json present AND parseable, at least one `skills/*.md`). If the repo lints/type-checks `scripts/` and `tests/` already, the new files enter the existing gates with zero config changes.

3. **Verify job-emission wiring before mirroring.** If the repo duplicates jobs across a directly-triggered workflow (`on: pull_request/push`) and a `workflow_call` file, grep for the caller (`uses: ./.github/workflows/<file>.yml`) before claiming the mirrored job emits a check-run. A `workflow_call` file with no caller emits nothing — the mirror is dead code and the plan must say so or drop it.

4. **Fetch the external convention doc the issue cites.** Exact requirements (must the check upload an artifact? is `twine check` semantics expected? exact check-run name casing?) come from the convention doc, not the issue's paraphrase. If unfetchable at planning time, list it explicitly as an unverified assumption for the reviewer.

5. **Honor repo-local CI constraints when authoring the job**: pinned action SHAs copied from existing jobs, no `|| true` / `continue-on-error` (repos may have a forbid-suppressions gate), yamllint line-length limits, canonical-check comment pattern matching the existing aggregate `test` job.

6. **Give the script collision-free exit codes** (0 built+verified, 1 build/verify failure, argparse's own 2 for usage errors) and one dedicated negative test per verify error kind, plus a real-repo ships-green test so the new gate is green on the current tree.

### Variant: manifest/dataset repo with a hardened workflow (Myrmidons #749, v1.1.0)

7. **When the category "seems N/A", fetch the convention doc FIRST.** The Odysseus `docs/ci-naming-convention.md` defines `package` as "sdist/wheel, container image, **or release archive**" — a dataset repo's release archive (tar.gz of `agents/` + `fleets/` + `schemas/` with SHA256SUMS) is a REAL distributable, not a fabricated job. The doc simultaneously forbids fabricating passing jobs and provides NO N/A-marker mechanism (the board is generated from live check-runs on `main`), so an issue's "document as N/A" option is usually a dead end — the only way to fill the board cell is a real check-run with the exact canonical name.

8. **Check-run name = the job's `name:` field, and the board needs it on `main`.** Put the job in a workflow that triggers on BOTH `pull_request` and `push: branches: [main]` (Myrmidons `_required.yml` already does). A PR-only workflow (e.g. `validate.yml`) never emits the check-run on `main` and leaves the board cell empty forever.

9. **Mirror the nearest sibling repo's canonical job shape.** Find precedent via org-wide code search: `gh api "search/code?q=org:<org>+package+in:file+filename:_required.yml"`, then fetch the sibling's job. ProjectHermes's `package` job: `needs: build`, validates the artifact the build produced, SHA-pinned `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1`, `if-no-files-found: error`.

10. **Give the packaging job real teeth** — this is what separates a genuine `package` check from a fabricated green job: deterministic tar (`--sort=name --owner=0 --group=0 --numeric-owner --mtime=<fixed>`), SHA256SUMS, a round-trip verify step (`tar -x` to a mktemp dir + `diff -r` per top-level dir + non-zero file-count assertion + `sha256sum --check`), and artifact upload with `if-no-files-found: error`.

11. **Read the hardened workflow's policy-guard jobs before adding anything.** Myrmidons `_required.yml` has a `forbid-suppressions` job rejecting `|| true`, `continue-on-error: true`, and `::warning::` in workflow files — a new job using any of those would fail CI. `::error::` is permitted.

12. **Sync all documented homes of the required-check list and sequence registration post-merge.** Update the `docs/branch-protection.md` table + full-restore contexts + an idempotent incremental snippet (`jq '.contexts += ["package"] | .contexts |= unique'`) and the CLAUDE.md CI/CD job list. Branch-protection registration is a manual post-merge admin step — registering a required context before the job exists on `main` would block every merge, including the PR that introduces the job.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Option 1: make pyproject pip-buildable | Considered adding `[build-system]` + explicit packages to run `python -m build` + `twine check` | Flat layout with `skills/ plugins/ schemas/ templates/` top-level dirs breaks auto-discovery; the only Python is repo tooling under `scripts/`; the existing `submit-pypi` check is dependency-graph auto-submission, not a publish path — nothing would ever consume the wheel | Define the canonical check around the repo's REAL distributable; do not force-fit a library build onto a data repo |
| Inline tar command in the workflow YAML | Considered `tar czf dist/... .claude-plugin skills ...` directly in the job step | Untestable, no verify step, invisible to ruff/mypy/pytest; violates the library-first executable-convention-guard pattern | Build+verify logic goes in a tested script; the CI job stays a one-line invocation |
| `tomllib` for version parsing | Considered `tomllib.load()` to read `[project] version` | `tomllib` is Python 3.11+ but the repo declares `requires-python = ">=3.9"` — the script would break for local 3.9/3.10 users even though CI pins 3.11 | Regex-parse the version line (or read from a format available at the floor version); match the repo's declared floor, not CI's pin |
| Mirroring the job into `_checks.yml` without verifying its caller | Plan mirrors the `package` job into a `workflow_call` file because every other job is duplicated there | No caller of `_checks.yml` was ever verified by grep — if nothing calls it, the mirrored job emits no check-run and the "mirror" rationale is cargo-culting an existing (possibly dead) pattern | Grep for `uses: ./.github/workflows/<file>.yml` BEFORE citing job mirroring as load-bearing; flag it as an assumption otherwise |
| Trusting the issue's paraphrase of the convention doc | Planned `package` semantics from the issue body's summary of Odysseus `ci-naming-convention.md` | The doc itself was never fetched; exact requirements (artifact upload mandatory? naming casing? verify semantics?) are unconfirmed | External convention docs must be fetched during planning, or explicitly listed as unverified inputs for the reviewer |
| Documenting `package` as N/A (Myrmidons #749 issue option 2) | Considered closing the board gap by documenting the category as not-applicable for a manifest repo | Convention doc has no N/A marker; board is generated from live check-runs on `main`; the cell would point at an open issue forever | Fetch the convention doc before assuming a category is inapplicable — the definition (e.g. "release archive") usually admits a real artifact |
| Adding the job to a PR-only workflow (`validate.yml`) | Considered hosting the new `package` job in the existing PR validation workflow | It only triggers on `pull_request`, so no check-run ever appears on `main` and the board badge stays empty | The board reads check-runs on `main`; the job must live in a push+PR workflow (e.g. `_required.yml`) |
| Registering `package` in branch protection in the same PR | Considered adding the new context to required status checks alongside the job-introducing PR | The context would be required before any run of the job exists on `main`, blocking the very PR that introduces it | Branch-protection registration is a manual post-merge admin step |

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

### Canonical `package` job for a manifest/dataset repo — deterministic release archive (Myrmidons #749, v1.1.0)

```yaml
  package:
    name: package
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@<same-pinned-sha-as-sibling-jobs>
      - name: Build release archive (deterministic)
        run: |
          mkdir -p dist
          tar --sort=name --owner=0 --group=0 --numeric-owner \
            --mtime='2026-01-01 00:00:00Z' \
            -czf "dist/${PROJECT}-${VERSION}.tar.gz" agents/ fleets/ schemas/
          ( cd dist && sha256sum ./*.tar.gz > SHA256SUMS )
      - name: Round-trip verify
        run: |
          tmp="$(mktemp -d)"
          tar -xzf dist/*.tar.gz -C "$tmp"
          for d in agents fleets schemas; do diff -r "$d" "$tmp/$d"; done
          count="$(find "$tmp" -type f | wc -l)"
          [ "$count" -gt 0 ] || { echo "::error::empty archive"; exit 1; }
          ( cd dist && sha256sum --check SHA256SUMS )
      - name: Upload package artifact
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: <project>-package
          path: dist/
          if-no-files-found: error
```

### Risks & uncertain assumptions (v1.1.0 additions — Myrmidons plan, unexecuted)

- Odysseus convention doc and ProjectHermes workflow were fetched live at plan time (2026-07-03) and can drift
- The `actions/upload-artifact` SHA pin was copied from ProjectHermes, not independently verified against the upstream release tag
- Deterministic-tar flags are GNU-tar-specific (fine on ubuntu-latest runners; fails on BSD tar)
- Plan not executed: no local or CI validation of the job YAML has run

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Mnemosyne | Issue #2911 planning (plan-only, not yet implemented) | Plan posted to the issue; implementation PR pending |
| HomericIntelligence/Myrmidons | Issue #749 planning — canonical `package` check via deterministic release archive in `_required.yml` (plan-only, nothing executed) | unverified — Odysseus convention doc + ProjectHermes precedent fetched live 2026-07-03; branch-protection registration sequenced post-merge |
