---
name: squash-only-repo-merge-method-docs
description: "Repo allows squash-only merges (allow_rebase_merge=false); using --rebase silently fails to arm auto-merge (CLI) or fails at runtime (code/API). The wrong merge method hides in docs, code, AND skill/plugin instruction files. The robust fix is settings-aware merge-method selection (query gh api repos/<repo>, pick rebase->squash->merge), not hardcoding a different fixed method. Use when: (1) gh pr merge --auto --rebase returns no error but auto-merge is not armed, (2) project docs or CLAUDE.md instruct --rebase for a repo that has disabled rebase merges, (3) a PyGithub pr.merge(merge_method='rebase') callsite on a squash-only repo fails with 'Rebase merges are not allowed on this repository', (4) verifying which merge method a repo supports before arming auto-merge, (5) updating stale documentation that references the wrong merge flag, (6) auditing a squash-only repo — grep for BOTH the gh pr merge --rebase CLI form and the merge_method=\"rebase\" code/API form, (7) a skill/plugin instruction file (e.g. /learn, /finish-branch SKILL.md) hardcodes gh pr merge --auto --rebase against a squash-only target repo, (8) deciding the merge method for a cross-repo gh pr merge — detect allowed methods instead of hardcoding."
category: ci-cd
date: 2026-06-09
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: squash-only-repo-merge-method-docs.history
tags:
  - auto-merge
  - squash
  - rebase
  - github
  - docs
---

# Squash-Only Repo: Use --squash Not --rebase for Auto-Merge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Fix stale `--rebase` instruction in CLAUDE.md for a squash-only repo |
| **Outcome** | CLAUDE.md corrected; PR #668 merged with `autoMergeRequest.mergeMethod=SQUASH` confirmed |
| **Verification** | verified-ci |

Some GitHub repos have `allow_rebase_merge: false` and `allow_squash_merge: true`. When
project documentation (e.g. CLAUDE.md) instructs `gh pr merge --auto --rebase`, auto-merge
silently fails to arm in squash-only repos — `gh pr merge` accepts the command without error
but does not enable auto-merge. The fix is to use `--squash` and to correct any stale docs.

**The wrong merge method also hides in CODE, not just docs.** A hardcoded PyGithub
`pr.merge(merge_method="rebase")` callsite (or a `merge_method: rebase` config value) on a
squash-only repo does **not** fail silently — it fails loudly at runtime with errors like
`GraphQL: Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)`
and `GraphQL: Rebase merges are not allowed on this repository. (mergePullRequest)`. When
auditing a squash-only repo, grep for BOTH the `gh pr merge --rebase` CLI form AND the
`merge_method="rebase"` code/API form.

## When to Use

- `gh pr merge --auto --rebase` completes without error but auto-merge is not armed
- Project CLAUDE.md or other docs instruct `--rebase` for a GitHub repo
- A PyGithub `pr.merge(merge_method="rebase")` callsite on a squash-only repo fails at runtime
  with "Rebase merges are not allowed on this repository" (the code form of this bug)
- Auditing a squash-only repo — grep for BOTH the `gh pr merge --rebase` CLI form and the
  `merge_method="rebase"` code/API form (docs are not the only place the wrong method hides)
- Verifying which merge method a repo supports before writing automation or instructions
- Updating stale documentation that references the wrong merge flag for a repo
- CI gate (`pr-policy`) reports auto-merge not enabled even though `--auto` was issued
- A skill/plugin instruction file (e.g. `/learn`, `/finish-branch` `SKILL.md`) hardcodes
  `gh pr merge --auto --rebase` against a squash-only target repo — a tooling skill's OWN
  instructions are a place the wrong-merge-method bug hides, not just repo docs or code
- Deciding the merge method for a cross-repo `gh pr merge` — **detect** the target repo's
  allowed methods instead of hardcoding any fixed flag (the robust, settings-aware fix)

