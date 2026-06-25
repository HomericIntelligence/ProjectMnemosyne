---
name: architecture-compose-resource-limit-env-substitution
description: "Planning pattern for exposing hard-coded docker-compose deploy.resources limits/reservations (cpus, memory) as overridable Compose ${VAR:-default} substitutions WITHOUT changing default behavior. CRITICAL test-breakage trap: yaml.safe_load does NOT interpolate ${VAR:-default} — it returns the literal string, so any test/parser that does float(limits['cpus']) on the raw YAML scalar raises ValueError once the scalar becomes '${HERMES_CPU_LIMIT:-0.50}'. When converting a YAML scalar to a substitution, audit EVERY test/parser that reads that key and add a regex helper that validates the substitution FORM + its default instead of float()-ing the raw value. Replicate the repo's EXISTING substitution convention exactly; keep current hard-coded values as the :-default so unconfigured `compose up` is byte-for-behavior unchanged; apply the same vars to ALL services sharing the identical block (YAGNI — no per-service knobs, no config-loader layer); document new vars in BOTH .env.example and the project config table; no Python Settings fields (Compose-runtime limits are orchestration config, not app config). Use when: (1) an issue asks to make compose resource limits/reservations overridable, (2) you are turning a YAML scalar into a ${VAR:-default} substitution, (3) a test does float()/parsing on a compose YAML value you are about to parameterize."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, docker-compose, deploy-resources, env-var-substitution, yaml-safe-load, float-parse-trap, default-preservation, yagni, orchestration-config, unverified]
---

