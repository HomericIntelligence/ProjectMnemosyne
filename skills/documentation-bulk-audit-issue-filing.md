---
name: documentation-bulk-audit-issue-filing
description: "Convert a structured repo audit's findings into a coherent set of GitHub issues with a parent tracker. Stage every issue body as a local file first, file the tracker first to capture its number, then file children sequentially with `sleep 1` and a `Tracking: #NNNN` footer, then back-patch the tracker body with concrete child references. Use when: (1) you have just finished a multi-section audit and need to file 10–40 issues, (2) you want a single parent issue showing audit progress at a glance, (3) you want every issue body reviewable as a local directory before any API call."
category: tooling
date: 2026-05-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, issues, audit, bulk-filing, tracker, parent-issue, governance, sleep-rate-limit]
---

# Bulk Audit Issue Filing: Stage, Tracker-First, Back-Patch

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-07 |
| **Objective** | Convert a finished audit into a tracked GitHub issue queue: 1 parent tracker + N child issues, each with a `Tracking: #<tracker>` footer, with the tracker's checklist back-patched to point at concrete child numbers. |
| **Outcome** | Verified on ProjectScylla 2026-05-07: 26 issues filed (#1934 tracker + #1935–#1959); 0 rate-limit errors; 0 typos requiring re-edit. |
| **Verification** | verified-local |

## When to Use

- After running a multi-section repo audit (`/repo-analyze*`, `/quality-audit`, etc.) with 10–40 findings
- Converting any structured findings document (markdown report, peer review, etc.) into a tracked GitHub issue queue
- You want a single parent issue showing audit progress at a glance
- You want the entire batch reviewable as a local directory of `.md` files before any `gh issue create` runs

**Don't use when:**

- Fewer than ~5 findings — file by hand
- Filing across multiple repos in one wave — see `github-bulk-issue-filing-rate-limit-recovery` instead
- You haven't yet decided what's critical vs. nitpick — triage first using `oss-contribution-issue-filing-pattern` or `repo-audit-triage-fix-and-issue-workflow`

## Core Principles

### 1. Stage Every Issue Body as a Local File First

Path convention: `analysis/audit-YYYY-MM-DD/NN-short-description.md`

- First line is `# <issue title>` (extracted later via `head -1 | sed 's/^# //'`)
- Line 2 is blank
- Body starts at line 3 (extracted via `tail -n +3`)

This makes the whole batch reviewable as a directory before any API calls. Inline heredocs lose
backticks and code-fence markers; staging avoids that entirely.

### 2. Tracker-First Ordering

Create the parent tracker issue FIRST so its number is known. Capture it:

```bash
url=$(gh issue create --title "$title" --body "$body")
TRACKER="${url##*/}"
```

Then file children with the tracker number appended via:

```bash
printf "\n\n---\nTracking: #%s\n" "$TRACKER"
```

After all children are filed, edit the tracker body in place to replace the placeholder
checklist with concrete `#NNNN` references.

### 3. Sequential Loop With `sleep 1` for Rate Limiting

```bash
for f in 0[1-9]-*.md 1[0-9]-*.md 2[0-5]-*.md; do
  title=$(head -1 "$f" | sed 's/^# //')
  body=$(tail -n +3 "$f"; printf "\n\n---\nTracking: #%s\n" "$TRACKER")
  url=$(gh issue create --title "$title" --body "$body")
  num="${url##*/}"
  echo "$num  $f  $url" | tee -a .child-urls
  sleep 1
done
```

`sleep 1` is sufficient for ~30 issues; never hit GitHub abuse-detection in practice. Sequential
ordering also keeps issue numbers monotonic, which makes the tracker checklist easier to read.

### 4. Group Nitpicks; Do Not Skip Them

~10 minor findings become 2–3 grouped "grab-bag" issues (e.g., "CI/tooling drift grab-bag",
"compliance gaps grab-bag", "DX polish grab-bag") rather than 10 individual noise issues. The
tracker stays readable and the work stays traceable.

### 5. Severity in Body, Not Labels — IF the Project Says So

Some projects ban labels (e.g., ProjectScylla `CLAUDE.md` says "Never use labels"). Detect this
by reading `CLAUDE.md` or asking. If labels are allowed, prefer existing taxonomy
(e.g., `severity:critical/major/minor/nitpick`, `audit-finding`) over new labels.

### 6. Title Format

```
[Audit] §<section-number> <severity?>: <short description>
```

Section number makes it easy to filter/group. Severity in title for criticals only; in body for
everything.

### 7. Body Template

Each finding's `.md` file:

```markdown
# [Audit] §3.2 critical: Race in tier_manager checkpoint

**Severity:** critical
**Section:** §3.2
**Audit date:** 2026-05-07

## Problem

`src/scylla/e2e/tier_manager.py:142-156` writes checkpoint without holding the lock that
`runner.py:88` acquires before reading. Race observed 3/10 runs in parallel-tier mode.

## Recommended fix

Hoist the lock acquisition into `tier_manager.checkpoint()` itself; remove the duplicate lock
in `runner.py`.

## Acceptance criteria

- [ ] No `tier_manager` write path runs without the lock held
- [ ] Parallel-tier reproduction (10 runs) shows zero divergence
- [ ] Unit test added under `tests/unit/e2e/test_tier_manager_lock.py`
```

### 8. Update Tracker Last

Once children are filed, write `00-tracker-updated.md` with concrete `#NNNN` checkboxes and:

```bash
gh issue edit "$TRACKER" --body-file 00-tracker-updated.md
```

## Verified Workflow

### Quick Reference

```bash
# 1. Stage issue bodies
mkdir -p analysis/audit-$(date +%F)
cd analysis/audit-$(date +%F)
# Write 00-tracker.md, 01-...md, 02-...md, etc.

# 2. File tracker first
title=$(head -1 00-tracker.md | sed 's/^# //')
body=$(tail -n +3 00-tracker.md)
url=$(gh issue create --title "$title" --body "$body")
TRACKER="${url##*/}"

# 3. File children with tracker reference
for f in 0[1-9]-*.md 1[0-9]-*.md 2[0-5]-*.md; do
  title=$(head -1 "$f" | sed 's/^# //')
  body=$(tail -n +3 "$f"; printf "\n\n---\nTracking: #%s\n" "$TRACKER")
  url=$(gh issue create --title "$title" --body "$body")
  echo "${url##*/}  $f  $url" | tee -a .child-urls
  sleep 1
done

# 4. Edit tracker body to back-patch child issue numbers
gh issue edit "$TRACKER" --body-file 00-tracker-updated.md
```

## Results & Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Issues filed (verified run) | 26 | 1 tracker + 25 children |
| Tracker number (verified run) | #1934 | ProjectScylla |
| Child range (verified run) | #1935–#1959 | Sequential, monotonic |
| Sleep between `gh issue create` calls | 1s | Sufficient for ≤30 issues; no abuse-detection trips |
| Wall time (26 issues) | ~50s | Dominated by `sleep 1` + GitHub API latency |
| Rate-limit errors | 0 | |
| Re-edits required for typos | 0 | Local-file staging caught everything pre-flight |
| Tracker back-patch | 1 `gh issue edit` call | Replaces placeholder checklist with `#NNNN` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Inline issue bodies in shell heredoc | Build the body string in the same `gh issue create` call | Backticks/code blocks/EOF markers break heredoc; lost a body once | Stage to local files first; pass via `--body "$(...)"` |
| File the tracker last | Create children first, tracker last with collected URLs | Children had no `Tracking: #NNNN` reference; had to edit each one after | Tracker-first; back-patch its body with `gh issue edit` once children are filed |
| Add severity labels by default | `--label "severity:major"` per issue | Some projects ban labels (`CLAUDE.md` says "Never use labels") | Check project conventions first; put severity in body if labels are banned |
| File 30 issues in parallel | Fire many `gh issue create` concurrently | Risk of GitHub abuse-detection; ordering of issue numbers becomes nondeterministic which breaks the tracker | Sequential with `sleep 1` |
| One issue per minor finding | Treat all 10 minors equally | Noise; tracker becomes unreadable | Group minors into 2–3 grab-bag issues by category |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | 2026-05-07 audit | Filed 26 issues (#1934 tracker + #1935–#1959); 0 rate-limit errors; 0 typos requiring re-edit |

## Related Skills

- `repo-audit-triage-fix-and-issue-workflow` — upstream of this skill: triages audit findings into fix-now vs. file-as-issue. This skill picks up after triage when you've decided to file.
- `oss-contribution-issue-filing-pattern` — similar staging discipline for upstream OSS, but with deduplication-against-existing-issues as the gate. Use that one when contributing to a repo you don't own.
- `github-bulk-issue-filing-rate-limit-recovery` — escalation path when filing 200+ issues across many repos and hitting org-level rate limits. This skill stays in single-repo, single-batch territory.
- `bulk-issue-terminology-migration` — for editing existing issues at scale, not creating them.
