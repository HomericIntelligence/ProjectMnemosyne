---
name: planning-slo-sla-adr-meta-repo
description: "How to plan adding SLO/SLA definitions to a read-mostly, ADR-driven meta-repo. Use when: (1) an audit finds no SLO/SLA/alerting targets in a docs-only repo, (2) planning where service-level targets should live when the implementing service is a separate submodule, (3) translating SLOs into Prometheus alerting rules."
category: documentation
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-slo-sla-adr-meta-repo.history
tags: []
---

# Planning SLO/SLA Definitions in a Read-Mostly ADR-Driven Meta-Repo

> ⚠️ **UNVERIFIED — PLAN ONLY.** This skill captures a *planning* pattern produced
> for Odysseus issue #185. No files were ever written, no ADR was created, no CI or
> `promtool` validation was run. Every numeric target, metric name, and file-location
> claim below is an assumption or an invented placeholder. Treat the workflow as a
> proposal to be verified, not as a record of executed and confirmed work.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Plan SLO/SLA docs for Odysseus issue #185 (no SLO/SLA/alerting targets exist anywhere in the repo) |
| **Outcome** | Plan produced (new ADR + alerting runbook + index/architecture cross-links) — **NOT implemented**; no files written, no CI run |
| **Verification** | unverified |
| **Category** | Documentation / Planning |
| **Related Issues** | #185 |

---

## When to Use

Use this skill when any of the following triggers apply:

1. An audit finds **no SLO/SLA/alerting targets** in a docs-only / read-mostly repo.
2. You are planning **where service-level targets should live** when the service that
   actually implements/emits the metrics is a *separate submodule*.
3. You need to **translate SLOs into Prometheus alerting rules**.

---

## Verified Workflow

> ⚠️ This is a **proposed** workflow. It was *not* executed or verified. Validate every
> step (especially metric names, file locations, and numeric targets) before acting.

1. **Reconcile every metric name and file path against the REAL implementing submodule
   BEFORE writing any alert rule.** This is the step the v1.0.0 plan skipped and was
   NOGO'd for: it invented metric names and an Argus layout from memory. Do not write a
   single `expr` until you have grepped the submodule for the metrics that actually exist:

   ```bash
   grep -rhoE "hi_[a-z_]+|homeric_[a-z_]+" \
     infrastructure/ProjectArgus/{rules,exporter} | sort -u
   ```

   Also read `configs/prometheus.yml` for the real scrape jobs and `docker-compose.yml`
   for how the rule directory is mounted. An alert against a metric that does not exist
   silently matches nothing — it is worse than no alert.

