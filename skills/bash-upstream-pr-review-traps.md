---
name: bash-upstream-pr-review-traps
description: "Implement a feature or fix in a forked bash project and navigate maintainer review rounds. Use when: (1) contributing a new flag/env-var to an upstream bash CLI extension, (2) performing two-round review of bash scripts for logic and safety bugs, (3) debugging git branch --list exit-code trap or bash function-before-definition hazard, (4) filing separate bug issues found during code review and opening one PR per bug with correct branch dependencies."
category: tooling
date: 2026-04-27
version: "2.0.0"
user-invocable: false
verification: verified-local
history: bash-upstream-pr-review-traps.history
tags: [bash, git-branch, function-definition, arg-parsing, ansi-color, env-var, upstream-pr, fork, open-source, review, gh-tidy, word-splitting, multi-pr, issue-filing, branch-dependency]
---

# Bash Upstream PR Review: Traps and Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-27 |
| **Objective** | Implement and review bash PRs against upstream forks, handle out-of-scope bug discovery, and manage multi-PR branch dependencies |
| **Outcome** | PR #63 (feature), PR #67/#68/#69 (bugs) created at `HaywardMorihara/gh-tidy`; all fixes verified locally |
| **Verification** | verified-local — tested with `GH_TIDY_DEV_MODE=1` in throwaway git repos; upstream CI pending |
| **History** | [changelog](./bash-upstream-pr-review-traps.history) |

## When to Use

- Contributing a new CLI flag + env-var override to an upstream bash extension you don't maintain
- Reviewing bash scripts for logic correctness and safety (two-round review process)
- Debugging silent failures where a `git` command's exit code is misleading
- Calling color/utility functions from inside a bash `while` arg-parsing loop
- Adding env-var override notices to a bash script's startup output
- Ensuring `--value-flag`-style arguments cannot silently consume the next flag as their value
- Filing separate GitHub issues for out-of-scope bugs found during code review
- Opening one PR per bug with correct branch dependencies (in-flight vs independent)
- Deciding whether a fix branch should be based on `main` or an in-flight feature branch

## Verified Workflow

### Quick Reference

```bash
# Fork and clone
gh repo fork <owner>/<repo> --clone --remote

# Implement following existing patterns exactly
# (read source first — do not rely on memory)

# Smoke test via dev mode
GH_TIDY_DEV_MODE=1 bash <script> [flags]

# Validate git branch presence correctly
# WRONG: if git branch --list "$branch"; then ...   (always exits 0)
# RIGHT: if [[ -n "$(git branch --list "$branch")" ]]; then ...

# Safe branch iteration — no word-splitting, no glob expansion
# WRONG (word-splits and glob-expands):
#   for branch in $(git branch --list); do ...
# RIGHT:
while IFS= read -r branch; do
  branch="${branch#\* }"   # strip leading "* " from current branch
  branch="${branch#  }"    # strip leading "  " from other branches
  ...
done < <(git branch --list)

# CRITICAL: when mutating a bash array inside the loop, MUST use process substitution
# (not pipe | while) — pipe creates a subshell and array mutations are lost
problem_branches=()
while IFS= read -r branch; do
  problem_branches+=("$branch")
done < <(git branch --list)

# Guard value-flags against consuming the next flag as value
--trunk)
  shift
  if [[ -z "$1" || "$1" == --* ]]; then
    echo "Error: --trunk requires a value" >&2; exit 1
  fi
  TRUNK_BRANCH="$1" ;;

# Prefer [[ -n "${var}" ]] over [[ ! -z ${var} ]]

# Place env-var override notices AFTER arg parsing, BEFORE first git op
# Use echo >&2 (not color functions) if calling from inside the while loop

# Sync fork before branching for independent bugs
git fetch upstream
git checkout main
git merge --ff-only upstream/main
git push origin main

# Parallel issue filing (independent gh issue create calls can run concurrently)
# Sequential PR creation (each needs its own number from GitHub)
# Push all branches in one call:
git push origin branch1 branch2 branch3
```

### Detailed Steps

