---
name: atlas-mesh-bringup-first-run
description: "Patterns for the first native (non-compose) bringup of the HomericIntelligence mesh on epimetheus, including correct binary paths, Hermes module name, multi-host myrmidon fan-out results per host, and Agamemnon task completion API findings. Use when: (1) bringing up Agamemnon/Nestor/Hermes natively on a new host, (2) launching hello-myrmidon workers on Tailnet hosts, (3) running the Atlas epic implementation session, (4) troubleshooting Agamemnon review wave task completion."
category: architecture
date: 2026-04-27
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - atlas
  - mesh
  - bringup
  - nats
  - agamemnon
  - nestor
  - hermes
  - myrmidon
  - tailscale
  - multi-host
  - review-wave
  - binary-paths
---

# Atlas Mesh Bringup: First Run Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-27 |
| **Objective** | Bring up HomericIntelligence mesh natively on epimetheus (no compose), launch hello-myrmidon workers on 3 Tailnet hosts, implement Atlas Epic issue #152 scaffold, run 6-dimension review wave |
| **Outcome** | Mesh reached 6 NATS connections at peak; Atlas PR #173 created and set to auto-merge (squash); 6/6 review dimensions approved |
| **Verification** | verified-local — executed end-to-end on epimetheus 2026-04-27 |

## When to Use

