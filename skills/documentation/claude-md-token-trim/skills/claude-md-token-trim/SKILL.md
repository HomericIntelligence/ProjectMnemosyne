---
name: claude-md-token-trim
description: "Reduce CLAUDE.md token consumption by replacing verbose/duplicate sections with concise summaries and links. Use when: (1) CLAUDE.md exceeds a line/token budget, (2) sections duplicate content already in shared docs, (3) pre-commit markdownlint MD060 table errors need fixing alongside trimming."
category: documentation
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute | Value |
| --------- | ----- |
| **Goal** | Reduce CLAUDE.md from N lines to ≤ target without losing critical information |
| **Trigger** | CLAUDE.md too large, token budget concerns, sections duplicating shared docs |
| **Output** | Trimmed CLAUDE.md + passing markdownlint + PR |
| **Risk** | Low — structural edits only, no logic changes |

## When to Use

- CLAUDE.md has grown beyond a line/token budget (e.g., >1,200 lines)
- Sections exist that fully duplicate content in `.claude/shared/` docs
- Pre-commit `markdownlint-cli2` reports MD060 table column style errors in existing tables
- A PR/issue requests "reduce CLAUDE.md" or "trim token consumption"

## Verified Workflow

### Quick Reference

```bash
# 1. Count lines
wc -l CLAUDE.md

# 2. Run markdownlint before editing (baseline)
pixi run npx markdownlint-cli2 CLAUDE.md

# 3. After edits, verify
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md  # must be 0 errors

# 4. Commit + PR
git add CLAUDE.md
git commit -m "docs(claude-md): trim CLAUDE.md from X to Y lines"
gh pr create ...
```

### Step 1 — Baseline measurement

Count lines and capture markdownlint errors before touching anything:

```bash
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 | tee /tmp/baseline-lint.txt
```

Note which errors are pre-existing vs. introduced by your edits. Use `git stash` + re-run
to confirm baseline:

```bash
git stash
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 > /tmp/before.txt
git stash pop
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt
```

### Step 2 — Identify high-value trim targets

Read the full file and look for:

| Pattern | Typical Size | Action |
| ------- | ------------ | ------ |
| Section fully duplicates a `/.claude/shared/` doc | 30–120 lines | Replace with 1-line pointer + link |
| Correct/Incorrect example pairs illustrating a rule already stated | 20–60 lines | Delete examples, keep rule statement |
| Multi-step CLI block already in a dedicated workflow doc | 15–40 lines | Collapse to 2–4 key commands |
| "Why this rule exists" rationale after rule already stated at top | 10–30 lines | Delete (rule stated at top is enough) |
| Verbose table that could be a condensed table | 5–20 lines | Condense or remove low-value columns |

**Never trim:**

- CRITICAL RULES section (branch protection, PR workflow)
- Any section with no corresponding link destination
- Mojo-specific critical patterns (out self, mut, ^, etc.)

### Step 3 — Apply edits with Edit tool

Use the `Edit` tool (not sed/awk) for all edits so changes are reviewable.

**Pattern: Replace verbose section with pointer**

```markdown
<!-- BEFORE: 65 lines of duplicate "Never Push to Main" instructions -->

### 🚫 Never Push Directly to Main

**⚠️ CRITICAL:** See [CRITICAL RULES section](#️-critical-rules---read-first) at the top of this document.

**This rule has NO EXCEPTIONS - not even for emergencies.** Always use the PR workflow described there.

<!-- AFTER: 3 lines -->
```

**Pattern: Condense verbose examples to key rules**

```markdown
<!-- BEFORE: 119 lines with correct/incorrect markdown examples -->

## Markdown Standards

All markdown files must follow these standards to pass `markdownlint-cli2` linting:

- **MD031/MD040**: Fenced code blocks must have blank lines before/after and a language tag
- **MD032**: Lists must be surrounded by blank lines
- **MD022**: Headings must be surrounded by blank lines
- **MD013**: Lines must not exceed 120 characters (code blocks and URLs exempt)

**Quick check before committing**: blank lines around all code blocks, lists, and headings;
language on all code fences; no lines >120 chars; file ends with newline.

```bash
pixi run npx markdownlint-cli2 path/to/file.md
```

<!-- AFTER: ~12 lines -->
```

**Pattern: Collapse verbose CLI blocks**

```markdown
<!-- BEFORE: Detailed table + pull/run/build sections = 41 lines -->

### Docker Registry (GHCR)

Images published to GHCR: `ghcr.io/homericintelligence/projectodyssey:{main,main-ci,main-prod}`.

```bash
docker pull ghcr.io/homericintelligence/projectodyssey:main  # ~2GB runtime
just docker-up    # Start dev environment
just docker-shell # Open shell in container
just docker-build-ci runtime  # Build locally
```

<!-- AFTER: ~8 lines -->
```

### Step 4 — Fix MD060 table column style errors

MD060 errors occur when table separator rows use compact notation (`|---|---|`) instead of
spaced notation (`| --- | --- |`). Fix all tables in the file:

```markdown
<!-- BEFORE (triggers MD060) -->
| Task Type | Budget | Examples | Rationale |
|-----------|--------|----------|-----------|

<!-- AFTER (passes MD060) -->
| Task Type | Budget | Examples | Rationale |
| --------- | ------ | -------- | --------- |
```

Run markdownlint after each batch of table fixes to confirm:

```bash
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 | grep MD060
```

### Step 5 — Verify and commit

```bash
# Final line count
wc -l CLAUDE.md

# Must be 0 errors
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1

# Commit
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(claude-md): trim CLAUDE.md from X to Y lines

Reduce token consumption by removing verbose/duplicate content:

- <Section>: <brief description of what was removed>
- Fixed pre-existing MD060 table column style lint errors

All critical information preserved via links to existing shared docs.
No content from CRITICAL RULES section was removed.

Closes #<issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Running `just pre-commit-all` to validate | Used `just pre-commit-all` as the validation step | Fails with unrelated pixi environment "Text file busy" errors — exit code 1 even when all hooks pass | Run `pixi run npx markdownlint-cli2 CLAUDE.md` directly instead of `just pre-commit-all`; the individual hooks pass even when the recipe itself errors |
| Assuming MD060 errors were introduced by edits | Saw MD060 in post-edit lint output | Errors existed before edits (confirmed with `git stash` + re-run) | Always baseline lint before editing so you know which errors you introduced vs. which are pre-existing |
| Editing with Bash sed | Considered `sed -i` for bulk replacements | sed is not the preferred tool per project conventions; edits are not reviewable | Always use the `Edit` tool for file modifications — it shows clear diffs and is tool-auditable |

## Results & Parameters

**Session result** (2026-03-15):

- File: `CLAUDE.md`
- Before: 1,257 lines
- After: 1,012 lines
- Reduction: 245 lines (19%)
- Target was ≤1,200 lines — achieved ≤1,012
- Markdownlint: 0 errors after fixing MD060 in 3 tables

**Sections trimmed and savings:**

| Section | Lines Saved | Technique |
| ------- | ----------- | --------- |
| Git Workflow duplicate "Never Push to Main" | ~62 | Replace 65-line duplicate with 3-line pointer |
| Markdown Standards correct/incorrect examples | ~107 | Replace 119-line verbose section with 12-line summary |
| Documentation Org GitHub issue code blocks | ~28 | Replace with single-line link to shared doc |
| Docker Registry detailed table + sections | ~33 | Collapse to 8-line summary |
| Agent Testing per-script commands | ~28 | Collapse to single loop + one-line summary |
| MD060 table fixes (3 tables) | -3 | Spacing fixes added 3 lines |
