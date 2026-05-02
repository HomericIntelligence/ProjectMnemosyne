---
name: pr-review-automation-workflow
description: "Use when: (1) building a PRReviewer class on top of implement_issues.py patterns, (2) implementing a two-phase Claude workflow (read-only analysis then full-tools fix) for automated PR remediation, (3) adding new Enum/State/Options models to an automation models.py, (4) running --review mode end-to-end in a live environment, (5) debugging nested Claude Code session failures caused by CLAUDECODE env var"
category: tooling
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# pr-review-automation-workflow

Implements and operates the `--review` mode in `implement_issues.py` and the `PRReviewer` class for automating PR fix cycles in ProjectScylla. Documents the two-phase Claude workflow, PR discovery strategies, context gathering, SRP-clean class design, and live integration operational patterns.

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-29 |
| Objective | Consolidated skill covering PRReviewer class implementation and live integration test results |
| Outcome | Success — two-phase review automation with CLAUDECODE env fix, 31 tests passing |
| Verification | unverified |

## When to Use

- Building a new automation class on top of the existing `IssueImplementer` patterns
- Implementing a two-phase Claude workflow (read-only analysis → full-tools fix)
- Adding new CLI flags to `scripts/implement_issues.py` that branch to a new orchestrator
- Adding `Enum/State/Options` trios to an automation `models.py`
- Gathering GitHub PR context (diff, CI logs, review comments) programmatically
- Running `--review` mode for the first time against a new environment
- Debugging why the review script fails when launched from inside Claude Code (CLAUDECODE env var)
- Understanding expected phase durations to set timeouts
- Choosing which PR to pick for testing (unit-tests-only failures are cleanest)

## Verified Workflow

### Quick Reference

```bash
# WRONG — fails if CLAUDECODE=1 is set (inside Claude Code CLI)
pixi run python scripts/implement_issues.py --review --issues 1216 --no-ui

# CORRECT — unset CLAUDECODE before launching
CLAUDECODE= pixi run python scripts/implement_issues.py --review --issues 1216 --no-ui

# First integration test: max-workers 1, no-ui for visibility
CLAUDECODE= pixi run python scripts/implement_issues.py \
  --review --issues <N> --max-workers 1 --no-ui 2>&1 | tee output.log
```

### Step 1: Add models to `models.py`

Three new types follow the existing `ImplementationPhase`/`ImplementationState`/`ImplementerOptions` pattern:

```python
class ReviewPhase(str, Enum):
    ANALYZING = "analyzing"
    FIXING = "fixing"
    PUSHING = "pushing"
    RETROSPECTIVE = "retrospective"
    COMPLETED = "completed"
    FAILED = "failed"

class ReviewState(BaseModel):
    issue_number: int
    pr_number: int
    phase: ReviewPhase = ReviewPhase.ANALYZING
    worktree_path: str | None = None
    branch_name: str | None = None
    plan_path: str | None = None
    session_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None

class ReviewerOptions(BaseModel):
    issues: list[int] = Field(default_factory=list)
    max_workers: int = 3
    dry_run: bool = False
    enable_retrospective: bool = True
    enable_ui: bool = True
```

### Step 2: Architecture — SRP Class Design

`PRReviewer` is a new class, not an extension of `IssueImplementer`. They share infrastructure but have different workflows:

```
PRReviewer
├── run()                      # Entry point: discover + parallel review
├── _discover_prs()            # issue[] → {issue: pr} map
├── _find_pr_for_issue()       # Branch-name lookup → body-search fallback
├── _review_all()              # ThreadPoolExecutor parallel loop
├── _review_pr()               # Per-PR 5-phase workflow
│   ├── Phase 1: _gather_pr_context()    # gh pr diff/view/checks + fetch_issue_info
│   ├── Phase 2: _run_analysis_session() # Claude (Read,Glob,Grep,Bash), saves plan
│   ├── Phase 3: _run_fix_session()      # Claude (Read,Write,Edit,Glob,Grep,Bash)
│   ├── Phase 4: _push_fixes()           # Script commits+pushes (not Claude)
│   └── Phase 5: _run_retrospective()    # Optional, resumes fix session
├── _save_state()              # Atomic write to .issue_implementer/review-{N}.json
└── _get_or_create_state()     # Thread-safe state access
```

**Critical principle**: Phase 3 (fix session) always runs, even if analysis finds no problems. This ensures the fix Claude instance always runs with a fresh view.

### Step 3: PR discovery strategy (two-tier)

