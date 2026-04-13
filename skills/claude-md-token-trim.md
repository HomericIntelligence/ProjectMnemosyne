---
name: claude-md-token-trim
description: 'Reduce CLAUDE.md token consumption by replacing verbose/duplicate sections
  with concise summaries and links. Use when: (1) CLAUDE.md exceeds a line/token budget,
  (2) sections duplicate content already in shared docs, (3) pre-commit markdownlint
  MD060 table errors need fixing alongside trimming.'
category: documentation
date: 2026-04-07
version: 2.0.0
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
- Sections contain long code-block examples that explain concepts (not rules)
- Content duplicates or elaborates on dedicated docs in `.claude/shared/` or `docs/dev/`

## Verified Workflow

### Quick Reference

```bash
# 1. Audit sections by line number
grep -n "^##\|^###\|^####" CLAUDE.md

# 2. Count lines
wc -l CLAUDE.md

# 3. Run markdownlint before editing (baseline)
pixi run npx markdownlint-cli2 CLAUDE.md

# 4. After edits, verify
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md  # must be 0 errors

# 5. Commit + PR
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

### Step 2 — Audit sections by category

Read CLAUDE.md headings with line numbers to categorize each section:

```bash
grep -n "^##\|^###\|^####" CLAUDE.md
```

Classify each section as:
- **Keep full**: Critical rules, decision trees, quick-ref tables
- **Trim examples**: Keep bullets/tables, remove code-block examples
- **Move + link**: Pure reference content that belongs in `.claude/shared/`

### Step 3 — Identify high-value trim targets

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
- Decision trees used in every interaction
- Quick reference tables (e.g., Thinking Budget, Hook Types)
- Any section prefixed with `⚠️` or containing enforcement language

### Step 4 — Apply move+link for reference sections

Create `.claude/shared/<section-name>.md` with full content, then replace
the CLAUDE.md section with a 2-5 line summary + link.

**Note on pre-commit after edits**: If `mojo-format` fails due to GLIBC incompatibility on
older Linux hosts (and no `.mojo` files were changed), skip it explicitly:

```bash
SKIP=mojo-format pre-commit run --all-files
# or at commit time:
SKIP=mojo-format git commit -m "docs(claude-md): trim <section> to summary + link"
```

All other hooks (markdownlint, trailing-whitespace, check-yaml, etc.) must pass.

```markdown
### Output Style Guidelines

Use repo-relative file paths with line numbers for code references. Structure PR/issue comments with
`## Summary`, `## Changes Made`, `## Files Modified`, `## Verification` sections.

See [Output Style Guidelines](.claude/shared/output-style-guidelines.md) for complete examples.
```

**For trim-examples sections** — remove markdown code-block examples that illustrate points already stated in bullet form. Keep:
- Bullet lists of when/when-not
- Tables (budget, hook types, tool selection)
- Decision trees (text-art `├─` style)

### Step 5 — Apply edits with Edit tool

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

**Quick check before committing**: blank lines around all code blocks, lists, and headings;
language on all code fences; no lines >120 chars; file ends with newline.

<!-- AFTER: ~12 lines -->
```

### Step 6 — Fix MD060 table column style errors

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

### Step 7 — Verify and commit

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
| Running `just pre-commit-all` directly | Used `just` command runner | `just` not in PATH in this shell environment | Use `pre-commit` directly from `.pixi/envs/default/bin/pre-commit` |
| Running `pixi run just pre-commit-all` | Pixi doesn't expose `just` as a run target | `just: command not found` inside pixi env | Run pre-commit directly, not via just |
| Running `pixi run markdownlint-cli2` | Tried to lint markdown directly | `markdownlint-cli2: command not found` as pixi task | Use `pre-commit run --all-files` which invokes it correctly |
| Editing main repo instead of worktree | Made all CLAUDE.md edits to `/home/mvillmow/Odyssey2/CLAUDE.md` | Worktree at `.worktrees/issue-3158/` tracks a different branch | Must `cp` changes from main repo to worktree, or edit worktree directly |

## Results & Parameters

**Session result** (2026-03-15, markdownlint + MD060):

- File: `CLAUDE.md`
- Before: 1,257 lines
- After: 1,012 lines
- Reduction: 245 lines (19%)
- Target was ≤1,200 lines — achieved ≤1,012
- Markdownlint: 0 errors after fixing MD060 in 3 tables

**Session result** (2026-03-05, move+link approach):

- Before: 1,786 lines
- After: 1,199 lines
- Reduction: 587 lines (33%)

**Sections trimmed and savings (markdownlint session):**

| Section | Lines Saved | Technique |
| ------- | ----------- | --------- |
| Git Workflow duplicate "Never Push to Main" | ~62 | Replace 65-line duplicate with 3-line pointer |
| Markdown Standards correct/incorrect examples | ~107 | Replace 119-line verbose section with 12-line summary |
| Documentation Org GitHub issue code blocks | ~28 | Replace with single-line link to shared doc |
| Docker Registry detailed table + sections | ~33 | Collapse to 8-line summary |
| Agent Testing per-script commands | ~28 | Collapse to single loop + one-line summary |
| MD060 table fixes (3 tables) | -3 | Spacing fixes added 3 lines |

**Sections moved to `.claude/shared/` (move+link session):**

| New File | Content Moved From | Lines Saved |
|----------|-------------------|-------------|
| `.claude/shared/output-style-guidelines.md` | Output Style Guidelines section | ~144 lines |
| `.claude/shared/tool-use-optimization.md` | Tool Use Optimization + Agentic Loop Patterns | ~210 lines |

**Key preservation rules** — always keep in CLAUDE.md (never move to shared):
- `## ⚠️ CRITICAL RULES` section in full
- Git workflow with concrete `gh pr create` examples
- Commit message format with HEREDOC example
- `### Mojo Development Guidelines` (Critical Patterns table)
- All `### Pre-Commit Hook Policy - STRICT ENFORCEMENT` content

**Pre-commit invocation** (workaround for GLIBC environment issues):

```bash
# Works — skips mojo-format which fails due to GLIBC version mismatch
SKIP=mojo-format /path/to/.pixi/envs/default/bin/pre-commit run --all-files
```
