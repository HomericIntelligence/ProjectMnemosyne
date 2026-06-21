---
name: nats-server-auth-authz-hardening
description: "Plan or implement NATS server-side authentication and authorization (authz) hardening for the HomericIntelligence mesh. Use when: (1) adding app-layer auth to NATS after TLS already landed, (2) deciding between token-based auth vs X.509 cert mapping (verify_and_map) vs decentralized operator/NKey/JWT, (3) configuring authorization{} blocks on BOTH client AND leafnode listeners (the dual-listener trap), (4) hardening the NATS cluster{} route listener on port 6222 against unauthorized peer joins, (5) scoping NATS subjects per agent/consumer/bridge against the ADR-005 hi.* schema, (6) writing an ADR for mesh auth (do NOT edit append-only ADRs), (7) auditing whether verify/verify_and_map/accounts{} or authorization{} are present in configs/nats or in cluster{}, (8) writing a brace-depth awk validator for NATS config blocks with word-boundary keyword anchoring, (9) wiring NATS auth validation tests into BOTH justfile and CI gates."
category: architecture
date: 2026-06-20
version: "1.3.0"
verification: verified-local
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
  - cluster-route
  - route-listener
  - port-6222
  - adr
  - subject-scoping
  - hi-schema
  - aid
  - jwt
  - nkey
  - token
  - homeric-intelligence
  - planning
  - ci
  - validation
  - awk
  - brace-depth
  - word-boundary
  - fail-closed
  - verified-local
---

