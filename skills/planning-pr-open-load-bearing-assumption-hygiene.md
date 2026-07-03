---
name: planning-pr-open-load-bearing-assumption-hygiene
description: "PR-open plans routinely depend on load-bearing external assumptions the planner did not verify: (a) `gh pr merge --auto --rebase` requires the repo to allow rebase-merge AND for auto-merge to be enabled at the repo level; on some `gh` versions and configurations, `--auto` fails with a non-obvious error, (b) a compat wrapper (e.g. `scripts/mojo-format-compat.sh`) exits 0 on hosts with older GLIBC — a load-bearing claim that the plan uses to assert '`just precommit` will pass without `SKIP=mojo-format`,' but is only true if the wrapper is actually present AND its GLIBC-detection logic is correct AND the referenced doc is current. The planner MUST either (1) probe the assumption before writing the plan (`gh repo view --json autoMergeAllowed,rebaseMergeAllowed`; `cat scripts/mojo-format-compat.sh`; `cat docs/dev/mojo-glibc-compatibility.md`), or (2) hedge the assumption explicitly with a documented fallback (`SKIP=mojo-format` with the doc-required reason; manual auto-merge enablement). Silent load-bearing assumptions cause execute-time failures that are hard to diagnose because the plan reads as if the issue was considered. Use when: (1) drafting any plan step that says `gh pr merge --auto`, (2) drafting any plan step that says `just precommit` on a repo with GLIBC-sensitive tooling, (3) writing a plan that depends on a compat wrapper OR a docs file being current, (4) writing a plan that depends on ANY repo setting (auto-merge, merge methods, required checks, branch protection) that the planner has not viewed via `gh repo view --json`."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pr-open
  - load-bearing-assumption
  - auto-merge
  - autoMergeAllowed
  - compat-wrapper
  - glibc
  - precommit
  - probe-before-plan
  - documented-fallback
---

# Planning: Load-Bearing Assumption Hygiene in PR-Open Plans

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Prevent PR-open plans from silently depending on unverified external assumptions (repo auto-merge settings; the presence/behavior of a compat wrapper script; the current state of a referenced doc) by requiring either (a) a probe at plan time or (b) an explicit hedge with a documented fallback. |
| **Outcome** | PLAN ONLY — captured during ProjectOdyssey #5527 planning where the plan (i) invoked `gh pr merge --auto --rebase` without probing `autoMergeAllowed` or `rebaseMergeAllowed`, and (ii) asserted `just precommit` would pass without `SKIP=mojo-format` based on a claim about `scripts/mojo-format-compat.sh` and `docs/dev/mojo-glibc-compatibility.md` — neither of which was read. |
| **Verification** | unverified |

## When to Use

- Drafting any plan step invoking `gh pr merge --auto` (any merge method) — the flag depends on repo settings the planner may not have viewed.
- Drafting any plan step invoking `just precommit` (or the equivalent hook-runner) on a repo with GLIBC-sensitive tooling — Mojo, Rust with musl, native extensions.
- Writing a plan that cites a compat wrapper script (e.g. `scripts/mojo-format-compat.sh`) to justify skipping a fallback step — the wrapper's behavior is load-bearing and must be verified.
- Writing a plan that cites a docs file (e.g. `docs/dev/mojo-glibc-compatibility.md`) as authority for a claim — the doc may be stale.
- Writing a plan that depends on ANY repo setting (auto-merge, merge methods, required checks, branch protection rules) the planner has not queried via `gh repo view --json <field>` or `gh api repos/OWNER/REPO/branches/main/protection`.

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed against ProjectOdyssey in this session: `gh repo view --json
> autoMergeAllowed,rebaseMergeAllowed` was NOT run, `scripts/mojo-format-compat.sh`
> was NOT read, and `docs/dev/mojo-glibc-compatibility.md` was NOT verified as
> current. Verify these against your target repo before adopting the pattern.

### Quick Reference

```bash
# --- Assumption 1: auto-merge is available ---
gh repo view HomericIntelligence/ProjectOdyssey \
  --json autoMergeAllowed,rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed \
  > /tmp/repo_merge_settings.json
cat /tmp/repo_merge_settings.json
# If autoMergeAllowed == false → plan MUST use manual merge (no --auto)
# If rebaseMergeAllowed == false → plan MUST use --squash or --merge, not --rebase
# Fallback: soft-fail the --auto step, keep the PR open, and log that manual
#           enablement is required; do NOT abort the whole task.

# --- Assumption 2: compat wrapper exists and exits 0 on incompatible hosts ---
ls -la scripts/mojo-format-compat.sh 2>&1 || echo "MISSING — plan must specify SKIP=mojo-format fallback"
grep -nE 'ldd --version|GLIBC|exit 0' scripts/mojo-format-compat.sh
# If the wrapper's GLIBC check is not present → SKIP=mojo-format is required
# If the wrapper is missing → the plan's "no SKIP= needed" claim is wrong

# --- Assumption 3: referenced doc is current ---
grep -nE 'GLIBC|compat|SKIP=' docs/dev/mojo-glibc-compatibility.md
# Verify the doc describes the SAME wrapper behavior the plan cites
git log -1 --format='%ci' docs/dev/mojo-glibc-compatibility.md
# If the doc is stale (>6 months) or its content contradicts the plan, re-read
```

