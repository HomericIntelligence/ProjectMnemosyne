# Session Notes: fix-markdown-agent-docs

## Context

- **Date**: 2026-03-06
- **PR**: #3319 (issue #3144) — consolidate 13 review specialists into 5
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3144-auto-impl
- **File fixed**: agents/hierarchy.md

## Objective

Address PR review feedback on #3319. The agent consolidation PR had one genuine
documentation issue: `agents/hierarchy.md` contained malformed closing code fences
and stale/inconsistent agent counts after the 13→5 review specialist consolidation.

## Plan (from .claude-review-fix-3144.md)

1. Fix malformed closing code fences on lines 70, 185, 201 (` ```text ` → ` ``` `)
2. Fix Level 3 specialist count from "10" to correct value
3. Commit, validate with pre-commit
4. CI failures (Core ExTensor, Models) confirmed pre-existing GLIBC issue, not PR regression

## Steps Taken

### 1. Read the file

Read agents/hierarchy.md in full to understand current state.

### 2. Fix closing fences

Three occurrences of ` ```text ` used as closing fences:
- Line 70: after the main hierarchy ASCII diagram
- Line 185: after "Top-Down (Task Decomposition)" code block
- Line 201: after "Bottom-Up (Status Reporting)" code block

First Edit attempt failed: tried to match using box-drawing chars from the diagram
which didn't match exactly. Succeeded by reading the exact lines around each fence
and using minimal context (1-2 lines before the malformed fence).

### 3. Verify actual agent counts

Used Grep to get `^level:` from all `.claude/agents/*.md` files.

Results:
- Level 0: 1 (chief-architect)
- Level 1: 6 (foundation, shared-library, tooling, papers, cicd, agentic-workflows orchestrators)
- Level 2: 4 (architecture-design, integration-design, security-design, code-review-orchestrator)
- Level 3: 15 (see below)
- Level 4: 6 (senior-impl, impl, test, documentation, performance, log-analyzer)
- Level 5: 3 (junior-impl, junior-test, junior-documentation)
- Template: 1 (excluded from counts)

Level 3 breakdown:
- Review specialists (4): general-review, mojo-language-review, security-review, test-review
- Implementation specialists (11): implementation, test, documentation, performance,
  security, blog-writer, numerical-stability, test-flakiness, pr-cleanup,
  mojo-syntax-validator, ci-failure-analyzer

Note: The plan doc said "5 code review specialists (general, mojo language, security, test, orchestrator)"
but the orchestrator (code-review-orchestrator) is Level 2, not Level 3.
The hierarchy.md line 217 incorrectly included it in the Level 3 count.

### 4. Updated counts in hierarchy.md

- Diagram box: "5 Code Review Specialists" → "4 Code Review Specialists"
- Diagram box: "4 Additional Specialists" → "6 Additional Specialists"
- Level Summaries L3: "(10 implementation/execution specialists + 5 code review specialists)"
  → "(11 implementation/execution specialists + 4 code review specialists)"
- Level 3 Breakdown: "10" → "11", "5 (general, mojo language, security, test, orchestrator)"
  → "4 (general, mojo language, security, test)"

### 5. Fixed markdown linting errors

After running `pixi run pre-commit run --all-files`, markdownlint reported:
- MD013 (line-length) on lines 98, 106, 108, 216, 219 (all over 120 chars)
- MD032 (blanks-around-lists) on line 216 (no blank line before list after bold heading)

Fixes:
- Wrapped long bullet continuation lines with 2-space indent
- Added blank line between `**Level 3 Breakdown:**` and the following list

### 6. Committed

```
SKIP=mojo-format git commit -m "fix: Address review feedback for PR #3319"
```

Mojo format skipped because GLIBC incompatibility on Debian Buster prevents mojo binary
from running. This is a pre-existing local environment issue, not introduced by this PR.
The PR only modifies .claude/agents/ and agents/hierarchy.md (no .mojo files).

## Key Lessons

1. **Always verify counts from source files** — plan docs can be stale; grep actual files
2. **Closing fences must be bare** — ` ```text ` on a closing fence is invalid markdown
3. **Orchestrators are not specialists** — code-review-orchestrator is Level 2
4. **Use `pixi run pre-commit run markdownlint-cli2 --all-files`** not `pixi run npx ...`
5. **`just` may not be installed** — fall back to `pixi run pre-commit run --all-files`
6. **SKIP=mojo-format** is appropriate when mojo binary can't run due to GLIBC mismatch
   on older Linux (and the commit touches no .mojo files)