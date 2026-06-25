---
name: nats-verify-and-map-san-dns-identity
description: "Mechanics of NATS verify_and_map cert→user identity matching. Use when: (1) mapping TLS client certs to NATS users via verify_and_map and wondering what field is matched, (2) debugging silent client rejection where every cert-presenting client is refused, (3) setting the accounts{} user= field and unsure whether to use CN, SAN-DNS, or full DN, (4) issuing role certs with step ca and needing the correct --san flag pattern, (5) writing a deny clause in accounts{} permissions and needing to know when deny overrides allow, (6) validating allow-list enforcement via a permissions-violation test."
category: architecture
date: 2026-06-19
version: "1.0.0"
verification: verified-local
user-invocable: false
history: nats-verify-and-map-san-dns-identity.history
tags:
  - nats
  - verify_and_map
  - mtls
  - tls
  - cert
  - san
  - accounts
  - identity
  - homeric-intelligence
  - adr-009
---

# NATS verify_and_map: SAN-DNS Identity Matching

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Document the exact cert→user identity matching mechanics of `verify_and_map` so that `accounts{}` user= fields, cert issuance flags, and verification tests are set up correctly on the first attempt |
| **Outcome** | Successful — ADR-009 implemented, `nats-server -t` parse check passed on both `server.conf` and `leaf.conf`. Two defects in the original plan were caught via PR #305 review and corrected before merge: (1) bare CN used as match key (fixed to SAN-DNS), (2) no-op deny clause in subscribe permissions block (removed). |
| **Verification** | `verified-local` — fix confirmed by `nats-server -t` parse check and PR review thread resolution (PRRT_kwDORoAqe86K6YL4). CI not run on the skill PR itself. |
| **History** | [changelog](./nats-verify-and-map-san-dns-identity.history) |

## When to Use

- You are mapping TLS client certificates to NATS users via `verify_and_map` and need to know exactly which cert field is used as the match key.
- You have issued certs but every cert-presenting client is silently rejected — this skill identifies the mismatch between the cert field and the `accounts{} user=` value.
- You are setting the `user=` field inside `accounts{}` and are unsure whether to use a bare CN, a SAN-DNS string, or the full RFC-2253 Subject DN.
- You are issuing per-role certs with `step ca certificate` and need the correct flag combination to ensure a DNS SAN is embedded.
- You have written a `deny = [...]` clause in an `accounts{}` subscribe block and want to know whether it actually fires.
- You are writing a runbook acceptance test for `accounts{}` subject scoping and need to know which subscription to test to guarantee a permissions violation.

## Verified Workflow

### Quick Reference

```bash
# 1. Issue a role cert WITH a DNS SAN (required for verify_and_map to match)
step ca certificate hermes.homeric \
  hermes-cert.pem hermes-key.pem \
  --san hermes.homeric

# 2. Verify the SAN is embedded — this MUST show DNS:hermes.homeric
openssl x509 -noout -ext subjectAltName -in hermes-cert.pem
# Expected output: DNS:hermes.homeric

# 3. Parse-check the config before deploying
nats-server -t -c configs/nats/server.conf
nats-server -t -c configs/nats/leaf.conf
# Fallback if nats-server is not installed locally:
docker run --rm -v "$PWD/configs/nats:/c" nats:latest -t -c /c/server.conf

# 4. Validate allow-list enforcement with a functional test
#    Use a subject that is ABSENT from the subscribe allow-list (e.g. hi.tasks.> for AGENTS)
#    NOT a subject in a deny clause — deny is only a log entry when it overrides an allow
nats --server tls://hub:4222 \
  --tlscert=agent-cert.pem --tlskey=agent-key.pem \
  sub 'hi.tasks.>'
# Expected: "nats: Permissions Violation for Subscription to hi.tasks.>"
```

