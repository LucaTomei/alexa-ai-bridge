"""Notifications: a short message when something worth knowing happens at home (an action confirmed by voice, a
refused attempt on a door or an alarm, an automation created by voice...), on the channels you configure:
the Home Assistant app (notify service), Telegram, ntfy, Gotify, a generic webhook.

Everything is optional and set from the admin page (Notifiche tab and Configurazione). Messages are sent by a
background thread, so an answer from Alexa is never slowed down, and a failing channel never breaks anything: it is
only logged, without its URL or token. The same message is not repeated within two minutes, and at most
NOTIFY_MAX_ORA messages leave per hour."""
import collections, json, logging, os, queue, threading, time, urllib.error, urllib.request
from urllib.parse import urlsplit
import impostazioni
import lingua as L

log = logging.getLogger("alexa-ai-bridge")
EVENTI = impostazioni.EVENTI_NOTIFICHE
CANALI = ("ha", "telegram", "ntfy", "gotify", "webhook")
TITOLO = "Alexa AI Bridge"
RIPETIZIONE = 120          # seconds: the same text is not sent again within this time
UA = os.environ.get("HTTP_USER_AGENT", "alexa-ai-bridge/1.0")


def _lista(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _env(nome):
    return os.environ.get(nome, "").strip()


ATTIVE = _env("NOTIFY_ATTIVE").lower() not in ("0", "false", "no", "off")
SCELTI = impostazioni.eventi_notifiche(_env("NOTIFY_EVENTI"))
MAX_ORA = int(_env("NOTIFY_MAX_ORA") or "30")
HA_URL, HA_TOKEN = _env("HA_URL").rstrip("/"), _env("HA_TOKEN")
HA_UA = os.environ.get("HA_UA") or UA
HA_SERVIZI = [s[7:] if s.startswith("notify.") else s for s in _lista(_env("NOTIFY_HA"))]
TELEGRAM_URL = (_env("NOTIFY_TELEGRAM_URL") or "https://api.telegram.org").rstrip("/")
TELEGRAM_TOKEN, TELEGRAM_CHAT = _env("NOTIFY_TELEGRAM_TOKEN"), _env("NOTIFY_TELEGRAM_CHAT")
NTFY_URL, NTFY_TOKEN = _env("NOTIFY_NTFY_URL"), _env("NOTIFY_NTFY_TOKEN")
GOTIFY_URL, GOTIFY_TOKEN = _env("NOTIFY_GOTIFY_URL").rstrip("/"), _env("NOTIFY_GOTIFY_TOKEN")
WEBHOOK_URL, WEBHOOK_TOKEN = _env("NOTIFY_WEBHOOK_URL"), _env("NOTIFY_WEBHOOK_TOKEN")

ULTIME = collections.deque(maxlen=30)          # the last notifications, for the admin page
_coda = queue.Queue(maxsize=200)
_lock = threading.Lock()
_stato = {"inviate": collections.deque(), "recenti": {}, "avvisato": 0.0, "thread": None}


def configurati():
    """Which channels have what they need."""
    return {"ha": bool(HA_URL and HA_TOKEN and HA_SERVIZI), "telegram": bool(TELEGRAM_TOKEN and TELEGRAM_CHAT),
            "ntfy": bool(NTFY_URL), "gotify": bool(GOTIFY_URL and GOTIFY_TOKEN), "webhook": bool(WEBHOOK_URL)}


def _host(url):
    p = urlsplit(url or "")
    return "%s://%s" % (p.scheme, p.hostname) if p.hostname else ""


def dettagli():
    """What each channel sends to, for the page: never a token, never the secret part of an address."""
    return {"ha": ", ".join("notify." + s for s in HA_SERVIZI), "telegram": ("chat " + TELEGRAM_CHAT) if TELEGRAM_CHAT else "",
            "ntfy": _host(NTFY_URL), "gotify": _host(GOTIFY_URL), "webhook": _host(WEBHOOK_URL)}


def _post(url, dati, intestazioni, timeout=8):
    req = urllib.request.Request(url, dati, dict(intestazioni, **{"User-Agent": intestazioni.get("User-Agent", UA)}), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


def _json(d):
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def _invia(canale, testo, urgente):
    """One message on one channel; raises on failure."""
    j = {"Content-Type": "application/json"}
    if canale == "ha":
        for s in HA_SERVIZI:
            _post("%s/api/services/notify/%s" % (HA_URL, s), _json({"title": TITOLO, "message": testo}),
                  dict(j, Authorization="Bearer " + HA_TOKEN, **{"User-Agent": HA_UA}))
    elif canale == "telegram":
        _post("%s/bot%s/sendMessage" % (TELEGRAM_URL, TELEGRAM_TOKEN), _json({"chat_id": TELEGRAM_CHAT, "text": TITOLO + "\n" + testo}), j)
    elif canale == "ntfy":
        h = {"Title": TITOLO, "Priority": "4" if urgente else "3", "Tags": "warning" if urgente else "house",
             "Content-Type": "text/plain; charset=utf-8"}
        if NTFY_TOKEN:
            h["Authorization"] = "Bearer " + NTFY_TOKEN
        _post(NTFY_URL, testo.encode("utf-8"), h)
    elif canale == "gotify":
        _post(GOTIFY_URL + "/message", _json({"title": TITOLO, "message": testo, "priority": 8 if urgente else 5}),
              dict(j, **{"X-Gotify-Key": GOTIFY_TOKEN}))
    elif canale == "webhook":
        h = dict(j, Authorization="Bearer " + WEBHOOK_TOKEN) if WEBHOOK_TOKEN else j
        # "text" for Slack and most tools, "content" for Discord, the rest for whoever wants the details
        _post(WEBHOOK_URL, _json({"title": TITOLO, "text": "%s: %s" % (TITOLO, testo), "content": "%s: %s" % (TITOLO, testo),
                                  "message": testo, "urgente": urgente, "t": int(time.time())}), h)


def _errore(e):
    """Why a channel failed, without its address (a Telegram URL holds the token, a webhook URL often too)."""
    if isinstance(e, urllib.error.HTTPError):
        return "HTTP %d" % e.code
    if isinstance(e, urllib.error.URLError):
        return str(getattr(e.reason, "strerror", None) or type(e.reason).__name__)[:80]
    return type(e).__name__


def _consegna(evento, testo, urgente, canali=None):
    esiti = {}
    for c, ok in configurati().items():
        if not ok or (canali is not None and c not in canali):
            continue
        try:
            _invia(c, testo, urgente)
            esiti[c] = "ok"
        except Exception as e:
            esiti[c] = _errore(e)
            log.warning("notification on %s not sent: %s", c, esiti[c])
    ULTIME.append({"t": time.time(), "evento": evento, "testo": testo, "esiti": esiti})
    return esiti


def _lavora():
    while True:
        voce = _coda.get()
        try:
            _consegna(*voce)
        except Exception as e:                  # never let the thread die
            log.warning("notification: %s", type(e).__name__)
        finally:
            _coda.task_done()


def notifica(evento, testo, urgente=False):
    """Send this message in the background, if the event (or one of these events) is chosen and a channel is set.
    Never blocks, never raises."""
    try:
        evento = next((e for e in ((evento,) if isinstance(evento, str) else evento) if e in SCELTI), None)
        if not (ATTIVE and evento and any(configurati().values())):
            return False
        testo = " ".join(str(testo).split())[:600]
        with _lock:
            ora, s = time.time(), _stato
            s["recenti"] = {k: t for k, t in s["recenti"].items() if ora - t < RIPETIZIONE}
            if testo in s["recenti"]:
                return False
            while s["inviate"] and ora - s["inviate"][0] > 3600:
                s["inviate"].popleft()
            if len(s["inviate"]) >= MAX_ORA:
                if ora - s["avvisato"] > 3600:
                    s["avvisato"] = ora
                    log.warning("notifications: more than %d in an hour, the next ones are not sent", MAX_ORA)
                return False
            s["recenti"][testo] = ora
            s["inviate"].append(ora)
            if s["thread"] is None or not s["thread"].is_alive():
                s["thread"] = threading.Thread(target=_lavora, daemon=True, name="notifiche")
                s["thread"].start()
        _coda.put_nowait((evento, testo, urgente))
        return True
    except Exception as e:
        log.warning("notification not queued: %s", type(e).__name__)
        return False


def attendi(timeout=5.0):
    """Wait (at most timeout seconds) until the queued notifications are sent: before a restart, and in the tests."""
    fine = time.time() + timeout
    while _coda.unfinished_tasks and time.time() < fine:
        time.sleep(0.02)
    return not _coda.unfinished_tasks


def prova(canali=None):
    """A test message on every configured channel (or only on these), now; whatever the events and limits say."""
    return _consegna("prova", L.t("n_prova"), False, canali)


def servizi_ha():
    """The notify services Home Assistant offers (mobile_app_..., telegram, persistent_notification...)."""
    req = urllib.request.Request(HA_URL + "/api/services", headers={"Authorization": "Bearer " + HA_TOKEN, "User-Agent": HA_UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        d = json.load(r)
    out = []
    for voce in d if isinstance(d, list) else []:
        if isinstance(voce, dict) and voce.get("domain") == "notify" and isinstance(voce.get("services"), dict):
            out += [s for s in voce["services"] if isinstance(s, str)]
    return sorted(set(out))