1. **Fork the upstream repo and clone**

   ```bash
   gh repo fork HaywardMorihara/gh-tidy --clone --remote
   cd gh-tidy
   git checkout -b feature/auto-delete-merged
   ```

2. **Read the full source file before writing a single line**

   Establish: existing flag pattern, env-var naming convention, color function names,
   where arg parsing ends, where the first git operation occurs. Do NOT rely on memory
   from the issue-filing session — the actual code may differ.

3. **Implement following existing patterns exactly**

   For a new boolean flag + env-var pair:

   ```bash
   # Env-var declaration (near top with other env vars):
   AUTO_DELETE_MERGED="${GH_TIDY_AUTO_DELETE_MERGED:-false}"

   # Arg-parsing block (inside while loop):
   --auto-delete-merged)
     AUTO_DELETE_MERGED=true ;;

   # Env-var override notice block (AFTER the while loop, BEFORE first git op):
   if [[ "$AUTO_DELETE_MERGED" == "true" ]]; then
     yellow "Notice: GH_TIDY_AUTO_DELETE_MERGED is set — skipping prompt for merged branches."
   fi

   # Usage logic (where merged branch prompts appear):
   if [[ "$AUTO_DELETE_MERGED" == "true" ]]; then
     delete_branch "$branch"
   else
     # existing interactive prompt
   fi
   ```

4. **First round review — structural and style issues**

   Run through this checklist before requesting review:

   - Comment placement: forward-looking TODO must be ABOVE the while loop (not inside it)
   - Are env-var override notices present for ALL flags, not just the new one?
   - Does help text use tabs (not spaces) for flag descriptions?
   - Is punctuation consistent across messages (periods or no periods — not mixed)?
   - Do ALL `read -p "..."` prompts have ANSI color resets at the END of the prompt string?
     - Wrong: `printf '%b' "$'\e[93m'Some prompt: "`
     - Right: `printf '%b' "$'\e[93m'Some prompt: $'\e[0m'"`
   - Is the `$problem_branches` array always declared, even in non-interactive paths?
   - Are all `for branch in $(git branch ...)` loops replaced with `while IFS= read -r`?
   - Are all `[[ ! -z ${var} ]]` patterns replaced with `[[ -n "${var}" ]]`?

5. **Second round review — logic and safety bugs**

   The most dangerous bugs hide in:

   a. **`git branch --list` exit code trap** (always returns 0):

      ```bash
      # WRONG — git branch --list exits 0 even if the branch does not exist
      if git branch --list "$branch"; then
        # This ALWAYS runs — the branch may not actually exist locally
        echo "branch exists"
      fi

      # RIGHT — test the OUTPUT, not the exit code
      if [[ -n "$(git branch --list "$branch")" ]]; then
        echo "branch exists"
      fi
      ```

   b. **`for` loop word-splitting on branch names**:

      ```bash
      # WRONG — word-splits and glob-expands branch names
      for branch in $(git branch --list); do
        echo "$branch"
      done

      # RIGHT — IFS= read -r prevents both
      while IFS= read -r branch; do
        branch="${branch#\* }"   # strip "* " prefix (current branch)
        branch="${branch#  }"    # strip "  " prefix (other branches)
        echo "$branch"
      done < <(git branch --list)
      ```

      **Critical subshell trap**: if the loop body mutates a bash array, you MUST use
      process substitution `< <(...)` — NOT a pipe (`| while`). A pipe creates a subshell
      and all array mutations in the loop body are lost when the subshell exits:

      ```bash
      # WRONG — subshell loses array mutations
      git branch --list | while IFS= read -r branch; do
        problem_branches+=("$branch")   # lost! subshell exits
      done

      # RIGHT — process substitution keeps array mutations in parent shell
      while IFS= read -r branch; do
        problem_branches+=("$branch")   # persists in parent shell
      done < <(git branch --list)
      ```

   c. **Value-flag silently consuming the next flag as its value**:

      ```bash
      # WRONG — if user passes `--trunk` at the end or immediately before another flag,
      # $1 after inner shift may be empty or another flag like "--auto-delete-merged"
      --trunk)
        shift
        TRUNK_BRANCH="$1" ;;

      # RIGHT — guard against both missing value and flag-as-value
      --trunk)
        shift
        if [[ -z "$1" || "$1" == --* ]]; then
          echo "Error: --trunk requires a branch name argument" >&2
          exit 1
        fi
        TRUNK_BRANCH="$1" ;;
      ```

   d. **Misleading prompt text** — "is the same as local `$trunk_branch`" should be
      "is merged into `$trunk_branch`" (more precise and less surprising to users)

   e. **`$problem_branches` array not declared** when AUTO_DELETE_MERGED=false skips the
      rebase section — declare it unconditionally:

      ```bash
      problem_branches=()   # declare before the if/else block that populates it
      ```

   f. **Typo in success message**: "Successfully rebase" → "Successfully rebased"

   g. **`[[ ! -z ${var} ]]` antipattern** — replace with the affirmative form:

      ```bash
      # Wrong — double negation, missing quotes
      [[ ! -z ${var} ]]

      # Right — affirmative, quoted
      [[ -n "${var}" ]]
      ```

   h. **`set_trunk_branch` missing `exit 1`**:

      ```bash
      # Wrong — prints error but returns normally; script continues with TRUNK_BRANCH=""
      red "Error: Could not determine trunk branch"
      # (falls through — next line prints: "Determined '' as the trunk branch")

      # Right — halt the script immediately
      red "Error: Could not determine trunk branch"
      exit 1
      ```

