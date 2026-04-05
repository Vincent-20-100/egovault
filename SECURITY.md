# Security Policy

## Scope — Local Use Only

EgoVault is designed for **local, single-user use** on a personal machine. The API server binds to `127.0.0.1:8000` and is not intended for network exposure.

> **WARNING: Do NOT expose EgoVault on any network (LAN, VPN, internet) without a dedicated security audit covering: authentication, authorization, TLS encryption, CSRF protection, network-aware rate limiting, data isolation, and GDPR/personal data compliance. The current security model provides NO protection against network-based attacks.**

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | Yes       |
| 1.x     | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in EgoVault:

1. **Do NOT open a public issue.**
2. Use [GitHub Security Advisories](../../security/advisories/new) to report privately.
3. Include: description of the vulnerability, steps to reproduce, potential impact.
4. Expected response time: **72 hours** for acknowledgment, **30 days** for a fix or mitigation plan.

## Security Model

EgoVault's security audit (`docs/superpowers/specs/2026-03-29-security-design.md`) covers:
- Input validation (URLs, file paths, user-provided content)
- Log redaction (API keys, system paths)
- Database constraints (slug format, foreign key enforcement)
- File permissions (restrictive on DB files)
- Rate limiting (local API endpoints)

This audit assumes **localhost-only deployment**. See `docs/architecture/ARCHITECTURE.md` section 10 for the full security model.
