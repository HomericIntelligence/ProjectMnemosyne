---
name: debugging-auth-mode-case-mismatch-fail-open
description: "Detect and fix the case-mismatched-enum + fail-open-default-branch pattern that ships dashboards open. Use when: (1) reviewing or auditing auth-mode middleware that compares against typed string constants, (2) you find a switch with a default branch that calls next.ServeHTTP."
category: debugging
date: 2026-05-06
version: "1.0.0"
user-invocable: false
tags:
  - security
  - auth-bypass
  - fail-open
  - case-mismatch
  - enum-normalization
  - defense-in-depth
  - go
---

# Skill: debugging-auth-mode-case-mismatch-fail-open

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-05-06 |
| Objective | Surface a recurring fail-open pattern that bypasses authentication when `ATLAS_AUTH_MODE` (or any analogous typed-enum config string) is set to a mixed-case value. |
| Outcome | Reproduced in production-shipped Atlas v0.2.0; fixed in v0.2.1 with a one-line normalization plus a defense-in-depth fail-closed default branch. Two regression tests in `internal/config/config_test.go::TestValidate_NormalizesAuthMode` and `internal/server/auth_test.go::TestMiddleware_UnknownModeFailsClosed`. |
| Verification | verified-ci — the v0.2.1 fix has regression tests that run in CI on every push. |
| Category | debugging |

### What Happened

A real auth bypass shipped in Atlas v0.2.0. Two bugs interacted; neither was dangerous alone:

1. `Config.Validate` lowercased `c.AuthMode` *into a local switch tag* but never mutated the field itself. Any mixed-case value (e.g. `ATLAS_AUTH_MODE=Bearer`) passed validation while the struct field retained its original casing.
2. The auth middleware's `switch mode` had a `default:` branch that fell through to `next.ServeHTTP(w, r)`. The intent was "AuthNone falls through"; the effect was "any unknown mode falls through".

Operators who set `ATLAS_AUTH_MODE=Bearer` (the natural-looking title case) got a dashboard that returned `HTTP 200` to unauthenticated callers. The bug was reachable via a single-byte typo.

## When to Use

Trigger this skill when:

- Reviewing any auth middleware that switches on a string-typed mode (`basic` / `bearer` / `token` / etc.).
- Reviewing config that reads an env var into a string field and never normalizes case.
- A dashboard, API, or admin endpoint mysteriously serves to unauthenticated callers despite "auth being enabled".
- The middleware's switch has a `default:` branch that calls `next.ServeHTTP(w, r)` instead of returning `401`.
- Auditing any typed enum derived from `os.Getenv` (log levels, feature flags, throttling modes, cache modes).

## Verified Workflow

### Quick Reference

```go
// FIX 1: Normalize the field IN PLACE in Validate (don't lowercase a local copy).

// BAD:
func (c *Config) Validate(logger *slog.Logger) error {
    switch mode := strings.ToLower(c.AuthMode); mode { // local-only lowercase
    case "bearer": /* ... */
    case "basic":  /* ... */
    case "none":   /* ... */
    default:
        return fmt.Errorf("unknown mode %q", c.AuthMode)
    }
}
// c.AuthMode is unchanged → middleware sees the raw mixed-case value later.

// GOOD:
func (c *Config) Validate(logger *slog.Logger) error {
    c.AuthMode = strings.ToLower(strings.TrimSpace(c.AuthMode)) // mutate the field
    switch c.AuthMode {
    case "bearer": /* ... */
    case "basic":  /* ... */
    case "none":   /* ... */
    default:
        return fmt.Errorf("unknown mode %q", c.AuthMode)
    }
}
```

```go
// FIX 2: Make the middleware's default branch FAIL CLOSED, not pass through.

// BAD:
func Middleware(mode AuthMode, ...) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            switch mode {
            case AuthBasic:  /* check */
            case AuthBearer: /* check */
            default:
                // AuthNone OR unknown — both fall through!
            }
            next.ServeHTTP(w, r)
        })
    }
}

// GOOD:
func Middleware(mode AuthMode, ...) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            switch mode {
            case AuthNone:   // explicit pass-through
            case AuthBasic:  /* check or 401 */
            case AuthBearer: /* check or 401 */
            default:
                // fail closed — Validate should have rejected this; if we got here,
                // something bypassed Validate (hand-built Config in a test? a future
                // code path?). 401 every request beats opening the dashboard.
                http.Error(w, "Unauthorized", http.StatusUnauthorized)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}
```

### Detailed Steps

1. **Audit every Validate function** that reads a typed-enum string from env. Look for the antipattern: `switch x := strings.ToLower(c.X); x` where `c.X` is the actual struct field. The lowercase happens on a local variable; the field stays raw and downstream consumers see the mixed-case value.
2. **Audit every middleware switch** on the same enum. Look for a `default:` branch that falls through to `next.ServeHTTP`. `AuthNone` is fine as an *explicit* case but unknown-mode-falls-through is the bug.
3. **Add regression tests in two places**:
   - **Config-level**: assert mixed-case (`"Bearer"`, `"BEARER"`, `"  bearer\t"`) all normalize to lowercase AND pass `Validate`.
   - **Middleware-level**: assert that a hand-built `Config` with an unknown mode (`AuthMode("Bearer")`, `AuthMode("magic")`, `AuthMode("")`) returns `401` — defense in depth.
