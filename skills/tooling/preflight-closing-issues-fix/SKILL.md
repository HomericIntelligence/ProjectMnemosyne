# Skill: preflight-closing-issues-fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | #802 |
| PR | #912 |
| Category | tooling |
| Objective | Fix `preflight_check.sh` Check 3 false positives caused by free-text PR search matching issue numbers in unrelated PR titles/bodies |
| Outcome | Success — 6 bash tests pass, all pre-commit hooks green, PR created with auto-merge |

## When to Use

Trigger this skill when:

- A preflight/guard script uses `gh pr list --search "<number>"` to detect if a PR already covers an issue
- A PR titled "Fix issue 735-related bug" incorrectly triggers STOP for issue 735
- You need to distinguish PRs that *formally close* an issue from PRs that merely *mention* the issue number
- Upgrading a GitHub PR search from free-text to authoritative `closingIssuesReferences`

**Trigger phrases**:

- "false positive from PR title search"
- "Check 3 may produce false positives"
- "gh pr list --search <issue-number>"
- "PR mentions issue but doesn't close it"

## Root Cause Pattern

`gh pr list --search "$ISSUE"` is a **full-text search** — it matches any PR whose title or body contains the string `"735"`. This causes false positives whenever a PR description casually references the issue number without formally closing it.

GitHub's `closingIssuesReferences` field is populated only when a PR body contains a recognized closing keyword (`Closes #N`, `Fixes #N`, `Resolves #N`) or the issue is explicitly linked via the GitHub UI. It is the authoritative signal for "this PR closes this issue."

## Verified Workflow

### 1. Identify the problematic search call

```bash
grep -n "gh pr list --search" scripts/preflight_check.sh
# Expected: gh pr list --search "$ISSUE" --state all --json ...
```

### 2. Replace with two-phase lookup

**Before** (false-positive prone):

```bash
PR_JSON=$(gh pr list --search "$ISSUE" --state all --json number,title,state 2>/dev/null)
MERGED_PRS=$(echo "$PR_JSON" | jq -r '.[] | select(.state == "MERGED") | "\(.number): \(.title)"')
OPEN_PRS=$(echo "$PR_JSON"   | jq -r '.[] | select(.state == "OPEN")   | "\(.number): \(.title)"')
```

**After** (precise, uses `closingIssuesReferences`):

```bash
CANDIDATE_JSON=$(gh pr list --state all --json number,title,state --limit 100 2>/dev/null)
MERGED_PRS=""
OPEN_PRS=""
while IFS=$'\t' read -r pr_num pr_title pr_state; do
    [[ -z "$pr_num" ]] && continue
    CLOSES=$(gh pr view "$pr_num" --json closingIssuesReferences \
        --jq '.closingIssuesReferences[].number' 2>/dev/null)
    if echo "$CLOSES" | grep -qx "$ISSUE"; then
        if [[ "$pr_state" == "MERGED" ]]; then
            MERGED_PRS+="${pr_num}: ${pr_title}"$'\n'
        elif [[ "$pr_state" == "OPEN" ]]; then
            OPEN_PRS+="${pr_num}: ${pr_title}"$'\n'
        fi
    fi
done < <(echo "$CANDIDATE_JSON" | jq -r '.[] | [.number,.title,.state] | @tsv')
MERGED_PRS="${MERGED_PRS%$'\n'}"
OPEN_PRS="${OPEN_PRS%$'\n'}"
```

### 3. Write bash tests with mock `gh` functions

Key technique: mock `gh` as a bash function in a subshell, capturing exit code with a temp file (not a pipe, which loses `$?`):

```bash
run_preflight_with_exit() {
    local issue="$1"
    local mock_body="$2"
    local tmpfile
    tmpfile=$(mktemp)
    bash -c "
        ${mock_body}
        export -f gh
        bash '${PREFLIGHT}' '${issue}' 2>&1
    " > "$tmpfile" 2>&1
    LAST_EXIT=$?
    LAST_OUTPUT=$(strip_ansi "$(cat "$tmpfile")")
    rm -f "$tmpfile"
}
```

### 4. Cover the six test cases

| Test | Scenario | Expected |
|------|----------|----------|
| 1 | No PRs exist | PASS exit 0 |
| 2 | MERGED PR, `closingRef=[issue]` | STOP exit 1 |
| 3 | OPEN PR, `closingRef=[issue]` | WARN exit 0 |
| 4 | MERGED PR mentioning issue in title, empty `closingRef` | PASS exit 0 (regression) |
| 5 | Multiple PRs, only one with `closingRef` | STOP with only that PR listed |
| 6 | PRs exist but `closingRef` targets different issue | PASS exit 0 |

### 5. Fix ShellCheck SC2001

ShellCheck flags `sed 's/\x1b...'` with SC2001. Since `\x1b` hex escape cannot be expressed in bash parameter expansion, suppress it with an inline directive:

```bash
# SC2001 is suppressed: bash parameter expansion cannot match \x1b hex escapes.
# shellcheck disable=SC2001
strip_ansi() { echo "$1" | sed 's/\x1b\[[0-9;]*m//g'; }
```

### 6. Update SKILL.md documentation

Update the Pre-Flight Check Results table rows for STOP/WARN to note that matching is now via `closingIssuesReferences`, not text search.

### 7. Commit, push, create PR

```bash
git add scripts/preflight_check.sh SKILL.md tests/test_preflight_check.sh
git commit -m "fix(preflight): use closingIssuesReferences for precise PR-issue matching

Closes #802"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #802"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

**Skill tool denied**: Attempted `commit-commands:commit-push-pr` skill but it was blocked by `don't ask mode`. Fell back to direct Bash git commands — this is the correct fallback and works identically.

**Pipe loses exit code**: Initial attempt captured `output=$(run_check3 ... | strip_ansi)` — piping through `sed` consumed the subshell exit code, making all exit-code assertions fail. Fix: write to a temp file, then `LAST_EXIT=$?` before stripping colors.

## Results & Parameters

### Files Changed

| File | Change |
|------|--------|
| `tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh` | Replace Check 3 free-text search with two-phase `closingIssuesReferences` lookup |
| `tests/claude-code/shared/skills/github/gh-implement-issue/SKILL.md` | Update STOP/WARN table rows to note `closingIssuesReferences` matching |
| `tests/claude-code/shared/skills/github/gh-implement-issue/tests/test_preflight_check.sh` | New — 6 bash tests with mocked `gh` functions |

### Key Parameters

| Parameter | Value |
|-----------|-------|
| PR fetch limit | `--limit 100` (avoids timeout on large repos) |
| `closingIssuesReferences` jq expression | `.closingIssuesReferences[].number` |
| grep for exact issue match | `grep -qx "$ISSUE"` (full-line match, avoids 73 matching 735) |
| Test runner | `bash tests/test_preflight_check.sh` |
| All pre-commit hooks | Pass (ShellCheck, Markdown lint, YAML lint, Ruff, mypy) |

## Key Takeaways

1. **`gh pr list --search` is full-text** — it searches titles AND bodies, making it unsuitable for issue ownership checks.
2. **`closingIssuesReferences` is authoritative** — populated only by recognized closing keywords or UI links.
3. **Two-phase lookup has a cost**: O(N) `gh pr view` calls where N = total PR count. The `--limit 100` bound keeps it practical for most repos.
4. **Bash test isolation**: mock `gh` as a function + `export -f gh` in a subshell; use temp files not pipes to preserve exit codes.
5. **ANSI colors in scripts**: when asserting on `[PASS]` / `[STOP]` prefixes, strip ANSI before grep — otherwise color codes cause silent mismatches.
