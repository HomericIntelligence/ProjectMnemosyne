---
name: nats-server-auth-authz-hardening
description: "Plan NATS server-side authentication and authorization (authz) hardening for the HomericIntelligence mesh on top of the existing ADR-008 TLS PKI. Use when: (1) adding app-layer auth to NATS after TLS already landed, (2) deciding between X.509 cert mapping (verify_and_map) vs decentralized operator/NKey/JWT, (3) scoping NATS subjects per agent/consumer/bridge against the ADR-005 hi.* schema, (4) writing an ADR for mesh auth (do NOT edit the append-only ADR-008), (5) auditing whether verify/verify_and_map/accounts{} are present in configs/nats, (6) avoiding the trap of treating Tailscale isolation as app-layer security."
category: architecture
date: 2026-06-19
version: "1.0.0"
verification: unverified
user-invocable: false
history: nats-server-auth-authz-hardening.history
tags:
  - nats
  - auth
  - authz
  - authorization
  - tls
  - pki
  - x509
  - verify_and_map
  - accounts
  - jetstream
  - mesh
  - leafnode
  - cluster
  - adr
  - subject-scoping
  - hi-schema
  - aid
  - jwt
  - nkey
  - homeric-intelligence
  - planning
  - unverified
---

# NATS Server Auth/Authz Hardening (HomericIntelligence Mesh)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Plan NATS server-side authentication + authorization hardening for the HomericIntelligence mesh, reusing the existing ADR-008 TLS PKI rather than standing up decentralized operator/NKey/JWT auth |
| **Outcome** | A plan was written: reuse the X.509 mutual-cert trust chain via `verify_and_map` (client) + `verify` (cluster/leafnode), plus subject-scoped `accounts{}` mapped to the ADR-005 `hi.*` schema. AID v0.2.0 Ed25519 + scoped JWT recorded as the documented FUTURE path. NOT executed — no config applied, no `nats-server -t` parse check run. |
| **Verification** | `unverified` (PLANNING ONLY — Odysseus session 2026-06-19; plan written but not executed) |
| **History** | [changelog](./nats-server-auth-authz-hardening.history) |

## When to Use

- You need to add application-layer authentication/authorization to NATS in a mesh where TLS has *already* landed (ADR-008) and you must not double-implement transport security.
- You are deciding between X.509 certificate mapping (`verify_and_map`) versus a decentralized operator/NKey/JWT scheme and need the trade-off rationale.
- You are scoping NATS subjects per role (agent / consumer / bridge) against the ADR-005 `hi.*` subject schema.
- You are about to write an ADR for mesh auth and need to know the next sequential number and the append-only rule (never edit ADR-008).
- You are auditing whether `verify` / `verify_and_map` / `authorization{}` / `accounts{}` already exist in `configs/nats/`.
- You are tempted to rely on Tailscale/Tailnet isolation as the security boundary and need the counter-argument.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — this is a PLANNING learning. The plan was written but NOT executed: no NATS config was applied and no `nats-server -t` parse check was actually run. The highest-risk assumptions (cert→user mapping semantics, JetStream API subject scoping, `accounts{}` syntax, `accounts{}`-in-leaf.conf validity) are listed unverified in Results & Parameters.

### Proposed Workflow

1. **Verify the on-disk config FIRST — do not trust an issue's cited line numbers.** The triggering issue (#175) cited `server.conf:12-21` as having "no tls block". That was STALE: TLS already landed via ADR-008 (PRs #290/#292). Confirm with a fresh read of `configs/nats/server.conf` and `configs/nats/leaf.conf`.

2. **Confirm TLS is present on every listener** (already true after ADR-008): `tls{}` on client (4222), leafnode (7422), cluster (6222), and monitoring HTTP (`127.0.0.1:8222`).

3. **Audit the auth/authz gap.** Run the grep in Quick Reference. The gap is: no `verify` / `verify_and_map` anywhere, and no `authorization{}` / `accounts{}` (only a commented `monitoring_authorization`).

