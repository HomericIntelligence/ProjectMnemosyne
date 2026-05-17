---
name: markdownlint-md024-siblings-only-for-changelogs
description: "Fix markdownlint MD024/no-duplicate-heading false positives on Keep-a-Changelog CHANGELOG.md files by setting siblings_only: true. Use when: (1) markdownlint CI fails with MD024 errors on ### Added/### Fixed/### Changed/### Removed under each ## [version] heading, (2) CHANGELOG.md follows Keep-a-Changelog convention with repeated subsection names per release, (3) ROADMAP.md or any doc legitimately repeats subsection headings under different parent sections, (4) you are tempted to rename headings or disable MD024 globally to silence the rule."
category: tooling
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - markdownlint
  - MD024
  - changelog
  - keep-a-changelog
  - duplicate-heading
  - siblings_only
---

# Markdownlint MD024 siblings_only for Keep-a-Changelog

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-17 |
| **Objective** | Stop MD024/no-duplicate-heading false positives on Keep-a-Changelog CHANGELOG.md without renaming valid Keep-a-Changelog section headings or globally disabling the rule |
| **Outcome** | Fixed — 14 violations to 0 violations after a single 3-line config change; CHANGELOG.md unchanged |
| **Verification** | verified-ci (ProjectAgamemnon PR #404, 2026-05-17 — markdownlint CI passed across CHANGELOG.md + ROADMAP.md after fix) |

## When to Use

- markdownlint CI job fails with `MD024/no-duplicate-heading` on `### Added`, `### Fixed`, `### Changed`, `### Removed`, `### Security`, or `### Deprecated`
- The flagged headings live under different `## [x.y.z]` (or other top-level) parents — i.e., they are NOT actual duplicates within the same section
- The file follows the [Keep-a-Changelog](https://keepachangelog.com) convention or any pattern with repeating subsections per parent
- You want a config-only fix that requires zero edits to the changelog itself
- You are considering renaming headings (`### Added in 0.2.0`) or disabling MD024 entirely — do this instead

## Verified Workflow

### Quick Reference

```yaml
# .markdownlint.yaml — add this block
MD024:
  siblings_only: true
```

```json
// .markdownlint.json — equivalent JSON form
{
  "MD024": { "siblings_only": true }
}
```

After committing this config change, no edits to CHANGELOG.md are needed — repeated `### Added` / `### Fixed` headings under different `## [version]` parents stop being flagged because the check only compares siblings under the same parent heading.

### Detailed Steps

1. Confirm the failure mode. The CI error must look like:

   ```text
   CHANGELOG.md:42 MD024/no-duplicate-heading Multiple headings with the same content [Context: "### Added"]
   CHANGELOG.md:58 MD024/no-duplicate-heading Multiple headings with the same content [Context: "### Fixed"]
   ```

   And the headings must be legitimately distinct (under different `## [x.y.z]` parents).

2. Locate (or create) the markdownlint config at repo root. Common names:
   - `.markdownlint.yaml` / `.markdownlint.yml`
   - `.markdownlint.json`
   - `.markdownlint-cli2.yaml` (markdownlint-cli2 — config key is the same)

3. Add the `MD024: { siblings_only: true }` rule. If the config does not exist, create `.markdownlint.yaml`:

   ```yaml
   # .markdownlint.yaml
   default: true

   MD024:
     siblings_only: true

   # Common companions for changelogs / release notes (apply only if needed):
   MD013: false                              # long changelog lines
   MD033:
     allowed_elements: [br, details, summary]  # collapsible release notes
   MD034: false                              # bare URLs in changelogs
   ```

4. Re-run markdownlint locally to verify:

   ```bash
   # markdownlint-cli2
   npx markdownlint-cli2 "**/*.md"

   # or pre-commit
   pre-commit run markdownlint-cli2 --all-files
   ```

   Expect: zero MD024 violations on CHANGELOG.md and ROADMAP.md.

5. Commit the config-only change. Do NOT edit CHANGELOG.md heading text.

6. Push and let CI confirm. The markdownlint job should be green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | -------------- | -------------- |
| 1 | Rename headings to be unique per release (`### Added in 0.2.0`, `### Fixed in 0.2.0`) | Breaks the Keep-a-Changelog convention; downstream tooling (release-drafter, auto-changelog generators, GitHub release parsers) expects literal `### Added` / `### Fixed` / `### Changed` and silently produces empty or malformed release notes | Do not rename — the convention is load-bearing for tooling. Fix the linter, not the doc. |
| 2 | Disable MD024 globally (`MD024: false`) | Too permissive — allows accidental true duplicates (e.g., two `## Installation` sections in a README from a bad merge) to slip through silently | Prefer `siblings_only: true`. It keeps the rule active for real same-parent duplicates while permitting legitimate repeated subsections under different parents. |
| 3 | Inline `<!-- markdownlint-disable MD024 -->` / `<!-- markdownlint-enable MD024 -->` around each release block | Verbose, must be added for every new release, easy to forget, and clutters the changelog. Also disables real duplicate detection within each release block. | Config-level fix is one line and applies repo-wide. Inline disables are a code smell when a config option exists. |

## Results & Parameters

### Verified config block (copy-paste)

```yaml
# .markdownlint.yaml
MD024:
  siblings_only: true
```

### Companion rules commonly set alongside on changelog-heavy repos

| Rule | Setting | Why |
| ---- | ------- | --- |
| `MD013` | `false` (or `line_length: 120`) | Keep-a-Changelog entries often paste long PR titles / URLs |
| `MD033` | `{ allowed_elements: [br, details, summary] }` | Collapsible release notes use `<details>` |
| `MD034` | `false` | Bare URLs are common in changelogs; wrapping in `<>` is noisy |
| `MD041` | `false` | If CHANGELOG.md does not lead with H1 (some teams start with `## [Unreleased]`) |

### Measured impact (ProjectAgamemnon)

| Metric | Before | After |
| ------ | ------ | ----- |
| Release blocks in CHANGELOG.md | 14 | 14 (unchanged) |
| MD024 violations on CHANGELOG.md | 14 | 0 |
| MD024 violations on ROADMAP.md | non-zero | 0 |
| Lines changed in CHANGELOG.md | n/a | 0 |
| Lines changed in `.markdownlint.yaml` | n/a | 3 (added `MD024:` block) |

### Verification commands

```bash
# Locally
npx markdownlint-cli2 CHANGELOG.md ROADMAP.md
pre-commit run markdownlint-cli2 --all-files

# CI
gh pr checks <PR_NUMBER>
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectAgamemnon | PR #404 (2026-05-17) | CHANGELOG.md had 14 release blocks each with `### Added` / `### Fixed`. Pre-fix: 14 MD024 violations. Post-fix (config-only): 0 violations. ROADMAP.md also benefited. |

## References

- Markdownlint MD024 rule: <https://github.com/DavidAnson/markdownlint/blob/main/doc/md024.md>
- Keep-a-Changelog spec: <https://keepachangelog.com>
- `siblings_only` parameter docs: <https://github.com/DavidAnson/markdownlint/blob/main/schema/.markdownlint.yaml>
