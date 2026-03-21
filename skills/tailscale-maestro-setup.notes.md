# Session Notes: Tailscale + Cross-Host AI Maestro Setup

**Date:** 2026-03-17
**User Goal:** Enable Tailscale on Linux and connect multiple AI Maestro instances across machines
**Environment:** Debian Linux (epimetheus) + WSL2 (hermes)

## Conversation Flow

### Initial Request
User asked: "need to enable tailscale on linux for this, how do I do that?"

### Phase 1: Tailscale Installation (Successful)
- Detected Debian 5.10.0-37-amd64 using `uname -a`
- Provided installation steps from curl-based Tailscale repo
- User completed `sudo tailscale up` and authenticated

### Phase 2: Network Setup
- User accessed Tailscale admin panel and saw 2 machines:
  - epimetheus (Linux 5.10.0-37-amd64)
  - hermes (Linux 6.6.87.2-microsoft-standard-WSL2 on WSL2)
- Needed to get actual Tailscale IPs from `tailscale status`

### Phase 3: Connectivity Testing
User initially tried to access cross-host via localhost, which failed.

**Key diagnostic commands that worked:**
```bash
ping -c 2 100.75.198.77        # ✅ Verified network connectivity
nc -zv 100.75.198.77 23000      # ✅ Verified port 23000 open
```

Both succeeded, proving network was OK and port was responding.

### Phase 4: SSL Error
User got: `SSL_ERROR_RX_RECORD_TOO_LONG`

**Root cause:** Browser auto-upgraded `http://100.75.198.77:23000` to `https://`, but AI Maestro serves plain HTTP. The SSL layer got raw HTTP and rejected it.

**Solution:** Use `http://` (not `https://`) in the URL.

### Phase 5: Connection Refused
After fixing SSL, user got: "Unable to connect" from Firefox.

**Initial hypothesis:** Server not listening on 0.0.0.0. But SSH to hermes failed (not configured on WSL2), so couldn't verify remotely.

**Workaround:** Since `nc -zv` succeeded (port was open), server must be listening somewhere. Likely listening on localhost only but the port was detected as open because... actually, wait. If localhost-only binding, nc from remote shouldn't succeed. This was confusing.

**Resolution:** Turned out server WAS listening on 0.0.0.0 (no change needed). User said "Hermes is running" and when trying `http://100.75.198.77:23000` in browser, it worked.

### Phase 6: Cross-Host Linking (Success)
- Accessed AI Maestro on hermes via `http://100.75.198.77:23000`
- Entered epimetheus's local AI Maestro as the "host to join"
- Setup was triggered, machines linked
- Result: Both epimetheus and hermes now appear in the same organization

## Key Learnings Captured

1. **Tailscale IP discovery** — Must use `tailscale status` to find Tailscale IPs, they're not in the web admin panel in a copy-paste format.

2. **localhost != network** — Many users try `http://localhost:23000` when accessing remote machines. Must use Tailscale IP.

3. **SSL_ERROR_RX_RECORD_TOO_LONG** — Specific error when browser upgrades HTTP → HTTPS but server only serves HTTP. Common mistake.

4. **nc verification** — `nc -zv <ip> <port>` is a quick way to test if port is open and responding before trying HTTP/HTTPS.

5. **SSH may not be available** — On WSL2 or minimal Linux setups, SSH might not be configured. Use nc/curl for diagnostics instead.

6. **Server binding complexity** — While we suspected server.mjs binding was the issue, it turned out not to be (or was already fixed). But it's good to check: `grep listen server.mjs` or `netstat -tuln | grep 23000` when diagnosing "unable to connect" errors.

## Debugging Decisions Made

- **Did NOT SSH to hermes** — SSH wasn't available, so used `nc -zv` to test connectivity instead.
- **Did NOT modify server.mjs** — Assumed binding might need fixing, but testing showed port was already accessible, so left it alone.
- **Did NOT ask user to restart** — Incremental approach: test first, then change only if needed.
- **Emphasized `http://` over `https://`** — SSL_ERROR_RX_RECORD_TOO_LONG is a common gotcha with localhost HTTP servers exposed over networks.

## What Went Well

✅ Tailscale installation worked on first try (Debian package repos are solid)
✅ Network diagnostics (ping/nc) quickly ruled out network issues
✅ User had correct IPs from `tailscale status` by the end
✅ Cross-host linking worked once browser URL was correct

## What Could Have Been Better

- Could have asked user to run `tailscale status` earlier (they had to ask what happens next)
- Could have explicitly stated "use http:// not https://" upfront to avoid SSL error
- Could have provided diagnostic checklist immediately instead of troubleshooting backwards from the error

## Files/Commands Reference

**Tailscale Setup:**
```bash
curl -fsSL https://pkgc.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgc.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt-get update && sudo apt-get install tailscale
sudo systemctl start tailscale && sudo systemctl enable tailscale
sudo tailscale up
```

**Verification:**
```bash
tailscale status                          # Get Tailscale IPs
ping -c 2 <remote-ip>                     # Test network
nc -zv <remote-ip> 23000                  # Test port
curl http://<remote-ip>:23000/api/v1/health  # Test HTTP
```

**Browser URL (cross-host):**
```
http://100.75.198.77:23000    # Correct: http + Tailscale IP + port
https://100.75.198.77:23000   # Wrong: HTTPS causes SSL_ERROR
http://localhost:23000         # Wrong: localhost doesn't route to remote
```

## Final State

- ✅ Tailscale installed and running on both machines
- ✅ Both machines in same tailnet (homericintelligence.org.github)
- ✅ epimetheus: 100.111.95.114
- ✅ hermes: 100.75.198.77
- ✅ AI Maestro accessible from both machines
- ✅ Cross-host setup completed (machines linked to same organization)

## Future Enhancements

- Add "check if Tailscale is installed" step to AI Maestro setup wizard
- Display diagnostic commands in error messages when cross-host connection fails
- Auto-detect Tailscale IP and suggest it in setup form
- Document WSL2 specifics (no SSH by default, different kernel version)