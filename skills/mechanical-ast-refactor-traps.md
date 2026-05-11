---
name: mechanical-ast-refactor-traps
description: "Three independently-replicable traps in mechanical batch refactors driven by Python AST + shell automation: (1) Claude Code Bash tool resets cwd between calls, so `git rebase --abort` issued in a follow-up call lands in the wrong directory and silently no-ops; (2) Python AST's `end_col_offset` overcounts past multi-byte UTF-8 characters (em-dash, Unicode arrows, etc.) so source-slicing-by-offset corrupts the next line; (3) ruff `--select G004 --fix --unsafe-fixes` detects f-string-logging anti-patterns but provides NO actual autofix despite the `help` message. Use when: (a) writing AST-based batch refactor scripts for large packages, (b) converting `logger.X(f\"...\")` to `%`-style logging across many files, (c) running multi-step git rebase operations from a Claude Code session where cwd is sandbox-reset between Bash calls, (d) AST-based source-rewriting unexpectedly corrupts adjacent lines."
category: tooling
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ast, refactor, fstring, g004, ruff, git-rebase, sandbox, cwd, end_col_offset, utf8, balanced-paren-scanner]
---
# Mechanical AST Refactor Traps

Three independently-replicable traps that bite during mechanical batch Python refactors driven by AST scripts and shell automation, captured from the 2026-05-10 ProjectHephaestus #317 f-string conversion (PR #402, 255 conversions across 13 files).

## Overview

| Attribute | Details |
|-----------|---------|
| **Date** | 2026-05-10 |
| **Objective** | Convert 255 `logger.X(f"...")` calls to `%`-style across `hephaestus/automation/*.py` |
| **Outcome** | Successfully completed via AST script; 2181 unit tests pass, 83.35% coverage |
| **Issue** | #317 |
| **PR** | #402 (auto-squash merged 23:30:33Z) |
| **Verification** | verified-local |

Three traps surfaced during this operation. They are documented together because they tend to bite in the same session: a mechanically-driven, large-scale Python source mutation (f-string-to-percent, string canonicalization, logging style enforcement) where the AST is used to locate call sites and the shell environment is managed through a multi-call Claude Code Bash tool session.

## When to Use

Use this skill — i.e., consult it before starting — when:

- Writing a Python AST-based script to batch-mutate source across many files (e.g., converting f-strings to `%`-style logging, renaming symbols, extracting call arguments).
- Running `ruff check --select G004` and considering whether `--fix` will handle it.
- Issuing multi-step git rebase / merge / cherry-pick operations from a Claude Code session where separate `Bash` tool calls are used (e.g., `cd <worktree>` in one call, then `git rebase --abort` in the next).
- Debugging why an AST-based source rewriter produces syntactically valid but semantically wrong output (next statement pulled onto the same line, indentation lost).

**Trigger phrases**:

- "Convert all f-string logging calls to %-style"
- "Run ruff --fix for G004"
- "git rebase --abort" (in a worktree from a Claude Code session)
- "AST source rewriter corrupted the next line"
- "end_col_offset" (when debugging AST-based source slicing)

## Verified Workflow

### Quick Reference

| Trap | Root Cause | Safe Workaround |
|------|-----------|----------------|
| Shell sandbox cwd-reset | Claude Code Bash sandbox resets cwd after every call; `git rebase --abort` in a follow-up call runs from the wrong directory | Issue rebase-state-mutating commands in ONE Bash call starting with `cd <abs-worktree>`, OR use `git -C <abs-worktree> rebase --abort` |
| AST `end_col_offset` UTF-8 overcounting | Python AST `end_col_offset` is a column offset computed in code-points, but multi-byte UTF-8 characters (em-dash = 3 bytes) cause it to land past the real closing `)` | Anchor only the START from AST; locate the matching `)` with a hand-rolled balanced-paren scanner |
| ruff G004 autofix is a no-op | G004 fix is a `help` suggestion, not an autofix — `--fix --unsafe-fixes` exits without touching files | Write an AST-based conversion script combined with the balanced-paren scanner |

