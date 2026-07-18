---
name: architecture-claude-permission-bypass-removal-planning
description: "Plan and review removal of Claude --dangerously-skip-permissions from autonomous automation paths without losing unattended operation. Use when: (1) a Claude automation path must stop passing the bypass flag, (2) permission-mode dontAsk plus allowedTools is being substituted for full bypass, (3) tests need AST guards against reintroducing unsafe Claude argv or extra_args, (4) compact/resume/print Claude CLI behavior is inferred from local patterns rather than verified end-to-end."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - claude
  - permissions
  - automation
  - ast-guard
  - security
  - hephaestus
  - planning
---

# Architecture: Claude Permission Bypass Removal Planning

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-07-02 |
| **Objective** | Preserve autonomous Claude automation while removing `--dangerously-skip-permissions` from named invocation paths and preventing reintroduction. |
| **Outcome** | Planning guidance only. The approach was inferred from repository patterns during ProjectHephaestus issue #1480 planning, not verified by an end-to-end automation run or live Claude CLI execution. |
| **Verification** | unverified |

## When to Use

- A ProjectHephaestus or ecosystem automation path invokes Claude with `--dangerously-skip-permissions` and must be moved to least-privilege permissions.
- The intended replacement is `permission_mode="dontAsk"` plus an existing scoped `allowed_tools` contract, and reviewers need to know what assumptions remain unproven.
- A shared Claude helper can centrally block unsafe flags, but direct `subprocess` Claude invocations still need AST or source-structure regression guards.
- A plan touches `invoke_claude_with_session(extra_args=...)`, direct Claude argv lists, `/compact`, `--resume`, `--print`, or `--output-format` behavior without live CLI verification.
- Reviewers need a checklist focused on unattended-operation regressions, false-negative guard patterns, and over-blocking legitimate constants or tests.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Find bypass usage and classify each occurrence before editing.
rg -n -- '--dangerously-skip-permissions|permission_mode|allowed_tools|extra_args' \
  hephaestus/automation tests

# Review direct Claude subprocess construction separately from helper calls.
rg -n 'subprocess\.(run|Popen)|\\["claude"|\\("claude"' hephaestus/automation tests

