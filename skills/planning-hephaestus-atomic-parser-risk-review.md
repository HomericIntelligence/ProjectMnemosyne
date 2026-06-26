---
name: planning-hephaestus-atomic-parser-risk-review
description: "Review-risk checklist for ProjectHephaestus issue plans that combine automation atomic-write migrations with validation CLI parser helper extraction. Use when: (1) reviewing a plan to replace Path.write_text calls with write_secure, (2) centralizing validation CLI flags such as --repo-root, --json, and --version, (3) checking issue title/body mismatch, stale grep counts, or unverified file/API assumptions before implementation."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - hephaestus
  - issue-plan
  - review-risks
  - atomic-writes
  - write-secure
  - path-write-text
  - validation-parser
  - repo-root
  - parser-helper
  - planning-assumptions
  - unverified-sources
---

# Hephaestus Atomic Writes and Validation Parser Plan Risk Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture durable reviewer guidance from the ProjectHephaestus issue #1410 implementation plan: replace raw automation state/log/prompt/output `Path.write_text()` writes with canonical atomic `write_secure()`, and extract shared validation CLI parser boilerplate without behavior changes. |
| **Outcome** | Planning guidance only. The plan was produced from issue context and planning-time repository observations, but the implementation was not completed or re-verified end-to-end in this learning capture. |
| **Verification** | unverified - only ProjectMnemosyne skill schema validation was run for this file; no ProjectHephaestus implementation, tests, or CI were executed as part of this skill capture. |

## When to Use

- Reviewing or authoring a ProjectHephaestus plan that treats an issue title/body mismatch as union scope instead of choosing one side.
- Replacing `Path.write_text()` writes in `hephaestus/automation` with `write_secure()` and needing to preserve payload, encoding, formatting, newline, and non-fatal behavior.
- Centralizing validation CLI boilerplate for `--repo-root`, `--json`, `--version`, fallback repo-root resolution, and argv handling.
- Auditing a plan that cites exact file/line references, grep counts, or external issue-context skills without direct verification in the implementation checkout.
- Checking parser refactors where `parse_args()` is overridden but `parse_known_args()` passthrough behavior must remain intact.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Proposed Workflow (UNVERIFIED - planning review checklist)

### Quick Reference

```bash
# Re-verify the write_text population before judging completeness.
rg -n '\.write_text\(' hephaestus/automation

# Re-verify the canonical atomic writer and its semantics before migrating call sites.
rg -n 'def write_secure|write_secure\(' hephaestus/io hephaestus/automation tests

# Re-verify validation CLI parser behavior and every command that should, or should not, take repo-root.
rg -n -- '--repo-root|--json|--version|parse_args|parse_known_args|get_repo_root' hephaestus tests scripts

# Confirm tests execute migrated behavior, not only import shape or grep structure.
rg -n 'write_secure|write_text|create_validation_parser|parse_known_args|repo-root' tests
```

### Detailed Steps

1. **Treat title/body mismatch as union scope only after stating it explicitly.**
   For issue #1410, the plan objective combined two surfaces: automation raw file writes and validation CLI parser boilerplate. A reviewer should confirm both sides are deliberately in scope and that neither is silently dropped as "not in the title" or "not in the body."

2. **Recompute the current offender set from the implementation checkout.**
   The plan recorded a planning-time `rg` count of 54 `write_text` offenders in `hephaestus/automation`, not the stale issue count of 84+. That count is not durable evidence. The completion gate should be based on the current checkout reaching zero scoped offenders in `hephaestus/automation`, with intentional uses elsewhere left alone.

3. **Verify `write_secure()` semantics before replacing write sites.**
   The plan assumed `hephaestus/io/utils.py` exposes the canonical atomic writer and that it preserves the required behavior for automation state, log, prompt, and output writes. Reviewers should read the helper and require tests around exact string payloads, JSON serialization, trailing newlines, encodings, and error behavior at representative call sites.

4. **Do not let an atomic-write migration become a formatting migration.**
   Each replacement should preserve the bytes the old code wrote unless the issue explicitly asks for a format change. JSON indentation, `sort_keys`, terminal newlines, and prompt transcript text are observable behavior for operators and downstream tools.

5. **Centralize parser boilerplate without broadening command requirements.**
   A shared `create_validation_parser()` helper is reasonable only if commands without repo-root semantics opt out, for example with `add_repo_root=False`. The helper must preserve `--json`, `--version`, explicit `--repo-root` precedence, fallback repo-root resolution, argv call sites, and exit behavior.

6. **Protect `parse_known_args()` passthrough behavior.**
   The plan assumed overriding `parse_args()` but not `parse_known_args()` preserves `mypy_per_file.py` passthrough behavior. That should be tested directly: a parser refactor can look harmless while changing how unknown arguments are forwarded.

