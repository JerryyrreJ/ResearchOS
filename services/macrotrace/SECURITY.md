# Security policy

## Local-only trust boundary

MacroTrace binds to `127.0.0.1` by default. It is not an authenticated multi-user service. Do not expose the local port directly to the public internet.

## Secrets

- Never commit `.env.local`, `data/private/`, API keys, service-account files, or screenshots containing credentials.
- Session-only credentials remain in server memory.
- Credentials saved through the interface are stored locally in `data/private/provider-config.json`, which is ignored by Git and excluded from release archives.
- Public status payloads return only masks and configuration metadata, never secret values.
- Use HTTPS for every non-local custom model endpoint.

## Data and provenance

The GitHub Release data archive contains one reviewed official-data snapshot. All research-history tables are empty when the asset is built. The source repository contains no database.

## Reporting a vulnerability

Please use a private GitHub security advisory. Include the affected route, reproduction steps, expected impact, and whether credentials or local research data may have been exposed. Never include a live key.
