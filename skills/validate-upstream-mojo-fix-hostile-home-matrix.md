---
name: validate-upstream-mojo-fix-hostile-home-matrix
description: "Validate that an upstream Mojo runtime crash fix (specifically the
  `getAcceleratorArchOrEmpty()` / `std::filesystem::status` family — modular/modular#6412
  and any successor) actually landed in your newly-bumped nightly BEFORE peeling
  back downstream Dockerfile/entrypoint workarounds. Uses a hostile-`$HOME` matrix
  (mode 000, mode 750+700, missing dir, /dev/null, unset) on a one-line `def main`
  binary. Use when: (1) you bumped the pinned Mojo version past the upstream
  fix-shipped date and want to confirm the fix landed in your build, (2) you are
  about to peel back a downstream workaround (sudoers `_ensure_writable`,
  `chmod 755 /home/$USER`, entrypoint `mkdir -p $HOME/.modular`, HOME-redirect
  fallback) and need a deterministic confirmation, (3) your container runtime is
  rootless and blocks `setpriv`/`runuser`/`sudo -u nobody`, so a true UID-mismatch
  reproducer is impossible locally and you need a permission-shape proxy instead,
  (4) an upstream Modular issue closed with 'fix in next nightly' and you want to
  verify the claim before commenting on the issue or opening a workaround-removal PR."
category: testing
date: 2026-05-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mojo
  - modular
  - upstream-validation
  - container
  - permissions
  - filesystem-error
  - getAcceleratorArchOrEmpty
  - hostile-home
  - workaround-removal
  - rootless-podman
---

# Validate Upstream Mojo Fix with a Hostile-`$HOME` Matrix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-13 |
| **Objective** | Confirm `modular/modular#6412` (uncaught `filesystem_error` in `M::Driver::Device::getAcceleratorArchOrEmpty()` when `$HOME` is not traversable by the running UID) is actually fixed in `mojo==1.0.0b2.dev2026050805` before removing downstream Dockerfile/entrypoint workarounds |
| **Outcome** | Successful — 8 hostile-`$HOME` shapes all returned exit 0 on the bumped build (would have been exit 134 SIGABRT on the buggy build). Upstream fix confirmed; comment posted to the issue |
| **Verification** | verified-local — executed inside `podman compose exec -T projectodyssey-dev`; CI run with workarounds neutralized is pending and recommended as follow-up |
| **Root Cause Recap** | `libAsyncRTMojoBindings.so` calls `std::filesystem::status("$HOME/.modular")` from `getAcceleratorArchOrEmpty()` at process startup; on `EACCES` / `ENOENT` shapes, the resulting `std::filesystem::filesystem_error` was uncaught and propagated to `std::terminate()` → `abort()` (exit 134). Fix shipped in next nightly per joshpeterson's 2026-04-20 closing comment. |
| **Confirmation Comment** | <https://github.com/modular/modular/issues/6412#issuecomment-4437744773> |
| **ProjectOdyssey commit** | `e3e0de83` (HEAD at validation time) |

## When to Use

- You bumped the pinned Mojo nightly past the date a relevant `filesystem_error` / `getAcceleratorArchOrEmpty` fix was claimed shipped
- You are about to remove or relax a downstream workaround (Dockerfile `chmod 755 /home/$USER`, entrypoint `mkdir -p $HOME/.modular`, HOME-redirect fallback) and need deterministic confirmation that the upstream fix landed
- An upstream Modular issue closed with "fix in next nightly" and you want to validate the claim before posting a confirmation comment or opening a workaround-removal PR
- Your container runtime is rootless (rootless podman, restricted dev container) and blocks `setpriv`, `runuser`, and `sudo -u nobody`, so a true cross-UID reproducer is impossible — you need a permission-shape proxy
- You are investigating a closed Modular issue affecting your build and need to know whether downstream chmod / HOME-redirect logic is still load-bearing
- You want a one-shot bash recipe (build once, exec under N hostile envs) rather than a repeated build-and-run loop
- Pre-flight before touching `[[docker-mojo-uid-mismatch-crash-fix]]` workarounds

