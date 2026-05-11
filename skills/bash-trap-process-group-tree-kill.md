---
name: bash-trap-process-group-tree-kill
description: "Kill the entire descendant process tree of a bash orchestrator on Ctrl-C/SIGTERM by enabling job control (set -m), tracking backgrounded job PIDs, and signalling negative pgids in INT/TERM/HUP traps. Use when: (1) a bash script backgrounds work with & and those jobs spawn their own descendants (Python, gh, claude, subprocesses), (2) Ctrl-C leaves orphan processes alive, (3) trap kill $(jobs -p) only hits direct children."
category: tooling
date: 2026-05-11
version: "1.0.0"
user-invocable: false
tags:
- bash
- traps
- signals
- process-groups
- sigint
- sigterm
- cleanup
- orchestrator
---

# Bash Trap + Process-Group Tree Kill

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | Make a bash orchestrator that backgrounds long-running work clean up the entire descendant tree on Ctrl-C / SIGTERM / SIGHUP — not just direct children. |
| **Outcome** | SUCCESS (verified-local). Synthetic 9-process / 3-pgid test rig: SIGINT to the parent leaves zero descendants alive, parent exits 130. |
| **Originating use case** | `scripts/run_automation_loop.sh` in ProjectHephaestus (`feat/automation-loop-6phase-knobs`, commit `5e9a9de`) — backgrounded `process_repo` subshells were spawning Python / `claude` / `gh` descendants that survived Ctrl-C. |
| **Verification** | verified-local (synthetic test passed; production CI Ctrl-C not yet exercised) |

## When to Use

Apply this pattern when **all** of these are true:

- You are writing a **bash** orchestrator (POSIX shell variants without job control will not work the same).
- The script backgrounds units of work via `&` (a worker pool, fan-out across repos / shards / phases, etc.).
- Those backgrounded jobs themselves spawn descendants — Python scripts, `claude`, `gh`, `git`, any subprocess pipeline.
- Users expect Ctrl-C to stop **everything** with no orphan processes left behind.
- A naive `trap "kill $(jobs -p)" INT` does not work because `jobs -p` returns positive PIDs that only signal direct children — grandchildren and below are orphaned.

Do **not** use this pattern when:

- The script does no backgrounding (`&` never appears) — normal bash signal delivery is sufficient.
- The backgrounded jobs are simple commands with no descendants — `kill $(jobs -p)` is enough.
- You are inside a Python / Node / Go process — use that runtime's signal handling instead (see `graceful-signal-handling`, `e2e-runner-hang-signal-fixes`, `batch-subprocess-signal-hang`).

## Verified Workflow

### Quick Reference

Drop-in template for any bash orchestrator that backgrounds work:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1) Enable job control so each `&` job gets its OWN process group
#    (pgid == job's PID). Without this, all background jobs share the
#    parent's pgid and `kill -TERM -$pid` cannot target individual jobs.
set -m

# 2) Global array — must be global so the trap handler can see it.
ACTIVE_PIDS=()

cleanup_on_signal() {
  local sig="$1"
  # 3) Disarm traps FIRST so the SIGTERM we are about to broadcast
  #    cannot recurse back into this handler.
  trap - INT TERM HUP

  echo "Caught SIG${sig}. Stopping ${#ACTIVE_PIDS[@]} background job(s)..." >&2

  # 4) Polite shot first — negative PID = entire process group.
  for pid in "${ACTIVE_PIDS[@]}"; do
    kill -TERM -"$pid" 2>/dev/null || true
  done

  # 5) 2-second grace window for well-behaved children to flush.
  sleep 2

  # 6) Guarantee stragglers die.
  for pid in "${ACTIVE_PIDS[@]}"; do
    kill -KILL -"$pid" 2>/dev/null || true
  done

  exit 130   # conventional exit code for "killed by SIGINT"
}

# 7) Trap real signals ONLY. Do NOT trap EXIT — see Failed Attempts.
trap 'cleanup_on_signal INT'  INT
trap 'cleanup_on_signal TERM' TERM
trap 'cleanup_on_signal HUP'  HUP

# 8) Background work + record pgid (== job's PID under `set -m`).
for item in "${WORK_ITEMS[@]}"; do
  process_one "$item" &
  ACTIVE_PIDS+=("$!")
done

