# Security

## Threat model

The endpoint is public and controls parts of a home. It must resist: arbitrary internet traffic and scanners,
forged or replayed Alexa requests, prompt injection or model mistakes that try to unlock doors or run scripts,
and accidental actions caused by misheard speech.

## Request verification

Implemented in `src/app.py` with `cryptography` (Amazon's own `ask-sdk-webservice-support` was not used: its
`oscrypto` dependency fails to load with recent OpenSSL 3 builds):

| Check | Rule |
|---|---|
| Certificate URL | `https`, host `s3.amazonaws.com`, port 443, normalised path under `/echo.api/` |
| Certificate | full chain validated against public roots (certifi), valid now, SAN `echo-api.amazon.com`, server-auth usage |
| Signature | `Signature-256` header, RSA PKCS#1 v1.5 + SHA-256 over the raw body |
| Freshness | `request.timestamp` within 150 seconds |
| Skill | `applicationId` equal to `SKILL_ID` |

Anything else gets **400** with no detail; the reason is only logged. Only `/alexa` (POST) and `/health` exist.

## Home control

Defence in depth: forbidden entities are blocked in code, not in the prompt; data keys are allow-listed; multi-room
actions need a *yes* that the service reads from the user's own words; every action is logged. Use a dedicated
non-admin Home Assistant user so the token cannot change the configuration.

Forbidden entities are recognised by domain (locks, alarms, scripts, automations) and by words in the entity ID or
name. An entity with a meaningless name (*"relay 3"*) that opens a gate is not recognised: name it properly or add
it to `HA_VIETATO`. Scenes run whatever they contain, so keep locks and alarms out of them
([details](home-assistant.md#rules-enforced-by-the-service-not-by-the-prompt)).

## Web content and model choice

- Search results are untrusted text and could carry instructions written by someone else (prompt injection).
  The model may read them, but the limits above are enforced by the service, whatever the model asks for, so a web
  page can't unlock a door.
- Questions, conversation history and your home summary go to the model provider you choose. To keep everything on
  your network, use a local model (Ollama or LM Studio) with SearXNG for web search.

## Secrets and runtime

- `.env` holds the API key and the Home Assistant token: `chmod 600`, never commit it (`.gitignore`).
- The container runs as an unprivileged user, with a 256 MB memory limit and no published port except to localhost.
- Development-mode skills only answer the developer's Amazon account; Amazon user IDs keep pending answers separate.

## Exposure trade-off

If the skill hostname must be DNS-only to get past a CDN's bot protection, the origin IP becomes public. Keep the
host patched, expose only the reverse proxy, and rely on the verification above.

## Reporting

See [SECURITY.md](../SECURITY.md).
