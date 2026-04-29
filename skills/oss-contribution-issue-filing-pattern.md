---
name: oss-contribution-issue-filing-pattern
description: "Strict OSS contribution workflow: audit an upstream repo, triage findings into critical bugs vs. quality improvements, check for duplicate issues, then file individual issues with embedded patches for each critical bug and a single omnibus issue for non-critical improvements. Use when: (1) performing a full repo audit before contributing to a project you don't maintain, (2) deciding which findings warrant individual issues vs. a bundled backlog issue, (3) filing bug reports with complete patches so the maintainer can accept without back-and-forth, (4) asking the maintainer which non-critical improvements they want before opening PRs."
category: tooling
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [oss, github, upstream, issue-filing, audit, deduplication, patch, bug-report, omnibus, triage, gh-tidy, shellcheck, bats, ci]
---

# OSS Contribution: Audit, Triage, and Issue Filing Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Audit `HaywardMorihara/gh-tidy`, triage findings into critical vs. non-critical, deduplicate against existing issues, then file individual issues for critical bugs (with patches) and one omnibus issue for non-critical improvements |
| **Outcome** | Issues #70 (branch_exists_locally bug), #71 (bats-core tests), #72 (GitHub Actions CI — references maintainer's own #28), #73 (12-item omnibus quality backlog) filed successfully |
| **Verification** | verified-local — `gh issue create` calls returned valid GitHub URLs for all 4 issues |
| **Source** | gh-tidy contribution session (second portion, after `bash-upstream-pr-review-traps` v2.0.0 covered the PR/fix side) |

## When to Use

- Performing a formal audit of an upstream OSS repo before contributing
- You have a mix of critical bugs (safety/correctness) and quality improvements (docs, style, CI)
- You want to avoid filing duplicate issues (checking what already exists before filing)
- You need to file bug reports that give the maintainer everything to merge with zero back-and-forth
- You want to propose a bundle of quality improvements but don't know which ones the maintainer wants
- The upstream repo already has an open question-issue (e.g., "Should we add CI?") that you want to address concretely

## Core Principles

### 1. Check Before File (Deduplication Gate)

Always run these two commands before filing any issue:

```bash
gh issue list --repo <owner>/<repo> --state all --limit 50
gh pr list --repo <owner>/<repo> --state all --limit 20
```

Cross-reference every finding against the list. A finding already covered by an existing
issue/PR should be skipped — filing it again wastes maintainer attention and looks unprofessional.

Note the existing issue numbers so you can reference them in your new filings (e.g.,
"addresses maintainer's own #28").

### 2. Triage: Critical vs. Non-Critical

| Category | Characteristics | Filing Strategy |
|----------|----------------|-----------------|
| **Critical** | Affects safety/correctness; wrong answer, data loss, silent failure, dead code that blocks protection | One issue per bug, include the exact patch |
| **Non-critical** | Docs, style, CI/CD, contributor experience, governance | Bundle all into one omnibus issue |

**Critical threshold** for a bash tool: bug causes the tool to do the wrong thing silently
(no error raised, wrong output), or a safety guard is bypassed by a logic error.

### 3. Critical Issues: Individual Issues With Patches

For each critical bug file one issue containing:
- The broken code with its **file + line number**
- The exact failing scenario (when does it bite users?)
- The exact fixed code as a code block (copy-paste ready)
- Impact statement (who gets hurt, how often)

```bash
gh issue create --repo <owner>/<repo> \
  --title "bug: <function>: <brief description of wrong behavior>" \
  --label bug \
  --body "$(cat <<'EOF'
## Problem

`<function_name>()` always returns `<wrong value>` regardless of input.

### Root Cause

`<file>:<line>`:
\`\`\`bash
# Current (broken):
<broken code snippet>
\`\`\`

`<command>` exits `0` even when `<condition>` — so the conditional is never
reached, meaning <consequence>.

### Impact

Every user who relies on `<protection>` is affected. The safety guard is dead code.

### Fix

\`\`\`bash
# Fixed:
<correct code snippet>
\`\`\`

### When it bites

- <specific scenario 1>
- <specific scenario 2>
EOF
)"
```

