# Raw Notes: jq-compatibility-fix

## Session Context

**Date**: 2026-03-12
**Repository**: ai-maestro (23blocks-OS/ai-maestro)
**Trigger**: `install-agent-cli.sh` fails with jq syntax error during installation

## Error Message

```
jq: error: syntax error, unexpected '+', expecting '}'
```

Occurs at line ~436 of `~/ai-maestro/install-agent-cli.sh`.

## Root Cause

The jq expression uses `] + (if $skill_installed then [...] else [] end)` for conditional
array concatenation. This syntax works on jq 1.6+ but fails on older versions (1.5 and
some distro-packaged builds) where the `+` operator for array concatenation inside complex
object literals is not fully supported.

## Exact Fix Applied

**File**: `~/ai-maestro/install-agent-cli.sh` (lines 416-443)

**Before**:
```bash
manifest=$(jq -n \
    --arg version "$INSTALLER_VERSION" \
    --arg installed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg platform "$(uname -s)" \
    --arg install_dir "$INSTALL_DIR" \
    --arg helpers_dir "$HELPERS_DIR" \
    --arg skill_dir "$skill_dir" \
    --argjson path_modified "$path_modified_json" \
    --argjson skill_installed "$skill_installed_json" \
    --arg shell_config "${shell_config:-}" \
    '{
        version: $version,
        installed_at: $installed_at,
        platform: $platform,
        install_dir: $install_dir,
        helpers_dir: $helpers_dir,
        skill_dir: $skill_dir,
        files: [
            ($install_dir + "/aimaestro-agent.sh"),
            ($helpers_dir + "/agent-helper.sh")
        ] + (if $skill_installed then [($skill_dir + "/SKILL.md")] else [] end),
        path_modified: $path_modified,
        skill_installed: $skill_installed,
        shell_config_file: $shell_config
    }')
```

**After**:
```bash
# Build files array in bash for compatibility with older jq versions
local files_json
files_json="[\"${INSTALL_DIR}/aimaestro-agent.sh\", \"${HELPERS_DIR}/agent-helper.sh\""
if [[ "$skill_installed_json" == "true" ]]; then
    files_json+=", \"${skill_dir}/SKILL.md\""
fi
files_json+="]"

manifest=$(jq -n \
    --arg version "$INSTALLER_VERSION" \
    --arg installed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg platform "$(uname -s)" \
    --arg install_dir "$INSTALL_DIR" \
    --arg helpers_dir "$HELPERS_DIR" \
    --arg skill_dir "$skill_dir" \
    --argjson path_modified "$path_modified_json" \
    --argjson skill_installed "$skill_installed_json" \
    --argjson files "$files_json" \
    --arg shell_config "${shell_config:-}" \
    '{
        version: $version,
        installed_at: $installed_at,
        platform: $platform,
        install_dir: $install_dir,
        helpers_dir: $helpers_dir,
        skill_dir: $skill_dir,
        files: $files,
        path_modified: $path_modified,
        skill_installed: $skill_installed,
        shell_config_file: $shell_config
    }')
```

## Verification

Tested with jq 1.7 — produces correct JSON with all fields including the conditional
`SKILL.md` entry in the files array.

## GitHub Issue

Filed as: https://github.com/23blocks-OS/ai-maestro/issues/272