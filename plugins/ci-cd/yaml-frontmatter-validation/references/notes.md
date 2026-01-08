# YAML Frontmatter Validation - Session Notes

Session date: 2026-01-08

## Initial Problem

User request: "Lets fix failing CI/CD runs on the open PR's"

## Analysis Phase

### Step 1: List Open PRs

```bash
gh pr list --state open --json number,title,headRefName,statusCheckRollup --limit 20
```

**Results:**
- PR #74: `skill/tooling/claude-code-v2.1-adoption` - 1 failure (FAILURE)
- PR #73: `feature/hooks-once-field` - 1 failure (FAILURE)
- PR #72: `feature/skills-agent-field` - No CI status
- PR #69: `skill/debugging/resume-crash-debugging` - 1 failure (FAILURE)
- PR #68: `skill/debugging/global-semaphore-parallelism` - 1 failure (FAILURE)

All failures from workflow: "Validate Plugins"

### Step 2: Get Failure Details

Extracted failing plugins from CI logs:

**PR #74** (3 failures):
- `claude-code-v2.1-adoption` - Invalid name format (has period)
- `retry-transient-errors` - Missing YAML frontmatter
- `judge-criteria-enhancement` - Missing YAML frontmatter

**PR #73** (2 failures):
- `retry-transient-errors` - Missing YAML frontmatter
- `judge-criteria-enhancement` - Missing YAML frontmatter

**PR #69** (2 failures):
- `retry-transient-errors` - Missing YAML frontmatter
- `judge-criteria-enhancement` - Missing YAML frontmatter

**PR #68** (3 failures):
- `retry-transient-errors` - Missing YAML frontmatter
- `global-semaphore-parallelism` - Missing YAML frontmatter
- `judge-criteria-enhancement` - Missing YAML frontmatter

### Step 3: Identify Patterns

**Common failures (on main branch):**
- `retry-transient-errors` - Appears in all 4 failing PRs
- `judge-criteria-enhancement` - Appears in all 4 failing PRs

**PR-specific failures:**
- `claude-code-v2.1-adoption` - Only on PR #74 (invalid name with period)
- `global-semaphore-parallelism` - Only on PR #68 (missing frontmatter on feature branch)

## Fix Implementation

### Fix 1: Main Branch (commit 4b8b469)

**Branch:** `main`

**Files modified:**
1. `plugins/debugging/retry-transient-errors/skills/retry-transient-errors/SKILL.md`
2. `plugins/evaluation/judge-criteria-enhancement/skills/judge-criteria-enhancement/SKILL.md`

**Changes:** Added YAML frontmatter to both files:

```yaml
---
name: retry-transient-errors
description: "Fix git clone failures caused by transient network errors. Use when experiencing connection reset, curl 56, or timeout errors in subprocess calls."
user-invocable: false
---
```

```yaml
---
name: judge-criteria-enhancement
description: "Add new evaluation criteria to LLM judge systems. Use when penalizing over-engineering, fixing result validation, or adding proportionality scoring."
user-invocable: false
---
```

**Verification:**
```bash
python3 scripts/validate_plugins.py 2>&1 | grep -E "(PASS|FAIL):\s+(retry-transient-errors|judge-criteria-enhancement)"
```
Output:
```
PASS: judge-criteria-enhancement
PASS: retry-transient-errors
```

**Commit:**
```bash
git add plugins/debugging/retry-transient-errors/skills/retry-transient-errors/SKILL.md plugins/evaluation/judge-criteria-enhancement/skills/judge-criteria-enhancement/SKILL.md
git commit -m "fix: add missing YAML frontmatter to retry-transient-errors and judge-criteria-enhancement skills"
git push
```

### Fix 2: PR #74 - Rename Plugin (commit 1fe4ca8)

**Branch:** `skill/tooling/claude-code-v2.1-adoption`

**Problem:** Plugin name `claude-code-v2.1-adoption` contains period (`.`), which violates validation regex `^[a-z0-9-]+$`

**Actions:**

1. Rebased on main to pick up frontmatter fixes:
   ```bash
   git checkout skill/tooling/claude-code-v2.1-adoption
   git pull --rebase origin main
   ```

