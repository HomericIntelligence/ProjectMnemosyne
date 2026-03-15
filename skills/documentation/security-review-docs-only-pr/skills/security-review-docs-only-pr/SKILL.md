---
name: security-review-docs-only-pr
description: "Efficiently triage and close security reviews for PRs containing only documentation or metadata changes. Use when: a security review is triggered on a PR that adds only markdown files, JSON metadata, or other static documentation with no executable code."
category: documentation
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | security-review-docs-only-pr |
| **Category** | documentation |
| **Scope** | Any PR where all changed files are documentation or static metadata |
| **Effort** | < 2 min (classification check → immediate close) |
| **Risk** | None — no code changes to audit |

When a `/security-review` is triggered on a PR that contains only markdown files, JSON metadata, YAML configuration documentation, or other static content, the correct response is to immediately classify it as having no exploitable attack surface and issue a clean no-findings report. This avoids wasted review cycles and gives the reviewer confidence the review was thorough.

## When to Use

- A security review is requested and ALL changed files have extensions: `.md`, `.json` (metadata only), `.txt`, `.rst`
- The PR adds only skill documentation, plugin manifests, or reference notes to a skills registry
- All changed files are under a `skills/`, `docs/`, or `references/` directory with no executable code
- The diff contains no `eval`, `exec`, subprocess calls, SQL queries, template rendering, or user input handling

## Verified Workflow

### Quick Reference

| File Type | Has Attack Surface? | Action |
|-----------|--------------------|-----------------------|
| `.md` markdown | No | Classify as docs-only |
| `plugin.json` (static metadata) | No | Classify as docs-only |
| `references/notes.md` | No | Classify as docs-only |
| `.py`, `.js`, `.ts`, `.sh` | Possibly | Perform full security review |
| `.yml` GitHub Actions workflow | Possibly (injection) | Check for untrusted input in `run:` steps |

### Step 1 — Classify all changed files

Scan the diff and list every changed file path. Check each against the attack surface criteria:

```
For each changed file:
  - Is it a .md, .txt, .rst file?                → No attack surface
  - Is it a static JSON metadata file?           → No attack surface (no deserialization)
  - Is it executable code (.py, .js, .ts, .sh)?  → Requires full review
  - Is it a GitHub Actions workflow (.yml)?       → Check for injection patterns
  - Is it a template or config with user input?  → Requires full review
```

If ALL files classify as "No attack surface" → proceed to Step 2.

If ANY file has potential attack surface → perform full security review per standard methodology.

### Step 2 — Apply hard exclusions from review policy

Verify the docs-only classification against the explicit hard exclusions:

> "16. Insecure documentation. Do not report any findings in documentation files such as markdown files."

Markdown files (`.md`) are explicitly excluded from security review findings by policy.

Static metadata JSON with no deserialization path has no injection or execution surface.

### Step 3 — Issue clean no-findings report

Output the standard no-findings response:

```
No security vulnerabilities were identified in this PR.

The changes consist entirely of documentation files (markdown skill documentation,
plugin metadata JSON, and session notes). Per the hard exclusion rules, insecure
documentation findings are excluded, and these files contain no executable code,
user input handling, authentication logic, cryptographic operations, or other
attack surfaces.
```

This is a complete and accurate security review — brevity here is a feature, not a gap.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Performing full multi-phase review on docs-only PR | Running Phase 1 repo context research + Phase 2 comparative analysis + Phase 3 vulnerability assessment on a PR with only `.md` and `plugin.json` files | Wastes significant time with zero security value; all findings would be excluded by the hard exclusion rule for documentation files | Classify file types first; if all are docs/metadata, skip to the no-findings report immediately |
| Flagging YAML workflow examples inside SKILL.md as injection risks | The SKILL.md contained example GitHub Actions YAML with expression patterns | The YAML is inside a markdown code block — it is documentation of a pattern, not an executable workflow | Code blocks inside `.md` files are documentation, not executable. Apply the same hard exclusion. |

## Results & Parameters

### Decision Tree

```
PR changed files → all .md / static .json?
├── YES → No attack surface → issue clean no-findings report
└── NO  → At least one executable/config file?
    ├── GitHub Actions .yml → check for untrusted input in run: steps
    ├── Python/JS/TS/Shell  → full security review
    └── Config with user input → full security review
```

### Hard Exclusion Reference

From the security review policy:

```
16. Insecure documentation. Do not report any findings in documentation
    files such as markdown files.
```

This exclusion is categorical — it applies regardless of what content is inside the markdown file (including code blocks showing potentially unsafe patterns).

### Example No-Findings Report (copy-paste template)

```markdown
No security vulnerabilities were identified in this PR.

The changes consist entirely of [describe file types]. Per the hard exclusion
rules, insecure documentation findings are excluded, and these files contain
no executable code, user input handling, authentication logic, cryptographic
operations, or other attack surfaces.
```
