---
name: architecture-odysseus-ai-maestro-integration-gap
description: "Deep analysis of ai-maestro's internal architecture vs actual ecosystem usage, identifying the 90% integration gap. Use when: (1) analyzing ai-maestro REST/WebSocket API surface, (2) planning new satellite repo integrations, (3) auditing endpoint usage, (4) investigating the webhook/NATS pipeline gap, (5) evaluating unused capabilities (memory, AMP, AID, lifecycle)."
category: architecture
date: 2026-03-27
version: 1.0.0
user-invocable: false
tags: [ai-maestro, odysseus, integration-gap, api-audit, webhook, nats, memory, amp, aid]
---

# Architecture: Odysseus ai-maestro Integration Gap Analysis

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Map the full integration surface between ai-maestro (23blocks-OS/ai-maestro v0.26.5) and the HomericIntelligence/Odysseus ecosystem, quantifying what is used vs unused |
| **Outcome** | Ecosystem uses approximately 10% of ai-maestro's API surface (4 of ~100 REST endpoints). Critical mismatches identified in task webhooks, PUT semantics, soft-delete behavior, and consumer naming. Entire subsystems (memory, AMP, AID, agent lifecycle) are unused. |
| **Verification** | Unverified -- research/analysis session only, no code was executed or tested |
| **Output** | /home/mvillmow/agents/odysseus-ai-maestro-analysis.md (comprehensive report) |

## When to Use

- Analyzing ai-maestro's REST API surface to understand what endpoints exist and which are actually consumed
- Planning a new satellite repo integration with ai-maestro (need to know which endpoints to target)
- Auditing endpoint usage across the Odysseus ecosystem
- Investigating the webhook/NATS pipeline -- specifically how task events reach NATS when ai-maestro has no task webhooks
- Evaluating unused ai-maestro capabilities (memory system, AMP protocol, AID identity, agent lifecycle) for potential adoption
- Debugging PUT-related data loss (field nullification on partial updates)
- Understanding soft-delete behavior when querying agents
- Planning authentication/authorization strategy using AID v0.2.0

## Verified Workflow

> **Note**: This is an unverified analysis -- research only, no code was executed or tested during this session. Findings should be verified against the live ai-maestro instance before acting on them.

### Quick Reference

```
Integration surface summary:
- ai-maestro exposes ~100 REST routes + WebSocket endpoints
- Ecosystem uses 4 endpoints (GET teams, GET tasks, GET agents/unified, PUT task)
- 13 critical findings documented below
- Key gap: no task.* webhook events exist -- only agent.* events
```

### Phase 1: ai-maestro API Surface Inventory

ai-maestro v0.26.5 exposes approximately 100 REST API routes organized across these domains:

```yaml
endpoint_domains:
  agents:
    count: ~25 routes
    includes: CRUD, hibernate/wake, transfer, import/export, skills, metrics,
              docs, code-graph, repos, tracking, metadata, subconscious,
              brain-inbox, playback
    used_by_ecosystem: 1 (GET /api/agents/unified)

  teams:
    count: ~15 routes
    includes: CRUD, members, tasks, task assignment
    used_by_ecosystem: 1 (GET /api/teams)

  tasks:
    count: ~10 routes
    includes: CRUD (team-scoped), assignment, status updates
    used_by_ecosystem: 2 (GET /api/teams/{id}/tasks, PUT /api/teams/{id}/tasks/{taskId})
    critical_note: "Tasks are team-scoped -- no standalone /tasks endpoint exists"

  memory:
    count: ~15 routes
    includes: per-agent CozoDB, vector embeddings (HuggingFace+ONNX),
              hybrid search (semantic+BM25+RRF fusion), long-term consolidation,
              confidence scoring, tier levels
    used_by_ecosystem: 0

  amp:
    count: ~10 routes
    includes: AMP v0.1.3 message routing, cryptographic signatures,
              read receipts, content security scanning (34 prompt injection patterns)
    used_by_ecosystem: 0

  aid:
    count: ~5 routes
    includes: AID v0.2.0, Ed25519 identity documents, OAuth 2.0 token exchange,
              scoped JWT tokens
    used_by_ecosystem: 0

  cerebellum:
    count: ~5 routes
    includes: motor learning, procedural memory
    used_by_ecosystem: 0

  webhooks:
    count: ~5 routes
    includes: webhook registration and delivery
    fires_events: "agent.created, agent.updated, agent.deleted, agent.email.changed ONLY"
    critical_note: "NO task.* webhook events exist"
    used_by_ecosystem: 0

  plugins:
    count: ~5 routes
    includes: plugin builder, marketplace
    used_by_ecosystem: 0

  misc:
    count: ~5 routes
    includes: health, search, organization
    used_by_ecosystem: 0
```

