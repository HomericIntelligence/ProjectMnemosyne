---
target_skill: training-hyperparam-lr-scale-depth-transfer
date: 2026-07-22
---

# Project-specific evidence: LR-Scale Transfer Failure

## Project
- predictive-coding-mojo (8-layer CNN/Variant-C, CIFAR-10).

## PR cycle
- PR #107 (`pc-scaling-investigation`). The 68-cell full-epoch bake-off was
  stopped at the first diverged cell (`bp_adan` @ `lr_scale` 1.0 collapsed to
  chance top-1 0.10, train CE 2.398 ~ ln(10)). A 204-cell 5-batch LR screen
  replaced the planned 73-min/epoch grid.

## Numbers
- Source-geometry sweep: 2-layer MLP, found `momentum` optimum at `lr_scale`
  = 0.25; `adan` optimum at `lr_scale` = 1.0; etc.
- Screen: 6 LR-scales x 17 optimizers x 2 rules = 204 cells.
- Screen ladder: `[1.0, 0.25, 0.063, 0.016, 0.004, 0.001]`.
- Screen wall time on hermes (2-concurrent, 8-core CPU): reported by the
  `experiments/sweep_matrix_runnable/` dispatcher; per-cell cost was sub-minute.
- Equivalent full-epoch grid estimate at 73 min/cell / 2-concurrent:
  bounded by the cell count, not by the screen. Result: most cells would have
  diverged at `lr_scale` = 1.0; the few winners would have been hard to
  distinguish without the screen.

## Tool / harness
- `scripts/gen_alexnet_lr_screen_specs.py` emits the 204-cell spec list.
- `scripts/collect_alexnet_lr_screen.py` picks per-`(rule, optimizer)`
  winners and emits the full-epoch spec.
- `scripts/optimizers.py` (24-name SSoT, `pythonpath = scripts`) is the
  dispatch-key inventory.

## Failure-of-failure mode
The screen itself can be tricked by pathologically short horizons
(`--max-batches 1`) that introduce noise into the CE signal. Always
sanity-check one screen cell end-to-end (full epoch) before committing
to the screen's choices for the rest.
