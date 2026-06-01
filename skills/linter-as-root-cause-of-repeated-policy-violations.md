---
name: linter-as-root-cause-of-repeated-policy-violations
description: "When two or more separate documents/skills/configs violate the same stated policy in the same way, the linter/validator that enforces that policy is the FIRST suspect — fix the linter before fixing the dependent files, or the new fixes will fail CI and downstream files will re-introduce the violation. Use when: (1) an audit flags the same policy violation in multiple files, (2) you are tempted to open N parallel PRs to fix N violating files, (3) a CLAUDE.md/CONTRIBUTING.md rule is repeatedly violated despite contributors knowing the rule, (4) a wrong-direction validator silently rejects the correct fix and accepts the wrong one."
category: debugging
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [linter, validator, policy-enforcement, wrong-direction-rule, root-cause, audit-remediation, repeated-violations, ci-policy, doc-policy, meta-debugging]
---

# Linter As Root Cause Of Repeated Policy Violations

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Diagnose the case where multiple unrelated documents/skills/configs violate the same stated policy in the same way, and avoid the trap of fixing the dependent files first |
| **Outcome** | Verified-CI: 4 PRs landed in correct order (linter fix first, then dependent docs) |
| **Verification** | verified-ci |
| **Source** | ProjectHephaestus 2026-05-31 strict audit: `--rebase` vs `--squash` merge-strategy policy |

## When to Use

- An audit (strict-mode, repo-analyze-strict, manual review) flags the SAME policy violation in 2+ separate files.
- You are tempted to open N parallel PRs to fix N violating files independently.
- A CLAUDE.md, CONTRIBUTING.md, or README policy is repeatedly violated despite contributors clearly knowing the rule.
- Recently-added documentation re-introduces a violation that you "already fixed" in older files — strong signal that the linter is wrong-direction.
- A PR that "fixes" a policy violation fails CI on a rule whose error message references the EXACT change you just made.
- The validator's rule definition has not been read against the META source of the policy (CLAUDE.md / CONTRIBUTING.md) in the current diagnostic session.
- You are running an audit-driven remediation epic and Phase 1 triage shows multiple files in different subdirectories all violating Rule X.

## Verified Workflow

### Quick Reference

```bash
# 1. When you see ≥2 files violating Rule X in an audit:
#    PAUSE. Do not open per-file fix PRs yet.

# 2. Find the linter that enforces Rule X
grep -rn "<rule-keyword>" hephaestus/validation/ tests/unit/validation/ scripts/audit_*.py
# Or whichever validation module the repo uses:
grep -rn "<rule-keyword>" <validation-module-path>/ <validation-tests-path>/

# 3. Find the META source of the policy
grep -n "<rule-keyword>" CLAUDE.md CONTRIBUTING.md README.md docs/

# 4. Diff the linter's assertion against the META source
#    If they DIFFER → the linter is the root cause.

# 5. Fix the linter FIRST (PR1), flip the test assertions, land it.
# 6. Fix the dependent docs (PR2..N) AFTER the linter PR has merged.
```

### Detailed Steps

#### Step 1 — Observe the pattern: "same rule violated in N separate files"

After running an audit (`/hephaestus:repo-analyze-strict`, `audit_doc_examples.py`, etc.), tally each finding by rule ID:

```bash
# If audit output is JSON:
audit_output.json | jq -r '.findings[].rule' | sort | uniq -c | sort -rn

# If audit output is text:
grep -oP 'Rule:\s*\K\S+' audit_report.md | sort | uniq -c | sort -rn
```

If any rule appears in ≥2 separate files in unrelated directories, treat the linter as a suspect. The threshold is the file-count, not the line-count — two violations in one file are likely a localized bug; two violations in two unrelated files are likely a systemic bug.

#### Step 2 — Locate the linter's rule definition

The linter that flagged the violations is the one whose assertion encodes the policy. Find it:

```bash
# Most repos use one of these locations:
grep -rn "<rule-keyword>" \
    src/<module>/validation/ \
    tests/unit/<module>/validation/ \
    scripts/audit_*.py \
    scripts/lint_*.py \
    .github/scripts/ \
    pre_commit_hooks/

# In ProjectHephaestus specifically:
grep -rn "<rule-keyword>" hephaestus/validation/ tests/unit/validation/
```

Read the rule's full definition: pattern, accept-list, reject-list, error message. If the rule has both a "good pattern" and a "bad pattern" registered (e.g., `POLICY_RULES["merge-strategy"]["good"] = "--rebase"`, `["bad"] = "--squash"`), READ BOTH SIDES.

