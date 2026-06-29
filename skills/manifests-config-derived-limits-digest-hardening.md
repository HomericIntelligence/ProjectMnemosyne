---
name: manifests-config-derived-limits-digest-hardening
description: "Use when: (1) a manifest-driven serving platform hardcodes model serving sequence lengths that can be derived from checkpoint metadata, (2) adding an optional relative model.config_path that points under model.path, (3) launch templates need placeholders for derived serving limits, (4) local .sqsh/squashfs runtime images carry manifest-owned SHA256 provenance that must be verified before launch."
category: architecture
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [manifest, config-json, serving-limits, squashfs, digest, container, validation, security]
---

# Manifest Config-Derived Limits and Digest Hardening

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-29 |
| **Objective** | Eliminate hardcoded serving sequence lengths in checked-in manifests by deriving missing serving limits from checkpoint `config.json`, while hardening local squashfs/container launch provenance. |
| **Outcome** | Successful pattern: manifests remain source-of-truth for the checkpoint and runtime image, validation derives safe defaults from checkpoint metadata, and local runtime image bytes are verified before launch. |
| **Verification** | verified-ci - original workflow was verified by local targeted tests and hosted CI in a private manifest-driven serving repo; private repo names, paths, branches, PRs, endpoints, model names, and commit SHAs are intentionally omitted. |

## When to Use

- A checked-in serving manifest repeats model window or output-token limits that already exist in checkpoint metadata.
- The platform wants manifests to reference `model.config_path` relative to `model.path`, without allowing arbitrary filesystem reads.
- A serving launch command contains placeholders that should resolve from derived manifest values instead of hand-maintained constants.
- A manifest references a local `.sqsh` or squashfs runtime image and records a digest that should be verified before materialization or container start.
- Tests or docs risk embedding private checkpoint roots, runtime-image locations, endpoint addresses, model identifiers, or real digests.

## Verified Workflow

### Quick Reference

```yaml
# <manifest-repo>/manifests/example.yaml
model:
  path: <checkpoint-root>/example-model
  config_path: config.json

serving:
  # Optional. If omitted, derive from model.path / model.config_path.
  max_context_tokens: 131072
  # Optional. If omitted and config only exposes a context/window key, use the
  # context value as an upper-bound output window, then enforce output <= context.
  max_output_tokens: 131072

runtime:
  image: <container.sqsh>
  digest: sha256:<64-hex>
  launch:
    - --context-length
    - "{serving.max_context_tokens}"
    - --max-output-tokens
    - "{serving.max_output_tokens}"
```

```python
CONTEXT_KEYS = (
    "max_position_embeddings",
    "max_sequence_length",
    "seq_length",
    "model_max_length",
    "n_positions",
)

OUTPUT_KEYS = (
    "max_output_tokens",
    "max_new_tokens",
)
```

```bash
# Shell wrapper preflight for local squashfs images.
case "$EXPECTED_DIGEST" in
  sha256:[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
  *) echo "invalid runtime image digest: $EXPECTED_DIGEST" >&2; exit 1 ;;
esac

actual_digest="sha256:$(sha256sum "$LOCAL_IMAGE" | awk '{print $1}')"
if [ "$actual_digest" != "$EXPECTED_DIGEST" ]; then
  echo "runtime image digest mismatch for $LOCAL_IMAGE" >&2
  exit 1
fi
```

### Detailed Steps

1. Add an optional `model.config_path` field to the manifest schema. Treat it as a path relative to `model.path`, not relative to the repository root or process working directory.
2. Before schema or model construction fills required `serving` fields, load the referenced config file when either serving limit is missing. This preserves manifest validation ergonomics: a real checkpoint config can satisfy missing derived fields, while an absent or invalid config produces a config-path-specific error.
3. Resolve `model.config_path` with strict path safety:
   - reject non-strings, empty strings, absolute paths, `~`, `.`, `..`, empty path segments, and any normalized path that escapes `model.path`;
   - reject `model.path` values outside the configured shared model root before reading configs;
   - report missing files, invalid JSON, non-object JSON, unsupported key sets, non-integer values, and non-positive values as `model.config_path` validation failures rather than generic missing `serving.*` failures.
4. Derive context/window limits from the first supported context key present: `max_position_embeddings`, `max_sequence_length`, `seq_length`, `model_max_length`, or `n_positions`.
5. Derive output limits from output-specific keys with explicit precedence: prefer `max_output_tokens` over `max_new_tokens` when both exist. If no output-specific key exists but a context/window key exists, using the context value as the model-window upper bound can be valid.
6. Always enforce `serving.max_output_tokens <= serving.max_context_tokens`. This keeps the context-only fallback from creating an unsafe output window if one field is explicit and the other is derived.
7. Resolve launch placeholders only after config derivation and full serving-limit validation. Launch strings stay tied to checkpoint metadata, not hardcoded constants.
8. For local `.sqsh` or squashfs runtime images with a manifest-owned digest, verify bytes before launch:
   - in artifact validation, stream the file through SHA256 hashing instead of reading the whole image into memory;
   - in any shell launch wrapper, require `sha256:<64 hex>` and compare `sha256sum` output before materializing or starting the container.
