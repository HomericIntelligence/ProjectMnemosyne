---
name: readme-badges-live-sources-and-count-drift-prevention
description: "Use when: (1) adding badges to a README and need live-source badge endpoints (shields.io, GitHub Actions status, PyPI JSON API) instead of hardcoded values; (2) adding missing PR-critical workflow badges to a README badge block; (3) automating README badge count validation to prevent drift when file/test counts grow; (4) verifying package names via PyPI before committing badge URLs; (5) replacing hardcoded test/file counts in README badges and prose with live commands users can run, preventing flakiness when counts change frequently."
category: documentation
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: readme-badges-live-sources-and-count-drift-prevention.history
tags:
  - documentation
  - badges
  - live-sources
  - ci-badges
  - pypi-verification
  - count-drift
  - shields-io
  - pre-commit
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Establish a single standard for README badges that use live data sources (shields.io, GitHub Actions, PyPI JSON API) instead of hardcoded values, add missing PR-critical CI badges, and prevent count-drift by either automating badge validation or replacing hardcoded counts with live commands |
| **Outcome** | Verified across ProjectHephaestus (#779), ProjectOdyssey (#3306, #3922, #3307), and ProjectScylla (#1322); pre-commit validation passes; PRs merged |
| **Verification** | verified-ci |

## When to Use

- Adding a new badge row or badge block to a README, or updating existing hardcoded badge values
- Adding a missing GitHub Actions status badge for a PR-critical workflow (build, test, lint, security)
- Establishing badge conventions across HomericIntelligence projects
- Validating that badges reflect current upstream data (PyPI version, CI status, etc.)
- A shields.io badge encodes a count (test files, source files) that grows over time and has drifted
- You want CI / pre-commit to catch badge count drift automatically, with a `--fix` self-service mode
- A hardcoded test/file count in README is flaky against a doc-accuracy CI check, and the fix should be "stop maintaining the number" by replacing it with a live command users can run
- Verifying the exact PyPI package name before committing a badge URL (avoid 404s from name normalization)

## Verified Workflow

### Quick Reference

```bash
# 1. Verify PyPI package exists (avoids 404 from name normalization)
curl -s https://pypi.org/pypi/HomericIntelligence-Hephaestus/json | jq '.info | {name, version}'

# 2. Inventory workflows vs. existing README badges
ls .github/workflows/
head -20 README.md

# 3. Add live-source badges (never hardcode version/status)
#    CI:      GitHub Actions workflow badge.svg (live)
#    PyPI:    shields.io pypi/v endpoint        (live)
#    Python:  shields.io static badge           (documents minimum)
#    License: shields.io static badge

# 4. Validate markdown before committing
pixi run pre-commit run --files README.md

# 5. Commit (signed where policy requires) + PR with literal "Closes #N"
git add README.md
git commit -S -m "docs(readme): add <badge-type> badge"
gh pr create --title "docs(readme): add <badge-type> badge" --body "Closes #<issue>"
gh pr merge --auto --squash   # confirm repo's allowed merge method (squash vs rebase)
```

Badge URL patterns:

| Badge | Endpoint pattern |
|-------|------------------|
| CI Status | `https://github.com/<org>/<repo>/actions/workflows/<file>.yml/badge.svg?branch=main` |
| PyPI Version | `https://img.shields.io/pypi/v/<package-name>` |
| Python | `https://img.shields.io/badge/python-3.10%2B-blue` |
| License | `https://img.shields.io/badge/license-MIT-green` |

### Detailed Steps

#### A. Add a CI status badge (single workflow)

Use when a README is missing a CI badge or a new PR-critical workflow should be surfaced.

1. Confirm the workflow file exists: `ls .github/workflows/`.
2. Read the existing badge block (top of `README.md`) to find where to insert.
3. Insert the new badge **after** the last existing CI badge (CI should anchor the block — inserting before breaks visual grouping):

   ```markdown
   [![Build](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml/badge.svg?branch=main)](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml)
   ```

4. Validate: `pixi run pre-commit run --files README.md` (markdownlint, trailing-whitespace, end-of-file-fixer must all pass).
5. Commit, push, PR with one `Closes #N` per line (never comma-separate issue refs).

**Criteria for a "badge-worthy" workflow:** runs on every PR (`on: pull_request`), represents a critical quality gate (build/test/lint/security), and is not niche/supplemental (benchmarks, weekly scans). Always pin `?branch=main` for stable status.

#### B. Add a live-source badge row (CI / PyPI / Python / License)

Use when standardizing a full badge row across projects.

1. **Verify the PyPI package** before building any PyPI badge — name normalization (hyphens/underscores, ordering) breaks URLs:

   ```bash
   PACKAGE="HomericIntelligence-Hephaestus"
   curl -s "https://pypi.org/pypi/${PACKAGE}/json" | jq '.info | {name, version}'
   ```

2. **Design URLs using live endpoints only.** Valid: GitHub Actions `badge.svg` (live CI), `shields.io/pypi/v/<pkg>` (live PyPI). Acceptable static: Python minimum version, license (these document a stable fact, not a moving value). **Never** use hardcoded version (`badge/version-1.0.0-blue`) or hardcoded status text (`badge/ci-passing-brightgreen`) — they go stale immediately.

3. **Place the row** as a table after the title (table cells keep long shields.io URLs under MD013 line limits):

   ```markdown
   | CI | Python | PyPI | License |
   |----|--------|------|---------|
   | [![CI](https://github.com/HomericIntelligence/<REPO>/actions/workflows/comprehensive-tests.yml/badge.svg?branch=main)](https://github.com/HomericIntelligence/<REPO>/actions/workflows/comprehensive-tests.yml) | [![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/) | [![PyPI](https://img.shields.io/pypi/v/HomericIntelligence-<Package>)](https://pypi.org/project/HomericIntelligence-<Package>/) | [![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE) |
   ```

4. **Validate** (`pixi run pre-commit run --files README.md`) — checks MD041 (top-level heading first), MD013 (line length), MD034 (no bare URLs), trailing whitespace, EOF newline.

5. **Commit + PR with full policy compliance** (even for docs-only changes): signed commit (`git commit -S`), PR body with literal `Closes #<issue>` (capital C, no colon), auto-merge. Verify signature via GitHub, not local git — `gh api repos/<org>/<repo>/commits/<sha> --jq '.commit.verification'` shows the truth; `git log --show-signature` can lie if committer email ≠ GPG key email.

#### C. Prevent badge count drift (automated validation)

Use when a badge encodes a growing count (e.g. `tests-247%2B`) and should stay accurate via a script + pre-commit hook.

1. **Count files with `subprocess.run(["find", ...])`** (mirrors project conventions, handles large trees). **Critical:** strip the `repo_root + "/"` prefix and check exclusions on the *relative* path — if the repo root itself contains an excluded segment (e.g. `.worktrees/issue-3307/`), absolute-path exclusion silently zeros all results.

   ```python
   def count_test_files(repo_root: Path) -> int:
       cmd = ["find", str(repo_root), "-name", "test_*.mojo", "-type", "f"]
       result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
       repo_prefix = str(repo_root) + "/"
       count = 0
       for path in result.stdout.splitlines():
           rel = path[len(repo_prefix):] if path.startswith(repo_prefix) else path
           if any(excl in rel for excl in _EXCLUDE_DIRS):
               continue
           count += 1
       return count
   ```

2. **Parse the badge count with regex** and **check drift with a 10% tolerance** (~one sprint of new tests — avoids nagging every commit):

   ```python
   _BADGE_COUNT_RE = re.compile(r"tests-(\d[\d,]*?)(?:%2B|-brightgreen|\+|\.svg|-[a-z])")

   def check_badge_drift(actual: int, badge: int, tolerance: float = 0.10) -> bool:
       if actual == 0:
           return badge == 0
       return abs(actual - badge) / actual <= tolerance
   ```

3. **Provide a `--fix` mode** that rewrites the badge in-place, and **scope the pre-commit hook to README only** so the expensive `find` does not run on every commit:

   ```yaml
   - id: check-test-count-badge
     name: Check Test Count Badge
     entry: python3 scripts/check_test_count_badge.py
     language: system
     files: ^README\.md$
     pass_filenames: false
   ```

4. **Format before staging.** Run `ruff format` on the script + tests, *then* `git add`, *then* commit — pre-commit stashes unstaged files, so formatting after staging triggers a stash-rollback loop that undoes the fix and fails the commit.

#### D. Replace hardcoded counts with live commands (stop maintaining the number)

Use when a doc-accuracy CI check makes a frequently-changing count flaky and the right fix is to remove the number entirely (vs. drift automation in C, which keeps the number).

1. **Locate every reference** — counts live in multiple independent places:

   ```bash
   grep -n "2026%2B\|[0-9]\+\+ test\|check_test_counts\|[0-9]\+\+ tests" README.md CLAUDE.md docs/*.md
   ```

   Check the badge line, the `### Testing` section prose and sub-bullets, and any features checklist.

2. **Apply the three standard fixes:**
   - Badge: `tests-2026%2B-brightgreen.svg` → `tests-passing-brightgreen.svg` (or a live CI badge if CI is wired).
   - Testing prose: replace `**115+ test files**` with a live command block:

     ```bash
     pixi run pytest tests/ --collect-only -q | tail -1
     ```

     (Use `--collect-only -q`, not `-v`, to keep output parseable.) Also strip counts from sub-bullets (`**Unit Tests** (115+ files):` → `**Unit Tests**:`).
   - Features checklist: `(2026+ tests, all passing)` → `(all passing)`.

3. **Delete the enforcement script if present** (`git rm scripts/check_test_counts.py`) and remove any `.github/workflows/*.yml` reference. Issues sometimes list artifacts that don't exist — confirm with `ls` before deleting.

4. **Verify no stale refs remain**, run pre-commit, commit + PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded version/status badges | `badge/version-1.0.0-blue` and `badge/ci-passing-brightgreen` | Went stale immediately after next release; status didn't reflect real CI | Badges must query live endpoints (PyPI JSON, GitHub Actions, shields.io dynamic) — never hardcode version numbers or status text |
| PyPI badge without name verification | Used `Hephaestus-HomericIntelligence` (assumed ordering) | 404 — actual name is `HomericIntelligence-Hephaestus` | Always verify exact PyPI name via `curl https://pypi.org/pypi/<name>/json` before committing |
| Skipping pre-commit validation | Committed README with long badge URLs directly | Failed MD013 (line too long); had to reformat | Run `pixi run pre-commit run --files README.md` first; use table format for long URLs |
| Trusting local signature status | Committed signed locally but committer email mismatched GPG key | `pr-policy` gate rejected as "Unverified" | Verify via `gh api repos/<org>/<repo>/commits/<sha> --jq '.commit.verification'`, not `git log --show-signature` |
| Badge before the CI anchor | Inserted new badge before `[![CI](…)]` | Broke visual grouping | Append after the last existing CI badge |
| Comma-separating `Closes` | `Closes #3922, #3306` in PR body | Convention requires one `Closes #N` per line | Use a separate line per issue reference |
| Absolute-path exclusion in counter | `if any(excl in path ...)` on full absolute path | Repo root was `.worktrees/issue-3307/`, so `worktrees/` matched every path, zeroing results | Strip `repo_root + "/"` and check exclusions on the relative path |
| Staging then formatting | Stage → commit → pre-commit ruff modifies staged content → stash restore rolls back the fix | pre-commit stashes unstaged files | Run `ruff format` before `git add`; format → stage → commit |
| Writing tests for a docs change | Followed issue-template request for pytest tests on a one-line README edit | No code to test | Skip tests for pure documentation changes; don't follow template boilerplate blindly |

## Results & Parameters

### Live badge endpoint URLs

```text
# CI Status (GitHub Actions) — live
https://github.com/HomericIntelligence/<REPO>/actions/workflows/comprehensive-tests.yml/badge.svg?branch=main

# PyPI Version — live (shields.io queries latest release)
https://img.shields.io/pypi/v/HomericIntelligence-<Package>

# Python Version — static (documents minimum)
https://img.shields.io/badge/python-3.10%2B-blue

# License — static
https://img.shields.io/badge/license-MIT-green
```

### Drift-prevention parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Tolerance | 10% (`--tolerance 0.05` to override) | ~1 sprint of test additions before alarm |
| Find excludes | `.pixi/`, `build/`, `dist/`, `.git/`, `worktrees/` | Check on relative path |
| Hook trigger | `^README\.md$` | Only on README changes |
| Auto-fix flag | `--fix` | Rewrites badge in-place |
| Tests | 22 pytest unit tests | All functions + `main()` integration |

### Live-command replacement (copy-paste)

```bash
pixi run pytest tests/ --collect-only -q | tail -1
```

### Pre-commit validation

```bash
pixi run pre-commit run --files README.md
# Expected: Markdown Lint / Trim Trailing Whitespace / Fix End of Files all Passed.
# Mojo Format is Skipped on .md files (no Mojo toolchain needed).
```

### PR policy requirements

- PR body MUST contain literal line `Closes #<issue-number>` (capital C, no colon), one per line.
- Commits signed where the repo enforces it (`git commit -S`); verify via GitHub API.
- Enable auto-merge with the repo's allowed method — confirm squash vs. rebase per repo settings.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #779 — live-source badge row (CI/PyPI/Python/License) | Pre-commit pass, signed commits, pr-policy verified in GitHub |
| ProjectOdyssey | Issue #3306, PR #3921 — add single CI badge | Pre-commit pass; under 5 min |
| ProjectOdyssey | Issue #3922, PR #4831 — add missing `build-validation.yml` badge | Pre-commit pass; auto-merge enabled |
| ProjectOdyssey | Issue #3307, PR #3923 — badge count drift automation | 22 pytest tests pass; badge 247→223 corrected |
| ProjectScylla | Issue #1322, PR #1325 — replace hardcoded counts with live command | Pre-commit pass (markdown-lint, audit-doc-policy) |
