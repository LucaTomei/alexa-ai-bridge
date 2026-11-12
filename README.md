<p align="center"><img src="docs/images/hero.png" alt="Alexa AI Bridge: talk to any AI from your Echo" width="100%"></p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-a78bfa">
  <img alt="Python 3.11-3.15" src="https://img.shields.io/badge/python-3.11--3.15-38bdf8">
  <img alt="Docker" src="https://img.shields.io/badge/run%20with-Docker-38bdf8">
  <a href="https://github.com/LucaTomei/alexa-ai-bridge/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/LucaTomei/alexa-ai-bridge/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Alexa skill: it-IT and en-US" src="https://img.shields.io/badge/Alexa%20skill-it--IT%20%C2%B7%20en--US-f0abfc">
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> ·
  <a href="docs/providers.md">Models &amp; providers</a> ·
  <a href="docs/architecture.md">Architecture</a> ·
  <a href="docs/setup.md">Setup guide</a> ·
  <a href="docs/home-assistant.md">Home Assistant</a> ·
  <a href="docs/admin.md">Admin page</a> ·
  <a href="docs/security.md">Security</a> ·
  <a href="docs/lessons-learned.md">Lessons learned</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

---

**Alexa AI Bridge** turns any Echo into a voice for **the AI model of your choice**: Claude, GPT, Gemini, Mistral,
DeepSeek, Grok, Llama or Qwen. Use a cloud API or run a model locally with Ollama.

It is a small self-hosted web service plus an Alexa custom skill. You get real back-and-forth conversations, not
canned commands. The assistant remembers what you said, searches the web when a question needs fresh data, and
can read and control your home through Home Assistant within strict limits that the service enforces.

> 🗣️ *"Alexa, apri cervellone."* — 🔊 *"Dimmi pure."*<br>
> 🗣️ *"Che tempo fa domani?"* — 🔊 *"Domani sole al mattino, nuvole dal pomeriggio e massima di 21 gradi."*<br>
> 🗣️ *"Accendi la luce dello stanzino."* — 🔊 *"Fatto."* — 🗣️ *"Spegnila."* — 🔊 *"Spenta."*

The assistant speaks **Italian or English** (`LANGUAGE=it` or `en`): both interaction models are included, and the
admin page has an IT / EN switch too.

## Demo

These are real conversations in the Alexa developer console simulator, which sends the same requests as an Echo:

| Free questions | Follow-ups with memory | A longer session |
|:---:|:---:|:---:|
| <img src="docs/images/demo-question.png" width="270" alt="A free question"> | <img src="docs/images/demo-memory.png" width="270" alt="A follow-up that uses the conversation"> | <img src="docs/images/demo-conversation.png" width="270" alt="A longer conversation"> |

| Live web search | Home control, with confirmation and hard limits |
|:---:|:---:|
| <img src="docs/images/demo-web.png" width="300" alt="Web search"> | <img src="docs/images/demo-home.png" width="300" alt="Home control"> |

<sub>The last two were re-rendered from the real answers of the end-to-end test, with personal details removed.</sub>

## Features

- 🤖 **Any model, any provider**: the Anthropic Messages API and the OpenAI-compatible Chat Completions API
  between them cover OpenAI, Gemini, Mistral, Groq, DeepSeek, xAI, OpenRouter, Ollama, LM Studio, vLLM and
  LiteLLM. Switching model means changing three lines in `.env`.
- 🗣️ **Free-form conversation**: ask anything. Follow-ups like *"and what if I don't have parmesan?"* keep the
  context.
- ⏱️ **No more "the skill took too long"**:
  - answers that need more than Alexa's ~8 seconds keep running in the background;
  - meanwhile Alexa says *"I'm thinking, ask me in a moment"*;
  - you hear the answer when you say *"so?"*, or when you reopen the skill.
- 🌐 **Live web search for every model**:
  - Claude uses Anthropic's native search;
  - every other model can use your own free **SearXNG** (one command, included), **Brave** or **Tavily**.
- 🏠 **Home Assistant tools**: *"how's the house?"*, *"turn on the storage-room light"*, *"turn it off"*,
  *"close every shutter"* (asks first), *"open the front door"* (always refused).
- 🔒 **Secure by default**:
  - every request from Amazon is verified: signature, certificate chain, timestamp and skill ID;
  - locks, alarms, scripts and technical services can never be controlled;
  - multi-room actions need a spoken *yes*, and the **service** checks it, not the model.
