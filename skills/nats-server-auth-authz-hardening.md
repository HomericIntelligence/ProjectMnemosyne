---
name: nats-server-auth-authz-hardening
description: "Plan NATS server-side authentication and authorization (authz) hardening for the HomericIntelligence mesh on top of the existing ADR-008 TLS PKI. Use when: (1) adding app-layer auth to NATS after TLS already landed, (2) deciding between X.509 cert mapping (verify_and_map) vs decentralized operator/NKey/JWT, (3) scoping NATS subjects per agent/consumer/bridge against the ADR-005 hi.* schema, (4) writing an ADR for mesh auth (do NOT edit the append-only ADR-008), (5) auditing whether verify/verify_and_map/accounts{} are present in configs/nats, (6) avoiding the trap of treating Tailscale isolation as app-layer security."
category: architecture
date: 2026-06-19
version: "1.1.0"
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
| **Outcome** | A plan was written then REVISED after a reviewer NOGO: reuse the X.509 mutual-cert trust chain via `verify_and_map` (client) + `verify` (cluster/leafnode), plus subject-scoped `accounts{}` mapped to the ADR-005 `hi.*` schema. v1.1.0 corrects the cert→user mapping (SAN-DNS, NOT bare CN), enumerates the real plaintext clients that fail-closed auth would break, separates mTLS-capable-but-unconfigured clients from those needing new code, and replaces token-grep checks with functional auth tests. AID v0.2.0 Ed25519 + scoped JWT recorded as the documented FUTURE path. STILL NOT executed — plan was reviewed, not run; no config applied, no `nats-server -t` parse check, no functional test. |
| **Verification** | `unverified` (PLANNING + REVIEW — Odysseus session 2026-06-19; plan written, NOGO'd, revised, but never executed end-to-end) |
| **History** | [changelog](./nats-server-auth-authz-hardening.history) |

## When to Use

- You need to add application-layer authentication/authorization to NATS in a mesh where TLS has *already* landed (ADR-008) and you must not double-implement transport security.
- You are deciding between X.509 certificate mapping (`verify_and_map`) versus a decentralized operator/NKey/JWT scheme and need the trade-off rationale.
- You are scoping NATS subjects per role (agent / consumer / bridge) against the ADR-005 `hi.*` subject schema.
- You are about to write an ADR for mesh auth and need to know the next sequential number and the append-only rule (never edit ADR-008).
- You are auditing whether `verify` / `verify_and_map` / `authorization{}` / `accounts{}` already exist in `configs/nats/`.
- You are tempted to rely on Tailscale/Tailnet isolation as the security boundary and need the counter-argument.
- You are mapping client certs to NATS users with `verify_and_map` and need to know what it actually matches (SAN-email → SAN-DNS → full RFC-2253 DN — NEVER a bare CN).
- You are about to flip NATS to fail-closed auth and need to enumerate every client that connects plaintext today before it breaks them.
- You need to triage per-client remediation: which clients are mTLS-capable-but-unconfigured (env-var fix) vs which lack cert wiring entirely (code fix / follow-up issue).
- You are writing acceptance criteria for a NATS auth change and need functional behavior tests (not just token-presence greps).

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — this is a PLANNING + REVIEW learning. The plan was written, NOGO'd by a reviewer, and revised (v1.1.0) — but still NOT executed: no NATS config applied, no `nats-server -t` parse check, no functional auth test run. The highest-risk assumptions (SAN-DNS cert→user mapping semantics, JetStream API subject scoping, `accounts{}` syntax, `accounts{}`-in-leaf.conf validity, the `step ca ... --san` invocation) are listed unverified in Results & Parameters.

### Proposed Workflow

1. **Verify the on-disk config FIRST — do not trust an issue's cited line numbers.** The triggering issue (#175) cited `server.conf:12-21` as having "no tls block". That was STALE: TLS already landed via ADR-008 (PRs #290/#292). Confirm with a fresh read of `configs/nats/server.conf` and `configs/nats/leaf.conf`.

2. **Confirm TLS is present on every listener** (already true after ADR-008): `tls{}` on client (4222), leafnode (7422), cluster (6222), and monitoring HTTP (`127.0.0.1:8222`).

3. **Audit the auth/authz gap.** Run the grep in Quick Reference. The gap is: no `verify` / `verify_and_map` anywhere, and no `authorization{}` / `accounts{}` (only a commented `monitoring_authorization`).

4. **Reuse the ADR-008 X.509 mutual-cert PKI for identity — do NOT build decentralized JWT.** Add `verify_and_map` to the client `tls{}` (maps the client cert identity to a NATS user), and `verify` to the cluster and leafnode `tls{}` blocks (mutual cert required, no user mapping needed there). This avoids the operator keypair, JWT resolver, and out-of-band issuance pipeline that decentralized auth would require and that do not exist on disk.

5. **Map by SAN-DNS, NOT bare CN — this was the #1 reviewer NOGO.** `verify_and_map` matches the client cert identity in this order: **SAN email → SAN DNS → full RFC-2253 Subject DN**. It does NOT match a bare CN. A v1.0.0-style `accounts.users[].user = "hermes.homeric" # CN=...` would have matched NOTHING and rejected every client. FIX: define a cert convention where each role cert carries a **DNS SAN equal to `<role>.homeric`** AND set the `accounts.users[].user` value to that exact SAN-DNS string. SAN-DNS is deterministic (no DN field-ordering fragility); document the full RFC-2253 DN only as a discouraged fallback. Pin this convention in the ADR so cert issuance (`step ca certificate <role>.homeric cert.pem key.pem --san <role>.homeric`) and the config stay in lockstep.

6. **Define subject-scoped `accounts{}` mirroring ADR-005.** Map cert identities (by SAN-DNS, per step 5) to accounts with publish/subscribe permissions scoped to the `hi.*` schema (see Quick Reference). Agents, the Keystone consumer, and the Hermes bridge each get distinct scopes. JetStream consumers need `$JS.API.CONSUMER.>` AND `$JS.API.STREAM.INFO.>` AND `$JS.ACK.>` — under-scoping silently breaks consumer/ack ops; over-scoping is benign. Validate the set with the functional consumer test (step 11), not by asserting a "minimal" set blindly.

7. **Before flipping to fail-closed, enumerate EVERY plaintext client from real service code — not just `e2e/`.** On-disk facts in Odysseus submodules: `infrastructure/ProjectHermes/src/hermes/config.py:34` defaults `nats_url="nats://localhost:4222"`; `provisioning/ProjectTelemachy/src/telemachy/config.py:21` same; `docker-compose.crosshost.yml:45` sets `NATS_URL: nats://nats:4222`. Grepping only `e2e/ tools/ justfile` MISSES the real service clients. Grep every submodule's client config module for `nats://` / `NATS_URL` first.

8. **Triage each client: mTLS-capable-but-unconfigured vs needs-new-code.** ProjectHermes ALREADY supports mTLS (`config.py:102-105` has `tls_ca_bundle/tls_cert_file/tls_key_file/tls_verify`; `config.py:126 build_ssl_context()` loads a client cert chain when cert+key set or URL is `tls://`) → it needs CONFIG (env vars), not code. ProjectTelemachy has a `require_tls` gate (`agamemnon_client.py:46-58`) that rejects plain `nats://` when `REQUIRE_TLS=true` but has NO client-cert wiring → a genuine code gap to track as a FOLLOW-UP issue, not silently assume works. Remediation differs per client (runbook env vs code issue).

9. **Treat the stream-creator cert as a hard runbook prerequisite.** ProjectHermes creates JetStream streams on startup (ADR-005), so the HERMES account needs `$JS.API.>` publish AND its cert must be provisioned BEFORE enabling `verify_and_map` — otherwise NO streams get created mesh-wide (highest blast radius).

10. **Write a NEW ADR — never edit ADR-008.** ADRs are append-only (CLAUDE.md principle 3; `docs/adr/README.md`). The next sequential number was 009. Reference ADR-008 (TLS) and ADR-005 (subject schema); do not modify them. The SAN-DNS cert convention (step 5) MUST live in this ADR.

11. **Record AID v0.2.0 Ed25519 + scoped JWT as the documented FUTURE path,** not the now path. It needs an operator keypair, a JWT resolver, and an issuance pipeline that do not yet exist.

12. **Validate with FUNCTIONAL tests, not token greps — these are the real acceptance criteria** (NOT run this session — they are the gate). `grep "verify=true"` proves the token is present, not that auth is enforced. Against a running hardened server: (a) a no-cert connect MUST be refused; (b) the stream-creator cert MUST be able to create a stream; (c) a low-priv cert MUST get a "permissions violation" on a denied subtree (e.g. agent denied `hi.research.>`). Plus the `nats-server -t -c <conf>` parse check (or docker `nats:latest` fallback).

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

# 5. Post-edit grep assertions (NECESSARY but NOT SUFFICIENT — presence != enforcement)
grep -q "verify_and_map" configs/nats/server.conf
grep -q "verify"         configs/nats/server.conf   # cluster + leafnode
grep -q "accounts {"     configs/nats/server.conf
grep -q "system_account" configs/nats/server.conf

# 6. Enumerate EVERY plaintext client before fail-closed (real service code, not just e2e/)
grep -rnE "nats://|NATS_URL" infrastructure provisioning control shared --include=*.py --include=*.yml --include=*.yaml
# Known on-disk: Hermes config.py:34, Telemachy config.py:21, docker-compose.crosshost.yml:45

# 7. Per-role cert with a DNS SAN equal to <role>.homeric (SAN-DNS is what verify_and_map maps)
step ca certificate hermes.homeric hermes.cert.pem hermes.key.pem --san hermes.homeric

# 8. FUNCTIONAL acceptance tests against a running hardened server (the REAL gate)
nats --server tls://hub:4222 pub hi.ping x                      # no cert -> MUST be refused
nats --server tls://hub:4222 --tlscert=hermes.cert.pem --tlskey=hermes.key.pem \
     stream add HI ...                                          # stream-creator -> MUST succeed
nats --server tls://hub:4222 --tlscert=agent.cert.pem --tlskey=agent.key.pem \
     sub 'hi.research.>'                                        # low-priv -> MUST get "permissions violation"
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
# CRITICAL (v1.1.0): verify_and_map matches SAN-email -> SAN-DNS -> full RFC-2253 DN,
# NEVER a bare CN. Each role cert MUST carry a DNS SAN = "<role>.homeric" and the
# user= value MUST be that exact SAN-DNS string. (UNVERIFIED syntax — not parse-checked.)
accounts {
  AGENTS {
    users = [ { user = "agent.homeric" } ]   # matches cert DNS SAN "agent.homeric"
    exports = []
    # publish hi.agents.> + hi.tasks.>; explicitly deny subscribe hi.research.>
    permissions { publish { allow = ["hi.agents.>", "hi.tasks.>"] }
                  subscribe { deny = ["hi.research.>"] } }
  }
  KEYSTONE {
    users = [ { user = "keystone.homeric" } ]   # cert DNS SAN "keystone.homeric"
    # consumer: subscribe hi.tasks.> + JetStream consumer/info/ack subjects
    permissions { subscribe { allow = ["hi.tasks.>", "$JS.API.CONSUMER.>",
                                       "$JS.API.STREAM.INFO.>", "$JS.ACK.>"] } }
  }
  HERMES {
    users = [ { user = "hermes.homeric" } ]   # cert DNS SAN "hermes.homeric"
    # stream-creator (highest blast radius): cert MUST exist before verify_and_map
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
| Map verify_and_map to bare CN | Set accounts user="hermes.homeric" expecting CN match | NATS matches SAN-email→SAN-DNS→full-DN, never bare CN; every client would be rejected | Carry a DNS SAN per role and set user= the SAN-DNS string; document the cert convention in the ADR |
| Grep only e2e/tools/justfile for nats:// | Scoped downstream-breakage check to e2e dirs | Missed real service clients (Hermes config.py:34, Telemachy config.py:21, compose:45) that default to plaintext nats:// and fail-close | Grep every submodule's client config module for nats:// / NATS_URL before enforcing auth |
| Assume all clients need new mTLS code | Treated client remediation uniformly | Hermes already had build_ssl_context()+cert fields (config not code); Telemachy genuinely lacked cert wiring (code) | Per client, distinguish capable-but-unconfigured from needs-code; remediation differs |
| Verify hardening with token greps only | grep verify=true / accounts{ to "prove" auth | Proves syntax/presence, not that unauth connect is rejected or scoping enforced | Add functional tests: no-cert rejected, stream-creator can create stream, low-priv denied a subtree |

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

# Downstream clients that fail-closed auth would break (v1.1.0 — enumerate from real code)
plaintext_clients:
  - "infrastructure/ProjectHermes/src/hermes/config.py:34 -> nats_url='nats://localhost:4222'"
  - "provisioning/ProjectTelemachy/src/telemachy/config.py:21 -> same plaintext default"
  - "docker-compose.crosshost.yml:45 -> NATS_URL: nats://nats:4222"

# Per-client remediation triage (v1.1.0 — capable-vs-needs-code)
client_triage:
  hermes:
    status: "mTLS-capable but unconfigured"
    evidence: "config.py:102-105 tls_ca_bundle/tls_cert_file/tls_key_file/tls_verify; config.py:126 build_ssl_context() loads cert chain when cert+key set or url is tls://"
    remediation: "CONFIG ONLY (env vars) — runbook, not code"
    note: "stream-creator (ADR-005) — highest blast radius; cert is a hard prerequisite before verify_and_map"
  telemachy:
    status: "needs new code"
    evidence: "agamemnon_client.py:46-58 has a require_tls gate that rejects plain nats:// when REQUIRE_TLS=true, but NO client-cert wiring"
    remediation: "FOLLOW-UP code issue — do not silently assume works"

# verify_and_map mapping order (v1.1.0 — the corrected core finding)
cert_user_mapping:
  order: ["SAN email", "SAN DNS", "full RFC-2253 Subject DN"]
  never_matches: "bare CN"
  convention: "each role cert carries DNS SAN = '<role>.homeric'; accounts.users[].user = that exact SAN-DNS string"
  issuance: "step ca certificate <role>.homeric cert.pem key.pem --san <role>.homeric"
  fallback: "full RFC-2253 DN — discouraged (field-ordering fragility)"

# Functional acceptance tests (v1.1.0 — token greps are insufficient)
functional_tests:
  - "no-cert connect MUST be refused"
  - "stream-creator cert MUST be able to create a stream"
  - "low-priv cert MUST get 'permissions violation' on a denied subtree (agent denied hi.research.>)"
  - "JetStream consumer needs $JS.API.CONSUMER.> + $JS.API.STREAM.INFO.> + $JS.ACK.> (validate functionally)"

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
  - id: san-dns-mapping
    risk: highest
    claim: "verify_and_map matches SAN-DNS and the accounts.users[].user value must equal the cert's DNS SAN string"
    unknown: "the SAN-DNS match claim and exact accounts.users[].user syntax under TLS mapping were NOT parse-checked with nats-server -t nor confirmed against current NATS docs this session — reasoned from the mapping-order rule. Still the top risk."
  - id: accounts-in-leaf-conf
    risk: high
    claim: "accounts{} can live in leaf.conf alongside a leafnodes.remotes block"
    unknown: "validity of accounts{} in leaf.conf, and how leaf-local client identities reconcile with hub accounts, is unverified."
  - id: jetstream-api-subjects
    risk: high
    claim: "minimal per-account JetStream subject set: $JS.API.CONSUMER.>, $JS.API.STREAM.INFO.>, $JS.ACK.> (+ $JS.API.> for the stream creator)"
    unknown: "plausible but only validated by the proposed functional tests, which were NOT run; under-scoping silently breaks consumer/ack ops."
  - id: step-ca-san-flag
    risk: medium
    claim: "step ca certificate <role>.homeric ... --san <role>.homeric issues a client-auth cert with the needed DNS SAN"
    unknown: "illustrative — exact flags/profile for the client-auth EKU were not verified against the installed step-ca version."
  - id: accounts-syntax
    risk: medium
    claim: "the accounts{} example (nested permissions, deny lists) is valid NATS config"
    unknown: "written from memory of NATS config format; NOT parse-checked with nats-server -t."
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | 2026-06-19 planning + review session | Plan written from on-disk reads of `configs/nats/{server,leaf}.conf` and submodule client config (Hermes/Telemachy); TLS confirmed present (ADR-008); auth/authz gap confirmed via grep. R0 plan NOGO'd by a reviewer (bare-CN mapping bug) and REVISED → v1.1.0. Still NOT executed — no config applied, no `nats-server -t`, no functional auth test run. Verification: `unverified`. |
