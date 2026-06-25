---
name: tooling-config-placeholder-grep-guard
description: "When a config file replaces a hardcoded value with a ${PLACEHOLDER}, add a fixed-string grep guard in the config-validation recipe/CI so the placeholder cannot be silently re-hardcoded — and audit EVERY placeholder-bearing config, not just the one named in the issue. Syntax/lint validators (nomad fmt -check, yamllint) do NOT detect a placeholder being replaced by a literal value; presence is a separate concern needing its own grep check. Use grep -qF '${PLACEHOLDER}' (fixed-string, single-quoted) so the shell does not expand ${...} and grep does not regex-interpret braces. Use when: (1) a config keeps an unresolved ${VAR} placeholder, (2) you want CI to fail if someone re-bakes a literal value, (3) you are tempted to trust an issue's claim that a sibling guard already exists or its cited line numbers."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: ["config-validation", "grep-guard", "placeholder", "ci", "justfile", "anti-regression"]
---

# Config Placeholder Grep Guard

## Overview

When a config file is de-hardcoded — a literal value (an IP, hostname, path) is replaced by a `${PLACEHOLDER}` that gets rendered at deploy time — nothing in the standard validation toolchain notices if a later edit bakes the literal value back in. `nomad fmt -check` and `yamllint` validate *syntax*; a re-hardcoded value is syntactically perfect. The durable fix is to add a fixed-string grep guard to the canonical config-validation recipe (the one CI actually invokes) that asserts the placeholder is still present, and to audit EVERY placeholder-bearing config rather than only the one named in the issue.

