---
name: technical-debt-tracker
description: "Track and resolve FIXME/TODO comments via GitHub issues"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Technical Debt Tracker

Audit FIXME/TODO comments in a codebase, create categorized GitHub issues, and update stale references.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Track and resolve all FIXME/TODO comments referencing closed issues | Created 8 category issues + 1 Epic, updated 20+ source files |

## When to Use

- (1) Auditing codebase for technical debt (FIXME/TODO comments)
- (2) Discovered FIXME/TODO references to closed GitHub issues
- (3) Need to create structured issues for each debt category
- (4) Updating stale issue references in source code comments
- (5) Creating an Epic to track multiple related issues

## Verified Workflow

### Phase 1: Discovery

1. **Find all FIXME comments**:

   ```bash
   grep -rn "FIXME" --include="*.mojo" --include="*.py" --exclude-dir='.*' .
   ```

2. **Find all TODO comments**:

   ```bash
   grep -rn "TODO" --include="*.mojo" --include="*.py" --exclude-dir='.*' .
   ```

3. **Extract referenced issue numbers**:

   ```bash
   grep -oP "FIXME\(#\K\d+" --include="*.mojo" --exclude-dir='.*' -r . | sort -u
   grep -oP "TODO\(#\K\d+" --include="*.mojo" --exclude-dir='.*' -r . | sort -u
   ```

4. **Check if referenced issues are closed**:

   ```bash
   gh issue view <number> --json state -q '.state'
   ```

### Phase 2: Create Category Issues

1. **Check available labels first** (critical!):

   ```bash
   gh label list --limit 50
   ```

2. **Create issue per category**:

   ```bash
   gh issue create \
     --title "[Category] Brief description" \
     --body "$(cat <<'EOF'
   ## Summary
   Description of the technical debt category.

   ## Files Affected
   - `path/to/file.mojo:line` - Description

   ## Acceptance Criteria
   - [ ] Criterion 1
   - [ ] Criterion 2

   ## Previous Issues
   Replaces closed #XXXX, #YYYY
   EOF
   )" \
     --label "existing-label"
   ```

### Phase 3: Create Epic

```bash
gh issue create \
  --title "[Epic] Technical Debt Resolution" \
  --body "$(cat <<'EOF'
## Objective
Track and resolve all stale FIXME/TODO comments.

## Child Issues
- [ ] #XXXX - Category 1
- [ ] #YYYY - Category 2
- [ ] #ZZZZ - Category 3
EOF
)"
```

### Phase 4: Update Source Comments

Use `replace_all` for bulk updates:

```bash
# Read file first, then update all references
# FIXME(#OLD) -> FIXME(#NEW)
# TODO(#OLD) -> TODO(#NEW)
```

## Results

Issues created in ProjectOdyssey session:

| Issue | Category | Description |
|-------|----------|-------------|
| #3008 | Testing | FP4/MXFP4 Test Coverage |
| #3009 | Testing | Float16 Precision Issues |
| #3010 | Testing | Placeholder Test Fixtures |
| #3011 | Cleanup | Unused Variable Declarations |
| #3012 | External | BFloat16 Workaround |
| #3013 | Feature | ExTensor Operations |
| #3014 | Feature | Autograd Enhancements |
| #3015 | Feature | SIMD Mixed Precision |
| #3016 | Epic | Technical Debt Resolution |

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `--label "technical-debt"` | Label didn't exist in repo | **Always run `gh label list` first** to check available labels |
| Tried to edit file without reading | Edit tool requires read first | Read files before attempting `replace_all` updates |
| Assumed referenced issues were open | All were actually closed | Verify issue state with `gh issue view --json state` |
| Included documentation examples in updates | They use fictional issue numbers | Skip files like `examples.md` and `.DEPRECATED` files |
| Searched hidden directories (.pixi, .git) | grep without --exclude-dir scanned dependencies | **Always add `--exclude-dir='.*'`** to exclude hidden directories |

## Error Handling

| Problem | Solution |
|---------|----------|
| `label not found` | Run `gh label list` and use existing labels |
| `File has not been read` | Read file before edit |
| Issue not linked | Use "Replaces #OLD" in body to document history |
| Stale references remain | Use grep to verify all references updated |

## Key Parameters

- **Comment patterns**: `FIXME(#XXXX)`, `TODO(#XXXX)`, `FIXME:`, `TODO:`
- **File types**: `.mojo`, `.py`, `.md`
- **Exclusions**: `.DEPRECATED` files, documentation examples
- **Labels**: Use existing repo labels (check with `gh label list`)

## Verification

After completing updates:

```bash
# Verify no old references remain (exclude hidden directories)
grep -rn "#OLD_NUMBER" --include="*.mojo" --exclude-dir='.*' .

# Should return empty or only documentation examples
```

## References

- See gh-read-issue-context for reading issue history
- See gh-post-issue-update for posting progress updates
- GitHub CLI docs: https://cli.github.com/manual/
