# Setup guide

About 30 minutes. You need:

- an [Amazon developer account](https://developer.amazon.com) — **the same Amazon account as your Echo**;
- a host with Docker and a public DNS name (a small VPS is fine);
- an AI model: an API key from any provider, or a local model with Ollama / LM Studio ([providers](providers.md));
- optionally, Home Assistant reachable from that host over HTTPS.

## 1. Create the skill

In the [Alexa developer console](https://developer.amazon.com/alexa/console/ask) → **Create Skill**:

| Field | Value |
|---|---|
| Name | anything (e.g. *Cervellone*) |
| Primary locale | Italian (IT) |
| Type of experience | Other |
| Model | **Custom** |
| Hosting | **Provision your own** |
| Template | Start from scratch |

Then **Build → Interaction Model → JSON Editor**, select everything, paste
[`skill/interaction-model.it-IT.json`](../skill/interaction-model.it-IT.json), **Save**, **Build skill** and wait for
*Build Successful*. Check **Intents**: you must see `AskIntent`, `AttesaIntent` and `FraseBreveIntent`
(if you still see `HelloWorldIntent`, the JSON was not saved).

Copy the **Skill ID** (`amzn1.ask.skill.…`) from **Build → Endpoint**.

> 💡 The invocation name is `cervellone`. Choose plain words in the skill's language: a brand-like name that
> works when typed in the simulator may not be recognised by voice.

## 2. Run the service

```bash
cp .env.example .env && chmod 600 .env
# edit .env: SKILL_ID, one model block (LLM_*), HOME_*, optionally WEB_* and HA_*
docker compose up -d --build
curl -s http://127.0.0.1:8090/health      # {"ok":true}
```

Check that the model answers before involving Alexa:

```bash
docker exec alexa-ai-bridge python -c "import app; print(app.ask_llm([{'role':'user','content':'ciao, chi sei?'}]))"
```

Using a model other than Claude and want web search? Set up one backend from
[providers.md → Web search](providers.md#web-search) (SearXNG is free and runs next to the service).

## 3. Expose it over HTTPS

Alexa only calls HTTPS endpoints with a certificate from a trusted CA. With Caddy:

```caddyfile
alexa.example.com {
	reverse_proxy 127.0.0.1:8090
}
```

If Caddy runs in Docker, put both containers on the same network and use `reverse_proxy alexa-ai-bridge:8090`
instead of publishing the port.

> ⚠️ **Cloudflare**: with the orange-cloud proxy and *Bot Fight Mode* enabled, Alexa's requests are blocked before
> they reach you — even with a WAF *Skip* rule, which never sees them. Use a **DNS-only** (grey cloud) record for
> the skill hostname. The service rejects everything that is not signed by Amazon for your skill.

Check from outside:

```bash
curl -s https://alexa.example.com/health                                   # {"ok":true}
curl -s -o /dev/null -w '%{http_code}\n' -X POST -d '{}' https://alexa.example.com/alexa   # 400
```

## 4. Point the skill to your endpoint

**Build → Endpoint** → **HTTPS** → Default Region: `https://alexa.example.com/alexa`, certificate type
*"My development endpoint has a certificate from a trusted certificate authority"* → **Save**.

## 5. Test

**Test** tab → *Skill testing is enabled in: Development*. Type:

```
apri cervellone
perché il cielo è blu
e di sera perché diventa rosso
che tempo fa domani
basta
```

Then on the Echo: *"Alexa, apri cervellone"*.

Follow the service while you test:

```bash
docker logs -f alexa-ai-bridge 2>&1 | grep -E "POST|domanda risposta|risposta lenta|web search|azione HA|rifiutata|rejected"
```

## 6. Home Assistant (optional)

See [home-assistant.md](home-assistant.md): create a dedicated non-admin user, generate its token, set
`HA_URL` / `HA_TOKEN`, restart, and run [`scripts/e2e.py`](../scripts/e2e.py).

## Configuration reference

| Variable | Default | Meaning |
|---|---|---|
| `SKILL_ID` | – | Only requests for this skill are accepted |
| `LLM_API` | `anthropic` if the URL is api.anthropic.com, else `openai` | Wire format: `anthropic` or `openai` (OpenAI-compatible) |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | – | Endpoint, key (empty for local models) and model ([examples](providers.md)) |
| `LLM_MAX_TOKENS` | `1024` | Max tokens per answer |
| `LLM_EXTRA_JSON` | `{}` | Extra fields for every request, e.g. `{"reasoning_effort": "low"}` |
| `ATTESA_MAX` | `6.0` | Seconds before "Ci sto pensando"; keep ≤ 7 |
| `LLM_TIMEOUT_LUNGO` | `120` | Max seconds for a background answer |
| `WEB_SEARCH` | `auto` | `auto`, `native` (Claude only), `searxng`, `brave`, `tavily`, `off` |
| `SEARXNG_URL`, `BRAVE_API_KEY`, `TAVILY_API_KEY` | – | Client-side search backends |
| `WEB_RESULTS`, `WEB_LANGUAGE`, `WEB_MAX` | `5`, `it`, `3` | Results per search, search language, native searches per question |
| `HOME_CITY`, `HOME_REGION`, `HOME_COUNTRY`, `HOME_TIMEZONE` | –, –, –, `Europe/Rome` | Local searches and "today" |
| `HA_URL`, `HA_TOKEN`, `HA_TOOLS` | –, –, `1` | Home Assistant tools (off without a token) |
| `HTTP_USER_AGENT` (`HA_UA`) | `alexa-ai-bridge/1.0` | User agent for outgoing calls (`HA_UA` overrides it for Home Assistant) |
| `HA_GRUPPI` | – | Entities acting on several rooms (always confirmed) |
| `HA_MAX_SENZA_CONFERMA` | `3` | More entities than this → confirmation |
| `HA_SUMMARY_EXTRA` | – | `entity_id=Label,…` extra lines in the home summary |
| `HA_TEMP_PATTERN` | – | Regex of temperature sensors for the summary |
| `HA_VIETATO` | see code | Regex of entities that can never be controlled |
| `SYSTEM_PROMPT`, `ISTRUZIONI_TURNO` | Italian voice rules | Override the instructions |
