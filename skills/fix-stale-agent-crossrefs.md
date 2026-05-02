---
name: fix-stale-agent-crossrefs
description: 'Fix stale cross-references in agent configs after specialist consolidation.
  Use when: agent files are deleted during consolidation and remaining configs still
  reference them.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Trigger** | PR review finds stale links in `.claude/agents/*.md` after consolidation |
| **Scope** | `.claude/agents/` directory |
| **Output** | Updated `Coordinates With` sections pointing to replacement agents |
| **Validation** | `python3 tests/agents/validate_configs.py .claude/agents/` + pre-commit markdownlint |

## When to Use

- After consolidating multiple review specialists into fewer (e.g., 13 → 5 agents)
- When PR review feedback identifies `Coordinates With` entries pointing to deleted files
- When `validate_configs.py` passes but internal markdown links are stale

## Verified Workflow

1. **Identify stale links** from PR review feedback or grep:

   ```bash
   grep -r "deleted-specialist-name" .claude/agents/
   ```

2. **Read each flagged file** around the `Coordinates With` section to confirm exact text.

3. **Apply parallel edits** — all four files can be updated simultaneously since they are
   independent:

   - Replace `[Deleted Specialist](./deleted-specialist.md)` with
     `[General Review Specialist](./general-review-specialist.md)`
   - Merge the description from both deleted lines into one concise line
   - Keep line length under 120 characters (markdownlint MD013)

4. **Validate** agent configs pass:

   ```bash
   python3 tests/agents/validate_configs.py .claude/agents/
   ```

5. **Run pre-commit** on affected files (markdownlint will catch line-length violations):

   ```bash
   pre-commit run --files .claude/agents/mojo-language-review-specialist.md \
     .claude/agents/numerical-stability-specialist.md \
     .claude/agents/security-review-specialist.md \
     .claude/agents/test-review-specialist.md
   ```

6. **Commit** with the format specified in the review plan file.

## Results & Parameters

### Line Length Rule

Markdownlint MD013 enforces 120-character max. When merging two bullet points into one,
always count characters before committing:

```text
- [General Review Specialist](./general-review-specialist.md) - <description>
 ^--- count from here to end must be <= 120
```

If over limit, shorten the description (e.g., "Coordinates on tests and untested code paths"
instead of "Suggests numerical/gradient tests and notes untested code paths").

### Mojo Format Hook

The `mojo-format` pre-commit hook will fail on hosts with GLIBC < 2.32 (Debian Buster).
This is a pre-existing environmental issue — skip it with `SKIP=mojo-format` or ignore
when only `.md` files changed. The commit hook runs only on staged filetypes, so committing
`.md`-only changes naturally skips mojo-format.

### Validation Output

`validate_configs.py` reports warnings (missing recommended sections) but these are
pre-existing and not caused by cross-reference fixes. Zero errors = passing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merging two lines into continuation indent | `- [General...] - Suggests...\n  untested code paths` | Markdownlint may reject indented continuation in list items | Prefer shortening the description to a single line under 120 chars |
| Running `just pre-commit-all` | `just: command not found` | `just` not installed on this host | Fall back to `pre-commit run --all-files` directly |
| Running `npx markdownlint-cli2` directly | `npx: command not found` | Node.js not in PATH outside pixi env | Use `pixi run npx markdownlint-cli2` or rely on pre-commit hook |
| `pixi run markdownlint-cli2` | `markdownlint-cli2: command not found` | pixi task not registered under that name | Rely on pre-commit hook for linting instead |
