# Addition Task - Complete Reference Implementation

Complete working example from Sionic AI blog with verified configs and results.

## Project Structure

```
addition-task/
├── TECHSPEC.md              # Experiment specification
├── configs/
│   ├── phase1_upper.yaml    # 3.18M params (91.5%)
│   ├── phase1_middle.yaml   # 1.4M params (79.31%)
│   ├── phase1_lower.yaml    # 253K params (37.6%)
│   ├── phase1_tiny.yaml     # 77K params (~0%)
│   ├── phase2_wide.yaml     # 512d-2L (87.2%)
│   ├── phase2_balanced.yaml # 256d-4L (79.31%)
│   └── phase2_deep.yaml     # 128d-8L (71.8%)
├── data/
│   ├── train.jsonl          # 100K samples
│   └── test.jsonl           # 10K samples
├── models/
│   └── base_model.py        # Model implementation
└── train.py                 # Training script
```

## Dataset Generation

```python
# generate_addition_dataset.py
import random
import json

def base100_tokenize(num):
    """Convert number to base-100 tokens (each digit 0-99)."""
    if num == 0:
        return [0]
    tokens = []
    while num > 0:
        tokens.append(num % 100)
        num //= 100
    return tokens[::-1]  # Reverse to big-endian

def generate_addition_sample():
    """Generate one addition sample: a + b = c"""
    a = random.randint(0, 999)
    b = random.randint(0, 999)
    c = a + b

    # Tokenize: [a_tokens] + [+] + [b_tokens] + [=] + [c_tokens]
    tokens = (
        base100_tokenize(a) +
        [100] +  # '+' token
        base100_tokenize(b) +
        [101] +  # '=' token
        base100_tokenize(c)
    )

    # Pad to max length 32
    tokens = tokens + [102] * (32 - len(tokens))  # PAD token

    return {
        "input": tokens[:-len(base100_tokenize(c))],
        "target": tokens[-len(base100_tokenize(c)):],
        "answer": c
    }

# Generate datasets
with open("data/train.jsonl", "w") as f:
    for _ in range(100_000):
        f.write(json.dumps(generate_addition_sample()) + "\n")

with open("data/test.jsonl", "w") as f:
    for _ in range(10_000):
        f.write(json.dumps(generate_addition_sample()) + "\n")
```

## Phase 1 Configurations

### Upper Bound (3.18M params, 91.5% accuracy)

```yaml
# configs/phase1_upper.yaml
model:
  vocab_size: 103  # 0-99 digits, +, =, PAD
  d_model: 256
  n_layers: 6
  n_heads: 8
  d_ff: 1024
  max_seq_len: 32
  dropout: 0.1

  # RoPE config for short sequences
  rope_theta: 100
  rope_scaling: null

training:
  batch_size: 256
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0

  # Monitoring
  check_every: 500
  early_stopping:
    patience: 3
    min_delta: 0.001

optimizer:
  type: adamw
  betas: [0.9, 0.95]
  weight_decay: 0.1

scheduler:
  type: cosine
  eta_min: 1e-5
```

### Middle (1.4M params, 79.31% accuracy)

```yaml
# configs/phase1_middle.yaml
model:
  vocab_size: 103
  d_model: 192
  n_layers: 4
  n_heads: 6
  d_ff: 768
  max_seq_len: 32
  dropout: 0.1
  rope_theta: 100

training:
  batch_size: 512  # Larger batch for smaller model
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0
  check_every: 500
  early_stopping:
    patience: 3
    min_delta: 0.001

optimizer:
  type: adamw
  betas: [0.9, 0.95]
  weight_decay: 0.1
```

### Lower (253K params, 37.6% accuracy)

```yaml
# configs/phase1_lower.yaml
model:
  vocab_size: 103
  d_model: 64
  n_layers: 3
  n_heads: 4
  d_ff: 256
  max_seq_len: 32
  dropout: 0.1
  rope_theta: 100

training:
  batch_size: 1024  # Even larger batch
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0
  check_every: 500
  early_stopping:
    patience: 3
    min_delta: 0.001
```

### Tiny (77K params, ~0% accuracy - FAILED)

```yaml
# configs/phase1_tiny.yaml
model:
  vocab_size: 103
  d_model: 32
  n_layers: 2
  n_heads: 2
  d_ff: 128
  max_seq_len: 32
  dropout: 0.1
  rope_theta: 100

training:
  batch_size: 2048
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0
  check_every: 500

# Note: This config flatlines at ~0%. Too small to learn addition.
# Minimum viable size is ~250K params.
```

## Phase 2 Configurations (Width vs Depth)

### Wide-Shallow (512d-2L, 1.05M params, 87.2% accuracy)

```yaml
# configs/phase2_wide.yaml
model:
  vocab_size: 103
  d_model: 512
  n_layers: 2
  n_heads: 8
  d_ff: 2048
  max_seq_len: 32
  dropout: 0.1
  rope_theta: 100

training:
  batch_size: 512
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0
  check_every: 500
  early_stopping:
    patience: 3
    min_delta: 0.001
```

