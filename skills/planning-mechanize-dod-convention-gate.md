---
name: planning-mechanize-dod-convention-gate
description: "Planning a mechanized Definition-of-Done / convention gate (e.g. a commit-message convention check) enforced at BOTH a local pre-commit stage and a REQUIRED CI job. Use when: (1) planning a hook + CI gate that enforces a project convention on new artifacts; (2) a plan rests on an external API field, a hook-installation mechanism, or an inferred allow-list and a reviewer NOGO'd it as unverified; (3) you must convert plan-time assumptions into verified evidence to move a plan from NOGO to GO; (4) adding a commit-msg-stage pre-commit hook and wondering why it never fires; (5) extending an existing GitHub GraphQL block to read commit.message; (6) deciding whether an allow-list (conventional-commit types) is safe to hard-fail."
category: ci-cd
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: [planning, definition-of-done, convention-gate, pre-commit, commit-msg-hook, conventional-commits, graphql, required-ci-job, plan-verification, nogo-to-go, load-bearing-assumption]
---

# Planning a Mechanized Definition-of-Done / Convention Gate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Plan a mechanized convention gate (commit-message convention) enforced locally (pre-commit `commit-msg` stage) AND in a REQUIRED CI job, for ProjectHephaestus issue #1209 |
| **Outcome** | A v1.0.0 plan was NOGO'd as `unverified` (load-bearing assumptions not directly checked). Re-plan verified each assumption against the live repo + live GitHub GraphQL API and folded the evidence in → GO. verified-local. |
| **Scope** | Plan-time verification of load-bearing assumptions; pre-commit commit-msg install mechanics; GraphQL commit.message availability; allow-list-vs-real-history scan |

## When to Use

- You are planning a hook + CI gate that enforces a project convention (commit-message format, file-naming, header presence) on NEW artifacts, not the whole history.
- A reviewer NOGO'd your plan because it rests on an unverified external API field, hook-installation mechanism, or inferred allow-list — even though the design itself is sound.
- You need to convert plan-time assumptions into directly-verified evidence to move a plan from NOGO to GO.
- You are adding a `commit-msg`-stage pre-commit hook and it never seems to run.
- You are extending an existing GitHub GraphQL query block to add `commit.message` and want to confirm it is actually returned.
- You are about to hard-fail on an allow-list (e.g. conventional-commit types) and need to know whether real history already conforms.

## Verified Workflow

**Verified locally only — CI validation of the implementation PR is pending.** The verification commands below were RUN against the live ProjectHephaestus repo and the live GitHub GraphQL API; the eventual implementation PR has NOT yet run through full CI. So: `verified-local`, not `verified-ci`.

### The headline meta-lesson

When a plan asserts a design that rests on **an external API field, a hook-installation mechanism, or an inferred allow-list**, a reviewer will (correctly) NOGO it until those are DIRECTLY verified — even when the design is sound. The fix on re-plan is NOT to change the design. It is to RUN the cheap verification for each assumption and fold the evidence into the plan. **Plan-time verification of load-bearing assumptions is what converts a NOGO to GO.** Each verification below costs seconds to minutes; skipping it costs a whole review round-trip.

### Quick Reference

```bash
# 1. commit-msg-stage hooks are INERT without default_install_hook_types.
#    Confirm whether the wiring exists; if absent, add it (cheaper than editing 3 doc files).
grep -n "default_install_hook_types" .pre-commit-config.yaml || echo "ABSENT — add it"
# Then add at top level of .pre-commit-config.yaml:
#   default_install_hook_types: [pre-commit, commit-msg]
# so the already-documented `pre-commit install` wires BOTH stages.

# 2. pre-commit run --all-files does NOT exercise commit-msg-stage hooks.
#    Verify the hook through its REAL stage:
pre-commit run <hook-id> --hook-stage commit-msg --commit-msg-filename /tmp/msg.txt

# 3. Confirm GraphQL commit.message is actually returned — run it against a REAL PR.
gh api graphql -f query='
  query($owner:String!,$name:String!,$num:Int!){
    repository(owner:$owner,name:$name){
      pullRequest(number:$num){
        commits(first:100){nodes{commit{message}}}
      }
    }
  }' -F owner=mvillmow -F name=ProjectHephaestus -F num=1233 \
  --jq '.data.repository.pullRequest.commits.nodes[].commit.message | split("\n")[0]'

# 4. An allow-list inferred from docs is NOT evidence. SCAN real history.
git log origin/main -n 60 --format='%s' | \
  grep -vE '^(feat|fix|docs|refactor|test|chore|ci|build|perf|style|revert)(\(.+\))?!?: ' || \
  echo "zero violations in recent history"
```

