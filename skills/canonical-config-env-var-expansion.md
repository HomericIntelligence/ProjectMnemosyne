---
name: canonical-config-env-var-expansion
description: "De-hardcode developer-specific values (IPs, hostnames, paths) from CANONICAL config files (NATS .conf, Nomad HCL) that hosts copy or symlink. CRITICAL: NATS expands a WHOLE-VALUE bare token only (url = $NATS_LEAF_URL) — NOT a substring inside a quoted URL; Nomad agent HCL does NOT expand OS env at all (use envsubst). Use when: (1) a canonical config in configs/ has a dev-specific literal like a Tailscale IP, (2) the file is deployed by copy/symlink so no launcher can inject values, (3) you need to verify env-var expansion actually resolves at runtime (run the daemon, not just -t)."
category: architecture
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: verified-local
history: canonical-config-env-var-expansion.history
tags: [nats, nomad, env-var-expansion, config, leaf-node, envsubst, daemon-verification, negative-control, tailscale, planning]
---

# Canonical Config Env-Var Expansion

## Overview

This skill captures a durable learning from re-planning Odysseus GitHub issue #181 after a NOGO: a developer-specific Tailscale IP (`100.92.173.32`) was hardcoded in `configs/nats/leaf.conf` and `configs/nomad/client.hcl`. The prior plan assumed each config engine would natively expand `$VAR`/`${VAR}`. Running the actual NATS daemon (nats-server v2.10.24) DISPROVED that assumption for the quoted-substring form, and Nomad docs disproved it for agent HCL entirely.

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Objective | De-hardcode a dev-specific Tailscale IP from canonical NATS/Nomad config files deployed by copy/symlink, and verify the expansion actually resolves at runtime |
| Outcome | NATS path proven by running the daemon; Nomad path corrected via docs (latent bug found in prior precedent) |
| Verification | verified-local (NATS=daemon-verified-local; Nomad=doc-verified-only) |
| History | [changelog](./canonical-config-env-var-expansion.history) |

## When to Use