---

### Trap 1 — Shell Sandbox Resets cwd; `git rebase --abort` No-Ops in the Wrong Directory

**Root cause.** The Claude Code Bash tool sandbox resets the working directory back to the project root after each `Bash` call. A `git rebase --abort` issued in a follow-up call therefore runs from the parent repo, not from the worktree where the rebase is live. The abort silently no-ops (no rebase in progress in the parent), leaving the worktree's rebase mid-flight with conflict markers.

**Discovery pattern.** The orphaned rebase state only surfaces later when the user asks "what are these unstaged changes?" — `git status` then shows `interactive rebase in progress` and `Unmerged paths: <file>.py`.

**Safe workaround — issue the abort inside a single Bash call that begins with `cd`:**

```bash
cd ~/.tmp/rebase-wt/pr-42 && git rebase --abort
# verify:
cd ~/.tmp/rebase-wt/pr-42 && git status
```

**Sandbox-safe alternative — use `git -C <abs-path>` so the path is in argv, not inherited cwd:**

```bash
git -C "$HOME/.tmp/rebase-wt/pr-42" rebase --abort
git -C "$HOME/.tmp/rebase-wt/pr-42" status
```

**Rule:** Any git command that mutates rebase / merge / cherry-pick state in a worktree MUST be issued either (a) inside a single Bash invocation that begins with `cd <worktree>`, or (b) via `git -C <abs-worktree-path> <subcommand>`. Never split the `cd` from the destructive git command across multiple tool calls.

---

### Trap 2 — Python AST `end_col_offset` Overcounts Past Multi-Byte UTF-8 Characters

**Root cause.** Python's AST module returns `end_col_offset` as a character-column count, but on lines containing multi-byte UTF-8 characters (em-dash `—` = 3 bytes, Unicode arrows, smart quotes, etc.) the byte offset of `end_col_offset` lands 1-3 positions past the real closing `)`. When an AST-based converter uses `text[end:]` to produce the trailing slice, it starts after the closing `)` AND after the trailing newline AND after the next line's leading whitespace — pulling the following statement onto the same line.

**Concrete example from this session.** `hephaestus/automation/planner.py:717`:

```python
# Before
logger.info(f"#{issue_number}: GO on iteration {iteration} — loop terminated")
```

The em-dash `—` caused AST to report `end_col_offset` 2 columns past the real `)`. The naive slicer produced:

```python
# Corrupted output
logger.info('#%s: GO on iteration %s — loop terminated', issue_number, iteration)               final_verdict_is_go = True
```

The next statement `final_verdict_is_go = True` was swallowed onto the same line.

