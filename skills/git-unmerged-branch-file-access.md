---
name: git-unmerged-branch-file-access
description: "Access and plan fixes for files that exist only on non-main git branches, and never declare a cited file 'phantom' until you have searched all branches. Use when: (1) Read/Glob/Grep return not-found for a file an issue references, so you are tempted to call it non-actionable / phantom code, (2) planning a 'follow-up from #NNN' bug whose cited file/symbol is absent from the default branch (it likely came from a parent PR that has not merged), (3) a PR fix must target a feature branch rather than main, (4) an issue cites a raw line number that no longer matches the branch tip (line drift)."
category: architecture
date: 2026-06-20
version: "2.0.0"
user-invocable: false
verification: verified-local
history: git-unmerged-branch-file-access.history
tags:
  - unmerged-branch
  - follow-up-issue
  - phantom-code
  - git-log-all
  - git-show
  - line-number-drift
  - planning
  - feature-branch
  - pr-base
  - carrier-branch
---

# Git Unmerged Branch File Access

**History:** [changelog](./git-unmerged-branch-file-access.history)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Read and plan fixes for files/symbols that exist only on non-main feature branches, and avoid the "phantom code" misdiagnosis when a cited file is absent from the default branch |
| **Outcome** | Successful recovery — a "follow-up bug" issue (#283) cited `mcp_server.py:82`, absent from `main`; `git log --all` found the file on the unmerged `173-auto-impl` branch (commit `07ea99a`), and the plan was re-scoped to target that branch |
| **Verification** | verified-local (investigation steps executed this session; downstream code fix is plan-only — see caveats) |

> **Verification split — read this.** The git-history **investigation** workflow below is
> `verified-local`: `git log --all`, `git branch --all --contains`, and `git show <sha>:<path>`
> were ACTUALLY run this session and produced the cited results (carrier commit `07ea99a` on
> branch `173-auto-impl`). The downstream **code fix** was NOT executed — it is plan-only.
> The fix-stage assumptions are recorded as explicit `unverified` caveats in
> [Results & Parameters](#results--parameters); treat those as hypotheses, not facts.

## When to Use

- `Read`, `Glob`, or `Grep` returns "not found" for a file you expect to exist, and you are
  about to conclude the issue is **non-actionable / references phantom code** — STOP and run
  this workflow first.
- Planning a **"follow-up from #NNN"** / refinement / cited-line-number bug fix where the
  referenced file or symbol is **not on the default branch**. Follow-up issues are frequently
  filed against code from a PARENT PR that has not yet merged.
- A PR fix must target a feature branch (e.g., `173-auto-impl`) instead of `main`.
- Planning a fix for code visible in a PR diff but absent from the working tree.
- An issue cites a **raw line number** that no longer matches the branch tip (line drift).

## Verified Workflow

> **Verified-local:** every command in this section was run this session against the
> ProjectTelemachy #283 carrier branch and produced the cited results. Do NOT skip step 1
> just because Glob/Grep already "proved" the file is missing — those tools only see the
> checked-out branch.

### Quick Reference

```bash
# 0. NEVER conclude "phantom code" from Glob/Grep alone. They only see the working tree
#    (the checked-out branch). Always run the all-branches search BEFORE declaring absence.

# 1. Find the carrier commit by PATH across ALL branches (local + remote):
git log --all --oneline -- "**/mcp_server.py"
#   → 07ea99a feat: add MCP server (#173)

# 1b. ...and by PARENT-ISSUE grep (follow-ups cite their parent PR/issue):
git log --all --oneline --grep="#173"

# 2. Identify which branch(es) carry that commit:
git branch -a --contains 07ea99a
#   → remotes/origin/173-auto-impl

# 3. Read the file content WITHOUT checking out the branch:
git show 07ea99a:src/telemachy/mcp_server.py
git show origin/173-auto-impl:src/telemachy/mcp_server.py   # branch-ref form

# 4. List what the commit changed:
git show --stat 07ea99a

# 5. Cite by SYMBOL, not raw line number (line numbers drift between the issue
#    snapshot and the branch tip — issue said line 82; actual was line 81):
git show origin/173-auto-impl:src/telemachy/mcp_server.py | grep -n "def call_tool\|class Dispatcher"

# 6. Scope the plan to the CARRIER branch:
git checkout -b fix/<description> origin/173-auto-impl
gh pr create --base 173-auto-impl --title "fix: ..."   # NOT --base main
```

### Detailed Steps

1. **Detect the problem — and resist the phantom-code conclusion.** If `Read`, `Glob`, or
   `Grep` returns not-found for a file an issue references, the file most likely lives on a
   feature branch not yet merged to `main`. The file-read tools operate on the **working tree
   (the checked-out branch)** and cannot see other branches. Do NOT mark the issue
   non-actionable yet.

2. **Find the carrier commit — search by path AND by parent issue.** A follow-up issue
   ("follow-up from #NNN") was usually filed against code from a parent PR. Search both ways:
   ```bash
   git log --all --oneline -- "**/<file>"
   git log --all --oneline --grep="#<parent-issue>"
   ```

3. **Identify the carrier branch:**
   ```bash
   git branch -a --contains <sha>
   ```
   If it only appears under `remotes/origin/<feature-branch>`, the file is not on `main`.

4. **Read the file without switching branches** using `git show <sha>:<path>` (or
   `git show origin/<branch>:<path>`). This lets you read and analyze the real content even
   though it never exists in your working tree.

5. **Cite findings by SYMBOL, not raw line number.** Line numbers in the issue body reflect
   the snapshot at filing time and drift as the branch advances. In #283 the issue said
   line 82 but the defect symbol was at line 81 on the branch tip. Reference
   `Dispatcher.call_tool` (or the equivalent symbol), not "line 82", so the plan stays correct
   regardless of drift.

6. **Scope the plan to the carrier branch.** The fix branch MUST fork from the carrier feature
   branch, and the PR base MUST be that branch — a branch off `main` would have **no file to
   edit**. State this explicitly in the plan and PR body so the reviewer understands why the
   base is not `main`.
   ```bash
   git checkout -b fix/<description> origin/<feature-branch>
   gh pr create --base <feature-branch> --title "fix: ..."
   ```
   The merged feature-branch PR will carry the fix to `main` when it eventually lands.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Concluded the issue was non-actionable / phantom code | Ran Glob + Grep over `src/` for the cited file, found nothing, and was about to mark the cited code nonexistent | Searched only the working tree / default branch; the file lived on an unmerged feature branch (`173-auto-impl`, commit `07ea99a`) | Always `git log --all -- <file>` (and `--grep="#<parent>"`) before declaring referenced code nonexistent |
| Trusted the issue's raw cited line number | Planned to point the fix at `mcp_server.py:82` as written in the issue | The symbol was actually at line 81 on the branch tip; line numbers drift between the issue-filing snapshot and the carrier branch's current state | Cite findings by SYMBOL (e.g. `Dispatcher.call_tool`), not raw line numbers |
| Direct Read tool | Used Read/Glob/Grep with the expected file path | File not found — silently returns nothing because the file only exists on a feature branch | File-read tools operate on the checked-out branch; they cannot see files on other branches |
| Assuming the file should exist on `main` | Proceeded as if the file was missing from the repo entirely | Wasted planning cycles trying to understand why a referenced file didn't exist | Follow-up issues are commonly filed against a parent PR's code that has not yet merged; check all branches |
| Planning the fix as a branch off `main` | Implicitly assumed the PR base would be `main` | A branch off `main` has no copy of the file to edit; the change could not be made there | Branch-from / PR-target must be the carrier feature branch, not `main`; note this in the plan and PR body |

## Results & Parameters

When the file is found via `git show`, record:

- The SHA of the carrier commit (`07ea99a`).
- The carrier branch (`origin/173-auto-impl`, from `git branch -a --contains`).
- Whether it is a remote tracking branch (`origin/<branch>`) or local.
- The SYMBOL the defect lives in, plus the branch-tip line for orientation only (expect drift).

For PR targeting:

- If the file only exists on `origin/<feature-branch>`, the fix PR **must** base off that
  feature branch: `gh pr create --base <feature-branch>` — not `--base main`.
- State in the PR body that the base is the carrier branch and why (file absent from `main`).

### Unverified fix-stage caveats (carry forward as risks, not facts)

These are from the ProjectTelemachy #283 plan; the investigation above is verified, but the
fix below was never executed:

- **MCP SDK exception handling is the single most uncertain assumption.** The plan assumes the
  MCP SDK's `@server.call_tool()` decorator catches handler exceptions and converts them to a
  structured `isError` result rather than crashing the stdio process. This was NOT verified
  against the installed `mcp` SDK version — it is inferred from the module's own docstring
  `_SDK_API_NOTES` and general MCP SDK behavior. **If false, raising `ValueError` alone may not
  keep the server alive, and a returned `TextContent` error may be required instead.**
- **Test/runner reliance is unexecuted.** The plan relies on `pixi run pytest` / `just test` /
  `just lint` and on the existing test layout (`tests/test_mcp_server.py`) as they exist on the
  feature branch — these were read via `git show`, NOT checked out and NOT executed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectTelemachy | Issue #283 — "follow-up bug" citing `mcp_server.py:82`, absent from `main` | `git log --all` found the file on unmerged `173-auto-impl` (commit `07ea99a`); plan re-scoped to that branch; defect symbol at line 81 (issue said 82 — drift). Investigation verified-local; fix plan-only |
| ProjectHephaestus | Issue #1300 planning (`severity_label.py` GITHUB_REPOSITORY KeyError) | File existed only on `1210-auto-impl` branch; discovered via `git log --all` (v1.0.0, unverified) |