4. **Reuse the ADR-008 X.509 mutual-cert PKI for identity — do NOT build decentralized JWT.** Add `verify_and_map` to the client `tls{}` (maps the client cert identity to a NATS user), and `verify` to the cluster and leafnode `tls{}` blocks (mutual cert required, no user mapping needed there). This avoids the operator keypair, JWT resolver, and out-of-band issuance pipeline that decentralized auth would require and that do not exist on disk.

5. **Define subject-scoped `accounts{}` mirroring ADR-005.** Map cert identities to accounts with publish/subscribe permissions scoped to the `hi.*` schema (see Quick Reference). Agents, the Keystone consumer, and the Hermes bridge each get distinct scopes.

6. **Write a NEW ADR — never edit ADR-008.** ADRs are append-only (CLAUDE.md principle 3; `docs/adr/README.md`). The next sequential number was 009. Reference ADR-008 (TLS) and ADR-005 (subject schema); do not modify them.

7. **Record AID v0.2.0 Ed25519 + scoped JWT as the documented FUTURE path,** not the now path. It needs an operator keypair, a JWT resolver, and an issuance pipeline that do not yet exist.

8. **Validate before claiming done** (these were NOT run in this planning session — they are the gate): `nats-server -t -c <conf>` parse check (or docker `nats:latest` fallback), plus grep assertions that `verify_and_map`, `verify`, `accounts {`, and `system_account` are present.

### Quick Reference

```bash
# 1. Verify on-disk config (NEVER trust an issue's cited line numbers)
sed -n '1,40p' configs/nats/server.conf      # confirm tls{} on every listener
sed -n '1,40p' configs/nats/leaf.conf

# 2. Audit the auth/authz gap
grep -riE "verify|authorization|accounts|nkey|jwt|resolver|operator" configs/nats
# Expected today: only a commented monitoring_authorization — no verify/accounts

# 3. Find the next ADR number (append-only; never edit ADR-008)
ls docs/adr/ | grep -E '^[0-9]{3}-'    # next sequential number (was 009)

# 4. VALIDATION GATE — run these BEFORE claiming done (NOT run in planning)
nats-server -t -c configs/nats/server.conf    # parse check
nats-server -t -c configs/nats/leaf.conf
# fallback if nats-server not installed:
docker run --rm -v "$PWD/configs/nats:/c" nats:latest -t -c /c/server.conf

# 5. Post-edit grep assertions (all must match after applying the plan)
grep -q "verify_and_map" configs/nats/server.conf
grep -q "verify"         configs/nats/server.conf   # cluster + leafnode
grep -q "accounts {"     configs/nats/server.conf
grep -q "system_account" configs/nats/server.conf
```

```hcl
# UNVERIFIED example shape — written from memory, NOT parse-checked.
# Client listener: map the client cert identity to a NATS user.
tls {
  # ... existing ADR-008 cert/key/ca ...
  verify_and_map = true        # client cert identity -> user field in accounts{}
}

# Cluster (6222) and leafnode (7422): mutual cert only, no user mapping.
cluster   { tls { verify = true } }
leafnodes { tls { verify = true } }

# Subject scoping mirrors ADR-005 hi.* schema.
accounts {
  AGENTS {
    users = [ { user = "agent" } ]   # mapped from cert CN/SAN (UNVERIFIED mapping)
    exports = []
    # publish hi.agents.> + hi.tasks.>; explicitly deny subscribe hi.research.>
    permissions { publish { allow = ["hi.agents.>", "hi.tasks.>"] }
                  subscribe { deny = ["hi.research.>"] } }
  }
  KEYSTONE {
    users = [ { user = "keystone" } ]
    # consumer: subscribe hi.tasks.> (durable "keystone-dag")
    permissions { subscribe { allow = ["hi.tasks.>"] } }
  }
  HERMES {
    users = [ { user = "hermes" } ]
    # bridge creates streams: broad hi.> plus JetStream API
    permissions { publish   { allow = ["hi.>", "$JS.API.>"] }
                  subscribe { allow = ["hi.>", "$JS.API.>"] } }
  }
}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Trust issue line-number evidence | #175 cited server.conf:12-21 as having no tls block | TLS already landed in ADR-008; cited lines were stale | Read the actual on-disk config; never plan against an issue's cited line numbers |
| Treat Tailscale as the security boundary | Rely on Tailnet isolation for mesh auth | Host-level isolation ≠ app-layer auth; one compromised host exposes the full mesh | Enforce app-layer auth on EVERY listener (client+cluster+leafnode), not just network isolation |
| Decentralized operator/NKey/JWT | Considered full NATS JWT auth (operator+resolver+accounts) | Needs operator keypair, JWT resolver, out-of-band issuance pipeline — none exist on disk | Reuse the existing ADR-008 X.509 mutual-cert PKI via verify_and_map; defer JWT to AID v0.2.0 |

## Results & Parameters

```yaml
# Repo facts verified by reading on disk (HomericIntelligence/Odysseus, 2026-06-19)
on_disk_facts:
  tls_status: "already landed via ADR-008 (PRs #290 / #292)"
  server_conf_tls: "tls{} present on client(4222), leafnode(7422), cluster(6222), monitoring http(127.0.0.1:8222)"
  leaf_conf_tls: "tls{} present (leafnode remotes block)"
  authz_gap: "no verify / verify_and_map anywhere; no authorization{} / accounts{}"
  authz_grep: 'grep -riE "verify|authorization|accounts|nkey|jwt|resolver|operator" configs/nats -> only commented monitoring_authorization'
  adr_rule: "ADRs are append-only (CLAUDE.md principle 3, docs/adr/README.md); next number was 009; NEVER edit ADR-008"

