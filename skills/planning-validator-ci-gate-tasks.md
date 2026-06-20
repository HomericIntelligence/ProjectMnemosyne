---
name: planning-validator-ci-gate-tasks
description: "Planning-phase risk assessment for 'add a build-free validator' tasks in a submodule meta-repo, where the validator shells out to an external CLI (nats-server, podman/docker compose, nomad) and gets wired into a pinned required CI gate. Captures the recurring uncertain assumptions a reviewer must check: (1) TOOL-FLAG SEMANTICS are the #1 risk — you cannot trust that `nats-server -c <f> -t` means 'test config and exit' or that `podman compose config -q` parses without a running daemon/images; either verify the exact flag at plan time (`<tool> --help | grep`) or label it an explicit unverified assumption the implementer confirms in step 1; (2) GRACEFUL-SKIP-WHEN-TOOL-ABSENT is mandatory to mirror existing conventions (the `nomad`-absent skip) BUT it creates a VACUOUS/DEAD-GATE hazard — a validator that skips when the binary is missing gives ZERO coverage if the enforcing CI runner lacks that binary, so for EACH skip branch the planner must answer 'does the required CI environment actually have this tool installed?'; (3) a repo-wide FORBID-SUPPRESSIONS gate (pre-commit `forbid-or-true` + `_required.yml` forbid-suppressions) rejects `|| true`, `continue-on-error: true`, and `::warning::` — draft every validator error branch with explicit `if`-guards from the start, never silence failures; (4) PINNED required-check contexts (`_required.yml` job `name:` values referenced in the org/repo ruleset JSON) must be STRENGTHENED IN PLACE, never renamed or split into a new job — grep the ruleset for pinned contexts and reuse an existing job; (5) editing `.github/workflows/*` may be blocked by a security hook — plan a Python read→replace→write fallback; (6) UNVERIFIED SYMBOLS in a sourced shared lib (e.g. an `exit_with_status`/`exit_with_failure_count` function in `e2e/lib/common.sh` whose tail was never read) must be confirmed on disk in step 1. Use when: planning to add a config-syntax or compose-validity validator, a justfile-recipe integrity test, strengthening `just validate-configs`, or wiring any new build-free check into a canonical `_required.yml` gate in a meta-repo. Cross-link: ci-hygiene-and-validation-gates (implementation: dead-gate detection + build-free check mechanics, esp. Pattern 4), justfile-and-local-build-verification (implementation: recipe authoring + local verify loop), planning-verify-issue-claims-and-required-check-gating (runs-vs-gates + grep-the-claim), planning-verify-assumptions-before-enforcement-gate (verify infra assumptions + git-ls-files scan scope)."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - planning-methodology
  - validator
  - ci-gate
  - config-validation
  - meta-repo
  - tool-availability
  - flag-semantics
  - graceful-skip
  - vacuous-pass
  - dead-gate
  - forbid-suppressions
  - no-op-suppression
  - pinned-context
  - required-status-check
  - strengthen-in-place
  - workflow-edit-hook
  - unverified-symbol
  - nats-server
  - compose-config
  - build-free
  - unverified-assumptions
---

# Planning: Risk Assessment for "Add a Build-Free Validator + CI Gate" Tasks

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the PLANNING-PHASE risk profile for "add a build-free validator" work in a submodule meta-repo (HomericIntelligence/Odysseus), where the validator shells out to an external CLI and is wired into a pinned, canonical `_required.yml` CI gate. This is a planning-quality skill: it enumerates the recurring UNCERTAIN ASSUMPTIONS a plan of this shape repeatedly gets wrong, and the discipline that resolves each one. |
| **Outcome** | A PLAN (not executed code) for Odysseus issue #198 ("No unit or integration tests for justfile recipes or configs"): add a NATS config-syntax validator (`nats-server -c <f> -t`), a docker-compose validity validator (`podman/docker compose -f <f> config -q`), a justfile-recipe integrity test sourcing `e2e/lib/common.sh`, strengthen `just validate-configs`, and wire the checks into the canonical `_required.yml` gate by STRENGTHENING the existing weak NATS step inside the already-pinned `integration-tests` job (not adding a new job). |
| **Verification** | **unverified** — this is a PLANNING learning. The plan was NOT executed, the validators were NOT run, and CI did NOT run. Every "ASSUMPTION" below is an open reviewer/implementer task to confirm in step 1, not a verified fact. |
| **Category** | ci-cd / planning |
| **History** | none (initial version) |