6. **Bash function-before-definition execution hazard**

   If your new code calls a color/utility function (e.g., `yellow()`, `red()`) from inside
   the arg-parsing `while` loop at the top of the script, and those functions are defined
   LATER in the file, the call will fail at runtime:

   ```bash
   # Script structure (simplified):
   while [[ "$#" -gt 0 ]]; do
     case "$1" in
       --bad-flag)
         red "Error: bad flag"   # BAD — red() is not defined yet at parse time
         exit 1 ;;
     esac
   done

   red() { printf '%b' "$'\e[31m'$*$'\e[0m'" ; }   # defined here — too late
   ```

   **Fix**: Use `echo >&2` (or `printf >&2`) for any error messages emitted during
   arg parsing — these don't depend on function definitions:

   ```bash
   --bad-flag)
     echo "Error: bad flag" >&2   # SAFE — no function dependency
     exit 1 ;;
   ```

7. **Env-var override notice placement**

   Always place the notice block:
   - AFTER the `while` arg-parsing loop (so CLI args have already been applied)
   - BEFORE the first git operation (so users see actual effective values)

   ```bash
   # Parse args
   while [[ "$#" -gt 0 ]]; do ... done

   # notices go here
   if [[ "$AUTO_DELETE_MERGED" == "true" ]]; then
     yellow "Notice: GH_TIDY_AUTO_DELETE_MERGED is set — merged branches will be deleted without prompt."
   fi

   # First git operation
   git fetch --prune ...
   ```

8. **ANSI color reset in `read -p` prompts**

   When using colored prompts with `read -p`, the color must be reset before the
   cursor — otherwise the user's input appears in the prompt color:

   ```bash
   # WRONG — user input appears in yellow
   read -p "$(printf '%b' "$'\e[93m'Delete branch $branch? [y/N]: ")" response

   # RIGHT — reset at end of prompt string
   read -p "$(printf '%b' "$'\e[93m'Delete branch $branch? [y/N]: $'\e[0m'")" response
   ```

9. **Create PR against upstream (feature)**

   ```bash
   gh pr create \
     --repo HaywardMorihara/gh-tidy \
     --head mvillmow:feature/auto-delete-merged \
     --base main \
     --title "Add --auto-delete-merged flag for non-interactive use" \
     --body "Closes #62 ..."
   ```