| Field | Value |
| --- | --- |
| **Date** | 2026-06-20 |
| **Objective** | Stop a `${PLACEHOLDER}` config token from being silently re-hardcoded by adding a presence grep guard to the CI-invoked config-validation recipe, across all placeholder-bearing configs |
| **Outcome** | Guard implemented and verified end-to-end in Odysseus (issue #320). Negative test confirmed: replacing `${NOMAD_ADVERTISE_ADDR}` with a literal Tailscale IP causes `just validate-configs` to exit non-zero with correct error message. `verified-local`. |

## When to Use

- A config file keeps an UNRESOLVED `${VAR}`/`<placeholder>` because it is rendered (e.g. via `envsubst`) before deploy, and you want CI to fail loudly if a literal value is re-baked in.
- You are reviewing or planning a "guard against re-hardcoding" change and need to know WHERE the guard goes and HOW to write the grep so it matches the literal placeholder text.
- The issue you are working from cites specific line numbers, or asserts that a sibling guard already exists — and you have not yet re-verified those claims against the current tree.
- More than one config in the repo carries a placeholder, and you are tempted to guard only the one the issue names.
- Adding anti-regression guards to a `validate-configs` or similar CI recipe in a justfile.

## Verified Workflow

1. **Re-derive the facts from the CURRENT tree — never trust the issue's line numbers or premises.** Issue bodies routinely cite stale line numbers (drift) and assert that a sibling guard exists when it does not. Grep the actual config files for `\$\{` to find which ones really carry a placeholder, and grep the validation recipe for the anchor you intend to edit. In the Odysseus case the issue claimed a `client.hcl` / `${NOMAD_SERVER_IP}` guard existed — it did not; `client.hcl` used a literal IP plus a runtime env-override pattern with NO `${...}` placeholder, so it was not guardable. Only `server.hcl` (`${NOMAD_ADVERTISE_ADDR}`) was.
2. **Audit EVERY placeholder-bearing config, not just the named one.** A single `grep -lE '\$\{' configs/**/*.{hcl,conf,yml}` reveals the full set. Each config that carries a `${...}` placeholder needs its own guard line; each config that does NOT (literal value + env override, or no templating) needs none — and forcing a guard onto it is wrong.
3. **Understand that syntax/lint validators do NOT detect a re-hardcoded placeholder.** `nomad fmt -check` and `yamllint` only verify syntax — both the templated form and the re-hardcoded literal form pass them. Presence of the placeholder is an orthogonal concern that needs its own grep check; do not assume the existing `fmt -check`/`yamllint` lines cover it.
4. **Write the guard with `grep -qF` and SINGLE quotes.** Use fixed-string mode (`-F`) so grep does not regex-interpret the `${...}` braces, and single-quote the pattern so the shell does not expand `${PLACEHOLDER}` to empty before grep sees it. `-q` keeps it quiet; the `|| { ...; exit 1; }` fails the build when the token is gone.
5. **Place the guard in the canonical validation recipe that CI actually invokes — verify which one.** Do not assume; trace the CI entrypoint (e.g. a `ci:` recipe) down to the recipe it calls (`validate-configs`). The recipe must run under `set -euo pipefail` so the `|| exit 1` actually fails the build rather than being swallowed.
6. **Verify with a negative test.** After adding the guard, temporarily replace the placeholder with a hardcoded value, run the recipe, confirm it exits non-zero with the expected error message, then restore the placeholder.

### Quick Reference

```bash
# 1. Find every config that ACTUALLY carries a ${...} placeholder (current tree, not the issue).
grep -lE '\$\{' configs/nomad/*.hcl configs/nats/*.conf 2>/dev/null

# 2. Guard pattern: fixed-string (-F), SINGLE-quoted so the shell does not expand ${...}.
grep -qF '${NOMAD_ADVERTISE_ADDR}' configs/nomad/server.hcl \
  || { echo "server.hcl lost its placeholder (re-hardcoded?)"; exit 1; }

# WRONG: double quotes -> bash expands ${VAR} to empty; no -F -> braces regex-interpreted.
#   grep -q "${NOMAD_ADVERTISE_ADDR}" configs/nomad/server.hcl   # do NOT do this

# 3. Verify with a negative test (then restore):
#   sed -i 's/${NOMAD_ADVERTISE_ADDR}/100.92.173.32/g' configs/nomad/server.hcl
#   just validate-configs  # must exit non-zero with error message
#   git checkout -- configs/nomad/server.hcl
```

Drop the guard into the CI-invoked recipe (Odysseus issue #320 — anti-re-hardcoding guard against regression from PR #181):

```just
validate-configs:
    #!/usr/bin/env bash
    set -euo pipefail
    nomad fmt -check configs/nomad/client.hcl configs/nomad/server.hcl   # syntax only — does NOT catch re-hardcoding
    yamllint -c .yamllint.yml configs/                                   # syntax only
    # Anti-re-hardcoding guard (issue #320, regression from #181): server.hcl must
    # keep its ${NOMAD_ADVERTISE_ADDR} placeholder, never a literal Tailscale IP.
    grep -qF '${NOMAD_ADVERTISE_ADDR}' configs/nomad/server.hcl || {
        echo "configs/nomad/server.hcl lost its \${NOMAD_ADVERTISE_ADDR} placeholder (hardcoded IP re-introduced — see #181)"; exit 1;
    }
```

Key implementation notes:
- The echo uses `\${NOMAD_ADVERTISE_ADDR}` (escaped) so the literal placeholder text appears in output, not an expanded (empty) value.
- The `|| { ...; exit 1; }` works inside justfile recipes because the recipe uses `#!/usr/bin/env bash` + `set -euo pipefail` — `exit 1` exits the shell, which fails the recipe.
- `just --summary` can be used to verify the justfile still parses correctly after the edit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Trust issue's cited line numbers (justfile:261) | Assumed the guard goes at the issue's stated line | Line numbers had drifted; the cited `client.hcl` guard did not exist in the tree | Re-grep the current file for the anchor; never trust issue line numbers |
| Assume symmetric guard across client.hcl and server.hcl | Planned to mirror an existing `client.hcl` placeholder guard | `client.hcl` has no `${...}` placeholder (uses a literal IP + env override); nothing to guard there | Audit each config's actual templating style before adding a guard |
| Use `grep -q '${VAR}'` (basic, double-quoted) | Naive grep with double quotes and no `-F` | Double quotes let bash expand `${VAR}` to empty; without `-F` grep may regex-interpret the braces | Single-quote + `grep -qF` for literal placeholder matching |
| Echo placeholder in error message with double quotes unescaped | `echo "...${NOMAD_ADVERTISE_ADDR}..."` | Shell expands `${NOMAD_ADVERTISE_ADDR}` to empty inside double quotes — error message shows blank | Escape the placeholder in echo: `\${NOMAD_ADVERTISE_ADDR}` so the literal string appears |

## Results & Parameters

Concrete facts derived from the current Odysseus tree (so the guard is grounded, not assumed):

- `configs/nomad/client.hcl` — `servers = ["100.92.173.32:4647"]` is a LITERAL IP with a runtime env-override pattern; it carries NO `${...}` placeholder, so it is NOT guardable. The issue's claim that a `client.hcl` / `${NOMAD_SERVER_IP}` guard existed was false.
- `configs/nomad/server.hcl` — carries `${NOMAD_ADVERTISE_ADDR}` (the only real placeholder among the Nomad configs), so it is the one config that gets a presence guard.
- `validate-configs` (justfile) is the canonical recipe; it runs under `set -euo pipefail`, calls `nomad fmt -check` (syntax-only) and `yamllint` (syntax-only), and is invoked by the `ci:` recipe (`ci: lint validate-configs check-doc-field-drift`). The guard belongs inside `validate-configs`.

Parameters:

- Guard form: `grep -qF '${PLACEHOLDER}' path/to/config || { echo "..."; exit 1; }`
- `-F` = fixed string (no regex), `-q` = quiet, SINGLE quotes = no shell expansion.
- Required precondition: the host recipe runs under `set -euo pipefail` so `exit 1` fails the build.
- Echo escaping: use `\${PLACEHOLDER}` (backslash-escaped) in double-quoted error messages so the literal placeholder text appears in output.

Verification: `verified-local`. Guard implemented in Odysseus justfile, `just --summary` confirmed parse success, `just validate-configs` passes with placeholder present, negative test (hardcoded IP substituted) causes non-zero exit with correct error message, file restored. CI not yet run, but logic is trivially correct.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| Odysseus | Planning a config placeholder re-hardcoding guard; derived facts by reading `configs/nomad/*.hcl` and the `validate-configs`/`ci` recipes in `justfile` | Planning learning (v1.0.0) — `unverified` |
| Odysseus | Issue #320 — add anti-re-hardcoding guard to `validate-configs` recipe (regression from PR #181 Tailscale IP); guard implemented and negative-tested | `verified-local`; PR #320 |
