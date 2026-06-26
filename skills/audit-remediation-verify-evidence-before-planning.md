---
name: audit-remediation-verify-evidence-before-planning
description: "Before planning a fix for an audit/remediation issue, verify the audit's cited evidence (file:line) against the live tree — audit findings go stale once the target is independently remediated, and an audit that names SEVERAL targets can have a SUBSET already fixed. Re-read EVERY cited file:line before planning, fix ONLY the issue-named targets (a repo-wide survey will surface more non-compliant siblings — note them out-of-scope, do not expand the PR), do not invent a unit test for a doc/UX field that has no test contract, and close already-remediated security/documentation policy issues only after rechecking the actual implementation branch. Use when: (1) planning a fix for an audit-filed issue with file:line evidence, (2) the issue spans multiple repos or submodules, (3) the issue recommends doc/field-name/frontmatter/security-policy changes that may already be done, (4) the audit names multiple targets and any subset may already be remediated, (5) the intended outcome may be a no-op issue close rather than a policy rewrite."
category: architecture
date: 2026-06-26
version: "1.3.0"
user-invocable: false
verification: verified-local
history: audit-remediation-verify-evidence-before-planning.history
tags: []
---

# Audit Remediation: Verify Evidence Before Planning

**History:** [changelog](./audit-remediation-verify-evidence-before-planning.history)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Plan a fix for a cross-repo audit-remediation GitHub issue without trusting stale audit evidence |
| **Outcome** | Discovered the audit was stale — target submodule already remediated; scoped the plan to only the genuinely-actionable owned-repo work + a drift guard |
| **Verification** | verified-local |

> **Verification note:** The evidence-verification steps below (grep against the live tree, confirming canonical names in the Pydantic source of truth) were genuinely RUN this session and confirmed the target docs were already remediated — that is what `verified-local` attests to. The downstream implementation (the architecture.md section + the drift-guard script wired into `just ci`) was **planned only**, not executed or CI-validated. Do not read this as `verified-ci`.
>
> **v1.1.0 note:** The canonical mapping (`subject`/`assign_to`/`blocked_by` model fields serialized as `subject`/`assigneeAgentId`/`blockedBy`) was verified this session by reading BOTH `models.py` AND `agamemnon_client.py` against the live tree. The corresponding architecture.md table edit itself was **planned only**, not executed or CI-validated.
>
> **v1.2.0 note (single-repo, multi-target frontmatter case):** Planning ProjectHephaestus issue #1553 ("Skills missing `argument-hint` frontmatter field"), which named TWO targets — `skills/brainstorm/SKILL.md` and `skills/python-repo-modernization/SKILL.md`. Reading `skills/brainstorm/SKILL.md:1-6` showed `argument-hint: <idea or feature description>` **already present at line 4** — the audit snapshot (2026-06-16) was stale for that target; only `python-repo-modernization` genuinely lacked the field. Re-reading every cited file:line before planning (not trusting the issue text) is what `verified-local` attests to here; the PR/CI for #1553 had **not landed at capture time** — state honestly, this is `verified-local`, not `verified-ci`. A repo-wide `awk` survey over all `skills/*/SKILL.md` both confirmed `brainstorm` was already compliant AND surfaced ~10 OTHER skills missing the field — deliberately EXCLUDED to respect one-issue-per-PR scope. The field is unenforced: `grep -rl "argument-hint" tests/` returned nothing and `ls tests/unit/ | grep -i skill` was empty, so verification is a YAML-frontmatter parse (`yaml.safe_load_all`), NOT a unit test — do not invent a test where no contract exists.
>
> **v1.3.0 note (already-remediated security policy case):** Planning ProjectHephaestus issue #1421 concluded the issue should be verified and closed as already remediated because the live tree reportedly had a root `SECURITY.md` with supported versions, private vulnerability reporting, a response timeline, and security scope. This capture records the planning/review lesson, not a fresh re-run of that ProjectHephaestus evidence. Treat the issue body, audit output, prior plan text, claimed line ranges, exact-reference search results, and branch state as assumptions until the implementer re-runs them on the actual implementation branch. The highest-risk mistake is rewriting or recreating a security policy that already exists on the branch under implementation.

## When to Use