### Detailed Steps

1. **For every `gh pr merge --auto` step in a plan**, probe repo settings first:
   ```bash
   gh repo view <owner>/<repo> --json autoMergeAllowed,rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed
   ```
   Match the merge method flag (`--rebase`/`--squash`/`--merge`) to what the repo permits. If `autoMergeAllowed` is false, the plan MUST NOT rely on `--auto`; document a manual-enablement fallback instead.
2. **Soft-fail `gh pr merge --auto` in the plan**, not hard-fail. The PR is still open even if `--auto` fails; the human reviewer can enable auto-merge manually. The plan should record the `--auto` result but not abort the whole PR-open task if it fails.
3. **For every claim of the form "X passes without Y because of compat wrapper Z"**, the plan MUST include a read of Z's source. Do not cite a wrapper's behavior from a docs claim — the docs may lag the wrapper.
4. **For every citation of a docs file** as authority for a load-bearing claim, the plan MUST show a probe result (`git log -1 --format='%ci' <doc>`; `grep -nE '<key-term>' <doc>`) proving the doc says what the plan says it says.
5. **Explicit hedges are cheaper than silent assumptions**. A plan that says "if `scripts/mojo-format-compat.sh` is present and exits 0 on WSL, `just precommit` will pass; otherwise use `SKIP=mojo-format` with the reason documented in `docs/dev/mojo-glibc-compatibility.md`" is more robust than one that says "`just precommit` will pass without SKIP=".
6. **In review**, load-bearing assumptions the planner did not verify should be treated as blocking — the executor cannot recover from them at run time without a fallback path.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 planning session: assert `just precommit` will pass without `SKIP=mojo-format` on a WSL host with GLIBC < 2.32, based on the claim that `scripts/mojo-format-compat.sh` exits 0 in that scenario and `docs/dev/mojo-glibc-compatibility.md` documents this. Neither the wrapper nor the docs file was read. | Two silent load-bearing assumptions: (a) the wrapper's GLIBC-detection logic may not cover the executor's specific host, (b) the docs file may be stale. If either fails, `just precommit` fails at execute time and the plan offers no fallback. | Read the wrapper. Read the doc. Or hedge explicitly: "if precommit fails on `mojo-format`, use `SKIP=mojo-format git commit -m '…'` and reference `docs/dev/mojo-glibc-compatibility.md` in the commit body." |
| Attempt 2 | ProjectOdyssey #5527 planning session: invoke `gh pr merge --auto --rebase` without probing `gh repo view --json autoMergeAllowed,rebaseMergeAllowed`. | On some repos `autoMergeAllowed=false` (auto-merge is not enabled at the repo level); on others `rebaseMergeAllowed=false` (only squash/merge is permitted). Either causes `--auto --rebase` to fail with a non-obvious error. The plan does not hedge, so a failure aborts the PR-open task even though the PR itself is fine. | Probe repo settings before writing the plan step, OR soft-fail the `--auto` step (record the failure, continue) so the PR stays open and manual merge remains available. |

## Results & Parameters

### Configuration

```yaml
plan-pattern:
  load-bearing-assumptions:
    require-probe-or-hedge: true
    common-probes:
      auto-merge:
        command: "gh repo view <owner>/<repo> --json autoMergeAllowed,rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed"
        expected-fields:
          - autoMergeAllowed: true
          - rebaseMergeAllowed: true    # or squashMergeAllowed / mergeCommitAllowed
      compat-wrapper:
        command: "grep -nE 'GLIBC|ldd --version|exit 0' scripts/<wrapper>.sh"
        fallback: "SKIP=<hook-id> with docs reason"
      docs-current:
        command: "git log -1 --format='%ci' docs/dev/<file>.md && grep -nE '<key-term>' docs/dev/<file>.md"
    soft-fail-steps:
      - "gh pr merge --auto"    # PR stays open; log failure; continue
```

### Expected Output

- Every `gh pr merge --auto` step in a plan is preceded by a repo-settings probe OR marked soft-fail.
- Every claim of the form "X works because of Y" is preceded by a read of Y's source (not just Y's documentation).
- Every citation of a docs file includes a freshness probe.
- Silent load-bearing assumptions in a plan are treated as blocking in review.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5527 planning session (2026-07-02) — captured two anti-patterns: (a) unhedged `gh pr merge --auto --rebase`, (b) unread `scripts/mojo-format-compat.sh` justifying "no SKIP= needed". Corrective pattern PLAN ONLY, not executed. | See ProjectOdyssey issue #5527 comments. |

## References

- [github-auto-merge-ci-gating-merge-method](github-auto-merge-ci-gating-merge-method.md) — sibling skill; deep dive on why `gh pr merge --auto` fails and how to diagnose. This skill covers the PLANNING-time probe; that skill covers RUN-time diagnosis.
- [planning-pr-body-extract-sibling-artifact-at-runtime](planning-pr-body-extract-sibling-artifact-at-runtime.md) — companion skill for sibling-task artifacts.
- [planning-pr-body-numeric-claims-source-derived](planning-pr-body-numeric-claims-source-derived.md) — companion skill for numeric claims.
- [planning-pr-open-file-scope-via-git-diff](planning-pr-open-file-scope-via-git-diff.md) — companion skill for file-path claims.
