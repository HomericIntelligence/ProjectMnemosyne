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

## Results & Parameters

### Consolidation from ProjectOdyssey issue #3146

**Before**: 4 implementation tiers

```text
implementation-specialist (L3)
  → senior-implementation-engineer (L4)
  → implementation-engineer (L4)
  → junior-implementation-engineer (L5)
  → implementation-specialist (L3, also receives)
```

**After**: 2 tiers

```text
implementation-specialist (L3)
  → implementation-engineer (L4, full spectrum)
```

**Agent count delta**: 44 → 42

**Key merge decisions**:

- Added `mojo-simd-optimize`, `mojo-memory-check` skills from senior tier
- Added `quality-fix-formatting`, `gh-check-ci-status` skills from junior tier
- Added performance-profiling workflow steps from senior tier
- Added anti-pattern reference and escalation rules from junior tier
- Kept two concrete examples: one standard, one performance-critical
- Removed `hooks.PreToolUse` Bash block (junior-only restriction, not needed for consolidated agent)

### Validation output

```text
Total files: 42
Passed: 42
Failed: 0
Total errors: 0
```

### Hierarchy counts to update

| Section | Before | After |
|---------|--------|-------|
| Level 4 count line | "6 agents" | "5 agents" |
| Level 5 count line | "3 types" | "2 types" |
| Agent Count table L4 | 6 | 5 |
| Agent Count table L5 | 3 | 2 |
| Total | 44 | 42 |
| Diagram box L4 | Lists senior + regular | Lists only regular |
| Diagram box L5 | Lists 3 juniors | Lists 2 juniors |

### Consolidation from ProjectOdyssey issue #3332 (junior-only variant)

**Before**: 3 test tiers

```text
test-specialist (L3)
  → test-engineer (L4)
  → junior-test-engineer (L5)
```

**After**: 2 tiers

```text
test-specialist (L3)
  → test-engineer (L4, handles all complexity)
```

**Agent count delta**: 31 → 30

**Key differences from implementation consolidation**:

- No senior tier to merge — only junior-to-middle merge needed
- `test-engineer.md` already had `Bash` tool access (unlike junior which blocked it via hook)
- Removed `hooks.PreToolUse` Bash block from junior; test-engineer retained Bash access
- Cross-references in `agents/hierarchy.md`, `agents/README.md`, `agents/docs/agent-catalog.md`,
  `scripts/agents/setup_agents.sh`, and `docs/dev/agent-claude4-update-status.md` all needed updating
- `test-specialist.md` `delegates_to` changed from `[test-engineer, junior-test-engineer]` to `[test-engineer]`

**Validation output**:

```text
Total files: 30
Passed: 30
Failed: 0
Total errors: 0
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3146 — implementation engineer tier consolidation | See Results above |
| ProjectOdyssey | Issue #3332 — test engineer tier consolidation (junior-only variant) | See Results above |
