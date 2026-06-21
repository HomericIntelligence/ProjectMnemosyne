---
name: homeric-crosshost-deployment-and-mesh-topology
description: "Deploy and operate the HomericIntelligence mesh across multiple Tailscale hosts using NATS JetStream, compose overlays, and justfile launchers. Use when: (1) splitting the E2E stack across multiple physical hosts via compose overlay or per-component launchers, (2) bringing up Agamemnon/Nestor/Hermes natively or via containers on any new Tailnet host from cold state, (3) running hub+remote-worker topology for cross-host myrmidon dispatch, (4) configuring NATS connections (direct or leafnode) over Tailscale, (5) implementing NATS JetStream publish retry with exponential backoff, (6) debugging Hermes webhook event types, compose healthchecks, or podman rootlessport/DNS quirks, (7) PLANNING credential-based authentication for a NATS leaf/server config and scrutinizing the uncertain assumptions a reviewer must verify in such a plan, (8) PLANNING Grafana anonymous-access hardening in the e2e compose stack (disable anonymous, fall back to admin login) and scrutinizing the unverified health-probe/provisioning assumptions a reviewer must confirm, (9) PLANNING a NATS TLS security runbook (cert provisioning via step-ca, zero-downtime cert rotation via SIGHUP, key-compromise response) for the canonical configs that now carry TLS per ADR-008, and scrutinizing the unverified step/nats-server/monitoring-API claims a reviewer must confirm, (10) PLANNING NATS client-cert mTLS wiring into ProjectTelemachy (config-layer `build_ssl_context()`/`nats_connect_kwargs()` because Telemachy has NO live `nats.connect()`), now with R1 (#304) verified-local facts: Hermes' `build_ssl_context()` is DEFINED-BUT-UNUSED at its connect site (no `tls=` kwarg), nats-py 2.14.0 `Client.connect` really accepts `tls`/`tls_hostname` (inspect `Client.connect`, NOT the `nats.connect` wrapper), `.gitignore` blocks committed PEM fixtures and no cert lib is installed so generate certs with the `openssl` binary into pytest `tmp_path`, and ADR-008 (not the cited ADR-009) is the real NATS TLS ADR; R2 (#304) adds the CONFIRMED `cli.py` insertion point (the `tls://` preflight goes INSIDE the existing `_run_with_signals()` async wrapper at `cli.py:141`, before the `async with AgamemnonClient(...)` at `cli.py:178` — do NOT add a second `asyncio.run`) and notes the R1 plan PASSED review; R3 (#304) RESOLVES the R2 review's two MINOR POLA findings (design/framing round, nothing newly executed): the preflight failure path now wraps `nats.connect(...)` and re-raises a typed `NatsConnectionError` (mirroring `AgamemnonError` at `agamemnon_client.py:13`) which the CLI catches and exits via `typer.Exit(1)` (no bare traceback out of `asyncio.run`), and the handshake-only preflight is framed as a DELIBERATE, DOCUMENTED, fail-closed verification gate (intent in docstring+CLI comment+CLAUDE.md+runbook) rather than a probe — plan now A/B-clean. (11) NATS e2e SIGKILL→restart fix in a MULTI-PROCESS test harness (Odysseus #328, VERIFIED-LOCAL IMPLEMENTATION — R3 round: unit test 15/15 green including 8/8 kill→restart→healthy loop; CI not yet confirmed). R2 MEASURED the core kernel mechanism locally and OVERTURNED the issue's hypothesis: the issue body asserts a monitor-port TIME_WAIT race (the `-m NATS_MONITOR_PORT` bind supposedly fails because the port lingers in TIME_WAIT after SIGKILL) and a prior reviewer escalated it into a load-bearing 'the ~15s bind-retry backoff cannot outlast Linux 2MSL ~60s' major. A tight kill→rebind experiment (start `nats-server -js -p 14299 -m 18299`, await `/healthz`, `kill -KILL`, IMMEDIATELY relaunch a fresh server on the SAME ports with NO port-free poll and NO sleep) gave 8/8 immediate rebinds, zero failures, zero delay — this finding is VERIFIED-LOCAL. The durable kernel fact: TIME_WAIT does NOT apply to a server's own LISTENING sockets — a SIGKILLed listener frees its port immediately; the 2MSL reservation only afflicts the endpoint that did an ACTIVE CLOSE of an ESTABLISHED connection (a client/peer socket, never the listener you rebind). So 'wait out 2MSL', 'free-poll the port', and 'SO_REUSEADDR to defeat TIME_WAIT' all solve a non-problem for this failure mode. The ACTUAL defect is a STALE-PROCESS RACE compounded by a process-boundary bug (R1): the kill targeted an EMPTY cross-process `_NATS_PID` shell global (because `_NATS_PID` is empty across the parent→child process boundary — `run-ipc-tests.sh:64` runs tests as `bash \"$script\"` which sources a fresh shell), so the original server stayed ALIVE and the relaunch raced a still-bound socket. R3 VERIFIED-LOCAL IMPLEMENTATION facts (unit test 15/15 confirmed): (a) `start_nats_bg` writes PID + store_dir to `/tmp/hi-nats-${NATS_MONITOR_PORT}.meta`; child processes read it via `nats_meta_pid()` / `nats_meta_store_dir()`; (b) `nats_kill()` SIGKILLs the meta-file PID then `wait`s for full exit (FD release) — `wait` on non-child returns 127; fall back to bounded `kill -0` poll (20× 0.1s) — this kill-then-wait is the CORRECTNESS gate; (c) `wait_port_free` must be wired into `nats_restart` at both call sites (after `nats_kill` before the loop AND after `nats_kill` inside each retry); (d) `wait_port_free` needs `timeout 1 bash -c \"...\"` guard because `/dev/tcp/localhost/PORT` HANGS (does not fail fast) on WSL2/some kernels; (e) skip blocks in unit tests need explicit `exit $?` — under `set -euo pipefail` `exit_code` only RETURNS a status, it does not terminate the script (pitfall: skip block falls through to the next section and fails on `start_nats_bg` when `nats-server` is absent); (f) A02 active path needs a meta-file guard: `[ -n \"$(nats_meta_pid)\" ]` before the kill+restart block, skip otherwise (prevents false-pass when running standalone — `nats_kill` no-ops and `nats_restart` falls back to mktemp store_dir → JetStream not preserved); (g) `start_nats_bg` must be split into `start_nats_bg` (fresh mktemp dir) + `start_nats_bg_at <dir>` (explicit dir AND writes meta file) — `nats_restart` calls `start_nats_bg_at` with the ORIGINAL store_dir so JetStream is preserved; (h) unit test loop variables are clobbered by inner functions — `wait_for` in common.sh has its own `for i in` that overwrites the outer `$i`; use unique loop variable (`_t5`) and a separate counter (`LOOP_ITER`); (i) `nats-crash-reconnect.sh` must `source process.sh` — it sources `nats.sh` (line 8) but `nats_kill`/`nats_restart`/`nats_meta_pid` live in `process.sh`. Files changed: `e2e/lib/process.sh` (meta-file helpers + `start_nats_bg_at` + `wait_port_free` + `nats_kill`/`nats_restart` + updated `cleanup_all`), `e2e/tests/fault/nats-crash-reconnect.sh` (add `source process.sh`, replace passive A02 with active kill+restart + meta-file guard + passive fallback), `e2e/tests/unit/test-nats-restart.sh` (NEW: 15-test unit covering the above). nats-server has NO SO_REUSEADDR/address-reuse flag (`nats-server --help`); `-sl/--signal` accepts only `ldm,stop,quit,term,reopen,reload` (none defeat TIME_WAIT, none needed); `-p`=client, `-m`=http monitor, `-ms`=https monitor. The NATS test helpers live in `e2e/lib/nats.sh` (`nats_health` nats.sh:12, `nats_wait_healthy` nats.sh:16, `nats_msg_count` nats.sh:27, `nats_stream_exists` nats.sh:99) — NOT in common.sh/process.sh; `nats-crash-reconnect.sh:8` already sources `nats.sh` so it needs `process.sh` ADDED. META-LESSON: when an issue body hands you a kernel/OS-timing root-cause hypothesis (TIME_WAIT, 2MSL, races), MEASURE it with a tight reproduction before architecting a fix around it — and before a reviewer escalates the hypothesis into a blocking 'your mechanism can't outlast X' major; a 10-line bash loop dissolved a load-bearing NOGO by proving the premise false. Distinguish LISTENING-socket teardown (immediate on SIGKILL) from ESTABLISHED-connection active-close (2MSL TIME_WAIT) — different sockets, different lifecycles."
category: architecture
date: 2026-06-20
version: "1.11.0"
user-invocable: false
verification: unverified
history: homeric-crosshost-deployment-and-mesh-topology.history
tags:
  - cross-host
  - deployment
  - compose
  - tailscale
  - nats
  - jetstream
  - podman
  - docker
  - distroless
  - healthcheck
  - justfile
  - per-component
  - launcher
  - mesh
  - hermes
  - agamemnon
  - nestor
  - myrmidon
  - atlas
  - cold-start
  - retry
  - backoff
  - e2e
  - cpp20
  - homeric-intelligence
  - auth
  - authorization
  - credentials
  - leafnode
  - leaf-conf
  - server-conf
  - security
  - planning
  - reviewer-risks
  - adr
  - grafana
  - anonymous-access
  - observability
  - hardening
  - tls
  - certificates
  - cert-rotation
  - step-ca
  - sighup
  - key-compromise
  - runbook
  - mtls
  - client-cert
  - telemachy
  - ssl-context
  - openssl
  - nats-py
  - gitignore
  - yagni
  - issue-304
  - e2e-fault-injection
  - sigkill
  - restart
  - port-bind-race
  - time-wait
  - wait-port-free
  - bind-retry
  - so-reuseaddr
  - process-sh
  - nats-port
  - nats-monitor-port
  - stale-issue-line-ref
  - issue-328
  - listening-socket
  - active-close
  - 2msl
  - kernel-networking
  - measure-before-design
  - sigkill-rebind
  - process-wait
  - stale-process-race
  - nats-restart-impl
  - meta-file
  - nats_kill
  - nats_restart
  - start_nats_bg_at
  - wait_port_free
  - wsl2-devtcp-timeout
  - exit-code-no-exit
  - false-pass-guard
  - loop-variable-clobber
---

