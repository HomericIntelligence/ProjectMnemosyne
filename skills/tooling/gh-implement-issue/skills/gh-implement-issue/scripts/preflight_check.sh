#!/usr/bin/env bash
#
# Pre-flight check before starting work on a GitHub issue.
#
# Runs 6 checks in order, stopping immediately on critical failures.
# Critical failures (exit 1): closed issue, merged PR, worktree conflict
# Warnings (exit 0): existing commits, open PRs, existing branches
#
# Usage:
#   bash /path/to/scripts/preflight_check.sh <issue-number>
#   bash "$(dirname "${BASH_SOURCE[0]}")/preflight_check.sh" <issue-number>
#
# Exit codes:
#   0 = all checks passed (or only warnings)
#   1 = critical failure - do not proceed

# Self-locating: works regardless of caller's CWD
# shellcheck disable=SC2034
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -uo pipefail

ISSUE="${1:-}"

if [[ -z "$ISSUE" ]]; then
    echo "Error: issue number required"
    echo "Usage: $0 <issue-number>"
    exit 1
fi

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

pass()  { echo -e "${GREEN}[PASS]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
stop()  { echo -e "${RED}[STOP]${NC} $*"; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

echo "Pre-flight check for issue #${ISSUE}"
echo "========================================"

# ---------------------------------------------------------------------------
# Check 1: Issue State (CRITICAL)
# ---------------------------------------------------------------------------
STATE_JSON=$(gh issue view "$ISSUE" --json state,title,closedAt 2>/dev/null) || {
    stop "Check 1: Cannot fetch issue #${ISSUE} - verify issue number"
    exit 1
}
ISSUE_STATE=$(echo "$STATE_JSON" | jq -r '.state')
ISSUE_TITLE=$(echo "$STATE_JSON" | jq -r '.title')

if [[ "$ISSUE_STATE" == "CLOSED" ]]; then
    CLOSED_AT=$(echo "$STATE_JSON" | jq -r '.closedAt')
    stop "Check 1: Issue #${ISSUE} is CLOSED (${CLOSED_AT})"
    echo "         Title: ${ISSUE_TITLE}"
    echo "         Do not proceed - work may already be complete."
    exit 1
fi
pass "Check 1: Issue #${ISSUE} is OPEN - \"${ISSUE_TITLE}\""

# ---------------------------------------------------------------------------
# Check 2: Existing commits (WARNING)
# ---------------------------------------------------------------------------
EXISTING_COMMITS=$(git log --all --oneline --grep="#${ISSUE}" 2>/dev/null | head -5)
if [[ -n "$EXISTING_COMMITS" ]]; then
    warn "Check 2: Found existing commits referencing #${ISSUE}"
    echo "$EXISTING_COMMITS" | while IFS= read -r line; do
        echo "         $line"
    done
else
    pass "Check 2: No existing commits found"
fi

# ---------------------------------------------------------------------------
# Check 3: PR Search (CRITICAL if merged, WARNING if open)
# Uses closingIssuesReferences for precise match — avoids false positives
# from text search matching issue numbers in unrelated PR titles/bodies.
# ---------------------------------------------------------------------------
CANDIDATE_JSON=$(gh pr list --state all --json number,title,state --limit 100 2>/dev/null)
MERGED_PRS=""
OPEN_PRS=""
while IFS= read -r pr_entry; do
    pr_num=$(echo "$pr_entry" | jq -r '.number')
    pr_title=$(echo "$pr_entry" | jq -r '.title')
    pr_state=$(echo "$pr_entry" | jq -r '.state')
    [[ -z "$pr_num" || "$pr_num" == "null" ]] && continue
    CLOSES=$(gh pr view "$pr_num" --json closingIssuesReferences \
        --jq '.closingIssuesReferences[].number' 2>/dev/null)
    if echo "$CLOSES" | grep -qx "$ISSUE"; then
        if [[ "$pr_state" == "MERGED" ]]; then
            MERGED_PRS+="${pr_num}: ${pr_title}"$'\n'
        elif [[ "$pr_state" == "OPEN" ]]; then
            OPEN_PRS+="${pr_num}: ${pr_title}"$'\n'
        fi
    fi
done < <(echo "$CANDIDATE_JSON" | jq -c '.[]')
MERGED_PRS="${MERGED_PRS%$'\n'}"
OPEN_PRS="${OPEN_PRS%$'\n'}"

if [[ -n "$MERGED_PRS" ]]; then
    stop "Check 3: Issue #${ISSUE} already has a MERGED PR"
    echo "$MERGED_PRS" | while IFS= read -r line; do
        echo "         PR #${line}"
    done
    echo "         Do not proceed - likely duplicate work."
    exit 1
elif [[ -n "$OPEN_PRS" ]]; then
    warn "Check 3: Issue #${ISSUE} has an OPEN PR - coordinate before proceeding"
    echo "$OPEN_PRS" | while IFS= read -r line; do
        echo "         PR #${line}"
    done
else
    pass "Check 3: No conflicting PRs found"
fi

# ---------------------------------------------------------------------------
# Check 4: Worktree conflicts (CRITICAL)
# ---------------------------------------------------------------------------
WORKTREE_MATCH=$(git worktree list 2>/dev/null | grep "$ISSUE" || true)
if [[ -n "$WORKTREE_MATCH" ]]; then
    stop "Check 4: Worktree already exists for issue #${ISSUE}"
    echo "         ${WORKTREE_MATCH}"
    echo "         Navigate to existing worktree or remove it first."
    exit 1
fi
pass "Check 4: No worktree conflicts"

# ---------------------------------------------------------------------------
# Check 5: Existing branches (WARNING)
# ---------------------------------------------------------------------------
EXISTING_BRANCHES=$(git branch --list "*${ISSUE}*" 2>/dev/null | sed 's/^[* ]*//')
if [[ -n "$EXISTING_BRANCHES" ]]; then
    warn "Check 5: Existing branches found for #${ISSUE}"
    echo "$EXISTING_BRANCHES" | while IFS= read -r line; do
        echo "         ${line}"
    done
else
    pass "Check 5: No existing branches"
fi

# ---------------------------------------------------------------------------
# Check 6: Context gathering (INFO - only reached if checks 1-5 pass)
# ---------------------------------------------------------------------------
COMMENT_COUNT=$(gh issue view "$ISSUE" --comments 2>/dev/null | grep -c "^--$" || echo "0")
info "Check 6: Issue context loaded (${COMMENT_COUNT} comment separator(s) found)"

echo "========================================"
echo -e "${GREEN}Pre-flight checks PASSED for issue #${ISSUE}${NC}"
echo "SAFE TO PROCEED with implementation."