### Plan architecture (the design that survived review)

Keep these patterns — they were not the reason for the NOGO:

- **One validator, two call sites.** A single pure `is_valid_subject(subject) -> (bool, reason)` function. The pre-commit hook calls it on the staged commit message; the CI job calls it on each new commit's subject. No duplicated rule logic.
- **Extend an existing REQUIRED CI job, do not add a new workflow.** Adding a new workflow risks a non-required job that silently never blocks. Per the *main-broken-by-nonrequired-precommit* incident, the CI half of the gate MUST be a REQUIRED job, folded into the existing required lint/check job rather than a standalone advisory step.
- **Mirror a proven sibling script.** Model the new validator and its CI invocation on an existing, already-passing convention-check in the repo rather than inventing a new shape.
- **Scope the gate to NEW artifacts, not history.** Validate only the commits introduced by the PR (or the staged message locally) — never re-validate the full `main` history, which contains a known historical deviation.
- **Empty-set passes.** Both halves must treat an empty/malformed fetch as PASS, not hard-fail, so a transient API hiccup can't block every PR.

### The five load-bearing verifications (each was a prior RISK, now resolved)

1. **commit-msg-stage hooks are inert without `default_install_hook_types`.** A hook declared `stages: [commit-msg]` does nothing under a plain `pre-commit install`, which wires only the pre-commit stage. Verified absent via `grep default_install_hook_types .pre-commit-config.yaml` → NONE. **Fix:** add top-level `default_install_hook_types: [pre-commit, commit-msg]` so the already-documented `pre-commit install` wires both stages — cheaper than editing install docs in three files (CONTRIBUTING / CLAUDE / README).

2. **`pre-commit run --all-files` does NOT exercise commit-msg-stage hooks.** Using it as the "local gate works" proof is a verification gap a reviewer catches as a silent-failure (POLA) blocker. **Fix:** verify the hook through its real stage: `pre-commit run <hook-id> --hook-stage commit-msg --commit-msg-filename <file>`.

