---
name: fix-yaml-frontmatter-colon-bug
description: "Fix YAML frontmatter parsing bugs where line.partition(':') silently truncates values containing colons. Use when: migrating a manual-split frontmatter parser to yaml.safe_load() following the partition-colon bug pattern."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Bug Pattern** | `key, _, value = line.partition(":")` silently drops everything after the first colon |
| **Trigger** | Script reads YAML frontmatter by splitting on `:` instead of using a YAML parser |
| **Fix** | Replace with `yaml.safe_load()` — handles colons in values, quoted strings, invalid YAML |
| **Scope** | Any Python script using the `partition(":")` or `split(":", 1)` pattern for YAML frontmatter |
| **Risk** | Low — `yaml.safe_load()` returns `{}` for invalid YAML instead of raising |

## When to Use

- A sibling or related script has the same `line.partition(":")` bug that was fixed in a parent issue
- A description field like `"Create PR linked to issue: #123"` is being silently truncated to `"Create PR linked to issue"`
- You need to propagate a `yaml.safe_load()` fix from one script to another using the same pattern
- Multiple scripts share the same manual-parsing logic and one was already fixed

## Verified Workflow

### Quick Reference

```python
# ❌ Buggy — silently truncates values with colons
for line in frontmatter_text.splitlines():
    if ":" in line:
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")

# ✅ Fixed — yaml.safe_load() handles colons correctly
import yaml

try:
    parsed = yaml.safe_load(frontmatter_text)
    result = parsed if isinstance(parsed, dict) else {}
except yaml.YAMLError:
    result = {}
```

### Steps

1. **Find the parent fix** — read the PR or issue that first fixed this pattern (e.g., `gh pr view <N>`)
   to understand the exact replacement used

2. **Locate the sibling script** — use `find` or `grep` to find all scripts with the same
   `line.partition(":")` pattern:

   ```bash
   grep -r 'partition.*":"' scripts/
   grep -r "partition.*':'" scripts/
   ```

3. **Read the full file** — understand context (function name, imports, return type) before editing

4. **Apply the fix** — two changes required:
   - Add `import yaml` to the imports block (alphabetically sorted)
   - Replace the `for line in ...` loop with the `yaml.safe_load()` pattern

5. **Write regression tests** — follow the same test class structure used for the parent fix.
   Tests should cover:
   - Plain value (baseline)
   - Colon in quoted value (regression case — the exact bug)
   - Colon in unquoted value
   - No frontmatter (returns `{}`)
   - Unclosed frontmatter (returns `{}`)
   - Invalid YAML (returns `{}` without raising)
   - Multiple colons in a single value

6. **Handle test file discovery** — when the script lives in an external repo
   (e.g., `ProjectMnemosyne`), use `importlib.util.spec_from_file_location()` with
   multiple candidate paths and `pytest.mark.skipif` if none exist:

   ```python
   _CANDIDATES = [
       Path.home() / "ProjectMnemosyne" / "scripts" / "migrate_to_skills.py",
       Path(__file__).parent.parent.parent / "build" / str(os.getpid())
           / "ProjectMnemosyne" / "scripts" / "migrate_to_skills.py",
   ]
   _SCRIPT_PATH = next((p for p in _CANDIDATES if p.exists()), None)

   pytestmark = pytest.mark.skipif(
       _SCRIPT_PATH is None,
       reason="Script not found; skipping",
   )
   ```

7. **Run tests** — confirm all pass:

   ```bash
   pixi run python -m pytest tests/scripts/test_<script_name>_frontmatter.py -v
   ```

8. **Commit the fix** to the external repo on a feature branch; commit the tests to the
   main repo on its own branch

9. **Create PRs** for both repos and enable auto-merge

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Search for file in worktree | `find` in `.worktrees/issue-3929/` for `migrate_to_skills.py` | File lives in `ProjectMnemosyne` repo, not in the ProjectOdyssey worktree | Check `build/*/ProjectMnemosyne/` and `~/ProjectMnemosyne/` for sibling repo scripts |
| Look for tracked file in git | `git ls-files \| grep migrate_to_skills` | Script is in a separate cloned repo, never committed to ProjectOdyssey | For cross-repo fixes, always look for the local checkout of the target repo first |
| Assume `build/` in worktree | Looked for `build/` under `.worktrees/issue-3929/` | `build/` is under the main repo root, not under worktree paths | PID-scoped builds live at `<repo_root>/build/<PID>/`, not under worktree subdirectories |

## Results & Parameters

### Regression Test Template

```python
class TestExtractFrontmatter:
    """Regression tests for extract_frontmatter() colon handling."""

    def test_colon_in_quoted_value(self, migrate_module) -> None:
        """Regression: description with a colon inside a quoted value must not be truncated."""
        content = '---\nname: my-skill\ndescription: "Create PR linked to issue: #123"\n---\n# Body'
        fm = migrate_module.extract_frontmatter(content)
        assert fm["description"] == "Create PR linked to issue: #123"

    def test_invalid_yaml_returns_empty_dict(self, migrate_module) -> None:
        """Malformed YAML in frontmatter returns {} without raising."""
        content = "---\n: invalid: yaml: [\n---\n# Body"
        fm = migrate_module.extract_frontmatter(content)
        assert fm == {}
```

### Fix Diff Pattern

```diff
+import yaml
+
 def extract_frontmatter(content: str) -> dict:
     ...
     frontmatter_text = content[3:end].strip()
-    result = {}
-    for line in frontmatter_text.splitlines():
-        if ":" in line:
-            key, _, value = line.partition(":")
-            result[key.strip()] = value.strip().strip('"').strip("'")
-    return result
+    try:
+        parsed = yaml.safe_load(frontmatter_text)
+        return parsed if isinstance(parsed, dict) else {}
+    except yaml.YAMLError:
+        return {}
```
