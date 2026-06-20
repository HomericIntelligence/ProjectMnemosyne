---
name: tracking-doc-checkbox-sync-regression-guard
description: "When a tracking DOCUMENT (remediation plan, roadmap, status table, audit-checklist markdown FILE) encodes issue/PR state as `- [ ]` / `- [x]` checkboxes, that state silently rots. The PREFERRED guard is a self-contained COMMITTED-FIXTURE INVARIANT TABLE: embed an explicit `declare -A EXPECT=([key]=state ...)` in the test, derive ONE stable key per line (leading `#NNN`, else `PR-X`, else a phrase), and diff each line's actual checkbox char against the expected char — no network, no `gh`, no auth, no SKIP path, deterministic everywhere (including required-CI runners with no issue-read token). Add bidirectional coverage cross-checks via a SEEN set: fail `__MISSING__` if a tracked line's key is absent from EXPECT, and fail if any EXPECT key was never SEEN (deleted/renamed line). Key by the line's STABLE PRIMARY TOKEN, not by scanning every `#NNN`, so an open bundle line with a closed child never false-FAILs. Do NOT use a live `gh issue view` guard: it SKIPs to a no-op when unauthenticated — exactly the required-CI state — giving ZERO protection, and it is non-deterministic. Use when: (1) editing a markdown tracking/remediation/roadmap doc whose checkboxes claim issue state, (2) adding a guard against checkbox drift, (3) a doc line bundles multiple `#NNN`, (4) you need a guard that the committed file itself passes deterministically in offline/sandboxed CI. This applies code-quality-enforcement-gates §5 ('assert the property via static analysis, NOT a live runtime check'); for ISSUE-BODY checklists see planning-roadmap-tracking-issue-reconciliation; for verify-findings-vs-ground-truth see code-quality-enforcement-gates §10."
category: documentation
date: 2026-06-20
version: "2.1.0"
user-invocable: false
verification: verified-local
history: tracking-doc-checkbox-sync-regression-guard.history
tags: [tracking-doc, remediation-plan, roadmap, checkbox, doc-sync, regression-guard, invariant-table, committed-fixture, hermetic-test, shimmed-test, static-analysis-not-runtime, deterministic, offline-ci, no-network, no-silent-failures, forbid-suppressions, bidirectional-coverage, seen-set, missing-sentinel, stable-key, bundle-line, pr-group-scoped, re-verify-same-pr, verify-ground-truth, audit, property-not-snapshot, planning, verified-local, unverified-subpattern]
---

