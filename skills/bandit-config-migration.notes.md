# Session Notes: bandit-config-migration

## Issue Context

- **Issue**: HomericIntelligence/ProjectOdyssey#3361
- **Title**: Document bandit skip rationale in a .bandit config file
- **Follow-up from**: Issue #3157 (which added bandit as pre-commit hook with `--skip B310,B202`)
- **PR**: HomericIntelligence/ProjectOdyssey#4017
- **Branch**: `3361-auto-impl`

## Problem Statement

The bandit pre-commit hook entry in `.pre-commit-config.yaml` had:

```yaml
entry: pixi run bandit -ll --skip B310,B202
```

Developers running `bandit -r scripts/` directly got B310 and B202 false positives because the
skips lived only in the pre-commit hook CLI args — invisible when running bandit manually.

## Investigation Results

### pyproject.toml [tool.bandit] — Does NOT work

Bandit 1.9.4 reads suppressions via `configparser` from `.bandit` INI files, not from
`pyproject.toml`. Verified by reading bandit source:

```python
# bandit/core/utils.py
def parse_ini_file(f_loc):
    config = configparser.ConfigParser()
    config.read(f_loc)
    return {k: v for k, v in config.items("bandit")}
```

And `bandit/cli/main.py` `_get_options_from_ini()` walks target dirs looking for `.bandit` files —
it never reads `pyproject.toml`.

### .bandit file format

INI format with `[bandit]` section:

```ini
[bandit]
targets = scripts
recursive = true
skips = B310,B202
```

The `_get_options_from_ini` function maps:
- `skips` → `args.skips`
- `targets` → `args.targets` (comma-split)
- `recursive` → `args.recursive`
- `exclude` → `args.excluded_paths`

### Auto-discovery limitation

Bandit only auto-discovers `.bandit` files by walking each passed target directory. If `.bandit`
is at repo root and target is `scripts/`, it won't be found. Must use `--ini .bandit` explicitly.

### Pixi task args appending

```toml
[tasks]
bandit = "bandit -r scripts/ -c pyproject.toml"
```

Running `pixi run bandit -ll -r scripts/` produces:
```
bandit -r scripts/ -c pyproject.toml -ll -r scripts/
```
This duplicates args and causes bandit to fail with "unrecognized arguments: scripts/".

Solution: Keep pixi task minimal:
```toml
bandit = "bandit --ini .bandit"
```

## Files Changed

- **`.bandit`** (new): INI config with targets, recursive, skips, and inline comments
- **`.pre-commit-config.yaml`**: Changed `--skip B310,B202` → `--ini .bandit`
- **`pixi.toml`**: Added `[tasks] bandit = "bandit --ini .bandit"`
- **`pyproject.toml`**: No change (attempted `[tool.bandit]` then reverted — doesn't work)

## Verification Commands

```bash
# Verify skips applied
bandit --ini .bandit --verbose 2>&1 | grep "cli exclude"
# [main]  INFO  cli exclude tests: B310,B202

# Verify no B310/B202 issues
bandit --ini .bandit 2>&1 | grep -E "B310|B202"
# (no output)

# Verify pre-commit passes
pixi run pre-commit run --all-files bandit
# Bandit Security Scan.....Passed

# Verify pixi task works
pixi run bandit 2>&1 | grep "cli exclude"
# [main]  INFO  cli exclude tests: B310,B202
```