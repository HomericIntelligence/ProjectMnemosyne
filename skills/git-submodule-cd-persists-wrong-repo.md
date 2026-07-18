---
name: git-submodule-cd-persists-wrong-repo
description: "A shell `cd` into a git SUBMODULE persists across separate Bash-tool calls and silently redirects later git commands to the SUBMODULE instead of the parent superproject. Use when: (1) `git add -A` stages nothing in a meta-repo/superproject and `git status --short` is unexpectedly empty, (2) `git log --oneline -1` shows a SUBMODULE's HEAD commit when you expected the superproject's, (3) submodule pin bumps appear to have 'vanished' after you inspected a submodule with `cd sub && git ...`, (4) you ran `cd control/Agamemnon && git fetch` in one Bash call and later git commands (issued without re-cd'ing) hit the wrong repo, (5) `git rev-parse --show-toplevel` resolves to a submodule path instead of the meta-repo root."
category: tooling
date: 2026-07-18
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - git
  - submodule
  - superproject
  - cwd
  - working-directory-persists
  - bash-tool
  - git-c
  - odysseus
  - meta-repo
  - subshell
---

# A `cd` Into a Submodule Persists Across Bash Calls and Redirects Git to the Wrong Repo

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-18 |
| **Objective** | Bump all submodule pins in the Odysseus meta-repo and commit them in the PARENT superproject. |
| **Outcome** | Recovered — the bumps were never lost; a persisted `cd` into a submodule had redirected `git add`/`status`/`log` to the submodule. Re-scoping with `git -C <superproject>` staged all 14 pins correctly. |
| **Verification** | verified-local — the `git -C <superproject> add -A` recovery was executed and observed to stage all 14 submodule pins in-session; this skill PR's own CI gate not yet observed green. |
| **History** | (none yet) |

## When to Use

- `git add -A` stages nothing in a meta-repo/superproject and `git status --short` comes back empty even though you know you changed submodule pins.
- `git log --oneline -1` shows a commit that belongs to a SUBMODULE (e.g. an Agamemnon commit) when you expected the superproject's HEAD.
- Submodule pin bumps appear to have "vanished" right after you inspected a submodule with `cd sub && git rev-parse HEAD`.
- You ran something like `cd control/Agamemnon && git fetch && git rev-parse HEAD` in one Bash call, and later git commands — issued WITHOUT re-cd'ing — silently operated on the submodule.
- `git rev-parse --show-toplevel` resolves to a submodule path instead of the meta-repo root.

## Root Cause

The Bash tool's working directory **persists between separate tool invocations**. A `cd` into a
submodule made in an earlier call is never undone, so every later git command runs inside the
submodule's `.git`, not the superproject's. Git commands are cwd-relative: `git add`,
`git status`, `git commit`, and `git log` all act on whatever repository owns the current
directory. Inside a submodule that is the submodule repo — a completely different `.git` — so:

- `git add -A` stages nothing in the parent (there is nothing to stage in the submodule).
- `git status --short` is empty (the submodule tree is clean).
- `git log --oneline -1` shows the submodule's HEAD, which looks like "my commits are gone".

Nothing errors. The symptoms read like "the submodule bumps disappeared" when in fact the
commands were pointed at the wrong repo the whole time.

## Verified Workflow

### Quick Reference

```bash
# PREFERRED: never rely on the shell's cwd — target the superproject explicitly.
SUPER=/abs/path/to/Odysseus            # the meta-repo / superproject root
git -C "$SUPER" add -A
git -C "$SUPER" status --short
git -C "$SUPER" commit -S -m "chore(submodules): bump pins"
git -C "$SUPER" log --oneline -1

# Inspect a submodule WITHOUT leaking the cwd — scope the cd in a subshell:
( cd "$SUPER/control/Agamemnon" && git fetch && git rev-parse HEAD )
# cwd is unchanged outside the parentheses.

# RECOVERY when you notice commands hitting the wrong repo:
cd "$SUPER"                            # or just switch to git -C
pwd                                    # confirm you are at the meta-repo root
git rev-parse --show-toplevel          # MUST print $SUPER, not a submodule path
git add -A && git status --short       # re-run staging; the pins reappear
```

### Detailed Steps

1. **Diagnose before concluding "changes are lost."** If `git add -A` stages nothing or
   `git log` shows an unexpected commit, do NOT assume the bumps vanished. Run
   `git rev-parse --show-toplevel` — if it prints a submodule path, the cwd is wrong, not the data.
2. **Recover by re-scoping.** `cd` back to the superproject root (verify with `pwd` +
   `git rev-parse --show-toplevel`), or switch every command to `git -C /abs/superproject`.
   Re-run `git add -A`; the submodule pin changes stage correctly.
3. **Prevent it going forward — two equally good options:**
   - Use `git -C /abs/path/to/superproject <cmd>` for every git command that must act on the
     parent. This is immune to a stray persisted `cd`.
   - If you must `cd` into a submodule to inspect it, scope the change in a subshell
     `( cd sub && git ... )`, or explicitly `cd` back to the superproject root afterward.
4. **Verify the commit landed in the parent.** After committing, `git -C "$SUPER" show --stat HEAD`
   should list the submodule paths (e.g. `control/Agamemnon`) as changed entries.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git add -A` after an un-scoped `cd` into a submodule | Ran `cd control/Agamemnon && git fetch && git rev-parse HEAD` in one Bash call, then later (without re-cd'ing) `git add -A` in a separate call | The Bash cwd persisted, so `git add -A` ran INSIDE control/Agamemnon (a clean submodule tree) — it staged nothing in the parent | Always scope a submodule `cd` with a subshell `( cd sub && git ... )`, or use `git -C /abs/superproject` so the parent is targeted regardless of cwd |
| Trusted `git log` / `git status` output showing a submodule's commit | Read `git log --oneline -1` (which showed an Agamemnon commit) and an empty `git status --short` as evidence the pin bumps were lost | The commands were operating on the submodule repo because of the persisted cwd — the parent's changes were intact all along | Before diagnosing "changes lost," run `git rev-parse --show-toplevel`; if it points at a submodule, the cwd is wrong, not the data |

## Results & Parameters

Recovery that worked in-session (staged all 14 Odysseus submodule pins correctly):

```bash
SUPER=/abs/path/to/Odysseus
git -C "$SUPER" rev-parse --show-toplevel   # -> $SUPER (confirms correct repo)
git -C "$SUPER" add -A
git -C "$SUPER" status --short               # -> 14 submodule paths staged
```

Key facts:

- The Bash tool's cwd carries between separate calls; a `cd` is NOT reset per invocation.
- Git is cwd-relative: inside a submodule, `add`/`status`/`commit`/`log` act on the submodule's
  `.git`, not the superproject's — silently, with no error.
- `git -C <path>` runs as if git had started in `<path>`, ignoring the ambient cwd — the robust fix.
- A subshell `( cd sub && ... )` confines the cwd change to the parentheses.
- Companion skill for the broader Odysseus pin workflow (selective `--remote`, `git add .`
  foot-gun, rebase/justfile collisions): [[odysseus-multi-branch-submodule-pin-management]].

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Bumping all submodule pins in the meta-repo; a persisted `cd control/Agamemnon` from an inspection call redirected later `git add`/`status`/`log` to the submodule | Recovery via `git -C <superproject> add -A` staged all 14 pins; verified-local (skill PR CI gate not yet observed green) |
