---
name: advise
description: Search team knowledge before starting work. Use when starting experiments, debugging unfamiliar errors, or before implementing features with unknowns.
user-invocable: false
---

# /advise

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2025-12-29 |
| Objective | Search the skills registry for relevant prior learnings before starting work |
| Outcome | ✅ Operational |

## When to Use

- Starting a new experiment or task
- Before implementing a feature with unknowns
- When debugging an unfamiliar error
- When you want to avoid repeating past mistakes

## Search Priority

1. **Failed Attempts first** — Most valuable, prevents wasted effort
2. **Exact tag matches** — High confidence relevance
3. **Description keywords** — Broader matches
4. **Copy-paste configs** — When available, include them

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
| --------- | ----------- | ---------------- |
| Searching only by exact tag match | Missed relevant skills with different tags | Include description keyword matching |
| Not prioritizing Failed Attempts | Users repeated mistakes | Show failures first in output |
| Vague search queries | Too many irrelevant results | Encourage users to be specific about context |
| Reading all SKILL.md files | Performance issues with large registry | Filter by category/tags first, then read top 5 |
| Not showing parameter snippets | Users had to open files manually | Include copy-paste configs in summary |

## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `commands/advise.md` for the full command implementation
- See `documentation-patterns` for writing searchable skills
