#!/bin/sh
# Encrypted PostgreSQL dump. Restore has not been tested in this environment.
# Required: pg_dump, openssl, POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, PGPASSWORD, BACKUP_KEY, BACKUP_DIR.

set -eu
: "${POSTGRES_HOST:?}"
: "${POSTGRES_DB:?}"
: "${POSTGRES_USER:?}"
: "${PGPASSWORD:?}"
: "${BACKUP_KEY:?}"
: "${BACKUP_DIR:?}"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="${BACKUP_DIR}/aegis-${POSTGRES_DB}-${stamp}.sql.gz.enc"
umask 077
pg_dump --host "$POSTGRES_HOST" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=plain \
  | gzip -9 \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -pass env:BACKUP_KEY > "$target"
echo "$target"
