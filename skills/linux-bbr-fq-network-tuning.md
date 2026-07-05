---
name: linux-bbr-fq-network-tuning
description: "Enable TCP BBR congestion control + fq qdisc on a Linux host, persistently and kernel-version-aware. Use when: (1) tuning throughput on lossy/higher-RTT paths like internet uploads or a Tailscale mesh, (2) tcp_available_congestion_control lists only \"reno cubic\" and bbr is missing because tcp_bbr is not loaded yet, (3) BBR reads back active but interfaces still show pfifo_fast, (4) applying the same tuning across multiple mesh hosts on different kernels (4.19 vs 5.10), (5) an lsmod grep says the module is \"not loaded\" but sysctl already reports bbr."
category: optimization
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [bbr, fq, tcp, congestion-control, qdisc, sysctl, network-tuning, tailscale, kernel-module]
---

# Linux BBR + fq Network Tuning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Switch a Linux host from default `cubic` + `pfifo_fast` to `bbr` + `fq` for better throughput on lossy/higher-latency paths (internet uploads, Tailscale mesh), persistently and in a kernel-version-aware way. |
| **Outcome** | Success. Verified live and persistent on host `epimetheus` (PureOS 10, kernel 5.10); approach assessed and adapted for `apollo` (Debian, kernel 4.19). |
| **Verification** | verified-local |

## When to Use

- Tuning throughput on lossy or higher-RTT paths — internet uploads, or a Tailscale mesh.
- `sysctl net.ipv4.tcp_available_congestion_control` lists only `reno cubic` and `bbr` is missing because `tcp_bbr` is not loaded yet.
- BBR reads back as active but interfaces still show `pfifo_fast`.
- Applying the same tuning across multiple mesh hosts on different kernels (4.19 vs 5.10).
- An `lsmod` grep says the module is "not loaded" but `sysctl` already reports `bbr` (false-negative check).

### Why BBR + fq

BBR paces sending based on measured bottleneck bandwidth and RTT instead of backing off on any packet loss (as `cubic`/`reno` do). `fq` (fair queue) is the qdisc that implements BBR's pacing and prevents bufferbloat. This is the pairing Google uses on its edge. It is congestion-control only — it affects TCP send pacing, not filtering or routing, so it cannot block connections and is fully reversible.

## Verified Workflow

### Quick Reference

```bash
# 1. Check current state — only "reno cubic" means BBR is NOT loaded yet
sysctl -n net.ipv4.tcp_available_congestion_control

# 2. Load the modules (the .ko files being present does NOT mean loaded)
modprobe tcp_bbr
modprobe sch_fq        # usually already available

# 3. Persist the module load across reboots
echo tcp_bbr > /etc/modules-load.d/bbr.conf

# 4. GUARD: abort if bbr did not actually load — never write the sysctl otherwise
grep -qw bbr <(sysctl -n net.ipv4.tcp_available_congestion_control) || {
  echo "ABORT: bbr not in available_congestion_control; module failed to load" >&2
  exit 1
}

# 5. Persist the sysctl settings
cat > /etc/sysctl.d/99-network-tuning.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF

# 6. Apply live
sysctl --system

# 7. Apply fq to ALREADY-UP interfaces (default_qdisc only affects NEW ones).
#    Required on kernel 4.19; on 5.10 a reboot would also suffice.
for i in /sys/class/net/*; do
  dev=$(basename "$i")
  [ "$dev" = "lo" ] && continue
  tc qdisc replace dev "$dev" root fq
done

# 8. Verify authoritatively
sysctl -n net.ipv4.tcp_congestion_control      # expect: bbr
[ -d /sys/module/tcp_bbr ] && echo "tcp_bbr LOADED"   # authoritative loaded-check
tc qdisc show dev enp0s31f6                     # expect: qdisc fq ... root
```

### Detailed Steps

1. **Check current state.** `sysctl net.ipv4.tcp_available_congestion_control`. If it shows only `reno cubic`, BBR is not loaded. Note: the `.ko` files being present on disk (`/lib/modules/$(uname -r)/kernel/net/ipv4/tcp_bbr.ko`, `.../net/sched/sch_fq.ko`) does NOT mean they are loaded.
2. **Load the modules.** `modprobe tcp_bbr` (and `modprobe sch_fq`, usually already available). After this, `bbr` appears in the available list.
3. **Persist the module load.** `echo tcp_bbr > /etc/modules-load.d/bbr.conf` so it loads on every boot.
4. **Guard before selecting.** Re-read `sysctl -n net.ipv4.tcp_available_congestion_control` and abort if `bbr` is not in it. Never write `net.ipv4.tcp_congestion_control = bbr` when the module did not load — the kernel rejects/ignores the value and you get a broken half-state.
5. **Persist settings** in `/etc/sysctl.d/99-network-tuning.conf`:
   ```ini
   net.core.default_qdisc = fq
   net.ipv4.tcp_congestion_control = bbr
   ```