9. Validate shell changes with `bash -n`. Do not run Python linters against shell scripts; they create invalid-syntax noise and obscure the real verification signal.
10. Keep tests and docs redacted. Use temp fixtures, manifest-owned fields, and placeholders such as `<checkpoint-root>` and `<container.sqsh>` instead of private infrastructure paths or real digests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Require output-specific keys in checkpoint configs | Validation demanded `max_output_tokens` or `max_new_tokens` before deriving `serving.max_output_tokens` | Real checkpoint configs may expose only model context/window keys; forcing output-only metadata violates the checkpoint config as source of truth | If only a context/window key exists, using that value as an upper-bound output window can be valid, but enforce `serving.max_output_tokens <= serving.max_context_tokens` |
| Validate after schema-filled required serving fields | Let schema/Pydantic construction fail on missing `serving.max_context_tokens` or `serving.max_output_tokens` before reading `model.config_path` | The user saw a generic missing-field error even though the manifest provided a config path that could derive the value | Read checkpoint config before required serving fields are finalized, and raise config-path-specific errors when derivation fails |
| Allow arbitrary config paths | Treated `model.config_path` like a normal file path | Absolute paths, `~`, `..`, or model paths outside the shared root can read unintended files and make manifests non-reproducible | Make `model.config_path` relative-only under `model.path`, and require `model.path` to stay under the configured shared model root |
| Replace launch constants before derivation | Resolved launch placeholders before the serving fields were derived | Placeholders either remained unresolved or fell back to stale constants | Derive and validate serving fields first, then render launch placeholders |
| Trust manifest-recorded local image digest without reading bytes | Stored `sha256:<digest>` in the manifest but did not verify the local `.sqsh` bytes before launch | The manifest looked reproducible while the actual local runtime image could drift | Stream SHA256 verification in artifact validation and repeat a cheap shell preflight before materialization or container start |
| Run Python linters on shell scripts | Included shell launch wrappers in a Python lint command | The linter reported Python invalid-syntax noise instead of shell correctness | Validate shell with `bash -n` and shell-focused checks; keep Python linters scoped to Python files |
| Publish repo-specific skill content | Included private repo names, paths, model names, branch names, PR numbers, or exact commit SHAs in reusable learning text | Durable skill content can be blocked for data exposure and becomes less reusable | Keep the skill generic and redacted; use placeholders only when shape matters |

## Results & Parameters

### Derivation Contract

| Field | Rule |
|-------|------|
| `model.config_path` | Optional string; relative-only under `model.path`; no absolute paths, `~`, `.`, `..`, empty segments, or escape after normalization |
| `model.path` | Must resolve under the configured shared model root before config reads |
| Context keys | `max_position_embeddings`, `max_sequence_length`, `seq_length`, `model_max_length`, `n_positions` |
| Output keys | `max_output_tokens` wins over `max_new_tokens` |
| Context-only fallback | May set output limit to the context/window value when no output-specific key exists |
| Safety invariant | `serving.max_output_tokens <= serving.max_context_tokens` |
| Error shape | Missing, invalid, unsupported, non-object, non-int, or non-positive config values should mention `model.config_path` |

### Test Matrix

Cover these cases before calling the manifest behavior complete:

- all supported context/window keys;
- output-key precedence when both output keys exist;
- partial derivation when one serving limit is explicit and the other is missing;
- invalid `model.config_path` values: absolute path, `~`, `.`, `..`, empty path segment, path escape, missing file, and non-string;
- `model.path` outside the configured shared model root;
- invalid JSON, non-object JSON, non-positive values, non-int values, and missing supported keys;
- real-manifest fixture mapping using redacted local fixtures;
- placeholder replacement after derivation;
- `serving.max_output_tokens > serving.max_context_tokens` rejection;
- streaming digest verification for local squashfs images;
- shell-wrapper digest format checks, digest mismatch behavior, and `bash -n` syntax validation.

### Redaction Hygiene

| Artifact | Guidance |
|----------|----------|
| Tests | Prefer temp directories and generated `config.json` fixtures over private checkpoint roots |
| Manifests | Let manifest-owned fields be the source of truth; do not duplicate private runtime paths in tests |
| Digests | Use placeholders or throwaway fixture digests; avoid real private artifact digests |
| Docs | Point to the manifest fields that own the values; do not embed private endpoints, branch names, PR numbers, model names, or exact commit SHAs |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Private manifest-driven serving repo | Generic workflow capture | verified-ci: local targeted tests and hosted CI passed for config-derived serving limits, launch placeholder resolution, output-window rejection, and local squashfs digest hardening. Private repo names, infrastructure paths, endpoints, model identifiers, branches, PRs, and commit SHAs are intentionally omitted. |