4. **Apply both fixes together**, not just one. `Validate`-only normalization closes the today-bug; middleware fail-closed prevents the next refactor from re-opening it via a different path. Defense in depth is cheap here.
5. **Reproduce against the shipped image** before claiming fixed. Run two `docker run` commands — one with `Bearer`, one with `bearer` — and confirm the pre-fix image returns `200` for the first and `401` for the second.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Lowercase the switch tag only | `switch mode := strings.ToLower(c.AuthMode); mode` in `Validate` | `Validate` accepts `"Bearer"`. Then `routes.go` calls `Middleware(AuthMode(s.cfg.AuthMode), ...)` with the un-normalized field. Middleware compares against typed const `AuthBearer = "bearer"` exactly; `"Bearer" != "bearer"`, hits default branch. Default falls through to `next.ServeHTTP`. Dashboard open. | Lowercasing a local copy in `Validate` accomplishes nothing for downstream consumers. Normalize the field. |
| Document case-sensitivity in the README only | Added a note that `ATLAS_AUTH_MODE` must be lowercase | One typo in a YAML deserializer or env-var injection path silently enables the bypass. Documentation is not a security control. | If a single-byte typo can ship the dashboard open, the code must defend itself, not rely on the operator reading docs. |
| Fix the default branch only | Made the middleware default fail closed but left `Validate` as-is | `Validate` accepts `"Bearer"`, fails to log a warning, and middleware then 401s every request from a "configured" deployment. The operator now has a working "auth enabled" config that 401s its own dashboard. | Both fixes are required. `Validate` should normalize and accept (so configs work as written); middleware fail-closed catches the not-supposed-to-happen case. |
| Trust intuitive enum semantics elsewhere | Not a case-mismatch bug per se but the same family — `nats.go`'s `MaxReconnects(0)` means "never reconnect", not "infinite". Atlas v0.2.0 set `MaxReconnects(0)` and lost reconnect resilience. | Intuition lost to docs. | Whenever an enum value's intuition could go either way, write a regression test that proves the actual semantic. |

## Results & Parameters

### Reproducing the Bug

```bash
# Atlas v0.2.0 (or any pre-fix build):
docker run -d --rm -p 3002:3002 \
  -e ATLAS_AUTH_MODE=Bearer \
  -e ATLAS_AUTH_BEARER_TOKEN=demo-secret \
  ghcr.io/homericintelligence/atlas:v0.2.0

# Without the bug, /readyz with no auth returns 401.
# With the bug:
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:3002/readyz
# → HTTP 200  (bypass!)

# Verify case-sensitivity is the culprit by changing only the env var:
docker run ... -e ATLAS_AUTH_MODE=bearer ...   # all-lowercase
curl ...
# → HTTP 401
```

### Regression Test Pattern (Go)

```go
// Config-level
func TestValidate_NormalizesAuthMode(t *testing.T) {
    for _, in := range []string{"Bearer", "BEARER", "BeArEr", "  bearer\t", "NONE", "BASIC"} {
        c := &Config{AuthMode: in, AuthBearerToken: "x", AuthUser: "u", AuthPass: "p"}
        if err := c.Validate(discardLogger()); err != nil {
            t.Fatalf("must accept normalized %q: %v", in, err)
        }
        if want, got := strings.ToLower(strings.TrimSpace(in)), c.AuthMode; got != want {
            t.Fatalf("AuthMode %q -> got %q, want %q", in, got, want)
        }
    }
}

// Middleware-level (defense in depth)
func TestMiddleware_UnknownModeFailsClosed(t *testing.T) {
    for _, mode := range []AuthMode{AuthMode("Bearer"), AuthMode("BEARER"), AuthMode("magic"), AuthMode("")} {
        h := Middleware(mode, "u", "p", "secret")(okHandler)
        rr := httptest.NewRecorder()
        h.ServeHTTP(rr, httptest.NewRequest(http.MethodGet, "/readyz", nil))
        if rr.Code != http.StatusUnauthorized {
            t.Errorf("mode %q must 401, got %d", string(mode), rr.Code)
        }
    }
}
```

### Generalization Beyond Atlas

This pattern shows up wherever:

- An env var or config string is parsed into a typed enum.
- The middleware/handler compares against typed constants exactly.
- A `default:` branch exists in either the `Validate` switch OR the runtime switch.

Examples to audit in any codebase:

- `LOG_LEVEL=Debug` vs `debug` (less catastrophic, but the same shape).
- Feature-flag enums (`FF_MODE=Strict` vs `strict`).
- Cache-invalidation modes, throttling modes, anything that gates request handling.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/ProjectArgus | Atlas v0.2.0 → v0.2.1 security audit, May 2026 | Bug shipped in v0.2.0 image; fixed in PR #457; regression tests live in `internal/config/config_test.go::TestValidate_NormalizesAuthMode` and `internal/server/auth_test.go::TestMiddleware_UnknownModeFailsClosed` |

## References

- [atlas-go-dashboard-milestone-delivery.md](atlas-go-dashboard-milestone-delivery.md) — original auth middleware design that this bug exposed a gap in
- [ci-shell-grep-case-mismatch.md](ci-shell-grep-case-mismatch.md) — sibling skill on case-mismatch bugs in CI assertions
- [model-id-normalization-resume-fix.md](model-id-normalization-resume-fix.md) — sibling skill on enum normalization for model identifiers
