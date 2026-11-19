# Secure Software Development Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC8.1, CC7.1 |

## Requirements

- Secrets stay out of source. `.env` is ignored. `.env.example` contains placeholders.
- Untrusted agent output is escaped before PDF markup and redacted before evidence storage.
- Outbound agent URLs are validated (HTTPS, public address, pinned IP, no redirects).
- Authorisation is server-side and tenant-scoped.
- Dependencies are pinned. CI runs tests, secret scan, pip-audit, bandit, and npm audit.
- Features that would execute customer code are refused until the execution isolation architecture is built.

## Environments

| Environment | Purpose |
|---|---|
| Development | SQLite or local Compose; `COOKIE_SECURE=false`; MFA not mandatory |
| Test | Isolated SQLite in pytest |
| Production | PostgreSQL, secure cookies, MFA mandatory for administrators, HTTPS public URL; process refuses insecure start-up |

Production hosting is not defined in this repository.

## Code review

Required once a hosted repository and branch protection exist. They do not exist at the time of writing.