```python
def _find_pr_for_issue(self, issue_number: int) -> int | None:
    # Strategy 1: Branch name lookup (fast, exact)
    branch_name = f"{issue_number}-auto-impl"
    result = _gh_call(["pr", "list", "--head", branch_name,
                       "--state", "open", "--json", "number", "--limit", "1"],
                      check=False)
    # ... return if found

    # Strategy 2: Body search (fallback)
    result = _gh_call(["pr", "list", "--state", "open",
                       "--search", f"#{issue_number} in:body",
                       "--json", "number", "--limit", "5"],
                      check=False)
    # ... return first result if found

    return None  # Not found
```

Use `check=False` on all discovery calls — missing PRs should return `None`, not raise.

### Step 4: Context gathering with graceful degradation

Wrap each `_gh_call` in `contextlib.suppress(Exception)` — partial context is better than a crash:

```python
context: dict[str, str] = {"pr_diff": "", "issue_body": "", ...}

with contextlib.suppress(Exception):
    result = _gh_call(["pr", "diff", str(pr_number)], check=False)
    context["pr_diff"] = (result.stdout or "")[:8000]  # Cap long diffs

with contextlib.suppress(Exception):
    result = _gh_call(["pr", "view", str(pr_number),
                       "--json", "body,reviews,comments"])
    pr_data = json.loads(result.stdout or "{}")
    # ... aggregate review_comments from reviews[] and comments[]
```

Cap `pr_diff` at 8000 chars to avoid overloading Claude context window.

### Step 5: Analysis session — read-only tools

```python
result = run(
    ["claude", str(prompt_file),
     "--output-format", "json",
     "--permission-mode", "dontAsk",
     "--allowedTools", "Read,Glob,Grep,Bash"],  # NO Write/Edit
    cwd=worktree_path,
    timeout=1200,  # 20 minutes
    env=env,       # env with CLAUDECODE stripped
)
data = json.loads(result.stdout or "{}")
plan_text = data.get("result", result.stdout or "")
write_secure(plan_file, plan_text)
```

Save plan to `.issue_implementer/review-plan-{issue}.md` using `write_secure` (atomic write).

### Step 6: Fix session — full tools, captures session_id

```python
result = run(
    ["claude", str(prompt_file),
     "--output-format", "json",
     "--permission-mode", "dontAsk",
     "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash"],
    cwd=worktree_path,
    timeout=1800,  # 30 minutes
    env=env,
)
data = json.loads(result.stdout or "{}")
session_id: str | None = data.get("session_id")  # explicit type to satisfy mypy
return session_id
```

### Step 7: Strip CLAUDECODE for nested claude subprocesses

Claude Code sets `CLAUDECODE=1` in all child processes. When the review script spawns a new `claude` subprocess, it refuses with a nested session error. Fix:

```python
import os

# Strip CLAUDECODE so nested claude subprocess can launch
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

result = run(
    ["claude", str(prompt_file), "--output-format", "json", ...],
    cwd=worktree_path,
    timeout=1200,
    env=env,
)
```

Apply this in both `_run_analysis_session` and `_run_fix_session`.

### Step 8: Push fixes — script handles git, not Claude

```python
def _push_fixes(self, pr_number, issue_number, branch_name, worktree_path):
    result = run(["git", "status", "--porcelain"], ...)
    if result.stdout.strip():
        run(["git", "add", *files_to_add], ...)
        run(["git", "commit", "-m", commit_msg], ...)

    result = run(["git", "log", f"origin/{branch_name}..HEAD", "--oneline"], ...)
    if result.stdout.strip():
        run(["git", "push", "origin", branch_name], ...)
```

### Step 9: CLI integration (`implement_issues.py`)

Add `--review` before `--epic` in `parse_args()`:

```python
parser.add_argument("--review", action="store_true",
    help="Review and fix open PRs linked to specified issues (requires --issues)")
```

Validate and branch in `main()` before the `IssueImplementer` block:

```python
if args.review:
    from scylla.automation.reviewer import PRReviewer
    from scylla.automation.models import ReviewerOptions
    reviewer = PRReviewer(ReviewerOptions(...))
    results = reviewer.run()
    return 0
```

### Step 10: Parallel review loop

Unlike `_implement_all()`, PR review has no dependency ordering — all PRs are independent:

```python
with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
    futures = {executor.submit(self._review_pr, issue, pr): issue
               for issue, pr in pr_map.items()}
    while futures:
        done, _ = wait(futures.keys(), timeout=1.0, return_when=FIRST_COMPLETED)
        for future in done:
            issue_num = futures.pop(future)
            results[issue_num] = future.result()
```