# 9) Wait for all jobs; signals interrupt `wait` and run the trap.
wait
```

### Detailed Steps

1. **Enable job control** with `set -m` near the top of the script. This is the single most important step — it is what causes each `&` job to be placed in its own new process group whose pgid equals the job's PID. Verify with `ps -eo pid,pgid,comm` after launching a job: the PID and PGID should match.
2. **Declare the PID array at global scope** (`ACTIVE_PIDS=()`), not inside a function. Bash trap handlers run in the script's top-level scope, so `local` arrays inside `main()` are invisible to them.
3. **Write the handler to take the signal name as an argument** so a single function can serve INT, TERM, and HUP and you can log which signal fired.
4. **Disarm traps as the very first line of the handler** (`trap - INT TERM HUP`). Otherwise, when you broadcast SIGTERM to your own process group's children — who include yourself if you ever forked into the same pgid — the signal can re-enter the handler.
5. **Send SIGTERM to negative PIDs**, e.g. `kill -TERM -"$pid"`. The leading minus sign tells `kill(2)` to target the entire process group with that pgid, not the single PID. Combined with `set -m`, this hits the backgrounded subshell, every command it forked, and every descendant they forked.
6. **Sleep ~2 seconds**, then send SIGKILL the same way. The grace window lets Python/`gh`/`claude` flush logs and remove temp files; the SIGKILL pass guarantees nothing survives.
7. **Trap INT, TERM, and HUP — NOT EXIT.** Trapping EXIT means a routine `exit 1` from arg validation will fire the cleanup, which (a) prints a misleading banner on every exit including `--help`, and (b) corrupts the exit code (`exit 1` becomes `exit 143` because the trap's own `kill` propagates).
8. **Record `$!` immediately** after the `&`. Do not try to recover PIDs later from `jobs -p` — that returns positive PIDs and loses the pgid framing you set up with `set -m`.
9. **Use `wait` (without arguments) at the end.** Bash interrupts `wait` to deliver the trap. If you `sleep infinity` or block in another way, signals may be deferred until the blocking call returns.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | `trap 'kill -TERM -$$' EXIT` — broadcast SIGTERM to the script's own pgid from an EXIT trap | Killed the script's own bash before it could exit cleanly. Every routine `exit 1` (bad args, `--help`) fired the trap, printed the cleanup banner, and turned `exit 1` into `exit 143` (128+15). EXIT trap is too aggressive. | EXIT-trap-based pgid kills are fundamentally wrong for cleanup. Limit signal-driven teardown to **real signals** (INT/TERM/HUP). |
| 2 | `trap "kill $(jobs -p)" INT` — kill direct children only, no pgid | `jobs -p` returns positive PIDs of direct children (the `process_repo` subshells). `kill <pid>` signals only that one process, not the descendants the subshell spawned. Python / `claude` / `gh` grandchildren were orphaned and continued running. | You must signal the **process group** (negative PID), not the leader PID, to take down a tree. `jobs -p` is not enough — you need the pgid framing that `set -m` gives you. |
| 3 | Relied on bash's normal teardown — `huponexit` shopt + bash sending SIGHUP to background jobs on shell exit | Bash's automatic SIGHUP delivery only happens on **interactive** shell exit when `huponexit` is set, and even then it is sent per-job, not per-pgid. Descendants spawned by those jobs are not signalled. Non-interactive scripts get nothing. | Never rely on bash's implicit cleanup of background jobs from a non-interactive script. Be explicit: track PIDs, trap signals, signal pgids. |

## Results & Parameters

### Configuration

The required ingredients, copy-paste ready:

```bash
# Required at script top
set -m                       # job control: each & job gets its own pgid
ACTIVE_PIDS=()               # global, NOT local

# Required trap registrations
trap 'cleanup_on_signal INT'  INT
trap 'cleanup_on_signal TERM' TERM
trap 'cleanup_on_signal HUP'  HUP
# Do NOT add: trap '...' EXIT

# Required kill pattern
kill -TERM -"$pid"           # leading minus = entire process group
sleep 2
kill -KILL -"$pid"
```

Tunable parameters:

| Parameter | Default | Notes |
| --------- | ------- | ----- |
| Grace window between SIGTERM and SIGKILL | 2 seconds | Increase to 5–10s if children need to flush large state (e.g. database commits). Decrease to 0 only if children cannot handle SIGTERM. |
| Exit code on SIGINT | 130 | Standard. SIGTERM-equivalent would be 143 if you want to distinguish the source. |
| Signals trapped | INT, TERM, HUP | Add `QUIT` if you want core-dumping Ctrl-\\ to also trigger cleanup. |

### Expected Output

After `Ctrl-C` (or `kill -INT <script_pid>`):

- Stderr shows: `Caught SIGINT. Stopping <N> background job(s)...`
- Within ~2 seconds, the parent script exits with code `130`.
- `pgrep -P <script_pid>` returns nothing.
- `ps -eo pid,pgid,comm | awk -v g=<pgid> '$2==g'` returns nothing for any of the recorded pgids.
- No orphan Python / `gh` / `claude` / `git` processes remain — verified with a topology-matching grep, e.g. `ps -eo pid,comm,args | awk '$2=="sleep" && $3=="60"'` for the synthetic test rig.

### Verification Evidence

A synthetic test rig at `/tmp/trap_test.sh` mirrored the originating topology:

- 3 backgrounded "repo" subshells
- Each spawned a "phase" sub-subshell
- Each phase spawned 2 `sleep 60` "claude/gh descendants"
- Total: **9 processes in 3 process groups**

`pstree` before SIGINT showed the full 9-process tree. After `kill -INT $TEST_PID`:

- Script exited 130 (correct).
- All 9 descendant processes were gone.
- Cleanup banner reported "Stopping 3 background repo job(s)".

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | `scripts/run_automation_loop.sh` on `feat/automation-loop-6phase-knobs` (commit `5e9a9de`). Originating bug: backgrounded `process_repo` subshells spawned Python/`claude`/`gh` descendants that survived Ctrl-C. | Verified-local via synthetic 9-process rig. Production CI Ctrl-C not yet exercised. |

## References

- `man 2 kill` — semantics of negative PID (signal entire process group)
- `man bash` — `set -m` (Monitor mode / job control), `trap`, `wait`
- Related skills:
  - `graceful-signal-handling.md` — Python-side checkpoint-on-SIGINT pattern (different runtime)
  - `e2e-runner-hang-signal-fixes.md` — Python parallel runner SIGINT/SIGTSTP fixes
  - `batch-subprocess-signal-hang.md` — Python `os.setpgrp()` and worker-thread signal traps
