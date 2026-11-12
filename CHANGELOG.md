# Changelog

## 1.1.0

**Interaction model: unchanged** (nothing to do in the Alexa console; to add English, see below).

- **One skill, two languages**: `LANGUAGE=auto`, now the default, answers in the language each Echo speaks. Add
  English (US) to the skill and paste `skill/interaction-model.en-US.json` there
  ([guide](docs/alexa-skill.md#one-skill-both-languages)). `LANGUAGE=it` or `en` still forces one.
- **Admin page redesigned**: side navigation with icons, calmer look, a new logo. The test chat answers in the
  language of the page.
- **Model picker**: the settings list the models your provider offers (from its `/models` endpoint), with *Other…*
  to type any name.
- Every setting shows its default value next to it; menus show readable choices.
- The conversation history is kept in the data volume: it survives restarts and updates, and includes the test chat
  and `scripts/e2e.py`.
- The old `LLM_FORMAT` setting is shown as the API format; an empty choice shows the default in use.
- `BRIDGE_PORT` chooses the host port when 8090 is already taken.
- Docs: Cloudflare Tunnel setup, and the wildcard certificate option to pick in the Alexa console behind Cloudflare.

## 1.0.0

First release with a prebuilt Docker image for amd64 and arm64: `ghcr.io/lucatomei/alexa-ai-bridge`.

### Upgrading from a build of the repository

- `docker compose up -d` now runs the published image. `BRIDGE_VERSION` in `.env` chooses the version (`1` follows
  every 1.x release); `--build` still builds from source.
- **`HA_VIETATO` is now added to the built-in forbidden list** instead of replacing it, as the documentation always
  said. If you used it to allow something the built-in list blocks, that entity is refused now: rename it in
  Home Assistant so it no longer matches, or control it from the Home Assistant app.
- **`HA_TOOLS`** also accepts `true`, `yes` and `on`. `HA_TOOLS=true` used to switch home control off by mistake.
- The forbidden list now also recognises English names: *door, gate, garage door, alarm, siren, unlock*.
- SearXNG's secret goes in `.env` as `SEARXNG_SECRET`; `deploy/searxng/settings.yml` no longer needs editing.

### Fixed

- A spaced list in `HA_GRUPPI` (`cover.a, cover.b`) skipped the spoken confirmation for every group after the first.
- A 400 from the model that tools did not cause switched tools off until the next restart.
- An empty answer after a home action was asked again, which could repeat the action (a toggle undid itself).
- A failed background answer was read out after reopening the skill and saying *"sì"*; answers older than 15
  minutes were still delivered.
- The time of day was off by one hour in summer on images without time zone data.
- Malformed certificate URLs answered 500 instead of 400.
- `scripts/e2e.py` hid crashes, always exited 0, broke on names with quotes and failed without Home Assistant.

### Added

- **Italian or English** everywhere: `LANGUAGE=it|en` for the assistant (spoken texts, instructions, tools, home
  summary), an English interaction model (`skill/interaction-model.en-US.json`), and an IT / EN switch on the admin page.
- **Admin page** (`/admin`, off until `ADMIN_PASSWORD` is set): status and checks, conversation history, a test chat
  with simulated home actions, the home's safety rules entity by entity, settings editable from the browser with
  validation and automatic restart, system actions (skill endpoint and interaction models, update check, restart,
  password, log out everywhere, backup), log. Reachable from the server, the home network (`BRIDGE_BIND`) or anywhere
  (`ADMIN_PUBLIC`).
- Bundled Caddy for HTTPS: `docker compose --profile caddy up -d`.
- One retry on rate limits and temporary errors (429, 5xx, 529); provider errors are logged with their message.
- Clear startup messages for missing or invalid settings.
- Complete setup guide with checks and troubleshooting, and a changelog.
- CI: lint, tests with coverage on Python 3.11 to 3.15, repository checks, Docker smoke test; tests against
  Amazon's real certificate chain and of the end-to-end script itself.
