# Session Notes: Mojo Runtime Crash Bisection

## Date: 2026-03-16

## Context

Working on ProjectOdyssey, an ML research platform in Mojo. VGG16 E2E tests
were crashing deterministically. The goal was to create minimal reproducers
for upstream bug reports against modular/modular.

## Investigation Timeline

1. **Initial hypothesis**: Two separate crashes (libKGEN vs libAsyncRT)
2. **Reality**: One crash with both libraries in the same call chain
3. **Reduction from VGG16** (359 lines, 10+ imports) to self-contained reproducer (223 lines, 2 imports)
4. **Root cause isolation**: `List[Int]` field in struct + heavy alloc/free + bitcast write

## Key Discovery: The List[Int] Factor

The most surprising finding was that removing the `List[Int] _shape` field from
the Tensor struct (replacing with fixed `Int` fields) completely eliminated the
crash, even with the same conv2d computation pattern. This means the crash is
caused by how the Mojo runtime handles `List[Int]` internal buffer
allocation/deallocation interleaved with raw `alloc[UInt8]` calls.

## Verification Steps Performed

- Bounds-checked conv2d: all indices in-bounds, still crashes
- Probe struct for move semantics: confirmed `deinit existing` suppresses `__del__`
- Refcount tracing: all transitions balanced
- Move vs copy in `__moveinit__`: both crash identically
- Function scope vs inline: only function-scoped calls crash

## Environment

- Mojo 0.26.1.0 (156d3ac6)
- Linux 6.6.87.2-microsoft-standard-WSL2 x86_64
- GLIBC 2.39
- Ubuntu 24.04

## Upstream Issue

Filed as modular/modular#6187
