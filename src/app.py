"""Alexa AI Bridge - web service for a custom Alexa skill that talks to any AI model.

Verifies every request from Amazon (signature, certificate chain, timestamp, skill ID), asks the model
(Anthropic Messages API or any OpenAI-compatible endpoint, see llm.py) and speaks the answer.
See docs/ for the full design. User-facing strings are Italian: the skill is it-IT."""
import os, re, json, time, base64, logging, posixpath, threading, urllib.request, warnings
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from xml.sax.saxutils import escape
from flask import Flask, request, jsonify, abort
import certifi
from cryptography import x509
from cryptography.x509 import DNSName
from cryptography.x509.verification import PolicyBuilder, Store
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.utils import CryptographyDeprecationWarning
import llm
import web_search as web
import home_tools as casa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("alexa-ai-bridge")
if not os.environ.get("SKILL_ID", "").strip():
    raise SystemExit("SKILL_ID is not set: copy .env.example to .env and fill it in (see docs/setup.md)")

SKILL_ID = os.environ["SKILL_ID"].strip()
SYSTEM = os.environ.get("SYSTEM_PROMPT",
    "Sei un assistente vocale in italiano. Rispondi in modo naturale e breve, al massimo 2-3 frasi, "
    "senza elenchi, senza markdown, senza emoji: la risposta viene letta ad alta voce.")
MAXH = 6

# ---------- Amazon request verification (mandatory for a self-hosted skill endpoint)
def _radici():
    with open(certifi.where(), "rb") as f:
        pem = f.read()
    out = []
    with warnings.catch_warnings():   # a few old roots have non-RFC serial numbers: harmless, but noisy
        warnings.simplefilter("ignore", CryptographyDeprecationWarning)
        for blocco in re.findall(rb"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", pem, re.S):
            try:
                out.append(x509.load_pem_x509_certificate(blocco))
            except Exception:
                pass
    return Store(out)

ROOTS = _radici()
_cache = {}

def url_cert_ok(u):
    try:
        p = urlsplit(u)
        porta = p.port
    except ValueError:
        return False
    if p.scheme.lower() != "https" or (p.hostname or "").lower() != "s3.amazonaws.com":
        return False
    if porta not in (None, 443):
        return False
    return posixpath.normpath(p.path).startswith("/echo.api/")

def scarica(u):
    return urllib.request.urlopen(u, timeout=5).read()

def cert_amazon(u):
    c = _cache.get(u)
    if c and c[1] > time.time():
        return c[0]
    leaf = verifica_catena(x509.load_pem_x509_certificates(scarica(u)))
    _cache[u] = (leaf, time.time() + 3600)
    return leaf

def verifica_catena(certs, quando=None):
    """Validate Amazon's chain (leaf first) against the public roots: SAN echo-api.amazon.com, server auth, dates."""
    pb = PolicyBuilder().store(ROOTS)
    if quando is not None:
        pb = pb.time(quando)
    pb.build_server_verifier(DNSName("echo-api.amazon.com")).verify(certs[0], certs[1:])
    return certs[0]

