---
name: cpp-nlohmann-json-value-nullptr-type-error
description: "Fix nlohmann/json value() returning nullptr_t when passed nullptr as default, causing .is_null() compile error. Use when: (1) json.value(key, nullptr).is_null() causes compile error about member reference base type nullptr_t, (2) checking if a json field is null using value() with nullptr default, (3) clang-tidy reports clang-diagnostic-error on a .value() call."
category: debugging
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - nlohmann-json
  - cpp
  - cpp20
  - nullptr
  - clang-tidy
  - type-error
---

# nlohmann/json value() Returns nullptr_t Not json When Passed nullptr

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Fix clang-diagnostic-error when calling .is_null() on result of json::value() with nullptr default |
| **Outcome** | Compile error fixed by wrapping nullptr in json() constructor |
| **Verification** | verified-ci |

## When to Use

- `json.value("key", nullptr).is_null()` causes compile error
- Error: "member reference base type 'std::nullptr_t' is not a structure or union"
- Checking if a json field is null using the `value()` accessor
- clang-tidy reports `[clang-diagnostic-error]` on a `.value()` call with nullptr

## Verified Workflow

### Quick Reference

```cpp
// WRONG — json::value(key, nullptr) returns nullptr_t, not json:
if (obj.value("myField", nullptr).is_null()) { ... }

// CORRECT — wrap nullptr in json() to force return type json:
if (obj.value("myField", json(nullptr)).is_null()) { ... }

// ALTERNATIVE — check contains() + is_null() explicitly:
if (!obj.contains("myField") || obj["myField"].is_null()) { ... }
```

### Detailed Steps

1. Find the call to `json::value()` where `nullptr` is passed as the default
2. Replace bare `nullptr` with `json(nullptr)` to explicitly construct a json null value
3. The return type of `value<T>(key, default)` is deduced from the type of `default` — `nullptr` deduces to `nullptr_t`, but `json(nullptr)` deduces to `json`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Bare nullptr default | `obj.value("completedAt", nullptr).is_null()` | clang-diagnostic-error: "member reference base type 'std::nullptr_t' is not a structure or union" | json::value() returns the type of the default argument — nullptr gives nullptr_t, not json |

## Results & Parameters

```cpp
// nlohmann/json value() signature (simplified):
// template<typename ValueType>
// ValueType value(const key_type& key, const ValueType& default_value) const;
//
// When called with nullptr, ValueType = std::nullptr_t
// When called with json(nullptr), ValueType = json  ← correct

// Real-world example from HomericIntelligence/ProjectAgamemnon store.cpp:
if (body.contains("status") && body["status"] == "completed" &&
    it->second.value("completedAt", json(nullptr)).is_null()) {
  it->second["completedAt"] = now_iso8601();
}

// Error text caught by clang-tidy:
// src/store.cpp:210:47: error: member reference base type 'std::nullptr_t'
//     is not a structure or union [clang-diagnostic-error]
//     it->second.value("completedAt", nullptr).is_null()
//                                              ^~~~~~~~
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | store.cpp update_task() — check completedAt null before setting timestamp | CI passes after changing nullptr to json(nullptr) |
