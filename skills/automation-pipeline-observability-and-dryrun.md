---
name: automation-pipeline-observability-and-dryrun
description: "Operational reliability of automation pipeline scripts (implement_issues.py, curses UI runners, Claude Code harness, multi-phase shell orchestrators). Use when: (1) dry-run mode leaks into post-implementation phases (PR creation, /learn, follow-up), (2) errors are swallowed or invisible in curses UI automation scripts, (3) execution logs are not persisted after worktree cleanup, (4) debugging implement_issues.py pipeline failures (git parsing, branch reuse, import errors), (5) auditing that runtime components are actually wired in the composition root and not structurally dead code, (6) a shell orchestrator fans out to multiple Python entry points and some phases declare --issues (or similar) as required=True while others auto-discover — uniform invocation produces silent argparse exit 2 in the required-arg phases."
category: debugging
date: 2026-05-24
version: "1.1.0"
user-invocable: false
verification: verified-precommit
history: automation-pipeline-observability-and-dryrun.history
tags: [dry-run, automation, implementer, curses-ui, error-visibility, log-persistence, composition-root, wiring, hephaestus, worktree, fan-out, argparse, orchestrator-contract, required-args]
---

# Automation Pipeline: Observability and Dry-Run Guard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Consolidate operational reliability patterns for automation pipelines: dry-run gating, error visibility, log persistence, pipeline bug fixes, and composition-root wiring audits |
| **Outcome** | SUCCESS — five complementary skills merged into one canonical reference |
| **Verification** | Verified across ProjectHephaestus (PR #271), ProjectScylla (PR #624, #633, issue #602), and Atlas audits |

## When to Use

- `--dry-run` leaks past the simulation phase into PR creation, `/learn`, or follow-up issue filing
- Workers in a curses UI go silently from "active" to `[idle]` with no visible error
- Retrospective or follow-up subprocess output disappears after worktree cleanup
- `implement_issues.py` fails with git parsing errors, "branch already exists", or import errors
- Tests pass but a feature is "done but not working" — metrics read zero, alerts never fire
- Before releasing any multi-phase CLI tool or tagging a version: verify every runtime component is wired in `cmd/` / `main`

## Verified Workflow

### Quick Reference

**Dry-run guard** — add ONE early return at the worker level after the simulation phase:

```python
session_id = self._run_claude_code(...)   # returns None in dry-run
with self.state_lock:
    state.session_id = session_id
self._save_state(state)

if self.options.dry_run:
    self._log("info", f"[DRY RUN] Skipping PR creation, learn, follow-up for #{issue_number}", thread_id)
    return WorkerResult(issue_number=issue_number, success=True,
                        branch_name=branch_name, worktree_path=str(worktree_path))

# Only reached in non-dry-run mode:
self._ensure_pr_created(...)
self._run_learn(...)
self._file_follow_up_issues(...)
```

**Dual-logging helper** — route to both standard logger and curses UI:

```python
def _log(self, level: str, msg: str, thread_id: int | None = None) -> None:
    getattr(logger, level)(msg)
    tid = thread_id or threading.get_ident()
    prefix = {"error": "ERROR", "warning": "WARN", "info": ""}.get(level, "")
    ui_msg = f"{prefix}: {msg}" if prefix else msg
    self.log_manager.log(tid, ui_msg)
```

**Log persistence** — save subprocess output on ALL exit paths:

```python
self.state_dir.mkdir(parents=True, exist_ok=True)
log_file = self.state_dir / f"claude-{issue_number}.log"
try:
    result = run([...], timeout=1800)
    log_file.write_text(result.stdout or "")
except subprocess.CalledProcessError as e:
    log_file.write_text(f"EXIT CODE: {e.returncode}\n\nSTDOUT:\n{e.stdout or ''}\n\nSTDERR:\n{e.stderr or ''}")
    raise RuntimeError(f"Claude Code failed: {e.stderr or e.stdout}") from e
except subprocess.TimeoutExpired as e:
    log_file.write_text(f"TIMEOUT after {e.timeout}s\n\nOutput:\n{e.output or ''}")
    raise RuntimeError("Claude Code timed out") from e
```

**Composition-root wiring grep** (Go; adapt for other languages):

```bash
grep -rn "pkg.New" cmd/ --include='*.go' | grep -v '_test.go'
# Zero hits = structurally dead code
```

**Fan-out orchestrator argument contract** — shell-side discovery, two-tier fix:

```bash
# Once per repo per loop, discover open issues ONCE:
local OPEN_ISSUES=()
mapfile -t OPEN_ISSUES < <(
  gh issue list --repo "$ORG/$repo" --state open --limit 200 \
    --json number --jq '.[].number' 2>/dev/null
)
local ISSUE_ARGS=()
[[ ${#OPEN_ISSUES[@]} -gt 0 ]] && ISSUE_ARGS=(--issues "${OPEN_ISSUES[@]}")

# Pass ISSUE_ARGS ONLY to required-arg phases (review-plans, review-prs,
# address-review, drive-green). Auto-discovering phases (plan, implement)
# must NOT receive --issues — they poll mid-loop for newly opened issues.
"$PYTHON" "$SCRIPT_DIR/review_plans.py" "${ISSUE_ARGS[@]}" -v $DRY_RUN_FLAGS \
  || echo "  [$repo] Warning: review-plans exited non-zero (loop $loop)"
```

Verify the contract before trusting the orchestrator:

```bash
grep -nE "add_argument\([\"']--issues[\"'].*required=True" \
  $(find . -name "*.py" -path "*/automation/*")
# Any hit = orchestrator MUST pass --issues to that phase
```

### 1. Dry-Run Guard for Multi-Phase CLI Tools

Locate the simulation phase, save any required state, then add an explicit early return before all side-effect phases. Do **not** rely on each downstream method to check the flag.

1. Identify where `_run_claude_code()` (or equivalent) returns `None` in dry-run mode.
2. Save state (e.g., `session_id`) before the guard so checkpoints reflect the dry-run attempt.
3. Return a proper success result object — callers expect it for aggregation.
4. Log clearly with `[DRY RUN]` listing exactly what was skipped.
5. Verify no side effects: no PR, no worktree left behind, no `/learn` committed, no follow-up issues filed.

### 2. Curses UI Error Visibility

1. **Add `_log()` dual-logging helper** as an instance method on the implementer class (not a module-level function — needs `self.log_manager`).
2. **Propagate `slot_id`/`thread_id`** through all sub-methods (`_run_claude_code`, `_ensure_pr_created`, `_run_retrospective`, `_run_follow_up_issues`).
3. **Add granular status updates** — replace 5 coarse phases with 12+ sub-steps via `status_tracker.update_slot()`.
4. **Show failure before releasing slot** — update slot to `"#N: FAILED - {error[:50]}"` inside the except block; call `time.sleep(1)` in `finally` before `release_slot()`.
5. **Classify exceptions** by type: `TimeoutExpired`, `CalledProcessError`, `RuntimeError`, `Exception` — each produces a different error message.
6. **Timeout all CLI calls** — `gh` CLI: 120 s, Claude Code: 1800 s, retrospective: 600 s.
7. **Broaden exception handling** for optional/non-critical paths (e.g., auto-merge): catch `Exception`, not only `CalledProcessError`.

#### Granular Status Update Sequence (12+ steps)

1. `#N: Creating worktree`
2. `#N: Checking plan`
3. `#N: Generating plan` (conditional)
4. `#N: Fetching issue`
5. `#N: Running Claude Code`
6. `#N: Checking commit`
7. `#N: Pushing branch`
8. `#N: Creating PR`
9. `#N: Running retrospective`
10. `#N: Identifying follow-ups`
11. `#N: Creating follow-up 1/N`
12. `#N: Creating follow-up N/N`

### 3. Log Persistence for Post-Mortem Analysis

1. **File logging for Python logger**: Add `FileHandler` to write all `logger.*()` output to `.issue_implementer/run.log`.
2. **Per-phase log files**: Write subprocess stdout/stderr to `claude-{N}.log`, `retrospective-{N}.log`, `follow-up-{N}.log`.
3. **Save on ALL exit paths** — success, `CalledProcessError`, and `TimeoutExpired`. Failures are what need debugging.
4. **Always call `mkdir(parents=True, exist_ok=True)`** before writing any log file (prevents `FileNotFoundError` in tests and on first run).
5. **Testing**: Use real file I/O with `tmp_path`, not `Path.write_text` mocks — patching causes infinite recursion.

#### Log Directory Layout

```text
.issue_implementer/
├── run.log                  # Full Python logger output (all phases, all issues)
├── claude-123.log           # Claude Code output for issue #123
├── retrospective-123.log    # Retrospective output for issue #123
├── follow-up-123.log        # Follow-up issues output for issue #123
└── issue-123.json           # State file for issue #123
```

### 4. Fixing implement_issues.py Pipeline Bugs

| Bug | Symptom | Fix |
| --- | --- | --- |
| Git status parsing | Files truncated (`ests/unit/...` instead of `tests/unit/...`) | Use `line[3:]` not `line[3:].strip()` — `.strip()` removes the first real character |
| Branch already exists | `fatal: a branch named '595-auto-impl' already exists` | Check `git rev-parse --verify <branch>` before `git worktree add -b`; reuse existing branch without `-b` |
| Branch not pushed | `Branch N-auto-impl not found on origin` | Fallback: push automatically instead of raising; verify-and-fallback beats strict verify-or-fail |
| Import error | `cannot import name 'gh_call'` | Use `_gh_call` (private); parse JSON from `result.stdout` |
| Claude hangs | Automation blocks indefinitely | Add `--permission-mode dontAsk` and `--allowedTools Read,Write,Edit,Glob,Grep,Bash` |

**Required `claude` CLI flags**:

```python
["claude", str(prompt_file),
 "--output-format", "json",
 "--permission-mode", "dontAsk",
 "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash"]
```

**Branch reuse pattern**:

```python
result = run(["git", "rev-parse", "--verify", branch_name], capture_output=True, check=False)
if result.returncode == 0:
    run(["git", "worktree", "add", worktree_path, branch_name])
else:
    run(["git", "worktree", "add", "-b", branch_name, worktree_path, base_branch])
```

### 5. Composition-Root Wiring Audit

The failure mode: a package has a complete implementation, passing tests, README mention, and populated `Config` — but `cmd/main.go` (or equivalent entry point) never calls the constructor or `Start(ctx)`. The package is structurally dead code in production.

1. **Enumerate runtime components** from `internal/` (subscribers, metrics, workers, validators, health checks, middleware).
2. **Grep the composition root** for each constructor symbol, excluding tests:

   ```bash
   grep -rn "pkg.New" cmd/ --include='*.go' | grep -v '_test.go'
   ```

   Zero hits = dead code. Document the package, constructor, and where it was expected to be wired.

3. **For metrics**, also grep mutator methods (`Inc`, `Observe`, `Set`) across non-test non-defining files — if the only hits are inside the defining file, the metric never moves.
4. **Verify goroutine launch**: confirm `go subscriber.Start(ctx)` not just `subscriber.Start(ctx)`.
5. **Build a wiring matrix** — one row per component, columns for: Defined? Tested? Constructed in `cmd/`? Lifecycle invoked?

#### Language Composition-Root Cheatsheet

| Language | Composition root | Constructor pattern | Lifecycle pattern |
| --- | --- | --- | --- |
| Go | `cmd/<binary>/main.go` | `pkg.New(`, `pkg.NewX(` | `.Start(ctx)`, `go pkg.Run(` |
| Python | `<pkg>/__main__.py`, `main.py` | `ClassName(`, `create_x(` | `.start()`, `await x.run()` |
| Rust | `src/main.rs`, `src/bin/*.rs` | `Type::new(`, `Builder::build()` | `.run().await`, `tokio::spawn(` |
| TypeScript | `src/index.ts`, `src/server.ts` | `new ClassName(`, `createX(` | `.start()`, `.listen(` |
| Mojo | top-level `fn main()` | `ClassName(`, factory fn | `.run()`, task spawn |

#### Drop-in Go wiring audit script

```bash
#!/usr/bin/env bash
# audit-wiring.sh — flag internal packages whose constructors are never
# called from cmd/. Run from repo root.
set -euo pipefail
CMD_DIR=${1:-cmd}
INTERNAL_DIR=${2:-internal}
echo "Composition-root wiring audit: $INTERNAL_DIR -> $CMD_DIR"
grep -rhn --include='*.go' --exclude='*_test.go' \
     -E '^func New[A-Z][A-Za-z0-9_]*\(' "$INTERNAL_DIR" \
  | sed -E 's/.*func (New[A-Za-z0-9_]+)\(.*/\1/' \
  | sort -u \
  | while read -r ctor; do
      hits=$(grep -rln --include='*.go' --exclude='*_test.go' "\b$ctor\b" "$CMD_DIR" || true)
      if [[ -z "$hits" ]]; then
        printf 'DEAD  %-40s (no call site in %s/)\n' "$ctor" "$CMD_DIR"
      fi
    done
```

Any line starting with `DEAD` is a release blocker until proven a deliberate library export.

### 6. Fan-Out Orchestrator Argument Contract (Auto-Discover vs Required-Arg Phases)

> **See also:** `debugging-silent-pipeline-stage-via-argparse-required-grep` covers
> the *diagnostic* (how to detect this bug class in ~60 seconds via source-grep).
> This section covers the *remediation* (the two-tier shell-side discovery pattern).

When a shell orchestrator fans out to multiple Python entry points across phases (plan,
review-plans, implement, review-prs, address-review, drive-green), the entry points are
*not* uniform. Some phases auto-discover open issues via `gh_list_open_issues()` when
`--issues` is omitted; others declare `--issues … required=True` in argparse and have no
auto-discovery fallback. Calling them uniformly without `--issues` and swallowing exit
codes with `|| echo "Warning"` makes the required-arg phases silently dead: argparse
exits with code 2 every loop, the operator sees "complete", and no work happens.

**Symptom**: orchestrator reports success; user thinks "only planning is running" — in
reality, planning and implementation work (they auto-discover), and 4 review-style phases
have been dead since the script was written.

**Root cause grep — verify the contract before trusting the orchestrator**:

```bash
# For every Python entry point the orchestrator calls, check argparse
grep -nE "add_argument\([\"']--issues[\"'].*required=True" \
  $(find . -name "*.py" -path "*/automation/*")
# Any hit = the orchestrator MUST pass --issues to that phase
```

**Two-tier fix — discover once per orchestration unit (per repo per loop) in the shell**:

```bash
# Once per repo per loop, AFTER rebase, BEFORE Phase 1
local OPEN_ISSUES=()
mapfile -t OPEN_ISSUES < <(
  gh issue list --repo "$ORG/$repo" --state open --limit 200 \
    --json number --jq '.[].number' 2>/dev/null
)
local ISSUE_ARGS=()
if [[ ${#OPEN_ISSUES[@]} -gt 0 ]]; then
  ISSUE_ARGS=(--issues "${OPEN_ISSUES[@]}")
fi
```

Then in each required-arg phase block (review-plans, review-prs, address-review, drive-green):

```bash
if phase_enabled review-plans; then
  if [[ ${#OPEN_ISSUES[@]} -eq 0 ]]; then
    echo "  [$repo] No open issues — skipping review-plans"
  else
    echo "  [$repo] Reviewing plans..."
    ( cd "$dir"
      "$PYTHON" "$SCRIPT_DIR/review_plans.py" \
        "${ISSUE_ARGS[@]}" \
        --max-workers "$MAX_WORKERS" -v $DRY_RUN_FLAGS \
        || echo "  [$repo] Warning: review-plans exited non-zero (loop $loop)"
    )
  fi
fi
```

**Do NOT** add `--issues` to auto-discovering phases (plan, implement) — they
intentionally poll for issues themselves so they can pick up issues opened mid-loop by
an earlier phase. The orchestration knowledge lives where it belongs: the shell.

**Why not push auto-discovery into the 4 required-arg `main()`s?** Larger blast radius:
4 argparse changes, 4 new code paths, downstream consumers (cron jobs, fleet wrappers)
inherit the new "called without --issues" surface area. Shell already owns per-repo
per-loop state — discovery belongs there.

**Distinguish argparse-2 from per-issue failures** — swallowing exit codes with
`|| echo "Warning: <phase> exited non-zero"` is uniform across both, which is what made
this bug invisible. Either:

- surface exit codes loudly with a per-repo error counter, or
- (better) make the contract impossible to violate via either uniform auto-discovery or
  shell-side discovery passed uniformly (the fix above).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Short-circuit only `_run_claude_code()` | Returned `None` from `_run_claude_code()` when `dry_run=True` | Execution continued to `_ensure_pr_created()` which called `gh pr create` on an empty branch, producing "No commits between main and `<branch>`" errors | A single method guard is not enough; the entire post-simulation pipeline must be skipped via an early return at the worker level |
| Check `dry_run` inside `_ensure_pr_created()` | Added `if self.options.dry_run: return` inside PR creation | Worked for PR creation but still ran `_run_learn()` and `_file_follow_up_issues()`, creating noise in skill files and issue trackers during testing | Each downstream method needs its own guard — brittle. One early return at the worker level is cleaner and more robust |
| Trust that empty `session_id` would prevent PR creation | Assumed `session_id = None` from `_run_claude_code()` would be checked before `_ensure_pr_created()` | `_ensure_pr_created()` did not check `session_id` before attempting PR creation | Never rely on implicit sentinel values flowing through to downstream steps; use explicit control flow |
| Use `line[3:].strip()` for git status parsing | Parsed filename portion of `git status --porcelain` output with `.strip()` | `.strip()` strips leading characters including the first letter of the filename, giving `ests/unit/...` instead of `tests/unit/...` | Understand exact byte positions before string manipulation; git porcelain format: positions 0-1 are status codes, position 2 is space, position 3+ is filename — no strip needed |
| Fail on unpushed branch | `raise RuntimeError("Not pushed")` when `branch_on_remote` was false | Pipeline aborted even when Claude simply forgot to push — a recoverable situation | Prefer verify-and-fallback over verify-or-fail for recoverable states; only raise on truly unrecoverable errors (e.g., no commit exists) |
| Trust "package exists + has tests = component works" | Earlier Atlas reviews graded the project healthy because `internal/nats.Subscriber` had complete implementation, 90%+ coverage, and architecture-doc mention | `cmd/argus-dashboard/main.go` never called `nats.New(...)` or `subscriber.Start(ctx)` — structurally dead code; SSE clients only received heartbeats | Test coverage is independent of production wiring. Always grep the composition root for the constructor symbol — exclude tests — before grading any component "done" |
| Trust the `/metrics` endpoint as evidence metrics work | `internal/server/AtlasMetrics` was defined, registered, and exposed at `/metrics`; endpoint returned valid Prometheus output | None of the `Inc*` / `Observe*` / `Set*` methods were called from production code — every counter permanently read zero; alerting rules referencing them could never fire | Endpoint reachability is not instrumentation correctness. Grep mutator methods excluding the defining package and tests; if only hits are inside the defining file, the metric is dead instrumentation |
| Hope reviewers catch wiring gaps during code review | Three rounds of human review on Atlas missed the gap for months | Wiring lives at the seam between PRs; per-PR review cannot catch "package added in PR A, never called from main.go modified in PR B" | Spine-wiring checks must be a release-gate audit step, not a reviewer-vibes check |
| Patch `Path.write_text` in tests | Mocked `Path.write_text` to avoid file I/O in unit tests for log persistence | Caused infinite recursion when the implementation itself called `write_text` during the test | Use real file I/O with `tmp_path` for log persistence tests; mock external processes, not file writes |
| Document the argument contract in the shell-script header | Added comment "Issue discovery is delegated to each phase's Python entrypoint (gh_list_open_issues)" and called all 6 phases of `run_automation_loop.sh` uniformly without `--issues` | The claim was only true for 2 of 6 phases (plan, implement); the other 4 (review-plans, review-prs, address-review, drive-green) declared `--issues … required=True` in argparse. Result: 4 phases failed argparse exit 2 silently every loop for months | Don't rely on header comments asserting an API contract — grep `required=True` against every entry point the orchestrator calls to verify the contract is real |
| Catch fan-out errors with `\|\| echo "Warning: <phase> exited non-zero"` | Same warning template for every phase's invocation in the orchestrator loop | argparse exit code 2 was swallowed identically to a real per-issue failure; the operator never saw the difference between "ran but found nothing" and "argparse rejected the invocation" | Either surface exit codes loudly with a per-repo error counter, or make orchestrator-pipeline contracts impossible to violate (uniform discovery in shell, or auto-discovery in every phase) — uniform warning-swallowing turns required-arg violations into invisible no-ops |
| Push auto-discovery into each required-arg `main()` (the "Option ii" approach) | Considered adding `if not args.issues: args.issues = gh_list_open_issues(...)` to all 4 required-arg phases | Larger blast radius: 4 argparse changes, 4 new code paths, downstream consumers (cron jobs, fleet wrappers) inherit the new "called without --issues" surface area | Push orchestration knowledge into the orchestrator, not into the phase. Shell already owns per-repo per-loop state — discovery belongs there. One mapfile + one ISSUE_ARGS array beats four argparse refactors |

## Results & Parameters

### Timeout Configuration

```python
GH_CLI_TIMEOUT      = 120    # seconds — gh CLI calls
CLAUDE_TIMEOUT      = 1800   # seconds — Claude Code invocation
RETROSPECTIVE_TIMEOUT = 600  # seconds — retrospective /learn phase
FOLLOW_UP_TIMEOUT   = 600    # seconds — follow-up issue filing
FAILURE_PAUSE       = 1      # seconds — show failure status before slot release
```

### UI Display Constants

```python
ERROR_TRUNCATE  = 50   # chars for error display in status slot
STDERR_TRUNCATE = 300  # chars for stderr in logs
LOG_PREFIXES    = {"error": "ERROR", "warning": "WARN", "info": ""}
```

### Dry-Run Phases After Fix

| Phase | Dry-Run Behavior | Non-Dry-Run Behavior |
| --- | --- | --- |
| `_run_claude_code()` | Returns `None` immediately | Runs Claude Code session |
| State save | Saves `session_id=None` to checkpoint | Saves real `session_id` |
| Early return guard | Returns `WorkerResult(success=True)` | Continues to next phase |
| `_ensure_pr_created()` | SKIPPED | Creates/updates PR |
| `_run_learn()` | SKIPPED | Commits skill to ProjectMnemosyne |
| `_file_follow_up_issues()` | SKIPPED | Files follow-up GitHub issues |

### Atlas Wiring Matrix (Example)

| Component | Defined? | Tested? | Constructed in `cmd/`? | Lifecycle invoked? | Status |
| --- | --- | --- | --- | --- | --- |
| `internal/nats.Subscriber` | yes | yes (90%+) | NO | NO | DEAD — fixed PR #444 |
| `internal/server.AtlasMetrics` | yes | yes | yes (struct) | NO mutators called | DEAD INSTRUMENTATION — fixed PR #445/#446 |
| Health-check registration | yes | yes | yes | yes | OK |
| Config validator | yes | yes | yes | yes | OK |

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectHephaestus | PR #271 — automation module dry-run guard; 596 tests pass | Dry-run across 14 repos confirmed no PRs created |
| ProjectScylla | PR #624 — implement_issues.py pipeline bug fixes; 199 tests pass | 6 commits: git parsing, branch reuse, fallback logic, import fix |
| ProjectScylla | PR #633 / Issue #632 — curses UI error visibility; 211 tests pass | Dual logging, granular status, exception classification |
| ProjectScylla | Issue #602 — log persistence; 30 tests pass (24 before) | Logs persisted to `.issue_implementer/` on all exit paths |
| Atlas (Go) | `/hephaestus:repo-analyze-strict-full` 2026-05-05 — wiring audit | Five dead-spine bugs caught; PRs #444–#448 merged; Atlas v0.2.0 shipped |
| ProjectHephaestus | PR #543 — `scripts/run_automation_loop.sh` fan-out argument contract; bash -n + ShellCheck + silent-failure-workaround pre-commit hook pass | Two-tier discovery: shell-side `mapfile` of open issues per repo per loop, passed via `${ISSUE_ARGS[@]}` to the 4 required-arg phases (review-plans, review-prs, address-review, drive-green); auto-discovering phases (plan, implement) unchanged. Verification: verified-precommit (CI gate pending merge) |