# Architecture: Compose Resource-Limit Env-Var Substitution

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Expose hard-coded docker-compose `deploy.resources` limits/reservations (`cpus`, `memory`) as overridable Compose `${VAR:-default}` substitutions without changing default behavior (ProjectHermes issue #537) |
| **Outcome** | Plan authored — NOT executed. The plan replicates the repo's existing `${VAR:-default}` convention, preserves current values as defaults, parameterizes both services that shared the identical block, and replaces a test's `float()` on the raw YAML scalar with a regex helper that validates the substitution form + default |
| **Verification** | unverified — PLANNING learning only; no tests were run, no `docker compose config` was executed (Docker unavailable during planning), no CI confirmed it. Source facts below were established by READING the files, not by running anything |
| **Category** | architecture / planning |
| **Related Issues** | ProjectHermes #537 |

## When to Use This Skill

Use this skill when planning (not yet implementing) and any of the following hold:

- An issue asks to make docker-compose `deploy.resources` limits/reservations (`cpus`, `memory`) **overridable** without changing the default `compose up` behavior.
- You are about to convert a YAML scalar (e.g. `cpus: "0.50"`) into a `${VAR:-default}` substitution string.
- A test or parser somewhere does `float(...)`, `int(...)`, or otherwise interprets a compose YAML value you are about to parameterize.
- The same hard-coded resource block is duplicated across multiple services and you must decide whether to expose one set of vars or per-service knobs.

**Triggers:**

- Issue body contains "make limits overridable," "expose resource limits as env vars," "parameterize cpus/memory," or names specific limit vars like `HERMES_CPU_LIMIT` / `HERMES_MEMORY_LIMIT`.
- You catch yourself typing `cpus: "${SOMETHING:-0.50}"` into a compose file.
- A repo already has a `tests/test_docker_compose.py` (or similar) that loads the compose file with `yaml.safe_load` and asserts on its values.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. Treat it as a hypothesis until CI confirms. Verification level: `unverified` — planning learning only; the plan it came from was never executed, no tests ran, and `docker compose config` was never invoked (Docker was unavailable during planning). The source-line facts below were established by READING the files, not by running anything.

### Step 1 — Replicate the repo's EXISTING substitution convention exactly

Do not invent a new convention. Grep the compose file for the form it already uses and mirror it character-for-character.

```bash
# ProjectHermes already uses the ${VAR:-default} form:
grep -n '\${' docker-compose.yml
#   "${HERMES_PORT:-8085}:8085"
#   WEBHOOK_SECRET=${WEBHOOK_SECRET:-}
```

The established form is `${VAR:-default}` (POSIX default-value expansion, which Compose supports). Use that, not `$VAR`, not `${VAR}`, not a `.env`-only var without an inline default.

### Step 2 — Keep current hard-coded values as the `:-default`

The whole point is zero behavior change when unconfigured. Put the CURRENT literal into the default slot:

```yaml
# before
limits:
  cpus: "0.50"
  memory: 256M
# after — identical behavior on `compose up` with no env set
limits:
  cpus: "${HERMES_CPU_LIMIT:-0.50}"
  memory: "${HERMES_MEMORY_LIMIT:-256M}"
```

An unconfigured `compose up` must resolve to byte-for-byte the same effective values as before.

### Step 3 — Apply the SAME vars to ALL services that shared the identical block (YAGNI)

In ProjectHermes both `nats` and `hermes` had the same `limits`/`reservations` block (docker-compose.yml around lines 22-29 and 58-65). Expose ONE set of vars that tunes the whole stack rather than fragmenting into `HERMES_CPU_LIMIT` + `NATS_CPU_LIMIT` + ... . Per-service knobs are YAGNI until someone actually needs to tune one service independently. Likewise: do NOT add a config-loader layer — plain `${VAR:-default}` with defaults is the entire mechanism.

### Step 4 — Audit EVERY test/parser that reads the key you are about to parameterize

This is the durable, easy-to-miss step. `yaml.safe_load` does NOT interpolate `${VAR:-default}` — it returns the literal string `"${HERMES_CPU_LIMIT:-0.50}"`. Any test that does `float(limits["cpus"])` will raise `ValueError` after the change.

```bash
# Find everything that interprets the values you're parameterizing:
grep -rn 'safe_load\|float(\|int(\|\["cpus"\]\|\["memory"\]' tests/
# ProjectHermes: tests/test_docker_compose.py lines ~19-48 do
#   float(limits["cpus"]) and float(reservations["cpus"])  → would break
```

Replace the raw-`float()` assertions with a regex helper that validates the substitution **form** and extracts/validates its **default**:

```python
import re

_SUBST = re.compile(r"^\$\{[A-Z0-9_]+:-(?P<default>[^}]+)\}$")

def _default_of(value: str) -> str:
    """Return the :-default inside a ${VAR:-default} scalar, asserting the form."""
    m = _SUBST.match(value)
    assert m, f"expected ${{VAR:-default}} substitution, got {value!r}"
    return m.group("default")

# then: float(_default_of(limits["cpus"])) > 0
```

This keeps the test meaningful (the default is still a positive float / non-empty memory string) AND locks in the substitution form.

### Step 5 — Document the new vars in BOTH places, and note the runtime caveat

- Add each new var to `.env.example` (with its default and a one-line description).
- Add each new var to the project's config table (here, `CLAUDE.md`).
- In `.env.example`, call out explicitly that env overrides take effect only on `compose up` / recreate — **not** on an already-running container.
- Do NOT add Python `Settings` fields. Compose-runtime resource limits are ORCHESTRATION config (consumed by the Compose engine), not application config (consumed by the app). Adding them to `hermes/config.py` would be a category error.

### Quick Reference

```text
1. grep the compose file for the EXISTING ${VAR:-default} form — mirror it exactly
2. put the CURRENT literal in the :-default slot → zero behavior change when unset
3. ONE set of vars for all services sharing the block (YAGNI; no per-service knobs, no loader)
4. grep tests/ for float()/int()/safe_load on the key → swap raw float() for _default_of() regex
5. document in .env.example AND the config table; note "applies on `compose up`, not live containers"
6. NO Python Settings fields — orchestration config, not app config
```

```yaml
# Canonical substitution form (both services):
cpus: "${HERMES_CPU_LIMIT:-0.50}"
memory: "${HERMES_MEMORY_LIMIT:-256M}"
```

```python
# The regex that keeps the test meaningful after substitution:
_SUBST = re.compile(r"^\$\{[A-Z0-9_]+:-(?P<default>[^}]+)\}$")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assume existing tests still pass after substitution | Left `tests/test_docker_compose.py` untouched, which does `float(limits["cpus"])` on the raw YAML scalar | `yaml.safe_load` does NOT interpolate `${VAR:-default}`; after the change the scalar is the literal string `"${HERMES_CPU_LIMIT:-0.50}"`, so `float()` raises `ValueError` | When converting a YAML scalar to a `${VAR:-default}` substitution, audit EVERY test/parser that reads that key; replace raw `float()` with a `_default_of()` regex helper that validates the substitution FORM and its default |
| Over-engineer with a config-loader layer or per-service knobs | Considered a Python loader that reads/validates the limits, and/or separate `HERMES_CPU_LIMIT` + `NATS_CPU_LIMIT` vars | Both services shared one identical block; per-service vars and a loader add surface area no one asked for | YAGNI — expose ONE set of plain `${VAR:-default}` vars with defaults; one override tunes the whole stack |
| Add the limits to Python `Settings` | Considered surfacing the limits via `hermes/config.py` like other tunables | Compose-runtime resource limits are consumed by the Compose engine, not the app — they are orchestration config, not application config | Keep orchestration config in the compose file + `.env.example`; do not mirror it into the app's `Settings` |
| Document only in the config table | Planned to add vars only to `CLAUDE.md`'s config table | `.env.example` is where operators copy from; omitting it hides the knob and its default | Document new vars in BOTH `.env.example` and the project config table |
| Imply env overrides apply to a live container | Initial wording suggested setting the var would re-limit a running container | Compose only applies resource changes on `up`/recreate, not to an already-running container | State the `compose up`/recreate caveat explicitly in `.env.example` |

## Results & Parameters

### What the plan delivered (design intent — unverified)

- `deploy.resources.limits` and `deploy.resources.reservations` for BOTH the `nats` and `hermes` services parameterized as `${VAR:-default}`, defaults equal to the current literals (`cpus 0.50/0.10`, `memory 256M/64M`).
- A `_default_of()` regex helper in `tests/test_docker_compose.py` that asserts the substitution form and validates the extracted default (positive float for cpus, non-empty for memory), replacing the now-broken `float(limits["cpus"])` calls.
- New vars documented in `.env.example` (with the `compose up`/recreate caveat) and in `CLAUDE.md`'s config table.
- No Python `Settings` changes.

### Canonical form (copy-paste)

```yaml
limits:
  cpus: "${HERMES_CPU_LIMIT:-0.50}"
  memory: "${HERMES_MEMORY_LIMIT:-256M}"
reservations:
  cpus: "${HERMES_CPU_RESERVATION:-0.10}"
  memory: "${HERMES_MEMORY_RESERVATION:-64M}"
```

```python
_SUBST = re.compile(r"^\$\{[A-Z0-9_]+:-(?P<default>[^}]+)\}$")

def _default_of(value: str) -> str:
    m = _SUBST.match(value)
    assert m, f"expected ${{VAR:-default}} substitution, got {value!r}"
    return m.group("default")
```

### Most uncertain assumptions / reviewer risks (verify before relying on these)

1. **Parameterizing `reservations` (not just `limits`) was an INFERENCE.** Issue #537 named only the two limit vars (`HERMES_CPU_LIMIT`, `HERMES_MEMORY_LIMIT`). Extending the pattern to `reservations` is justified by test/behavior consistency but was NOT explicitly requested — a reviewer could legitimately scope it down to limits only.
2. **`docker compose config` verification was NOT run.** The acceptance checks that confirm the substitution resolves to the old defaults require Docker, which was unavailable during planning. Those steps are unverified.
3. **Exact line numbers may have drifted.** The plan cited `docker-compose.yml:36`/`:42` for the substitution examples and `tests/test_docker_compose.py` lines ~19-48 for the `float()` calls; the files were read once but may have changed since.
4. **No repo-wide consumer audit was done.** It was not verified that no OTHER consumer (a CI workflow, a helm chart, `scripts/`, or deployment tooling) reads these compose resource values and would break when they become substitution strings. Grep the whole repo for `deploy.resources`, `cpus`, `memory`, and the file path before relying on "only the test reads these."

### Generalizable lessons (the durable takeaway)

1. `yaml.safe_load` returns `${VAR:-default}` scalars VERBATIM — it does not interpolate. Any code that `float()`s/`int()`s/parses such a value breaks the moment the scalar becomes a substitution.
2. When parameterizing a YAML scalar, the audit of downstream readers (tests, parsers, CI) is the real work — replace raw conversion with a regex helper that validates the substitution form + its default.
3. Mirror the repo's EXISTING substitution convention; do not introduce a second one.
4. Preserve current values as `:-default` so the unconfigured path is byte-for-behavior unchanged.
5. One set of vars for all services sharing an identical block; per-service knobs and config-loader layers are YAGNI.
6. Orchestration-runtime config (Compose resource limits) belongs in the compose file + `.env.example`, NOT in the application's `Settings`.
7. Env overrides to compose resource limits apply on `up`/recreate, not to live containers — say so where operators will read it.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHermes | Issue #537 planning | Planning-only; unverified — plan never executed, no tests run, `docker compose config` never invoked. Source facts (compose lines, test `float()` calls, existing `${VAR:-default}` usage) confirmed by READING the files |
