---
name: audit-composition-root-wiring-check
description: "Verifies that internal components are actually wired in the composition root (cmd/main, app entry, DI container) — not just present as packages with tests. Use when: (1) auditing a codebase before declaring it complete or shippable, (2) tests pass but a feature seems 'done but not working' or metrics permanently read zero, (3) before tagging a release, (4) inheriting a codebase and need to know what's actually live in production vs structurally dead."
category: debugging
date: 2026-05-05
version: "1.0.0"
user-invocable: false
tags: ["audit", "dead-code", "composition-root", "wiring", "instrumentation", "go", "verification"]
---

# Audit: Composition-Root Wiring Check

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-05 |
| **Objective** | Catch the architecture-vs-implementation gap: components that exist + have tests + are documented, but are never instantiated or invoked from the composition root, so they don't actually run in production. |
| **Outcome** | Verified-local. Caught five separate dead-spine bugs in Atlas that earlier reviews missed for months; fix PRs merged and Atlas v0.2.0 shipped with the spine wired. |

## When to Use

- Before declaring any audit complete (this is the single most missed class of audit defect).
- When tests pass and CI is green, but a feature seems "done but not working" in staging or prod.
- When metrics permanently read zero, or alerts referencing those metrics never fire.
- Before tagging a release. The "headline architectural promise" of the release is exactly the kind of thing that can be merged-but-unwired.
- When inheriting a codebase: distinguish what's actually live from what's merely present.
- Whenever a reviewer says "this package looks complete" — that's the trigger to check if it's wired.

The failure mode this catches: package implementation exists, unit tests pass with 90%+ coverage, README and architecture doc reference it, `Config` struct is populated — but `cmd/<binary>/main.go` never calls the constructor or `Start(ctx)`. The package is structurally dead code in production.

## Verified Workflow

### Quick Reference

For each runtime component (subscriber, metrics type, worker, validator, health check), pick the constructor or hot-path method symbol, then grep the composition root only:

```bash
# Go (substitute for your language as noted below)
pkg=internal/nats
ctor=nats.New        # constructor symbol
start=Subscriber.Start

# Is the package instantiated from cmd/?
grep -rn "$ctor"  cmd/ --include='*.go' | grep -v '_test.go'

# Is the lifecycle method actually invoked?
grep -rn ".Start(" cmd/ --include='*.go' | grep -v '_test.go'
```

If the first command returns zero non-test hits, the package is structurally dead code and any test coverage is misleading. Stop and flag it as a release blocker.

### Detailed Steps

1. **Enumerate runtime components.** From `internal/`, list every package that should be a runtime component (not a pure utility). Typical categories:

   | Component type | What "wired" means | Symbol to grep |
   | --- | --- | --- |
   | Subscriber / event consumer | `Start(ctx)` is called, ideally as a goroutine | `pkg.New`, `Start(` |
   | Metrics type (counter/histogram/gauge) | `Inc*` / `Observe*` / `Set*` called from real call sites, not just defined | `Inc`, `Observe`, `Set`, `Add` |
   | Background worker / poller | Constructed AND `go x.Start(ctx)` (or equivalent) | `pkg.New`, `go ` + start method |
   | Health-check registration | Registered with the health registry | `Register(`, `RegisterCheck(` |
   | Validator | Called from `Load()` / config-parse path | validator function name |
   | Middleware / interceptor | Added to the router/server chain | `Use(`, `WithMiddleware(`, chain registration |

2. **For each component, run the negative grep.** Search the composition root (`cmd/`, `app/`, wherever `main` lives) — excluding tests — for the constructor symbol:

   ```bash
   grep -rn "<ctor-symbol>" cmd/ --include='*.go' | grep -v '_test.go'
   ```

   Zero hits = structurally dead code. Document the package, the constructor, and where it was *expected* to be wired.

3. **For metrics specifically, also check the call sites of the mutator methods.** A metric that is only `Inc`'d inside its own defining package is dead instrumentation:

   ```bash
   # If the only hits for `IncFanout` are in metrics.go itself, the metric never moves.
   grep -rn 'IncFanout\|ObserveLatency\|SetActiveClients' \
        --include='*.go' \
        --exclude='*_test.go' \
        --exclude-dir=vendor
   ```

   Cross-reference with any alerting rules (`rules/*.yml`, Prometheus alerts). An alert that references a metric whose mutator is never called from production cannot ever fire, even though every component "exists".

4. **Verify the goroutine is actually launched.** `Start(ctx)` returning immediately is just as bad as not calling it. Confirm the call site uses `go subscriber.Start(ctx)` (or the equivalent supervised-goroutine pattern), and that the cancel/shutdown wiring is in place.

5. **Build a wiring matrix and put it in the audit report.** One row per component, one column per "expected", "constructed in cmd/", "lifecycle invoked", "exercised in production path". Anything with empty cells is a finding — not a nit, a blocker.

### Language-specific symbol-grep cheatsheet

