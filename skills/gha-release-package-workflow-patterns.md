---
name: gha-release-package-workflow-patterns
description: "Use when: (1) creating a tag-triggered release workflow with keepachangelog CHANGELOG format and semver version consistency checks across manifests, (2) implementing automated package building via GitHub Actions with artifact publication and GitHub Release creation, (3) cutting a protected-branch release through a merge queue and proving the remote signed tag and published assets, (4) adding pre-commit script validation of Python version drift between pyproject.toml classifiers and Dockerfile FROM line, (5) adding CI steps that replace fragile shell printf emoji byte-escape encoding with dedicated Python scripts for better portability."
category: ci-cd
date: 2026-07-17
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: gha-release-package-workflow-patterns.history
tags:
  - github-actions
  - releases
  - keepachangelog
  - semver
  - git-tags
  - version-consistency
  - version-drift
  - pre-commit
  - ci-portability
  - release-automation
  - package-publishing
  - merge-queue
  - protected-main
---

# GitHub Actions Release and Package Workflow Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-17 |
| **Objective** | Capture reusable GitHub Actions patterns for release and packaging automation: tag-triggered release workflows with cross-manifest semver consistency, package building with artifact publication and GitHub Release creation, and the protected-branch operational release path from a manifest-bump PR through merge-queue validation, signed-tag verification, and release-asset readback. |
| **Outcome** | Operational across multiple repos — release.yml validates tag/manifest consistency before publishing; version-drift checks block silent mismatches; printf-emoji removal makes report-building locale-independent. Athena v0.3.0 additionally proved the protected-branch path end-to-end: required PR gate, synthetic merge-group gate, signed annotated tag on the merged commit, GitHub verification, and six release assets. |
| **Verification** | verified-ci (the v1.2.0 footer-bleed fixture remains verified-local) |

## When to Use

- Project is ready for its first (or next) pinnable versioned release with a semver git tag (`v1.0.0`+).
- CHANGELOG must transition from aspirational to dated release sections with the `[Unreleased]` convention.
- CI must fail closed when a git tag does not match the version declared in all manifests (`pixi.toml`, `pyproject.toml`, `dagger/package.json`, etc.).
- Release artifacts / packages need to be built and published to GitHub Releases on tag push.
- A repository uses protected `main` and a merge queue, so a release tag must point to the **queue-merged** commit rather than a PR head SHA.
- You need auditable proof that a release tag is annotated, GitHub-verified, targets protected `main`, and that the release actually contains its expected archive, SBOM, and checksum artifacts.
- You are adding a Python version classifier to `pyproject.toml` and want to guard against the Dockerfile `FROM python:X.Y` line silently drifting.
- A GitHub Actions workflow embeds emoji via `printf '\xf0\x9f...'` byte escapes in report-building steps and needs to be made locale/shell-independent.
- A pre-commit hook should guard `pyproject.toml`, `docker/Dockerfile`, or version-bearing manifest changes before they reach `main`.

## Verified Workflow

### Quick Reference

| Goal | Mechanism | Fail-closed check |
| ---- | --------- | ----------------- |
| Tag-triggered release | `.github/workflows/release.yml` on `push.tags: v[0-9]+.[0-9]+.[0-9]+` | Tag must match `^v[0-9]+\.[0-9]+\.[0-9]+$` (no pre-release/build suffix) |
| Manifest version consistency | `scripts/check_version_consistency.py` (pre-commit + release.yml) | All manifests + CHANGELOG agree on version |
| CHANGELOG format | keepachangelog: `[Unreleased]` + `## [X.Y.Z] - YYYY-MM-DD` | release.yml requires both sections present |
| Package publish | `softprops/action-gh-release` after `validate` job | `publish` job `needs: validate` |
| Release notes body | Python step regexes the dated CHANGELOG section into `RELEASE_NOTES` (end-anchor stops at next `## [`, the link-ref footer, or EOF) | `body: ${{ steps.notes.outputs.RELEASE_NOTES }}` (empty body = missing step; footer in body = missing `\n\[[^\]]+\]: ` anchor) |
| Signed release tag | `git tag -s -a vX.Y.Z` + `git log --format='%h %G? %s'` | Every line shows `G` (good signature) |
| Protected-branch release | Merge a signed manifest-bump PR through the queue; tag detached `origin/main` only after its `merge_group` run succeeds | The release tag points at the queue-merged commit, not the unmerged PR head |
| Remote tag trust | GitHub `git/ref/tags` then `git/tags/<tag-object-sha>` API readback | `object.type == tag`, `verification.verified == true`, and `object.sha` is the intended `main` commit |
| Published-release readback | `gh release view vX.Y.Z --json tagName,isDraft,isPrerelease,assets` | Non-draft, non-prerelease release with every expected archive/SBOM/checksum asset |
| Python version drift | `scripts/check_python_version_consistency.py` | Highest `pyproject.toml` classifier == Dockerfile `FROM python:X.Y` |
| CI emoji portability | `scripts/build_<report>.py` Python script | pytest asserts `b"\xf0\x9f"` not in output |