# Verify the implementation with focused tests plus the repo's standard gate.
pixi run pytest tests/unit/automation -v
pixi run pre-commit run --all-files
```

### Detailed Steps

1. **Re-read the live issue before implementing.** For issue-driven work, fetch the current issue body and acceptance criteria before coding. The original planning session did not re-read GitHub issue #1480, so cited file names, line numbers, and acceptance details may have drifted.

2. **Inventory every Claude invocation path by mechanism.** Split findings into helper-based calls, direct `subprocess` argv construction, and compact/resume helpers. Do not treat `invoke_claude_with_session(...)` and raw `["claude", ...]` lists as equivalent; they need different guards.

3. **For autonomous helper calls, replace bypass with scoped non-interactive permissions.** Where the call already has an intentionally narrow `allowed_tools` scope, the proposed replacement is to remove `extra_args=["--dangerously-skip-permissions"]` and pass `permission_mode="dontAsk"` through the helper. This is a hypothesis for paths such as `post_merge_processor.py` and `ci_fix_orchestrator.py`: it follows nearby implementer/review/address-review patterns, but must be proven by an unattended run.

4. **For `/compact`, prefer no tool access unless a real run disproves it.** The planning assumption was that `learn.py` `compact_session()` can drop the bypass flag without adding `--permission-mode` or `--allowedTools`, because `/compact` should not need tool access. Keep this as least-privilege pending a real Claude CLI `/compact` execution.

5. **Add a helper-level denylist, but do not rely on it alone.** A central denylist in `claude_invoke.py` can block helper-based reintroduction through `extra_args`, but it cannot see future direct subprocess calls, shell strings, wrapper functions, or dynamically constructed argv.

6. **Add AST guard coverage for direct invocation shapes.** The guard should catch actual automation call argv lists and `invoke_claude_with_session(extra_args=...)` usage. It should intentionally allow the denylist constant in `claude_invoke.py` and benign tests or documentation that mention the string without invoking Claude.

7. **Test for unsafe variables, not only literal absence.** A test that asserts no literal `extra_args=["--dangerously-skip-permissions"]` remains can miss variables, helper wrappers, joined shell strings, or computed lists that still carry the unsafe flag. Include fixtures for non-literal and wrapper-shaped bypasses when building the guard.

8. **Verify unattended behavior as the decisive acceptance test.** Local unit tests and AST guards prove the bypass flag is absent; they do not prove the automation remains autonomous. Reviewers should require a real or faithfully simulated drive-green/learn/CI-fix path before upgrading the verification level above `unverified`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Infer autonomy from nearby patterns only | Assumed `permission_mode="dontAsk"` plus existing `allowed_tools` keeps post-merge and CI-fix paths unattended | Not proven by an end-to-end automation run; Claude may still prompt or deny a needed tool | Treat this as a high-risk assumption until a real unattended path completes |
| Drop `/compact` bypass without live CLI verification | Assumed `/compact` needs no tool access and therefore needs neither `--permission-mode` nor `--allowedTools` | The command shape was not tested against a real Claude CLI session | Keep the least-privilege design, but make compact-session behavior a reviewer focus |
| Central denylist only | Blocked unsafe flags in `claude_invoke.py` helper inputs | Direct `subprocess` invocations and shell strings bypass the helper | Pair the denylist with AST/source guards over automation invocation sites |
| Literal-only regression guard | Checked for absence of a literal unsafe `extra_args` list | Variables, wrapper functions, computed lists, or shell strings can still carry the bypass | Add guard fixtures for non-literal unsafe flag paths |
| Broad string ban | Considered blocking every occurrence of `--dangerously-skip-permissions` | Would over-block the denylist constant, negative tests, and legitimate documentation | Scope guards to executable invocation contexts and explicitly allow the denylist/test constants |
| Plan from stale local inspection | Relied on planner-read files and line numbers without re-reading issue #1480 or GitHub branch policy | Issue body, source line numbers, or required checks may drift before implementation | Re-query live issue and current source before final implementation |

## Results & Parameters

Use these review questions before approving a permission-bypass removal PR:

| Risk Area | Reviewer Check |
| --------- | -------------- |
| Unattended operation | Did a real or faithful drive-green, learn, or CI-fix path complete without interactive prompts after removing the bypass flag? |
| Scoped tools | Does each autonomous path preserve the narrow `allowed_tools` it already relied on, rather than widening permissions to compensate? |
| Helper denylist | Does `claude_invoke.py` reject unsafe bypass flags passed through `extra_args` while still allowing the denylist constant itself? |
| Direct subprocesses | Does an AST guard scan direct Claude argv construction under the automation tree, not just helper calls? |
| Non-literal bypasses | Do tests include variables, wrappers, computed argv lists, and shell-string cases that could smuggle the bypass flag? |
| Over-blocking | Are tests, constants, and documentation allowed to mention the unsafe flag when they are not executable Claude invocations? |
| Compact behavior | Was `/compact` tested in a real session, or is the no-tool least-privilege behavior still marked unverified? |
| External assumptions | Were issue #1480, current source locations, Claude CLI semantics, branch protection, and required checks freshly verified? |

Suggested focused implementation checklist:

1. Re-read the issue and current source.
2. Remove `--dangerously-skip-permissions` from named helper and direct invocation paths.
3. Add `permission_mode="dontAsk"` only where unattended tool access is required and an explicit `allowed_tools` scope already exists.
4. Leave `/compact` without tool permissions unless live verification shows it needs them.
5. Add central helper denylist coverage.
6. Add AST guard coverage for direct Claude invocation contexts and unsafe helper `extra_args`.
7. Run focused unit tests, pre-commit, and an unattended automation-path verification before claiming the workflow is verified.
