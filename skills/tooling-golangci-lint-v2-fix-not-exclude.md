---
name: tooling-golangci-lint-v2-fix-not-exclude
description: "Bumping golangci-lint v1 to v2 (and adding errorlint/bodyclose) surfaces real bugs the v1 config missed — fix every finding, do not add to exclude-rules. Use when: (1) migrating a Go project's .golangci.yml from v1 to v2 schema, (2) enabling errorlint or bodyclose on an existing Go codebase, (3) inheriting a Go service with minimal lint config, (4) tempted to suppress a new linter finding via exclude-rules, (5) before tagging a Go service release, (6) investigating subtle production bugs that 'shouldn't be possible' (e.g., govet copylocks)."
category: tooling
date: 2026-05-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - golangci-lint
  - go
  - linting
  - errorlint
  - bodyclose
  - copylocks
  - govet
  - gosec
  - staticcheck
  - errcheck
  - ci
  - atlas
  - argus
---

# golangci-lint v2 Migration: Fix Findings, Don't Exclude Them

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-05 |
| **Objective** | Migrate Atlas (HomericIntelligence/ProjectArgus) `.golangci.yml` from v1 to v2 schema, enable `errorlint` + `bodyclose`, and resolve every new finding rather than suppressing them via `exclude-rules`. |
| **Outcome** | Successful — Atlas PR #448 merged on `HomericIntelligence/ProjectArgus`. All 9 findings fixed, including a real `govet copylocks` production bug. `golangci-lint v2 run ./...` reports `0 issues` on Atlas v0.2.0. |
| **Verification** | verified-ci — CI green on PR #448; `golangci-lint v2 run ./...` reports zero issues. |
| **History** | none (initial version) |

## When to Use

- Bumping `golangci-lint` from v1.x to v2.x in any Go project
- Adding `errorlint` or `bodyclose` to an existing project's enabled linters
- Inheriting a Go codebase with a minimal v1-schema `.golangci.yml`
- Whenever you are tempted to add a new finding to `issues.exclude-rules`
- Before tagging a Go service release (e.g., a v0.x → v0.y bump)
- Investigating subtle production bugs that "shouldn't be possible" — especially around `sync.Mutex` / `sync.RWMutex` / `sync.WaitGroup` returned by value
- Auditing `//nolint:errcheck` directives — v2 reads them differently than v1 and may surface previously-hidden errors

## Verified Workflow

### Quick Reference

```bash
# 1. Pin golangci-lint version: latest in CI (NOT a fixed alpine tag — see Companion below)
# .github/workflows/<go-ci>.yml
- uses: golangci/golangci-lint-action@v6
  with:
    version: latest          # NOT v1.57.2 / NOT a pinned alpine tag
    working-directory: ./dashboard

# 2. Migrate .golangci.yml to v2 schema. Minimal-but-strict template:
cat > .golangci.yml <<'YAML'
version: "2"
run:
  timeout: 5m
  modules-download-mode: readonly
linters:
  default: none
  enable:
    - govet
    - staticcheck
    - errcheck
    - ineffassign
    - unused
    - gosec
    - errorlint     # NEW in v2 setup — catches non-%w error wrapping
    - bodyclose     # NEW in v2 setup — catches HTTP body leaks
  settings:
    gosec:
      excludes:
        - G401   # weak crypto (intentional in this project)
        - G501   # blacklisted import (intentional in this project)
issues:
  max-issues-per-linter: 0
  max-same-issues: 0
YAML

# 3. Run locally and FIX every finding (do not add to exclude-rules)
golangci-lint run ./...

# 4. Re-run until 0 issues, commit, push, watch CI go green
```

### Detailed Steps

1. **Migrate the schema.** A v1 `.golangci.yml` with no `version:` key will be rejected by the v2 binary:

   ```text
   Error: can't load config: unsupported version of the configuration: ""
   ```

   Add `version: "2"` and convert `linters.enable` and `linters-settings` → `linters.settings`. The v2 schema also requires `linters.default: none` if you want to opt-in to a specific set (otherwise v2 will enable its default fastset on top of yours).

2. **Pin the action to `version: latest`, not a fixed tag.** The `golangci-lint:latest-alpine` Docker image is built with Go 1.24 and will refuse to lint a Go 1.25 module:

   ```text
   Error: can't load config: the Go language version (go1.24) used to
   build golangci-lint is lower than the targeted Go version (1.25.8)
   ```

   In GitHub Actions, `golangci/golangci-lint-action@v6` with `version: latest` resolves to a fresh release per run and avoids this trap.

3. **Run locally and triage findings.** With `errorlint` and `bodyclose` enabled, expect a wave. Triage each:

   - Real bug → fix the code.
   - False positive specific to one site → narrow `//nolint:<linter> // <reason>` directive at the offending line, with a written reason.
   - Whole-rule false positive across the codebase → only then consider `issues.exclude-rules`, and only with a written reason.

   **The default must be "fix the code."** Suppressing a v2 finding by default defeats the point of the upgrade.

