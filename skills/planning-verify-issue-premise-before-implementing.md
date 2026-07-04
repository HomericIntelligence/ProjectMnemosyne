---
name: planning-verify-issue-premise-before-implementing
description: "Verify issue and plan premises against authoritative sources before acting. Use this when an issue, PR plan, review, CI fix, or enforcement change assumes an artifact exists, prior work merged, a live service still needs work, a full population was checked, a CI job gates, an implementation returns a shape, or an integration point exists. Convert the premise into deterministic checks before implementing, closing, gating, or declaring work complete."
category: architecture
date: 2026-06-20
version: "3.0.0"
user-invocable: false
verification: unverified
history: planning-verify-issue-premise-before-implementing.history
tags: [planning, issue-premise, verify-before-implementing, premise-verification, assumption-verification, authoritative-source, full-population-check, live-state-check, merge-state, prerequisite-verification, unmerged-branch, self-contained-pr, enforcement-gate, integration-point, ci-gate, ruleset, implementation-shape, route-shape, deterministic-gate, no-op-forbidden, issue-claims, follow-up-issue]
---

# Planning: Verify Premises Before Acting

## Overview

Plans fail when they treat issue text, a previous plan, a branch-local grep, or a stale config as the source of truth. Before implementing, closing, gating, or declaring an issue done, identify the premise the plan depends on and verify it against the authority that can actually prove it.

This skill consolidates the planning-verify family into one generic workflow. It preserves the issue-specific examples in history and keeps the durable rule here: every consequential claim becomes a deterministic check before it drives scope, disposition, tests, or merge readiness.

| Field | Value |
|-------|-------|
| Date | 2026-07-04 |
| Objective | Merge similar planning-verification memories into a generic rule with concrete issue examples retained. |
| Version | 3.0.0, major bump because this replaces seven standalone memories with a broader canonical recommendation. |
| Verification | unverified for this consolidation; source examples are preserved verbatim in history. |

## When to Use

- An issue or plan names a script, file, branch, PR, route, workflow, ruleset, dashboard, helper, API response, or config as if it already exists.
- A follow-up issue assumes prior work merged, was tested, or is available on `main`.
- A review or issue claims that a fix is mechanical, blocked, already complete, or safe to close.
- A gate, guard, rule, CI job, or enforcement path is being added and the plan assumes the integration point already exists.
- A plan samples only named entities but the requirement applies to a whole population.
- A test assertion depends on an implementation return shape that has not been read from source.
- A live external state, such as GitHub rulesets or CI status, may differ from repository files.
- The next step would be a no-op, defer, close, or human-ratified judgment instead of a runnable proof.

## Verified Workflow

> This is a planning discipline, not proof that every listed command is valid for every repository. Select the authority that applies to the premise and record the exact check result before acting.

### Quick Reference

```bash
# Prior PR/work claimed to have landed.
gh pr view 173 --json state,mergedAt,headRefName
git merge-base --is-ancestor <commit-or-branch> origin/main

# Artifact claimed to exist on the branch where new work will run.
git ls-files <path-or-pattern>
git show origin/main:<path>
rg '<symbol-or-route>' <candidate-paths>

# CI/ruleset claimed to gate, not merely run.
gh api repos/<org>/<repo>/rulesets --jq '.[] | {name, enforcement, conditions, rules}'

# Population claimed complete.
gh repo list "$ORG" --limit 200 --json name --jq '.[].name'
git ls-files | rg '<population-pattern>'
```

1. Name the premise before choosing a fix. Common premise classes are: artifact exists, prior PR merged, branch contains a helper, live work remains, all entities were checked, CI job gates, implementation returns a shape, or an enforcement integration point exists.
2. Pick the authoritative source. Use `origin/main` or `HEAD` for branch-local artifacts, GitHub PR metadata for merge state, live APIs for rulesets and repository population, workflow/ruleset definitions for gates, and source code for return shapes.
3. Convert the claim into a deterministic command. The command should be repeatable by the next agent and should return a result that changes the plan if false.
4. Decide disposition from evidence, not intent. Valid dispositions are self-contained implementation, explicit dependency with a hard halt, verified close, verified already-complete, or expanded scope. A no-op is forbidden when the premise is unverified.
5. If an artifact exists only on an unmerged branch and can be reproduced, make the PR self-contained. If it cannot be reproduced, encode the dependency explicitly and stop until the dependency is merged.
6. For enforcement and CI, prove consumption. A job that runs is not a gate unless the branch protection or ruleset requires its context. A guard cannot be added at an integration point that does not exist.
7. For populations, enumerate the full set from the authority before sampling. Named issue examples are clues, not coverage.
8. For implementation behavior, read the actual route/function/helper before asserting response shape, return keys, side effects, or test expectations.
9. Preserve the evidence in the plan: command, observed output summary, and how it changed scope or disposition.

### Worked Examples

