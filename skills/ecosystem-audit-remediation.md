---
name: ecosystem-audit-remediation
description: 'Systematic cross-repo ecosystem audit and remediation. Use when: validating
  multi-repo integration boundaries, hunting cross-repo contract bugs, or remediating
  documentation drift.'
category: architecture
date: 2026-03-16
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Objective** | Audit and remediate a distributed multi-repo ecosystem for integration bugs, documentation drift, and pattern inconsistencies |
| **Scope** | 12 repositories, 6 PRs, 6 issues filed |
| **Findings** | 4 critical bugs, 9 important issues, 5 minor issues |
| **Duration** | Single session — plan mode audit → 5-wave remediation → verification → PRs |

## When to Use

- Multiple repos share contracts (NATS subjects, REST API fields, status enums) and you need to verify they agree
- Documentation (architecture.md, ADRs) may have drifted from implementation
- A new repo was scaffolded and needs validation against the ecosystem's actual integration points
- You need to find "silent failures" where code runs without errors but drops messages or uses wrong field names

## Verified Workflow

### Quick Reference

1. **Audit phase** (plan mode): Read every repo's code + docs, build alignment matrix
2. **Categorize**: Critical (runtime breaks) > Important (confusion/drift) > Minor (style)
3. **Wave execution**: Fix criticals first, docs second, integration third, standardization fourth, cleanup fifth
4. **Verification**: Run tests after each wave, use sub-agents for parallel file-level verification
5. **PR creation**: One PR per repo, file follow-up issues for remaining work

### Phase 1: Cross-Repo Audit

Build an alignment matrix comparing documented behavior vs actual behavior:

| Repo | Documented Role | Actual Role | Aligned? |
| ------ | ---------------- | ------------- | ---------- |
| Each repo | What docs say | What code does | Yes/No |

Key areas to cross-check:
- **NATS subjects**: Compare publisher subjects (Hermes) vs subscriber filters (Keystone, Telemachy) vs documentation (Odysseus ADRs)
- **API field names**: Compare REST client field mappings vs Pydantic model attributes vs CLAUDE.md references
- **Status enums**: Compare status values across all repos that handle task lifecycle
- **Dependency claims**: Verify "imported by X" claims in architecture docs against actual `pixi.toml`/`pyproject.toml` dependencies

### Phase 2: Wave-Based Remediation

Execute fixes in dependency order:

1. **Wave 1 — Critical runtime bugs**: Fix code that crashes or silently drops data
2. **Wave 2 — Documentation**: Fix architecture docs, create missing ADRs, add central references
3. **Wave 3 — Integration gaps**: Fix subscription mismatches, missing event types
4. **Wave 4 — Pattern standardization**: Unify config patterns, client patterns, status values
5. **Wave 5 — Cleanup**: Gitignore, naming conventions, minor consistency

### Phase 3: Verification

- Run `just test` in every modified repo
- Use parallel sub-agents for file-level verification (PASS/FAIL per check)
- Fix any issues found during verification before committing

### Phase 4: PR and Issue Creation

- One branch + PR per repo (consistent naming: `ecosystem-audit-remediation`)
- File GitHub issues for follow-up work discovered but out of scope
- Set PRs to auto-merge

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting CLAUDE.md status values over code | Used `todo`/`done` from CLAUDE.md as authoritative | Code actually uses `pending`/`completed` — CLAUDE.md was stale | Always treat code (especially Pydantic models and enums) as the source of truth for field names and status values |
| Assuming NATS subject part count from comments | Code comment said "6 parts" so check was `< 6` | `hi.tasks.team.task.updated` is actually 5 parts — the comment was wrong | Count the actual dots in the subject string; never trust comments over split() behavior |
| Creating PRs targeting default branch without checking | Used `gh pr create` without `--base` flag | Some repos use `main`, others `master` — PR creation failed with "no common history" | Always check `gh repo view --json defaultBranchRef` and verify local branch was created from the correct base |
| Skipping HMAC in webhook tests | Tests sent raw JSON without computing HMAC signature | `.env` file had `WEBHOOK_SECRET` set, so server validated HMAC and returned 401 | When migrating config to pydantic-settings (which auto-loads `.env`), check if `.env` contains values that change behavior — especially secrets that gate auth checks |
| Removing `close()` calls without adding the method | Removed `await maestro_client.close()` from daemon.py as the fix for C3 | When later refactoring MaestroClient to persistent connections, `close()` became valid and needed | Consider the full fix arc — if you're going to refactor a client later in the same session, plan the close() story end-to-end |

## Results & Parameters

### Bugs Fixed

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
  I4: CLAUDE.md status values aligned with code (todo→pending, done→completed)
  I5: ADR 005 created documenting actual NATS subject schema
  I6: Keystone MaestroClient persistent httpx.AsyncClient
  I7: Hephaestus "imported by all" → "not yet imported"
  I8: Hermes + Telemachy config migrated to pydantic-settings
  I9: .gitignore cleanup for ProjectMnemosyne/ and build/ artifacts

minor:
  M1: 8 new NATSListener tests
  M2: pixi.toml names standardized (project-telemachy, project-hephaestus)
  M4: docs/nats-subjects.md central reference created
  M5: Odysseus justfile recipes for keystone-start/status, scylla-test
```

### Test Results

```yaml
ProjectKeystone: 27/27 passed
ProjectHermes: 19/19 passed (was 14/18 — fixed HMAC in tests)
ProjectTelemachy: 24/24 passed
```

### Cross-Check Pattern (reusable)

```bash
# Find all NATS subject definitions across ecosystem
grep -r "hi\.tasks\|hi\.agents\|TASK_SUBJECT\|AGENT_EVENTS" ~/Project*/src/ ~/Odysseus/docs/

# Find all status enum definitions
grep -r "completed\|pending\|backlog\|in_progress" ~/Project*/src/*/models.py

# Find all maestro_client patterns
grep -r "httpx.AsyncClient\|async with.*client" ~/Project*/src/*/maestro_client.py

# Verify config patterns
grep -r "BaseSettings\|os.environ.get\|load_dotenv" ~/Project*/src/*/config.py
```
