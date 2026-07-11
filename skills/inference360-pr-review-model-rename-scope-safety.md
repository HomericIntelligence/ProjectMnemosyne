---
name: inference360-pr-review-model-rename-scope-safety
description: "Strict review workflow for Inference360 model inventory and model-size rename PRs. Use when: (1) a PR changes H200 Slurm model inventory docs, manifests, generated asset mirrors, scripts, tests, examples, or provider configs, (2) a size/name rename such as 8B to 7B may cross runtime-facing surfaces, (3) green CI must be checked against issue scope, compatibility, source-of-truth parity, and redaction risk."
category: documentation
date: 2026-07-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - inference360
  - pr-review
  - model-inventory
  - model-rename
  - h200-slurm
  - manifests
  - generated-assets
  - redaction
  - compatibility
---

# Inference360 PR Review: Model Rename Scope Safety

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Strictly review Inference360 PR #393, which added `docs/h200-slurm-model-inventory.md` and renamed IFM BBQ 8B / IFM_8B / bbq-8b terminology to 7B across manifests, generated asset mirrors, scripts, tests, docs, examples, and provider configs. |
| **Outcome** | The review workflow produced a strict NO-GO even though CI was green, because issue scope, source-vs-asset parity, inventory acceptance rows, compatibility, traceability, and redaction risks were not proven. |
| **Verification** | verified-local. The review workflow was exercised locally against PR #393, issue #392, and related issue #391. This Mnemosyne skill file was validated locally with `python3 scripts/validate_plugins.py`; Mnemosyne CI and auto-merge are separate and may still be pending. |

## When to Use

- Reviewing an Inference360 PR that changes H200 Slurm model inventory documentation or model-size naming.
- A PR closes one issue but also implements broader rename work from a related open issue.
- Manifests, generated asset mirrors, scripts, tests, examples, docs, provider configs, routes, labels, or operator surfaces change together.
- CI is green but acceptance criteria, source-of-truth parity, compatibility, or redaction evidence still need a strict review verdict.
- A rename may affect runtime-facing identifiers such as default slots, Slurm job names, provider IDs, served model names, benchmark labels, promotion labels, metric labels, routes, or operator flags.

## Verified Workflow

Verified locally only - CI validation pending for this skill PR.

### Quick Reference

```bash
gh pr view 393 --json number,title,body,baseRefName,headRefName,headRefOid,author,files,commits,closingIssuesReferences,statusCheckRollup > /tmp/pr-393-view.json
gh pr diff 393 > /tmp/pr-393.diff
gh issue view 392 --comments --json number,title,state,body,comments,labels,url > /tmp/issue-392.json
gh issue view 391 --comments --json number,title,state,body,comments,labels,url > /tmp/issue-391.json
gh pr checks 393
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
rg -n "IFM_8B|MODEL_8B|PORT_8B|bbq-8b|BBQ-8B|ifm-bbq-8b|/8b|8B" manifests inference360/assets docs examples scripts tests tools -S
comm -3 <(find manifests/services -maxdepth 1 -type f -printf '%f\n' | sort) <(find inference360/assets/manifests/services -maxdepth 1 -type f -printf '%f\n' | sort)
diff -u manifests/services/<service>.yaml inference360/assets/manifests/services/<service>.yaml
rg -n "(/mnt|/lustrefs|<user>|\.internal|checkpoint|prompt_mix|cookie|token)" docs examples manifests inference360/assets tools scripts -S
```

### Detailed Steps

1. Start from issue and PR ownership, not CI status. Read the PR body, closing issue, related open issues, changed file list, and status checks before reading the diff. For this review, compare PR #393 against issue #392 and related open issue #391.

2. Read the repository contract and routing docs before judging H200 Slurm manifest behavior:

   ```bash
   sed -n '1,220p' AGENTS.md
   sed -n '1,220p' CLAUDE.md
   sed -n '1,220p' README.md
   sed -n '1,260p' docs/inference360-design.md
   sed -n '1,220p' docs/runbooks/operator-script-contracts.md
   ```

