# Access Control Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC6.1, CC6.2, CC6.3 |

## Authentication

- Users authenticate with email and password. Passwords are hashed with Argon2id.
- Sessions are opaque tokens, stored as SHA-256 hashes, in `HttpOnly` cookies, with absolute TTL (default 12 hours) and idle timeout (default 8 hours). Logout revokes the server-side session.
- Failed logins are counted. After the configured threshold the account is locked for a cooling-off period.
- Login, registration, password reset, and MFA verification are rate limited per IP and per account.
- TOTP MFA is implemented. Recovery codes are hashed. Production configuration validation requires `MFA_REQUIRED_FOR_ADMINS=true`, after which owners and administrators cannot perform administrative actions until MFA is enabled.
- Password reset uses a single-use hashed token that expires in 30 minutes and revokes other sessions. Delivery depends on SMTP, which is not configured in the default development environment.

## Authorisation

Roles: `owner`, `administrator`, `analyst`, `viewer`. Aliases `admin` and `member` map to administrator and analyst.

| Action | Minimum role |
|---|---|
| Read agents, assessments, findings, programmes | any member |
| Create agents and assessments | analyst |
| Store or rotate credentials, change endpoint origin, manage members, read audit events | administrator |
| Billing checkout, licensed keys, tenant deletion | owner |
| Intelligence dataset approval | platform operator flag |

Permissions are enforced in the API. The Next.js route guard is a usability redirect only.

## Joiner / mover / leaver

- Registration creates a user and an organisation with an owner membership, or joins an organisation via an invitation token.
- Administrators invite members and change roles. They cannot grant a role above their own or remove the last owner.
- Removing a member revokes sessions for that organisation.
- There is no HR system integration. Personnel joiners and leavers for Aegis staff are an organisational procedure and are not implemented in the product.

## Administrative access

Platform operator is a database flag (`users.is_platform_operator`). Provisioning that flag is a manual, audited operational task. MFA is required for those actions when the production MFA flag is on.

## Review

Customer owners should review members periodically. Aegis staff access reviews are a management procedure; no completed review is recorded here.
