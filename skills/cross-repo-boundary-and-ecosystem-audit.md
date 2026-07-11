---
name: cross-repo-boundary-and-ecosystem-audit
description: "Enforce repo charters, audit ecosystem health, and remediate scope creep
  across multi-repo HomericIntelligence projects. Use when: (1) validating multi-repo
  integration boundaries and hunting cross-repo contract bugs, (2) a repo has suffered
  scope creep and needs charter enforcement via stacked deletion PRs, (3) mapping actual
  vs documented component state before deployment or onboarding, (4) auditing ai-maestro
  REST/WebSocket API surface vs ecosystem usage, (5) performing multi-domain code-quality
  remediation (logging, exceptions, DRY, CI) across a shared library."
category: architecture
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: cross-repo-boundary-and-ecosystem-audit.history
tags:
  - cross-repo
  - ecosystem-audit
  - charter
  - scope-creep
  - stacked-prs
  - integration-gap
  - ground-truth
  - multi-repo
  - component-inventory
  - ai-maestro
  - nats
  - remediation
---

# Cross-Repo Boundary and Ecosystem Audit

## Overview

| Field | Value |
|-------|-------|
| **Theme** | Enforce repo charters, audit ecosystem health, and remediate scope creep across multi-repo HomericIntelligence projects |
| **Scope** | 12 repositories, integration contracts (NATS/REST), charter enforcement, component readiness, API surface analysis |
| **Key Artifacts** | Multi-repo alignment matrix, component readiness matrix, stacked deletion PRs, integration gap report |
| **Failure Mode** | Scope creep, documentation drift, silent runtime bugs, cross-repo contract mismatches |

## When to Use

- Multiple repos share contracts (NATS subjects, REST API fields, status enums) and you need to verify they agree.
- Documentation (architecture.md, ADRs, CLAUDE.md) may have drifted from implementation.
- A repo started as "data + schema" but accumulated reconcilers and runtime logic that belong in consumers.
- You want to delete a large amount of out-of-charter code and need small, reviewable diffs.
- Planning a new satellite repo integration and need to know what ai-maestro endpoints actually exist.
- Audit report surfaces critical/major/minor issues across exception handling, logging, DRY, and CI simultaneously.
- Onboarding to the ecosystem and need ground truth rather than aspirational architecture docs.
- Checking whether submodule pins in Odysseus match standalone checkouts.

## Verified Workflow

### Quick Reference

```bash
# 1. Ecosystem contract cross-check
grep -r "hi\.tasks\|hi\.agents\|TASK_SUBJECT" ~/Project*/src/       # NATS subjects
grep -r "completed\|pending\|backlog\|in_progress" ~/Project*/src/*/models.py  # Status enums
grep -r "httpx.AsyncClient\|async with.*client" ~/Project*/src/*/maestro_client.py

# 2. Component health check
curl -s http://localhost:8080/v1/agents   # Agamemnon (port 8080)
curl -s http://localhost:8081/v1/health   # Nestor (port 8081)
curl -s http://localhost:8085/health      # Hermes (port 8085)
nats stream ls                            # JetStream streams
curl -s http://localhost:8222/varz | jq '{connections, num_subscriptions}'  # NATS monitoring (8222, NOT 4222)

# 3. Submodule freshness
git -C ~/Odysseus/provisioning/Myrmidons log -1 --oneline
git -C ~/Myrmidons log -1 --oneline

# 4. Charter enforcement — bucket every artifact
gh issue list --state open --json number,title,labels --limit 500 > /tmp/issues.json

# 5. Code quality audit
grep -rn 'logger\.\(info\|warning\|error\|debug\)(f"' <src>/     # f-string anti-patterns
grep -rn 'except Exception' <src>/                                  # broad excepts
grep -rn '^    print(' <src>/ | grep -v cli/utils | grep -v 'def main'  # print() in lib code
```

### Phase 1: Cross-Repo Contract Audit

Build an alignment matrix comparing documented behavior vs actual behavior:

| Repo | Documented Role | Actual Role | Aligned? |
|------|-----------------|-------------|----------|
| Each repo | What docs say | What code does | Yes/No |

Key areas to cross-check:

- **NATS subjects**: Compare publisher subjects (Hermes) vs subscriber filters (Keystone) vs documentation (Odysseus ADRs). Count actual dots — `"hi.tasks.team.task.updated".split(".")` = 5 parts, not 6.
- **API field names**: Compare REST client mappings vs Pydantic model attributes vs CLAUDE.md references. Code is always authoritative over docs.
- **Status enums**: Compare status values across all repos handling task lifecycle (`pending`/`completed` in code vs `todo`/`done` in stale CLAUDE.md).
- **Dependency claims**: Verify "imported by X" claims against actual `pixi.toml`/`pyproject.toml`.

