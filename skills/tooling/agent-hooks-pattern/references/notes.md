# Agent Hooks Pattern - Implementation Notes

## Context

Documented agent-scoped hooks pattern from Claude Code v2.1.0 CHANGELOG for ProjectMnemosyne skills marketplace.

## Examples from CHANGELOG

### Basic Agent Hooks

```yaml
---
name: my-agent
hooks:
  - type: PreToolUse
    once: true
  - type: PostToolUse
  - type: Stop
---
```

### Tool Blocking Example

Using hooks to block specific tools (reframes the user's requested `disallowedTools` field, which is not supported in agent frontmatter):

```yaml
---
name: restricted-agent
hooks:
  - type: PreToolUse
    matcher: "Bash"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "This agent cannot run Bash commands"}'
---
```

## Verified On

| Project | Context | Status |
|---------|---------|--------|
| ProjectMnemosyne | Documentation skill creation | ✅ Verified from v2.1.0 CHANGELOG |

## Key Findings

1. **No `disallowedTools` in frontmatter**: The user requested this field, but it's not supported in v2.1.0. Only CLI `--disallowedTools` and settings.json work.

2. **Hooks provide better control**: PreToolUse hooks with deny decisions offer more flexibility than a simple disallowedTools array.

3. **once field is critical**: Prevents duplicate hook execution for initialization hooks.

## Links

- [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
