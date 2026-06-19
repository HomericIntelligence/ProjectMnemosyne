---
name: placeholder-config-deploy-render-footgun
description: "Fix-completeness / blast-radius discipline for de-hardcoding a value out of a CANONICAL config file when the config engine cannot interpolate it at startup, so the committed file must carry an UNRESOLVED placeholder (e.g. ${NOMAD_SERVER_IP}). The placeholder is a POLA footgun: any deployment path that consumes the committed file RAW feeds the literal ${...} to the daemon. The fix is NOT done until EVERY raw-consumption path (deployment docs, runbooks, disaster-recovery) renders the file first. Render to a DEPLOY-LOCAL dir (not back into configs/) so no rendered file enters the repo and no .gitignore band-aid is needed; keep ONE file that IS the template (placeholder + loud GENERATED header) rather than a separate .tmpl + resolved sibling; and add a doc-level grep gate plus a validate-configs placeholder guard. Use when: (1) a committed config in configs/ must keep an unresolved ${VAR}/<placeholder> because the engine cannot expand it at startup, (2) docs/runbooks bind-mount or -config the committed file directly, (3) you are choosing between one self-documenting template file vs a .tmpl + resolved sibling, (4) you want the fix to be enforced so it cannot silently regress in code OR docs."
category: architecture
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: verified-local
history: placeholder-config-deploy-render-footgun.history
tags: [config, placeholder, envsubst, render, nomad, nats, deployment-docs, runbook, blast-radius, pola, grep-gate, validate-configs, tailscale, planning]
---

# Placeholder Config Deploy-Render Footgun

## Overview

This skill captures a durable learning from re-planning Odysseus GitHub issue #181 (de-hardcode a developer-specific Tailscale IP from canonical NATS/Nomad configs). The companion skill [[canonical-config-env-var-expansion]] (PRs #2609, #2612) covers the ENGINE EXPANSION SEMANTICS — whether and how `$VAR`/`${VAR}` expands in NATS vs Nomad. THIS skill covers the next problem: once you've chosen a placeholder mechanism, making the deployment actually USE it. A committed config that carries an unresolved `${NOMAD_SERVER_IP}` is a Principle-of-Least-Astonishment footgun — any path that consumes the committed file RAW hands the literal `${...}` to the daemon. The reviewer NOGO'd two plans that fixed the config file but left deployment docs mounting/launching it raw.

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Objective | Make a de-hardcoding fix COMPLETE: every raw-consumption path (docs/runbooks/DR) renders the placeholder config before launch, the gap is designed out, and regression is gated |
| Outcome | Render-then-launch flow designed across all docs; grep gate + validate-configs guard specified; doc-render flow design-verified and grep-gated, NOT end-to-end deploy-tested (nomad not installed on this host) |
| Verification | verified-local (design-verified + grep-gated; NOT deploy-tested, NOT verified-ci) |

## When to Use

- A committed canonical config in `configs/` must keep an UNRESOLVED placeholder (e.g. `${NOMAD_SERVER_IP}`) because the config engine cannot interpolate it at startup (see [[canonical-config-env-var-expansion]] for which engines can/cannot).
- Deployment docs or runbooks bind-mount the committed file (`-v $(pwd)/configs/...:...`), `cp` it into a daemon config dir, or `daemon -config configs/...` it DIRECTLY — every such path is a raw-consumption footgun.
- You are deciding between one self-documenting template file (placeholder + loud `GENERATED` header) and a separate `.tmpl` plus a committed resolved `.hcl` sibling.
- You want the fix enforced so it cannot silently regress — in CODE (re-hardcoding the value) OR in DOCS (a runbook drifting back to a raw mount).

## Verified Workflow