**Strict semver tag regex (no pre-release or build suffixes):**

```text
^v[0-9]+\.[0-9]+\.[0-9]+$
```

Right: `v1.0.0`, `v0.1.0`, `v2.1.3`. Wrong: `v1.0.0-alpha`, `v1.0.0+build`, `1.0.0`, `version-1.0.0`.

**Implementation order for a first release (do not skip):**

1. Create/update `CHANGELOG.md` (keepachangelog: `[Unreleased]` + dated sections).
2. Write bash regression tests for tag format, manifest consistency, dispatch contract.
3. Create `release.yml` triggered on semver tags; validate then publish.
4. Place bash regression tests in a dedicated job (NOT the lint job).
5. Add pre-commit hooks: signed commits + version consistency.
6. Integration-test locally before opening the PR.

### Detailed Steps

#### A. Tag-triggered release workflow with CHANGELOG + manifest consistency

**1. CHANGELOG.md in keepachangelog format**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added

- Feature X

### Fixed

- Bug Y

## [0.1.0] - 2026-06-03

### Added

- Initial release with pipeline primitives: build(), test(), lint()
- Cross-repo dispatch via GitHub Actions

### Fixed

- Cross-repo dispatch payload contract validation (#15, #84)

[Unreleased]: https://github.com/OWNER/REPO/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/OWNER/REPO/releases/tag/v0.1.0
```

Rules: top section is always `## [Unreleased]` (exact case); dated releases use `## [X.Y.Z] - YYYY-MM-DD` with **no** `v` prefix in the header; keep the format strict because `release.yml` parses it with regex.

**2. Bash regression tests (`tests/dispatch-apply.test.sh`)**

```bash
#!/usr/bin/env bash
set -euo pipefail
test_count=0; pass_count=0

test_semver_tag_format() {
  if [[ $1 =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "PASS: Tag '$1' matches semver format"; ((pass_count++))
  else echo "FAIL: Tag '$1' bad format"; fi
  ((test_count++))
}

test_changelog_structure() {
  if grep -q "^## \[Unreleased\]$" CHANGELOG.md; then
    echo "PASS: CHANGELOG has [Unreleased]"; ((pass_count++))
  else echo "FAIL: missing [Unreleased]"; fi
  ((test_count++))
}

test_version_consistency() {
  local v="$1"
  grep -q "^version = \"${v}\"" pixi.toml && { echo "PASS: pixi.toml $v"; ((pass_count++)); } || echo "FAIL: pixi.toml"
  grep -q "\"version\": \"${v}\"" dagger/package.json && { echo "PASS: package.json $v"; ((pass_count++)); } || echo "FAIL: package.json"
  ((test_count += 2))
}

echo "=== version/dispatch regression tests ==="
test_semver_tag_format "v0.1.0"
test_changelog_structure
test_version_consistency "0.1.0"
echo ""; echo "Results: ${pass_count}/${test_count} tests passed"
[ "$pass_count" -eq "$test_count" ] || exit 1
```

**3. release.yml (validate → publish)**

```yaml
name: Release

on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'

permissions:
  contents: write

jobs:
  validate:
    name: validate-release-assets
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Extract version from git tag
        id: tag
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          echo "tag=${TAG}" >> "$GITHUB_OUTPUT"
          echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"
      - name: Validate semver tag format
        run: |
          TAG="${{ steps.tag.outputs.tag }}"
          [[ $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "::error::Tag '$TAG' not strict semver"; exit 1; }
      - name: Validate pixi.toml version matches tag
        run: |
          V="${{ steps.tag.outputs.version }}"
          P=$(grep '^version = ' pixi.toml | cut -d'"' -f2)
          [ "$P" = "$V" ] || { echo "::error::pixi.toml '$P' != tag '$V'"; exit 1; }
      - name: Validate CHANGELOG has dated + Unreleased sections
        run: |
          V="${{ steps.tag.outputs.version }}"
          grep -q "^## \[$V\] - [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}$" CHANGELOG.md || { echo "::error::missing dated section"; exit 1; }
          grep -q "^## \[Unreleased\]$" CHANGELOG.md || { echo "::error::missing [Unreleased]"; exit 1; }
      - name: Run regression tests
        run: bash tests/dispatch-apply.test.sh

  publish:
    name: publish-release
    runs-on: ubuntu-24.04
    needs: validate
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Extract version from git tag
        id: tag
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          echo "tag=${TAG}" >> "$GITHUB_OUTPUT"
          echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"
      - name: Extract release notes from CHANGELOG
        id: notes
        env:
          VERSION: ${{ steps.tag.outputs.version }}
        run: |
          python3 << 'EOF'
          import os
          import re

          version = os.environ["VERSION"]
          with open("CHANGELOG.md", "r", encoding="utf-8") as f:
              content = f.read()
          # Match "## [X.Y.Z] - YYYY-MM-DD" up to the next "## [" header, the first
          # keepachangelog link-reference footer line, or EOF. The `\n\[[^\]]+\]: `
          # alternative is REQUIRED: for the top/most-recent dated section there is no
          # next "## [" below it, only the link-reference footer
          # ([Unreleased]: .../compare/..., [X.Y.Z]: .../releases/tag/...), so without it
          # `.*?` (re.DOTALL) runs to EOF and bleeds those footer lines into the body.
          pattern = rf"## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n(.*?)(?=\n## \[|\n\[[^\]]+\]: |$)"
          match = re.search(pattern, content, re.DOTALL)
          if not match:
              print("::error::Could not extract release notes for version", version)
              raise SystemExit(1)
          notes = match.group(1).strip()
          # Escape for the GitHub Actions step output (single-line set).
          notes = notes.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
          with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
              out.write(f"RELEASE_NOTES={notes}\n")
          EOF
      - name: Create GitHub Release
        uses: softprops/action-gh-release@de2c0eb89ae2a093876385947365ece477b33038  # v0.1.15
        with:
          tag_name: ${{ steps.tag.outputs.tag }}
          body: ${{ steps.notes.outputs.RELEASE_NOTES }}
          draft: false
          prerelease: false
```