# Tracking-Doc Checkbox Sync + Regression Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Keep `- [ ]` / `- [x]` checkbox state in a tracking markdown FILE (`docs/audit-2026-04-28/remediation-plan.md`) honest, and add a regression guard that (a) the committed file itself passes, and (b) actually protects in a required-CI runner that has NO issue-read token |
| **Outcome** | R1 (re-plan) of ProjectProteus issue #183. The R0 live-`gh` guard got a NOGO (offline-SKIP = zero CI protection; committed artifact failed its own test). R1 replaces it with a committed-fixture INVARIANT TABLE that runs with no network and PASSES deterministically. The embedded test logic was executed this session: PASS on a matching fixture, FAIL on each of 3 negative fixtures (drift / new line / deleted line) as designed |
| **Verification** | verified-local for the v2.0.0 EXPECT-table test logic. The v2.1.0 additions (a re-planning session for **ProjectProteus issue #186**) are a DESIGN: the offline-fixture test was NOT implemented or CI-run this session, so the v2.1.0 sub-pattern is **unverified** until the PR lands and CI runs |
| **History** | [changelog](./tracking-doc-checkbox-sync-regression-guard.history) |
| **Related** | `code-quality-enforcement-gates` §5 (assert the property via static analysis, NOT a live runtime check) and §10 (verify findings vs ground truth); `planning-roadmap-tracking-issue-reconciliation` (issue-BODY checklists); `automation-moot-issue-regression-guard-pattern` (property-as-test). The repo's anti-silent-failure policy — `forbid-suppressions` job (`.github/workflows/_required.yml:53-105`) + `docs/runbooks/no-silent-failures.md` — is the REASON the live-`gh` skip-on-unauth design is disallowed |

## When to Use

- You are editing a markdown tracking document — remediation plan, roadmap, status table, audit checklist — whose `- [ ]` / `- [x]` checkboxes assert the OPEN/CLOSED state of GitHub issues or PRs.
- You want a guard against checkbox drift that the committed file itself PASSES, and that protects in a required-CI runner with **no** issue-read token (i.e. where a live-`gh` guard would SKIP to a no-op).
- A single doc line bundles MORE THAN ONE `#NNN` (e.g. a Wave-3 PR row that ships several issues together) and you must not false-FAIL when one bundled child closes while the row stays `[ ]`.
- You are tempted to query `gh issue view` at test time — read the Failed Attempts first; that design is demoted here.
- You are wiring a state-drift check into the repo's aggregate task (e.g. justfile `check`) and need it deterministic offline.
- The repo has an anti-silent-failure CI policy (e.g. a `forbid-suppressions` job, a `no-silent-failures` runbook) that BANS `|| true` / unconditional `exit 0` / skip-on-error paths — so any test that SKIPs when `gh` is unauthenticated is a policy violation, not just a weak guard.
- You want to PROVE the committed guard is not a no-op (a reviewer demanded it) — see the temp-tree proof in the workflow.
- You are mirroring an existing repo test as a model: mirror its PROPERTY (hermetic/deterministic — e.g. `tests/dispatch-apply.test.sh` shims `curl`, uses a fake token, hits no network), not merely its file location.

## Verified Workflow

> Verified locally this session: the embedded EXPECT-table test logic was executed against a
> matching fixture (PASS, exit 0) and three negative fixtures — checkbox drift, a new untracked
> line, and a deleted line — which each FAILed exactly as designed. The run uses no network, no
> `gh`, and no auth, so it is deterministic in any environment. CI on the consuming repo
> (ProjectProteus) has not been run, hence `verified-local` rather than `verified-ci`.

### Quick Reference

```bash
# The guard is a self-contained bash test with an embedded EXPECTED-STATE table.
# No `gh`, no network, no auth, no SKIP path -> deterministic in required CI.

declare -A EXPECT=(
  [#1]=' '            # OPEN  -> expect unchecked
  [#84]='x'           # CLOSED-> expect checked
  [PR-C]=' '          # bundle line: stays [ ] even if a child issue is CLOSED
  ["wave-3 docs sweep"]=' '   # phrase-keyed line (no leading #NNN)
)
# 1. derive ONE stable key per line (leading #NNN, else PR-X, else phrase)
# 2. diff actual checkbox char vs EXPECT[key]
# 3. SEEN-set cross-checks: __MISSING__ if a tracked line's key is not in EXPECT;
#    and fail if any EXPECT key was never SEEN (deleted/renamed line).
# See Detailed Steps for the full, runnable script.
```

### Detailed Steps

1. **Author an explicit EXPECTED-STATE table inside the test.** A bash
   `declare -A EXPECT=([key]=state ...)` maps each tracked line's stable key to its expected
   checkbox char (`' '` for OPEN/unchecked, `'x'` for CLOSED/checked). This is a committed fixture —
   a static-analysis assertion, not a live runtime query. (Direct application of
   `code-quality-enforcement-gates` §5: "assert the property via static analysis, NOT a live runtime
   check.") Because the table is authored to match the committed checkbox state, the file PASSES its
   own test deterministically — which removes the R0 disqualifier (the R0 committed artifact failed
   the test it shipped).

2. **Key each line by its STABLE PRIMARY TOKEN, not by scanning every `#NNN` on the line.** Derive
   exactly ONE key per line: the leading `#NNN` if present, else a `PR-X` token, else a short phrase.
   Look that single key up in `EXPECT`. A closed child inside an OPEN bundle line can never trip the
   guard, because the bundle line is keyed once (e.g. `PR-C`) and expected `[ ]`. This is the fix for
   the R0 bundle-line false-FAIL.

3. **Diff actual vs expected and collect violations.** For every line matching the checkbox regex,
   compare its actual char to `EXPECT[key]`; emit `::error::` and increment a counter on mismatch.

4. **Add bidirectional coverage cross-checks with a `SEEN` set.** (a) If a tracked-looking line's key
   is absent from `EXPECT`, fail with a `__MISSING__` sentinel — new lines cannot silently escape
   coverage. (b) After parsing, fail if any `EXPECT` key was never `SEEN` — catches a deleted or
   renamed line.

5. **Constrain the checkbox regex deliberately.** `^-\ \[([\ x])\]\ (.*)$` matches only `[ ]` / `[x]`
   (lowercase `x`, single space). A `[X]` or `[~]` is silently skipped as a non-checkbox — acceptable
   for a tracked file that uses the canonical form, but a sharp edge to record.

6. **Wire the guard into the repo's existing aggregate task** (e.g. justfile `check: lint validate`).
   Cite the target by its recipe NAME and grep for it — never hard-code a `justfile` line number, which
   drifts on any edit above it.

7. **(Future enhancement, NOT part of this guard) Add a SEPARATE non-required tokened nightly job** that
   diffs the EXPECT table against live `gh` issue state and opens an issue on drift. This is the
   belt-and-suspenders complement that restores freshness-detection without sacrificing the determinism
   of the required guard.

### v2.1.0 sub-pattern (UNVERIFIED design — ProjectProteus #186 re-plan)

> **Warning:** The following sub-pattern is from a re-planning session for ProjectProteus issue #186.
> The offline-fixture test shape below is a DESIGN — it was NOT implemented or CI-run this session. It is
> **unverified** until the PR lands and CI runs. The v2.0.0 core workflow above remains `verified-local`.

8. **Reconcile the guard against the repo's anti-silent-failure POLICY before choosing a design.** A
   live-`gh`-in-CI test that SKIPs (exit 0 + `::notice::`) when `gh` is unauthenticated is not merely a
   weak guard — in a repo with a `forbid-suppressions` job (`.github/workflows/_required.yml:53-105`) and
   a `docs/runbooks/no-silent-failures.md` runbook, it is a POLICY VIOLATION: a false-green no-op that
   the reviewer NOGO'd on P1/KISS + P7/POLA grounds. The policy is the REASON to go fully offline, not
   just a nicety. The CORRECT design is the committed-fixture invariant table above: deterministic, zero
   network, fails loudly.

9. **Mirror the PROPERTY of an existing repo test, not just its file location.** When you claim to
   "mirror" an existing test, mirror its core property. The repo's `tests/dispatch-apply.test.sh` is
   HERMETIC: it shims `curl`, uses a fake token, and hits no network. A live-`gh` test placed in the same
   `tests/` dir INVERTS that property (network-dependent, non-deterministic) — that is not mirroring, it
   is a regression. Mirror hermetic/deterministic; embed the `EXPECTED` map as a committed fixture.

10. **Ground-truth at AUTHORING time, not test time.** Build the `EXPECTED` map by running `gh issue view`
    on every referenced issue WHILE PLANNING (not in the test). For #186 this enumerated all 38 referenced
    issues and surfaced TWO stale entries (#92, #100) that the issue body never mentioned — exactly the
    drift a body-trusting plan would have missed. The committed map is a snapshot; the test reads no network.

11. **Mitigate snapshot staleness with a `# RE-VERIFY:` comment + the same-PR rule.** Annotate the fixture
    with `# RE-VERIFY: ran gh issue view <YYYY-MM-DD>` and enforce the rule "**the fixture and the doc change
    land in the SAME PR**". This bounds the window in which a reopened issue (e.g. a `[x]` issue that gets
    reopened) can desync the snapshot from reality.

12. **Tick Wave-3 / PR-GROUP lines only when EVERY issue on the line is CLOSED.** PR-group lines are
    group-scoped, not per-issue: a group box stays `[ ]` until ALL of its bundled issues are CLOSED. For
    #186 the groups with open children (#98 / #101 / #103) must stay unticked — ticking on the first child
    closing is a false-checked violation.

13. **PROVE the guard is not a no-op (runnable temp-tree proof).** A reviewer will (rightly) reject a
    verification step that merely SAYS "point the test at `$tmp`" without doing it. Actually copy the test
    into a throwaway tree so its `$0`-relative `REPO_ROOT` retargets, mutate a checkbox to introduce drift,
    run it, and ASSERT a nonzero exit:

    ```bash
    work="$(mktemp -d)"
    mkdir -p "$work/tests" "$work/docs/audit-2026-04-28"
    cp tests/check-remediation-checkboxes.sh "$work/tests/"      # $0-relative REPO_ROOT now points at $work
    cp docs/audit-2026-04-28/remediation-plan.md "$work/docs/audit-2026-04-28/"
    # Introduce drift: flip a known-CLOSED issue's box from [x] to [ ]
    sed -i 's/- \[x\] #84/- [ ] #84/' "$work/docs/audit-2026-04-28/remediation-plan.md"
    if ( cd "$work" && bash tests/check-remediation-checkboxes.sh ); then
      echo "PROOF FAILED: guard passed on drifted doc -> it is a no-op"; exit 1
    else
      echo "PROOF OK: guard exited nonzero on drift -> not a no-op"
    fi
    rm -rf "$work"
    ```

```bash
#!/usr/bin/env bash
# tests/check-remediation-checkboxes.sh — committed-fixture invariant table.
# Parses the tracking doc and diffs each line's checkbox char against EXPECT.
# No network, no gh, no auth, no SKIP path -> deterministic in every environment.
set -euo pipefail

DOC="${1:-docs/audit-2026-04-28/remediation-plan.md}"

# EXPECTED state table. Key -> expected checkbox char (' ' or 'x').
# HAND-MAINTAINED: when an issue closes, flip BOTH the doc checkbox AND its entry here.
declare -A EXPECT=(
  [#1]=' '       # OPEN
  [#84]='x'      # CLOSED
  [#85]='x'      # CLOSED
  [#112]='x'     # CLOSED (mis-grouped child; actually closed)
  [#183]=' '     # OPEN  (the tracking-doc fix itself)
  [PR-C]=' '     # bundle row: stays [ ] even though a child is CLOSED
  ["wave-3 docs sweep"]=' '
)

# Derive ONE stable key per line: leading #NNN, else PR-X, else a phrase.
key_for() {
  local text="$1"
  if [[ "$text" =~ ^(#[0-9]+) ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
  elif [[ "$text" =~ (PR-[A-Z]) ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
  else
    printf '%s' "$(printf '%s' "$text" | tr '[:upper:]' '[:lower:]' | awk '{print $1, $2, $3}')"
  fi
}

declare -A SEEN=()
violations=0

while IFS= read -r line; do
  # Match ONLY '- [ ]' / '- [x]' (lowercase x, single space). [X]/[~] are skipped.
  [[ "$line" =~ ^-\ \[([\ x])\]\ (.*)$ ]] || continue
  actual="${BASH_REMATCH[1]}"
  rest="${BASH_REMATCH[2]}"
  key="$(key_for "$rest")"
  SEEN["$key"]=1
  if [[ -z "${EXPECT[$key]+set}" ]]; then
    echo "::error::tracked line key '$key' is __MISSING__ from EXPECT table: $line"
    violations=$((violations + 1)); continue
  fi
  exp="${EXPECT[$key]}"
  if [[ "$actual" != "$exp" ]]; then
    echo "::error::key '$key' expected [${exp}] but doc has [${actual}]: $line"
    violations=$((violations + 1))
  fi
done < "$DOC"

# Bidirectional: every EXPECT key must have been SEEN (catches deleted/renamed line).
for k in "${!EXPECT[@]}"; do
  if [[ -z "${SEEN[$k]+set}" ]]; then
    echo "::error::EXPECT key '$k' was never SEEN in $DOC (deleted/renamed line?)"
    violations=$((violations + 1))
  fi
done

[[ "$violations" -eq 0 ]] || { echo "FAIL: $violations checkbox invariant violation(s)"; exit 1; }
echo "PASS: all tracked lines match the invariant table"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Live-`gh` regression guard (R0 primary; now DEMOTED) | Guard queried `gh issue view <n> --json state` at test time and SKIPed (exit 0 + `::notice::`) when `gh` was unavailable/unauthenticated | The required-CI runner has no issue-read token, so the guard SKIPs to a no-op in EXACTLY the environment CI runs in — ZERO protection and false confidence. It is also non-deterministic / network-dependent | Do not assert via a live runtime API call. Apply `code-quality-enforcement-gates` §5: assert the property via STATIC analysis (a committed EXPECT table diffed offline). No network, no auth, no SKIP path |
| Scan every `#NNN` on an unchecked line (R0 refinement) | Treated each issue number on a `- [ ]` line as "claimed open"; flagged any CLOSED `#NNN` on an unchecked line | Bundle lines (one PR row shipping several issues) legitimately stay `[ ]` while a child is already CLOSED — mis-fired on PR-C / PR-E batches | Derive ONE stable key per line (leading `#NNN`, else `PR-X`, else phrase) and look up that single key. A closed child inside an open bundle is never tested because the bundle is keyed once, as `[ ]`-expected |
| Snapshot which specific boxes are ticked | Test asserted literal `- [x]` positions / a fixed list of ticked items | Breaks on the next legitimate doc edit — false regression noise | Assert the invariant via the EXPECT table (key -> expected char), not a positional snapshot |
| Trust the triggering issue body's wave grouping / OPEN-CLOSED claims | Accepted #183's body buckets and CLOSED/OPEN annotations as authoritative | The body grouped #112 under the wrong wave; #112 was already CLOSED. Body annotations drift like the doc itself | Re-derive each box from ground truth; the issue body is a self-report. (`code-quality-enforcement-gates` §10) |
| Treat the invariant table as freshness against GitHub | Assumed a passing EXPECT-table test means the doc matches live issue state | The table is HAND-MAINTAINED: it enforces file-vs-table consistency, NOT file-vs-live-GitHub. If a human flips neither the checkbox nor the table entry when an issue closes, the test passes but the doc is stale | Be honest: this guard trades freshness-detection for determinism. Add a SEPARATE non-required tokened nightly job to diff the table against live `gh` and open an issue on drift (future enhancement, not part of this required guard) |
| Assume keys are always unique | Keyed each line by its leading token without checking for collisions | If two lines share a leading token (two `PR-C` rows, or one `#NNN` leading two lines) the SEEN/table mapping collapses — last write wins, coverage is lost silently | Verify keys are distinct for the target file (25 distinct keys here). It is a structural assumption; a duplicate-key pre-check would harden it |
| Cite the justfile wire-in point by line number | Referenced `justfile:73` / `:76` for the `check` recipe | Line numbers are read live but drift on any edit above them | Cite the recipe NAME (`check`) and grep for it; never hard-code a line number |
| Live-`gh issue view` in a REQUIRED CI test that skips on unauth (#186) | Required test ran `gh issue view <n>` and exited 0 (`::notice::`) when `gh` was unauthenticated | False-green no-op AND a policy violation: the repo's `forbid-suppressions` job (`_required.yml:53-105`) + `no-silent-failures` runbook ban skip-on-error; reviewer NOGO'd on P1/KISS + P7/POLA | Use an offline committed fixture asserted against the doc; verify GitHub state at AUTHORING time, not test time. Reconcile the design with the repo's anti-silent-failure policy BEFORE choosing it |
| Claimed to "mirror" the repo's existing test but inverted its core property (#186) | Said the new live-`gh` test "mirrors" `tests/dispatch-apply.test.sh` because both live in `tests/` | `dispatch-apply.test.sh` is HERMETIC (shims `curl`, fake token, no network); the live-`gh` test was network-dependent — the opposite property | Mirror the PROPERTY (hermetic/deterministic), not just the file location. Shim/embed; never reach the network in a required test |
| 41 network calls to verify a static doc fact (#186) | Designed the guard to make ~one `gh` call per checkbox at test time | Slow, rate-limit-prone, non-deterministic, and pointless: the fact being asserted is static and committed | A doc-vs-fixture string assertion needs ZERO network. Do the live lookups once at authoring time to build the fixture |
| Trusted the issue body's stale-entry list (#186) | Accepted #186's body as the complete list of stale checkboxes | The body omitted #92 and #100 — two stale entries it never mentioned | Enumerate EVERY checkbox and ground-truth each during planning; the body is a self-report, not an index |
| Treated Wave-3 PR-group lines as per-issue (#186) | Would tick a group box when any one bundled child closed | Groups with open children (#98 / #101 / #103) would be falsely checked | Tick a group line only when ALL of its issues are CLOSED — PR-group lines are group-scoped |
| Verification step that says "point the test at `$tmp`" without doing it (#186) | Wrote a verification step describing the temp-tree proof but never executed it | Unexecuted hand-wave; the reviewer flagged it as no evidence the guard isn't a no-op | Actually copy the test into `$work/tests/` so its `$0`-relative `REPO_ROOT` retargets the temp tree, introduce drift, run it, and assert a NONZERO exit |

## Results & Parameters

**Local test execution this session (the basis for `verified-local`):**

| Fixture | Scenario | Result |
|---------|----------|--------|
| matching | every line's char matches EXPECT (incl. open `PR-C` bundle with a closed child) | PASS, exit 0 |
| drift | `#84` is CLOSED (expect `[x]`) but doc has `[ ]` | FAIL — `key '#84' expected [x] but doc has [ ]` |
| new line | a `#999` line not present in EXPECT | FAIL — `__MISSING__` sentinel |
| deleted line | `#112` line removed from the doc | FAIL — EXPECT key `#112` never SEEN |

**Ground-truth facts captured (ProjectProteus):**

| Issue | Live state | Note |
|-------|------------|------|
| #183 | OPEN | The triggering follow-up issue (the tracking-doc fix) |
| #112 | CLOSED | Mis-grouped under the wrong wave by #183's body; caught by per-issue verification |
| #84  | CLOSED | dispatch host contract fixed |
| #85  | CLOSED | Trivy gate restored |

**Target doc:** `docs/audit-2026-04-28/remediation-plan.md` (ProjectProteus).
**Aggregate task to wire into:** justfile `check` recipe (cite by name, not line).

**The invariant the guard enforces (state it explicitly in the script header):**

```text
For every tracked line, derive ONE stable key K (leading #NNN, else PR-X, else phrase):
  EXPECT[K] must exist (else __MISSING__ violation), and
  actual_checkbox_char(line) == EXPECT[K]            (else drift violation)
And every K in EXPECT must be SEEN at least once     (else deleted/renamed violation)
This is file-vs-TABLE consistency, enforced statically and offline.
It is NOT freshness against live GitHub state (see Failed Attempts — add a separate
non-required tokened nightly drift job for that).
```

## Verified On

| Project | Context |
|---------|---------|
| ProjectProteus | issue #183 remediation-plan checkbox guard, R1 re-plan. Replaced the R0 live-`gh` guard (NOGO: offline-SKIP gave zero CI protection; committed artifact failed its own test) with a committed-fixture invariant table. Embedded test logic executed locally: PASS on a matching fixture, FAIL on drift / new-line / deleted-line fixtures as designed. Consuming-repo CI not run — `verified-local` |
| ProjectProteus | issue #186 re-plan (v2.1.0 sub-pattern). First plan NOGO'd for a live-`gh` skip-on-unauth required test (false-green no-op; violates `forbid-suppressions` (`_required.yml:53-105`) + `no-silent-failures` runbook; P1/P7). Re-plan: offline committed `EXPECTED` fixture mirroring the hermetic `tests/dispatch-apply.test.sh`, ground-truthed at authoring time (38 issues; surfaced stale #92/#100), `# RE-VERIFY:` same-PR rule, PR-group ticking only when all issues CLOSED, plus a runnable temp-tree not-a-no-op proof. **Unverified** — the offline test was a DESIGN, not implemented or CI-run this session |
