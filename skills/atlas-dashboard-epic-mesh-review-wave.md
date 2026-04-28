---
name: atlas-dashboard-epic-mesh-review-wave
description: "Design and file a GitHub Epic + child issues for a new service, then run a multi-dimension Myrmidon review wave (arch/code/security/ux/ops/docs) against the plan. Use when: (1) starting a new HomericIntelligence service from scratch and need a fully filed epic with milestones and labels, (2) running a parallel 6-agent review wave against an architecture plan before implementation begins, (3) tracking and resolving critical findings from a multi-dimension agent review."
category: architecture
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - atlas
  - dashboard
  - github-epic
  - mesh-review
  - nats
  - htmx
  - go
  - templ
  - sse
  - tailscale
  - grafana
  - mnemosyne
---

# Atlas Dashboard: GitHub Epic Filing + 6-Agent Mesh Review Wave

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Design the Atlas unified operator dashboard (Go + Chi + templ + htmx + NATS, port 3002), file Epic #151 + 20 child issues across 6 milestones on HomericIntelligence/Odysseus, run 6-dimension Myrmidon review wave, resolve all 8 critical findings |
| **Outcome** | Successful — Epic + 20 issues filed; 6/6 review dimensions ran; 8 critical findings resolved; corrections posted to relevant issues |
| **Verification** | verified-local (review wave ran, issues filed; implementation not started yet) |

## When to Use

- Starting a new service in the HomericIntelligence ecosystem and need a complete epic + child issues in GitHub
- Running a 6-dimension parallel review (arch/code/security/ux/ops/docs) against a plan before implementation
- Filing GitHub milestones and labels at scale (20+ issues, 6 milestones, 24 labels) via CLI
- Verifying NATS subject schema, compose topology, and justfile integration before implementation
- Auditing a plan for port constants, compose DNS service names, crypto API safety, iframe sandbox escape risks, env var prefix consistency, and SSE concurrency patterns

## Verified Workflow

### Quick Reference

```bash
# 1. File Epic + milestones + labels via gh CLI
gh issue create --repo HomericIntelligence/Odysseus \
  --title "Epic: Atlas — unified operator dashboard" \
  --label "epic,dashboard,atlas" --body "$(cat epic-body.md)"

# 2. Create milestones
for title in "M1: Scaffold" "M2: NATS" "M3: REST pollers" "M4: Tailscale" "M5: Mnemosyne" "M6: Auth+Security"; do
  gh api repos/HomericIntelligence/Odysseus/milestones \
    -f title="$title" -f state=open
done

# 3. File 20 child issues linked to milestones
gh issue create --repo HomericIntelligence/Odysseus \
  --milestone "M1: Scaffold" --title "..." --body "Closes #151 (Atlas Epic)"

# 4. Dispatch 6-agent review wave via Agamemnon
TEAM_ID=$(curl -s -X POST "$AGAMEMNON_URL/v1/teams" \
  -H "Content-Type: application/json" \
  -d '{"name":"atlas-review","description":"Atlas plan review wave"}' | jq -r .id)

for dim in arch code security ux ops docs; do
  curl -s -X POST "$AGAMEMNON_URL/v1/teams/$TEAM_ID/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"review-$dim\",\"type\":\"atlas-review\",\"params\":{\"dimension\":\"$dim\"}}"
done

# 5. Aggregate verdicts (exits 0 only when 6/6 approved)
just atlas-review-aggregate M1 "$TEAM_ID"
```

### Detailed Steps

1. **Design architecture first** — Before filing any issues, fully specify: package layout, HTTP routes, NATS subscriber plane (JetStream consumers), REST pollers, UI component list, Tailscale source, Grafana iframe embedding, Mnemosyne browser. Verify against live configs before filing (see Failed Attempts for why this matters).

2. **Verify all constants against live configs** — Before writing a single issue body, check:
   - Hermes port: grep `config.py` in ProjectHermes (default is 8085, not 8082)
   - NATS URL: use compose service DNS (`nats://nats:4222`), not WSL2 gateway IPs
   - Stream names: verify in `control/ProjectAgamemnon/src/nats_client.cpp:76-80`
   - Grafana dashboard UIDs: `agent-health`, `argus-health`, `loki-explorer`, `nats-events`, `task-throughput`
   - Compose network name (`argus`) and `depends_on` targets: grep `docker-compose.yml` in ProjectArgus
   - Mnemosyne volume path: grep ProjectMnemosyne repo
   - `argus-start` justfile line: `grep -n "argus-start" justfile` (currently line 204)

