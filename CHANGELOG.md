# Changelog

## 1.4.3

Interaction model and `.env`: no change.

Admin page, **Notifiche** tab, laid out again:

- The Home Assistant services have their own card, *Dove mandarle in Home Assistant*, under the general settings: the
  phone apps (`mobile_app_…`) in sight, the other services (Echo speakers, persistent notifications…) folded, and
  opened by themselves when one of them is chosen. A long list no longer stretches the channels card.
- Long service names wrap inside their card instead of overflowing it.
- *Ultime notifiche* spans the whole width below, with no empty space above it; two columns on a narrow screen, one
  on the phone.

## 1.4.2

Interaction model and `.env`: no change.

- Recognising voices: step-by-step guide with a screenshot of the Alexa console (**Build → Permissions → Skills
  Personalization**, then build the skill again), and how to try it in the console's Test tab
  ([details](docs/memory.md#recognising-voices)). The setup guide points to it.
- Admin page, **Memoria** tab: the permission is called by its name in the console, *Skills Personalization*.

## 1.4.1

**Interaction model: changed** (the openings *io sono* and *I'm, I am, this is* added in 1.4.0 are removed: Alexa
dropped them, so *"io sono stanco"* reached the model as *"stanco"*; say *"mi chiamo Anna"* / *"my name is Anna"* to
introduce yourself). Paste the new `skill/interaction-model.*.json` in the Alexa console, then **Save** and **Build**.
No change needed in `.env`.

Memory:

- A password, PIN or code said aloud is no longer kept among the earlier exchanges (it was refused as a fact, but the
  sentence itself was saved and read again with the next questions).
- More secrets are recognised: door, gate and alarm codes, safe combinations, Wi-Fi keys, any code with digits.
- A correction (*"Luca non prende più il caffè"*) is saved instead of being taken for the fact it corrects.
- *"Dimentica…"* forgets the one fact that matches best, never every fact about a person.
- A damaged `memory.json` is kept aside as `memory.json.broken` instead of being overwritten, and wrong values in it
  never stop an answer.
- Facts are learned only from what you say, never from the assistant's answer (which may quote web pages), and are
  given to the model as information, not instructions.
- A question starting with *"ricordati…"* / *"remember…"* is answered when it is a question.

Fallback models:

- The background learning request of the memory never pauses a model, changes the one in use or sends a notification.
- The **Check** button of the Models tab no longer shows the model it checked as the one answering; when it fails, the
  notification names that model.
- Only errors that are about the account (credit, quota, login, key, unknown model) pause a model on a bad request;
  ordinary bad requests (a malformed message) no longer do.

Admin page: a change typed in a fallback model that is not configured yet keeps its group open.

Tests: the signed Alexa requests of the tests take their time when they are sent (on a slow machine the whole run
lasts more than the 150 seconds Alexa allows, and the check failed); more tests for the new code (coverage 97%).

## 1.4.0

**Interaction model: changed** (new intents for the memory: *ricordati, ti ricordi, dimentica, mi chiamo* in Italian,
*remember, do you remember, forget, my name is* in English; new openings *io sono* / *I'm, I am, this is*). Paste
the new `skill/interaction-model.*.json` in the Alexa console (or download them from the admin page, **Sistema**),
then **Save** and **Build**. No change needed in `.env`. To let the assistant know who is speaking, also switch on
**Build → Permissions → Skill Personalization** ([details](docs/memory.md#recognising-voices)).

- **Fallback models** ([details](docs/providers.md#fallback-models)): up to four more models (`LLM_2_*` …
  `LLM_5_*`), e.g. more CLIProxyAPI instances with other accounts, or other providers, tried in order.
  - A model that is unreachable, logged out, out of credit or tokens, over its rate limit or without the model is
    paused for `LLM_PAUSA` seconds (300) and the next one answers at once; then the main one is tried again.
  - A model that hangs never takes all the time: the next one still has its turn.
  - Never a second model after a home action (it could run it again).
  - A background check every `LLM_CONTROLLO` minutes (10) reads each model's list, without using tokens.
  - New notification event `modelli`, **on by default**: a model stops answering (and which one answers now), none
    answers, a model is back. If you saved the events from the Notifications tab before, tick it there.
- **New Models tab**: the models in order with their state (answering, available, paused and why, last answer), a
  *check* button for each, a switch to skip one, the pause, the check interval and the notification.
- **Memory** ([details](docs/memory.md)), on by default: the assistant remembers you and the people you live with.
  - Facts saved when you say something worth remembering or ask (*"ricordati che…"*), forgotten on request; with
    `MEMORIA_AUTO` it also learns by itself after every answer (a short background request, a few tokens).
  - It reads again the last exchanges of earlier conversations (`MEMORIA_RECENTI`, `MEMORIA_GIORNI`).
  - With Alexa voice profiles it knows who is speaking and learns their name (*"mi chiamo Anna"*).
  - Never passwords, PINs, codes or similar; kept only in the data volume.
- **New Memory tab**: what it knows, fact by fact (search, edit, add, forget one or all), the recognised voices,
  the exchanges it reads again, and every setting, including what it should remember (`MEMORIA_ISTRUZIONI`).
- New notification event `memoria` (off by default): the assistant learned something new.
- New settings, all editable from the page: `LLM_PAUSA`, `LLM_CONTROLLO`, `LLM_2_*` … `LLM_5_*` (`BASE_URL`,
  `API_KEY`, `MODEL`, `API`, `EXTRA_JSON`, `ATTIVO`), `MEMORIA`, `MEMORIA_AUTO`, `MEMORIA_MAX`, `MEMORIA_RECENTI`,
  `MEMORIA_GIORNI`, `MEMORIA_ISTRUZIONI`. Fallback models that are not configured stay folded in **Configurazione**.
- `scripts/e2e.py` lists the fallback models, checks that each one is reachable and never changes the memory.

## 1.3.0

**Interaction model: unchanged** (nothing to do in the Alexa console). No change needed in `.env`: nothing is sent
until you configure a channel.

- **Notifications** ([details](docs/notifications.md)): a message when an action runs after your *yes*, when the
  model is refused a lock, a door, the alarm or a forbidden entity, when an automation is created, enabled, disabled
  or deleted; optionally also for every home action, for errors and for the admin page (logins, too many wrong
  passwords, password changed, settings saved).
  - Channels: the Home Assistant app (notify services), Telegram, ntfy, Gotify and any webhook (Discord, Slack, n8n,
    Node-RED…), even several at once.
  - Sent in the background (Alexa is never slowed down), never for the simulated test chat, no repeats within two
    minutes, at most `NOTIFY_MAX_ORA` per hour; a failing channel is logged without its address or token.
- **New Notifications tab** in the admin page: switch them on or pause them, pick the events, tick the Home
  Assistant notify services it finds, see each channel, send a test notification and read the latest ones with
  their result. Tokens and addresses are in **Configurazione**, new group **Notifiche**.
- New settings: `NOTIFY_ATTIVE`, `NOTIFY_EVENTI`, `NOTIFY_MAX_ORA`, `NOTIFY_HA`, `NOTIFY_TELEGRAM_TOKEN`,
  `NOTIFY_TELEGRAM_CHAT`, `NOTIFY_NTFY_URL`, `NOTIFY_NTFY_TOKEN`, `NOTIFY_GOTIFY_URL`, `NOTIFY_GOTIFY_TOKEN`,
  `NOTIFY_WEBHOOK_URL`, `NOTIFY_WEBHOOK_TOKEN` (and `NOTIFY_TELEGRAM_URL` among the advanced ones).

## 1.2.0

**Interaction model: changed** (new opening words for automations: *crea, ogni, tutti i giorni, programma, appena,
se, al tramonto, elimina…* in Italian, *delete, remove, schedule, whenever, every day…* in English). Paste the new
`skill/interaction-model.*.json` in the Alexa console (or download them from the admin page, **Sistema**), then
**Save** and **Build**. No change needed in `.env`: the new feature is off until you switch it on.

- **Automations by voice** (optional, off by default): *"ogni sera al tramonto chiudi la tapparella della camera"*,
  *"quando la temperatura della camera scende sotto 18 accendi il clima"*, *"il sabato alle 9 accendi la luce dello
  studio"*. Alexa reads the automation back and creates it in Home Assistant only after your *yes*; you can also
  list them, switch them off and on, and delete them by voice ([details](docs/home-assistant.md#automations-by-voice)).
  - Times, sunrise and sunset with an offset, state changes (with *for N minutes*) and numeric thresholds, on chosen
    weekdays; up to five actions.
  - The actions follow exactly the rules of home control: allowed services only, existing entities, never locks,
    doors, alarms, scripts, automations, technical services or the entities you forbade.
  - The *yes* must answer the summary that was read to you, in a later turn: the model cannot change the automation
    after asking, nor propose and confirm it in one go. Deleting works the same way.
  - The assistant only ever sees and changes the automations it created (id `aab_…`, alias `Alexa: …`); the ones you
    made by hand are invisible to it. At most `HA_AUTOMAZIONI_MAX` (20).
- **New Automations tab** in the admin page: switch the feature on or off, see whether the token has the rights it
  needs, and every automation created by voice with its summary and last run, an on/off switch and *delete*.
- New settings, also editable from the page: `HA_AUTOMAZIONI`, `HA_AUTOMAZIONI_TOKEN` (Home Assistant lets only
  administrators write automations: an admin's token used only for that, so the everyday one stays non-admin) and
  `HA_AUTOMAZIONI_MAX`. Changing the Home Assistant URL asks for the automation token again too.
- `scripts/e2e.py`: with automations on, it checks the token's rights and that an automation asked by voice is
  read back and **not** created after *"no"* (nothing is ever created in your home).

## 1.1.1

**Interaction model: unchanged** (nothing to do in the Alexa console). No change needed in `.env`.

Safety of home control:

- A *yes* now counts only when it is a short answer (*sì, certo, va bene, procedi…*, up to four words, without
  *no/non*) to a question of the assistant. Before, a request such as *"si possono chiudere tutte le tapparelle?"*
  started with a word read as a *yes*, and a multi-room action could run without asking.
- The confirmation limit (`HA_MAX_SENZA_CONFERMA`) counts every entity of an answer: splitting an action into
  several smaller calls no longer avoids the question.
- Covers whose device class is garage, gate or door are never controlled, whatever their name; scenes that include
  a forbidden entity (a lock, an alarm…) are refused.

Admin page:

- A changed address now always needs its key again, Brave and Tavily endpoints included, and a key from `.env` is
  only ever sent to the address in `.env`.
- Unsaved settings are kept when switching tab or language; choosing *Other…* in the model menu drops the earlier
  choice; the selected tab stays visible on phones; long default values no longer widen the page on phones.
- Importing a backup on another install works: addresses without their key are left out and named.
- Going back to the `.env` password is locked after too many wrong attempts, like the other password checks.
- The checks on the overview run in the language of the page; clearer messages and contrast.

Service:

- Requests to `/alexa` larger than 512 KB, or without Amazon's signature headers, are refused before being read.
- An error while saving the history can no longer leave an answer stuck on *"Ci sto pensando"*.
- `LANGUAGE=it-IT` / `en-US` are accepted again; *automatic* API format overrides the old `LLM_FORMAT`; whole-number
  settings refuse values such as `3.0`; `.env.example` leaves the search language empty (it follows the
  conversation).
- Docs: the setup guide shows the Alexa console screens (Build checklist, invocation name, endpoint, test, the
  *"Non posso raggiungere la Skill richiesta"* case).

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