### 4. Non-Critical Issues: Single Omnibus Issue

Bundle all quality improvements into one issue. Key structure:
- Summary table (item, area, effort)
- Before/after code for each item
- Grouped by area (docs, code quality, contributor experience, security/governance)
- Ordered by effort within each group
- Explicitly ask which ones to implement before opening PRs

```bash
gh issue create --repo <owner>/<repo> \
  --title "improvement: quality backlog (docs, code, CI, contributor experience)" \
  --label enhancement \
  --body "$(cat <<'EOF'
## Overview

During a code review I found N quality improvements that aren't bugs.
Rather than filing N issues, I'm bundling them here and asking which ones
you'd like me to submit as PRs.

## Summary Table

| # | Area | Description | Effort |
|---|------|-------------|--------|
| A | Docs | ... | 5 min |
| B | Code | ... | 10 min |
| C | CI | ... | 30 min |

## Detailed Items

### A — <Title>

**Before:**
\`\`\`bash
<before code>
\`\`\`

**After:**
\`\`\`bash
<after code>
\`\`\`

---

<!-- repeat for B, C, ... -->

## Which ones would you like?

Happy to open separate PRs for whichever items interest you. Just let me know.
EOF
)"
```

### 5. CI Issue Should Reference Existing CI Issue

If the maintainer already has an open "should we add CI?" issue, don't file a new one
asking the same question. File a **concrete implementation issue** that says
"here's the actual CI config, addresses #<existing-issue-number>."

```bash
--body "...
This PR adds the GitHub Actions CI workflow requested in #<existing-number>.
..."
```

## Strict Audit Grading Approach

When the audit requires assigning grades:

- **Default every section to F** — upgrade only with concrete evidence
- **Automatic zeros for bash projects**: Testing=F (no test files), CI=F (no `.github/` dir),
  AI Agent=F (no `CLAUDE.md` or equivalent)
- **B grades are achievable** for: dependency management (minimal deps, nothing to mismanage),
  packaging (single-command install via `gh extension install`), CLI API design
  (consistent flag naming, `--dry-run` present)
- **Overall score** = weighted average across 15 sections; a tool can have a
  well-designed core (B in architecture/API) but fail on process/infrastructure
  (F in Testing/CI) dragging overall to D+

### 15-Section Grading Checklist

| Section | Auto-F condition | Evidence required for B |
|---------|-----------------|------------------------|
| README | Missing or placeholder | Installation + usage + examples present |
| Testing | No test files | Bats/shunit2 tests for core functions |
| CI/CD | No `.github/workflows/` | At least one workflow running shellcheck+tests |
| Security | World-writable files or eval on user input | `shellcheck` clean, no unsafe `eval` |
| Documentation | No docs beyond README | API reference or man page |
| Dependency Management | Undeclared deps or pinned at SHA=latest | Declared deps, version constraints |
| Packaging | No install instructions | `gh extension install` or equivalent documented |
| CLI API Design | Inconsistent flag naming | Consistent flags, `--help` works |
| Error Handling | Silent failures | `set -euo pipefail` or explicit error checks |
| Logging | No logging | Structured output, `--verbose` flag |
| Configuration | Hardcoded values | Env-var overrides for all user-facing settings |
| Contributor Experience | No CONTRIBUTING.md | CONTRIBUTING.md + dev setup instructions |
| Code Quality | Shellcheck warnings | Shellcheck clean, functions < 40 lines |
| AI Agent Tooling | No CLAUDE.md | CLAUDE.md or equivalent AI agent context |
| Versioning | No version tracking | Git tags or `--version` flag |

## Verified Workflow

### Step 1: Clone and Read Source

```bash
# Clone to throwaway for reading only (no state changes)
git clone https://github.com/<owner>/<repo> /tmp/<repo>-audit-$$

# Read primary script
cat /tmp/<repo>-audit-$$/main-script.sh   # adapt to actual filename

# Check repo structure
ls /tmp/<repo>-audit-$$/
ls /tmp/<repo>-audit-$$/.github/ 2>/dev/null || echo "No CI"
find /tmp/<repo>-audit-$$/ -name "*.bats" -o -name "test_*.sh" 2>/dev/null || echo "No tests"
```

