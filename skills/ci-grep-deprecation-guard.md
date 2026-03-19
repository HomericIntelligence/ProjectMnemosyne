---
name: ci-grep-deprecation-guard
description: 'Add a CI step that grep-blocks reappearance of deprecated identifiers.
  Use when: (1) deprecated names/aliases have been removed and you want a regression
  guard, (2) a cleanup PR removed old identifiers and follow-up CI enforcement is
  needed, (3) you want a no-build-required lint check for forbidden symbols.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Goal** | Prevent reappearance of removed deprecated identifiers by failing CI on any match |
| **Trigger** | Post-cleanup follow-up issue: "add regression guard for identifiers removed in #N" |
| **Output** | New `run:` step in an existing syntax-check job (no new workflow needed) |
| **Language** | Any (Mojo, Python, TypeScript, …) — uses plain `grep` |
| **Build required** | No — pure file scan, runs before compilation |

## When to Use

- A cleanup PR removed deprecated type aliases, function names, or module paths
- The team wants CI to hard-fail if those names are accidentally re-added
- A follow-up issue explicitly asks for a "regression guard" without requiring code review
- The identifiers to block are known at write-time and won't legitimately reappear

## Verified Workflow

### Quick Reference

```bash
# Pattern for the grep command (pipe-separated for BRE)
PATTERN='OldName1\|OldName2\|OldName3'

# Scan (exclude comment lines to avoid false positives)
grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
  | grep -v '^\s*#' \
  | grep -v '^\s*"""' \
  | grep -q .
```

### Step 1 — Verify zero current matches

Before adding the CI step, confirm the codebase is already clean:

```bash
PATTERN='OldName1\|OldName2\|OldName3'
grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null
# Expected: no output
```

This prevents the CI step from failing on day one.

### Step 2 — Identify the right workflow job

Look for an existing syntax/lint job that runs early (before compilation):

```bash
ls .github/workflows/
# Open the workflow that contains other pattern-check steps
# (e.g., comprehensive-tests.yml with a mojo-syntax-check job)
```

Placing the new step inside the existing job avoids creating a separate workflow
and keeps it in the critical path (compilation depends on syntax-check).

### Step 3 — Add the step after similar pattern checks

Add a new `- name:` step inside the existing job's `steps:` list.
Place it after any existing pattern-check steps so the output is grouped logically.

```yaml
      - name: Check for deprecated backward result alias names
        run: |
          echo "============================================================"
          echo "Checking for deprecated backward result alias names..."
          echo "============================================================"

          # The N deprecated type aliases removed in #CLEANUP_PR.
          # They must not reappear in shared/ or tests/.
          PATTERN='Name1\|Name2\|Name3'

          # Two-phase grep: broad scan, then exclude comment/docstring lines.
          if grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
               | grep -v '^\s*#' \
               | grep -v '^\s*"""' \
               | grep -q .; then
            echo ""
            echo "::error::Deprecated alias names detected in shared/ or tests/"
            grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
              | grep -v '^\s*#' \
              | grep -v '^\s*"""'
            echo ""
            echo "FAILED: The above deprecated type aliases were removed in #N."
            echo "Use the replacement struct names directly."
            exit 1
          else
            echo ""
            echo "PASSED: No deprecated alias names found"
          fi
```

Key decisions:
- `grep -v '^\s*#'` — excludes Mojo/Python single-line comments
- `grep -v '^\s*"""'` — excludes docstring boundary lines
- Second `grep` run (without `-q`) prints the offending lines for the developer
- `::error::` annotation surfaces in GitHub's PR diff view
- Avoid `❌` / `✅` emoji in `echo` — some CI runners mis-render them

### Step 4 — Commit and PR

```bash
git add .github/workflows/<workflow-file>.yml
git commit -m "ci(syntax-check): add CI step to block deprecated <X> alias names

Add a step to the <job-name> job that hard-fails if any of the N
deprecated identifiers reappear in <dirs>.

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "ci: add deprecation guard for <X>" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Emoji in echo | Used `❌ FAILED:` and `✅ PASSED:` strings in `echo` lines | CI runners on some Ubuntu images mis-render multi-byte emoji, causing garbled output in logs | Use plain ASCII text like `FAILED:` / `PASSED:` in CI echo statements |
| Single grep pass | Used one `grep -rn "$PATTERN" ... \| grep -q .` without filtering comments | Matched lines inside `# TODO: remove OldName` comments, causing false positives | Add `grep -v '^\s*#'` and `grep -v '^\s*"""'` filter stages |
| `--label ci` on PR create | Passed `--label ci` to `gh pr create` | Label `ci` does not exist in the target repo, causing `gh` to exit 1 | Check available labels with `gh label list` before using `--label`; omit unknown labels |
| New workflow file | Considered creating a standalone `.github/workflows/deprecation-guard.yml` | Unnecessary complexity; the pattern fits naturally inside the existing syntax-check job | Prefer adding steps to an existing job over creating a new workflow |

## Results & Parameters

### Workflow placement

```yaml
jobs:
  mojo-syntax-check:                  # existing job
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout code
        uses: actions/checkout@<sha>

      - name: Check for deprecated List[Type](args) pattern   # existing
        run: ...

      - name: Check for deprecated backward result alias names # NEW — added here
        run: |
          PATTERN='...'
          ...
```

### Pattern format

Use BRE (Basic Regular Expression) pipe syntax — compatible with GNU `grep -n` (default on Ubuntu):

```bash
# BRE pipe — works with grep (not grep -E)
PATTERN='Name1\|Name2\|Name3'
grep -rn "$PATTERN" ...

# ERE alternative (requires grep -E or grep -P)
PATTERN='Name1|Name2|Name3'
grep -rEn "$PATTERN" ...
```

GitHub Actions Ubuntu runners ship GNU grep, so both work. BRE was chosen to match the
suggestion in the originating issue.

### Directories to scan

Scan the directories where the deprecated names could legitimately reappear:

| Directory | Include |
|-----------|---------|
| `shared/` | Yes — library code |
| `tests/` | Yes — test files could import old names |
| `examples/` | Optional — may still reference old names during migration |
| `benchmarks/` | Optional |

Omit generated or vendored directories.
