---
name: regex-value-strip-before-finite-check
description: "A validity/sentinel check that runs AFTER a numeric-extraction step is dead code — the extraction strips the sentinel characters (nan/inf) before the check ever sees them, so a broken run passes green. Use when: (1) writing a validity/sentinel check right after a value-extraction step, (2) a nan/inf or bounds check that never fires, (3) reviewing your own CI assertion/gate code, (4) a smoke gate that passes on obviously-broken output."
category: debugging
date: 2026-07-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [regex, grep, ci, smoke-gate, sentinel, nan-inf, bash, dead-code, adversarial-review]
---

# Regex Value-Strip Before Finite-Check — Dead-Code Sentinel Bug

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-11 |
| **Objective** | Make a CI smoke gate actually reject a diverged training run (`Loss: -inf`) instead of passing it green |
| **Outcome** | Latent dead-code check found and fixed; the non-finite check now runs against the RAW matched lines, prefix-anchored. CI validation pending (verified in-container end-to-end + unit-tested parse logic against 7 cases, not yet confirmed green in remote CI) |
| **Verification** | verified-local |

## When to Use

- Writing a validity/sentinel check (nan/inf, bounds, "must be non-empty") **right after** a value-extraction step that filters the string
- Debugging a "my nan/inf check never fires" symptom — a gate that passes on obviously-broken output
- Reviewing your OWN CI assertion / gate / smoke-test code (adversarial self-review of assertions)
- A "smoke gate" bash recipe that greps a value out of program output, then re-greps the extracted value for a bad marker

> **Different from `toml-section-bounded-regex-dotall-bug`:** that skill is about `re.DOTALL` matching *across* TOML `[section]` boundaries (over-matching). THIS skill is about an extraction step *stripping the sentinel characters* out of the string before a downstream check tests for them (the check silently never fires). If you are debugging "my nan/inf check never fires," this is the skill.

## Verified Workflow

### Quick Reference

```bash
# BAD — DEAD CODE. Extraction char class [-0-9.eE] contains no n/a/i/f,
# so "Loss: -inf" is stripped to "-" BEFORE the finite-check runs.
# The check below can NEVER match "nan"/"inf" → diverged run passes GREEN.
losses=$(echo "$out" | grep -oiE "Loss:[[:space:]]*[-0-9.eE]+" | grep -oE "[-0-9.eE]+$")
if echo "$losses" | grep -qiE "nan|inf"; then      # never fires
    echo "FAILED: non-finite loss"; exit 1
fi

# GOOD — check the sentinel against the RAW matched lines FIRST,
# prefix-anchored on "Loss:" so an unrelated "nan"/"inf" can't false-positive.
loss_lines=$(echo "$out" | grep -iE "Loss:[[:space:]]*[-+]?(nan|inf|[0-9.])")
if echo "$loss_lines" | grep -qiE "Loss:[[:space:]]*[-+]?(nan|inf)([^a-z0-9]|$)"; then
    echo "FAILED: non-finite loss value"; exit 1
fi
# only NOW extract numerics for the >=2-finite-lines count
losses=$(echo "$loss_lines" | grep -oiE "Loss:[[:space:]]*[-+]?[0-9.eE]+" | grep -oE "[-+]?[0-9.eE]+$")
```

### Detailed Steps

