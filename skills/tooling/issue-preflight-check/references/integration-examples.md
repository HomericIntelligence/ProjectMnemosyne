# Integration Examples: Issue Pre-Flight Check

## Overview

This document provides concrete examples of how to integrate the `issue-preflight-check` skill into various workflows, automation scripts, and development processes.

---

## Table of Contents

1. [Manual Command-Line Usage](#manual-command-line-usage)
2. [Shell Aliases and Functions](#shell-aliases-and-functions)
3. [GitHub Workflows (CI/CD)](#github-workflows-cicd)
4. [Git Hooks](#git-hooks)
5. [Integration with Existing Skills](#integration-with-existing-skills)
6. [IDE Integration](#ide-integration)
7. [Team Onboarding](#team-onboarding)
8. [Automation Scripts](#automation-scripts)

---

## Manual Command-Line Usage

### Basic Pre-Flight Check

```bash
# Before starting work on issue #686
ISSUE=686

# Run all 6 checks manually
echo "Pre-flight check for issue #$ISSUE"

# 1. Issue State
gh issue view $ISSUE --json state,title,closedAt

# 2. Git History
git log --all --oneline --grep="$ISSUE" | head -5

# 3. PR Search
gh pr list --search "$ISSUE" --state all --json number,title,state

# 4. Worktree Check
git worktree list | grep "$ISSUE"

# 5. Branch Check
git branch --list "*$ISSUE*"

# 6. Context
gh issue view $ISSUE --comments
```

### Quick One-Liner

```bash
# Abbreviated check (critical checks only)
ISSUE=686
gh issue view $ISSUE --json state && \
gh pr list --search "$ISSUE" --state all --json number,state && \
git worktree list | grep "$ISSUE" && \
echo "✅ Critical checks passed"
```

---

## Shell Aliases and Functions

### Bash/Zsh Function (Recommended)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Full pre-flight check with colored output
preflight() {
  local issue_number=$1
  local RED='\033[0;31m'
  local GREEN='\033[0;32m'
  local YELLOW='\033[1;33m'
  local NC='\033[0m' # No Color

  if [ -z "$issue_number" ]; then
    echo "Usage: preflight <issue-number>"
    return 1
  fi

  echo "================================================"
  echo "Pre-Flight Check: Issue #$issue_number"
  echo "================================================"
  echo

  # Check 1: Issue State
  echo -n "Check 1/6: Issue State... "
  if ! state_json=$(gh issue view "$issue_number" --json state,title,closedAt 2>&1); then
    echo -e "${RED}FAILED${NC}"
    echo "  Issue not found or inaccessible"
    return 1
  fi

  state=$(echo "$state_json" | jq -r '.state')
  if [ "$state" != "OPEN" ]; then
    echo -e "${RED}FAILED${NC}"
    echo "  Issue is $state"
    return 1
  fi
  echo -e "${GREEN}PASSED${NC}"

  # Check 2: Git History
  echo -n "Check 2/6: Git History... "
  commits=$(git log --all --oneline --grep="$issue_number" 2>&1 | head -5)
  if [ -n "$commits" ]; then
    echo -e "${YELLOW}WARNING${NC}"
    echo "  Existing commits found:"
    echo "$commits" | sed 's/^/    /'
  else
    echo -e "${GREEN}PASSED${NC}"
  fi

  # Check 3: PR Search
  echo -n "Check 3/6: PR Search... "
  prs=$(gh pr list --search "$issue_number" --state all --json number,title,state 2>&1)

  merged_count=$(echo "$prs" | jq '[.[] | select(.state=="MERGED")] | length' 2>/dev/null || echo "0")
  if [ "$merged_count" -gt 0 ]; then
    echo -e "${RED}FAILED${NC}"
    echo "  MERGED PR found - work complete"
    echo "$prs" | jq '.[] | select(.state=="MERGED")' | sed 's/^/    /'
    return 1
  fi

  open_count=$(echo "$prs" | jq '[.[] | select(.state=="OPEN")] | length' 2>/dev/null || echo "0")
  if [ "$open_count" -gt 0 ]; then
    echo -e "${YELLOW}WARNING${NC}"
    echo "  OPEN PR found - coordinate first"
    echo "$prs" | jq '.[] | select(.state=="OPEN")' | sed 's/^/    /'
  else
    echo -e "${GREEN}PASSED${NC}"
  fi

  # Check 4: Worktree
  echo -n "Check 4/6: Worktree... "
  if worktree=$(git worktree list | grep "$issue_number"); then
    echo -e "${RED}FAILED${NC}"
    echo "  Worktree exists:"
    echo "$worktree" | sed 's/^/    /'
    return 1
  fi
  echo -e "${GREEN}PASSED${NC}"

  # Check 5: Branches
  echo -n "Check 5/6: Branches... "
  if branches=$(git branch --list "*$issue_number*"); then
    echo -e "${YELLOW}WARNING${NC}"
    echo "  Existing branches:"
    echo "$branches" | sed 's/^/    /'
  else
    echo -e "${GREEN}PASSED${NC}"
  fi

  # Check 6: Context
  echo -n "Check 6/6: Loading Context... "
  context_file="/tmp/preflight_${issue_number}.md"
  if gh issue view "$issue_number" --comments > "$context_file" 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
    echo "  Context saved: $context_file"
  else
    echo -e "${RED}FAILED${NC}"
    return 1
  fi

  echo
  echo "================================================"
  echo -e "${GREEN}✅ Pre-Flight Complete${NC}"
  echo "================================================"
  echo
  echo "Next steps:"
  echo "  1. Review: cat $context_file"
  echo "  2. Branch: git checkout -b $issue_number-description"
  echo "  3. Worktree: git worktree add .worktrees/issue-$issue_number -b $issue_number-description"
  echo

  return 0
}
```

**Usage**:

```bash
preflight 686
```

### Simple Alias (Quick Check)

```bash
# Add to ~/.bashrc or ~/.zshrc
alias pf='f() { gh issue view "$1" --json state && gh pr list --search "$1" --state all; }; f'
```

**Usage**:

```bash
pf 686  # Quick state + PR check
```

---

## GitHub Workflows (CI/CD)

### Workflow 1: Pre-Flight on Issue Assignment

`.github/workflows/preflight-on-assignment.yml`:

```yaml
name: Pre-Flight Check on Assignment

on:
  issues:
    types: [assigned]

jobs:
  preflight:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for git log search

      - name: Check Issue State
        id: issue_state
        run: |
          state=$(gh issue view ${{ github.event.issue.number }} --json state --jq '.state')
          echo "state=$state" >> $GITHUB_OUTPUT

          if [ "$state" != "OPEN" ]; then
            echo "::error::Issue is $state, not OPEN"
            exit 1
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Search for Existing Commits
        id: git_search
        run: |
          commits=$(git log --all --oneline --grep="${{ github.event.issue.number }}" | head -5)
          if [ -n "$commits" ]; then
            echo "::warning::Existing commits found for issue #${{ github.event.issue.number }}"
            echo "$commits"
          fi

      - name: Search for Existing PRs
        id: pr_search
        run: |
          prs=$(gh pr list --search "${{ github.event.issue.number }}" --state all --json number,state)
          merged_count=$(echo "$prs" | jq '[.[] | select(.state=="MERGED")] | length')

          if [ "$merged_count" -gt 0 ]; then
            echo "::error::MERGED PR found for issue #${{ github.event.issue.number }}"
            echo "$prs" | jq '.[] | select(.state=="MERGED")'
            exit 1
          fi

          open_count=$(echo "$prs" | jq '[.[] | select(.state=="OPEN")] | length')
          if [ "$open_count" -gt 0 ]; then
            echo "::warning::OPEN PR found for issue #${{ github.event.issue.number }}"
            echo "$prs" | jq '.[] | select(.state=="OPEN")'
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Post Pre-Flight Results
        if: success()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ **Pre-Flight Check Passed**\n\nAll safety checks completed successfully. Safe to proceed with implementation.\n\n**Checks:**\n- ✅ Issue is OPEN\n- ✅ No conflicting PRs\n- ✅ No duplicate commits detected\n\n**Next Steps:**\n1. Create feature branch: `git checkout -b ' + context.issue.number + '-description`\n2. Begin implementation following issue requirements'
            })

      - name: Post Pre-Flight Failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ **Pre-Flight Check Failed**\n\nSafety checks detected potential conflicts. Review workflow logs for details.\n\n**Do not proceed** until conflicts are resolved.'
            })
```

### Workflow 2: Pre-Flight as Reusable Action

`.github/workflows/preflight-check.yml`:

```yaml
name: Reusable Pre-Flight Check

on:
  workflow_call:
    inputs:
      issue_number:
        required: true
        type: number
    outputs:
      status:
        description: "Pre-flight check status"
        value: ${{ jobs.preflight.outputs.status }}

jobs:
  preflight:
    runs-on: ubuntu-latest
    outputs:
      status: ${{ steps.summary.outputs.status }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Pre-Flight Checks
        id: checks
        run: |
          # Check 1: Issue State
          state=$(gh issue view ${{ inputs.issue_number }} --json state --jq '.state')
          [ "$state" = "OPEN" ] && echo "✅ Issue OPEN" || exit 1

          # Check 3: PR Search (skip Check 2 for speed)
          merged=$(gh pr list --search "${{ inputs.issue_number }}" --state merged --json number)
          [ "$merged" = "[]" ] && echo "✅ No merged PRs" || exit 1

          echo "status=passed" >> $GITHUB_OUTPUT
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Summary
        id: summary
        run: |
          if [ "${{ steps.checks.outcome }}" = "success" ]; then
            echo "status=passed" >> $GITHUB_OUTPUT
          else
            echo "status=failed" >> $GITHUB_OUTPUT
          fi
```

**Usage in another workflow**:

```yaml
jobs:
  validate:
    uses: ./.github/workflows/preflight-check.yml
    with:
      issue_number: 686

  implement:
    needs: validate
    if: needs.validate.outputs.status == 'passed'
    runs-on: ubuntu-latest
    steps:
      - name: Begin Implementation
        run: echo "Pre-flight passed, starting work..."
```

---

## Git Hooks

### Pre-Commit Hook

`.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit hook: Verify issue in commit message is still open

commit_msg_file="$1"
commit_msg=$(cat "$commit_msg_file")

# Extract issue number from commit message
issue_number=$(echo "$commit_msg" | grep -oP '#\K\d+' | head -1)

if [ -n "$issue_number" ]; then
  echo "Verifying issue #$issue_number is still open..."

  # Check issue state
  if ! state=$(gh issue view "$issue_number" --json state --jq '.state' 2>/dev/null); then
    echo "⚠️  Warning: Could not verify issue #$issue_number"
    echo "   Proceeding anyway (may be offline)"
  elif [ "$state" != "OPEN" ]; then
    echo "❌ Error: Issue #$issue_number is $state"
    echo "   You're committing to a closed issue!"
    echo "   Verify this is intentional before proceeding."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  else
    echo "✅ Issue #$issue_number is OPEN"
  fi
fi

exit 0
```

**Make executable**:

```bash
chmod +x .git/hooks/pre-commit
```

### Prepare-Commit-Msg Hook

`.git/hooks/prepare-commit-msg`:

```bash
#!/bin/bash
# Prepare-commit-msg: Add issue context to commit message

commit_msg_file="$1"
commit_source="$2"

# Only run for regular commits (not merge, squash, etc.)
[ "$commit_source" = "message" ] || [ "$commit_source" = "" ] || exit 0

# Check if currently on issue branch
current_branch=$(git branch --show-current)
issue_number=$(echo "$current_branch" | grep -oP '^\d+' || echo "")

if [ -n "$issue_number" ]; then
  # Get issue title
  issue_title=$(gh issue view "$issue_number" --json title --jq '.title' 2>/dev/null)

  if [ -n "$issue_title" ]; then
    # Add issue reference comment to commit message
    echo "" >> "$commit_msg_file"
    echo "# Issue #$issue_number: $issue_title" >> "$commit_msg_file"
  fi
fi
```

**Make executable**:

```bash
chmod +x .git/hooks/prepare-commit-msg
```

---

## Integration with Existing Skills

### Integration 1: With `gh-implement-issue` Workflow

**Enhanced gh-implement-issue.sh**:

```bash
#!/bin/bash
# gh-implement-issue: Automated issue implementation workflow

issue_number=$1

if [ -z "$issue_number" ]; then
  echo "Usage: gh-implement-issue <issue-number>"
  exit 1
fi

echo "========================================="
echo "GitHub Issue Implementation Workflow"
echo "Issue #$issue_number"
echo "========================================="
echo

# STEP 1: Pre-Flight Check (CRITICAL)
echo "Step 1/5: Running Pre-Flight Check..."
if ! preflight "$issue_number"; then
  echo "❌ Pre-flight failed - STOPPING"
  exit 1
fi
echo "✅ Pre-flight passed"
echo

# STEP 2: Read Issue Context
echo "Step 2/5: Loading Issue Context..."
context_file="/tmp/issue_${issue_number}_context.md"
gh issue view "$issue_number" --comments > "$context_file"
echo "Context saved to: $context_file"
echo

# STEP 3: Create Worktree
echo "Step 3/5: Creating Worktree..."
branch_name="${issue_number}-auto-impl"
worktree_path=".worktrees/issue-${issue_number}"

git worktree add "$worktree_path" -b "$branch_name"
cd "$worktree_path" || exit 1
echo "Switched to worktree: $worktree_path"
echo

# STEP 4: Begin Implementation
echo "Step 4/5: Ready for Implementation"
echo "Review context: cat $context_file"
echo "Current directory: $(pwd)"
echo

# STEP 5: Instructions
echo "Step 5/5: Next Steps"
echo "1. Implement changes following issue requirements"
echo "2. Commit: git commit -m 'type(scope): description (#$issue_number)'"
echo "3. Push: git push -u origin $branch_name"
echo "4. Create PR: gh pr create --body 'Closes #$issue_number'"
echo

# Open context in editor (optional)
if command -v code >/dev/null 2>&1; then
  echo "Opening context in VS Code..."
  code "$context_file"
fi
```

**Usage**:

```bash
./gh-implement-issue.sh 686
# Automatically runs preflight, creates worktree, loads context
```

---

### Integration 2: With `planning-implementation-from-issue`

**planning-workflow.sh**:

```bash
#!/bin/bash
# Planning workflow with pre-flight check

issue_number=$1

# Always run pre-flight BEFORE planning
echo "Pre-flight check before planning..."
if ! preflight "$issue_number"; then
  echo "❌ Cannot plan - pre-flight failed"
  exit 1
fi

# Load context
echo "Loading issue context..."
gh issue view "$issue_number" --comments > "/tmp/plan_context_${issue_number}.md"

# Enter planning mode
echo "Entering planning mode..."
echo "Context available at: /tmp/plan_context_${issue_number}.md"

# Create planning document
cat > "/tmp/plan_${issue_number}.md" <<EOF
# Implementation Plan: Issue #${issue_number}

## Pre-Flight Results
✅ All pre-flight checks passed
- Issue is OPEN
- No conflicting PRs
- No worktree conflicts
- No duplicate work detected

## Issue Context
[Review /tmp/plan_context_${issue_number}.md for full details]

## Implementation Plan
[Begin planning here...]

EOF

# Open planning document
if command -v code >/dev/null 2>&1; then
  code "/tmp/plan_${issue_number}.md"
else
  echo "Plan created: /tmp/plan_${issue_number}.md"
fi
```

---

### Integration 3: With `commit-commands:commit-push-pr`

**commit-pr-wrapper.sh**:

```bash
#!/bin/bash
# Wrapper for commit-push-pr with pre-flight re-check

# Extract issue number from current branch
branch=$(git branch --show-current)
issue_number=$(echo "$branch" | grep -oP '^\d+')

if [ -z "$issue_number" ]; then
  echo "Cannot extract issue number from branch: $branch"
  echo "Proceeding without pre-flight check..."
else
  # Re-run critical checks before creating PR
  echo "Re-checking issue state before PR creation..."

  state=$(gh issue view "$issue_number" --json state --jq '.state')
  if [ "$state" != "OPEN" ]; then
    echo "❌ STOP: Issue #$issue_number is $state"
    echo "Cannot create PR for closed issue"
    exit 1
  fi

  # Check for duplicate PRs
  existing_prs=$(gh pr list --search "$issue_number" --state open --json number)
  if [ "$existing_prs" != "[]" ]; then
    echo "⚠️  WARNING: Open PR already exists for issue #$issue_number"
    echo "$existing_prs" | jq '.[].number'
    read -p "Create duplicate PR anyway? (y/N) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
  fi
fi

# Proceed with commit-push-pr
echo "Creating PR..."
gh pr create --body "Closes #$issue_number" "$@"
```

---

## IDE Integration

### VS Code Task

`.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Pre-Flight Check",
      "type": "shell",
      "command": "preflight",
      "args": ["${input:issueNumber}"],
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Implement Issue",
      "type": "shell",
      "command": "gh-implement-issue",
      "args": ["${input:issueNumber}"],
      "dependsOn": "Pre-Flight Check",
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "issueNumber",
      "type": "promptString",
      "description": "GitHub Issue Number"
    }
  ]
}
```

**Usage**:

- `Cmd/Ctrl + Shift + P` → "Tasks: Run Task" → "Pre-Flight Check"
- Enter issue number
- View results in terminal

### VS Code Snippet

`.vscode/snippets.code-snippets`:

```json
{
  "Pre-Flight Check": {
    "prefix": "preflight",
    "body": [
      "# Pre-Flight Check: Issue #${1:number}",
      "",
      "gh issue view ${1:number} --json state,title,closedAt",
      "git log --all --oneline --grep='${1:number}' | head -5",
      "gh pr list --search '${1:number}' --state all --json number,title,state",
      "git worktree list | grep '${1:number}'",
      "git branch --list '*${1:number}*'",
      "gh issue view ${1:number} --comments"
    ],
    "description": "Insert pre-flight check commands"
  }
}
```

---

## Team Onboarding

### New Developer Checklist

**onboarding/developer-setup.md**:

```markdown
# Developer Setup: ProjectScylla

## Pre-Flight Check Setup (Required)

Before you can start working on issues, set up the pre-flight check workflow:

### 1. Install Shell Function

Add to `~/.bashrc` or `~/.zshrc`:

\`\`\`bash
# Paste the preflight function from:
# .claude-plugin/skills/issue-preflight-check/references/integration-examples.md
\`\`\`

Reload shell:
\`\`\`bash
source ~/.bashrc  # or ~/.zshrc
\`\`\`

### 2. Test Pre-Flight

Try on a closed issue (should fail):
\`\`\`bash
preflight 1
\`\`\`

Expected: "Issue is CLOSED" error

Try on open issue:
\`\`\`bash
preflight <open-issue-number>
\`\`\`

Expected: "Pre-Flight Complete" success

### 3. Set Up Git Hooks (Optional)

\`\`\`bash
# Copy pre-commit hook
cp .github/hooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
\`\`\`

### 4. Workflow: Starting New Issue

**ALWAYS run pre-flight before starting work:**

\`\`\`bash
# 1. Pre-flight check
preflight <issue-number>

# 2. If passed, create worktree
git worktree add .worktrees/issue-<number> -b <number>-description

# 3. Navigate and begin work
cd .worktrees/issue-<number>
\`\`\`

### 5. Common Mistakes (Avoid These!)

❌ DON'T:
- Skip pre-flight check
- Work on closed issues
- Create worktree without checking for existing one
- Ignore warnings about existing PRs

✅ DO:
- Run pre-flight before every new issue
- Stop if critical checks fail
- Investigate warnings before proceeding
- Read full issue context with --comments
\`\`\`

---

## Automation Scripts

### Batch Pre-Flight for Multiple Issues

**scripts/batch-preflight.sh**:

```bash
#!/bin/bash
# Run pre-flight on multiple issues

issues=("$@")

if [ ${#issues[@]} -eq 0 ]; then
  echo "Usage: batch-preflight.sh <issue1> <issue2> ..."
  exit 1
fi

echo "========================================"
echo "Batch Pre-Flight Check"
echo "Issues: ${issues[*]}"
echo "========================================"
echo

passed=0
failed=0
warnings=0

for issue in "${issues[@]}"; do
  echo "Checking issue #$issue..."

  # Run preflight in subshell to prevent early exit
  if (preflight "$issue" >/dev/null 2>&1); then
    echo "  ✅ PASSED"
    ((passed++))
  else
    echo "  ❌ FAILED"
    ((failed++))
  fi

  # Check for warnings (heuristic: look for existing commits/PRs)
  if git log --all --oneline --grep="$issue" | grep -q .; then
    echo "  ⚠️  Has existing commits"
    ((warnings++))
  fi

  echo
done

echo "========================================"
echo "Batch Results"
echo "========================================"
echo "Total: ${#issues[@]}"
echo "Passed: $passed"
echo "Failed: $failed"
echo "Warnings: $warnings"
echo

# Generate safe-to-work list
echo "Safe to work on:"
for issue in "${issues[@]}"; do
  if (preflight "$issue" >/dev/null 2>&1); then
    echo "  - Issue #$issue"
  fi
done
```

**Usage**:

```bash
./scripts/batch-preflight.sh 686 687 688 689
```

---

### Stale Worktree Cleanup

**scripts/cleanup-stale-worktrees.sh**:

```bash
#!/bin/bash
# Clean up worktrees for merged issues

echo "Finding stale worktrees..."

git worktree list --porcelain | while read -r line; do
  if [[ $line =~ ^worktree\ (.+)$ ]]; then
    worktree_path="${BASH_REMATCH[1]}"
  elif [[ $line =~ ^branch\ refs/heads/(.+)$ ]]; then
    branch="${BASH_REMATCH[1]}"

    # Extract issue number from branch name
    issue_number=$(echo "$branch" | grep -oP '^\d+')

    if [ -n "$issue_number" ]; then
      # Check if issue is closed
      state=$(gh issue view "$issue_number" --json state --jq '.state' 2>/dev/null)

      if [ "$state" = "CLOSED" ]; then
        echo "Found stale worktree for closed issue #$issue_number"
        echo "  Path: $worktree_path"
        echo "  Branch: $branch"

        # Check if branch is merged
        if git branch --merged main | grep -q "$branch"; then
          echo "  Status: MERGED - safe to cleanup"

          read -p "  Remove worktree? (y/N) " -n 1 -r
          echo
          if [[ $REPLY =~ ^[Yy]$ ]]; then
            git worktree remove "$worktree_path"
            git branch -d "$branch"
            echo "  ✅ Cleaned up"
          fi
        else
          echo "  Status: NOT MERGED - manual review needed"
        fi

        echo
      fi
    fi
  fi
done
```

---

## Summary of Integration Points

| Integration Point | Automation Level | Recommended For |
|-------------------|------------------|-----------------|
| Manual CLI | Low | Individual developers |
| Shell Function | Medium | Team standard |
| GitHub Workflows | High | CI/CD automation |
| Git Hooks | Medium | Local enforcement |
| IDE Tasks | Medium | VS Code users |
| Batch Scripts | High | Maintainers/leads |
| Skill Integration | High | Automated workflows |

---

*Use these examples as templates and customize for your specific workflow needs.*
