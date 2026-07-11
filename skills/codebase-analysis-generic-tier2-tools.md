---
name: codebase-analysis-generic-tier2-tools
description: "Use when: (1) analyzing code structure, module hierarchy, or dependency\
  \ graphs for orientation or documentation; (2) extracting algorithms, equations,\
  \ or hyperparameters from research papers for implementation planning; (3) measuring\
  \ function performance via benchmarking or profiling to identify bottlenecks; (4)\
  \ checking test coverage, detecting code smells, or linting for quality assurance;\
  \ (5) validating function inputs for correctness and suggesting optimization strategies."
category: evaluation
date: '2026-05-19'
version: 1.0.0
user-invocable: false
history: codebase-analysis-generic-tier2-tools.history
tags:
  - code-analysis
  - benchmarking
  - profiling
  - coverage
  - linting
  - dependencies
  - architecture
  - paper-extraction
  - optimization
  - input-validation
---

# Codebase Analysis Generic Tier-2 Tools

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-05-19 |
| Objective | Consolidated Tier-2 sub-skills for code structure analysis, paper content extraction, performance measurement, and quality assessment across any Mojo or Python project. |
| Outcome | Operational |

Generic reusable analysis utilities covering the full analysis lifecycle: orient in a
new codebase, extract knowledge from research papers, measure and improve performance,
and validate quality before shipping.

## When to Use

1. **Code structure & dependencies** — initial orientation, mapping module hierarchy,
   identifying circular imports, planning refactoring.
2. **Paper extraction** — converting equations, algorithms, hyperparameters, or ML
   architectures from research PDFs into implementation-ready documentation.
3. **Performance** — benchmarking function speed with `timeit`/Mojo timing, profiling
   CPU/memory hotspots with `cProfile`/`memory_profiler`, then recommending targeted
   optimizations.
4. **Quality gates** — measuring test coverage with `pytest-cov`, detecting code smells
   via `pylint`/`radon`, running linters before commits.
5. **Defensive programming** — validating function inputs (types, shapes, ranges) to
   catch bad data early.
6. **Environment validation** — verifying all required packages are installed and
   version-compatible before starting experiments.

### Quick Reference

```bash
# --- Structure & dependencies ---
find . -name "*.py" -o -name "*.mojo" | head -20
tree -L 2 --dirsfirst
grep -r "^class\|^def\|^fn\|^struct" --include="*.py" --include="*.mojo" | head -30
grep -r "^import\|^from" --include="*.py" . | sort | uniq
pipdeptree                     # dependency graph

# --- Paper extraction ---
pdftotext -layout paper.pdf - | grep -E '\$\$|\\begin\{equation\}' | head -20
pdftotext paper.pdf - | grep -A 20 -i "algorithm\|pseudocode" | head -50
pdftotext paper.pdf - | grep -i "learning rate\|batch\|epochs\|weight decay" | head -20

# --- Performance ---
python3 -m timeit -s 'import module' 'module.function(args)' -n 1000 -r 5
mojo run benchmark_script.mojo
python3 -m cProfile -s cumulative script.py | head -30
python3 -m memory_profiler script.py

# --- Quality gates ---
pytest --cov=<module> --cov-report=html tests/ && coverage report --fail-under=80
pylint --disable=all --enable=convention,refactor module.py
radon cc -a module.py          # cyclomatic complexity
radon mi -s module.py          # maintainability index
flake8 . && black --check .
pixi run mojo format file.mojo

# --- Environment ---
pip check && pip show <package>
pixi info && pixi task list

# --- Input validation (Python) ---
# assert isinstance(x, ExpectedType), "..."
# assert x.shape == expected_shape, "..."
```

## Verified Workflow

### A — Code Structure Analysis

1. Survey top-level modules with `find`/`tree`.
2. List key components: `grep` for classes, structs, `fn`/`def` signatures.
3. Trace imports and detect circular dependencies with `pipdeptree` or manual `grep`.
4. Document hierarchy and notable patterns (MVC, singleton, factory).

