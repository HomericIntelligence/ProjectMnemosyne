---
name: architecture-container-secret-cmdline-leak-fix
description: "Use when: (1) a secret like ANTHROPIC_API_KEY is passed to a container via `-e VAR=value` on a podman/docker run command line, (2) two container workers use different binaries with different auth paths and need asymmetric fixes, (3) a name-only -e VAR form is added and a pre-flight guard for the unset-var silent-injection case is needed, (4) a 'safe to remove/change' argument is about to be applied across multiple call sites — confirm each site invokes the SAME binary/auth path first, (5) writing a regression test for a credential change — a string-absence test is NOT an auth-regression test, (6) citing a test runner in a verification plan — confirm the runner actually exists in pixi.toml/justfile."
category: architecture
date: 2026-06-19
version: "1.2.0"
user-invocable: false
verification: verified-local
history: architecture-container-secret-cmdline-leak-fix.history
tags: [security, secrets, container, podman, docker, cmdline-leak, anthropic-api-key, oauth, credentials, proc, planning, env-name-only, per-callsite-binary, auth-regression-test, verify-the-runner, asymmetric-fix]
---

# Container Secret Cmdline Leak Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Remove API key / secret values from podman `run -e VAR=value` cmdline to prevent world-readable exposure via `ps auxww` and `/proc/<pid>/cmdline` |
| **Outcome** | SUCCESS — both workers fixed asymmetrically; Odysseus PR #311 merged; Layer-1 acceptance tests pass |
| **Verification** | verified-local — Layer-1 cmdline-absence acceptance tests pass; live container auth probe confirmed on developer machine |
| **History** | [changelog](./architecture-container-secret-cmdline-leak-fix.history) |

## When to Use

- A podman/docker `run` command passes `-e VAR=value` with a secret value on the command line
- A security review flags that the secret is readable via `ps auxww`, `ps -ef`, or `/proc/<pid>/cmdline` by any host user for the process lifetime
- You are about to "fix" the leak by moving the secret to a different `-e` var or another command-line mechanism (this is the same class of bug)
- Two sibling container workers invoke **different binaries** with different auth paths — **asymmetric fixes required**
- Adding the podman name-only `-e VAR` form and needing a pre-flight guard for the silent-injection case when the host var is unset
- You are about to apply a single "safe to remove/change this argument" judgement across MULTIPLE call sites — first confirm each site invokes the SAME binary and auth path
- Writing a bash acceptance test for a cmdline-absence security fix in a repo without pytest

## Verified Workflow

### Quick Reference

```bash
# 1. PROVE the leak class: a secret on the run command line is world-readable on the host.
ps auxww | grep -i ANTHROPIC_API_KEY          # any host user sees it
cat /proc/<container-runtime-pid>/cmdline | tr '\0' ' '   # also exposes it

# 2. Find every injection site AND the binary each site runs.
grep -rn ANTHROPIC_API_KEY e2e/*.py
#  The two workers invoke DIFFERENT binaries with DIFFERENT auth paths:
#    claude-myrmidon.py       -> runs mounted standalone `claude-host` (OAuth-capable)
#    claude-myrmidon-multi.py -> runs image-baked npm `claude` (@anthropic-ai/claude-code), NO claude-host mount

# 3. SINGLE worker fix (OAuth binary — drop env var entirely):
#    Delete the -e line; binary reads creds from mounted ~/.claude/.credentials.json + ~/.claude.json
#    Result: ANTHROPIC_API_KEY not in cmd args at all

# 4. MULTI worker fix (npm binary — name-only form preserves auth):
"-e", "ANTHROPIC_API_KEY",   # podman reads value from host env; value NEVER on cmdline

# 5. Add pre-flight guard (name-only silently injects nothing if host var unset):
if not os.environ.get("ANTHROPIC_API_KEY"):
    log("claude", f"{YELLOW}ANTHROPIC_API_KEY is unset — container auth may fail{NC}")

# 6. Tighten auth-failure heuristic in any live probe:
_AUTH_FAILURE_TOKENS = ("authentication", "invalid api key", "credential", "unauthorized")
_stderr_lower = (result.stderr or "").lower()
if result.returncode != 0 or not out or any(tok in _stderr_lower for tok in _AUTH_FAILURE_TOKENS):
    sys.exit(1)

# 7. Verify no value-bearing form remains:
grep -rn 'ANTHROPIC_API_KEY=' e2e/claude-myrmidon.py e2e/claude-myrmidon-multi.py
# criterion: zero matches
```

### Detailed Steps

1. **Identify the auth path for each worker** — do NOT assume symmetry. Read each worker's
   invocation function and trace which binary it calls:
   - If the binary is a standalone OAuth binary (e.g. `claude-host`) that authenticates via
     mounted credentials files → drop the env var entirely (it is unused and leaking)
   - If the binary is an npm/image-baked CLI whose auth path is unverified → keep the key
     reaching the container but switch to podman name-only `-e VAR` form

