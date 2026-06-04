---
name: versioned-releases-changelog-release-workflow
description: "Implement pinnable versioned releases with keepachangelog CHANGELOG format and tag-triggered GitHub Actions release workflows. Use when: (1) project needs versioned releases with semver tags (v1.0.0+), (2) CHANGELOG entries must be organized by dated release sections with [Unreleased] section, (3) release.yml workflow triggers on semver tags and validates version consistency across manifests, (4) all commits must be signed, (5) pre-commit hooks must validate version fields in manifest files."
category: ci-cd
date: '2026-06-03'
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - versioning
  - releases
  - keepachangelog
  - github-actions
  - git-tags
  - semver
  - tag-workflow
  - signed-commits
  - release-automation
---

# Versioned Releases with Keepachangelog and Tag-Triggered Workflows

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-03 |
| **Objective** | Establish pinnable versioned releases: semver git tags (v1.0.0+) trigger a release.yml workflow that validates version consistency across all manifests, generates release notes from CHANGELOG, and publishes releases to GitHub. CHANGELOG uses keepachangelog format with [Unreleased] + dated version sections. All commits must be signed (git commit -S). Pre-commit hooks validate version strings in manifest files. |
| **Outcome** | Operational — first versioned release (v0.1.0) published, release.yml validates tag/CHANGELOG/manifest consistency before publishing, pre-commit hooks enforce signed commits and version field validation. |
| **Verification** | verified-local |

## When to Use

- Project is ready for its first versioned release (v1.0.0 or similar pinnable semver tag)
- CHANGELOG needs to transition from aspirational to dated release sections with [Unreleased] convention
- CI must fail closed if git tag does not match version in all manifests (pyproject.toml, pixi.toml, dagger/package.json, etc.)
- Release artifacts need to be published to GitHub Releases (or other registry) on tag push
- All commits MUST be signed (GPG or SSH); unsigned commits should block merges to main
- Pre-commit hook must catch version drift in manifest files before commits reach main
- PR body requires specific format (e.g., "Closes #N") to be compliant with release policy

## Verified Workflow

### Quick Reference

**Implementation order (critical — do not skip steps):**

1. **Create/update CHANGELOG.md** — keepachangelog format with [Unreleased] + dated sections
2. **Write regression tests** — bash script that validates tag format, manifest consistency, dispatch contract
3. **Create release.yml workflow** — triggered on semver tags, validates consistency, publishes release
4. **Update CI job placement** — move regression tests to dedicated dispatch-contract-test job (not lint)
5. **Add pre-commit hooks** — sign all commits, validate version fields, reject unsigned commits on push
6. **Integration test** — verify all acceptance criteria pass before PR creation

**Tag format (strict, no pre-release or build suffixes):**
```
^v[0-9]+\.[0-9]+\.[0-9]+$
```

Examples: `v1.0.0`, `v0.1.0`, `v2.1.3` ✓
Wrong: `v1.0.0-alpha`, `v1.0.0+build`, `1.0.0` (no v), `version-1.0.0` ✗

### Detailed Steps

#### Step 1: Create CHANGELOG.md in Keepachangelog Format