1. **Find the pattern.** Look for any pipeline of the shape `extract_value | check_value_for_sentinel`, where the extraction step is a regex/character-class filter and the sentinel is characters (nan/inf, letters, symbols) that the extraction class does NOT include.
2. **Prove it is dead code.** Feed the broken input (e.g. `Loss: -inf`) through ONLY the extraction step and inspect the output. If the sentinel characters are gone (stripped to `""` or a bare `-`), the downstream check can never match — it is dead code.
3. **Move the sentinel check upstream.** Run the sentinel check against the RAW matched lines, BEFORE (or independent of) numeric extraction.
4. **Anchor the sentinel on the prefix.** Match `Loss:[[:space:]]*[-+]?(nan|inf)` (not a bare `nan|inf`) so an unrelated occurrence — e.g. a path like `nanometer-net` or a word `information` — cannot false-reject a healthy run.
5. **Add a word boundary after the sentinel.** `([^a-z0-9]|$)` after `(nan|inf)` prevents matching a longer token that merely starts with `inf` (e.g. `infinity_scheduler`, `information`).
6. **Extract numerics only after the check passes**, from the already-filtered `loss_lines`, for any downstream count (e.g. ADR-014's "≥2 finite loss lines" requirement).
7. **Unit-test the parse logic** against canned cases including at least one broken case and one adversarial false-positive case (sentinel-in-unrelated-line).

### Why the Extraction Strips the Sentinel

The extraction character class `[-0-9.eE]` (and its variants like `[-+]?[0-9.eE]+`) is designed to keep only digits, sign, decimal point, and the `e/E` of scientific notation. It contains **none** of the letters `n`, `a`, `i`, `f`. So `grep -oE "[-0-9.eE]+"` applied to `-inf` yields `-` (or nothing), and applied to `nan` yields the empty string. Any downstream `grep "nan|inf"` on that output is testing a string from which those letters were already deleted.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Check extracted values | `losses=$(... \| grep -oE "[-0-9.eE]+$")` then `echo "$losses" \| grep -qiE "nan\|inf"` | DEAD CODE: the extraction class `[-0-9.eE]` contains no n/a/i/f, so it strips `nan`/`inf` to `""`/`-` **before** the check runs — the check never matches. `Loss: -inf` passed the gate GREEN | Never run a sentinel/validity check against a string that an earlier extraction step already stripped the sentinel characters out of — check the RAW input |
| Bare-sentinel grep on raw lines | `grep -qiE "nan\|inf"` on the raw program output | False-positives: an unrelated line (a path `nanometer-net`, a word `information`) contains `nan`/`inf` and wrongly rejects a healthy run | Anchor the sentinel on the value prefix (`Loss:[[:space:]]*[-+]?(nan\|inf)`), not a bare `nan\|inf` |
| Prefix anchor, no trailing boundary | `grep -qiE "Loss:[[:space:]]*[-+]?(nan\|inf)"` | Could match a longer token starting with the sentinel (e.g. `Loss: information...`) | Add a trailing word boundary `([^a-z0-9]\|$)` after `(nan\|inf)` |
| Trust the green gate | Assumed the gate worked because it passed | The gate passed on a KNOWN-BROKEN (`-inf`) input — passing proved nothing because the assertion never fired | Adversarially review your OWN gate/assertion code; reproduce the bypass empirically with a broken input |

## Results & Parameters

Final smoke-gate recipe (bash), enforcing ADR-014's "catch a broken training MECHANISM" (non-finite loss OR fewer than 2 finite loss lines both fail):

```bash
# $out holds the captured stdout of the training run.

# 1. Grab the RAW loss lines (numeric OR non-finite).
loss_lines=$(echo "$out" | grep -iE "Loss:[[:space:]]*[-+]?(nan|inf|[0-9.])")

# 2. FAIL on any non-finite loss — checked against RAW lines, prefix-anchored,
#    with a trailing boundary so unrelated tokens can't false-positive.
if echo "$loss_lines" | grep -qiE "Loss:[[:space:]]*[-+]?(nan|inf)([^a-z0-9]|$)"; then
    echo "FAILED: non-finite loss value"; exit 1
fi

# 3. Only NOW extract numeric values, and require >= 2 finite loss lines.
losses=$(echo "$loss_lines" | grep -oiE "Loss:[[:space:]]*[-+]?[0-9.eE]+" | grep -oE "[-+]?[0-9.eE]+$")
n=$(echo "$losses" | grep -c .)
if [ "$n" -lt 2 ]; then
    echo "FAILED: fewer than 2 finite loss lines"; exit 1
fi
echo "OK: $n finite loss lines, none non-finite"
```

### Test Matrix (verified-local)

| Case | Input | Expected | Result |
|------|-------|----------|--------|
| Healthy 4-line | `Loss: 0.9 ... Loss: 0.3` (4 lines) | OK | OK |
| Diverged `-inf` | line with `Loss: -inf` + finite lines | REJECTED (non-finite) | REJECTED |
| Bare `nan` | `Loss: nan` | REJECTED (non-finite) | REJECTED |
| Uppercase `INF` | `Loss: INF` | REJECTED (case-insensitive) | REJECTED |
| Single line | one `Loss:` line only | FAILED (<2 finite) | FAILED |
| Sci-notation + negative | `Loss: -1.2e-3`, `Loss: 3.4E2` | OK | OK |
| Sentinel in non-loss line | `nanometer-net loaded` + 2 finite `Loss:` lines | OK (no false-reject) | OK |

Also re-verified the real recipe end-to-end in-container (exit 0 on the healthy run). **CI validation pending** — not yet confirmed green in remote CI.

### How It Was Caught

A strict default-F review swarm (parallel sub-agent reviewers, one focused on correctness) empirically **reproduced** the bypass: it fed `Loss: -inf` through the extraction step, observed the sentinel was already stripped, and demonstrated the gate passed green on a diverged run. The lesson: adversarial review of your own gate/assertion code catches assertions that silently never fire — a green gate is not evidence the assertion works unless you have seen it reject a known-bad input.