10. **When out-of-scope bugs are found during review — file separate issues**

    Each distinct bug gets its own issue. File all issues in parallel (independent calls),
    then create PRs sequentially:

    ```bash
    # File all issues in parallel (gh issue create calls are independent)
    gh issue create --repo owner/repo --title "fix: bug 1" --body "..." &
    gh issue create --repo owner/repo --title "fix: bug 2" --body "..." &
    gh issue create --repo owner/repo --title "fix: bug 3" --body "..." &
    wait
    # Note the issue numbers assigned by GitHub

    # Sync fork before branching
    git fetch upstream
    git checkout main && git merge --ff-only upstream/main && git push origin main

    # Create branches (see dependency decision tree below)
    # Push all branches in one call
    git push origin branch1 branch2 branch3

    # Create PRs sequentially (each needs its own number)
    gh pr create --repo owner/repo --head fork:branch1 --base main --title "..." --body "..."
    gh pr create --repo owner/repo --head fork:branch2 --base main --title "..." --body "..."
    gh pr create --repo owner/repo --head fork:branch3 --base main --title "..." --body "..."
    ```

11. **Branch dependency decision tree**

    Before creating a fix branch, decide its base:

    ```text
    Does the bug touch code that was already modified by an in-flight PR?
    YES → git checkout <in-flight-branch>
          git checkout -b <issue>-<description>
          PR body note: "Based on #<PR>; needs rebase onto main after #<PR> merges"
    NO  → git checkout main && git pull --ff-only
          git checkout -b <issue>-<description>
    ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `if git branch --list "$branch"; then` | Used exit code of `git branch --list` to check branch existence | `git branch --list` always exits 0, even when the branch does not exist — the exit code only reflects command execution, not whether any branch was matched | Always test the OUTPUT: `[[ -n "$(git branch --list "$branch")" ]]` |
| Calling `red()` from inside arg-parsing while loop | Emitted a colored error message during argument parsing using a color function defined later in the file | Bash function definitions are not hoisted; functions defined below the while loop don't exist when the loop runs | Use `echo >&2` or `printf >&2` for all error output inside arg-parsing blocks |
| `--trunk` flag with no guard after inner shift | After `shift` to consume `--trunk`, used `$1` directly as `TRUNK_BRANCH` | If `--trunk` is the last arg or is followed immediately by another flag, `$1` is empty or another flag name | After shifting a value-flag, always guard: `[[ -z "$1" || "$1" == --* ]]` and emit an error |
| "is the same as local $trunk_branch" prompt text | Used this phrasing to tell users a branch matches trunk | The phrase is misleading — "same as" implies identical content, but the check is whether the branch is merged into trunk | Use "is merged into $trunk_branch" for accuracy |
| Assuming $problem_branches was always initialized | Used `$problem_branches` in cleanup code without unconditional declaration | When `REBASE_ALL=false`, the block that populates `problem_branches` was skipped — using the array later caused an unbound variable error | Always declare arrays unconditionally before conditional blocks that populate them |
| Placing env-var notices inside the while loop | Emitted override notices during argument parsing | The CLI override for that flag may appear later in the argument list | Place the entire notice block after the while loop closes, before the first git operation |
| `for branch in $(git branch ...)` loop | Iterated over branch names using command substitution in a for-loop | Word-splits on spaces/newlines and glob-expands special characters; pipe subshell loses bash array mutations | Use `while IFS= read -r branch; do ... done < <(git branch ...)` — process substitution keeps mutations in parent shell |
| `set_trunk_branch` missing `exit 1` | Function printed an error but returned normally | Script continued with `TRUNK_BRANCH=""`, printed `"Determined '' as the trunk branch"`, then failed on `git checkout ` (empty argument) | Always add `exit 1` immediately after the error message in error-handling branches |
| `[[ ! -z ${var} ]]` instead of `[[ -n "${var}" ]]` | Used negative-of-zero check throughout `set_trunk_branch` (8 occurrences) | Double negation is harder to read; missing quotes allow glob expansion of `$var` | Prefer the affirmative form `[[ -n "${var}" ]]` with double-quoted variable |
| Basing dependent fix branch on `main` | Created branch for a bug in code already modified by in-flight PR #63, starting from `main` | Would have conflicted with in-flight changes — the for-loops were already modified by PR #63's branch | If the buggy code was already touched by an in-flight PR, base the fix branch on that PR's branch; note the dependency in the PR body |

## Results & Parameters

### Pattern: Complete new flag + env-var template for bash CLI

```bash
# 1. Near the top — env-var with default:
FLAG_NAME="${GH_TIDY_FLAG_NAME:-false}"