def richiesta_valida(body, headers, dati):
    u, s = headers.get("SignatureCertChainUrl", ""), headers.get("Signature-256", "")
    if not u or not s or not url_cert_ok(u):
        return "intestazioni di firma mancanti o non valide"
    try:
        cert_amazon(u).public_key().verify(base64.b64decode(s), body, padding.PKCS1v15(), hashes.SHA256())
    except Exception as e:
        return "firma non valida: %s" % e
    try:
        ts = datetime.fromisoformat(dati["request"]["timestamp"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        return "timestamp mancante"
    if abs((datetime.now(timezone.utc) - ts).total_seconds()) > 150:
        return "richiesta troppo vecchia"
    app_id = (dati.get("session") or {}).get("application", {}).get("applicationId") \
        or dati.get("context", {}).get("System", {}).get("application", {}).get("applicationId")
    if app_id != SKILL_ID:
        return "skill diversa"
    return None

# ---------- model
ISTRUZIONI_TURNO = os.environ.get("ISTRUZIONI_TURNO",
    "[Sei l'assistente vocale di casa su Alexa, non un assistente di programmazione: non parlare di codice o di file. "
    "Rispondi in italiano parlato, in modo naturale, al massimo 3-4 frasi, senza elenchi, senza markdown e senza emoji: "
    "la risposta viene letta ad alta voce. Rispondi direttamente, senza premesse. La frase arriva dal riconoscimento "
    "vocale e spesso manca la parola iniziale (perché, come, cosa, quanto, quando, dove, chi): trattala sempre come "
    "una domanda o una richiesta, mai come un'affermazione da confermare.]")

WEB = web.backend(llm.API)          # None | native | searxng | brave | tavily
HOME_TZ = web.HOME_TZ
GIORNI = ["lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

try:
    _TZ = ZoneInfo(HOME_TZ)
except Exception:
    log.warning("unknown HOME_TIMEZONE=%r: using UTC+1 (install tzdata or fix the name)", HOME_TZ)
    _TZ = timezone(timedelta(hours=1))

def adesso():
    n = datetime.now(_TZ)
    return "%s %d %s %d, ore %02d:%02d" % (GIORNI[n.weekday()], n.day, MESI[n.month - 1], n.year, n.hour, n.minute)

def web_attivo():
    if WEB == "native":
        return llm.STATO["web_nativo"]
    return bool(WEB) and llm.STATO["strumenti"]

def casa_attiva():
    return casa.ATTIVO and llm.STATO["strumenti"]

def con_istruzioni(history):
    """Voice rules, date and tool hints go in the last user turn (not only in the system prompt: some gateways
    replace or prepend their own). They are never stored in the conversation."""
    h = [dict(m) for m in history]
    if h and h[-1]["role"] == "user":
        dove = ("casa e' a %s. " % web.HOME_CITY) if web.HOME_CITY else ""
        extra = ("[Oggi e' %s; %s" % (adesso(), dove)) + (
            "Se serve un'informazione aggiornata (meteo, notizie, risultati, orari, prezzi, eventi) cercala sul web; "
            "non dire che stai cercando e non leggere indirizzi web." if web_attivo() else "") + (
            " Puoi leggere e comandare la casa con gli strumenti riepilogo_casa, cerca_in_casa ed esegui_azione: "
            "per comandare trova prima l'entity_id con cerca_in_casa; dopo un'azione di' in poche parole cosa hai fatto; "
            "porta, portone e antifurto non si possono comandare da qui." if casa_attiva() else "") + "]"
        h[-1]["content"] = ISTRUZIONI_TURNO + "\n" + extra + "\n\n" + h[-1]["content"]
    return h

def esegui_strumento(nome, argomenti):
    if nome == web.STRUMENTO["name"]:
        return web.cerca(argomenti.get("query", ""), WEB)
    return casa.esegui_strumento(nome, argomenti)

def ask_llm(history, timeout=60):
    ultima = history[-1]["content"] if history and history[-1]["role"] == "user" else ""
    casa.imposta_domanda(ultima if isinstance(ultima, str) else "")
    strumenti = ([web.STRUMENTO] if WEB not in (None, "native") else []) + (casa.STRUMENTI if casa.ATTIVO else [])
    return llm.chiedi(SYSTEM, con_istruzioni(history), strumenti, esegui_strumento,
                      nativo=web.NATIVO if WEB == "native" else None, timeout=timeout)

def pulisci(t):
    t = re.sub(r"\[azioni eseguite:[^\]]*\]", "", t)
    t = re.sub(r"[*_#`>|]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 700:
        t = t[:700].rsplit(" ", 1)[0] + "."
    return t

def risposta(testo, ascolta=None, attr=None, fine=False):
    r = {"outputSpeech": {"type": "SSML", "ssml": "<speak>%s</speak>" % escape(testo)}, "shouldEndSession": fine}
    if ascolta and not fine:
        r["reprompt"] = {"outputSpeech": {"type": "SSML", "ssml": "<speak>%s</speak>" % escape(ascolta)}}
    return {"version": "1.0", "sessionAttributes": attr or {}, "response": r}

# ---------- slow answers: the model keeps working in the background, the user asks "allora?" (so?) to hear it
ATTESA = float(os.environ.get("ATTESA_MAX", "6.0"))            # beyond this, Alexa says "I'm thinking, ask me in a moment"
TIMEOUT_LUNGO = float(os.environ.get("LLM_TIMEOUT_LUNGO", "120"))
CONSERVA = 900                                                # pending answers are kept for 15 minutes
PAROLE_ATTESA = {"allora", "e allora", "allora che mi dici", "hai finito", "sei pronto", "quindi", "pronto",
                 "fatto", "vai", "ci sei", "eccomi", "si", "sì", "la risposta", "dimmi la risposta", "dammi la risposta"}
_lavori, _lock = {}, threading.Lock()

def pendente(uid):
    """The pending job of this user, if any and not older than CONSERVA."""
    with _lock:
        lav = _lavori.get(uid)
        if lav and time.time() - lav["t"] > CONSERVA:
            del _lavori[uid]
            return None
        return lav

def scarta(uid, lav):
    """Forget this job, but only if it is still the user's current one (another Echo may have asked since)."""
    with _lock:
        if _lavori.get(uid) is lav:
            del _lavori[uid]

def utente(d):
    return ((d.get("session") or {}).get("user") or {}).get("userId") \
        or d.get("context", {}).get("System", {}).get("user", {}).get("userId") or "anonimo"

def calcola(lav):
    t0 = time.time()
    casa.azzera_azioni()
    try:
        r = pulisci(ask_llm(lav["hist"], timeout=TIMEOUT_LUNGO))
        if not r and casa.azioni_fatte():
            r = "Fatto."      # the actions ran: asking again could repeat them (a toggle would undo itself)
        elif not r:
            log.info("risposta vuota, riprovo")
            r = pulisci(ask_llm(lav["hist"], timeout=TIMEOUT_LUNGO))
        if r:
            lav["risposta"] = r
            lav["azioni"] = casa.azioni_fatte()
            log.info("domanda risposta in %.1f s", time.time() - t0)
        else:
            lav["errore"] = "risposta vuota"
    except Exception as e:
        lav["errore"] = str(e)[:200]
    if lav["errore"]:
        log.warning("modello: %s (%.1f s)", lav["errore"], time.time() - t0)
    lav["evento"].set()

def avvia(uid, hist):
    lav = {"hist": hist, "evento": threading.Event(), "risposta": None, "errore": None, "t": time.time()}
    with _lock:
        for k in [k for k, v in _lavori.items() if time.time() - v["t"] > CONSERVA]:
            del _lavori[k]
        _lavori[uid] = lav
    threading.Thread(target=calcola, args=(lav,), daemon=True).start()
    return lav

def consegna(uid, lav, attr, inizio=""):
    with _lock:
        if _lavori.get(uid) is lav:
            del _lavori[uid]
    if lav["risposta"]:
        nota = ("\n[azioni eseguite: %s]" % "; ".join(lav["azioni"])) if lav.get("azioni") else ""
        attr["h"] = (lav["hist"] + [{"role": "assistant", "content": lav["risposta"] + nota}])[-MAXH:]
        return risposta(inizio + lav["risposta"], "Altro?", attr)
    return risposta("Non sono riuscito a rispondere. Riprova a farmi la domanda.", "Cosa vuoi sapere?", attr)

def ancora(attr, prima_volta):
    if prima_volta:
        return risposta("Ci sto pensando. Dimmi allora tra qualche secondo.", "Vuoi la risposta? Dimmi allora.", attr)
    return risposta("Ci sto ancora pensando. Dimmi allora tra qualche secondo.", "Vuoi la risposta? Dimmi allora.", attr)

def chiedi_risposta(uid, attr, resta):
    lav = pendente(uid)
    if not lav:
        return risposta("Non ho risposte in sospeso. Cosa vuoi sapere?", "Cosa vuoi sapere?", attr)
    if lav["evento"].wait(timeout=max(resta, 0)):
        return consegna(uid, lav, attr)
    return ancora(attr, False)

AIUTO = "Fammi una domanda, per esempio: come si cucina il risotto. Se ci metto un po', dimmi allora per sentire la risposta. Per uscire di' basta."

def gestisci(d, t_req=None):
    t_req = t_req or time.time()
    resta = lambda: ATTESA - (time.time() - t_req)
    rq = d.get("request", {})
    tipo = rq.get("type")
    attr = (d.get("session") or {}).get("attributes") or {}
    uid = utente(d)
    if tipo == "LaunchRequest":
        lav = pendente(uid)
        finito = bool(lav) and lav["evento"].is_set()     # read once: the job may finish meanwhile
        if finito and lav["risposta"]:
            return consegna(uid, lav, attr, "Ho la risposta alla domanda di prima. ")
        if finito:
            scarta(uid, lav)    # failed in the background: forget it, or a later "si'" would hear the error
        elif lav:
            return risposta("Sto ancora pensando alla domanda di prima. Dimmi allora tra poco, oppure fammi un'altra domanda.",
                            "Cosa vuoi fare?", attr)
        return risposta("Dimmi pure.", "Cosa vuoi sapere?", attr)
    if tipo in ("SessionEndedRequest", "System.ExceptionEncountered"):   # Alexa ignores any speech here
        if tipo == "System.ExceptionEncountered":
            log.warning("Alexa reported an error: %s", json.dumps(rq.get("error"), ensure_ascii=False)[:300])
        return {"version": "1.0", "response": {}}
    if tipo != "IntentRequest":
        return risposta("Ciao!", fine=True)
    nome = rq.get("intent", {}).get("name")
    if nome in ("AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.NavigateHomeIntent"):
        return risposta("Ciao!", fine=True)
    if nome == "AMAZON.HelpIntent":
        return risposta(AIUTO, "Cosa vuoi sapere?", attr)
    lav = pendente(uid)
    in_sospeso = lav is not None
    q_sino = None
    if nome == "AMAZON.YesIntent" and not in_sospeso:
        q_sino = "si'"      # answer to a question from the model (e.g. confirming an action)
    elif nome == "AMAZON.NoIntent" and not in_sospeso:
        q_sino = "no"
    elif nome in ("AttesaIntent", "AMAZON.YesIntent"):
        return chiedi_risposta(uid, attr, resta())
    if nome == "AMAZON.NoIntent" and not q_sino:
        scarta(uid, lav)
        return risposta("Va bene. Altro?", "Cosa vuoi sapere?", attr)
    if nome not in ("AskIntent", "FraseBreveIntent") and not q_sino:
        return risposta("Non ho capito. " + AIUTO, "Cosa vuoi sapere?", attr)
    slots = rq.get("intent", {}).get("slots") or {}
    q = q_sino or (slots.get("query") or {}).get("value") or (slots.get("frase") or {}).get("value")
    if not q:
        return risposta("Non ho capito, puoi ripetere?", "Puoi ripetere?", attr)
    if q.strip().lower().strip("?!. ") in PAROLE_ATTESA and in_sospeso:
        return chiedi_risposta(uid, attr, resta())
    lav = avvia(uid, (attr.get("h") or [])[-MAXH:] + [{"role": "user", "content": q}])
    if lav["evento"].wait(timeout=max(resta(), 0)):
        return consegna(uid, lav, attr)
    log.info("risposta lenta: la tengo da parte")
    return ancora(attr, True)

app = Flask(__name__)

@app.post("/alexa")
def alexa():
    t_req = time.time()
    body = request.get_data()
    try:
        d = json.loads(body)
    except Exception:
        abort(400)
    errore = richiesta_valida(body, request.headers, d)
    if errore:
        log.warning("richiesta rifiutata: %s", errore)
        abort(400)
    return jsonify(gestisci(d, t_req))

@app.get("/health")
def health():
    return jsonify(ok=True)
