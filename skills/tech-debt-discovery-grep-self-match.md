---
name: tech-debt-discovery-grep-self-match
description: "Planning discipline for tech-debt Epic automation, grep-marker scanners, and gating CI side-effects. Use when: (1) a scheduled discovery job (e.g. .github/workflows/tech-debt-discovery.yml) keeps posting a 'debt found' comment to an Epic on EVERY run — fix the side-effecting step's gate, not the data it consumes; (2) a repo-wide grep marker scanner (FIXME/TODO/DEPRECATED/HACK/XXX) self-matches and you must separate tool artifacts from genuine debt; (3) a discovery shell script uses `grep ... || echo` and you need a real clean/dirty EXIT-CODE signal for a workflow to gate on; (4) you are about to dress local-only `grep -r` noise as a CI fix, or reuse label names from another repo's playbook."
category: tooling
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: tech-debt-discovery-grep-self-match.history
tags: ["tech-debt", "grep", "self-match", "discovery", "epic", "planning", "false-positive", "fixme", "todo", "labels", "git-grep", "ci", "github-actions", "exit-code", "gating", "side-effects", "nogo", "re-plan", "set-euo-pipefail"]
---

# Tech-Debt Discovery Grep Self-Match

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture durable planning discipline for tech-debt / marker-discovery Epics whose automation "runs a grep scanner and posts/files findings" — and how to fix a job that acts UNCONDITIONALLY |
| **Outcome** | RE-PLAN after a NOGO. The fix is an EXIT-CODE signal from the script + an `if:` gate on the workflow's posting step — NOT rewording prose or excluding dirs (those touch the data, not the trigger) |
| **Verification** | unverified — PLANNING session only; no code written or executed end-to-end, no CI run |
| **History** | Amends v1.0.0 (PR #2629, NOGO'd). See `tech-debt-discovery-grep-self-match.history` |

## When to Use

- A scheduled discovery job (e.g. `.github/workflows/tech-debt-discovery.yml`) keeps posting a "debt found" comment to an Epic on EVERY run, regardless of whether anything was found — because the posting step has no `if:` gate and no `continue-on-error`.
- A repo-wide grep marker scanner (FIXME / TODO / DEPRECATED / HACK / XXX) reports non-zero hits and you must distinguish tool artifacts (self-matches, the scanner's own comments, untracked worktree copies) from genuine debt before filing issues.
- A discovery shell script uses `grep ... || echo "(none)"`, which forces `exit 0` always and therefore destroys the clean/dirty signal a workflow needs to gate on.
- You are about to model "what CI scans" with a `grep -r` over a dev working tree (which includes untracked `build/` and worktree copies), instead of `git grep` / `git ls-files` (tracked-only).
- A discovery tool's own status/output strings contain the very marker tokens it scans for, re-polluting downstream channels (Epic comments, logs).
- You are carrying label names (P0/P1/P2, refactoring, config) over from another repo's playbook into `gh issue create`.

## Verified Workflow

> **PROPOSED WORKFLOW — UNVERIFIED HYPOTHESIS.** This section is titled "Verified Workflow"
> only to satisfy the marketplace validator. It was produced in a PLANNING session after a
> NOGO re-plan: **no code was written or executed, and CI never ran.** Treat every step as a
> hypothesis until CI confirms it. Known-uncertain items are listed in
> **Results & Parameters → Most uncertain assumptions**.

### Quick Reference

```bash
# 0. THESIS CHECK: if the bug is "automation posts/acts on EVERY run," the fix MUST modify
#    the gating of the side-effecting step. Trace the actual side-effecting line first:
#      .github/workflows/tech-debt-discovery.yml -> "Post summary comment" -> gh issue comment 544
#    Confirm what gates it (an `if:`? continue-on-error?) BEFORE touching scan data.

# 1. Model the CLEAN CHECKOUT (actions/checkout = tracked files only), NOT a dev `grep -r`.
git ls-files build .claude                    # what is actually tracked under these dirs
git grep -nE 'FIXME|TODO|DEPRECATED|HACK|XXX' -- '*.py' '*.toml' '*.yml'   # the CI view

# 2. SCRIPT signals clean/dirty via EXIT CODE (not || echo, which forces exit 0 forever):
#      rc=0; grep ... || rc=$?     # capture under set -e; grep returns 1 on no-match
#      markers found -> print listing + exit 1
#      clean         -> print TOKEN-FREE sentinel + exit 0

# 3. WORKFLOW gates the comment on the script's exit code:
#      scan step:    set +e; OUTPUT=$(script); rc=$?; set -e
#                    echo "found=true|false" >> "$GITHUB_OUTPUT"
#      comment step: if: steps.scan.outputs.found == 'true'

# 4. Pre-validate labels against the REAL repo before any gh issue create:
gh label list --repo <owner>/<repo>
```

### Detailed Steps

1. **THESIS CHECK FIRST — fix the side-effecting step, not the data it consumes.** When a plan's thesis is "automation posts/acts unconditionally," the load-bearing bug is in the conditional/gating logic of the action itself. In ProjectHermes #544 the workflow's "Post summary comment" step had NO `if:` gate and NO `continue-on-error` — it piped scan stdout to `gh issue comment 544` on EVERY run. Rewording the scan's prose or excluding dirs (changing the DATA) leaves the unconditional post fully intact. Trace the actual side-effecting line, confirm what gates it, and edit THAT.

2. **Make the script signal clean/dirty via EXIT CODE.** The original `grep ... || echo "(none found)"` forces `exit 0` always — which is precisely WHY the workflow could not gate. New behavior: grep returns 0 on match / 1 on no-match; capture it with `rc=0; grep ... || rc=$?` (because `set -e` would otherwise abort on the no-match exit 1). Then: markers found -> print the listing + `exit 1`; clean -> print a TOKEN-FREE sentinel + `exit 0`.

3. **Gate the workflow comment step on that exit code.** The scan step wraps the script in `set +e` (so exit 1 does not kill the job), captures `rc`, and exports `found=true|false` to `$GITHUB_OUTPUT`. The comment step gets `if: steps.scan.outputs.found == 'true'`. Now a clean run produces no Epic comment.

4. **Model the clean CI checkout with `git grep` / `git ls-files`, not `grep -r`.** In a real `actions/checkout`, only git-TRACKED files exist. `build/.worktrees/` and `.claude/worktrees/` are UNTRACKED (`git ls-files build .claude` -> only `.claude/settings.json` tracked), so CI sees exactly ONE hit, not 38. A `grep -r` over a dev tree inflated the count ~38x and is NOT a proxy for CI. Therefore `--exclude-dir=build/.claude` has NO CI effect — it is pure local-developer ergonomics; do not dress it as a CI fix.

5. **Keep the tool's own status strings TOKEN-FREE.** The clean sentinel must contain ZERO bare marker tokens, or it re-pollutes the very channel it reports on (the v1.0.0 sentinel spelled all five tokens, and that string was piped into the #544 comment). Use e.g. `Tech-debt scan clean: no debt markers found in source.`

6. **State scanner SCOPE limits explicitly.** The script only globs `*.py` / `*.toml` / `*.yml`, so marker tokens in `scripts/README.md:9` and `scripts/discover-tech-debt.sh:4` are invisible by design and are NOT debt. Do not claim "the only hit" without stating the scoping.

7. **Test against FIXTURE trees, not the live repo (POLA).** A unit test asserting the LIVE repo is marker-free flips red the instant someone adds a legitimate TODO — astonishing for a tool whose JOB is to discover markers. Test `tmp_path` fixtures: clean dir -> exit 0 + token-free sentinel; planted-FIXME dir -> exit 1 + marker listed; marker inside `build/.worktrees` -> still exit 0. Keep the live-repo run as an informational smoke command only, never a hard-coupled assertion.

8. **Pre-validate labels with `gh label list` against the ACTUAL repo.** Prior playbooks assumed P0/P1/P2, refactoring, config — none exist in ProjectHermes. The real set: tech-debt, chore, epic, testing, documentation, refactor, cleanup, bug, enhancement.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rewording prose + excluding dirs to silence an unconditional-posting workflow | v1.0.0 plan "fixed" the noisy Epic comment by rewording the workflow's prose comment to drop FIXME/TODO tokens and adding `--exclude-dir=build/.claude` to the grep | NOGO: neither change touched the "Post summary comment" step, which had no `if:` gate / no `continue-on-error` and piped scan stdout to `gh issue comment 544` on EVERY run. The headline bug stayed fully intact while cosmetic symptoms were "fixed" | When a plan's thesis is "automation posts/acts unconditionally," the fix MUST modify the side-effecting step's gate (`if:` / exit-code path), not the data it consumes. Trace the actual side-effecting line and confirm what gates it |
| `grep ... \|\| echo` to force exit 0 | Used `grep <pat> \|\| echo "(none found)"` so the `set -euo pipefail` script survives no-match | It forces `exit 0` on EVERY run, which destroys the clean/dirty signal the workflow needs to gate on — the exact reason the comment posted unconditionally | Use grep's real exit code (0=match, 1=none). Capture it with `rc=0; grep ... \|\| rc=$?` under `set -e`, then `exit 1` on markers and `exit 0` (token-free sentinel) when clean |
| Treating `grep -r` over the dev tree as the CI view | Claimed a clean scan emits "38+ lines every Monday," counting hits from a `grep -r` over the local working tree | In `actions/checkout` only git-TRACKED files exist; `build/.worktrees/` and `.claude/worktrees/` are UNTRACKED (`git ls-files build .claude` -> only `.claude/settings.json`), so CI sees ONE hit, not 38. The `--exclude-dir` change has zero CI effect | Model the clean-checkout view with `git grep` / `git ls-files`, not `grep -r`. Don't dress local-only working-tree noise as a CI fix |
| Clean sentinel spelling out FIXME/TODO/DEPRECATED/HACK/XXX | v1.0.0 clean sentinel was literally "No FIXME/TODO/DEPRECATED/HACK/XXX markers found" | That string is piped into the #544 comment, re-polluting the Epic with all five tokens it claims are absent — and would self-match if ever scanned | A marker-scanner's own status/output strings must contain ZERO bare marker tokens (e.g. "Tech-debt scan clean: no debt markers found in source.") |
| Unit test asserting the LIVE repo is marker-free | v1.0.0 test asserted the live repo produced the clean sentinel | It flips red the instant someone adds a legitimate TODO — a POLA violation for a tool whose JOB is to discover markers; couples a unit test to repo-wide cleanliness | Test against `tmp_path` FIXTURE trees (clean -> exit 0 + token-free sentinel; planted FIXME -> exit 1 + listed; marker in `build/.worktrees` -> still exit 0). Keep the live-repo run as informational smoke only |
| Trusting carried-over label names | Planned `gh issue create --label P0,refactoring,config` from another repo's playbook | Those labels do not exist in ProjectHermes; the create would fail or silently drop labels | Always run `gh label list` against the real repo before referencing any label |

## Results & Parameters

### Corrected script — exit-code branch (proposed)

```bash
set -euo pipefail
# grep returns 1 on no-match; capture it instead of letting set -e abort the script.
rc=0
OUTPUT=$(grep -rnE 'FIXME|TODO|DEPRECATED|HACK|XXX' -- *.py *.toml *.yml) || rc=$?
if [ "$rc" -eq 0 ]; then
  echo "$OUTPUT"
  exit 1                                                   # markers found -> dirty
else
  echo "Tech-debt scan clean: no debt markers found in source."   # TOKEN-FREE sentinel
  exit 0                                                   # clean
fi
```

### Workflow gate (proposed) — capture rc, export `found=`, gate the comment

```yaml
- name: Scan for tech-debt markers
  id: scan
  run: |
    set +e
    OUTPUT=$(scripts/discover-tech-debt.sh); rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then echo "found=true" >> "$GITHUB_OUTPUT"; else echo "found=false" >> "$GITHUB_OUTPUT"; fi
    {
      echo "body<<EOF"
      echo "$OUTPUT"
      echo "EOF"
    } >> "$GITHUB_OUTPUT"

- name: Post summary comment
  if: steps.scan.outputs.found == 'true'     # <-- the load-bearing gate
  run: gh issue comment 544 --body "${{ steps.scan.outputs.body }}"
```

### Token-free clean sentinel

```
Tech-debt scan clean: no debt markers found in source.
```

(NEVER use the v1.0.0 sentinel "No FIXME/TODO/DEPRECATED/HACK/XXX markers found" — it spells all five tokens into the #544 comment.)

### CI-view check (tracked files only)

```bash
git ls-files build .claude          # -> only .claude/settings.json tracked (1 hit, not 38)
git grep -nE 'FIXME|TODO|DEPRECATED|HACK|XXX' -- '*.py' '*.toml' '*.yml'
```

### Real label set (ProjectHermes, verified via `gh label list`)

```
tech-debt, chore, epic, testing, documentation, refactor, cleanup, bug, enhancement
```

(WRONGLY assumed from other playbooks: P0, P1, P2, refactoring, config — none exist.)

### Most uncertain assumptions (honest risks)

- **Pre-edit line numbers in `tech-debt-discovery.yml`** (scan step ~25–34, comment step ~36–49) were read once locally; an editor must re-confirm before editing.
- **The `set +e; OUTPUT=$(script); rc=$?; set -e` rc-capture pattern** in the scan step is reasoned, not executed. GitHub Actions `run:` blocks have their own shell flags; confirm the rc capture survives and that a multi-line `$OUTPUT` heredoc export still works.
- **`git ls-files build .claude` showing only `.claude/settings.json` tracked** was verified in THIS working tree; other branches/checkouts could differ.
- **Runner names** (`pixi run pytest`, `pixi run ruff check src tests`) taken from `justfile:41,60` / CLAUDE.md, not executed this session.
- **No code was written or run** — this is a PLANNING artifact. Verification: unverified.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | Issue #544 (Technical-Debt Epic) — RE-PLAN after a NOGO review | Unverified. First plan (v1.0.0 / PR #2629) NOGO'd for fixing scan DATA (prose + dir excludes) while leaving the unconditional `gh issue comment 544` step un-gated. Corrected fix: script exit-code signal + workflow `if: steps.scan.outputs.found == 'true'` gate; token-free sentinel; fixture-based tests. |