```hcl
# server.conf: verified snippet (ADR-009, parse-checked with nats-server -t)
tls {
  # ... existing cert/key/ca_file from ADR-008 ...
  verify_and_map = true   # maps client cert identity to accounts{} user= field
}

accounts {
  HERMES {
    users = [ {
      # user= MUST be the cert's DNS SAN string, NOT "CN=hermes.homeric" or "hermes"
      user = "hermes.homeric"
      permissions {
        publish   { allow = ["hi.>", "$JS.API.>"] }
        subscribe { allow = ["hi.>", "$JS.API.>", "_INBOX.>"] }
      }
    } ]
  }

  AGENTS {
    users = [ {
      user = "agent.homeric"   # cert DNS SAN "agent.homeric"
      permissions {
        publish   { allow = ["hi.agents.>", "hi.tasks.>"] }
        # Correct: omit hi.research.> from allow-list — it is simply absent.
        # Do NOT add deny = ["hi.research.>"] here: deny only overrides an existing allow,
        # and hi.research.> is not in the allow-list, so deny would be a no-op.
        subscribe { allow = ["hi.agents.>", "_INBOX.>"] }
      }
    } ]
  }
}
```

### Detailed Steps

1. **Understand the match-precedence chain.** `verify_and_map` inspects the client certificate in this exact order to produce the identity string it compares against `accounts{} user=`:
   1. SAN email (rfc822Name extension)
   2. SAN DNS (dNSName extension) — **use this; set via `--san` in step CLI**
   3. RFC-2253 Subject DN (full string, e.g. `CN=hermes.homeric,O=HomericIntelligence`) — order-sensitive, fragile
   4. Bare CN — **never matched**; if no SAN is present NATS falls to full-DN, not bare CN

2. **Issue every role cert with BOTH a CN AND a matching DNS SAN.** The canonical pattern for HomericIntelligence role certs:
   ```bash
   step ca certificate <role>.homeric cert.pem key.pem --san <role>.homeric
   ```
   Where `<role>` is `hermes`, `agent`, `keystone`, etc. Verify the SAN is present with `openssl x509 -noout -ext subjectAltName`.

3. **Set `accounts{} user=` to the exact SAN-DNS string.** If the cert carries `DNS:hermes.homeric` in its SAN extension, then `user = "hermes.homeric"`. No prefix, no scheme, no slashes — just the raw DNS name.

4. **Write `deny` clauses only when the subject is in the `allow` list.** A `deny` clause overrides an existing `allow` entry. If a subject is already absent from the allow-list, adding it to `deny` has no effect — the subject was already implicitly denied. Remove the no-op `deny` to keep configs readable and tests accurate.

5. **Write runbook verification tests against absent subjects, not deny clauses.** To prove `accounts{}` subject scoping is enforced, subscribe as a low-privilege role to a subject that is NOT in its allow-list. Do not test a deny clause — test the absence from the allow-list instead (a guaranteed permissions violation).

6. **Parse-check before deploying.** Run `nats-server -t -c <conf>` against both `server.conf` and `leaf.conf`. This catches syntax errors before any client connection attempt. Only then run functional tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Bare CN as match key | Set `user = "hermes.homeric"` assuming `verify_and_map` would match the cert's `CN=hermes.homeric` field | `verify_and_map` NEVER matches a bare CN. Match order is SAN-email → SAN-DNS → full RFC-2253 Subject DN. A cert with only `CN=hermes.homeric` and no SAN falls through to the full-DN step, which requires the complete string (e.g. `CN=hermes.homeric,O=HomericIntelligence`). Every client was silently rejected. | Always issue certs with a DNS SAN equal to the intended identity string, and set `user=` to that SAN-DNS value. Verify the SAN with `openssl x509 -noout -ext subjectAltName`. |
| No-op deny clause | Added `deny = ["hi.research.>"]` to the AGENTS subscribe block to "block research subjects" | `hi.research.>` was not in the AGENTS subscribe allow-list, so it was already implicitly denied. The `deny` clause had no effect — it can only override an existing allow, not re-deny an absence. | Use deny only to narrow an overly broad allow entry. If the subject is absent from allow, omit the deny entirely. |
| Testing deny clause to prove scoping | Runbook acceptance test subscribed to a subject in the deny clause to expect a permissions violation | The deny clause was a no-op (see above), so the test proved nothing about actual scoping. Worse, if the deny clause was later removed the test would still pass for the wrong reason. | Test allow-list enforcement by subscribing to a subject that is ABSENT from the allow-list — that guarantees a permissions violation regardless of deny clauses. |