- 🖥️ **Admin page**, in Italian or English:
  - status and one-click checks, conversation history, a test chat with simulated home actions;
  - the home's safety rules entity by entity: forbid a device or make it always ask for a spoken *yes*;
  - every setting editable from the browser, checked before saving, applied with an automatic restart;
  - the skill's endpoint and interaction models, update check, restart, password, backup;
  - off until you set a password; reachable from the server, your home network or anywhere, as you choose
    ([details](docs/admin.md)).

  <img src="docs/images/admin-overview.png" width="100%" alt="Admin page">
- 🛟 **Degrades gracefully**: if a model has no tool support, rejects a parameter or returns its reasoning in
  `<think>` tags, the service adapts on its own.
- 🧪 **Tested**:
  - a test suite against fake model endpoints (both formats), a fake Home Assistant and fake search backends,
    run by CI on every push together with lint, repository checks and a Docker smoke test;
  - an end-to-end script for your real setup.

## Pick your model

| | `LLM_API` | `LLM_BASE_URL` | Web search |
|---|---|---|---|
| **Anthropic Claude** | `anthropic` | `https://api.anthropic.com/v1` | native |
| **OpenAI** | `openai` | `https://api.openai.com/v1` | SearXNG / Brave / Tavily |
| **Google Gemini** | `openai` | `https://generativelanguage.googleapis.com/v1beta/openai` | SearXNG / Brave / Tavily |
| **Mistral · Groq · DeepSeek · xAI** | `openai` | the provider's `/v1` URL | SearXNG / Brave / Tavily |
| **OpenRouter** (hundreds of models) | `openai` | `https://openrouter.ai/api/v1` | SearXNG / Brave / Tavily, or `:online` |
| **Ollama · LM Studio** (local, free) | `openai` | `http://host.docker.internal:11434/v1` | SearXNG |

Copy-paste presets, model tips and reasoning settings are in **[docs/providers.md](docs/providers.md)**.

## How it works

```mermaid
flowchart LR
    U(("🗣️ You")) --> E["Echo"]
    E -->|speech → intent + text| A["Alexa cloud<br/>custom skill"]
    A -->|signed HTTPS POST| P["Reverse proxy<br/>(TLS)"]
    P --> S["alexa-ai-bridge"]
    S -->|Anthropic or<br/>OpenAI-compatible API| M["🤖 Any AI model"]
    S -. web search .-> W["🌐 native · SearXNG<br/>Brave · Tavily"]
    S -->|REST API, restricted| H["🏠 Home Assistant"]
    S -->|SSML answer| A
```

1. Alexa turns your speech into an intent. Alexa only captures free text in an `AMAZON.SearchQuery` slot when the
   sentence starts with one of the skill's ~150 *carrier phrases* (*che*, *come*, *accendi*, …). A custom slot
   handles short phrases (*spegnila*, *di più*, *a metà*).
2. The service:
   - verifies the request;
   - adds the voice instructions and today's date;
   - calls the model with up to four tools: web search plus three for the home.
3. If the model answers within `ATTESA_MAX` seconds, Alexa speaks the answer straight away. Otherwise the service
   keeps it for 15 minutes and delivers it on *"allora?"* (*so?*), on *"sì"*, or when you reopen the skill.

Full details: [docs/architecture.md](docs/architecture.md).

## Quick start

> You need a free Amazon developer account (same login as your Echo), a Linux host with Docker, a public DNS name
> with ports 80/443 open, an AI model (any API key, or Ollama), and optionally Home Assistant.
>
> 📘 **First time? Follow the [complete setup guide](docs/setup.md)**: every step, with checks and troubleshooting.