3. **File Epic issue** — Use `gh issue create` with all top-level labels. Add a task list in the body referencing the 20 child issue numbers (fill these in after child issues are created, or use a second edit pass).

4. **Create milestones** — Use `gh api repos/.../milestones` (not `gh milestone create` — that flag doesn't exist). Create all 6 before filing any child issues so you can assign milestone IDs.

5. **Create labels** — Use `gh label create` for any non-default labels. For 24 labels, batch in a loop. If a label already exists, the command errors; add `2>/dev/null || true` guard.

6. **File 20 child issues** — Each issue body must include: acceptance criteria table, env vars section, docker-compose snippet (if relevant), justfile task name. File sequentially (not parallel) so issue numbers are predictable for cross-linking.

7. **Dispatch review wave** — L0 commander creates a team via Agamemnon `POST /v1/teams`, then posts one task per review dimension. Verdicts are delivered on `hi.tasks.{team_id}.{task_id}.completed`. See Results section for review dimension assignments.

8. **Aggregate verdicts** — Use `just atlas-review-aggregate MILESTONE TEAM` which subscribes to the NATS subject and exits 0 only when all 6 dimensions report `approved`. If any dimension reports `rejected`, surface the finding immediately.

9. **Resolve critical findings** — Post findings as edit comments on the relevant child issues. Update spec text in-place. See Failed Attempts for the 8 critical findings from this session.

10. **Branch protection** — Add `atlas / review-wave (M*)` as a required status check. Gate merge on 6/6 approval.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hermes port from memory | Used port 8082 as the Hermes default | Actual default is 8085 per `config.py`; context section was wrong | Always grep `config.py` in ProjectHermes before setting any port constant |
| NATS_URL default as WSL2 gateway | Set `NATS_URL=nats://172.20.0.1:4222` in `.env.example` | WSL2 gateway IPs are host-specific and break in CI / other machines; compose service DNS is stable | Always use compose service DNS names (`nats://nats:4222`) as defaults in `.env.example` |
| `goldmark.WithUnsafe(false)` | Called goldmark with `WithUnsafe(false)` to disable raw HTML | `goldmark.WithUnsafe()` (no args) ENABLES raw HTML; there is no `WithUnsafe(false)` overload; the safe default is to simply omit the option | Never call `goldmark.WithUnsafe()` — omitting it is already safe; calling it enables raw HTML |
| iframe sandbox with allow-scripts + allow-same-origin | Used `sandbox="allow-scripts allow-same-origin"` on Grafana iframes | Combining these flags allows the iframe script to reach `window.parent`, removing the sandbox entirely | Use `allow-scripts allow-popups` only (or serve cross-origin); never combine `allow-scripts` with `allow-same-origin` |
| AUTH_* env var prefix | Issue #154 used `AUTH_MODE` while docker-compose used `ATLAS_AUTH_MODE` | Inconsistent prefix caused confusion about which var controlled auth; would cause silent failures at runtime | Standardise on `ATLAS_` prefix for all Atlas-specific env vars from day one |
| Unconditional Tailscale socket mount | Mounted `/var/run/tailscale/tailscaled.sock` unconditionally in compose | CI environments don't have the Tailscale daemon running; compose fails to start | Comment out the socket volume in compose by default; set `TAILSCALE_SOURCE=static` as the default; make socket mount opt-in via env var |
| RingBuffer without thread-safety spec | Designed `RingBuffer[T]` generics without specifying concurrency model | JetStream writers and SSE readers run concurrently; without `sync.RWMutex` the ring buffer has a data race | Always specify `sync.RWMutex` (write lock on Push, read lock on Snapshot) in the issue spec for any shared buffer used by concurrent goroutines |
| Incomplete .env.example | Issue #154 listed only 4 env vars in .env.example | The full Atlas service needs 14+ vars; users cloning the repo would miss required config | Always enumerate every env var in `.env.example`, including optional ones with safe defaults |
| Trusting plan-level port constants without verification | Used port numbers from the planning document without cross-checking | Planning docs are often written before configs are finalised; they lag behind actual defaults | Treat all port/URL constants in a plan as unverified until confirmed against live config files |
| SSE subscriber channels unbuffered | Left SSE fan-out channels as unbuffered | A slow SSE client blocks the JetStream writer goroutine, causing message lag for all clients | SSE subscriber channels MUST be buffered (1000 events minimum) for non-blocking fan-out |

## Results & Parameters

### Atlas Stack Specification

| Parameter | Value |
|-----------|-------|
| Language | Go 1.22+ |
| Router | Chi |
| Templates | templ |
| Frontend | htmx |
| Messaging | nats.go (JetStream) |
| Port | 3002 |
| Location | `infrastructure/ProjectArgus/dashboard/` |
| Compose network | `argus` |
| Auth default | `ATLAS_AUTH_MODE=none` (local dev) |
| Tailscale source default | `TAILSCALE_SOURCE=static` |

### NATS Configuration (Verified)

| Parameter | Value |
|-----------|-------|
| NATS_URL default | `nats://nats:4222` (compose service DNS) |
| Consumer type | Durable JetStream, one per stream |
| Ack policy | `AckExplicit` |
| MaxAckPending | 1024 |
| AckWait | 30s |
| Streams | `homeric-agents`, `homeric-tasks`, `homeric-heartbeat`, `homeric-health`, `homeric-metrics`, `homeric-events` |
| Subject schema (agents) | `hi.agents.{host}.{name}.{verb}` (ADR-005) |
| Subject schema (tasks) | `hi.tasks.{team_id}.{task_id}.{verb}` (ADR-005) |

### Grafana Dashboard UIDs (Verified)

| UID | Dashboard |
|-----|-----------|
| `agent-health` | Agent health overview |
| `argus-health` | Argus stack health |
| `loki-explorer` | Log explorer |
| `nats-events` | NATS event stream |
| `task-throughput` | Task throughput |

### 6-Milestone Structure

| Milestone | Scope | Key Issues |
|-----------|-------|------------|
| M1: Scaffold | Repo structure, Chi server, templ layout, CI | #152–#156 |
| M2: NATS | JetStream consumers, ring buffers, SSE | #157–#160 |
| M3: REST Pollers | Agent/task/metric REST pollers, retry | #161–#163 |
| M4: Tailscale | Tailscale peer source, network map UI | #164–#166 |
| M5: Mnemosyne | Skill browser, search, detail view | #167–#169 |
| M6: Auth+Security | Auth middleware, iframe CSP, .env hardening | #170–#171 |

### 6-Agent Review Wave — Dimension Assignments

| Dimension | Agent focus | Key findings from this session |
|-----------|-------------|-------------------------------|
| `arch` | Package layout, NATS topology, stream verification | Verified 6 streams in nats_client.cpp:76-80; compose network verified |
| `code` | Go patterns, generics, SSE fan-out, ring buffer safety | RingBuffer needs `sync.RWMutex`; SSE channels must be buffered(1000) |
| `security` | iframe sandbox, CSP headers, auth env vars, goldmark | iframe sandbox escape; goldmark WithUnsafe() inversion; AUTH_ prefix conflict |
| `ux` | htmx patterns, templ component structure, Grafana embed | Grafana iframe cross-origin serving recommendation |
| `ops` | Compose topology, Tailscale mount, CI pipeline, env vars | Tailscale socket must be conditional; NATS_URL must use service DNS |
| `docs` | .env.example completeness, justfile tasks, ADR references | .env.example missing 10+ entries; Hermes port wrong |

### Review Wave justfile Tasks

```makefile
# Dispatch review wave for a milestone
atlas-review-dispatch MILESTONE PR:
  #!/usr/bin/env bash
  TEAM_ID=$(curl -sf "$AGAMEMNON_URL/v1/teams" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"atlas-review-{{MILESTONE}}\",\"pr\":\"{{PR}}\"}" | jq -r .id)
  for dim in arch code security ux ops docs; do
    curl -sf "$AGAMEMNON_URL/v1/teams/$TEAM_ID/tasks" -X POST \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"review-$dim\",\"type\":\"atlas-review\",\"params\":{\"dimension\":\"$dim\",\"milestone\":\"{{MILESTONE}}\"}}"
  done
  echo "Review team: $TEAM_ID"

# Aggregate verdicts (exits 0 only when 6/6 approved)
atlas-review-aggregate MILESTONE TEAM:
  #!/usr/bin/env bash
  nats sub "hi.tasks.{{TEAM}}.*.completed" --count 6 | \
    jq -e '[.[] | select(.verdict=="approved")] | length == 6'
```

### Branch Protection Required Check

Add to repo ruleset: `atlas / review-wave (M*)` as a required status check. This status is posted by the `atlas-review-aggregate` justfile task.

### Key ADR References

| ADR | Relevance |
|-----|-----------|
| ADR-005 | NATS subject schema — `hi.agents.*` and `hi.tasks.*` patterns |
| ADR-002 | NATS event bridge — JetStream consumer configuration |
| ADR-003 | Nomad over k8s — compose topology for local development |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | Atlas dashboard Epic #151, issues #152–#171, 6 milestones, 24 labels | Review wave ran; 8 critical findings resolved; implementation not started |
