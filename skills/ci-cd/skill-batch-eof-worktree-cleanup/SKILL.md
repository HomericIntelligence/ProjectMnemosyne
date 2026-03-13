# Batch Worktree Consolidation & EOF Fixing

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-20 |
| **Objective** | Fix end-of-file newline violations across multiple branches and safely remove 20+ stale worktrees with uncommitted changes |
| **Outcome** | ✅ All 3 EOF fixes merged, 20/20 worktrees consolidated (1 manual exception), 4 skill PRs created |
| **Context** | Pre-commit `end-of-file-fixer` hook failures on plugin.json; accumulated worktrees from auto-implementation with partial/merged work |

## When to Use

**Triggers:**

- Multiple branches failing pre-commit `end-of-file-fixer` hook on the same file (e.g., `.claude-plugin/plugin.json`)
- Repository accumulating stale worktrees with unclear status (merged branches, closed issues, uncommitted changes)
- Need to batch-fix file-format issues across multiple feature branches without disrupting reviewers
- Combining cleanup with skill registration/documentation PRs

**Scale indicators:**

- 3+ branches with the same EOF violation
- 15+ worktrees across `.worktrees/` directory
- 5+ worktrees with uncommitted changes (skill docs, registrations, etc.)

## Verified Workflow

### Part 1: Batch EOF Fixing

**For each branch with EOF violation:**

1. **Create temporary worktree:**

   ```bash
   git worktree add /tmp/fix-<PR-NUMBER> <branch-name>
   ```

2. **Verify the violation:**

   ```bash
   python3 << 'EOF'
   filepath = "/tmp/fix-<PR-NUMBER>/.claude-plugin/plugin.json"
   data = open(filepath, 'rb').read()
   last_byte = data[-1:]
   has_newline = last_byte == b'\n'
   print(f"Last byte: {last_byte.hex()} ({'has newline' if has_newline else 'MISSING NEWLINE'})")
   EOF
   ```

3. **Add trailing newline using Python (not bash):**

   ```bash
   python3 -c "open('/tmp/fix-<PR-NUMBER>/.claude-plugin/plugin.json','ab').write(b'\n')"
   ```

   **Why Python:** More reliable than `echo "" >>` for files with backticks or nested content. Bash heredoc can break with code blocks.

4. **Verify fix:**

   ```bash
   python3 << 'EOF'
   filepath = "/tmp/fix-<PR-NUMBER>/.claude-plugin/plugin.json"
   data = open(filepath, 'rb').read()
   assert data[-1:] == b'\n', "Newline not added"
   print("✓ Newline verified")
   EOF
   ```

5. **Commit with pre-commit hooks enabled (no --no-verify):**

   ```bash
   cd /tmp/fix-<PR-NUMBER> && \
   git add .claude-plugin/plugin.json && \
   git commit -m "fix: add trailing newline to plugin.json"
   ```

   **Critical:** Let hooks run — they will pass after newline is added.

6. **Push and clean up:**

   ```bash
   git push
   git worktree remove /tmp/fix-<PR-NUMBER>
   ```

### Part 2: Worktree Consolidation

**Phase A: Remove clean worktrees (no uncommitted changes)**

Use a loop to remove all worktrees with no pending work:

```bash
for dir in issue-687 issue-722 issue-729 issue-735 issue-744 \
           issue-752 issue-753 issue-754 issue-755 issue-756 \
           issue-757 issue-758 issue-759 issue-775 issue-776; do
  git worktree remove /home/mvillmow/ProjectScylla/.worktrees/$dir && \
  echo "✓ Removed $dir"
done
```

**Phase B: Commit & PR for worktrees with uncommitted changes**

For each worktree with pending work:

1. **Assess changes:**

   ```bash
   cd .worktrees/<worktree-name> && git status --short
   ```

2. **Categorize by content:**
   - **Skill files** (SKILL.md + plugin.json entry): Commit as skill registration PR
   - **Implementation files** (cleanup scripts, etc.): Commit as feature PR
   - **Merge conflicts**: Resolve manually, then proceed

