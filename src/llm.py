"""Model adapters. Two wire formats cover practically every AI provider:

- ``anthropic``: the Anthropic Messages API (Claude), with native server-side web search;
- ``openai``: the OpenAI-compatible Chat Completions API, spoken by OpenAI, Google Gemini, Mistral, Groq,
  DeepSeek, xAI, OpenRouter, Together, Ollama, LM Studio, vLLM, LiteLLM and most gateways.

Both formats get the same tools (home control, client-side web search) through function calling. If an
endpoint or model rejects tools, the adapter switches them off and keeps answering in plain text.

Fallback models: besides the main one (LLM_*), up to four more (LLM_2_* ... LLM_5_*), e.g. several CLIProxyAPI
instances or other providers. They are tried in order: one that is unreachable, logged out, out of credit or over
its rate limit is paused for LLM_PAUSA seconds and the next one answers; the main one is tried again after the pause.
Every change (a model stops answering, comes back) can send a notification."""
import http.client, json, os, re, threading, time, logging, urllib.request, urllib.error
from urllib.parse import urlsplit
import lingua as L
import notifiche

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
RISERVE_MAX = 5          # the main model is 1, the fallback ones 2..5
PAUSA = int(os.environ.get("LLM_PAUSA") or "300")              # seconds a failing model is skipped
CONTROLLO = int(os.environ.get("LLM_CONTROLLO") or "10")       # minutes between background checks, 0 = never


def _stato_nuovo():
    return {"web_nativo": True, "strumenti": True, "max_completion": False, "thinking": True}


class Fornitore:
    """One model endpoint. n=1 is the main one (its settings are the module globals, read at every request)."""
    def __init__(self, n, base, key, model, api, extra, stato, attivo=True):
        self.n, self.base, self.key, self.model, self.api, self.extra, self.stato, self.attivo = \
            n, base, key, model, api, extra, stato, attivo

    @property
    def host(self):
        p = urlsplit(self.base)
        return (p.hostname or "?") + (":%d" % p.port if p.port else "")

    @property
    def nome(self):
        return "%s (%s)" % (self.model, self.host)


def _riserva(n):
    e = lambda k: os.environ.get("LLM_%d_%s" % (n, k), "").strip()
    base, model = e("BASE_URL").rstrip("/"), e("MODEL")
    if not base and not model:
        return None
    for k, v in (("BASE_URL", base), ("MODEL", model)):
        if not v:
            raise SystemExit("LLM_%d_%s is not set: a fallback model needs both LLM_%d_BASE_URL and LLM_%d_MODEL" % (n, k, n, n))
    api = (e("API") or ("anthropic" if "anthropic.com" in base else "openai")).lower()
    if api not in ("anthropic", "openai"):
        raise SystemExit("LLM_%d_API must be 'anthropic' or 'openai' (OpenAI-compatible), not %r" % (n, api))
    try:
        extra = json.loads(e("EXTRA_JSON") or "{}")
        assert isinstance(extra, dict)
    except (ValueError, AssertionError):
        raise SystemExit("LLM_%d_EXTRA_JSON must be a JSON object, e.g. {\"reasoning_effort\": \"low\"}" % n) from None
    return Fornitore(n, base, e("API_KEY"), model, api, extra, _stato_nuovo(), e("ATTIVO").lower() not in ("0", "false", "no", "off"))


RISERVE = [f for f in (_riserva(n) for n in range(2, RISERVE_MAX + 1)) if f]
_lock = threading.Lock()
SALUTE = {}              # n -> {"giu", "fino", "errore", "t_errore", "t_ok", "controllo"}
ULTIMO = {"n": None, "t": None}      # the model that answered last


def salute(n):
    return SALUTE.setdefault(n, {"giu": False, "fino": 0.0, "errore": None, "t_errore": None, "t_ok": None, "controllo": False})


def principale():
    return Fornitore(1, BASE, KEY, MODEL, API, EXTRA, STATO)


