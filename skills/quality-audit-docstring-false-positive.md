---
name: quality-audit-docstring-false-positive
description: "---"
category: documentation
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: quality-audit-docstring-false-positive
description: "Use when a quality audit flags a module docstring as a sentence fragment, but the docstring is actually grammatically complete. Covers triage, fix pattern, and PR workflow."
user-invocable: false
category: documentation
date: 2026-03-03
---

# quality-audit-docstring-false-positive

How to handle recurring quality-audit flags on module docstrings that are grammatically correct but visually ambiguous due to line wrapping.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-03 |
| Objective | Fix a module docstring flagged in multiple quality audits as a sentence fragment |
| Outcome | Success — PR created, pre-commit passes, issue closed |

## When to Use

- A quality audit (e.g. March 2026 audit) flags a module docstring as "garbled" or "sentence fragment"
- On inspection the docstring is grammatically complete — just wrapped across lines
- The issue has recurred across multiple audit cycles (false positive repeating)
- The fix is cosmetic: restructure the sentence to remove visual ambiguity at the line break

## Verified Workflow

1. **Read the flagged file** to verify actual content:
   ```bash
   head -10 <module>.py
   ```

2. **Check the issue plan** for any suggested replacement text:
   ```bash
   gh issue view <number> --comments
   ```

3. **Identify the ambiguity**: A line break mid-sentence that makes the second line look like a fragment.
   Common pattern — audit sees line N+1 starting with a continuation like `parallel execution, and file I/O operations.` and flags it without reading line N.

4. **Apply the minimal fix**: Restructure the sentence with a relative clause so it reads unambiguously complete:
   - Before: `...EvalRunner class that orchestrates test execution\nacross multiple tiers...`
   - After:  `...EvalRunner class, which orchestrates test execution\nacross multiple tiers...`
   - Alternatively: reflow the sentence so no line ends mid-clause

5. **Run pre-commit on the file only**:
   ```bash
   pre-commit run --files <module>.py
   ```

6. **Commit, push, and open PR**:
   ```bash
   git add <module>.py
   git commit -m "fix(docs): Fix garbled module docstring in <module>.py\n\nCloses #<number>"
   git push -u origin <branch>
   gh pr create --title "fix(docs): Fix garbled module docstring in <module>.py" \
     --body "Closes #<number>"
   gh pr merge --auto --rebase
   ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Simply moving the line break | Produces essentially same content — audit may flag again | Change sentence structure, not just whitespace |
| Checking if tests are needed | None needed — pure docs change | `pre-commit run --files` is sufficient verification for docstring-only fixes |

## Results & Parameters

The working fix pattern for a wrapped-sentence false positive:

```python
# BEFORE (visually ambiguous — line N+1 looks like a fragment)
"""Module summary line.

This module provides the Foo class that does X
across multiple Y, with support for
Z and W.
"""

# AFTER (unambiguous — relative clause makes completeness clear)
"""Module summary line.

This module provides the Foo class, which does X
across multiple Y, with support for
Z and W.
"""
```

Key insight: quality audit tools often parse line-by-line; a line starting with a lowercase continuation word triggers a fragment heuristic. The fix is to restructure so no line starts with a bare continuation.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1360, Issue #1346 | [notes.md](references/notes.md) |

## References

- Related skills: `documentation/doc-stale-future-improvements-audit`
- Audit policy: `.claude/shared/common-constraints.md` (minimal change principle)
