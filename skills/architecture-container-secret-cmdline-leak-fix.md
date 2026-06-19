---
name: architecture-container-secret-cmdline-leak-fix
description: "Use when: (1) a secret like ANTHROPIC_API_KEY is passed to a container via `-e VAR=value` on a podman/docker run command line, (2) planning to fix a credential leak observable through `ps auxww` or `/proc/<pid>/cmdline`, (3) deciding whether to relocate a secret to a file vs. delete it because the CLI authenticates via mounted OAuth credentials instead."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [security, secrets, container, podman, docker, cmdline-leak, anthropic-api-key, oauth, credentials, proc, planning]
---

# Container Secret on Command Line Leak — Delete-Before-Relocate Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Plan the fix for a secret (ANTHROPIC_API_KEY) leaking to all host users via the container command line (`ps auxww` / `/proc/<pid>/cmdline`) for GitHub issue #180 in the Odysseus repo |
| **Outcome** | Plan produced: the KISS fix is to DELETE the `-e ANTHROPIC_API_KEY=...` line (the standalone `claude`/`claude-host` CLI authenticates via mounted OAuth credential files), not relocate it. Plan was NOT executed; CI never ran it. |
| **Verification** | unverified — implementation plan only; container was never run with the env var removed |

## When to Use

- A secret is injected into a container with `-e SECRET=value` on the `podman run` / `docker run` command line
- A security review flags that the secret is readable via `ps auxww`, `ps -ef`, or `/proc/<pid>/cmdline` by any host user for the process lifetime
- You are about to "fix" the leak by moving the secret to a different `-e` var or another command-line mechanism (this is the same class of bug)
- You are deciding between relocating a secret to a file vs. deleting it entirely
- The containerized CLI may authenticate via mounted OAuth credentials (`~/.claude/.credentials.json`, `~/.claude.json`) and may ignore the env var altogether
- Planning a regression test for a secret-on-cmdline leak and judging whether that test actually proves the fix is safe

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. It is an implementation plan for issue #180 that was never executed, and CI never ran it. Treat every step as a hypothesis until a live container run confirms auth still works. Verification level: `unverified`.

### Quick Reference

```bash
# 1. PROVE the leak class: a secret on the run command line is world-readable on the host.
ps auxww | grep -i ANTHROPIC_API_KEY          # any host user sees it
cat /proc/<container-runtime-pid>/cmdline | tr '\0' ' '   # also exposes it

# 2. BEFORE relocating the secret to a file, ask: is it needed AT ALL?
#    Many CLIs (standalone `claude` / `claude-host`) auth via OAuth from mounted creds
#    and IGNORE ANTHROPIC_API_KEY. If so, the KISS fix is to DELETE the line.

# 3. Find every injection site (do NOT assume there are only two).
grep -rn ANTHROPIC_API_KEY e2e/*.py            # found exactly 2 here — but see scope caveat below
grep -rn ANTHROPIC_API_KEY .                   # also check Dockerfiles, entrypoints, Nomad HCL, compose

# 4. Verify the credential files exist and are already bind-mounted into the container.
ls -l ~/.claude/.credentials.json ~/.claude.json   # 0600 expected

# 5. Confirm the in-container UID can READ the 0600 creds.
#    --userns=keep-id maps host UID into the container; chmod o+r (S_IROTH) makes
#    0600 -> 0604 so the mapped UID can read them. Verify BOTH are in place.

# 6. DELETE the `-e ANTHROPIC_API_KEY=...` line (KISS) rather than relocating it.
#    Then RUN the container and confirm auth still works — the unit test does NOT prove this.
```

### Steps (Proposed)

