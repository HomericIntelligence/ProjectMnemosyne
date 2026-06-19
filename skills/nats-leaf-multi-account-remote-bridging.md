---
name: nats-leaf-multi-account-remote-bridging
description: "Configure NATS leaf node remote bridging when named accounts{} + system_account are defined. Use when: (1) a leaf node has explicit accounts{} + system_account, and leaf-local client traffic silently fails to reach the hub, (2) deciding how many remotes entries to write (one per non-SYS account), (3) debugging silent propagation failures where clients authenticate locally but hi.* messages never arrive at the hub, (4) verifying leaf→hub propagation after adding per-account remotes entries."
category: architecture
date: 2026-06-19
version: "1.0.0"
verification: verified-local
user-invocable: false
tags:
  - nats
  - leafnode
  - accounts
  - multi-account
  - bridging
  - verify_and_map
  - homeric-intelligence
---

# NATS Leaf Node Multi-Account Remote Bridging

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Ensure that leaf node clients in each named account (HERMES, AGENTS, KEYSTONE, TELEMACHY) have their traffic propagated to the hub when `accounts{}` + `system_account` are defined on the leaf server |
| **Outcome** | Successful — splitting the single `remotes` entry into one entry per non-SYS account (each with an explicit `account = "NAME"` field) fixed silent propagation. SYS account intentionally excluded. All remote entries reuse the same TLS cert/key/CA. Fix confirmed via `nats-server -t` parse check on the updated `configs/nats/leaf.conf`. |
| **Verification** | `verified-local` — `nats-server -t` parse check passed in local env; functional propagation test (publish on leaf with agent cert, subscribe on hub) confirmed message arrival. CI not run. |
| **History** | Discovered via PR #305 review thread `PRRT_kwDORoAqe86K6YL1` on `configs/nats/leaf.conf:79` in HomericIntelligence/Odysseus |

## When to Use

- A NATS leaf node server defines explicit `accounts{}` + `system_account`, AND leaf-local client traffic silently fails to reach the hub (messages authenticated locally but `hi.*` never propagates upstream).
- You are writing the `leafnodes { remotes = [...] }` block for a leaf that has named accounts and need to know how many entries to create.
- You hit a situation where the hub sees no messages from a leaf client even though the leaf client authenticated successfully — the missing `account:` field in a single remotes entry is the likely cause.
- You are auditing `configs/nats/leaf.conf` for correctness after adding `accounts{}` to the leaf server config.
- You are writing a functional verification runbook for a NATS leaf→hub deployment and want to ensure the propagation check covers per-account paths, not only the hub directly.

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm accounts{} and system_account exist on the leaf server
grep -E "accounts|system_account" configs/nats/leaf.conf

# 2. Count how many non-SYS accounts need a remotes entry
grep -E "^\s+[A-Z]+ \{" configs/nats/leaf.conf | grep -v "SYS"

# 3. Parse-check the config BEFORE and AFTER editing
nats-server -t -c configs/nats/leaf.conf
# fallback if nats-server not installed:
docker run --rm -v "$PWD/configs/nats:/c" nats:latest -t -c /c/leaf.conf

# 4. Leaf→hub propagation verification (run AFTER deploying)
# Publish on leaf node with an agent cert; subscribe on hub; confirm message arrives.
nats --server tls://leaf-ip:4222 \
     --tlscert=/etc/nats/certs/agent-cert.pem \
     --tlskey=/etc/nats/certs/agent-key.pem \
     --tlsca=/etc/nats/certs/ca.pem \
     pub hi.agents.ping test-payload

# On hub (separate terminal):
nats --server tls://hub-ip:4222 \
     --tlscert=/etc/nats/certs/server-cert.pem \
     --tlskey=/etc/nats/certs/server-key.pem \
     --tlsca=/etc/nats/certs/ca.pem \
     sub 'hi.agents.>'
# Expected: "test-payload" arrives. If nothing arrives — missing account: field.
```

### Detailed Steps

1. **Confirm the leaf server has named accounts.** When `accounts{}` with named accounts AND `system_account` are present, the implicit global account is GONE. Every client belongs to a named account and every remotes bridge must name that account explicitly.

2. **List all non-SYS accounts that need bridging.** The SYS / system account is internal-only — it must NOT receive a user-facing remotes entry. Every other account (e.g. HERMES, AGENTS, KEYSTONE, TELEMACHY) needs exactly one remotes entry.

3. **Write one remotes entry per non-SYS account**, each with:
   - `url` pointing to the hub leafnode listener (e.g. `nats+tls://<hub-ip>:7422`)
   - `account = "NAME"` set to the exact account name defined in `accounts{}`
   - A `tls {}` block with the leaf server's cert/key/CA (all entries can reuse the same TLS identity)

