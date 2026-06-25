---
name: github-issue-workflow-and-preflight-gates
description: "Use when: (1) starting work on any GitHub issue — run preflight checks to avoid duplicate implementation, (2) building or maintaining automated preflight safety gates in issue-implementation workflows, (3) filing 10–40 audit findings as a tracked GitHub issue queue with a parent tracker, (4) filing issues that cite repo-internal markdown docs — push docs to origin/main first so URLs resolve on first render, (5) posting structured progress updates or completion summaries to GitHub issues, (6) filing a feature request against a third-party OSS repo with a proposed patch and duplicate check, (7) verifying an already-resolved issue and closing it with grep evidence, (8) the duplicate-search before filing often reshapes scope — finding an existing issue may convert 'file N issues' into 'comment on K existing + file (N-K) new', (9) a transient validation transcript captures a real unresolved bug and should become a durable GitHub bug issue instead of a checked-in artifact"
category: tooling
date: 2026-06-17
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: github-issue-workflow-and-preflight-gates.history
tags: [github, issues, preflight, duplicate-prevention, workflow, bulk-filing, tracker, audit, progress-update, upstream, feature-request, safety-gates, automation, validation-artifacts, bug-template]
---

# GitHub Issue Workflow and Preflight Gates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-17 |
| **Objective** | Consolidate GitHub issue lifecycle disciplines: preflight duplicate-prevention checks, automated safety gates, bulk audit-to-issue filing, doc-push-before-filing ordering, structured progress updates, and upstream OSS feature requests |
| **Outcome** | Covers the full operational workflow around GitHub issues — from "verify before starting" to "post structured completion update"; now includes converting transient validation transcripts into durable bug issues without committing the transcript |
| **Verification** | verified-ci |
| **History** | [changelog](./github-issue-workflow-and-preflight-gates.history) |
| **Key Learning** | Always run preflight checks (~6 s) before any implementation; stage issue bodies as local files before bulk filing; push repo-internal docs to `origin/main` before filing issues that cite them; unresolved bugs from validation artifacts belong in GitHub issues using the repo template |

Consolidates: `preflight-verify-before-implementing`, `preflight-script-integration-patterns`,
`documentation-bulk-audit-issue-filing`, `push-docs-before-filing-issues`,
`gh-post-issue-update`, `file-upstream-feature-request`.

## When to Use

- **Preflight (manual)**: Before starting work on any GitHub issue, branch, worktree, or auto-impl prompt file; when resuming interrupted work
- **Preflight (automated)**: Adding safety gates to `gh-implement-issue`, `worktree-create`, or similar workflows; fixing false positives in `gh pr list --search` based checks
- **Bulk audit filing**: After running `/repo-analyze*` or any multi-section audit with 10–40 findings you want as a tracked GitHub issue queue
- **Doc-push-first**: Filing N>5 issues that cite repo-internal markdown not yet on `origin/main`; issues that cross-reference each other by GitHub number
- **Progress updates**: Reporting implementation progress, design decisions, blockers, or completion summaries to a GitHub issue
- **Upstream feature requests**: Filing a feature/bug against a third-party OSS repo with a proposed patch gist and duplicate check; even when the task says "file N issues" — the duplicate-search pass can collapse scope (e.g., turn "file 2 issues" into "comment on 1 existing + file 1 new")
- **Verify-and-close**: An issue is suspected to be already resolved — verify absence of the removed content with grep, confirm replacement content exists at path:line, comment the evidence on the issue, then close it
- **Validation artifact cleanup**: A PR or branch contains ad hoc validation transcripts (`artifacts/*validation*.md`) that should not be checked in, but one transcript records a real unresolved bug; file the bug with the repo's issue template, then delete the transient artifact and update docs/tests to reference the durable issue number

**Don't use when:**
- Filing 1–3 standalone issues with no cross-references — manual filing is fine
- Docs already on `main` — skip the doc-push phase; file directly
- Filing 200+ issues across many repos — see `github-bulk-issue-filing-rate-limit-recovery` instead

## Verified Workflow

### Quick Reference

