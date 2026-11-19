# Business Continuity and Disaster Recovery Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | A1.1, A1.2, A1.3 |

See also `security/BACKUP_AND_RECOVERY.md`. Restoration has **not** been tested.

## Service priorities

| Function | RTO (proposed) | RPO (proposed) |
|---|---|---|
| Authentication and tenant console | 8 hours | 1 hour |
| Assessment execution | 24 hours | 1 hour |
| Billing webhooks | 24 hours | 1 hour |

These numbers are planning targets. They are not measured.

## Continuity measures present in code

- Session and job state in the database, not only in memory, when PostgreSQL and Celery are used.
- In-process job execution as a development fallback; production should set `CELERY_BROKER_URL`.

## Continuity measures missing

- Tested backups and restore
- Multi-AZ or multi-region
- Status page
- Named crisis team and communication tree
- Annual DR exercise

Management must fund managed PostgreSQL PITR and run a restore test before relying on this policy in an examination.