| Language | Composition root | Constructor pattern | Lifecycle pattern |
| --- | --- | --- | --- |
| Go | `cmd/<binary>/main.go` | `pkg.New(`, `pkg.NewX(` | `.Start(ctx)`, `go pkg.Run(` |
| Python | `<package>/__main__.py`, `app.py`, `main.py` | `ClassName(`, `create_x(` | `.start()`, `await x.run()` |
| Rust | `src/main.rs`, `src/bin/*.rs` | `Type::new(`, `Builder::build()` | `.run().await`, `tokio::spawn(` |
| TypeScript/Node | `src/index.ts`, `src/server.ts` | `new ClassName(`, `createX(` | `.start()`, `.listen(` |
| Mojo | top-level `fn main()` in entry module | `ClassName(`, factory fn | `.run()`, task spawn |

In every case the rule is the same: grep the composition root, exclude tests, look for the constructor and the lifecycle method.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust "package exists + has tests = component works" | Earlier Atlas reviews graded the project as healthy because `internal/nats.Subscriber` had a complete implementation, a test file with a mock bus and 90%+ coverage, an architecture-doc entry, a README mention, and a wired-up `Config` with `DefaultStreams()`. | `cmd/argus-dashboard/main.go` never called `nats.New(...)` or `subscriber.Start(ctx)`. The package was structurally dead code in production; SSE clients only ever received heartbeats. The headline architectural promise of the entire epic was unimplemented in production. | Test coverage is independent of production wiring. Always grep the composition root for the constructor symbol — exclude tests — before grading any component "done". |
| Trust the `/metrics` endpoint as evidence metrics work | `internal/server/AtlasMetrics` was defined, registered, and exposed at `/metrics`. The endpoint returned valid Prometheus output. | None of the `Inc*` / `Observe*` / `Set*` methods were ever called from production code paths. Every counter and histogram permanently read zero. `rules/atlas-alerts.yml` referenced these metrics, so none of those alerts could ever fire. | Endpoint reachability is not instrumentation correctness. Grep the mutator methods (`Inc`, `Observe`, `Set`) excluding the metric's own package and tests; if the only hits are inside the defining file, the metric is dead instrumentation. |
| Hope reviewers would catch it during normal code review | Three rounds of human review on Atlas missed the gap for months because each PR only touched one layer (subscriber package, metrics package, main.go) and no review held all three in mind at once. | Wiring lives at the seam between PRs. A per-PR review is structurally incapable of catching "package added in PR A is never called from main.go modified in PR B". | Spine-wiring checks must be a release-gate audit step, not a reviewer-vibes check. Add a wiring matrix to the audit report. |

## Results & Parameters

### Atlas case: the wiring matrix that caught the bugs

| Component | Defined? | Tested? | Constructed in `cmd/`? | Lifecycle invoked? | Status |
| --- | --- | --- | --- | --- | --- |
| `internal/nats.Subscriber` | yes | yes (90%+) | **NO** | **NO** | DEAD — fixed in PR #444 |
| `internal/server.AtlasMetrics` (Inc/Observe/Set) | yes | yes | yes (struct constructed) | **NO mutators called** | DEAD INSTRUMENTATION — fixed in PR #445/#446 |
| Health-check registration | yes | yes | yes | yes | OK |
| Config validator | yes | yes | yes (called from `Load()`) | yes | OK |

The first two rows are what F-graded the audit. PRs #444 #445 #446 #447 #448 wired the spine and Atlas v0.2.0 shipped.

### Drop-in audit script (Go)

```bash
#!/usr/bin/env bash
# audit-wiring.sh — flag internal packages whose constructors are never
# called from cmd/. Run from repo root.
set -euo pipefail

CMD_DIR=${1:-cmd}
INTERNAL_DIR=${2:-internal}

echo "Composition-root wiring audit: $INTERNAL_DIR -> $CMD_DIR"
echo

# Enumerate exported constructors (functions starting with New) in internal/.
grep -rhn --include='*.go' --exclude='*_test.go' \
     -E '^func New[A-Z][A-Za-z0-9_]*\(' "$INTERNAL_DIR" \
  | sed -E 's/.*func (New[A-Za-z0-9_]+)\(.*/\1/' \
  | sort -u \
  | while read -r ctor; do
      hits=$(grep -rln --include='*.go' --exclude='*_test.go' "\b$ctor\b" "$CMD_DIR" || true)
      if [[ -z "$hits" ]]; then
        printf 'DEAD  %-40s (no call site in %s/)\n' "$ctor" "$CMD_DIR"
      fi
    done
```

Run before every release. Any line starting with `DEAD` is a release blocker until proven a deliberate library export.

### Expected output on a healthy repo

```text
Composition-root wiring audit: internal -> cmd
(no DEAD lines)
```

On Atlas pre-fix this same script would have printed `DEAD New` for the NATS subscriber and several metrics constructors — caught in seconds, not months.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Atlas (Go observability dashboard) | `/hephaestus:repo-analyze-strict-full` audit on 2026-05-05 graded the project F (NO-GO) on this exact issue. Three independent reviewer agents (architecture, source-quality, safety/reliability) converged on the same root cause. Fix PRs #444 #445 #446 #447 #448 merged; Atlas v0.2.0 shipped with the spine wired. | This skill |

## References

- Companion skill: [audit-implementation](audit-implementation.md) — how to triage and ship the fixes once the wiring gap is identified.
- Companion skill: [code-quality-audit-principles](code-quality-audit-principles.md) — broader audit framework; this skill is the "is it actually live?" subroutine.
