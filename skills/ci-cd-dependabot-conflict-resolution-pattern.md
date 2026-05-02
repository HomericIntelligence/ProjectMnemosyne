---
name: ci-cd-dependabot-conflict-resolution-pattern
description: "Use when: (1) Dependabot PRs conflict after other Dependabot PRs merge to main,
  (2) gh pr merge fails with squash or merge-commit (repo enforces rebase-only), (3) multiple
  Dependabot dependency bumps are open and landing sequentially causes stale PRs, (4) a GitHub
  issue audit turns up items that may already be resolved, (5) test file ruff E402/E401 import
  order failures after using conftest.py for sys.path, (6) closing a stale aggregate-audit
  issue after its sub-issues are resolved, (7) a feature branch added a minimal dependabot.yml
  (e.g., just github-actions) but main now has a comprehensive config that is a strict superset
  — add/add conflict during rebase."
category: ci-cd
date: 2026-04-25
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: ci-cd-dependabot-conflict-resolution-pattern.history
tags: [dependabot, conflict, rebase, merge-policy, issue-audit, stale, ruff, E402, conftest, pytest, add-add-conflict, subset-skip]
---

# CI/CD Dependabot Conflict Resolution Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-14 (amended 2026-04-25) |
| **Objective** | Merge 6 Dependabot PRs, resolve 3 GitHub issues (including an aggregate audit), fix ruff lint failures in a test PR |
| **Outcome** | All 6 Dependabot PRs resolved (5 merged via `--rebase`, 1 applied directly to main + closed); all 3 issues closed; CI green throughout |
| **Verification** | verified-ci — PRs #1278, #1279 merged with passing CI; all Dependabot PRs fully merged |
| **Scale** | 6 Dependabot PRs, 3 issues (1 aggregate), 1 test coverage PR with lint fixes |

## When to Use

- Dependabot PRs are stacking and one shows CONFLICTING/DIRTY after others have merged
- `gh pr merge --squash` or `gh pr merge --merge` returns "Repository does not allow..." error
- A GitHub issue was filed as an audit/batch tracker — check if sub-issues already resolved before acting
- Test file has ruff E402 (module-level import not at top of file) and conftest.py already sets `sys.path`
- Multiple issues from a previous audit are partially or fully resolved on main already
- A Dependabot `rebase` comment was posted but the rebased PR hasn't landed before your merge window
- A feature branch added a minimal `dependabot.yml` (e.g., just github-actions), but main now has a comprehensive config that is a strict superset — add/add conflict during rebase

## Verified Workflow

### Quick Reference

```bash
# Determine repo merge policy
gh api repos/<owner>/<repo> --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge'
# Dependabot PRs: use --rebase (others blocked by policy)
gh pr merge <pr-number> --rebase

# Conflicting Dependabot PR → apply directly to main
# 1. Check what the bump changes
gh pr diff <pr-number>
# 2. Apply the change to main files
# 3. Commit and close the PR
git add requirements-dev.txt pyproject.toml  # or relevant lockfiles
git commit -m "chore(deps-dev): bump <package> from X to Y"
gh pr close <pr-number> --comment "Applied directly to main (conflict after other bumps landed). Closes #<pr-number>."

# Stale audit issue: check current state before acting
gh issue view <number> --comments
git log --oneline main | head -20   # confirm items already on main

# Close aggregate issue after sub-issues resolved
gh issue close <number> --comment "All sub-issues resolved: #N1, #N2, #N3 (PRs merged). Closing."
```

### Phase 1: Determine Repo Merge Policy

Before touching any PRs, check what merge methods are allowed:

```bash
gh api repos/<owner>/<repo> --jq '{
  squash: .allow_squash_merge,
  merge_commit: .allow_merge_commit,
  rebase: .allow_rebase_merge
}'
```

In repos that enforce **rebase-only**:
- `gh pr merge --squash` → "Repository does not allow squash merging"
- `gh pr merge --merge` → "Repository does not allow merge commits"
- `gh pr merge --rebase` → works

