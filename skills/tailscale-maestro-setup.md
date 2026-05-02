---
name: tailscale-maestro-setup
description: 'Set up Tailscale on Linux and configure cross-host AI Maestro connectivity.
  Use when: (1) enabling Tailscale on Debian/Linux, (2) connecting multiple AI Maestro
  instances across machines, (3) diagnosing network connectivity issues between hosts.'
category: tooling
date: 2026-03-17
version: 1.0.0
user-invocable: false
---
## Overview

This skill documents the complete process for setting up Tailscale on Linux (Debian-based systems) and configuring cross-host AI Maestro connectivity. It includes installation steps, network diagnostics, and troubleshooting for common SSL/connectivity errors.

| Phase | Purpose |
| ------- | --------- |
| Tailscale Installation | Enable VPN networking on Linux via Debian package repository |
| Network Diagnostics | Verify Tailscale connectivity and port accessibility |
| AI Maestro Configuration | Bind AI Maestro to all interfaces (0.0.0.0) for cross-host access |
| Cross-Host Linking | Connect multiple AI Maestro instances via Tailscale IPs |

## When to Use

- **Installing Tailscale on Debian/Linux** - Fresh Tailscale setup on Linux machines
- **Connecting AI Maestro instances** - Multiple machines running AI Maestro that need to communicate
- **Cross-host team meetings** - Setting up team meetings between agents on different machines
- **Diagnosing SSL/connectivity errors** - Troubleshooting "Unable to connect" or SSL_ERROR_RX_RECORD_TOO_LONG errors

## Verified Workflow

### Step 1: Install Tailscale on Linux (Debian)

```bash
# Add Tailscale's package repository
curl -fsSL https://pkgc.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgc.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list

# Update package list
sudo apt-get update

# Install Tailscale
sudo apt-get install tailscale

# Start the Tailscale daemon
sudo systemctl start tailscale
sudo systemctl enable tailscale

# Authenticate and connect to your tailnet
sudo tailscale up
```

The `sudo tailscale up` command will output a login URL. Open it in a browser, authenticate with your Tailscale account, and authorize the device to join your tailnet.

### Step 2: Verify Tailscale Installation

```bash
# Check Tailscale status and get assigned IP
tailscale status

# Example output:
# 100.111.95.114  epimetheus  mvillmow@  linux  -
# 100.75.198.77   hermes      mvillmow@  linux  idle, tx 404 rx 252
```

Record the Tailscale IPs of all machines you plan to connect.

### Step 3: Configure AI Maestro on Each Machine

Ensure AI Maestro is running on all machines and bound to all interfaces (0.0.0.0), not just localhost.

**Check current binding:**
```bash
# On the machine running AI Maestro
grep -n "listen\|localhost\|0.0.0.0" ~/ai-maestro/server.mjs | head -5
```

**If bound to localhost, update server.mjs:**
```javascript
// Change from:
httpServer.listen(PORT, 'localhost', ...)

// To:
httpServer.listen(PORT, '0.0.0.0', ...)
```

Then restart AI Maestro:
```bash
cd ~/ai-maestro
yarn dev    # or yarn start for production
```

### Step 4: Diagnose Connectivity Between Machines

From machine A, test connectivity to machine B:

```bash
# Verify Tailscale network connectivity
ping -c 2 <tailscale-ip-of-machine-b>

# Verify port 23000 is open and responding
nc -zv <tailscale-ip-of-machine-b> 23000

# Test HTTP connectivity to AI Maestro
curl http://<tailscale-ip-of-machine-b>:23000/api/v1/health
```

All three should succeed. If any fail, see "Failed Attempts" section.

### Step 5: Link AI Maestro Instances

On the first machine (epimetheus), access:
```
http://localhost:23000
```

During setup, enter the Tailscale IP of the second machine (hermes):
```
http://100.75.198.77:23000
```

This will:
1. Connect to hermes
2. Fetch the organization name
3. Add both machines to the same organization
4. Enable cross-host communication