The release-notes extraction step is what wires the CHANGELOG into the release `body`. Without
it the `Create GitHub Release` step publishes an **empty** release. Key details:

- **Regex** `## \[VERSION\] - \d{4}-\d{2}-\d{2}\n(.*?)(?=\n## \[|\n\[[^\]]+\]: |$)` with
  `re.DOTALL` so `.` spans newlines; capture group 1 is everything between this version header
  and the next `## [` header, the first keepachangelog link-reference footer line, or EOF.
  `re.escape(version)` guards the dotted version. The `\n\[[^\]]+\]: ` alternative in the
  end-anchor is **required** to stop footer-bleed: the top/most-recent dated section (the common
  case — you just promoted `[Unreleased]` to vX.Y.Z) has no next `## [` below it, only the
  link-reference footer, so without it `.*?` runs to EOF and the published body absorbs
  `[Unreleased]: .../compare/...` and `[X.Y.Z]: .../releases/tag/...`.
- **GitHub-output escaping**: `%`→`%25`, `\n`→`%0A`, `\r`→`%0D` (escape `%` first so the
  later replacements are not double-escaped). This lets a multi-line CHANGELOG section survive a
  single-line `>> "$GITHUB_OUTPUT"` write.
- **Wiring**: `body: ${{ steps.notes.outputs.RELEASE_NOTES }}` on the release-create step.

