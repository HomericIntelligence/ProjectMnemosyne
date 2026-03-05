# Notes: Bulk PR JSON Repair and Auto-Merge

## Session Context

**Date**: 2026-03-05
**Repository**: ProjectMnemosyne
**Trigger**: PR #306 had 181 JSON parse errors from a previous session that removed `"tags"` field
by deleting only the `"tags": [` line, leaving array contents orphaned.

## Exact Error Messages

```
FAIL: docker-multistage-build
  Errors:
    - Invalid JSON in plugin.json: Expecting ':' delimiter: line 7 column 13 (char 258)

FAIL: github-bulk-housekeeping
  Errors:
    - Invalid JSON in plugin.json: Expecting ':' delimiter: line 7 column 13 (char 429)

FAIL: dockerfile-layer-caching
  Errors:
    - Invalid JSON in plugin.json: Expecting property name enclosed in double quotes: line 7 column 1 (char 307)
```

Total: 181 plugins with errors initially, grew to 184 after first pass (some fixed files exposed
previously-hidden errors in files that were double-broken).

## Corruption Examples

### Type 1: Trailing comma
```json
{
  "name": "issue-triage-and-fix",
  "date": "2026-02-22",   <- trailing comma, no more properties
}
```

### Type 2: Orphaned array (no subsequent fields)
```json
{
  "name": "github-actions-ci-speedup",
  "date": "2026-01-01",
    "github",              <- orphaned tag items
    "actions",
    "speedup"
  ]                        <- orphaned closing bracket
}
```

### Type 3: Orphaned array (with subsequent valid fields)
```json
{
  "name": "e2e-artifact-deduplication",
  "created": "2026-01-11",
    "e2e-evaluation",      <- orphaned tag items
    "deduplication",
    "optimization",
    "file-structure",
    "judge-prompts",
    "artifact-consolidation"
  ],                       <- closes orphaned block
  "triggers": [            <- valid field follows
    "duplicate files...",
  ],
  "related_files": [...]
}
```

## Fix Script Evolution

### Attempt 1: xargs + jq
```bash
find skills/ plugins/ -name "plugin.json" | xargs -I{} sh -c 'jq "del(.tags)" "{}" > /tmp/plugin_tmp.json && mv /tmp/plugin_tmp.json "{}"'
```
**Blocked by Safety Net**: `xargs -I{} sh -c` pattern flagged.

### Attempt 2: Python json.loads pass
Fixed 225 valid-JSON files. 184 remained broken (couldn't parse).

### Attempt 3: Regex trailing comma pass
Fixed 44 more. 140 remained.

### Attempt 4: First orphaned-block state machine
Issue: treated ALL bare strings as orphaned, including legitimate array items in `triggers: [...]`.
Fixed 121. Left 19 broken.

### Attempt 5: Improved state machine with `in_valid_array` tracking
Fixed all remaining 19. Key insight: track whether we're inside a `"key": [` context to distinguish
legitimate array contents from orphaned ones.

## Git Staging Mistake

First commit accidentally included nested untracked directories:
- `skills/testing/fix-flaky-sleep-mock/fix-flaky-sleep-mock/` (entire ProjectMnemosyne clone)
- `skills/testing/rubric-conflict-detection/rubric-conflict-detection/`

Result: 1227 files in commit instead of 184.

**Root cause**: `git add skills/` picks up untracked content under the path.

**Fix**: `git reset HEAD~1` then `git add $(git diff --name-only)` to stage only modified files.

## PR Auto-Merge Results

| PR Range | Method | Result |
|----------|--------|--------|
| #330, #329, #327, #325, #324, #322, #321, #319-#317, #316-#315, #313, #312, #309-#307, #304 | `gh pr merge --auto --rebase` | auto-merge enabled |
| #328, #323, #320, #314, #311, #310 | `gh pr merge --rebase` | merged directly (already clean) |
| #306 | auto-merge was pre-enabled; triggered by fix push | merged automatically after CI pass |
| #331 | `gh pr merge --auto --rebase` then immediately `--rebase` | merged (was clean) |

## Repository Merge Settings

- Squash merging: **disabled**
- Merge commits: **disabled**
- Rebase merging: **enabled** (only option)

Discovered by trial and error — try `--squash` → `--merge` → `--rebase` in that order.