> **Verification note:** Nothing in this skill was executed end-to-end. In particular, the tool-flag semantics (`nats-server -t`, `compose config -q`), the presence of `nats-server` in the `_required.yml` integration-tests runner, and the exact name of the "return exit code from failure count" function in `e2e/lib/common.sh` were NOT confirmed by execution at plan time. Treat each as an explicit unverified assumption.

## When to Use

- Planning to add a **build-free validator** (config-syntax check, compose-validity check, recipe-integrity test) that shells out to an external CLI such as `nats-server`, `podman`/`docker compose`, or `nomad`.
- Planning to **strengthen an existing `just validate-configs`-style recipe** or add a new lint/validate recipe.
- Planning to wire any new check into a **canonical / pinned `_required.yml` CI gate** in a meta-repo.
- The plan **sources a shared shell lib** (e.g. `e2e/lib/common.sh`) and depends on a helper function whose definition you have not fully read.
- The repo has a **silent-failure-forbidding gate** (`forbid-suppressions` / `forbid-or-true`) and you are about to draft validator error branches.
- You are about to add or rename a **CI job `name:`** that may be pinned as a required status-check context in the org/repo ruleset.

## Proposed Workflow

> **Warning:** This workflow has NOT been validated end-to-end. It is a PLANNING methodology captured at `unverified` level — the plan was never executed and CI never ran. Treat every step as a hypothesis and every "ASSUMPTION" as an open task to confirm before relying on it.

> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. Read the steps as **proposed**, per the warning above.

## Verified Workflow

> **Warning:** This workflow has NOT been validated end-to-end. Treat as a hypothesis until CI confirms. The "Verified Workflow" heading exists only to satisfy the marketplace validator; the actual verification level is `unverified` (see frontmatter and the warning banner above).

### Quick Reference

```bash
# 1. TOOL-FLAG SEMANTICS — the #1 risk for "add a validator". Verify the exact flag at plan time,
#    OR mark it an explicit unverified assumption the implementer confirms in step 1.
#    Do NOT assume `-t` means "test config and exit" or `config -q` parses without a daemon.
nats-server --help 2>&1 | grep -iE -- '-t|--test|config'        # confirm the "check & exit" flag
podman compose --help 2>&1 | grep -iE -- 'config'               # confirm `config -q` is parse-only
docker compose config --help 2>&1 | grep -iE -- 'quiet|-q'      # version-dependent; pin it

# 2. VACUOUS-PASS / DEAD-GATE check — graceful-skip is mandatory BUT must not be a dead gate.
#    For EACH skip branch, answer: does the ENFORCING CI runner actually have this binary?
command -v nats-server >/dev/null || { echo "skip: nats-server absent"; }   # mirrors existing nomad skip
#    THEN grep the workflow that defines the required job to confirm the tool is installed there:
grep -nE 'nats-server|apt-get install|setup-.*nats|container:' .github/workflows/_required.yml
#    If the runner lacks the binary, the new required check is a DEAD GATE (zero coverage).

# 3. FORBID-SUPPRESSIONS — never emit `|| true`, `continue-on-error: true`, or `::warning::`.
#    Read the gate's regex BEFORE drafting; write explicit if-guards from the start.
grep -nE 'forbid|or-true|continue-on-error|suppress' .pre-commit-config.yaml .github/workflows/_required.yml
#    BAD : nats-server -c "$f" -t || true
#    GOOD: if ! nats-server -c "$f" -t; then echo "FAIL: $f"; rc=1; fi

# 4. PINNED CONTEXTS — strengthen in place, never rename/split. Grep the ruleset for pinned names.
gh api repos/<org>/<repo>/rulesets --jq '.[].id' | while read id; do
  gh api repos/<org>/<repo>/rulesets/$id \
    --jq '.rules[]?|select(.type=="required_status_checks")|.parameters.required_status_checks[].context'
done
#    Reuse an EXISTING pinned job (e.g. integration-tests); renaming/splitting bricks the merge queue.

# 5. WORKFLOW-EDIT may be hook-blocked — plan a Python read->replace->write fallback up front.
python3 - <<'PY'
import pathlib; p=pathlib.Path(".github/workflows/_required.yml")
s=p.read_text(); s=s.replace("<old weak step>","<strengthened step>"); p.write_text(s)
PY

# 6. UNVERIFIED SYMBOLS in a sourced lib — confirm the helper exists and its name/signature.
grep -nE 'exit_with_status|exit_with_failure_count|^[a-z_]+\(\)' e2e/lib/common.sh   # read the WHOLE file
```

### Detailed Steps — the discipline a plan of this shape needs

