---
name: planning-audit-finding-premise-verification
description: "When planning a fix for an audit/lint/reviewer finding, verify the finding's stated PREMISE against the CURRENT repo state before designing the fix — the premise can be factually stale, and a stale premise redirects the entire fix. A finding that says a file is 'committed' / 'in source' / cites `path:line` is a CLAIM: prove the file is actually TRACKED with `git ls-files | grep <path>` and `git log --all -- <path>` (empty = never committed) before planning any edit to it — editing an untracked file produces an un-reviewable, non-recurrence-preventing diff. Separately, when a file 'appears ignored' locally, distinguish REPO-level ignore from the developer's GLOBAL ignore with `git -c core.excludesFile=/dev/null check-ignore -v <path>` (rc=1 => the repo `.gitignore` does NOT defend the file; it is protected only on machines whose `~/.config/git/ignore` happens to match). Worked example (ProjectHephaestus #1494): the audit claimed three permission fragments cluttered a 'committed config' at `.claude/settings.local.json:11-13`; `git ls-files` and `git log --all` proved the file was NEVER tracked, and `core.excludesFile=/dev/null check-ignore` proved the repo `.gitignore` did not ignore it — only the dev's global `~/.config/git/ignore:1` did. The fix PIVOTED from 'scrub three entries out of the file' (untracked, un-reviewable, recurrence-prone) to 'add an explicit repo-level `.gitignore` rule + a subprocess regression test asserting `git -c core.excludesFile=/dev/null check-ignore -v <path>` returns 0'. Use when: (1) planning a fix for an audit/lint/reviewer finding that cites a file path + line numbers, (2) a finding describes a file as 'committed' / 'in source' — verify tracking first, (3) a file appears ignored locally but you need repo-level defense that survives a contributor lacking your global ignore."
category: architecture
date: 2026-07-01
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [planning, audit-finding, premise-verification, git-ls-files, git-check-ignore, core-excludesfile, global-vs-repo-ignore, untracked-file, committed-config, gitignore, regression-test, stale-premise, verify-before-planning]
---

# Verify an Audit Finding's Premise Against the Current Repo Before Fixing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Objective** | Stop designing fixes off a stale audit premise: verify the finding's stated facts (file is tracked/committed; file is repo-ignored) against the current repo before scoping the fix. |
| **Outcome** | Successful — the premise check flipped the fix from a byte-scrub of an untracked file to a repo-level `.gitignore` rule + regression test that prevents recurrence for every contributor. |
| **Verification** | verified-local — the `git` premise-check commands were run and confirmed in-session on ProjectHephaestus #1494; CI has not yet validated the eventual `.gitignore` regression test. |
| **History** | (initial version) |

## When to Use

- Planning a fix for an audit / lint / reviewer finding that cites a specific `file:line` — treat the cited coordinates and the surrounding narrative as CLAIMS, not ground truth.
- A finding describes a file as "committed", "in source", "checked in", or "in the repo config" — verify the file is actually TRACKED (`git ls-files`, `git log --all`) before planning any edit to it. An untracked file cannot be fixed by editing it: the diff is un-reviewable and does not prevent recurrence.
- A file "appears ignored" on your machine but you need to guarantee it stays out of the repo for a contributor who lacks your personal global ignore — distinguish the repo `.gitignore` from your GLOBAL `~/.config/git/ignore`.
- The audited artifact is not present in the working tree at all — the plan must target the CLASS of problem (an uncommittable artifact), not the specific bytes the audit quotes.

## Verified Workflow

### Quick Reference

```bash
# 1. Is the audit-cited file ACTUALLY tracked/committed? (empty output => it is not)
git ls-files | grep '.claude/settings.local.json'
git log --all --oneline -- .claude/settings.local.json   # empty => NEVER committed

# 2. Repo-level ignore vs. developer's GLOBAL ignore.
#    Disable the global excludes file to test the REPO .gitignore in isolation:
git -c core.excludesFile=/dev/null check-ignore -v .claude/settings.local.json
#    rc=1 (no output) => the repo .gitignore does NOT defend the file.
#    Compare with the normal call (global ignore active):
git check-ignore -v .claude/settings.local.json
#    e.g. prints "/home/you/.config/git/ignore:1:**/.claude/settings.local.json"
#    => the file is protected ONLY by YOUR global ignore, not by the repo.

# 3. Regression test that pins the protection to the REPO, not one machine:
#    (subprocess unit test)
#    subprocess.run(["git","-c","core.excludesFile=/dev/null",
#                    "check-ignore","-v",".claude/settings.local.json"])
#    assert result.returncode == 0   # repo .gitignore now covers it
```

### Detailed Steps

1. **Read the finding as a set of claims.** An audit body typically asserts (a) a file exists,
   (b) it is committed/tracked, (c) it lives at `path:line`, and (d) some content is wrong. Each
   is independently falsifiable. Do NOT begin fix design until each load-bearing claim is checked.

2. **Verify tracking before verifying content.** Run `git ls-files | grep <path>` and
   `git log --all -- <path>`. Empty results mean the file is NOT under version control and was
   NEVER committed — the audit's "committed config" premise is false for this repo. Editing the
   file now yields an untracked, un-reviewable change that also does nothing to prevent the file
   from being committed by a future contributor.