# 2. In the while/case arg-parsing block:
--flag-name)
  FLAG_NAME=true ;;

# 3. After the while loop closes, before first git op — override notices:
if [[ "$FLAG_NAME" == "true" ]]; then
  yellow "Notice: GH_TIDY_FLAG_NAME is set — <describe behavior>."
fi

# 4. At the point of use — skip/automate the interactive prompt:
if [[ "$FLAG_NAME" == "true" ]]; then
  <automated action>
else
  read -p "$(printf '%b' "$'\e[93m'<Prompt text>? [y/N]: $'\e[0m'")" response
  if [[ "$response" =~ ^[Yy]$ ]]; then
    <action>
  fi
fi
```

### git branch existence check (correct pattern)

```bash
# Test OUTPUT, not exit code
branch_exists_locally() {
  local branch="$1"
  [[ -n "$(git branch --list "$branch")" ]]
}
```

### Value-flag arg-parsing guard (correct pattern)

```bash
--trunk)
  shift
  if [[ -z "$1" || "$1" == --* ]]; then
    echo "Error: --trunk requires a branch name argument" >&2
    exit 1
  fi
  TRUNK_BRANCH="$1" ;;
```

### Safe branch iteration with array mutation

```bash
# Correct form — process substitution preserves array in parent shell
problem_branches=()
while IFS= read -r branch; do
  branch="${branch#\* }"   # strip "* " (current branch marker)
  branch="${branch#  }"    # strip "  " (regular branch indent)
  [[ -z "$branch" ]] && continue
  problem_branches+=("$branch")
done < <(git branch --list)
# problem_branches is fully populated here
```

### Parallel issue filing, sequential PR creation

```bash
# File all issues in parallel — save the issue numbers
IDS=()
while IFS= read -r id; do IDS+=("$id"); done < <(
  gh issue create --repo owner/repo --title "fix: bug 1" --body "..." --json number --jq .number &
  gh issue create --repo owner/repo --title "fix: bug 2" --body "..." --json number --jq .number &
  gh issue create --repo owner/repo --title "fix: bug 3" --body "..." --json number --jq .number &
  wait
)

# Push all branches in one call
git push origin "${IDS[0]}-bug1" "${IDS[1]}-bug2" "${IDS[2]}-bug3"

# Create PRs sequentially
gh pr create --repo owner/repo --head fork:"${IDS[0]}-bug1" --base main --title "..." --body "Fixes #${IDS[0]}"
gh pr create --repo owner/repo --head fork:"${IDS[1]}-bug2" --base main --title "..." --body "Fixes #${IDS[1]}"
gh pr create --repo owner/repo --head fork:"${IDS[2]}-bug3" --base main --title "..." --body "Fixes #${IDS[2]}"
```

### Issue body quality checklist

```text
- Exact file + line numbers of the bug
- Minimal code snippet showing the bug (not the whole function)
- Fix snippet (the correct code)
- Impact/scope (N occurrences, what breaks)
- Title format: "fix(scope): <short description>"
```

### Two-round review process summary

```text
Round 1 (structural/style):
  - Comment placement
  - Missing env-var notices for all flags
  - Help text tabs vs spaces
  - Punctuation consistency
  - ANSI reset in all read -p prompts
  - for-loops using $(git branch ...) — replace with while IFS= read -r
  - [[ ! -z ${var} ]] — replace with [[ -n "${var}" ]]

Round 2 (logic/safety):
  - git branch --list exit code trap
  - Value-flag silently consuming next flag
  - Misleading prompt text
  - Uninitialized array variables
  - Typos in messages
  - Function-before-definition hazard
  - Missing exit 1 after error messages in utility functions
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| gh-tidy (HaywardMorihara/gh-tidy) | PR #63 `--auto-delete-merged` feature (issue #62) | Two review rounds; verified locally with `GH_TIDY_DEV_MODE=1` |
| gh-tidy (HaywardMorihara/gh-tidy) | PRs #67/#68/#69 — three bug fixes found during PR #63 review | Issues #64 (word-split), #65 (exit 1), #66 (style); #69 branched off #63's branch; #67/#68 branched off main |