# NATS Server Auth/Authz Hardening (HomericIntelligence Mesh)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Plan or implement NATS server-side authentication + authorization hardening for the HomericIntelligence mesh |
| **Outcome** | v1.0.0–v1.1.0: A plan was written then REVISED after a reviewer NOGO: reuse the X.509 mutual-cert trust chain via `verify_and_map` (client) + `verify` (cluster/leafnode), plus subject-scoped `accounts{}` mapped to the ADR-005 `hi.*` schema. v1.2.0: EXECUTED and CI-verified (issue #176, PR #303). Token-based auth added on BOTH the client listener AND the leafnode listener via two separate `authorization {}` blocks. Key traps documented: auth only on the client listener leaves the leafnode listener open; brace-depth awk required to validate nested configs; NATS exits non-zero (not silently empty string) on unset env vars; port 7422 for leafnode remotes; CI validator must be a dedicated step not just a justfile recipe. v1.3.0: EXECUTED and verified-local (issue #306, PR #341). Cluster route listener (port 6222) hardened with `authorization { token = "$NATS_CLUSTER_TOKEN" }` inside `cluster{}`. Extended validator with a 4th check using the brace-depth `block()` function (word-boundary anchored). Test file wired into BOTH justfile and CI gates. ADR-009 amended in-place (not created new). |
| **Verification** | `verified-local` (v1.3.0 — Odysseus issue #306, PR #341, CI pending); `verified` (v1.2.0 — Odysseus issue #176, PR #303, CI passed) |
| **History** | [changelog](./nats-server-auth-authz-hardening.history) |

## When to Use

- You need to add application-layer authentication/authorization to NATS in a mesh where TLS has *already* landed (ADR-008) and you must not double-implement transport security.
- You are deciding between token-based auth, X.509 certificate mapping (`verify_and_map`), or decentralized operator/NKey/JWT and need the trade-off rationale.
- You are adding `authorization {}` to `server.conf` and need to know that the client listener and the `leafnodes {}` listener are SEPARATE — auth on the client listener does NOT protect the leafnode listener.
- You are configuring `leaf.conf` remotes and need to know the correct port (7422, not 4222) and token syntax.
- You are writing a shell validator for NATS config files that contain nested blocks (e.g. `tls {}` inside `leafnodes {}`) and need a brace-depth awk extractor instead of a simple range match.
- You need to write a CI step that asserts NATS auth is fail-closed and need to know the correct assertion (expect `nats-server -t` to exit non-zero when a required env var is unset, do NOT grep output).
- You are adding a NATS auth CI step and need to know it must be a dedicated step in `ci.yml`, not just a justfile recipe (CI never invokes `just validate-configs` unless the workflow explicitly calls it).
- You are hardening the NATS `cluster{}` route listener (port 6222) against unauthorized peer joins — the same fail-open class as the client and leafnode listeners.
- You are adding `authorization { token = "$NATS_CLUSTER_TOKEN" }` inside `cluster{}` and need to know this is the correct pattern (cluster routes use token or user/password auth inside `cluster{}`, NOT per-route NKey/JWT — only leafnodes support NKey/JWT per remote).
- You have a single-host deployment with no routes configured and need to know the cluster auth block is inert/no-op when no routes are active, so adding it does not break a single-host setup.
- You are writing a brace-depth awk block extractor and need to anchor the keyword match with `"(^|[[:space:]])" kw "[[:space:]]*\\{"` to prevent a keyword like `cluster` from matching `subcluster {` or `mycluster {`.
- You added a test file for the NATS validator and need to know test files do NOT self-invoke — you must explicitly call them in BOTH the justfile recipe AND the CI step, or the test coverage never runs.
- You are about to write a new ADR but the issue body says to create a specific ADR number — always run `ls docs/adr/` first; the number may already exist (issue #306 referenced ADR-009, which already existed from issue #176).
- You are reading issue body line-number citations — they are frequently stale after prior PRs merge and shift lines; always re-read the actual file to verify coordinates.
- You are scoping NATS subjects per role (agent / consumer / bridge) against the ADR-005 `hi.*` subject schema.
- You are about to write an ADR for mesh auth and need to know the next sequential number and the append-only rule.
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

## Verified Workflow (v1.2.0) — Token Auth on Both Listeners

> **Verification:** `verified` — Odysseus issue #176, PR #303, CI passed (2026-06-19).

### Token Auth: The Dual-Listener Trap

NATS `server.conf` has two completely independent listeners: the **client listener** (port 4222) and the **leafnode listener** (port 7422). An `authorization {}` block at the top level of `server.conf` protects the CLIENT listener only. To protect the leafnode listener, a SEPARATE `authorization {}` block must live INSIDE the `leafnodes {}` block.

```hcl
# server.conf — TWO separate authorization blocks are required
authorization {
  token = "$NATS_CLIENT_TOKEN"   # protects the client listener (port 4222)
}

leafnodes {
  port = 7422
  tls {
    cert_file = "..."
    key_file  = "..."
    ca_file   = "..."
    verify    = true
  }
  authorization {
    token = "$NATS_LEAF_TOKEN"   # protects the leafnode listener — SEPARATE from above
  }
}
```

```hcl
# leaf.conf — remotes must use port 7422 (NOT 4222) and include the token
leafnodes {
  remotes = [{
    url = "nats+tls://<hub-ip>:7422"   # port 7422, NOT 4222 (4222 silently never connects)
    tls { ca_file = "/etc/nats/certs/ca.pem" }
    token = "$NATS_LEAF_TOKEN"          # env-substituted at parse time
  }]
}
```

### Token-Based Auth Workflow (issue #176)

1. **Add `authorization { token = "$NATS_CLIENT_TOKEN" }` at the top level of `server.conf`** (before any listener-specific blocks). This protects the 4222 client listener.

2. **Add a SECOND `authorization { token = "$NATS_LEAF_TOKEN" }` block INSIDE the `leafnodes {}` block in `server.conf`.** This is a completely separate config directive. Without it the leafnode listener accepts anonymous connections.

3. **Add `token = "$NATS_LEAF_TOKEN"` to the `remotes` entry in `leaf.conf`**. NATS substitutes `$VAR` at parse time. If the env var is unset, `nats-server -t` exits non-zero (fail-closed) — it does NOT silently substitute empty string.

4. **Verify the leafnode remote URL targets port 7422, not 4222.** The `url` in the `remotes` block must be `nats+tls://<hub-ip>:7422`. A connection to 4222 from a leaf silently never establishes — there is no error at the leaf side, the leafnode just never joins.

5. **Write a validator using brace-depth awk.** A simple `awk '/leafnodes/,/}/'` range terminates at the FIRST `}` which is inside the nested `tls {}` block, not the closing `}` of `leafnodes {}`. The `authorization {}` that follows the `tls {}` block is never captured, giving a false negative on a correctly-configured file. The correct approach is brace-depth tracking:

```bash
# Brace-depth block extractor — correctly handles nested blocks
block() {
  local file="$1" kw="$2"
  sed 's/#.*//' "$file" | awk -v kw="$kw" '
    inb==0 && $0 ~ kw"[[:space:]]*\\{" { inb=1; d=0 }
    inb==1 {
      print
      o=gsub(/\{/,"{"); c=gsub(/\}/,"}"); d+=o-c
      if (d<=0) inb=2
    }'
}

# Usage: check that leafnodes{} contains an authorization block
block configs/nats/server.conf leafnodes | grep -q "authorization" || { echo "FAIL: leafnodes has no auth"; exit 1; }
```

6. **Wire the validator into CI as a DEDICATED STEP in `.github/workflows/ci.yml`, NOT just a justfile recipe.** CI workflows only invoke `just` targets that are explicitly listed in a step. A recipe in the justfile is never invoked unless the workflow explicitly calls it. A `validate-configs` recipe in the justfile and a CI workflow that doesn't call it provide zero CI enforcement.

7. **Assert fail-closed with `! nats-server -c leaf.conf -t`, not grep on output.** When `$NATS_LEAF_TOKEN` is unset, NATS errors at parse time: `variable reference for "NATS_LEAF_TOKEN" can not be found` (non-zero exit). The correct CI assertion is `! nats-server -c configs/nats/leaf.conf -t 2>/dev/null` (expect non-zero). A grep-based assertion (`nats-server -c leaf.conf -t 2>&1 || true | grep -q 'NATS_LEAF_TOKEN'`) fails for the WRONG reason: NATS's error message contains the variable name, so grep matches and exits 1 even though the assertion was intended to prove fail-closed behavior.

### Quick Reference (v1.2.0)

```bash
# 1. Audit — check BOTH listeners for authorization
grep -n "authorization" configs/nats/server.conf   # must appear twice: once top-level, once inside leafnodes{}

# 2. Verify leafnodes authorization is inside the block (brace-depth, not range match)
block() {
  sed 's/#.*//' "$1" | awk -v kw="$2" '
    inb==0 && $0 ~ kw"[[:space:]]*\\{" { inb=1; d=0 }
    inb==1 { print; o=gsub(/\{/,"{"); c=gsub(/\}/,"}"); d+=o-c; if (d<=0) inb=2 }'
}
block configs/nats/server.conf leafnodes | grep -q "authorization"

# 3. Assert NATS is fail-closed on unset token (expect non-zero)
! nats-server -c configs/nats/leaf.conf -t 2>/dev/null

# 4. Check leaf.conf remote port (must be 7422)
grep "url" configs/nats/leaf.conf   # must contain :7422, NOT :4222

# 5. Check .gitignore covers credential files
grep -E "\*.creds|\*.pem|\*.key" .gitignore

# 6. Validate that the CI step is actually in the workflow (not just the justfile)
grep -n "validate\|nats" .github/workflows/ci.yml
```

## Verified Workflow (v1.3.0) — Cluster Route Listener Authorization

> **Verification:** `verified-local` — Odysseus issue #306, PR #341, all 6 test cases pass, `just validate-configs` passes, CI pending (2026-06-20).

### Cluster Route Listener: The Third Listener

NATS has THREE distinct listeners, each requiring its own `authorization {}` block:
- **Client listener** (port 4222): protected by a top-level `authorization {}` block
- **Leafnode listener** (port 7422): protected by `authorization {}` inside `leafnodes {}`
- **Cluster route listener** (port 6222): protected by `authorization {}` inside `cluster {}`

Issue #306 is in the same fail-open class as issue #176 — the cluster listener was left without auth after client and leafnode were hardened.

### Cluster Auth Pattern

Cluster routes authenticate via `authorization {}` (token or user/password) placed INSIDE the `cluster {}` block. This is NOT per-route NKey/JWT — only leafnodes support NKey/JWT per remote. The token must match on every peer in a multi-server cluster.

```hcl
# server.conf — THREE separate authorization blocks required (one per listener)
authorization {
  token = "$NATS_CLIENT_TOKEN"   # protects the client listener (port 4222)
}

leafnodes {
  port = 7422
  tls { ... }
  authorization {
    token = "$NATS_LEAF_TOKEN"   # protects the leafnode listener (port 7422)
  }
}

cluster {
  name = "homeric"
  port = 6222
  tls { ... }
  authorization {
    token = "$NATS_CLUSTER_TOKEN"   # protects the cluster route listener (port 6222)
  }
  # routes = [ ... ]  # only needed when routes are configured; block is inert on single-host
}
```

**Single-host deployment note:** When no `routes` are configured, the `authorization {}` inside `cluster {}` is inert at runtime — a single-host deployment is unaffected. The block is defensive: it takes effect only when routes are added.

### Extending the Brace-Depth Validator (4th Check)

The existing `tools/validate-nats-auth.sh` already had a `block()` brace-depth parser from issue #176. Extending it for cluster is a one-step addition of check 4:

```bash
# In validate-nats-auth.sh — Check 4: cluster{} authorization
CLUSTER_BLOCK=$(block "$SERVER_CONF" cluster)
if [ -n "$CLUSTER_BLOCK" ]; then
  # A cluster{} block exists — it MUST have authorization{}
  if ! echo "$CLUSTER_BLOCK" | grep -q "authorization"; then
    fail "cluster{} block found but no authorization{} inside it"
  fi
fi
# No cluster{} block → single-host deployment; pass (exit 0)
```

### Word-Boundary Anchoring in the block() Function

The critical fix: the `block()` awk pattern MUST be word-boundary anchored. Without anchoring, `block configs/nats/server.conf cluster` also matches `subcluster {` or `mycluster {`.

```bash
block() {
  local file="$1" kw="$2"
  sed 's/#.*//' "$file" | awk -v kw="$kw" '
    inb==0 && $0 ~ "(^|[[:space:]])" kw "[[:space:]]*\\{" { inb=1; d=0 }
    inb==1 {
      print
      o=gsub(/\{/,"{"); c=gsub(/\}/,"}"); d+=o-c
      if (d<=0) inb=2
    }'
}
```

The anchoring pattern `"(^|[[:space:]])" kw "[[:space:]]*\\{"` requires the keyword to appear at the start of a line or after whitespace — not as a substring of a longer word.

### Test File Wiring (Critical — Both Gates Required)

A test file does NOT self-invoke. After creating `tools/tests/test-validate-nats-auth.sh` with 6 cases, BOTH gates must explicitly call it:

1. **justfile** `validate-configs` recipe:
   ```
   bash tools/validate-nats-auth.sh configs/nats/server.conf configs/nats/leaf.conf
   bash tools/tests/test-validate-nats-auth.sh
   ```

2. **`.github/workflows/ci.yml`** Validate NATS auth step:
   ```yaml
   - name: Validate NATS auth
     run: |
       bash tools/validate-nats-auth.sh configs/nats/server.conf configs/nats/leaf.conf
       bash tools/tests/test-validate-nats-auth.sh
   ```

If only `tools/validate-nats-auth.sh` is called but not the test file, the brace-depth regression and check-4 coverage never run in CI.

### 6 Test Cases for Cluster Auth

```bash
# tools/tests/test-validate-nats-auth.sh
# Case 1: real server.conf passes
# Case 2: authed cluster fixture passes
# Case 3: unauthed leaf fixture fails (check 3 regression)
# Case 4: unauthed cluster fixture fails (check 4 new)
# Case 5: no cluster{} block passes (single-host is valid)
# Case 6: brace-depth guard — auth outside cluster{} does NOT satisfy check
#          (auth { } before cluster { ... } must not falsely pass)
```

### Quick Reference (v1.3.0)

```bash
# 1. Verify ALL three listeners have authorization (should appear 3x)
grep -n "authorization" configs/nats/server.conf
# Expected: line in top-level scope (client), line inside leafnodes{}, line inside cluster{}

# 2. Word-boundary block extractor (anchored — prevents substring matches)
block() {
  sed 's/#.*//' "$1" | awk -v kw="$2" '
    inb==0 && $0 ~ "(^|[[:space:]])" kw "[[:space:]]*\\{" { inb=1; d=0 }
    inb==1 { print; o=gsub(/\{/,"{"); c=gsub(/\}/,"}"); d+=o-c; if (d<=0) inb=2 }'
}
block configs/nats/server.conf cluster | grep -q "authorization" && echo "OK" || echo "FAIL"

# 3. Check that the test file is wired into both gates
grep -n "test-validate-nats-auth" justfile .github/workflows/ci.yml
# Must appear in both files

# 4. Check ADR directory before creating a new ADR (avoid number collision)
ls docs/adr/ | grep -E '^[0-9]{3}-'

# 5. Re-read the actual file coordinates — never trust issue body line numbers
# Issue #306 cited server.conf:54-64 — the actual cluster{} block may be at different lines
# after prior PRs (e.g. #303 from issue #176) shifted the file
grep -n "^cluster" configs/nats/server.conf
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
| Verify hardening with token greps only (v1.1.0) | grep verify=true / accounts{ to "prove" auth | Proves syntax/presence, not that unauth connect is rejected or scoping enforced | Add functional tests: no-cert rejected, stream-creator can create stream, low-priv denied a subtree |
| grep-based fail-closed CI assertion (v1.2.0) | `nats-server -c leaf.conf -t 2>&1 \|\| true \| grep -q 'NATS_LEAF_TOKEN'` | NATS errors at parse time; its error message contains the var name, so grep matches and incorrectly exits 1 even when config is valid | Use `! nats-server -c leaf.conf -t 2>/dev/null` — assert non-zero exit, don't grep output |
| Simple awk range extraction (v1.2.0) | `awk '/leafnodes/,/}/'` to extract leafnodes block | First `}` inside nested `tls {}` terminates the range; `authorization {}` after tls{} is never captured → false negative | Use brace-depth awk: count `{`/`}` depth; only stop when depth returns to 0 |
| Assuming .gitignore covers *.creds (v1.2.0) | `grep "creds" .gitignore` expected a match | `*.creds` was not in .gitignore even though `*.pem` was — a silent gap | Always verify gitignore coverage for credential file extensions explicitly; don't assume |
| Assuming justfile recipe = CI gate (v1.2.0) | Added `validate-nats-auth` recipe to justfile, assumed CI would run it | CI only invokes `just` targets that appear in explicit workflow steps; `ci.yml` never called `just validate-configs` | Wire validators as DEDICATED steps in `ci.yml`; a justfile recipe with no CI caller provides zero enforcement |
| Unanchored awk keyword in block() (v1.3.0) | Used `kw "[[:space:]]*\\{"` without word-boundary prefix | Pattern matches `subcluster {` or `mycluster {` as false positives for `cluster` | Anchor with `"(^|[[:space:]])" kw "[[:space:]]*\\{"` so keyword must be at line-start or after whitespace |
| Test file not wired into CI gate (v1.3.0) | Created `tools/tests/test-validate-nats-auth.sh` but only ran `tools/validate-nats-auth.sh` in justfile and ci.yml | Brace-depth regression and check-4 coverage never ran in CI — reviewer flagged the gap | Explicitly call the test file in BOTH justfile recipe AND ci.yml step; test files do NOT self-invoke |
| Assuming ADR number is free (v1.3.0) | Issue body said "document in ADR-009" — assumed number was available | ADR-009 already existed (created during issue #176); attempting `git add docs/adr/009-*.md` would create a duplicate | Run `ls docs/adr/` before creating any ADR; amend the existing ADR if the decision is an extension |
| Stale issue line-number coordinates (v1.3.0) | Issue #306 cited `server.conf:54-64` as the cluster{} block location | After issue #176 (PR #303) merged and shifted lines, the actual cluster{} block was at different lines | Issue body line numbers are often stale after prior PRs merge; always re-read the file to verify coordinates |

## Results & Parameters

```yaml
# Repo facts verified by reading on disk (HomericIntelligence/Odysseus, 2026-06-19 / 2026-06-20)
on_disk_facts:
  tls_status: "already landed via ADR-008 (PRs #290 / #292)"
  server_conf_tls: "tls{} present on client(4222), leafnode(7422), cluster(6222), monitoring http(127.0.0.1:8222)"
  leaf_conf_tls: "tls{} present (leafnode remotes block)"
  authz_gap: "no verify / verify_and_map anywhere; no authorization{} / accounts{}"
  authz_grep: 'grep -riE "verify|authorization|accounts|nkey|jwt|resolver|operator" configs/nats -> only commented monitoring_authorization'
  adr_rule: "ADRs are append-only (CLAUDE.md principle 3, docs/adr/README.md); next number was 009; NEVER edit ADR-008"
  cluster_auth_gap: "v1.2.0 closed client+leafnode; cluster{} route listener (port 6222) was still open → fixed in v1.3.0 (issue #306, PR #341)"
  cluster_auth_token_syntax: "authorization { token = \"$NATS_CLUSTER_TOKEN\" } inside cluster{} — NOT per-route NKey/JWT (only leafnodes support that)"
  cluster_auth_single_host: "no routes configured → cluster authorization{} block is inert at runtime; single-host deployment unaffected"
  validator_check_count: "v1.3.0: 4 checks — (1) client auth, (2) leafnode listener auth, (3) leaf.conf remote token, (4) cluster{} auth if cluster{} block present"
  test_file_wiring: "test file must be called in BOTH justfile recipe AND ci.yml step — it does NOT self-invoke"
  adr_amendment: "ADR-009 already existed (issue #176); amended in-place to add cluster listener decision point; did NOT create new ADR"
  issue_line_numbers_stale: "issue #306 cited server.conf:54-64 — actual cluster{} location shifted after PR #303 merged; always re-read the file"

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
| HomericIntelligence/Odysseus | 2026-06-19 planning + review session (v1.1.0) | Plan written from on-disk reads of `configs/nats/{server,leaf}.conf` and submodule client config (Hermes/Telemachy); TLS confirmed present (ADR-008); auth/authz gap confirmed via grep. R0 plan NOGO'd by a reviewer (bare-CN mapping bug) and REVISED → v1.1.0. Still NOT executed — no config applied, no `nats-server -t`, no functional auth test run. Verification: `unverified`. |
| HomericIntelligence/Odysseus | 2026-06-19 implementation session (v1.2.0) | Issue #176: token-based auth added to `configs/nats/server.conf` (TWO `authorization {}` blocks: one top-level for the client listener, one inside `leafnodes {}` for the leafnode listener) and `configs/nats/leaf.conf` (token in remotes). `tools/validate-nats-auth.sh` created with brace-depth awk block extractor. CI validator wired as a dedicated step in `.github/workflows/ci.yml`. PR #303 committed and pushed; CI passed. Verification: `verified`. |
| HomericIntelligence/Odysseus | 2026-06-20 implementation session (v1.3.0) | Issue #306: cluster route listener (port 6222) hardened with `authorization { token = "$NATS_CLUSTER_TOKEN" }` inside `cluster{}` in `configs/nats/server.conf`. `tools/validate-nats-auth.sh` extended with a 4th check using existing `block()` function (word-boundary anchored). `tools/tests/test-validate-nats-auth.sh` created with 6 test cases and wired into both justfile and ci.yml gates. ADR-009 amended in-place. All 6 test cases pass; `just validate-configs` passes. PR #341 opened. Verification: `verified-local` (CI pending). |
