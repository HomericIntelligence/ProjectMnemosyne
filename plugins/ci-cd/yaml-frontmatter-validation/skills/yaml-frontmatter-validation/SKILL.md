---
name: yaml-frontmatter-validation
description: "Fix CI failures caused by missing YAML frontmatter in SKILL.md files. Use when plugin validation fails with 'missing YAML frontmatter' errors across multiple PRs."
user-invocable: false
category: ci-cd
date: 2026-01-08
---

# YAML Frontmatter Validation Fixes

Systematic approach to diagnosing and fixing CI validation failures across multiple PRs when the root cause is missing YAML frontmatter in SKILL.md files.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | Fix CI failures on 5 open PRs (4 with failures) caused by missing YAML frontmatter |
| Outcome | ✅ Successfully fixed all 5 PRs - all CI now passing |
| Strategy | Fix main branch first, then fix PR-specific issues, then rebase |

## When to Use

Use this skill when you encounter:

1. **Multiple PRs failing with similar validation errors** - Same error appearing across different PRs suggests shared root cause
2. **"SKILL.md missing YAML frontmatter" errors** - Validation script reports files don't start with `---`
3. **Plugin name validation failures** - Invalid characters in plugin names (e.g., periods in `claude-code-v2.1-adoption`)
4. **CI failures that shouldn't affect feature branches** - Errors in main branch plugins affecting all PRs
5. **Need to fix both main and feature branches** - Systematic approach required for cascading fixes

### Trigger Patterns

```text
FAIL: plugin-name
  Errors:
    - SKILL.md missing YAML frontmatter (must start with ---)
```

```text
FAIL: plugin-name
  Errors:
    - Invalid name format 'plugin-v2.1-name' (use lowercase, numbers, hyphens)
```

## Verified Workflow

### Phase 1: Analyze the Failures

**What worked:**

1. **List all open PRs with CI status:**
   ```bash
   gh pr list --state open --json number,title,headRefName,statusCheckRollup --limit 20
   ```

2. **Get failure details for each failing run:**
   ```bash
   gh run view <run-id> --log 2>/dev/null | grep -E "(PASS|FAIL):" | head -20
   gh run view <run-id> --log 2>/dev/null | grep -A 10 "FAIL: plugin-name"
   ```

3. **Identify patterns:**
   - Common failures across multiple PRs → likely main branch issue
   - PR-specific failures → branch-specific issues
   - Count unique failing plugins to understand scope

**Example from this session:**
- 5 open PRs, 4 with failures
- 2 plugins failing on main: `retry-transient-errors`, `judge-criteria-enhancement`
- 2 PR-specific issues: `claude-code-v2.1-adoption` (period in name), `global-semaphore-parallelism` (missing frontmatter)

### Phase 2: Fix Main Branch First

**Critical principle:** Fix shared root causes on main before touching feature branches.

**What worked:**

1. **Checkout main and pull latest:**
   ```bash
   git checkout main
   git pull
   ```

2. **Add YAML frontmatter to each failing plugin:**
   ```yaml
   ---
   name: plugin-name
   description: "Brief description with trigger conditions. Use when..."
   user-invocable: false
   ---
   ```

3. **Verify fixes locally:**
   ```bash
   python3 scripts/validate_plugins.py 2>&1 | grep -E "(PASS|FAIL): (plugin1|plugin2)"
   ```

4. **Commit and push to main:**
   ```bash
   git add plugins/.../SKILL.md
   git commit -m "fix: add missing YAML frontmatter to <plugin-names> skills"
   git push
   ```

**Why this order matters:**
- Fixes propagate to all branches during rebase
- Reduces duplicate work across PRs
- Ensures consistent fixes

### Phase 3: Fix PR-Specific Issues

**What worked:**

For each PR with unique failures:

1. **Checkout the feature branch:**
   ```bash
   git checkout <branch-name>
   git pull --rebase origin main  # Pick up main branch fixes
   ```

2. **Fix PR-specific validation errors:**

   **For missing frontmatter:**
   - Add YAML frontmatter as in Phase 2

   **For invalid plugin names (periods, underscores, uppercase):**
   ```bash
   # Update plugin.json name field
   # Update SKILL.md frontmatter name field
   # Rename directories
   git mv plugins/category/old-name plugins/category/new-name
   git mv plugins/category/new-name/skills/old-name plugins/category/new-name/skills/new-name

   # Regenerate marketplace
   python3 scripts/generate_marketplace.py
   ```

3. **Verify and commit:**
   ```bash
   python3 scripts/validate_plugins.py 2>&1 | grep "FAIL:"
   git add -A
   git commit -m "fix: <specific fix description>"
   git push --force-with-lease
   ```

### Phase 4: Rebase Remaining PRs

**What worked:**

For PRs that only had main branch failures (now fixed):

```bash
git fetch origin <branch-name>
git checkout <branch-name>
git pull --rebase origin main
git push --force-with-lease
```

