---
name: automation-agent-commit-type-must-match-pr-policy-allowlist
description: "An LLM commit-message / PR-title generator inside an automation loop can emit a Conventional-Commit type that the repo's OWN pr-policy CI gate forbids, BLOCKING the PR and triggering an expensive CI-fix agent to clean up the automation's own output (a self-inflicted CI failure). The fix has two REQUIRED parts plus a drift guard: (1) PROMPT — list the allowed types explicitly in BOTH the commit-message prompt AND the PR-message prompt so the agent stays in-bounds; (2) LOCAL NORMALIZATION (defense — the model can still go off-list) — after parsing the agent's subject/title, rewrite a disallowed leading `type(scope)?:` token to a safe default (`chore`) while PRESERVING scope, `!`, and description, and prepend a `chore:` prefix (with a following space) when there is no recognizable prefix; apply to BOTH the commit subject AND the PR title (a squash merge uses the PR title as the commit subject, so a forbidden type in the TITLE fails pr-policy too); (3) SINGLE SOURCE OF TRUTH — mirror the gate's ALLOWED_TYPES as a library constant but do NOT import the standalone CI check script into library code (that inverts the scripts->library dependency direction, and the script must stay standalone for the gate) — instead add a TEST that asserts the mirrored set == the script's ALLOWED_TYPES (import the script via sys.path) so drift fails CI. Use when: (1) an automation/agent loop generates commit messages or PR titles and the repo enforces a conventional-commit-type allowlist in CI (pr-policy / check_conventional_commit.py); (2) a PR went BLOCKED on pr-policy with a forbidden type like `security(audit):` or `wip:` and a CI-fix agent had to re-type the commits; (3) you fixed only the commit subject but forgot the PR title and the squash-merge subject still fails; (4) you are tempted to import a `scripts/check_*.py` gate into library code to reuse its allowlist; (5) you rely on the prompt alone to keep the model in-bounds."
category: ci-cd
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - ci-cd
  - conventional-commits
  - commit-message
  - pr-title
  - pr-policy
  - allowlist
  - allowed-types
  - self-inflicted-ci-failure
  - automation-loop
  - llm-generated-commit
  - local-normalization
  - squash-merge-subject
  - single-source-of-truth
  - scripts-library-dependency-direction
  - drift-sync-test
  - chore-fallback
  - verified-ci
---