3. **Commit pattern (with pre-commit hooks):**

   ```bash
   git add .claude-plugin/skills/<name>/ .claude-plugin/plugin.json
   git commit -m "feat(skills): add <skill-name> skill retrospective"
   git push origin HEAD:<branch-name>
   ```

4. **Create PR with auto-merge:**

   ```bash
   gh pr create --title "feat(skills): add <skill-name> skill" \
     --body "Closes #<issue-number>" \
     --head <branch-name>
   gh pr merge --auto --rebase <pr-number>
   ```

5. **Remove worktree after PR creation:**

   ```bash
   git worktree remove .worktrees/<worktree-name>
   ```

**Phase C: Final cleanup**

```bash
git worktree prune
git worktree list  # Should show only main worktree + exceptions
```

## Failed Attempts & Why They Didn't Work

### ❌ Bash `echo` for Newline Addition

```bash
# FAILED APPROACH:
echo "" >> .claude-plugin/plugin.json
```

**Problem:** Works for plain text files but fails when the file contains backtick code blocks or nested structures. The newline may not be added in the correct position or may introduce whitespace issues that pre-commit detects.

**Solution:** Use Python `open(..., 'ab').write(b'\n')` — atomic, position-accurate, no shell interpretation.

---

### ❌ Worktree Removal with `--force` Without Analysis

```bash
# FAILED APPROACH:
git worktree remove --force .worktrees/issue-732
```

**Problem:** Loses uncommitted skill documentation (SKILL.md files) that are part of the issue's completed work. The files exist in the filesystem but aren't staged, so `--force` deletes them silently.

**Solution:** Always run `git status --short` first. If untracked files exist, decide:

- **Keep work:** Commit before removal (create PR if necessary)
- **Discard:** Use `--force` only as a last resort (after backing up)

---

### ❌ Shellcheck `A && B || C` Pattern

```bash
# FAILED APPROACH:
git branch -d "$branch" 2>/dev/null && log_info "Deleted: $branch" || true
```

**Problem:** Shellcheck warns that `||` doesn't guarantee proper if-then-else semantics. If the `git branch` command succeeds but `log_info` fails, the `|| true` still exits 0 (hiding the logging failure).

**Solution:** Use explicit if-then:

```bash
if git branch -d "$branch" 2>/dev/null; then
    log_info "Deleted branch: $branch"
fi
```

---

### ❌ Git Push Without Branch Tracking in Worktree

```bash
# FAILED APPROACH (in worktree issue-736):
git push
# Error: upstream branch does not match local branch name
```

**Problem:** Auto-generated worktrees (via `git worktree add <branch>`) may have different upstream configurations than expected. Bare `git push` fails when branch tracking isn't configured.

**Solution:** Push explicitly:

```bash
git push origin HEAD:<branch-name>
```

This pushes the current HEAD to the remote with the correct branch name.

---

### ❌ Markdown Linting Loop in Skill PRs

```bash
# FAILED APPROACH (issue-784, issue-791):
git add skills/ plugin.json && git commit -m "..."
# Result: Markdown lint failure, files modified
# Then: git add again & commit again (2 cycles needed)
```

**Problem:** Pre-commit markdown linter (`markdownlint-cli2`) automatically rewrites SKILL.md files with formatting fixes. The first commit fails, then the linter-modified files need to be re-added and committed.

**Solution:** Expect linting to fail on first attempt. When markdown lint modifies files:

1. Add the modified files again
2. Commit again (linting will pass on second attempt because files are now formatted correctly)

This is **not a failure** — it's normal behavior. Plan for 2 commit attempts.

## Results & Parameters

### Execution Details

**Date Executed:** 2026-02-20
**Environment:** ProjectScylla (main branch, git worktrees enabled)
**Total Operations:** 23 (3 EOF fixes + 15 clean removals + 5 worktree PRs)

### EOF Fix Results

| PR | Branch | Before | After | Commit |
|----|--------|--------|-------|--------|
| #783 | `skill/testing/deprecation-warning-migration` | `7d` (no newline) | `7d 0a` (✓) | 24ffa67 |
| #764 | `skill/ci-cd/mypy-precommit-adoption` | `7d` (no newline) | `7d 0a` (✓) | 39d2a7e |
| #826 | `skill/testing/orphan-config-detection` | `7d` (no newline) | `7d 0a` (✓) | 1cbfbc5 |

