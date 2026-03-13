# Skill: Scope ShellCheck Suppressions to Template Subdirectory

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-19 |
| Issue | #722 |
| PR | #778 |
| Objective | Move template-specific shellcheck suppressions from root `.shellcheckrc` to `scylla/e2e/templates/.shellcheckrc` so non-template scripts in `scripts/` and `docker/` are fully checked |
| Outcome | Success — all 12 pre-commit hooks pass, 2209 tests pass |

## When to Use

- ShellCheck suppressions are needed only for a specific subdirectory (e.g., template files using Python `string.Template` syntax)
- Non-template shell scripts are getting false-positive suppression from a global `.shellcheckrc`
- You want to enable stricter checking in some directories while keeping suppressions in others

## How ShellCheck Finds Config Files

ShellCheck walks **up** from the file being checked, using the **first** `.shellcheckrc` it finds. This means:

- A `.shellcheckrc` in `scylla/e2e/templates/` applies **only** to files in that directory and below
- Files outside that directory walk up and find the root `.shellcheckrc`

This makes subdirectory `.shellcheckrc` files the cleanest way to scope suppressions.

## Verified Workflow

### Step 1: Create the subdirectory `.shellcheckrc`

```bash
# In the directory where false-positives are expected
cat > scylla/e2e/templates/.shellcheckrc << 'EOF'
# ShellCheck configuration for template files only
# These checks are disabled because templates use Python string.Template syntax:
#   - $variable  → substituted at runtime (not unused/unassigned)
#   - $$         → escaped dollar sign (causes SC1036/SC1088 parse errors)
#
# SC2034: Variable appears unused
# SC2154: Variable is referenced but not assigned
# SC1036: Invalid parentheses (false positive for $$ escaping)
# SC1088: Parsing stopped (false positive for $$ escaping)
disable=SC2034,SC2154,SC1036,SC1088
EOF
```

### Step 2: Clean up the root `.shellcheckrc`

Remove the suppression directives and replace with a comment explaining the scoping:

```bash
cat > .shellcheckrc << 'EOF'
# ShellCheck configuration for ProjectScylla
#
# Template-specific suppressions (SC2034, SC2154, SC1036, SC1088) are scoped to:
#   scylla/e2e/templates/.shellcheckrc
#
# SC1091 is suppressed per-invocation via args in .pre-commit-config.yaml
EOF
```

### Step 3: Run shellcheck to surface newly enabled warnings

```bash
pre-commit run shellcheck --all-files
```

Expect newly surfaced SC2034 warnings in non-template scripts — these are **legitimate issues** that were previously hidden. Fix them.

### Step 4: Fix legitimate surfaced warnings

Common patterns:

- **Unused color variables**: Remove `BLUE='\033[0;34m'` if only RED/GREEN/YELLOW are used
- **Unused intermediate variables**: Remove `PARENT_DIR=$(dirname "$REPO_DIR")` if never referenced
- **Dead code arrays**: Remove `VALID_TOOLS=(...)` arrays that are assigned but never iterated

### Step 5: Exclude archived/raw data directories from shellcheck

If you have archived shell scripts that shouldn't be linted (e.g., `docs/arxiv/` raw experiment data), add an exclude to `.pre-commit-config.yaml`:

```yaml
- id: shellcheck
  ...
  args: ['--exclude=SC1091']
  exclude: ^docs/arxiv/   # Add this
```

### Step 6: Verify everything passes

```bash
pre-commit run --all-files
pixi run python -m pytest tests/ -v
```

## Failed Attempts

None — the subdirectory `.shellcheckrc` approach worked on the first try.

The alternative approaches from the issue were intentionally skipped:

- **Option 2** (inline `# shellcheck disable=` comments): Requires modifying every template file; verbose and harder to maintain
- **Option 3** (file pattern config): ShellCheck doesn't natively support per-pattern configs; requires wrapper scripts

## Key Gotchas

### Tracked files in gitignored directories

If a shell script lives in a path matching a `.gitignore` pattern (e.g., `tests/claude-code/shared/skills/worktree/`), `git add` will fail with "paths are ignored". Use `git add -f` since the file is already tracked:

```bash
git add -f tests/claude-code/shared/skills/worktree/worktree-create/scripts/remove_worktree.sh
```

### ShellCheck config resolution is directory-based, not glob-based

ShellCheck does NOT support per-pattern rules like "apply SC2034 only to `*.template` files". The only way to scope rules to a file pattern is to ensure all matching files live in a dedicated subdirectory with its own `.shellcheckrc`.

## Results & Parameters

**Suppressions moved to subdirectory:**

| Code | Description | Reason in Templates |
|------|-------------|---------------------|
| SC2034 | Variable appears unused | `$variable` → runtime substitution |
| SC2154 | Variable referenced but not assigned | `$workspace` etc. from template context |
| SC1036 | Invalid parentheses | `$$` escaping in Python string.Template |
| SC1088 | Parsing stopped | `$$` escaping in Python string.Template |

**Files changed:**

- `scylla/e2e/templates/.shellcheckrc` — new, template-scoped suppressions
- `.shellcheckrc` — root, suppressions removed, comment only
- `.pre-commit-config.yaml` — added `exclude: ^docs/arxiv/` to shellcheck hook
- `scripts/docker_common.sh` — removed unused `BLUE` color variable
- `tests/claude-code/shared/skills/worktree/worktree-create/scripts/remove_worktree.sh` — removed unused `PARENT_DIR`
- `tests/claude-code/shared/skills/agent/agent-validate-config/scripts/validate_agent.sh` — removed unused `VALID_TOOLS` array