3. **GraphQL `commit.message` availability confirmed by a live query, not assumed.** Verified by running the actual augmented query against a real PR (#1233): `.commit.message | split("\n")[0]` yields the subject line. **Lesson:** when extending an existing GraphQL block to add a field, run the augmented query against one real object before trusting it; add an empty-set-passes fallback so a malformed/empty fetch can't hard-fail the gate.

4. **An inferred allow-list is not evidence — SCAN real history.** "Verify zero current violations before adding a hard-fail gate" must be an EXECUTED command, not a claim. Running the `ALLOWED_TYPES` scan over the last 60 `origin/main` subjects found exactly 1 violation — the already-known historical deviation — confirming recent practice conforms and the gate won't break legitimate work on day one.

5. **Test names must match what they exercise.** A test called `..._multiple_colons` that uses a single-colon input is a TDD gap the reviewer will flag. Use the genuine edge-case input the advise findings named: `fix: url: handle https://...`.

### Implementer handoff note

Stale line numbers in a plan are a known liability. Cite them for orientation, but instruct the implementer to **re-grep before editing**, since concurrent merges shift them between plan-time and implement-time.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Ship a sound design with its load-bearing assumptions only described, not verified | v1.0.0 plan asserted the commit-msg hook, the GraphQL `commit.message` field, and a conventional-commit allow-list as facts | Reviewer NOGO'd as `unverified` — a sound design resting on unchecked external-API / hook-install / allow-list assumptions is not a GO | Plan-time verification of load-bearing assumptions is what converts NOGO→GO. Don't change the design; RUN the cheap verification per assumption and fold the evidence into the plan. |
| Rely on `pre-commit install` to wire the commit-msg hook | Declared the hook with `stages: [commit-msg]` and assumed the documented `pre-commit install` would activate it | A plain `pre-commit install` wires only the pre-commit stage; commit-msg-stage hooks are INERT without `default_install_hook_types`. Verified absent via grep → NONE | Add top-level `default_install_hook_types: [pre-commit, commit-msg]` to `.pre-commit-config.yaml` — cheaper than editing install docs in 3 files |
| Prove the local gate with `pre-commit run --all-files` | Planned to demonstrate the hook works by running `pre-commit run --all-files` | `--all-files` does NOT exercise commit-msg-stage hooks — a silent-failure (POLA) gap the reviewer flags | Verify the hook through its real stage: `pre-commit run <hook-id> --hook-stage commit-msg --commit-msg-filename <file>` |
| Assume GraphQL returns `commit.message` | Extended the existing GraphQL commits block to read `commit.message` without running it | An added field on an existing query is unverified until a real object proves it; an empty/malformed fetch could hard-fail every PR | Run the augmented query against one real PR (#1233 → `.commit.message \| split("\n")[0]` = subject) and add an empty-set-passes fallback |
| Infer the allowed commit types from docs and hard-fail on them | Built the `ALLOWED_TYPES` allow-list from CONTRIBUTING prose and planned a hard-fail gate | A docs-inferred allow-list is not evidence that real history conforms; a day-one hard-fail could break legitimate work | SCAN real history: the `ALLOWED_TYPES` scan over the last 60 origin/main subjects found exactly 1 violation (the known historical deviation) — recent practice conforms |
| Name a test for the behavior it doesn't exercise | Wrote `test_..._multiple_colons` using a single-colon input | Reviewer flags it as a TDD gap — the name claims an edge case the input doesn't hit | Use the genuine edge-case input the advise findings named: `fix: url: handle https://...` |
| Hardcode the plan's grep line numbers as edit targets | Cited exact line numbers in the plan and pointed the implementer straight at them | Concurrent merges shift line numbers between plan-time and implement-time | Cite line numbers for orientation but instruct the implementer to re-grep before editing |
| Plan a standalone advisory CI workflow for the convention check | Considered a new, separate workflow for the CI half of the gate | A non-required job silently never blocks (the main-broken-by-nonrequired-precommit incident) | The CI half MUST be a REQUIRED job — fold it into the existing required lint/check job, not a new advisory workflow |

## Results & Parameters

### Verification checklist before declaring a convention-gate plan GO

```yaml
load_bearing_assumptions_verified:
  hook_install_mechanism:
    - grep_default_install_hook_types: executed   # not assumed
    - hook_tested_via_real_stage: true            # --hook-stage commit-msg
  external_api_field:
    - graphql_field_run_against_real_object: true # PR #1233
    - empty_set_passes_fallback: true
  inferred_allow_list:
    - scanned_real_history: true                  # last 60 origin/main subjects
    - current_violation_count_known: true         # = 1 (historical deviation)
  tdd:
    - test_names_match_inputs: true
  ci_half:
    - is_a_required_job: true                     # not advisory/non-required
```

### Design invariants to preserve

| Invariant | Why |
| ----------- | ----- |
| One validator, two call sites | DRY — local hook + CI job share `is_valid_subject` |
| Extend existing REQUIRED CI job | Non-required jobs never block (main-broken-by-nonrequired-precommit) |
| Mirror a proven sibling script | Reuse a passing shape rather than invent one |
| Scope gate to NEW artifacts | History contains a known deviation; don't re-validate it |
| Empty-set passes | Transient/malformed fetch must not hard-fail every PR |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1209 re-plan, 2026-06-12 | NOGO→GO after directly verifying commit-msg install mechanics, GraphQL `commit.message` (PR #1233), and allow-list-vs-real-history (1 violation in last 60 subjects) |

## References

- ProjectHephaestus issue #1209 (mechanized DoD / convention gate)
- Related learning: main-broken-by-nonrequired-precommit-and-strict-false (the CI half must be a REQUIRED job)