### Phase 2: Endpoint Usage by ProjectKeystone

ProjectKeystone's `maestro_client.py` is the primary (and nearly sole) consumer of ai-maestro's REST API:

```yaml
endpoints_used:
  - method: GET
    path: /api/teams
    purpose: Fetch team list for task scoping
    consumer: ProjectKeystone maestro_client.py

  - method: GET
    path: /api/teams/{id}/tasks
    purpose: Fetch tasks for DAG construction
    consumer: ProjectKeystone maestro_client.py

  - method: GET
    path: /api/agents/unified
    purpose: Fetch agent roster for task assignment
    consumer: ProjectKeystone maestro_client.py

  - method: PUT
    path: /api/teams/{id}/tasks/{taskId}
    purpose: Update task status after DAG execution
    consumer: ProjectKeystone maestro_client.py
    bug: "PUT overwrites ALL fields -- partial payloads silently null omitted fields (issue #251)"
```

### Phase 3: Critical Mismatches

#### 1. Task Webhook Gap (Critical -- Open Question)

```yaml
problem: |
  ai-maestro webhook service fires ONLY agent.* events:
    - agent.created
    - agent.updated
    - agent.deleted
    - agent.email.changed
  There are NO task.* webhook events (task.created, task.updated, etc.)

question: |
  How does ProjectHermes generate hi.tasks.* NATS events?
  Possibilities:
    a) Hermes polls ai-maestro REST API for task changes (wasteful)
    b) Hermes watches ai-maestro WebSocket for task updates (undocumented)
    c) Task events are generated by a different component entirely
    d) The hi.tasks.* NATS pipeline is not yet functional

impact: |
  This is the most critical architectural question. The entire DAG execution
  pipeline (Keystone subscribes to hi.tasks.* via NATS) depends on these
  events existing. If they do not flow, the pipeline is broken.
```

#### 2. PUT Overwrites All Fields (Issue #251)

```yaml
problem: |
  PUT /api/teams/{id}/tasks/{taskId} with partial data silently nulls out
  all omitted fields. There is no PATCH endpoint.

impact: |
  ProjectKeystone must send complete task objects on every update.
  If it sends only {status: "completed"}, all other fields (title, description,
  assignee, dependencies, etc.) are set to null.

workaround: |
  Always GET the full task object first, merge changes, then PUT the complete object.
  Or wait for a PATCH endpoint (no GitHub issue requesting this was found).
```

#### 3. Soft-Delete by Default

```yaml
problem: |
  DELETE /api/agents/{id} performs soft-delete by default.
  Soft-deleted agents can reappear in GET responses.
  Permanent deletion requires ?hard=true query parameter.

impact: |
  ProjectKeystone DAG walker may encounter "deleted" agents in GET /api/agents/unified
  responses. These agents have a non-null deletedAt field but are still returned.

fix: |
  Filter GET /api/agents/unified responses by deletedAt === null.
  Or use ?hard=true when deletion is intentional and permanent.
```

#### 4. Durable Consumer Name Mismatch

```yaml
problem: |
  ADR-005 documents the NATS durable consumer name as "keystone-dag".
  ProjectKeystone code actually uses "keystone-daemon" as the consumer name.

impact: |
  Documentation and implementation disagree. Anyone setting up NATS consumers
  from the ADR will use the wrong name. JetStream will create two separate
  consumer groups, splitting message delivery.

fix: |
  Align ADR-005 with code (use "keystone-daemon") or vice versa.
```

#### 5. Team-Scoped Task Endpoints

```yaml
problem: |
  Odysseus documentation references /tasks as a standalone endpoint.
  The actual ai-maestro endpoint is /api/teams/{id}/tasks -- tasks are
  always scoped to a team. No standalone /tasks route exists.

impact: |
  ProjectMyrmidons and ProjectTelemachy need team IDs before they can
  interact with tasks. Any integration code that assumes /tasks exists
  will get 404 errors.

fix: |
  Update all documentation to use /api/teams/{id}/tasks.
  Consider whether ai-maestro should add a cross-team /api/tasks endpoint.
```

#### 6. hostUrl Unreliable on WSL2 (Issue #276)

