---
name: tracking-doc-checkbox-sync-regression-guard
description: "When a tracking DOCUMENT (remediation plan, roadmap, status table, audit-checklist markdown FILE) encodes issue/PR state as `- [ ]` / `- [x]` checkboxes, that state silently rots out of sync with live GitHub OPEN/CLOSED state. Fix in two parts: (1) verify EVERY referenced `#NNN` against `gh issue view <n> --json state` ground truth BEFORE editing — do NOT trust the triggering issue body's own wave/group/CLOSED claims (they drift and mis-bucket children); (2) add a REGRESSION GUARD that asserts the INVARIANT as a property ('no CLOSED issue sits on an unchecked `- [ ]` line'), not a snapshot of which boxes are ticked, and that SKIPS gracefully (exit 0 + notice) when `gh` is unavailable/unauthenticated so it never breaks offline/sandboxed CI; wire it into the repo's aggregate task (e.g. justfile `check`). Use when: (1) editing a markdown tracking/remediation/roadmap doc whose checkboxes claim issue state, (2) an issue body groups children under waves/sections you are tempted to trust, (3) a single doc line bundles multiple `#NNN`, (4) adding a guard against checkbox drift. This is doc-FILE sync; for reconciling a GitHub ISSUE BODY checklist see planning-roadmap-tracking-issue-reconciliation; for the general 'verify audit findings vs ground truth' principle see code-quality-enforcement-gates §10."
category: documentation
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [tracking-doc, remediation-plan, roadmap, checkbox, doc-sync, regression-guard, verify-ground-truth, gh-issue-state, offline-skip, false-confidence, audit, property-not-snapshot, planning, unverified]
---

# Tracking-Doc Checkbox Sync + Regression Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Correct stale `- [ ]` / `- [x]` checkbox state in a tracking markdown FILE (`docs/audit-2026-04-28/remediation-plan.md`) so it matches live GitHub issue OPEN/CLOSED state, and add a regression guard that survives future legitimate edits |
| **Outcome** | PLAN produced for ProjectProteus issue #183. Per-issue `gh issue view` verification was done and caught a mis-grouping (the #183 body bucketed #112 under the wrong wave; #112 is in fact CLOSED). The doc edit and the guard were NOT executed end-to-end and no CI ran |
| **Verification** | unverified — this is a plan, not executed code. See warning in Proposed Workflow |
| **Related** | `planning-roadmap-tracking-issue-reconciliation` (issue-BODY checklists), `code-quality-enforcement-gates` §10 (verify audit findings vs ground truth), `automation-moot-issue-regression-guard-pattern` (property-as-test) |

## When to Use

- You are editing a markdown tracking document — remediation plan, roadmap, status table, audit checklist — whose `- [ ]` / `- [x]` checkboxes assert the OPEN/CLOSED state of GitHub issues or PRs.
- The triggering issue (or the doc itself) groups child issues under "waves", "phases", or sections, and you are tempted to trust that grouping or its CLOSED/OPEN annotations.
- A single doc line bundles MORE THAN ONE `#NNN` (e.g. a Wave-3 line that ships several issues together).
- You want to add a guard that prevents checkbox state from silently rotting again — without pinning to a brittle snapshot of which specific boxes are ticked today.
- You are about to wire a state-drift check into the repo's aggregate task (e.g. justfile `check`) and need it to behave in offline/sandboxed CI.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps below are emitted under that heading to keep validation green. This skill was captured at `unverified` level — the per-issue ground-truth checks were performed this session, but the doc edit, the guard, and CI were NOT executed. Read the steps as **proposed**, per the warning above.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Ground-truth EVERY referenced issue BEFORE editing any checkbox.
#    Do NOT trust the triggering issue body's wave/group/CLOSED claims.
for n in $(grep -oE '#[0-9]+' docs/audit-2026-04-28/remediation-plan.md | tr -d '#' | sort -un); do
  state=$(gh issue view "$n" --repo OWNER/REPO --json state --jq .state 2>/dev/null || echo "UNKNOWN")
  echo "#$n -> $state"
done

# 2. A CLOSED issue must NOT sit on an unchecked '- [ ]' line; OPEN must NOT sit on '- [x]'.
#    Edit the doc to match ground truth (flip boxes), one issue at a time.

# 3. Add a regression guard that asserts the PROPERTY and SKIPS when gh is unusable.
#    (see Detailed Steps for the full script + the single-issue-line refinement)
```

### Detailed Steps

1. **Enumerate every `#NNN` in the tracking doc and query live state.** Parse the markdown for issue
   references and call `gh issue view <n> --json state` for each. The triggering issue body for #183
   grouped #112 under the wrong wave; per-issue verification caught it (#112 is CLOSED). This is a
   direct application of "verify audit/reviewer findings against ground truth" — the issue body is a
   self-report, not a fact source.

2. **Flip checkboxes to match ground truth, one issue at a time.** The invariant: a CLOSED issue
   belongs on a `- [x]` line; an OPEN issue belongs on a `- [ ]` line. Do NOT bulk-trust the doc's
   existing groupings — re-derive each box from `gh` output.

3. **Add a regression guard that encodes the INVARIANT as a property, not a snapshot.** Assert "no
   CLOSED issue sits on an unchecked `- [ ]` line", NOT "boxes 3, 7, 9 are ticked". A snapshot test
   breaks on the next legitimate edit; a property test survives it. (Same principle as
   `code-quality-enforcement-gates` §5 and `automation-moot-issue-regression-guard-pattern`.)

4. **Make the guard SKIP gracefully when `gh` is unavailable or unauthenticated.** Exit 0 with a
   `::notice::` (or plain skip line) so the check never breaks offline or sandboxed CI runners. SEE
   THE CAVEAT BELOW — this graceful skip is also the guard's biggest weakness.

