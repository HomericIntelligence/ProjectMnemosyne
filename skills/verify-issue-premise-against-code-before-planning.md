---
name: verify-issue-premise-against-code-before-planning
description: "An issue body that asserts 'the current code does X' is a CLAIM, not ground truth — before writing a plan, grep the repo for the distinctive tokens in the issue's premise and confirm WHICH file/job actually matches, and ENUMERATE EVERY site that matches before scoping. Issues drift from code; follow-up issues especially describe a since-changed state, and CI/workflow issues are dangerous because the same step pattern appears in several workflow files AND in several jobs of one file. In ProjectAgamemnon #248 the premise said the repo used `setup-pixi` with `cache: false` skipping built-in save; grepping `cache: false` (the issue's OWN premise token) showed the scenario lived in TWO jobs of `_required.yml` (`lint` AND `pixi-check`), plus a look-alike `security-dependency-scan` with a DIFFERENT defect. A first plan that grepped the INCIDENTAL token `pixi install --locked` (which the issue never named) matched only `pixi-check`, silently dropped `lint`, and earned a NOGO. Use when: (1) planning any issue whose description asserts current code structure/config, (2) the issue is a follow-up to a prior issue, (3) CI/workflow issues where similar steps appear in multiple workflow files OR multiple jobs, (4) the premise tokens may have already been fixed, (5) the issue fixes a recurring code pattern likely present in more than one place — especially after a single-site plan or when a sibling/look-alike site exists."
category: documentation
date: 2026-06-19
version: "1.1.0"
history: verify-issue-premise-against-code-before-planning.history
user-invocable: false
verification: unverified
tags:
  - planning
  - issue-premise
  - verify-before-planning
  - stale-issue
  - follow-up-issue
  - ci-cd
  - github-actions
  - grep-the-premise
  - wrong-file
  - workflow-disambiguation
  - pixi
  - actions-cache
  - enumerate-all-sites
  - ratify-scope
  - under-scoping
  - self-fulfilling-narrowing
  - multi-site
---

# Verify the Issue Premise Against the Code Before Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture a durable planning-discipline lesson: an issue's description of "what the current code does" is a CLAIM to verify against the actual files, not ground truth to plan on — grep the distinctive premise tokens to confirm WHICH file/job actually matches, AND enumerate EVERY site that matches the premise before scoping, ratifying in-scope and excluded sites explicitly |
| **Outcome** | Plan written for ProjectAgamemnon #248 ("Add pixi.lock restore-only cache fallback on miss"). **(v1.0.0)** The premise implied `python-client.yml`, but those jobs use the full `actions/cache@v4` (auto-saves) — grepping the premise tokens disambiguated `_required.yml`. **(v1.1.0)** The FIRST revision of that plan fixed only ONE job (`pixi-check`) and got a NOGO: grepping the incidental token `pixi install --locked` (which the issue never named) silently dropped a SECOND matching job, `lint`. Grepping the issue's OWN premise token `cache: false` enumerated BOTH `lint` + `pixi-check` as in-scope and surfaced a look-alike `security-dependency-scan` (different defect) to ratify as out-of-scope |
| **Verification** | unverified — PLANNING session only; neither the disambiguation plan nor the enumerate-and-ratify revision was implemented or run through CI, and the proposed `actions/cache/restore@v5` + `actions/cache/save@v5` split was not executed end-to-end |

This is a planning-DISCIPLINE learning, distinct from the cache-mechanics skill
`pixi-cache-true-unreliable`. The lesson is not "how cache syntax works" — it is "do not
trust the issue's narration of the current code; grep the premise's distinctive tokens and
plan against the file that actually matches."

**v1.1.0 extends the same theme from disambiguation to exhaustive enumeration.** v1.0.0
answers "WHICH single file does this premise point to?". v1.1.0 answers "ALL N sites this
premise matches — fix every in-scope one and ratify every excluded look-alike." The two
failure modes are different: wrong-file (disambiguate) vs under-scoping / silently-dropped
sibling (enumerate-and-ratify). Both share one root: grep the issue's OWN premise token, not
an incidental token from your first-found site.

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until
> CI confirms.

## When to Use

- Planning any issue whose description ASSERTS the current code's structure or configuration
  ("the workflow uses `cache: false`", "the job re-downloads X", "we currently call Y").
