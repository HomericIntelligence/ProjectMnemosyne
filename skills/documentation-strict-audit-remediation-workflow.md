---
name: documentation-strict-audit-remediation-workflow
description: "Workflow for running strict repo audits and fixing documentation findings. Use when: (1) performing comprehensive repository quality audits, (2) remediating documentation issues found in audits."
category: documentation
date: 2026-03-22
version: "1.0.0"
user-invocable: false
tags: [audit, documentation, quality, strict-grading, remediation]
---

# Strict Repository Audit: Documentation Remediation Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-22 |
| **Objective** | Run a strict 15-section repository audit on ProjectHephaestus and fix identified documentation issues |
| **Outcome** | Successful. Audit scored B+ (87%) overall. Three documentation issues identified and fixed: stale SECURITY.md, misleading code comment, missing COMPATIBILITY.md |

## When to Use

- Running `/repo-analyze-strict` on a Python library and need to act on findings
- Fixing documentation issues identified during quality audits
- Creating missing policy documents (COMPATIBILITY.md, SECURITY.md updates)
- Prioritizing audit remediation items (documentation vs CI vs code quality)

## Verified Workflow

### Quick Reference

```bash
# 1. Run the strict audit
/repo-analyze-strict

# 2. Common documentation fixes:

# Fix stale SECURITY.md version table
# Edit the supported versions table to match current release

# Fix misleading comments in source code
# Remove or update comments that don't match the function's role

# Create missing policy docs referenced in CHANGELOG
# Check CHANGELOG for references to files that don't exist
grep -r "COMPATIBILITY\|SECURITY\|MIGRATION" CHANGELOG.md
```

### Detailed Steps

1. **Run the strict audit** using `/repo-analyze-strict` — this launches 3 parallel Explore agents to read source files, tests, and CI configs, then produces a 15-section graded report

2. **Identify documentation findings** across all sections — documentation issues appear not just in Section 2 (Documentation) but also in:
   - Section 8 (Security) — stale SECURITY.md
   - Section 4 (Source Code Quality) — misleading comments
   - Section 12 (Packaging) — missing COMPATIBILITY.md
   - Section 14 (API Design) — misleading function comments

3. **Fix stale version tables** — SECURITY.md supported versions must match the current release. When the project is at v0.4.0, the table should list 0.4.x as supported

4. **Fix misleading code comments** — comments like "Example usage function" on public API functions (`get_config_value`) confuse both humans and AI agents. Remove or rewrite to accurately describe the function's role

5. **Create missing referenced documents** — search CHANGELOG.md for references to files that were "added" but don't exist in the repo. Create them with appropriate content for the project's maturity level (e.g., v0.x compatibility policy differs from v1.0+)

6. **Verify changes** — run linters on modified source files to ensure no regressions:
   ```bash
   pixi run ruff check <modified-files>
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Initial plan proposed CI matrix expansion | Proposed expanding Python test matrix as top priority fix from audit | User preferred documentation fixes over CI changes | Ask the user which audit findings to prioritize rather than assuming the highest-severity finding should be fixed first |

## Results & Parameters

### Common Documentation Audit Findings (Python Libraries)

| Finding | Typical Section | Severity | Fix |
| --------- | ---------------- | ---------- | ----- |
| Stale SECURITY.md versions | Section 8 | MINOR | Update version table to include current release |
| Misleading code comments | Section 4 | NITPICK | Remove or rewrite comments that don't match function purpose |
| Missing referenced docs | Section 12 | MINOR | Create the document with appropriate content |
| No ADRs | Section 2 | MINOR | Usually deferred — design decisions live in CHANGELOG |
| No API auto-generation | Section 2 | MINOR | Add Sphinx/MkDocs if project warrants it |

### COMPATIBILITY.md Template for v0.x Projects

Key sections for a pre-1.0 library compatibility policy:
- v0.x stability expectations (minor releases may break API)
- Definition of breaking vs non-breaking changes
- Deprecation policy (warn for at least one minor release)
- Planned v1.0 stability guarantee

### Audit Score Distribution (ProjectHephaestus Baseline)

- **A- range (90-92%)**: Structure, Documentation, Developer Experience, Dependencies
- **B+ range (87-89%)**: Architecture, Code Quality, Testing, CI/CD, Security, AI Tooling, Packaging
- **B range (83-86%)**: Planning, API Design, Compliance
- **C+ range (77-79%)**: Safety & Reliability

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Strict audit + documentation remediation | [notes.md](./skills/documentation-strict-audit-remediation-workflow.notes.md) |