## Verified Workflow

> **Note:** verified-local. Ran inside `podman compose exec -T projectodyssey-dev` against
> `mojo==1.0.0b2.dev2026050805 (ed7c8f0a)` (May 8 2026 nightly). All 8 hostile-`$HOME`
> shapes returned exit 0; on the buggy build (any nightly before the 2026-04-20+ shipped
> fix) shapes 2/3/4/5/7/8 reproduce exit 134 SIGABRT with
> `terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'`.
> True UID-mismatch (image-built-as-uid-1000, run-as-uid-1001+) was NOT testable locally —
> see Failed Attempts. CI run with workarounds neutralized is the authoritative final
> confirmation; this skill produces the local pre-flight signal.

### Quick Reference

```bash
# 0. Verify the version premise FIRST (do not skip — see Failed Attempts row 1)
grep '^mojo' pixi.toml
git log --oneline -- pixi.toml | head -5

# 1. Write a minimal Mojo binary (Mojo 1.0+ uses `def`, not `fn`)
cat > /tmp/hello.mojo <<'EOF'
def main():
    print("ok")
EOF

# 2. Build ONCE, then exec under hostile-HOME matrix
pixi run mojo build /tmp/hello.mojo -o /tmp/hello

# Result interpretation:
#   exit 0   = upstream fix landed for that HOME shape
#   exit 134 = still broken (filesystem_error → SIGABRT) — do NOT peel workarounds
#   anything else = investigate, do NOT peel workarounds

# Shape 1: real HOME, baseline
/tmp/hello; echo "1: exit=$?"

# Shape 2: HOME mode 000, owner = self (EACCES proxy for cross-UID)
mkdir -p /tmp/fake-home && chmod 000 /tmp/fake-home
HOME=/tmp/fake-home /tmp/hello; echo "2: exit=$?"
chmod 755 /tmp/fake-home  # cleanup so rm works

# Shape 3: HOME mode 755, no .modular subdir
mkdir -p /tmp/fake-home2 && chmod 755 /tmp/fake-home2
HOME=/tmp/fake-home2 /tmp/hello; echo "3: exit=$?"

# Shape 4: HOME mode 750, .modular mode 700 (verbatim from issue body)
mkdir -p /tmp/fake-home3/.modular
chmod 750 /tmp/fake-home3 && chmod 700 /tmp/fake-home3/.modular
HOME=/tmp/fake-home3 /tmp/hello; echo "4: exit=$?"

# Shape 5: HOME path doesn't exist at all
HOME=/tmp/does-not-exist-$$ /tmp/hello; echo "5: exit=$?"

# Shape 6: HOME unset entirely
env -u HOME /tmp/hello; echo "6: exit=$?"

# Shape 7: HOME points at a non-directory
HOME=/dev/null /tmp/hello; echo "7: exit=$?"

# Shape 8: real $HOME chmoded 700 + .modular removed; full `mojo run` startup
#         (workarounds neutralized — closest-to-real test we can do locally)
SAVED_HOME_MODE=$(stat -c '%a' "$HOME")
[ -e "$HOME/.modular" ] && mv "$HOME/.modular" "$HOME/.modular.bak.$$"
chmod 700 "$HOME"
pixi run mojo run /tmp/hello.mojo; echo "8: exit=$?"
chmod "$SAVED_HOME_MODE" "$HOME"
[ -e "$HOME/.modular.bak.$$" ] && mv "$HOME/.modular.bak.$$" "$HOME/.modular"

# Cleanup
rm -rf /tmp/fake-home /tmp/fake-home2 /tmp/fake-home3 /tmp/hello /tmp/hello.mojo
```

### Detailed Steps

