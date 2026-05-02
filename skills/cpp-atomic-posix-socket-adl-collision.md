---
name: cpp-atomic-posix-socket-adl-collision
description: "Fix C++ build failures when std::atomic members break POSIX socket API calls. Use when: (1) adding std::atomic<int> to a class that uses POSIX socket functions causes build errors like 'call to deleted constructor of std::atomic<int>', (2) a bind() call suddenly resolves as std::bind instead of POSIX bind(), (3) socket/file descriptor operations fail with type errors after a member is changed to atomic."
category: debugging
date: 2026-03-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cpp
  - atomic
  - posix
  - adl
  - socket
---

# C++ std::atomic POSIX Socket ADL Collision

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-31 |
| **Objective** | Fix build failures when `std::atomic<int>` members cause unqualified POSIX socket calls to resolve incorrectly via ADL |
| **Outcome** | All sanitizer CI builds (asan/lsan/ubsan/tsan/msan) pass after applying `.load()` + `::` qualification fixes |
| **Verification** | verified-ci |

## When to Use

- A class has `std::atomic<int>` or `std::atomic<uint16_t>` members (e.g., `server_fd_`, `port_`)
- The class also calls POSIX socket functions: `bind()`, `accept()`, `listen()`, `getsockname()`, `setsockopt()`, `close()`, `poll()`
- Build fails with: `error: call to deleted constructor of 'std::atomic<int>'` at a socket call site
- The error message mentions `std::bind` in the call stack even though you wrote `bind()`
- You added `<atomic>` or `<functional>` to a file that previously only used `<sys/socket.h>`

## Verified Workflow

### Quick Reference

```cpp
// BEFORE (broken — bind() resolves as std::bind via ADL):
bind(server_fd_, (struct sockaddr*)&address, sizeof(address))
htons(port_)
setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))
pfd.fd = server_fd_;

// AFTER (correct — explicit POSIX scope + .load()):
::bind(server_fd_.load(), (struct sockaddr*)&address, sizeof(address))
htons(port_.load())
setsockopt(server_fd_.load(), SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))
pfd.fd = server_fd_.load();
```

### Detailed Steps

1. **Understand the root cause**: When `<functional>` or `<atomic>` is included (directly or transitively), `std::bind` is in scope. Unqualified `bind(fd, ...)` triggers ADL — the compiler finds `std::bind` which takes a callable and arguments, not file descriptors. The `std::atomic<int>` argument cannot be copy-constructed (deleted), producing the cryptic error.

2. **Find all affected call sites** — every place a `std::atomic<T>` is passed to a POSIX function:
   ```bash
   # Find socket calls using atomic members (look for patterns like member_fd_, port_)
   grep -n "bind\|listen\|accept\|setsockopt\|getsockname\|close\|pfd\.fd" src/file.cpp
   ```

3. **Apply two fixes to each call site**:
   - **Add `::` prefix** to ambiguous POSIX functions: `::bind(...)`, `::close(...)`, `::accept(...)`, `::listen(...)`, `::getsockname(...)`, `::setsockopt(...)`
   - **Add `.load()`** to extract the `int` value from each `std::atomic<int>`: `server_fd_.load()`

4. **`htons()` does NOT need `::` prefix** (it's in `<netinet/in.h>`, not conflicted), but still needs `.load()` for atomic port values.

5. **`close()` is not ambiguous** but still needs `.load()`: `close(server_fd_.load())`

6. **Assignment to non-atomic fields**: `pfd.fd = server_fd_.load()` — `pollfd.fd` is plain `int`

### Full Pattern Reference

```cpp
// All call sites that need fixing when server_fd_ is std::atomic<int>
// and port_ is std::atomic<uint16_t>:

// socket() — returns int, store normally: server_fd_ = socket(AF_INET, SOCK_STREAM, 0)
// setsockopt — needs load + scope:
::setsockopt(server_fd_.load(), SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))

// bind — needs load + scope (most critical — ADL collision here!):
::bind(server_fd_.load(), (struct sockaddr*)&address, sizeof(address))

// htons on atomic port — needs load (no :: needed):
address.sin_port = htons(port_.load())

// getsockname — needs load + scope:
::getsockname(server_fd_.load(), (struct sockaddr*)&actual_address, &len)

// listen — needs load + scope:
::listen(server_fd_.load(), BACKLOG)

// poll — struct field assignment needs load:
pfd.fd = server_fd_.load()

// accept — needs load + scope:
int client_fd = ::accept(server_fd_.load(), (struct sockaddr*)&addr, &len)

// close — needs load (no ADL issue but still needs value):
close(server_fd_.load())

// Conditional checks — needs load:
if (server_fd_.load() >= 0) { ... }
if (server_fd_.load() < 0) { ... }
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Just adding `.load()` without `::` on `bind()` | `bind(server_fd_.load(), ...)` | ADL still resolves `bind` as `std::bind` even with plain `int` argument | Must add `::` to explicitly select global namespace `bind` |
| Only fixing `bind()` | Fixed bind but left setsockopt/getsockname/listen with atomic members | Other call sites still pass `std::atomic<int>` directly to POSIX APIs | Audit ALL socket call sites systematically with grep |
| Treating as a simple type error | Thought it was just about passing int instead of atomic | The real issue is ADL + name lookup, not just type conversion | `std::bind` in scope from `<functional>` (via `<atomic>`) hijacks unqualified `bind()` |
| Only applying `.load()` to bind | `bind(server_fd_.load(), ...)` without `::` prefix | ADL still finds `std::bind` and tries to match | Both fixes required together: `::` prefix AND `.load()` |

## Results & Parameters

### Why This Happens

```
Headers that introduce std::bind into scope:
  <atomic>  → includes <functional> → introduces std::bind

ADL lookup for bind(server_fd_, ...) where server_fd_ is atomic<int>:
  → Finds std::bind (takes callable + args)
  → std::atomic<int> cannot be copy-constructed (deleted constructor)
  → Error: "call to deleted constructor of std::atomic<int>"
```

### Grep Pattern to Find All Affected Sites

```bash
# Find all POSIX socket function calls in a file
grep -n "bind\|listen\|accept\|setsockopt\|getsockname\|close\|pfd\.fd\|pollfd\|htons" src/monitoring/health_check_server.cpp

# Find atomic member usages
grep -n "server_fd_\|port_\." src/monitoring/health_check_server.cpp
```

### Verification

After fixing, all sanitizer builds should pass:
- `Test (asan)` — AddressSanitizer
- `Test (lsan)` — LeakSanitizer
- `Test (ubsan)` — UndefinedBehaviorSanitizer
- `Test (tsan)` — ThreadSanitizer (may have pre-existing flaky tests, unrelated)
- `Code Coverage` — Coverage build

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | PR #146 — `health_check_server.cpp` atomics | All sanitizer builds pass in CI 2026-03-31 |