6. **Apply live.** `sysctl --system`.
7. **Apply fq to already-up interfaces.** `net.core.default_qdisc = fq` only applies to NEWLY created interfaces. Existing interfaces keep their qdisc until reboot. On kernel 4.19 nothing switches automatically, so loop over `/sys/class/net` (excluding `lo`) running `tc qdisc replace dev <iface> root fq`. On 5.10 a reboot suffices, but applying live avoids the reboot.
8. **Verify authoritatively.** `sysctl -n net.ipv4.tcp_congestion_control` returns `bbr`; `[ -d /sys/module/tcp_bbr ]` is the authoritative "is it loaded" check; `tc qdisc show dev <iface>` shows `qdisc fq`.

### Kernel-version-aware notes

- **kernel 5.10 (epimetheus):** Worked cleanly; modules present. A reboot switches qdiscs automatically, but applying `fq` live avoids needing one.
- **kernel 4.19 (apollo):** BBR is loadable (`modprobe -n tcp_bbr` dry-run OK) and `tcp_bbr.ko`/`sch_fq.ko` are present, but stock config was `cubic`/`pfifo_fast` with available list `reno cubic`. On 4.19 you MUST apply `fq` live to already-up interfaces — it will not auto-switch — so a remote tuning script should loop over `/sys/class/net` (excluding `lo`) doing `tc qdisc replace dev $i root fq`.

### Reversibility

Fully reversible; cannot block connections (congestion control only affects TCP send pacing, not filtering/routing):

```bash
rm -f /etc/sysctl.d/99-network-tuning.conf /etc/modules-load.d/bbr.conf
sysctl --system
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Set `net.ipv4.tcp_congestion_control=bbr` directly | Writing the sysctl before loading the module | `bbr` wasn't in `tcp_available_congestion_control` (module unloaded), so the value is rejected/ignored, leaving a broken half-state | `modprobe tcp_bbr` FIRST, then guard-check the available list before selecting `bbr`. |
| Trust `lsmod \| grep '^tcp_bbr'` as proof of load state | Using an `lsmod` grep as the verification signal in a script | Reported "NOT loaded" while BBR was in fact active and serving 44 sockets — a false negative (strict `^tcp_bbr` grep missed the registered module on Debian) | Use `[ -d /sys/module/tcp_bbr ]` + `sysctl` readback as authoritative; `lsmod` grep is unreliable as a negative signal. |
| Assume `default_qdisc=fq` takes effect immediately on live interfaces | Setting the sysctl and checking `tc qdisc show` | Already-up interfaces kept `pfifo_fast`; `default_qdisc` only affects newly-created interfaces | Apply live with `tc qdisc replace dev <iface> root fq`, or reboot; on kernel 4.19 live application is required. |

## Results & Parameters

### `/etc/sysctl.d/99-network-tuning.conf` (full contents)

```ini
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
```

### `/etc/modules-load.d/bbr.conf` (full contents)

```
tcp_bbr
```

### modprobe → guard → apply sequence

```bash
modprobe tcp_bbr
modprobe sch_fq
echo tcp_bbr > /etc/modules-load.d/bbr.conf

# GUARD — do not proceed if bbr failed to load
grep -qw bbr <(sysctl -n net.ipv4.tcp_available_congestion_control) || {
  echo "ABORT: bbr not available; module not loaded" >&2; exit 1; }

cat > /etc/sysctl.d/99-network-tuning.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF
sysctl --system

# Apply fq to already-up interfaces (required on 4.19)
for i in /sys/class/net/*; do
  dev=$(basename "$i"); [ "$dev" = "lo" ] && continue
  tc qdisc replace dev "$dev" root fq
done
```

### Verification commands and expected outputs

| Command | Expected output | Meaning |
|---------|-----------------|---------|
| `sysctl -n net.ipv4.tcp_congestion_control` | `bbr` | Active congestion control. Kernel won't accept a cc value it cannot provide, so this doubles as a load check. |
| `[ -d /sys/module/tcp_bbr ]` | exit 0 (`/sys/module/tcp_bbr` present) | Authoritative "module is loaded" check. |
| `tc qdisc show dev enp0s31f6` | `qdisc fq 8001: root ...` | fq is active on the interface (after `tc qdisc replace`). |
| `sysctl -n net.ipv4.tcp_available_congestion_control` | includes `bbr` (e.g. `reno cubic bbr`) | BBR module registered and selectable. |

### Observed proof of loaded state

`lsmod` line showing the module in use (the trailing number is the count of active sockets using it):

```
tcp_bbr                20480  44
```

corroborated by `/sys/module/tcp_bbr` being present and `sysctl -n net.ipv4.tcp_congestion_control` reading back `bbr`. Note the `lsmod` line is proof it IS loaded — but a strict `grep '^tcp_bbr'` can still miss it, which is why it must never be used as a negative signal.