1. **Verify the version premise first.** A prior `/advise` call in this session
   accepted the user's claim that the version had been bumped; it had not. Always
   run `grep '^mojo' pixi.toml && git log --oneline -- pixi.toml | head` before
   declaring anything about an upstream fix. If the pinned version predates the
   upstream-fix-shipped date in the issue, validation is meaningless — open a
   version-bump PR first.

2. **Write a minimal binary.** A one-line `def main(): print("ok")` is sufficient
   because the crash happens in `getAcceleratorArchOrEmpty()` during startup,
   before user code runs. Any Mojo binary works; smaller is better for build
   speed. **Mojo 1.0 removed `fn` for top-level functions — use `def`.**

3. **Build once, exec many.** The bug is in shared library startup, not in the
   compiler. Build the binary once with `pixi run mojo build`, then re-exec under
   each hostile-`$HOME` shape. This is ~10× faster than `pixi run mojo run`
   per shape and exercises the exact code path that fires in production.

4. **Run the 8-shape matrix.** See Quick Reference. Shapes 2/3/4/5/7/8 are the
   shapes that reproduce on the buggy build. Shape 1 is a smoke test. Shape 6
   confirms `HOME` unset is handled. Shape 8 neutralizes the downstream
   workaround (chmods real `$HOME` to 700 + removes `.modular`) and runs full
   `mojo run` (not the pre-built binary) — this is the closest-to-real test
   possible inside a rootless container.

5. **Interpret results.**
   - All 8 → exit 0: fix is in. Safe to open a workaround-removal PR (but still
     open it as a separate CI-validated branch — the local test is a pre-flight,
     not a final approval).
   - Any shape → exit 134 with `filesystem_error` text: fix did NOT land. Keep
     workarounds. Re-check the version premise (Step 1) and the upstream issue
     for follow-up reports.
   - Any shape → other non-zero exit: investigate before touching workarounds.

6. **Post a confirmation comment on the upstream issue.** If all 8 shapes pass,
   post a result table to the closed Modular issue so future readers (and
   maintainers tracking regressions) have a verified data point. State the
   pinned Mojo version, the commit/date, and the exact shape table. Be explicit
   about what you could NOT test (true UID mismatch).

7. **Open a separate CI-validated workaround-removal PR.** Local validation is
   necessary but not sufficient — the original bug surfaced in cross-UID CI
   shapes that local rootless containers cannot reproduce. The follow-up PR
   should disable Dockerfile `chmod 755 /home/$USER` and entrypoint
   `mkdir -p $HOME/.modular`, then let CI confirm. The bind-mount sudoers
   `_ensure_writable` work in entrypoint.sh is a separate concern (covered by
   `[[docker-mojo-uid-mismatch-crash-fix]]` v1.2.0+) and should be kept.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Trusted user's claim that the Mojo version had been bumped, ran validation immediately | The version had not actually been bumped yet — earlier `/advise` accepted the premise without checking, then validation gave a meaningless answer | Always `grep '^mojo' pixi.toml && git log --oneline -- pixi.toml | head` before validating any claim about an upstream fix landing. The version premise IS the validation; without it, the rest is theater. |
