"""Model adapters. Two wire formats cover practically every AI provider:

- ``anthropic``: the Anthropic Messages API (Claude), with native server-side web search;
- ``openai``: the OpenAI-compatible Chat Completions API, spoken by OpenAI, Google Gemini, Mistral, Groq,
  DeepSeek, xAI, OpenRouter, Together, Ollama, LM Studio, vLLM, LiteLLM and most gateways.

Both formats get the same tools (home control, client-side web search) through function calling. If an
endpoint or model rejects tools, the adapter switches them off and keeps answering in plain text."""
import json, os, re, time, logging, urllib.request, urllib.error

log = logging.getLogger("alexa-ai-bridge")

for _v in ("LLM_BASE_URL", "LLM_MODEL"):
    if not os.environ.get(_v, "").strip():
        raise SystemExit("%s is not set: pick a model block in .env (see .env.example and docs/providers.md)" % _v)
BASE = os.environ["LLM_BASE_URL"].strip().rstrip("/")
KEY = os.environ.get("LLM_API_KEY", "").strip()
MODEL = os.environ["LLM_MODEL"].strip()
# LLM_FORMAT is the old name; LLM_API set but empty (e.g. "automatic" saved from the admin page) means: guess from the URL
API = ((os.environ.get("LLM_API") if "LLM_API" in os.environ else os.environ.get("LLM_FORMAT"))
       or ("anthropic" if "anthropic.com" in BASE else "openai")).strip().lower()
if API not in ("anthropic", "openai"):
    raise SystemExit("LLM_API must be 'anthropic' or 'openai' (OpenAI-compatible), not %r" % API)
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1024"))
UA = os.environ.get("HTTP_USER_AGENT", "alexa-ai-bridge/1.0")
try:
    EXTRA = json.loads(os.environ.get("LLM_EXTRA_JSON") or "{}")   # provider-specific fields, merged into every request
    assert isinstance(EXTRA, dict)
except (ValueError, AssertionError):
    raise SystemExit("LLM_EXTRA_JSON must be a JSON object, e.g. {\"reasoning_effort\": \"low\"}") from None
MAX_ROUNDS = 8
RIPROVA = {429, 500, 502, 503, 504, 529}   # rate limit / overloaded / gateway errors: worth one more try

# what the endpoint accepted so far (learned at runtime, shared by all requests)
STATO = {"web_nativo": True, "strumenti": True, "max_completion": False, "thinking": True}


class Rifiutata(Exception):
    """HTTP 400/422: the endpoint rejected something in the request body."""


class ErroreModello(Exception):
    """Any other HTTP error from the endpoint, with the start of its body (wrong key, unknown model...)."""
    def __init__(self, testo, codice):
        super().__init__(testo)
        self.codice = codice


