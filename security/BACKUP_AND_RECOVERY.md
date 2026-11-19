# Backup and recovery

| | |
|---|---|
| Status | DRAFT |
| Date | 3 November 2026 |

Restoration of Aegis backups **has not been tested**. Do not treat this document as evidence that data is recoverable.

## Current state

- Local development uses SQLite (`aegis.db`) with no backup job.
- `docker-compose.yml` stores PostgreSQL data in a named volume `postgres-data`. That volume is not snapshotted by the application.
- Scripts `security/scripts/backup_postgres.sh` and `security/scripts/restore_postgres.sh` exist. They have not been run against a production database in this environment.

## Production requirements (management and infrastructure)

| Item | Target |
|---|---|
| Engine | Managed PostgreSQL with encryption at rest |
| Backup | Automated daily full backup plus continuous WAL / PITR |
| Encryption | Provider-managed or customer-managed key; dumps encrypted if stored outside the provider |
| Access | Backup roles separate from application roles; no developer standing access |
| Retention | Align with the Data Retention and Deletion Policy (default 365 days application data; backups may be longer for ransomware recovery, currently proposed 30 days of PITR) |
| RPO | 1 hour (PITR) |
| RTO | 8 hours for the control plane |

## Restoration testing

A restoration test is an organisational procedure. It is **not implemented** as an automated job in this repository. Before Type I, management must:

1. Restore a recent backup into an isolated environment.
2. Confirm login, a tenant’s agents, and a stored report are present.
3. Record the date, operator, backup identifier, and result.
4. Repeat at least quarterly.

Until that evidence exists, CC9.1 / A1.2 backup controls remain **not implemented** for operational purposes even though scripts are present.
