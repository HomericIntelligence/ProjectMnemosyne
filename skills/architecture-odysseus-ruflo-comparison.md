---
name: architecture-odysseus-ruflo-comparison
description: "Deep architectural comparison of multi-repo agent ecosystem (Odysseus) vs in-process agent orchestration framework (Ruflo). Use when: (1) comparing infrastructure-centric vs application-centric agent architectures, (2) evaluating integration opportunities between container-based and in-process orchestration, (3) performing ecosystem audit of HomericIntelligence repos against external agent frameworks."
category: architecture
date: 2026-03-27
version: 1.0.0
user-invocable: false
tags: [odysseus, ruflo, agent-orchestration, multi-repo, comparison, ecosystem-audit]
---

# Architecture: Odysseus vs Ruflo Comparison

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Deep architectural comparison of HomericIntelligence/Odysseus (12-submodule meta-repo) with ruflo (TypeScript/Rust monorepo v3.5), identifying complementarity and integration opportunities |
| **Outcome** | Analysis complete — 6 integration proposals identified. No code executed; research only. |
| **Verification** | Unverified — analysis only, no code was executed or tested |
| **Output** | /home/mvillmow/agents/odysseus-ruflo-analysis.md (12-section comprehensive report) |

## When to Use

- Analyzing how HomericIntelligence/Odysseus compares to a third-party agent orchestration framework
- Evaluating whether to integrate an external AI agent library into the Odysseus ecosystem
- Identifying gaps in Odysseus capabilities (especially memory/vector search) that external tools could fill
- Designing integration patterns between container-based infrastructure (Nomad/Podman) and in-process orchestration
- Auditing the complementarity between infrastructure-centric and application-centric agent architectures

## Verified Workflow

> **Note**: This is a proposed workflow — analysis only, no code was executed or tested during this session.

### Quick Reference

```
Parallel exploration strategy:
1. Sub-agent A: Clone + explore Odysseus (git submodules, ADRs, justfile, architecture.md)
2. Sub-agent B: Clone + explore Ruflo (src/, CLAUDE.md, ADRs, core TypeScript files)
3. Plan agent: Design 12-section analysis structure
4. Sequential: Write analysis merging both sub-agent findings
```

### Phase 1: Repository Exploration (Parallel Sub-Agents)

**Odysseus exploration checklist:**
- Read all ADRs (`docs/adr/`)
- Read `architecture.md` and any runbooks
- Read `justfile` for operational patterns
- List all 12 submodule names and their roles
- Note: Odysseus is a meta-repo — actual implementations live in submodules (ai-maestro, ProjectTelemachy, ProjectKeystone, ProjectHermes, AchaeanFleet, etc.)

**Ruflo exploration checklist:**
- Read `CLAUDE.md` for project summary
- Read core orchestration files: `SwarmCoordinator.ts`, `WorkflowEngine.ts`, `Task.ts`, `Agent.ts`, `HybridBackend.ts`
- Read all ADRs (Ruflo had 10+ at time of analysis)
- Note TypeScript/Rust hybrid architecture (Node.js + WASM modules)

### Phase 2: Dimensional Analysis Framework

Compare across these 6 dimensions:

| Dimension | Odysseus Pattern | Ruflo Pattern |
|-----------|-----------------|---------------|
| **Paradigm** | Infrastructure-centric (process boundaries, 12 repos) | Application-centric (DDD monorepo, in-process) |
| **Orchestration** | 3-layer REST/NATS (ai-maestro → Telemachy → Keystone DAGs) | In-process SwarmCoordinator + Q-Learning 3-tier router |
| **Agent model** | Container-per-agent (Podman + Nomad, strong isolation) | Logical TypeScript objects (60+ types, shared heap) |
| **Memory** | Key-value only (ai-maestro), no vector search | HNSW vector search, ReasoningBank, SONA, Knowledge Graph |
| **Distribution** | Real multi-host (Tailscale + Nomad across WSL2 hosts) | Application-simulated (FederationHub in Node.js process) |
| **Recovery** | GitOps (Myrmidons `just apply-all` from YAML git) | SQLite WAL only — in-flight state lost on crash |

### Phase 3: Gap and Strength Identification

Key asymmetry found in this analysis:

- **Odysseus BIGGEST GAP**: Memory — ai-maestro key-value only, no vector search, no learning
- **Ruflo BIGGEST STRENGTH**: Memory — HNSW vector search (150x–12,500x faster than linear scan), ReasoningBank, SONA (self-optimizing neural architecture), Knowledge Graph, 3-scope isolation

- **Ruflo BIGGEST GAP**: Distribution resilience — FederationHub is simulated within a single Node.js process; crash loses in-flight state
- **Odysseus BIGGEST STRENGTH**: Infrastructure resilience — real multi-host via Tailscale + Nomad, GitOps recovery

### Phase 4: Integration Proposal Generation

Use the complementarity framework to generate integration proposals (value-ordered):

