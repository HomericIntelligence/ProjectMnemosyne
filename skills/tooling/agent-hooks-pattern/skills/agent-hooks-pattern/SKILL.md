---
name: agent-hooks-pattern
description: "Pattern for agent-scoped lifecycle hooks in Claude Code v2.1.0. Use when implementing custom agents with safety controls or tool restrictions."
user-invocable: false
---

# Agent-Scoped Hooks Pattern

Pattern for adding lifecycle hooks directly to agent frontmatter in Claude Code v2.1.0+.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | Document agent-scoped hooks pattern from Claude Code v2.1.0 |
| Outcome | Verified pattern for PreToolUse, PostToolUse, and Stop hooks in agent frontmatter |
| Source | Claude Code CHANGELOG v2.1.0 |

## When to Use

- Implementing custom agents with tool access restrictions
- Adding safety controls to junior/trainee agents (block dangerous commands)
- Creating read-only review agents (block Edit, Write, Bash)
- Enforcing agent-specific workflows with lifecycle hooks
- Adding once-per-session initialization hooks to agents

## Verified Workflow

### 1. Basic Agent Hooks

Add hooks directly to agent frontmatter:

```yaml
---
name: my-agent
description: Custom agent with lifecycle hooks
hooks:
  - type: PreToolUse
    once: true  # Run only once per session
  - type: PostToolUse
  - type: Stop
---

# Agent implementation
```

### 2. Junior Engineer Agent (Block Dangerous Tools)

```yaml
---
name: junior-engineer
description: Junior engineer agent with restricted tool access
hooks:
  - type: PreToolUse
    matcher: Bash
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Junior engineers cannot run Bash commands. Please ask a senior engineer."}'
---
```

### 3. Review Specialist Agent (Read-Only Enforcement)

```yaml
---
name: review-specialist
description: Code review agent with read-only access
hooks:
  - type: PreToolUse
    matcher: "(Edit|Write|Bash)"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Review agents are read-only. Cannot modify files or run commands."}'
  - type: PreToolUse
    matcher: "Task"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Review agents cannot spawn sub-agents."}'
---
```

### 4. Hook Types

**PreToolUse**: Runs before tool execution
- Can allow, deny, or ask for permission
- Can modify tool input (middleware)
- Supports `matcher` for specific tools

**PostToolUse**: Runs after tool execution
- Can process or log tool results
- Cannot modify output (read-only)

**Stop**: Runs when agent completes
- Cleanup operations
- Final reporting
- State persistence

### 5. Hook Options

```yaml
hooks:
  - type: PreToolUse
    once: true              # Run only once per session (NEW in v2.1.0)
    matcher: "Bash"         # Match specific tool (regex)
    hooks:
      - type: command       # Execute shell command
        command: "script.sh"
        timeout: 120        # Timeout in seconds
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Adding `disallowedTools` array to agent frontmatter | Field not supported in v2.1.0 - only CLI/settings.json support `--disallowedTools` | Use hooks with deny decision for tool blocking |
| SessionEnd hooks for user messages | SessionEnd hooks cannot display messages to users | Use UserPromptSubmit hooks for session-end messages |
| Blocking tools without proper deny message | Users confused why tool calls silently failed | Always include clear `message` field in deny responses |

## Results & Parameters

### Junior Engineer Agent Template

```yaml
---
name: junior-engineer
description: Trainee agent with restricted dangerous tool access
hooks:
  - type: PreToolUse
    matcher: "Bash"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Junior engineers cannot run Bash commands."}'
  - type: PreToolUse
    matcher: "WebFetch"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Junior engineers cannot fetch external URLs."}'
  - type: PreToolUse
    matcher: "Task"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Junior engineers cannot spawn sub-agents."}'
---
```

### Review Specialist Template (Read-Only)

```yaml
---
name: review-specialist
description: Code review agent with read-only enforcement
hooks:
  - type: PreToolUse
    matcher: "(Edit|Write|Bash|WebFetch|Task)"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Review agents are read-only. Use Read and Grep tools only."}'
---
```

### Hook Response Format

```json
{
  "decision": "allow" | "deny" | "ask",
  "message": "User-facing explanation",
  "updatedInput": "Modified tool input (optional, for middleware)"
}
```

## Key Insights

1. **Agent-scoped hooks > Global hooks**: Attach restrictions directly to agent definitions for better encapsulation
2. **Use `once: true` for initialization**: Prevent duplicate setup operations
3. **Clear deny messages**: Always explain why a tool was blocked
4. **Regex matchers**: Use `(Edit|Write|Bash)` for multiple tool blocking
5. **No `disallowedTools` in frontmatter**: Use hooks with deny decisions instead

## References

- Claude Code v2.1.0 CHANGELOG: Agent hooks field support
- Related skill: claude-plugin-format (plugin schema requirements)
- Related skill: retrospective-hook-integration (SessionEnd hooks)
