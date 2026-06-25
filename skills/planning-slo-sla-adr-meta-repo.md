---
name: planning-slo-sla-adr-meta-repo
description: "How to plan adding SLO/SLA definitions to a read-mostly, ADR-driven meta-repo. Use when: (1) an audit finds no SLO/SLA/alerting targets in a docs-only repo, (2) planning where service-level targets should live when the implementing service is a separate submodule, (3) translating SLOs into Prometheus alerting rules."
category: documentation
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
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

1. **Confirm the repo's canonical decision vehicle.** In an ADR-driven meta-repo,
   SLO/SLA targets belong in a **new, sequentially-numbered ADR** plus an **operational
   runbook** — not loose docs scattered around. Verify the next ADR number first:
   `ls docs/adr/` and take `max(existing) + 1`.

2. **Give every SLI a NUMERIC target backed by a named Prometheus metric.** No vague
   targets. Back each SLI with a concrete metric:
   - counters: `*_requests_total`, `*_errors_total`
   - histograms: `*_request_duration_seconds` with buckets
     `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]`

3. **Translate each SLO into a RATE-BASED alert.** Use windowed rate/quantile
   expressions — never instantaneous counter comparisons:
   - latency: `histogram_quantile(0.99, sum(rate(<metric>_bucket[5m])) by (le))`
   - error/volume: `increase(<metric>[5m]) > <threshold>`

4. **Decide WHERE thresholds live.** Document the **canonical targets in the meta-repo**
   (ADR + runbook), but the **actual alert rules live in the observability submodule
   (ProjectArgus)**. The rule of thumb: *meta-repo documents, submodule implements.*

5. **Prevent an orphaned ADR.** Add a row to the `docs/adr/README.md` decision-log
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

### Risks / Uncertain Assumptions

The most uncertain parts of this plan, listed verbatim:

- The specific numeric targets (50ms, 99.5%, 100 tasks/min, 5s) are INVENTED placeholders, not derived from measured baselines or stakeholder agreement.
- The Prometheus metric NAMES (nats_event_duration_seconds, agamemnon_tasks_total, nats_reconnect_duration_seconds) are ASSUMED — they were not verified to exist in ProjectArgus/Agamemnon/Hermes; the actual emitted metric names were never grepped in those submodules.
- The claim "ProjectArgus owns the Prometheus rule files" and the file location for slo_alerts.yml in Argus were NOT verified against the Argus repo layout.
- `docs/architecture.md:167-178` line numbers and `docs/adr/README.md:13-20` table bounds are point-in-time and may drift.
- promtool was assumed available for validation but never confirmed installed.
