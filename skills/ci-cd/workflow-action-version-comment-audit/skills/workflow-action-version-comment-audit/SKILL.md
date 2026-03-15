---
name: workflow-action-version-comment-audit
description: "Audit SHA-pinned GitHub Actions uses: lines for missing version comments, add them, and add a regression test. Use when: (1) a SHA-pinning pass left bare SHA refs without # vX.Y.Z comments, (2) a follow-up issue flags inconsistent comment coverage, (3) a regression test is needed to prevent future omissions."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

# Workflow Action Version Comment Audit

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Find SHA-pinned `uses:` lines missing `# vX.Y.Z` version comments, add them, and create a regression test |
| Outcome | All SHA-pinned action refs have human-readable version comments; a pytest regression blocks future omissions |

## When to Use

- After a SHA-pinning pass (e.g. from `pin-action-shas-to-commit`) where some workflow files
  were updated inconsistently — some lines got `# v6.0.1` comments, others didn't
- A follow-up issue flags that certain workflow files (e.g. `comprehensive-tests.yml`) contain
  bare SHAs with no comment
- You want a CI-enforced regression test that ensures no future `uses:` line omits the comment

## Verified Workflow

### Quick Reference

```bash
# Find all bare SHA lines (no comment)
grep -rn "uses:.*@[0-9a-f]\{40\}" .github/ | grep -v "#"

# Bulk-add comment via sed (replace exact SHA)
sed -i 's/uses: actions\/checkout@<SHA>$/uses: actions\/checkout@<SHA>  # v6.0.1/g' .github/workflows/<file>.yml

# Verify no bare SHAs remain
grep -rn "uses:.*@[0-9a-f]\{40\}" .github/ | grep -v "#"
```

### Step-by-step

1. **Identify bare SHA lines** across the entire `.github/` tree:

   ```bash
   grep -rn "uses:.*@[0-9a-f]\{40\}" .github/ | grep -v "#"
   ```

   Lines without a `#` after the SHA need a version comment.

2. **Determine the human-readable version** for each SHA. If the SHA was introduced
   in a prior PR with `# vX.Y.Z` already present on some lines, use the same tag.
   Otherwise resolve via the GitHub API:

   ```bash
   # List tags for a repo sorted by creation date
   gh api repos/<owner>/<action-name>/git/refs/tags --jq '.[].ref' | head -20
   ```

3. **Add the comment** — either edit manually or use `sed` for bulk updates when
   all bare lines share the same SHA:

   ```bash
   sed -i 's/uses: <owner>\/<action>@<40-char-sha>$/uses: <owner>\/<action>@<40-char-sha>  # vX.Y.Z/g' \
     .github/workflows/<file>.yml
   ```

   Format: two spaces before `#`, then the version tag as it appears in the original release.

4. **Verify consistency** — all lines that previously had comments and the newly fixed lines
   should now use the same comment format:

   ```bash
   grep -n "uses:.*checkout@" .github/workflows/<file>.yml
   ```

5. **Create a regression test** in `tests/workflows/` using pytest:

   ```python
   import re
   from pathlib import Path
   from typing import List
   import pytest
   import yaml

   GITHUB_DIR = Path(__file__).parents[2] / ".github"
   WORKFLOW_FILES: List[Path] = sorted(
       list(GITHUB_DIR.glob("workflows/*.yml")) +
       list(GITHUB_DIR.glob("actions/**/*.yml"))
   )

   SHA_RE = re.compile(r"uses:\s+\S+@([0-9a-f]{40})")
   TAG_RE = re.compile(r"uses:\s+\S+@v[0-9]")
   COMMENT_RE = re.compile(r"uses:\s+\S+@[0-9a-f]{40}.*#")

   @pytest.mark.parametrize("workflow_file", WORKFLOW_FILES, ids=lambda f: f.name)
   def test_no_tag_pinned_actions(workflow_file: Path) -> None:
       for i, line in enumerate(workflow_file.read_text().splitlines(), 1):
           assert not TAG_RE.search(line), (
               f"{workflow_file.name}:{i}: tag-pinned (use SHA): {line.strip()}"
           )

   @pytest.mark.parametrize("workflow_file", WORKFLOW_FILES, ids=lambda f: f.name)
   def test_sha_pinned_actions_have_version_comment(workflow_file: Path) -> None:
       for i, line in enumerate(workflow_file.read_text().splitlines(), 1):
           # Skip local composite action references
           if SHA_RE.search(line) and "./.github" not in line:
               assert COMMENT_RE.search(line), (
                   f"{workflow_file.name}:{i}: missing version comment: {line.strip()}"
               )
   ```