3. **Distinguish repo ignore from global ignore.** A file can look "handled" locally purely
   because of your personal `~/.config/git/ignore`. Prove where the protection actually lives:
   `git -c core.excludesFile=/dev/null check-ignore -v <path>`. If this returns rc=1 (nothing),
   the repo `.gitignore` does NOT cover the file — the defense is a per-machine accident. Run the
   plain `git check-ignore -v <path>` to see which ignore file (repo vs. global) actually matches.

4. **Pivot the fix to the real, durable defect.** If the premise was "scrub N entries out of a
   committed file" but the file is untracked and undefended at the repo level, the durable fix is
   the CLASS fix: add an explicit repo-level `.gitignore` rule so the file can never be committed,
   plus a regression test. The specific bytes the audit quoted are irrelevant to recurrence.

5. **Encode the protection as a repo-portable regression test.** Write a subprocess unit test that
   invokes `git -c core.excludesFile=/dev/null check-ignore -v <path>` and asserts
   `returncode == 0`. The `core.excludesFile=/dev/null` flag removes any dependence on a
   developer's global ignore, so the test fails unless the protection lives in the repo itself.

6. **State the un-inspectable assumptions explicitly.** When the audited artifact is not present
   in your tree, you cannot inspect the specific offending bytes — say so, and scope the fix to the
   class of problem (an uncommittable artifact) rather than the literal contents you never saw.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Take the audit premise at face value | Plan to "scrub the three fragment permission entries (`Bash(for f:*)`, `Bash(do echo:*)`, `Bash(done)`) out of the committed `.claude/settings.local.json`" | `git ls-files \| grep settings.local` and `git log --all -- .claude/settings.local.json` were both EMPTY — the file was never tracked. The audit's "committed config" premise and its `:11-13` line numbers were false for this repo; editing the file would be an untracked, un-reviewable diff that also never prevents recurrence. | An audit's "committed"/`path:line` claim is a CLAIM. Prove tracking with `git ls-files` + `git log --all` before designing any edit. |
| Assume "it's already gitignored, nothing to do" | Ran plain `git check-ignore -v .claude/settings.local.json`, saw it matched, concluded the repo already defends against committing it | The match came from `~/.config/git/ignore:1` (the developer's GLOBAL ignore), not the repo `.gitignore`. `git -c core.excludesFile=/dev/null check-ignore -v <path>` returned rc=1 — a contributor without that global ignore would commit the file. | `git check-ignore` conflates repo and global ignore. Re-run with `core.excludesFile=/dev/null` to isolate the REPO `.gitignore`; only that is portable across contributors. |
| Trust the audit machine's file contents unseen | Plan referenced the three specific permission entries as if inspecting them | The file does not exist in this repo/tree, so the entries were never directly inspected — the plan relied entirely on the audit body's description. | When the artifact is absent, target the CLASS of problem (uncommittable artifact) and LABEL the byte-level detail as an unverified, audit-sourced assumption — do not present it as observed fact. |

## Results & Parameters

Confirmed session evidence (ProjectHephaestus #1494, run in-session):

```text
$ git ls-files | grep settings.local
(no output)                          # NOT tracked

$ git log --all --oneline -- .claude/settings.local.json
(no output)                          # NEVER committed

$ git -c core.excludesFile=/dev/null check-ignore -v .claude/settings.local.json ; echo rc=$?
rc=1                                 # repo .gitignore does NOT ignore it

$ git check-ignore -v .claude/settings.local.json ; echo rc=$?
/home/USER/.config/git/ignore:1:**/.claude/settings.local.json	.claude/settings.local.json
rc=0                                 # ignored ONLY by the developer's GLOBAL ignore
```

Durable fix shape (the pivot the premise check produced):

```gitignore
# .gitignore (repo-level — defends every contributor, not just those with a global ignore)
.claude/settings.local.json
```

```python
# Regression test — protection must live in the repo, not one machine.
import subprocess

def test_settings_local_is_repo_ignored():
    result = subprocess.run(
        ["git", "-c", "core.excludesFile=/dev/null",
         "check-ignore", "-v", ".claude/settings.local.json"],
        capture_output=True, text=True,
    )
    # rc == 0 only if the REPO .gitignore matches (global ignore is disabled here).
    assert result.returncode == 0, (
        "repo .gitignore must ignore .claude/settings.local.json "
        "independent of any developer global ignore"
    )
```

Reviewer focus / uncertain assumptions to flag in the plan:

- The audit machine's `.claude/settings.local.json` "contains those three entries" — unverified externally; the file is absent here, so the plan targets the uncommittable-artifact class, not the specific bytes.
- `git check-ignore` behavior in CI — if CI uses a different `core.excludesFile` or checks out without a root `.gitignore`, the test could behave differently; the `core.excludesFile=/dev/null` flag mitigates this but was validated locally only, not in CI.
- No existing test covers `.gitignore` (grep found none) — a reviewer should confirm the new test does not duplicate an import-surface or config test.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1494 — audit claimed permission fragments cluttered a "committed" `.claude/settings.local.json:11-13`; premise check proved the file was never tracked and only globally (not repo-) ignored, pivoting the fix to a repo `.gitignore` rule + `core.excludesFile=/dev/null` regression test. | verified-local — git premise-checks run and confirmed in-session; CI validation of the eventual test pending. |
