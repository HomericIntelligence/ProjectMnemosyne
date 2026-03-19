---
name: pr-review-automation
description: 'TRIGGER CONDITIONS: Adding a new automation class that reviews and fixes
  open PRs via Claude Code. Use when: (1) building a PR fix workflow on top of implement_issues.py,
  (2) creating a two-phase Claude workflow (analysis then fix) for automated PR remediation,
  (3) adding new Enum/State/Options models to scylla/automation/models.py following
  existing patterns.'
category: tooling
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# pr-review-automation

How to implement the `--review` mode in `implement_issues.py` and the `PRReviewer` class for automating PR fix cycles in ProjectScylla. Documents the two-phase Claude workflow, PR discovery strategies, context gathering, and the SRP-clean class design.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Add `--review` mode to `implement_issues.py` to automate PR fix cycles (CI failures, review feedback) using a two-phase Claude workflow |
| Outcome | Success — 31 tests passing, all pre-commit hooks pass, PR #1321 created |
| Issue | HomericIntelligence/ProjectScylla#1320 |
| PR | HomericIntelligence/ProjectScylla#1321 |

## When to Use

- Building a new automation class on top of the existing `IssueImplementer` patterns
- Implementing a two-phase Claude workflow (read-only analysis → full-tools fix)
- Adding new CLI flags to `scripts/implement_issues.py` that branch to a new orchestrator
- Adding `Enum/State/Options` trios to `scylla/automation/models.py`
- Needing to gather GitHub PR context (diff, CI logs, review comments) programmatically

## Architecture: SRP Class Design

The key design decision: **`PRReviewer` is a new class, not an extension of `IssueImplementer`**. They share infrastructure (WorktreeManager, StatusTracker, CursesUI, ThreadLogManager) but have different workflows.

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

**Critical principle**: Phase 2 (fix session) always runs, even if analysis finds no problems. This ensures the fix Claude instance always runs with a fresh view.

## Verified Workflow

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

### Step 2: Add prompt templates to `prompts.py`

Two templates with `{variable}` placeholders and matching getter functions:

- `REVIEW_ANALYSIS_PROMPT` → `get_review_analysis_prompt(pr_number, issue_number, pr_diff, issue_body, ci_status, ci_logs, review_comments, pr_description, worktree_path)`
- `REVIEW_FIX_PROMPT` → `get_review_fix_prompt(pr_number, issue_number, plan, worktree_path)`

**Key prompt design rules**:
- Analysis prompt: instruct Claude to produce a **structured** fix plan with Summary, Problems Found, Fix Order, Verification sections
- Fix prompt: explicitly say "do NOT push — the script handles pushing"
- Fix prompt: specify commit message format with `Co-Authored-By`

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

Cap `pr_diff` at 8000 chars (avoids overloading Claude context window with huge diffs).

### Step 5: Analysis session — read-only tools

```python
result = run(
    ["claude", str(prompt_file),
     "--output-format", "json",
     "--permission-mode", "dontAsk",
     "--allowedTools", "Read,Glob,Grep,Bash"],  # NO Write/Edit
    cwd=worktree_path,
    timeout=1200,  # 20 minutes
)
# Extract plan from JSON result field
data = json.loads(result.stdout or "{}")
plan_text = data.get("result", result.stdout or "")
write_secure(plan_file, plan_text)
return str(plan_file)
```

Save plan to `.issue_implementer/review-plan-{issue}.md` using `write_secure` (atomic write).

### Step 6: Fix session — full tools, captures session_id

```python
result = run(
    ["claude", str(prompt_file),
     "--output-format", "json",
     "--permission-mode", "dontAsk",
     "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash"],  # Full tools
    cwd=worktree_path,
    timeout=1800,  # 30 minutes
)
data = json.loads(result.stdout or "{}")
session_id: str | None = data.get("session_id")
return session_id
```

**Important**: Declare `session_id: str | None` explicitly to satisfy mypy (avoids `no-any-return` error from `data.get()`).

### Step 7: Push fixes — script handles git, not Claude

```python
def _push_fixes(self, pr_number, issue_number, branch_name, worktree_path):
    # 1. Check for uncommitted changes and commit them
    result = run(["git", "status", "--porcelain"], ...)
    if result.stdout.strip():
        # Filter secret files, stage safe files, commit
        run(["git", "add", *files_to_add], ...)
        run(["git", "commit", "-m", commit_msg], ...)

    # 2. Push only if there are new commits
    result = run(["git", "log", f"origin/{branch_name}..HEAD", "--oneline"], ...)
    if result.stdout.strip():
        run(["git", "push", "origin", branch_name], ...)
```

