---
name: bash-upstream-pr-review-traps
description: "Implement a feature in a forked bash project and navigate maintainer review rounds. Use when: (1) contributing a new flag/env-var to an upstream bash CLI extension, (2) performing two-round review of bash scripts for logic and safety bugs, (3) debugging git branch --list exit-code trap or bash function-before-definition execution hazard."
category: tooling
date: 2026-04-27
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [bash, git-branch, function-definition, arg-parsing, ansi-color, env-var, upstream-pr, fork, open-source, review, gh-tidy]
---

# Bash Upstream PR Review: Traps and Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-27 |
| **Objective** | Implement `--auto-delete-merged` / `GH_TIDY_AUTO_DELETE_MERGED` flag in forked bash CLI extension (`HaywardMorihara/gh-tidy`), address maintainer feedback across two review rounds, and submit a clean PR |
| **Outcome** | PR #63 created at https://github.com/HaywardMorihara/gh-tidy/pull/63; all maintainer feedback addressed; two logic/safety bugs found and fixed in round 2 |
| **Verification** | verified-local — tested with `GH_TIDY_DEV_MODE=1` in throwaway git repos; CI validation pending maintainer review |
| **Source** | Session implementing gh-tidy issue #62 |

## When to Use

- Contributing a new CLI flag + env-var override to an upstream bash extension you don't maintain
- Reviewing bash scripts for logic correctness and safety (two-round review process)
- Debugging silent failures where a `git` command's exit code is misleading
- Calling color/utility functions from inside a bash `while` arg-parsing loop
- Adding env-var override notices to a bash script's startup output
- Ensuring `--value-flag`-style arguments cannot silently consume the next flag as their value

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

# Guard value-flags against consuming the next flag as value
--trunk)
  shift
  if [[ -z "$1" || "$1" == --* ]]; then
    echo "Error: --trunk requires a value" >&2; exit 1
  fi
  TRUNK_BRANCH="$1" ;;

# Place env-var override notices AFTER arg parsing, BEFORE first git op
# Use echo >&2 (not color functions) if calling from inside the while loop
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

   b. **Value-flag silently consuming the next flag as its value**:

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

   c. **Misleading prompt text** — "is the same as local `$trunk_branch`" should be
      "is merged into `$trunk_branch`" (more precise and less surprising to users)

   d. **`$problem_branches` array not declared** when AUTO_DELETE_MERGED=false skips the
      rebase section — declare it unconditionally:

      ```bash
      problem_branches=()   # declare before the if/else block that populates it
      ```

   e. **Typo in success message**: "Successfully rebase" → "Successfully rebased"

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

   Bash function definitions take effect when that line is reached during execution.
   The `while` loop runs before the function definitions below it. The result is that
   bash tries to execute `red` as a command, producing confusing `: No such file or
   directory` errors.

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

   # ← notices go HERE
   if [[ "$AUTO_DELETE_MERGED" == "true" ]]; then
     yellow "Notice: GH_TIDY_AUTO_DELETE_MERGED is set — merged branches will be deleted without prompt."
   fi
   if [[ "$TRUNK_BRANCH" != "main" ]]; then
     yellow "Notice: GH_TIDY_TRUNK_BRANCH is set — using '$TRUNK_BRANCH' as trunk."
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

   Check ALL `read -p` and `printf`/`echo` prompt calls for consistent reset behavior.

9. **Create PR against upstream**

   ```bash
   gh pr create \
     --repo HaywardMorihara/gh-tidy \
     --head mvillmow:feature/auto-delete-merged \
     --base main \
     --title "Add --auto-delete-merged flag for non-interactive use" \
     --body "Closes #62 ..."
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `if git branch --list "$branch"; then` | Used exit code of `git branch --list` to check branch existence | `git branch --list` always exits 0, even when the branch does not exist — the exit code only reflects command execution, not whether any branch was matched | Always test the OUTPUT: `[[ -n "$(git branch --list "$branch")" ]]` |
| Calling `red()` from inside arg-parsing while loop | Emitted a colored error message during argument parsing using a color function defined later in the file | Bash function definitions are not hoisted; functions defined below the while loop don't exist when the loop runs — bash tries to exec the function name, producing `: No such file or directory` | Use `echo >&2` or `printf >&2` for all error output inside arg-parsing blocks; save color functions for post-parse code |
| `--trunk` flag with no guard after inner shift | After `shift` to consume `--trunk`, used `$1` directly as `TRUNK_BRANCH` | If `--trunk` is the last arg or is followed immediately by another flag, `$1` is empty or is the next flag — the flag was silently consumed or `TRUNK_BRANCH` was set to another flag name | After shifting a value-flag, always guard: `[[ -z "$1" || "$1" == --* ]]` and emit an error if either is true |
| "is the same as local $trunk_branch" prompt text | Used this phrasing to tell users a branch matches trunk | The phrase is misleading — "same as" implies identical content, but the actual check is whether the branch is merged into trunk (a superset relationship) | Use "is merged into $trunk_branch" for accuracy |
| Assuming $problem_branches was always initialized | Used `$problem_branches` in cleanup code without unconditional declaration | When `REBASE_ALL=false` (the default), the block that populates `problem_branches` was skipped entirely — using the array later caused a bash unbound variable error | Always declare arrays unconditionally before any conditional blocks that populate them: `problem_branches=()` |
| Placing env-var notices inside the while loop | Emitted override notices during argument parsing | The CLI override for that flag may appear later in the argument list — notices emitted during parsing reflect the pre-CLI env value, not the final effective value | Place the entire notice block after the while loop closes, before the first git operation |

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

### Two-round review process summary

```text
Round 1 (structural/style):
  - Comment placement
  - Missing env-var notices for all flags
  - Help text tabs vs spaces
  - Punctuation consistency
  - ANSI reset in all read -p prompts

Round 2 (logic/safety):
  - git branch --list exit code trap
  - Value-flag silently consuming next flag
  - Misleading prompt text
  - Uninitialized array variables
  - Typos in messages
  - Function-before-definition hazard
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| gh-tidy (HaywardMorihara/gh-tidy) | Implementing issue #62 `--auto-delete-merged` flag from fork `mvillmow/gh-tidy` | PR #63 submitted; tested with `GH_TIDY_DEV_MODE=1` in throwaway repos; two review rounds completed |
