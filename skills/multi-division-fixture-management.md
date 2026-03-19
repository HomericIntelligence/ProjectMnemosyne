---
name: multi-division-fixture-management
description: 'TRIGGER CONDITIONS: Use when adding a second division''s fixture set
  to a flat tests/fixtures/ directory, or when capture-fixtures CLI needs named subdirs,
  or when integration tests need to auto-discover all fixture sets.'
category: testing
date: 2026-03-01
version: 1.0.0
user-invocable: false
---
# multi-division-fixture-management

How to migrate flat API fixture directories to per-division slugged subdirs, extend the capture CLI to auto-name them, and parameterize pytest integration tests to cover all sets automatically.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-01 |
| Objective | Add a second AES division fixture set without breaking existing integration tests, then make the system auto-scale to N divisions |
| Outcome | Success — 189 tests pass (175 unit + 14 integration = 7 per division × 2 divisions) |

## When to Use

- You have a flat `tests/fixtures/*.json` layout and need to add a second fixture set
- Your `capture_fixtures` CLI writes to a hardcoded output directory (no per-division naming)
- Integration tests reference a single `FIXTURES_DIR` constant and need to scale to N divisions
- You want `pixi run capture-fixtures <URL>` to auto-name subdirs from the division name, zero config

## Verified Workflow

### Step 1 — Move existing flat fixtures into a named subdir

Determine the division name from the existing `event.json`:

```python
import json
d = json.load(open("tests/fixtures/event.json"))
# Find division name from plays.json: d["Division"]["Name"]
```

```bash
mkdir tests/fixtures/<slug>/
mv tests/fixtures/*.json tests/fixtures/<slug>/
```

### Step 2 — Update `capture_fixtures` CLI to auto-resolve slug subdir

Before opening the API client, fetch the event to resolve the division name, then write to `output_dir / slug`:

```python
async def capture_fixtures(url: str, output_dir: Path):
    parts = parse_aes_url(url)

    async with AESClient() as client:
        # Resolve division name first so we can name the subdirectory
        event = await client.get_event(parts.event_key)
        division_name = next(
            (d["Name"] for d in event.get("Divisions", [])
             if d["DivisionId"] == parts.division_id),
            "unknown",
        )
        slug = _slugify(division_name)
        output_dir = output_dir / slug
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Capturing fixtures for '{division_name}' → {output_dir}/")

        _save(output_dir / "event.json", event)
        # ... rest of capture unchanged, all paths use output_dir
```

Key: save `event.json` here (already fetched) — don't fetch again.

### Step 3 — Rewrite integration test to auto-discover fixture subdirs

Replace the single `FIXTURES_DIR` constant with a `_fixture_dirs()` discovery function, then parametrize all test classes:

```python
FIXTURES_ROOT = Path(__file__).parent / "fixtures"

def _fixture_dirs() -> list[Path]:
    """Return all subdirs of fixtures/ that contain plays.json."""
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(d for d in FIXTURES_ROOT.iterdir()
                  if d.is_dir() and (d / "plays.json").exists())

_ALL_FIXTURE_DIRS = _fixture_dirs()
_FIXTURE_IDS = [d.name for d in _ALL_FIXTURE_DIRS]

skip_no_fixtures = pytest.mark.skipif(
    len(_ALL_FIXTURE_DIRS) == 0,
    reason="No fixture directories found. Run: pixi run capture-fixtures <URL>",
)

@skip_no_fixtures
@pytest.mark.parametrize("fixture_dir", _ALL_FIXTURE_DIRS, ids=_FIXTURE_IDS)
class TestEndToEndWithFixtures:
    def test_full_pipeline_produces_valid_json(self, fixture_dir, tmp_path):
        plays = _load(fixture_dir, "plays.json")
        # ... use fixture_dir / filename everywhere instead of FIXTURES_DIR / filename
```

For test classes that only apply when certain files exist (e.g. poolsheets, brackets), filter at parametrize time:

```python
@pytest.mark.parametrize(
    "fixture_dir",
    [d for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
    ids=[d.name for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
)
class TestPoolParserWithFixtures:
    ...
```

### Step 4 — Capture the new division and verify

```bash
pixi run capture-fixtures <NEW_URL>
pixi run test-all
```

Adding a new division now automatically adds 7 more integration tests with zero code changes.

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Dumping new fixtures into the same flat `tests/fixtures/` | `poolsheet_*.json` globs would mix IDs from different divisions; `plays.json` would be overwritten | Always namespace by slug from the start |
| Fetching `event.json` twice in `capture_fixtures` (once for slug, once as step 1) | Wasted API call; left a duplicate `_save(output_dir / "event.json", event)` dangling in code | Reuse the already-fetched event; save it immediately after slug resolution |
| Keeping `FIXTURES_DIR` as a module-level constant and using `skipif` on `_has_fixture("plays.json")` | Doesn't generalize — only tests one hardcoded dir; adding a second set requires manual code changes | Use `_fixture_dirs()` discovery + `@pytest.mark.parametrize` — zero-config scaling |

## Results & Parameters

**Test count scaling:**
- 1 division → 7 integration tests
- 2 divisions → 14 integration tests
- N divisions → 7N integration tests (automatic)

**Slug function used:**
```python
def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s or 'unknown'
# "18s - 15s Power League" → "18s-15s-power-league"
# "14s Girls"              → "14s-girls"
```

**Directory layout after migration:**
```
tests/fixtures/
├── .gitkeep
├── 14s-girls/
│   ├── event.json
│   ├── plays.json
│   ├── playdays.json
│   ├── brackets_YYYY-MM-DD.json
│   ├── pools_YYYY-MM-DD.json
│   └── poolsheet_{playId}.json  (N files)
└── 18s-15s-power-league/
    ├── plays.json
    ├── playdays.json
    └── ...
```

Note: `event.json` is optional in subdirs — some divisions' events may be shared. The integration tests only require `plays.json` to detect a valid fixture dir.

**pixi task (unchanged, works automatically):**
```toml
[tool.pixi.tasks]
capture-fixtures = { cmd = "python -m scraper.cli --capture-fixtures" }
test-all = "pytest tests/"
```

## Verified On

- TitanSchedule project (AES volleyball tournament scraper)
- Python 3.14, pytest 9.0.2, pixi environment
- Two fixture sets: `14s-girls` (50 poolsheets) and `18s-15s-power-league` (80 poolsheets, 4 bracket dates)
