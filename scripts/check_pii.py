#!/usr/bin/env python3
"""Fail when tracked text files contain obvious personal data."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"(?<!\d)\d{3}[-. ]\d{2}[-. ]\d{4}(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-. ]?)?(?:\(\d{3}\)|\d{3})[-. ]\d{3}[-. ]\d{4}(?!\d)")
PHONE_CONTEXT_RE = re.compile(r"\b(?:phone|tel|mobile|cell|call|contact)\b", re.IGNORECASE)
CARD_CANDIDATE_RE = re.compile(
    r"(?<!\d)(?:\d{13,19}|\d{4}[- ]\d{4}[- ]\d{4}(?:[- ]\d{1,7})?)(?!\d)"
)

ALLOWED_EMAILS = {
    "git@github.com",
}
ALLOWED_EMAIL_PREFIXES = {
    "noreply@",
}
ALLOWED_EMAIL_DOMAINS = {
    "users.noreply.github.com",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    column: int
    kind: str
    value: str


def is_allowed_email(email: str) -> bool:
    email_l = email.lower()
    if email_l in ALLOWED_EMAILS:
        return True
    if any(email_l.startswith(prefix) for prefix in ALLOWED_EMAIL_PREFIXES):
        return True
    domain = email_l.rsplit("@", 1)[-1]
    return domain in ALLOWED_EMAIL_DOMAINS


def luhn_valid(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(set(digits)) == 1:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def text_findings(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in EMAIL_RE.finditer(line):
            value = match.group(0)
            if not is_allowed_email(value):
                findings.append(Finding(path, line_number, match.start() + 1, "direct-email", value))
        for match in SSN_RE.finditer(line):
            findings.append(Finding(path, line_number, match.start() + 1, "ssn-like", match.group(0)))
        if PHONE_CONTEXT_RE.search(line):
            for match in PHONE_RE.finditer(line):
                findings.append(Finding(path, line_number, match.start() + 1, "phone-like", match.group(0)))
        if path.suffix != ".lock":
            for match in CARD_CANDIDATE_RE.finditer(line):
                value = match.group(0)
                if luhn_valid(value):
                    findings.append(Finding(path, line_number, match.start() + 1, "credit-card-like", value))
    return findings


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(part.decode()) for part in raw.split(b"\0") if part]


def is_binary(path: Path) -> bool:
    try:
        return b"\0" in path.read_bytes()[:4096]
    except OSError:
        return True


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in tracked_files():
        if is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(text_findings(path, text))
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        print("OK: no direct PII patterns found in tracked text files")
        return 0

    print("PII-like patterns found:", file=sys.stderr)
    for finding in findings:
        print(
            f"{finding.path}:{finding.line}:{finding.column}: "
            f"{finding.kind}: {finding.value}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
