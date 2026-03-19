# Raw Notes: Bulk Skill PR Merge (2026-03-03)

## Session Context

ProjectMnemosyne had accumulated 30 open PRs, all adding skill plugins. The goal was to merge all of them in one session.

## PR Groups

### Group A: 24 PRs with passing CI
PRs: #236, #237, #238, #239, #240, #241, #242, #243, #244, #245, #246, #249, #251, #254, #255, #257, #259, #262, #264, #266, #267, #268, #269, #270

### Group B: 6 PRs with failing CI

| PR | Skill | Branch | Error | Fix Applied |
|----|-------|--------|-------|-------------|
| #248 | fix-isolation-mode-export-data-path | `skill/debugging/fix-isolation-mode-export-data-path` | Missing `version` field | Added `"version": "1.0.0"` |
| #250 | dockerfile-tomllib-fallback | `skill/ci-cd/dockerfile-tomllib-fallback` | Missing plugin.json | Created plugin.json |
| #252 | dockerfile-extras-validation | `skill/ci-cd/dockerfile-extras-validation` | Missing plugin.json | Created plugin.json |
| #256 | immutable-method-refactor | `skill/architecture/immutable-method-refactor` | Missing plugin.json | Created plugin.json |
| #261 | narrow-mypy-override-subset | `skill/testing/narrow-mypy-override-subset` | Missing plugin.json | Created plugin.json |
| #271 | lazy-clone-dependency | `skill/automation/lazy-clone-dependency` | Invalid category `automation` | Changed to `tooling` |

## Conflict Details

### PR #255 (runtime-error-guard-tests-workspace-manager)

- Branch: `skill/testing/runtime-error-guard-tests-workspace-manager`
- Conflict: `skills/runtime-error-guard-tests/SKILL.md` (content conflict)
- HEAD had #1214 follow-up (closure & inline guards, sections 7-9)
- PR branch had #1215 follow-up (workspace manager subprocess guards, sections 7-9)
- Resolution: Kept both sections, renumbered PR branch content as sections 10-12

### PR #259 (verify-mypy-compliance-test-annotations)

- Branch: `skill/testing/verify-mypy-compliance-test-annotations`
- Conflict type: add/add (two PRs created same file path on same branch)
- HEAD had expanded 3-instance version (issues #1285, #1286, #1288)
- PR branch had original single-instance version (issue #1286 only)
- Resolution: Kept HEAD (more complete) version for both commits

## Key Commands Used

```bash
# List PR CI status
gh pr checks <PR_NUMBER>

# Switch branches (Safety Net blocks git checkout)
git switch <branch-name>

# Merge with rebase
gh pr merge <PR_NUMBER> --rebase --delete-branch

# Rebase after conflicts
git rebase origin/main
git push --force-with-lease

# Verify all merged
for pr in ...; do
  echo "PR #$pr: $(gh pr view $pr --json state --jq '.state')"
done
```

## Branch Protection Settings

- Requires: `validate` check passes
- Approvals: 0 required
- Linear history: rebase merge only
- `strict: false` — PRs don't need to be up-to-date with main before merging

## Timeline

1. Fetched all remote branches
2. Ran bulk merge loop for Group A (22/24 succeeded, 2 became conflicting)
3. Fixed all 6 Group B PRs (pushed fixes, CI passed immediately)
4. Rebased PRs #255 and #259, resolved conflicts, force-pushed
5. Merged all remaining PRs
6. Verified all 30 merged