```bash
# ── PREFLIGHT: run these 5 checks before ANY implementation (~6 s total) ──

# 1. Check current branch commits (catches auto-impl duplicates)
git log --oneline -5

# 2. Check issue state (stop immediately if CLOSED)
gh issue view <issue-number> --json state,title,closedAt

# 3. Check for existing PR on this branch
gh pr list --head $(git branch --show-current)

# 4. Search all PRs and commits for this issue
gh pr list --search "<issue-number>" --state all --json number,title,state
git log --all --oneline --grep="<issue-number>" | head -5

# 5. Check for worktree/branch conflicts
git worktree list | grep "<issue-number>"
git branch --list "*<issue-number>*"

# ── AUTOMATED PREFLIGHT SCRIPT (closingIssuesReferences — no false positives) ──

# Precise PR-issue ownership check (avoids free-text false positives)
CANDIDATE_JSON=$(gh pr list --state all --json number,title,state --limit 100 2>/dev/null)
MERGED_PRS=""
OPEN_PRS=""
while IFS=$'\t' read -r pr_num pr_title pr_state; do
    [[ -z "$pr_num" ]] && continue
    CLOSES=$(gh pr view "$pr_num" --json closingIssuesReferences \
        --jq '.closingIssuesReferences[].number' 2>/dev/null)
    if echo "$CLOSES" | grep -qx "$ISSUE"; then
        if [[ "$pr_state" == "MERGED" ]]; then
            MERGED_PRS+="${pr_num}: ${pr_title}"$'\n'
        elif [[ "$pr_state" == "OPEN" ]]; then
            OPEN_PRS+="${pr_num}: ${pr_title}"$'\n'
        fi
    fi
done < <(echo "$CANDIDATE_JSON" | jq -r '.[] | [.number,.title,.state] | @tsv')

# ── BULK AUDIT FILING: stage-tracker-first-back-patch ──

# 1. Stage issue bodies as local files
mkdir -p analysis/audit-$(date +%F) && cd analysis/audit-$(date +%F)
# Write 00-tracker.md, 01-...md, 02-...md (first line = title, body from line 3)

# 2. File tracker first, capture number
TRACKER_URL=$(gh issue create --title "$(head -1 00-tracker.md | sed 's/^# //')" \
  --body "$(tail -n +3 00-tracker.md)")
TRACKER="${TRACKER_URL##*/}"

# 3. File children sequentially with tracker reference
for f in 0[1-9]-*.md 1[0-9]-*.md 2[0-5]-*.md; do
  title=$(head -1 "$f" | sed 's/^# //')
  body=$(tail -n +3 "$f"; printf "\n\n---\nTracking: #%s\n" "$TRACKER")
  url=$(gh issue create --title "$title" --body "$body")
  echo "${url##*/}  $f  $url" | tee -a .child-urls
  sleep 1
done

# 4. Back-patch tracker with concrete child numbers
gh issue edit "$TRACKER" --body-file 00-tracker-updated.md

# ── DOC-PUSH-FIRST ORDERING ──

# Phase B: Push docs before filing issues
git checkout -b feature/<topic>-docs
git push -u origin feature/<topic>-docs
gh pr create --base main --head feature/<topic>-docs --title "..." --body "..."
# (user reviews and merges)

# Phase C: Branch from updated origin/main for next phase
git fetch origin
git checkout -b feature/<topic>-issue-bodies origin/main
# Write issue bodies with absolute URLs: https://github.com/<org>/<repo>/blob/main/path#anchor

# ── PROGRESS UPDATE TO ISSUE ──

# Short update
gh issue comment <number> --body "Status: [brief update]"

# Detailed update from file
gh issue comment <number> --body-file /path/to/update.md

# ── UPSTREAM OSS FEATURE REQUEST ──

# Duplicate check first (always --state all) — scope-reshaping pass
# Run BEFORE drafting any issue body; use at least two keyword angles
gh issue list --repo <owner>/<repo> --state all --search "<keywords>" --limit 20
gh issue list --repo <owner>/<repo> --state all --search "<related keywords>" --limit 20
# If existing issue found: comment on it; a URL recorded in your tracker = "filed" for acceptance purposes

# Label discovery
gh label list --repo <owner>/<repo>

# Clone to throwaway dir, propose patch, create secret gist
git clone https://github.com/<owner>/<repo> /tmp/<repo>-$$
git -C /tmp/<repo>-$$ checkout -b proposal-<feature>
# ... edit following existing pattern ...
bash -n /tmp/<repo>-$$/<script>   # syntax check
git -C /tmp/<repo>-$$ diff main..proposal-<feature> > /tmp/patch.diff
gh gist create /tmp/patch.diff --desc "Proposed patch: <feature>"   # secret by default

gh issue create --repo <owner>/<repo> --title "..." --label enhancement \
  --body-file /tmp/issue-body.md
rm -rf /tmp/<repo>-$$

# ── VERIFY-AND-CLOSE (issue believed already resolved) ──

# 1. Confirm the removed content is truly gone (exit code 1 = not found = good)
grep -rn "old-content\|other-old-pattern" .github/    # or relevant directory
echo "Exit code: $?"  # must be 1 (no matches)

# 2. Confirm the replacement content exists at expected path:line
grep -n "new-content" path/to/relevant/file

# 3. Post evidence comment on issue
gh issue comment <number> --body "$(printf 'Verified already resolved.\n\nEvidence:\n- `path/to/file:NN`: `new-content` — correct state confirmed.\n- grep for old-content returned exit code 1 (no matches).\n\nClosing as completed.')"

# 4. Close the issue
gh issue close <number> --reason completed

# -- VALIDATION TRANSCRIPT -> DURABLE BUG ISSUE --

# 1. Read the repo's bug template and draft a concise body outside the repo.
sed -n '1,220p' .github/ISSUE_TEMPLATE/bug_report.md
ISSUE_BODY=/tmp/<repo>-<bug-slug>.md
$EDITOR "$ISSUE_BODY"

# 2. File the durable bug issue using the template structure.
gh issue create --repo <owner>/<repo> \
  --title "Bug: <concise observed failure>" \
  --label bug \
  --body-file "$ISSUE_BODY"

# 3. Delete the transient validation transcript(s) from the branch.
git rm artifacts/<transient-validation-transcript>.md

# 4. Update docs/tests to reference the GitHub issue, then prove stale names are gone.
rg -n "<old-artifact-stem-1>|<old-artifact-stem-2>|validation-transcript" .
# Expected for complete cleanup: exit code 1 with no output.
```