## Verified Workflow

### Quick Reference

```bash
# Step 1: Check which merge methods the repo allows
gh api repos/OWNER/REPO --jq '{rebase: .allow_rebase_merge, squash: .allow_squash_merge, merge: .allow_merge_commit}'
# Example output: {"rebase": false, "squash": true, "merge": false}

# Step 2: Use the correct flag — squash-only repos require --squash
gh pr merge --auto --squash   # NOT --rebase

# Step 3: Verify auto-merge is armed with the correct method
gh pr view <PR_NUMBER> --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
# Should output: SQUASH

# Step 4 (audit): find EVERY wrong-method occurrence — BOTH the CLI form and the code/API form
grep -rn 'merge_method="rebase"\|--auto --rebase\|gh pr merge.*--rebase' .
# Catches: PyGithub pr.merge(merge_method="rebase"), gh pr merge --auto --rebase in docs/scripts
```

### Settings-aware merge-method selection (the robust fix)

The reactive fix of swapping a hardcoded `--rebase` to a hardcoded `--squash` just trades one
fixed assumption for another — it breaks on a rebase-only or merge-only target. Instead, **detect**
the target repo's allowed methods and pick dynamically. Default preference order is
`rebase` (linear history) -> `squash` -> `merge` commit; it is configurable, but rebase->squash->merge
is the documented default. If the repo policy mandates squash (e.g. ProjectHephaestus, enforced by
its `pr-policy` gate), detection naturally yields `--squash` because rebase is disabled there — no
special-casing needed.

```bash
# Pick the auto-merge flag the TARGET repo actually allows.
# Preference order: rebase (linear history) -> squash -> merge commit.
choose_merge_flag() {
  local repo="$1"
  local flag
  flag=$(gh api "repos/${repo}" --jq '[
    (if .allow_rebase_merge then "--rebase" else empty end),
    (if .allow_squash_merge then "--squash" else empty end),
    (if .allow_merge_commit then "--merge"  else empty end)
  ] | .[0] // ""')
  if [ -z "$flag" ]; then
    echo "ERROR: target repo ${repo} allows no merge methods" >&2
    return 1
  fi
  printf '%s\n' "$flag"
}

MERGE_FLAG=$(choose_merge_flag "HomericIntelligence/ProjectMnemosyne")   # -> --squash here
gh pr merge "$PR_NUMBER" --auto "$MERGE_FLAG" --repo HomericIntelligence/ProjectMnemosyne
```

### Detailed Steps

1. **Check repo merge settings** before writing any automation or docs:
   ```bash
   gh api repos/OWNER/REPO --jq '{rebase: .allow_rebase_merge, squash: .allow_squash_merge, merge: .allow_merge_commit}'
   ```

2. **Correct any stale documentation**. Common locations to audit:
   - `CLAUDE.md` — Git Workflow section and PR policy section
   - `CONTRIBUTING.md` — PR workflow steps
   - `.claude/shared/` — shared guidance files
   - Automation scripts that call `gh pr merge`

3. **Create a tracking issue** (required by `pr-policy` CI gate):
   ```bash
   gh issue create --title "docs: fix stale --rebase merge instruction (repo is squash-only)" \
     --body "CLAUDE.md instructs gh pr merge --auto --rebase but the repo has rebase disabled."
   ```

4. **Commit the doc fix** (signed), with `Closes #N` in the commit body, and arm auto-merge with `--squash`:
   ```bash
   git commit -S -m "docs(claude): use --squash for auto-merge (repo has rebase disabled)

   Closes #<N>"
   gh pr merge --auto --squash
   ```