## Results & Parameters

```yaml
# Cert issuance convention (HomericIntelligence ADR-009)
cert_convention:
  pattern: "step ca certificate <role>.homeric cert.pem key.pem --san <role>.homeric"
  verify_san: "openssl x509 -noout -ext subjectAltName -in cert.pem"
  expected_san_output: "DNS:<role>.homeric"
  roles:
    - hermes.homeric   # stream-creator (highest blast radius)
    - agent.homeric
    - keystone.homeric

# verify_and_map match precedence (from NATS docs)
match_precedence:
  1: "SAN email (rfc822Name)"
  2: "SAN DNS (dNSName)  ← USE THIS"
  3: "full RFC-2253 Subject DN (e.g. CN=hermes.homeric,O=HomericIntelligence)  ← fragile"
  never: "bare CN (e.g. hermes.homeric extracted from the CN field)  ← NEVER matched"

# accounts{} user= value rule
accounts_user_field:
  rule: "Must equal the exact SAN-DNS string from the cert (e.g. 'hermes.homeric')"
  wrong_examples:
    - "CN=hermes.homeric"          # full DN — only works if no SAN present AND order matches
    - "hermes"                     # bare label — never matches
  correct_example: "hermes.homeric"  # exact DNS SAN value

# deny clause semantics
deny_clause:
  effect: "overrides an existing allow entry in the same permissions block"
  no_op_when: "the subject is already absent from the allow-list — deny adds nothing"
  correct_use: "narrow an overly broad wildcard allow (e.g. allow hi.> then deny hi.admin.>)"

# Acceptance test pattern for allow-list enforcement
acceptance_test:
  goal: "Prove that a low-priv role cannot subscribe to out-of-scope subjects"
  pattern: "Subscribe as <role> to a subject ABSENT from its allow-list"
  example_for_agents:
    test: "nats sub 'hi.tasks.>' as agent.homeric"
    expected: "nats: Permissions Violation for Subscription to hi.tasks.>"
    why: "hi.tasks.> is not in AGENTS subscribe allow-list"
  anti_pattern: "Testing a deny clause subject — no-op deny makes this prove nothing"

# Validation gate (run before any claim of done)
validation_gate:
  - "nats-server -t -c configs/nats/server.conf"
  - "nats-server -t -c configs/nats/leaf.conf"
  - "openssl x509 -noout -ext subjectAltName -in <role>-cert.pem  # verify SAN present"
  - "Functional test: no-cert connect MUST be refused"
  - "Functional test: stream-creator cert MUST be able to create a stream"
  - "Functional test: agent cert sub hi.tasks.> MUST return permissions violation"

# PR #305 review thread where defects were caught
pr_review_reference:
  thread: "PRRT_kwDORoAqe86K6YL4"
  defects_caught:
    - "Bare CN as match key (fixed: SAN-DNS issuance + user= SAN-DNS value)"
    - "No-op deny clause in AGENTS subscribe block (fixed: removed deny)"
    - "Runbook verification test was testing allow-list rejection, not deny-clause firing (fixed: test hi.tasks.> subscription)"
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | ADR-009 implementation (issue #175) | `nats-server -t` parse check passed on both `server.conf` and `leaf.conf`. Two defects caught via PR #305 review thread PRRT_kwDORoAqe86K6YL4: bare CN match key and no-op deny clause. Both fixed before merge. `verified-local`. |

## References

- [NATS docs: TLS Authentication](https://docs.nats.io/running-a-nats-service/configuration/securing_nats/auth_intro/tls_mutual_auth)
- [NATS verify_and_map](https://docs.nats.io/running-a-nats-service/configuration/securing_nats/auth_intro/tls_mutual_auth#mapping-client-certificates)
- [Related skill: nats-server-auth-authz-hardening](./nats-server-auth-authz-hardening.md) — broader planning context (NATS auth/authz hardening for HomericIntelligence mesh, including client enumeration, JetStream subject scoping, and ADR authoring)
- [HomericIntelligence/Odysseus ADR-009](https://github.com/HomericIntelligence/Odysseus/blob/main/docs/adr/009-nats-mtls-auth.md)
