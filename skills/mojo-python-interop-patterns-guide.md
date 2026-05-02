---
name: mojo-python-interop-patterns-guide
description: "Canonical Mojo-Python interop patterns from Modular. Use when: (1) calling Python libraries from Mojo, (2) converting between PythonObject and Mojo types, (3) building Python extension modules in Mojo, (4) exposing Mojo structs to Python."
category: architecture
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, python, interop, pythonobject, extension-module, modular-upstream]
---

# Mojo-Python Interop Patterns Guide

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Canonical patterns for Mojo ↔ Python interoperability |
| **Outcome** | Authoritative reference from Modular for Python interop in Mojo |
| **Source** | [modular/skills](https://github.com/modular/skills) (Apache 2.0) |

## When to Use

- Calling Python libraries (numpy, etc.) from Mojo
- Converting between `PythonObject` and Mojo types (`Int`, `String`, `Float64`)
- Building Python extension modules (`.so`) with `PythonModuleBuilder`
- Exposing Mojo structs with methods to Python consumers
- Using `mojo.importer` for auto-compilation of `.mojo` files from Python

## Verified Workflow

### Quick Reference

```mojo
from std.python import Python, PythonObject

# Import Python modules
var np = Python.import_module("numpy")

# PythonObject → Mojo: MUST use py= keyword (NOT positional)
var i = Int(py=py_obj)
var f = Float64(py=py_obj)
var s = String(py=py_obj)
var b = Bool(py=py_obj)            # Bool is the exception — positional also works
```

### Common WRONG/CORRECT Patterns

| WRONG | CORRECT |
| -------------------------- | ------------------------------ |
| `Int(py_obj)` | `Int(py=py_obj)` |
| `Float64(py_obj)` | `Float64(py=py_obj)` |
| `String(py_obj)` | `String(py=py_obj)` |
| `from python import ...` | `from std.python import ...` |

### Mojo → Python Conversions

Types implementing `ConvertibleToPython` auto-convert when passed to Python functions.
For explicit conversion: `value.to_python_object()`.

### Building Python Collections

```mojo
var py_list = Python.list(1, 2.5, "three")
var py_tuple = Python.tuple(1, 2, 3)
var py_dict = Python.dict(name="value", count=42)

# Mixed types in dict: wrap each value
# WRONG:  Python.dict(flag=my_bool, count=42)
# CORRECT: Python.dict(flag=PythonObject(my_bool), count=PythonObject(42))

# Literal syntax
var list_obj: PythonObject = [1, 2, 3]
var dict_obj: PythonObject = {"key": "value"}
```

### PythonObject Operations

`PythonObject` supports attribute access, indexing, slicing, arithmetic, comparison,
`len()`, `in`, and iteration — all returning `PythonObject`.

```mojo
for item in py_list:
    print(item)               # item is PythonObject

var result = obj.method(arg1, arg2, key=value)
var none_obj = Python.none()
var obj: PythonObject = None  # implicit conversion
```

### Evaluating Python Code

```mojo
var result = Python.evaluate("1 + 2")
var mod = Python.evaluate("def greet(n): return f'Hello {n}'", file=True)
var greeting = mod.greet("world")

Python.add_to_path("./my_modules")
var my_mod = Python.import_module("my_module")
```

### Exception Handling

Python exceptions propagate as Mojo `Error`. Functions calling Python must be `raises`:

```mojo
def use_python() raises:
    try:
        var result = Python.import_module("nonexistent")
    except e:
        print(String(e))
```

### Building Python Extension Modules

Export Mojo functions to Python via `PythonModuleBuilder`:

```mojo
from std.os import abort
from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder

@export
def PyInit_my_module() -> PythonObject:
    try:
        var m = PythonModuleBuilder("my_module")
        m.def_function[add]("add")
        return m.finalize()
    except e:
        abort(String("failed to create module: ", e))

def add(a: PythonObject, b: PythonObject) raises -> PythonObject:
    return a + b
```

### Exporting Types with Methods

```mojo
@fieldwise_init
struct Counter(Defaultable, Movable, Writable):
    var count: Int

    def __init__(out self):
        self.count = 0

    @staticmethod
    def py_init(out self: Counter, args: PythonObject, kwargs: PythonObject) raises:
        if len(args) == 1:
            self = Self(Int(py=args[0]))
        else:
            self = Self()

    # Methods are @staticmethod — two patterns:
    # 1. Manual downcast: py_self: PythonObject
    @staticmethod
    def increment(py_self: PythonObject) raises -> PythonObject:
        var self_ptr = py_self.downcast_value_ptr[Self]()
        self_ptr[].count += 1
        return PythonObject(self_ptr[].count)

    # 2. Auto downcast: self_ptr: UnsafePointer[Self, MutAnyOrigin]
    @staticmethod
    def get_count(self_ptr: UnsafePointer[Self, MutAnyOrigin]) -> PythonObject:
        return PythonObject(self_ptr[].count)
```

Register with:
```mojo
m.add_type[Counter]("Counter")
    .def_py_init[Counter.py_init]()
    .def_method[Counter.increment]("increment")
    .def_method[Counter.get_count]("get_count")
```

### Importing Mojo from Python

```python
import mojo.importer       # enables Mojo imports, auto-compiles .mojo files
import my_module           # auto-compiles my_module.mojo

print(my_module.add(1, 2))
```

The `.mojo` file must not contain a `main()` function when built as a shared library.

### Returning Mojo Values to Python

```mojo
return PythonObject(alloc=my_mojo_value^)    # transfer ownership with ^
var ptr = py_obj.downcast_value_ptr[MyType]() # recover later
ptr[].field                                    # access fields
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| (none — sourced from upstream) | Sourced from Modular's official skills repo | N/A — authoritative reference | Verify `py=` keyword usage — positional conversion is the #1 mistake |

## Results & Parameters

### Method Signature Patterns

| Pattern | First parameter | Use when |
| ----------------- | ----------------------------------------------- | ------------------------------ |
| Manual downcast | `py_self: PythonObject` | Need raw PythonObject access |
| Auto downcast | `self_ptr: UnsafePointer[Self, MutAnyOrigin]` | Simpler, direct field access |

### Common Patterns

```mojo
# Environment variables — use Mojo native, not Python os
from std.os import getenv
var val = getenv("MY_VAR")  # returns Optional[String]

# Sorting with custom key (no lambda in Mojo)
var key_fn = Python.evaluate("lambda x: x['" + field + "']")
var sorted_data = builtins.sorted(data, key=key_fn)
```

## Related Skills

- [mojo-python-interop-placeholder-replacement](./mojo-python-interop-placeholder-replacement.md) — Placeholder migration patterns
- [mojo-python-interop-to-stdlib](./mojo-python-interop-to-stdlib.md) — Migrating Python calls to Mojo stdlib
- [mojo-026-breaking-changes](./mojo-026-breaking-changes.md) — Current Mojo syntax reference

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (upstream) | Modular official skills repo | Authoritative reference for Mojo-Python interop |

---
*Adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0.
Copyright (c) Modular Inc.*
