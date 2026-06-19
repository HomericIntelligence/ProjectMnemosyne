---
name: audit-remediation-verify-evidence-before-planning
description: "Before planning a fix for a cross-repo audit/remediation issue, verify the audit's cited evidence (file:line) against the live tree — audit findings go stale once the target repo is independently remediated. Use when: (1) planning a fix for an audit-filed issue with file:line evidence, (2) the issue spans multiple repos or submodules, (3) the issue recommends doc/field-name changes that may already be done."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Audit Remediation: Verify Evidence Before Planning

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Plan a fix for a cross-repo audit-remediation GitHub issue without trusting stale audit evidence |
| **Outcome** | Discovered the audit was stale — target submodule already remediated; scoped the plan to only the genuinely-actionable owned-repo work + a drift guard |
| **Verification** | verified-local |

> **Verification note:** The evidence-verification steps below (grep against the live tree, confirming canonical names in the Pydantic source of truth) were genuinely RUN this session and confirmed the target docs were already remediated — that is what `verified-local` attests to. The downstream implementation (the architecture.md section + the drift-guard script wired into `just ci`) was **planned only**, not executed or CI-validated. Do not read this as `verified-ci`.

## When to Use

- Planning a fix for an issue filed by an automated/ecosystem audit that cites specific `file:line` evidence.
- The issue spans multiple repos, especially when some are git submodules owned by other repos.
- The recommendation is a doc/field-name/role-description change that another team may have already fixed.
- Any "documentation drift" or "X docs show deprecated Y" issue.

## Verified Workflow

The evidence-verification phase (steps 1-3) was actually executed against the live tree and is the basis for the `verified-local` claim. Steps 4-6 (scoping and the drift guard) were the resulting plan, which was not itself executed in CI.

1. **Read the issue's cited evidence FIRST and diff it against the live tree.** For every `file:line` the issue names, open the live file at those coordinates and confirm the claimed text is actually there. Do not assume the evidence is current — an audit captures a snapshot at filing time, and the target may have moved on.
2. **Identify the source of truth and confirm canonical values there.** For a field-name/schema issue, the source of truth is the code (Pydantic models / enums / REST contract), not the prose. Confirm the canonical values in code, and treat docs as the thing aligned TO code, never the reverse.
3. **Distinguish real hits from false positives — grep, then eyeball each in context.** A token like `title:` inside a generated JSON-Schema is a display label, and a method name like `test_unknown_depends_on_raises` is describing behavior — neither is a documented schema field. A raw grep count is not a violation count; inspect every hit.
4. **Scope by ownership.** Do NOT edit files inside git submodules from the meta-repo — they are owned by their own repo and must be PR'd there (or a referencing issue filed). One PR per owned repo.
5. **If the cited target is already remediated, say so explicitly.** State it in the plan and in the PR body, then pivot the plan to (a) the still-actionable owned-repo recommendation and (b) a drift-prevention guard so the deprecated form cannot silently return.
6. **Match the repo's EXISTING check pattern for the guard.** Here that meant a bash script under `scripts/` plus a `just` recipe wired into `just ci` — not a new framework. A meta-repo with "no application code" should not get a pytest harness just for a doc check.

### Quick Reference

```bash
# 1. Re-verify audit evidence against live tree (expect: stale audit => no hits)
grep -nE '^[[:space:]]*-?[[:space:]]*(title|depends_on):' <cited-docs>
# 2. Confirm canonical names in the source of truth (Pydantic model)
grep -nE 'subject:|blocked_by:' src/<pkg>/models.py
# 3. Check ownership before editing — submodules are off-limits from the meta-repo
git submodule status
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusting the audit's file:line evidence as current | Issue cited `CLAUDE.md:55-58` / `README.md:62-69` as showing `title`/`depends_on` | The submodule had already been remediated independently; those lines now use `subject`/`blocked_by` | Always re-read cited evidence against the live tree before planning |
| Grepping for `title`/`depends_on` and treating every hit as a violation | Raw grep flagged JSON-Schema `"title":` labels and a `test_unknown_depends_on_raises` method name | These are not documented workflow fields — false positives | Anchor the pattern to field-key syntax and eyeball each hit in context |
| Assuming the meta-repo can fix the submodule's docs in this PR | Planned to edit `provisioning/ProjectTelemachy` docs from Odysseus | Submodules are owned by their own repos; editing their working tree from the meta-repo is wrong scope | Scope edits by ownership; PR the owning repo or file a referencing issue |

## Results & Parameters

- **Canonical field names** (Agamemnon REST contract / Telemachy `TaskSpec`): `subject` (not `title`), `blocked_by`/`blockedBy` (not `depends_on`), `assignee_agent_id`/`assigneeAgentId`.
- **Drift-guard pattern:** first-party-only file list via
  `git ls-files -- '*.md' | awk '!/^(infrastructure|control|provisioning|ci-cd|research|shared|testing)\//'`;
  field-key regex `^[[:space:]]*-?[[:space:]]*(title|depends_on):`;
  exit `0` clean / `1` drift / `2` usage; wire into `just ci`.
- **Submodule dirs in this ecosystem to exclude from first-party scans:** `infrastructure/` `control/` `provisioning/` `ci-cd/` `research/` `shared/` `testing/`.
