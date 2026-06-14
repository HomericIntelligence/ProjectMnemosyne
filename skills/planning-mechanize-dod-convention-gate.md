---
name: planning-mechanize-dod-convention-gate
description: "Plan-time pattern for mechanizing a convention-only Definition-of-Done item (e.g. a conventional-commit rule) by writing ONE pure-stdlib validator and wiring it into BOTH a local pre-commit hook AND an existing REQUIRED CI job. Use when: (1) planning to turn a documented-but-unenforced convention (commit-message format, naming rule, file-layout rule) into an automated gate, (2) deciding whether to add a new CI workflow vs extend a job that already fetches the data you need, (3) scoping a new gate so it does not retroactively fail on historical deviations, (4) you need a register of the assumptions a reviewer MUST scrutinize before implementing a conventional-commit / pre-commit / GraphQL-commit-message gate."
category: ci-cd
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-cd
  - planning
  - conventional-commits
  - pre-commit
  - definition-of-done
  - validation-gate
  - pr-policy
  - graphql
---

# Planning: Mechanize a Convention-Only Definition-of-Done Gate

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Produce a durable plan-time pattern for mechanizing a convention-only Definition-of-Done item — specifically, an automated conventional-commit gate (ProjectHephaestus issue #1209) — so that a human-enforced rule becomes machine-enforced. |
| **Outcome** | Plan produced; NOT executed. The validator script, its unit test, the pre-commit hook, and the CI step do not yet exist. No CI run confirms the approach. |
| **Verification** | unverified — this is a hypothesis until an implementation lands and CI confirms it. |

## When to Use

- You are PLANNING to convert a documented-but-unenforced convention (commit-message format, branch naming, file layout, header presence) into an automated gate.
- You are deciding whether to author a brand-new CI workflow or extend an existing required job that already fetches the relevant data (e.g. PR commits, changed files).
- You need to scope a new gate so a historical deviation already on `main` does not fail the gate retroactively.
- You are about to implement a conventional-commit / commit-msg / GraphQL-`commit.message` gate and want the list of assumptions a reviewer should challenge first.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. It is a *proposed* workflow (verification: unverified) — the validator section heading is "Verified Workflow" but the plan was never executed. Treat every step below as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Find a proven sibling script to mirror (standalone stdlib + unit-tested core + thin main()).
ls scripts/check_*.py
sed -n '1,40p' scripts/check_security_policy_no_hardcoded_date.py
sed -n '1,40p' tests/.../test_check_security_policy_no_hardcoded_date.py   # note the sys.path.insert(...,"scripts") import shim

# 2. Re-grep every line number you intend to cite — do NOT trust a plan's stale numbers.
grep -n "pr-policy\|commit\|signature" .github/workflows/*_required.yml
grep -n "Conventional" docs/DEFINITION_OF_DONE.md

# 3. Confirm the data the existing required job ALREADY fetches before adding a step to it.
grep -n "message\|oid\|signature" .github/workflows/*_required.yml   # is commit.message actually queried?

# 4. Before shipping, scan open PRs + recent history for the allowed-types list you assumed.
#    A wrong allowed-types list fails legitimate commits on day one.

# 5. commit-msg hooks need an explicit install — default `pre-commit install` does NOT wire them.
pre-commit install --hook-type commit-msg
# NOTE: `pre-commit run --all-files` does NOT exercise commit-msg-stage hooks. Use stdin + pytest.
```

### Detailed Steps

1. **One validator, two call sites.** Write a single pure-stdlib validator function. Wire it into:
   - a **local pre-commit hook** (catches the bad commit before push), AND
   - an **existing REQUIRED CI job** (catches it in CI).
   The CI half MUST live in a *required* job, not an advisory one. Project memory ("main-broken-by-nonrequired-precommit") records that advisory / non-required pre-commit checks let bad commits land on `main`.

2. **Extend an existing job, don't add a workflow.** If a required CI job already fetches the data you need (here, `pr-policy` already fetches every PR commit via GraphQL), add a new *step* there rather than authoring a new workflow file. Lower cost, keeps related policy co-located.

3. **Mirror a proven sibling verbatim.** Copy the shape of an existing, working script + test pair (here `scripts/check_security_policy_no_hardcoded_date.py` and its test): a standalone stdlib script, a unit-tested pure core function, a thin `main()`, and a test that imports via a `sys.path.insert(..., "scripts")` shim. Reusing a proven sibling shrinks the review surface.

4. **Scope the gate to NEW artifacts, not history.** A historical deviation (e.g. commit `67079cc3` `[FIX]...`) must NOT make the gate fail retroactively. Gate only new PR commits, and reuse the repo's existing `dependabot[bot]` exemption idiom rather than inventing a new one.

5. **Unit-test the conventional-commit parser edge cases:**
   - split on the FIRST colon only — `subject.split(":", 1)`;
   - extract scope via `index("(")` / `rindex(")")` so nested parens survive (`feat(core(sub)):`);
   - allow the trailing `!` breaking marker (`feat!:`, `feat(api)!:`);
   - ignore `Merge` / `Revert` / `fixup!` / `squash!` machinery commits;
   - reject the bracketed `[FIX]` form, unknown types, and empty description / scope / subject.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| GraphQL `commit.message` reuse | Plan assumes the GitHub GraphQL `Commit.message` field returns the full message, with subject = `message.split("\n")[0]`. | UNVERIFIED — the existing `pr-policy` query selects only `oid` and `signature`; `message` was never queried or tested. Field name or newline handling may differ. | Confirm the exact field is queryable and returns what you expect BEFORE building parsing on top of it. |
| `commit-msg` stage wiring | Plan assumes `stages: [commit-msg]` + `pass_filenames: true` passes the commit-message file path as the sole arg, and that `pre-commit install` wires the commit-msg hook type. | Default `pre-commit install` wires ONLY the pre-commit stage; commit-msg needs `pre-commit install --hook-type commit-msg`. The plan never added that install step — a real gap. | A commit-msg-stage hook is dead unless the install explicitly requests `--hook-type commit-msg`. Add that step. |
| `pre-commit run --all-files` as proof | Plan's verification step ran `pre-commit run --all-files` to "prove" the new hook works. | That command does NOT execute commit-msg-stage hooks, so it proves nothing about the new hook. Only the stdin/`-` path and pytest give real coverage. | Verify a commit-msg hook via stdin (`echo "msg" \| hook -`) and unit tests, never via `--all-files`. |
| Trusting cited line numbers | Plan cites `_required.yml:334/390/440` and `DEFINITION_OF_DONE.md:18`. | Concurrent merges shift line numbers; cited numbers go stale between plan and implementation. | The implementer must re-grep every anchor, not trust the plan's numbers. |
| Hardcoded allowed-types list | Assumed `feat\|fix\|docs\|refactor\|test\|chore\|ci\|build\|perf\|style\|revert`, inferred from CLAUDE.md + observed history. | Not from an authoritative repo config. If real history uses other types, the gate fails legitimate commits on day one. The plan said "verify zero current violations" but never actually scanned open PRs. | Derive the allowed-types list from an authoritative source and scan ALL open PRs + recent history before enabling the gate. |
| Nested-paren + breaking-marker combo | Parser uses `endswith((")", ")!"))` to detect scope-close, then strips the `!`. | The interaction between the nested-paren scope extraction and the `!`-strip is subtle and a likely bug source (e.g. `feat(core(sub))!:`). | Give the nested-paren + breaking-marker combination extra dedicated test cases; it is the most fragile branch. |

Every row above is an **unverified assumption made during planning**, recorded honestly so a reviewer scrutinizes it before implementation. "Why It Failed" describes the *risk*, since none of these were directly proven.

## Results & Parameters

**Pattern summary (copy-paste checklist for the implementer):**

```text
[ ] ONE pure-stdlib validator function; thin main(); unit-tested core.
[ ] Wired into a LOCAL pre-commit hook (stages: [commit-msg], pass_filenames: true).
[ ] Wired into an EXISTING REQUIRED CI job (pr-policy) as a new step — NOT a new workflow.
[ ] CI half is in a REQUIRED job (advisory checks let bad commits reach main).
[ ] Mirrors scripts/check_security_policy_no_hardcoded_date.py + its test (sys.path.insert shim).
[ ] Gates NEW PR commits only; reuses the dependabot[bot] exemption; no retroactive failures.
[ ] Added `pre-commit install --hook-type commit-msg` to setup docs (default install skips it).
[ ] Verified GraphQL commit.message is actually queryable + returns full message.
[ ] Re-grepped every cited line number (do not trust plan numbers).
[ ] Allowed-types list derived from authoritative config; scanned all open PRs for violations.
```

**Conventional-commit parser invariants to assert in tests:**

```text
"feat: x"            -> OK
"feat(api): x"       -> OK
"feat!: x"           -> OK (breaking marker)
"feat(api)!: x"      -> OK (scope + breaking)
"feat(core(sub)): x" -> OK (nested paren via index("(")/rindex(")"))
"[FIX] x"            -> REJECT (bracketed form)
"frobnicate: x"      -> REJECT (unknown type)
"feat: "             -> REJECT (empty description)
"feat(): x"          -> REJECT (empty scope)
"Merge branch ..."   -> IGNORE  (machinery)
"Revert ..."         -> IGNORE
"fixup! ..."         -> IGNORE
"squash! ..."        -> IGNORE
```

**Source context:** plan produced for ProjectHephaestus issue #1209 (mechanize the last convention-only Definition-of-Done item). Verification level `unverified` — script, test, hook, and CI step do not yet exist; no CI run confirms the approach.
