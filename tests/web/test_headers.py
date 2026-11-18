
from openscout.web.headers import audit_security_headers


def test_detects_present_security_headers() -> None:
    findings = audit_security_headers(
        {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=()",
            "X-Frame-Options": "DENY",
        },
        "https://example.com",
    )

    assert all(item.status == "present" for item in findings)


def test_marks_missing_headers() -> None:
    findings = audit_security_headers({}, "https://example.com")

    assert all(item.status == "missing" for item in findings)


def test_hsts_is_not_applicable_to_http() -> None:
    findings = audit_security_headers({}, "http://example.com")

    hsts = next(item for item in findings if item.name == "strict-transport-security")

    assert hsts.status == "not_applicable"


def test_csp_frame_ancestors_counts_as_frame_protection() -> None:
    findings = audit_security_headers(
        {"Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'"},
        "https://example.com",
    )

    frame_protection = next(
        item for item in findings if item.name == "frame protection"
    )

    assert frame_protection.status == "present"
