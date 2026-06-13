---
name: tooling-build-john-jumbo-gpg-no-sudo
description: 'TRIGGER CONDITIONS: Need a working gpg2john plus a john "gpg" format to
  crack a GnuPG private-key passphrase WITHOUT sudo/root. Use when the packaged john
  is not jumbo, hashcat lacks OpenPGP modes, and you must build john-jumbo against
  OpenSSL headers borrowed from an existing pixi/conda environment.'
category: tooling
date: 2026-06-12
version: 1.0.0
user-invocable: false
tags:
- john
- john-jumbo
- gpg2john
- openssl
- passphrase
- no-sudo
- hashcat
- gnupg
---
# tooling-build-john-jumbo-gpg-no-sudo

How to get a working `gpg2john` **and** a john `gpg` cracking format to recover a GnuPG private-key passphrase on a machine where you have **no sudo/root**, by building john-jumbo against OpenSSL headers reused from an existing pixi/conda environment.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-06-12 |
| Environment | Debian/PureOS, GnuPG 2.2.27, no sudo |
| Objective | Crack a GnuPG key passphrase with `gpg2john` + john `gpg` format |
| Outcome | Success — built john-jumbo with both `gpg2john` and a working `gpg` format; validated against a known-passphrase key |
| Key constraint | No sudo: cannot `apt install libssl-dev`; reuse OpenSSL headers/libs from a pixi env |

## When to Use

- You need to crack/recover a GnuPG private-key passphrase and have **no root** on the box.
- The distro-packaged `john` is the non-jumbo build (no `gpg2john`, no `gpg` format).
- `hashcat` on the box has no OpenPGP mode (e.g., no mode `17010`).
- You have an existing pixi/conda environment that already ships OpenSSL headers (`openssl/opensslv.h`) and `libcrypto`/`libssl`.
- You need to validate the cracker end-to-end with a throwaway key whose passphrase you control.

## Verified Workflow

The non-jumbo `john` and `hashcat` are dead ends (see Failed Attempts). The only path that yields **both** `gpg2john` and a functioning `gpg` format without sudo is building john-jumbo against borrowed OpenSSL headers. The `gpg` format depends on OpenSSL at compile time, so `--without-openssl` is NOT acceptable — it produces `gpg2john` but no `gpg` format.

### 1. Confirm the packaged tooling can't do it

```bash
# Debian john 1.8.0-4 (john/john-data) is NOT jumbo: no gpg2john, no gpg format
john --list=formats | grep -i gpg   # => empty
which gpg2john                       # => not found
# hashcat 6.1.1 here has no OpenPGP mode 17010 => out
```

### 2. Clone john-jumbo

```bash
git clone --depth 1 https://github.com/openwall/john /tmp/john-jumbo
```

### 3. Locate OpenSSL headers/libs in an existing pixi/conda env

```bash
# Must contain openssl/opensslv.h
SSL_INC=/path/to/project/.pixi/envs/default/include
SSL_LIB=/path/to/project/.pixi/envs/default/lib
ls "$SSL_INC/openssl/opensslv.h"     # sanity check
```

### 4. Configure + build against the borrowed OpenSSL (no sudo)

```bash
cd /tmp/john-jumbo/src && make -s clean
CPPFLAGS="-I$SSL_INC" \
LDFLAGS="-L$SSL_LIB -Wl,-rpath,$SSL_LIB" \
  ./configure && make -sj4
```

Headers can be a newer major (OpenSSL 3.6.2) than the system runtime (`libcrypto.so.1.1`) and still compile/link fine — the APIs john uses are stable across the 1.1/3.x boundary. The embedded `-Wl,-rpath,$SSL_LIB` lets the binary find the pixi libs at runtime.

### 5. Verify the gpg format is present, then run

```bash
run/john --list=formats | grep -i gpg   # => shows "gpg" and "gpg-opencl"
# When running, also export the lib path so the loader finds the pixi OpenSSL:
LD_LIBRARY_PATH="$SSL_LIB" run/gpg2john secret.asc > hash.txt
LD_LIBRARY_PATH="$SSL_LIB" run/john --format=gpg hash.txt
```

### Quick Reference

