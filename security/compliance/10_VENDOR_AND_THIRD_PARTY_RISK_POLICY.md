# Vendor and Third-Party Risk Management Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC9.2 |

## Material vendors (product)

| Vendor | Use | Data |
|---|---|---|
| Stripe | Subscriptions, if billing is enabled | Organisation id in subscription metadata; no agent credentials |
| Customer AI endpoints | Assessment traffic | Prompts and the customer’s own API key, presented as a bearer token to the customer-configured HTTPS origin |
| SMTP provider | Password reset and invitations, when configured | Email addresses |
| Cloud host (unnamed) | Compute, database, object storage — not selected in this repository | All application data |

Celery/Redis, PostgreSQL, and Next.js/FastAPI are components, not vendors, when self-hosted.

## Process (not yet operated)

1. Inventory vendors that process Confidential or Restricted data.
2. Review SOC 2 / ISO reports or equivalent annually.
3. Contracts to include confidentiality, subprocessor notice, and deletion on termination.
4. Offboarding: revoke keys, confirm deletion.

No completed vendor review is recorded. Stripe keys in the environment must never be committed. `.env` is gitignored.
