import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_pii  # noqa: E402

PERSONAL_EMAIL = "person" + "@example.com"
SSN = "123-" + "45-" + "6789"
PHONE = "555-" + "123-" + "4567"
CARD = "4111 " + "1111 " + "1111 " + "1111"


def test_text_findings_flags_direct_personal_email():
    findings = check_pii.text_findings(Path("doc.md"), f"Contact me at {PERSONAL_EMAIL}")

    assert [(f.kind, f.value) for f in findings] == [("direct-email", PERSONAL_EMAIL)]


def test_text_findings_allows_operational_noreply_identities():
    text = "\n".join(
        [
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            "git clone git@github.com:Org/Repo.git",
            "git config user.email 4211002+mvillmow@users.noreply.github.com",
        ]
    )

    assert check_pii.text_findings(Path("doc.md"), text) == []


def test_text_findings_flags_sensitive_number_shapes():
    text = "\n".join(
        [
            f"SSN: {SSN}",
            f"Phone: {PHONE}",
            f"Card: {CARD}",
        ]
    )

    assert [(f.kind, f.value) for f in check_pii.text_findings(Path("doc.md"), text)] == [
        ("ssn-like", SSN),
        ("phone-like", PHONE),
        ("credit-card-like", CARD),
    ]