### Step 11: Live integration — choosing a test target

```bash
# Find PRs with only unit test failures (best first target)
for pr in $(gh pr list --state open --json number --jq '.[].number' | head -10); do
  echo "=== PR #$pr ==="
  gh pr checks $pr 2>&1 | grep -E "fail|pass" | head -4
done
```

Best first target: unit tests failing, pre-commit passing → cleanest failure mode.

### Step 12: Successful run log sequence

```
[INFO] Starting PR review for issues: [N]
[INFO] Found PR #XXXX for issue #N via branch name
[INFO] Created worktree for issue #N at .../.worktrees/issue-N
  ~5.5 min: Analysis session (Phase 1)
[INFO] Analysis complete for PR #XXXX, plan saved
  ~2.9 min: Fix session (Phase 2)
[INFO] Pushing 1 commit(s) to PR #XXXX
  ~2 min: push (pre-commit hooks run remotely)
  ~2 min: Retrospective (Phase 3)
[INFO] PR #XXXX review complete for issue #N
[INFO] PR Review Summary: Total PRs: 1, Successful: 1, Failed: 0
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running review inside Claude Code | Called `pixi run python scripts/implement_issues.py --review` from within a Claude Code session | `CLAUDECODE=1` causes nested claude subprocess to refuse launch | Always unset `CLAUDECODE` or strip it in the subprocess env |
| Using `data.get("session_id")` without type annotation | Called `data.get("session_id")` and returned result directly | mypy `no-any-return` error because `.get()` returns `Any` | Declare `session_id: str \| None = data.get("session_id")` explicitly |

## Results & Parameters

### Claude invocation parameters

| Session | Tools | Timeout | Output format |
| --------- | ------- | --------- | --------------- |
| Analysis | `Read,Glob,Grep,Bash` | 1200s (20 min) | `json` |
| Fix | `Read,Write,Edit,Glob,Grep,Bash` | 1800s (30 min) | `json` |
| Retrospective | `Read,Write,Edit,Glob,Grep,Bash` | 600s (10 min) | `--print` |

### Phase timings (observed, single PR)

| Phase | Duration | Notes |
| ------- | ---------- | ------- |
| PR discovery | ~1s | Branch-name lookup fast path |
| Worktree creation | ~1s | Branch reused if exists |
| Analysis session | ~5.5 min | Claude reads code, CI logs, produces plan |
| Fix session | ~2.9 min | Claude implements plan, runs tests, commits |
| Push | ~2 min | Includes remote pre-commit hook execution |
| Retrospective | ~2 min | Optional |
| **Total** | **~12.5 min** | Single PR, max-workers=1 |

### State file locations

```
.issue_implementer/
  review-{issue}.json           # ReviewState (phase tracking)
  review-plan-{issue}.md        # Analysis plan output
  review-analysis-{issue}.log   # Analysis session stdout
  review-fix-{issue}.log        # Fix session stdout
  review-retrospective-{issue}.log
```

### CLI usage

```bash
# Review specific issues (finds their open PRs)
python scripts/implement_issues.py --review --issues 595 596

# Dry run (skips Claude calls, shows PR discovery)
python scripts/implement_issues.py --review --issues 595 --dry-run

# Recommended for first test
CLAUDECODE= pixi run python scripts/implement_issues.py \
  --review --issues <N> --max-workers 1 --no-ui 2>&1 | tee output.log
```

### Test structure (31 tests)

```
TestReviewerOptions    (2)  — defaults, custom values
TestReviewState        (2)  — default phase, all phases exist
TestPRDiscovery        (6)  — branch lookup, search fallback, no-PR, multiple issues, exception, empty
TestGatherPRContext    (3)  — all fields, partial failure, diff cap
TestRunAnalysisSession (5)  — creates plan, read-only tools, dry run, timeout, process error
TestRunFixSession      (5)  — captures session_id, full tools, dry run, timeout, missing plan
TestReviewPR           (8)  — success, slot failure, analysis fail, fix fail, push fail, state FAILED, retrospective skip/call
```

### What still needs testing

- Multi-PR parallel execution (`--max-workers > 1`)
- Body-search fallback (PR not on `{issue}-auto-impl` branch)
- PRs with both pre-commit AND test failures
- Push with no new commits (Claude committed inside session)
- Retrospective disabled (`--no-retrospective`)