6. **Run the test** to verify all files pass:

   ```bash
   pixi run python -m pytest tests/workflows/test_workflow_action_pins.py -v
   ```

7. **Commit and push**:

   ```bash
   git add .github/workflows/<file>.yml tests/workflows/test_workflow_action_pins.py
   git commit -m "fix(workflows): add missing version comments and regression test for action pins"
   git push -u origin <branch>
   ```

## Key Distinctions

- **Scope is comment-only** — this skill doesn't change SHAs, only adds `# vX.Y.Z` comments
  to lines that are already correctly SHA-pinned. Contrast with `pin-action-shas-to-commit`
  which converts tag refs to SHAs.
- **Bulk vs. individual sed** — when multiple bare lines share the same SHA (e.g. 5 occurrences
  of `actions/checkout@8e8c483...`) a single `sed -i` with `g` flag handles all at once.
- **Local composite refs are exempt** — lines like `uses: ./.github/actions/setup-pixi` never
  have a `@SHA` and should be excluded from the comment check (see `"./.github" not in line`
  guard in the test).
- **Two-space indent before `#`** — the convention `@<sha>  # vX.Y.Z` (two spaces) matches
  the style used by Dependabot and most ecosystem tools.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4845, issue #3974 | [notes.md](../../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching only for lines entirely without `#` using `grep -v "#"` | Expected to catch all bare SHA lines | Lines with unrelated `#` characters elsewhere on the line (e.g. in job names) were excluded from the match incorrectly | Use a more targeted regex: `grep -rn "uses:.*@[0-9a-f]{40}" \| grep -v "#"` to match only lines where the action SHA itself lacks a trailing comment |
| Assuming a prior SHA-pinning PR was complete | Trusted the issue description that all workflow files were already pinned consistently | Bare SHA lines existed in `comprehensive-tests.yml` at lines 40, 76, 166, 552, 634 while other lines in the same file had `# v6.0.1` | Always run the grep audit yourself — don't trust issue descriptions or prior PR completeness claims |

## Results & Parameters

**Grep to find bare SHA lines (no comment):**

```bash
grep -rn "uses:.*@[0-9a-f]\{40\}" .github/ | grep -v "#"
```

**Sed pattern for bulk comment addition:**

```bash
sed -i 's/uses: <owner>\/<action>@<40-char-sha>$/uses: <owner>\/<action>@<40-char-sha>  # vX.Y.Z/g' \
  .github/workflows/<file>.yml
```

**Regex patterns for pytest regression:**

```python
SHA_RE     = re.compile(r"uses:\s+\S+@([0-9a-f]{40})")       # matches SHA-pinned line
TAG_RE     = re.compile(r"uses:\s+\S+@v[0-9]")               # matches tag-pinned line
COMMENT_RE = re.compile(r"uses:\s+\S+@[0-9a-f]{40}.*#")      # matches SHA + comment
```

**ProjectOdyssey verified action SHAs with comments:**

| Action | Comment | SHA |
|--------|---------|-----|
| `actions/checkout` | `# v6.0.1` | `8e8c483db84b4bee98b60c0593521ed34d9990e8` |
| `actions/checkout` | `# v6` | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