#### Step 3 — Locate the META source of the policy

The META source is the single document that the rule purports to enforce. Common locations:

| Repo Convention | META Source |
|---|---|
| Codebase-level | `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `docs/POLICIES.md` |
| Repo-policy-level | GitHub branch protection rules, `.github/CODEOWNERS`, ruleset JSON |
| Org-level | Org-wide CLAUDE.md, shared style guide repo |

Read the META source's statement of the rule verbatim.

#### Step 4 — Diff the linter's assertion vs the META source

Now perform the diff. There are three outcomes:

| Linter says | META source says | Verdict |
|---|---|---|
| Accept X, reject Y | Require X, prohibit Y | Linter is correct. The violations are real bugs in the dependent files. Proceed with normal per-file fixes. |
| Accept Y, reject X | Require X, prohibit Y | **LINTER IS WRONG-DIRECTION.** Fix linter FIRST. |
| No assertion present | Require X, prohibit Y | Linter has a gap. Add the assertion, then fix dependent files. |

If the linter is wrong-direction, the dependent files were written TO COMPLY WITH the wrong linter. They are not independently buggy — they are downstream consumers of a wrong contract.

#### Step 5 — Re-sequence the fix as: linter PR FIRST, dependent PRs SECOND

Reorder your planned PRs:

```text
WRONG ORDER (will fail CI):
  PR1: fix skill A      ← CI will reject because linter rejects the new pattern
  PR2: fix skill B      ← CI will reject for the same reason
  PR3: fix doc C        ← CI will reject for the same reason

CORRECT ORDER:
  PR1: fix linter (validator + test assertions)  ← lands, unblocks the rest
  PR2: fix skill A      ← now CI accepts the correct pattern
  PR3: fix skill B      ← CI accepts
  PR4: fix doc C        ← CI accepts
```

When fixing the linter, you MUST flip the test assertions in lock-step. The validator's own test suite is currently asserting the wrong direction. Treat the linter source + linter tests as a single atomic change.

#### Step 6 — Verify each fix PR with the new linter

After the linter PR merges, rebase the dependent PRs on top of main and confirm each one's CI passes. Do NOT batch-merge the dependent PRs without re-running CI on each — if the linter fix was incomplete, the dependent fixes may still fail.

#### Step 7 — Add a regression test that exercises BOTH directions

The validator's tests previously asserted "accept Y, reject X." Now they must assert "accept X, reject Y." Add at least one explicit test for each direction so that future drift is caught immediately:

```python
def test_accepts_correct_pattern_X():
    """Rule must accept the META-source-required pattern."""
    assert validator.is_valid("gh pr merge --auto --squash")

def test_rejects_wrong_pattern_Y():
    """Rule must reject the META-source-prohibited pattern."""
    assert not validator.is_valid("gh pr merge --auto --rebase")
```

A single direction-test is not enough — a future contributor with the same wrong-direction mental model could flip the assertion direction again. Pair tests prevent silent drift.

#### Step 8 — Update the META source if BOTH are wrong

In rare cases, BOTH the linter AND the META source are wrong (e.g., CLAUDE.md says `--rebase` but GitHub branch protection actually disables rebase merging). The ultimate source of truth is the deployed configuration, not the documentation. Confirm against:

- `gh api repos/<owner>/<repo>/branches/<branch>/protection` for branch protection
- The actual CI behavior (run a test PR and observe)
- Org-wide policy if it exists

If META is wrong too, fix META FIRST, then linter, then dependent docs (3 PRs in dependency order).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Open N parallel PRs to fix N violating skill files | 2 separate PRs to fix `skills/myrmidon-swarm/SKILL.md` and `skills/learn/SKILL.md` for `gh pr merge --auto --rebase` → `--squash` | The linter at `hephaestus/validation/doc_policy.py` was enforcing the WRONG direction: it REQUIRED `--rebase` and REJECTED `--squash`. New PRs would fail CI because the linter rejects the correct pattern | When ≥2 docs violate the same rule, the linter is the FIRST suspect. Read its rule definition before opening per-file fix PRs. |
| Trust the META source (CLAUDE.md) but skip reading the linter | Assumed CLAUDE.md said `--squash` and that was sufficient ground truth to fix the docs | The skills were written to comply with the LINTER, not CLAUDE.md. The linter was authoritative in practice because CI gates on it | The linter's actual enforcement IS the de-facto policy. Always confirm linter and META source agree before fixing dependents |
| Fix linter and skills in the same PR | Considered bundling all corrections into one mega-PR | Linter and skill changes have different test surfaces — bundling makes CI feedback ambiguous if either side fails | Keep linter fix as its own atomic PR; dependent doc fixes land afterward on top of the correct linter |
| Skip flipping the linter's test assertions | Initially planned to update only the validator code, not its tests | Validator tests would have continued asserting "reject `--squash`" — CI would fail on the linter PR itself | Linter source + linter tests must be flipped together as a single atomic change |
| Single-direction regression test only | Wrote a test that only asserted "accepts `--squash`" | A future agent with the same wrong-direction mental model could re-flip the assertion to "rejects `--squash`" and ship it | Pair tests: assert correct pattern accepted AND wrong pattern rejected. Both directions prevent silent drift |

## Results & Parameters

### Diagnostic checklist (run BEFORE opening per-file fix PRs)

```bash
# 1. Count distinct files violating the same rule
audit_output | grep "Rule: <rule-id>" | awk '{print $2}' | sort -u | wc -l
# If >= 2 → linter is a suspect

