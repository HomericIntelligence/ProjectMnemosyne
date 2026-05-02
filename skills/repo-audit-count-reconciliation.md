---
name: repo-audit-count-reconciliation
description: 'Reconcile count mismatches across documentation files after a repository
  audit. Use when: counts in CLAUDE.md/README/hierarchy docs differ, audit reveals
  stale agent or skill counts, or on-disk file counts don''t match any documented
  number.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Trigger** | Count mismatch found during audit (agents, skills, workflows, architectures) |
| **Output** | Updated documentation with accurate, consistent counts |
| **Scope** | All docs claiming counts of file-backed entities |
| **Risk** | Low — documentation only, no code changes |

## When to Use

- An audit scorecard finds 3+ different numbers for the same entity across docs
- `ls .claude/agents/*.md | wc -l` doesn't match any documented agent count
- CLAUDE.md, hierarchy.md, and README.md all disagree on agent/skill counts
- Documentation lists agents/skills that don't exist as files on disk

## Verified Workflow

### Step 1: Count actual on-disk files

```bash
# Count actual agent files (exclude templates/ directory)
ls .claude/agents/*.md | wc -l

# Count actual skill definitions (exclude template file and tier dirs)
ls .claude/skills/ | grep -v "\.md\|^tier-" | wc -l

# Count CI workflows
ls .github/workflows/*.yml | wc -l
```

### Step 2: List stale references in documentation

```bash
# Find all agent count claims
grep -rn "42 agents\|37 agents\|31 agents\|agents total" \
  CLAUDE.md agents/ docs/ 2>/dev/null

# Find all skill count claims
grep -rn "82 total\|58 total\|35+\|82+" \
  CLAUDE.md docs/ 2>/dev/null

# Find all workflow count claims
grep -rn "23 workflow\|workflows" CLAUDE.md docs/ 2>/dev/null
```

### Step 3: Verify listed entities exist on disk

For agents specifically, check README lists against actual files:

```bash
# Extract agent names from README
grep '`.*\.md`' agents/README.md | sed "s/.*\`\(.*\)\.md\`.*/\1/" > /tmp/readme_agents.txt

# Check each one exists
while read name; do
  if [ ! -f ".claude/agents/$name.md" ]; then
    echo "MISSING: $name"
  fi
done < /tmp/readme_agents.txt
```

### Step 4: Update all count references

Edit each file found in Step 2, replacing stale counts with the verified number.
Key files to update for agent counts:

- `CLAUDE.md` — may have 2+ references
- `agents/README.md` — total + per-level counts
- `agents/hierarchy.md` — count table + level breakdown

For skill counts:

- `CLAUDE.md` — "N total" in skill delegation section
- `docs/dev/skills-architecture.md` — executive summary line

### Step 5: Fix stale entity listings

When README.md lists non-existent files (e.g. removed agents), update the list:

- Remove entries for files that don't exist
- Update per-level subtotals to match
- Update the total

### Step 6: Commit and PR

```bash
git checkout -b audit-fixes-count-reconciliation
git add CLAUDE.md agents/README.md agents/hierarchy.md docs/dev/skills-architecture.md
git commit -m "fix(audit): reconcile agent/skill counts to match on-disk state

- Agents: N→M (actual .md files on disk)
- Skills: N→M (actual skill definitions)
- Removed N non-existent agent stubs from README"
git push -u origin audit-fixes-count-reconciliation
gh pr create --title "fix(audit): reconcile counts" --body "Closes #..."
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust CLAUDE.md count | Used "42 agents" from CLAUDE.md as ground truth | CLAUDE.md had 42, hierarchy had 37, disk had 31 — all wrong | Always count with `ls *.md \| wc -l` first |
| Count `ls .claude/agents/` | `ls` of directory returns 32 (includes `templates/` dir) | `templates/` is a directory, not an agent file | Use `ls .claude/agents/*.md` to get only .md files |
| Fix only CLAUDE.md | Updated CLAUDE.md count but not hierarchy.md or agents/README.md | Three docs still disagreed | Search ALL docs for count claims before committing |
| Use README level subtotals | Added up README per-level counts expecting to get disk total | README listed 12 agents that no longer exist as files | Verify each listed agent exists before trusting subtotals |

## Results & Parameters

### Session: 2026-03-07 ProjectOdyssey audit

**Before reconciliation:**

| Doc | Claimed Count |
| ----- | -------------- |
| `CLAUDE.md` | 42 agents, 82 skills |
| `agents/hierarchy.md` | 37 agents |
| `agents/README.md` | 42 agents (with 12 non-existent entries) |
| `docs/dev/skills-architecture.md` | 35+ skills |

**After reconciliation:**

| Entity | On-Disk Count | All Docs Now Say |
| -------- | -------------- | ----------------- |
| Agents | 31 `.md` files | 31 |
| Skills | 58 entries | 58 |

**Non-existent agents removed from README:**

- `implementation-review-specialist`
- `documentation-review-specialist`
- `safety-review-specialist`
- `performance-review-specialist`
- `algorithm-review-specialist`
- `architecture-review-specialist`
- `data-engineering-review-specialist`
- `paper-review-specialist`
- `research-review-specialist`
- `dependency-review-specialist`
- `senior-implementation-engineer`
- `junior-implementation-engineer`