- Planning a fix for an issue filed by an automated/ecosystem audit that cites specific `file:line` evidence.
- The issue spans multiple repos, especially when some are git submodules owned by other repos.
- The recommendation is a doc/field-name/role-description change that another team may have already fixed.
- Any "documentation drift" or "X docs show deprecated Y" issue.
- Authoring a doc/table that CLAIMS canonical names or values — every cell must be code-traceable.
- The audit names MULTIPLE targets (e.g. "these 2 skills are missing field Z"). Any subset may already be remediated — verify EACH named target independently; never plan for all of them on the strength of the issue title.
- The recommendation is a config/frontmatter/UX field change (e.g. a Claude Code plugin `argument-hint`) that may be unenforced — confirm whether a test/validator contract exists before scoping any verification step.
- The issue is a stale documentation or security-policy audit where the correct implementation may be to verify the branch and close the issue with evidence, not to rewrite the policy file.
- A reviewer is checking a no-op remediation plan and needs to challenge whether the planner re-ran the line-range, path, reference-search, guard-coverage, and branch-state claims.

**Related:** `agent-config-validation-and-integrity` covers HOW to validate YAML frontmatter structurally (`yaml.safe_load_all`, required fields). This skill is distinct: it is about VERIFYING AUDIT FINDINGS before planning — re-reading every cited target on disk, detecting stale/partially-fixed multi-target audits, and resisting scope creep. Reach for that skill once you know what to validate; reach for this one to decide whether the audit's claim is even still true.

## Verified Workflow

The evidence-verification phase (steps 1-3) was actually executed against the live tree and is the basis for the `verified-local` claim. Steps 4-6 (scoping and the drift guard) were the resulting plan, which was not itself executed in CI.

1. **Read the issue's cited evidence FIRST and diff it against the live tree.** For every `file:line` the issue names, open the live file at those coordinates and confirm the claimed text is actually there. Do not assume the evidence is current — an audit captures a snapshot at filing time, and the target may have moved on.
2. **Identify the source of truth and confirm canonical values there.** For a field-name/schema issue, the source of truth is the code (Pydantic models / enums / REST contract), not the prose. Confirm the canonical values in code, and treat docs as the thing aligned TO code, never the reverse.
3. **Distinguish real hits from false positives — grep, then eyeball each in context.** A token like `title:` inside a generated JSON-Schema is a display label, and a method name like `test_unknown_depends_on_raises` is describing behavior — neither is a documented schema field. A raw grep count is not a violation count; inspect every hit.
4. **Scope by ownership.** Do NOT edit files inside git submodules from the meta-repo — they are owned by their own repo and must be PR'd there (or a referencing issue filed). One PR per owned repo.
5. **If the cited target is already remediated, say so explicitly.** State it in the plan and in the PR body, then pivot the plan to (a) the still-actionable owned-repo recommendation and (b) a drift-prevention guard so the deprecated form cannot silently return.
6. **Match the repo's EXISTING check pattern for the guard.** Here that meant a bash script under `scripts/` plus a `just` recipe wired into `just ci` — not a new framework. A meta-repo with "no application code" should not get a pytest harness just for a doc check.
7. **When you author a canonical-names/values table, read EACH cell from the source of truth, and distinguish the model/field layer from the serialization/wire layer** (e.g. Pydantic `assign_to` vs JSON `assigneeAgentId` in the REST client). Never invent a "deprecated/legacy" variant for a field that is current. A drift guard that only matches the OLD tokens will not catch a wrong NEW canonical name — so add a positive check (table cell == code) and a negative check (guessed-wrong name is absent).
8. **Verify EACH named target separately when the audit names several.** An audit that says "targets A and B are missing field Z" is two independent claims — open A and B at their cited coordinates and confirm Z is absent in EACH. A partially-stale audit (A already fixed, B genuinely missing) is the norm, not the exception; planning a no-op edit on the already-fixed target earns a reviewer NOGO.
9. **Run a repo-wide survey to learn the convention AND the true scope — then fix ONLY the issue-named targets.** A one-liner (`awk`/`grep` over the whole population) both confirms which named targets are genuinely non-compliant and reveals the convention to follow (field position, quoting). It will usually surface MORE non-compliant siblings than the issue named. Resist fixing them: note them explicitly as out-of-scope (they belong to the broader audit bundle), keep the PR to one issue's targets.
10. **Don't invent a test where no contract exists.** For a pure doc/UX/frontmatter field, check whether any test or validator actually asserts it (`grep -rl "<field>" tests/`, `ls tests/unit/ | grep -i <area>`). If nothing does, the verification is a structural parse (`yaml.safe_load_all` over the frontmatter), not a new unit test. Adding a bespoke test for an unenforced field is scope creep and a false-rigor signal.
11. **Derive the field VALUE from the artifact's actual behavior, and place it per the dominant convention.** For `argument-hint`, read what the skill operates on (it modernizes a target repo -> `<path to Python repo to modernize>`) rather than copying a generic placeholder, and position it where sibling skills put it (immediately after `description`) confirmed by reading siblings, not by guessing.
12. **For security-policy no-op remediation, verify the actual implementation branch before closing.** Do not rely on the audited live tree, a prior plan, or remembered line numbers. Check the branch you will PR/close from for the root policy file, required policy elements, absence of stale references, and existing drift guards. If the implementation branch differs from the verified live tree, reconcile that branch first; otherwise close with evidence and no policy rewrite.
13. **Review existing drift guards before adding new ones.** Confirm the repo already has checks for the exact drift class (for example, supported-version consistency, no hardcoded policy dates, pre-commit wiring, and unit tests for those scripts). If the guards exist and cover the claim, do not add duplicate scripts; if they do not, scope a guard in the repo's established pattern.
14. **Reviewer checklist for already-remediated audit plans:** require the actual commands or file reads used to prove the policy exists; challenge un-rerun line ranges; reject unnecessary docs churn; verify no unrelated docs references need editing; and confirm tests/guards cover the claimed drift instead of merely existing nearby.