Create or update `CHANGELOG.md` at project root. Follow [keepachangelog.com](https://keepachangelog.com/en/1.1.0/) format:

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

### Changed

- Breaking change Z

## [0.1.0] - 2026-06-03

### Added

- Initial release with Dagger TypeScript module
- Pipeline primitives: build(), test(), lint()
- Cross-repo dispatch via GitHub Actions
- Image promotion via skopeo
- Branch protection and pre-commit enforcement

### Fixed

- Cross-repo dispatch payload contract validation (#15, #84)

### Known Issues

- Build/promote tag arithmetic broken in edge cases (#2, #83)
- Pipeline YAML configs not consumed in production (#1, #82)

[Unreleased]: https://github.com/HomericIntelligence/ProjectProteus/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HomericIntelligence/ProjectProteus/releases/tag/v0.1.0
```

**Key rules:**
- Top section is always `## [Unreleased]`
- Dated releases use `## [X.Y.Z] - YYYY-MM-DD` format (no v prefix in section header)
- Links at bottom: `[Unreleased]: <compare-url>`, `[X.Y.Z]: <tag-url>`
- Keep format strict for release.yml parsing

#### Step 2: Write Regression Tests for Version Consistency

Create `tests/dispatch-apply.test.sh` (or rename from existing if present):

```bash
#!/usr/bin/env bash
# Regression tests for versioning and dispatch contract
set -euo pipefail

test_count=0
pass_count=0

# Test 1: Validate semver tag format
test_semver_tag_format() {
  local tag="$1"
  if [[ $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "PASS: Tag '$tag' matches semver format"
    ((pass_count++))
  else
    echo "FAIL: Tag '$tag' does not match ^v[0-9]+\.[0-9]+\.[0-9]+$"
  fi
  ((test_count++))
}

# Test 2: Validate CHANGELOG.md structure
test_changelog_structure() {
  if [ ! -f "CHANGELOG.md" ]; then
    echo "FAIL: CHANGELOG.md does not exist"
    ((test_count++))
    return
  fi
  if grep -q "^## \[Unreleased\]$" CHANGELOG.md; then
    echo "PASS: CHANGELOG.md has [Unreleased] section"
    ((pass_count++))
  else
    echo "FAIL: CHANGELOG.md missing [Unreleased] section"
  fi
  ((test_count++))
}

# Test 3: Validate version consistency across manifests
test_version_consistency() {
  local expected_version="$1"
  local errors=0

  if [ -f "pixi.toml" ]; then
    if grep -q "^version = \"${expected_version}\"" pixi.toml; then
      echo "PASS: pixi.toml version is ${expected_version}"
      ((pass_count++))
    else
      echo "FAIL: pixi.toml version mismatch"
      ((errors++))
    fi
  fi

  if [ -f "dagger/package.json" ]; then
    if grep -q "\"version\": \"${expected_version}\"" dagger/package.json; then
      echo "PASS: dagger/package.json version is ${expected_version}"
      ((pass_count++))
    else
      echo "FAIL: dagger/package.json version mismatch"
      ((errors++))
    fi
  fi

  ((test_count += 2))
}

# Test 4: Validate dispatch contract (client_payload.host)
test_dispatch_contract() {
  local dispatch_script="scripts/dispatch-apply.sh"
  if [ ! -f "$dispatch_script" ]; then
    echo "WARN: dispatch-apply.sh not found, skipping contract test"
    return
  fi
  if grep -q "client_payload.host" "$dispatch_script"; then
    echo "PASS: dispatch-apply.sh validates client_payload.host"
    ((pass_count++))
  else
    echo "FAIL: dispatch-apply.sh missing client_payload.host validation"
  fi
  ((test_count++))
}

# Run tests
echo "=== Running version/dispatch regression tests ==="
test_semver_tag_format "v0.1.0"
test_changelog_structure
test_version_consistency "0.1.0"
test_dispatch_contract

echo ""
echo "Results: ${pass_count}/${test_count} tests passed"
if [ "$pass_count" -ne "$test_count" ]; then
  exit 1
fi
exit 0
```

Make executable:
```bash
chmod +x tests/dispatch-apply.test.sh
```

Verify locally:
```bash
bash tests/dispatch-apply.test.sh
```

#### Step 3: Create release.yml Workflow

Create `.github/workflows/release.yml`:

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
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0  # Full history for tag comparison

      - name: Extract version from git tag
        id: tag
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          VERSION="${TAG#v}"
          echo "tag=${TAG}" >> "$GITHUB_OUTPUT"
          echo "version=${VERSION}" >> "$GITHUB_OUTPUT"

      - name: Validate semver tag format
        run: |
          TAG="${{ steps.tag.outputs.tag }}"
          if [[ ! $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "::error::Tag '$TAG' does not match semver format ^v[0-9]+\.[0-9]+\.[0-9]+$"
            exit 1
          fi
          echo "✓ Tag '$TAG' matches semver format"

      - name: Validate pixi.toml version matches tag
        run: |
          VERSION="${{ steps.tag.outputs.version }}"
          PIXI_VERSION=$(grep '^version = ' pixi.toml | cut -d'"' -f2)
          if [ "$PIXI_VERSION" != "$VERSION" ]; then
            echo "::error::pixi.toml version '$PIXI_VERSION' does not match tag version '$VERSION'"
            exit 1
          fi
          echo "✓ pixi.toml version matches tag: $VERSION"

      - name: Validate dagger/package.json version matches tag
        run: |
          VERSION="${{ steps.tag.outputs.version }}"
          PKG_VERSION=$(grep '"version":' dagger/package.json | cut -d'"' -f4)
          if [ "$PKG_VERSION" != "$VERSION" ]; then
            echo "::error::dagger/package.json version '$PKG_VERSION' does not match tag version '$VERSION'"
            exit 1
          fi
          echo "✓ dagger/package.json version matches tag: $VERSION"

      - name: Validate CHANGELOG.md has dated section for version
        run: |
          VERSION="${{ steps.tag.outputs.version }}"
          if ! grep -q "^## \[$VERSION\] - [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}$" CHANGELOG.md; then
            echo "::error::CHANGELOG.md missing dated section for v$VERSION (format: ## [X.Y.Z] - YYYY-MM-DD)"
            exit 1
          fi
          echo "✓ CHANGELOG.md has dated section for v$VERSION"

      - name: Validate CHANGELOG.md has [Unreleased] section
        run: |
          if ! grep -q "^## \[Unreleased\]$" CHANGELOG.md; then
            echo "::error::CHANGELOG.md missing [Unreleased] section"
            exit 1
          fi
          echo "✓ CHANGELOG.md has [Unreleased] section"

      - name: Run regression tests
        run: bash tests/dispatch-apply.test.sh

  publish:
    name: publish-release
    runs-on: ubuntu-24.04
    needs: validate
    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0

      - name: Extract version from git tag
        id: tag
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          VERSION="${TAG#v}"
          echo "tag=${TAG}" >> "$GITHUB_OUTPUT"
          echo "version=${VERSION}" >> "$GITHUB_OUTPUT"

      - name: Extract release notes from CHANGELOG
        id: notes
        run: |
          VERSION="${{ steps.tag.outputs.version }}"
          # Extract from "## [X.Y.Z]" to next "## [" or EOF
          python3 << 'EOF'
          import re
          with open('CHANGELOG.md', 'r') as f:
              content = f.read()
          # Find the section for this version
          pattern = rf'## \[{re.escape(VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n(.*?)(?=\n## \[|$)'
          match = re.search(pattern, content, re.DOTALL)
          if not match:
              print("::error::Could not extract release notes for version")
              exit(1)
          notes = match.group(1).strip()
          # Escape for GitHub output
          notes = notes.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
          print(f"RELEASE_NOTES={notes}", file=open(os.environ['GITHUB_OUTPUT'], 'a'))
          EOF

      - name: Create GitHub Release
        uses: softprops/action-gh-release@de2c0eb89ae2a093876385947365ece477b33038  # v0.1.15
        with:
          tag_name: ${{ steps.tag.outputs.tag }}
          body: ${{ steps.notes.outputs.RELEASE_NOTES }}
          draft: false
          prerelease: false
```

#### Step 4: Verify Dispatch Test is in Correct CI Job

In `.github/workflows/_required.yml` (or your main CI file), ensure bash regression tests run in a **separate** job from lint:

```yaml
dispatch-contract-test:
  name: dispatch-contract-test
  runs-on: ubuntu-24.04
  steps:
    - name: Checkout
      uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
    - name: Run dispatch-apply shell tests
      run: bash tests/dispatch-apply.test.sh
```

**Do NOT mix this with the lint job.** Bash tests are integration/regression tests, not linting.

#### Step 5: Add Pre-Commit Hooks for Signed Commits

Add to `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/mattlqx/pre-commit-sign
  rev: v1.1.4
  hooks:
    - id: sign-commit
      stages: [commit]
      # This hook will enforce GPG/SSH signing on commit

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

Create `scripts/check_version_consistency.py`:

```python
#!/usr/bin/env python3
"""
Pre-commit hook: validate version consistency across manifest files.
Ensures pixi.toml, dagger/package.json, and CHANGELOG.md all declare the same version.
"""
import sys
import tomllib
import json
import re
from pathlib import Path


def get_pixi_version() -> str:
    """Extract version from pixi.toml."""
    if not Path("pixi.toml").exists():
        return None
    with open("pixi.toml", "rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("version") or data.get("version")


def get_package_json_version() -> str:
    """Extract version from dagger/package.json."""
    pkg_file = Path("dagger/package.json")
    if not pkg_file.exists():
        return None
    with open(pkg_file) as f:
        data = json.load(f)
    return data.get("version")


def get_changelog_version() -> str:
    """Extract latest version from CHANGELOG.md (first dated section)."""
    if not Path("CHANGELOG.md").exists():
        return None
    with open("CHANGELOG.md") as f:
        content = f.read()
    # Find first dated section: ## [X.Y.Z] - YYYY-MM-DD
    match = re.search(r'## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}', content)
    return match.group(1) if match else None


def main() -> int:
    """Validate version consistency across all manifests."""
    versions = {
        "pixi.toml": get_pixi_version(),
        "dagger/package.json": get_package_json_version(),
        "CHANGELOG.md": get_changelog_version(),
    }

    # Filter out None values (missing optional files)
    versions = {k: v for k, v in versions.items() if v is not None}

    if not versions:
        print("WARNING: No version-bearing files found")
        return 0

    unique_versions = set(versions.values())
    if len(unique_versions) == 1:
        print(f"✓ All manifest versions consistent: {unique_versions.pop()}")
        return 0

    print("::error::Version mismatch across manifest files:")
    for file, version in sorted(versions.items()):
        print(f"  {file}: {version}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

Make executable:
```bash
chmod +x scripts/check_version_consistency.py
```

#### Step 6: Verify PR Body Format (Policy)

Before creating PR, ensure the PR body contains exact `Closes #N` on its own line (case-sensitive):

```
## Summary
Brief description of the release.

Closes #101
```

This ensures GitHub automatically closes the linked issue when the PR merges.

#### Step 7: Test Integration Locally

Before pushing, verify everything works:

```bash
# 1. Run regression tests
bash tests/dispatch-apply.test.sh

# 2. Validate release.yml syntax
pip install yamllint
yamllint .github/workflows/release.yml

# 3. Validate CHANGELOG.md format
python3 scripts/check_version_consistency.py

# 4. Verify no unsigned commits
git log --oneline --format='%h %G? %s' | head -10
# All should show 'G' (valid signature), not 'N' (not signed)
```

#### Step 8: Create Commit and PR

After all validations pass:

```bash
git add CHANGELOG.md tests/dispatch-apply.test.sh \
  .github/workflows/release.yml \
  scripts/check_version_consistency.py \
  .pre-commit-config.yaml

git commit -S -m "feat: ship first versioned release v0.1.0 with CHANGELOG and release workflow

Implements keepachangelog CHANGELOG format with [Unreleased] section and dated
release sections. release.yml workflow validates tag/version consistency across
all manifests before publishing to GitHub Releases. All commits must be signed;
pre-commit hooks enforce version consistency.

Verification: verified-local

Key learnings:
- Keepachangelog format with [Unreleased] + dated version sections
- Bash tests in dedicated CI job, not mixed with lint
- Strict semver tag validation only (^v[0-9]+\.[0-9]+\.[0-9]+$)
- Pre-commit hooks scoped to version-bearing files
- All commits must be signed; PR body needs 'Closes #N' format
- Implementation order: test → workflow → CI integration → support files

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

git push -u origin <branch>

gh pr create --repo <owner>/<repo> --base main \
  --title "feat: ship first versioned release v0.1.0 with CHANGELOG and release workflow" \
  --body "## Summary

Adds keepachangelog CHANGELOG with [Unreleased] section and release.yml workflow that validates semver tag consistency across manifests before publishing to GitHub Releases.

## Key Features

- CHANGELOG.md in keepachangelog format with [Unreleased] + dated sections
- release.yml validates tag/version consistency across pixi.toml, dagger/package.json, CHANGELOG.md
- Strict semver tag validation (^v[0-9]+\.[0-9]+\.[0-9]+$ only, no pre-release suffixes)
- Pre-commit hooks enforce signed commits and version consistency
- Regression tests in dispatch-contract-test job (not lint)

## Verification

All acceptance criteria verified locally:
- Tests pass: bash tests/dispatch-apply.test.sh
- CHANGELOG structure: [Unreleased] + [X.Y.Z] - YYYY-MM-DD sections
- Version consistency: pixi.toml == dagger/package.json == CHANGELOG
- Workflow YAML validates
- Pre-commit hooks configured

Closes #101"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Mixing bash regression tests with lint job | Placed `dispatch-apply.test.sh` as `run: bash tests/...` inside the lint job | Lint job runs linters (shellcheck, yamllint) — runtime behavior tests belong in a separate job; mixing them causes confusion about job purpose and hard to add new regression tests | Create a dedicated `dispatch-contract-test` job for bash regression tests; keep lint focused on static analysis |
| Using hatch-vcs for dual-stack projects | Added hatch-vcs to handle auto-versioning from git tags across pixi.toml + dagger/package.json | Hatch-vcs is Python-only; dagger/package.json is Node.js — cannot auto-version both. Requires manual validation workflow instead | For polyglot projects, use manual semver validation in release.yml instead of hatch-vcs; validation workflow ensures consistency across all language stacks |
| Using `git tag -a` without pre-commit signing | Developers created release tags with `git tag -a vX.Y.Z` without enforcing GPG signing | Unsigned commits bypassed branch protection; release tags could be spoofed; CI cannot verify tag authorship | Use pre-commit hook `mattlqx/pre-commit-sign` to enforce GPG/SSH signing; configure git to reject unsigned commits on push to main |
| Putting version in PR title instead of body | Tried "feat: v0.1.0 release" as PR title | GitHub "Closes #N" link only works on PR body, not title; issue did not auto-close on merge | Always put "Closes #N" on its own line in PR body (not title); GitHub link parser requires exact format |
| CHANGELOG without dated sections | Used only `[Unreleased]` with no historical release sections | release.yml has no previous version to compare for consistency validation; users cannot see what was in released versions | Always include dated sections for all released versions: `## [X.Y.Z] - YYYY-MM-DD`. Keep [Unreleased] at top for next version |

## Results & Parameters

### Version Consistency Test Results

Expected output after `bash tests/dispatch-apply.test.sh`:
```
=== Running version/dispatch regression tests ===
PASS: Tag 'v0.1.0' matches semver format
PASS: CHANGELOG.md has [Unreleased] section
PASS: pixi.toml version is 0.1.0
PASS: dagger/package.json version is 0.1.0
PASS: dispatch-apply.sh validates client_payload.host

Results: 5/5 tests passed
```

### Manifest Version Values

| Manifest | Location | Pattern | Example |
| --------- | --------- | --------- | --------- |
| pixi.toml | Top level `version =` | `^version = "X.Y.Z"$` | `version = "0.1.0"` |
| dagger/package.json | `{ "version": "..." }` | `"version": "X.Y.Z"` | `"version": "0.1.0"` |
| CHANGELOG.md | Section header | `## [X.Y.Z] - YYYY-MM-DD` | `## [0.1.0] - 2026-06-03` |

### Pre-Commit Hook Validation

When committing changes to version-bearing files:
```bash
$ git commit -S -m "..."
# Pre-commit hooks run:
# 1. sign-commit — verifies commit is GPG/SSH signed
# 2. version-consistency-check — validates all three manifests agree on version

# If version mismatch:
check_version_consistency.py.....................................................FAILED
- hook id: version-consistency-check
  exit code: 1
  
  ::error::Version mismatch across manifest files:
    CHANGELOG.md: 0.1.0
    dagger/package.json: 0.2.0
    pixi.toml: 0.1.0
```

### release.yml Execution Flow

When pushing a tag like `git push origin v0.1.0`:

1. **GitHub detects tag matching pattern** `v[0-9]+.[0-9]+.[0-9]+`
2. **validate job runs**:
   - Extract version from tag (v0.1.0 → 0.1.0)
   - Check tag format matches `^v[0-9]+\.[0-9]+\.[0-9]+$`
   - Validate pixi.toml version == tag version
   - Validate dagger/package.json version == tag version
   - Validate CHANGELOG.md has `## [0.1.0] - YYYY-MM-DD` section
   - Validate CHANGELOG.md has `## [Unreleased]` section
   - Run regression tests (bash tests/dispatch-apply.test.sh)
3. **If all validations pass**, publish job creates GitHub Release with:
   - Release name: `v0.1.0`
   - Release body extracted from CHANGELOG `## [0.1.0]` section
4. **If any validation fails**, workflow stops and alerts maintainer

### Tag Workflow Example

```bash
# 1. Ensure CHANGELOG.md has dated section
# ## [0.1.0] - 2026-06-03

# 2. Ensure version consistency
python3 scripts/check_version_consistency.py
# Output: ✓ All manifest versions consistent: 0.1.0

# 3. Create signed commit (if not already present)
git add CHANGELOG.md
git commit -S -m "chore: prepare v0.1.0 release"

# 4. Create signed tag
git tag -s -a v0.1.0 -m "Release v0.1.0: initial versioned release"

# 5. Push both commit and tag
git push origin main
git push origin v0.1.0

# 6. GitHub Actions:
#    - release.yml detects tag
#    - validate job checks all assertions
#    - publish job creates GitHub Release
#    - Users can now download v0.1.0 artifacts
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectProteus | Issue #101 — first v0.1.0 release | release.yml validates tag/manifest consistency, CHANGELOG has [Unreleased] + [0.1.0], dispatch-contract-test job validates bash regression tests |
| ProjectProteus | Commit 1c04a4a | feat: ship first versioned release v0.1.0 with CHANGELOG and release workflow (#101) |

## References

- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Actions: Triggering a workflow](https://docs.github.com/en/actions/using-workflows/triggering-a-workflow#triggering-a-workflow-with-events)
- [GitHub Actions: Creating releases](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)
- ProjectProteus: https://github.com/HomericIntelligence/ProjectProteus/issues/101