2. **Split SLIs into measurable-today vs requires-instrumentation.** Write ACTIVE alert
   rules only for metrics that exist now. For an SLI with no backing metric, record it in
   the ADR as a *target-with-prerequisite* and keep its alert rule **COMMENTED / BLOCKED**
   so nothing silently matches nothing (aligns with the repo's no-silent-failures runbook).

3. **Anchor at least one numeric target to a measured baseline found in the repo** (here:
   the e2e walkthrough's Hermes webhook P50 = 1ms / P95 = 3ms) rather than inventing every
   number. Explicitly label the remaining targets as *unvalidated proposals* **inside the
   ADR Context**, not merely in the plan's reasoning — the canonical append-only ADR must
   not commit fabricated numbers as fact.

4. **Confirm the repo's canonical decision vehicle.** In an ADR-driven meta-repo,
   SLO/SLA targets belong in a **new, sequentially-numbered ADR** plus an **operational
   runbook** — not loose docs scattered around. Verify the next ADR number first:
   `ls docs/adr/` and take `max(existing) + 1`.

5. **Give every SLI a NUMERIC target backed by a named Prometheus metric.** No vague
   targets. Back each SLI with a concrete metric:
   - counters: `*_requests_total`, `*_errors_total`
   - histograms: `*_request_duration_seconds` with buckets
     `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]`

6. **Translate each SLO into a RATE-BASED alert.** Use windowed rate/quantile
   expressions — never instantaneous counter comparisons:
   - latency: `histogram_quantile(0.99, sum(rate(<metric>_bucket[5m])) by (le))`
   - error/volume: `increase(<metric>[5m]) > <threshold>`
   - **Check the metric TYPE first:** `rate()`/`increase()` are meaningful only on a
     monotonic counter. Never `rate()` a gauge (e.g. `hi_tasks_total` is a gauge); a
     throughput SLO requires a real `*_total` counter to exist first.

7. **Decide WHERE thresholds live.** Document the **canonical targets in the meta-repo**
   (ADR + runbook), but the **actual alert rules live in the observability submodule
   (ProjectArgus)**. The rule of thumb: *meta-repo documents, submodule implements.*

8. **Prevent an orphaned ADR.** Add a row to the `docs/adr/README.md` decision-log
   table **and** a forward link from the architecture observability section so the new
   ADR is discoverable and audits do not re-flag it as missing.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Instantaneous counter alert | `expr: errors_total > 0` | Counters only increase and never reset, so the alert never clears | Use `increase(metric[5m]) > threshold` (rate-based, self-resetting) |
| Vague SLO targets | Writing "low latency"/"high availability" | ADR reviews reject non-measurable targets; no baseline for alert thresholds | Every SLI needs a number (p99 < 50ms, 99.5%/mo, ≥100 tasks/min) |
| Putting thresholds in meta-repo configs | Adding alert rules to Odysseus `configs/` | `configs/` only holds NATS+Nomad; alert rules belong to the observability submodule | Meta-repo documents canonical targets; submodule implements rules |
| New ADR not indexed | Creating the ADR file only | Orphaned ADR flagged by audits | Always add the README decision-log row + architecture cross-link |
| Invented metric names from memory | Used nats_event_duration_seconds, agamemnon_tasks_total, nats_reconnect_duration_seconds in alert exprs | Those metrics do not exist; the real Argus exporter emits only hi_*/homeric_* gauges, so every alert silently matches nothing | Grep the implementing submodule for real metric names before writing any expr |
| Assumed observability repo layout | Guessed where Prometheus rule files live and how they load | Layout unverified; could point the runbook at a nonexistent path | Verify the rules dir + mount in the submodule (rules/ -> /etc/prometheus/rules/*.yml via docker-compose) |
| rate() on a gauge | Planned throughput SLO as rate(hi_tasks_total) | hi_tasks_total is a GAUGE, not a counter; rate() on a gauge is meaningless | A monotonic *_total counter must exist before rate()/throughput SLOs; check the metric TYPE, not just the name |
| Targets only flagged in plan reasoning | Noted "targets are estimates" in the plan narrative but not in the ADR | Reviewer: the canonical append-only ADR would still commit fabricated numbers as fact | Put the "unvalidated initial proposals" framing INSIDE the ADR Context, with one number anchored to a measured baseline |

---

## Results & Parameters

The plan produced four named SLIs. The following SLI → SLO → metric table is **proposed**,
with invented placeholder targets and assumed metric names (see Risks below).

| SLI | SLO (target) | Backing Prometheus metric |
|-----|--------------|---------------------------|
| NATS event latency | p99 < 50ms, p95 < 10ms | `nats_event_duration_seconds` (histogram) |
| Agamemnon task throughput | ≥ 100 tasks/min | `agamemnon_tasks_total` (counter) |
| NATS reconnect latency | p99 < 5s | `nats_reconnect_duration_seconds` (histogram) |
| Availability | 99.5% / month | `*_requests_total` vs `*_errors_total` (counters) |

### Example `slo_alerts.yml` rule-group snippet

```yaml
groups:
  - name: slo_alerts
    rules:
      - alert: NATSEventLatencyHigh
        expr: |
          histogram_quantile(0.99,
            sum(rate(nats_event_duration_seconds_bucket[5m])) by (le)
          ) > 0.05
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "NATS event latency p99 above 50ms SLO"

      - alert: AgamemnonThroughputLow
        expr: increase(agamemnon_tasks_total[5m]) < 500
        for: 10m
        labels:
          severity: ticket
        annotations:
          summary: "Agamemnon throughput below 100 tasks/min SLO"

      - alert: NATSReconnectSlow
        expr: |
          histogram_quantile(0.99,
            sum(rate(nats_reconnect_duration_seconds_bucket[5m])) by (le)
          ) > 5
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "NATS reconnect p99 above 5s SLO"

      - alert: AvailabilityBelowSLO
        expr: |
          (
            sum(increase(http_requests_total[30d]))
            - sum(increase(http_errors_total[30d]))
          ) / sum(increase(http_requests_total[30d])) < 0.995
        for: 1h
        labels:
          severity: page
        annotations:
          summary: "Monthly availability below 99.5% SLO"
```

> ⚠️ The metric names in the table above are the v1.0.0 ASSUMED names and are now known
> to be wrong (see Reconciliation checklist). Reconcile against the real Argus surface
> before reusing them.

### Reconciliation checklist

Run this BEFORE writing any alert expr (see Workflow step 1):

- **Grep the implementing submodule for real metric names** —
  `grep -rhoE "hi_[a-z_]+|homeric_[a-z_]+" infrastructure/ProjectArgus/{rules,exporter} | sort -u`.
- **Confirm the metric TYPE** (gauge vs counter vs histogram) — `rate()`/`increase()`
  and `histogram_quantile()` are only valid on counters/histograms, never on a gauge.
- **Confirm the rule-file directory + mount path** — verify `rules/` maps to
  `/etc/prometheus/rules/*.yml` via the submodule's `docker-compose.yml`, and the scrape
  jobs in `configs/prometheus.yml`.
- **Find any measured baseline in the repo** — search `docs/` and e2e reports for real
  numbers to anchor at least one target (e.g. Hermes webhook P50 = 1ms / P95 = 3ms).

### Real Argus metric surface (verified by reconciliation)

The actual exporter emits only these (NOT the v1.0.0 assumed names):

- `hi_agamemnon_health`, `hi_nestor_health` (gauges)
- `hi_agents_online`, `hi_agents_offline`, `hi_agents_total` (gauges)
- `hi_tasks_total` (**gauge — not a counter**; cannot `rate()` for throughput)
- `hi_tasks_by_status` (gauge)
- `homeric_exporter_scrape_timestamp`, `homeric_exporter_scrape_duration_seconds`,
  `homeric_exporter_fetch_errors_total`
- `up` (Prometheus built-in scrape liveness)

### Risks / Uncertain Assumptions

Status after the re-plan reconciliation:

- **RESOLVED — metric names verified.** The v1.0.0 assumed names
  (nats_event_duration_seconds, agamemnon_tasks_total, nats_reconnect_duration_seconds) do
  NOT exist; the real surface is the `hi_*`/`homeric_*` set listed above.
- **RESOLVED — Argus layout verified.** Rule files live under `rules/` mounted to
  `/etc/prometheus/rules/*.yml` via the submodule `docker-compose.yml`.
- **REMAINS — numeric targets are unvalidated proposals.** Only the latency anchor is
  tied to a measured baseline (Hermes webhook P50 = 1ms / P95 = 3ms); the rest are still
  proposals pending real traffic and stakeholder agreement, and must be framed as such
  inside the ADR Context.
- **REMAINS — throughput SLO blocked.** No monotonic `*_total` counter exists today
  (`hi_tasks_total` is a gauge), so any throughput/rate SLO must stay COMMENTED/BLOCKED in
  the rule file until the counter is instrumented.
- **REMAINS — point-in-time references.** `docs/architecture.md` and `docs/adr/README.md`
  line/table bounds drift; re-locate at write time.
- **REMAINS — promtool not confirmed.** promtool availability for rule validation was
  assumed, never confirmed installed.