# Automation Agent Commit Type Must Match the pr-policy Allowlist

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-23 |
| **Objective** | Stop an automation loop from self-inflicting CI failures: an LLM commit-message / PR-title generator can emit a Conventional-Commit type that the repo's OWN `pr-policy` gate forbids, blocking the PR and forcing an expensive CI-fix agent to clean up the automation's own output. |
| **Outcome** | Implemented and CI-verified. ProjectHephaestus PR #1589 ("fix loop self-inflicted CI failures") added the allowed types to BOTH generator prompts, added local normalization of a disallowed leading `type(scope)?:` token (→ `chore`) on BOTH the commit subject AND the PR title, mirrored the gate's `ALLOWED_TYPES` as a library constant, and added a sync test asserting the mirror equals the script's set. |
| **Verification** | verified-ci (PR #1589 merged; a subsequent clean run on 2026-06-23 produced a valid `ci(workflows): add concurrency controls to event-driven workflows` commit and PR #1590 merged with NO pr-policy failure and NO CI-fix self-cleanup). |
| **Files** | `hephaestus/automation/pr_manager.py` (`_commit_message_prompt`, `_pr_message_prompt`, `ALLOWED_CONVENTIONAL_TYPES`), `scripts/check_conventional_commit.py` (the gate, unchanged), a sync test asserting mirror == gate `ALLOWED_TYPES`. |

## When to Use

Reach for this whenever an automation or agent loop GENERATES a commit message or a PR title and the repository enforces a conventional-commit-type allowlist as a required CI gate. Specifically:

- An automation pipeline calls an LLM to write the commit subject and/or PR title, and the repo's `pr-policy` job (`scripts/check_conventional_commit.py` or equivalent) rejects any leading `type:` outside a fixed allowlist.
- A PR went BLOCKED on `pr-policy` / `required-checks-gate` because the generated subject used a forbidden type (real example: `security(audit): add threat model and pip-audit reminder` — `security` is not in the allowlist), and a CI-fix agent then spent ~10 min / ~37 turns / ~594s re-typing the commits to `fix:`.
- You normalized the commit SUBJECT but the PR is still red — because a squash merge uses the PR TITLE as the merge-commit subject, so a forbidden type in the title fails `pr-policy` independently.
- You are tempted to `import` the standalone `scripts/check_*.py` gate into library code to reuse its allowlist — which inverts the scripts→library dependency direction AND breaks the gate's standalone requirement.
- You are relying on the prompt alone to keep the model in-bounds — it occasionally still emits a disallowed type, so a non-LLM normalization step is required as defense.

## Verified Workflow

### Quick Reference

The fix is two REQUIRED parts plus a drift guard:

| Part | What | Why required |
| - | - | - |
| 1. Prompt | List the allowed types explicitly in BOTH `_commit_message_prompt` AND `_pr_message_prompt` | Keeps the model in-bounds in the common case; cheapest layer |
| 2. Normalize | After parsing the agent's output, rewrite a disallowed leading `type(scope)?:` token to `chore` (preserve scope, `!`, description); prepend a `chore:` token + space if no recognizable prefix. Apply to BOTH the commit SUBJECT and the PR TITLE | The model can still go off-list; prompt alone is not enough. The PR title becomes the squash-merge subject, so it ALSO must pass pr-policy |
| 3. Sync test | Mirror the gate's `ALLOWED_TYPES` as a library constant (`ALLOWED_CONVENTIONAL_TYPES`); add a test asserting `mirror == gate.ALLOWED_TYPES` (import the script via `sys.path`) | DRY without inverting the scripts→library dependency arrow; drift between the two lists fails CI |

Allowlist (ProjectHephaestus `pr-policy`): `feat, fix, docs, refactor, test, chore, ci, build, perf, style, revert`. NOT allowed: `security`, `wip`, anything else.

Normalization regex and examples:

```text
^(?P<type>[a-z]+)(?P<scope>\([^)]*\))?(?P<bang>!)?:\s
```

| Input subject/title | Normalized output | Note |
| - | - | - |
| `security(audit): X` | `chore(audit): X` | type swapped, scope kept |
| `security!: X` | `chore!: X` | type swapped, `!` kept |
| `wip: X` | `chore: X` | type swapped |
| `add a thing` (no prefix) | `chore: add a thing` | `chore:` + space prepended |
| `fix(io): X` (allowed) | `fix(io): X` | unchanged |

### Detailed Steps

**1. Add the allowlist to BOTH generator prompts.**
In the commit-message prompt (`_commit_message_prompt`) and the PR-message prompt (`_pr_message_prompt`), state the allowed conventional-commit types explicitly and instruct the model that the subject/title MUST begin with one of them. This is the cheap, first-line defense — it eliminates most off-list output but is NOT sufficient alone.

**2. Normalize after parsing — for BOTH the commit subject AND the PR title.**
Do not trust the model. After extracting the subject (and separately the PR title), apply a deterministic rewrite:

- Match a leading conventional prefix with `^(?P<type>[a-z]+)(?P<scope>\([^)]*\))?(?P<bang>!)?:\s`.
- If `type` is in the allowlist → leave the string unchanged.
- If `type` is NOT in the allowlist → replace ONLY the `type` token with `chore`, preserving `scope`, `!`, and the description verbatim.
- If there is NO recognizable conventional prefix at all → prepend a `chore:` token followed by a space.

Apply this to the commit subject AND the PR title. The PR TITLE is load-bearing: a squash merge (this repo is squash-only) uses the PR title as the merge-commit subject, so a forbidden type left in the title fails `pr-policy` even when every individual commit is clean. Forgetting the title is the single most common partial-fix mistake.

**3. Single source of truth — mirror, do NOT import the gate.**
The library must not `import scripts.check_conventional_commit`:

- It inverts the dependency direction (scripts → library is the allowed arrow; library → scripts is not).
- The check script must stay standalone (stdlib-only, no library import) so the CI gate can run it in isolation.

Instead, declare a library constant (e.g. `ALLOWED_CONVENTIONAL_TYPES` in `pr_manager.py`) that mirrors the gate's `ALLOWED_TYPES`, and add a TEST that imports the script via `sys.path.insert(0, scripts_dir)` and asserts `ALLOWED_CONVENTIONAL_TYPES == check_conventional_commit.ALLOWED_TYPES`. Any future drift between the two lists then fails CI instead of silently re-opening the self-inflicted-failure hole.

**4. Verify on a clean run, not just unit tests.**
Confirm the fix end-to-end: a real automation run should produce a valid-typed commit/PR and merge with NO `pr-policy` failure and NO CI-fix agent self-cleanup. (PR #1590's `ci(workflows): ...` run did exactly this.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Prompt only | Tell the model the allowed types in the prompt and trust it | The model still occasionally emits a disallowed type (`security`, `wip`), so the PR intermittently goes BLOCKED on pr-policy | The prompt is necessary but NOT sufficient; add deterministic local normalization as defense |
| Subject only | Normalize the commit subject but leave the PR title untouched | A squash merge uses the PR TITLE as the commit subject, so a forbidden type in the title fails pr-policy even with clean commits | Normalize BOTH the commit subject AND the PR title — the title is the squash-merge subject |
| Import the gate | `import scripts.check_conventional_commit` into library code to reuse its `ALLOWED_TYPES` | Inverts the scripts→library dependency direction and breaks the gate's standalone (stdlib-only) requirement | Mirror the set as a library constant and add a sync TEST (import the script via sys.path) asserting mirror == gate set |
| Hand-fix after the fact | Let the CI-fix agent re-type the commits when pr-policy blocks | Expensive: ~10 min / ~37 turns / ~594s of agent time spent cleaning up the automation's OWN output; the title was even left wrong | Prevent the bad output at generation time; do not absorb the cost of a downstream CI-fix loop on self-inflicted failures |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Verification level** | verified-ci (ProjectHephaestus PR #1589 merged; clean follow-up run + PR #1590 merged with no pr-policy failure and no CI-fix self-cleanup, 2026-06-23) |
| **Allowlist (gate)** | `feat, fix, docs, refactor, test, chore, ci, build, perf, style, revert` |
| **Forbidden examples** | `security`, `wip` (and any token not in the allowlist) |
| **Real failing case** | `security(audit): add threat model and pip-audit reminder` (merged commit `b167c57` on main landed BEFORE this fix existed) |
| **Safe-default type** | `chore` (preserve scope, `!`, description; prepend a `chore:` token + space when no prefix) |
| **Normalization regex** | `^(?P<type>[a-z]+)(?P<scope>\([^)]*\))?(?P<bang>!)?:\s` |
| **Apply to** | BOTH the commit subject AND the PR title (squash-merge subject = PR title) |
| **DRY mechanism** | Mirror `ALLOWED_TYPES` as a library constant + a sync test (`mirror == gate.ALLOWED_TYPES`); never import the script into library code |
| **Self-cleanup cost avoided** | ~594s / ~37-turn CI-fix agent run per blocked PR |

### Verified On

| Repo | Context | Status |
| ---- | ------- | ------ |
| ProjectHephaestus | PR #1589 — added allowlist to both generator prompts, local normalization of commit subject + PR title, mirrored constant + sync test | verified-ci (merged) |
| ProjectHephaestus | PR #1590 — clean follow-up automation run produced `ci(workflows): add concurrency controls to event-driven workflows` | verified-ci (merged 2026-06-23 with no pr-policy failure, no CI-fix self-cleanup) |