### Quick Reference

```bash
# 1. Re-verify audit evidence against live tree (expect: stale audit => no hits)
grep -nE '^[[:space:]]*-?[[:space:]]*(title|depends_on):' <cited-docs>
# 2. Confirm canonical names in the source of truth (Pydantic model)
grep -nE 'subject:|blocked_by:' src/<pkg>/models.py
# 3. Check ownership before editing — submodules are off-limits from the meta-repo
git submodule status
# 4. When authoring a canonical table: verify BOTH layers cell-by-cell
#    model/field layer (Pydantic / YAML)
grep -nE 'assign_to|subject|blocked_by' src/<pkg>/models.py
#    serialization/wire layer (JSON keys in the REST client) — these can DIFFER
grep -nE 'assigneeAgentId|blockedBy|"subject"' src/<pkg>/<rest_client>.py
# 5. Negative check — the guessed-wrong canonical name must be ABSENT from the doc
! grep -nE '<guessed-wrong-name>' <doc>   # e.g. ! grep -nE 'assignee_agent_id' docs/architecture.md

# --- multi-target frontmatter audit (e.g. ProjectHephaestus #1553 argument-hint) ---
# 6. Verify EACH named target's frontmatter separately (expect: a subset already has it)
sed -n '1,8p' skills/brainstorm/SKILL.md                 # already has argument-hint => STALE claim
sed -n '1,8p' skills/python-repo-modernization/SKILL.md  # genuinely missing => actionable
# 7. Survey the WHOLE population for convention + true scope (fix only the named targets)
for f in skills/*/SKILL.md; do printf '%s: ' "$f"; awk -F': ' '/^argument-hint:/{print $2; found=1} END{if(!found)print "MISSING"}' "$f"; done
# 8. Confirm there is NO test contract before scoping a test (expect: no output)
grep -rl "argument-hint" tests/ ; ls tests/unit/ | grep -i skill
# 9. Verification IS a frontmatter parse, not a unit test
python3 -c "import yaml,sys; list(yaml.safe_load_all(open(sys.argv[1]).read().split('---')[1]))" skills/python-repo-modernization/SKILL.md

# --- security/documentation policy audit that may already be remediated ---
# 10. Verify the root policy file on the ACTUAL branch under implementation
test -f SECURITY.md && nl -ba SECURITY.md | sed -n '1,80p'
# Example required elements: supported versions, private reporting path, response timeline, scope.
grep -nEi 'supported versions|report|vulnerabil|timeline|scope|private' SECURITY.md
# 11. Re-run exact-reference searches instead of trusting prior plan text
rg -n 'SECURITY\.md|security policy|vulnerability|supported versions' CLAUDE.md docs .github README.md 2>/dev/null || true
# 12. Confirm existing guard coverage before proposing another guard
ls scripts/check_security_* tests/unit/scripts 2>/dev/null
rg -n 'check_security_version_consistency|check_security_policy_no_hardcoded_date|security' .pre-commit-config.yaml pyproject.toml .github/workflows 2>/dev/null || true
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusting the audit's file:line evidence as current | Issue cited `CLAUDE.md:55-58` / `README.md:62-69` as showing `title`/`depends_on` | The submodule had already been remediated independently; those lines now use `subject`/`blocked_by` | Always re-read cited evidence against the live tree before planning |
| Grepping for `title`/`depends_on` and treating every hit as a violation | Raw grep flagged JSON-Schema `"title":` labels and a `test_unknown_depends_on_raises` method name | These are not documented workflow fields — false positives | Anchor the pattern to field-key syntax and eyeball each hit in context |
| Assuming the meta-repo can fix the submodule's docs in this PR | Planned to edit `provisioning/ProjectTelemachy` docs from Odysseus | Submodules are owned by their own repos; editing their working tree from the meta-repo is wrong scope | Scope edits by ownership; PR the owning repo or file a referencing issue |
| Filling a canonical-names table from memory/issue text | Wrote canonical=`assignee_agent_id`, deprecated=`assigned_to (legacy)` | Source of truth has `assign_to` (model) serialized as `assigneeAgentId`; the guessed names existed nowhere | Read every table cell verbatim from code before writing it |
| Assuming the model field name equals the wire/JSON key | Conflated Pydantic `assign_to` with the REST payload key | They differ: the client maps `spec.assign_to` -> `assigneeAgentId` | Always check the serialization layer (REST client) separately from the model |
| Trusting a drift guard to catch a wrong canonical name | Guard only greps deprecated `title`/`depends_on` | A fabricated canonical name passes the guard silently | Verify the canonical table with a positive (cell==code) AND negative (guessed-wrong absent) check, not just the deprecated-token guard |
| Trusting a multi-target audit issue verbatim | #1553 named `brainstorm` + `python-repo-modernization` as missing `argument-hint`; planned to add the field to both | `skills/brainstorm/SKILL.md:4` ALREADY had `argument-hint` — the audit snapshot (2026-06-16) was stale for that target; the edit would be a no-op (or a confusing "add field that already exists") | Re-read EVERY cited file:line before planning; verify each named target independently — a subset is usually already remediated |
| Expanding the fix to all skills missing the field | A repo-wide `awk` survey surfaced ~10 OTHER skills also missing `argument-hint`; tempting to fix them all in one PR | Scope creep — violates one-issue-per-PR; those skills belong to the broader audit bundle, not #1553 | Fix ONLY the issue-named targets; note the additional non-compliant siblings as explicitly out-of-scope |
| Inventing a unit test for the frontmatter field | Considered adding a `tests/unit/` test asserting `argument-hint` is present | No test contract exists: `grep -rl "argument-hint" tests/` is empty and there are no skill tests under `tests/unit/`; the field is unenforced | Verification is a YAML-frontmatter parse (`yaml.safe_load_all`), not a unit test — don't add false-rigor tests for an unenforced doc/UX field |
| Copying a generic placeholder for the field VALUE | Almost used a vague `<argument>` hint | The value must describe what the artifact actually operates on, positioned per the dominant convention | Derive the value from behavior (`<path to Python repo to modernize>`), place it after `description` as confirmed by reading sibling skills |
| Treating the audited live tree as the implementation branch | Plan concluded root `SECURITY.md` already satisfied the issue but did not require rechecking the branch that would close it | A branch can differ from the audited live tree; stale branch state is the highest-risk assumption in no-op remediation | Re-confirm the policy file and required elements on the actual branch before closing or opening a no-op PR |
| Rewriting an already-compliant security policy | Planned to recreate or normalize `SECURITY.md` content because an audit issue existed | Churn risks weakening precise reporting/timeline/scope language and distracts reviewers from the real question: is the issue already satisfied? | If the branch already has the required policy elements, preserve the file and close with evidence |
| Trusting exact line ranges from a prior plan | Claimed supported versions/reporting/timeline/scope line ranges without re-running `nl -ba SECURITY.md` | Line ranges drift after edits and are not evidence unless generated from the current checkout | Regenerate line-number evidence immediately before using it in a plan, review, PR, or close comment |
| Assuming "guards exist" means "this drift is covered" | Pointed to security scripts, pre-commit wiring, tests, Bandit config, lint tasks, and security workflow as generic reassurance | Some tooling is adjacent security context, not a guard for the policy requirement being audited | Map each guard to the exact drift claim it prevents; separate policy-drift checks from general security scanning |

## Results & Parameters

- **Canonical field names — TWO layers (verified by reading `models.py` AND `agamemnon_client.py` this session):**
  - Model / YAML field (Pydantic source of truth): `subject` (models.py:38), `assign_to` (models.py:40), `blocked_by` (models.py:41).
  - JSON wire key (REST client serialization): `subject` (agamemnon_client.py:207), `assigneeAgentId` (agamemnon_client.py:211,214), `blockedBy` (agamemnon_client.py:216).
  - The model field `assign_to` is serialized as `assigneeAgentId`; **the two layers differ and must be read separately**. There is NO `assignee_agent_id` field anywhere.
  - Deprecated forms (the only ones that exist): `title` (-> `subject`) and `depends_on` (-> `blocked_by`). There is NO `assigned_to (legacy)` deprecated form — that was a fabricated guess caught by a reviewer.
- **Drift-guard pattern:** first-party-only file list via
  `git ls-files -- '*.md' | awk '!/^(infrastructure|control|provisioning|ci-cd|research|shared|testing)\//'`;
  field-key regex `^[[:space:]]*-?[[:space:]]*(title|depends_on):`;
  exit `0` clean / `1` drift / `2` usage; wire into `just ci`.
- **Submodule dirs in this ecosystem to exclude from first-party scans:** `infrastructure/` `control/` `provisioning/` `ci-cd/` `research/` `shared/` `testing/`.
- **ProjectHephaestus #1553 (`argument-hint` frontmatter, v1.2.0 case):**
  - Named targets: `skills/brainstorm/SKILL.md` (ALREADY compliant — `argument-hint: <idea or feature description>` at line 4; stale audit) and `skills/python-repo-modernization/SKILL.md` (genuinely missing — the only actionable target).
  - Convention (confirmed by reading siblings): `argument-hint` placed immediately after `description`; value describes what the skill operates on. For `python-repo-modernization`: `<path to Python repo to modernize>`.
  - Enforcement: NONE. `grep -rl "argument-hint" tests/` -> no matches; no skill tests under `tests/unit/`. Verification = structural YAML-frontmatter parse (`yaml.safe_load_all`), not a unit test. `argument-hint` is optional/advisory in the Claude Code plugin format (inferred from the absence of any validator, not confirmed against upstream plugin-spec docs).
  - Out-of-scope (deliberately NOT fixed in #1553): ~10 other `skills/*/SKILL.md` also missing `argument-hint`, surfaced by the survey — they belong to the broader audit bundle (split from #1518), one issue per PR.
  - Provenance taken at face value (low risk): the audit timestamp (2026-06-16) and the split-from-#1518 origin.
- **Security policy already-remediated planning pattern (v1.3.0 case):**
  - Objective: verify and close a stale security-policy audit issue as already remediated when the implementation branch's root `SECURITY.md` already contains all required policy elements.
  - Required branch-local evidence to regenerate: supported versions table, private vulnerability reporting instructions, response timeline, and policy scope. In the captured ProjectHephaestus plan, these were cited as `SECURITY.md` lines 3-12, 14-24, 25-26, and 28-43 respectively; those line ranges are examples to re-run, not durable facts.
  - Reference-search evidence to regenerate: exact searches for stale `SECURITY.md` or security-policy references in `CLAUDE.md`, docs, workflow docs, and other repo surfaces. A prior plan said no `CLAUDE.md` or docs references existed; reviewers should require the command output from the current checkout.
  - Existing guard context to inspect before adding anything: `scripts/check_security_version_consistency.py`, `scripts/check_security_policy_no_hardcoded_date.py`, pre-commit wiring, and tests under `tests/unit/scripts`. General security context such as Bandit configuration in `pyproject.toml`, pixi lint tasks, and `.github/workflows/security.yml` should be reported separately from policy-drift guards.
  - Correct no-op outcome: if the actual branch matches the verified live tree, do not recreate, rewrite, or restyle `SECURITY.md`; close the issue with regenerated evidence. If the branch differs, reconcile only the missing requirement and keep existing wording where it already satisfies the audit.