### Preflight Decision Matrix

| Commits on branch | PR exists | Action |
| ------------------- | ----------- | -------- |
| Yes (issue ref) | Yes (open) | Report done, stop — do NOT re-implement |
| Yes (issue ref) | No | Create PR, do NOT re-commit |
| No | No | Proceed with implementation |
| No | Yes (merged) | STOP — issue complete, do not duplicate |

### Automated Preflight Exit Code Discipline

| Exit | Check | Reason |
| ------ | ------- | -------- |
| 1 | Issue CLOSED | Never proceed — work complete or abandoned |
| 1 | PR MERGED (via `closingIssuesReferences`) | Duplicate work risk |
| 1 | Worktree exists | Git prevents two worktrees on same branch |
| 0 | Existing commits | May be partial — user decides |
| 0 | Open PR exists | May be collaborative — user decides |
| 0 | Existing branch | Orphaned — user should review, not blocked |

### Bulk Filing Principles

- **Stage first**: Write every issue body as a local `.md` file before any `gh issue create` call — avoids heredoc escaping issues and lets you review the full batch before any API call
- **Tracker-first**: Create the parent tracker issue first to capture its number; back-patch it with concrete child `#NNNN` references after all children are filed
- **`sleep 1` between calls**: Sufficient for ≤30 issues; prevents GitHub abuse-detection; keeps issue numbers monotonic
- **Group nitpicks**: ~10 minor findings → 2–3 grab-bag issues; keeps tracker readable
- **Severity in body** (not labels) unless the project's `CLAUDE.md` allows labels

### Doc-Push-First: Reordered Plan

Naive order (causes broken links and backfill pain):
1. Write docs → file issues with placeholder paths → push docs → backfill `gh issue edit` on every issue

Correct order (one extra PR cycle, zero backfill):
1. Write docs
2. **Push docs PR** to `origin/main`
3. Write issue bodies with absolute `https://github.com/<org>/<repo>/blob/main/...` URLs
4. Push issue-body files PR (keeps them reviewable in-repo)
5. Pre-flight (labels, milestones, auth)
6. File issues in **dependency order** (blockers before dependents)
7. Substitute `{{placeholder}}` tokens in epic body; `gh issue edit` once

### Progress Update Templates