**4. Keep bash regression tests in a dedicated job** (not lint — lint is static analysis; bash tests are runtime/regression):

```yaml
dispatch-contract-test:
  name: dispatch-contract-test
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
    - run: bash tests/dispatch-apply.test.sh
```

**5. Pre-commit: signed commits + version consistency**

```yaml
- repo: https://github.com/mattlqx/pre-commit-sign
  rev: v1.1.4
  hooks:
    - id: sign-commit
      stages: [commit]

- repo: local
  hooks:
    - id: version-consistency-check
      name: version-consistency-check
      entry: python3 scripts/check_version_consistency.py
      language: python
      files: ^(pixi\.toml|dagger/package\.json|CHANGELOG\.md)$
      pass_filenames: false
      stages: [commit]
```

`scripts/check_version_consistency.py` reads each manifest (`tomllib` for TOML, `json` for package.json, regex for the first dated CHANGELOG section), filters out absent optional files, and exits non-zero if the surviving set has more than one distinct version.

**6. Create the release tag *signed*, then verify the signature**

Branch protection and the `mattlqx/pre-commit-sign` hook only cover commits — the release **tag**
must also be signed, or the published release cannot be verified for authorship. Use `-s` (sign;
it creates an annotated tag):

```bash
git tag -s v0.1.0 -m "Release v0.1.0: initial versioned release"
git push origin v0.1.0
```

Verify the tag (and recent commits) carry a good signature before pushing:

```bash
git log --format='%h %G? %s' | head -10
# Every line must show 'G' (good signature); 'N' (not signed) or 'B' (bad) blocks the release.
```

`%G?` legend: `G` good, `B` bad, `U` good-but-unknown-validity, `N` no signature, `E` cannot
check. Treat anything other than `G` as a failed release gate.

#### A.7 Protected-branch release: merge queue, signed tag, and remote readback

For a protected repository, the release is an operational sequence, not just a `git tag` command.
Prepare the version values in **every shipped host manifest** on a signed, DCO-attested PR. Let
the current-head required gate pass, enqueue it, and wait for a successful `merge_group` run.
Only then fetch `main` and tag the queue-created commit. Do not tag the PR head: queue integration
can create a distinct SHA.

```bash
# After the release-preparation PR has merged through the queue:
git fetch origin main
git switch --detach origin/main
git status --short                         # expected: no output

# Verify each release contract's source of truth before creating an irreversible tag.
git show origin/main:.claude-plugin/plugin.json
git show origin/main:.claude-plugin/marketplace.json
git show origin/main:.codex-plugin/plugin.json

# `-s` produces an annotated signed tag; explicitly name the verified main SHA.
git tag -s vX.Y.Z -m "Project vX.Y.Z" origin/main
git verify-tag --raw vX.Y.Z
git push origin vX.Y.Z

# GitHub must confirm this is an annotated tag whose signature is valid and whose
# target is the intended queue-merged main commit.
gh api repos/OWNER/REPO/git/ref/tags/vX.Y.Z
gh api repos/OWNER/REPO/git/tags/<tag-object-sha>

# Watch the tag-triggered workflow, then read back the published release and its assets.
gh run watch <release-run-id> --repo OWNER/REPO --exit-status
gh release view vX.Y.Z --repo OWNER/REPO --json tagName,targetCommitish,isDraft,isPrerelease,url,assets
```

The second API response must report `verification.verified: true`; its embedded `object.sha`
must be the queue-merged `main` commit (not the annotated tag object SHA). The release readback
must show `isDraft: false`, `isPrerelease: false`, and every expected archive/SBOM/checksum.

If the release reuses a required workflow that consults issue-backed policy, grant its **caller**
job the required read permission (for example, `issues: read`). A reusable workflow cannot elevate
the caller token, so permissions declared only in the callee cannot repair a tag-time failure.

#### B. Python version drift detection (pyproject.toml ↔ Dockerfile)

Create `scripts/check_python_version_consistency.py` — stdlib-only, numeric tuple comparison, regex that survives `slim`/`alpine`/digest-pinned/multi-stage `FROM` lines:

```python
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

_DOCKERFILE_FROM_RE = re.compile(r"^\s*FROM\s+python:(\d+\.\d+)", re.IGNORECASE | re.MULTILINE)
_CLASSIFIER_VERSION_RE = re.compile(r"Programming Language :: Python :: (\d+\.\d+)$")
```

Key rules: compare versions as `(3, 10)` tuples (string sort wrongly ranks `"3.9" > "3.10"`); compare the **highest** classifier to the Dockerfile, not any classifier; exit 1 on missing/malformed files. Add the pre-commit hook and a CI step:

```yaml
# .pre-commit-config.yaml
- id: check-python-version-consistency
  name: Check Python Version Consistency
  entry: pixi run python scripts/check_python_version_consistency.py
  language: system
  files: ^(pyproject\.toml|docker/Dockerfile)$
  pass_filenames: false
```

```yaml
# .github/workflows/test.yml — place BEFORE "Install pixi" (stdlib-only, system Python is enough)
- name: Check Python version consistency (pyproject.toml vs Dockerfile)
  run: python3 scripts/check_python_version_consistency.py
```

#### C. CI portability: replace printf emoji byte-escapes with a Python script

Replace fragile shell `printf '\xf0\x9f...'` report-builders with a dedicated script invoked from a single `run:` line. Also fix any `comment-marker:` YAML field that uses the same emoji (e.g. `\U0001F4CA`) — set it to plain ASCII so it matches the new header.

```python
#!/usr/bin/env python3
"""Build PR comment markdown from input content."""
import argparse
import sys
from pathlib import Path

HEADER = "## Report Title\n\n"
FOOTER = "\n\n---\n*Footer note*\n"


def build_comment(input_file: Path, output_file: Path) -> int:
    if not input_file.exists():
        print(f"Error: input file not found: {input_file}", file=sys.stderr)
        return 1
    output_file.write_text(HEADER + input_file.read_text(encoding="utf-8") + FOOTER, encoding="utf-8")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-file", required=True, type=Path)
    p.add_argument("--output-file", required=True, type=Path)
    a = p.parse_args()
    return build_comment(a.input_file, a.output_file)


if __name__ == "__main__":
    sys.exit(main())
```

```yaml
# Before (fragile):
- name: Build report
  run: |
    {
      printf '## \xf0\x9f\x93\x8a Report Title\n\n'
      cat input.md
      printf '\n\n---\n*Footer*\n'
    } > output.md

# After (robust):
- name: Build report
  run: python scripts/build_report.py --input-file input.md --output-file output.md
```

