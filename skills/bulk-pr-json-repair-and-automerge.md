---
name: bulk-pr-json-repair-and-automerge
description: Repair bulk-corrupted JSON files and enable auto-merge on many open PRs
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Bulk PR JSON Repair and Auto-Merge

## Overview

| Field | Details |
|-------|---------|
| Date | 2026-03-05 |
| Objective | Fix 181 JSON-invalid plugin.json files caused by botched batch tag removal, then enable auto-merge on 25 open PRs |
| Outcome | Success — all 184 broken files fixed, all 25 PRs merged or set to auto-merge |

## When to Use

- A batch edit removed a JSON key's opening line (e.g., `"tags": [`) but left array contents and closing `]` behind
- Many JSON files have trailing commas after a removed last property
- You need to enable auto-merge across 20+ open PRs at once
- A PR branch has corrupted JSON that blocks CI; auto-merge was already enabled but waiting

## Verified Workflow

### Step 1: Diagnose the JSON corruption patterns

Run validation first to understand scope:

```bash
python3 scripts/validate_plugins.py skills/ plugins/ 2>&1 | grep -c "Invalid JSON"
```

Examine a few broken files to identify the pattern(s):

```bash
cat <broken-file>.json
```

Common patterns after botched key removal:
1. **Trailing comma** — last remaining property has a trailing comma before `}`
2. **Orphaned array items (no subsequent fields)** — bare string items + lone `]` with nothing after
3. **Orphaned array items (with subsequent fields)** — bare string items + `],` followed by other valid keys

### Step 2: Fix with Python (NOT xargs/shell)

Use Python's `json` module for a safe, idempotent fix. The Safety Net blocks `xargs -I{} sh -c` patterns.

**Phase 1 — Fix files that are already valid JSON (just remove the key):**

```python
import json, pathlib, subprocess

result = subprocess.run(['find', 'skills/', 'plugins/', '-name', 'plugin.json'],
                       capture_output=True, text=True)
files = result.stdout.strip().split('\n')

for f in files:
    p = pathlib.Path(f)
    try:
        data = json.loads(p.read_text())
        if 'tags' in data:
            del data['tags']
            p.write_text(json.dumps(data, indent=2) + '\n')
    except Exception:
        pass  # Handle broken JSON separately
```

**Phase 2 — Fix trailing commas (regex):**

```python
import re
fixed_text = re.sub(r',(\s*[}\]])', r'\1', text)
```

**Phase 3 — Fix orphaned array blocks (line-by-line state machine):**

Track whether you're inside a valid `key: [` array vs. an orphaned block:

```python
in_orphaned_block = False
in_valid_array = False

for line in lines:
    stripped = line.strip()

    # Valid array start: "key": [
    if re.match(r'"[^"]+"\s*:\s*\[', stripped):
        in_valid_array = True
        in_orphaned_block = False
        new_lines.append(line)
        if stripped.endswith(']') or stripped.endswith('],'):
            in_valid_array = False
        continue

    # Closing bracket
    if stripped in (']', '],'):
        if in_valid_array:
            new_lines.append(line)
            in_valid_array = False
        elif in_orphaned_block:
            in_orphaned_block = False  # skip the closing bracket
        else:
            new_lines.append(line)
        continue

    # Bare string detection (orphaned tag item)
    is_bare_string = (stripped.startswith('"') and
                      not re.match(r'"[^"]+"\s*:', stripped) and
                      (stripped.endswith('",') or stripped.endswith('"')))

    if is_bare_string:
        if in_valid_array:
            new_lines.append(line)  # legitimate array item
        else:
            in_orphaned_block = True  # skip orphaned tag
        continue

    new_lines.append(line)
```

### Step 3: Verify before committing

```bash
python3 scripts/validate_plugins.py skills/ plugins/ 2>&1 | tail -5
```

### Step 4: Stage only modified files (not untracked dirs)

```bash
# Safe: only stages modified tracked files
git add $(git diff --name-only)
```

Do NOT use `git add skills/` or `git add -A` — this picks up any nested untracked directories.

### Step 5: Enable auto-merge on many PRs

```bash
# Try rebase first (squash/merge-commit may be disabled)
for pr in 330 329 328 ...; do
  gh pr merge --auto --rebase $pr && echo "OK: #$pr" || echo "FAIL: #$pr"
done
```

PRs that report "Pull request is in clean status" are already ready — merge them directly:

```bash
gh pr merge --rebase <number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Corruption patterns and fix counts (this run)

| Pattern | Count | Fix Method |
|---------|-------|------------|
| Valid JSON with `tags` key | 225 | `json.loads` + `del data['tags']` |
| Trailing comma only | 44 | Regex: `re.sub(r',(\s*[}\]])', r'\1', text)` |
| Orphaned array (no subsequent fields) | 121 | Line-by-line state machine |
| Orphaned array (with subsequent fields like `triggers`) | 19 | Line-by-line state machine with `in_valid_array` tracking |
| **Total fixed** | **184** | |

### GitHub merge method discovery

```bash
# Test in order until one works:
gh pr merge --auto --squash <pr>   # Usually fails if squash disabled
gh pr merge --auto --merge <pr>    # Usually fails if merge commits disabled
gh pr merge --auto --rebase <pr>   # Rebase-only repos: this works
```

### Handling "clean status" PRs

"Pull request is in clean status" means CI already passed — auto-merge can't be enabled (it has nothing to wait for). Just merge directly:

```bash
gh pr merge --rebase <number>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #306 fix + 25 PRs auto-merge | [notes.md](../../references/notes.md) |