```yaml
problem: |
  agent.hostUrl field can contain unreachable internal IPs, especially
  on WSL2 where the internal network IP is not routable from other hosts.

impact: |
  Any code that uses agent.hostUrl for cross-host communication will fail
  silently on WSL2 environments.

fix: |
  Use Tailscale IPs from host-sync instead of agent.hostUrl.
  See tailscale-maestro-setup skill for cross-host connectivity patterns.
```

### Phase 4: Unused Capabilities Assessment

#### Memory System (Entirely Unused)

```yaml
capability: |
  ai-maestro provides per-agent CozoDB databases with:
    - Vector embeddings via HuggingFace + ONNX runtime
    - Hybrid search: semantic + BM25 + Reciprocal Rank Fusion
    - Long-term memory consolidation (facts, preferences, patterns, decisions, insights)
    - Confidence scoring per memory entry
    - Tiered memory levels (working, short-term, long-term)

ecosystem_usage: None

potential_value: |
  Could replace ProjectHephaestus's skill/knowledge system with persistent
  per-agent memory. Agents could remember past task outcomes, learn from
  failures, and share knowledge through the memory API.
```

#### AMP Protocol (Unused Despite ADR-002)

```yaml
capability: |
  Agent Messaging Protocol v0.1.3:
    - Cryptographic message signatures (Ed25519)
    - Read receipts
    - Content security scanning (34 prompt injection patterns)
    - Rate limiting (60 req/agent/60s on /v1/route)

ecosystem_usage: None

contradiction: |
  ADR-002 states "AMP stays as the point-to-point channel for agent-to-agent
  communication." But no satellite repo uses AMP. All messaging goes through
  NATS, bypassing AMP's security features entirely.

potential_value: |
  AMP's prompt injection scanning alone justifies adoption for any agent
  that processes untrusted input. The 34-pattern scanner is built-in.
```

#### AID v0.2.0 (Not Documented in Any ADR)

```yaml
capability: |
  Agent Identity protocol introduced in v0.26.0:
    - Ed25519 identity documents per agent
    - Proof of possession challenges
    - OAuth 2.0 token exchange
    - Scoped JWT tokens with configurable permissions

ecosystem_usage: None
documentation: "Not mentioned in any Odysseus ADR"

potential_value: |
  Solves the "no REST API authentication" problem. AID could provide
  per-agent scoped tokens for ai-maestro API access, replacing the
  current unauthenticated Phase 1 design.
```

#### Agent Lifecycle Features (All Unused)

```yaml
unused_features:
  - hibernate/wake: Suspend and resume agents (saves resources)
  - transfer: Move agents between teams/orgs
  - import/export: Serialize agent state for backup/migration
  - skills: Register agent capabilities
  - metrics: Per-agent performance tracking
  - docs: Agent documentation storage
  - code-graph: Code structure analysis per agent
  - repos: Git repository association
  - tracking: Activity and usage tracking
  - metadata: Custom key-value metadata
  - subconscious: Background processing pipeline
  - brain-inbox: Queued messages for offline agents
  - playback: Replay agent actions
```

### Phase 5: Authentication Gap

```yaml
current_state: |
  Phase 1 design -- no authentication middleware on any REST route.
  MAESTRO_API_KEY config key exists but defaults to empty string.
  Only AMP /v1/route has rate limiting (60 req/agent/60s).

risk: |
  Any network-accessible ai-maestro instance accepts unauthenticated
  requests. In the Tailscale-only deployment model this is mitigated
  by network-level access control, but any port exposure is a full
  API compromise.

future_path: |
  AID v0.2.0 provides the authentication primitives (Ed25519 + JWT).
  Integration path:
    1. Generate AID identity documents for each satellite repo
    2. Configure ai-maestro to require AID JWT on REST routes
    3. Update ProjectKeystone maestro_client.py to include JWT in headers
    4. Use AID scopes to enforce least-privilege per satellite

security_note: |
  CozoDB query injection was found and fixed (issue #286, March 2026).
  Unescaped template literals in CozoDB queries allowed injection.
  This is fixed but highlights the importance of input validation.
```

### Phase 6: Recommended Immediate Fixes