A pytest guard asserts the bytes are gone: `assert b"\xf0\x9f" not in out.read_bytes()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Mixing bash regression tests with the lint job | Added `run: bash tests/...` inside the lint job | Lint runs static analyzers (shellcheck, yamllint); runtime behavior tests belong elsewhere — mixing obscures job purpose | Create a dedicated `dispatch-contract-test` job; keep lint for static analysis only |
| Using hatch-vcs for polyglot auto-versioning | Added hatch-vcs to auto-version from git tags across `pixi.toml` + `dagger/package.json` | hatch-vcs is Python-only; it cannot version the Node `package.json` | For polyglot repos use a manual semver validation workflow that checks all language stacks |
| Tags via `git tag -a` without enforced signing | Created release tags unsigned | Unsigned tags bypass branch protection and cannot be verified for authorship | Enforce GPG/SSH signing via `mattlqx/pre-commit-sign`; reject unsigned commits on push to main |
| Version in PR title instead of body | Used "feat: v0.1.0 release" as the PR title | GitHub `Closes #N` only links from the PR body, not the title — the issue did not auto-close | Put `Closes #N` on its own line in the PR body |
| CHANGELOG with only `[Unreleased]` | Skipped dated historical sections | release.yml has no version section to validate or extract notes from | Always add `## [X.Y.Z] - YYYY-MM-DD` for each release; keep `[Unreleased]` at the top |
| String-sorting Python versions | Compared classifier vs Dockerfile versions as strings | `"3.9" > "3.10"` by string sort — picks the wrong "highest" | Compare as numeric tuples: `(3, 9) < (3, 10)` |
| Committing the new Python script once | Staged all files and ran `git commit` | ruff-format/ruff-check modified files and aborted the first commit (and an SQLite pre-commit lock briefly blocked the retry) | Re-stage the linter-modified files and commit again; retry clears the transient lock |
| Leaving emoji in `comment-marker` YAML | Kept `"\U0001F4CA Test Metrics Report"` while making the file body plain text | The marker locates existing bot comments; a unicode escape is inconsistent with the new plain header | Set the marker to plain ASCII to match the script's header string |
| Release published with empty notes | Wired only `tag_name` into `action-gh-release` and assumed it would pull notes from the CHANGELOG automatically | `softprops/action-gh-release` does not read CHANGELOG.md — with no `body`, the release notes are blank | Add an explicit extraction step (regex the dated section, escape `%`/`\n`/`\r` for `$GITHUB_OUTPUT`) and wire `body: ${{ steps.notes.outputs.RELEASE_NOTES }}` |
| Pushing an unsigned (or lightweight) release tag | Ran `git tag v0.1.0` / `git tag -a v0.1.0` and pushed | The tag had no signature, so authorship could not be verified and `%G?` showed `N` | Sign the tag with `git tag -s vX.Y.Z -m "..."` and gate the release on `git log --format='%h %G? %s'` showing `G` |
| Tagging the release-preparation PR head | Treated the signed PR commit as the release commit before it passed the merge queue | A merge queue validates and lands a synthetic integration commit; the tag would not identify the exact protected-main commit that passed merge-group checks | Wait for PR merge, fetch `origin/main`, detach at that SHA, then create the signed tag there |
| Trusting only local signature output | Ran `git verify-tag` and assumed the remote tag object had the same target and verification result | Local success does not prove the pushed ref is annotated, GitHub accepted the signature, or the tag points at the merged commit | Read back `git/ref/tags` and `git/tags/<tag-object-sha>`; require `type: tag`, `verification.verified: true`, and the expected commit SHA |
| Omitting caller `issues: read` from a reusable release gate | The called required-check workflow read an active issue-backed vulnerability exception, but its release caller supplied only `contents: read` | Reusable workflows cannot raise their caller's token permissions, so the tag workflow fails before publication | Declare every required read scope, including `issues: read`, on the caller job and cover the workflow contract with a regression test |
| Release notes absorbed the CHANGELOG link-footer | Extracted the dated section with end-anchor `(?=\n## \[\|$)` | For the top/most-recent dated section there is no next `## [` below it — only the keepachangelog link-reference footer — so `.*?` (re.DOTALL) ran to EOF and pulled `[Unreleased]: …/compare/…` and `[X.Y.Z]: …/releases/tag/…` into the published release body (verified-local: synthetic top-section fixture, old anchor → footer in body) | Extend the end-anchor to also stop at the first link-reference line: `(?=\n## \[\|\n\[[^\]]+\]: \|$)`; prove it with a synthetic top-section CHANGELOG fixture asserting `compare/`/`releases/tag/` are absent from the body |

## Results & Parameters

**Bash regression test expected output:**

```text
=== version/dispatch regression tests ===
PASS: Tag 'v0.1.0' matches semver format
PASS: CHANGELOG has [Unreleased]
PASS: pixi.toml 0.1.0
PASS: package.json 0.1.0
Results: 4/4 tests passed
```

**Manifest version locations:**

| Manifest | Pattern | Example |
| --------- | --------- | --------- |
| pixi.toml | `^version = "X.Y.Z"$` | `version = "0.1.0"` |
| dagger/package.json | `"version": "X.Y.Z"` | `"version": "0.1.0"` |
| CHANGELOG.md | `## [X.Y.Z] - YYYY-MM-DD` | `## [0.1.0] - 2026-06-03` |

**Python version drift script invocation:**

```bash
python3 scripts/check_python_version_consistency.py            # exit 0 match / 1 mismatch
python3 scripts/check_python_version_consistency.py --verbose  # show parsed versions
python3 scripts/check_python_version_consistency.py --repo-root /path/to/repo
```