- Bringing up Agamemnon, Nestor, or Hermes natively (binary/uvicorn) on any Tailnet host
- Launching hello-myrmidon Python workers on multiple Tailnet hosts (fan-out pattern)
- Running the Atlas epic implementation (issue #152) without the myrmidon-multi pipeline
- Troubleshooting Agamemnon review wave task completion API calls
- Checking which Tailnet hosts are reachable via SSH vs blocked

## Verified Workflow

### Quick Reference — Native Mesh Bringup on epimetheus

```bash
# 1. Start NATS (native binary)
nats-server -js &
# Monitor at http://localhost:8222/varz (NOT port 4222)

# 2. Start Agamemnon (binary is in build/debug/, NOT build/ root)
./control/ProjectAgamemnon/build/debug/agamemnon &

# 3. Start Nestor (binary is in build/debug/, NOT build/ root)
./control/ProjectNestor/build/debug/nestor &

# 4. Start Hermes — module is hermes.server:app (NOT hermes.main:app)
cd infrastructure/ProjectHermes
uvicorn hermes.server:app --host 0.0.0.0 --port 8085 &

# 5. Verify all services respond
curl -s http://localhost:8080/v1/agents  # Agamemnon
curl -s http://localhost:8081/v1/health  # Nestor
curl -s http://localhost:8085/health     # Hermes
curl -s http://localhost:8222/varz | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('connections:', d['connections'])"
```

### Critical Binary Path Facts

```
CORRECT:  control/ProjectAgamemnon/build/debug/agamemnon
WRONG:    control/ProjectAgamemnon/build/agamemnon

CORRECT:  control/ProjectNestor/build/debug/nestor
WRONG:    control/ProjectNestor/build/nestor

CORRECT:  uvicorn hermes.server:app
WRONG:    uvicorn hermes.main:app
```

### After NATS Restart: Restart Agamemnon and Nestor

Agamemnon and Nestor do NOT auto-reconnect to NATS reliably after a restart. Always kill and
restart them pointed at the new NATS:

```bash
# Find and kill Agamemnon / Nestor
pkill -f agamemnon || kill $(pgrep -f agamemnon)
pkill -f nestor    || kill $(pgrep -f nestor)
# pkill may return exit code 144 in some environments — use kill <pid> if needed

# Restart them (binary paths as above)
```

### NATS Monitoring Port

```bash
# NATS monitoring is on port 8222 (not 4222)
# 4222 is the client port for pub/sub
curl http://localhost:8222/varz          # server stats including connection count
curl http://localhost:8222/connz         # active connections
curl http://localhost:8222/jsz           # JetStream stats
```

### Multi-Host Myrmidon Fan-Out

Launch hello-myrmidon Python workers on remote Tailnet hosts. The `main.py` is the Python
worker — `main.cpp` also exists in hello-world/ and should be ignored.

```bash
# On each reachable remote host:
# ALWAYS use main.py (Python), NOT main.cpp (C++ — ignore it)
NATS_URL=nats://<epimetheus-tailscale-ip>:4222 \
  nohup python3 provisioning/Myrmidons/hello-world/main.py \
  > /tmp/hello-myrmidon.log 2>&1 &
```

#### Host Reachability Matrix (2026-04-27)

| Host | Tailscale IP | SSH | nats-py | myrmidon result |
| ------ | ------------- | ----- | --------- | ----------------- |
| epimetheus (local) | 100.92.173.32 | N/A | yes | RUNNING (local) |
| apollo | 100.68.51.128 | yes | yes | RUNNING |
| hermes | 100.73.61.56 | yes | yes | RUNNING |
| hephaestus | — | yes | NO | FAILED — no pip/ensurepip, no sudo |
| titan | — | FAIL | unknown | sshd not enabled |
| athena | — | FAIL | unknown | sshd not enabled |
| cleopatra | — | FAIL | unknown | sshd not enabled |
| artemis | — | FAIL | unknown | sshd not enabled |

**hephaestus workaround needed**: Python 3.12.3 is installed but `pip` and `ensurepip` are
absent and there is no sudo. `nats-py` cannot be installed without pre-provisioning via
Myrmidons YAML manifests or a direct `pip install` from a privileged session.

### Atlas Implementation: Use Direct Worktree (Not myrmidon-multi)

The `claude-myrmidon-multi.py` pipeline is NOT suitable for Atlas scaffold work. It is designed
for formula-driven issue processing, not precision file content generation. For Atlas epic
implementation:

1. Create a worktree directly from `main` (not from a feature branch)
2. Implement the scaffold with one agent in the worktree
3. Ensure `go.mod` uses `go 1.23.0` (not 1.22) — templ v0.3.1001 requires Go 1.23
4. toolchain directive is `go1.24.2`

**Branch base rule**: Always fork from `main`. If the wrong base was used (e.g., forked from
`feat/issue-22-ci-hardening` picking up 12 extra CI commits), cherry-pick the Atlas commit
onto a clean `main` fork:

```bash
# Identify the Atlas commit SHA
git log --oneline feat/issue-152-atlas-bootstrap | head -5

# Create clean branch from main
git checkout -b feat/issue-152-atlas-bootstrap-clean main

# Cherry-pick only the Atlas commit
git cherry-pick <atlas-commit-sha>

# Force-push to replace the branch on the remote
git push --force-with-lease origin feat/issue-152-atlas-bootstrap-clean
```

## Agamemnon Review Wave: Task Completion API

### What Worked

Team creation and task dispatch work correctly:

```bash
# Create review team — response is {"team": {"id": "...", ...}}
# The team ID is nested under "team", not at the top level
TEAM_ID=$(curl -s -X POST "$AGAMEMNON_URL/v1/teams" \
  -H "Content-Type: application/json" \
  -d '{"name":"atlas-review","description":"Atlas plan review wave"}' \
  | jq -r '.team.id')   # <-- .team.id, NOT .id

# Create tasks — one per review dimension
for dim in arch code security ux ops docs; do
  curl -s -X POST "$AGAMEMNON_URL/v1/teams/$TEAM_ID/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"review-$dim\",\"type\":\"atlas-review\",\"params\":{\"dimension\":\"$dim\"}}"
done
```

### Task Completion API — Known Issue (2026-04-27)

The task completion endpoint `POST /v1/teams/{team_id}/tasks/{task_id}/complete` returns 404
in most cases. Only 1 of 6 review agents successfully posted its verdict back via Agamemnon.

**Before next session**: Verify the correct completion endpoint against
`control/ProjectAgamemnon/src/routes.cpp`. The working endpoint may be:
- `PATCH /v1/teams/{team_id}/tasks/{task_id}` with a JSON body
- A different verb or path structure

The 6/6 review approvals were confirmed via direct agent output, not via Agamemnon state.

### NATS Connection Count at 6-Worker Peak

```
Agamemnon     → 1 connection
Nestor        → 1 connection
Hermes        → 1 connection
epimetheus myrmidon → 1 connection
apollo myrmidon     → 1 connection
hermes myrmidon     → 1 connection
─────────────────────────────
Total: 6 connections
```

Verify via: `curl -s http://localhost:8222/varz | jq .connections`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `uvicorn hermes.main:app` | Used `hermes.main:app` as the Hermes FastAPI entry point | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` for Hermes uvicorn launch |
| Binary at `build/agamemnon` | Looked for Agamemnon binary at `control/ProjectAgamemnon/build/agamemnon` | Binary is in `build/debug/` subdirectory: `build/debug/agamemnon` | Check `build/debug/` not `build/` root for C++ debug builds |
| NATS monitoring on port 4222 | Tried `curl localhost:4222/varz` | Port 4222 is the client port; monitoring HTTP is on 8222 | NATS monitoring: port 8222. Client pub/sub: port 4222 |
| `pkill -f "nats-server"` | Used pkill to stop NATS | Returns exit code 144 in some environments (shell interprets as fatal signal) | Use `kill $(pgrep nats-server)` after `ps aux \| grep nats` to get the PID directly |
| nats-py on hephaestus | Attempted `pip install nats-py` on hephaestus (Python 3.12.3) | No pip, no ensurepip, no sudo — cannot install packages without pre-provisioning | Pre-provision hephaestus via Myrmidons manifests; skip for ad-hoc fan-out sessions |
| myrmidon-multi for Atlas scaffold | Tried to use `claude-myrmidon-multi.py` pipeline for precision Atlas file creation | Pipeline is formula-driven; Atlas scaffold requires exact file content and directory layout | Use direct worktree approach with a single agent for precision scaffold work |
| Forking Atlas branch from feature branch | Created `feat/issue-152-atlas-bootstrap` from `feat/issue-22-ci-hardening` | Picked up 12 extra CI commits not part of the Atlas work; PR was not rebased to main | Always check the base branch before creating a worktree; `git worktree add ... main` ensures clean fork |
| `POST /v1/teams/{id}/tasks/{id}/complete` | Agents tried this endpoint to mark tasks complete | Returns 404 in most cases; endpoint likely does not exist at this path | Verify routes.cpp before next review wave session; use `PATCH` verb or different path |

## Results & Parameters

### go.mod Requirements for Atlas (templ v0.3.1001)

```
go 1.23.0          # templ v0.3.1001 requires Go >= 1.23; "go 1.22" is rejected
toolchain go1.24.2 # matches the toolchain installed on the build host
```

### Session Metrics (2026-04-27)

| Metric | Value |
| -------- | ------- |
| NATS connections at peak | 6 |
| Myrmidon workers launched | 3 (epimetheus local, apollo, hermes) |
| Hosts SSH-failed | 4 (titan, athena, cleopatra, artemis — sshd disabled) |
| Hosts pip-failed | 1 (hephaestus — no pip/ensurepip/sudo) |
| Review dimensions run | 6/6 |
| Review dimensions approved | 6/6 |
| Task completion via Agamemnon | 1/6 (5/6 returned 404) |
| Atlas PR | #173 on HomericIntelligence/Odysseus |
| PR status | MERGEABLE, auto-merge (squash) enabled |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | Atlas epic implementation session 2026-04-27 | Native mesh bringup on epimetheus; 3-host myrmidon fan-out; PR #173 |
