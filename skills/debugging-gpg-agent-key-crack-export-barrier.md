---
name: debugging-gpg-agent-key-crack-export-barrier
description: "Recover (or correctly conclude you cannot fast-crack) a forgotten passphrase for a GnuPG secret encryption subkey whose secret material lives ONLY as a gpg-agent S-expression file ~/.gnupg/private-keys-v1.d/<KEYGRIP>.key. Use when: (1) you must decrypt a message but the required subkey is protected by an unknown passphrase, (2) gpg2john rejects the .key file with 'can't find PGP armor boundary', (3) gpg --export-secret-keys/--export-secret-subkeys refuses without the passphrase ('No passphrase given' under loopback, 'Inappropriate ioctl for device' without pinentry) or emits only a gnu-dummy S2K stub, (4) you are tempted to hand-build a john \\$gpg\\$ hash by copying salt/count/iv/blob out of the .key S-expression and john reports 'No password hashes loaded', (5) you need the SAFE always-correct fallback trial loop and its realistic throughput before quoting an ETA. GnuPG 2.2.27, 2021-era openpgp-s2k3-sha1-aes-cbc keys."
category: debugging
date: 2026-06-12
version: "1.0.0"
user-invocable: false
tags:
  - gpg
  - gnupg
  - gpg-agent
  - passphrase-recovery
  - keygrip
  - s-expression
  - s2k
  - gpg2john
  - john-the-ripper
  - export-secret-keys
  - loopback-pinentry
  - gpgme
  - openpgp
  - aes-cbc
  - credential-safety
---

# Debugging: gpg-agent S-expression Key Crack Export Barrier

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Recover a forgotten passphrase for a GnuPG secret encryption subkey whose secret material exists only as a gpg-agent file `~/.gnupg/private-keys-v1.d/<KEYGRIP>.key`, in order to decrypt a message — or determine authoritatively that no fast offline crack is reachable without re-authorizing an export of the private key |
| **Outcome** | Partial — established that the `.key` cannot be fed to a fast cracker (gpg2john/john) without first EXPORTING it to OpenPGP form, and that gpg-agent refuses to export without the passphrase. Proved the fast path works only for already-exported keys. The safe, always-correct trial path runs at a hard ~1.4 tries/sec floor imposed by the S2K work factor |
| **Verification** | verified-local (GnuPG 2.2.27) |

## When to Use

- You need to decrypt a message but the required encryption subkey is locked by a passphrase nobody remembers, and the only copy of the secret material is the gpg-agent file `~/.gnupg/private-keys-v1.d/<KEYGRIP>.key`.
- `gpg2john ~/.gnupg/private-keys-v1.d/<KEYGRIP>.key` fails with `can't find PGP armor boundary` — it expects an exported OpenPGP key, not an agent S-expression.
- `gpg --export-secret-keys` / `--export-secret-subkeys` refuses: `No passphrase given` (empty loopback) or `Inappropriate ioctl for device` (no pinentry on a headless host), or `--export-secret-subkeys '<ID>!'` returns only a tiny `gnu-dummy` S2K STUB with no secret material.
- You are about to (or have already) hand-built a john `$gpg$*...` hash string by copying the salt/count/iv/encrypted-blob parsed out of the `.key`, and john says `No password hashes loaded` / `No password hashes left to crack`.
- You want the SAFE fallback that is always correct, and need its realistic throughput before you promise anyone an ETA.
- You are weighing whether to copy private-key material into /tmp or a container to re-serialize it — recognize this is a credential-handling decision that belongs to the human owner, not the agent.

## Verified Workflow

### Quick Reference

```bash
# 1. Map the message's required subkey -> keygrip
gpg --list-packets <msg.asc> | grep -i keyid          # key id the message needs
gpg --list-secret-keys --with-keygrip \
    --with-subkey-fingerprints                        # subkey fp -> keygrip
#   The keygrip names the file ~/.gnupg/private-keys-v1.d/<KEYGRIP>.key

# 2. SAFE always-correct trial loop (no export, no exfiltration).
#    Per-candidate, via gpg loopback:
printf '%s' "$CANDIDATE" | \
  gpg --batch --pinentry-mode loopback --passphrase-fd 0 \
      --decrypt <msg.asc> >/dev/null 2>&1 && echo "MATCH: $CANDIDATE"
#    Reset/avoid the agent passphrase cache between attempts:
gpgconf --reload gpg-agent      # or: echo RELOADAGENT | gpg-connect-agent
#    Throughput is a HARD ~1.4 tries/sec floor (S2K iteration cost),
#    identical for in-process GPGME and per-process gpg. Plan ETA on 1.4/s.
```

In-process equivalent (Python GPGME), same ~1.4/s floor:

```python
import gpg
with gpg.Context(pinentry_mode=gpg.constants.PINENTRY_MODE_LOOPBACK) as c:
    c.set_passphrase_cb(lambda *a: candidate.encode())
    try:
        c.decrypt(open("msg.asc", "rb"))   # success => candidate is correct
    except gpg.errors.GPGMEError:
        pass
```

### Procedure / Findings

1. **Identify the target.** The `.key` filename is the KEYGRIP. Confirm it is the subkey the message actually requires (step 1 above) before spending any compute.
2. **Recognize the file format.** The `.key` is a GnuPG canonical **S-EXPRESSION**, not an OpenPGP packet:
   `(21:protected-private-key(3:rsa(1:n257:..)(1:e..))(9:protected25:openpgp-s2k3-sha1-aes-cbc((4:sha1 8:<salt> 9:<count>) 16:<iv>) <enclen>:<encrypted>))`.
   2021-era keys use `openpgp-s2k3-sha1-aes-cbc` = AES-128-CBC with an iterated-salted SHA1 S2K. Newer GnuPG emits `openpgp-s2k3-ocb-aes` (OCB, not CBC) — note which you have, the crackers differ.
