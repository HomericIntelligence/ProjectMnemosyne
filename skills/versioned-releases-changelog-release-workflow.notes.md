# Notes: Versioned Releases with Keepachangelog and Release Workflows

## Acceptance Criteria Checklist

This skill was verified against the following acceptance criteria from ProjectProteus #101:

### CHANGELOG.md Requirements

- [ ] CHANGELOG.md exists at project root
- [ ] Top section is `## [Unreleased]` (exact format, case-sensitive)
- [ ] [Unreleased] section contains subsections: Added, Fixed, Changed, Removed, Deprecated, Security, Known Issues (as applicable)
- [ ] At least one dated release section exists: `## [X.Y.Z] - YYYY-MM-DD` format
- [ ] Dated section does NOT have "v" prefix: `## [0.1.0]` not `## [v0.1.0]`
- [ ] Comparison links at bottom: `[Unreleased]: <url>`, `[X.Y.Z]: <tag-url>`
- [ ] Format is strict — release.yml parses it with regex; extra spaces will break the workflow

### Version Consistency Requirements

- [ ] `pixi.toml` has `version = "X.Y.Z"` at project root (not in tool sections)
- [ ] `dagger/package.json` has `"version": "X.Y.Z"` (case-sensitive key)
- [ ] `CHANGELOG.md` has dated section matching the version
- [ ] All three files declare the same version (no X.Y.Z vs vX.Y.Z inconsistencies)
- [ ] Pre-commit hook validates consistency before commits reach main

### Git Tag Requirements

- [ ] Tag format is strict: `v[0-9]+.[0-9]+.[0-9]+` (regex: `^v[0-9]+\.[0-9]+\.[0-9]+$`)
- [ ] NO pre-release suffixes: ✗ `v1.0.0-alpha`, ✗ `v1.0.0-rc.1`
- [ ] NO build metadata: ✗ `v1.0.0+build.123`
- [ ] Tag is signed with GPG or SSH: `git tag -s -a v0.1.0 -m "..."`
- [ ] Commits backing the tag are all signed: `git log --format='%h %G?'` shows all 'G'

### release.yml Workflow Requirements

- [ ] Workflow file: `.github/workflows/release.yml`
- [ ] Triggered on: `push.tags` pattern `v[0-9]+.[0-9]+.[0-9]+`
- [ ] Job 1 (validate):
  - [ ] Extract version from git tag
  - [ ] Validate tag format (no pre-release, no build suffix)
  - [ ] Validate pixi.toml version matches tag
  - [ ] Validate dagger/package.json version matches tag
  - [ ] Validate CHANGELOG.md has dated section for version
  - [ ] Validate CHANGELOG.md has [Unreleased] section
  - [ ] Run regression tests: `bash tests/dispatch-apply.test.sh`
  - [ ] Fail closed if ANY validation fails (no silent failures)