def fornitori(tutti=False):
    """The main model and the fallback ones, in order (only the active ones unless tutti)."""
    return [principale()] + [f for f in RISERVE if tutti or f.attivo]


def fornitore(n):
    return next((f for f in fornitori(True) if f.n == n), None)


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


def _invia(url, hdr, body, scadenza, nativo=None, stato=None, riprova=True):
    """POST, adapting the body once per kind of rejection: max_tokens name, thinking, native web search, tools.
    What was turned off is remembered for the next requests only if the request then succeeds: a 400 caused by
    something else (a malformed message, a context that is too long) must not switch home control off for good."""
    stato = STATO if stato is None else stato
    tolto, riprovato, primo = [], not riprova, None
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
            stato[k] = k == "max_completion"
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
def _anthropic(f, system, messaggi, strumenti, esegui, nativo, scadenza, riprova=True):
    url, hdr = f.base + "/messages", {"x-api-key": f.key, "anthropic-version": "2023-06-01"}
    body = dict({"model": f.model, "max_tokens": MAX_TOKENS, "system": system, "messages": messaggi}, **f.extra)
    invia = lambda: _invia(url, hdr, body, scadenza, nativo, f.stato, riprova)
    if f.stato["thinking"] and "thinking" not in f.extra:
        body["thinking"] = {"type": "disabled"}   # extended thinking can eat the whole token budget
    tools = ([nativo] if nativo else []) + [{"name": s["name"], "description": s["description"], "input_schema": s["parameters"]}
                                            for s in strumenti]
    if tools:
        body["tools"] = tools
    d = invia()
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
        d = invia()
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


def _openai(f, system, messaggi, strumenti, esegui, scadenza, riprova=True):
    url, hdr = f.base + "/chat/completions", ({"Authorization": "Bearer " + f.key} if f.key else {})
    body = dict({"model": f.model, "messages": [{"role": "system", "content": system}] + messaggi}, **f.extra)
    body["max_completion_tokens" if f.stato["max_completion"] else "max_tokens"] = MAX_TOKENS
    invia = lambda: _invia(url, hdr, body, scadenza, None, f.stato, riprova)
    if strumenti:
        body["tools"] = [{"type": "function", "function": {"name": s["name"], "description": s["description"], "parameters": s["parameters"]}}
                         for s in strumenti]
    d = invia()
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
        d = invia()
    t = _testo_openai(((d.get("choices") or [{}])[0].get("message")) or {})
    if not t.strip():
        log.warning("answer without text: %s", _riassunto(d))
    return t


def modelli(timeout=8, f=None):
    """The models the endpoint offers ({"id", "nome"}), as listed by its /models endpoint (both formats have one)."""
    f = f or principale()
    if f.api == "anthropic":
        url, hdr = f.base + "/models?limit=1000", {"x-api-key": f.key, "anthropic-version": "2023-06-01"}
    else:
        url, hdr = f.base + "/models", ({"Authorization": "Bearer " + f.key} if f.key else {})
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


# ---------- fallback between models
PASSABILI = (ErroreModello, Rifiutata, OSError, http.client.HTTPException, json.JSONDecodeError)
# a 400 that says the account cannot answer (no credit, logged out, unknown model): the model is paused too
_NON_PUO = re.compile(r"credit|balance|quota|billing|exhaust|insufficient|rate.?limit|unauthori[sz]ed|forbidden|"
                      r"invalid.{0,10}api.?key|api.?key.{0,20}(?:invalid|missing|expired)|\bauth(?:_|entica|ori[sz]ation\b|\b)|"
                      r"\blog(?:ged)?.?(?:in|out)\b|model.{0,30}(?:not.?found|does not exist|not available|unsupported)|"
                      r"(?:unknown|unsupported|invalid) model|model_not_found|permission.?denied|account.{0,30}(?:suspended|disabled)", re.I)


