---
name: fix-stale-agent-crossrefs
description: "Fix stale cross-references in agent configs and docs after specialist consolidation. Use when: (1) agent files are deleted during consolidation and remaining configs still reference them, (2) agent files are deleted or consolidated and docs still reference old agent names."
category: documentation
date: 2026-03-05
version: 2.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Trigger** | PR review finds stale links in `.claude/agents/*.md` after consolidation, or grep of `.claude/agents/` / `docs/` reveals references to non-existent agent files |
| **Scope** | `.claude/agents/` directory, `agents/`, `docs/dev/` markdown files |
| **Output** | Updated `Coordinates With` sections pointing to replacement agents; all stale agent name references replaced with new consolidated agent name |
| **Validation** | `python3 tests/agents/validate_configs.py .claude/agents/` + pre-commit markdownlint; re-run grep to confirm zero stale references |
| **Outcome** | Absorbed update-stale-agent-references on 2026-05-03 |

Absorbed: update-stale-agent-references on 2026-05-03

## When to Use

- After consolidating multiple review specialists into fewer (e.g., 13 → 5 agents)
- When PR review feedback identifies `Coordinates With` entries pointing to deleted files
- When `validate_configs.py` passes but internal markdown links are stale
- After agent consolidation issues (e.g. merging N specialist agents into one general agent)
- Follow-up cleanup after deleting agent `.md` files
- When a grep of `.claude/agents/` or `docs/` reveals references to non-existent files
- Before closing a consolidation PR to verify no dangling cross-references remain

## Verified Workflow

### Fixing Coordinates With / Agent Config Cross-References

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

### Finding and Updating Stale Agent References Across All Docs

1. **Identify deleted agent names** from the consolidation issue (e.g. issue body lists files deleted)

2. **Run broad grep** across all markdown files to find any references:

   ```bash
   grep -r "algorithm-review-specialist\|safety-review-specialist\|..." \
     --include="*.md" -l
   ```

3. **Inspect each match** with line numbers to understand context:

   ```bash
   grep -n "deleted-agent-name" path/to/file.md
   ```

4. **Read the file** to understand the section and what the correct replacement should be

5. **Edit the file** replacing deleted agent list entries with the consolidated agent:
   - Update count labels (e.g. "Review Specialists (10):" → "Review Specialists (4):")
   - Replace deleted agent bullet points with the new consolidated agent
   - Keep surviving agents (those not deleted) in the list

6. **Re-run grep** to confirm zero remaining stale references:

   ```bash
   grep -r "deleted-agent-name" --include="*.md"
   ```

7. **Commit** with a descriptive message referencing the consolidation issue

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

### Grep Pattern for Broad Agent Reference Searches

```bash
grep -rn \
  "algorithm-review-specialist\|safety-review-specialist\|performance-review-specialist\|architecture-review-specialist\|documentation-review-specialist\|data-engineering-review-specialist\|dependency-review-specialist\|implementation-review-specialist\|paper-review-specialist\|research-review-specialist" \
  --include="*.md"
```

### Edit Pattern: Replace Deleted Agent List Section

Replace a 10-item deleted-agent list section:

```
**Review Specialists (10):**

- `.claude/agents/algorithm-review-specialist.md`
- ...10 deleted agents...
```

With the consolidated 4-agent section:

```
**Review Specialists (4):**

- `.claude/agents/general-review-specialist.md`
- `.claude/agents/mojo-language-review-specialist.md`
- `.claude/agents/security-review-specialist.md`
- `.claude/agents/test-review-specialist.md`
```

### Key Insights

- The only file with stale references after a consolidation may be a tracking/status doc
  (e.g., `docs/dev/agent-claude4-update-status.md`), not the primary `agents/` directory or
  `hierarchy.md` — always check all `*.md` files recursively.
- `validate_configs.py` passing does not mean cross-references are clean — it only checks
  config structure, not link targets. Always run a grep sweep in addition.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Merging two lines into continuation indent | `- [General...] - Suggests...\n  untested code paths` | Markdownlint may reject indented continuation in list items | Prefer shortening the description to a single line under 120 chars |
| Running `just pre-commit-all` | `just: command not found` | `just` not installed on this host | Fall back to `pre-commit run --all-files` directly |
| Running `npx markdownlint-cli2` directly | `npx: command not found` | Node.js not in PATH outside pixi env | Use `pixi run npx markdownlint-cli2` or rely on pre-commit hook |
| `pixi run markdownlint-cli2` | `markdownlint-cli2: command not found` | pixi task not registered under that name | Rely on pre-commit hook for linting instead |
<<<<<<< HEAD
=======
| Searching only `.claude/agents/` | Ran grep scoped to `.claude/agents/*.md` | Tracking docs in `docs/dev/` were missed | Always search the full repo, not just the agents directory |
| Assuming hierarchy.md is the only doc to update | Only checked `agents/hierarchy.md` | Status/tracking docs like `agent-claude4-update-status.md` also list agents by name | Search recursively across all `*.md` files |
| Replacing agent names without reading context | Applied sed-style bulk replace | Counting labels ("Review Specialists (10)") also need updating | Read surrounding context before editing; update counts too |
>>>>>>> 5783bcc7 (chore(skills): consolidate clusters B+G — absorb stale-agent-refs + multi-repo skills (sub-wave 1 remainder))
