# Ecosystem Audit & Remediation — Session Notes

## Date: 2026-03-16

## Context

The HomericIntelligence ecosystem has 12 repositories organized around ai-maestro (core platform). This session performed a full audit validating repo integration boundaries, documentation accuracy, and code correctness.

## Repositories Audited

1. ai-maestro (core, not modified)
2. AchaeanFleet
3. ProjectHermes — webhook → NATS bridge
4. ProjectArgus — observability
5. Myrmidons — GitOps agent provisioning
6. ProjectTelemachy — workflow engine
7. ProjectKeystone — DAG executor (most bugs found here)
8. ProjectProteus — CI/CD
9. ProjectMnemosyne — skills marketplace
10. ProjectHephaestus — shared utilities
11. ProjectOdyssey — research/training
12. ProjectScylla — testing/chaos

## Critical Findings Detail

### C1: NATSListener Subject Parsing Bug

**File**: `ProjectKeystone/src/keystone/nats_listener.py:42-43`

The code had:
```python
# Expected: hi . tasks . {team_id} . {task_id} . updated  (6 parts)
if len(parts) < 6:
```

But `"hi.tasks.team.task.updated".split(".")` produces `["hi", "tasks", "team", "task", "updated"]` = 5 parts, not 6. Every single NATS message was silently dropped with a warning log. The daemon's only working path was the startup scan.

### C2: Daemon AttributeError

**File**: `ProjectKeystone/src/keystone/daemon.py:79-82`

Used `task.title`, `task.assigned_to`, `task.depends_on` but the Task model has `task.subject`, `task.assignee_agent_id`, `task.blocked_by`. This was clearly a case of writing code against CLAUDE.md documentation rather than the actual model.

### C3: Missing close() Method

**File**: `ProjectKeystone/src/keystone/daemon.py:95,114`

Called `await maestro_client.close()` but MaestroClient created new httpx.AsyncClient per request and had no close() method. Fixed by refactoring to persistent client with proper lifecycle.

### C4: Odysseus Architecture Completely Wrong About Keystone

**File**: `Odysseus/docs/architecture.md`

Described Keystone as "Secrets and credential management; injects secrets into ai-maestro agent configs" with "Vault or SOPS backend". Keystone has zero secrets-related code — it's a DAG executor that watches NATS events. This was likely a placeholder from initial scaffolding that was never updated.

## Integration Contract Mismatches Found

| Contract | Publisher (Hermes) | Subscriber (Keystone) | Docs (Odysseus) |
| ---------- | ------------------- | ---------------------- | ----------------- |
| NATS subjects | `hi.tasks.{team}.{task}.{verb}` | Was: `hi.tasks.*.*.updated` only | Was: `maestro.task.*` |
| Task verbs | `updated`, `completed`, `failed` | Was: only `updated` | Not documented |
| Subscribed events | `_TASK_EVENTS` has 3 | `_SUBSCRIBED_EVENTS` had only 1 task event | N/A |
| Status values | Passes through from ai-maestro | Code: `completed`, CLAUDE.md: `done` | Not documented |

## Config Pattern Audit

| Repo | Before | After |
| ------ | -------- | ------- |
| Keystone | pydantic-settings (good) | unchanged |
| Hermes | os.environ.get + python-dotenv | pydantic-settings |
| Telemachy | os.environ.get + python-dotenv | pydantic-settings |

## PRs Created

| Repo | PR | URL |
| ------ | ----- | ----- |
| ProjectKeystone | #82 | https://github.com/HomericIntelligence/ProjectKeystone/pull/82 |
| ProjectHermes | #1 | https://github.com/HomericIntelligence/ProjectHermes/pull/1 |
| ProjectTelemachy | #1 | https://github.com/HomericIntelligence/ProjectTelemachy/pull/1 |
| Odysseus | #1 | https://github.com/HomericIntelligence/Odysseus/pull/1 |
| Myrmidons | #1 | https://github.com/HomericIntelligence/Myrmidons/pull/1 |
| ProjectHephaestus | #17 (updated) | https://github.com/HomericIntelligence/ProjectHephaestus/pull/17 |

## Key Lesson

The most dangerous bugs were "silent" — NATSListener dropping all messages logged a warning but never crashed. If you only look at error logs, you'd think it was working. The startup scan masked the problem by advancing DAGs on boot. Only by tracing the actual subject string through `.split(".")` and counting parts could you find the off-by-one.