Regex patterns: `r"^\s*FROM\s+python:(\d+\.\d+)"` (IGNORECASE | MULTILINE) and `r"Programming Language :: Python :: (\d+\.\d+)$"`. Verified with 31 unit tests across 3 classes (classifier parsing, Dockerfile parsing, consistency check).

**release.yml execution flow on `git push origin v0.1.0`:** GitHub detects the tag → `validate` job extracts version, checks tag format, verifies all manifests + CHANGELOG agree, runs regression tests → on success `publish` job creates the GitHub Release with notes from the CHANGELOG section → any failure stops the workflow.

**Protected-main release evidence (verified-ci):** Athena v0.3.0 used a signed manifest PR
([#46](https://github.com/HomericIntelligence/Athena/pull/46)) that passed the required PR gate
and merge-group run before landing at `03590735aad37a2a97fe3a73278aa01a87022ed9`. Annotated tag
object `2ed1659decd9458a9016b92f8a44227cbb991181` was GitHub-verified and targets that commit. The
tag-triggered [Release run](https://github.com/HomericIntelligence/Athena/actions/runs/29613538587)
passed trust verification, reusable required checks, package/SBOM generation, and publication.
The release readback returned six uploaded assets: the plugin archive plus checksum and two SBOM
formats plus their checksums.

**Release-notes footer-bleed guard (verified-local):**

The end-anchor must stop at the keepachangelog link-reference footer, not just the next `## [`
header or EOF. The dangerous case is the **topmost** dated section (you just promoted
`[Unreleased]` to vX.Y.Z), which sits directly above the footer with no `## [` below it. Prove
the fix with a synthetic CHANGELOG fixture where the dated section is topmost and assert the
footer URLs do not bleed into the extracted body:

```python
import re

def extract_notes(content: str, version: str) -> str:
    # Note the `\n\[[^\]]+\]: ` alternative — without it the top section bleeds the footer.
    pattern = rf"## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n(.*?)(?=\n## \[|\n\[[^\]]+\]: |$)"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(1).strip()

def test_release_notes_no_footer_bleed() -> None:
    # Dated section is TOPMOST; link-reference footer directly below it.
    changelog = (
        "# Changelog\n\n"
        "## [1.2.0] - 2026-06-20\n\n"
        "### Added\n\n- Footer-bleed fix\n- Another bullet\n\n"
        "[Unreleased]: https://github.com/OWNER/REPO/compare/v1.2.0...HEAD\n"
        "[1.2.0]: https://github.com/OWNER/REPO/releases/tag/v1.2.0\n"
    )
    body = extract_notes(changelog, "1.2.0")
    assert "compare/" not in body       # [Unreleased] footer must not bleed in
    assert "releases/tag/" not in body  # [X.Y.Z] footer must not bleed in
    assert body.endswith("- Another bullet")  # stops at the last bullet
```

With the old `(?=\n## \[|$)` anchor this test fails (both footer lines land in `body`); with the
`\n\[[^\]]+\]: ` alternative added it passes.

**Emoji-removal test:**

```python
def test_no_emoji_byte_escapes(tmp_path: Path) -> None:
    metrics = tmp_path / "in.md"; metrics.write_text("data\n", encoding="utf-8")
    out = tmp_path / "out.md"
    build_comment(metrics, out)
    assert b"\xf0\x9f" not in out.read_bytes()
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectProteus | Issue #101 — first v0.1.0 release (commit 1c04a4a) | release.yml validates tag/manifest/CHANGELOG consistency; dispatch-contract-test job runs bash regression tests |
| ProjectScylla | Issue #1168 / PR #1292 (follow-up from #1118) | Python version drift check; 31 new tests, 3615 total project tests passed |
| ProjectOdyssey | Issue #3345 / PR #3977 | Replaced coverage.yml printf emoji byte-escape with `scripts/build_pr_comment.py`; 4 tests passed |
| Athena | v0.3.0 / PR #46 | Protected-main release: signed manifest PR → successful merge group → signed annotated tag targeting `0359073` → GitHub signature verification → successful release with archive, SBOMs, and checksums |