1. **Ruflo as AchaeanFleet vessel** — Containerize Ruflo in Nomad; Odysseus provides infra, Ruflo provides intelligence
2. **NATS as Ruflo's external event bus** — Solve Ruflo's crash-recovery gap via durable JetStream streams
3. **Ruflo QueenCoordinator as Odysseus routing advisor** — ProjectKeystone feeds tasks to Ruflo's complexity scorer
4. **MCP bridge for ai-maestro REST endpoints** — Expose ai-maestro tools to Ruflo agents via MCP protocol
5. **AgentDB as ai-maestro memory backend sidecar** — Add vector search to Odysseus without replacing ai-maestro
6. **ProjectHephaestus maestro-client for shared memory bridge** — Shared memory layer between both systems

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — research session | Direct parallel exploration approach worked | N/A | For architectural comparisons, parallel sub-agents (one per codebase) are more efficient than sequential exploration |

## Results & Parameters

### Architectural Paradigm Classification

```yaml
infrastructure_centric:
  example: Odysseus (HomericIntelligence)
  characteristics:
    - Process-boundary separation between components
    - Each service is a separate repo/container
    - Orchestration via message broker (NATS) + REST
    - Deployment via container scheduler (Nomad)
    - Recovery via GitOps (declarative YAML + git)
  tradeoffs:
    strengths: [real-isolation, multi-host, crash-resilience, ops-maturity]
    weaknesses: [memory-gap, no-learning, cross-service-latency]

application_centric:
  example: Ruflo (ruvnet)
  characteristics:
    - All coordination in-process (single Node.js runtime)
    - DDD monorepo with rich domain types (60+ TypeScript types)
    - Orchestration via in-process coordinator + ML router
    - Distribution simulated within process (FederationHub)
    - Memory: HNSW vector search + knowledge graph
  tradeoffs:
    strengths: [rich-memory, ml-routing, vector-search, type-richness]
    weaknesses: [fake-distribution, crash-loses-state, single-process-limit]
```

### Q-Learning Router Tiers (Ruflo-specific)

```yaml
tier_1_wasm:
  latency: "<1ms"
  use_case: "Simple deterministic tasks"
  model: "Compiled WASM module"

tier_2_haiku:
  latency: "~500ms"
  use_case: "Moderate reasoning tasks"
  model: "Claude Haiku"

tier_3_opus:
  latency: "2-5s"
  use_case: "Complex multi-step reasoning"
  model: "Claude Opus"
```

### Memory Architecture Gap (Odysseus vs Ruflo)

```yaml
odysseus_memory:
  type: key-value
  backend: ai-maestro built-in store
  vector_search: false
  learning: false
  cross_session: limited

ruflo_memory:
  type: multi-tier
  backends:
    - HNSW_vector_index   # 150x–12,500x faster than linear scan
    - ReasoningBank       # episodic memory for reasoning chains
    - SONA                # self-optimizing neural architecture
    - KnowledgeGraph      # entity-relationship store
  vector_search: true
  learning: true          # SONA adapts over time
  cross_session: full
  scope_isolation: [agent, team, global]
```

### Integration Pattern: Ruflo in Nomad

```hcl
# AchaeanFleet vessel for Ruflo
job "ruflo-swarm" {
  type = "service"

  group "coordinator" {
    task "ruflo" {
      driver = "podman"
      config {
        image = "ruflo:v3.5"
        ports = ["http", "metrics"]
      }
      # NATS sidecar for durable event recovery
      resources {
        cpu    = 2000
        memory = 4096
      }
    }
  }
}
```

### Key File Paths Explored

```yaml
odysseus:
  meta_repo: ~/HomericIntelligence/Odysseus/
  adrs: docs/adr/ADR-001 through ADR-005
  architecture: docs/architecture.md
  justfile: justfile

ruflo:
  repo: ~/ruvnet/ruflo/  (github.com/ruvnet/ruflo)
  core_files:
    - src/SwarmCoordinator.ts
    - src/WorkflowEngine.ts
    - src/Task.ts
    - src/Agent.ts
    - src/HybridBackend.ts
  claude_md: CLAUDE.md
  adrs: docs/adr/ (10+ ADRs)
```

### Complementarity Matrix

| Odysseus Gap | Ruflo Capability | Integration Path |
|-------------|------------------|------------------|
| No vector memory | HNSW search | AgentDB sidecar or Ruflo vessel |
| No ML routing | Q-Learning 3-tier | QueenCoordinator → Keystone |
| No learning | SONA adaptation | Shared memory bridge via Hephaestus |
| No MCP tooling | Can consume MCP | MCP bridge for ai-maestro REST |

| Ruflo Gap | Odysseus Capability | Integration Path |
|-----------|---------------------|------------------|
| Fake distribution | Real Tailscale+Nomad | Containerize Ruflo in AchaeanFleet |
| Crash loses state | NATS JetStream | NATS as Ruflo external event bus |
| No container isolation | Podman per agent | Nomad task driver wraps Ruflo workers |

## References

- [Odysseus meta-repo](https://github.com/HomericIntelligence/Odysseus)
- [Ruflo framework](https://github.com/ruvnet/ruflo)
- [Full analysis report](/home/mvillmow/agents/odysseus-ruflo-analysis.md)
- [ecosystem-audit-remediation skill](ecosystem-audit-remediation.md)