```bash
# Progress update
gh issue comment <number> --body "$(cat <<'EOF'
## Progress Update

### Completed
- [x] Step A
- [x] Step B

### In Progress
- [ ] Step C

### Next Steps
1. Complete test coverage
2. Integration testing
EOF
)"

# Implementation complete
gh issue comment <number> --body "$(cat <<'EOF'
## Implementation Complete

**PR**: #<pr-number>

### Summary
[Brief description]

### Files Changed
- `path/to/file` - description

### Verification
- [x] Tests pass
- [x] Pre-commit passes
- [x] Manual verification complete
EOF
)"
```

### Upstream OSS Feature Request Issue Body Template

```markdown
## Summary
<1-2 sentences>

## Proposed Behavior

| Invocation | Flag present | Env Var set | Result |
|------------|--------------|-------------|--------|
| Default    | No           | Not set     | Current behavior |
| With flag  | Yes          | —           | <new behavior> |

## Motivation
<Why needed>

## Proposed Implementation
Proposed patch following existing flag/env-var pattern: <gist URL>

Apply: `curl -sL <raw gist URL> | git apply`

## Environment

| Component | Value |
|-----------|-------|
| Installed version | `<SHA>` |
| Upstream HEAD | `<SHA>` |
| `gh` version | `<version>` |

## Verification
Syntax-checked with `bash -n`; smoke-tested with `<DEV_MODE>=1` in throwaway repo.
```

### Validation Transcript to Durable Bug Issue

Use this when an ad hoc validation transcript proves a real bug but the transcript itself
is not durable source material. The issue tracker is the durable bug record; the artifact
is temporary evidence.

1. Read `.github/ISSUE_TEMPLATE/bug_report.md` in the target repo and mirror its headings,
   checklist, and status fields rather than writing a free-form issue.
2. Convert the transcript into a concise issue body that preserves dated evidence,
   endpoint/model details, observed behavior, expected behavior, reproduction steps, and
   current checklist/status.
3. Keep the draft body outside the repo, for example `/tmp/<repo>-<bug-slug>.md`, so the
   PR branch does not accumulate another disposable artifact.
4. File the issue with `gh issue create --repo <owner>/<repo> --title "Bug: ..." --label bug
   --body-file /tmp/<repo>-<bug-slug>.md`.
5. Remove the transient validation artifact files from the PR branch.
6. Update docs/tests to reference the durable GitHub issue number/URL instead of the
   deleted artifact names.
7. Run a stale-reference scan with every old filename stem. `rg` exit code 1 with no
   output is the expected success state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Start implementing without checking git log | Read prompt file, began planning deletions | Commit `e738761d` already contained the exact implementation | Always run `git log --oneline -5` before any work on a pre-existing branch |