> **Warning:** The doc-render flow here is DESIGN-VERIFIED and GREP-GATED, not end-to-end deploy-tested — nomad is not installed on this host, so the full `render → mount → nomad agent` path was reasoned through and mechanically gated, NOT run. The engine-expansion behavior it builds on was daemon-proven in prior rounds (see [[canonical-config-env-var-expansion]], PRs #2609/#2612). Treat the render gates as sound-by-construction; confirm in CI / on a host with nomad before claiming verified-ci.

1. **Treat the placeholder as a blast radius, not a one-line edit.** The moment a committed config carries `${NOMAD_SERVER_IP}` (because the engine cannot expand it), grep the WHOLE repo — docs, runbooks, disaster-recovery, compose files — for every path that consumes that file RAW. Fixing only the config is incomplete: a doc that bind-mounts or `-config`s the committed file feeds the literal `${...}` to the daemon.
2. **Switch EVERY raw-consumption path to render-then-launch.** In this repo the three offenders were: `docs/deployment.md` bind-mounted `$(pwd)/configs/nomad/server.hcl` into the container; `docs/runbooks/add-new-host.md` did `cp configs/nomad/client.hcl /etc/nomad.d/` plus a manual edit; `disaster-recovery.md` ran `nomad agent -config configs/nomad/server.hcl`. All must become "render first (`envsubst` → deploy-local dir), then mount/launch the RENDERED file."
3. **Render to a DEPLOY-LOCAL dir, never back into `configs/`.** Render to e.g. `/etc/nomad.d/` so NO rendered file (which would contain a real IP) can land in the repo tree. This designs the gap out entirely — no `.gitignore` rule is needed. Adding a gitignore rule to hide a rendered-into-`configs/` file is a band-aid; eliminating the possibility is the fix.
4. **Keep ONE file that IS the template.** Prefer the committed `.hcl`/`.conf` itself carrying the placeholder plus a loud header comment (`# GENERATED — render before use (just render-nomad-configs); do NOT launch this file raw`) over a separate `.tmpl` sibling next to a committed resolved `.hcl`. Two files invite editing/mounting the wrong one (the unrendered or a stale resolved copy); one file with a loud header is unambiguous.
5. **Guard against silent re-hardcoding** with a `validate-configs` check that asserts the placeholder is still present: `grep -q '${NOMAD_SERVER_IP}' configs/nomad/client.hcl || exit 1`. If someone re-bakes a literal IP, the placeholder disappears and the gate fails.
6. **Add a DOC-LEVEL grep gate** — docs drift is part of the fix surface and needs its own check, just like code. Assert every runbook renders before launch AND none still does `-config configs/nomad/*.hcl` raw (no raw bind-mount of `configs/nomad/*.hcl` either). Docs are not exempt from the regression gate.
7. **Shared render recipes require ALL vars for ALL templates they process — document the surprise at the call site.** When a single recipe (e.g. `render-nomad-configs`) renders multiple config files (both `client.hcl` and `server.hcl`), the recipe must satisfy the union of all variable requirements across every template. This means a client-only host must export server-only vars (e.g. `NOMAD_ADVERTISE_ADDR`) even though the client never uses the `advertise{}` block and the resulting `/etc/nomad.d/server.hcl` is unused on that host. The resolution is NOT to split the shared recipe into per-role recipes (that sacrifices simplicity). Instead, add a comment at the call site — the runbook export line — explaining why the operator must export a var that seems irrelevant to their role: e.g. `# NOMAD_ADVERTISE_ADDR is required by the shared render recipe (templates both client.hcl and server.hcl) even though a client-only host only uses client.hcl.`

### Quick Reference

`render-nomad-configs` just recipe (render to a deploy-local dir, NOT into `configs/`):

```just
# Render committed placeholder configs to a deploy-local dir (default /etc/nomad.d).
# OUT_DIR must be OUTSIDE the repo tree so no rendered file (real IP) is committable.
render-nomad-configs OUT_DIR="/etc/nomad.d":
    #!/usr/bin/env bash
    set -euo pipefail
    : "${NOMAD_SERVER_IP:?set NOMAD_SERVER_IP before rendering}"
    mkdir -p "{{OUT_DIR}}"
    for f in configs/nomad/*.hcl; do
        envsubst < "$f" > "{{OUT_DIR}}/$(basename "$f")"
    done
    echo "rendered configs/nomad/*.hcl -> {{OUT_DIR}} (launch the RENDERED files, not configs/)"
```

`validate-configs` placeholder guard (fails if the placeholder was re-hardcoded):

```bash
# Placeholder MUST still be present — its absence means someone baked a literal IP back in.
grep -q '${NOMAD_SERVER_IP}' configs/nomad/client.hcl || { echo "client.hcl lost its placeholder (re-hardcoded?)"; exit 1; }
grep -q '${NOMAD_SERVER_IP}' configs/nomad/server.hcl || { echo "server.hcl lost its placeholder (re-hardcoded?)"; exit 1; }
```

Doc-level grep gate (Criterion 6 — docs must render before launch, none raw):

```bash
# FAIL if any doc/runbook still launches or mounts a committed config RAW.
if grep -rEn 'nomad agent[^\n]*-config[[:space:]]+configs/nomad/' docs/; then
    echo "FAIL: a doc launches nomad against a RAW committed config; must render first"; exit 1
fi
if grep -rEn -- '-v[[:space:]]+[^[:space:]]*configs/nomad/[^[:space:]]+\.hcl' docs/; then
    echo "FAIL: a doc bind-mounts a RAW committed config; must mount the RENDERED file"; exit 1
fi
# Positive assertion: every runbook that launches nomad references the render step first.
for d in docs/deployment.md docs/runbooks/add-new-host.md docs/runbooks/disaster-recovery.md; do
    grep -q 'render-nomad-configs' "$d" || { echo "FAIL: $d does not render before launch"; exit 1; }
done
echo "PASS: all runbooks render before launch; no raw -config/-v of configs/nomad/*.hcl"
```

Loud header to put at the TOP of each committed placeholder config (one-file-is-the-template):

```hcl
# GENERATED CONFIG — render before use:  just render-nomad-configs
# This file intentionally carries the UNRESOLVED placeholder ${NOMAD_SERVER_IP}.
# Do NOT launch or bind-mount THIS file raw — Nomad reads ${...} literally.
servers = ["${NOMAD_SERVER_IP}:4647"]
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Commit resolved config | Committing a resolved `.hcl` with the dev IP | Other operators copy it and dial the wrong host | Commit a placeholder + render per host |
| Placeholder but raw docs | Committing `${VAR}` placeholder but leaving docs mounting the file raw | Operator follows docs verbatim → daemon gets literal `${VAR}` | Update every doc/runbook to render-then-launch |
| Render into `configs/` | Rendering back into `configs/` | Rendered file with a real IP can get committed; needs gitignore band-aid | Render to a deploy-local dir (/etc/nomad.d); gap designed out |
| Two-file template | Separate `.tmpl` + resolved `.hcl` sibling | Ambiguous which file to edit/mount; easy to mount the unrendered or stale one | One file = the template, loud GENERATED header, validate-configs placeholder guard |
| Grep only code | Only grepping code for the old IP | Docs/runbooks still carried the raw-mount path | Add a doc-level grep gate: every runbook renders before launch, none uses `-config configs/...` raw |
| Shared render recipe with unequal var requirements | A single `render-nomad-configs` recipe renders both `client.hcl` and `server.hcl`; client-only host operator confused by mandatory `export NOMAD_ADVERTISE_ADDR` which client never uses | Operator on client-only host sees a server-only var required at export time plus an unused `/etc/nomad.d/server.hcl` rendered by the recipe — POLA violation surfaced in PR review | Keep the shared recipe (simpler); add a comment at the call site (runbook) explaining that the shared recipe templates ALL files and requires the union of their vars, even vars the local role ignores |

## Results & Parameters

Concrete fix surface for Odysseus issue #181 (all three docs were raw-consumption offenders the reviewer NOGO'd):

- `docs/deployment.md` — bind-mounted `$(pwd)/configs/nomad/server.hcl` into the container → must mount the RENDERED file from the deploy-local dir instead.
- `docs/runbooks/add-new-host.md` — did `cp configs/nomad/client.hcl /etc/nomad.d/` plus a manual edit → must `just render-nomad-configs` to `/etc/nomad.d/` (no manual edit).
- `docs/runbooks/disaster-recovery.md` — ran `nomad agent -config configs/nomad/server.hcl` → must render first, then `nomad agent -config /etc/nomad.d/server.hcl`.

Design decisions (the durable part):

- Render OUTPUT goes to a DEPLOY-LOCAL dir (`/etc/nomad.d/`), NOT back into `configs/`. Consequence: no rendered file (with a real IP) can enter the repo, so NO `.gitignore` change is required. Designing the gap out beats a gitignore band-aid.
- ONE file is the template: the committed `client.hcl`/`server.hcl` carries the `${NOMAD_SERVER_IP}` placeholder + a loud `GENERATED — render before use` header. Reject the separate-`.tmpl`-plus-resolved-`.hcl` shape — it invites mounting the wrong (unrendered or stale) file.
- `validate-configs` placeholder guard prevents silent re-hardcoding: `grep -q '${NOMAD_SERVER_IP}' client.hcl || exit 1`.
- Doc-level grep gate (Criterion 6) treats docs drift as part of the fix surface: assert every runbook renders before launch and NONE does `-config configs/nomad/*.hcl` (or bind-mounts `configs/nomad/*.hcl`) raw.

Cross-link: once you've chosen the placeholder mechanism per [[canonical-config-env-var-expansion]] (which engine expands `$VAR` and how — proven by running the daemon, not `-t`), THIS skill makes the deployment actually use it end-to-end.

Verification status: `verified-local`. The render/grep/guard gates are mechanically sound and were reasoned through; the underlying engine-expansion behavior was daemon-proven in prior rounds (PRs #2609/#2612). The FULL `render → mount → nomad agent` deploy was NOT run here (nomad not installed). Doc-render flow is design-verified + grep-gated, NOT end-to-end deploy-tested. NOT `verified-ci`.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| Odysseus | Re-planning issue #181 round 3 (de-hardcode dev Tailscale IP from canonical NATS/Nomad configs); reviewer NOGO'd two plans for ignoring raw-consumption doc paths | Companion engine-semantics skill: [[canonical-config-env-var-expansion]] (PRs #2609, #2612) |