```yaml
priority_1_documentation:
  - Update Odysseus docs to use /api/teams/{id}/tasks (not /tasks)
  - Document AID v0.2.0 in a new ADR
  - Align ADR-005 consumer name with ProjectKeystone code
  - Document the task webhook gap explicitly

priority_2_code:
  - ProjectKeystone: Always send complete task objects on PUT (workaround for #251)
  - ProjectKeystone: Filter GET /api/agents/unified by deletedAt === null
  - ProjectKeystone: Use Tailscale IPs, not agent.hostUrl

priority_3_investigation:
  - Determine how hi.tasks.* NATS events are generated (the task webhook gap)
  - Evaluate AID adoption for REST API authentication
  - Assess memory system for ProjectHephaestus knowledge storage
  - Investigate AMP adoption for agent-to-agent message security
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed /tasks endpoint exists | Checked for standalone /tasks route based on Odysseus docs | ai-maestro only has team-scoped /api/teams/{id}/tasks -- no standalone route | Always verify endpoint paths against the actual ai-maestro source (server.mjs route registrations), not downstream documentation |
| Looked for task webhook events | Searched ai-maestro webhook service for task.* event types | Only agent.* events are implemented (created, updated, deleted, email.changed) | The webhook event vocabulary is smaller than expected -- do not assume CRUD events exist for all resource types |
| Searched for PATCH endpoint | Looked for PATCH /api/teams/{id}/tasks/{taskId} as alternative to PUT | No PATCH endpoint exists for tasks | ai-maestro uses PUT-as-replace semantics -- always send complete objects |
| Checked for REST auth middleware | Searched for authentication middleware in ai-maestro route setup | MAESTRO_API_KEY defaults to empty string; no middleware enforces auth | Phase 1 security model relies entirely on network-level access control (Tailscale) |

## Results & Parameters

### Integration Surface Metrics

```yaml
ai_maestro_version: v0.26.5
total_rest_routes: ~100
routes_used_by_ecosystem: 4
usage_percentage: ~4%
websocket_endpoints: multiple (undocumented usage)
webhook_event_types: 4 (all agent.*, no task.*)

unused_subsystems:
  - memory (CozoDB + vector embeddings)
  - AMP v0.1.3 (agent messaging protocol)
  - AID v0.2.0 (agent identity)
  - cerebellum (motor learning)
  - plugins (builder + marketplace)
  - agent lifecycle (hibernate, wake, transfer, import/export)
  - agent skills, metrics, docs, code-graph, repos, tracking
  - agent metadata, subconscious, brain-inbox, playback

critical_mismatches:
  - task_webhook_gap: "No task.* webhook events -- pipeline unclear"
  - put_semantics: "PUT nulls omitted fields (issue #251)"
  - soft_delete: "DELETE is soft by default, agents reappear in queries"
  - consumer_name: "ADR-005 says keystone-dag, code says keystone-daemon"
  - team_scoped_tasks: "No standalone /tasks -- must use /api/teams/{id}/tasks"
  - hosturl_wsl2: "agent.hostUrl unreachable on WSL2 (issue #276)"

authentication:
  current: "None (Phase 1 -- MAESTRO_API_KEY defaults to empty)"
  future: "AID v0.2.0 (Ed25519 + OAuth 2.0 + scoped JWT)"
```

### GitHub Issues Referenced

```yaml
open_issues:
  - "#251": "PUT overwrites all fields with partial payload"
  - "#276": "agent.hostUrl unreliable on WSL2"

closed_issues:
  - "#286": "CozoDB query injection via unescaped template literals (fixed March 2026)"

ai_maestro_release_velocity: "18 releases in 7 weeks (high churn)"
```

### Key File Paths

```yaml
analysis_output: /home/mvillmow/agents/odysseus-ai-maestro-analysis.md
ai_maestro_source: /home/mvillmow/ai-maestro/
keystone_client: ProjectKeystone/src/keystone/maestro_client.py
odysseus_adrs: Odysseus/docs/adr/ADR-001 through ADR-005
odysseus_architecture: Odysseus/docs/architecture.md
odysseus_nats_subjects: Odysseus/docs/nats-subjects.md
```

### Related Skills

- [architecture-odysseus-ruflo-comparison](architecture-odysseus-ruflo-comparison.md) -- Compares Odysseus with Ruflo framework (different topic: external framework comparison vs internal integration gap)
- [ecosystem-audit-remediation](ecosystem-audit-remediation.md) -- Cross-repo contract bug audit (complementary: found some of the same mismatches, this skill goes deeper on ai-maestro internals)
- [tailscale-maestro-setup](tailscale-maestro-setup.md) -- Cross-host connectivity setup (referenced for hostUrl workaround)

## References

- [ai-maestro repository](https://github.com/23blocks-OS/ai-maestro)
- [Odysseus meta-repo](https://github.com/HomericIntelligence/Odysseus)
- [Full analysis report](/home/mvillmow/agents/odysseus-ai-maestro-analysis.md)
