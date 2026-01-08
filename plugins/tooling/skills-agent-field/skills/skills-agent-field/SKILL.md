---
name: skills-agent-field
description: "Pattern for specifying which agent type should execute a skill using the agent field in Claude Code v2.1.0."
user-invocable: false
---

# Skills Agent Field Pattern

Pattern for routing skills to specific agent types using the `agent` field in Claude Code v2.1.0+.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | Document skills agent field pattern from Claude Code v2.1.0 |
| Outcome | Verified pattern for routing skills to specialized agents |
| Source | Claude Code CHANGELOG v2.1.0 |

## When to Use

- Creating skills that require specialized agent capabilities
- Routing Mojo syntax skills to Mojo validator agents
- Directing GitHub workflow skills to implementation engineers
- Assigning code review skills to review specialist agents
- Enforcing skill execution by specific agent types

## Verified Workflow

### 1. Basic Agent Assignment

Add `agent` field to skill frontmatter:

```yaml
---
name: mojo-syntax-validator
description: Validate Mojo code syntax
agent: mojo-specialist  # Route to Mojo specialist agent
---
```

### 2. Mojo Skills → Syntax Validators

```yaml
---
name: mojo-simd-optimize
description: Apply SIMD optimizations to Mojo code
agent: mojo-optimization-specialist
category: optimization
---
```

```yaml
---
name: mojo-memory-check
description: Verify memory safety in Mojo code
agent: mojo-memory-specialist
category: testing
---
```

### 3. GitHub Skills → Implementation Engineers

```yaml
---
name: gh-create-pr-linked
description: Create PRs linked to GitHub issues
agent: implementation-engineer
category: tooling
---
```

```yaml
---
name: gh-implement-issue
description: End-to-end implementation workflow for GitHub issues
agent: code-review-orchestrator
category: tooling
---
```

### 4. Quality Skills → Review Specialists

```yaml
---
name: quality-security-scan
description: Scan code for security vulnerabilities
agent: security-review-specialist
category: architecture
---
```

```yaml
---
name: quality-complexity-check
description: Analyze code complexity metrics
agent: code-quality-specialist
category: architecture
---
```

### 5. Skill Routing Patterns

**By Language**:
- `mojo-*` skills → `mojo-specialist`, `mojo-validator`
- `python-*` skills → `python-specialist`

**By Task Type**:
- `gh-*` skills → `implementation-engineer`, `code-review-orchestrator`
- `quality-*` skills → `review-specialist`, `security-specialist`
- `test-*` skills → `test-engineer`, `qa-specialist`

**By Complexity**:
- Simple skills → `junior-engineer`
- Complex skills → `senior-engineer`
- Architecture skills → `architect`

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Using agent field without defining agents | Skill fails to execute if agent doesn't exist | Define agents before referencing in skills |
| Circular agent dependencies | Agent A calls skill requiring Agent B which calls skill requiring Agent A | Design clear agent hierarchy with delegation patterns |
| Over-specialization | Creating too many agent types fragments knowledge | Start with broad agents, specialize only when needed |

## Results & Parameters

### Mojo Skills Template

```yaml
---
name: mojo-skill-name
description: Mojo-specific functionality
agent: mojo-specialist
category: optimization | testing | debugging
tags: ["mojo", "performance", "memory-safety"]
---
```

### GitHub Workflow Skills Template

```yaml
---
name: gh-skill-name
description: GitHub workflow automation
agent: implementation-engineer
category: tooling
tags: ["github", "workflow", "automation"]
---
```

### Code Review Skills Template

```yaml
---
name: review-skill-name
description: Code quality and review automation
agent: review-specialist
category: architecture | testing
tags: ["code-review", "quality", "standards"]
---
```

### Agent Type Naming Conventions

**Specialist Agents**:
- `{language}-specialist`: Language-specific expertise (mojo-specialist, python-specialist)
- `{domain}-specialist`: Domain expertise (security-specialist, performance-specialist)

**Role-Based Agents**:
- `junior-engineer`: Limited tool access, simple tasks
- `senior-engineer`: Full access, complex implementations
- `architect`: System design, architectural decisions
- `reviewer`: Read-only, code review and analysis

**Orchestrator Agents**:
- `code-review-orchestrator`: Coordinates PR review workflows
- `implementation-orchestrator`: Manages multi-step implementations
- `test-orchestrator`: Coordinates testing workflows

## Key Insights

1. **Agent hierarchy matters**: Design clear delegation patterns to avoid circular dependencies

2. **Language-specific routing**: Use `agent` field to route language-specific skills to specialized validators

3. **Role-based specialization**: Match skill complexity to agent capability level

4. **Marketplace compatibility**: Skills with `agent` field work across repositories with different agent architectures

5. **Optional field**: Skills without `agent` field execute on default/current agent

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Template updates and documentation | [notes.md](../references/notes.md) |

## References

- Claude Code v2.1.0 CHANGELOG: Skills agent field
- Related skill: agent-hooks-pattern (agent lifecycle hooks)
- Related skill: claude-plugin-format (plugin schema requirements)