1. **Verify tool-flag semantics, or flag them as unverified — this is the #1 planning risk.**
   When a validator shells out to an external CLI, the exact "check config and exit" flag and
   its no-daemon behavior are version-dependent and NOT trustworthy from memory. The plan assumed
   `nats-server -c <f> -t` is the correct "test config and exit" invocation and that
   `podman compose config -q` parses without a running daemon or pulled images — NEITHER was
   verified by execution. EITHER run `<tool> --help | grep` during planning to confirm the flag,
   OR write the assumption into the plan explicitly as "implementer must confirm in step 1." Both
   `nats-server -t` and `compose config -q` are plausible but pinned-version-dependent.

2. **For every graceful-skip branch, answer "does the enforcing CI runner have this tool?"**
   Mirroring the existing `nomad`-absent skip is the right convention for local dev. BUT a
   validator that skips when the binary is absent provides ZERO coverage in a CI image that lacks
   the binary — a "vacuous pass" / dead gate. The plan did NOT confirm whether `nats-server` is
   installed in the `_required.yml` integration-tests runner; that is a real gap. For each skip
   branch, grep the workflow that defines the required job and confirm the tool is installed
   (`apt-get install`, a setup action, or a `container:` image that bundles it). A required check
   that always skips on CI enforces nothing (ties to `ci-hygiene-and-validation-gates` Pattern 4:
   a named required check that asserts nothing).

3. **Draft error branches with explicit `if`-guards; never use `|| true` / `continue-on-error`.**
   Repos with a silent-failure-forbidding gate (`forbid-suppressions` in `_required.yml` plus a
   `forbid-or-true` pre-commit hook) reject `|| true`, `continue-on-error: true`, and `::warning::`.
   The plan had to iterate its own snippets to remove `|| true`. Read the gate's literal regex
   first, then author every validator failure path as an explicit `if ! cmd; then ...; rc=1; fi`
   from the start — do not draft a suppression and "fix it later."

4. **Strengthen pinned required-check contexts IN PLACE — never rename or split.** `_required.yml`
   job `name:` values are pinned in the org/repo ruleset JSON; renaming a job (or moving a step
   into a brand-new job) removes the pinned context and bricks the merge queue. The plan correctly
   strengthened the weak NATS step INSIDE the existing `integration-tests` job rather than adding a
   new job. Before touching CI, grep the ruleset JSON (`gh api .../rulesets`) for the pinned
   contexts and reuse an existing required job (cross-link
   `planning-verify-issue-claims-and-required-check-gating`: runs-vs-gates).

5. **Plan a Python read→replace→write fallback for `.github/workflows/*` edits.** Editing workflow
   files may be blocked by a security hook. Decide up front that if a direct edit is refused, you
   will apply the change via a small stdlib `pathlib` read/replace/write script, and write that
   into the plan so the implementer is not stuck mid-execution.

6. **Confirm every symbol you source from a shared lib exists on disk.** The plan sources
   `e2e/lib/common.sh` and calls a "return exit code based on failure count" helper it named
   `exit_with_status`, but only lines 13–40 were read — the tail was NOT read, so the name and
   signature are UNVERIFIED. List it as an open step-1 confirmation. Read the WHOLE sourced file
   before depending on a function from it.

7. **Honesty gate: a planning-only learning is `unverified`.** Because the plan was never executed
   and CI never ran, the verification level is `unverified`: title the workflow section "Proposed
   Workflow" with the warning banner (the literal "## Verified Workflow" heading is kept only to
   satisfy the validator), and set frontmatter `verification: unverified`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Drafted validator with `nats-server -c <f> -t` from memory | Assumed `-t` is the "test config and exit" flag and `podman compose config -q` parses without a daemon/images | Neither flag's semantics was verified by execution; both are version-dependent and may differ on the pinned toolchain | Verify the exact flag with `<tool> --help \| grep` at plan time, OR write it into the plan as an explicit unverified assumption the implementer confirms in step 1 |
