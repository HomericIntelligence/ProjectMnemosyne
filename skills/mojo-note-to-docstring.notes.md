# Session Notes: mojo-note-to-docstring

## Session Details

- **Date**: 2026-03-05
- **Issue**: #3072 (ProjectOdyssey) — [Cleanup] Convert implementation constraint NOTEs to docstrings
- **PR**: #3287
- **Branch**: 3072-auto-impl

## Raw Grep Output

Initial discovery found 25 `# NOTE:` occurrences in 19 files. After filtering to
implementation constraints in non-test production code, 12 were targeted for conversion.

Files with NOTEs NOT converted (out of scope):
- tests/models/test_alexnet_layers.mojo — test skip explanations (Float16 precision)
- tests/shared/core/test_conv.mojo — backward test disabled explanation
- tests/shared/training/test_training_loop.mojo — generic constraint note
- tests/shared/utils/test_logging.mojo — unimplemented feature note
- examples/lenet-emnist/run_infer.mojo — external library limitation
- examples/googlenet-cifar10/train.mojo — scope limitation note
- shared/__init__.mojo:52 — pending implementation note (left as-is)
- shared/__init__.mojo:127 — Mojo language limitation note (left as-is)
- scripts/verify_installation.mojo — pending implementation
- benchmarks/scripts/compare_results.mojo — intentional hardcoded paths

## Key Decision Points

1. **What counts as "implementation constraint"?**
   A NOTE that a caller/user of the API should be aware of, describing a design decision
   or platform limitation that affects behavior. NOT test-specific skip reasons.

2. **When to add to docstring vs. remove?**
   - Add to docstring when: it describes behavior callers depend on
   - Remove when: the docstring already says the same thing
   - Rephrase when: it's module-level (no docstring context available)

3. **Large block comments (like FP16 SIMD in mixed_precision.mojo)**
   The original was 22 lines explaining the limitation in extreme detail.
   Decision: summarize the essential constraint (what's blocked, impact, path forward)
   in 4 lines in the docstring. Condense inline to 1-liner cross-reference.

## Timing

- Discovery + categorization: ~5 minutes
- Edits across 10 files: ~10 minutes
- Pre-commit verification: passed on first run
- Total session: ~20 minutes