### Phase 2: Component Ground Truth Inventory

Read actual source code — not architecture docs — to determine each component's real state:

| Component | Type | Port | NATS | Status |
|-----------|------|------|------|--------|
| Agamemnon | C++20 REST API | 8080 | 6 JetStream streams | Production ready |
| Nestor | C++20 REST API | 8081 | nats.c | Production ready |
| Hermes | Python FastAPI | 8085 | HMAC webhooks | Production ready |
| Keystone | C++20 library | — | MessageBus (library) | Needs work — daemon not built |
| Odysseus | Meta-repo justfile | — | none | Ready for what it is |
| Myrmidons | Dataset + YAML | — | none | Watch submodule pin staleness |
| ProjectOdyssey | Mojo ML framework | — | none | Not relevant to mesh |

Critical binary paths:

```yaml
agamemnon:  control/ProjectAgamemnon/build/debug/agamemnon  # NOT build/agamemnon
nestor:     control/ProjectNestor/build/debug/nestor         # NOT build/nestor
hermes:     uvicorn hermes.server:app                        # NOT hermes.main:app
nats_monitoring: port 8222                                   # NOT 4222 (client port)
```

### Phase 3: ai-maestro Integration Gap Analysis

ai-maestro v0.26.5 exposes ~100 REST routes. The ecosystem uses approximately 4 (4%):

```yaml
endpoints_used:
  - GET  /api/teams
  - GET  /api/teams/{id}/tasks       # tasks are ALWAYS team-scoped; no standalone /tasks
  - GET  /api/agents/unified         # filter by deletedAt === null (soft-delete is default)
  - PUT  /api/teams/{id}/tasks/{id}  # sends ALL fields — partial PUT silently nulls omitted fields

unused_subsystems:
  - memory (CozoDB + HNSW vector search)
  - AMP v0.1.3 (agent messaging + prompt injection scanning)
  - AID v0.2.0 (Ed25519 + OAuth 2.0 + scoped JWT)
  - cerebellum, plugins, lifecycle (hibernate/wake/transfer/import/export)

critical_mismatches:
  task_webhook_gap: "Webhooks fire only agent.* events — no task.* events; pipeline source unclear"
  put_semantics:    "PUT nulls all omitted fields (issue #251) — always GET-merge-PUT"
  soft_delete:      "DELETE is soft by default — filter GET /api/agents/unified by deletedAt === null"
  consumer_name:    "ADR-005 says keystone-dag; code says keystone-daemon"
  team_scoped_tasks: "No standalone /tasks — always /api/teams/{id}/tasks"
  hosturl_wsl2:     "agent.hostUrl unreachable on WSL2 (issue #276) — use Tailscale IPs"
  authentication:   "Phase 1 — MAESTRO_API_KEY defaults to empty; AID v0.2.0 is the future path"
```

### Phase 4: Charter Enforcement via Stacked Deletion PRs

When a repo has suffered scope creep:

1. **Lock the charter in writing first.** Commit to `CLAUDE.md`/`CHARTER.md`: "This repo is ONLY X, Y, Z." Every deletion PR references this charter as justification.
2. **Bucket every artifact** (files, issues, ADRs, CI workflows): in-charter or out-of-charter.
3. **PORT vs DELETE** for each out-of-charter artifact:
   - Has a consumer that needs it? → PORT to the consumer's repo (independent PR).
   - Dead code / no consumer? → DELETE.
4. **Open independent cross-repo PRs — do not coordinate merge ordering.** The cleanup PR can land first; the receiving repo reconstructs from commit history + PR links. Cross-repo merge dependencies create deadlock.
5. **Stack deletion PRs (C1 → C2 → C3 → C4)**, each rebased on the prior. One focused theme per PR (a few thousand lines). Net reduction is the same but each PR is reviewable.
6. **Mass-close out-of-charter issues by verdict bucket**, not individually. Template: "Out-of-charter per `<charter-link>`. Migrated to `<repo>#<PR>`."
7. **The reconciler-vs-dataset boundary:** Any "make actual match desired" logic lives in the consumer, never in the dataset repo.

### Phase 5: Multi-Domain Code Quality Remediation

For audit reports surfacing findings across logging, exceptions, DRY, and CI simultaneously:

**Safe execution order**: critical runtime bugs → exception narrowing → f-string logging → print() in lib code → DRY extraction → CI threshold alignment → documentation.

**F-string logging** (convert to lazy format):

```python
# BEFORE
logger.info(f"Found {count} files in {path}")
# AFTER — only interpolates if log level is active
logger.info("Found %d files in %s", count, path)
```

