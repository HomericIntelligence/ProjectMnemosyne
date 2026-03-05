---
name: consolidate-review-agents
description: "Merge overlapping review specialist agents into a single general-review-specialist. Use when: (1) multiple review agents have overlapping scopes, (2) project complexity doesn't justify 10+ specialists, (3) you want to reduce total agent count while keeping full review coverage."
category: architecture
date: 2026-03-05
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Pattern** | Agent consolidation — many-to-one specialist merge |
| **When Applicable** | Early-stage projects with premature specialization |
| **Effort** | ~30 min (read 10 files, write 1, update 2 references) |
| **Risk** | Low — review coverage preserved, only file count changes |
| **Result (ProjectOdyssey)** | 13 review specialists → 5, total agents 44 → 35 |

## When to Use

Trigger this skill when:

1. Agent count for a single concern (e.g., code review) has grown to 10+
2. Most specialists share identical YAML frontmatter (same tools, model, level, phase, hooks)
3. Specialists cross-reference each other in "What I do NOT review" sections, creating circular scope
4. The project is still in planning/early implementation phase — premature specialization adds overhead
5. An orchestrator's `delegates_to` list has more than 5–6 entries for the same concern

## Verified Workflow

### Step 1: Identify candidates for merging

Read all candidate files. Look for:
- Same `tools`, `model`, `level`, `phase`, and `hooks` in YAML frontmatter
- Scope definitions that explicitly exclude each other ("→ Implementation Specialist", "→ Algorithm Specialist")
- Small, focused review checklists (5–10 items each)

Agents to **keep separate** if they have genuinely unique requirements:
- Mojo-language-specific agents (special syntax knowledge)
- Security agents (distinct attack-vector expertise)
- Test agents (coverage metrics, assertions)
- Orchestrators (coordination role, different tools)

### Step 2: Create `general-review-specialist.md`

Create `.claude/agents/general-review-specialist.md` with:

```yaml
---
name: general-review-specialist
description: "Reviews code for [list all merged dimensions]. Select for any general code review dimension not covered by [remaining specialists]."
level: 3
phase: Cleanup
tools: Read,Grep,Glob
model: sonnet
delegates_to: []
receives_from: [code-review-orchestrator]
hooks:
  PreToolUse:
    - matcher: "Edit"
      action: "block"
      reason: "Review specialists are read-only - cannot modify files"
    - matcher: "Write"
      action: "block"
      reason: "Review specialists are read-only - cannot create files"
    - matcher: "Bash"
      action: "block"
      reason: "Review specialists are read-only - cannot run commands"
---
```

Body structure:
- One `## Scope` section with subsections per merged domain
- Merged review checklists (one per domain)
- Representative example review per domain (keep 3–4, skip redundant ones)
- Coordinates With pointing to remaining specialists

### Step 3: Delete the merged files

```bash
git rm .claude/agents/algorithm-review-specialist.md \
       .claude/agents/architecture-review-specialist.md \
       # ... (all 10)
```

### Step 4: Update the orchestrator

In `code-review-orchestrator.md`, update:
- `delegates_to` list: replace 10 entries with `general-review-specialist`
- Delegation decision matrix: merge 10 rows into one catch-all row
- Routing dimensions table: collapse to 4 rows
- "Delegates To" section: 13 items → 4 items
- Body text mentioning "13 specialists" → "4 specialists"

### Step 5: Update hierarchy documentation

In `agents/hierarchy.md`, update:
- Level 3 specialist count in the ASCII diagram
- Level 3 agent count in the "Level Summaries" section
- Agent Count table (Level 3 row + Total row)
- Level 3 Breakdown bullet list

### Step 6: Validate

```bash
python3 tests/agents/validate_configs.py .claude/agents/
pixi run pre-commit run --all-files
```

All hooks should pass. The mojo GLIBC errors on older Linux systems are pre-existing
environment issues unrelated to agent file changes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `Edit` tool without prior `Read` | Tried to edit `code-review-orchestrator.md` directly after reading it via `bash sed` | Tool requires `Read` tool call in conversation history | Always call `Read` tool explicitly before `Edit`, even if you saw file contents via Bash |
| Single `git rm` with wildcard | `git rm .claude/agents/*-review-specialist.md` excluding some files | Shell glob would also match files to keep (mojo, security, test) | List each file explicitly in `git rm` |

## Results & Parameters

**ProjectOdyssey outcome**:

```
Before: 13 review specialists (algorithm, architecture, data-engineering,
        dependency, documentation, implementation, mojo-language, paper,
        performance, research, safety, security, test)

After: 5 review agents (general, mojo-language, security, test, orchestrator)

Files changed: -10 deleted, +1 created, +2 updated
Lines changed: -1063 insertions, +297 deletions (net -766 lines)
Total agents: 44 → 35
```

**Which specialists to keep separate (decision criteria)**:

| Keep Separate | Reason |
|---------------|--------|
| `mojo-language-review-specialist` | Language-specific: SIMD patterns, ownership semantics, v0.26.1+ syntax |
| `security-review-specialist` | Domain expertise: CVEs, attack vectors, auth flows |
| `test-review-specialist` | Metrics-driven: coverage thresholds, assertion quality, test isolation |
| `code-review-orchestrator` | Coordinator role: different tools (`Task`), different level (2 vs 3) |

**Key insight**: When 10 agents all have identical `tools: Read,Grep,Glob`, `model: sonnet`,
`level: 3`, `phase: Cleanup`, and identical `hooks` blocks, they are structurally identical.
The only difference is the review checklist — which can live as subsections in one file.