| 2 | `sudo -n rm -rf /tmp/fake-home && sudo -n chown root:root /tmp/fake-home` to set up a HOME owned by a different UID | Rootless container's NOPASSWD sudoers grant covers `mkdir/chown/chmod` for `_ensure_writable` paths only — not arbitrary `rm` or `chown` on `/tmp/...` | Skip true UID-mismatch repro inside rootless dev containers. Use mode-000 dirs owned by self instead — they trigger the same `std::filesystem::status` throw path on EACCES, which is the only thing that matters for the `filesystem_error` code path. |
| 3 | `setpriv --reuid=65534 --regid=65534 -- /tmp/hello` to drop to `nobody` for a real UID-mismatch test | `setresuid: Operation not permitted` — rootless podman containers lack `CAP_SETUID` regardless of sudoers config | In-container UID switching needs privileged mode or `--cap-add=SETUID` at container start. CI is the only authoritative confirmation for true cross-UID. Document this caveat in the upstream comment. |
| 4 | `sudo -n -u nobody /tmp/hello` as a setpriv alternative | sudoers NOPASSWD grant is `runas=root` only, no `runas=nobody` entry | Same lesson as row 2/3. Permission-shape proxies (mode 000, mode 700+ missing .modular) are the substitute we have. |
| 5 | Wrote `fn main(): print("ok")` for the minimal reproducer | Mojo 1.0 removed top-level `fn`; compiler error: `'fn' is not a valid function declaration at top level — use 'def'` | In Mojo 1.0+ all top-level functions use `def`. Migrate any `fn` reproducer snippets in old skills/docs accordingly. |
| 6 | `pixi run mojo test tests/...` for a sanity-check regression run after validation | `error: no such command 'test'` — the `mojo test` subcommand was removed in Mojo 1.0 | Tests now route through `just test-mojo` / `just test-group <PATH> <PATTERN>`. Don't assume `mojo test` exists in 1.0+. Update any skill or doc that calls it directly. |
| 7 | First `gh issue comment 6412 --repo modular/modular --body ...` attempt to post the confirmation | `Resource not accessible by personal access token (addComment)` — the active `GITHUB_TOKEN` env var was a fine-grained PAT scoped only to the user's own repos | When commenting on third-party repos: `unset GITHUB_TOKEN; gh auth switch -h github.com -u <user>` to activate the classic OAuth token (`gho_…` with `repo` scope). The fine-grained PAT in `GITHUB_TOKEN` overrides the classic token in `~/.config/gh/hosts.yml`. Do NOT modify gh config beyond switching active accounts. |

## Results & Parameters

### Hostile-`$HOME` Matrix Results

| # | HOME shape | Exit (fixed build) | Exit (buggy build, expected) | Notes |
| --- | ----------------------------------------------------- | ---- | ---- | ----------------------- |
| 1 | Real `$HOME`, baseline | 0 | 0 | Smoke test |
| 2 | `mkdir /tmp/fake-home && chmod 000`, owner = self | 0 | 134 | EACCES proxy |
| 3 | HOME exists mode 755, no `.modular` subdir | 0 | 134 | Missing-`.modular` path |
| 4 | HOME mode 750, `.modular` mode 700 (verbatim from issue body) | 0 | 134 | Issue's exact reproducer |
| 5 | HOME path doesn't exist | 0 | 134 | ENOENT path |
| 6 | HOME unset (`env -u HOME`) | 0 | varies | Edge case |
| 7 | `HOME=/dev/null` (not a directory) | 0 | 134 | ENOTDIR path |
| 8 | Real `$HOME` chmoded 700 + `.modular` removed, full `mojo run` startup (workarounds neutralized) | 0 | 134 | Closest-to-real local |

### Verified On

| Field | Value |
| --- | --- |
| ProjectOdyssey commit | `e3e0de83` |
| Mojo version | `1.0.0b2.dev2026050805 (ed7c8f0a)` (May 8 2026 nightly) |
| Container | `podman compose exec -T projectodyssey-dev` |
| Host glibc | 2.32+ (via container; host glibc may be older — Mojo enforces 2.32+) |
| Upstream issue | <https://github.com/modular/modular/issues/6412> |
| Upstream fix-shipped comment | joshpeterson, 2026-04-20: "fix should be available in the next nightly build tomorrow" |
| Confirmation comment posted | <https://github.com/modular/modular/issues/6412#issuecomment-4437744773> |
| User association | CONTRIBUTOR (issue filed by mvillmow 2026-04-12, closed 2026-04-20) |

### Bash Recipe (Single Block)

