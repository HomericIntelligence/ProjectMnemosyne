---
name: cpp-deprecated-field-internal-use-pragma-suppression
description: "Suppress -Wdeprecated-declarations in the struct/class's own .cpp when a field is marked [[deprecated]]. Use when: (1) adding [[deprecated(\"...\")]] to a C++ struct/class member causes the struct's own implementation file to fail under -Werror,-Wdeprecated-declarations, (2) internal assignments to a deprecated field need to be silenced without removing the deprecation marker, (3) a deprecation-marker PR must not refactor internals."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cpp
  - deprecated
  - pragma
  - werror
  - wdeprecated-declarations
  - diagnostic-suppression
  - struct-field
---

# C++ `[[deprecated]]` Field Causes Own .cpp to Fail Under `-Werror`

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Add `[[deprecated("...")]]` to a C++ struct field without breaking the struct's own implementation file under `-Werror,-Wdeprecated-declarations` |
| **Outcome** | Successful — CI build passed after wrapping internal assignments with `#pragma GCC diagnostic` blocks |
| **Verification** | verified-ci — applied to ProjectKeystone PR #545, `src/core/message.cpp` |

## When to Use

- Adding `[[deprecated("...")]]` to a struct or class **member** in a C++ project with `-Werror`
- The struct's own `.cpp` assigns to the deprecated field internally and now fails to compile
- You want to keep the deprecation marker for external callers without refactoring internals in the same PR
- CI error resembles: `error: 'T field' is deprecated [-Werror,-Wdeprecated-declarations]` pointing at your own source file

## Verified Workflow

### Quick Reference

```cpp
// Wrap a single assignment:
_Pragma("GCC diagnostic push")
_Pragma("GCC diagnostic ignored \"-Wdeprecated-declarations\"")
msg.command = cmd;
_Pragma("GCC diagnostic pop")

// Wrap a block of consecutive assignments:
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
msg.command = actionTypeToString(action);
msg.command = "CANCEL_TASK";
msg.command = cmd;
#pragma GCC diagnostic pop
```

### Detailed Steps

1. **Add the deprecation marker** to the struct field in the header:

   ```cpp
   struct KeystoneMessage {
     [[deprecated("Use 'action' field instead; 'command' will be removed in v3.0")]]
     std::string command;
     // ...
   };
   ```

2. **Build** — CI (or local `-Werror` build) will now fail with errors like:

   ```
   src/core/message.cpp:42:7: error: 'std::string KeystoneMessage::command' is deprecated
       [-Werror,-Wdeprecated-declarations]
      msg.command = cmd;
          ^~~~~~~
   ```

3. **Identify all internal assignment/read sites** in the struct's own `.cpp`:

   ```bash
   grep -n "\.command" src/core/message.cpp
   ```

4. **Wrap each site** (or each consecutive block) with diagnostic suppression:

   - For a single assignment, use `_Pragma` (works inside macros and inline functions):

     ```cpp
     _Pragma("GCC diagnostic push")
     _Pragma("GCC diagnostic ignored \"-Wdeprecated-declarations\"")
     msg.command = cmd;
     _Pragma("GCC diagnostic pop")
     ```

   - For a block of consecutive uses, prefer the cleaner `#pragma` directive form:

     ```cpp
     #pragma GCC diagnostic push
     #pragma GCC diagnostic ignored "-Wdeprecated-declarations"
     msg.command = actionTypeToString(action);
     msg.command = "CANCEL_TASK";
     msg.command = cmd;
     #pragma GCC diagnostic pop
     ```

5. **Rebuild** — the internal uses are now silenced; external callers still see the deprecation warning.

6. **Verify CI passes** with `-Werror` enabled.

### Why Not Remove the Deprecation?

The deprecation is intentional — external callers must migrate. The internal uses are the legacy
path that has not been ripped out yet. Removing the deprecation defeats the purpose of the PR.

### Why Not Refactor Internal Uses?

Out of scope for a deprecation-marker PR. The PR's purpose is to **start** the deprecation cycle,
not finish migrating internals. Mixing refactoring into the same PR obscures reviewability and
increases blast radius.

### Clang Compatibility

Both `#pragma GCC diagnostic` and `_Pragma("GCC diagnostic ...")` are recognized by Clang as
well as GCC. No separate `#pragma clang diagnostic` block is needed for mixed-compiler projects.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| No suppression | Added `[[deprecated]]` and submitted PR | Internal assignments in the same `.cpp` triggered `-Wdeprecated-declarations`; build failed under `-Werror` | The compiler has no automatic exemption for "a class's own implementation file" — all call sites are treated equally |
| Removing deprecation | Considered removing `[[deprecated]]` to silence CI | Would defeat the purpose of the deprecation-marker PR; external callers would not be warned | Keep the deprecation, suppress only the internal legacy sites |
| Refactoring internals | Considered migrating all internal uses in the same PR | Out of scope; changes review surface, increases risk, conflates two separate concerns | Do the pragma suppression now; schedule the internal migration as a follow-up issue |

## Results & Parameters

### Pattern Summary

| Scenario | Pragma Form | When to Use |
|----------|-------------|-------------|
| Single assignment | `_Pragma("GCC diagnostic push/ignored/pop")` | Inside macros, template bodies, or single-line contexts |
| Block of assignments | `#pragma GCC diagnostic push/ignored/pop` | Cleaner for 2+ consecutive uses in a plain `.cpp` block |

### Verified on ProjectKeystone

- **File**: `src/core/message.cpp`
- **PR**: ProjectKeystone #545 (2026-05-09)
- **Compiler flags**: `-Werror,-Wdeprecated-declarations` (via CMake)
- **Fields suppressed**: `KeystoneMessage::command` (3 assignment sites)
- **CI result**: Build passed (asan / lsan / ubsan variants)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PR #545 deprecating `KeystoneMessage::command` field | `src/core/message.cpp`, 3 internal assignments wrapped, CI green |