1. Reproduce / confirm the leak: the secret appears in `ps auxww` and `/proc/<pid>/cmdline` because it is an `-e VAR=value` argument on the `podman run` line. The exposure lasts the entire process lifetime and is visible to every host user.
2. Challenge the relocation reflex: relocating the value to a secret file is the standard remediation, but FIRST determine whether the value is even consumed. The standalone `claude` / `claude-host` binary is believed to authenticate purely via OAuth from mounted credential files (`~/.claude/.credentials.json`, `~/.claude.json`) and to ignore `ANTHROPIC_API_KEY`. If true, the simplest correct fix is to delete the line.
3. Enumerate all injection sites with `grep -rn ANTHROPIC_API_KEY` — including Dockerfiles, container entrypoints, Nomad HCL, and compose env, not just the Python e2e harness.
4. Verify the credential files exist on the host and are already bind-mounted read-only into the container.
5. Verify readability inside the container: `--userns=keep-id` maps the host UID, and `chmod o+r` (S_IROTH) on the 0600 credentials makes them readable by the in-container UID.
6. Delete the `-e ANTHROPIC_API_KEY=...` line.
7. Add a regression test asserting the secret string is absent from the assembled command list — BUT treat this as necessary-not-sufficient (see Failed Attempts). Require a live container auth dry-run before merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Relocate the secret to a different `-e` var / pass it via the command line differently | Move ANTHROPIC_API_KEY to another env flag still set on the `podman run` line, or otherwise keep it as a process argument | Still leaks — any `-e VAR=value` argument is visible via `ps auxww` and `/proc/<pid>/cmdline` to all host users; it is the same class of bug | Command-line args are world-readable on the host. The fix must remove the value from the command line entirely (file, stdin, or delete), not move it to another flag |
| Treat a unit test asserting absence from the command list as sufficient proof | Add a pytest asserting `ANTHROPIC_API_KEY` is not in the assembled command args | Proves the string is gone from the cmdline but proves NOTHING about whether auth still works; a green suite gives false confidence | A regression test for a leak must be paired with a live auth check; absence-of-string ≠ functionality-preserved |
| Pass per-process secrets the host can observe (team KB) | Inject secrets as process arguments / env on the run line for any host-visible process | Other host users can read `/proc/<pid>/environ` and `/proc/<pid>/cmdline`; secrets belong in files with restrictive perms or runtime secret stores | Never put secrets where a host process listing can reveal them |
| Rely on ANTHROPIC_API_KEY pre-flight checks for the containerized CLI (team KB) | Gate the container start on the env var being set, assuming the CLI needs it | The standalone `claude`/`claude-host` CLI authenticates via OAuth credential files and ignores the env var; the pre-flight check guards a value the binary never reads | Verify what the binary actually consumes before adding guards or relocating values around it |

## Results & Parameters

### UNCERTAIN ASSUMPTIONS / UNVERIFIED RELIANCES (read this first, reviewer)

This is the most important section. The plan rests on the following claims that were NOT validated by running the container:

- **Unverified runtime claim — the binary ignores the env var.** The plan asserts `claude-host` authenticates purely via OAuth and "does not use" `ANTHROPIC_API_KEY`. This came from a team skill (`test-matrix-and-e2e-infrastructure`) and from local file existence (`~/.claude/.credentials.json`), NOT from running the container with the env var removed. If the binary falls back to the env var in some code path, deleting the line breaks auth. The regression would only surface at container runtime, which the proposed pytest does NOT exercise.
- **Test coverage gap.** The proposed test proves the secret is not on the command line; it proves nothing about whether auth still works. A green suite would give false confidence. The reviewer should require a live dry-run / actual container auth check before merge.
- **Two-file scope assumption.** The plan relied on `grep -n ANTHROPIC_API_KEY e2e/*.py` finding exactly two injection sites. If the secret also flows through the achaean-claude image entrypoint, a Dockerfile, Nomad HCL, or compose env, those were NOT inspected — the achaean-claude image/entrypoint was not in the checkout (the glob returned no files). The reviewer should confirm the image itself does not expect the env var.
- **Stale, untouched code (deferred).** `claude-myrmidon.py:217` hardcodes standalone version `2.1.120`, which does not exist locally (only 2.1.176–178 are present); a glob fallback masks the mismatch. Out of scope for #180 but flagged for a follow-up.
- **Local-environment generalization.** Credential file existence and permissions were verified on ONE dev machine. Other hosts running these workers may not have OAuth credentials populated; on those hosts, deleting the env var with no fallback could break auth.

### Parameters / Facts Established

```
Leak vector:        `-e ANTHROPIC_API_KEY=<value>` on the `podman run` command line
Observable via:     ps auxww | ps -ef | /proc/<pid>/cmdline | /proc/<pid>/environ
Audience:           every host user, for the full process lifetime
Issue:              GitHub #180 (Odysseus repo) — plan only, NOT executed

Credential files (host, dev machine):
  ~/.claude/.credentials.json    perms 0600 (must be o+r / 0604 for in-container UID)
  ~/.claude.json                 perms 0600

Container access mechanics:
  --userns=keep-id   maps host UID into container so mounted creds are owned by it
  chmod o+r          adds S_IROTH so a 0600 file becomes readable by the mapped UID

Injection sites found:   2 (in e2e/*.py)  — UNVERIFIED as complete; image not in checkout
KISS fix chosen:         DELETE the `-e ANTHROPIC_API_KEY=...` line (do not relocate)
Required before merge:    live container auth dry-run (NOT covered by proposed pytest)
```

### Test Plan Checklist (for the reviewer)

```
[ ] Regression test: ANTHROPIC_API_KEY absent from assembled command args
[ ] LIVE container auth dry-run WITHOUT the env var (the load-bearing check)
[ ] grep -rn ANTHROPIC_API_KEY across Dockerfiles / entrypoints / Nomad HCL / compose
[ ] Confirm achaean-claude image entrypoint does not require the env var
[ ] Confirm OAuth creds exist + are readable in-container on ALL target hosts
[ ] Follow-up: claude-myrmidon.py:217 hardcoded version 2.1.120 mismatch
```