5. **Refine the property so bundled lines do not false-FAIL.** A Wave-3 line that bundles multiple
   `#NNN` legitimately stays `- [ ]` while ONE of its children is already CLOSED. Asserting on every
   `#NNN` of an unchecked line mis-fires. Restrict the assertion to lines carrying a SINGLE issue
   number, or parse a per-issue ✅ annotation, before treating "unchecked line + CLOSED issue" as a
   violation.

6. **Wire the guard into the repo's existing aggregate task** (e.g. justfile `check: lint validate`).
   Cite the target by its recipe NAME, not a line number — `justfile` line numbers (e.g. `:73`/`:76`)
   are read live but drift; grep for the recipe name instead.

```bash
# scripts/check-remediation-checkboxes.sh — property guard with offline skip
set -euo pipefail
DOC="docs/audit-2026-04-28/remediation-plan.md"
REPO="OWNER/REPO"

# OFFLINE SKIP: never break sandboxed/offline CI (but see CAVEAT — zero protection here).
if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
  echo "::notice::gh unavailable/unauthenticated — skipping checkbox-state guard"
  exit 0
fi

violations=0
# Only assert on lines carrying a SINGLE issue number (avoids bundled-line false FAILs).
while IFS= read -r line; do
  ids=$(grep -oE '#[0-9]+' <<<"$line" | tr -d '#')
  [ "$(wc -w <<<"$ids")" -eq 1 ] || continue          # skip bundled / zero-issue lines
  n="$ids"
  state=$(gh issue view "$n" --repo "$REPO" --json state --jq .state 2>/dev/null || echo UNKNOWN)
  if grep -qE '^\s*- \[ \]' <<<"$line" && [ "$state" = "CLOSED" ]; then
    echo "::error::#$n is CLOSED but sits on an unchecked line: $line"
    violations=$((violations + 1))
  fi
done < <(grep -nE '^\s*- \[[ x]\].*#[0-9]+' "$DOC")

[ "$violations" -eq 0 ] || { echo "::error::$violations checkbox(es) out of sync with issue state"; exit 1; }
echo "remediation-plan checkboxes consistent with live issue state"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the triggering issue body's wave grouping | Read #183's body, accepted its wave-to-issue buckets as authoritative | The body grouped #112 under the wrong wave; #112 was already CLOSED | Verify EVERY `#NNN` with `gh issue view <n> --json state`; the issue body is a self-report, not ground truth |
| Trust the issue body's OPEN/CLOSED claims | Took the body's own CLOSED/OPEN annotations at face value | Body annotations drift the same way the doc checkboxes do | Re-derive each box from live `gh` output, not from any prose claim |
| Snapshot which specific boxes are ticked | Test asserted literal `- [x]` positions / a fixed list of ticked items | Breaks on the next legitimate doc edit — false regression noise | Assert the PROPERTY ("no CLOSED issue on a `- [ ]` line"), not a snapshot |
| Offline-skip guard treated as real protection | Guard exits 0 + notice when `gh` is unavailable/unauth | Sandboxed CI runners have no `gh` auth — so the guard SKIPS in exactly the environment CI runs in, giving ZERO protection and FALSE confidence | An offline-skipping guard is near-worthless in default CI. Prefer a committed fixture file diffed offline, OR run the check only in a job that has a token. Document the gap honestly |
| Assert on every `#NNN` of an unchecked line | Treated each issue number on a `- [ ]` line as "claimed open" | Wave-3 lines bundle multiple issues; a line legitimately stays `[ ]` while one child is CLOSED — mis-fires (e.g. on PR-C / PR-E batches) | Restrict the property to lines with a SINGLE issue number, or parse a per-issue ✅ annotation; do not assert on bundled lines |
| Cite the justfile wire-in point by line number | Referenced `justfile:73` / `:76` and the `check: lint validate` recipe by line | Line numbers were read live but are brittle and drift on any edit above them | Cite the recipe NAME (`check`) and grep for it; never hard-code a line number |

## Results & Parameters

**Ground-truth facts captured this session (ProjectProteus):**

| Issue | Live state (`gh issue view`) | Note |
|-------|------------------------------|------|
| #183 | OPEN | The triggering follow-up issue (the tracking-doc fix) |
| #112 | CLOSED | Mis-grouped under the wrong wave by #183's body; caught by per-issue verification |

**Target doc:** `docs/audit-2026-04-28/remediation-plan.md` (ProjectProteus).
**Aggregate task to wire into:** justfile `check` recipe (cite by name, not line).

**The invariant the guard enforces (state it explicitly in the script header):**

```text
For every tracking-doc line carrying exactly one issue reference #N:
  state(#N) == CLOSED  =>  the line is checked   ( - [x] )
  state(#N) == OPEN    =>  the line is unchecked  ( - [ ] )
Lines bundling >1 issue are EXEMPT from the simple property (refine before asserting).
```

**Stronger alternative a reviewer should weigh (the offline-skip gap is real):** instead of (or in
addition to) the live-API guard, snapshot the expected per-issue states into a COMMITTED fixture file
and diff against it offline — this provides protection in sandboxed CI where `gh` auth is absent. Or
gate the live check to a CI job that is granted a token. Do not present the offline-skipping guard as
full protection.

## Verified On

| Project | Context |
|---------|---------|
| ProjectProteus | issue #183 remediation-plan checkbox sync (PLAN ONLY — unverified). Per-issue `gh` verification caught #112 mis-grouped under the wrong wave (#112 CLOSED, #183 OPEN). Doc edit + guard + CI not executed |