# HomericIntelligence Cross-Host Deployment and Mesh Topology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Deploy and operate the HomericIntelligence mesh across multiple Tailscale hosts using NATS JetStream, compose overlays, justfile launchers, and resilient publish patterns; and plan credential-based authentication for the credential-less NATS leaf/server config |
| **Outcome** | Deployment patterns verified-local (two-host + 6-host). The NATS leaf/server auth fix is still an UNVERIFIED PLAN for issue #176 (R1, post-NOGO) — the full plan was not run end-to-end and no CI passed. BUT the config-block-presence validator was PROTOTYPED this session (verified-local: exit 0 on the fixed fixture, exit 1 on the repo's current configs). The Grafana anonymous-access hardening (issue #206) is an UNVERIFIED PLAN — no container was run; the load-bearing untested assumption is that Grafana's `/api/health` stays unauthenticated when anonymous access is disabled (so e2e health probes survive). The NATS TLS security RUNBOOK (issue #208 — cert provisioning, rotation, compromise response) is an UNVERIFIED PLAN — no commands run, no CI. The ProjectTelemachy NATS client-cert mTLS wiring (issue #304) is an UNVERIFIED PLAN overall (no CI) but R1 (post-NOGO) VERIFIED-LOCAL several facts the R0 round had only flagged as reviewer-risk: **(a)** Telemachy has NO live `nats.connect()` call (`_monitor_completion` HTTP-polls Agamemnon, it is not a NATS subscriber — re-confirmed); **(b)** Hermes does NOT consume `build_ssl_context()` at its connect site — `grep` shows ONLY the method DEFINITION at `config.py:126`, and `publisher.py:91-97` calls `nats.connect(...)` with NO `tls=` kwarg, so "wire it exactly as Hermes does" mirrors a connect site that DOES NOT EXIST (Hermes has the same latent gap); **(c)** nats-py **2.14.0** `nats.aio.client.Client.connect` really accepts `tls`, `tls_hostname`, and `tls_handshake_first` (inspect `Client.connect`, NOT the module-level `nats.connect` wrapper, which does not expose them); **(d)** the root + Telemachy `.gitignore` block committed `*.pem`/`*.key`/`*.crt` fixtures AND neither `cryptography` nor `trustme` is installed in the Telemachy pixi env — but the `openssl` binary IS on PATH (OpenSSL 3.6.2), so the working approach is to generate certs at test time into pytest `tmp_path`; **(e)** ADR-009 does NOT exist (only 001-008; ADR-008 IS the NATS TLS encryption ADR) and `docs/runbooks/enable-nats-auth.md` is ABSENT — both cited by the issue. Because a config-builder alone CANNOT satisfy AC1 ("Telemachy connects to NATS"), the honest fix is to ADD a minimal real consumed `nats_client.connect_nats()` (CLI `run` `tls://` preflight), not ship an unconsumed `nats_connect_kwargs()` helper (YAGNI, flagged in the NOGO). **IMPORTANT premise correction:** the #176-era claim that `configs/nats/*.conf` ship with NO TLS is now STALE — ADR-008 (Status: Proposed) is already merged into the configs, so both `server.conf` and `leaf.conf` now carry top-level `tls {}`, `leafnodes { port=7422; tls{} }`, and cluster TLS referencing `/etc/nats/certs/{server-cert.pem,server-key.pem,ca.pem}`, and leaf.conf's remote is now `nats+tls://<ip>:7422`. The plan's highest-value content remains its catalogue of uncertain assumptions a reviewer must verify, now sharpened by concrete NOGO causes and the stale-premise correction. **R2 increment (#304):** the R1 plan PASSED review (no new NOGO), and the `cli.py` preflight insertion point is now CONFIRMED — the `tls://` preflight (`nc = await connect_nats(settings); await nc.drain()`) goes INSIDE the existing `_run_with_signals()` async wrapper (`cli.py:141`, already used by the `run` command at `cli.py:120` with SIGINT/SIGTERM handlers + a Rich `Progress` context), AFTER the signal handlers are installed and BEFORE the `async with AgamemnonClient(...)` block (`cli.py:178`); do NOT add a second `asyncio.run` or block at import time. **R3 increment (#304):** the R2 plan got a narrow B/NOGO with ONLY two MINOR POLA findings; this design/framing round RESOLVES both inside the plan body (nothing newly executed). **(1)** Preflight failure handling: `connect_nats()` wraps `nats.connect(...)` in `try/except Exception` and re-raises a typed `NatsConnectionError` (mirroring the existing `AgamemnonError` at `agamemnon_client.py:13`) with an operator-guiding message ("confirm TLS_CERT_FILE/TLS_KEY_FILE/TLS_CA_BUNDLE are set and the cert is CA-signed"); the CLI `run` preflight catches `NatsConnectionError`, prints a red `console` line, and exits via `typer.Exit(1)` (matching the existing failure style at `cli.py:68-80`) — so a raw `ssl.SSLError`/`nats.errors.*` never escapes `asyncio.run()` as a bare traceback. **(2)** "Handshake-only preflight = connects" is RESOLVED by framing the connection as a DELIBERATE, DOCUMENTED, fail-closed verification gate: intent stated in the helper docstring, the CLI comment, the CLAUDE.md env-var row, AND the runbook; named as the single real connection site future data paths reuse; hard-failing (non-zero exit) on rejection so it complements the existing pre-connection `require_tls` gate at `agamemnon_client.py`. Both resolutions are decisions stated in-plan, not new investigation — a minors-only NOGO is closable that way. |
| **Verification** | unverified OVERALL for the NATS auth-planning section (the full plan was not exercised end-to-end); the brace-depth config-block validator specifically is verified-local (prototyped 2026-06-19 against fixed + current fixtures). The Grafana anonymous-access hardening subsection is unverified (no container run; `/api/health`-unaffected claim untested). The NATS TLS security-runbook section (issue #208) is unverified (no commands run; `step` CLI flags, NATS SIGHUP cert hot-reload, and the `/varz` `tls_required` field name were all written from memory). The Telemachy mTLS-wiring section (issue #304) is unverified OVERALL (no CI), but R1 (post-NOGO) CONVERTED the prior round's assumed-by-analogy claims into VERIFIED-LOCAL facts this session: the nats-py `tls=`/`tls_hostname` kwargs are confirmed on `nats.aio.client.Client.connect` for the installed **nats-py 2.14.0** (via `inspect.signature`); Hermes' `build_ssl_context()` is confirmed DEFINED-BUT-UNUSED at its connect site (`publisher.py:91-97` passes NO `tls=`); `cryptography`/`trustme` are confirmed ABSENT from the Telemachy pixi env while the `openssl` binary (3.6.2) IS present; and `.gitignore` is confirmed to block `*.pem`/`*.key`/`*.crt`. Still verified this round: the ABSENCE of a live `nats.connect()`, of ADR-009 (ADR-008 is the TLS ADR), and of `enable-nats-auth.md`. The exception: the `.gitignore` cert-key coverage claim (`*.pem`/`*.key`/`*.crt`/`secrets/`/`*.secret`) was actually grepped from the file this session and is TRUE. R2 (#304) adds one verified-local detail: the `cli.py` structure (the `run` command at `:120` wraps execution in `_run_with_signals()` at `:141`, which opens `async with AgamemnonClient(...)` at `:178`) was read this session, confirming the preflight insertion point; the R1 plan also PASSED review (no NOGO). R3 (#304) added NOTHING newly executed — it is a design/framing round that RESOLVED R2's two minor POLA findings by specifying behavior (the typed `NatsConnectionError` + `typer.Exit(1)` failure path) and re-framing a judgment call (the handshake preflight as a documented fail-closed verification gate) inside the plan; no CI ran and no new external claims were made. Verified-local for all prior deployment content (Odysseus sessions 2026-04-03 to 2026-05-03). The NATS e2e SIGKILL→restart section (Odysseus #328) is **VERIFIED-LOCAL (R3 implementation — unit test 15/15, 8/8 kill→restart→healthy loop; CI not yet confirmed)**. R2 confirmed via experiment that TIME_WAIT does NOT apply to a server's own LISTENING sockets (8/8 immediate rebinds after SIGKILL, NO port-free poll needed). R3 implemented and confirmed the full fix: `start_nats_bg` writes PID + store_dir to `/tmp/hi-nats-${NATS_MONITOR_PORT}.meta`; `nats_meta_pid()` / `nats_meta_store_dir()` read it cross-process; `nats_kill()` SIGKILLs the meta-file PID and `wait`s for full exit (the correctness gate — `wait` on non-child returns 127, falls back to bounded `kill -0` poll 20× 0.1s); `wait_port_free` wired into `nats_restart` at both call sites with `timeout 1` guard (WSL2 `/dev/tcp` hangs without it); skip blocks use explicit `exit $?` under `set -euo pipefail`; A02 has meta-file guard to prevent false-pass when running standalone; `start_nats_bg` split into `start_nats_bg` + `start_nats_bg_at <dir>` for JetStream continuity; unit test uses unique loop variable `_t5` + `LOOP_ITER` counter to avoid clobbering by inner `wait_for` loops; `nats-crash-reconnect.sh` sources `process.sh`. Files changed: `e2e/lib/process.sh`, `e2e/tests/fault/nats-crash-reconnect.sh`, `e2e/tests/unit/test-nats-restart.sh` (NEW). Remaining uncertain: CI has not confirmed (verified-local only); `pixi run bash`/`pixi run shellcheck` wiring unconfirmed; parent PR #184 merge-conflict risk. META-LESSON: when an issue body hands you a kernel/OS-timing hypothesis, MEASURE it with a tight reproduction before architecting a fix around it; a 10-line bash loop dissolved a load-bearing NOGO major by proving the premise false. |
| **History** | [changelog](./homeric-crosshost-deployment-and-mesh-topology.history) |

## When to Use

- Splitting the HomericIntelligence E2E compose stack across multiple physical machines
- Configuring NATS connections (direct or leafnode) over Tailscale mesh networking
- Bringing up Agamemnon, Nestor, or Hermes natively (binary/uvicorn) or via podman on any Tailnet host from cold state
- Launching myrmidon Python workers across Tailnet hosts (fan-out or hub+remote-worker pattern)
- Adding justfile recipes that launch C++ binaries or delegate to submodule justfiles
- Choosing between compose overlay vs native binary vs per-component launcher deployment
- Implementing NATS JetStream publish retry with exponential backoff and jitter in Python
- Debugging cross-host service communication, NATS leafnode config, or podman networking issues
- Planning credential-based authentication for the canonical credential-less `configs/nats/leaf.conf` + `server.conf` (issue #176) and reviewing such a plan for unverified assumptions
- Planning Grafana anonymous-access hardening in `docker-compose.e2e.yml` (issue #206) — disabling `GF_AUTH_ANONYMOUS_ENABLED`, falling back to admin login, and reviewing the unverified `/api/health` / provisioning assumptions
- Planning a NATS TLS security runbook (issue #208) — cert provisioning (step-ca), zero-downtime cert rotation (SIGHUP), and key-compromise response — against the canonical configs that NOW carry TLS per ADR-008, and reviewing the unverified `step`/`nats-server`/`/varz` claims
- Planning NATS client-cert mTLS wiring into ProjectTelemachy (issue #304) — config-layer helpers because Telemachy has NO live `nats.connect()` site — now with R1 (post-NOGO) verified-local facts: Hermes' `build_ssl_context()` is DEFINED-BUT-UNUSED at its connect site (no `tls=` kwarg — the "exactly as Hermes does" analogy mirrors a site that does not exist); nats-py 2.14.0 `Client.connect` accepts `tls`/`tls_hostname` (inspect `Client.connect`, NOT the `nats.connect` wrapper); generate test certs with the `openssl` binary into pytest `tmp_path` because `.gitignore` blocks PEM fixtures and no cert lib is installed; ADR-008 (not the cited ADR-009) is the real NATS TLS ADR; and a config-builder alone cannot meet AC1 — add a minimal real consumed `connect_nats()` rather than an unconsumed helper (YAGNI)
- Understanding the NATS e2e SIGKILL→restart fix implementation in a MULTI-PROCESS test harness (Odysseus #328, VERIFIED-LOCAL R3 — unit test 15/15, 8/8 kill→restart→healthy loop): the fix uses a port-keyed meta file (`/tmp/hi-nats-${NATS_MONITOR_PORT}.meta`) for cross-process PID tracking; `nats_kill` SIGKILLs then `wait`s for exit (the correctness gate); `wait_port_free` uses `timeout 1` guard (WSL2 `/dev/tcp` hangon closed port); skip blocks need `exit $?` under `set -euo pipefail`; A02 has meta-file guard to prevent false-pass; `start_nats_bg` split into `start_nats_bg` + `start_nats_bg_at <dir>` for JetStream continuity; unit test uses unique loop variable to avoid clobbering. TIME_WAIT does NOT apply to a server's own LISTENING socket (8/8 immediate rebinds after SIGKILL, VERIFIED). Whenever an issue hands you a kernel/OS-timing root cause (TIME_WAIT, 2MSL, races), MEASURE it with a tight reproduction before designing around it. See the "Proposed Workflow — NATS e2e SIGKILL→restart port-bind-race fix" section below

## Verified Workflow

### Quick Reference

```bash
# Compose overlay — start worker host
CONTROL_HOST_IP=<control-tailscale-ip> just crosshost-up $CONTROL_HOST_IP

# Compose overlay — start control host (Nestor native binary)
NATS_URL=nats://<worker-ip>:4222 <build-root>/ProjectNestor/ProjectNestor_server

# Per-component launchers (any host, any service)
just install-worker                                   # Worker: podman + tools
just install-control                                  # Control: C++ build chain + compile
just start-nats
just start-agamemnon NATS_URL=nats://worker-ip:4222
just start-nestor    NATS_URL=nats://worker-ip:4222
just start-hermes    NATS_URL=nats://worker-ip:4222
just start-myrmidon  NATS_URL=nats://worker-ip:4222 AGAMEMNON_URL=http://worker-ip:8080
just start-argus
just start-console   NATS_URL=nats://worker-ip:4222

# Hub+remote-worker topology (hermes=hub, epimetheus=remote worker)
just hermes-hub-up && just hermes-hub-test

# Single-host full E2E stack
podman compose -f docker-compose.e2e.yml up -d --build
just e2e-test

# Cross-host E2E validation (8 phases)
WORKER_HOST_IP=<worker-ip> just crosshost-test $WORKER_HOST_IP

# Verify NATS health
curl http://localhost:8222/varz    # monitoring (NOT port 4222)
curl http://localhost:8222/connz   # active connections
```

### Critical Binary Names and Paths

```
CORRECT:  control/ProjectAgamemnon/build/debug/ProjectAgamemnon_server
WRONG:    control/ProjectAgamemnon/build/debug/agamemnon

CORRECT:  control/ProjectNestor/build/debug/ProjectNestor_server
WRONG:    control/ProjectNestor/build/debug/nestor

CORRECT:  PYTHONPATH=src uvicorn hermes.server:app
WRONG:    uvicorn hermes.server:app     (no PYTHONPATH — module not found)
WRONG:    uvicorn hermes.main:app       (module does not exist)

CORRECT:  ~/.local/bin/nats-server -js  (use full path — not in PATH by default)
WRONG:    nats-server -js               (bare name, command not found on most hosts)

NATS:     port 4222 = client pub/sub;  port 8222 = HTTP monitoring
```

### Native Mesh Bringup (single host, pixi available)

```bash
# 1. NATS (binary NOT in PATH — use full path)
~/.local/bin/nats-server -js &

# 2. Agamemnon — build inside pixi for correct conda toolchain
pixi run bash -c "
  cd control/ProjectAgamemnon
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug \
    -DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF
  cmake --build build/debug
  ./build/debug/ProjectAgamemnon_server &
"

# 3. Nestor
pixi run bash -c "
  cd control/ProjectNestor
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug
  cmake --build build/debug
  ./build/debug/ProjectNestor_server &
"

# 4. Hermes — src layout requires PYTHONPATH
cd infrastructure/ProjectHermes
pixi run bash -c "PYTHONPATH=src uvicorn hermes.server:app --host 0.0.0.0 --port 8085" &

# 5. Verify
curl -s http://localhost:8080/health    # {"service":"ProjectAgamemnon","status":"ok"}
curl -s http://localhost:8081/v1/health
curl -s http://localhost:8085/health
curl -s http://localhost:8222/varz | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('connections:', d['connections'])"
```

### Multi-Host Cold-Start Strategy (up to 6 Tailnet Hosts)

| Host | Odysseus Present | Strategy | Special Notes |
| ------ | ---------------- | -------- | ------------- |
| titan, aeolus, athena | No | `gh repo clone` + podman containers | Agamemnon build ~5-10 min (Conan C++ deps) |
| artemis | Yes, pixi available | Native build inside `pixi run bash -c "..."` | Must use `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` |
| hephaestus | No | Clone fresh, native build | Nestor needs `-DCMAKE_EXE_LINKER_FLAGS='-lz'` |
| apollo | No | Python 3.7 — too old for Hermes | Use `docker run --network=host` for all services |

**Pre-check**: `ls ~/<project-root>` — clone via `gh repo clone` if missing.

```bash
# Podman container build (hosts without native toolchain)
gh repo clone HomericIntelligence/Odysseus ~/<project-root>
cd ~/<project-root> && git submodule update --init --recursive
podman build -t agamemnon control/ProjectAgamemnon/
podman run -d --name agamemnon --network=host agamemnon
```

**Hermes Dockerfile**: requires `prometheus_client` in pip install; use `HERMES_PORT=8085` (not 8080 — conflicts with Agamemnon). Fixed in PR #415.

### Compose Overlay Pattern for Cross-Host Splits

```yaml
# docker-compose.crosshost.yml (overlay on docker-compose.e2e.yml)
services:
  nestor:
    profiles: ["disabled"]     # runs on control host as native binary
  argus-exporter:
    environment:
      - NESTOR_URL=http://${CONTROL_HOST_IP}:8081
```

```bash
podman compose -f docker-compose.e2e.yml -f docker-compose.crosshost.yml up -d
```

**Disable-via-overlay pattern**: `profiles: ["disabled"]` is the correct way to exclude a service from an overlay without removing it from the base compose file.

### NATS Connection Strategy: Direct vs. Leaf Node

| Topology | Recommended | Reason |
| ---------- | ------------- | -------- |
| 2 hosts, 1 remote client | Direct connection | Zero additional complexity; Tailscale handles routing |
| 2+ hosts, multiple remote clients | Leaf node | Reduces WAN connections; local pub/sub for co-located services |
| Hub-and-spoke (many remotes) | Leaf nodes per spoke | Each spoke gets local NATS; leaf auto-reconnects |

**Leafnode config — critical**: leaf.conf must connect to port **7422** (leafnode listen port), **NOT** port 4222 (client port).

```hcl
# server.conf (hub)
leafnodes { port = 7422 }

# leaf.conf (spoke)
leafnodes {
  remotes [{ url: "nats-leaf://<hub-ip>:7422" }]
}
```

## Proposed Workflow — Planning NATS Leaf/Server Auth (UNVERIFIED, issue #176)

> **Warning:** This section is an UNVERIFIED PLAN. No code was run, no CI passed,
> and the NATS version behaviors below were not exercised. Treat every step as a
> hypothesis until CI confirms. The highest-value content here is the
> reviewer-risk catalogue in **Results & Parameters** — read it before trusting any step.

The canonical `configs/nats/leaf.conf` and `configs/nats/server.conf` ship with NO
authentication: the `leafnodes {}` listener accepts anonymous leaf connections, so any
host that can reach port 7422 can join the mesh and relay traffic. This is the plan for
closing that hole. `configs/` is canonical — fixing it propagates to every host that
copies the config.

> **STALE-PREMISE CORRECTION (2026-06-20, issue #208):** The "ship with NO TLS / NO auth"
> premise above is the #176-era state and has DRIFTED. ADR-008 ("Require TLS for All NATS
> Inter-Service Communication", Status: Proposed) is now MERGED into the configs: both
> `server.conf` and `leaf.conf` carry top-level `tls {}` blocks, `leafnodes { port=7422;
> tls{} }`, and cluster TLS, all referencing `/etc/nats/certs/{server-cert.pem,
> server-key.pem,ca.pem}`; leaf.conf's remote is now `nats+tls://<ip>:7422`. The auth
> (credential) gap may still exist, but the **TLS gap is closed**. LESSON: re-read the
> canonical configs every session before asserting their security posture — a documented
> gap may already be closed by a later ADR/PR. See the **NATS TLS Security Runbook** section
> and its reviewer-risk catalogue below for the full #208 plan.

### Proposed Steps

1. **Add `authorization {}` to BOTH the client listener AND the `leafnodes {}` listener
   in `server.conf`.** A leafnode listener without its own authorization stays open even
   if the client listener is authed — they are independent. Do not assume top-level
   `authorization {}` covers the leafnode listener.
2. **Add a credential to each `leaf.conf` `remotes` entry.** Prefer
   `credentials = ".../leaf.creds"` (NKey/JWT, per-leaf, individually revocable). A
   `token = "$NATS_LEAF_TOKEN"` is an acceptable bootstrap fallback only. **Keep the URL
   on port 7422 — never 4222** (4222 is the client port; leaf remotes pointed at 4222
   silently fail to connect).
3. **Reference secrets via NATS env substitution** (`$NATS_LEAF_TOKEN`), mirroring the
   existing `$NATS_MONITORING_PASSWORD` pattern already in the configs. Never commit
   secret values.
4. **Treat `configs/` as canonical** — the fix lands once and propagates to every host
   that copies or symlinks the config.
5. **Enforce with a fail-closed lint wired into the EXISTING runner/CI gate.** This repo
   is `just` / `pixi`, **NOT** pytest. Add a shell validator invoked by
   `just validate-configs` (which CI must call). The gate **must strip comments before
   grepping** so a commented-out example does not satisfy the check, and it must assert
   per-block (the leafnode block has its own authorization) rather than file-wide.
6. **Auth is a NEW architectural decision → write a NEW append-only ADR (ADR-009).**
   Never edit an accepted ADR.

```hcl
# server.conf — PROPOSED (both listeners authed)
authorization {
  user = "$NATS_CLIENT_USER"
  password = "$NATS_CLIENT_PASSWORD"
}
leafnodes {
  port = 7422
  authorization {                 # leafnode listener needs its OWN block
    token = "$NATS_LEAF_TOKEN"     # or per-leaf user/account + .creds
  }
  tls { ... }                     # NOTE: nested block — see awk-parser risk below
}
```

```hcl
# leaf.conf — PROPOSED (authed remote, still port 7422)
leafnodes {
  remotes [
    {
      url: "nats-leaf://<hub-ip>:7422"
      credentials: "/etc/nats/creds/leaf.creds"   # preferred; revocable per-leaf
      # token: "$NATS_LEAF_TOKEN"                  # bootstrap fallback only
    }
  ]
}
```

### Canonical Config-Block-Presence Check — Brace-Depth Validator (verified-local, R1)

**This is the validated heart of the R1 plan.** The NOGO killed the first plan because its
validator stopped at the first `}` — which closes the nested `tls {}`, not the `leafnodes {}`
block. A config-block validator MUST track brace DEPTH (count `{` vs `}`), never stop at the
first close brace. Prototyped this session: exit 0 on the fixed fixture, exit 1 on the repo's
current (unauthed) `configs/nats/server.conf`.

```bash
#!/usr/bin/env bash
# validate-configs (wired into `just validate-configs`; CI must invoke it explicitly).
# Extract a named brace-block by DEPTH, stripping comments first, then assert auth inside it.
set -euo pipefail

# block FILE BLOCKNAME -> prints the contents of the first top-level BLOCKNAME { ... },
# tracking nested braces by depth so nested tls{}/jetstream{} do NOT close it early.
block() {
  local file="$1" name="$2"
  sed 's/#.*//' "$file" | awk -v blk="$name" '
    $0 ~ blk"[[:space:]]*\\{" && depth==0 { inblk=1 }
    inblk {
      n=gsub(/\{/,"{"); m=gsub(/\}/,"}");
      depth += n - m;
      print;
      if (depth<=0 && started) { inblk=0 }
      if (n>0) started=1
    }
  '
}

# Assert the leafnodes{} listener carries its OWN authorization{} (per-block, not file-wide).
if ! block configs/nats/server.conf leafnodes | grep -q 'authorization'; then
  echo "FAIL: server.conf leafnodes{} listener has no authorization{} block" >&2
  exit 1
fi
echo "OK: leafnodes listener is authenticated"
```

Verification discipline that makes this gate real (all learned from the NOGO):

```bash
# Assert BOTH directions — a validator that always exits 1 "passes" the bad-case check
# for the WRONG reason and silently rejects the FIX too.
./validate-configs                 # MUST exit 0 on the fixed config
git stash && ! ./validate-configs  # MUST exit 1 on the unfixed config
git stash pop

# Fail-closed must be TESTED, not asserted: render the config with the token UNSET and
# grep for the leaked literal. Install a pinned nats-server in CI and run it unconditionally
# — never gate the check on `command -v nats-server` (that turns it into a silent no-op).
NATS_LEAF_TOKEN= nats-server -t -c configs/nats/server.conf 2>&1 \
  | grep -q '\$NATS_LEAF_TOKEN' && { echo "FAIL: unset token leaked as literal"; exit 1; }
```

### Agamemnon API Shape (Confirmed)

```bash
# Health
curl -s http://localhost:8080/health
# Returns: {"service":"ProjectAgamemnon","status":"ok"}

# Create team — response wraps ID under .team.id
TEAM_ID=$(curl -s -X POST http://localhost:8080/v1/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"my-team","description":"..."}' \
  | jq -r '.team.id')   # NOT .id

# Create task — team-scoped path (NOT /v1/tasks)
curl -s -X POST "http://localhost:8080/v1/teams/$TEAM_ID/tasks" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-task","type":"echo","params":{}}'

# Complete task — echo tasks require external PATCH (no autonomous executor)
curl -s -X PATCH "http://localhost:8080/v1/teams/$TEAM_ID/tasks/<task_id>" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}'
```

### Multi-Host Myrmidon Fan-Out

```bash
# On each reachable remote host — always use main.py (Python), NOT main.cpp
NATS_URL=nats://<controller-tailscale-ip>:4222 \
  nohup python3 provisioning/Myrmidons/hello-world/main.py \
  > /tmp/hello-myrmidon.log 2>&1 &

# Verify cross-host NATS connection count
curl -s http://<hub-ip>:8222/varz | jq .connections
```

### NATS JetStream Publish Retry with Exponential Backoff

```python
import asyncio, json, random, time, nats

_RETRYABLE_PUBLISH_ERRORS = (
    nats.errors.TimeoutError,
    nats.errors.NoRespondersError,
    nats.errors.DrainTimeoutError,
    nats.errors.ConnectionReconnectingError,
    nats.errors.StaleConnectionError,
)

async def publish_with_retry(js, subject, message, retries=3, base_delay=0.1, timeout=5.0):
    last_exc = None
    for attempt in range(retries):
        try:
            return await js.publish(subject, message, timeout=timeout)
        except _RETRYABLE_PUBLISH_ERRORS as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = min(base_delay * (2 ** attempt), 2.0) * random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
    raise last_exc
```

Retry budget defaults (`retries=3`, `base_delay=0.1s`, `timeout=5.0s`): ~15.3s worst case.
Non-retryable errors (`AuthorizationError`, `BadSubjectError`, generic `Exception`) propagate immediately.

### Host-Network Workaround (rootlessport absent)

```bash
# SYMPTOM: start-stack.sh hangs at `podman wait --condition=healthy`
# ROOT CAUSE: rootlessport absent — bridge networking never binds host ports
kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true
podman run -d --name hi-nats --network=host nats:alpine -js -m 8222
# When using --network=host, Grafana datasources must use localhost, not service names
```

**Grafana on air-gapped hosts** — add to grafana service to prevent startup hang:

```yaml
environment:
  - GF_ANALYTICS_REPORTING_ENABLED=false
  - GF_ANALYTICS_CHECK_FOR_UPDATES=false
  - GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false
```

#### Grafana anonymous-access hardening (planning learning, UNVERIFIED, issue #206)

> **Warning:** This subsection is an UNVERIFIED PLAN. No container was run this
> session. The load-bearing untested assumption is that Grafana's `/api/health`
> endpoint stays unauthenticated when anonymous access is disabled — so the e2e
> health probes keep working. Treat every claim as a hypothesis until a runtime
> `up -d grafana` + curl confirms it. Re-grep all cited line numbers before
> editing; they drift.

The Odysseus e2e compose stack ships Grafana with anonymous viewer access enabled.
To CLOSE that (issue #206 asks to *disable*, not downgrade to a lower role):

```yaml
# docker-compose.e2e.yml — grafana service environment (PROPOSED)
environment:
  - GF_AUTH_ANONYMOUS_ENABLED=false                     # disable anonymous access
  # REMOVE GF_AUTH_ANONYMOUS_ORG_ROLE entirely — it is DEAD config once anon is off
  # With anon off, Grafana falls back to login → MUST supply an admin credential:
  - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
```

**Pattern rules (reusable across HomericIntelligence compose stacks):**

1. To disable anonymous access set `GF_AUTH_ANONYMOUS_ENABLED: "false"` AND **remove**
   `GF_AUTH_ANONYMOUS_ORG_ROLE` — once anonymous is off the role var is dead config and
   leaving it invites a reviewer to think anonymous is merely downgraded, not disabled.
2. With anonymous off Grafana falls back to its login screen, so the stack MUST provide an
   admin credential. Use env-overridable defaults
   (`${GRAFANA_ADMIN_USER:-admin}` / `${GRAFANA_ADMIN_PASSWORD:-admin}`) to keep the e2e
   stack one-command. The `admin/admin` default is a DELIBERATE trade-off — name it
   explicitly so a reviewer can object; it is overridable via env, but the bootstrap default
   can silently become the permanent posture (same shape as the NATS shared-token risk above).
3. **KEY UNVERIFIED ASSUMPTION (highest reviewer risk):** Grafana's `/api/health` is
   unauthenticated REGARDLESS of anonymous-access settings, so disabling anon does NOT break
   the e2e health probes (`e2e/run-hello-world.sh`, `run-crosshost-e2e.sh`,
   `run-hermes-hub-e2e.sh`, `e2e/doctor.sh` all curl `:3001/api/health`). This was asserted
   from Grafana docs knowledge, NOT verified in-session. A reviewer/implementer MUST confirm
   at runtime that `/api/health` still returns `database=ok` with anon disabled.
4. **SECOND UNVERIFIED ASSUMPTION:** dashboards/datasources are file-provisioned via read-only
   volume mounts (`/etc/grafana/provisioning`), so they do NOT depend on the anonymous API and
   survive the change. Confirm provisioning still loads after login is required.

**Scoping (and its risk):** the plan changes ONLY `docker-compose.e2e.yml` at the Odysseus
root. Evidence: the overlays (`docker-compose.crosshost.yml`, `e2e/docker-compose.*.yml`)
define no grafana service; `build/.worktrees/*` are throwaway; ProjectArgus/ProjectKeystone are
separate submodules out of scope (sibling `provisioning/ProjectKeystone/k8s/grafana.yaml` is a
different deployment surface). The issue names `docker-compose.e2e.yml` at the Odysseus root.
**Reviewer risk:** confirm no other CANONICAL compose file in the Odysseus root re-enables
anonymous Grafana, and that the per-issue submodule boundary is correct.

**Verification discipline — structural compose validation is NOT runtime validation:**

```bash
# compose config passing proves SYNTAX ONLY — it never starts Grafana or probes health.
podman compose -f docker-compose.e2e.yml config >/dev/null   # syntax only — NOT proof

# The load-bearing claim (health probe still green with anon off) needs an ACTUAL run:
podman compose -f docker-compose.e2e.yml up -d grafana
curl -s http://localhost:3001/api/health    # MUST still return {"database":"ok",...}
# And confirm provisioning survived login-required mode (datasources/dashboards present).
```

Cited line numbers seen once this session (may have drifted — re-grep before editing):
`docker-compose.e2e.yml:154-155` (`GF_AUTH_ANONYMOUS_ENABLED`), `:153-159` (anon block),
`:160-162` (admin creds region), sibling `provisioning/ProjectKeystone/k8s/grafana.yaml:95,100-101`,
`docs/e2e-walkthrough-report.md:290`.

## Proposed Workflow — NATS TLS Security Runbook (UNVERIFIED, issue #208)

> **Warning:** This section is an UNVERIFIED PLAN. No commands were run, no CI passed.
> The `step` CLI flags, the NATS SIGHUP cert hot-reload behavior, and the `/varz`
> `tls_required` field name below were ALL written from memory, NOT exercised. Treat every
> command as a reviewer-must-verify hypothesis. The highest-value content is the
> reviewer-risk catalogue in **Results & Parameters** — read it before trusting any step.

Issue #208 (§9) reported there is no runbook for NATS authentication setup or certificate
rotation. The plan adds `docs/runbooks/nats-security.md` (TLS cert provisioning, rotation,
compromise response) plus one row in `docs/README.md`'s runbook index. This is the
operational-runbook complement to the #176 NATS-auth planning above.

**Premise the whole plan rests on (CORRECTED):** the canonical configs are NO LONGER
credential-less for TLS. ADR-008 (Status: **Proposed**) already added full TLS to both
`server.conf` and `leaf.conf`: top-level `tls {}`, `leafnodes { port=7422; tls{} }`,
cluster TLS — all referencing `/etc/nats/certs/{server-cert.pem,server-key.pem,ca.pem}`,
with the leaf remote now `nats+tls://<ip>:7422`. The runbook OPERATIONALIZES this existing
TLS config; it does not introduce it.

### Proposed Steps (cert lifecycle)

1. **Provision certs with `step-ca`** (`/etc/nats/certs/`), matching ADR-008's path
   convention. Permissions: private key `600`, cert + CA `644`. **`step` flags below are
   UNVERIFIED — `step ca init` flags in particular vary by version:**

   ```bash
   # UNVERIFIED step CLI syntax (written from memory; confirm against installed step version)
   step ca init --name "HomericIntelligence" --dns ca.internal --address :443 --provisioner admin
   step ca certificate "<host>" /etc/nats/certs/server-cert.pem /etc/nats/certs/server-key.pem --san <ip>
   step ca root /etc/nats/certs/ca.pem
   chmod 600 /etc/nats/certs/server-key.pem
   chmod 644 /etc/nats/certs/server-cert.pem /etc/nats/certs/ca.pem
   ```

2. **Scenario 2 — zero-downtime rotation via SIGHUP (UNVERIFIED claim).** The plan claims
   `kill -HUP <nats-server pid>` makes NATS re-read the cert files in place without dropping
   JetStream state. NATS DOES support config reload on SIGHUP, but whether the running
   version re-reads cert files in-place (vs requiring a full restart) was NOT exercised.
   **If SIGHUP does NOT re-read certs, the "zero-downtime" claim is false** and a full
   restart is needed — and per the **After NATS Restart** section, Agamemnon and Nestor do
   NOT auto-reconnect, so they must be manually restarted too. Tie the claim to a verified
   reload signal before trusting it.

   ```bash
   # UNVERIFIED: replace the cert files on disk, then signal a reload
   kill -HUP "$(pgrep -f nats-server)"     # claim: hot-reloads TLS certs, JetStream survives
   # If this does NOT re-read certs, a full restart is required (then restart Agamemnon+Nestor)
   ```

3. **Scenario 3 — key-compromise response.** Revoke the compromised cert, rotate the CA if
   the CA key is compromised, re-issue all leaf/server certs, push to every host (`configs/`
   is canonical), reload/restart. `step ca revoke --cert <cert>` — **flag UNVERIFIED.**

4. **Verify TLS is actually required (UNVERIFIED field name).** The plan greps the NATS
   monitoring API:

   ```bash
   # UNVERIFIED: the exact JSON key for "TLS required on client port" was NOT confirmed
   curl -s http://127.0.0.1:8222/varz \
     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tls_required'))"
   ```

5. **Do NOT edit ADR-008.** CLAUDE.md principle 3: ADRs are append-only — once accepted,
   never edited. The plan's optional back-reference line into ADR-008's References is
   DROPPABLE. Prefer one-directional linking (runbook → ADR); discoverability is satisfied
   by the `docs/README.md` index row alone.

6. **Confirm ADR-008 is still the source of truth.** Its Status is "Proposed", not
   "Accepted". The cert-path convention, permissions, and three provisioning strategies are
   treated as settled by the plan — confirm ADR-008 has not been superseded before relying
   on them.

### Discipline that was DONE RIGHT this session (contrast with #176's fabrication)

- **`.gitignore` cert-key coverage was actually GREPPED, not assumed.** `*.pem`, `*.key`,
  `*.crt`, `.env`, `.env*.local`, `secrets/`, `*.secret` are ALL present in `.gitignore`, so
  cert keys / creds won't be committed. This is the correct discipline — it directly
  reinforces the #176 lesson that the EARLIER `.gitignore` claim was fabricated. Grep the
  actual file; don't infer coverage from a convention.

- **Use `ls docs/runbooks/` to enumerate runbooks — NOT the `docs/README.md` table.** The
  README runbook table (lines ~35-41) is hand-maintained and already MISSING existing
  runbooks `branch-protection-rollout.md` and `no-silent-failures.md`. The index drifts;
  don't trust it as a complete inventory.

### Compose Healthchecks (Dual-Runtime: podman-compose 1.5.0 + Docker Compose v2/v5)

```yaml
# CORRECT — YAML string form; Docker Compose v2 and v5 both treat it as CMD-SHELL
healthcheck:
  test: "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"
  interval: 5s
  timeout: 3s
  retries: 10
  start_period: 10s

# For nats:alpine (BusyBox wget rejects combined -qO- flag)
healthcheck:
  test: "wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"
```

#### Distroless app images — binary self-probe healthcheck (planning learning, unverified)

> **Unverified planning learning (R2, issue #154).** The self-probe pattern below was
> derived from a plan, NOT tested end-to-end. No container was built or observed reaching
> `healthy`. Treat it as the correct distroless-safe shape, but confirm at runtime.

**Rule:** distroless `static`/`base` images (`gcr.io/distroless/static-*`,
`gcr.io/distroless/base-*`) contain ONLY the static binary — **no shell, no wget, no curl,
no busybox**. A `wget`/`curl`/`sh` healthcheck command simply does not exist in the
container, so it fails permanently and the service never reports `healthy`. Compose
healthchecks ALWAYS run inside the container, so there is no shell-free external-tool
option. The ONLY in-container probe is the binary self-checking.

```yaml
# Distroless runtime (gcr.io/distroless/static-*): NO shell/wget/busybox.
# The ONLY in-container probe is the binary self-checking. Requires the app
# binary to expose a -healthcheck flag (localhost GET /healthz, exit 0/1).
healthcheck:
  test: ["CMD", "/argus-dashboard", "-healthcheck"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 15s   # Go/static binaries cold-start; avoid early flapping
```

**Cross-issue coordination note:** the self-probe creates a dependency on the binary owning
a `-healthcheck` flag. When the Dockerfile/binary is delivered by a different issue/PR than
the compose wiring, name that flag explicitly as a blocking note — never assume it exists.

**Verification discipline (do BOTH — structural config validation is insufficient):**

```bash
# Assert the healthcheck does NOT shell out to wget/sh (would fail on distroless)
docker compose config | grep -A4 'healthcheck' | grep -q '/<binary>' && ! (docker compose config | grep -E 'test:.*wget')
# Post-build, assert the container ACTUALLY reaches healthy (config alone is insufficient)
docker compose ps | grep -E '<service>.*healthy'
```

## Proposed Workflow — Telemachy NATS Client-Cert mTLS Wiring (UNVERIFIED overall; R1 facts VERIFIED-LOCAL, issue #304)

> **Warning:** This section is an UNVERIFIED PLAN overall — no CI passed. BUT R1 (post-NOGO)
> VERIFIED-LOCAL several facts the R0 round only flagged as reviewer-risk; they are marked
> **VERIFIED-LOCAL (R1, #304)** inline below. Confirmed this session: nats-py **2.14.0**
> `nats.aio.client.Client.connect` accepts `tls`/`tls_hostname`/`tls_handshake_first`
> (inspect `Client.connect`, NOT the `nats.connect` wrapper); Hermes' `build_ssl_context()`
> is DEFINED-BUT-UNUSED at its connect site (`publisher.py:91-97` passes NO `tls=`);
> `cryptography`/`trustme` are ABSENT from Telemachy's pixi env while the `openssl` binary
> (3.6.2) IS present (generate certs into pytest `tmp_path`); ADR-009 and
> `docs/runbooks/enable-nats-auth.md` do NOT exist (ADR-008 is the real TLS ADR). The
> highest-value content is the reviewer-risk catalogue in **Results & Parameters** — read it
> before trusting any step.

Issue #304 asks to wire NATS client-cert mTLS into ProjectTelemachy so it presents a client
cert to a `verify_and_map=true` NATS server. The plan's load-bearing finding reshapes the task.

### Load-Bearing Finding: Telemachy has NO live `nats.connect()` site (VERIFIED-LOCAL, R1, #304)

```bash
# Verified this session — returns NOTHING:
grep -rn "nats.connect\|import nats\|from nats" provisioning/ProjectTelemachy/src
```

`executor.py:265-300` (`_monitor_completion`) is **HTTP polling of Agamemnon `get_tasks`**, NOT
a NATS subscription. CONSEQUENCE: the issue's "wire these into the NATS client connection"
requirement has **no existing connection site to modify**.

**AC scope trap (R1):** "Telemachy connects to NATS" CANNOT be met by a config builder alone. The
R0 plan proposed shipping `build_ssl_context()` + an unconsumed `nats_connect_kwargs()` helper — but
a helper nobody calls is YAGNI (flagged in the NOGO) and does not make Telemachy connect. The HONEST
fix that genuinely satisfies AC1 (not narrows it) is to ADD a real, CONSUMED connection site: a
`nats_client.connect_nats()` invoked from the CLI `run` path as a `tls://` preflight handshake.

- `build_ssl_context()` loads CA + client cert/key into an `ssl.SSLContext`, and
- `connect_nats()` (the new minimal consumer) actually calls
  `nats.connect(url, tls=ctx, tls_hostname=host)` as a preflight — rather than handing a dict to a
  hypothetical future caller.

**Insertion point CONFIRMED (VERIFIED-LOCAL, R2, #304).** The preflight belongs INSIDE the existing
`_run_with_signals()` async function (`cli.py:141`), which the `run` command (`cli.py:120`) already
uses to wrap execution with SIGINT/SIGTERM handlers and a Rich `Progress` context. Put
`nc = await connect_nats(settings); await nc.drain()` AFTER the signal handlers are installed and
BEFORE the `async with AgamemnonClient(...)` block (`cli.py:178`). **LESSON:** when adding an async
preflight to a Typer CLI command, locate the existing `asyncio.run(_inner())` wrapper and insert
inside it — do NOT add a second `asyncio.run` or block at import time.

**POLA resolution (R3, #304) — two MINOR review findings closed in-plan (design/framing, nothing newly run).**

1. **Preflight failure handling → typed `NatsConnectionError` + `typer.Exit(1)`.** A `tls://` mTLS
   preflight that lets the handshake exception propagate out of `asyncio.run()` is a POLA gap (bare
   traceback). The fix mirrors the codebase's EXISTING typed-error convention: `connect_nats()` wraps
   `nats.connect(...)` in `try/except Exception` and re-raises a new typed `NatsConnectionError`
   (modeled on the existing `AgamemnonError` at `agamemnon_client.py:13`) with an operator-guiding
   message ("confirm TLS_CERT_FILE/TLS_KEY_FILE/TLS_CA_BUNDLE are set and the cert is CA-signed").
   The CLI `run` preflight catches `NatsConnectionError`, prints a red `console` line, and exits via
   `typer.Exit(1)` — matching the existing failure style at `cli.py:68-80`. A unit test
   (`test_connect_failure_raises_typed_error`) monkeypatches `nats.connect` to raise `ssl.SSLError`
   and asserts the typed error + message.

   ```python
   class NatsConnectionError(Exception):  # mirrors AgamemnonError (agamemnon_client.py:13)
       """NATS connect/handshake failed; operator-actionable."""

   async def connect_nats(url, ssl_ctx, server_hostname):
       try:
           return await nats.connect(url, tls=ssl_ctx, tls_hostname=server_hostname)
       except Exception as exc:  # ssl.SSLError, nats.errors.* — never let them escape asyncio.run()
           raise NatsConnectionError(
               f"NATS mTLS preflight to {url} failed: {exc}. "
               "Confirm TLS_CERT_FILE/TLS_KEY_FILE/TLS_CA_BUNDLE are set and the cert is CA-signed."
           ) from exc
   # ...and at the CLI run preflight boundary:
   #   except NatsConnectionError as exc:
   #       console.print(f"[red]{exc}[/red]"); raise typer.Exit(1)  # matches cli.py:68-80
   ```

   **LESSON:** when adding a new external-connection helper to a codebase that already has a
   typed-error + `typer.Exit(1)` convention, mirror that convention from the START — don't let a raw
   `ssl.SSLError`/`nats.errors.*` escape an `asyncio.run()` entrypoint; wrap-and-retype at the helper
   boundary and translate to a clean exit at the CLI boundary.

2. **"Handshake-only preflight = is it really connecting?" → framed as a DESIGNED fail-closed
   verification gate.** When a component has no live data path for protocol X but an AC says it must
   "connect over X presenting a cert," the honest resolution is NOT to narrow the AC nor to add an
   ambiguous open/close probe — it is to make the connection a DELIBERATE, DOCUMENTED, fail-closed
   verification gate: state the intent in the helper docstring, the CLI comment, the CLAUDE.md
   env-var row, AND the runbook; name it as the single real connection site future data paths reuse;
   and have it hard-fail (non-zero exit) on rejection so it complements the existing pre-connection
   gate (here `agamemnon_client.py`'s `require_tls`). **LESSON:** a reviewer's "is this really
   connecting?" doubt is answered by DESIGN INTENT made explicit in code+docs and fail-closed
   behavior — not by more code, and not by narrowing the acceptance criterion.

> **Review trajectory (#304):** R0 NOGO (6 majors) → R1 fixed all 6 but surfaced residual MINORs →
> R2 B/NOGO (narrow, "needs confirmation" on the two POLAs) → R3 resolved BOTH in-plan. LESSON: a
> B/NOGO with only minors is closable WITHOUT new external verification — by specifying the
> unspecified behavior (the typed error path) and re-framing the judgment call (documented design
> intent), both inside the plan body. Don't treat a minors-only NOGO as needing fresh investigation;
> it usually needs decisions stated.

**The Hermes-analogy is a trap (VERIFIED-LOCAL, R1, #304).** The premise "ProjectHermes is already
mTLS-capable / wire it exactly as Hermes does" (per #304 / parent #175) is TRUE only at the CONFIG
layer. `grep -rn "tls=\|build_ssl_context\|ssl_context" infrastructure/ProjectHermes/src/` returns
ONLY the method DEFINITION at `config.py:126`; `publisher.py:91-97` calls
`nats.connect(url, allow_reconnect=False, connect_timeout=..., disconnected_cb=..., reconnected_cb=...)`
with NO `tls=` kwarg. So Hermes builds an `SSLContext` but does NOT wire it into its NATS connection —
it has the SAME latent gap. A plan that says "wire it exactly as Hermes does" is building on a
connect-site analogy that DOES NOT EXIST. **REVIEWER LESSON:** grep the actual call site before
asserting a reference implementation "already does X"; a defined-but-unused helper is a trap. (Hermes'
own `test_tls_config.py` only asserts context CREATION against a NON-EXISTENT `/fake/ca.pem` path —
it never calls `load_cert_chain`, so it does not even prove the loading path.)

### Proposed config-layer helper + real consumer (nats-py kwargs VERIFIED-LOCAL on 2.14.0)

```python
# config layer — build the SSLContext.
import ssl

def build_ssl_context(ca_path, cert_path, key_path) -> ssl.SSLContext:
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_path)
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)  # client cert for mTLS — raises on malformed PEM
    return ctx

# VERIFIED-LOCAL (R1, #304): on the installed nats-py **2.14.0**
# (importlib.metadata.version('nats-py')), inspect.signature(nats.aio.client.Client.connect)
# shows `tls`, `tls_hostname`, AND `tls_handshake_first` are all real parameters.
# NOTE: the module-level `nats.connect` wrapper does NOT expose `__version__` and the params
# live on `Client.connect`, not the wrapper — inspect `nats.aio.client.Client.connect`.
import nats

async def connect_nats(url, ssl_ctx, server_hostname):
    # The REAL consumer (CLI `run` tls:// preflight). NOT an unconsumed kwargs dict (YAGNI).
    return await nats.connect(url, tls=ssl_ctx, tls_hostname=server_hostname)
```

### Test path and the `.gitignore` fixture conflict (VERIFIED-LOCAL, R1, #304)

The test asserts the **cert-LOADING depth**: `ssl.SSLContext.load_cert_chain` on a real cert/key —
a malformed PEM raises `ssl.SSLError`. This is strictly DEEPER than Hermes' own tests, which only
use a NON-EXISTENT `/fake/ca.pem` path and assert context creation, never calling `load_cert_chain`.

Both R0 cert-sourcing options are now **VERIFIED CLOSED**:

1. Generate at test time via `cryptography` — **CONFIRMED ABSENT**: `pixi run python -c "import
   cryptography"` AND `import trustme` BOTH raise `ModuleNotFoundError` in the Telemachy env (deps
   are only pydantic, pydantic-settings, nats-py, pytest, pytest-asyncio, pytest-cov). So a
   `cryptography`/`trustme` test fails to import.
2. Commit a static throwaway PEM pair under `tests/fixtures/` — **CONFIRMED BLOCKED**:
   `provisioning/ProjectTelemachy/.gitignore:21-22` = `*.key`/`*.pem` and root `.gitignore:7-9` =
   `*.key`/`*.pem`/`*.crt`, so a checked-in PEM fixture is silently git-ignored.

**SOLUTION THAT WORKS (VERIFIED-LOCAL, R1):** the `openssl` binary IS on PATH inside pixi (OpenSSL
3.6.2). Generate the cert/key at test time into pytest's `tmp_path` (ephemeral, never committed →
`.gitignore` is moot):

```python
import subprocess

def test_build_ssl_context_loads_real_cert(tmp_path):
    cert, key = tmp_path / "c.pem", tmp_path / "k.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key), "-out", str(cert), "-days", "1",
                    "-subj", "/CN=telemachy-test"], check=True)
    # build_ssl_context runs load_cert_chain → raises ssl.SSLError on a malformed cert.
    build_ssl_context(str(cert), str(cert), str(key))
```

LESSON: when a repo ignores `*.pem`/`*.key` and ships no cert lib, generate certs at runtime via the
`openssl` binary into `tmp_path` rather than committing fixtures or adding a `cryptography` dep.

### Non-existent referenced artifacts (do NOT fabricate) (VERIFIED-LOCAL, R1, #304)

```bash
ls docs/adr/                      # shows 001–008 ONLY — 009 is ABSENT; 008 is the NATS TLS ADR
ls docs/runbooks/                 # enable-nats-auth.md is ABSENT
```

- **ADR-009 does NOT exist; ADR-008 is the real TLS ADR.** `ls docs/adr/` shows 001–008 only, and
  008 is `008-nats-tls-encryption…`. Issue #304 cites
  `docs/adr/009-nats-authentication-authorization.md` (and `docs/runbooks/enable-nats-auth.md`) as
  if present — BOTH are absent. Either ADR-009 lands in a sibling PR (issue #175 / parent) or the
  plan must stop asserting it as present and point docs at ADR-008, which actually exists. Do NOT
  fabricate ADR-009. LESSON: an issue body can reference a sibling-PR artifact (ADR-009 from #175)
  that has not landed; verify `ls docs/adr docs/runbooks` before citing or linking it.
- **`docs/runbooks/enable-nats-auth.md` does NOT exist** (present: add-new-agent-type, add-new-host,
  branch-protection-rollout, disaster-recovery, no-silent-failures, wsl2-podman-setup). The issue
  says Telemachy is "documented in" it as if it exists; the plan CREATES it. **REVIEWER RISK:** if a
  Hermes/#175 PR also creates this same runbook, two PRs collide on the same new file — confirm
  ownership of `enable-nats-auth.md` before creating it.

### After NATS Restart

Agamemnon and Nestor do NOT auto-reconnect after NATS restarts. Always kill and restart them:

```bash
pkill -f ProjectAgamemnon_server || kill $(pgrep -f ProjectAgamemnon_server)
pkill -f ProjectNestor_server    || kill $(pgrep -f ProjectNestor_server)
```

## Proposed Workflow — NATS e2e SIGKILL→restart port-bind-race fix (VERIFIED-LOCAL IMPLEMENTATION R3, Odysseus issue #328)

> **Implementation status:** This section is **VERIFIED-LOCAL (R3)**. The unit test passes 15/15
> including an 8× kill→restart→healthy loop. CI has not yet confirmed. R2 measured the core kernel
> mechanism (8/8 immediate SIGKILL→rebind, no port-free poll needed). R3 implemented the full fix and
> confirmed it locally. The section retains the R2 analysis and design rationale for reference.
> See the R3 implementation facts (10 confirmed points) in the "Uncertain Assumptions" table below.

### The MEASURED root cause (R2): TIME_WAIT does not apply to a listening socket — VERIFIED-LOCAL

The issue #328 body asserts a monitor-port TIME_WAIT race: after SIGKILL the `-m NATS_MONITOR_PORT`
bind supposedly fails because the port lingers in TIME_WAIT. A PRIOR reviewer escalated this into a
load-bearing major: "the ~15s bind-retry backoff can't outlast Linux 2MSL ~60s." **This round I RAN
the experiment** instead of reasoning about it:

```bash
# VERIFIED-LOCAL this session — nats-server at ~/.local/bin/nats-server
for i in $(seq 1 8); do
  nats-server -js -p 14299 -m 18299 & pid=$!
  until curl -sf http://127.0.0.1:18299/healthz >/dev/null; do sleep 0.05; done
  kill -KILL "$pid"                       # SIGKILL the listener
  # IMMEDIATELY relaunch a fresh server on the SAME -p/-m ports: NO port-free poll, NO sleep
  nats-server -js -p 14299 -m 18299 & pid=$!
  until curl -sf http://127.0.0.1:18299/healthz >/dev/null; do sleep 0.05; done
  kill -KILL "$pid"
done
# RESULT: 8/8 immediate rebinds succeeded, ZERO failures, ZERO delay.
```

**The durable kernel-networking fact: TIME_WAIT does NOT apply to a server's own LISTENING sockets.**
When you SIGKILL a process holding a LISTEN-state socket, the kernel reclaims the port immediately.
The TIME_WAIT (2MSL) reservation only afflicts the endpoint that performed an ACTIVE CLOSE of an
ESTABLISHED connection — i.e. a client/peer socket, never the listener you are trying to rebind.
So "wait out 2MSL", "free-poll the port", and "SO_REUSEADDR to defeat TIME_WAIT" were ALL solving a
non-problem for this failure mode. The prior reviewer's blocking "backoff can't outlast 2MSL" major
rested on a false premise — a 10-line bash loop dissolved it.

Confirmed by `nats-server --help` this session: there is NO SO_REUSEADDR / address-reuse flag at
all; the available signals via `-sl/--signal` are `ldm,stop,quit,term,reopen,reload` (none defeat
TIME_WAIT, and none are needed); `-p`=client port, `-m`=http monitor, `-ms`=https monitor.

### The ACTUAL defect (R2): a stale-process race, not a kernel-timing race

The real failure is a STALE-PROCESS RACE compounded by the R1 process-boundary bug. The R1 kill
targeted an EMPTY cross-process `_NATS_PID` shell global (each e2e test runs as a separate
`bash "$script"` CHILD — `e2e/run-ipc-tests.sh:64` — while NATS is started in the PARENT at
`topology.sh:21`, and the runner exports only PORTS, not PIDs, at `run-ipc-tests.sh:50`). So the
kill no-opped, the ORIGINAL server stayed ALIVE, and the relaunch raced a still-bound socket. The
real fix is therefore:

- **(a) kill the RIGHT pid** via a port-keyed PID/meta file, and
- **(b) `wait` for the killed process to FULLY EXIT (FD released) before relaunch.** This
  `wait`-for-exit is the CORRECTNESS gate. A short 3×/1s bind-retry is only a sub-second teardown
  margin (covering the gap between SIGKILL delivery and FD release on a loaded box), NOT a 2MSL wait
  — there is no 2MSL window on the listener port to outlast.

### The corrected fix design (R2, kernel mechanism verified-local; plan unverified)

1. **Cross-process kill needs a PID/meta FILE, not a shell global.** Record the NATS PID (and its
   `--store_dir`) in a port-keyed meta file under `/tmp` so the forked child can find and kill the
   parent-started NATS. Mirror the repo's existing PID-file idiom (`doctor.sh:292` writes
   `aardvark.pid`); `pkill -f` is also precedented (`start-hermes-hub.sh:197`). After the kill,
   `wait` for the pid to fully exit (FD release) before relaunch — this is the correctness gate.

   ```bash
   # Parent writes a port-keyed meta file when it starts NATS; the child reads it.
   _nats_meta_file() { printf '/tmp/homeric-nats-%s.meta' "${NATS_MONITOR_PORT:-18222}"; }

   nats_kill() {
     local meta; meta="$(_nats_meta_file)"
     [ -f "$meta" ] || return 0
     local pid; pid="$(sed -n '1p' "$meta")"
     _kill_if_alive "$pid"      # process.sh:16-24 — returns 0 if pid empty/dead
     kill -9 "$pid" 2>/dev/null || true
     # WAIT for full exit (FD release) — the real correctness gate. `wait` returns 127
     # for a NON-CHILD pid (the parent-started NATS is not the child test's child), so
     # fall back to a bounded kill -0 poll until the process is gone.
     wait "$pid" 2>/dev/null || \
       for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 0.1; done
   }
   ```

2. **Relaunch AT the original `--store_dir`, do not mktemp a fresh one.** `start_nats_bg`
   (`process.sh:64-79`) mktemps a NEW `--store_dir` on every call (lines 65,74) — a "clean restart"
   that silently EMPTIES the JetStream streams. A02/A01 assert message continuity
   (`nats_msg_count`, "messages flowing"), so a fresh store breaks them. Record the original store
   dir in the meta file and relaunch at it:

   ```bash
   start_nats_bg_at() {  # like start_nats_bg but binds an EXISTING --store_dir
     local store="$1"
     nats-server -p "$NATS_PORT" -m "$NATS_MONITOR_PORT" -js -sd "$store" &
     printf '%s\n%s\n' "$!" "$store" > "$(_nats_meta_file)"
   }
   nats_restart() {
     local store; store="$(sed -n '2p' "$(_nats_meta_file)")"
     nats_kill
     start_nats_bg_at "$store"           # preserve JetStream state
   }
   # After restart, spot-check continuity (do NOT just trust "healthy"):
   nats_stream_exists "$STREAM" || fail "stream lost across restart"
   ```

3. **The correctness gate is `wait`-for-exit, NOT a 2MSL-sized backoff.** The MEASURED result (8/8
   immediate rebinds) shows there is no TIME_WAIT window on the listener port to outlast; once the
   killed pid is reaped, the port is free. So the retry loop is only a thin SUB-SECOND teardown
   margin (covering SIGKILL-delivery → FD-release latency on a loaded box), documented as such — it
   is explicitly NOT a 2MSL wait.

   ```bash
   nats_kill                          # kills the RIGHT pid AND waits for FD release
   for attempt in 1 2 3; do           # ~3s max — a sub-second teardown margin, NOT a 2MSL wait
     start_nats_bg_at "$store" && nats_wait_healthy && break
     sleep 1
   done
   ```

   **What the prior round got wrong (now corrected):** R1 sized a 1→2→4→8s backoff to "clear the
   TIME_WAIT window" and a reviewer escalated "can't outlast 2MSL ≈ 60s" into a blocking major. The
   measurement shows that whole framing is moot — TIME_WAIT does not apply to the listener, so there
   is nothing to outlast. The only real gap is sub-second FD teardown after the killed PID is reaped.
   `SO_REUSEADDR` is not exposed by `nats-server` anyway (confirmed via `--help`) and is unnecessary.

### Proposed Steps

1. **Map the process boundary BEFORE designing PID/state handling.** Confirm who forks whom and what
   is inherited vs exported. Verified this session: `run-ipc-tests.sh:64` forks each test via
   `bash "$script"`; line 50 exports only the four PORT vars + `IPC_TOPOLOGY` (no PIDs);
   `topology.sh:21` starts NATS in the PARENT (`start_nats_bg`) for T1; `topology_stop` →
   `cleanup_all` (`process.sh:120-123`). A `_NATS_PID` shell global set in the parent is invisible
   to the forked child — this is the defect the R0 plan missed.
2. **Use a port-keyed PID/meta FILE for cross-process kill, not a shell global.** Mirror
   `doctor.sh:292` (aardvark.pid); `pkill -f` precedented at `start-hermes-hub.sh:197`. The named
   `nats_restart`/`nats_kill` helpers DO NOT EXIST on main today — the plan SHIPS them; check parent
   PR #184 for whether they already landed on another branch (merge-conflict risk).
3. **Preserve `--store_dir` across the restart.** `start_nats_bg` (`process.sh:64-79`) mktemps a
   fresh store_dir each call (65,74) and binds `-p NATS_PORT`/`-m NATS_MONITOR_PORT` (defaults
   `NATS_PORT=14222`/`NATS_MONITOR_PORT=18222`). Record the original store dir in the meta file and
   relaunch via `start_nats_bg_at <dir>`; spot-check `nats_stream_exists` after restart so the
   A01/A02 continuity asserts survive.
4. **MEASURE the kernel mechanism before designing around it.** This round a tight kill→rebind loop
   (8/8 immediate rebinds, VERIFIED-LOCAL) showed TIME_WAIT does NOT apply to the LISTENING socket —
   a SIGKILLed listener frees its port immediately; 2MSL only hits the ACTIVE-CLOSE side of an
   ESTABLISHED connection. So `wait`-for-process-exit (FD release) is the correctness gate; a short
   3×/1s bind-retry is only a sub-second teardown margin, documented as NOT a 2MSL wait. Do NOT size a
   backoff to "clear TIME_WAIT" and do NOT reach for `SO_REUSEADDR` (nats-server exposes neither, per
   `--help`) — both target a non-problem here. The general rule: when an issue body hands you a
   kernel/OS-timing root cause, run a 10-line reproduction before architecting (or before a reviewer
   escalates the hypothesis into a blocking major).
5. **Source EVERY lib whose helpers the test calls — grep the defining file first.** The NATS
   helpers (`nats_wait_healthy` `nats.sh:16`, `nats_stream_exists` `nats.sh:99`, `nats_health`
   `nats.sh:12`, `nats_msg_count` `nats.sh:27`) live in `e2e/lib/nats.sh`, NOT in common.sh/process.sh
   — a test that sources only common.sh + process.sh hits `command not found` under `set -e`.
   `e2e/tests/fault/nats-crash-reconnect.sh:8` already sources `nats.sh`, so it needs `process.sh`
   ADDED (for the new kill/restart helpers), not `nats.sh`.
6. **Exercise the REAL harness path before claiming the bug is fixed.** Run
   `run-ipc-tests.sh --topology t1 --test ...` (cross-process), NOT just a convenient single-shell
   unit test where the global IS visible — that single-shell test is a FALSE POSITIVE for a
   parent/child defect. `topology_supports "<t>"` (`common.sh:127`) is the gating idiom
   (case-sensitive; `IPC_TOPOLOGY` is lowercase `t1`).
7. **Do NOT assume the test runner or `nats-server` availability.** `pixi run bash` /
   `pixi run shellcheck` wiring is unconfirmed (fall back to bare binaries; the harness normally
   runs via `bash e2e/run-ipc-tests.sh`). `nats-server` presence on the runner is assumed. Neither
   the new unit test nor the real A02 was executed this session — the whole plan remains UNVERIFIED
   OVERALL; only the kernel-behavior experiment ran.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Leaf.conf to port 4222 | Connected leaf node to NATS client port | Leaf nodes require dedicated leafnode listener port 7422 | Always use port 7422 for leafnode remotes, not 4222 |
| `agamemnon` as binary name | Called `./build/debug/agamemnon` | Binary is `ProjectAgamemnon_server` — exact CMake target name | Check `ls build/debug/` to confirm binary name |
| `nestor` as binary name | Called `./build/debug/nestor` | Binary is `ProjectNestor_server` — exact CMake target name | Always use `ProjectNestor_server` |
| Hermes without PYTHONPATH | `uvicorn hermes.server:app` with no env prefix | src layout — Python cannot find `hermes` module | Always prefix `PYTHONPATH=src` |
| `uvicorn hermes.main:app` | Used `hermes.main:app` entry point | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` |
| `nats-server` without full path | Called bare `nats-server` | `~/.local/bin` not in PATH on most remote hosts | Always use `~/.local/bin/nats-server` |
| NATS monitoring on port 4222 | `curl localhost:4222/varz` | Port 4222 is client port; monitoring HTTP is on 8222 | NATS monitoring: port 8222; client pub/sub: port 4222 |
| NATS via podman (slirp4netns) | Podman container NATS without rootlessport | slirp4netns remaps 4222 to ephemeral port invisible to external clients | Run NATS as native binary when rootlessport absent |
| cmake without pixi on artemis | Ran cmake directly without `pixi run bash -c` | pixi conda toolchain not activated; wrong sysroot | Run cmake inside `pixi run bash -c "..."` |
| cmake without `_ENABLE_CLANG_TIDY=OFF` | Default cmake on artemis | clang-tidy sysroot mismatch causes build failure | Always pass `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` on conda sysroot hosts |
| Nestor without `-lz` on hephaestus | Standard cmake for Nestor | OpenSSL zlib dep not automatically linked | Pass `-DCMAKE_EXE_LINKER_FLAGS='-lz'` on hephaestus |
| `POST /v1/tasks` Agamemnon | Used flat `/v1/tasks` path | Returns 404 — endpoint is team-scoped only | Correct: `POST /v1/teams/<teamId>/tasks` |
| `POST .../complete` task completion | Used POST complete endpoint | Returns 404 — endpoint does not exist | Use `PATCH /v1/teams/<id>/tasks/<id>` with `{"status":"completed"}` |
| `jq -r '.id'` on team response | Extracted `.id` directly | Team ID is nested: `{"team": {"id": "..."}}` | Always use `.team.id` |
| Hermes with `HERMES_PORT=8080` | Default port for Hermes container | Conflicts with Agamemnon on 8080 | Set `HERMES_PORT=8085`; Agamemnon owns 8080 |
| Hermes Dockerfile without `prometheus_client` | Built without prometheus_client | Hermes imports it at startup; container crashes | Add `prometheus_client` to pip install (PR #415) |
| hello-myrmidon `main.cpp` | Used C++ file in hello-world | Requires build step; Python `main.py` is the worker | Always use `main.py`; it subscribes via JetStream push consumer |
| `worker.py` in start-myrmidon recipe | Referenced non-existent worker.py | File does not exist — correct file is `main.py` | Use `main.py`; subscribes to `hi.myrmidon.hello.>` |
| `task.created` to Hermes webhook | Sent `task.created` event | Hermes `_TASK_EVENTS` allowlist: `task.updated`, `task.completed`, `task.failed`, `agent.*` only — silently dropped | Always use `task.updated` for test webhook validation |
| Submodule scripts as-is | Used provisioning/Myrmidons scripts | Submodule pinned to old commit with `aim_*` functions targeting ai-maestro | Verify submodule pins match standalone checkouts after migrations |
| Monolithic e2e-all launcher | Single `just e2e-all` starts everything | Defeats multi-machine flexibility; per-component granularity needed | Individual launchers compose better for distributed deployment |
| `nats:latest` for healthchecks | Used `nats:latest` container | `nats:latest` is distroless — no shell, wget, or curl | Use `nats:alpine` for compose healthchecks |
| CMD-SHELL array healthcheck on podman-compose 1.5.0 | `["CMD-SHELL", "wget ..."]` format | podman-compose 1.5.0 rejects this array format | Use `["CMD", "sh", "-c", "wget ..."]` or YAML string form |
| CMD/CMD-SHELL array on Docker Compose v5 | JSON array `["CMD","sh","-c","full cmd"]` | Docker Compose v5 splits 4th element on spaces — `sh -c wget` runs wget alone | Use YAML string `test: "cmd"` — both v2 and v5 treat it as CMD-SHELL without splitting |
| `wget -qO-` in nats:alpine | Combined short flag with BusyBox wget | BusyBox wget rejects `-qO-`; prints usage and exits 1 | Use `-q -O /dev/stdout` (space-separated, explicit path) |
| Sleeping after final retry attempt | `if attempt < retries` guard | Adds unnecessary latency after retries exhausted | Guard with `if attempt < retries - 1` |
| Catching bare `Exception` in retry | Catch-all in retry loop | Hides non-retryable bugs as transient failures; burns retry budget | Only catch explicit `_RETRYABLE_PUBLISH_ERRORS` tuple |
| No restart after NATS port change | Left Agamemnon/Hermes running | Processes lose NATS connection and do not auto-reconnect | Restart both services after NATS is stable |
| Assuming Odysseus present on all hosts | Skipped `gh repo clone` step | Only some hosts had a clone; others needed fresh clone | Pre-check `ls ~/<project-root>` — clone if missing |
| `podman cp` to overwrite read-only bind-mount | Tried `podman cp` on `:ro` Prometheus config | Volume is `:ro` — copy fails with "device or resource busy" | Write resolved-IP config to host bind-mount source, then `/-/reload` |
| Forking Atlas branch from feature branch | Created feat branch from `feat/issue-22-ci-hardening` | Picked up 12 extra CI commits; PR not rebased to main | Always fork from `main`; check base before `git worktree add` |
| Leaf remote on port 4222 (auth fix) | Pointing `remotes.url` at the client port while adding creds | Leaf nodes silently never connect | Leaf remotes MUST use 7422, even when adding auth |
| Auth only on client listener | Adding `authorization{}` only at the top level of `server.conf` | The `leafnodes{}` listener stays open — anonymous leaf relay still works | The leafnode listener needs its OWN `authorization` block |
| `sensitive = true` in Nomad var | Terraform-ism to hide NATS creds in a Nomad variable | Nomad parse error: "argument named 'sensitive' is not expected" | Don't secure NATS creds via Nomad `sensitive` vars |
| Naive grep gate | `grep` for `token` without stripping comments | A commented-out example passes the check (false-negative) | Strip comments before asserting presence; assert per-block, not file-wide |
| Assuming pytest exists | Planning a pytest-based regression test for the config | Odysseus has no pytest; tasks are `just`-backed | Wire gates into the existing `just` / CI runner |
| awk parser that ends block on first `}` | Validate leafnodes auth by scanning until the first `}` | Nested `tls{}` inside `leafnodes{}` closes first — parser declared a CORRECTLY-authed config unauthenticated; exited 1 on BOTH fixed and broken configs | A config-block validator MUST track brace DEPTH (count `{` vs `}`), not stop at the first `}`. Nested blocks are the norm in NATS/HCL-style configs |
| Verification that only checks the broken case | `git stash && ! validator && echo PASS` | A validator that always exits 1 "passes" this check for the wrong reason — masks that it also rejects the FIX | Always assert BOTH directions: exit 1 on the unfixed config AND exit 0 on the fixed config. A regression gate that can't accept the fix is broken |
| Assuming a recipe wired into justfile runs in CI | Claimed validator "already runs on pull_request via ci.yml" | `ci.yml`'s validate job inlines its own steps and never invokes `just validate-configs`/`pixi run validate` | Don't assume CI calls your `just` recipe — READ the workflow. Add an explicit CI step (or confirm the recipe is invoked) or the gate doesn't exist |
| Parse check gated on `command -v nats-server` | `command -v nats-server && nats-server -t ... \|\| echo skipped` | The tool is absent in CI, so the check silently skips — the fail-closed assumption is never actually tested | If a verification matters, INSTALL the tool in CI (pinned release) and run it unconditionally; a `command -v ... \|\|` guard turns the check into a no-op |
| Asserting `.gitignore` coverage from a pattern | Claimed `/etc/nats/certs/` was already git-ignored | `grep -n "certs\|creds\|nats" .gitignore` → no matches; the claim was fabricated from the certs convention | Grep the actual file before claiming a path is ignored. "It follows the convention" is not evidence the entry exists |
| `wget` healthcheck against a distroless app image | Used `["CMD","wget","-qO-","http://localhost:PORT/healthz"]` (matching sibling services that use slim/alpine images) on a service whose runtime is `gcr.io/distroless/static-debian12:nonroot` | Distroless `static` images have NO shell, wget, busybox, or any external tool — the healthcheck command does not exist in the container, so it fails permanently and the container never reports `healthy` | A wget/curl/sh healthcheck is unusable on a distroless runtime. Use a binary self-probe `["CMD","/<binary>","-healthcheck"]`; the app binary must expose a healthcheck flag that does a localhost GET and exits 0/1. Compose healthchecks always run INSIDE the container — there is no shell-free external option |
| Trusting `docker compose config` as proof the healthcheck works | Plan's verification ran `docker compose config` and passed, treated as evidence the service would be healthy | `docker compose config` only validates STRUCTURE/syntax — it never executes the healthcheck command, so a healthcheck pointing at a nonexistent binary (wget in distroless) passes config but fails at runtime | Structural compose validation is NOT runtime validation. For a healthcheck on a distroless image, separately assert the probe does not shell out to wget/sh AND (post-build) assert the container actually reaches `healthy` |
| "matches every existing service" reasoning for healthcheck form | Justified the wget array healthcheck because 4 sibling services use the identical form | The siblings run slim/alpine images (wget present); the new service runs distroless (wget absent) — the convention does not transfer across base-image families | Convention-matching is only valid when the BASE IMAGE family matches. Check the target service's runtime image before copying a sibling's healthcheck |
| Downgrade Grafana anon to Viewer instead of disabling | Kept `GF_AUTH_ANONYMOUS_ENABLED` on and set `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer` | Issue #206 asks to DISABLE anonymous access, not downgrade the anonymous role — anonymous read access still exists | To disable anonymous access set `GF_AUTH_ANONYMOUS_ENABLED: "false"`; downgrading the org role still leaves anonymous access open |
| Left `GF_AUTH_ANONYMOUS_ORG_ROLE` after disabling anon | Set `GF_AUTH_ANONYMOUS_ENABLED=false` but kept the org-role var | Once anonymous is off the role var is dead config; it misleads a reviewer into thinking anonymous is only downgraded | REMOVE `GF_AUTH_ANONYMOUS_ORG_ROLE` when disabling anonymous — it has no effect and obscures intent |
| Disabling Grafana anon without an admin credential | Set `GF_AUTH_ANONYMOUS_ENABLED=false` with no `GF_SECURITY_ADMIN_*` | With anon off Grafana falls back to the login screen; no usable credential means a locked-out e2e stack | Supply env-overridable admin creds (`${GRAFANA_ADMIN_USER:-admin}`/`${GRAFANA_ADMIN_PASSWORD:-admin}`) so the one-command e2e stack still logs in |
| Assuming `compose config` proves the Grafana health probe still works | Ran `compose config` (syntax OK) and treated it as proof `:3001/api/health` survives anon disable | `compose config` validates structure only — it never starts Grafana or curls health; the `/api/health`-unaffected claim is untested | Structural compose validation is NOT runtime validation. Actually `up -d grafana` + curl `/api/health` (expect `database=ok`) before claiming probes survive |
| Asserting configs are credential-less from the #176-era skill | Planned #208 assuming `configs/nats/*.conf` still ship with no TLS/auth | ADR-008 already added full TLS (`tls{}`, leafnodes port 7422 + tls, cluster tls, `/etc/nats/certs/`) to both configs | Re-read the canonical configs each session; a documented security gap may already be closed by a later ADR/PR |
| Writing `step ca ...` flags from memory | Plan used `step ca init/certificate/root/revoke` with specific flags, unrun | `step` subcommand flags vary by version and were never executed | Treat external CLI syntax as unverified; install/run the tool or mark every flag reviewer-must-verify |
| Claiming SIGHUP gives zero-downtime cert rotation | `kill -HUP <nats pid>` asserted to hot-reload TLS certs without JetStream loss | Reload-reads-certs-in-place behavior not exercised for the running NATS version | Tie any "zero-downtime" claim to a verified reload signal; if certs need a restart, dependent services (Agamemnon/Nestor) need manual restart too |
| Editing an append-only ADR for a back-link | Plan proposed adding a References line to ADR-008 | CLAUDE.md principle 3: ADRs are append-only / never edited once accepted | Link one-directionally (runbook→ADR); satisfy discoverability via the docs/README index row, not by editing the ADR |
| Trusting docs/README runbook table as complete | Used the README table as the runbook inventory | Table already omits `branch-protection-rollout.md` and `no-silent-failures.md` | The hand-maintained README table drifts; enumerate runbooks with `ls docs/runbooks/`, not the index |
| Trusting `/varz` `tls_required` field name from memory | Plan greps `curl :8222/varz \| ... d.get('tls_required')` to confirm TLS-on-client | The exact JSON key for "TLS required on client port" in the running NATS monitoring API was not confirmed | Don't assert monitoring-API JSON key names from memory; curl `/varz` against the running version and read the actual keys |
| Assuming Telemachy has a live `nats.connect()` to wire mTLS into | Planned to modify Telemachy's NATS client connection per issue #304 | `grep -rn "nats.connect\|import nats\|from nats" provisioning/ProjectTelemachy/src` returns NOTHING; `_monitor_completion` (executor.py:265-300) HTTP-polls Agamemnon, it is not a NATS subscriber | There is no connection site to modify. Satisfy "wire into the NATS client" at the CONFIG layer (`build_ssl_context()` + `nats_connect_kwargs()` helpers a future connection consumes), mirroring Hermes; grep for the connect call before assuming it exists |
| Asserting nats-py `tls=` kwarg "exactly as Hermes does" without verifying | Plan used `nats.connect(url, tls=ssl_ctx, tls_hostname=...)` claiming Hermes consumes `build_ssl_context()` at its connect site | Hermes `publisher.py:91 nats.connect(...)` was seen but the TLS-arg wiring was NEVER grepped; `build_ssl_context()` exists in Hermes config but its call site passing the context was not confirmed | Verify the exact nats-py kwarg (`tls` vs `tls_handshake_first`/`tls_hostname`) against the installed version AND confirm Hermes actually passes the context at a connect site before claiming "exactly as Hermes does" |
| Referencing ADR-009 as the governing decision | Issue #304 cites ADR-009; plan's runbook header links to it | `ls docs/adr \| grep 009` is empty — only 001-007 exist (008 referenced as "Proposed"); ADR-009 does NOT exist in the repo | Do NOT fabricate ADR-009. Either it lands in a sibling PR (#175/parent) or stop asserting it as present; verify ADR existence with `ls docs/adr` before citing |
| Assuming `docs/runbooks/enable-nats-auth.md` exists | Issue says Telemachy is "documented in enable-nats-auth.md (step 3)" as if present | `ls docs/runbooks/` shows it is ABSENT (present: add-new-agent-type, add-new-host, branch-protection-rollout, disaster-recovery, no-silent-failures, wsl2-podman-setup) | The plan CREATES the runbook; confirm ownership first — a Hermes/#175 PR may also create the same new file and collide. Enumerate runbooks with `ls docs/runbooks/`, never trust the issue body |
| Assuming `cryptography` is in Telemachy's pixi env for a test cert | Test plan generates a self-signed cert/key via `cryptography` "already transitively present" | `pixi.toml` lists pydantic, pydantic-settings, nats-py, pytest, pytest-asyncio, pytest-cov — `cryptography` was NOT seen as a direct dep | Don't assume a transitive dep is importable in tests; prefer a checked-in static throwaway PEM pair under `tests/fixtures/` (no runtime dep), or confirm `cryptography` is declared |
| Committing a test PEM fixture without checking `.gitignore` | Plan to commit a throwaway cert/key pair under `tests/fixtures/` | The team skill notes `.gitignore` covers `*.pem`/`*.key`/`*.crt`/`secrets/`/`*.secret` — which would BLOCK committing the fixture | A `.gitignore` that ignores cert keys conflicts with a checked-in test fixture; resolve with a scoped negation (`!tests/fixtures/*.pem`) and confirm the file is actually staged before relying on it |
| (R1, #304) Assumed Hermes passes `tls=` at its connect site | Planned to "wire it exactly as Hermes does", claiming Hermes consumes `build_ssl_context()` in its `nats.connect()` | VERIFIED: `grep -rn "tls=\|build_ssl_context\|ssl_context" infrastructure/ProjectHermes/src/` returns ONLY the method DEFINITION at `config.py:126`; `publisher.py:91-97` calls `nats.connect(...)` with NO `tls=` kwarg — Hermes has the SAME latent gap | Grep the actual call site before asserting a reference impl "already does X"; a defined-but-unused helper is a trap — there is no Hermes connect site to mirror |
| (R1, #304) Planned a checked-in PEM test fixture | Tried to source the test cert/key from a committed `tests/fixtures/*.pem` pair | VERIFIED: Telemachy `.gitignore:21-22` (`*.key`/`*.pem`) + root `.gitignore:7-9` (`*.key`/`*.pem`/`*.crt`) silently exclude it; AND `cryptography`/`trustme` BOTH `ModuleNotFoundError` in the pixi env | Generate the cert/key at test time with the `openssl` binary (on PATH, 3.6.2) into pytest `tmp_path` (ephemeral → `.gitignore` is moot); don't commit fixtures or add a `cryptography` dep |
| (R1, #304) Inspected `nats.connect` wrapper signature for `tls=` | `inspect.signature(nats.connect)` to confirm the mTLS kwargs | The module-level `nats.connect` wrapper does NOT expose those params (nor `__version__`); the params live on `nats.aio.client.Client.connect` | Inspect `nats.aio.client.Client.connect` — `tls`/`tls_hostname`/`tls_handshake_first` are confirmed there on nats-py 2.14.0, not on the wrapper |
| (R1, #304) Cited ADR-009 as the governing TLS decision | Linked docs at `docs/adr/009-nats-authentication-authorization.md` per the issue body | VERIFIED: `ls docs/adr/` shows 001–008 ONLY; 009 is ABSENT and `008-nats-tls-encryption…` is the real TLS ADR; `docs/runbooks/enable-nats-auth.md` also absent | Verify `ls docs/adr docs/runbooks` before citing; point docs at ADR-008 (which exists), not the unlanded sibling-PR ADR-009 |
| (R1, #304) Shipped an unconsumed `nats_connect_kwargs()` helper for AC1 | Returned a kwargs dict a hypothetical future `nats.connect()` caller would use, to satisfy "Telemachy connects to NATS" | A config builder nobody calls is YAGNI and does NOT make Telemachy connect; Telemachy has NO `nats.connect()` anywhere | Add the minimal REAL consumer — `connect_nats()` invoked from the CLI `run` path as a `tls://` preflight — not a helper for a hypothetical caller |
| (R2, #304) Adding a second `asyncio.run` (or import-time block) for the `tls://` preflight | Wanted to run the async `connect_nats()` preflight from the Typer `run` command, so reached for a fresh `asyncio.run(preflight())` (or a module-level block) | The `run` command (`cli.py:120`) ALREADY drives async via `_run_with_signals()` (`cli.py:141`); a second `asyncio.run` nests event loops (`RuntimeError`) and an import-time block runs before the command is even invoked | Insert the preflight INSIDE the existing `_run_with_signals()` wrapper — after the signal handlers, before the `async with AgamemnonClient(...)` at `cli.py:178`; reuse the existing loop, never open a second one |
| (R3, #304) Letting `ssl.SSLError`/`nats.errors.*` escape `asyncio.run()` from the mTLS preflight | Called `await nats.connect(url, tls=ctx, ...)` in the `tls://` preflight and let a failed handshake propagate straight out of `_run_with_signals()` / `asyncio.run()` | An unwrapped handshake failure surfaces as a bare traceback (POLA gap) and ignores the codebase's existing typed-error + `typer.Exit(1)` convention (`AgamemnonError` at `agamemnon_client.py:13`, failure style at `cli.py:68-80`) | Wrap `nats.connect(...)` in `try/except Exception` and re-raise a typed `NatsConnectionError` with an operator-guiding message at the helper boundary; catch it at the CLI boundary, print a red `console` line, and `raise typer.Exit(1)`. Mirror the typed-error convention from the start; never let raw `ssl.SSLError`/`nats.errors.*` escape an `asyncio.run()` entrypoint |
| (#328, planning) Trust the issue's cited file:line (`e2e/lib/nats.sh:157`) | Would have edited the wrong file to fix the restart race | `nats.sh` is 139 lines, pure curl-monitoring (no process mgmt); the real port-binding code is `e2e/lib/process.sh` (`start_nats_bg` at 64-79). The cited refs were auto-generated from a sibling PR branch | Grep the named symbols repo-wide before trusting issue line refs in #328-style auto-generated follow-up issues |
| (#328, planning) Poll only the client port free before relaunch | Reintroduces the exact flake | the monitor port `-m` bind fails on a lingering TIME_WAIT socket even after the client port is free | Free-poll BOTH ports; nats-server binds `-p` (`NATS_PORT`) AND `-m` (`NATS_MONITOR_PORT`) |
| (#328, planning) Rely on the free-poll alone (no retry) | TIME_WAIT can outlive the poll window so the bind still fails intermittently | nats-server exposes no `SO_REUSEADDR` to the caller | Add a bind-retry fallback loop; the health-wait is the authoritative gate, the free-poll is best-effort (`\|\| true`) |
| (#328, planning) Assume `nats_restart`/`nats_kill` already exist to patch | There is nothing to patch — `grep -rn` returns nothing | the A02 test `nats-crash-reconnect.sh` is PASSIVE (defers the kill as "topology-dependent"); the helpers are absent | The plan must SHIP the helper, not patch a poll loop; check parent PR #184 for whether they already landed on another branch (conflict risk) |
| (#328, R1) Use a `_NATS_PID` shell global to kill NATS from a fault test | Kills nothing — the global is empty in the test process | Each e2e test runs as a separate `bash "$script"` CHILD (`run-ipc-tests.sh:64`); NATS is started in the PARENT (`topology.sh:21` → `start_nats_bg`); the runner exports only PORTS not PIDs (`run-ipc-tests.sh:50`), so the child's freshly-sourced `_NATS_PID=""`. A no-op kill + relaunch on still-held ports makes the flake DETERMINISTIC | Cross-process kill needs a PID/meta FILE (port-keyed, under /tmp), not a shell global. Mirror the repo's existing PID-file idiom (`doctor.sh:292` aardvark.pid) |
| (#328, R1) Treat a port "free-poll" (`echo >/dev/tcp/localhost/$port` fails) as the fix for a TIME_WAIT bind race | Free-poll PASSES yet `bind()` still fails EADDRINUSE | A socket in TIME_WAIT has NO listener, so connect() refuses and the poll reports "free", but the kernel still RESERVES the port for ~2MSL → the relaunch bind fails anyway | The free-poll is latency-only, NOT a correctness gate. The real fix is bind-RETRY-with-backoff that outlasts the 2MSL window. Diagnose the actual kernel mechanism before picking the primary fix |
| (#328, R1) Restart NATS by calling a `start_nats_bg` that mktemps a fresh `--store_dir` each call | Silently discards JetStream state across the "clean restart" | A02/A01 assert message continuity (`nats_msg_count`, "messages flowing"); a new store_dir empties the streams | Record the original store_dir in the meta file and relaunch AT it (`start_nats_bg_at <dir>`); spot-check `nats_stream_exists` after restart |
| (#328, R1) Claim the A02 repro is fixed after the single-shell unit test passes | The unit test runs in ONE shell where the global IS visible; the real A02 runs cross-process and still breaks — masking the defect | The unit harness is not how A02 actually runs (`bash "$script"` fork) | Always exercise the REAL harness path (`run-ipc-tests.sh --topology t1 --test ...`), not just the convenient single-shell test, before claiming a parent/child bug is fixed |
| (#328, R2) Accept an issue's "TIME_WAIT race" hypothesis for a server-port rebind without measuring | Designed a fix around waiting out / polling past 2MSL | TIME_WAIT does not apply to LISTENING sockets — a SIGKILLed listener frees its port immediately (measured 8/8 instant rebinds). The 2MSL reservation only hits the ACTIVE-CLOSE side of an ESTABLISHED connection | MEASURE the actual rebind behavior with a tight kill→rebind loop before designing around a kernel-timing hypothesis; an issue body's root-cause guess can be wrong |
| (#328, R2) Treat bind-retry-with-backoff as needing to outlast 2MSL (~60s) | Sized a 1→2→4→8s backoff to "clear the TIME_WAIT window" | There is no TIME_WAIT window on the listener port; the only real gap is sub-second FD teardown after the killed PID is reaped | Make `wait`-for-process-exit the correctness gate; keep bind-retry as a thin sub-second margin, documented as NOT a 2MSL wait |
| (#328, R2) Call `nats_wait_healthy`/`nats_stream_exists` from a test that sources only common.sh + process.sh | Unit test would hit `command not found` under `set -e` | Those helpers live in `nats.sh` (`nats_wait_healthy` nats.sh:16, `nats_stream_exists` nats.sh:99, `nats_health` nats.sh:12), not common.sh/process.sh | Grep the helper's defining file before sourcing; source EVERY lib whose functions the test calls |

## Results & Parameters

```yaml
# Service ports
services:
  nats:    client=4222, monitoring=8222
  agamemnon: 8080
  nestor:    8081
  hermes:    8085  # NOT 8080 -- conflicts with Agamemnon
  prometheus: 9090 (or 19090 if conflicting)
  grafana:   3001 (or 13001)
  loki:      3100 (or 13100)
  argus-exporter: 9100

# Key environment variables
env_vars:
  NATS_URL:         "nats://<worker_ip>:4222"
  AGAMEMNON_URL:    "http://<worker_ip>:8080"
  NESTOR_URL:       "http://<control_ip>:8081"
  CONTROL_HOST_IP:  "<Tailscale IP of the control host>"
  WORKER_HOST_IP:   "<Tailscale IP of the worker host>"
  PYTHONPATH:       "src"   # required for Hermes

# NATS publish retry defaults (Python/nats-py)
nats_publish_retry:
  retries: 3
  base_delay: 0.1s          # doubles each attempt; cap at 2.0s
  jitter: "uniform(0.5, 1.5)"
  publish_timeout: 5.0s
  worst_case_total: ~15.3s

# Hermes supported webhook event types (_TASK_EVENTS allowlist)
hermes_event_types:
  - task.updated
  - task.completed
  - task.failed
  - "agent.*"
  # NOT supported (silently dropped): task.created

# Justfile recipes (per-component launchers)
recipes:
  install-worker:   "e2e/doctor.sh --role worker --install + submodule init"
  install-control:  "e2e/doctor.sh --role control --install + build Agamemnon/Nestor"
  start-nats:       "podman run -d --replace nats:alpine -js -m 8222"
  start-agamemnon:  "NATS_URL=... <build-root>/ProjectAgamemnon/ProjectAgamemnon_server"
  start-nestor:     "NATS_URL=... <build-root>/ProjectNestor/ProjectNestor_server"
  start-hermes:     "delegates to infrastructure/ProjectHermes justfile"
  start-myrmidon:   "NATS_URL=... python3 provisioning/Myrmidons/hello-world/main.py"
  start-argus:      "delegates to infrastructure/ProjectArgus justfile"
  start-console:    "python3 tools/odysseus-console.py"
```

### Uncertain Assumptions a Reviewer MUST Verify (NATS auth plan, issue #176)

This is the core value of the planning learning. A plan for NATS leaf/server auth in this
ecosystem is only as trustworthy as these unverified claims. A reviewer should treat each as
a blocking question, not a settled fact.

1. **Env-var substitution in `authorization { token = "$NATS_LEAF_TOKEN" }` — fail-closed is now
   TESTED, not assumed (R1 downgrade).** Previously the HIGHEST-RISK untested assumption; R1 adds a
   pinned `nats-server -t -c server.conf` run with the var UNSET that greps the rendered config for
   the leaked literal `$NATS_LEAF_TOKEN`. With that CI step the fail-closed behavior is verified, not
   hoped for. The residual risk is keeping that pinned check unconditional (never gate it on
   `command -v nats-server`) so it can't silently skip.
2. **Whether one shared token across client + all leaf nodes is acceptable** vs per-leaf
   `.creds`. A shared token is a shared secret with no per-leaf revocation. The plan documents
   `.creds` as recommended but ships a token fallback; the reviewer must confirm the bootstrap
   token is not silently becoming the permanent posture.
3. **The awk leafnode-block parser brittleness is RESOLVED in R1 by the brace-depth validator.**
   The original NOGO cause: a parser that ends the block on the first `}` closes the nested
   `tls {}`, not `leafnodes {}`, mis-declaring auth. R1 replaces it with the depth-tracking
   `block()` helper (counts `{` vs `}`, strips comments) prototyped this session — exit 0 on the
   fixed fixture, exit 1 on the current configs. Reviewer residual: confirm the validator is run in
   BOTH directions (rejects the bad config AND accepts the fix), never just the bad case.
4. **Cited line numbers may have drifted.** `server.conf:27-34`, `leaf.conf:34-37`,
   `justfile:258-266`, `ci.yml:11-55`, `deployment.md:152-161` were read once. Re-confirm each
   before editing.
5. **ADR-008 Status is "Proposed", not "Accepted".** The plan builds ADR-009 on top of an
   unaccepted ADR. Confirm the sequencing/numbering is still valid.
6. **`.gitignore` coverage of `.creds`/`certs` was FABRICATED in R0 — confirmed absent in R1.**
   `grep -n "certs\|creds\|nats" .gitignore` returns no matches; the R0 claim that the convention
   already ignored these paths was invented. The plan must ADD the `.gitignore` entries, not assume
   them. Lesson: grep the actual file before claiming a path is ignored.
7. **`just validate-configs` running in CI on `pull_request` was FALSE — confirmed in R1.**
   `ci.yml`'s validate job inlines its own steps and never invokes `just validate-configs` /
   `pixi run validate`. The gate does not exist until an explicit CI step is added (or the workflow
   is changed to call the recipe). Read `ci.yml` end-to-end; do not infer the invocation graph.
8. **Shared-token-vs-per-leaf-`.creds` posture risk REMAINS (R1, unresolved).** The plan still
   ships a `token` bootstrap fallback alongside the recommended per-leaf `.creds`. A shared token is
   a shared secret with no per-leaf revocation; the reviewer must confirm the bootstrap token is not
   silently becoming the permanent posture. This is the one reviewer-risk item the R1 prototype did
   NOT retire.

### Reviewer-risk + Meta-Lessons (planning learnings from the NOGO, R1)

These are the durable PLANNING lessons the NOGO cycle taught — independent of NATS specifics.

- **The single most valuable planning move was PROTOTYPING the validator before shipping the
  plan.** Running the brace-depth `block()` extractor against fixed + current fixtures turned "I
  think this works" into "exit 0 vs exit 1, verified." Plans that ship unvalidated shell/awk get
  NOGO'd on latent traps (here: the nested-`tls{}` brace).
- **Verify the CI invocation graph, not just file existence.** A gate wired into a `just` recipe is
  invisible to CI unless the workflow actually calls that recipe. Read `ci.yml` end-to-end.
- **Every line-number citation drifts.** The NOGO flagged `:27-39` vs the actual `:27-40`. Re-grep
  before citing; precision claims invite precision checks.
- **Fail-closed must be TESTED, not asserted.** The highest-risk assumption (unset
  `$NATS_LEAF_TOKEN` resolves empty, not to the literal string) only became believable once a pinned
  `nats-server -t` run was added that greps the rendered config for a leaked literal.
- **Negative-path verification needs BOTH directions.** Asserting only "rejects the bad config"
  hides a validator that rejects everything — including the fix. Assert exit 1 on broken AND exit 0
  on fixed.

**Distroless healthcheck planning lessons (R2, issue #154 — unverified, plan only):**

- **Before copying a sibling service's healthcheck, check the TARGET service's runtime base image.**
  wget/curl/sh healthchecks silently break on distroless (`gcr.io/distroless/static-*` has no
  shell/wget/busybox); the convention only transfers within the same base-image family.
- **`docker compose config` passing is NOT evidence a healthcheck works** — it validates structure,
  never executes the probe. A plan whose only health verification is `compose config` can be green
  while the acceptance criterion ("shows healthy") fails at runtime. Separately assert the container
  actually reaches `healthy` post-build.
- **When the healthcheck binary/flag is owned by a DIFFERENT issue than the compose wiring, the
  self-probe introduces a cross-issue coordination dependency** — name the `-healthcheck` flag
  explicitly as a blocking note, never assume it exists.
- **An issue body's verbatim YAML/code block is a desired end-state, not a guaranteed-correct
  literal** — it may encode a healthcheck that cannot run against the chosen runtime image. Re-derive
  correctness from the actual base image, don't copy blindly. (This generalizes the prior "issue
  snippet ≠ literal diff" lesson already in the skill from the duplicate-recipe learning.)

### Uncertain Assumptions a Reviewer MUST Verify (Grafana anon-access plan, issue #206 — unverified)

No container was run this session; these are blocking questions, not settled facts.

1. **HIGHEST RISK — `/api/health` is unauthenticated regardless of anon settings.** The plan claims
   disabling `GF_AUTH_ANONYMOUS_ENABLED` does NOT break the e2e health probes (`e2e/run-hello-world.sh`,
   `run-crosshost-e2e.sh`, `run-hermes-hub-e2e.sh`, `e2e/doctor.sh` all curl `:3001/api/health`). This
   was asserted from Grafana docs knowledge, NOT verified. Confirm at runtime that `/api/health` still
   returns `database=ok` with anon disabled. If false, every health-check-gated e2e phase fails.
2. **Provisioning survives login-required mode.** Dashboards/datasources are assumed file-provisioned
   via read-only `/etc/grafana/provisioning` mounts that do not depend on the anonymous API. Confirm
   provisioning still loads after login is required.
3. **`admin/admin` default posture.** Env-overridable defaults keep the e2e stack one-command, but the
   bootstrap default can silently become the permanent posture (same shape as the NATS shared-token
   risk). Name the trade-off so a reviewer can object.
4. **Scope boundary is correct.** Only `docker-compose.e2e.yml` at the Odysseus root changes. Confirm
   no other CANONICAL root compose file re-enables anonymous Grafana, that the overlays
   (`docker-compose.crosshost.yml`, `e2e/docker-compose.*.yml`) define no grafana service, and that
   ProjectArgus/ProjectKeystone (separate submodules) are correctly out of scope.
5. **`compose config` ≠ runtime proof.** Structural validation passing proves syntax only — it never
   starts Grafana or probes health. The health-probe-still-green claim needs an actual `up -d grafana`
   + curl, not config validation.
6. **Cited line numbers may have drifted.** `docker-compose.e2e.yml:154-155`, `:153-159`, `:160-162`,
   sibling `provisioning/ProjectKeystone/k8s/grafana.yaml:95,100-101`, `docs/e2e-walkthrough-report.md:290`
   were read once. Re-grep before editing.

### Uncertain Assumptions a Reviewer MUST Verify (NATS TLS security runbook, issue #208 — unverified)

No commands were run this session; these are blocking questions, not settled facts.

1. **THE CONFIGS CHANGED — re-read them (single most important correction).** The #176-era
   premise that `configs/nats/*.conf` ship with NO TLS is STALE. ADR-008 (Status: Proposed) is
   already merged: both `server.conf` and `leaf.conf` now carry top-level `tls {}`,
   `leafnodes { port=7422; tls{} }`, and cluster TLS referencing
   `/etc/nats/certs/{server-cert.pem,server-key.pem,ca.pem}`; leaf.conf's remote is now
   `nats+tls://<ip>:7422`. LESSON: re-read the canonical configs each session before asserting
   their security posture; a documented gap may already be closed by a later ADR/PR.
2. **`step` CLI command syntax was NOT verified.** `step ca init --name ... --dns ... --address :443
   --provisioner admin`, `step ca certificate <name> cert key --san <ip>`, `step ca root ca.pem`,
   and `step ca revoke --cert ...` were written from memory. `step ca init` flags in particular
   vary across versions — confirm against the installed `step` version.
3. **NATS SIGHUP cert reload was NOT verified.** The plan claims `kill -HUP <nats pid>` reloads TLS
   certs without dropping JetStream state. NATS supports config reload on SIGHUP, but whether it
   re-reads cert files in-place (vs requiring a full restart) for the running version was not
   exercised. If SIGHUP does not re-read certs, Scenario 2's "zero-downtime" claim inverts into a
   downtime + manual-restart procedure (and Agamemnon/Nestor must be restarted too).
4. **`/varz` `tls_required` field name unverified.** The exact JSON key for "TLS required on client
   port" in the running NATS monitoring API was not confirmed. Curl `/varz` and read the actual keys.
5. **ADR-008 Status is "Proposed", not "Accepted".** The plan operationalizes a Proposed ADR and
   treats its cert-path convention (`/etc/nats/certs/...`), permissions (key 600 / cert+ca 644), and
   three provisioning strategies as settled. Confirm ADR-008 is still the source of truth and has not
   been superseded.
6. **Append-only-ADR tension.** The plan's optional back-reference line into ADR-008's References
   conflicts with CLAUDE.md principle 3 (ADRs append-only / never edited). Drop it; link
   one-directionally (runbook → ADR); satisfy discoverability via the `docs/README.md` index row.
7. **Runbook-index drift observed (correct-discipline lesson).** `docs/README.md`'s runbook table
   (lines ~35-41) is MISSING existing runbooks `branch-protection-rollout.md` and
   `no-silent-failures.md`. Enumerate runbooks with `ls docs/runbooks/`, not the index table.
8. **`.gitignore` cert-key coverage — VERIFIED this time (contrast with #176's fabrication).** The
   claim that `*.pem`, `.env*`, `*.secret`, `secrets/` are git-ignored was actually grepped and is
   TRUE (`*.key`, `*.pem`, `*.crt`, `.env`, `.env*.local`, `secrets/`, `*.secret` all present). This
   is the correct discipline (grep the actual file) — directly reinforcing the #176 lesson that the
   earlier `.gitignore` claim was fabricated.

### Reviewer-risk + Meta-Lessons (NATS TLS runbook planning, issue #208 — unverified)

Durable PLANNING lessons that generalize beyond NATS:

- **A skill premise of the form "X has no security config" has a SHELF LIFE.** Security gaps get
  closed by other issues/ADRs between sessions. Verify the current file state before building a plan
  on top of a documented gap — here, ADR-008 had already added TLS the #176-era skill said was absent.
- **External CLI command syntax written from memory is an unverified-assumption CLASS.** `step`,
  `nats-server` flags, and monitoring-API JSON keys must each be flagged reviewer-must-verify, never
  presented as fact. Install/run the tool or mark every flag uncertain.
- **A "zero-downtime rotation" claim hinges on whether the daemon HOT-RELOADS certs.** If it does
  not, the claim inverts into a downtime + manual-restart procedure. Always tie the reload mechanism
  to a verified signal/behavior before claiming zero downtime.

### Reviewer Verification Status (Telemachy NATS client-cert mTLS, issue #304 — R1 facts VERIFIED-LOCAL; R2 insertion point; R3 two POLAs resolved)

R1 (post-NOGO) converted most of the R0 reviewer-risks into verified-local facts. Only items 1 and 4
remain genuine reviewer questions; the rest are now settled-this-session.

1. **STILL A REVIEWER QUESTION — config-layer wiring vs a live connection (acceptance criterion).**
   Telemachy has NO `nats.connect()` (VERIFIED: grep returns nothing; `_monitor_completion`
   HTTP-polls Agamemnon). A config-builder ALONE cannot satisfy AC1 "Telemachy connects to a NATS
   server with verify_and_map=true". The R1 honest fix ADDS a minimal REAL consumer —
   `connect_nats()` invoked from the CLI `run` path as a `tls://` preflight handshake — rather than
   shipping an unconsumed `nats_connect_kwargs()` helper (YAGNI, flagged in the NOGO). **R2 UPDATE:
   the R1 plan PASSED review (no new NOGO)** — the preflight-handshake consumer was ACCEPTED as the
   intended scope, and the insertion point is now CONFIRMED: inside the existing `_run_with_signals()`
   wrapper (`cli.py:141`, used by `run` at `:120`), after the signal handlers and before the
   `async with AgamemnonClient(...)` block (`cli.py:178`). No second `asyncio.run`. **R3 UPDATE — the
   two remaining MINOR POLA questions are RESOLVED in-plan (design/framing, nothing newly run):**
   (a) the preflight's failure path now wraps `nats.connect(...)` and re-raises a typed
   `NatsConnectionError` (mirroring `AgamemnonError` at `agamemnon_client.py:13`) that the CLI catches
   and exits via `typer.Exit(1)` (`cli.py:68-80` style), so no bare traceback escapes `asyncio.run()`;
   a unit test monkeypatches `nats.connect` to raise `ssl.SSLError` and asserts the typed error.
   (b) "is a handshake-only preflight really connecting?" is answered by framing it as a DELIBERATE,
   DOCUMENTED, fail-closed verification gate (intent in docstring + CLI comment + CLAUDE.md env-var
   row + runbook; the single real connection site; hard-fail on rejection, complementing
   `agamemnon_client.py`'s `require_tls`) — design intent in code+docs, NOT more code or a narrowed
   AC. The plan is now A/B-clean.
2. **nats-py connect kwargs — VERIFIED-LOCAL (R1, #304).** On **nats-py 2.14.0**
   (`importlib.metadata.version('nats-py')`), `inspect.signature(nats.aio.client.Client.connect)`
   confirms `tls`, `tls_hostname`, AND `tls_handshake_first` are real parameters, so
   `nats.connect(url, tls=ctx, tls_hostname=host)` is correct. CAVEAT: inspect
   `nats.aio.client.Client.connect`, NOT the module-level `nats.connect` wrapper (which exposes
   neither these params nor `__version__`). The "exactly as Hermes does" analogy is FALSE-CONFIRMED:
   Hermes does NOT pass `tls=` at its connect site (`publisher.py:91-97`), only DEFINES
   `build_ssl_context()` at `config.py:126`.
3. **ADR-009 does NOT exist — VERIFIED-LOCAL (R1, #304).** `ls docs/adr/` shows 001–008 only; 008 is
   the NATS TLS encryption ADR. The issue cites `009-nats-authentication-authorization.md` as
   governing — it is absent. Point docs at ADR-008 (which exists); do NOT fabricate ADR-009 (may land
   via #175/parent).
4. **STILL A REVIEWER QUESTION — `docs/runbooks/enable-nats-auth.md` does NOT exist (VERIFIED absent,
   R1).** The issue references it as if present; the plan would CREATE it. If a Hermes/#175 PR also
   creates the same new file, the two PRs collide — confirm ownership of `enable-nats-auth.md` before
   creating it.
5. **Test-cert sourcing — VERIFIED-LOCAL (R1, #304).** `cryptography` AND `trustme` BOTH
   `ModuleNotFoundError` in the Telemachy pixi env, and the `.gitignore` (`*.pem`/`*.key`/`*.crt` at
   both root `:7-9` and Telemachy `:21-22`) BLOCKS a committed fixture. CONFIRMED solution: generate
   the cert/key with the `openssl` binary (on PATH, OpenSSL 3.6.2) into pytest `tmp_path`; the test
   then exercises `load_cert_chain` (raises `ssl.SSLError` on a malformed cert) — strictly deeper than
   Hermes' `test_tls_config.py`, which uses a NON-EXISTENT `/fake/ca.pem` and never loads a chain.
6. **Hermes/Telemachy line-number citations may have drifted.** `config.py:126`, `publisher.py:91-97`,
   Telemachy `executor.py:265-300`, the two `.gitignore` ranges — all read once this session. Re-grep
   before editing; precision claims invite precision checks.

```yaml
# Telemachy NATS client-cert mTLS wiring — issue #304 (R1 facts VERIFIED-LOCAL; R2 insertion point; R3 POLA resolutions)
telemachy_mtls_plan:
  load_bearing_finding: "VERIFIED: Telemachy has NO live nats.connect() — _monitor_completion HTTP-polls Agamemnon (executor.py:265-300)"
  approach: "ADD a minimal REAL consumer connect_nats() (CLI run tls:// preflight) — NOT an unconsumed nats_connect_kwargs() helper (YAGNI, NOGO-flagged)"
  proves: "client-cert LOADING path (load_cert_chain raises ssl.SSLError on malformed PEM) — DEEPER than Hermes test_tls_config.py (uses /fake/ca.pem, never loads a chain)"
  hermes_analogy: "VERIFIED FALSE: Hermes build_ssl_context() is DEFINED-BUT-UNUSED (config.py:126); publisher.py:91-97 nats.connect(...) passes NO tls= — same latent gap, no connect site to mirror"
  nats_py_kwargs: "VERIFIED on nats-py 2.14.0: nats.aio.client.Client.connect accepts tls/tls_hostname/tls_handshake_first — inspect Client.connect, NOT the nats.connect wrapper"
  adr: "VERIFIED: ADR-009 does NOT exist (ls docs/adr/ -> 001-008); 008 IS the NATS TLS ADR — point docs at 008, do NOT fabricate 009 (may land via #175/parent)"
  runbook: "VERIFIED absent: docs/runbooks/enable-nats-auth.md — plan CREATES it; confirm ownership vs a colliding #175 PR"
  test_cert_source: "VERIFIED: cryptography AND trustme both ModuleNotFoundError; .gitignore blocks *.pem/*.key/*.crt — generate via openssl binary (3.6.2, on PATH) into pytest tmp_path"
  acceptance_risk: "config-builder ALONE cannot meet AC1; add the real consumed connect_nats() preflight — confirm a preflight (vs full subscriber) is the intended scope"
  insertion_point: "VERIFIED-LOCAL (R2): preflight goes INSIDE _run_with_signals() (cli.py:141, used by run at :120), after signal handlers, BEFORE async with AgamemnonClient(...) (cli.py:178) — NO second asyncio.run / import-time block"
  failure_handling: "R3 POLA fix: connect_nats() wraps nats.connect() and re-raises typed NatsConnectionError (mirrors AgamemnonError, agamemnon_client.py:13); CLI catches it, prints red console line, raise typer.Exit(1) (cli.py:68-80 style) — no bare traceback out of asyncio.run; test monkeypatches nats.connect->ssl.SSLError, asserts typed error"
  preflight_framing: "R3 POLA fix: handshake-only preflight = a DELIBERATE, DOCUMENTED, fail-closed verification gate (intent in docstring+CLI comment+CLAUDE.md row+runbook; single real connect site; hard-fail on rejection, complements agamemnon_client.py require_tls) — design intent, NOT a probe or a narrowed AC"
  review_outcome: "R2: R1 plan PASSED review (no new NOGO); preflight scope ACCEPTED. R3: the two MINOR POLA findings from R2's narrow B/NOGO are RESOLVED in-plan -> plan now A/B-clean"
  verification: "unverified overall (no CI); R3 is a design/framing round — nothing newly executed, no new external claims/deps; prior verified-local facts unchanged"
```

```yaml
# PROPOSED Grafana anon-hardening env (docker-compose.e2e.yml grafana service) — issue #206
grafana_anon_hardening_env:
  GF_AUTH_ANONYMOUS_ENABLED:    "false"                          # disable anonymous access
  # REMOVE GF_AUTH_ANONYMOUS_ORG_ROLE — dead config once anon is off
  GF_SECURITY_ADMIN_USER:       "${GRAFANA_ADMIN_USER:-admin}"   # login fallback; env-overridable
  GF_SECURITY_ADMIN_PASSWORD:   "${GRAFANA_ADMIN_PASSWORD:-admin}"  # deliberate default trade-off
  scope:           "docker-compose.e2e.yml at Odysseus root ONLY (overlays/submodules out of scope)"
  load_bearing_assumption: "/api/health stays unauthenticated with anon off — UNTESTED, confirm at runtime"
  runtime_check:   "podman compose -f docker-compose.e2e.yml up -d grafana && curl :3001/api/health  # expect database=ok"
  verification:    "unverified — no container run; compose config validates syntax only, not health"
```

```yaml
# PROPOSED NATS TLS security runbook (docs/runbooks/nats-security.md + docs/README row) — issue #208
nats_tls_runbook:
  premise: "configs NOW carry TLS per ADR-008 (Proposed) — NOT credential-less; runbook operationalizes existing TLS"
  cert_paths: "/etc/nats/certs/{server-cert.pem,server-key.pem,ca.pem}"
  permissions: "key 600; cert+ca 644"
  provisioning: "step-ca — step CLI flags UNVERIFIED (init/certificate/root/revoke; vary by version)"
  rotation: "Scenario 2 = SIGHUP hot-reload — UNVERIFIED whether NATS re-reads cert files in place; if not, full restart + restart Agamemnon/Nestor"
  compromise: "Scenario 3 = revoke cert (+rotate CA if CA key compromised), re-issue, push canonical configs, reload/restart"
  tls_required_check: "curl :8222/varz | d.get('tls_required') — JSON key name UNVERIFIED"
  adr_link: "one-directional runbook->ADR-008 ONLY; ADRs are append-only — do NOT edit ADR-008"
  runbook_index: "add ONE row to docs/README.md; enumerate runbooks via `ls docs/runbooks/` (README table drifts)"
  gitignore: "VERIFIED grepped: *.pem,*.key,*.crt,.env,.env*.local,secrets/,*.secret all present"
  verification: "unverified — no commands run, no CI; step/SIGHUP/varz claims written from memory"
```

```yaml
# PROPOSED NATS auth env vars (mirror existing $NATS_MONITORING_PASSWORD pattern)
nats_auth_env_vars:
  NATS_LEAF_TOKEN:        "$ENV — bootstrap fallback only; MUST fail closed if unset"
  NATS_CLIENT_USER:       "$ENV"
  NATS_CLIENT_PASSWORD:   "$ENV"
  # Preferred over token: per-leaf NKey/JWT .creds at /etc/nats/creds/leaf.creds (revocable)

# PROPOSED fail-closed lint (shell, wired into `just validate-configs`, NOT pytest)
config_auth_gate:
  runner: "just validate-configs — MUST be invoked by an EXPLICIT ci.yml step"
  ci_invocation: "ci.yml inlines its own steps; it does NOT call the recipe today — add the step"
  must_strip_comments_before_grep: true     # else a commented example passes
  brace_depth_extraction: true              # block() counts {/} — nested tls{} must not close early
  assert_per_block: true                    # leafnodes{} needs its own authorization{}
  assert_both_directions: true              # exit 1 on broken config AND exit 0 on the fix
  fail_closed_test: "NATS_LEAF_TOKEN= nats-server -t -c server.conf | grep -q '$NATS_LEAF_TOKEN'"
  nats_server_in_ci: "pinned release, run UNCONDITIONALLY (never `command -v` guard)"
  ports:
    leaf_remote: 7422                        # never 4222
  adr: "new ADR-009 (append-only); never edit accepted ADRs"
  validator_status: "prototyped verified-local: exit 0 on fixed fixture, exit 1 on current configs"
```

### Verified-Local Implementation Facts (NATS e2e SIGKILL→restart, issue #328 — VERIFIED-LOCAL R3)

R3 implemented and unit-tested the fix. 15/15 tests pass including an 8× kill→restart→healthy loop.
CI has not yet confirmed. The 10 facts below are all CONFIRMED BY RUNNING CODE this session.

**R2 verified-local base (kernel mechanism, still applies):**

- **The kill→rebind experiment: 8/8 immediate rebinds, zero failures, zero delay** (ports 14299/18299,
  `nats-server` at `~/.local/bin/nats-server`). TIME_WAIT does NOT apply to a LISTENING socket — a
  SIGKILLed listener frees its port immediately. The 2MSL reservation only afflicts the ACTIVE-CLOSE
  side of an ESTABLISHED connection (a client/peer socket), never the listener.
- `nats-server --help`: NO SO_REUSEADDR / address-reuse flag exists; `-sl/--signal` accepts only
  `ldm,stop,quit,term,reopen,reload` (none defeat TIME_WAIT, none needed); `-p`=client, `-m`=http
  monitor, `-ms`=https monitor.
- The NATS helpers live in `e2e/lib/nats.sh`: `nats_health` :12, `nats_wait_healthy` :16,
  `nats_msg_count` :27, `nats_stream_exists` :99 — NOT in common.sh/process.sh.
- `e2e/tests/fault/nats-crash-reconnect.sh:8` already sources `nats.sh` (so it needs `process.sh`
  ADDED, not `nats.sh`).
- `e2e/run-ipc-tests.sh:64` forks each test via `bash "$script"`; line 50 exports ONLY
  `AGAMEMNON_PORT NATS_PORT NATS_MONITOR_PORT HERMES_PORT IPC_TOPOLOGY` (no PIDs).
- `_NATS_PID` is EMPTY across the parent→child process boundary, confirming the root cause.

**R3 newly confirmed implementation facts (all VERIFIED-LOCAL by unit test 15/15):**

| # | Implementation fact | VERIFIED-LOCAL by |
|---|---------------------|-------------------|
| 1 | Root cause is confirmed stale-process race, NOT TIME_WAIT. `_NATS_PID` is empty across parent→child boundary (`run-ipc-tests.sh:64` runs tests as `bash "$script"`); prior kill no-opped → relaunch raced still-alive original server. VERIFIED by 8/8 immediate rebinds after SIGKILL with no port-free poll | 8/8 kill→rebind experiment + unit test |
| 2 | `start_nats_bg` writes PID + store_dir to `/tmp/hi-nats-${NATS_MONITOR_PORT}.meta`. Child processes read it via `nats_meta_pid()` / `nats_meta_store_dir()`. Works cross-process | unit test meta-file round-trip test |
| 3 | `nats_kill()` SIGKILLs the meta-file PID then `wait`s for full exit (FD release). `wait` on non-child returns 127; fall back to bounded `kill -0` poll (20× 0.1s). This kill-then-wait IS the correctness gate — not the port-free poll | unit test kill-then-wait test |
| 4 | `wait_port_free` must be wired into `nats_restart` at BOTH call sites: after initial `nats_kill` before the loop AND after `nats_kill` inside each retry iteration, for both NATS_PORT and NATS_MONITOR_PORT. Use `|| true` since port usually frees instantly. Reviewer caught the YAGNI risk if only in unit tests | code review + implementation |
| 5 | `wait_port_free` needs `timeout 1 bash -c "..."` guard on WSL2 — `/dev/tcp/localhost/PORT` to a closed port HANGS (does not fail fast) on WSL2/some kernels | WSL2 behavior confirmed |
| 6 | Skip blocks in unit tests need explicit `exit $?` — under `set -euo pipefail`, `exit_code` only RETURNS a status (common.sh:41), it does NOT terminate the script. Without `exit $?`, a skip block falls through to the next section and fails on `start_nats_bg` when `nats-server` is absent | unit test skip test |
| 7 | A02 active path needs meta-file guard: `[ -n "$(nats_meta_pid)" ]` before the active kill+restart block; `skip` otherwise. Running `nats-crash-reconnect.sh` standalone (without `start_nats_bg` in the same process) leaves `nats_meta_pid` empty → `nats_kill` no-ops → `nats_restart` falls back to mktemp store_dir → false-passes "JetStream stream survived restart" | implementation + guard test |
| 8 | `start_nats_bg` must be split into `start_nats_bg` (allocates fresh mktemp dir) + `start_nats_bg_at <dir>` (launches at explicit dir AND writes the meta file). `nats_restart` calls `start_nats_bg_at` with the ORIGINAL store_dir so JetStream is preserved | unit test 8× restart loop (stream exists after each restart) |
| 9 | Loop variable clobbering — inner functions called from `for i in $(seq 1 8)` loops (like `wait_for` in common.sh) have their own `for i in` that overwrite the outer `$i`. Use unique loop variable (`_t5`) and track iteration with separate counter (`LOOP_ITER`) | unit test loop test |
| 10 | `nats-crash-reconnect.sh` must source `process.sh` — it already sources `nats.sh` (line 8) but `nats_kill`/`nats_restart`/`nats_meta_pid` live in `process.sh`. Add `source "$(dirname "$(dirname "$SCRIPT_DIR")")/lib/process.sh"` after the common.sh line | implementation |

**Files changed (R3):**
- `e2e/lib/process.sh` — meta-file helpers, `start_nats_bg` split, `wait_port_free`, `nats_kill`, `nats_restart`, updated `cleanup_all`
- `e2e/tests/fault/nats-crash-reconnect.sh` — added `source process.sh`, replaced passive A02 with active kill+restart + meta-file guard + passive fallback
- `e2e/tests/unit/test-nats-restart.sh` (NEW) — 15-test unit covering port-free poll, meta-file round-trip, kill-then-wait, 8× restart loop

**Remaining uncertain (CI not yet run):**

| # | Item | Status |
|---|------|--------|
| 1 | CI confirmation | Not yet — verified-local only (15/15 unit tests, 8/8 restart loop) |
| 2 | `pixi run bash` / `pixi run shellcheck` wiring | UNCONFIRMED — harness runs via `bash e2e/run-ipc-tests.sh` |
| 3 | Parent PR #184 merge-conflict risk | `nats_restart`/`nats_kill` did not exist on main; check PR #184 for collision |
| 4 | The meta-file approach under concurrent T1 runs | Assumes a SINGLE NATS instance per `NATS_MONITOR_PORT`; no concurrent collisions expected |

### Reviewer-risk + Meta-Lessons (NATS e2e restart, issue #328 — VERIFIED-LOCAL R3)

- **META-LESSON (most durable): MEASURE a kernel/OS-timing hypothesis before architecting around it.**
  When an issue body hands you a root-cause guess involving kernel/OS timing (TIME_WAIT, 2MSL, races),
  run a tight reproduction FIRST — and especially before a reviewer escalates the hypothesis into a
  blocking "your mechanism can't outlast X" major. A 10-line bash kill→rebind loop dissolved a
  load-bearing NOGO finding here by proving the premise was false. **Distinguish LISTENING-socket
  teardown (immediate on SIGKILL) from ESTABLISHED-connection active-close (2MSL TIME_WAIT) — they are
  different sockets with different lifecycles.**
- **TIME_WAIT does NOT apply to your own listening socket.** The 2MSL reservation only afflicts the
  endpoint that did an ACTIVE CLOSE of an ESTABLISHED connection (a client/peer). A SIGKILLed server
  frees its LISTEN port immediately; no `SO_REUSEADDR`, no port free-poll, no 2MSL wait is needed.
- **The real defect was a stale-process race, not a kernel-timing race.** R1's empty `_NATS_PID` left
  the original server ALIVE, so the relaunch raced a still-bound socket. Fix: kill the RIGHT pid via a
  port-keyed PID/meta FILE, then `wait` for full process EXIT (FD release) before relaunch — that
  `wait` is the correctness gate; bind-retry is only a sub-second teardown margin.
- **Map the process boundary FIRST (carried from R1).** A shell global that works in one shell
  silently no-ops across `bash "$script"`; map who forks whom and what is exported before designing
  PID/state handling.
- **Source EVERY lib whose helpers a test calls.** `nats_wait_healthy`/`nats_stream_exists` live in
  `nats.sh`, not common.sh/process.sh — grep the defining file before sourcing or hit `command not
  found` under `set -e`.
- **A "clean restart" that mktemps a fresh store_dir is a silent data-loss bug.** A01/A02 assert
  message continuity; relaunch AT the recorded `--store_dir` and spot-check the stream survives.
- **Always exercise the REAL harness path before claiming a parent/child bug is fixed.** A
  single-shell unit test where the global IS visible is a FALSE POSITIVE for a cross-process defect.

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | 2026-04-03 Cross-host compose overlay | Two-host deployment: epimetheus (worker) + control host; full 6-phase validation PASS 2026-04-06 |
| HomericIntelligence/Odysseus | 2026-04-04 Per-component launchers | 9 justfile recipes; commit 82742b7 on feat/crosshost-e2e-pipeline |
| HomericIntelligence/Odysseus | 2026-04-20 Hermes-hub topology | Hub+remote-worker scripts written; validated 2026-04-27 in Atlas session |
| HomericIntelligence/Odysseus | 2026-04-21 E2E compose pipeline | 10-container stack; all 7 phases passing on podman + docker; PR #117 |
| HomericIntelligence/Odysseus | 2026-04-24 NATS publish retry | Full retry loop with jitter verified in CI (ProjectHermes) |
| HomericIntelligence/Odysseus | 2026-05-03 Atlas 6-host cold-start | 6 hosts started (4 podman, 1 pixi native, 1 docker); Agamemnon API confirmed |
| Odysseus | Plan for issue #176 (NATS leaf auth) | unverified plan — no code run, no CI; value is the reviewer-risk catalogue of uncertain assumptions |
| Odysseus | Plan R1 for issue #176 (NATS leaf auth, post-NOGO) | validator prototyped verified-local (brace-depth `block()`: exit 0 on fixed fixture, exit 1 on current configs); full plan still unverified |
| Odysseus | Plan R2 for issue #154 (Argus distroless dashboard healthcheck, post-NOGO) | unverified planning learning — distroless `static` images have no shell/wget; use binary self-probe `["CMD","/<binary>","-healthcheck"]`; `docker compose config` validates structure only. No container built or observed healthy |
| Odysseus | Plan for issue #206 (Grafana anonymous-access hardening, docker-compose.e2e.yml) | unverified planning learning — disable `GF_AUTH_ANONYMOUS_ENABLED`, remove dead `GF_AUTH_ANONYMOUS_ORG_ROLE`, add env-overridable admin creds. Load-bearing untested assumption: `/api/health` stays unauthenticated with anon off so e2e probes survive. No container run |
| Odysseus | Plan for issue #208 (NATS TLS security runbook — cert provisioning, rotation, compromise) | unverified planning learning — adds `docs/runbooks/nats-security.md` + README row. KEY correction: ADR-008 already added TLS to the configs (the #176-era "credential-less" premise is stale). `step` flags, SIGHUP cert hot-reload, and `/varz` `tls_required` key all written from memory (reviewer-must-verify). `.gitignore` cert-key coverage VERIFIED grepped. No commands run |
| ProjectTelemachy | Plan for issue #304 (NATS client-cert mTLS wiring) | unverified planning learning — LOAD-BEARING FINDING: Telemachy has NO live `nats.connect()` (`_monitor_completion` HTTP-polls Agamemnon), so the plan wires mTLS at the CONFIG layer (`build_ssl_context()` + `nats_connect_kwargs()`, mirroring Hermes) and proves only the client-cert LOADING path. nats-py `tls=` kwarg + Hermes' connect-site consumption assumed-by-analogy (unverified). ADR-009 and `docs/runbooks/enable-nats-auth.md` both cited by the issue but do NOT exist in the repo. `cryptography` test-dep unverified; committing a PEM fixture conflicts with `.gitignore`. No code run |
| ProjectTelemachy | Plan R1 for issue #304 (NATS client-cert mTLS, post-NOGO) | R1 VERIFIED-LOCAL (no CI): Hermes `build_ssl_context()` is DEFINED-BUT-UNUSED (`config.py:126`); `publisher.py:91-97 nats.connect(...)` passes NO `tls=` — the "exactly as Hermes does" analogy mirrors a connect site that does not exist. nats-py **2.14.0** `nats.aio.client.Client.connect` confirmed to accept `tls`/`tls_hostname`/`tls_handshake_first` (inspect `Client.connect`, NOT the `nats.connect` wrapper). `cryptography`+`trustme` both ModuleNotFoundError and `.gitignore` blocks `*.pem`/`*.key`/`*.crt` → generate certs via the `openssl` binary (3.6.2) into pytest `tmp_path`. ADR-009 absent (`ls docs/adr/` -> 001-008; 008 IS the TLS ADR); `enable-nats-auth.md` absent. AC1 needs a real consumed `connect_nats()` (`tls://` preflight), NOT an unconsumed helper (YAGNI). Stacks on #2717's v1.6.0 |
| ProjectTelemachy | Plan R2 for issue #304 (NATS client-cert mTLS, plan APPROVED) | R2 (PATCH, no CI): the R1 plan PASSED review — no new NOGO; preflight-handshake scope ACCEPTED. CONFIRMED insertion point (verified-local): the `tls://` preflight goes INSIDE the existing `_run_with_signals()` async wrapper (`cli.py:141`, used by the `run` command at `:120` with SIGINT/SIGTERM handlers + a Rich `Progress` context), after the signal handlers and BEFORE the `async with AgamemnonClient(...)` block (`cli.py:178`); do NOT add a second `asyncio.run` or block at import time. Stacks on #2717 (v1.6.0) and #2720 (v1.7.0) |
| HomericIntelligence/Odysseus | Plan for issue #328 (NATS e2e SIGKILL→restart port-bind-race) | UNVERIFIED planning learning — no code run, no unit test executed, no CI. FIX DESIGN: a `wait_port_free` helper (port is free only when it REFUSES connections) gating BOTH `NATS_PORT` and `NATS_MONITOR_PORT` before relaunch, PLUS a bind-retry fallback loop (no `SO_REUSEADDR` exposed to callers; health-wait is the authoritative gate; `\|\| true` on the free-poll masks no assertion). VERIFIED-LOCAL premise greps: the issue's cited `e2e/lib/nats.sh:157`/`nats_restart`/`nats_kill` refs are STALE (nats.sh is 139 lines of pure curl-monitoring); the real port code is `e2e/lib/process.sh` (`start_nats_bg` 64-79; `NATS_PORT=14222`/`NATS_MONITOR_PORT=18222`); the restart helpers DO NOT EXIST yet and the A02 test `nats-crash-reconnect.sh` is PASSIVE (so the plan SHIPS the helper — check parent PR #184 for conflicts). UNREPRODUCED: the TIME_WAIT-on-monitor causal chain (issue author's hypothesis). Tooling (`pixi run shellcheck`/`bash`) unconfirmed; harness runs via `e2e/run-ipc-tests.sh` |
| HomericIntelligence/Odysseus | Plan R1 for issue #328 (NATS e2e SIGKILL→restart, post-NOGO/grade D) | UNVERIFIED planning learning — no code run; the corrected unit test was DESIGNED but never executed; the real cross-process A02 was not run; no CI. CORRECTED ROOT CAUSE: a PROCESS-MODEL defect, not a TIME_WAIT race — each e2e test is a forked `bash "$script"` CHILD (`run-ipc-tests.sh:64`) and the runner exports PORTS not PIDs (`run-ipc-tests.sh:50`), so a `_NATS_PID` shell global is EMPTY in the child and the kill no-ops, making the flake DETERMINISTIC. The R0 free-poll was misdiagnosed as the fix: a TIME_WAIT socket reports "free" to a connect-poll yet still fails `bind()` for ~2MSL (latency-only, NOT a correctness gate). CORRECTED FIX: a port-keyed PID/meta FILE under /tmp (mirror `doctor.sh:292` aardvark.pid) for cross-process kill; a store_dir-PRESERVING `start_nats_bg_at <dir>` relaunch (the existing `start_nats_bg` mktemps a fresh `--store_dir` each call → silently empties JetStream the A01/A02 continuity asserts need); and bind-RETRY-with-backoff (1→2→4→8s) as the correctness gate. RESIDUAL RISK: ~15s backoff may NOT outlast Linux default 2MSL ≈ 60s. VERIFIED-LOCAL: `topology.sh:21` starts NATS in the PARENT; `process.sh` `_kill_if_alive` 16-24 / `cleanup_all` 120-123; `common.sh:127` `topology_supports`; `pkill -f` precedent `start-hermes-hub.sh:197`. META-LESSON: map the process boundary BEFORE designing PID/state handling, and separate latency-optimization from correctness-gate explicitly. Check parent PR #184 (helpers absent on main) |
| HomericIntelligence/Odysseus | Plan R2 for issue #328 (NATS e2e SIGKILL→restart, MEASURED root cause overturns the issue, post-NOGO/grade C) | UNVERIFIED OVERALL (no CI; unit test + real A02 not run) but the CORE KERNEL MECHANISM is VERIFIED-LOCAL: a tight kill→rebind loop (`nats-server -js -p 14299 -m 18299`, await `/healthz`, `kill -KILL`, IMMEDIATE relaunch on the SAME ports, NO free-poll/NO sleep) gave **8/8 immediate rebinds, zero failures, zero delay**. DURABLE FACT: TIME_WAIT does NOT apply to a server's own LISTENING socket — a SIGKILLed listener frees its port immediately; the 2MSL reservation only hits the ACTIVE-CLOSE side of an ESTABLISHED connection (a client/peer), never the listener you rebind. This OVERTURNS the issue's monitor-port TIME_WAIT hypothesis AND a prior reviewer's load-bearing "~15s backoff can't outlast 2MSL ~60s" major. The ACTUAL defect is a STALE-PROCESS RACE compounded by R1's empty cross-process `_NATS_PID` (the kill no-opped, the old server stayed alive, the relaunch raced a still-bound socket); real fix = kill the RIGHT pid via a port-keyed PID/meta FILE + `wait` for full process EXIT (FD release) before relaunch — bind-retry (3×/1s) is a sub-second teardown margin, NOT a 2MSL wait. Also VERIFIED-LOCAL: `nats-server --help` has NO SO_REUSEADDR flag and `-sl/--signal` only `ldm,stop,quit,term,reopen,reload`; the NATS helpers live in `e2e/lib/nats.sh` (`nats_wait_healthy` :16, `nats_stream_exists` :99, `nats_health` :12, `nats_msg_count` :27) so a test sourcing only common.sh+process.sh hits `command not found`; `nats-crash-reconnect.sh:8` already sources `nats.sh` (needs `process.sh` ADDED). META-LESSON: MEASURE a kernel/OS-timing hypothesis with a tight reproduction before architecting around it — a 10-line bash loop dissolved a load-bearing NOGO by proving the premise false. Residual: plan unverified overall; `nats_kill`'s `wait`→`kill -0` fallback path unverified; CI-runner kernel assumed identical; parent PR #184 may collide |
| HomericIntelligence/Odysseus | Implementation R3 for issue #328 (NATS e2e SIGKILL→restart, VERIFIED-LOCAL — unit test 15/15, 8/8 kill→restart→healthy loop; CI not yet confirmed) | R3 converts the R2 plan from UNVERIFIED to VERIFIED-LOCAL. The 10 confirmed implementation facts: (1) root cause is confirmed stale-process race (not TIME_WAIT) — `_NATS_PID` empty across parent→child boundary; (2) port-keyed meta file (`/tmp/hi-nats-${NATS_MONITOR_PORT}.meta`) carries PID + store_dir cross-process; `nats_meta_pid()` / `nats_meta_store_dir()` read it; (3) `nats_kill` SIGKILL + bounded `kill -0` poll (20× 0.1s) is the correctness gate (not port-free poll); (4) `wait_port_free` wired into `nats_restart` at BOTH call sites with `|| true`; (5) `wait_port_free` needs `timeout 1` guard (WSL2 `/dev/tcp` hangs on closed port); (6) skip blocks need `exit $?` under `set -euo pipefail` (`exit_code` at common.sh:41 only returns, does not terminate); (7) A02 needs meta-file guard (`[ -n "$(nats_meta_pid)" ]`) to prevent false-pass when running standalone; (8) `start_nats_bg` split into `start_nats_bg` + `start_nats_bg_at <dir>` for JetStream continuity; (9) unit test loop variable clobbering — use `_t5` + `LOOP_ITER`; (10) `nats-crash-reconnect.sh` must source `process.sh`. Files changed: `e2e/lib/process.sh`, `e2e/tests/fault/nats-crash-reconnect.sh`, `e2e/tests/unit/test-nats-restart.sh` (NEW) |
| ProjectTelemachy | Plan R3 for issue #304 (NATS client-cert mTLS, two minor POLAs resolved → A/B-clean) | R3 (PATCH, no CI; design/framing round, nothing newly executed): the R2 plan got a narrow B/NOGO with ONLY two MINOR POLA findings; both are RESOLVED in-plan. (1) Preflight failure handling: `connect_nats()` wraps `nats.connect(...)` and re-raises a typed `NatsConnectionError` (mirroring `AgamemnonError` at `agamemnon_client.py:13`) with an operator-guiding message; the CLI catches it, prints a red `console` line, and exits via `typer.Exit(1)` (`cli.py:68-80` style) — no bare traceback escapes `asyncio.run()`; a unit test monkeypatches `nats.connect`→`ssl.SSLError` and asserts the typed error. (2) The handshake-only preflight is FRAMED as a deliberate, DOCUMENTED, fail-closed verification gate (intent in docstring + CLI comment + CLAUDE.md row + runbook; the single real connect site; hard-fail on rejection, complementing `agamemnon_client.py` `require_tls`) — design intent in code+docs, not a probe or a narrowed AC. LESSON: a minors-only NOGO is closable WITHOUT new external verification by stating decisions in-plan. No new external claims/deps. Stacks on #2717 (v1.6.0), #2720 (v1.7.0), #2739 (v1.7.1) |