- De-hardcoding developer-specific values (IPs, hostnames, paths) from CANONICAL config files that hosts copy or symlink (not files launched by the repo's own justfile/CI).
- You cannot rely on a launcher script to inject values — the deploy model is "copy file, export env var, start daemon".
- A fix relies on a config engine's env-var expansion and you must PROVE it resolves — different engines expand env DIFFERENTLY, so never assume parity across engines or across config sites within one engine.
- The same literal appears in MULTIPLE files (config + `.env.example`) and all must be fixed consistently.

## Verified Workflow

> **Status:** NATS half = daemon-verified-local (ran nats-server v2.10.24 on this host and observed the dial target). Nomad half = doc-verified-only (nomad not installed; behavior confirmed from developer.hashicorp.com/nomad/docs/configuration, not run). Not verified-ci.

1. **Know how EACH engine expands env — they differ.**
   - **NATS** expands a `$VAR`/`${VAR}` ONLY when it is the WHOLE value of a config token (a bare, unquoted token). It does NOT expand `$VAR` as a substring inside a quoted string. So put the FULL `scheme://host:port` into one variable: `url = $NATS_LEAF_URL`.
   - **Nomad agent HCL** does NOT interpolate OS env vars (`${ENV}` / `${env("VAR")}`) in config files at all. Only `bind_addr`/`addresses`/`advertise` accept go-sockaddr `{{...}}` templates, and those resolve LOCAL interfaces only — they cannot supply a REMOTE server's IP. Pre-render the file with `envsubst` (or similar) before `nomad agent -config`.
2. **Verify by RUNNING THE DAEMON, not by syntax checks.** `nats-server -t` and `nomad fmt -check` are SYNTAX-ONLY and return "valid" for BOTH the broken substring form and the working whole-value form — they cannot detect this failure. Start the daemon with debug logging, grep for the resolved IP, and add a NEGATIVE-CONTROL test that proves the detector catches the broken substring form.
3. Reuse env-var names ALREADY declared in `.env.example` where possible, but the NATS value must now be a WHOLE URL — introduce `NATS_LEAF_URL` (full URL) rather than only `NATS_SERVER_IP`, because a bare host var cannot be spliced into a quoted string.
4. A hardcoded value typically recurs across MULTIPLE files. Fix all occurrences, and make `.env.example` defaults NEUTRAL placeholders (e.g. `nats+tls://<your-server-tailscale-ip>:7422`), NEVER the dev literal, so a copied-but-unedited `.env` fails loudly.
5. Do NOT treat an existing `${NOMAD_ADVERTISE_ADDR}` in `server.hcl` as precedent — Nomad reads it LITERALLY, so it is a latent bug, not proof of interpolation.

### Quick Reference

NATS — whole-value bare var (WORKS, coexists with `tls{}`):

```hocon
# leaf.conf  (NATS_LEAF_URL=nats+tls://10.11.12.13:7422)
leafnodes {
  remotes = [
    {
      url = $NATS_LEAF_URL          # bare token, WHOLE value — expanded
      tls { ca_file: "/etc/nats/ca.pem" }
    }
  ]
}
```

NATS — daemon verification + negative control:

```bash
# WORKING form: expect a dial to the resolved IP
NATS_LEAF_URL=nats+tls://10.11.12.13:7422 \
  timeout 3 nats-server -c leaf.conf -D -p 14222 2>&1 \
  | grep -q 'connect as leafnode to remote server on "10.11.12.13:7422"' \
  && echo "PASS: env resolved to IP"
# observed: [DBG] ... Trying to connect as leafnode to remote server on "10.11.12.13:7422" -> dial tcp 10.11.12.13:7422

# NEGATIVE CONTROL: the broken quoted-substring form must FAIL on the literal token
#   url = "nats+tls://$NATS_SERVER_IP:7422"
NATS_SERVER_IP=10.11.12.13 \
  timeout 3 nats-server -c leaf-broken.conf -D -p 14223 2>&1 \
  | grep -q 'lookup $NATS_SERVER_IP: no such host' \
  && echo "PASS: detector catches the broken substring form"
# observed: [ERR] ... lookup $NATS_SERVER_IP: no such host  (dialed the LITERAL "$NATS_SERVER_IP")
```

Nomad — pre-render with envsubst (NOT native interpolation):

```bash
# client.hcl.tmpl contains:  servers = ["${NOMAD_SERVER_IP}:4647"]
export NOMAD_SERVER_IP=10.11.12.13
envsubst < configs/nomad/client.hcl.tmpl > configs/nomad/client.hcl
nomad agent -config=configs/nomad/client.hcl
# wire this as e.g.  just render-nomad-configs  so deploy = render then start
```

Notes:

- With NATS the whole URL (scheme+host+port) lives in `NATS_LEAF_URL`; you cannot keep the port literal and splice only the host into a quoted string.
- `nats-server -t` / `nomad fmt -check` PASS on the broken config — never rely on them alone.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Using the hardcoded constant as the env default | Set the .env.example default to the dev IP literal | Still bakes the dev-specific value into the template; a copied .env silently targets the dev host | Default must be a NEUTRAL placeholder, not the original literal |
| Inventing a new var name (NATS_HUB_HOST) | Introduced a brand-new env var name as suggested in the issue | Orphans existing .env.example entries and config comments already wired to NATS_SERVER_IP / NOMAD_SERVER_IP | Reuse names already declared in .env.example; but NATS needs a WHOLE-URL var, so add NATS_LEAF_URL |
| Reaching for a Nomad `sensitive` attribute | Tried to mark the server address with a Nomad `sensitive` attribute | No such attribute exists in Nomad | Use envsubst pre-rendering / Vault, not a non-existent attribute |
| Assuming env expansion works without testing the daemon | Relied on NATS docs + server.hcl precedent for quoted-string `$VAR` and `servers=[]` array interpolation | The forms were ASSUMED, not run; running the daemon disproved them | Run the daemon and observe the dial target before claiming verified |
| NATS substring `$VAR` in quoted URL | `url="nats+tls://$VAR:7422"` dials literal `"$VAR"` → `lookup $VAR: no such host` | NATS only expands a WHOLE-VALUE bare token, never a substring inside quotes | Put the full URL (scheme+host+port) in ONE var: `url = $NATS_LEAF_URL` |
| Trusting `nats-server -t` / `nomad fmt -check` | Relied on the validate flag returning "valid" | Syntax-only; returns valid for the broken config | Run the daemon and observe the dial target; add a negative-control test |
| Assuming Nomad `${ENV}` interpolates in agent HCL | Expected `${ENV}` / `${env(...)}` to expand in client.hcl | Nomad does not expand OS env in config files; advertise uses go-sockaddr `{{}}` (local-only) | Pre-render with envsubst before `nomad agent -config` |
| Treating existing `${NOMAD_ADVERTISE_ADDR}` as precedent | Cited server.hcl's advertise block as proof the form works | It is a latent bug read literally by Nomad, not proof of interpolation | Verify the mechanism per engine; don't generalize from an untested sibling config |

## Results & Parameters

Concrete before/after (corrected):

- **leaf.conf** url
  - BROKEN (prior plan): `url: "nats+tls://$NATS_SERVER_IP:7422"` → dials literal `"$NATS_SERVER_IP"`
  - WORKING: `url = $NATS_LEAF_URL` with `NATS_LEAF_URL=nats+tls://10.11.12.13:7422`
- **client.hcl** servers
  - NOT native: `servers = ["${NOMAD_SERVER_IP}:4647"]` is read LITERALLY by Nomad agent HCL
  - WORKING: keep that line in a `client.hcl.tmpl` and run `envsubst` to produce `client.hcl` before `nomad agent -config`
- **.env.example** placeholder pattern → `NATS_LEAF_URL=nats+tls://<your-server-tailscale-ip>:7422` (neutral, fails loud)

Exact log lines observed (nats-server v2.10.24, this host):

- WORKING whole-value: `[DBG] ... Trying to connect as leafnode to remote server on "10.11.12.13:7422"` followed by `dial tcp 10.11.12.13:7422`.
- BROKEN substring: `[ERR] ... lookup $NATS_SERVER_IP: no such host`.

Parameters:

- NATS leaf var: `NATS_LEAF_URL` = full `nats+tls://<host>:7422` URL (whole value, bare token).
- Nomad var: `NOMAD_SERVER_IP` consumed by `envsubst`, NOT by Nomad itself.

Verification status: NATS expansion is **daemon-verified-local** — proven by running `nats-server -c FILE -D` and observing the resolved dial target plus a negative control. Nomad is **doc-verified-only** — confirmed from developer.hashicorp.com/nomad/docs/configuration that agent HCL does not interpolate OS env (nomad not installed here, so not daemon-run). Overall level: `verified-local` (not `verified-ci`).
