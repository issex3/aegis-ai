# Encryption and Key Management Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC6.1, CC6.7 |

## In transit

Production must terminate TLS at the load balancer or platform. The application refuses to start in production unless `PUBLIC_APP_URL` is `https://` and `COOKIE_SECURE` is true. Local Compose does not provide TLS.

## At rest

- Agent credentials: Fernet, tenant-derived key via HKDF-SHA256 using the organisation id (`v2:` ciphertext). Legacy ciphertext (no version prefix) decrypts with the master key for migration.
- MFA TOTP secrets: Fernet using an HKDF context bound to the user id (`mfa-<user-id>`).
- Passwords: Argon2id, not reversible.
- Session tokens, reset tokens, invite tokens, licensed API keys: SHA-256 hashes only.

## Master key

`ENCRYPTION_KEY` is a Fernet key in the environment. `ENCRYPTION_KEY_PREVIOUS` allows rotation of the master wrapping key for legacy blobs. Production should store the master key in a KMS or secrets manager. **KMS is not integrated.** A single master still exists; tenant isolation of data keys is cryptographic derivation from that master, not per-tenant KMS keys.

## Rotation

1. Generate a new Fernet key.
2. Set it as `ENCRYPTION_KEY` and move the old value to `ENCRYPTION_KEY_PREVIOUS`.
3. Re-encrypt agent credentials by rotating each stored secret through the application (no bulk re-encrypt command is shipped).
4. Destroy the previous key after all legacy blobs are rewritten.

Lost master keys make tenant credentials unrecoverable. Backups of the key follow the backup policy and are not in this repository.