7. **Demote planning-time file/line references to hints.**
   References such as `hephaestus/io/utils.py:144`, `hephaestus/io/utils.py:171-182`, `hephaestus/cli/utils.py:75`, validation script line numbers, and the `rg` offender list were planning-time observations. Reviewers should require a fresh checkout read before accepting implementation claims based on those references.

8. **Flag external or embedded guidance that was not locally verified.**
   The plan used embedded issue-context guidance for `dry-refactoring-workflow` because `skills/dry-refactoring-workflow.md` was not present in the checkout. Treat that guidance as external context until the relevant local skill or repo source is verified.

9. **Require behavior tests for migrated commands.**
   Import tests and grep guards are useful but insufficient. Tests should invoke migrated validation commands through their real argv paths and should exercise JSON output, version output, explicit repo-root, fallback repo-root, no-repo-root commands, and passthrough behavior where applicable.

10. **Scope the zero-`write_text` guard narrowly.**
    A guard that rejects all `Path.write_text()` anywhere in the repository is too broad. The issue target was automation state/log/prompt/output writes, so a grep guard should be scoped to `hephaestus/automation` and should allow unrelated intentional write_text usage elsewhere.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Choose one half of the issue | Treat the title/body mismatch as a reason to implement only atomic writes or only parser cleanup | The implementation plan objective was the union of issue title and body; dropping either side leaves the plan incomplete | State union scope up front and map acceptance checks to both surfaces |
| Trust stale write counts | Use the issue's 84+ `write_text` count as the completion target | Planning-time grep found 54 offenders in `hephaestus/automation`; either number can drift before implementation | Recompute offenders in the implementation checkout and gate on current zero scoped matches |
| Treat `write_secure()` as a mechanical rename | Replace calls without proving byte-for-byte behavior at representative call sites | Atomicity can be correct while payload formatting, newline, encoding, JSON serialization, or error behavior changes | Review exact outputs and add behavior tests, not only structural grep checks |
| Add repo-root to every validation command | Centralize parser setup by forcing shared `--repo-root` behavior everywhere | Commands without repo-root semantics may start failing outside a git/project root | Use an opt-out such as `add_repo_root=False` and test no-repo-root commands directly |
| Test only parser imports | Assert `create_validation_parser()` exists and commands import it | Import structure does not prove argv, fallback, explicit precedence, JSON/version output, or passthrough behavior | Exercise real CLI entry paths and `parse_known_args()` passthrough cases |
| Treat planning line numbers as current facts | Implement from cited file/line references and old rg output | Line numbers and offender sets are planning-time observations and drift quickly | Freshly read the helper, scripts, and offender list before coding or approving |

## Results & Parameters

### Issue #1410 Risk Checklist

```text
Scope
- [ ] Title/body mismatch handled as union scope.
- [ ] Atomic-write migration and parser-helper extraction both have acceptance checks.

Atomic writes
- [ ] Current `rg -n '\.write_text\(' hephaestus/automation` offender set recomputed.
- [ ] All migrated automation state/log/prompt/output writes use `write_secure()`.
- [ ] Exact payload strings, JSON formatting, trailing newlines, encodings, and non-fatal/error behavior are preserved.
- [ ] Zero-write_text guard is scoped to `hephaestus/automation`, not the whole repo.

Validation parser helper
- [ ] Shared helper preserves `--json`, `--version`, explicit `--repo-root`, and fallback repo-root resolution.
- [ ] Commands without repo-root semantics opt out, for example with `add_repo_root=False`.
- [ ] Existing argv call sites still pass arguments correctly.
- [ ] `parse_known_args()` passthrough behavior is tested for commands that forward unknown args.

Evidence discipline
- [ ] File/line references and grep counts from the plan are re-verified in the implementation checkout.
- [ ] Embedded or external workflow guidance is treated as unverified until checked locally.
- [ ] Behavior tests run migrated commands, not only import/grep structure.
```

### Planning-Time Assumptions to Re-Verify

| Assumption | Planning Status | Reviewer Action |
|------------|-----------------|-----------------|
| Issue title/body mismatch means union scope | Unverified policy decision | Confirm issue owner/reviewer expectation and ensure both workstreams are delivered |
| `hephaestus/automation` has 54 current `write_text` offenders | Planning-time `rg` observation | Re-run the scoped grep before and after implementation |
| `write_secure()` is the canonical atomic writer | Planning-time source observation | Read the helper and test migrated behavior at representative call sites |
| Parser helper can preserve behavior with `add_repo_root=False` for no-root commands | Design assumption | Exercise no-root commands outside a git/project root |
| Overriding `parse_args()` but not `parse_known_args()` preserves passthrough | Design assumption | Add or run a passthrough regression test for the affected command |
| `dry-refactoring-workflow` guidance applies | Embedded issue-context guidance, local skill absent | Treat as external guidance unless verified in the local checkout |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1410 implementation-plan learning capture | Planning-only guidance for reviewing atomic `write_secure()` migration plus validation parser helper extraction. Verification level is unverified; only ProjectMnemosyne skill validation was run for this learning PR. |
