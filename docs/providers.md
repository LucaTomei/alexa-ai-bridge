# Models and providers

Alexa AI Bridge talks to any model through one of two wire formats:

- **`LLM_API=anthropic`**: the Anthropic Messages API (Claude).
- **`LLM_API=openai`**: the OpenAI-compatible Chat Completions API, which almost every provider, gateway and local
  runtime speaks.

Home control and web search use standard function calling, so they work with every model that supports tools.
If a model doesn't support them, the service notices on the first request and carries on with plain answers.

## Presets

Copy one block into `.env`. The model names are only examples: pick any current chat model from the provider's
list. **Fast models sound best on a voice assistant**: *haiku / mini / flash / small* models usually answer
well within Alexa's 8 seconds.

| Provider | `LLM_API` | `LLM_BASE_URL` | Example `LLM_MODEL` | Web search |
|---|---|---|---|---|
| **Anthropic** (Claude) | `anthropic` | `https://api.anthropic.com/v1` | `claude-haiku-5-5` | native ✅ |
| **OpenAI** | `openai` | `https://api.openai.com/v1` | `gpt-5.4-mini` | backend |
| **Google Gemini** | `openai` | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-flash-latest` | backend |
| **Mistral** | `openai` | `https://api.mistral.ai/v1` | `mistral-small-latest` | backend |
| **Groq** | `openai` | `https://api.groq.com/openai/v1` | a tool-capable model | backend |
| **DeepSeek** | `openai` | `https://api.deepseek.com/v1` | `deepseek-chat` | backend |
| **xAI** | `openai` | `https://api.x.ai/v1` | a Grok model | backend |
| **OpenRouter** | `openai` | `https://openrouter.ai/api/v1` | `vendor/model` | backend, or `:online` models |
| **Ollama** (local) | `openai` | `http://host.docker.internal:11434/v1` | `qwen3:8b` | backend |
| **LM Studio** (local) | `openai` | `http://host.docker.internal:1234/v1` | the loaded model | backend |
| **LiteLLM / vLLM / any gateway** | `openai` or `anthropic` | your gateway URL | – | depends |

*Backend* means one of the client-side search services described below.

### Provider notes

- **Anthropic**: Claude's extended thinking is turned off automatically. Native web search is billed per search,
  so check the provider's pricing.
- **OpenAI** and other reasoning models:
  - Set `LLM_EXTRA_JSON={"reasoning_effort": "low"}` for fast spoken answers.
  - If a model wants `max_completion_tokens` instead of `max_tokens`, the service switches to it on its own.
  - If a model only works through the Responses API, put LiteLLM in front of it.
- **Gemini**: get a key from Google AI Studio. `reasoning_effort` works here too.
- **OpenRouter**: one key gives you hundreds of models. OpenRouter's `:online` model variants search the web on
  OpenRouter's side, so you can skip the search backend.
- **Ollama**:
  - Choose a model with **tool support** if you want home control. Open reasoning models print their reasoning in
    `<think>` tags, and the service removes it before Alexa speaks.
  - By default Ollama only listens on `127.0.0.1`. Start it with `OLLAMA_HOST=0.0.0.0` (and firewall port 11434) so
    the container can reach it through `host.docker.internal`, or run Ollama in the same Compose project and use
    `http://ollama:11434/v1`.
  - The first request after an idle period also loads the model, which can take a while. The *"Ci sto pensando,
    dimmi allora"* fallback covers that wait.
- **Local models without an API key**: leave `LLM_API_KEY` empty and no `Authorization` header is sent.
- **Azure OpenAI, Bedrock, Vertex AI**: use them through LiteLLM, which exposes an OpenAI-compatible endpoint.

### Check your choice

```bash
docker compose up -d
docker exec alexa-ai-bridge python -c "import app; print(app.ask_llm([{'role':'user','content':'ciao, chi sei?'}]))"
docker logs alexa-ai-bridge 2>&1 | grep -E "rejected|without text" || echo "no warnings"
```

A `tools rejected` warning means the model can't call tools. Answers still work, but there is no home control
and no client-side search. To get those back, pick a tool-capable model.

## Web search

| `WEB_SEARCH` | What it uses | Needs |
|---|---|---|
| `auto` (default) | Claude: native; other models: the first configured backend among SearXNG, Brave, Tavily | – |
| `native` | Anthropic's server-side `web_search` tool | `LLM_API=anthropic` |
| `searxng` | your own [SearXNG](https://docs.searxng.org) instance: free, private, no key | `SEARXNG_URL` |
| `brave` | [Brave Search API](https://brave.com/search/api/) | `BRAVE_API_KEY` |
| `tavily` | [Tavily](https://tavily.com) | `TAVILY_API_KEY` |
| `off` | no web search | – |

Client-side backends are offered to the model as a tool, `cerca_sul_web`. The model writes the query (adding your
`HOME_CITY` when it matters), and the service returns titles and snippets of the top `WEB_RESULTS` results. The
model never sees full URLs, and the voice rules tell it never to read them aloud.

### SearXNG next to the service

`compose.yaml` includes an optional SearXNG service, which is not published on any port:

```bash
# in .env:  SEARXNG_URL=http://searxng:8080  and  SEARXNG_SECRET=<output of: openssl rand -hex 32>
docker compose --profile searxng up -d
docker exec alexa-ai-bridge python -c "import web_search as w; print(w.cerca('meteo Roma domani', 'searxng'))"
```

The provided [`deploy/searxng/settings.yml`](../deploy/searxng/settings.yml) enables the JSON format the service
needs (`search.formats: [html, json]`) and turns off the limiter, since only the bridge can reach the instance.