3. Classify the PR scope. A model inventory PR may document ambiguity without changing runtime facts. A model-size rename PR may change manifests, scripts, routes, labels, and operator surfaces. Do not let one PR close only the inventory issue while quietly implementing broader rename work from a separate open issue.

4. Map acceptance criteria to concrete rows and files. If the issue still requires rows such as Registry identifier, Slurm job class, RoPE settings, route/port labels, operational readiness, dashboard/metric identifiers, known missing facts, or revalidation facts, a simplified table cannot honestly close the issue unless the issue scope is updated.

5. Audit rename scope beyond labels. Check default slots, manifest IDs, routes, metrics/dashboard labels, benchmark/promotion labels, Slurm job names, served model names, provider config IDs, operator flags, environment-variable compatibility, checkpoint references, and generated asset mirrors.

6. Verify source-vs-installed asset manifests by content, not just filename sets. A path-set-only test can stay green while source manifests and packaged asset manifests disagree. Diff representative files and inspect promotion gates, default engine selection, service IDs, readiness gates, and any renamed fields.

7. Treat checkpoint reference renames as evidence-bearing changes. Do not infer that a 7B path exists or is equivalent to an older 8B path from naming alone. Require dated cluster/storage evidence or keep the old physical fact while documenting naming ambiguity.

8. Preserve operator compatibility unless migration is explicitly implemented and tested. Removing `--model-8b`, `MODEL_8B`, `bbq-8b`, `IFM_8B`, provider IDs, or similar surfaces needs aliases, fail-closed migration notes, and regression tests when the related issue asks for compatibility or explicit migration.

9. Compare provider docs to provider configs directly. Provider README IDs can drift from actual config IDs. Do not trust one surface as proof of the other.

10. Run redaction scans across every changed surface, not only the new report. Examples and generated artifacts can expose endpoint addresses, absolute infrastructure paths, checkpoint paths, user-specific paths, internal hostnames, prompt paths, cookies, or tokens. Replace sensitive values with placeholders such as `<REDACTED_ENDPOINT>`, `<REDACTED_CHECKPOINT_PATH>`, `<REDACTED_INFRA_PATH>`, or `<REDACTED_USER_PATH>`.

11. Issue the verdict from requirements and safety evidence. Green CI is necessary but insufficient; strict review should still be NO-GO when acceptance criteria, single-purpose traceability, source-of-truth parity, compatibility, or redaction safety is missing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusted green CI as merge readiness | PR #393 had passing checks, so the review could have stopped there | CI did not prove issue #392 acceptance criteria, source-vs-asset parity, compatibility aliases, or redaction safety | Green CI is necessary but insufficient for H200 Slurm manifest and inventory changes |
| Closed only issue #392 while implementing issue #391 rename scope | The PR linked the inventory issue but also performed broad 8B-to-7B runtime-facing renames | Traceability and single-purpose PR boundaries broke; the related open issue still governed aliases and migration notes | Compare closing issues, related open issues, PR body, and changed files before deciding scope is acceptable |
| Treated the 7B inventory column as permission to rename runtime facts | Issue #392 requested mapping the 7B column to current 8B / IFM BBQ naming and noting ambiguity | Runtime-facing manifests and scripts were changed without explicit scope reconciliation | Documentation ambiguity should not mutate runtime facts unless the issue asks for that and evidence supports it |
| Renamed checkpoint references from 8B-shaped paths to 7B-shaped paths | The rename inferred that new path names existed or were equivalent | Physical storage facts are not proven by naming; bad paths can break serving allocations | Require dated evidence for path existence/equivalence or preserve known physical facts with documented ambiguity |
| Removed old operator surfaces without migration coverage | Old flags, environment variables, model IDs, and provider IDs disappeared | POLA and backward compatibility were violated when issue #391 asked for explicit aliases or migration notes | Add compatibility aliases, fail-closed migration tests, and operator notes before removing established surfaces |
| Compared only asset filename sets | Existing `tests/test_package_metadata_docs.py` compared YAML asset path sets | Source and packaged asset manifests could disagree in content while tests stayed green | Diff source and installed asset manifest contents, especially promotion gates and renamed identifiers |
| Trusted provider README IDs | Documentation and provider config IDs were assumed to match | README IDs can drift from actual config IDs | Compare provider docs and configs directly before approving a rename |
| Scanned only the new inventory report for redaction | The new report looked clean | Renamed examples or generated artifacts can still expose sensitive paths, hosts, prompts, cookies, or tokens | Scan all changed docs, examples, manifests, asset mirrors, scripts, tools, tests, and provider configs |