**Handle merge conflicts:**
- Template files often conflict (e.g., `templates/experiment-skill/skills/SKILL_NAME/SKILL.md`)
- Keep both changes when adding new optional fields
- Mark resolved: `git add <file> && git rebase --continue`

### Phase 5: Verify All PRs

**What worked:**

```bash
gh pr list --state open --json number,title,statusCheckRollup
```

Check for `"conclusion":"SUCCESS"` in all PRs.

**Wait for CI if needed:**
```bash
sleep 30 && gh pr view <number> --json statusCheckRollup --jq '.statusCheckRollup[] | select(.workflowName == "Validate Plugins") | {status: .status, conclusion: .conclusion}'
```

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Fixing PR branches before main | Had to add same frontmatter fixes to every PR individually | Always fix main branch shared issues first, then rebase PRs to inherit fixes |
| Using `git push` instead of `git push --force-with-lease` after rebase | Push rejected because history was rewritten | After rebase, must use `--force-with-lease` to safely force-push |
| Not checking local validation before pushing | Pushed invalid changes, triggering another CI failure | Always run `python3 scripts/validate_plugins.py` locally before pushing |
| Trying to read files before Edit without explicit Read | Edit tool error: "File has not been read yet" | Must use Read tool before Edit, even if file was previously read and modified |

## Results & Parameters

### Validation Rules (from `scripts/validate_plugins.py`)

**Plugin name requirements:**
- Regex: `^[a-z0-9-]+$`
- Lowercase only
- Numbers allowed
- Hyphens allowed
- NO periods, underscores, uppercase

**YAML frontmatter requirements:**
```yaml
---
name: plugin-name  # Must match directory name
description: "Trigger conditions..."  # 20+ chars
user-invocable: false  # or true
# Optional fields:
category: ci-cd  # One of 8 categories
date: YYYY-MM-DD
agent: specialist-name
---
```

### Fix Strategy Decision Matrix

| Scenario | Action |
|----------|--------|
| Same error on multiple PRs | Fix on main first |
| Plugin name validation error | Rename plugin (directories + files) |
| Missing frontmatter | Add frontmatter block at file start |
| PR only needs main fixes | Rebase on main |
| PR has unique failures | Fix on branch, then rebase |
| Merge conflict in template | Keep both changes if adding optional fields |

### Commands Used

```bash
# Analysis
gh pr list --state open --json number,title,statusCheckRollup --limit 20
gh run view <run-id> --log 2>/dev/null | grep -A 10 "FAIL:"

# Local validation
python3 scripts/validate_plugins.py 2>&1 | grep "FAIL:"

# Git workflow
git checkout main && git pull
git checkout -b fix/<issue>
git add <files>
git commit -m "fix: <description>"
git push --force-with-lease  # After rebase

# Rebase
git pull --rebase origin main
git rebase --continue  # After resolving conflicts

# Rename plugin
git mv plugins/category/old plugins/category/new
python3 scripts/generate_marketplace.py
```

### Session Results

**Before:**
- 5 open PRs
- 4 PRs with failing CI
- 6 unique failing plugins (2 on main, 4 PR-specific)

**After:**
- 5 open PRs
- 0 PRs with failing CI ✅
- All validations passing

**Commits:**
1. Main: `4b8b469` - Added frontmatter to 2 plugins
2. PR #74: `1fe4ca8` - Renamed `claude-code-v2.1-adoption` → `claude-code-v21-adoption`
3. PR #68: `8b80c67` - Added frontmatter to `global-semaphore-parallelism`
4. PR #73, #69, #72: Rebased on main

## Key Takeaways

1. **Fix main first, then branches** - Shared issues on main propagate to all PRs. Fix once, rebase everywhere.

2. **Use CI logs to identify patterns** - Same error across PRs = main branch issue. Unique errors = branch-specific.

3. **Plugin naming is strict** - Only `[a-z0-9-]` allowed. No periods (`.`), underscores (`_`), or uppercase.

4. **YAML frontmatter is mandatory** - Must start with `---` and include `name` and `description` fields.

5. **Validate locally before pushing** - Run `scripts/validate_plugins.py` to catch errors before CI.

6. **Force-push safely after rebase** - Use `--force-with-lease` not `--force` to avoid overwriting others' work.

7. **Template conflicts are common** - When rebasing PRs that add optional fields, keep both changes in merge conflicts.

8. **CI can lag behind** - Use `gh pr view <number> --json statusCheckRollup` or wait 30s to verify success.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #74, #73, #72, #69, #68 | Fixed 4 failing PRs by adding frontmatter and renaming plugins. See [notes.md](../references/notes.md) for CI logs and commands. |

## References

- `scripts/validate_plugins.py` - Plugin validation script
- CLAUDE.md - Plugin standards documentation
- Related skill: `claude-plugin-format` - Plugin structure requirements
- Related skill: `retrospective-hook-integration` - CI/CD workflow patterns
