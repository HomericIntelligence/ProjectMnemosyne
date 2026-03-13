# Skill: validate-agent-tools-content

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #780 |
| PR | #825 |
| Category | tooling |
| Outcome | Success — 2209 tests pass, pre-commit passes |

Objective: Upgrade the bash agent validation script to check individual tool names against a known valid set, catching misconfigured agent files that reference non-existent tools.

## When to Use

- Adding content validation to a bash YAML field validator
- Upgrading format-only validation (`[...]` check) to per-item content validation
- Synchronizing a `VALID_*` array across bash and Python validators
- Any time a bash validator has a declared-but-unused constant array

## Verified Workflow

### 1. Identify the authoritative source for the valid set

Before expanding a `VALID_*` array, check whether a Python counterpart already has the canonical list:

```bash
grep -r "VALID_TOOLS\|valid_tools" . --include="*.py" | grep -v ".git"
```

In this project `scripts/agents/validate_agents.py` was authoritative. Always align bash and Python validators.

### 2. Pattern: bracket-strip → comma-split → trim → validate each

Reuse the same loop structure as the existing phase validation (already in the same file):

```bash
VALID_TOOLS=("Read" "Write" "Edit" "Bash" "Grep" "Glob" "Task" \
  "WebFetch" "WebSearch" "TodoWrite" "SlashCommand" \
  "AskUserQuestion" "NotebookEdit" "BashOutput" "KillShell")

TOOLS_LINE=$(echo "$FRONTMATTER" | grep "^tools:" | cut -d':' -f2-)

if [[ "$TOOLS_LINE" =~ \[.*\] ]]; then
    echo "✅ Tools field properly formatted"
    # Strip brackets, split on commas
    TOOLS_CONTENT="${TOOLS_LINE//[/}"
    TOOLS_CONTENT="${TOOLS_CONTENT//]/}"
    IFS=',' read -ra TOOL_LIST <<< "$TOOLS_CONTENT"
    for tool_entry in "${TOOL_LIST[@]}"; do
        tool_name=$(echo "$tool_entry" | tr -d ' ')
        [[ -z "$tool_name" ]] && continue
        TOOL_VALID=false
        for valid_tool in "${VALID_TOOLS[@]}"; do
            if [[ "$tool_name" == "$valid_tool" ]]; then
                TOOL_VALID=true
                break
            fi
        done
        if [[ "$TOOL_VALID" == "true" ]]; then
            echo "✅ Valid tool: $tool_name"
        else
            echo "❌ Invalid tool: $tool_name"
            echo "   Valid tools: ${VALID_TOOLS[*]}"
            ((ERRORS++))
        fi
    done
else
    echo "⚠️  Tools field may be improperly formatted"
fi
```

Key points:

- `"${TOOLS_LINE//[/}"` — bash parameter expansion strips `[` (no regex needed)
- `[[ -z "$tool_name" ]] && continue` — skip empty tokens from trailing commas
- Preserve `⚠️` (no `ERRORS++`) for malformed format; only `❌` increments errors
- The `Task` tool is valid — real agent configs use it; don't use the SKILL.md subset

### 3. Update SKILL.md error table

Add a row for the new error type so users know what tools are valid:

```markdown
| Unknown tool name | Use: Read, Write, Edit, Bash, Grep, Glob, Task, WebFetch, WebSearch, TodoWrite, SlashCommand, AskUserQuestion, NotebookEdit, BashOutput, KillShell |
```

### 4. Smoke-test before running full suite

```bash
# Valid tools — expect exit 0
cat > /tmp/good.md << 'EOF'
---
name: test-agent
role: specialist
level: 3
phase: Plan
description: Test
tools: [Read, Write, Bash]
---
body
EOF
bash tests/.../validate_agent.sh /tmp/good.md

# Invalid tool — expect exit 1 + "❌ Invalid tool: FakeTool"
cat > /tmp/bad.md << 'EOF'
---
...
tools: [Read, FakeTool, Bash]
---
body
EOF
bash tests/.../validate_agent.sh /tmp/bad.md
```

### 5. Run full test suite

```bash
pixi run python -m pytest tests/ -v
```

## Failed Attempts

None in this session. The implementation was straightforward by following the existing phase-validation pattern already in the file.

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Tools format required | `[Tool1, Tool2, ...]` (brackets + comma-separated) |
| Malformed format handling | `⚠️` warning only, no error increment |
| Invalid tool handling | `❌` error + hint, `ERRORS++` |
| Valid tool count | 15 tools |

## Files Changed

| File | Change |
|------|--------|
| `tests/claude-code/shared/skills/agent/agent-validate-config/scripts/validate_agent.sh` | Expand `VALID_TOOLS`, add per-tool validation loop |
| `tests/claude-code/shared/skills/agent/agent-validate-config/SKILL.md` | Add unknown tool name row to Error Handling table |

## References

- Issue #780 — original request
- PR #825 — implementation
- `scripts/agents/validate_agents.py` — authoritative Python validator (keep in sync)