| Assume clean branch because `git status` is clean | Relied on `git status` showing nothing unstaged | Clean status means nothing unstaged — prior commits can have done all the work | `git status` clean != implementation not started; check `git log` too |
| Check only the issue state | Looked at issue description to understand deliverables | Issue state (open/closed) doesn't tell you if the branch already has commits | Check git log on the **current branch**, not just the issue |
| Jump straight to implementation | Started reading issue and planning without checking git log | Found PR #3176 was already open and commit `e21e00b9` had done all the work | Always check `git log --oneline -5` AND `gh pr list --head <branch>` before any implementation |
| Implement without verifying referenced code exists | Read issue plan suggesting functions needed implementation | All functions already existed with full test coverage | Verify current codebase state; issues filed weeks/months ago may describe already-solved problems |
| Treat all CI failures as blockers on a docs PR | Blocked merge on failing test groups for a docs-only PR | Failures were pre-existing and unrelated to the diff | Attribute failures to the diff — docs changes cannot break Mojo/Python tests |
| `set -e` with grep in preflight script | Used `set -e` and ran `git log ... \| grep "$ISSUE" \| head -5` | `grep` returns exit code 1 when no matches found; script aborted silently | Use `set -uo pipefail` and capture with `\|\| true` |
| `gh pr list --search "<number>"` for PR-issue ownership | Free-text PR search for issue number | Matches any PR mentioning the number in title or body — false positives | Use `closingIssuesReferences` via `gh pr view "$pr_num" --json closingIssuesReferences` |
| Treating open PRs as critical failures in preflight | Hard-stopped on any open PR | An open PR may be stale, abandoned, or collaborative — blocks legitimate handoff scenarios | Open PR → WARN (exit 0). Only MERGED PRs closing the issue are critical (exit 1) |
| Inline issue bodies in shell heredoc | Build the body string in the same `gh issue create` call | Backticks/code blocks/EOF markers break heredoc | Stage to local files first; pass via `--body "$(...)"`  |
| File the tracker last | Create children first, tracker last with collected URLs | Children had no `Tracking: #NNNN` reference; had to edit each one after | Tracker-first; back-patch its body with `gh issue edit` once children are filed |
| File 30 issues in parallel | Fire many `gh issue create` concurrently | Risk of GitHub abuse-detection; ordering becomes nondeterministic | Sequential with `sleep 1` |
| Add severity labels by default | `--label "severity:major"` per issue | Some projects ban labels (`CLAUDE.md` says "Never use labels") | Check project conventions first; put severity in body if labels are banned |
| File issues before pushing docs | Filed issues with `./docs/...` relative paths | Would have required a `gh issue edit` backfill pass on every issue body | Reorder so docs land on `main` before any `gh issue create`; absolute `blob/main` URLs from the start |
| Direct push to `main` after accumulating commits locally | Tried `git push origin main` after building up doc commits | User enforces PR-to-main discipline | Always assume PR-to-main discipline; branch + PR every phase |
| `git reset --hard origin/main` after squash merge | Wanted to clean up divergent local `main` | Blocked by safety net (destructive op) | Branch directly from `origin/main` for next phase; leave divergent local `main` alone |
| Guess heading anchors for double-digit numeric prefixes | Assumed `## 2.2 Memory layout` → `#2-2-memory-layout` | GitHub strips `.` and concatenates: actual anchor is `#22-memory-layout` | Smoke-test anchors in a browser before filing 25+ issues |
| Skip pre-flight label/milestone check before filing loop | Started filing loop, hit "label not found" on issue 6 | Loop filed 5 issues then errored; those already-filed issues lacked the label | Run `gh label list` and `gh api .../milestones` BEFORE the loop; create missing ones up front |
| `yes \| gh tidy` for OSS smoke test | Piped `yes` to bypass interactive prompts | Fragile — output order is unpredictable, prompts may not align with `yes` responses | Use dev-mode env vars (e.g., `GH_TIDY_DEV_MODE=1`) for smoke testing |
| Assigning labels without checking upstream repo | Assumed common labels like `feature` or `good-first-issue` existed | Labels vary per repo; assigning a non-existent label causes `gh issue create` to fail | Always run `gh label list --repo <owner>/<repo>` before any `--label` argument |
| Filing from memory / stale context of upstream code | Drafted issue without re-reading current source | Existing pattern may differ from memory; patch becomes inconsistent | Always read the full source file before proposing a change |
| Skipping duplicate check before filing upstream | Jumped straight to implementation | Risk of filing a duplicate issue, wasting maintainer time | Always run `gh issue list --state all --search "<keywords>"` first |
| Skipped the duplicate-check because the task said "file 2 issues" | Treated issue-filing requirement as literal, started drafting both bodies | One was already filed (by the same author) months earlier; the other was based on a stale audit (the cited code already existed). Drafting both consumed time before discovery | Always run duplicate-search FIRST — even when the upstream relationship is yours. Authors forget what they've filed. The duplicate-collapse can re-scope the entire task, not merely confirm absence. |
| Pipe to preserve exit code in bash preflight tests | `bash -c "..." \| cat; echo $?` | Pipe runs in subshell; `$?` is lost | Write output to temp file, capture `LAST_EXIT=$?` after |
| Concluding "already resolved" from keyword presence without grep | Assumed absence of macos/windows CI refs from memory | Keyword presence elsewhere in context does not prove absence in files | Always run `grep -rn <removed-content> <dir>` and confirm exit code 1 before closing |
| Checking in transient validation transcripts | Kept ad hoc `artifacts/<date>-<pr>-validation*.md` files on a PR branch | The transcript created repo churn and stale evidence. One transcript represented a real unresolved bug, so deleting it without a durable bug record would lose the follow-up path | Do not check in one-off validation transcripts. File the real bug with the repo's bug template, reference the GitHub issue from docs/tests, delete the transient files, and scan for stale artifact names before committing |

## Results & Parameters

### Preflight Timing Benchmarks

| Phase | Time |
| ------- | ------ |
| `git log --oneline -5` | <1 s |
| `gh issue view` (state check) | ~1 s |
| `gh pr list --head <branch>` | ~1 s |
| `git log --all --grep` | ~2 s |
| Worktree + branch check | ~1 s |
| **Total** | **~6 s** |

