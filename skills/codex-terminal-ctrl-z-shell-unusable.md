---
name: codex-terminal-ctrl-z-shell-unusable
description: "Capture and triage Codex terminal job-control failures after Ctrl-Z suspend/resume over iTerm2 plus tsh into remote Linux/Slurm. Use when: (1) Codex or the shell stops accepting command input after fg, (2) debugging terminal mode or job-control state after SIGTSTP/SIGCONT, (3) recording evidence for upstream Codex issue #29730 without inventing a workaround."
category: tooling
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - codex
  - terminal
  - ctrl-z
  - sigtstp
  - sigcont
  - iterm2
  - tsh
  - slurm
  - job-control
  - shell-state
  - upstream-issue
---

# Codex Ctrl-Z Suspend/Resume Can Leave Remote Shell Unusable

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Preserve a tooling/debugging note about a Codex terminal job-control bug observed by the user. |
| **Scenario** | User presses Ctrl-Z while Codex is running work, then resumes with `fg`. Environment: iTerm2 on macOS, `tsh` into a remote Linux Slurm cluster. After Codex resumes, shell input/submission becomes unusable. |
| **Outcome** | Upstream issue filed: [openai/codex#29730](https://github.com/openai/codex/issues/29730), titled "Ctrl-Z suspend during active work can leave shell unusable after resume over tsh/Slurm". No verified workaround was tested. |
| **Verification** | unverified |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until the upstream issue is resolved or a reproducible local mitigation is tested.

## When to Use

- Codex was suspended with Ctrl-Z during active work and resumed with `fg`, then the shell no longer accepts or submits commands normally.
- The environment includes a local terminal emulator plus remote transport, especially iTerm2 on macOS through `tsh` to a Linux Slurm cluster.
- You need to preserve a precise upstream-bug trail before trying recovery steps that may destroy evidence.
- You are tempted to document `reset`, `stty sane`, reconnecting, or another terminal recovery command as a fix without first reproducing and validating it.
- You are searching for terminal mode, SIGTSTP/SIGCONT, job-control, or remote shell state failures in Codex.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI or a reproducible environment-specific test confirms it.

### Quick Reference

```bash
# Avoid this while openai/codex#29730 is unresolved:
#   Ctrl-Z an active Codex session over iTerm2 + tsh + remote Linux/Slurm, then resume with fg.

# Duplicate-search command used before filing the upstream issue:
gh issue list -R openai/codex \
  --search "Ctrl+Z suspend tsh slurm iTerm2 shell" \
  --limit 10

# Minimum evidence to capture before trying recovery commands:
printf '%s\n' \
  "Terminal: iTerm2 on macOS" \
  "Remote transport: tsh" \
  "Remote host class: Linux Slurm cluster" \
  "Steps: Codex active -> Ctrl-Z -> fg -> shell input/submission unusable" \
  "Upstream issue: https://github.com/openai/codex/issues/29730"
```

### Detailed Steps

1. **Avoid Ctrl-Z as the pause mechanism for active Codex sessions in this environment.** Until the upstream issue has a confirmed fix, prefer leaving Codex running, stopping it cleanly, or opening a separate terminal/session for unrelated shell work.
2. **If it happens, capture evidence before mitigations.** Record the terminal emulator, local OS, remote transport, remote OS/cluster type, shell, any terminal multiplexer, whether Codex had active tool work in flight, the exact Ctrl-Z and `fg` sequence, and the observed failure mode.
3. **Search upstream with the exact environment terms.** The observed session used:
   `gh issue list -R openai/codex --search "Ctrl+Z suspend tsh slurm iTerm2 shell" --limit 10`
   and found no targeted duplicate results.
4. **Link the upstream issue in downstream notes.** Use [openai/codex#29730](https://github.com/openai/codex/issues/29730) as the canonical report for this observation.
5. **Do not invent a verified fix.** A plausible hypothesis is that terminal mode or job-control state is not restored correctly after SIGTSTP/SIGCONT, especially through iTerm2 plus `tsh` on remote Linux machines. That hypothesis is not a mitigation. Only promote a recovery command to a verified workflow after reproducing the failure and confirming the command restores normal command submission.

## Verified Workflow

No verified workflow exists yet. This heading is present because `scripts/validate_plugins.py` currently requires the literal `## Verified Workflow` section for every skill. The actionable guidance for this unverified observation is the `## Proposed Workflow` section above.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Suspend/resume active Codex over remote Slurm shell | User pressed Ctrl-Z while Codex was running work, then resumed with `fg` from iTerm2 over `tsh` into a Linux Slurm cluster | After resume, shell input/submission became unusable | Avoid Ctrl-Z on active Codex sessions in this environment until the upstream issue is resolved or a mitigation is verified |
| Search for a targeted upstream duplicate | Ran `gh issue list -R openai/codex --search "Ctrl+Z suspend tsh slurm iTerm2 shell" --limit 10` | No targeted duplicate results were returned | File or link a precise upstream issue with the terminal, transport, cluster, and job-control sequence |
| Treat terminal recovery as solved | No reproducible `reset`, `stty sane`, reconnect, or other recovery command was validated end-to-end | A recovery command may appear plausible but would be undocumented speculation without a repro and confirmation | Keep verification at `unverified` and document only conservative avoidance plus evidence capture |

## Results & Parameters

### Captured upstream report

| Field | Value |
|-------|-------|
| Repository | `openai/codex` |
| Issue | [#29730](https://github.com/openai/codex/issues/29730) |
| Title | `Ctrl-Z suspend during active work can leave shell unusable after resume over tsh/Slurm` |
| Expected behavior | After resume, Codex and/or the shell restores terminal state cleanly and accepts commands normally. |
| Actual behavior | Shell input/submission becomes unusable after resume. |
| Hypothesis | Terminal mode or job-control state is not restored correctly after SIGTSTP/SIGCONT, especially through iTerm2 plus `tsh` on remote Linux machines. |
| Verification level | `unverified`; user-reported environment-specific observation plus upstream filing; no end-to-end validated workaround. |

### Evidence checklist for future reproductions

```text
Terminal emulator:
Local OS:
Remote transport:
Remote OS / cluster:
Shell:
Terminal multiplexer, if any:
Was Codex actively running tool work?
Exact suspend/resume steps:
Observed failure after fg:
Recovery commands attempted:
Did recovery restore command submission?
Link to upstream issue/comment:
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Codex terminal session | 2026-06-23 user-reported observation in iTerm2 over `tsh` to a Linux Slurm cluster | Unverified; upstream issue filed at [openai/codex#29730](https://github.com/openai/codex/issues/29730) |
