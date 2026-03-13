# Skill: docs-status-fix

## Overview

| Field      | Value                                              |
|------------|----------------------------------------------------|
| Date       | 2026-02-19                                         |
| Category   | documentation                                      |
| Objective  | Fix stale "Current Status" in CLAUDE.md            |
| Issue      | #753                                               |
| PR         | #810                                               |
| Outcome    | Success — merged via auto-merge after CI passed    |

## When to Use

Trigger this skill when:

- A GitHub issue asks to update a "Current Status" or project phase description in CLAUDE.md
- The status in CLAUDE.md contradicts the README or actual codebase state (CI workflows, test counts, Docker setup, published results)
- The issue describes evidence of operational state that conflicts with a "planning phase" label

## Verified Workflow

1. **Read the issue** to understand what the inaccurate text says and what it should say:

   ```bash
   gh issue view <number> --comments
   ```

2. **Read the relevant section of CLAUDE.md** (use `Read` tool, offset + limit to target the area):

   ```
   Read: CLAUDE.md lines 1–20
   ```

3. **Apply the Edit** — single `Edit` call replacing the old status line(s):

   ```
   old: "Research and planning phase - establishing benchmarking methodology..."
   new: "Operational - active research with full evaluation infrastructure..."
   ```

   Match the wording already present in README.md's stable status badge description for consistency.

4. **Commit** with conventional commit format (`fix(docs): ...`) and include `Closes #<issue>`:

   ```bash
   git add CLAUDE.md
   git commit -m "fix(docs): Update CLAUDE.md 'Current Status' to reflect operational state\n\nCloses #<issue>"
   ```

   Pre-commit hooks run automatically and validate Markdown — no manual lint step needed.

5. **Push and open PR**:

   ```bash
   git push -u origin <branch>
   gh pr create --title "..." --body "Closes #<issue>"
   gh pr merge --auto --rebase <pr-number>
   ```

## Failed Attempts

| Attempt | What happened | Why it failed |
|---------|---------------|---------------|
| `Skill commit-commands:commit-push-pr` | Blocked by permission mode | `Skill` tool is disabled in don't-ask mode; must use raw git + gh CLI instead |

**Lesson**: When `Skill` tool is unavailable (permission denied), fall back to direct `git add / git commit / git push / gh pr create` commands — they are fully equivalent and always available.

## Results & Parameters

- **Files changed**: `CLAUDE.md` (2 lines, lines 11–12)
- **Tests required**: None — documentation-only change; pre-commit markdown lint covers it
- **CI checks**: Markdown Lint, Trim Trailing Whitespace, Fix End of Files — all passed
- **Time to complete**: < 5 minutes
- **PR**: <https://github.com/HomericIntelligence/ProjectScylla/pull/810>

## Notes

- The worktree's CLAUDE.md and the root ProjectScylla CLAUDE.md are separate files. The root may also need updating — check both when fixing project status.
- CLAUDE.md in the worktree already had the correct status after a prior commit (`ff52f07`) — the worktree CLAUDE.md was ahead of the root one. This is normal in worktrees that branch from a different base.
- Always read the file before editing — the `Edit` tool will reject changes on unread files.
