# Session Notes — Prometheus JSON API Exporter Sidecar

## Session Date
2026-03-15

## Context
HomericIntelligence ProjectArgus observability stack. Prometheus was configured to scrape
ai-maestro (`/api/diagnostics`, `/api/agents/health`) and NATS (`/metrics`) directly.
All 4 targets showed `up=0`.

## Root Cause Discovery
1. `docker exec argus-prometheus cat /etc/prometheus/prometheus.yml` — container had old
   config despite `POST /-/reload` being called. Config showed raw JSON endpoint scrapes.
2. `curl -s http://172.20.0.1:23000/api/diagnostics` — returns JSON `{"summary":{"status":"pass",...}}`
3. `curl -s http://172.24.0.1:8222/metrics` — 404, NATS only has `/varz` and `/jsz`
4. `docker network inspect projectargus_argus` — gateway is `172.24.0.1` (not localhost)

## Solution
Wrote `exporter/exporter.py` — stdlib Python HTTP server on port 9100.
Scrapes ai-maestro and NATS JSON endpoints, converts to Prometheus text format.
Added as `argus-exporter` sidecar in docker-compose.yml.
Updated prometheus.yml to only scrape the sidecar + prometheus self.

## Key Numbers
- ai-maestro gateway: 172.20.0.1:23000 (WSL2 host gateway on the docker network it originally lived on)
- NATS gateway: 172.24.0.1:8222 (argus Docker network gateway → host)
- Exporter port: 9100
- Grafana port: 3001 (3000 already taken by another service)

## Additional Fix: pixi src-layout
ProjectKeystone `pixi run python -m keystone.daemon` failed with ModuleNotFoundError.
Fix: add `keystone = { path = ".", editable = true }` to `[pypi-dependencies]` in pixi.toml.
`pixi install` re-solves and makes the package importable.

## GitHub Push
All 12 HomericIntelligence repos pushed to GitHub:
- 5 new repos created: Odysseus, ProjectArgus, ProjectHermes, ProjectProteus, ProjectTelemachy
- All under HomericIntelligence org (already existed)
- ProjectKeystone had no remote set — added manually
