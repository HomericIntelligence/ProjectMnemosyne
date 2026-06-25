---
name: tooling-parallel-gpg-passphrase-trial
description: "Brute-force a forgotten passphrase against a GPG-encrypted file using gpg itself (always-correct, no key export), parallelized across cores with a tiered most-likely-first wordlist. Use when: (1) you must recover a forgotten GPG passphrase and the fast offline john gpg path is unavailable, (2) you need a safe always-correct fallback that never exports key material, (3) you need to parallelize gpg trial decryption across CPU cores without gpg-agent contention."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [gpg, passphrase, recovery, parallel, wordlist, gnupg]
---

# Parallel GPG Passphrase Trial (Safe Slow Fallback)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Recover a forgotten passphrase on a GPG-encrypted file using gpg itself (no key export), parallelized across cores, with a smart most-likely-first wordlist |
| **Outcome** | Successful — single-thread floor ~1.4 pw/s, ~5.6 pw/s on a 4-core box with per-worker GNUPGHOME isolation |
| **Verification** | verified-local (GnuPG 2.2.27, 4-core box) |

This is the SAFE fallback path when fast offline cracking (john's `gpg` format) is
unavailable. Trial decryption through `gpg` is always correct because it asks gpg
the same question the real unlock does — no key export, no format conversion, no
risk of a false negative.

Related skills (cross-reference, NOT duplicates):

- `debugging-gpg-agent-key-crack-export-barrier` — the export-barrier problem that
  blocks the fast path.
- `tooling-build-john-jumbo-gpg-no-sudo` — building john jumbo for the FAST path.
  This skill is the slow-but-safe alternative when that path is not available.

## When to Use

- A GPG-encrypted file's passphrase is forgotten and the fast offline `john` gpg
  format is unavailable (cannot extract the hash, cannot build john, key won't export).
- You need an always-correct method that never exports key material from the keyring.
- You want to parallelize gpg trial decryption across CPU cores without gpg-agent
  serializing or corrupting the workers.
- You have candidate passwords (e.g. from a password manager) and want to order
  them so a probable hit lands early instead of after the full keyspace.

## Verified Workflow

### Quick Reference

```bash
# ---- Parallel worker skeleton: split + per-worker GNUPGHOME + sentinel ----
WORKDIR=$(mktemp -d)
N=$(nproc)                      # one worker per core
ENC=secret.gpg                  # the encrypted file
WORDLIST=candidates.txt         # tiered, most-likely-first, deduped

mkdir -p "$WORKDIR/chunks"
split -n l/$N "$WORDLIST" "$WORKDIR/chunks/chunk."

try_chunk() {
  local chunk="$1" home="$2"
  cp -a "$HOME/.gnupg" "$home"      # ISOLATED keyring per worker — critical
  while IFS= read -r pw; do
    [ -f "$WORKDIR/found" ] && return 0          # another worker won; stop
    if GNUPGHOME="$home" gpg --batch --quiet --pinentry-mode loopback \
         --passphrase "$pw" --decrypt "$ENC" >/dev/null 2>&1; then
      printf '%s' "$pw" > "$WORKDIR/found"        # record the hit
      return 0
    fi
  done < "$chunk"
}

i=0
for chunk in "$WORKDIR"/chunks/chunk.*; do
  try_chunk "$chunk" "$WORKDIR/gpghome.$i" &
  i=$((i+1))
done
wait
[ -f "$WORKDIR/found" ] && echo "PASSPHRASE: $(cat "$WORKDIR/found")" || echo "not found"
```

```python
# ---- Tiered most-likely-first wordlist generator (outline) ----
# Pull bare bases from the user's password manager, apply case variants,
# then combine. Dedupe while PRESERVING priority order.
import itertools

def case_variants(w):
    return {w, w.capitalize(), w.lower(), w.upper(),
            (w[:1].upper() + w[1:]) if w else w}

SUFFIXES = ["!", "@", "#", "$", "A", "B", "C", "D", "1", "1234", "1234!", "!@A", "!A"]
SEPS = ["", ".", "-", "_"]

def gen(bases, stored):
    out = []
    # Tier 1: stored passwords + case variants
    for p in stored:
        out += list(case_variants(p))
    # Tier 2: bare bases + single suffixes
    for b in bases:
        for v in case_variants(b):
            out.append(v)
            for s in SUFFIXES:
                out.append(v + s)
    # Tier 3: concatenations of two bases (people join two short passwords)
    for a, b in itertools.product(bases, repeat=2):
        for va in case_variants(a):
            for vb in case_variants(b):
                for sep in SEPS:
                    out.append(va + sep + vb)
                for s in SUFFIXES:
                    out.append(va + vb + s)        # pw1pw2<suffix>
                    out.append(va + s + vb)        # pw1<suffix>pw2
    return out

# Cap length to prune (e.g. <= 30), then dedupe preserving order:
#   gen(...) | awk 'length<=30' | awk '!seen[$0]++' > candidates.txt
```

```bash
# Dedupe preserving priority order (Tier 1 stays first):
awk 'length<=30' raw_candidates.txt | awk '!seen[$0]++' > candidates.txt
```

### Detailed Steps

1. **Source candidates from the user's own password manager.** Install
   `pip install --user pykeepass`; open the KDBX4/Argon2 db with its master
   password and iterate `kp.entries -> e.password`. These stored passwords are the
   seed for Tiers 1–3. Do NOT use KWallet entries for modern email accounts: on KDE
   those are usually OAuth TOKENS (52–95 char blobs), not passphrase candidates.

   ```python
   from pykeepass import PyKeePass
   kp = PyKeePass("db.kdbx", password=MASTER)
   stored = [e.password for e in kp.entries if e.password]
   ```

2. **Derive bare bases.** Strip known suffixes off each stored password to get the
   bare base word, then apply case variants. Bases feed Tier 2/3 combinations.

3. **Generate the tiered wordlist (most-likely-first):**
   - Tier 1: plain stored passwords + case variants (capitalize/lower/upper first letter).
   - Tier 2: single suffixes the user appends — `! @ # $ A B C D 1 1234 1234!` and
     combos like `!@A` `!A`.
   - Tier 3: concatenations (people join two short passwords) — `pw1pw2`,
     `pw1<suffix>pw2`, `pw1<suffix>pw2<suffix>`, `pw1pw2<suffix>`, and
     separator-joined `pw1.pw2` / `pw1-pw2` / `pw1_pw2`.

4. **Cap and dedupe preserving order.** Drop candidates over the length cap
   (e.g. `<=30`), then `awk '!seen[$0]++'` to dedupe WITHOUT reordering — Tier 1
   must stay at the front.

5. **Split the wordlist** into N chunks with `split -n l/N` (N = `nproc`).

6. **Run N background workers, each with its OWN isolated GNUPGHOME.** Copy the
   keyring per worker (`cp -a ~/.gnupg $WORKDIR/gpghome.$i`) and run
   `GNUPGHOME=... gpg --batch --pinentry-mode loopback --passphrase <pw> --decrypt`.
   Isolation is mandatory — see Failed Attempts.

7. **Use a shared sentinel file** named `found`. Each worker checks `[ -f found ]`
   at the top of its loop and returns early once any worker writes the hit. The
   first hitter writes the passphrase to `found`; all others stop.

8. **Size the run realistically and run longest tiers last.** N stored passwords
   pairwise-concatenated is N*N candidates; at ~1.4/s that's days for N=400. Even
   at 4-core ~5.6/s, full NxN of hundreds of passwords is many hours. Get hints
   from the user (likely base words, suffix/structure) to collapse the space.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Speed up a single attempt | Tuned a single-thread `gpg`/GPGME loopback decrypt, with and without gpg-agent cache reloads | Hard floor ~1.4 passphrases/sec from GnuPG's deliberate s2k slowdown — identical across per-process gpg, in-process GPGME, and cache variants | You cannot speed up ONE attempt; the only lever is parallelism across cores |
| Shared GNUPGHOME across workers | Ran N parallel gpg workers all using the default `~/.gnupg` | Workers contend on one gpg-agent and serialize / corrupt each other's cache, killing the parallelism | Give every worker its OWN isolated GNUPGHOME (`cp -a ~/.gnupg gpghome.$i`) |
| Blind full-keyspace brute force | Enumerated the whole candidate keyspace with no ordering | Intractable — full NxN of hundreds of passwords is days at 1.4/s, hours even at 5.6/s | Prioritize tiers, get hints from the user, run longest tiers last |
| KWallet entries as candidates | Pulled "passwords" from KWallet for modern email accounts | They were OAuth tokens (52–95 char blobs), not passphrases — wasted the run | On KDE, source candidates from a real password manager (pykeepass), not KWallet token blobs |
| Unordered wordlist | Fed candidates in arbitrary order | The likely hit was buried near the end, so the run took far longer than necessary | Order most-likely-first (Tier 1 stored pw → Tier 2 suffixes → Tier 3 concats) and dedupe preserving order |

## Results & Parameters

**Measured throughput (GnuPG 2.2.27, 4-core box):**

| Config | Throughput |
|--------|-----------|
| Single-thread (per-process gpg, GPGME loopback, ± agent cache) | ~1.4 passphrases/sec (hard s2k floor) |
| 4 workers, isolated GNUPGHOME each | ~5.6 passphrases/sec (≈ N× single) |

**Tier ordering (most-likely-first):**

1. Tier 1 — plain stored passwords + case variants (capitalize / lower / upper first letter).
2. Tier 2 — single suffixes appended to bare bases: `! @ # $ A B C D 1 1234 1234!` and combos `!@A` `!A`.
3. Tier 3 — concatenations of two bases: `pw1pw2`, `pw1<suffix>pw2`, `pw1<suffix>pw2<suffix>`, `pw1pw2<suffix>`, separator-joined `pw1.pw2` / `pw1-pw2` / `pw1_pw2`.

**Candidate sourcing (pykeepass):**

```python
# pip install --user pykeepass
from pykeepass import PyKeePass
kp = PyKeePass("db.kdbx", password=MASTER_PASSWORD)
stored = [e.password for e in kp.entries if e.password]
# NOTE: KWallet on KDE often stores OAuth TOKENS (52-95 char blobs) for modern
# email accounts, not passwords — do not use them as passphrase candidates.
```

**Length cap + dedupe-preserving-order:**

```bash
# Cap length to prune, then dedupe WITHOUT reordering (Tier 1 stays first):
awk 'length<=30' raw_candidates.txt | awk '!seen[$0]++' > candidates.txt
```

**Sizing reality:** N stored passwords pairwise-concatenated = N*N candidates.
For N=400 at 1.4/s ≈ days; at 4-core 5.6/s still many hours. Collapse the space
with user hints (base words, likely suffix/structure) and run longest tiers last.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Local recovery | GnuPG 2.2.27, 4-core box — safe slow fallback when john gpg path unavailable | Cross-ref `debugging-gpg-agent-key-crack-export-barrier`, `tooling-build-john-jumbo-gpg-no-sudo` |
