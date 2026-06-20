---
name: tooling-wipe-claude-code-session-secrets
description: "After a Claude Code session handled secrets (passwords, candidate lists, decrypted data), shredding your own output files is NOT enough — secrets persist in four hidden harness locations (transcript, background-task outputs, persisted tool-results, sub-agent transcripts). Use when: (1) a session processed passwords/wordlists/decrypted data and you need to scrub it afterward, (2) you shredded your working files but want to verify nothing leaked into the harness, (3) you need exact path templates for Claude Code session-state on a single-user Linux box, (4) you must hand the user transcript-wipe commands you cannot safely run mid-session."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [secrets, claude-code, session, transcript, shred, tool-results, background-tasks, subagents, cleanup, scrub, sensitive-data, harness, jsonl]
---

# Wipe Claude Code Session Secrets

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | After a Claude Code session handled secrets, scrub them from every place the harness persists them — not just the agent's own output files. |
| **Outcome** | Successful: identified four persistence locations beyond working files; agent can safely shred three of them and must hand the transcript wipe to the user. |
| **Verification** | verified-local (single-user Linux box, project path-slug `-home-<user>`) |

## When to Use

- A session processed secrets (passwords, candidate/wordlists, decrypted data) and you need to scrub the box afterward.
- You shredded your working files but want to confirm nothing leaked into the Claude Code harness.
- You need exact path templates for Claude Code session-state files.
- You must wipe the active session transcript but cannot do so yourself mid-session and need to hand the user the commands.

## Verified Workflow

The agent shreds task-outputs, persisted tool-results, and sub-agent files NOW (safe), then HANDS
the user exact `shred -u` commands for the `.jsonl` transcript to run AFTER closing the session.
The agent CANNOT delete the current active session's `.jsonl`: the harness holds it open and is
still appending; deleting mid-session risks corrupting session state / losing context.

### Quick Reference

```bash
# 0. Get SESSION_ID + project-slug from any background-task path the harness reported, e.g.
#    ~/.tmp/claude-<uid>/<project-slug>/<SESSION_ID>/tasks/*.output

PROJ="<project-slug>"        # e.g. -home-<user>
SID="<SESSION_ID>"
UID_DIR="claude-<uid>"

# 1. Selectively shred ONLY secret/crack background-task outputs (preserve unrelated ones)
grep -lE "passphrase |tried [0-9]+|candidates across|no password in the list" \
  ~/.tmp/$UID_DIR/$PROJ/$SID/tasks/*.output 2>/dev/null | xargs -r shred -u

# 2. Shred persisted (spilled-to-disk) tool-results — VERIFY hard-links (link count 2): shred AND rm
for f in ~/.claude/projects/$PROJ/$SID/tool-results/*.txt; do
  [ -e "$f" ] && shred -u "$f"; rm -f "$f"   # rm covers a surviving hard-link
done

# 3. Shred sub-agent transcripts
shred -u ~/.claude/projects/$PROJ/$SID/subagents/* 2>/dev/null
rm -rf ~/.claude/projects/$PROJ/$SID/subagents 2>/dev/null

# 4. Drop any cached gpg passphrase; uninstall task-only pip packages
gpgconf --kill gpg-agent

# 5. HAND TO USER (run AFTER closing the session — agent must NOT run this mid-session):
#    shred -u ~/.claude/projects/<project-slug>/<SESSION_ID>.jsonl
```

### Detailed Steps

1. **Find the SESSION_ID.** It appears in the background-task output paths the harness reports for
   every `run_in_background` Bash command: `.../<SESSION_ID>/tasks/*.output`. Read it from there.
2. **Wipe the four persistence locations** (see Results & Parameters for exact templates):
   background-task outputs, persisted tool-results, sub-agent transcripts, and (handed to user) the
   main transcript.
3. **Grep before shred** to scope to crack/secret artifacts only and avoid clobbering unrelated
   session files.
4. **Handle gotchas**: hard-linked tool-results (shred one link, the other survives — `rm` the path
   too); Docker-root-owned temp dirs (remove via a throwaway container); cached gpg passphrase
   (`gpgconf --kill gpg-agent`); task-only pip installs (uninstall).
5. **Hand the transcript wipe to the user.** Confirm scope first — it is destructive and hard to
   reverse.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Shredded only the working `~/kp-*.txt` files and called it done | Left the transcript, background-task outputs, and persisted tool-results intact — the biggest leak vectors | Shredding working files does NOT touch the harness; the transcript is the largest remaining leak |
| 2 | Agent tried to delete the active session `.jsonl` itself | Harness holds it open and keeps appending; deleting mid-session risks corrupting session state / losing context | The agent must HAND the user `shred -u` commands to run after closing the session |
| 3 | Plain `rm` on a persisted tool-result file | The file was hard-linked (link count 2); the other link survived with the secret intact | Verify link count; `shred` may not blank all links — `rm` the path too |
| 4 | `rm` on a Docker-root-owned temp dir (`docker run -v /tmp/x:/out ...`) | Permission denied — dir owned by root from the container | Remove via another throwaway container: `docker run --rm -v /tmp:/t ubuntu rm -rf /t/x` |

## Results & Parameters

**Four persistence locations beyond your own output files** (path-slug `-home-<user>`):

```
a. Main session TRANSCRIPT (full conversation incl. echoed secrets):
   ~/.claude/projects/<project-slug>/<SESSION_ID>.jsonl

b. Background-task OUTPUT files (full stdout of run_in_background commands — e.g. live
   `gpg --passphrase <CANDIDATE>` process lines from `ps`, or wordlist dumps; often dozens):
   ~/.tmp/claude-<uid>/<project-slug>/<SESSION_ID>/tasks/*.output

c. PERSISTED tool-results (large outputs spilled to disk verbatim — e.g. a 60KB crack-progress
   dump full of candidate passwords):
   ~/.claude/projects/<project-slug>/<SESSION_ID>/tool-results/*.txt

d. SUB-AGENT transcripts:
   ~/.claude/projects/<project-slug>/<SESSION_ID>/subagents/
```

**SESSION_ID tip:** read it from the background-task output paths the harness reports for every
background Bash command (`.../<SESSION_ID>/tasks/*.output`).

**Gotchas:**

- **Hard-linked tool-results** (link count 2) — `shred` may not blank all links; verify and `rm` the
  path too.
- **Docker-root-owned temp dirs** — `docker run --rm -v /tmp:/t ubuntu rm -rf /t/x`.
- **Cached gpg passphrase** — `gpgconf --kill gpg-agent`; also uninstall task-only pip packages.
- **False sense of done** — shredding working files does NOT touch the transcript.

**Honesty / safety:**

- Prefer `shred -u` over `rm` for password lists.
- Confirm scope with the user before deleting the transcript (destructive, hard to reverse).
- If a file unexpectedly disappears, say so plainly rather than guessing which command did it.