### Step 8: CLI integration (`implement_issues.py`)

Add `--review` before `--epic` in `parse_args()`:

```python
parser.add_argument("--review", action="store_true",
    help="Review and fix open PRs linked to specified issues (requires --issues)")
```

Add validation after existing validation:

```python
if args.review and not args.issues:
    parser.error("--review requires --issues (not supported with --epic)")
if args.review and args.epic:
    parser.error("--review cannot be used with --epic")
```

In `main()`, branch **before** the `IssueImplementer` block:

```python
if args.review:
    from scylla.automation.reviewer import PRReviewer
    from scylla.automation.models import ReviewerOptions
    reviewer_options = ReviewerOptions(...)
    reviewer = PRReviewer(reviewer_options)
    results = reviewer.run()
    # check failed results, return exit code
    return 0

# Existing IssueImplementer code below...
```

### Step 9: Parallel review loop (no dependency ordering needed)

Unlike `_implement_all()` in `IssueImplementer`, PR review has no dependency ordering — all PRs are independent. Submit all at once:

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

## Failed Attempts

### Attempt 1: Wrapping the long error_output f-string in parentheses

**What failed**: Tried wrapping the long f-string in parentheses to satisfy E501:
```python
error_output = (
    f"EXIT CODE: {e.returncode}\n\nSTDOUT:\n{e.stdout or ''}\n\nSTDERR:\n{e.stderr or ''}"
)
```
Ruff formatter unwrapped the parentheses back to a single line. The string was still > 100 chars.

**Fix**: Extract variables first:
```python
stdout = e.stdout or ""
stderr = e.stderr or ""
error_output = f"EXIT CODE: {e.returncode}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
```

### Attempt 2: Using `# type: ignore[return-value]` for session_id

**What failed**: Added `# type: ignore[return-value]` but mypy reported it was (a) unused and (b) the actual error was `no-any-return`.

**Fix**: Declare the variable with an explicit type annotation:
```python
session_id: str | None = data.get("session_id")
return session_id  # no type: ignore needed
```

### Attempt 3: Prompts with content that includes curly braces

**What worked**: The `REVIEW_FIX_PROMPT` includes a commit message format block with `{variables}`. Since the prompt uses Python `.format()`, any literal braces in the prompt template would need to be doubled (`{{` and `}}`).

**Avoided by**: The commit message format uses backtick code blocks and the `{pr_number}` / `{issue_number}` placeholders in the format string are actual template variables (they should be replaced). No literal curly braces needed in the prompt string.

### Attempt 4: CI log fetch via `--branch --pr=N`

The CI log fetch command uses `gh run list --branch --pr={pr_number}`. In practice this flag combination may not work as expected with `gh` CLI — the `--branch` flag expects a branch name, not `--pr=N`. Wrapped in `contextlib.suppress(Exception)` so it degrades gracefully. Real integration testing needed.

## Results & Parameters

### Claude invocation parameters

| Session | Tools | Timeout | Output format |
|---------|-------|---------|---------------|
| Analysis | `Read,Glob,Grep,Bash` | 1200s (20 min) | `json` |
| Fix | `Read,Write,Edit,Glob,Grep,Bash` | 1800s (30 min) | `json` |
| Retrospective | `Read,Write,Edit,Glob,Grep,Bash` | 600s (10 min) | `--print` |

### State file locations

```
.issue_implementer/
  review-{issue}.json           # ReviewState (phase tracking)
  review-plan-{issue}.md        # Analysis plan output
  review-analysis-{issue}.log   # Analysis session stdout
  review-fix-{issue}.log        # Fix session stdout
  review-retrospective-{issue}.log  # Retrospective stdout
```

### CLI usage

```bash
# Review specific issues (finds their open PRs)
python scripts/implement_issues.py --review --issues 595 596

# Dry run (skips Claude calls, shows PR discovery)
python scripts/implement_issues.py --review --issues 595 --dry-run

# Disable retrospective
python scripts/implement_issues.py --review --issues 595 --no-retrospective

# More workers
python scripts/implement_issues.py --review --issues 595 596 597 --max-workers 3

# No UI (plain logging)
python scripts/implement_issues.py --review --issues 595 --no-ui
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