### B — Paper Extraction (Equations / Algorithms / Hyperparameters / Architecture)

1. **Equations**: Extract LaTeX notation via `pdftotext`; break into primitive ops;
   map to Mojo/Python operations; specify dtypes (float32, float64).
2. **Algorithms**: Locate pseudocode sections; enumerate inputs/outputs; document
   complexity; translate to implementation checklist.
3. **Hyperparameters**: Find "Table 1" / "Hyperparameters" section; document LR,
   batch size, epochs, optimizer, dropout, weight decay; write YAML/JSON config.
4. **Architecture**: Locate architecture diagram; enumerate layers with type, size,
   activation, normalization; map skip-connections/attention; plan Mojo structs.

### C — Performance Measurement

1. **Benchmark**: Set up warm-up iterations; record mean/median/std across ≥5 runs;
   compare to baseline; report improvement percentage.
2. **Profile**: Select profiler (`cProfile` for CPU, `memory_profiler` for RAM); run
   instrumented; identify top-10 functions by cumulative time; analyze call graph.
3. **Suggest optimizations**: From profile data: check algorithmic complexity, data
   structure choice, caching opportunities, SIMD/vectorization potential; estimate
   impact and implementation difficulty.

### D — Quality Assurance

1. **Coverage**: Run `pytest --cov`; generate HTML report; identify uncovered lines
   and branches; meet ≥80 % threshold.
2. **Code smells**: Run `pylint`/`radon`; classify by severity; map to SOLID
   principle violations; prioritize refactoring by impact.
3. **Lint**: Run `pylint`/`flake8`/`black`/`pixi run mojo format`; fix in severity
   order; re-run to confirm clean.

### E — Input Validation

1. Document expected types, shapes, and ranges per parameter.
2. Add assertions with clear error messages before processing.
3. Raise `ValueError` on assertion failure with context.
4. Write test cases for invalid inputs (None, wrong dtype, wrong shape).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| No warm-up in benchmarks | Ran `timeit` with `number=1` | First-call JIT overhead skewed results | Always warm up with ≥100 iterations; use `-r 5` for repeats |
| `cProfile` alone for memory issues | Used CPU profiler to debug OOM | cProfile doesn't track allocations | Pair `cProfile` (CPU) with `memory_profiler` (RAM) |
| Single-pass linting | Ran only `flake8`, skipped `pylint` | Missed complexity and convention issues | Run both; `radon` for complexity; `black --check` for format |
| Searching paper for equations without `pdftotext` | Relying on OCR screenshots | Noisy output, missed LaTeX structure | Use `pdftotext -layout` for structured text extraction |
| Coverage report without branch coverage | Used `--cov` without `--cov-branch` | Missed uncovered conditional branches | Add `--cov-branch` for complete coverage picture |

## Results & Parameters

### Coverage thresholds

| Metric | Recommended minimum |
| -------- | ------------------- |
| Line coverage | 80 % |
| Branch coverage | 70 % |

### Benchmarking parameters

| Parameter | Recommended value |
| ----------- | ----------------- |
| `timeit` iterations (`-n`) | 1000 |
| `timeit` repeats (`-r`) | 5 |
| Warm-up runs | 10–100 (discard) |

### Cyclomatic complexity thresholds (radon)

| Grade | CC score | Action |
| ------- | -------- | ------ |
| A | 1–5 | OK |
| B | 6–10 | Monitor |
| C+ | 11+ | Refactor |

### Input validation pattern

```python
def validate_tensor(tensor, expected_dtype=DType.float32):
    assert tensor is not None, "Tensor cannot be None"
    assert isinstance(tensor, ExTensor), "Must be ExTensor type"
    assert len(tensor.shape) > 0, "Tensor shape cannot be empty"
    assert tensor.dtype() == expected_dtype, f"Expected {expected_dtype}, got {tensor.dtype()}"
    return True
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Mnemosyne | Epic #1828 M23 cluster (14 Tier-2 sub-skills) | Absorbed from batch-generated 2026-03-19 release |