4. **Worked example — the 9 findings on Atlas.** The full triage on Atlas v0.2.0:

   | # | Linter | Where | Real bug? | Fix |
   |---|--------|-------|-----------|-----|
   | 1–3 | `errcheck` | `internal/{catalog,poller,tailscale}/*` | Yes — `resp.Body.Close()` errors swallowed | Capture and log close errors; partial-read failures no longer hidden |
   | 4–6 | `gosec G104` | `handlers/*` (11 sites) | Yes — `templ.Render` errors silently swallowed under pre-existing `//nolint:errcheck` | Check and propagate the render error |
   | 7 | `gosec G304` | `internal/mnemosyne/reader.go` `os.ReadFile(filepath.Join(dir, e.Name()))` | Defense-in-depth — symlink inside skills dir could escape | Add `filepath.EvalSymlinks` + containment check that resolved abs path lives under configured root |
   | 8 | `gosec G302` | test fixture chmod | Pre-existing `0o755` script | Write at `0o600`, then `chmod 0o700` (owner-only rwx) |
   | 9 | `staticcheck ST1011` | `PollAgamemnonMs time.Duration` | Style — unit-suffix violates Go convention for `time.Duration` | Rename field to `PollAgamemnon`; keep env var `ATLAS_POLL_AGAMEMNON_MS` (operator-side suffix is fine) |
   | **10** | **`govet copylocks`** | **`internal/poller/poller.go`** | **YES — real production bug** | **See worked example below** |

5. **Worked example — the `copylocks` bug (the headline finding).** This is why the v2 upgrade was worth it.

   The original code:

   ```go
   // BEFORE — broken: returns base by value, copies the embedded RWMutex
   type base struct {
       mu       sync.RWMutex
       interval time.Duration
       // ...
   }

   func newBase(interval time.Duration /* ... */) base {
       b := base{interval: interval /* ... */}
       return b
   }

   type AgamemnonPoller struct {
       base    // embedded by value
       // ...
   }

   type NATSPoller struct {
       base    // embedded by value
       // ...
   }
   ```

   `base` contained `sync.RWMutex`. Returning `base` by value **copies the mutex** at construction, and embedding `base` (not `*base`) means every method receiver also has a copy. Any `b.mu.Lock()` in a method takes a lock on a different mutex than the caller intended — silently broken concurrent access in production.

   The fix:

   ```go
   // AFTER — return *base; embed *base
   func newBase(interval time.Duration /* ... */) *base {
       return &base{interval: interval /* ... */}
   }

   type AgamemnonPoller struct {
       *base
       // ...
   }

   type NATSPoller struct {
       *base
       // ...
   }
   ```

   This bug had passed v1 review and human review for months. `govet copylocks` in the v2 setup was the only thing that surfaced it.

6. **Resist the temptation to exclude.** If you find yourself writing this:

   ```yaml
   # ANTI-PATTERN — do not do this
   issues:
     exclude-rules:
       - linters: [govet]
         text: "copylocks"
       - linters: [errorlint]
         text: "non-wrapping format verb for fmt.Errorf"
       - linters: [bodyclose]
         text: "response body must be closed"
   ```

   **Stop.** Each of those rules exists because there is a class of real bugs the linter is detecting. `copylocks` → silent mutex copies. `errorlint` → `errors.Is`/`errors.As` will not match wrapped errors. `bodyclose` → file descriptor leaks under load. Suppressing the warning leaves the bug.

   The same applies to `gosec G306` (file perms), `gosec G302` (chmod perms), `gosec G304` (file inclusion). Treat each finding as evidence of a real-world failure mode.

