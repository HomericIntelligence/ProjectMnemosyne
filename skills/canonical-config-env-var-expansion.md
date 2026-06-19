---
name: canonical-config-env-var-expansion
description: "De-hardcode developer-specific values (IPs, hostnames, paths) from CANONICAL config files (NATS .conf, Nomad HCL) that hosts copy or symlink, using the config engine's native env-var expansion instead of a templating preprocessor. Use when: (1) a canonical config file in configs/ contains a dev-specific literal like a Tailscale IP, (2) the file is deployed by copy/symlink (not launched by the repo's own justfile/CI), so no launcher can inject values, (3) you need to neutralize .env.example defaults to fail-loud placeholders."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Canonical Config Env-Var Expansion

## Overview

This skill captures a durable PLANNING learning derived from an implementation plan for Odysseus GitHub issue #181: a developer-specific Tailscale IP (`100.92.173.32`) was hardcoded in `configs/nats/leaf.conf` and `configs/nomad/client.hcl`. The plan proposes de-hardcoding it using each config engine's native env-var expansion rather than introducing a templating preprocessor.

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Objective | De-hardcode a dev-specific Tailscale IP from canonical NATS/Nomad config files deployed by copy/symlink |
| Outcome | Plan only, NOT executed — hypothesis |
| Verification | unverified |

## When to Use

- De-hardcoding developer-specific values (IPs, hostnames, paths) from CANONICAL config files that hosts copy or symlink (not files launched by the repo's own justfile/CI).
- You cannot rely on a launcher script to inject values — the deploy model is "copy file, export env var, start daemon".
- The same literal appears in MULTIPLE files (config + .env.example) and all must be fixed consistently.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps and `### Quick Reference` are emitted under that heading to keep validation green. This skill is a PLANNING learning captured at `unverified` level — read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

1. Prefer the config ENGINE's NATIVE env-var expansion over a templating preprocessor. NATS supports `$VAR` (and `${VAR}`) inside `.conf`; Nomad HCL supports `${VAR}` and `${env("VAR")}`. No `.tmpl` files or launcher script needed — this preserves the "copy file, export var, start daemon" model.
2. Reuse env-var names ALREADY declared in `.env.example` rather than inventing new ones. (The issue suggested `NATS_HUB_HOST`, but `NATS_SERVER_IP` and `NOMAD_SERVER_IP` already existed and were already documented as "used in configs/...". Renaming would orphan existing comments and `.env` entries.)
3. A hardcoded value typically recurs across MULTIPLE files — here the same IP was in `leaf.conf`, `client.hcl`, AND `.env.example`. Fix all occurrences.
4. `.env.example` defaults must be NEUTRAL placeholders (e.g. `<your-server-tailscale-ip>`), NEVER the dev literal, so a copied-but-unedited `.env` fails loudly instead of silently targeting the dev host.
5. Follow EXISTING in-repo precedent: `server.hcl` already used `${NOMAD_ADVERTISE_ADDR}`, which justifies the same `${VAR}` interpolation form in `client.hcl`.
6. Add a RUNTIME parse check before claiming verified: `nats-server -t -c leaf.conf` and a `nomad agent -dev` smoke test. Syntax-only checks (`nomad fmt -check`, `grep`, `just validate-configs`) do NOT prove the env var resolves at runtime or that the daemon connects.

### Quick Reference

Copy-paste before/after snippets:

- **leaf.conf** url
  - before: `url: "nats+tls://100.92.173.32:7422"`
  - after: `url: "nats+tls://$NATS_SERVER_IP:7422"`
- **client.hcl** servers
  - before: `servers = ["100.92.173.32:4647"]`
  - after: `servers = ["${NOMAD_SERVER_IP}:4647"]`
- **.env.example**
  - before: `NATS_SERVER_IP=100.92.173.32`
  - after: `NATS_SERVER_IP=<your-server-tailscale-ip>` (same for `NOMAD_SERVER_IP`)

Notes:

- Ports stay LITERAL (`7422` leaf, `4647` Nomad, `4222` client) — only the HOST is parameterized.
- Runtime checks: `nats-server -t -c configs/nats/leaf.conf` ; `nomad agent -dev -config=configs/nomad/client.hcl` smoke.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Using the hardcoded constant as the env default | Set the .env.example default to the dev IP literal | Still bakes the dev-specific value into the template; a copied .env silently targets the dev host | Default must be a NEUTRAL placeholder, not the original literal |
| Inventing a new var name (NATS_HUB_HOST) | Introduced a brand-new env var name as suggested in the issue | Orphans existing .env.example entries and config comments already wired to NATS_SERVER_IP / NOMAD_SERVER_IP | Reuse names ALREADY declared in .env.example |
| Reaching for a Nomad `sensitive` attribute | Tried to mark the server address with a Nomad `sensitive` attribute | No such attribute exists in Nomad | Use env interpolation `${VAR}` / Vault, per server.hcl precedent |
| Assuming env expansion works without testing the daemon | Relied on NATS docs + server.hcl precedent for quoted-string `$VAR` and `servers=[]` array interpolation | NATS quoted-string `$VAR` expansion and Nomad `servers` array `${VAR}` interpolation were ASSUMED, not run | Add a runtime parse check (`nats-server -t -c leaf.conf`, `nomad agent -dev` smoke) before claiming verified |

## Results & Parameters

Concrete before/after results:

- **leaf.conf** url → `url: "nats+tls://$NATS_SERVER_IP:7422"`
- **client.hcl** servers → `servers = ["${NOMAD_SERVER_IP}:4647"]`
- **.env.example** placeholder pattern → `<your-server-tailscale-ip>`

Parameters:

- Ports `7422` (leaf), `4647` (Nomad server RPC), and `4222` (NATS client) stay literal — only the host is parameterized.
- Env-var names: `NATS_SERVER_IP`, `NOMAD_SERVER_IP` (reused, already declared in `.env.example`).

Verification status: The plan's primary verification is syntactic/grep-based (`just validate-configs`), which is necessary but NOT sufficient — a green run does NOT prove the daemon connects or that the env var resolves at runtime. Treat as `unverified` until `nats-server -t -c leaf.conf` and a `nomad agent -dev` smoke test confirm runtime resolution.