| Issue or Context | Premise Type | Verification | Correct Disposition |
|---|---|---|---|
| ProjectHermes #556 and #674 | Branch-scoped artifact and helper existence | Scanned all branches, checked merge ancestry, and grepped the working tree for the named helper. | The work was valid but not present on `main`; make the PR self-contained by regenerating or adding the helper rather than waiting on a sibling branch. |
| ProjectProteus #182 and #185 | Follow-up issue assumes prerequisite work exists on `main` | Checked `gh pr view` merge state and `git show origin/<branch>:<file>` versus current `main`. | Add an explicit merge gate or expand scope; do not reference recipes or claims absent from the branch where the hook runs. |
| ProjectProteus #184 | CI job runs but may not gate | Compared workflow presence with ruleset/required-context state. | Treat ungated CI as advisory until branch protection or rulesets require it. |
| ProjectHephaestus #1207 | Enforcement guard assumes an integration point exists | Read the installed architecture and found no hook path for the proposed guard. | Ship the library/CLI verifier and clear earlier unverified guard assumptions instead of pretending the integration point exists. |
| ProjectAgamemnon #316 | Test plan assumes route/API response shape | Read the actual route and implementation return keys before writing assertions. | Assert the real shape, not the issue text's inferred shape. |
| Ecosystem branch migration #24 | Named subset treated as full population | Enumerated the live repository population and current branch state. | Expand to the full population or close as already complete when live state proves no remaining work. |
| Doc-config enforcement gate and Grafana issue #179 | Gate matcher assumes exact shipped layout | Tested the matcher against the post-fix tree using tracked files. | Validate the shipped layout with `git ls-files`; do not rely on pre-fix paths or recursive filesystem assumptions. |
| Ruleset/live-state issue #177 | Static repository file treated as source of truth | Read live GitHub rulesets and compared them to proposed file edits. | Preserve live applied enforcement; a static edit that weakens live state is a regression. |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| Current-branch-only artifact check | Concluded a script or helper never existed after grepping only the working tree. | The artifact lived on an unmerged sibling branch. | Scan `origin/main` and relevant remote branches before deciding an issue premise is false. |
| Correct but blocked plan | Acknowledged a valid dependency but left the work waiting on another PR. | The plan was not actionable today. | Reproduce or vendor the prerequisite into the current PR when possible; otherwise encode a hard dependency. |
| NOGO assumptions left unresolved | Listed unverified assumptions after review identified them as gating. | The next agent still had to guess. | Convert each assumption into a check, disposition, or explicit blocker. |
| Named subset scan | Checked only repositories or files named in the issue. | An unnamed population member changed the result, or the work was already complete. | Enumerate the full population from the authority before planning coverage. |
| CI presence treated as gating | Saw that a job ran and claimed enforcement existed. | The job was not required by branch protection or rulesets. | Verify required contexts and rulesets, not just workflow execution. |
| Route shape inferred from issue text | Wrote assertions for JSON keys without reading the route. | The implementation returned a different shape. | Read source before asserting behavior. |
| Static config edited without live check | Proposed a repository file change against an already-applied live ruleset. | The static edit would have regressed live enforcement. | Compare desired config with live API state before changing enforcement. |
| Gate matcher not tested on shipped tree | Designed a matcher around pre-fix or recursive filesystem assumptions. | The gate did not match the actual tracked layout. | Test gates against the post-fix tracked tree with `git ls-files`. |
| Missing integration point ignored | Planned a guard at an architecture hook that was absent. | There was nowhere reliable to attach enforcement. | First verify the integration point exists; otherwise change scope to create or replace it. |

## Results & Parameters

Use the smallest command that proves or disproves the premise. Record the command and the observed fact in the plan or PR comment.

```bash
# Merge state and branch ancestry.
gh pr view <number> --json state,mergedAt,headRefName
git merge-base --is-ancestor <sha-or-ref> origin/main

# Artifact and source-of-truth checks.
git show origin/main:<path>
git ls-files <path-or-pattern>
rg '<symbol-or-route>' <candidate-paths>

# Rulesets and gate enforcement.
gh api repos/<org>/<repo>/rulesets --jq '.[] | {name, enforcement, rules, conditions}'
gh pr checks <number>

# Full population checks.
gh repo list "$ORG" --limit 200 --json name --jq '.[].name'
git ls-files | rg '<population-pattern>'

# Tracked-tree gate simulation.
git ls-files | <gate-command-or-filter>
```

Parameters to capture:

- `premise`: the exact claim the plan relies on.
- `authority`: the source that can prove or disprove it.
- `command`: the deterministic check used.
- `observed_result`: concise output or fact, not speculation.
- `disposition`: self-contained implementation, explicit dependency, expanded scope, verified close, or verified already-complete.
- `examples`: issue-specific facts belong in the plan and in this skill's history, not in new duplicate memories unless the rule is genuinely different.
