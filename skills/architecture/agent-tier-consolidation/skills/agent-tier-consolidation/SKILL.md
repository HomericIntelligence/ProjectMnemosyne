---
name: agent-tier-consolidation
description: "Pattern for merging a redundant junior agent tier into its parent level. Use when: a lowest-level junior tier duplicates the parent scope with simpler tasks and the distinction adds configuration overhead without meaningful value."
category: architecture
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Category** | Architecture |
| **Effort** | Low (30 min) |
| **Risk** | Low |
| **Scope** | Agent config files + documentation |

Consolidating a junior agent tier into its parent removes redundant hierarchy levels
without losing capability. The parent absorbs the junior's scope, the junior's config
file is deleted, and all downstream references are updated atomically.

## When to Use

- A junior (lowest-level) agent tier exists whose responsibilities are a strict subset of the parent level's
- The junior and parent use the same model (e.g. both haiku) making the split artificial
- The total agent count needs to be reduced for maintainability
- A prior consolidation (e.g. junior implementation/test) established the pattern and documentation engineers should follow suit

## Verified Workflow

1. **Read all three tiers** — specialist (L3), engineer (L4), junior (L5) — to understand scope overlap
2. **Expand the parent (L4) config**: absorb junior description, scope items, workflow steps, skills, and constraints into the engineer agent file; set `delegates_to: []`
3. **Update the specialist (L3) config**: remove junior from its `delegates_to` list
4. **Delete the junior config file** (`git rm` or plain `rm`)
5. **Update documentation files** — search for every reference to the junior agent name:
   - `agents/hierarchy.md`: remove from L5 diagram box; update L5 narrative count
   - `agents/README.md`: remove entry; update Level 5 agent count in heading
   - `agents/docs/agent-catalog.md`: remove full section; update total counts; update delegation references; update Quick Reference table row
   - `agents/docs/onboarding.md`: remove list entry; update "N agents" link text
6. **Verify no stale references**: `grep -r "junior-<domain>-engineer" .claude/agents/ agents/ CLAUDE.md`
7. **Run agent validation tests**: `python3 tests/agents/validate_configs.py .claude/agents/` — must be 0 failures
8. **Commit all changes atomically** with a `refactor(agents):` conventional commit message

## Results & Parameters

### What to absorb into the parent (L4) engineer agent

```yaml
# Before (documentation-engineer.md)
description: "Select for code documentation work..."
delegates_to: [junior-documentation-engineer]

# After
description: "Select for code documentation work... Also handles simple tasks: fills docstring
  templates, formats documentation, generates changelog entries, checks links."
delegates_to: []
```

Add to Scope list: all junior scope items (template filling, formatting, changelog, link checking).

Add to Workflow: junior steps (format consistently, check for typos, validate markdown).

Add to Skills table: junior skills (`quality-fix-formatting`, `gh-check-ci-status`).

Add to Constraints: junior DO/DO NOT rules (use templates, format consistently, validate markdown).

### Count updates required

| File | Old value | New value |
|------|-----------|-----------|
| `agents/hierarchy.md` L5 narrative | "3 types (Implementation, Test, Documentation)" | "2 types (Implementation, Test)" |
| `agents/README.md` Level 5 heading | "(2 agents)" | "(1 agent)" |
| `agents/docs/agent-catalog.md` overview | "44 agents" | "43 agents" |
| `agents/docs/agent-catalog.md` footer | "44 ... 3 L5" | "43 ... 2 L5" |
| `agents/docs/onboarding.md` junior count | "3 junior types" | "2 junior types" |
| `agents/docs/onboarding.md` browse link | "44 agents" | "43 agents" |

### Commit message template

```
refactor(agents): consolidate <domain> engineer tiers from 3 to 2

Merge junior-<domain>-engineer (L5) into <domain>-engineer (L4),
consistent with the rationale in #<prior-issue> for junior tier consolidation.

Changes:
- Absorb junior scope into <domain>-engineer.md; set delegates_to: []
- Remove junior from <domain>-specialist delegates_to list
- Delete .claude/agents/junior-<domain>-engineer.md
- Update agents/hierarchy.md, README.md, agent-catalog.md, onboarding.md

All agent validation tests pass (0 errors).

Closes #<issue>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching for count updates by number alone | `grep -n "44\|31\|3 L5"` across docs | Multiple unrelated occurrences of these numbers; hard to target | Search for the full count phrase, e.g. "3 junior types" or "44 agents" |
| Assuming hierarchy.md table already correct | Skipped table check because it showed 31 | L5 narrative ("3 types") was still wrong even though table count was right | Always check both the table AND the narrative prose separately |
| Updating catalog Quick Reference table row | Tried to remove the Junior Documentation Engineer row without context | `old_string` not unique without surrounding rows | Include both flanking rows in `old_string` for uniqueness |