- The issue is a FOLLOW-UP to a prior issue/PR (e.g. #248 was a follow-up from #62) — the
  earlier state it narrates may have since changed.
- CI / GitHub-Actions / workflow issues, where the SAME step pattern (a cache step, a setup
  step, an install step) appears in MULTIPLE workflow files and the issue names none of them
  exactly — or names the wrong one.
- You are about to start editing the first file whose name "sounds like" the issue's subject,
  without confirming the described tokens actually live there.
- The premise's distinctive tokens may have ALREADY been fixed — in which case the right plan
  is "state it's already addressed," not a no-op change.
- **(v1.1.0)** Planning any issue that fixes a RECURRING code pattern — a CI workflow step
  repeated across jobs, a lint rule, a config key — where the same pattern likely appears in
  more than ONE place. Especially after you have already written a SINGLE-site plan, and
  especially when a sibling or look-alike site exists in the same file/dir. The choice of which
  sites to fix is a scope DECISION the reviewer must ratify; enumerate them all first.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. It was produced in a PLANNING
> session only; no code was written or run, and CI never executed. The section is titled
> "Verified Workflow" only to satisfy the marketplace validator (which requires that exact
> heading). Treat every step below as a **Proposed Workflow / hypothesis** until CI and a human
> planner confirm it.

### Quick Reference

```bash
# 1. EXTRACT the distinctive string tokens from the issue's PREMISE (not its title).
#    For #248: "cache: false", "pixi install --locked", the exact cache key string.

# 2. GREP those tokens across the relevant dir — let the code, not the prose, name the file.
grep -rn 'cache: false' .github/workflows/
grep -rn 'pixi install --locked' .github/workflows/
#    The INTERSECTION is the disambiguator:
grep -rln 'pixi install --locked' .github/workflows/ \
  | xargs grep -l 'cache: false'
#    -> .github/workflows/_required.yml   (job: pixi-check)  == the REAL target
#    NOT python-client.yml, whose jobs use the full actions/cache@v4 (auto-saves).

# 3. If the match lands in a DIFFERENT file than the issue names, plan against the MATCH and
#    call out the discrepancy in the plan's Approach, citing the grep as evidence.

# 4. If the premise tokens DON'T match anywhere, the premise may be ALREADY-FIXED.
#    State that explicitly in the plan instead of implementing a no-op.

# 5. (v1.1.0) ENUMERATE ALL SITES, then RATIFY scope. Grep the issue's OWN premise token —
#    NOT an incidental token from the first site you found.
grep -rn 'cache: false' .github/workflows/_required.yml   # the issue's premise token
#    -> matches TWO jobs: `lint` (lines 72-89) AND `pixi-check` (lines 153-170). Both in-scope.
#    A first plan grepped `pixi install --locked` (incidental, never named by the issue) and
#    matched ONLY pixi-check -> silently dropped `lint` -> NOGO.

#    For each match, CLASSIFY:
#      in-scope    = matches the issue's EXACT defect (cache:false skips built-in save)
#      look-alike  = matches the token but has a DIFFERENT defect, e.g.
#                    security-dependency-scan: built-in setup-pixi caching is ON (no `cache:`
#                    key) -> a separate broken-cache:true problem, OUT of scope for #248.

#    In the PLAN, list EVERY in-scope site to fix AND EVERY excluded look-alike with reasons.
#    A silent omission reads as an oversight (NOGO); an explicit ratified deferral does not.

#    WATCH per-site DIVERGENCE before templating one fix across sites:
#      lint  uses cache key `pixi-lint-*` and path clients/python/.pixi
#      pixi-check uses cache key `pixi-*` and a different path
#    A uniform save would write under a key the restore never looks up -> silent cache miss.
```

### Detailed Steps

1. **Treat the issue body's "the current code does X" as a CLAIM, not ground truth.** An
   issue — especially a follow-up — narrates a snapshot of the code that may be stale or simply
   wrong about which file is involved. #248's premise asserted `setup-pixi` with `cache: false`
   skipping the built-in save and "fully re-downloads .pixi on cold cache." That description
   matched a job, but NOT the one the wording implied.

2. **Extract the distinctive tokens from the premise.** Pull the literal strings that pin down
   the scenario: here `cache: false`, `pixi install --locked`, and the exact cache key. These
   are the search surface — not the issue's title or your guess at the file.

3. **Grep those tokens across the relevant directory and take the INTERSECTION.** `grep -rn`
   each token over `.github/workflows/`. Individually each token appears in several files; the
   FILE THAT CONTAINS ALL OF THEM is the real target. For #248 the `cache: false` +
   `pixi install --locked` intersection resolved to exactly one place: `_required.yml` job
   `pixi-check`. The `python-client.yml` jobs matched `pixi install` but used the full
   `actions/cache@v4` action (which auto-saves) — i.e. they are NOT the issue's scenario.

4. **When the match is in a different file than the issue names, plan against the match and
   document the discrepancy.** Do not silently re-target; in the plan's Approach state "the
   issue's wording implies X, but grepping the premise tokens shows the described scenario lives
   in Y (job Z)," and include the grep as evidence so a reviewer can verify the redirection.

5. **If the premise tokens match NOWHERE, suspect an already-fixed premise.** A follow-up issue
   may describe a state a prior PR already changed. In that case the correct plan is to state
   "the described condition no longer exists (grep evidence)" rather than implementing a change
   that is a no-op or, worse, re-introduces removed behavior.

6. **Flag SHA-pin-by-analogy and other unverified externals as reviewer risks.** When the plan
   pins sub-actions (`actions/cache/restore`, `actions/cache/save`) to the parent action's SHA
   by analogy, say so explicitly and mark it unverified — do not present an assumed ref
   resolution as confirmed.

7. **(v1.1.0) Enumerate EVERY site matching the premise BEFORE scoping — grep the issue's OWN
   premise token, not an incidental one.** The defining token is the one the ISSUE states
   (`cache: false`). A distinctive token that merely happens to appear at your first-found site
   (`pixi install --locked`) is a SELF-FULFILLING filter: it matches only that site and silently
   excludes valid siblings. `grep -rn` the premise token across the relevant scope (whole file /
   dir / repo) to list ALL candidate sites. In #248 the premise token `cache: false` matched TWO
   jobs (`lint` and `pixi-check`) in the SAME file; the incidental-token grep matched only one,
   dropped `lint`, and earned a NOGO.

8. **(v1.1.0) Classify each candidate in-scope vs look-alike, and RATIFY the scope explicitly.**
   For each match, decide: does it have the issue's EXACT defect (in-scope), or does it merely
   share the token while having a DIFFERENT defect (look-alike, out of scope)? In #248
   `security-dependency-scan` matched the area but had the built-in setup-pixi cache ON (no
   `cache:` key) — a separate broken-`cache:true` problem, not #248's "`cache:false` skips save."
   In the plan, list every in-scope site to fix AND every excluded look-alike WITH the reason
   ("excluded because it has defect Y, not the issue's defect X"). Which sites to fix is a
   DECISION the reviewer must ratify; a silent omission of a matching site reads as an oversight
   (NOGO), an explicit ratified deferral does not.

9. **(v1.1.0) Check per-site DIVERGENCE before applying a templated fix.** Sites matching the
   same premise can still differ in their details. In #248 the two jobs used DIFFERENT cache keys
   (`pixi-lint-*` vs `pixi-*`) and different paths. A uniform fix copied from one job would write
   the save under a key the other job's restore never looks up — a silent save-under-wrong-key
   cache miss. Inspect each in-scope site's specifics and fit the fix to each, rather than
   templating one site's parameters across all.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Took the issue's "`cache: false` skips save" premise at face value | Assumed it referred to `python-client.yml` | Those jobs use the full `actions/cache@v4`, which auto-saves — not the issue's scenario | Grep the premise tokens; don't assume the first pixi workflow is the target |
| Assumed `actions/cache/restore` + `/save` share the parent action's pinned SHA | Pinned both sub-actions to `27d5ce7...# v5.0.5` without independently verifying the sub-action paths resolve at that commit | Unverified — sub-action path resolution at a pinned SHA was assumed, not checked against the GitHub Actions API/marketplace | Flag SHA-pin-by-analogy assumptions as a reviewer risk; verify the ref resolves before relying on it |
| **(v1.1.0)** Scoped the fix by grepping `pixi install --locked` | Assumed that token defined the issue's target job | It's incidental to ONE job; the issue's real premise token is `cache: false`, which also matched the `lint` job — silently dropped → NOGO | Grep the issue's OWN premise token, not a distinctive token from your first-found site |
| **(v1.1.0)** Fixed only the first matching job and didn't mention the others | Treated single-site as obviously-complete | Reviewer reads a dropped matching sibling as an oversight; ambiguous scope must be surfaced, not silently resolved | Enumerate all sites; ratify which are in/out of scope with reasons |
| **(v1.1.0)** Considered treating all pixi-cache jobs uniformly | Would have copied one job's cache key to all | `lint` and `pixi-check` use DIFFERENT keys (`pixi-lint-*` vs `pixi-*`) and paths; a uniform save would write under a key the restore never looks up | Check per-site divergence before applying a templated fix |

## Results & Parameters

### The disambiguating grep (the core of this skill)

```bash
# Each token alone is ambiguous across workflow files; the INTERSECTION is the answer.
grep -rln 'pixi install --locked' .github/workflows/ | xargs grep -l 'cache: false'
# -> .github/workflows/_required.yml  (job: pixi-check)
#    python-client.yml is EXCLUDED: its jobs use the full actions/cache@v4 (auto-save),
#    which is NOT the "cache: false skips save" scenario the issue describes.
```

### Uncertain assumptions / unverified externals from THIS plan (for the reviewer)

- **UNVERIFIED:** `actions/cache/restore@<SHA>` and `actions/cache/save@<SHA>` resolve at commit
  `27d5ce7f107fe9357f9df03efb73ab90386fccae` (v5.0.5) — assumed because they are sub-actions of
  `actions/cache` at the same tag; NOT confirmed against the registry.
- **UNVERIFIED:** that `actions/cache/save` rejects/ignores `restore-keys` (the plan omits it) —
  standard for the save sub-action but not re-checked against current docs.
- **ASSUMPTION:** the `&&` compound `if:` expression
  (`steps.detect.outputs.skip == 'false' && steps.pixi-cache.outputs.cache-hit != 'true'`) is
  valid GitHub Actions expression syntax — true, but worth a YAML+expression lint.
- **ASSUMPTION:** line numbers `_required.yml:128-170` are current as of the plan; they are a
  snapshot and may drift.
- **SCOPE DECISION:** `python-client.yml` jobs deliberately left out of scope (they auto-save via
  the full action). Reviewer should confirm that exclusion is intended for #248.

### (v1.1.0) Enumerate-and-ratify residuals from the REVISED plan (for the reviewer)

The revised plan grepped the issue's own premise token `cache: false` and enumerated TWO in-scope
jobs (`lint`, `pixi-check`) plus one ratified exclusion. The residual uncertainties:

- **ASSUMPTION:** `lint` and `pixi-check` are the COMPLETE set of in-scope sites, and
  `security-dependency-scan` is the only look-alike. Based on grepping `cache: false` + reading the
  one workflow file `_required.yml`; OTHER workflow files (e.g. `python-client.yml`) were judged out
  of scope (they use the full `actions/cache@v4` action, which auto-saves) — reviewer should confirm
  that whole-repo judgment.
- **UNVERIFIED:** `actions/cache/save@v4` (tag-pinned, used in the `lint` job) behaves like the
  v5.0.5 SHA-pinned save sub-action re: no `restore-keys` input — assumed by analogy across major
  versions, not checked against v4 docs.
- **ASSUMPTION:** the `lint` save placed after `pixi run typecheck` captures a fully-materialised
  `clients/python/.pixi` (typecheck triggers the install). If `setup-pixi` with `cache:false` does
  NOT install the env (only `pixi run` does), the env is present by save time — but the exact
  materialisation point was reasoned, not traced.
- **ASSUMPTION:** line numbers (`_required.yml:72-89`, `:153-170`, `:381-395`) are a snapshot and may
  drift.
- **SCOPE DECISION needing ratification:** `security-dependency-scan` deferred as a separate
  follow-up (different defect: built-in setup-pixi caching active, no `cache:` key). Confirm that
  deferral is intended for #248.

### Related skills

- `pixi-cache-true-unreliable` — the cache-MECHANICS skill (when `cache: true` / built-in save is
  unreliable). THIS skill is the planning-discipline complement: verify which file/job the issue
  actually describes before applying any cache fix.
- `planning-follow-up-issue-line-number-drift` — verify cited line numbers against current HEAD;
  complementary "the follow-up issue's coordinates may have drifted" discipline.
- `planning-verify-issue-premise-before-implementing` — verify an issue-named ARTIFACT exists
  (repo-wide, across branches) before concluding it was never built. THIS skill instead
  disambiguates WHICH same-repo file/job a premise's tokens actually match.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Issue #248 ("Add pixi.lock restore-only cache fallback on miss") — a follow-up from #62 | unverified — planning session only. The premise implied `python-client.yml`, but grepping `cache: false` + `pixi install --locked` resolved the described scenario to `_required.yml` job `pixi-check`. Plan proposes splitting that job's single restore-only `actions/cache@v5` into `actions/cache/restore@v5` + a guarded `actions/cache/save@v5` after `pixi install --locked`. Not implemented or CI-run. |
