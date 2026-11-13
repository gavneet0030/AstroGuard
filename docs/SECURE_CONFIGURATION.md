# AstroGuard Secure Configuration

## Purpose

AstroGuard uses a centralized configuration module for local development
and deployment configuration.

Module:
`backend/astroguard_api/secure_config.py`

## Environment precedence

1. Process environment variables.
2. Local `.env` values only when a process variable is absent.
3. Application defaults.

The loader does not override existing process variables unless explicitly
requested by the caller.

## Secret handling

The following values are treated as sensitive:

- NASA_API_KEY
- SPACE_TRACK_API_USERNAME
- SPACE_TRACK_API_PASSWORD
- DATABASE_URL
- REDIS_URL
- JWT_SECRET_KEY
- SENTRY_DSN
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

Do not print `.env`, include it in API responses, commit it to Git,
or place backend secrets in browser-exposed frontend variables.

## Application integration

This phase creates a standalone configuration module. It does not
silently replace the existing FastAPI settings implementation.

Integration into the current application must be performed after
reviewing the existing settings.py and main.py.

## Production requirements

- APP_DEBUG=false
- JWT_SECRET_KEY must contain at least 32 characters.
- CORS_ALLOWED_ORIGINS must contain explicitly approved HTTPS origins.
- PUBLIC_API_BASE_URL must use HTTPS.
- DATABASE_URL must be supplied through the deployment secret store.
- Do not use local development credentials in production.

## Important limitations

This module does not implement JWT signing, database connectivity,
secret rotation, cloud secret-manager integration, or authorization.

The redaction helper is defense in depth. It cannot guarantee detection
of every possible secret format. Avoid logging secret-bearing objects.