## Results & Parameters

### Session Result

| Item | Value |
|------|-------|
| Project | LLM360/Inference360 |
| PR reviewed | #393 |
| Closing issue | #392 |
| Related open issue | #391 |
| PR theme | Add H200 Slurm model inventory and rename IFM BBQ 8B / IFM_8B / bbq-8b terminology to 7B |
| CI state | Green at review time |
| Strict review verdict | NO-GO |
| Main blockers | Issue-scope mismatch, missing required inventory rows, source/asset promotion gate mismatch not caught by existing test, compatibility risk, redaction risk |
| Verification level | verified-local for the review workflow and this skill-file validation; Mnemosyne CI and auto-merge are separate |

### Review Checklist

```text
Issue and PR traceability:
- PR body matches closing issue acceptance criteria.
- Related open issues are read and reconciled.
- Broad rename work is not hidden inside an inventory-only issue.

Inventory completeness:
- Registry identifier.
- Slurm job class.
- RoPE settings.
- Route and port labels.
- Operational readiness.
- Dashboard and metric identifiers.
- Known missing facts.
- Revalidation facts and dates.

Rename safety:
- Default slots.
- Manifest IDs.
- Routes.
- Metrics and dashboard labels.
- Benchmark and promotion labels.
- Slurm job names.
- Served model names.
- Provider config IDs.
- Operator flags and environment-variable compatibility.
- Checkpoint references.
- Generated asset mirrors.

Source-of-truth parity:
- Source manifests and packaged asset manifests match by content where they should.
- Promotion readiness gates remain fail-closed.
- Tests cover content drift, not only filename drift.

Redaction:
- Changed docs, examples, manifests, generated assets, scripts, tools, tests, and provider configs are scanned.
- Sensitive values use placeholders: <REDACTED_ENDPOINT>, <REDACTED_CHECKPOINT_PATH>, <REDACTED_INFRA_PATH>, <REDACTED_USER_PATH>.
```

### Compatibility Guard Ideas

```text
Accept old operator inputs only as explicit aliases:
- --model-8b
- MODEL_8B
- bbq-8b
- IFM_8B
- legacy provider IDs

Fail closed when a removed input cannot be mapped safely:
- explain the replacement;
- point to migration docs;
- do not silently select a different model or path.
```

### Tests That Should Catch This Class

```text
1. Source-vs-asset manifest content parity, not only path-set parity.
2. Compatibility tests for legacy flags, env vars, served names, and provider IDs.
3. Redaction tests or scripted scans over all changed docs/examples/manifests/assets.
4. Inventory docs tests that assert issue-required row labels remain present unless the issue scope changes.
5. Promotion readiness tests proving renamed manifests still fail closed until all H200 Slurm gates pass.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Strict review of PR #393 against issue #392 and related issue #391 | The review workflow was exercised locally and produced CI-green but strict NO-GO findings for scope, acceptance criteria, asset parity, compatibility, and redaction risks. |
| HomericIntelligence/Mnemosyne | Skill capture in isolated worktree | The skill file was validated locally with `python3 scripts/validate_plugins.py`; Mnemosyne PR CI and auto-merge should be checked separately. |
