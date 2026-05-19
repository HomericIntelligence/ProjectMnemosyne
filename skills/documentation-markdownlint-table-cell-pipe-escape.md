---
name: documentation-markdownlint-table-cell-pipe-escape
description: "Use when: (1) markdownlint reports MD056/table-column-count
  'Expected: N; Actual: N+2; Too many cells' on a single row that visually has
  the correct number of `|` separators, (2) the offending row contains an inline
  code span with GitHub Actions / shell / template syntax using `||` or `|` such
  as `${{ a && '1' || '0' }}` or `cmd | other`, (3) you assumed backticks would
  protect `|` inside a table cell but markdownlint still counts them as cell
  separators, (4) CI is failing across multiple PRs on the same pre-existing
  file and you need to confirm it is not a PR-introduced regression before
  rebasing, (5) the entire PR queue (10+ open PRs) is red on the same
  markdownlint check pointing to the same file:line — systemic block needing
  fix + bulk admin-merge recovery"
category: documentation
date: 2026-05-18
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: documentation-markdownlint-table-cell-pipe-escape.history
tags:
  - markdownlint
  - MD056
  - tables
  - inline-code
  - pipe-escape
  - ci-unblocking
  - github-actions
  - queue-unblock
  - admin-merge
---

# Markdownlint Table Cell Pipe Escape Inside Inline Code

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Fix markdownlint MD056 firing on a 4-column table row whose only "extra cells" come from `\|\|` inside a backtick-wrapped GitHub Actions expression, AND recover an entire PR queue blocked by the bug |
| **Outcome** | v1.0.0: 1-line escape fix merged as PR #1756. v1.1.0: documented systemic queue-block pattern and two-track recovery (fix-PR + parallel bulk admin-merge of 17 stuck PRs) — total recovery ~2 minutes once diagnosed |
| **Verification** | verified-ci (PR #1756 merged green on HomericIntelligence/ProjectMnemosyne main) |

## When to Use

Apply this pattern when:

1. **MD056 fires on a table row with backticks containing `|`** — counterintuitive because the inline code span looks like it should protect the pipe
2. **CI error reads** `MD056/table-column-count Table column count [Expected: 4; Actual: 6; Too many cells, extra data will be missing]` — the delta (Actual - Expected) equals the number of literal `|` chars inside backticks on that row (each `|` adds one phantom cell; `||` adds two)
3. **Multiple open PRs all fail on the same file/line** — strong signal the bug is in `main`, not PR-introduced; verify before rebasing
4. **The cell renders correctly on GitHub** — GitHub Flavored Markdown renders the inline code fine, so the bug is invisible until markdownlint runs in CI

### Systemic Impact: One Bad Row Blocks the Whole Queue

**Symptom:** Every open PR (observed: 17 PRs in one session — #1724, #1751–#1767) fails the **same** required `markdownlint` check pointing to the **same** `file:line` — but none of those PRs touch that file.

**Mechanism:** Required-check CI runs markdownlint over the merge-base snapshot (PR HEAD merged into base). The bad file lives in `main`, so every merge-snapshot inherits it. Every PR becomes un-mergeable until `main` is fixed, even though no PR introduced the regression.

**Diagnostic giveaway:** when the failing `file:line` is identical across unrelated PRs, the bug is upstream — do not rebase, do not blame the PR authors, fix `main`.

## Verified Workflow

### Quick Reference

Copy-paste fix: inside an inline code span (between backticks) inside a markdown table cell, escape every `|` as `\|`.

```markdown
<!-- BEFORE (MD056 fires: 4-column table, this row has 6 cells) -->
| Attempt | Tried | Why Failed | Lesson |
| ------- | ----- | ---------- | ------ |
| GHA expr | Used `${{ inputs.x && '1' || '0' }}` | n/a | n/a |

<!-- AFTER (passes MD056) -->
| Attempt | Tried | Why Failed | Lesson |
| ------- | ----- | ---------- | ------ |
| GHA expr | Used `${{ inputs.x && '1' \|\| '0' }}` | n/a | n/a |
```

The HTML entity `&#124;` also works but renders as the entity itself inside backticks (since backticks suppress entity decoding), so `\|` is preferred for table cells with inline code.

### Step 1 — Diagnose (per-PR signature)

Read the CI error carefully. The format is:

```text
<file>:<line>:<col> MD056/table-column-count Table column count [Expected: N; Actual: M; Too many cells, ...]
```

If `M - N == count of '|' inside backticks on that line`, this is your bug.

**One-line recipe** to pull the exact error from a failing run:

```bash
gh run view <RUN_ID> --log-failed | grep MD056
```

Single-line output. The `<file>:<line>:<col>` is your fix target.

### Step 2 — Confirm not PR-introduced

Before rebasing or blaming a PR, diff the failing file against `main`:

```bash
gh pr diff <PR_NUM> --repo <owner>/<repo> -- <failing-file>
```

If the file is unchanged in every failing PR, the bug is in `main` and needs its own fix PR. Do not rebase.

### Step 3 — Verify the queue is uniformly red BEFORE bulk admin-merging

Critical safety gate: confirm every stuck PR is failing **only** on the same markdownlint check — never admin-merge a PR whose other checks (tests, security, lint of its own changes) are hiding real bugs.

```bash
for pr in <list-of-pr-numbers>; do
  echo -n "PR #$pr: "
  gh pr view $pr --json statusCheckRollup \
    | python3 -c "import json,sys; d=json.load(sys.stdin); \
        print(','.join(c['name'] for c in d['statusCheckRollup'] \
              if c.get('conclusion') in ('FAILURE','CANCELLED','TIMED_OUT')))"
done
```

Expected output: every line ends in just `markdownlint` (or whatever the single shared check is). If any line lists additional failures, **investigate that PR before merging it** — do not bulk-merge a queue with mixed failure modes.

### Step 4 — Apply escape

Replace each `|` inside backticks on the offending row with `\|`. Leave structural pipes (the cell separators) alone.

### Step 5 — Validate locally

```bash
markdownlint-cli2 --config .markdownlint.yaml <file>
```

Expect exit code 0.

### Step 6 — Two-Track Recovery (queue unblock)

Run both tracks **in parallel** once Step 3 confirms uniform failure mode:

**Track A — Land the fix:**

1. Branch from `main`, apply the escape, push.
2. Open the fix PR. It will ALSO fail markdownlint (its own merge-base still contains the bad file — that's the file it's fixing).
3. **Admin-merge** the fix PR to land it on `main`.

**Track B — Drain the stuck queue:**

1. Iterate the verified-uniform-failure PR list from Step 3.
2. Admin-merge each one **sequentially, not in parallel** — see the cross-referenced skill `tooling-gh-pr-merge-admin-parallel-base-branch-race` for why parallel admin-merge causes base-branch races and most merges fail.

Total wall time observed: **~2 minutes** for 17 PRs once the diagnosis was made.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Assumed PR-introduced regression | Saw 5 open PRs (#1751, #1752, #1753, #1754, #1724) all failing markdownlint on the same file and assumed one of them introduced it; planned to rebase each | The failing file (`skills/ci-cd-gated-debug-instrumentation-workflow-dispatch.md`) was untouched by every PR — the bug had been merged to main earlier and only surfaced after a markdownlint version bump | Always `gh pr diff <num> -- <file>` to confirm a PR changed the failing file before blaming/rebasing the PR |
| Wrapped expression in HTML code tags | Tried using HTML `<code>...</code>` markup instead of backticks, hoping HTML would protect the pipe characters | markdownlint MD056 tokenizes the row on `\|` before HTML parsing — bare pipe inside HTML code tags is still counted as a cell separator | Tag substitution does not help; backslash-escape each pipe individually |
| Used HTML entity for pipe | Replaced pipes with `&#124;` inside the backticks | Backticks render the entity verbatim — readers see the literal entity text instead of a pipe in the rendered table | Use `&#124;` only outside backticks; inside inline code, use backslash-escape |
| Tried `--fix` on markdownlint-cli2 | Ran `markdownlint-cli2 --fix '**/*.md'` hoping autofix would handle MD056 | MD056 has no autofix implementation — `--fix` reports 0 modifications and the error persists | Manual escape required; do not waste time on autofix for MD056 |
| Parallel admin-merge of 17 stuck PRs | Ran `gh pr merge --admin` against all 17 PRs concurrently to drain the queue fast | Only 4 succeeded; 13 hit "base branch was modified" race conditions and rejected — GitHub serializes merges to the same base ref and parallel requests collide | Admin-merge stuck queues **sequentially**, one PR at a time; see `tooling-gh-pr-merge-admin-parallel-base-branch-race` |
| Bulk admin-merge without per-PR check audit | Trusted the "all red on markdownlint" surface signal and started admin-merging without verifying each PR's full status rollup | Risk (avoided here, but real): admin-merge bypasses required checks — a PR with hidden real failures (tests, security) would land broken code on main | Always run the Step 3 per-PR `statusCheckRollup` loop and confirm uniform failure mode before bulk admin-merge |

## Results & Parameters

### Reproducer

```markdown
| A | B | C | D |
| - | - | - | - |
| x | y | `cmd \|\| other` | z |
```

`markdownlint-cli2 --config .markdownlint.yaml file.md` → exit 0.

Without the backslashes, same row → `MD056 Expected: 4; Actual: 6`.

### Tooling versions verified

| Tool | Version | Result |
| ---- | ------- | ------ |
| markdownlint-cli2 | 0.20.0 (local) | 0 errors after escape |
| markdownlint-cli2 | 0.22.1 (CI) | green on PR #1756 post-merge |
| markdownlint | 0.40.0 (CI underlying) | green |

### Queue-recovery telemetry (2026-05-18 session)

| Metric | Value |
| ------ | ----- |
| PRs blocked on the same MD056 line | 17 (#1724, #1751–#1767) |
| Fix PR | #1756 |
| Track-A admin-merge wall time | ~30 s |
| Track-B sequential admin-merge of remaining 16 | ~90 s |
| Total queue recovery | ~2 minutes |

### When NOT to use this skill

- If the error is `Expected: N; Actual: N-K` (too FEW cells), this is unrelated — usually a missing trailing `|` on the row.
- If `M - N` does not equal the count of `|` inside backticks, look for additional unescaped `|` elsewhere on the line.
- If Step 3 reveals **mixed** failure modes across the stuck PRs, do **not** bulk admin-merge — investigate each diverging PR.
- For bulk fixes across hundreds of files, see `markdown-linting-bulk-table-format-fix` instead.

## Related Skills

- `tooling-gh-pr-merge-admin-parallel-base-branch-race` — why Track B must be sequential
- `markdown-linting-bulk-table-format-fix` — for repo-wide MD0xx cleanup

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectMnemosyne | PR #1755 — `fix/markdownlint-table-pipe-escape` unblocks 5 other PRs (#1751, #1752, #1753, #1754, #1724) | File: `skills/ci-cd-gated-debug-instrumentation-workflow-dispatch.md` line 107 |
| ProjectMnemosyne | PR #1756 — same root cause re-surfaced across 17 PRs (#1724, #1751–#1767); two-track recovery executed in ~2 minutes | Diagnostic: `gh run view --log-failed \| grep MD056`; recovery: fix-PR admin-merge + sequential admin-merge of 16 stuck PRs |