# Subject scoping plan (mirrors ADR-005 hi.* schema)
subject_scoping:
  agents:
    publish: ["hi.agents.>", "hi.tasks.>"]
    deny_subscribe: ["hi.research.>"]
  keystone_consumer:
    subscribe: ["hi.tasks.>"]
    durable: "keystone-dag"
  hermes_bridge:    # creates streams
    allow: ["hi.>", "$JS.API.>"]

# Chosen path vs deferred
decision:
  now: "reuse ADR-008 X.509 mutual-cert PKI: verify_and_map (client) + verify (cluster/leafnode) + subject-scoped accounts{}"
  future: "AID v0.2.0 Ed25519 identity docs + scoped JWT (needs operator keypair + JWT resolver + issuance pipeline; none on disk)"

# Validation commands that SHOULD run before claiming done (NOT run in this planning session)
validation_gate:
  - "nats-server -t -c configs/nats/server.conf   # parse check"
  - "nats-server -t -c configs/nats/leaf.conf"
  - "docker run --rm -v $PWD/configs/nats:/c nats:latest -t -c /c/server.conf   # fallback"
  - 'grep -q verify_and_map configs/nats/server.conf'
  - 'grep -q "accounts {" configs/nats/server.conf'
  - 'grep -q system_account configs/nats/server.conf'

# Most uncertain assumptions (UNVERIFIED RISKS — highest first)
unverified_assumptions:
  - id: cert-to-user-mapping
    risk: highest
    claim: "verify_and_map maps client cert CN/SAN to the `user` field in accounts{}"
    unknown: "exact mapping semantics (CN vs SAN vs full DN), and whether users=[{user=...}] is the correct key under TLS mapping vs needing an authorization{users} block. NOT verified against NATS docs."
  - id: jetstream-api-subjects
    risk: high
    claim: "per-account JetStream subjects needed: $JS.API.>, $JS.API.CONSUMER.>, $JS.ACK.>"
    unknown: "plausible but not verified against actual Hermes/Keystone client code; over/under-scoping breaks stream creation or consumer ack."
  - id: accounts-syntax
    risk: high
    claim: "the accounts{} example (nested permissions, deny lists) is valid NATS config"
    unknown: "written from memory of NATS config format; NOT parse-checked with nats-server -t."
  - id: accounts-in-leaf-conf
    risk: high
    claim: "accounts{} can live in leaf.conf alongside a leafnode remotes block"
    unknown: "validity of accounts{} in leaf.conf, and how leaf-local client identities reconcile with hub accounts, is unverified."
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | 2026-06-19 planning session | Plan written from on-disk reads of `configs/nats/{server,leaf}.conf`; TLS confirmed present (ADR-008); auth/authz gap confirmed via grep. Plan NOT executed — no config applied, no `nats-server -t` run. Verification: `unverified`. |