Both machines should now appear in the same AI Maestro network.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Accessed via localhost from remote machine | Used `http://localhost:23000` to connect from hermes to epimetheus | localhost on machine A doesn't resolve to machine B — each machine has its own localhost | Always use Tailscale IP addresses (100.x.x.x) for cross-host communication, never localhost |
| Accessed via HTTPS | Tried `https://100.75.198.77:23000` | Browser auto-upgraded HTTP to HTTPS, but AI Maestro serves plain HTTP; SSL layer rejected raw HTTP traffic with SSL_ERROR_RX_RECORD_TOO_LONG | Always use `http://` (not `https://`) for cross-host AI Maestro connectivity; localhost-only app doesn't use TLS |
| SSH to remote host | Ran `ssh hermes "curl ..."` to verify server binding | SSH was not configured on the target machine (WSL2 environment) | Not all machines will have SSH available; use network diagnostics (ping, nc) to test connectivity instead |
| Assumed AI Maestro was listening on all interfaces | Didn't verify server.mjs binding | Server was bound to localhost only, rejecting cross-host connections; nc showed port was "open" but actually couldn't reach it from another machine | Always verify server binding with `grep listen server.mjs` or `netstat -tuln \| grep 23000`; localhost binding is the most common cause of "Unable to connect" errors |

## Results & Parameters

### Successful Cross-Host Setup Parameters

**Environment:**
- Machine 1 (epimetheus): Linux 5.10.0-37-amd64 (Debian)
- Machine 2 (hermes): Linux 6.6.87.2-microsoft-standard-WSL2 (Windows Subsystem for Linux)
- Network: Tailscale VPN (no internet relay needed for local network)
- Tailscale version: 1.94.2

**Tailscale IPs (from `tailscale status`):**
- epimetheus: `100.111.95.114`
- hermes: `100.75.198.77`

**AI Maestro Configuration:**
- Port: 23000 (default)
- Binding: 0.0.0.0 (all interfaces)
- Protocol: HTTP (no TLS on localhost)
- Mode: Full (Next.js + WebSocket)

**Connectivity Verification Commands:**
```bash
# From epimetheus to hermes
ping -c 2 100.75.198.77           # ✅ 2 packets, 0% loss, ~12ms RTT
nc -zv 100.75.198.77 23000         # ✅ Connection succeeded
curl http://100.75.198.77:23000/api/v1/health  # ✅ HTTP 200
```

### Debugging Checklist

If cross-host setup fails, follow this checklist in order:

1. ✅ **Tailscale running on both machines**
   ```bash
   tailscale status
   ```
   Should show both machines with assigned IPs (100.x.x.x).

2. ✅ **Network connectivity (ping)**
   ```bash
   ping -c 2 <remote-tailscale-ip>
   ```
   Should show 0% packet loss and reasonable latency (<100ms).

3. ✅ **Port accessibility (nc)**
   ```bash
   nc -zv <remote-tailscale-ip> 23000
   ```
   Should print "Connection succeeded".

4. ✅ **AI Maestro binding (netstat/ss on remote)**
   ```bash
   ssh remote "netstat -tuln | grep 23000"
   # or
   ssh remote "ss -tuln | grep 23000"
   ```
   Should show listening on `0.0.0.0:23000` or `:::23000`, NOT `127.0.0.1:23000`.

5. ✅ **HTTP connectivity (curl)**
   ```bash
   curl http://<remote-tailscale-ip>:23000/api/v1/health
   ```
   Should return HTTP 200 with JSON response.

6. ✅ **Browser URL format**
   - Use `http://` (not `https://`)
   - Use Tailscale IP (not localhost, not hostname)
   - Include port: `:23000`
   - Example: `http://100.75.198.77:23000`

### Common Error Messages

| Error | Cause | Fix |
| ------- | ------- | ----- |
| "Unable to connect" (Firefox) | AI Maestro not listening on 0.0.0.0 or port 23000 is blocked | Update server.mjs: `listen(PORT, '0.0.0.0')` and restart |
| SSL_ERROR_RX_RECORD_TOO_LONG | Browser forced HTTPS, but server serves HTTP | Use `http://` (not `https://`) in the URL |
| "Connection refused" | Port 23000 is not open on remote machine | Verify port is bound: `netstat -tuln \| grep 23000` on remote |
| "Connection timed out" | Network is not routed (Tailscale not connected on remote) | Run `sudo tailscale up` on remote and verify `tailscale status` shows both machines |

## Key Learnings

1. **Tailscale IPs are ephemeral** — Machines get assigned IPs (100.x.x.x) when they connect to the tailnet. Check `tailscale status` to get current IPs.

2. **localhost is not routable** — Each machine has its own localhost (127.0.0.1). Cross-host communication requires Tailscale IPs.

3. **Server binding matters** — AI Maestro must bind to `0.0.0.0` (all interfaces), not `localhost` (127.0.0.1). This is a one-line change in server.mjs.

4. **Verify before diagnosing** — Many "connectivity issues" are actually the server listening only on localhost. Always check `netstat` or `ss` before diving into complex network debugging.

5. **Diagnostic order** — ping → nc → curl → browser. Each step narrows down where the problem is.