2. Updated plugin name in files:
   - `plugins/tooling/claude-code-v2.1-adoption/.claude-plugin/plugin.json`: Changed `name` to `claude-code-v21-adoption`
   - `plugins/tooling/claude-code-v2.1-adoption/skills/claude-code-v2.1-adoption/SKILL.md`: Changed frontmatter `name` to `claude-code-v21-adoption`

3. Renamed directories:
   ```bash
   git mv plugins/tooling/claude-code-v2.1-adoption plugins/tooling/claude-code-v21-adoption
   git mv plugins/tooling/claude-code-v21-adoption/skills/claude-code-v2.1-adoption plugins/tooling/claude-code-v21-adoption/skills/claude-code-v21-adoption
   ```

4. Regenerated marketplace:
   ```bash
   python3 scripts/generate_marketplace.py
   # Output: Generated .claude-plugin/marketplace.json (Plugins indexed: 132)
   ```

5. Verified:
   ```bash
   python3 scripts/validate_plugins.py 2>&1 | grep -E "(PASS|FAIL):\s+claude-code-v2"
   # Output: PASS: claude-code-v21-adoption
   ```

6. Committed and pushed:
   ```bash
   git add -A
   git commit -m "fix: rename claude-code-v2.1-adoption to claude-code-v21-adoption (remove period)"
   git push --force-with-lease
   ```

### Fix 3: PR #68 - Add Frontmatter (commit 8b80c67)

**Branch:** `skill/debugging/global-semaphore-parallelism`

**Problem:** New plugin on feature branch missing YAML frontmatter

**Actions:**

1. Checked out branch:
   ```bash
   git fetch origin skill/debugging/global-semaphore-parallelism
   git checkout skill/debugging/global-semaphore-parallelism
   ```

2. Added frontmatter to `plugins/debugging/global-semaphore-parallelism/skills/global-semaphore-parallelism/SKILL.md`:
   ```yaml
   ---
   name: global-semaphore-parallelism
   description: "Implement global parallelism control using shared semaphores. Use when limiting concurrent workers across multiple process pools or fixing per-tier parallelism issues."
   user-invocable: false
   ---
   ```

3. Verified:
   ```bash
   python3 scripts/validate_plugins.py 2>&1 | grep -E "(PASS|FAIL):\s+global-semaphore-parallelism"
   # Output: PASS: global-semaphore-parallelism
   ```

4. Committed, rebased, and pushed:
   ```bash
   git add plugins/debugging/global-semaphore-parallelism/skills/global-semaphore-parallelism/SKILL.md
   git commit -m "fix: add missing YAML frontmatter to global-semaphore-parallelism skill"
   git pull --rebase origin main
   git push --force-with-lease
   ```

### Fix 4: Rebase PR #73

**Branch:** `feature/hooks-once-field`

**Actions:**
```bash
git fetch origin feature/hooks-once-field
git checkout feature/hooks-once-field
git pull --rebase origin main
git push --force-with-lease
```

Result: Successfully rebased, inherited main branch frontmatter fixes.

### Fix 5: Rebase PR #69

**Branch:** `skill/debugging/resume-crash-debugging`

**Actions:**
```bash
git fetch origin skill/debugging/resume-crash-debugging
git checkout skill/debugging/resume-crash-debugging
git pull --rebase origin main
git push --force-with-lease
```

Result: Successfully rebased, inherited main branch frontmatter fixes.

### Fix 6: Rebase PR #72 (with conflict resolution)

**Branch:** `feature/skills-agent-field`

**Problem:** Merge conflict in `templates/experiment-skill/skills/SKILL_NAME/SKILL.md`

**Actions:**

1. Attempted rebase:
   ```bash
   git fetch origin main
   git fetch origin feature/skills-agent-field
   git checkout feature/skills-agent-field
   git pull --rebase origin main
   ```

2. Conflict occurred:
   ```
   CONFLICT (content): Merge conflict in templates/experiment-skill/skills/SKILL_NAME/SKILL.md
   ```