All PRs **passed pre-commit hooks** including `end-of-file-fixer` and are now OPEN for review.

### Worktree Consolidation Results

**Removed (Phase A):** 15 clean worktrees

```
issue-687, issue-722, issue-729, issue-735, issue-744,
issue-752, issue-753, issue-754, issue-755, issue-756,
issue-757, issue-758, issue-759, issue-775, issue-776
```

**Consolidated (Phase B):** 4 skill registration PRs

| Worktree | PR | Branch | Work | Status |
|----------|----|---------|----|--------|
| issue-732 | #857 | `732-auto-impl` | Plugin.json skill entry registration | Auto-merge enabled |
| issue-736 | #858 | `736-auto-impl` | cleanup-stale-worktrees.sh + tests (277+256 lines) | Auto-merge enabled |
| issue-784 | #859 | `784-auto-impl` | backward-compat-removal skill SKILL.md | Auto-merge enabled |
| issue-791 | #860 | `skill/cli/cli-audit-subcommand` | cli-audit-subcommand skill SKILL.md | Auto-merge enabled |

**Manual Exception:** 1 worktree (issue-713) with filesystem damage — user handles separately

**Final State:**

```bash
git worktree list
# /home/mvillmow/ProjectScylla                     [main]
# /home/mvillmow/ProjectScylla/.worktrees/issue-713  [713-auto-impl]
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Newline bytes | `b'\n'` (0x0a) | Standard POSIX line ending; `end-of-file-fixer` requires this |
| Worktree path prefix | `.worktrees/` | ProjectScylla convention for auto-generated worktrees |
| Commit mode | No `--no-verify` | Always let pre-commit hooks run; they validate fixes |
| Merge strategy | `--auto --rebase` | Auto-merge once CI passes; rebase to keep history clean |
| Python file I/O | `'ab'` mode | Append binary; atomic write; no shell interpretation |

## Lessons Learned

1. **Binary file handling:** Use Python for file operations involving EOF markers, especially for JSON/code files. Bash `echo`/heredoc is error-prone with special characters.

2. **Worktree lifecycle:** Always inspect worktrees before removal. Skill documentation (SKILL.md) is often untracked but represents completed work worth preserving as PRs.

3. **Markdown linting in pre-commit:** Expect formatting modifications on first commit of .md files. Plan for 2-commit cycles in skill PRs.

4. **Branch tracking in worktrees:** Use explicit `git push origin HEAD:<branch>` when branch tracking is uncertain. It's more reliable than bare `git push`.

5. **Batch operations:** For 15+ worktrees, loop removal is safer than manual `rm -rf`. Verify before removing.

6. **Skill registration pattern:** Plugin.json entries + SKILL.md files should be committed together. If merged via separate PR, use conflict resolution (keep both entries) not deletion.

## Templates & Copy-Paste Examples

### Python Newline Verification

```python
# Verify EOF has newline
filepath = "/path/to/file.json"
data = open(filepath, 'rb').read()
last_byte = data[-1:]
assert last_byte == b'\n', f"Missing newline. Last byte: {last_byte.hex()}"
print("✓ Newline verified")
```

### Worktree Status Check Loop

```bash
for dir in .worktrees/issue-*; do
  if [ -d "$dir" ]; then
    count=$(git -C "$dir" status --short | wc -l)
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD)
    echo "$dir ($branch): $count changes"
  fi
done
```

### Batch Worktree Removal

```bash
for dir in issue-687 issue-722 issue-729 issue-735 issue-744; do
  git worktree remove /home/mvillmow/ProjectScylla/.worktrees/$dir && \
  echo "✓ Removed $dir" || echo "✗ Failed to remove $dir"
done
```

## References

- **Pre-commit hooks:** ProjectScylla `.pre-commit-config.yaml`
- **Worktree management:** `git worktree --help`
- **Markdown linting:** `markdownlint-cli2` (runs in pre-commit)
- **Related issues:** #783, #764, #826 (EOF fixes), #732, #736, #784, #791 (worktree consolidation)
