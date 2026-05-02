# Session Notes: getting-started-doc-audit

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #3914 — "Add quick-start guide for getting-started/ section"
- **Follow-up from**: #3304 (installation.md)
- **Branch**: `3914-auto-impl`
- **PR**: HomericIntelligence/ProjectOdyssey#4828

## Objective

Audit `docs/getting-started/` for stub/placeholder files after `installation.md` was written.
Rewrite any files with placeholder text, sourcing commands from `justfile` and versions from
`pixi.toml`.

## Files Audited

| File | Status | Action |
| ------ | -------- | -------- |
| `quickstart.md` | Accurate | No changes |
| `installation.md` | Accurate (written in #3304) | No changes |
| `first_model.md` | Fabricated APIs throughout | Full rewrite |
| `repository-structure.md` | Broken code blocks + non-existent scripts | Fix code blocks + commands |

## Fabricated APIs Found in first_model.md

All of these were shown as imports/usage but do NOT exist in `shared/`:

- `shared.data.TensorDataset`
- `shared.data.BatchLoader`
- `shared.utils.download_mnist`
- `shared.utils.normalize_images`
- `shared.utils.load_model`
- `shared.utils.load_image`
- `shared.utils.plot_image`
- `shared.utils.plot_confusion_matrix`
- `shared.training.evaluate_model`
- `shared.training.Adam` (class)
- `shared.training.Trainer` (class)
- `shared.training.schedulers.StepLR`
- `shared.data.transforms.RandomRotation`
- `shared.data.transforms.RandomShift`
- `Sequential`, `Layer`, `ReLU`, `Softmax`, `EarlyStopping`, `ModelCheckpoint`

Also: malformed fenced code blocks with duplicate/nested delimiters:
```
```bash
```bash
...
```text
```

## Broken Commands Found in repository-structure.md

| Fabricated Command | Real Equivalent |
|--------------------|-----------------|
| `python scripts/validate_links.py docs/` | `just pre-commit-all` |
| `python scripts/validate_structure.py` | (does not exist) |
| `python tools/paper-scaffold/scaffold.py --paper {name}` | `cp -r papers/_template papers/{name}` |
| `mojo benchmarks/scripts/run_benchmarks.mojo` | `pixi run mojo shared/benchmarking/run_benchmarks.mojo` |
| `mojo test tests/` | `just test-mojo` |
| `python scripts/setup.py` | (does not exist) |
| `python scripts/check_readmes.py` | (does not exist) |
| `mojo papers/lenet5/train.mojo --config ...` | `just train lenet-emnist fp32 10` |

## Markdown Lint Errors Encountered

### MD001 heading-increment (repository-structure.md lines 169, 185, 199)

**Cause**: `#####` items 2, 3, 4 in "Supporting Directories" section. Item 1 (`##### 1. docs/`)
contained `### Key Sections` and `### Common Tasks` inner headings. Markdownlint tracks the
running heading level; after seeing `###`, the next `#####` jumps 2 levels.

**Fix**: Demoted items 2, 3, 4 from `#####` to `####`.

## Key Learnings

1. **Grep APIs before keeping them** — fabricated APIs look plausible but break user trust when
   they try to run the code
2. **Justfile is authoritative for commands** — `just --list` reveals all real recipes
3. **MD001 can trigger from headings inside a block** — a `###` inside a `#####` block resets
   the lint's "current level" counter; the next `#####` is then flagged as skipping levels
4. **"Conceptual orientation" is valid when APIs don't exist** — better to explain what exists
   and what's planned than to fabricate
