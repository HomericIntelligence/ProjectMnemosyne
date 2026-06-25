# Notes: canonical-config-env-var-expansion

Uncertain assumptions and risks for a reviewer:

- **NATS in-string `$VAR` expansion** inside a quoted URL value (`"nats+tls://$NATS_SERVER_IP:7422"`) — this is documented NATS behavior but UNVERIFIED in this plan (not tested with `nats-server -t`).
- **Nomad `servers` array `${VAR}` interpolation** parity with the `advertise` block — INFERRED from `server.hcl`'s existing `${NOMAD_ADVERTISE_ADDR}` usage; NOT independently confirmed that `client.hcl` `servers` arrays interpolate env vars the same way as advertise blocks.
- **`nomad fmt -check` validates SYNTAX only** — it does NOT prove the env var resolves at runtime. The plan's primary verification is syntactic/grep-based; a green `just validate-configs` does NOT prove the daemon connects.

Source: Odysseus meta-repo, GitHub issue #181, implementation plan (plan only, not executed).