7. **Verify zero issues, then commit.** A clean run is:

   ```text
   $ golangci-lint run ./...
   0 issues.
   ```

   Anything else means there is more to fix or a deliberate, narrow `//nolint:` to write with a reason comment.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Run v2 binary against the existing v1 `.golangci.yml` (no `version:` key) | `Error: can't load config: unsupported version of the configuration: ""` | v2 requires explicit `version: "2"` and the new schema layout (`linters.settings` not `linters-settings`, `linters.default: none` to disable v2's default fastset) |
| 2 | Pin CI to `golangci-lint:latest-alpine` Docker image | Image is built with Go 1.24; refuses Go 1.25 module: `the Go language version (go1.24) used to build golangci-lint is lower than the targeted Go version (1.25.8)` | Use `golangci/golangci-lint-action@v6` with `version: latest` so each CI run pulls a fresh release built against current Go |
| 3 | Suppress new findings via `issues.exclude-rules` to ship the v2 upgrade quickly | Would have left 3 real `errcheck` resource leaks, 11 silently-swallowed `templ.Render` errors, a real `gosec G304` symlink-escape risk, and the `govet copylocks` bug in production | The whole point of the v2 upgrade is to surface these. Excluding the rule defeats the upgrade. Fix each finding. |
| 4 | Treat `govet copylocks` as a style nit and add `//nolint:govet` on `func newBase(...) base` | The "style nit" is a real bug — embedding `base` (not `*base`) means each `AgamemnonPoller` and `NATSPoller` had its own copy of the `sync.RWMutex`, so concurrent access was unsynchronized despite the lock calls | `copylocks` always indicates a real concurrency bug for any struct with a `sync.*` field. Fix by returning `*base` and embedding `*base` |
| 5 | Drop `ST1011 PollAgamemnonMs` finding and keep the unit-suffixed `time.Duration` field name | Unit suffix on `time.Duration` is misleading at call sites (`cfg.PollAgamemnonMs * time.Millisecond` looks correct but double-multiplies) | Strip unit suffix from `time.Duration` fields; keep the suffix on the env var on the operator side (`ATLAS_POLL_AGAMEMNON_MS`) |
| 6 | Fix `gosec G302` test chmod by adding `//nolint:gosec` for an `0o755` fixture | The fixture only needs owner-execute, not group/world | Use `0o700` instead — strictly more secure and lint-clean. Reach for `//nolint` only when the loose perm is truly required |
| 7 | Fix `gosec G304` `os.ReadFile(filepath.Join(dir, e.Name()))` by adding a comment that `e.Name()` is from `os.ReadDir` so traversal is impossible | A symlink inside the configured skills dir could resolve to `/etc/passwd`. The `os.ReadDir` argument blocks `..` traversal but not symlink escape | Use `filepath.EvalSymlinks` on the joined path and verify the resolved absolute path is contained under the configured root |

## Results & Parameters

### v1 → v2 schema migration template

```yaml
# BEFORE (v1)
run:
  timeout: 5m
  modules-download-mode: readonly
linters:
  enable: [govet, staticcheck, errcheck, ineffassign, unused, gosec]
issues:
  exclude-rules:
    - linters: [gosec]
      text: "G401|G501"
```

```yaml
# AFTER (v2) — strict, opt-in, with errorlint + bodyclose
version: "2"
run:
  timeout: 5m
  modules-download-mode: readonly
linters:
  default: none
  enable:
    - govet
    - staticcheck
    - errcheck
    - ineffassign
    - unused
    - gosec
    - errorlint
    - bodyclose
  settings:
    gosec:
      excludes:
        - G401   # weak crypto — document the intentional reason in this list
        - G501   # blacklisted import — document the intentional reason in this list
issues:
  max-issues-per-linter: 0
  max-same-issues: 0
```

### GitHub Actions snippet (Go 1.25-safe)

```yaml
- name: golangci-lint
  uses: golangci/golangci-lint-action@v6
  with:
    version: latest             # NOT a pinned alpine tag — see "Companion" below
    working-directory: dashboard/
    args: --timeout=5m
```

### copylocks fix snippet (drop-in pattern)

```go
// Whenever a struct contains a sync.{Mutex,RWMutex,WaitGroup,Cond} field:
// - constructors return *T, never T
// - embedders embed *T, never T
// - method receivers are *T, never T

type base struct {
    mu sync.RWMutex
    // ...
}

func newBase(/* ... */) *base { return &base{ /* ... */ } }

type Poller struct {
    *base       // embedded by pointer
    // ...
}

func (p *Poller) Tick() {
    p.mu.Lock()           // takes the shared lock on the embedded *base
    defer p.mu.Unlock()
    // ...
}
```

### Companion finding — Go 1.25 + golangci-lint Docker tag

```text
# Symptom (when CI pins to golangci-lint:latest-alpine):
Error: can't load config: the Go language version (go1.24) used to
build golangci-lint is lower than the targeted Go version (1.25.8)

# Fix: use the GitHub Action with version: latest
- uses: golangci/golangci-lint-action@v6
  with:
    version: latest
```

The `golangci-lint:latest-alpine` Docker image lags behind the GitHub Action's release stream by a Go minor version. The Action with `version: latest` pulls a fresh release per run and tracks current Go.

### Quick decision rule

> When `golangci-lint v2` surfaces a finding the v1 config missed, the default action is **fix the code**. Reach for `//nolint` only at a single line with a written reason. Reach for `issues.exclude-rules` only for a whole-codebase false-positive class with a written reason. **`copylocks`, `errorlint`, `bodyclose`, and `gosec G3xx` should never go in `exclude-rules`** — every one of them maps to a real-world failure class.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectArgus (Atlas v0.2.0) | golangci-lint v1 → v2 migration; enabled `errorlint` + `bodyclose`; fixed all 9 findings including a `govet copylocks` production bug in `internal/poller/poller.go` | PR #448 (merged); `golangci-lint v2 run ./...` reports `0 issues` post-merge |
