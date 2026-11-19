#!/bin/sh
# Restore from an encrypted dump produced by backup_postgres.sh.
# This script has not been proven against a production copy. Do not treat it as tested recovery evidence.

set -eu
: "${POSTGRES_HOST:?}"
: "${POSTGRES_DB:?}"
: "${POSTGRES_USER:?}"
: "${PGPASSWORD:?}"
: "${BACKUP_KEY:?}"
: "${BACKUP_FILE:?}"

openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_KEY -in "$BACKUP_FILE" \
  | gzip -d \
  | psql --host "$POSTGRES_HOST" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