def motivo(e):
    """A short reason, for the page, the log and the notifications: never a URL or a key."""
    if isinstance(e, str):
        return e[:100]
    if isinstance(e, (ErroreModello, Rifiutata)):
        testo = str(e)
        codice = getattr(e, "codice", None) or 400
        corpo = testo.split(": ", 1)[1] if testo.startswith("HTTP ") and ": " in testo else testo
        try:
            j = json.loads(corpo)
            err = j.get("error", j) if isinstance(j, dict) else j
            corpo = (err.get("message") or err.get("type") or "") if isinstance(err, dict) else str(err)
        except ValueError:
            pass
        corpo = re.sub(r"https?://\S+", "", " ".join(str(corpo).split()))[:100]
        return ("HTTP %d: %s" % (codice, corpo)).rstrip(": ")
    if isinstance(e, urllib.error.URLError):
        r = e.reason
        return str(getattr(r, "strerror", None) or (r if isinstance(r, str) else type(r).__name__))[:80]
    if isinstance(e, TimeoutError):
        return "timeout"
    return (getattr(e, "strerror", None) or type(e).__name__)[:80]


def _segna_giu(f, e, controllo=False):
    """Pause this model; True if it was answering before (a change worth a notification)."""
    with _lock:
        s, ora = salute(f.n), time.time()
        prima = s["giu"]
        s.update(giu=True, fino=ora + PAUSA, errore=motivo(e), t_errore=ora, controllo=controllo and (not prima or s["controllo"]))
    log.warning("model %d %s: %s, paused for %d s", f.n, f.nome, motivo(e), PAUSA)
    return not prima


def _segna_su(f, controllo=False, in_uso=True):
    """This model answered; True if it was paused (it is back)."""
    with _lock:
        s = salute(f.n)
        tornato = s["giu"] and (not controllo or s["controllo"])
        if tornato or not s["giu"]:
            s.update(giu=False, fino=0.0, controllo=False)
        s["t_ok"] = time.time()
        if not controllo and in_uso:
            ULTIMO.update(n=f.n, t=time.time())
    if tornato:
        log.info("model %d %s answers again", f.n, f.nome)
    return tornato


def _avvisa_caduti(caduti, chi, solo=False):
    if caduti and solo:                   # the check of one model from the admin page
        for f, m in caduti:
            notifiche.notifica("modelli", L.t("n_modello_irraggiungibile") % (f.nome, m), True)
    elif caduti:
        elenco = ", ".join("%s: %s" % (f.nome, m) for f, m in caduti)
        notifiche.notifica("modelli", (L.t("n_modello_giu") % (elenco, chi.nome)) if chi else (L.t("n_modelli_giu") % elenco), True)


def _domanda(f, system, messaggi, strumenti, esegui, nativo, scadenza, riprova=True, per_api=None):
    if per_api and f.api in per_api:
        strumenti, nativo = per_api[f.api]
    strumenti = strumenti if f.stato["strumenti"] else []
    if f.api == "anthropic":
        return _anthropic(f, system, messaggi, strumenti, esegui, nativo if f.stato["web_nativo"] else None, scadenza, riprova)
    return _openai(f, system, messaggi, strumenti, esegui, scadenza, riprova)


