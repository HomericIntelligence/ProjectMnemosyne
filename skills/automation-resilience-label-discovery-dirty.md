---
name: automation-resilience-label-discovery-dirty
description: "Three resilience patterns for hephaestus.automation implement/plan pipelines: (1) auto-create missing GitHub labels and retry on label-not-found error, (2) auto-discover open issues when no --issues/--epic CLI arg is given via gh_list_open_issues(), (3) WorktreeDirtyError preserve-and-report pattern that blocks forced removal of dirty worktrees and prints a rerun command. Use when: (1) gh issue create fails with 'could not add label: X not found', (2) implementer/planner needs to process all open issues by default, (3) cleanup_all() should not silently discard in-progress agent worktrees."
category: tooling
date: 2026-04-22
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - automation
  - implement-issues
  - plan-issues
  - github-labels
  - gh_list_open_issues
  - WorktreeDirtyError
  - worktree
  - dirty-worktree
  - resilience
  - hephaestus
---

# Automation Resilience: Labels, Discovery, and Dirty Worktrees

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-22 |
| **Objective** | Fix five failure modes in implement_issues.py / plan_issues.py pipeline |
| **Outcome** | Success — 1403 tests pass, PR #301 merged |
| **Verification** | verified-ci |
| **Project** | ProjectHephaestus, PR #301 (branch: port-circuit-breaker-success-threshold) |

## When to Use

- `gh issue create` fails with `could not add label: '<name>' not found` in stderr
- You want to run the implementer/planner against ALL open issues without specifying `--issues` explicitly
- `cleanup_all()` in `worktree_manager.py` is forcibly removing dirty worktrees that contain in-progress agent work
- You need the cleanup summary to tell the user which issues still need rerunning and how to force-discard if desired

## Verified Workflow

### Quick Reference

```python
# Pattern 1: Ensure labels exist before gh issue create
_ensure_labels_exist(labels)        # creates any missing labels
result = gh_create_issue(...)       # then create issue
# If stderr still contains label-not-found, parse name and retry once

# Pattern 2: Discover open issues when no --issues/--epic given
from hephaestus.automation.github_api import gh_list_open_issues
issues = gh_list_open_issues(limit=500)  # returns list[int]

# Pattern 3: Preserve dirty worktrees in cleanup
try:
    manager.remove_worktree(issue_number, path, force=False)
except WorktreeDirtyError as e:
    manager.preserved.append((e.issue_number, e.path))
```

### Detailed Steps

---

#### Pattern 1 — Auto-Create Missing GitHub Labels

**Problem**: `gh issue create --label foo` fails with `could not add label: 'foo' not found`
when the label has never been created in the repository.

**Solution** — three new functions in `hephaestus/automation/github_api.py`:

```python
import functools

@functools.lru_cache(maxsize=None)
def gh_list_labels() -> list[str]:
    """Return all label names in the repo (cached per process)."""
    result = _gh_call(["label", "list", "--json", "name", "--jq", ".[].name"])
    return result.stdout.strip().splitlines()


def gh_create_label(name: str, color: str = "ededed") -> None:
    """Create a label idempotently (--force overwrites if it already exists)."""
    _gh_call(["label", "create", name, "--color", color, "--force"])
    gh_list_labels.cache_clear()   # Invalidate cache after mutation


def _ensure_labels_exist(labels: list[str]) -> None:
    """Create any labels that do not yet exist in the repo."""
    existing = set(gh_list_labels())
    for label in labels:
        if label not in existing:
            gh_create_label(label)
```

**In `gh_issue_create()`** — call `_ensure_labels_exist()` before creating, then retry
once if the error still appears:

```python
def gh_issue_create(title: str, body: str, labels: list[str]) -> int:
    _ensure_labels_exist(labels)
    try:
        result = _gh_call(["issue", "create", "--title", title, "--body", body,
                           *(["--label", l] for l in labels)])
    except subprocess.CalledProcessError as e:
        # Parse label name from stderr and retry once
        match = re.search(r"could not add label: '([^']+)' not found", e.stderr or "")
        if match:
            gh_create_label(match.group(1))
            result = _gh_call(["issue", "create", "--title", title, "--body", body,
                               *(["--label", l] for l in labels)])
        else:
            raise
    return _parse_issue_number(result.stdout)
```

**Key properties**:
- `gh_list_labels()` is cached — one API call per process, not per issue
- `gh_create_label(..., --force)` is idempotent — safe to call even if label exists
- Cache is invalidated after mutation so subsequent `gh_list_labels()` calls see new label
- Retry is attempted at most once — avoids infinite loop on persistent errors

---

#### Pattern 2 — Auto-Discover Open Issues

**Problem**: Running implementer/planner with no `--issues` or `--epic` flag silently
processes nothing (empty list), surprising users.

**Solution** — add `gh_list_open_issues()` to `hephaestus/automation/github_api.py`:

```python
def gh_list_open_issues(limit: int = 500) -> list[int]:
    """Return issue numbers for all open issues in the repo."""
    result = _gh_call([
        "issue", "list",
        "--state", "open",
        "--limit", str(limit),
        "--json", "number",
        "--jq", ".[].number",
    ])
    return [int(n) for n in result.stdout.strip().splitlines() if n]
```

**In `implementer.py` and `planner.py` `main()`**:

```python
def main() -> None:
    args = parse_args()
    if args.issues:
        issues = args.issues
    elif args.epic:
        issues = gh_list_epic_issues(args.epic)
    else:
        issues = gh_list_open_issues(limit=500)
        logger.info(
            "No --issues/--epic given; discovered %d open issues: %s",
            len(issues), issues,
        )
    # ... rest of main
```

---

#### Pattern 3 — WorktreeDirtyError Preserve-and-Report

**Problem**: `cleanup_all()` previously removed worktrees with `--force`, silently
discarding in-progress agent work. Users had no indication which issues needed rerunning.

**Solution** — custom exception + preserved list + summary block:

```python
# hephaestus/automation/worktree_manager.py

class WorktreeDirtyError(Exception):
    """Raised when a worktree has uncommitted changes and force=False."""
    def __init__(self, issue_number: int, path: Path) -> None:
        self.issue_number = issue_number
        self.path = path
        super().__init__(f"Worktree for issue #{issue_number} is dirty: {path}")


class WorktreeManager:
    def __init__(self, ...):
        ...
        self.preserved: list[tuple[int, Path]] = []

    def remove_worktree(
        self,
        issue_number: int,
        path: Path,
        force: bool = False,
    ) -> None:
        if not force and not is_clean_working_tree(path):
            raise WorktreeDirtyError(issue_number, path)
        run(["git", "worktree", "remove", str(path)] + (["--force"] if force else []))

    def cleanup_all(self) -> None:
        for issue_number, path in list(self._active_worktrees.items()):
            try:
                self.remove_worktree(issue_number, path, force=False)
            except WorktreeDirtyError as e:
                logger.warning("Preserving dirty worktree for issue #%d: %s", e.issue_number, e.path)
                self.preserved.append((e.issue_number, e.path))

    def _print_summary(self) -> None:
        # ... existing summary code ...
        if self.preserved:
            issue_nums = " ".join(str(n) for n, _ in self.preserved)
            print("\n⚠️  Preserved worktrees (contain uncommitted work):")
            for issue_number, path in self.preserved:
                print(f"  Issue #{issue_number}: {path}")
            print(f"\nRerun:  scripts/implement_issues.py --issues {issue_nums}")
            print("Force-discard (loses agent work):")
            for _, path in self.preserved:
                print(f"  git worktree remove --force {path}")
```

**Key properties**:
- `force=False` is the default — safe by default, never silently discards
- Preserved worktrees are reported with actionable rerun commands
- Force-discard commands are shown but not executed — user must choose explicitly
- `self.preserved` accumulates across multiple `cleanup_all()` calls (idempotent)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Retry on all CalledProcessError from gh issue create | Retry the entire create call when any gh error occurs | Too broad — retries would loop on unrelated errors (rate limit, auth) | Parse the specific label name from stderr; only retry after creating that exact label |
| Use gh_list_labels() without caching | Called gh API on every label check per issue | O(N) API calls for N issues — slow and rate-limit-prone | Cache with functools.lru_cache; invalidate only after write operations |
| Always force-remove dirty worktrees in cleanup_all() | Used --force to ensure cleanup completes | Silently discards in-progress agent work; users lost partial implementations | Block removal with WorktreeDirtyError; accumulate in preserved list; report at summary |

## Results & Parameters

### Files Changed

| File | Change |
| ------ | -------- |
| `hephaestus/automation/github_api.py` | Added `gh_list_labels()`, `gh_create_label()`, `_ensure_labels_exist()`, `gh_list_open_issues()` |
| `hephaestus/automation/implementer.py` | Added open-issue auto-discovery in `main()`; call `_ensure_labels_exist()` |
| `hephaestus/automation/planner.py` | Added open-issue auto-discovery in `main()` |
| `hephaestus/automation/worktree_manager.py` | Added `WorktreeDirtyError`; `preserve` list; `remove_worktree(force=False)` guard; `_print_summary()` preserved block |
| Tests | Updated/added tests for all three patterns |

### Test Results

```bash
pixi run pytest tests/unit -v
# 1403 passed, 0 failed (CI: PR #301)
```

### Label error pattern to match

```python
import re
LABEL_NOT_FOUND_RE = re.compile(r"could not add label: '([^']+)' not found")
```

### gh_list_open_issues() output format

```bash
gh issue list --state open --limit 500 --json number --jq '.[].number'
# → one integer per line: 301\n302\n303\n...
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #301, branch port-circuit-breaker-success-threshold | 1403 tests pass in CI |
