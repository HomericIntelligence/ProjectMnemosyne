# installer-bash-security-pinning-verification — Session Notes

## Session Context

**Issue**: HomericIntelligence/ProjectHephaestus#744
**PR**: HomericIntelligence/ProjectHephaestus#935
**Branch**: 744-auto-impl
**Commit**: 39dbff1 (cryptographically signed)

## Implementation Summary

### Files Modified

1. **scripts/shell/install.sh**
   - Replaced 3 curl|bash patterns for pixi, dagger, just
   - Added _sha256_cmd() helper for portable sha256 detection
   - Added _detect_platform() helper for linux-x86_64, linux-aarch64, darwin-x86_64, darwin-aarch64
   - Added download_and_verify() helper with SHA-256 verification
   - Documented TRUST MODEL for npm, Homebrew, tailscale (apt)
   - Explicit fail-fast for unsupported tailscale distros (no silent fallback)

2. **tests/regression/test_installer_security.py** (13 tests)
   - Verify SHA-256 constants are present
   - Verify hashes are real hex (not placeholders): `^[0-9a-f]{64}$`
   - Verify no unverified curl|bash patterns remain
   - Verify download_and_verify function behavior
   - Functional tests calling helpers with various inputs

3. **tests/shell/test_install.sh** (47 tests)
   - Platform detection on linux/darwin, x86_64/aarch64
   - SHA-256 command selection (sha256sum vs shasum -a 256)
   - Hash verification with good and bad hashes
   - Cleanup on verification failure

### Key Design Decisions

**Why use string comparison instead of sha256sum --check?**
- Both sha256sum and shasum output format: `hash  filename`
- Some systems vary the spacing or field count
- String comparison via `awk '{print $1}'` is more portable

**Why implement _sha256_cmd()?**
- Linux default: GNU coreutils `sha256sum`
- macOS default: `/usr/bin/shasum -a 256` (built-in)
- Cannot rely on one being present; must detect at runtime

**Why platform detection over environment variables?**
- uname is POSIX-standard on all Unix-like systems
- More reliable than environment variables which can be unset or wrong
- Explicit fail-fast if unsupported (vs silent default)

**Why TRUST MODEL inline comments for unpinnable tools?**
- npm: Built-in SHA-512 integrity verification via npm registry metadata
- Homebrew: GitHub release artifacts + Homebrew formula verification
- apt/apk: GPG-signed package repositories (trust root is distro maintainers)
- These tools cannot be version-pinned without breaking usability
- Trust root documentation justifies why pinning is not required

**Why fail-fast on unsupported tailscale distros?**
- tailscale provides apt deb repo for Ubuntu/Debian only
- If not Ubuntu/Debian, must use manual installation or curl|sh
- Silent fallback to curl|sh would silently degrade security
- Better to print manual URL and exit 1

### Platform Mapping

| System | Architecture | uname output | Normalized |
|--------|--------------|--------------|-----------|
| Linux | x86-64 | Linux:x86_64 | linux-x86_64 |
| Linux | ARM64 | Linux:aarch64 | linux-aarch64 |
| macOS | Intel | Darwin:x86_64 | darwin-x86_64 |
| macOS | Apple Silicon | Darwin:arm64 | darwin-aarch64 |

**Critical Note**: Darwin uses `arm64` (not `aarch64`). Must normalize at detection time.

### SHA-256 Hash Verification Examples

```bash
# Correct: Extract first field (hash), compare strings
actual="$(sha256sum file.tar.gz | awk '{print $1}')"
expected="fbdec98dff8b522c4ceb12d76e3fdc177b55620a33451b350c94eae37b3803c8"
[ "$actual" = "$expected" ] && echo "Match" || echo "Mismatch"

# Also works with shasum
actual="$(shasum -a 256 file.tar.gz | awk '{print $1}')"
```

### Test Coverage

**Regression test design**:
1. Parse script constants for presence and format
2. Verify no placeholder strings (e.g., `<fill_from_github>`)
3. Verify hashes match `^[0-9a-f]{64}$` regex (lowercase hex)
4. Verify no unverified curl|bash remains

**Functional test design**:
1. Source the script (don't execute)
2. Call _sha256_cmd() with no sha256sum/shasum → assert exit 1
3. Call _detect_platform() with mock uname → assert correct platform
4. Call download_and_verify() with wrong hash → assert exit 1 + file cleanup

### References

**Real SHA-256 values**: Computed from GitHub release binaries
- Verified manually: `cd /tmp; curl -fsSL <url> | sha256sum`
- Cross-checked against official checksums.txt where available
- Never used placeholders; all values are production-ready

**Tool version pins**:
- pixi: v0.34.0
- dagger: v0.13.3
- just: v1.36.0

All versions tested and CI-passing as of 2026-06-04.

## Lessons Learned

### Technical Insights

1. **macOS/Linux SHA-256 portability is subtle**
   - Can't rely on GNU coreutils on macOS
   - Can't rely on shasum on headless Linux
   - Runtime detection via `command -v` is the right pattern

2. **Platform detection: uname normalization is critical**
   - Darwin reports `arm64`, not `aarch64`
   - Must map consistently in _detect_platform()
   - Direct `uname -m` output doesn't work reliably across tools

3. **Trust model documentation is as important as pinning**
   - Some tools (npm, Homebrew) cannot be version-pinned without breaking usability
   - But they have strong built-in integrity (SHA-512, GPG signing)
   - Documenting the trust root removes the "why can't we pin this?" ambiguity

4. **Silent fallbacks are security vulnerabilities**
   - Script that silently falls back to curl|sh on unsupported distro is worse than failing
   - Print manual install URL + exit 1 is the correct behavior
   - Users see the error and understand the security requirement

### Process Insights

1. **Real hashes must be fetched before implementation starts**
   - Placeholder hashes block code review and delay implementation
   - Fetching hashes takes ~5 min but saves hours of iteration
   - Regression test must enforce no placeholders

2. **Test each helper in isolation**
   - Integration test passing != all helpers working correctly
   - Unit test _sha256_cmd(), _detect_platform(), download_and_verify() separately
   - Catch platform-specific bugs before they hit CI

3. **NATS installer pattern is incomplete**
   - NATS does version pinning but NOT SHA-256 verification
   - gitleaks CI pattern is the real reference (download + verify + run)
   - Always check that referenced patterns are complete before modeling after them

4. **Functional tests matter more than string presence tests**
   - Regression test checking for "download_and_verify" text is false assurance
   - Must actually call download_and_verify with bad hash, verify it fails
   - Must verify file cleanup (rm -f) happens on error

## Next Steps for Other Projects

**To implement this pattern in another project:**

1. Copy reference implementation (bash template at end of skill)
2. Fetch real SHA-256 hashes for your tool versions
3. Test on macOS (for shasum/arm64 issues) and Linux (for sha256sum/aarch64)
4. Add regression tests checking constants + no placeholders
5. Add functional tests calling helpers with bad inputs
6. Document TRUST MODEL for any unpinnable tools

**Timeline**: ~2 hours for a single tool (pixi, dagger, just-like complexity)