```bash
git clone --depth 1 https://github.com/openwall/john /tmp/john-jumbo
SSL_INC=/path/.pixi/envs/default/include      # has openssl/opensslv.h
SSL_LIB=/path/.pixi/envs/default/lib
cd /tmp/john-jumbo/src && make -s clean
CPPFLAGS="-I$SSL_INC" LDFLAGS="-L$SSL_LIB -Wl,-rpath,$SSL_LIB" ./configure && make -sj4
run/john --list=formats | grep gpg            # expect: gpg, gpg-opencl
LD_LIBRARY_PATH="$SSL_LIB" run/gpg2john secret.asc > hash.txt
LD_LIBRARY_PATH="$SSL_LIB" run/john --format=gpg hash.txt
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| apt john | Use distro `john` (1.8.0-4, `john`/`john-data`) | Non-jumbo: no `gpg2john`, `john --list=formats \| grep gpg` empty | Packaged john is a dead end; you must build jumbo. Also `apt` needs root anyway. |
| hashcat | Crack the GPG hash with hashcat 6.1.1 | That build has no OpenPGP mode (no `17010`) | hashcat out for OpenPGP here; john-jumbo is the route. |
| --without-openssl | `./configure --without-openssl && make` to dodge missing libssl-dev | Builds and yields `gpg2john`, but resulting `john` has NO `gpg` format; `--format=gpg` => "No format matched requested name 'gpg'" | The `gpg` format is OpenSSL-dependent; `gpg2john` alone is useless. Must compile against real OpenSSL headers. |
| default configure | Plain `./configure` with no flags | Fails: "OpenSSL headers not found" (no libssl-dev, no sudo to install it) | Need headers from somewhere non-root — reuse a pixi/conda env's `include`/`lib`. |
| OCB test key for CBC | Validate the CBC code path with a key made by a newer GnuPG/agent | New GnuPG defaults to OCB protection (`openpgp-s2k3-ocb-aes`); format mismatch vs older CBC (`openpgp-s2k3-sha1-aes-cbc`) keys | To validate the CBC path you must generate the test key with an OLD gpg (e.g., 2.2.4). |

## Results & Parameters

**Working build parameters (no sudo):**
- `SSL_INC` = pixi env `include` dir containing `openssl/opensslv.h` (was OpenSSL 3.6.2 headers).
- `SSL_LIB` = pixi env `lib` dir (system runtime was `libcrypto.so.1.1`; mismatched major is fine — stable APIs).
- Configure: `CPPFLAGS="-I$SSL_INC" LDFLAGS="-L$SSL_LIB -Wl,-rpath,$SSL_LIB" ./configure && make -sj4`.
- Run with `LD_LIBRARY_PATH="$SSL_LIB"` so the loader resolves the pixi OpenSSL.
- After build, `run/john --list=formats | grep gpg` shows `gpg` + `gpg-opencl`.

**End-to-end validation recipe (Docker, old gpg for the CBC path):**
- Spin up a container with an OLD GnuPG: `ubuntu:18.04` + `apt install gnupg` gives GnuPG 2.2.4.
- Generate a throwaway key with a KNOWN passphrase inside that container.
- Why old gpg matters: newer GnuPG/agent defaults to OCB key protection (`openpgp-s2k3-ocb-aes`); 2021-era keys use CBC (`openpgp-s2k3-sha1-aes-cbc`). To exercise the CBC path you must use the old gpg.
- Export: `gpg --export-secret-keys --armor > secret.asc`.
- Crack: `gpg2john secret.asc > hash.txt` then `john --format=gpg hash.txt` recovers the known passphrase (confirmed).

## Key Insights

1. **`gpg2john` and the `gpg` format are decoupled.** You can have the extractor without the cracker; only a real-OpenSSL build gives you both.
2. **No sudo ≠ no OpenSSL.** A pixi/conda env is a perfectly good, writable source of headers and libs.
3. **Major-version skew is OK.** OpenSSL 3.6.2 headers linked against / running with a 1.1 runtime works because john uses stable APIs; bake an `-rpath` and set `LD_LIBRARY_PATH` so the right lib loads.
4. **Match the protection mode when validating.** OCB vs CBC key protection is determined by the gpg version that created the key — use an old gpg in Docker to validate the CBC path.