Always use `gh pr merge --rebase` in rebase-only repos. For Dependabot PRs specifically, `--rebase` is always the correct flag.

### Phase 2: Merge Sequential Dependabot PRs

List and sort Dependabot PRs by number (oldest first = least likely to conflict):

```bash
gh pr list --state open --author dependabot --json number,title,headRefName,mergeStateStatus \
  | python3 -c "
import json, sys
prs = json.load(sys.stdin)
for p in sorted(prs, key=lambda x: x['number']):
    print(f\"#{p['number']:5d} [{p['mergeStateStatus']:12s}] {p['title']}\")
"
```

Merge each in order, oldest first:

```bash
gh pr merge <pr-number> --rebase
```

After each merge, wait for the next PR's CI to update before merging it. GitHub's Dependabot will often auto-rebase conflicting PRs, but this can take time.

### Phase 3: Handle a Conflicting Dependabot PR

When a Dependabot PR goes CONFLICTING after other bumps land:

**Option A: Wait for Dependabot rebase** (preferred if not urgent)
- Post a comment `@dependabot rebase` on the PR
- Wait 5–15 minutes for Dependabot to push a rebased commit

**Option B: Apply directly to main** (use when Dependabot rebase is slow or already tried)

```bash
# 1. See exactly what the PR changes
gh pr diff <pr-number>

# 2. Apply the change(s) to main directly
# For a requirements-dev.txt bump:
sed -i 's/package==OLD/package==NEW/' requirements-dev.txt

# For a pyproject.toml bump (optional-dependencies section):
# Edit the relevant version constraint manually

# 3. Verify the change
git diff

# 4. Commit to main
git add requirements-dev.txt pyproject.toml
git commit -m "$(cat <<'EOF'
chore(deps-dev): bump <package> from X to Y

Applying Dependabot PR #<number> directly to main after conflict.
The bump was blocked by conflicts from other Dependabot bumps landing first.
EOF
)"

# 5. Close the stale PR
gh pr close <pr-number> --comment "Applied directly to main (conflict from sequential Dependabot bumps). Resolved."
```

**Why this works**: The conflict is purely positional (version string changed in the same line in both the branch and main). The semantic intent (bump the version) is already achieved by direct application.

### Phase 4: Triage a Stale Issue Audit

When an issue audit was filed weeks/months ago, check current state before acting:

```bash
# Read the issue (requirements listed)
gh issue view <number>

# Check what's been done since the audit
git log --oneline --since="<audit-date>" main | head -30

# For each item in the audit, verify on main:
ls <expected-files>
git show main:<path/to/file> | head -5

# If items already exist:
gh issue close <number> --comment "Resolved: <item1> exists at <path>, <item2> merged in PR #N. All audit items addressed."
```

**Key rule**: Never start implementing audit items without first checking whether they've already been done. Audits become stale rapidly on active repos.

### Phase 5: Fix ruff E402 in Test Files (conftest.py sys.path pattern)

When a test file fails CI with `E402 Module level import not at top of file`:

**Root cause**: The test file manually adds to `sys.path` (e.g., `sys.path.insert(0, ...)`) before imports. ruff sees the imports below the `sys.path` manipulation as E402 violations.

**Fix**: Remove the `sys.path` manipulation from individual test files. Use `conftest.py` for this.

```python
# BAD — in test_foo.py (causes E402 on all imports below):
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import my_module   # E402: module level import not at top of file

# GOOD — conftest.py handles sys.path; test_foo.py has clean imports:
import pytest
import my_module   # no E402 — conftest ran first
```

Check if conftest.py already handles the path:

```bash
# Check repo conftest files
find <project-root> -name "conftest.py" | xargs grep -l "sys.path" 2>/dev/null
```

If conftest.py already sets `sys.path`, simply delete the duplicate block from the test file.

**Also watch for**: E501 (line too long) in test files — break long strings across lines or shorten variable names.

### Phase 6: Fix ruff Unused Import Warnings in Test Files

When CI shows `F401 'patch' imported but unused` or `F401 'pytest' imported but unused`:

```bash
# Check which imports are actually used
grep -n "patch\|@pytest.mark\|pytest\." test_file.py

# Remove unused imports
# If 'patch' is imported but mock.patch is used inline:
# from unittest.mock import patch  → remove if using mock.patch() directly
```

**Pattern**: Test files generated by sub-agents often import `patch` from `unittest.mock` but use `mock.patch()` as a context manager directly — the standalone `patch` import is unused.

### Phase 7: Close Aggregate Audit Issues

When an issue is an aggregate tracker ("All X issues should be fixed"):

```bash
# Verify all sub-issues are closed
gh issue list --label <label> --state open  # should be empty
# Or check linked issues in the audit issue body

# Close with summary
gh issue close <number> --comment "$(cat <<'EOF'
All items in this audit have been resolved:
- #N1: resolved via PR #M1
- #N2: resolved via PR #M2
- #N3: already existed on main (confirmed <date>)

Closing this aggregate tracker.
EOF
)"
```

### Dependabot add/add Conflict: Subset Skip

When rebasing a feature branch onto main and encountering an **add/add conflict** in `.github/dependabot.yml` — where both the branch and main added the file independently:

**a. Inspect the conflict during rebase:**

```bash
# During git rebase, after conflict is reported:
git diff
# The conflict markers show what the branch added vs. what main has
```

**b. Compare branch content to main's version:**

If main's `dependabot.yml` contains ALL entries that the branch's version has (plus additional stanzas), the branch config is a **strict subset** of main's comprehensive config. Common pattern: branch added only a `github-actions` entry; main has 10+ Docker package-ecosystem entries plus npm and github-actions.

```bash
# To confirm: view main's version of the file
git show origin/main:.github/dependabot.yml
```

**c. Resolution — use `git rebase --skip`:**

Do NOT resolve manually. Do NOT use `git checkout --ours` or `--theirs`. Skip the entire commit:

```bash
git rebase --skip
```

This drops the branch's commit entirely, keeping main's comprehensive config.

**d. MANDATORY silent-drop check:**

After `--skip`, the rebase may complete with zero commits remaining:

```bash
git log origin/main..HEAD --oneline
```

If this output is **empty**, the branch's only commit was the dropped one. The branch is **fully superseded** — no PR is needed. Document the branch as superseded and do not open a PR.

**e. Cleanup:**

```bash
git worktree remove <worktree-path>
# Document outcome: "Branch <name> superseded — dependabot.yml commit subsumed by main's comprehensive config (2026-04-25)"
```

**Why `--skip` and not manual merge**: The branch added a minimal subset (e.g., github-actions only). Main's config is already a strict superset. Manually merging both sides would either produce duplicate stanzas or simply reproduce main's config — `--skip` is the correct semantic operation here.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh pr merge --squash` on Dependabot PR | Used squash merge for a dependency bump | "Repository does not allow squash merging" | Check repo merge policy first; only `--rebase` works in rebase-only repos |
| `gh pr merge --merge` on Dependabot PR | Used merge commit flag | "Repository does not allow merge commits" | Same lesson — always use `--rebase` in rebase-only repos |
| Waiting for `@dependabot rebase` to land | Posted rebase comment on PR #1238; waited several minutes | Comment triggers async rebase; no guarantee it completes in time | If rebase comment doesn't land within ~10 min, apply directly to main and close the PR |
| Implementing all items from an audit issue | Started implementing items from Issue #924 (aggregate audit) without checking current state | SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, pytest CI, and validate scripts all already existed on main | Always check current state of repo before acting on audit items; audits go stale quickly |
| Duplicate `sys.path` block in test files | Sub-agent added `sys.path.insert()` in every test file because conftest.py pattern wasn't checked | Caused ruff E402 on all imports below the `sys.path` block | Check for conftest.py `sys.path` handling before generating test files; never duplicate in test files |
| Keeping unused `patch` import from `unittest.mock` | Generated tests imported `patch` for anticipated use | `patch` was never used directly (used `mock.patch()` context manager instead) | After generating test files, run `ruff check --select F401` to catch unused imports before pushing |
| Manually resolving add/add dependabot.yml conflict by merging both sides | Branch added minimal github-actions entry; main had comprehensive 10-stanza config; attempted manual merge of both conflict sides | Unnecessary when branch entries are a strict subset of main's config — produces duplicate stanzas or just reproduces main's version | When branch dependabot.yml is a strict subset of main's, use `git rebase --skip`; then run mandatory silent-drop check (`git log origin/main..HEAD --oneline`) |

## Results & Parameters

### Repo Merge Policy Detection

```bash
# Quick check — if any are false, that method is blocked
gh api repos/<owner>/<repo> --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge'
# false / false / true → rebase-only repo
```

### Dependabot PR Resolution Decision Tree

```
Dependabot PR open?
├── MERGEABLE → gh pr merge <N> --rebase
├── CONFLICTING →
│   ├── Post @dependabot rebase comment → wait 10 min
│   │   ├── PR rebased → gh pr merge <N> --rebase
│   │   └── Still conflicting → apply directly to main (Phase 3)
│   └── Apply directly to main + close PR
└── BLOCKED (CI failing) →
    ├── Check required checks: gh api repos/owner/repo/branches/main --jq '.protection.required_status_checks.contexts[]'
    └── Fix the actual failure before merging
