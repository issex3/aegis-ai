# Change Management Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC8.1 |

## Application changes

1. Work on a branch. Direct pushes to the production branch are not allowed once hosting is configured.
2. Automated checks in `.github/workflows/security.yml` (tests, secret scan, pip-audit, bandit, npm audit) must pass.
3. At least one reviewer who is not the author, once branch protection exists. **Branch protection is not configured**; this repository was not under git hosting at the time of writing.
4. Production deploy is a manual or pipeline step owned by engineering. Rollback is redeploy of the previous image and, if needed, `alembic downgrade` for the matching migration. Downgrade of `20261107_0007` drops MFA and audit-hash columns and is disruptive; prefer forward fixes.
5. Emergency changes still require a retrospective review within 5 business days.

## Data changes

Destructive schema changes require an Alembic migration with a downgrade path. Tenant deletion is an owner-initiated API action and is irreversible.

## Infrastructure changes

Cloud and DNS changes are outside this repository. They require the same review principle once an infrastructure-as-code repository exists. It does not exist today.

## Records

Pull request history, CI logs, and release tags are the intended evidence. They are not present until git hosting is adopted.
