"""Web search for every model.

- ``native``: Anthropic's server-side web_search tool (Claude only, nothing to host);
- ``searxng``: your own SearXNG instance (free, private, no API key);
- ``brave`` / ``tavily``: hosted search APIs with a free tier.

With ``WEB_SEARCH=auto`` (default) Claude uses ``native`` and any other model uses the first backend that is
configured. The client-side backends are exposed to the model as an ordinary tool, ``cerca_sul_web``."""
import json, os, re, logging, urllib.request
from urllib.parse import urlencode, urlsplit
import lingua as L

log = logging.getLogger("alexa-ai-bridge")

MODO = os.environ.get("WEB_SEARCH", "auto").strip().lower()
SEARXNG_URL = os.environ.get("SEARXNG_URL", "").rstrip("/")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_URL = os.environ.get("BRAVE_URL", "https://api.search.brave.com/res/v1/web/search")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_URL = os.environ.get("TAVILY_URL", "https://api.tavily.com/search")
RISULTATI = int(os.environ.get("WEB_RESULTS", "5"))
LINGUA = os.environ.get("WEB_LANGUAGE") or L.LINGUA
UA = os.environ.get("HTTP_USER_AGENT", "alexa-ai-bridge/1.0")

HOME_TZ = os.environ.get("HOME_TIMEZONE", "Europe/Rome")
HOME_CITY = os.environ.get("HOME_CITY", "")
_LOC = {k: v for k, v in (("city", HOME_CITY), ("region", os.environ.get("HOME_REGION", "")),
                          ("country", os.environ.get("HOME_COUNTRY", "")), ("timezone", HOME_TZ if HOME_CITY else "")) if v}

NATIVO = {"type": "web_search_20250305", "name": "web_search", "max_uses": int(os.environ.get("WEB_MAX", "3")),
          **({"user_location": dict({"type": "approximate"}, **_LOC)} if _LOC else {})}

NOME_STRUMENTO = "cerca_sul_web"


def strumento():
    return {"name": NOME_STRUMENTO, "description": L.t("web_desc"),
            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": L.t("web_query")}},
                           "required": ["query"]}}

_CONFIGURATO = {"searxng": SEARXNG_URL, "brave": BRAVE_API_KEY, "tavily": TAVILY_API_KEY}


def backend(api, modo=None):
    """Which search to use with this model API: 'native', 'searxng', 'brave', 'tavily' or None."""
    m = (modo if modo is not None else MODO) or "off"
    if m in ("1", "true", "yes", "on"):
        m = "auto"
    if m in ("0", "false", "no", "off", "none"):
        return None
    if m == "auto":
        if api == "anthropic":
            return "native"
        return next((b for b in ("searxng", "brave", "tavily") if _CONFIGURATO[b]), None)
    if m == "native":
        if api != "anthropic":
            log.warning("WEB_SEARCH=native only works with LLM_API=anthropic: web search is off")
            return None
        return "native"
    if m not in _CONFIGURATO:
        log.warning("unknown WEB_SEARCH=%r: web search is off", m)
        return None
    if not _CONFIGURATO[m]:
        log.warning("WEB_SEARCH=%s but its URL/key is not set: web search is off", m)
        return None
    return m


def _get(url, hdr=None, body=None, timeout=8):
    h = dict({"Accept": "application/json", "User-Agent": UA}, **(hdr or {}))
    if body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, None if body is None else json.dumps(body).encode(), h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _pulito(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t or "")).strip()


def _formatta(risultati, risposte=()):
    righe = [L.t("web_diretta") + _pulito(a) for a in risposte if _pulito(a)]
    for i, (titolo, estratto, url) in enumerate(risultati[:RISULTATI], 1):
        fonte = (urlsplit(url).hostname or "").removeprefix("www.")
        righe.append("%d. %s - %s (%s)" % (i, _pulito(titolo), _pulito(estratto)[:500], fonte))
    return "\n".join(righe) or L.t("web_niente")


def _searxng(q):
    d = _get(SEARXNG_URL + "/search?" + urlencode({"q": q, "format": "json", "language": LINGUA}))
    risposte = [a if isinstance(a, str) else (a or {}).get("answer", "") for a in d.get("answers") or []]
    return _formatta([(r.get("title"), r.get("content"), r.get("url", "")) for r in d.get("results") or []], risposte)


def _brave(q):
    d = _get(BRAVE_URL + "?" + urlencode({"q": q, "count": RISULTATI, "search_lang": LINGUA}),
             {"X-Subscription-Token": BRAVE_API_KEY})
    return _formatta([(r.get("title"), r.get("description"), r.get("url", "")) for r in (d.get("web") or {}).get("results") or []])


def _tavily(q):
    d = _get(TAVILY_URL, {"Authorization": "Bearer " + TAVILY_API_KEY},
             {"query": q, "max_results": RISULTATI, "search_depth": "basic", "include_answer": True})
    return _formatta([(r.get("title"), r.get("content"), r.get("url", "")) for r in d.get("results") or []],
                     [d["answer"]] if isinstance(d.get("answer"), str) else [])


def cerca(query, quale):
    """Run a client-side search and return a short text for the model."""
    query = (query or "").strip()
    if not query:
        return L.t("web_vuota")
    try:
        out = {"searxng": _searxng, "brave": _brave, "tavily": _tavily}[quale](query)
        log.info("web search (%s): %d results", quale, out.count("\n") + 1 if out != L.t("web_niente") else 0)
        return out
    except Exception as e:
        log.warning("web search (%s): %s", quale, e)
        return L.t("web_errore") % str(e)[:120]