### Narrow-Deep (128d-8L, 1.02M params, 71.8% accuracy)

```yaml
# configs/phase2_deep.yaml
model:
  vocab_size: 103
  d_model: 128
  n_layers: 8
  n_heads: 4
  d_ff: 512
  max_seq_len: 32
  dropout: 0.1
  rope_theta: 100

training:
  batch_size: 512
  learning_rate: 1e-4
  warmup_steps: 500
  max_steps: 10000
  grad_clip: 1.0
  check_every: 500
  early_stopping:
    patience: 3
    min_delta: 0.001
```

## Critical Bug Fix: RoPE Dimension Mismatch

**Error:**
```
RuntimeError: The size of tensor a (32) must match the size of tensor b (16)
at non-singleton dimension 3
```

**Cause**: Standard RoPE implementations output freqs with shape `[seq_len, head_dim/2]`, but the attention layer expects `[seq_len, head_dim]` for broadcasting.

**Solution:**

```python
# models/rope.py (BEFORE - broken)
def apply_rotary_pos_emb(q, k, freqs):
    # freqs shape: [seq_len, head_dim/2]
    q_rot = q * freqs.cos() + rotate_half(q) * freqs.sin()
    k_rot = k * freqs.cos() + rotate_half(k) * freqs.sin()
    # ERROR: freqs [seq_len, 16] can't broadcast with q [batch, heads, seq_len, 32]
    return q_rot, k_rot

# models/rope.py (AFTER - fixed)
def apply_rotary_pos_emb(q, k, freqs):
    # freqs shape: [seq_len, head_dim/2]

    # Duplicate freqs to match head_dim
    freqs = torch.cat((freqs, freqs), dim=-1)  # [seq_len, head_dim]

    # Add batch and head dimensions for broadcasting
    freqs = freqs.unsqueeze(0).unsqueeze(0)  # [1, 1, seq_len, head_dim]

    # Now broadcasting works correctly
    q_rot = q * freqs.cos() + rotate_half(q) * freqs.sin()
    k_rot = k * freqs.cos() + rotate_half(k) * freqs.sin()
    return q_rot, k_rot

def rotate_half(x):
    """Rotate half the hidden dims of the input."""
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)
```

## Running the Experiments

```bash
# Generate dataset
python generate_addition_dataset.py

# Phase 1: Size scaling
python train.py configs/phase1_upper.yaml   # Expected: 91.5%
python train.py configs/phase1_middle.yaml  # Expected: 79.31%
python train.py configs/phase1_lower.yaml   # Expected: 37.6%
python train.py configs/phase1_tiny.yaml    # Expected: ~0% (will fail)

# Phase 2: Width vs depth
python train.py configs/phase2_wide.yaml     # Expected: 87.2%
python train.py configs/phase2_balanced.yaml # Expected: 79.31%
python train.py configs/phase2_deep.yaml     # Expected: 71.8%
```

## Expected Results Table

| Phase | Config | d_model | depth | Params | Exact Match | GPU Hours |
|-------|--------|---------|-------|--------|-------------|-----------|
| 1 | Upper | 256 | 6 | 3.18M | 91.5% | 8h |
| 1 | Middle | 192 | 4 | 1.4M | 79.31% | 5h |
| 1 | Lower | 64 | 3 | 253K | 37.6% | 2h |
| 1 | Tiny | 32 | 2 | 77K | ~0% | 1h |
| 2 | Wide | 512 | 2 | 1.05M | 87.2% | 4h |
| 2 | Balanced | 256 | 4 | 1.31M | 79.31% | 5h |
| 2 | Deep | 128 | 8 | 1.02M | 71.8% | 4h |

**Total GPU time**: 29 hours (A100-80GB)

## Key Learnings

1. **Minimum viable size**: ~253K params (37.6% accuracy), but realistically need ~1M for >70%
2. **Width > Depth**: For positional operations like addition, 512d-2L beats 128d-8L by 15.4%
3. **RoPE bug**: Standard implementations need dimension fix for short sequences
4. **d_proj bottleneck**: Using 32 causes 8% performance drop, use 64+
5. **Batch size scaling**: Smaller models can handle larger batches (up to 2048 for 77K model)
6. **Early stopping**: Essential to avoid overtraining (patience=3 works well)

## Troubleshooting

### Model flatlines at ~0%
- **Cause**: Model too small (<250K params)
- **Solution**: Increase d_model or n_layers to reach ~1M params

### RuntimeError: dimension mismatch in RoPE
- **Cause**: Standard RoPE outputs [seq_len, head_dim/2]
- **Solution**: Add `freqs = torch.cat((freqs, freqs), dim=-1)`

### Accuracy drops unexpectedly
- **Cause**: d_proj=32 information bottleneck
- **Solution**: Use d_proj >= 64

### OOM errors
- **Cause**: Batch size too large for model size
- **Solution**: Use 256 for 3M+ models, 512 for 1M, 1024+ for <500K

## References

- Source: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Hardware: NVIDIA A100-SXM4-80GB
- Framework: PyTorch 2.0.1, CUDA 11.8
- Total dataset: 100K train + 10K test samples