**Safe workaround — balanced-paren scanner.** Anchor only the START position from AST, then walk forward with a hand-rolled scanner to find the matching `)`. See the full scanner implementation in [Results & Parameters](#results--parameters).

```python
# Usage pattern
call_start = node.col_offset  # trust the start
open_paren = source_line.index("(", call_start)
end = find_matching_paren(source, open_paren_abs_offset)
replacement = source[:start] + new_call + source[end + 1:]
```

**Rule:** Never trust AST `end_col_offset` for source-text slicing when the codebase may contain any non-ASCII character. Use a balanced-paren scanner anchored from the START.

---

### Trap 3 — ruff `--select G004 --fix --unsafe-fixes` Is a No-Op

**Root cause.** Ruff's G004 rule (`logging-f-string`) detects `logger.X(f"...")` correctly and emits a `help: Convert to lazy %-formatting` message. However, G004 has no autofix implementation — the `help` line is documentation only. Running `ruff check --select G004 --fix --unsafe-fixes` reports the violations and exits non-zero, but writes zero file changes.

This is easy to misread as "fix attempted but blocked by safety checks." It is not — the fix simply does not exist in ruff.

**Verification:**

```bash
# Produces N violations, exits non-zero, modifies NO files:
ruff check hephaestus/automation/ --select G004 --fix --unsafe-fixes
# git diff produces nothing after this command
```

**Safe workaround.** Write an AST-based conversion script (see Results & Parameters) combined with the balanced-paren scanner from Trap 2. Then run `ruff format` to clean up formatting, and manually split any lines that exceed E501 via implicit Python string concatenation:

```python
logger.info(
    "Long format string part 1 "
    "part 2 %s",
    variable,
)
```

**Rule:** Do not rely on `ruff --fix` for G004. Write or reuse an AST-based script.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| `cd` to worktree in one `Bash` call, then `git rebase --abort` in a follow-up `Bash` call (PR #399 rebase loop) | Claude Code Bash sandbox resets cwd between calls; the abort ran from the project root where no rebase was in progress. The worktree rebase (in `~/.tmp/rebase2/pr-399`) was left mid-flight with conflict markers in `hephaestus/automation/follow_up.py`. Orphaned state discovered hours later when user asked "what are these unstaged changes?" | Discovered hours later when `git status` showed `interactive rebase in progress` and `Unmerged paths: follow_up.py` — not at the time of the abort call | Issue all rebase-state-mutating git commands inside a single Bash call that begins with `cd <worktree>`, OR use `git -C <abs-path> ...` form — `-C` is sandbox-safe because the path is in the argv, not inherited cwd |
| Trusted `node.end_col_offset` from Python AST to slice source text for replacement (`source[:start] + new_call + source[end:]`) | Lines containing multi-byte UTF-8 characters (specifically the em-dash `—` in `planner.py:717` and `pr_manager.py`) caused `end_col_offset` to report 2 columns past the real closing `)`. The trailing slice started after the newline, swallowing the next statement onto the replacement line. | Corrupted output detected during post-conversion syntax check: `final_verdict_is_go = True` appeared on the same line as the preceding `logger.info(...)` call | Never trust AST `end_col_offset` for source-text slicing on codebases with non-ASCII content. Anchor the START from AST; use a balanced-paren scanner to find the real matching `)` |
| Ran `ruff check hephaestus/automation/ --select G004 --fix --unsafe-fixes` to auto-convert all f-string logging violations | ruff G004 (`logging-f-string`) has no autofix implementation — the `help: Convert to lazy %-formatting` message is documentation only, not a fix. The command exits non-zero (violations detected) but modifies zero files. | Confirmed by running `ruff check --select G004 --fix --unsafe-fixes` and checking `git diff` — no changes produced despite 255 reported violations | Use an AST-based conversion script combined with the balanced-paren scanner. ruff `--fix` is not sufficient for G004 in any version current as of 2026-05-10 |

## Results & Parameters

### Balanced-Paren Scanner (Trap 2 Workaround)

The following scanner correctly located the matching `)` for all 255 call sites in PR #402, including those with em-dash and other multi-byte UTF-8 characters.

```python
def find_matching_paren(src: str, open_paren_offset: int) -> int:
    """Return offset of matching ')' given the offset of '('.

    Skips string literals (single/double/triple-quoted with escapes)
    and line comments so nested parens inside strings are not counted.

    Args:
        src: Full source text as a Unicode string (not bytes).
        open_paren_offset: Offset of the '(' to match.

    Returns:
        Offset of the matching ')'. Returns -1 if not found (malformed source).
    """
    depth = 0
    i = open_paren_offset
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in ("'", '"'):
            # Triple or single/double quoted string — skip past close quote
            triple = src[i : i + 3]
            if triple in ("'''", '"""'):
                end_seq = triple
                j = i + 3
                while j < n - 2:
                    if src[j : j + 3] == end_seq:
                        j += 3
                        break
                    if src[j] == "\\":
                        j += 2
                    else:
                        j += 1
                i = j
                continue
            else:
                end_ch = ch
                j = i + 1
                while j < n:
                    if src[j] == end_ch:
                        j += 1
                        break
                    if src[j] == "\\":
                        j += 2
                    elif src[j] == "\n":
                        break  # unterminated string literal, bail
                    else:
                        j += 1
                i = j
                continue
        if ch == "#":
            # Line comment — skip to end of line
            while i < n and src[i] != "\n":
                i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1  # unmatched paren
```

### AST-Based Conversion Pattern (Trap 3 Workaround)

The general shape of the script that produced all 255 correct conversions (abbreviated):

```python
import ast
import re
from pathlib import Path

def convert_fstring_logging(source: str) -> str:
    """Convert logger.X(f\"...\") calls to logger.X(\"%s\", ...) style."""
    tree = ast.parse(source)
    replacements = []  # (start_offset, end_offset, new_text)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Check it's logger.X(...)
        if not (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id in ("logger", "log") and
                node.args and isinstance(node.args[0], ast.JoinedStr)):
            continue

        # Anchor START from AST (safe — start positions are always exact)
        start_line = node.lineno - 1
        start_col = node.col_offset
        start_offset = sum(len(l) + 1 for l in source.splitlines()[:start_line]) + start_col

        # Find the opening paren of the call (right after the method name)
        open_paren = source.index("(", start_offset)

        # Use balanced-paren scanner to find the real end — NOT end_col_offset
        end_offset = find_matching_paren(source, open_paren)
        if end_offset == -1:
            continue  # malformed, skip

        original_call = source[start_offset : end_offset + 1]
        new_call = rebuild_percent_call(node, source, original_call)
        if new_call != original_call:
            replacements.append((start_offset, end_offset + 1, new_call))

    # Apply replacements in reverse order so offsets stay valid
    for start, end, new_text in sorted(replacements, reverse=True):
        source = source[:start] + new_text + source[end:]

    return source
```

Key points:
- `node.lineno` / `node.col_offset` (START positions) are trusted — they are byte-exact for ASCII and correct for the first code-point of any character.
- `node.end_col_offset` is NOT used — replaced by `find_matching_paren`.
- Replacements are applied in **reverse order** to preserve earlier offsets.

### Session Statistics

| Metric | Value |
|--------|-------|
| Files converted | 13 |
| Call sites converted | 255 |
| Unit tests after conversion | 2181 passing |
| Coverage | 83.35% |
| Lines with multi-byte UTF-8 (em-dash) | 2 (planner.py:717, pr_manager.py) |
| PR | HomericIntelligence/ProjectHephaestus#402 |
| Merge time | 2026-05-10 23:30:33Z |

### git -C Form Reference

For any git command that mutates rebase/merge/cherry-pick state in a worktree, prefer the `-C` form which is sandbox-safe:

```bash
# Safe — path is in argv, not inherited cwd
git -C "$HOME/.tmp/rebase-wt/pr-42" rebase --abort
git -C "$HOME/.tmp/rebase-wt/pr-42" status
git -C "$HOME/.tmp/rebase-wt/pr-42" rebase origin/main

# Risky — relies on inherited cwd surviving sandbox reset
cd "$HOME/.tmp/rebase-wt/pr-42"
# ... (subsequent Bash call) ...
git rebase --abort  # runs from project root, not worktree
```

## Verified On

- **Project**: ProjectHephaestus `hephaestus/automation/` package
- **Session**: 2026-05-10 strict-review-then-fix-waves session
- **Trap 1**: Encountered during PR #399 rebase pass; orphaned rebase state surfaced hours later during PR #402 cleanup. Recovery: `git -C <worktree> rebase --abort`.
- **Trap 2**: Surfaced on `planner.py:717` and `pr_manager.py` (em-dash `—` on both lines). Recovered by switching to balanced-paren scanner; all 255 conversions then succeeded.
- **Trap 3**: `ruff check hephaestus/automation/ --select G004 --fix --unsafe-fixes` produced 0 file modifications despite 255 reported violations. All 255 fixed via AST script.
- **Verification level**: `verified-local` — all three workarounds confirmed against ProjectHephaestus PR #402 (merged via auto-squash). The shell-sandbox cwd-reset behavior is specific to the Claude Code Bash tool sandbox; it is verified locally but not in a generic CI environment.
