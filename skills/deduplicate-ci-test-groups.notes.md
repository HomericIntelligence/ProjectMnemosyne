# Session Notes — deduplicate-ci-test-groups

**Date**: 2026-03-08
**Issue**: #3640 — fix(ci): deduplicate CI test groups — Data/Shared Infra wildcard overlap
**PR**: #4453

## Problem

Three CI test groups had overlapping wildcard patterns:

1. "Data" group used `test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo` — this matched ALL files already covered by dedicated sub-groups
2. "Shared Infra & Testing" included `training/test_*.mojo` — but ALL training tests are in the exclusion list in `validate_test_coverage.py`
3. "Misc Tests" and "Shared Infra" both matched training tests

## Files Changed

- `.github/workflows/comprehensive-tests.yml` — Data group and Shared Infra group patterns
- `scripts/validate_test_coverage.py` — added 9 new training files to exclusion list

## Verification Commands

```bash
# Check no uncovered files
python scripts/validate_test_coverage.py

# Check no duplicates
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from validate_test_coverage import parse_ci_matrix, expand_pattern
from pathlib import Path
from collections import defaultdict
root = Path('.')
groups = parse_ci_matrix(root / '.github/workflows/comprehensive-tests.yml')
file_to_groups = defaultdict(list)
for name, info in groups.items():
    for f in expand_pattern(info['path'], info['pattern'], root):
        file_to_groups[f].append(name)
dupes = {f: gs for f, gs in file_to_groups.items() if len(gs) > 1}
print(f'Duplicates: {len(dupes)}')
"
```

## Result

- 0 uncovered files
- 0 files in more than one CI group
- All pre-commit hooks passed