---
name: verify-audit-findings-before-acting
description: "Strict-mode repo audits routinely hallucinate critical findings (references to nonexistent files, claims of missing CI checks that already exist). Verify each finding against current filesystem state BEFORE filing issues or fixing. Use when: (1) consuming output from /repo-analyze-strict or any swarm-audit, (2) about to bulk-file remediation issues, (3) deciding which audit majors are real."
category: documentation
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [audit, code-review, fact-checking, remediation]
---

# Verify Each Audit Finding Against the Filesystem Before Acting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Catch hallucinated audit findings before they become wasted remediation work |
| **Outcome** | Saved 3 false-positive PRs in one session by verifying each finding against `ls` / `grep` |
| **Verification** | verified-local (caught 3 of 11 major findings as stale/false in a single audit run) |

## When to Use

- Receiving output from `/repo-analyze-strict`, `/repo-analyze-strict-full`, or any swarm-of-15 audit
- About to bulk-file `gh issue create` for every flagged finding
- Reviewing a "missing X" finding before adding X to the codebase
- A new auditor (model or human) makes a sweeping "you don't have Y" claim about your repo

## Verified Workflow

### Quick Reference

```bash
# For EACH audit finding, run the 30-second verify step:
ls <path-the-audit-claimed-is-missing>     # is the file really absent?
grep -rn <symbol-or-config> <path>          # is the integration really missing?
git log --all -- <path>                     # was it ever there? (helps spot a recent delete)
```

### Detailed Steps

**The pattern:** Strict-mode audit agents are instructed to "treat absence of evidence as evidence of absence." They take ~60s per section and read excerpts. They make claims like:

- "`.claude/settings.local.json` references `.claude/hooks/learn-trigger.py` (missing) — CRITICAL"
- "No `gitleaks` / `truffleHog` in CI — MAJOR"
- "`bootstrap` recipe is broken; doesn't install the package — MAJOR"

Each is a structurally plausible failure. None of them was true in the verified session.

**Mechanism of the false positives:**

1. **Hallucinated cross-reference** — the agent saw `.claude/` in `.gitignore` and inferred a `.claude/hooks/learn-trigger.py` reference must exist in `.claude/settings.local.json`. Neither file existed.
2. **Stale knowledge** — the agent's audit window covered files in batches; gitleaks v8.30.0 IS installed in `.github/workflows/_required.yml` but the security-section agent didn't search that file.
3. **Documentation reading error** — pixi.toml comments warned about `dev-install` being required, but the agent inferred this meant the `bootstrap` justfile recipe was broken. The recipe was incomplete but pixi's editable build did make the package importable for most CLIs; the audit's "imports fail" claim was wrong.

**Verification protocol (per finding, 30s budget):**

| Finding type | Verify with |
|--------------|-------------|
| "Reference to missing file X" | `ls X && grep -rln 'reference-pattern' <dir>` — if file absent AND no reference exists, finding is hallucinated |
| "No SAST/secrets-scan/dep-audit in CI" | `grep -rE 'gitleaks\|trufflehog\|detect-secrets\|pip-audit\|bandit\|codeql\|semgrep' .pre-commit-config.yaml .github/workflows/*.yml` — if any line matches, the tool IS present |
| "Function X has wrong return type" | `grep -nE '^def X' <file> && grep -nE 'return\|sys.exit' <file>` — read the actual signature + every return |
| "Bootstrap/setup is broken" | Run the bootstrap recipe in a clean env (or read it + the dependencies it triggers); don't trust audit prose |
| "Coverage gap in module Y" | `pixi run pytest tests/ --cov=hephaestus.Y --no-cov-fail` — measure real coverage, not the audit's count |

**Triage rule:** If verification shows the finding is wrong, log it but DO NOT file an issue or open a PR. Track stale-finding rate per audit run; if it exceeds 20%, escalate to question the audit methodology, not the codebase.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| File all audit findings as issues, then triage in PRs | Trust the audit; backlog will sort itself | 3 of 11 majors were stale → 3 PRs would have produced backwards "fixes" (e.g. adding gitleaks when it's already there) | Triage during audit-consume, not after issue filing |
| Re-run the audit to "verify itself" | Hope a second pass catches the hallucinations | Identical output. Strict-mode prompt + same model = same hallucinations | Audits can't fact-check themselves; you must check against the filesystem |
| Believe "CRITICAL" severity tags | Defer to the audit's own ranking | The "CRITICAL: missing hook" was hallucinated. Severity tag doesn't correlate with finding accuracy | Severity is a model's prediction, not a filesystem fact |

## Results & Parameters

**Stale-finding rate observed:** 3/11 majors in a single ProjectHephaestus audit (27%). Higher than expected. Likely range across audits: 10–30%.

**Time cost:**
- Without verification: ~10 minutes to file 11 issues + ~30 minutes per false-positive PR to discover the fix is a no-op = ~100 minutes wasted on 3 false positives.
- With verification: ~5 minutes (30s × 11 findings) = saves ~95 minutes per audit.

**Specific verification commands that caught the false positives in this session:**

```bash
# Catch #1: missing hook reference
ls .claude/settings.local.json .claude/hooks/learn-trigger.py 2>&1
# Both → "No such file or directory" → no reference, no missing file, finding is hallucinated

# Catch #2: gitleaks claim
grep -nE 'gitleaks|trufflehog|detect-secrets' .pre-commit-config.yaml .github/workflows/*.yml
# Returned multiple matches in _required.yml → gitleaks IS installed and run; finding is stale

# Catch #3: bootstrap claim — partial true, partial false
grep -A 5 'bootstrap' justfile  # showed recipe omits dev-install (real)
# but: pixi.toml [dependencies] auto-installs package as editable for most CLIs (refutes "imports fail")
```

**Pre-flight script for any strict audit:**
```bash
# Run this script after reading the audit report, BEFORE filing issues.
# Outputs: real_issues.txt, stale_findings.txt
for finding in <each major from the report>; do
  echo "Finding: $finding"
  # 30-second verify per finding type (table above)
  read -p "Real? [y/N] " yn
  if [[ "$yn" == "y" ]]; then echo "$finding" >> real_issues.txt
  else echo "$finding" >> stale_findings.txt; fi
done
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-26 strict-mode full-coverage audit (B+ 84%) | 3 of 11 majors were stale: hallucinated `.claude/hooks/learn-trigger.py` reference (S11 critical), claim of "no gitleaks in CI" (S8 major) when gitleaks v8.30.0 was already wired, partially-wrong claim that `bootstrap` recipe was broken (S13 major). Caught all 3 in under 5 minutes of `ls`/`grep` verification before filing issues. |
