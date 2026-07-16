---
name: scan-vulnerabilities
description: "Detect and gate code or dependency vulnerabilities. Use when: (1) auditing source or dependencies, (2) enforcing Grype findings in CI, (3) allowing a temporary vulnerability exception without creating a broad permanent suppression."
category: tooling
date: 2026-07-15
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: scan-vulnerabilities.history
tags:
  - vulnerability-scanning
  - grype
  - syft
  - sca
  - exceptions
  - ci-policy
---

# Scan Vulnerabilities

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-15 |
| **Objective** | Scan source and dependency inventories, fail closed on actionable findings, and govern unavoidable exceptions narrowly. |
| **Outcome** | Operational: Athena PR #14 passed required CI with a locked Grype scan over a native Syft inventory and a narrowly approved, expiring exception. |
| **Verification** | verified-ci |
| **History** | [changelog](./scan-vulnerabilities.history) |

## When to Use

- Auditing source code for unsafe patterns or known dependency CVEs.
- Adding a required software-composition-analysis gate to CI.
- Scanning a prebuilt Syft SPDX inventory with Grype instead of rescanning a different input.
- A fixable High or Critical finding must block a pull request.
- A vendor has no usable fix and a temporary exception is unavoidable.

## Verified Workflow

### Quick Reference

```bash
# Produce the inventory once, then make the policy scanner consume that exact evidence.
syft scan <authoritative-input> -o spdx-json=build.spdx.json
grype sbom:build.spdx.json -o json > grype-report.json

# Preserve the complete report even when policy rejects a finding.
# The policy command should parse grype-report.json and exit nonzero after writing it.
python3 scripts/enforce_vulnerability_policy.py grype-report.json exceptions.yaml
```

### Detailed Steps

1. Lock the scanner, inventory generator, and build environment versions. A floating scanner or
   database makes a green result difficult to reproduce.
2. Generate one authoritative dependency inventory and feed that exact SBOM to the vulnerability
   scanner. Do not independently rescan the filesystem and assume the evidence sets are equal.
3. Retain the full machine-readable scanner report on both pass and failure. Enforcement should
   happen after report creation, and artifact retention should use an unconditional workflow step.
4. Fail closed on the repository's declared threshold. For Athena, a High or Critical finding is
   actionable only when the scanner reports a usable fixed version.
5. Treat exceptions as exact records, not free-form ignore strings. Require the vulnerability ID,
   package name, affected version, severity, rationale, approving identity, approval date, expiry
   date, and a durable issue URL.
6. Reject expired exceptions and records whose package/version/severity do not exactly match the
   finding. Keep exception parsing and matching covered by positive and negative tests.
7. Run the real scan in required CI. Unit tests for parsers do not prove that the locked tools,
   database, inventory, and workflow wiring operate end to end.

Example exception schema:

```yaml
exceptions:
  - vulnerability: CVE-YYYY-NNNN
    package: exact-package-name
    version: 1.2.3
    severity: High
    rationale: No usable fixed version is available; compensating control documented in issue.
    approved_by: github-user-or-team
    approved_on: 2026-07-15
    expires_on: 2026-08-14
    issue: https://github.com/OWNER/REPO/issues/NN
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Rescanned the repository instead of consuming the generated SBOM | The policy scan independently discovered dependencies from the workspace | The enforcement evidence could differ from the SBOM published with the release | Generate once and scan the exact retained inventory with `grype sbom:<path>`. |
| Used a broad CVE ignore | A vulnerability ID alone suppressed every matching package and version | The exception silently covered future or unrelated findings | Match the full finding tuple and require approval, rationale, issue, and expiry metadata. |
| Uploaded the report only after a successful scan | The scanner's nonzero exit skipped the later artifact step | The report disappeared precisely when investigation was needed | Write the report first and retain it with an unconditional artifact step. |
| Treated any listed fixed version as actionable | The scanner reported a fix that was not available for the deployed release line | CI demanded an impossible upgrade | Encode the repository's usable-fix rule explicitly and test the boundary. |

## Results & Parameters

| Parameter | Verified value |
| --------- | -------------- |
| Inventory | Native Syft SPDX 2.3 document |
| Scanner | Locked Grype environment consuming `sbom:<path>` |
| Athena threshold | Fixable High or Critical findings fail required CI |
| Exception matching | Exact vulnerability, package, version, and severity tuple |
| Exception governance | Rationale, approver, approval date, expiry, and durable issue required |
| Evidence retention | Full JSON report retained on pass and failure |
| Verification | Athena PR #14, required dependency-scan and aggregate gate passed at commit `7c9ac8356ed0828787ceb303b82cf20048e64db5` |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| Athena | Issue #10 / PR #14 supply-chain enforcement | Locked Syft/Grype execution, exact exception validation, negative policy tests, and required CI all passed. |