4. **Remove any remotes entry that lacks an `account:` field.** A single entry with no `account:` field silently bridges only the implicit global account — which no longer exists when named accounts are defined. Clients authenticate locally but traffic is never propagated.

5. **Run `nats-server -t -c configs/nats/leaf.conf`** to parse-check the config before deploying.

6. **Run the leaf→hub propagation check** (see Quick Reference step 4) after deploying. This is the acceptance gate — the previous runbook only tested the hub directly and missed the propagation gap entirely.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Single `remotes` entry with no `account:` field | One remotes block pointing to the hub, no `account =` key | When `accounts{} + system_account` are defined, the implicit global account no longer exists; leaf clients authenticated locally but `hi.*` traffic never reached the hub | Explicit `account = "NAME"` is required per remotes entry when named accounts are defined |
| Verify-only-at-hub runbook | Functional verification that only subscribed on the hub directly | Missed the leaf→hub propagation leg entirely; the gap was uncaught until PR review | Add a publish-on-leaf / subscribe-on-hub round-trip check as the mandatory acceptance gate |

## Results & Parameters

```yaml
# Correct leaf.conf remotes pattern when accounts{} + system_account are defined
leaf_remotes_pattern:
  rule: "one remotes entry per non-SYS named account; SYS is internal-only"
  account_field: "required — exact string matching the account name in accounts{}"
  tls_identity: "all entries can reuse the same cert/key/CA (leaf has one TLS identity)"
  sys_account: "must NOT get a user-facing remotes entry"

# Accounts in HomericIntelligence Odysseus leaf (as of PR #305)
accounts_requiring_remotes:
  - HERMES
  - AGENTS
  - KEYSTONE
  - TELEMACHY
accounts_excluded:
  - SYS   # system_account — internal only

# Root cause of silent propagation failure
root_cause:
  trigger: "accounts{} + system_account defined on leaf server"
  effect: "implicit global account no longer exists"
  symptom: "leaf clients authenticate; hi.* messages silently dropped — never forwarded to hub"
  fix: "split single remotes into N per-account entries, each with account = NAME"

# Verification gap that let the bug through initial implementation
verification_gap:
  old_runbook: "only tested hub directly — never published from leaf and confirmed arrival at hub"
  fix: "add leaf→hub propagation check: publish on leaf with agent cert, subscribe on hub"

# Parse check (must pass before deployment)
parse_check:
  primary: "nats-server -t -c configs/nats/leaf.conf"
  fallback: "docker run --rm -v $PWD/configs/nats:/c nats:latest -t -c /c/leaf.conf"
```

### Expected Output

Correct `leafnodes` block shape:

```hcl
leafnodes {
  remotes = [
    {
      url     = "nats+tls://<hub-ip>:7422"
      account = "HERMES"
      tls {
        cert_file = "/etc/nats/certs/server-cert.pem"
        key_file  = "/etc/nats/certs/server-key.pem"
        ca_file   = "/etc/nats/certs/ca.pem"
      }
    }
    {
      url     = "nats+tls://<hub-ip>:7422"
      account = "AGENTS"
      tls {
        cert_file = "/etc/nats/certs/server-cert.pem"
        key_file  = "/etc/nats/certs/server-key.pem"
        ca_file   = "/etc/nats/certs/ca.pem"
      }
    }
    {
      url     = "nats+tls://<hub-ip>:7422"
      account = "KEYSTONE"
      tls {
        cert_file = "/etc/nats/certs/server-cert.pem"
        key_file  = "/etc/nats/certs/server-key.pem"
        ca_file   = "/etc/nats/certs/ca.pem"
      }
    }
    {
      url     = "nats+tls://<hub-ip>:7422"
      account = "TELEMACHY"
      tls {
        cert_file = "/etc/nats/certs/server-cert.pem"
        key_file  = "/etc/nats/certs/server-key.pem"
        ca_file   = "/etc/nats/certs/ca.pem"
      }
    }
    # SYS account intentionally omitted — internal only
  ]
}
```

- `nats-server -t` exits 0 (parse OK)
- Leaf→hub propagation test: message published on leaf arrives on hub subscriber

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | PR #305 review thread `PRRT_kwDORoAqe86K6YL1`, `configs/nats/leaf.conf:79`, 2026-06-19 | Single remotes entry with no `account:` field caused silent propagation failure. Fix: split into one entry per non-SYS account. Verified via `nats-server -t` parse check (local env) + leaf→hub functional propagation test. |

## References

- [NATS Leaf Node Documentation](https://docs.nats.io/running-a-nats-service/configuration/leafnodes)
- [NATS Accounts Configuration](https://docs.nats.io/running-a-nats-service/configuration/securing_nats/accounts)
- [nats-server-auth-authz-hardening](./nats-server-auth-authz-hardening.md)
- [homeric-crosshost-deployment-and-mesh-topology](./homeric-crosshost-deployment-and-mesh-topology.md)
