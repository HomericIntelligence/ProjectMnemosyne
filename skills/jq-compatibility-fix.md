---
name: jq-compatibility-fix
description: Fix jq syntax errors caused by array concatenation with conditionals
  in older jq versions
category: debugging
date: 2026-03-12
version: 1.0.0
user-invocable: false
---
# Skill: jq-compatibility-fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-12 |
| Objective | Fix jq syntax error `unexpected '+', expecting '}'` in install-agent-cli.sh on older jq versions |
| Outcome | Success -- replaced in-jq array concatenation with bash-built JSON array passed via --argjson |

## When to Use

Use this skill when:

- jq fails with `syntax error, unexpected '+', expecting '}'`
- The failing expression uses `] + (if $var then [...] else [] end)` array concatenation
- The script works on jq 1.6+ but fails on older jq versions (1.5 and some distro-patched builds)
- `--argjson` with conditional expressions causes parse errors

**Don't use when:**

- The jq error is unrelated to array concatenation (e.g., missing quotes, bad JSON input)
- The target environment guarantees jq 1.6+

## Verified Workflow

### 1. Identify the problematic jq pattern

Look for array concatenation with conditionals inside jq expressions:

```jq
files: [
    ($install_dir + "/file1.sh"),
    ($helpers_dir + "/file2.sh")
] + (if $condition then [($dir + "/file3.md")] else [] end),
```

### 2. Build the array in bash instead

Move the conditional logic to bash and construct the JSON array as a string:

```bash
local files_json
files_json="[\"${INSTALL_DIR}/file1.sh\", \"${HELPERS_DIR}/file2.sh\""
if [[ "$condition" == "true" ]]; then
    files_json+=", \"${dir}/file3.md\""
fi
files_json+="]"
```

### 3. Pass the pre-built array via --argjson

Replace the inline array construction with:

```bash
jq -n \
    --argjson files "$files_json" \
    '{ files: $files }'
```

### 4. Verify

Test the fixed expression produces correct JSON output:

```bash
echo "$result" | jq .
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Before (broken on old jq)

```jq
files: [
    ($install_dir + "/aimaestro-agent.sh"),
    ($helpers_dir + "/agent-helper.sh")
] + (if $skill_installed then [($skill_dir + "/SKILL.md")] else [] end),
```

### After (compatible)

```bash
local files_json
files_json="[\"${INSTALL_DIR}/aimaestro-agent.sh\", \"${HELPERS_DIR}/agent-helper.sh\""
if [[ "$skill_installed_json" == "true" ]]; then
    files_json+=", \"${skill_dir}/SKILL.md\""
fi
files_json+="]"

# Then in jq: --argjson files "$files_json" and use files: $files
```

### Related issue

- [GitHub Issue #272](https://github.com/23blocks-OS/ai-maestro/issues/272)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ai-maestro | Issue #272 - jq syntax error in install-agent-cli.sh | [notes.md](../../references/notes.md) |