- [ ] Job 2 (publish):
  - [ ] Extract release notes from CHANGELOG using regex
  - [ ] Create GitHub Release with tag and extracted notes
  - [ ] Mark as final release (prerelease: false)
  - [ ] Depends on validate job (won't run if validate fails)

### Pre-Commit Hook Requirements

- [ ] `.pre-commit-config.yaml` includes `mattlqx/pre-commit-sign` hook
- [ ] Signed commits enforced: `sign-commit` stage runs on all commits
- [ ] Version consistency hook:
  - [ ] Entry: `scripts/check_version_consistency.py`
  - [ ] Runs only on files matching: `pixi.toml`, `dagger/package.json`, `CHANGELOG.md`
  - [ ] `pass_filenames: false` (check all files, not just changed ones)
  - [ ] Validates pixi.toml == dagger/package.json == CHANGELOG first dated section
- [ ] Both hooks fail closed on mismatch (no `continue-on-error: true`)

### Regression Test Requirements

- [ ] File: `tests/dispatch-apply.test.sh`
- [ ] Executable: `chmod +x tests/dispatch-apply.test.sh`
- [ ] Tests pass locally: `bash tests/dispatch-apply.test.sh` → "5/5 tests passed"
- [ ] Tests run in **dedicated** CI job: `dispatch-contract-test` (NOT mixed with lint)
- [ ] CI job location: `.github/workflows/_required.yml` or similar

### PR Requirements

- [ ] All changes committed with `-S` flag: `git commit -S -m "..."`
- [ ] PR body contains exact `Closes #N` on own line (GitHub link parser requirement)
- [ ] PR body describes:
  - [ ] CHANGELOG format change (keepachangelog [Unreleased] convention)
  - [ ] release.yml validation flow
  - [ ] Signed commit requirement
  - [ ] Version consistency mechanism
- [ ] No auto-merge (manual review required for first release)

## Common Pitfalls

### Semver Tag Format

**Wrong:**
- `v1.0.0-alpha` (has pre-release suffix)
- `1.0.0` (missing v prefix)
- `release-1.0.0` (wrong prefix)
- `v1.0.0.0` (4-part version)

**Right:**
- `v1.0.0`
- `v0.1.0`
- `v2.3.4`

### CHANGELOG Format

**Wrong:**
```markdown
## [v0.1.0] - 2026-06-03  # Do NOT include "v" in section header
```

**Right:**
```markdown
## [0.1.0] - 2026-06-03  # NO "v" prefix
## [Unreleased]  # Always at the top, exact case
```

### Version Consistency

**Wrong:**
```toml
# pixi.toml
version = "0.1.0"
```

```json
// dagger/package.json
"version": "v0.1.0"  // Different format!
```

**Right:**
```toml
# pixi.toml
version = "0.1.0"
```

```json
// dagger/package.json
"version": "0.1.0"  // Same format
```

### Pre-Commit Hooks

**Wrong:**
```yaml
- id: sign-commit
  stages: [commit]
  # Missing on push — signatures only enforced at commit time, not push

- id: version-consistency-check
  files: .*  # Too broad, checks ALL files
  pass_filenames: true  # Wrong — file checker needs all files at once
```

**Right:**
```yaml
- id: sign-commit
  stages: [commit]
  # sign-commit automatically enforces on push as well

- id: version-consistency-check
  files: ^(pixi\.toml|dagger/package\.json|CHANGELOG\.md)$  # Specific files
  pass_filenames: false  # Check all files at once, not per-file
```

## Debugging Failed release.yml

### Symptom: "Tag does not match semver format"

```
::error::Tag 'v1.0.0-alpha' does not match semver format ^v[0-9]+\.[0-9]+\.[0-9]+$
```

**Solution:** Tag must be strict semver with no pre-release. Delete the tag and recreate:
```bash
git tag -d v1.0.0-alpha
git push origin :refs/tags/v1.0.0-alpha
git tag -s -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Symptom: "pixi.toml version does not match tag"

```
::error::pixi.toml version '0.2.0' does not match tag version '0.1.0'
```

**Solution:** Update the version in pixi.toml to match the tag, then amend the commit or create a new one:
```bash
# Update pixi.toml
sed -i 's/version = "0.2.0"/version = "0.1.0"/' pixi.toml

# Commit (signed)
git add pixi.toml
git commit -S -m "fix: correct pixi.toml version to 0.1.0"
git push origin main

# Delete and recreate tag
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0
git tag -s -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

### Symptom: "CHANGELOG.md missing dated section"

```
::error::CHANGELOG.md missing dated section for v0.1.0 (format: ## [X.Y.Z] - YYYY-MM-DD)
```

**Solution:** Add the dated section to CHANGELOG.md:
```markdown
## [0.1.0] - 2026-06-03

### Added
- Feature X
```

Then commit and re-tag:
```bash
git add CHANGELOG.md
git commit -S -m "chore: add CHANGELOG section for v0.1.0"
git push origin main
git tag -s -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

### Symptom: "Dispatch regression tests failed"

```
FAIL: dispatch-apply.sh missing client_payload.host validation
Results: 4/5 tests passed
```

**Solution:** Update `scripts/dispatch-apply.sh` to validate the dispatch contract:
```bash
# In scripts/dispatch-apply.sh, add:
if [ -z "${HOST:-}" ]; then
  echo "::error::client_payload.host is required"
  exit 1
fi
```

## Related Skills

- `hatch-vcs-pyproject-auto-versioning-setup` — for Python projects using git tags to auto-version
- `versioning-consistency-release-workflow` — for managing version drift across multiple files
- `generate-changelog` — for parsing commits into changelog entries

## Implementation Timeline (Estimated)

| Step | Time | Notes |
| --------- | --------- | --------- |
| 1. Create CHANGELOG.md | 10 min | Copy template, fill in sections |
| 2. Write regression tests | 15 min | bash script to validate formats |
| 3. Create release.yml | 20 min | GitHub Actions workflow with validation steps |
| 4. Add pre-commit hooks | 15 min | Configure sign-commit and version-consistency hooks |
| 5. Test locally | 10 min | Run regression tests, validate formats, test signing |
| 6. Commit and PR | 10 min | Create signed commit, push, open PR |
| **Total** | **~70 min** | Can be faster with template copy-paste |