5. **Confirm** auto-merge is armed correctly:
   ```bash
   gh pr view <PR> --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
   # Expect: SQUASH
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh pr merge --auto --rebase` on squash-only repo | Issued auto-merge with `--rebase` flag as instructed by stale CLAUDE.md | Repo has `allow_rebase_merge: false`; the command appeared to succeed but auto-merge was not armed | Always verify allowed merge methods with `gh api repos/OWNER/REPO` before using `--rebase` |
| Relying on stale docs | CLAUDE.md documented `--rebase` because it was originally correct | Repo settings changed (or were always squash-only) without corresponding doc update | Docs about merge flags rot silently; audit CLAUDE.md against `gh api` before issuing PRs |
| Hardcoded `pr.merge(merge_method="rebase")` in PyGithub code | `hephaestus/github/pr_merge.py` hardcoded `merge_method="rebase"` while a sibling path (`github_api.py:gh_pr_create`) already used `--auto --squash` | Failed at runtime (not silently) with `GraphQL: Rebase merges are not allowed on this repository. (mergePullRequest)` / `...(enablePullRequestAutoMerge)` — ~27 such errors in one automation run | The wrong method hides in CODE too, not just docs; grep for `merge_method="rebase"` as well as the CLI `--rebase` form, and watch for inconsistency between sibling callsites. Durable guard: a unit test that uses `inspect.getsource` on the module and asserts the source contains no `merge_method="rebase"` and does contain `merge_method="squash"` |
| Swapped a hardcoded `--rebase` to a hardcoded `--squash` (e.g. learn skill #867) | Reactive fix: replaced the fixed `--rebase` flag with a fixed `--squash` flag | Still wrong for a rebase-only or merge-only target repo; just trades one fixed assumption for another | Detect the target repo's allowed methods via `gh api repos/<repo>` and pick dynamically (rebase->squash->merge) — see `choose_merge_flag` |
| `/learn` skill plugin instruction ran `gh pr merge --auto --rebase` against ProjectMnemosyne (squash-only) | The shipped `/learn` `SKILL.md` (stale plugin cache line 420) hardcoded `--auto --rebase --repo HomericIntelligence/ProjectMnemosyne` | Rejected: `Merge method rebase merging is not allowed on this repository`; three sub-agents each hit it and independently fell back to `--squash` | A tooling skill's OWN instructions are a place the wrong-merge-method bug hides; fixed via settings-aware detection (ProjectHephaestus #911) |
| Regression test asserted `template = mod._AGENT_PROMPT_TEMPLATE` for an f-string in `hephaestus/github/tidy.py` | The hardcoded `gh pr merge --auto --merge` lived inside an f-string built at call time by `_make_agent_prompt()`, not a module-level constant | `AttributeError: module 'hephaestus.github.tidy' has no attribute '_AGENT_PROMPT_TEMPLATE'` | For f-string templates, assert on `inspect.getsource(mod._make_agent_prompt)` instead — see "Regression-test pattern for f-string templates" below |
| Earlier plan iteration used a 10-line look-back heuristic for "this hit is inside an instructional `choose_merge_flag` example" | The lint scanned for hardcoded flags but exempted any hit within 10 lines of `choose_merge_flag` mention | Brittle: re-orderings or a long preface broke the heuristic; a skill author could not predict whether their example would lint-clean | Replace with an explicit per-block marker `<!-- merge-method-allowed: example -->` on the immediately preceding non-blank line of the fenced block; the lint walks fence -> first non-blank and checks exact-string equality |
| `gh api --jq '...' -` to process a stdin-piped response body | `printf '%s' "$raw" \| gh api --jq '...' -` to chain a second jq pass over the captured response | Non-standard usage; `gh api --jq` is documented to operate on the response of its own API call, not stdin. Some `gh` versions silently fail | Use plain `jq -r '...' 2>/dev/null` directly on the response body — the conventional, unsurprising form |

## Results & Parameters

### Repo merge-method audit command (copy-paste ready)

```bash
# Check what merge methods are enabled — run once before writing any PR automation
gh api repos/OWNER/REPO --jq '
  "rebase=\(.allow_rebase_merge) squash=\(.allow_squash_merge) merge=\(.allow_merge_commit)"'
```

### Confirmed settings for ProjectHephaestus

```json
{"rebase": false, "squash": true, "merge": false}
```

Always use `gh pr merge --auto --squash` in ProjectHephaestus (and any repo with the same settings).

### Settings-aware merge-flag selection (preferred over any hardcode)

Rather than hardcoding `--squash` (or `--rebase`), query the target repo and pick the first
allowed method in preference order `rebase` -> `squash` -> `merge`, erroring if none are allowed.
This yields `--squash` on a squash-mandated repo without special-casing, and stays correct if a
repo enables/disables a method later.

```bash
# Pick the auto-merge flag the TARGET repo actually allows.
# Preference order: rebase (linear history) -> squash -> merge commit.
choose_merge_flag() {
  local repo="$1"
  local flag
  flag=$(gh api "repos/${repo}" --jq '[
    (if .allow_rebase_merge then "--rebase" else empty end),
    (if .allow_squash_merge then "--squash" else empty end),
    (if .allow_merge_commit then "--merge"  else empty end)
  ] | .[0] // ""')
  if [ -z "$flag" ]; then
    echo "ERROR: target repo ${repo} allows no merge methods" >&2
    return 1
  fi
  printf '%s\n' "$flag"
}

MERGE_FLAG=$(choose_merge_flag "HomericIntelligence/ProjectMnemosyne")   # -> --squash here
gh pr merge "$PR_NUMBER" --auto "$MERGE_FLAG" --repo HomericIntelligence/ProjectMnemosyne
```

The preference order is configurable, but rebase->squash->merge is the documented default. A repo
whose policy mandates squash (e.g. ProjectHephaestus, enforced by its `pr-policy` gate) has rebase
disabled, so detection lands on `--squash` automatically.

### Tiered helper sourcing for cross-repo callers

The recommended call form is **source the helper** rather than re-define the function inline. The helper now exists as a real, sourceable file in ProjectHephaestus: `scripts/choose_merge_flag.sh`. Sub-agents running a Hephaestus skill from inside *another* repo (e.g. running `/finish-branch` against a ProjectMnemosyne worktree) cannot see this file via the current worktree's `git rev-parse --show-toplevel`. Use a three-candidate tiered lookup with `--squash` as the fallback (verified org-wide-correct for every HomericIntelligence repo per `tooling-gh-pr-auto-merge-rebase-squash-fallback` v2.0.0):

```bash
HELPER=""
for cand in \
    "${HEPHAESTUS_REPO_ROOT:-}/scripts/choose_merge_flag.sh" \
    "$(git rev-parse --show-toplevel 2>/dev/null)/scripts/choose_merge_flag.sh" \
    "$HOME/Projects/ProjectHephaestus/scripts/choose_merge_flag.sh"; do
    if [ -r "$cand" ]; then HELPER="$cand"; break; fi
done
if [ -n "$HELPER" ]; then
    . "$HELPER"
    MERGE_FLAG=$(choose_merge_flag "$(gh repo view --json nameWithOwner --jq .nameWithOwner)") \
        || MERGE_FLAG="--squash"   # safe org-wide default per HomericIntelligence policy
else
    MERGE_FLAG="--squash"
fi
gh pr merge --auto "$MERGE_FLAG"
```

The helper itself uses plain `jq -r` on the captured response body (no `gh api --jq -` stdin-pipe trick — that pattern is non-standard and silently fails on some `gh` versions).

### Marker-based lint exemption for instructional code blocks

The companion lint (`hephaestus/validation/skill_merge_method.py` in ProjectHephaestus) scans skill files for hardcoded `gh pr merge --auto --(rebase|squash|merge)` and would otherwise flag any "do-not-copy" example. The exemption is an explicit per-block marker on the immediately preceding non-blank line of the fenced code block:

```text
<!-- merge-method-allowed: example -->
\`\`\`bash
gh pr merge --auto --rebase   # OLD: do not copy
\`\`\`
```

The lint walks backward from the matching line to the fence open, then to the first non-blank line, and checks exact-string equality. The marker exempts only the *immediately following* block; a second hardcoded flag in a *later* block is still flagged. Earlier plan iterations used a fragile 10-line look-back heuristic for "is this hit near a `choose_merge_flag` mention?" — replaced with the marker because it's concrete, file-local, and predictable for skill authors.

### Regression-test pattern for f-string templates

When the hardcoded merge flag lives inside an f-string built at call time (not a module-level constant), an `inspect.getsource` assertion is the durable regression guard. Example for `hephaestus/github/tidy.py:_make_agent_prompt`:

```python
import inspect
import re
from hephaestus.github import tidy

def test_agent_prompt_does_not_hardcode_merge_method() -> None:
    source = inspect.getsource(tidy._make_agent_prompt)
    assert not re.search(r"--auto\s+--(rebase|squash|merge)\b", source), \
        "tidy._make_agent_prompt still hardcodes a merge method; use choose_merge_flag instead."
    assert "choose_merge_flag" in source
```

This is the f-string analogue of the v1.1.0 `inspect.getsource(pr_merge)` test for the PyGithub call-site bug. Asserting on `_AGENT_PROMPT_TEMPLATE` (assuming a module constant) raises `AttributeError` because the template is constructed inside the function — a common gotcha.

### Verification that auto-merge is armed

```bash
gh pr view <PR> --json autoMergeRequest
# Expected (squash-only repo):
# {"autoMergeRequest": {"mergeMethod": "SQUASH", "enabledAt": "...", "enabledBy": {...}}}
```

### Code-form fix (PyGithub) and regression guard

The same bug in PyGithub code is fixed by changing the merge method on the `pr.merge(...)` call:

```python
# WRONG on a squash-only repo — fails at runtime:
pr.merge(merge_method="rebase")
# Right:
pr.merge(merge_method="squash")
```

Also update any log/argparse strings that say "rebase". The durable regression guard is a
source-inspection unit test:

```python
import inspect
from hephaestus.github import pr_merge

def test_pr_merge_uses_squash_not_rebase():
    src = inspect.getsource(pr_merge)
    assert 'merge_method="rebase"' not in src
    assert 'merge_method="squash"' in src
```

This was shipped in ProjectHephaestus PR #904 (Closes #718, merged 2026-06-03, verified-ci).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-28: CLAUDE.md had stale `--rebase` instruction; PR #668 corrected it | `gh pr view 668 --json autoMergeRequest` confirmed `mergeMethod=SQUASH`; issue #666 |
| ProjectHephaestus | 2026-06-03: `hephaestus/github/pr_merge.py` hardcoded `pr.merge(merge_method="rebase")` — code form of the same bug, ~27 runtime GraphQL errors in one automation run; PR #904 changed it to `merge_method="squash"` | Closes #718; durable guard = `inspect.getsource` unit test asserting no `merge_method="rebase"`; verified-ci |
| ProjectHephaestus | 2026-06-03: `/learn` plugin instruction (`skills/learn/SKILL.md`, stale plugin cache line 420) hardcoded `--auto --rebase` vs squash-only ProjectMnemosyne; three sub-agents each hit `Merge method rebase merging is not allowed on this repository`; filed issue #911 for settings-aware selection (supersedes #721, #867) | `choose_merge_flag` pattern documented; verified-ci |
| ProjectHephaestus | 2026-06-09: PR #1069 ships `scripts/choose_merge_flag.sh` (sourceable Bash helper) + `hephaestus/validation/skill_merge_method.py` (marker-aware lint) + tiered sourcing in 4 skill files + `inspect.getsource` regression test for the `tidy.py` f-string template | Closes #911, Closes #721; all CI green (33 checks), signed commit, body-format compliant; verified-ci |
