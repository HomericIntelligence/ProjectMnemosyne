# Session Notes: mojo-bounds-test-pattern

Date: 2026-03-07
Issue: HomericIntelligence/ProjectOdyssey#3387
PR: HomericIntelligence/ProjectOdyssey#4065

## Raw Session Notes

The __setitem__ implementation in shared/core/extensor.mojo checks:

```text
if index < 0 or index >= self._numel:
    raise Error("Index out of bounds")
```

The existing test only covered `index >= numel` (t[5] = 1.0 on a size-3 tensor).
Added test for `index < 0` (t[-1] = 1.0).

Pattern in test_utility.mojo uses a `raised` flag with try/except:

```mojo
var raised = False
try:
    t[-1] = 1.0
except:
    raised = True
if not raised:
    raise Error("...")
```

GLIBC issue: The dev machine runs Debian 10 (Buster) with GLIBC 2.28.
Mojo requires GLIBC 2.32+. All Mojo test execution happens in Docker containers.