# 2. Find the linter
grep -rn "<rule-keyword>" hephaestus/validation/ tests/unit/validation/

# 3. Find the META source
grep -n "<rule-keyword>" CLAUDE.md CONTRIBUTING.md

# 4. Diff the linter's good/bad pattern against META
#    (read both and compare manually)

# 5. If they disagree → fix linter PR FIRST
```

### Re-sequencing template

```text
Originally planned:
  PR1: fix file_A   → MAJOR audit finding
  PR2: fix file_B   → MAJOR audit finding

Re-sequenced after linter check:
  PR1: fix linter (validator + flipped test assertions)
  PR2: fix file_A (depends on PR1 landing)
  PR3: fix file_B (depends on PR1 landing)
  PR4: fix META source (only if META was also wrong)
```

### Worked example — ProjectHephaestus 2026-05-31

| PR | Target | Status |
|---|---|---|
| #863 | `hephaestus/validation/doc_policy.py` — `POLICY_RULES` flipped from `--rebase` to `--squash`; rejected `--rebase`/`--merge` | MERGED first (root-cause fix) |
| #865 | `README.md` + `CONTRIBUTING.md` — added explicit `--squash` to all `gh pr merge` examples | MERGED after #863 |
| #866 | `skills/myrmidon-swarm/SKILL.md:318` — `--rebase` → `--squash` | MERGED after #863 |
| #867 | `skills/learn/SKILL.md:422` — `--rebase` → `--squash` | MERGED after #863 |

All 4 PRs merged clean. Had PRs #866/#867 been opened first, they would have failed CI because the linter would have rejected the new `--squash` instructions.

### Pair-direction regression test template

```python
class TestPolicyRule:
    """Verify both directions for <rule-id> to prevent wrong-direction drift."""

    def test_accepts_required_pattern(self):
        """Linter must accept the META-source-required pattern."""
        assert is_compliant("<required-pattern>"), (
            "Linter rejected the META-source-required pattern. "
            "Check that POLICY_RULES['<rule-id>'] enforces the correct direction."
        )

    def test_rejects_prohibited_pattern(self):
        """Linter must reject the META-source-prohibited pattern."""
        assert not is_compliant("<prohibited-pattern>"), (
            "Linter accepted the META-source-prohibited pattern. "
            "Check that POLICY_RULES['<rule-id>'] enforces the correct direction."
        )
```

### When to escalate to a META-source audit

If you discover that the linter was wrong-direction AND the META source (CLAUDE.md, CONTRIBUTING.md) was also internally inconsistent (e.g., one place says `--squash` and another says `--rebase`), file a follow-up issue to audit ALL policy statements in the META source. Wrong-direction linters are often downstream symptoms of META-source drift.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | 2026-05-31 strict audit caught 2 skill files violating `--squash`-only merge policy; root-cause was `hephaestus/validation/doc_policy.py` enforcing the opposite direction. 4 PRs landed in dependency order. | PRs #863, #865, #866, #867 |

## References

- Related: [[doc-audit-policy-violations]] — standard audit workflow that this skill amends with the linter-as-root-cause meta-pattern.
- Related: [[audit-driven-remediation-workflow]] — Phase 1 triage now must include "is the linter wrong-direction?" check.
- Related: [[verify-audit-findings-before-acting]] — verification step generalizes to "verify the linter too, not just the findings."