**Broad except clauses** — strategy by module:

| Module | Recommended exceptions |
|--------|----------------------|
| File I/O | `OSError` |
| YAML parsing | Keep `Exception` + comment (undocumented subtypes) |
| Subprocess | `subprocess.CalledProcessError`, `OSError` |
| GitHub API (PyGithub) | Keep `Exception` + comment |
| Retry utilities | Keep `Exception` + comment (intentional) |

Check `# noqa` validity before adding: `grep "select" pyproject.toml | grep BLE` — if BLE not selected, `# noqa: BLE001` causes `RUF100` (unused directive). Use a plain comment instead.

**DRY extraction** — when the same pattern appears in 3+ places, create a shared utility. Type signatures must accept `set[str] | frozenset[str] | None` when callers may pass frozensets.

### Phase 6: Verification and PR Creation

```bash
# After each wave of fixes
just test              # or pixi run pytest tests/unit -v
pre-commit run --all-files

# PR creation
gh repo view --json defaultBranchRef  # always check base branch name
gh pr create --base <base> --title "<name>" --body "..."

# NATS end-to-end
nats pub hi.tasks.team.task.updated '{"id":"test"}' && nats sub "hi.tasks.>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting CLAUDE.md over code for status values | Used `todo`/`done` from CLAUDE.md as authoritative | Code actually uses `pending`/`completed` — CLAUDE.md was stale | Always treat Pydantic models and enums as source of truth; docs lag |
| Assuming NATS subject part count from comments | Comment said "6 parts"; check was `< 6` | `"hi.tasks.team.task.updated".split(".")` = 5 parts — comment was wrong | Count actual dots in the subject string; never trust comments over split() |
| Creating PRs without checking default branch | Used `gh pr create` without `--base` flag | Some repos use `main`, others `master` — creation failed | Always run `gh repo view --json defaultBranchRef` before creating PRs |
| Skipping HMAC in webhook tests | Tests sent raw JSON without HMAC signature | `.env` had `WEBHOOK_SECRET` set — server returned 401 | When migrating to pydantic-settings (auto-loads `.env`), check for secrets that gate auth |
| Coordinated cross-repo merge ordering | Gated "consumer imports code" BEFORE "dataset deletes it" | Creates cross-repo deadlock; user vetoed | Open independent PRs; link in bodies; each merges on its own schedule |
| Single monolithic deletion PR | One 25k-line diff for the full cleanup | Unreviewed in practice — cognitive load too high | Stack 4 deletion PRs (C1→C4), one theme per PR |
| Assumed /tasks standalone endpoint | Checked for `/tasks` based on Odysseus docs | ai-maestro only has `/api/teams/{id}/tasks` — always team-scoped | Verify endpoint paths against actual ai-maestro route registrations, not downstream docs |
| Looked for task webhook events | Searched for `task.*` event types in ai-maestro webhook service | Only `agent.*` events implemented | Do not assume CRUD webhook events exist for all resource types |
| `uvicorn hermes.main:app` | Used `hermes.main:app` as Hermes entry point | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` |
| Binary at `build/agamemnon` | Looked for Agamemnon at `build/agamemnon` | Debug build lands in `build/debug/agamemnon` | C++ debug builds go to `build/debug/`, not `build/` root |
| NATS monitoring on port 4222 | `curl localhost:4222/varz` | Port 4222 is client port; monitoring is on 8222 | NATS monitoring: 8222. Client: 4222 |
| Added `# noqa: BLE001` to broad except clauses | Used noqa directive to suppress ruff warnings | `BLE` not in ruff `select` list — `RUF100` (unused directive) fired | Check `pyproject.toml` select list before adding noqa comments |
| Used `set[str] \| None` for shared utility type | `def find_markdown_files(..., exclude_dirs: set[str] \| None = None)` | mypy error: callers pass `frozenset[str]` from dataclass defaults | Use `set[str] \| frozenset[str] \| None` for exclude_dirs parameters |
| Removed `sys` import after replacing stderr prints | Deleted `import sys` when `print(..., file=sys.stderr)` replaced | `sys.exit(0)` in `main()` still required `sys` | Grep all `sys.` usages before removing the import |
| Estimated issue counts upfront | Estimated "~118 issues" from partial scan | Actual count was 127 — edge cases not captured | Re-run `gh issue list` after each closure wave; trust live count, not plan estimate |
| Assumed Myrmidons submodule was current | Read submodule version of api.sh | Submodule was stale; standalone checkout already migrated | Always check both submodule pin AND standalone checkout |
| Planned Keystone as a transport daemon | Architecture docs describe it as invisible transport | Keystone is a C++20 library, not a deployable service | Read actual source, not architecture docs |
| Expected ProjectOdyssey to integrate with agent mesh | Docs say "research sandbox graduates to AchaeanFleet" | ProjectOdyssey is a pure Mojo ML framework with zero NATS/REST | ProjectOdyssey has nothing to do with the agent mesh |