```

### dependabot.yml add/add Conflict Decision Tree

```
add/add conflict in .github/dependabot.yml during rebase?
├── Branch entries are a STRICT SUBSET of main's config →
│   └── git rebase --skip
│       ├── git log origin/main..HEAD --oneline is EMPTY →
│       │   └── Branch fully superseded — no PR needed; document and clean up
│       └── git log origin/main..HEAD --oneline has commits →
│           └── Remaining commits are non-dependabot changes; open PR normally
└── Branch entries are NOT a strict subset (branch has unique entries) →
    └── Manual merge: keep all unique entries from both sides; git add .github/dependabot.yml; git rebase --continue
```

### Issue Audit Checklist

Before acting on any audit/batch issue:

1. `gh issue view <number>` — read all requirements
2. For each requirement: `ls <path>` or `git show main:<path>` — does it exist?
3. For any CI requirement: `gh run list --branch main --limit 5` — is it running?
4. If >80% already done: close the issue with evidence, don't re-implement

### ruff Lint Quick Fix Reference

| Error | Cause | Fix |
| ------- | ------- | ----- |
| `E402 Module level import not at top` | `sys.path` manipulation before imports | Remove duplicate `sys.path` block; conftest.py handles it |
| `F401 imported but unused` | Generated test imports `patch` but never calls it standalone | Remove unused import |
| `E501 Line too long` | Long test assertion strings | Break string across lines with `(` `)` |
| `E303 too many blank lines` | Extra blank lines in test file | Remove extra blank lines |

### Scale Reference

| Task | Method | Time |
| ------ | -------- | ------ |
| 5 sequential Dependabot PRs (no conflicts) | `gh pr merge --rebase` per PR | ~2 min total |
| 1 conflicting Dependabot PR | Apply directly to main + close | ~5 min |
| Stale issue audit (3 issues) | Check current state, close with evidence | ~10 min |
| Sub-agent test PR with ruff lint failures | Fix on branch directly, push | ~15 min |
| Myrmidon sub-agent for text-change task | Delegate via swarm | ~90 sec wall-clock, 7 tool calls |
| dependabot.yml add/add subset conflict (rebase) | `git rebase --skip` + silent-drop check | ~5 min |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | 6 Dependabot PRs (pytest, PyYAML, certifi, etc.), Issues #909/#916/#924, 2026-04-14 | PRs #1278/#1279 merged with CI passing; PR #1238 (pytest 9.0.3) applied to main directly |
| AchaeanFleet | Branch 100-auto-impl rebase onto origin/main, 2026-04-25 | add/add conflict in .github/dependabot.yml; branch config was strict subset; `git rebase --skip` resolved; empty log confirmed branch fully superseded — no PR opened |