3. **Why the fast tools don't apply directly.** `gpg2john` needs an EXPORTED OpenPGP key and rejects the S-expression outright (`can't find PGP armor boundary`).
4. **The export barrier (the crux).** `gpg --export-secret-keys` / `--export-secret-subkeys` will not release plaintext secret material without the passphrase — the agent enforces unlock-to-export. Loopback with an empty passphrase gives `No passphrase given`; no pinentry gives `Inappropriate ioctl for device`; `--export-secret-subkeys '<ID>!'` yields only a 659-byte `gnu-dummy` S2K stub with no key bits. There is no agent-side flag to dump the still-encrypted blob in OpenPGP framing.
5. **Hand-building the john hash does not work.** The agent S-expression and the OpenPGP secret-key packet encrypt **different byte layouts**, so copied salt/count/iv/blob are not interchangeable: the S-expr blob is ~720 bytes (all MPIs d,p,q,u + a 20-byte SHA1 integrity hash + cipher-block padding) while the OpenPGP packet john parses is a ~668-byte blob with OpenPGP MPI framing. john therefore loads nothing.
6. **The only fast path requires re-serialization, which is a human decision.** Feeding the real key to a fast cracker needs either the passphrase (which defeats the purpose) or importing the `.key` into gpg and re-serializing to OpenPGP. Copying private-key material into /tmp or a Docker container is flagged by safety tooling as credential exfiltration; that authorization is the OWNER's to give, not the agent's to route around.
7. **Safe fallback (always correct, slow).** Feed candidates to gpg via GPGME loopback or `gpg --batch --pinentry-mode loopback --passphrase-fd 0 --decrypt` (Quick Reference). Throughput is a hard ~1.4 tries/sec floor from the S2K slowdown — in-process GPGME and per-process gpg both measure ~1.4/s, and agent-cache reloads do not change it. Reset/avoid the agent passphrase cache between attempts so a cached good unlock can't mask a wrong candidate.
8. **Validation primitive that proves the fast path is real.** Build john-jumbo with gpg support (see the separate john-jumbo build skill). Create a CBC test key with a KNOWN passphrase using OLD gpg in Docker (`ubuntu:18.04`, gnupg 2.2.4), then `export-secret-keys` -> `gpg2john` -> `john --format=gpg` recovers it. This confirms the fast path works for EXPORTED keys; the sole blocker for the real key is the export barrier in step 4.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| gpg2john on the agent file | `gpg2john ~/.gnupg/private-keys-v1.d/<KEYGRIP>.key` | `can't find PGP armor boundary` — gpg2john expects an exported OpenPGP key, not a GnuPG S-expression | The `.key` is an S-expression; the fast tools never accept it directly |
| Export the subkey | `gpg --export-secret-subkeys '<ID>!'` | Returned only a 659-byte `gnu-dummy` S2K STUB with no secret material | A `!`-selected subkey export without unlock yields a stub, not crackable bits |
| Export without passphrase | `gpg --export-secret-keys` under loopback / headless | `No passphrase given` (empty loopback) or `Inappropriate ioctl for device` (no pinentry) | The agent enforces unlock-to-export; there is no plaintext dump without the passphrase |
| Hand-build a john hash | Assembled `$gpg$*1*<len>*<bits>*<enchex>*254*2*7*<ivlen>*<ivhex>*<count>` from the S-expr's parsed salt/count/iv/blob | `No password hashes loaded` — S-expr encrypts a different layout (d,p,q,u + 20-byte SHA1 + block padding, ~720 B) than the OpenPGP packet john expects (~668 B, OpenPGP MPI framing) | The two serializations are not byte-interchangeable; you cannot transplant fields between them |
| Naive speed-up | Tried to push the safe loopback trial loop faster (process reuse, agent-cache reloads) | Stayed pinned at ~1.4 tries/sec | The S2K work factor is a hard floor; in-process GPGME and per-process gpg both hit ~1.4/s. Quote ETAs on 1.4/s |

## Results & Parameters

| Parameter | Value / Note |
|-----------|--------------|
| GnuPG version | 2.2.27 (target); 2.2.4 used in `ubuntu:18.04` Docker for the known-pass test key |
| Agent file | `~/.gnupg/private-keys-v1.d/<KEYGRIP>.key`, a GnuPG canonical S-expression |
| S2K / cipher (2021-era) | `openpgp-s2k3-sha1-aes-cbc` = AES-128-CBC, iterated-salted SHA1 |
| S2K / cipher (newer GnuPG) | `openpgp-s2k3-ocb-aes` (OCB, not CBC) — crackers differ; check which you have |
| S-expr blob layout | all MPIs d,p,q,u + 20-byte SHA1 integrity hash + cipher-block padding => ~720-byte encrypted blob |
| OpenPGP packet layout | OpenPGP MPI framing => ~668-byte encrypted blob (what `gpg2john`/john parse) |
| Layout interchangeability | None — copied salt/count/iv/blob between the two => john `No password hashes loaded` |
| Subkey -> keygrip map | `gpg --list-secret-keys --with-keygrip --with-subkey-fingerprints` |
| Message's required key id | `gpg --list-packets <msg.asc> | grep keyid` |
| Stub export size | 659 bytes (`gnu-dummy` S2K, no secret material) |
| Safe trial throughput | ~1.4 tries/sec, hard S2K floor; identical for GPGME in-process and per-process gpg; unaffected by agent-cache reloads |
| Export refusal modes | `No passphrase given` (empty loopback) / `Inappropriate ioctl for device` (no pinentry) |
| Safety boundary | Re-serializing the `.key` via /tmp or a container is credential exfiltration — owner-authorized only, not agent-routable |