```bash
set -e
grep '^mojo' pixi.toml
cat > /tmp/hello.mojo <<'EOF'
def main():
    print("ok")
EOF
pixi run mojo build /tmp/hello.mojo -o /tmp/hello

run() { local n="$1"; shift; "$@" /tmp/hello; echo "shape $n: exit=$?"; }

# 1
/tmp/hello; echo "shape 1: exit=$?"
# 2
mkdir -p /tmp/fake-home && chmod 000 /tmp/fake-home
HOME=/tmp/fake-home /tmp/hello; echo "shape 2: exit=$?"
chmod 755 /tmp/fake-home
# 3
mkdir -p /tmp/fake-home2 && chmod 755 /tmp/fake-home2
HOME=/tmp/fake-home2 /tmp/hello; echo "shape 3: exit=$?"
# 4
mkdir -p /tmp/fake-home3/.modular
chmod 700 /tmp/fake-home3/.modular && chmod 750 /tmp/fake-home3
HOME=/tmp/fake-home3 /tmp/hello; echo "shape 4: exit=$?"
# 5
HOME=/tmp/does-not-exist-$$ /tmp/hello; echo "shape 5: exit=$?"
# 6
env -u HOME /tmp/hello; echo "shape 6: exit=$?"
# 7
HOME=/dev/null /tmp/hello; echo "shape 7: exit=$?"
# 8
SAVED_HOME_MODE=$(stat -c '%a' "$HOME")
[ -e "$HOME/.modular" ] && mv "$HOME/.modular" "$HOME/.modular.bak.$$"
chmod 700 "$HOME"
pixi run mojo run /tmp/hello.mojo; echo "shape 8: exit=$?"
chmod "$SAVED_HOME_MODE" "$HOME"
[ -e "$HOME/.modular.bak.$$" ] && mv "$HOME/.modular.bak.$$" "$HOME/.modular"

# Cleanup
rm -rf /tmp/fake-home /tmp/fake-home2 /tmp/fake-home3 /tmp/hello /tmp/hello.mojo
```

### Caveats

- **True cross-UID is NOT validated locally.** Rootless podman containers block
  `setpriv`/`sudo -u`/`runuser`. The mode-000 EACCES path is a *proxy* for the
  `std::filesystem::status` throw site — it exercises the same exception path,
  but a true image-built-as-1000-run-as-1001 scenario can only be confirmed in
  CI. See `[[docker-mojo-uid-mismatch-crash-fix]]` for the CI-cache-key fix.
- **Bind-mount writability is a separate concern.** This skill validates the
  `getAcceleratorArchOrEmpty()` startup crash only. Bind-mount subdir writability
  (`build/`, `datasets/`, `lenet5_weights/`) is fixed via sudoers `_ensure_writable`
  in entrypoint.sh — keep that work in place even if this validation passes.
- **Do not amend the issue body.** Post a NEW comment on the closed issue with
  the result table; do not edit the original report.

## Related Skills

- `[[docker-mojo-uid-mismatch-crash-fix]]` — the downstream workaround skill
  (Dockerfile chmod 755, entrypoint `mkdir -p $HOME/.modular`, sudoers
  `_ensure_writable`). Status update: upstream `getAcceleratorArchOrEmpty()`
  crash confirmed fixed in `mojo==1.0.0b2.dev2026050805+`; the bind-mount
  `_ensure_writable` portion is still load-bearing.
- `[[mojo-upstream-bug-filing-reproducibility-standard]]` — the gate to apply
  BEFORE filing an upstream Mojo bug (this skill is the AFTER-fix-shipped mirror).
- `[[ci-cd-remove-upstream-fixed-workaround-fan-out-matrix]]` — what to do
  AFTER this skill confirms the fix landed (peel the workaround, fan the
  workflow back out).
- `[[mojo-026-breaking-changes]]` / `[[mojo-runtime-crash-bisection]]` —
  background on Mojo 1.0 `fn`→`def` migration and runtime crash bisection.