2. **Single worker fix** (OAuth binary): delete the `-e ANTHROPIC_API_KEY=...` element from
   the cmd list. Update the docstring to explain why the key is absent. Confirm the OAuth
   credential files are bind-mounted (e.g. `~/.claude`, `~/.claude.json`).

3. **Multi worker fix** (npm binary): replace `"-e", f"ANTHROPIC_API_KEY={os.environ.get(...)}"`
   with `"-e", "ANTHROPIC_API_KEY"`. Podman 4.9.3 name-only `-e VAR`: reads the value from the
   host process environment and injects it into the container — only the name appears on the
   cmdline, never the value.

4. **Add pre-flight guard** for the multi worker: name-only `-e` silently injects nothing if the
   host variable is unset. Log a visible warning so an operator on a host without the key gets a
   clear signal rather than a silent auth break.

5. **Write the acceptance test** as a bash script (`e2e/tests/security/test-*.sh`) matching the
   repo idiom — do NOT use pytest if the repo has no pytest dep. Two layers:
   - Layer 1 (always): import each worker module in Python inline, call the builder with a
     sentinel secret value, assert the value is absent from the joined command string
   - Layer 2 (gated): live container auth probe — skip cleanly if podman or image absent

6. **Tighten auth-failure heuristics** in any live probe helper: avoid broad substrings like
   `"auth"` (matches "author", "authenticated successfully") or `"ERROR" in stdout`. Use specific
   failure tokens and rely on returncode + empty-output as primary signals:
   ```python
   _AUTH_FAILURE_TOKENS = ("authentication", "invalid api key", "credential", "unauthorized")
   _stderr_lower = (result.stderr or "").lower()
   if result.returncode != 0 or not out or any(tok in _stderr_lower for tok in _AUTH_FAILURE_TOKENS):
       sys.exit(1)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Symmetric fix — drop env var in both workers | Applied "drop env var entirely" to both `claude-myrmidon.py` and `claude-myrmidon-multi.py` | Wrong: the workers run different binaries with different auth paths — the single worker invokes the mounted standalone `claude-host` (OAuth, env var droppable), the multi worker invokes the image-baked npm `claude` (`@anthropic-ai/claude-code`) with NO `claude-host` mount | Before generalizing a "safe to remove/change" argument across call sites, confirm each site invokes the SAME binary/auth path |
| Broad `"auth"` substring in auth-failure heuristic | `"auth" in result.stderr.lower()` to detect auth failure | Matches benign substrings: "author", "authorize", "authenticated successfully" — false positives | Use specific failure tokens: "authentication", "invalid api key", "credential", "unauthorized" |
| `"ERROR" in stdout` check in auth-failure heuristic | `"ERROR" in out` to catch auth errors in stdout | Matches any model reply that quotes the word "ERROR" — false positive | Drop stdout check; rely on returncode and empty-output as primary signals |
| Using pytest for acceptance test | Wrote test in pytest style | Odysseus repo has no pytest dep in `pixi.toml`; `just test` runs `ctest` over C++ submodules only | Match the repo's established idiom: standalone bash scripts in `e2e/tests/security/*.sh` |
| Relocate the secret to a different `-e` var | Move ANTHROPIC_API_KEY to another env flag still set as `-e VAR=value` | Still leaks — any `-e VAR=value` argument is visible via `ps auxww` and `/proc/<pid>/cmdline` | Command-line args are world-readable. Remove the VALUE from the cmdline (name-only `-e`, file, stdin, or delete), not move it to another flag |
| Remove the secret entirely when it must still reach the container | Delete the `-e ANTHROPIC_API_KEY` line everywhere as the KISS fix | Breaks auth where the env var is the only working path (e.g. the multi worker's npm `claude`) | Use podman/docker name-only `-e VAR` so the value stays off the cmdline but is still injected from the host environment |
| Assert removal of `-e ANTHROPIC_API_KEY` is behavior-neutral for all workers | Applied one "safe to remove the env var" judgement to BOTH workers | Wrong: the workers run different binaries with different auth paths | Before generalizing a safety argument across call sites, confirm each site's binary/auth path |

## Results & Parameters

| Parameter | Verified Value |
|-----------|----------------|
| Podman version | 4.9.3 (name-only `-e VAR` confirmed) |
| Name-only `-e VAR` behavior | Podman reads value from host process env; value never appears on cmdline |
| Single worker binary | `claude-host` (standalone OAuth binary, mounted `:ro`) |
| Multi worker binary | `claude` (npm binary baked into `achaean-claude:latest`, no `claude-host` mount) |
| Auth-failure tokens | `"authentication"`, `"invalid api key"`, `"credential"`, `"unauthorized"` |
| Test runner | Bash script (`e2e/tests/security/*.sh`), not pytest |
| Verification command | `grep -rn 'ANTHROPIC_API_KEY=' <workers>` → zero matches |
| PR | Odysseus #311 (merged) |
| Issue | Odysseus #180 |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Issue #180, PR #311 | Both myrmidon workers fixed asymmetrically; Layer-1 acceptance tests pass; PR merged |