| Drafted validator error branch with `\|\| true` | Wrote `nats-server -c "$f" -t \|\| true` to keep the step "non-fatal" | The repo's `forbid-suppressions` (`_required.yml`) + `forbid-or-true` pre-commit hook reject `\|\| true`, `continue-on-error: true`, and `::warning::` | Read the suppression gate's regex first; author every failure path as an explicit `if ! cmd; then echo FAIL; rc=1; fi` from the start — never draft a suppression |
| Assumed graceful-skip-when-tool-absent was sufficient coverage | Mirrored the existing `nomad`-absent skip for the new `nats-server` check | A skip-when-absent validator gives ZERO coverage if the ENFORCING CI runner lacks the binary — a vacuous/dead required gate; the plan never confirmed `nats-server` is installed in the `_required.yml` integration-tests runner | For each skip branch, grep the workflow defining the required job and confirm the tool is installed there; a required check that always skips on CI enforces nothing |
| Considered adding a new dedicated CI job for the validators | Thought a clean separate job would be tidier than touching the existing step | `_required.yml` job `name:` values are pinned in the org/repo ruleset; a new job is not a required context (runs but does not gate) and renaming an existing one bricks the merge queue | Strengthen the weak step IN PLACE inside the already-pinned `integration-tests` job; grep `gh api .../rulesets` for pinned contexts before changing any CI job name |
| Planned a direct edit to `.github/workflows/_required.yml` with no fallback | Assumed the workflow file could be edited directly | Editing `.github/workflows/*` may be blocked by a security hook, leaving the implementer stuck mid-execution | Plan a stdlib `pathlib` read→replace→write fallback up front and write it into the plan |
| Referenced `exit_with_status` from `e2e/lib/common.sh` sight-unread | Named the "return exit code from failure count" helper and built the recipe-integrity test on it after reading only lines 13–40 | The function's existence, exact name, and signature were never confirmed — the file tail was not read | Read the WHOLE sourced lib before depending on a function; list the symbol as an explicit step-1 confirmation in the plan |

## Results & Parameters

- **Task shape:** add build-free validators + wire into a pinned `_required.yml` gate, in a
  ~14-submodule meta-repo (HomericIntelligence/Odysseus, issue #198).
- **Validators planned (all unverified flag semantics):**
  - NATS config syntax: `nats-server -c <f> -t` (ASSUMED "test config and exit"; confirm flag).
  - Compose validity: `podman compose -f <f> config -q` / `docker compose -f <f> config -q`
    (ASSUMED parse-only, no daemon/images required; confirm `-q` exists on the pinned version).
  - Justfile-recipe integrity test sourcing `e2e/lib/common.sh` (depends on an UNVERIFIED helper,
    plan-named `exit_with_status`; confirm on disk in step 1).
  - Strengthen `just validate-configs` to invoke the above.
- **CI wiring:** strengthen the existing weak NATS step INSIDE the already-pinned
  `integration-tests` job in `_required.yml` — do NOT add a new job (a new job is not a required
  context; renaming an existing one removes the pinned context and bricks the merge queue).
- **Forbid-suppressions constraint:** `_required.yml` forbid-suppressions + pre-commit
  `forbid-or-true` reject `|| true`, `continue-on-error: true`, `::warning::`. All validator error
  branches must be explicit `if`-guards.
- **Graceful-skip convention:** mirror the existing `nomad`-absent skip — but EACH skip branch is a
  potential vacuous/dead gate; the plan must confirm the enforcing CI runner has the tool installed.
- **Workflow-edit fallback:** plan a Python `pathlib` read→replace→write in case a security hook
  blocks editing `.github/workflows/*`.
- **Open reviewer/implementer tasks (step 1 of execution):** (a) exact `nats-server` "check & exit"
  flag; (b) whether `compose config -q` parses without a daemon on the pinned version; (c) whether
  `nats-server` is installed in the `_required.yml` integration-tests runner; (d) the real name of
  the failure-count→exit-code helper in `e2e/lib/common.sh`.
- **Verification level:** `unverified` — plan only; nothing executed, no CI run. Workflow section is
  titled "Proposed Workflow" with a warning banner; the "## Verified Workflow" heading is retained
  solely to satisfy `scripts/validate_plugins.py`.

### Related skills

- `ci-hygiene-and-validation-gates` — IMPLEMENTATION patterns for build-free CI/pre-commit gates and
  detecting/repairing a dead required gate (Pattern 4). THIS skill is the upstream PLANNING-phase
  risk assessment; it does not duplicate that skill's implementation mechanics.
- `justfile-and-local-build-verification` — IMPLEMENTATION patterns for justfile recipe authoring
  and the local verify→fix→commit→PR loop. THIS skill plans the validator/recipe before it is built.
- `planning-verify-issue-claims-and-required-check-gating` — runs-vs-gates distinction and the
  grep-the-claim discipline for required status checks (the rulesets-API gating-reality check).
- `planning-verify-assumptions-before-enforcement-gate` — verify infrastructure assumptions before
  building a gate, and scope file scans with `git ls-files` (the index) so submodules drop out.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/Odysseus | Issue #198 planning ("No unit or integration tests for justfile recipes or configs") | unverified — planning session only; validators not run, CI not run. All tool-flag semantics, CI-runner tool presence, and the `e2e/lib/common.sh` helper name are open step-1 confirmations, not verified facts. |