1. **Create the skill** in the [Alexa developer console](https://developer.amazon.com/alexa/console/ask):
   - choose a *Custom* model with *Provision your own* hosting;
   - paste [`skill/interaction-model.it-IT.json`](skill/interaction-model.it-IT.json) (Italian) or
     [`skill/interaction-model.en-US.json`](skill/interaction-model.en-US.json) (English) into the JSON editor;
   - click **Save**, then **Build**, and copy the **Skill ID**.
2. **Run the service** on your host:

   ```bash
   git clone https://github.com/LucaTomei/alexa-ai-bridge.git && cd alexa-ai-bridge
   cp .env.example .env && chmod 600 .env     # SKILL_ID, PUBLIC_HOST, one model block, optional WEB_* and HA_*
   docker compose --profile caddy up -d           # bridge + HTTPS (add --profile searxng for free web search)
   curl -s https://alexa.example.com/health       # {"ok":true}
   ```

   Already have a reverse proxy? Skip `--profile caddy` and point it to `127.0.0.1:8090`. The image is prebuilt
   for amd64 and arm64 (Raspberry Pi included) and published with every
   [release](https://github.com/LucaTomei/alexa-ai-bridge/releases); updates are one
   `docker compose pull && docker compose up -d` away, or automatic ([how](docs/setup.md#updating)).
3. **Set the skill endpoint** to `https://<your-host>/alexa` and choose *"certificate from a trusted certificate
   authority"*.
4. **Test** in the console simulator, then on your Echo: *"Alexa, apri cervellone"*.

## Safety model

| | Allowed | Never |
|---|---|---|
| **Read** | people, lights, covers, climate, sensors, locks (state only) | – |
| **Control** | lights, covers, climate, switches, fans, humidifiers, scenes | locks, doors, gates, alarms, scripts, automations, containers / technical services |
| **Confirmation** | one room: immediate | several rooms or groups: only after the user says *yes*, enforced by the service |

These rules live in code, not in the prompt, so they hold whatever model you choose, and whatever a web page
might try to inject. More in [docs/security.md](docs/security.md) and [docs/home-assistant.md](docs/home-assistant.md).

## Tests

```bash
pip install -r requirements.txt pytest && python -m pytest -q     # unit and integration tests
python scripts/check_repo.py                                      # docs links, skill model, env variables
```

For your real deployment, [`scripts/e2e.py`](scripts/e2e.py) runs a scripted conversation inside the container
against the real model and the real home. Its only real action is on a light you choose, and it puts the light
back as it was afterwards:

<p align="center"><img src="docs/images/e2e.png" width="85%" alt="End-to-end check: all OK"></p>

## Lessons learned

Most of the work in a voice assistant on Alexa goes into Alexa's limits. These cost the most time:

- Alexa gives a skill **~8 seconds**, so anything slower needs an asynchronous pattern ([details](docs/lessons-learned.md#1-the-8-second-limit)).
- Free text only works **after a carrier phrase**, and one-word follow-ups need a custom slot ([details](docs/alexa-skill.md#carrier-phrases)).
- **Brand-like invocation names** that work typed in the simulator can fail by voice.
- **Cloudflare Bot Fight Mode** silently blocks Alexa's requests and Python's default user agent.
- Reasoning can eat the whole token budget and return **no text at all**.
- Conversation memory must include **what the assistant actually did**, not only what it said.

All fifteen, with their fixes, are in [docs/lessons-learned.md](docs/lessons-learned.md).

## Project structure

```
├── src/
│   ├── app.py              # Alexa endpoint: request verification, conversation, slow answers
│   ├── llm.py              # Anthropic + OpenAI-compatible adapters, tool loop, graceful degradation
│   ├── web_search.py       # native search (Claude) or SearXNG / Brave / Tavily (any model)
│   ├── home_tools.py       # Home Assistant tools with allow-lists and server-side confirmation
│   ├── lingua.py           # every text of the assistant, in Italian and English
│   ├── admin.py · admin/   # admin page: status, history, test chat, home rules, settings, system, log
│   └── impostazioni.py     # settings saved from the admin page, validation
├── skill/
│   ├── interaction-model.it-IT.json   # paste into the Alexa console JSON editor (Italian)
│   └── interaction-model.en-US.json   # the same for English
├── deploy/                 # Caddyfile example, SearXNG settings
├── scripts/
│   ├── e2e.py              # end-to-end check against a running deployment
│   └── check_repo.py       # consistency checks run by CI
├── tests/                  # pytest suite with fake models, fake Home Assistant, fake search
├── docs/                   # providers, architecture, setup, Home Assistant, security, lessons
├── .github/workflows/      # CI (lint, tests, coverage, Docker smoke test) and releases (image on ghcr.io)
└── Dockerfile · compose.yaml · .env.example
```

## Limitations

- The skill runs in **development mode**, so it only works on the Echo devices of the developer's Amazon account.
  Publishing it would need Amazon certification.
- Sentences must start with one of the carrier phrases. Anything else ends in *"non ho capito"*.
- Pending answers are kept in memory, so run **one** gunicorn worker.
- Home control and client-side search need a model with **tool calling**. Without it you still get plain answers.
- Costs depend on your provider. Local models are free. Use official APIs: routing a consumer subscription
  through third-party proxies may break its terms of service.

## Contributing

Translations, provider presets and new tools are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). This project is not affiliated with, endorsed by or sponsored by Amazon or any AI provider.
"Alexa" and "Echo" are trademarks of Amazon. Model and provider names belong to their respective owners.
