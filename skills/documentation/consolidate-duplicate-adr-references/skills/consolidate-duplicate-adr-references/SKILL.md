---
name: consolidate-duplicate-adr-references
description: "Consolidate duplicate inline comments or docstring Notes into a single ADR, then replace each duplicate with a short cross-reference. Use when: two or more functions have nearly identical limitation comments, or an issue asks to reduce maintenance burden by centralizing a workaround note in an ADR."
category: documentation
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Purpose** | Replace duplicate inline limitation comments with a single ADR + concise cross-references |
| **Trigger** | Follow-up issue requesting ADR consolidation of a workaround documented in multiple places |
| **Scope** | Any language; illustrated with Mojo `.mojo` files and `docs/adr/` directory |
| **Output** | New ADR file, updated ADR index, shortened inline comments pointing to the ADR |

## When to Use

- A GitHub issue says "consider a single shared ADR instead of cross-referencing between two function docstrings"
- Two or more functions contain nearly identical `# NOTE:` or `Note:` blocks describing the same limitation/workaround
- A follow-up from a PR asks to make a limitation "easier to update" when the underlying constraint is resolved
- An audit finds that updating a limitation note requires editing multiple files

## Verified Workflow

1. **Read the issue and its plan** to confirm scope:

   ```bash
   gh issue view <number> --comments
   ```

2. **Locate all duplicate comment blocks** with Grep before editing anything:

   ```
   Grep pattern="NOTE.*<keyword>" glob="**/*.mojo" output_mode="content"
   ```

3. **Check the next ADR number** and read existing ADR structure:

   ```bash
   ls docs/adr/
   ```

   Read one recent ADR (e.g., ADR-009) to match structure — Status, Date, Issue Reference,
   Executive Summary, Context, Decision, Rationale, Consequences, Alternatives, Implementation
   Plan, References, Revision History, Document Metadata.

4. **Create the ADR** at `docs/adr/ADR-NNN-<kebab-name>.md`. Key sections to fill:

   - **Executive Summary**: One paragraph — what the limitation is and what workaround is used
   - **Context / Key Findings**: Bullet list of compiler/runtime facts discovered
   - **Decision**: The workaround approach (e.g., scalar loop, file split, etc.)
   - **Consequences**: Performance or maintenance impact (quantify if known)
   - **Alternatives Considered**: Include "keep duplicate comments" as an alternative and explain why rejected
   - **Supersession Criteria**: Explicit conditions under which this ADR becomes Superseded
   - **Implementation Plan**: Check boxes — mark Phase 1 (consolidation) complete

5. **Update `docs/adr/README.md`** — add one row to the index table:

   ```markdown
   | [ADR-NNN](ADR-NNN-<name>.md) | <Title> | Accepted | YYYY-MM-DD |
   ```

6. **Edit source files** — replace each verbose block with 2–3 lines:

   ```mojo
   # <Short description of limitation>; using <workaround>.
   # See docs/adr/ADR-NNN-<name>.md for rationale.
   ```

   Also update any inline body comments that cross-reference the sibling function
   (e.g., "see convert_to_fp32_master docstring") to reference the ADR directly instead.

7. **Run pre-commit**:

   ```bash
   pixi run pre-commit run --all-files
   ```

   Watch for markdown line-length violations (MD013, 120-char limit). URLs in list items
   are NOT automatically exempt — wrap the line if the link text + URL exceeds 120 chars.

8. **Commit, push, and open PR**:

   ```bash
   git add docs/adr/ADR-NNN-<name>.md docs/adr/README.md <source-files>
   git commit -m "docs(adr): add ADR-NNN for <topic>\n\nCloses #<number>"
   git push -u origin <branch>
   gh pr create --title "docs(adr): add ADR-NNN for <topic>" --body "Closes #<number>" --label documentation
   gh pr merge --auto --rebase
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Manual `npx markdownlint-cli2` | Ran `pixi run npx markdownlint-cli2 <file>` to lint ADR before committing | `npx: command not found` even inside pixi environment | Use `pixi run pre-commit run --all-files` instead — it invokes markdownlint correctly |
| Long URL list item on one line | Put `[Issue #NNN](https://...): description text (this ADR)` on one line | MD013 fired: line was 138 chars (limit 120) | Wrap after the closing `)` of the URL: `[Issue #NNN](https://...):↵  description text` |
| Referencing sibling function in comment | Left "see sibling_fn() for details" in inline comment instead of pointing to ADR | Defeats the purpose — still requires navigating to another function | Update ALL cross-references to point directly to the new ADR path |

## Results & Parameters

**ADR file naming**: `docs/adr/ADR-NNN-<kebab-description>.md`
(NNN = next integer after highest existing ADR)

**Replacement comment pattern** (2–3 lines max):

```mojo
# <Limitation summary>; using <workaround>.
# See docs/adr/ADR-NNN-<name>.md for rationale.
```

**Docstring Note replacement** (keep the `Note:` label, shorten body):

```
Note:
    <Limitation> uses <workaround> (~Xx slower than optimized path).
    See docs/adr/ADR-NNN-<name>.md for full rationale.
```

**Markdown line-length fix** for long issue links:

```markdown
- [Issue #NNN](https://github.com/Org/Repo/issues/NNN):
  Description text that would have exceeded 120 chars
```

**Pre-commit command** (works in ProjectOdyssey with pixi):

```bash
pixi run pre-commit run --all-files
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3291 — FP16 SIMD limitation | [notes.md](../references/notes.md) |
