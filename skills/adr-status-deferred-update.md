---
name: adr-status-deferred-update
description: 'Update ADR status to Accepted (Deferred) when implementation is bypassed
  pending platform support. Use when: ADR is marked Accepted but code explicitly bypasses
  the design, or a known platform limitation prevents activation.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| Category | documentation |
| Trigger | ADR status says Accepted but implementation uses a bypass (e.g., `# Temporary: Direct malloc`) |
| Root Cause | Status label was set at design time and not updated when implementation deferred activation |
| Fix | Change status to `Accepted (Deferred)` in both header and Document Metadata section |

## When to Use

- An ADR has `**Status**: Accepted` but the implementation explicitly bypasses the architecture
- The bypass comment references a known platform gap (e.g., Mojo global variable support, missing stdlib feature)
- The underlying design decision is still valid — only the _active status_ is incorrect
- A PR or issue flags the discrepancy between ADR status and code reality

## Verified Workflow

1. **Read the ADR** to confirm it has both a header status and a Document Metadata status:

   ```text
   **Status**: Accepted          ← line ~3 (header)
   ...
   - **Status**: Accepted        ← line ~301 (Document Metadata section)
   ```

2. **Use `replace_all: true`** in the Edit tool to update both occurrences in one operation:

   ```
   old_string: **Status**: Accepted
   new_string: **Status**: Accepted (Deferred)
   replace_all: true
   ```

3. **Verify both locations were updated** by reading the file at the header and tail.

4. **Run markdownlint** to confirm no formatting regressions:

   ```bash
   pixi run pre-commit run markdownlint-cli2 --files docs/adr/<adr-file>.md
   ```

   Note: Use `pixi run pre-commit run markdownlint-cli2 --files <file>`, NOT
   `pixi run npx markdownlint-cli2` (npx may not be available in all environments).

5. **Commit with conventional commit format**:

   ```bash
   git commit -m "docs(adr): update ADR-NNN status to Accepted (Deferred)"
   ```

6. **Create PR** linked to the tracking issue and enable auto-merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `just pre-commit-all` | Ran `just pre-commit-all` to validate markdown | `just` not available in the worktree shell environment | Use `pixi run pre-commit run markdownlint-cli2 --files <file>` instead |
| `pixi run npx markdownlint-cli2` | Ran markdownlint via npx | `npx` not available in the pixi environment | Use `pixi run pre-commit run markdownlint-cli2 --files <file>` — pre-commit has the tool |
| Single Edit without `replace_all` | Edited only the header status field | ADR has two status locations (header + Document Metadata); only one was updated | Use `replace_all: true` to catch all occurrences in one edit |

## Results & Parameters

### Correct Edit Command

```text
Tool: Edit
file_path: docs/adr/ADR-NNN-<name>.md
old_string: **Status**: Accepted
new_string: **Status**: Accepted (Deferred)
replace_all: true
```

### Correct Lint Command

```bash
# Works in pixi-managed environments (does NOT require npx or just)
pixi run pre-commit run markdownlint-cli2 --files docs/adr/<adr-file>.md
```

### Commit Message Pattern

```bash
git commit -m "docs(adr): update ADR-NNN status to Accepted (Deferred)

<Brief explanation of what the bypass is and why it is deferred>

Closes #<issue-number>"
```

### When the ADR Already Has a "Current Limitation" Section

If the ADR body already documents the bypass (e.g., has a "Current Limitation" or "Known Limitation"
section with the bypass code), only the status label needs changing — no body edits required.
The existing limitation section is sufficient context.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3151, PR #3339 | ADR-003 memory pool bypassed pending Mojo global state support |