## Results & Parameters

### Ecosystem Contract Bugs Fixed (ecosystem-audit session, 2026-03-16)

```yaml
critical:
  C1: NATSListener parts count < 6 → < 5 (was dropping ALL messages)
  C2: daemon.py task.title/assigned_to/depends_on → subject/assignee_agent_id/blocked_by
  C3: MaestroClient refactored to persistent connections with close()
  C4: Odysseus architecture.md Keystone "secrets management" → "DAG execution"

important:
  I1: NATS subject hi.tasks.*.*.updated → hi.tasks.> (catch all verbs)
  I2: Hermes registrar missing task.completed/task.failed subscriptions
  I3: Core NATS → JetStream durable consumer (at-least-once delivery)
  I4: CLAUDE.md status values aligned (todo→pending, done→completed)
  I5: ADR 005 created for actual NATS subject schema
  I6: Keystone MaestroClient → persistent httpx.AsyncClient
  I7: Hephaestus "imported by all" → "not yet imported"
  I8: Hermes + Telemachy config migrated to pydantic-settings
  I9: .gitignore cleanup for Mnemosyne/ and build/ artifacts
```

### Code Quality Remediation Metrics (multi-domain session, 2026-03-14)

| Metric | Before | After |
|--------|--------|-------|
| Tests passing | 351 | 358 |
| Coverage | 81.65% | 81.66% |
| Broad `except Exception` (unjustified) | 21 | 0 |
| F-string logging instances | 35 | 0 |
| `print()` in library code | 44 | 0 |
| Duplicated markdown discovery | 3 locations | 1 shared utility |

### Charter Enforcement Results (Myrmidons session, 2026-05-17)

```text
PR #730 (C1: remove reconciler core)        ~  8,200 lines deleted, 52 files
PR #731 (C2: remove reconciler tests)        ~  6,400 lines deleted, 38 files
PR #732 (C3: remove TLS/auth docs/scripts)   ~  5,600 lines deleted, 41 files
PR #733 (C4: remove reconciler CI/workflows) ~  4,400 lines deleted, 28 files
TOTAL                                          -24,632 lines, 159 files
127 GitHub issues auto-closed across 4 verdict buckets
```

**Verdict bucket template:**

```bash
for n in $(jq -r '.[] | select(.verdict=="MOVED-TO-AGAMEMNON") | .number' /tmp/classified.json); do
  gh issue close "$n" --comment "Out-of-charter per <charter-link>. Migrated to ProjectAgamemnon: <PR-url>"
done
```

### ai-maestro Integration Surface (analysis, 2026-03-27)

```yaml
ai_maestro_version: v0.26.5
total_rest_routes: ~100
routes_used_by_ecosystem: 4
usage_percentage: ~4%
webhook_event_types: 4 (all agent.*, no task.*)
authentication_current: "None — MAESTRO_API_KEY defaults to empty"
authentication_future: "AID v0.2.0 (Ed25519 + OAuth 2.0 + scoped JWT)"
```

### Component Readiness Matrix (ground truth, 2026-04-03)

```yaml
PRODUCTION_READY: [Agamemnon, Nestor, Hermes, hello-myrmidon, Argus, E2E compose]
NEEDS_WORK:       [Myrmidons submodule pin, NATS leafnode configs, hi.logs pipeline]
NOT_STARTED:      [Keystone daemon, BlazingMQ, peer discovery, persistence, chaos injection]
NOT_RELEVANT:     [ProjectOdyssey — Mojo ML framework, zero mesh integration]
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence ecosystem (12 repos) | 2026-03-16 audit and remediation session | `ecosystem-audit-remediation` skill snapshot |
| ProjectHephaestus | 2026-03-14 post-audit v2 remediation | `multi-domain-audit-remediation` skill snapshot |
| HomericIntelligence/Myrmidons | 2026-05-17 charter enforcement, -24,632 lines | `dataset-repo-charter-stacked-deletion-prs` skill snapshot |
| ai-maestro v0.26.5 vs Odysseus ecosystem | 2026-03-27 integration gap analysis | `architecture-odysseus-ai-maestro-integration-gap` skill snapshot |
| Odysseus vs Ruflo v3.5 | 2026-03-27 architectural comparison | `architecture-odysseus-ruflo-comparison` skill snapshot |
| HomericIntelligence full component inventory | 2026-04-03 ground truth mapping | `architecture-homeric-ecosystem-ground-truth` skill snapshot |