### Step 2: Deduplication Gate

```bash
gh issue list --repo <owner>/<repo> --state all --limit 50
gh pr list --repo <owner>/<repo> --state all --limit 20
```

Record existing issue numbers. For each audit finding, mark: `NEW` or `DUPLICATE of #<n>`.

### Step 3: Grade Each Section

Work through the 15-section checklist. Use concrete evidence for each grade:
- "No `.github/` directory" → CI = F
- "No `.bats` or `test_*.sh` files anywhere" → Testing = F
- "`gh extension install <repo>` works" → Packaging = B

### Step 4: Triage Findings

Split findings into two buckets:

**Critical bugs (individual issues):**
- Silent wrong answer
- Dead safety-guard code
- Data-loss risk

**Quality improvements (omnibus issue):**
- Missing tests (not a bug, but important)
- Missing CI
- Style inconsistencies
- Documentation gaps
- Contributor-experience improvements

### Step 5: File Critical Issues

```bash
# One gh issue create call per critical bug
# Include: broken code with line, exact fix, impact, when-it-bites
# Use --label bug
```

### Step 6: File Omnibus Issue

```bash
# Single gh issue create for all non-critical items
# Include: summary table, before/after for each, ask which ones to implement
# Use --label enhancement
```

### Step 7: Cleanup

```bash
rm -rf /tmp/<repo>-audit-$$
```

## Results & Parameters

### Session Outcomes (gh-tidy audit, 2026-04-28)

| Issue | Type | Title | Result |
|-------|------|-------|--------|
| #70 | Critical bug | `branch_exists_locally()` always returns true | Filed with patch |
| #71 | Critical gap | Add bats-core test suite | Filed with example tests |
| #72 | Critical gap | Add GitHub Actions CI (addresses #28) | Filed with complete `.github/workflows/ci.yml` |
| #73 | Non-critical | 12-item quality improvements backlog | Filed as omnibus, asked maintainer which ones |

### Audit Score (gh-tidy, 2026-04-28)

- Overall: D+ (56%)
- Sections failing: Testing=F, CI/CD=F, AI Agent Tooling=F
- Sections passing: Packaging=B, CLI API=B, Dependency Management=B

### Key Parameter: When to Embed Patch vs. Reference PR

- **Embed patch in issue body** when: the fix is < 10 lines, you haven't forked yet, you want maintainer to assess before you open a PR
- **Open a PR directly** when: fix is already proven locally, you've already forked, this is a follow-up to an accepted issue

### Key Parameter: Omnibus Issue Grouping Order

Group by area, then within each group order by effort (ascending). Suggested areas:
1. Documentation
2. Code Quality
3. Contributor Experience
4. Security / Governance

## Failed Attempts

| Approach | Why It Failed | Correct Approach |
|----------|---------------|-----------------|
| Filing a new CI issue without referencing the maintainer's existing #28 | Looks like you didn't read the issue tracker; duplicate question | File a concrete implementation issue that says "addresses #28" |
| Filing 12 separate quality-improvement issues | Floods the issue tracker; maintainer has to triage 12 issues, most of which they may not want | Bundle into one omnibus issue and ask which ones they want |
| Filing the audit results before checking existing issues | Discovered issues #64/#65/#66 already existed from the same session; would have created duplicates | Always run `gh issue list --state all` first |
| Assigning labels without checking what labels exist | `gh issue create --label xyz` fails silently or errors if label doesn't exist | Run `gh label list --repo <owner>/<repo>` first |

## Related Skills

- `bash-upstream-pr-review-traps` (v2.0.0) — Covers the PR implementation side after issues are filed
- `file-upstream-feature-request` (v1.0.0) — Single feature request with gist-attached patch; use for simpler cases
- `bulk-issue-filing` (v1.0.0) — Filing many issues from code markers in your own repo
- `hephaestus:repo-analyze-strict` — The 15-section strict audit skill (F by default, evidence required)