3. Inspected conflict:
   ```yaml
   ---
   name: SKILL_NAME
   description: "TRIGGER CONDITIONS: When to use this skill"
   user-invocable: false  # Set to true only for user-facing commands, false for internal/sub-skills
   <<<<<<< HEAD
   =======
   agent: specialist-agent  # Optional: specify which agent type should execute this skill
   >>>>>>> 5879aee (feat(skills): add agent field to route skills to specialized agents)
   category: CATEGORY
   date: YYYY-MM-DD
   ---
   ```

4. Resolved by keeping both fields (both are valid optional fields):
   ```yaml
   ---
   name: SKILL_NAME
   description: "TRIGGER CONDITIONS: When to use this skill"
   user-invocable: false  # Set to true only for user-facing commands, false for internal/sub-skills
   agent: specialist-agent  # Optional: specify which agent type should execute this skill
   category: CATEGORY
   date: YYYY-MM-DD
   ---
   ```

5. Completed rebase:
   ```bash
   git add templates/experiment-skill/skills/SKILL_NAME/SKILL.md
   git rebase --continue
   git push --force-with-lease
   ```

## Final Verification

```bash
gh pr list --state open --json number,title,statusCheckRollup --limit 10
```

**Results:**

| PR | Status | Conclusion |
|----|--------|------------|
| #74 | COMPLETED | SUCCESS ✅ |
| #73 | COMPLETED | SUCCESS ✅ |
| #72 | COMPLETED | SUCCESS ✅ |
| #69 | COMPLETED | SUCCESS ✅ |
| #68 | COMPLETED | SUCCESS ✅ |

## Validation Script Insights

From `scripts/validate_plugins.py`:

**Name validation (line 102-103):**
```python
if not re.match(r"^[a-z0-9-]+$", name):
    errors.append(f"Invalid name format '{name}' (use lowercase, numbers, hyphens)")
```

**Frontmatter validation (line 158-159):**
```python
if not content.startswith("---"):
    errors.append("SKILL.md missing YAML frontmatter (must start with ---)")
```

**Required frontmatter fields:**
- `name` (must match plugin.json)
- `description` (20+ chars minimum)

**Optional frontmatter fields:**
- `user-invocable` (boolean)
- `category` (one of 8 approved)
- `date` (YYYY-MM-DD format)
- `agent` (specialist name)

## Commands Reference

### Analysis Commands
```bash
# List PRs with CI status
gh pr list --state open --json number,title,headRefName,statusCheckRollup --limit 20

# Get CI run logs
gh run view <run-id> --log 2>/dev/null | grep -A 50 "Run python scripts/validate_plugins.py"

# Get specific failures
gh run view <run-id> --log 2>/dev/null | grep -E "^validate.*FAIL:" | head -20
gh run view <run-id> --log 2>/dev/null | grep -A 10 "FAIL: plugin-name"
```

### Validation Commands
```bash
# Full validation
python3 scripts/validate_plugins.py

# Check specific plugins
python3 scripts/validate_plugins.py 2>&1 | grep -E "(PASS|FAIL):\s+(plugin1|plugin2)"

# Show only failures
python3 scripts/validate_plugins.py 2>&1 | grep "FAIL:"
```

### Git Commands
```bash
# Fix workflow
git checkout main && git pull
# Make edits
git add <files>
git commit -m "fix: <description>"
git push

# Rebase workflow
git checkout <branch>
git pull --rebase origin main
# Resolve conflicts if needed
git add <conflicted-file>
git rebase --continue
git push --force-with-lease

# Rename plugin
git mv plugins/category/old-name plugins/category/new-name
git mv plugins/category/new-name/skills/old-name plugins/category/new-name/skills/new-name
python3 scripts/generate_marketplace.py
git add -A
```

## Lessons Learned

1. **Pattern recognition is key** - Same error across multiple PRs immediately suggests main branch issue

2. **Fix propagation order matters** - Main → Feature branches (via rebase) avoids duplicate work

3. **Plugin naming is stricter than expected** - Periods are invalid despite being common in semantic versioning (v2.1.0)

4. **Tool requirements** - Edit tool requires Read first, even after previous reads

5. **Merge conflicts in templates** - When adding optional fields, conflicts are expected and should keep both changes

6. **CI lag** - GitHub Actions can take 20-30s to start, use `sleep` + `gh pr view` for verification

7. **Force-push safety** - `--force-with-lease` prevents overwriting remote changes, unlike `--force`