def _post(url, hdr, body, timeout):
    h = dict(hdr, **{"Content-Type": "application/json", "User-Agent": UA})
    req = urllib.request.Request(url, json.dumps(body).encode(), h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        testo = e.read()[:400].decode("utf-8", "replace")
        if e.code in (400, 422):
            raise Rifiutata(testo) from None
        raise ErroreModello("HTTP %d: %s" % (e.code, testo), e.code) from None


def _resta(scadenza):
    return max(scadenza - time.time(), 3)


def _invia(url, hdr, body, scadenza, nativo=None):
    """POST, adapting the body once per kind of rejection: max_tokens name, thinking, native web search, tools.
    What was turned off is remembered for the next requests only if the request then succeeds: a 400 caused by
    something else (a malformed message, a context that is too long) must not switch home control off for good."""
    tolto, riprovato, primo = [], False, None
    while True:
        try:
            d = _post(url, hdr, body, _resta(scadenza))
        except ErroreModello as e:
            if riprovato or e.codice not in RIPROVA or scadenza - time.time() < 8:
                raise
            riprovato = True
            log.warning("model endpoint: %s, retrying once", str(e)[:200])
            time.sleep(2)
            continue
        except Rifiutata as e:
            msg, tools = str(e), body.get("tools") or []
            primo = primo or msg
            if "max_tokens" in body and "max_completion_tokens" in msg:
                body["max_completion_tokens"] = body.pop("max_tokens"); tolto.append(("max_completion", msg))
            elif "thinking" in body and "thinking" in msg:
                body.pop("thinking"); tolto.append(("thinking", msg))
            elif nativo is not None and any(t is nativo for t in tools):
                body["tools"] = [t for t in tools if t is not nativo]; tolto.append(("web_nativo", msg))
            elif tools:
                body["tools"] = []; tolto.append(("strumenti", msg))
            elif primo != msg:
                raise Rifiutata("%s (after adapting the request: %s)" % (primo, msg[:200])) from None
            else:
                raise
            if not body.get("tools"):
                body.pop("tools", None); body.pop("tool_choice", None)
            continue
        for k, msg in tolto:
            STATO[k] = k == "max_completion"
            log.warning("%s (%s)", {"max_completion": "the endpoint wants max_completion_tokens: switching to it",
                                    "thinking": "the endpoint does not accept the thinking parameter: not sending it",
                                    "web_nativo": "native web search rejected: continuing without it",
                                    "strumenti": "tools rejected by the endpoint or model: continuing without them"}[k], msg[:200])
        return d


def senza_pensieri(t):
    """Remove the reasoning that some open models (DeepSeek R1, Qwen, ...) put in <think> tags."""
    t = re.sub(r"<think>.*?</think>", "", t or "", flags=re.S)
    return t.split("</think>")[-1] if "</think>" in t else t


# ---------- Anthropic Messages API
def _anthropic(system, messaggi, strumenti, esegui, nativo, scadenza):
    url, hdr = BASE + "/messages", {"x-api-key": KEY, "anthropic-version": "2023-06-01"}
    body = dict({"model": MODEL, "max_tokens": MAX_TOKENS, "system": system, "messages": messaggi}, **EXTRA)
    if STATO["thinking"] and "thinking" not in EXTRA:
        body["thinking"] = {"type": "disabled"}   # extended thinking can eat the whole token budget
    tools = ([nativo] if nativo else []) + [{"name": s["name"], "description": s["description"], "input_schema": s["parameters"]}
                                            for s in strumenti]
    if tools:
        body["tools"] = tools
    d = _invia(url, hdr, body, scadenza, nativo)
    for _ in range(MAX_ROUNDS):   # long web searches (pause_turn) and client tools (tool_use)
        sr = d.get("stop_reason")
        if sr == "pause_turn":
            body["messages"] = body["messages"] + [{"role": "assistant", "content": d["content"]}]
        elif sr == "tool_use":
            ris = [{"type": "tool_result", "tool_use_id": b["id"], "content": esegui(b["name"], b.get("input") or {})}
                   for b in (d.get("content") or []) if b.get("type") == "tool_use"]
            if not ris:
                break
            body["messages"] = body["messages"] + [{"role": "assistant", "content": d["content"]}, {"role": "user", "content": ris}]
        else:
            break
        d = _invia(url, hdr, body, scadenza, nativo)
    bl = d.get("content") or []
    cerche = sum(1 for b in bl if b.get("type") == "server_tool_use")
    if cerche:
        log.info("web searches: %d", cerche)
    # speak only what comes after the last search result (the text before it is "let me check...")
    ultimo = max([i for i, b in enumerate(bl) if b.get("type") == "web_search_tool_result"], default=-1)
    t = "".join(b.get("text", "") for b in bl[ultimo + 1:] if b.get("type") == "text") \
        or "".join(b.get("text", "") for b in bl if b.get("type") == "text")
    if not t.strip():
        log.warning("answer without text: %s", _riassunto(d))
    return t


def _riassunto(d):
    """The shape of an answer, never its content (it could hold anything the endpoint sent back)."""
    if not isinstance(d, dict):
        return type(d).__name__
    if "choices" in d:
        c = (d.get("choices") or [{}])[0] or {}
        m = c.get("message") or {}
        return "finish_reason=%s, tool_calls=%d" % (c.get("finish_reason"), len(m.get("tool_calls") or []))
    if "content" in d or "stop_reason" in d:
        tipi = [b.get("type") for b in d.get("content") or [] if isinstance(b, dict)]
        return "stop_reason=%s, blocks=%s" % (d.get("stop_reason"), ",".join(map(str, tipi)) or "none")
    return "unexpected fields: %s" % ",".join(sorted(map(str, d))[:10])


# ---------- OpenAI-compatible Chat Completions API
def _testo_openai(m):
    c = m.get("content")
    if isinstance(c, list):   # some providers return content parts
        c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c or ""


def _argomenti(a):
    if isinstance(a, dict):
        return a
    try:
        a = json.loads(a or "{}")
    except (TypeError, ValueError):
        return {}
    return a if isinstance(a, dict) else {}


def _openai(system, messaggi, strumenti, esegui, scadenza):
    url, hdr = BASE + "/chat/completions", ({"Authorization": "Bearer " + KEY} if KEY else {})
    body = dict({"model": MODEL, "messages": [{"role": "system", "content": system}] + messaggi}, **EXTRA)
    body["max_completion_tokens" if STATO["max_completion"] else "max_tokens"] = MAX_TOKENS
    if strumenti:
        body["tools"] = [{"type": "function", "function": {"name": s["name"], "description": s["description"], "parameters": s["parameters"]}}
                         for s in strumenti]
    d = _invia(url, hdr, body, scadenza)
    for _ in range(MAX_ROUNDS):
        m = ((d.get("choices") or [{}])[0].get("message")) or {}
        chiamate = [c for c in (m.get("tool_calls") or []) if isinstance(c, dict)]
        if not chiamate:
            break
        risposte = [{"role": "tool", "tool_call_id": c.get("id", ""),
                     "content": esegui((c.get("function") or {}).get("name", ""), _argomenti((c.get("function") or {}).get("arguments")))}
                    for c in chiamate]
        eco = {"role": "assistant", "content": _testo_openai(m), "tool_calls": chiamate}
        body["messages"] = body["messages"] + [eco] + risposte
        d = _invia(url, hdr, body, scadenza)
    t = _testo_openai(((d.get("choices") or [{}])[0].get("message")) or {})
    if not t.strip():
        log.warning("answer without text: %s", _riassunto(d))
    return t


def modelli(timeout=8):
    """The models the endpoint offers ({"id", "nome"}), as listed by its /models endpoint (both formats have one)."""
    if API == "anthropic":
        url, hdr = BASE + "/models?limit=1000", {"x-api-key": KEY, "anthropic-version": "2023-06-01"}
    else:
        url, hdr = BASE + "/models", ({"Authorization": "Bearer " + KEY} if KEY else {})
    req = urllib.request.Request(url, headers=dict(hdr, **{"User-Agent": UA, "Accept": "application/json"}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        raise ErroreModello("HTTP %d: %s" % (e.code, e.read()[:200].decode("utf-8", "replace")), e.code) from None
    voci = d.get("data") or d.get("models") if isinstance(d, dict) else d
    out, visti = [], set()
    for m in voci if isinstance(voci, list) else []:
        mid = m.get("id") or m.get("name") if isinstance(m, dict) else m
        if isinstance(mid, str) and mid and mid not in visti:
            visti.add(mid)
            out.append({"id": mid, "nome": (m.get("display_name") or "") if isinstance(m, dict) else ""})
    return out


def chiedi(system, messaggi, strumenti, esegui, nativo=None, timeout=60):
    """One answer from the model. messaggi: [{"role": "user"|"assistant", "content": str}];
    strumenti: [{"name", "description", "parameters"}]; esegui(name, args) -> str runs a tool;
    nativo: the Anthropic server-side web search tool, if wanted."""
    scadenza = time.time() + timeout
    strumenti = strumenti if STATO["strumenti"] else []
    if API == "anthropic":
        t = _anthropic(system, messaggi, strumenti, esegui, nativo if STATO["web_nativo"] else None, scadenza)
    else:
        t = _openai(system, messaggi, strumenti, esegui, scadenza)
    return senza_pensieri(t).strip()