Without preflight: 30–60+ minutes of duplicate/unnecessary work.

### Automated Preflight Check Sequence

| Check | Command | Exit on failure |
| ------- | --------- | ---------------- |
| 1. Issue state | `gh issue view "$ISSUE" --json state,title,closedAt` | exit 1 (CLOSED) |
| 2. Existing commits | `git log --all --oneline --grep="#${ISSUE}" \| head -5` | exit 0 (WARN) |
| 3. PR via `closingIssuesReferences` | Two-phase lookup | exit 1 (MERGED), exit 0 (OPEN) |
| 4. Worktree conflict | `git worktree list \| grep "$ISSUE"` | exit 1 |
| 5. Existing branches | `git branch --list "*${ISSUE}*"` | exit 0 (WARN) |

Key parameters: `--limit 100` for PR fetch; `grep -qx "$ISSUE"` for full-line match (prevents `73` matching `735`).

### Bulk Audit Filing Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Issues per verified run | 26 | 1 tracker + 25 children (ProjectScylla 2026-05-07) |
| Sleep between `gh issue create` | 1 s | Sufficient for ≤30 issues; no abuse-detection trips |
| Wall time (26 issues) | ~50 s | Dominated by `sleep 1` + GitHub API latency |
| Rate-limit errors | 0 | |
| Re-edits for typos | 0 | Local-file staging catches everything pre-flight |
| Tracker back-patch | 1 `gh issue edit` call | |

### Doc-Push-First Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Issues filed (verified run) | 26 | 1 epic + 25 children (`mvillmow/Random` 2026-05) |
| PR cycles | 3 | docs → issue-bodies → file-issues registry |
| Cross-link references resolved on first render | 25 | Zero backfill needed |
| `gh issue edit` for backfill | 1 | Only the epic; children correct first time |
| Sleep between `gh issue create` | 1 s | Sufficient for ≤30 issues |

### Duplicate-Collapse Decision Tree (Upstream Issue Filing)

After running the duplicate-search (Step 2 of upstream feature request), branch on what was found:

- **Existing issue found, scope fully covers your need** → COMMENT on it recording your interest + the SLA you'll wait. Record the URL in your tracking issue. Do not file a duplicate.
- **Existing issue found, scope partially covers** → comment cross-linking your narrower issue; file the narrower one.
- **No existing issue** → file as planned.

In all cases, the tracking-issue acceptance criterion "issue filed/recorded" is satisfied by a URL — not by authorship. A comment on a pre-existing matching issue, with the URL captured in your tracking issue, fully discharges the requirement.

### Gist Visibility Reference

| Flag | Visibility |
| ------ | ----------- |
| `gh gist create` (no flag) | Secret — URL-accessible, not listed on profile |
| `gh gist create --public` | Public — appears on profile |

Use secret gists for proposed patches on third-party repos.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3063 auto-impl worktree | Detected pre-existing commit `e738761d` in 2 tool calls |
| ProjectOdyssey | Issue #2672 training dashboard | Detected closed issue + existing implementation after 12 wasted calls |
| ProjectOdyssey | Issue #3013 ExTensor operations | All operations already existed; only stale TODOs needed updating |
| ProjectScylla | Issue #735 preflight integration | PR #917, 100% adoption enforced; closingIssuesReferences fix |
| ProjectScylla | Issue #802 false-positive fix | PR #912, 6 bash tests passing |
| ProjectScylla | Issue #803 propagate to worktree-create | PR #917, docs-only propagation |
| ProjectScylla | 2026-05-07 audit filing | Filed 26 issues (#1934 tracker + #1935–#1959); 0 rate-limit errors |
| mvillmow/Random | Predictive-Coding-in-Mojo Pass 4 | Filed epic #4 + 25 child issues #5–#29; all 25 cross-links resolved on first render |
| HaywardMorihara/gh-tidy | `--auto-delete` feature request | Issue #62 filed; gist created; throwaway clone cleaned up |
| ProjectHephaestus | Issue #539 verify-and-close | `grep -rn "macos-latest\|windows-latest" .github/` → exit 1; `.github/workflows/test.yml:58: os: [ubuntu-latest]` confirmed; issue closed via `gh issue close 539 --reason completed` |
| H200 Slurm inference stack | PR #155 validation-artifact cleanup | Durable bug issue #158 created from the unresolved validation finding; PR #155 checks passed after transient artifacts were removed and stale artifact names were replaced with issue references |