def chiedi(system, messaggi, strumenti, esegui, nativo=None, timeout=60, irreversibile=None, per_api=None, solo=None,
           silenzioso=False):
    """One answer from the model. messaggi: [{"role": "user"|"assistant", "content": str}];
    strumenti: [{"name", "description", "parameters"}]; esegui(name, args) -> str runs a tool;
    nativo: the Anthropic server-side web search tool, if wanted; per_api: {"anthropic"|"openai": (strumenti, nativo)}
    for fallback models of another format. The models are tried in order (the paused ones last); the next one is
    tried only if irreversibile() is false: nothing that must not happen twice (a home action) was done.
    solo: ask only this model (the checks of the admin page). silenzioso: a background request (the memory learning):
    it follows the same order but never pauses a model, changes the one in use or sends a notification."""
    scadenza = time.time() + timeout
    elenco = [solo] if solo else fornitori()
    ora = time.time()
    ordine = [f for f in elenco if salute(f.n)["fino"] <= ora] + [f for f in elenco if salute(f.n)["fino"] > ora]
    caduti, errore = [], None
    for i, f in enumerate(ordine):
        resto = scadenza - time.time()
        if i and resto < 4:
            break
        altri = i < len(ordine) - 1
        limite = max(resto / 2, min(resto, 15)) if altri else resto     # leave time for the next ones
        try:
            t = _domanda(f, system, messaggi, strumenti, esegui, nativo, time.time() + limite, not altri, per_api)
        except PASSABILI as e:
            errore = e
            if silenzioso:
                log.info("background request: model %d %s: %s", f.n, f.nome, motivo(e))
            elif isinstance(e, Rifiutata) and not _NON_PUO.search(str(e)):
                log.warning("model %d %s refused the request: %s", f.n, f.nome, str(e)[:200])
            elif _segna_giu(f, e):
                caduti.append((f, motivo(e)))
            if irreversibile and irreversibile():
                log.warning("model %d failed after a home action: not asking another model (it could repeat it)", f.n)
                break
            continue
        if not silenzioso and _segna_su(f, in_uso=not solo):
            notifiche.notifica("modelli", L.t("n_modello_su") % f.nome)
        if (f.n != 1 or caduti) and not silenzioso:
            log.info("answered by model %d %s", f.n, f.nome)
        _avvisa_caduti(caduti, f, bool(solo))
        return senza_pensieri(t).strip()
    _avvisa_caduti(caduti, None, bool(solo))
    raise errore if errore else ErroreModello("no model available", 0)


def controlla(f, timeout=8):
    """Is this model reachable and does its key work? Its /models list, which costs no tokens. Returns (ok, reason);
    ok is None when the endpoint has no /models list (nothing can be said)."""
    try:
        elenco = modelli(timeout, f)
    except ErroreModello as e:
        if e.codice in (404, 405, 501):
            return None, motivo(e)
        return False, motivo(e)
    except (OSError, http.client.HTTPException, ValueError) as e:
        return False, motivo(e) if not isinstance(e, ValueError) else "invalid answer"
    if not elenco:
        return False, L.t("nessun_modello")
    return True, "%d" % len(elenco)


def controlla_tutti():
    """The background check: a model that stops answering is paused and notified, one that comes back too
    (only if this check paused it: a model out of credit still lists its models)."""
    for f in fornitori():
        ok, perche = controlla(f)
        if ok is None:
            continue
        # a gateway that answers questions but refuses its model list: trust the answers of the last check periods
        if ok is False and perche.startswith("HTTP") and (salute(f.n)["t_ok"] or 0) > time.time() - 2 * max(CONTROLLO, 1) * 60:
            continue
        if ok:
            if _segna_su(f, controllo=True):
                notifiche.notifica("modelli", L.t("n_modello_su") % f.nome)
        elif _segna_giu(f, perche, controllo=True):
            notifiche.notifica("modelli", L.t("n_modello_irraggiungibile") % (f.nome, perche), True)


def _controllore():
    while True:
        time.sleep(CONTROLLO * 60)
        try:
            controlla_tutti()
        except Exception as e:              # never let the thread die
            log.warning("model check: %s", type(e).__name__)


def avvia_controllo():
    if CONTROLLO > 0:
        threading.Thread(target=_controllore, daemon=True, name="controllo-modelli").start()


def descrivi():
    """Every model with its state, for the admin page: never a key, only the host of its address."""
    ora, out = time.time(), []
    for f in fornitori(True):
        s = dict(salute(f.n))
        out.append({"n": f.n, "modello": f.model, "api": f.api, "host": f.host, "chiave": bool(f.key), "attivo": f.attivo,
                    "giu": s["giu"], "in_pausa": s["fino"] > ora, "fino": s["fino"] or None, "errore": s["errore"],
                    "t_errore": s["t_errore"], "t_ok": s["t_ok"], "in_uso": ULTIMO["n"] == f.n})
    return out
