"""Admin page: status and checks, conversation history, a test chat, settings and recent log.

Off unless ADMIN_PASSWORD is set (12 characters or more). Reachable directly (the server itself, or the home network
with BRIDGE_BIND) and, only with ADMIN_PUBLIC=on, through a reverse proxy: a request that carries proxy headers is
refused otherwise, whatever the proxy is. See docs/admin.md."""
import collections, hashlib, hmac, json, logging, os, signal, subprocess, sys, threading, time
from flask import Blueprint, abort, jsonify, request, send_from_directory, session
from flask.sessions import SecureCookieSessionInterface
import impostazioni

log = logging.getLogger("alexa-ai-bridge")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ATTIVO = len(PASSWORD) >= 12
if PASSWORD and not ATTIVO:
    log.warning("ADMIN_PASSWORD is shorter than 12 characters: the admin page is off")
PUBBLICO = os.environ.get("ADMIN_PUBLIC", "off").strip().lower() == "on"
VERSIONE = os.environ.get("APP_VERSION", "dev")
AVVIO = time.time()
CARTELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin")
try:
    _N = int(os.environ.get("ADMIN_HISTORY", "").strip() or "100")
except ValueError:
    raise SystemExit("ADMIN_HISTORY must be a number (0 turns the history off)") from None
STORICO = collections.deque(maxlen=max(_N, 1))
STORIA_ATTIVA = _N > 0
REGISTRO = collections.deque(maxlen=300)
RITARDO = 1.0            # seconds added to every wrong password; logins are checked one at a time
DURATA = 12 * 3600       # absolute lifetime of a session
INTESTAZIONI_PROXY = ("X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "Forwarded", "X-Real-IP")
_lock, _lock_registro, _lock_login, _lock_salva = threading.Lock(), threading.Lock(), threading.Lock(), threading.Lock()

bp = Blueprint("admin", __name__)


# ---------- what the page shows: history and log
class _Cattura(logging.Handler):
    def emit(self, r):
        with _lock_registro:
            REGISTRO.append({"t": r.created, "livello": r.levelname, "testo": r.getMessage()[:1000]})


def righe_registro():
    with _lock_registro:
        return list(REGISTRO)


logging.getLogger("alexa-ai-bridge").addHandler(_Cattura(logging.INFO))


def registra(lav, uid, origine):
    """Called by the service when a question is answered (or fails)."""
    if not STORIA_ATTIVA:
        return
    domanda = lav["hist"][-1]["content"] if lav.get("hist") else ""
    with _lock:
        STORICO.append({"t": lav["t"], "utente": hashlib.sha256(uid.encode()).hexdigest()[:8], "origine": origine,
                        "domanda": domanda, "risposta": lav.get("risposta"), "errore": lav.get("errore"),
                        "durata": round(lav.get("durata") or 0, 1), "azioni": lav.get("azioni") or []})


# ---------- authentication
SEGRETO = impostazioni.segreto()          # random, never derived from the password
_FILE_REVOCATE = os.path.join(impostazioni.DATA_DIR, "admin-sessions-revoked.json")


def _impronta():
    """Ties a session to the current password: changing ADMIN_PASSWORD logs everyone out."""
    return hmac.new(SEGRETO, PASSWORD.encode(), hashlib.sha256).hexdigest()[:16]


def _leggi_revocate():
    try:
        with open(_FILE_REVOCATE, encoding="utf-8") as f:
            d = json.load(f)
        return {k: float(v) for k, v in d.items() if float(v) > time.time()} if isinstance(d, dict) else {}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


REVOCATE = _leggi_revocate()   # session id -> when it would have expired anyway


def _revoca(sid):
    REVOCATE[sid] = time.time() + DURATA
    for k in [k for k, v in REVOCATE.items() if v < time.time()]:
        del REVOCATE[k]
    if impostazioni.scrivibile():
        try:
            fd = os.open(_FILE_REVOCATE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(REVOCATE, f)
        except OSError:
            pass


def autenticato():
    return (bool(session.get("admin")) and session.get("pw") == _impronta() and session.get("sid") not in REVOCATE
            and 0 <= time.time() - float(session.get("login") or 0) < DURATA)


_tentativi = collections.defaultdict(list)


def _client():
    # without ADMIN_PUBLIC no proxied request gets here; with it, the last hop is the one our proxy added
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[-1].strip() if xff and PUBBLICO else "") or request.remote_addr or "?"


def _bloccato(chi):
    ora = time.time()
    with _lock:
        for k in list(_tentativi):
            _tentativi[k] = [t for t in _tentativi[k] if ora - t < 900]
            if not _tentativi[k]:
                del _tentativi[k]
        return len(_tentativi.get(chi, [])) >= 5


@bp.before_request
def _controlli():
    if not ATTIVO:
        abort(404)
    if not PUBBLICO and any(h in request.headers for h in INTESTAZIONI_PROXY):
        abort(404)               # reached through a reverse proxy, but the page is not meant to be published
    if request.path.startswith("/admin/api/") and request.endpoint not in ("admin.login", "admin.sessione"):
        if not autenticato():
            return jsonify(errore="non autenticato"), 401
        if request.method != "GET" and not hmac.compare_digest(request.headers.get("X-CSRF", ""), session.get("csrf", "")):
            return jsonify(errore="token CSRF non valido"), 403


@bp.after_request
def _intestazioni(r):
    r.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store"
    return r


@bp.get("/admin")
@bp.get("/admin/")
def pagina():
    return send_from_directory(CARTELLA, "index.html")


@bp.get("/admin/<any('app.js','app.css','icon.svg'):nome>")
def risorsa(nome):
    return send_from_directory(CARTELLA, nome)


@bp.get("/admin/api/sessione")
def sessione():
    ok = autenticato()
    return jsonify(autenticato=ok, csrf=session.get("csrf") if ok else None)


@bp.post("/admin/api/login")
def login():
    chi = _client()
    if _bloccato(chi):
        log.warning("admin: too many failed logins (%s)", chi)
        return jsonify(errore="Troppi tentativi: riprova tra 15 minuti."), 429
    d = request.get_json(silent=True)
    pw = d.get("password", "") if isinstance(d, dict) else ""
    with _lock_login:            # one check at a time: at most one wrong password per RITARDO, from everyone together
        if not isinstance(pw, str) or not hmac.compare_digest(pw.encode("utf-8", "replace"), PASSWORD.encode()):
            with _lock:
                _tentativi[chi].append(time.time())
            log.warning("admin: wrong password (%s)", chi)
            time.sleep(RITARDO)
            return jsonify(errore="Password errata."), 401
    session.clear()
    session.permanent = True
    session.update(admin=True, csrf=os.urandom(16).hex(), sid=os.urandom(16).hex(), login=time.time(), pw=_impronta())
    log.info("admin: login (%s)", chi)
    return jsonify(csrf=session["csrf"])


@bp.post("/admin/api/logout")
def logout():
    _revoca(session.get("sid", ""))      # the cookie stops working even if someone kept a copy
    session.clear()
    return jsonify(ok=True)


# ---------- status and checks
def _a():
    import app
    return app


@bp.get("/admin/api/stato")
def stato():
    A = _a()
    with _lock:
        voci = list(STORICO)
    durate = [v["durata"] for v in voci if v["risposta"]]
    return jsonify(
        versione=VERSIONE, avvio=AVVIO, ora=time.time(),
        modello={"api": A.llm.API, "url": impostazioni.mascherato(A.llm.BASE) or A.llm.BASE, "nome": A.llm.MODEL, "chiave": bool(A.llm.KEY)},
        web={"backend": A.WEB, "attiva": A.web_attivo()},
        casa={"configurata": bool(A.casa.HA and A.casa.TOKEN), "attiva": A.casa_attiva(), "url": impostazioni.mascherato(A.casa.HA) or A.casa.HA},
        adattamenti={k: v for k, v in A.llm.STATO.items()},
        attesa=A.ATTESA, in_sospeso=len(A._lavori),
        statistiche={"domande": len(voci), "errori": sum(1 for v in voci if v["errore"]),
                     "lente": sum(1 for v in voci if v["durata"] > A.ATTESA),
                     "durata_media": round(sum(durate) / len(durate), 1) if durate else None,
                     "azioni": sum(len(v["azioni"]) for v in voci)},
        avvisi=sum(1 for r in righe_registro() if r["livello"] in ("WARNING", "ERROR", "CRITICAL")),
        storico_attivo=STORIA_ATTIVA, configurabile=impostazioni.scrivibile())


def _cronometra(f):
    t = time.time()
    try:
        return {"ok": True, "esito": f(), "durata": round(time.time() - t, 1)}
    except Exception as e:
        return {"ok": False, "esito": str(e)[:500], "durata": round(time.time() - t, 1)}


@bp.post("/admin/api/prova/<any(modello,web,casa):cosa>")
def prova(cosa):
    A = _a()
    if cosa == "modello":
        r = _cronometra(lambda: A.ask_llm([{"role": "user", "content": "Rispondi solo con: tutto funziona."}], timeout=30)
                        or "(risposta vuota)")
    elif cosa == "web":
        if not A.WEB:
            return jsonify(ok=False, esito="Ricerca web spenta o non configurata.", durata=0)
        citta = A.web.HOME_CITY or "Roma"
        if A.WEB == "native":
            r = _cronometra(lambda: A.ask_llm([{"role": "user", "content": "che tempo fa oggi a %s? cercalo sul web" % citta}], timeout=60))
        else:
            r = _cronometra(lambda: A.web.cerca("meteo %s oggi" % citta, A.WEB))
            r["ok"] = r["ok"] and not r["esito"].startswith("Ricerca web non disponibile")
    else:
        if not A.casa.ATTIVO:
            return jsonify(ok=False, esito="Home Assistant non configurato (HA_URL e HA_TOKEN).", durata=0)
        A.casa._cache["t"] = 0
        r = _cronometra(A.casa.riepilogo)
    log.info("admin: check %s -> %s", cosa, "ok" if r["ok"] else "error")
    return jsonify(r)


@bp.get("/admin/api/storico")
def storico():
    with _lock:
        return jsonify(voci=list(reversed(STORICO)), attivo=STORIA_ATTIVA)


@bp.delete("/admin/api/storico")
def svuota_storico():
    with _lock:
        STORICO.clear()
    return jsonify(ok=True)


@bp.get("/admin/api/registro")
def registro():
    return jsonify(voci=list(reversed(righe_registro())))


# ---------- test chat: the same pipeline as Alexa, home actions simulated unless asked otherwise
@bp.post("/admin/api/chat")
def chat():
    A = _a()
    d = request.get_json(silent=True)
    d = d if isinstance(d, dict) else {}
    testo = str(d.get("testo") or "").strip()[:1000]
    if not testo:
        return jsonify(errore="Scrivi una domanda."), 400
    storia = d.get("storia") if isinstance(d.get("storia"), list) else []
    storia = [{"role": m["role"], "content": m["content"][:4000]} for m in storia if isinstance(m, dict)
              and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-A.MAXH:]
    if storia and storia[0]["role"] != "user":
        storia = storia[1:]
    lav = {"hist": storia + [{"role": "user", "content": testo}], "t": time.time(), "risposta": None, "errore": None}
    A.casa.azzera_azioni()
    A.casa.imposta_simulazione(d.get("simula", True) is not False)
    try:
        r = A.pulisci(A.ask_llm(lav["hist"], timeout=A.TIMEOUT_LUNGO))
        lav["risposta"] = r or None
        lav["errore"] = None if r else "risposta vuota"
    except Exception as e:
        lav["errore"] = str(e)[:300]
    finally:
        A.casa.imposta_simulazione(False)
    lav["durata"] = time.time() - lav["t"]
    lav["azioni"] = A.casa.azioni_fatte()
    registra(lav, "admin-chat", "chat")
    nota = ("\n[azioni eseguite: %s]" % "; ".join(lav["azioni"])) if lav["azioni"] else ""
    return jsonify(risposta=lav["risposta"], errore=lav["errore"], durata=round(lav["durata"], 1), azioni=lav["azioni"],
                   lenta=lav["durata"] > A.ATTESA,
                   storia=(lav["hist"] + ([{"role": "assistant", "content": lav["risposta"] + nota}] if lav["risposta"] else []))[-A.MAXH:])


# ---------- settings
@bp.get("/admin/api/impostazioni")
def leggi_impostazioni():
    return jsonify(campi=impostazioni.valori(), configurabile=impostazioni.scrivibile(), cartella=impostazioni.DATA_DIR)


def _riavvia(server):
    """Ask gunicorn for a graceful reload: a new worker imports the service again with the new settings."""
    if server.startswith("gunicorn"):
        threading.Timer(0.5, os.kill, (os.getppid(), signal.SIGHUP)).start()
        return True
    return False


TESTI_LUNGHI = ("SYSTEM_PROMPT", "ISTRUZIONI_TURNO")
# changing where requests go means re-entering the secret sent there: a stolen session cannot redirect a stored key
SEGRETO_DI = {"LLM_BASE_URL": "LLM_API_KEY", "HA_URL": "HA_TOKEN"}


def _pulisci_valore(k, v, tipi):
    """The value to store, or raises ValueError with a message for the page."""
    if isinstance(v, bool) or not isinstance(v, (str, int, float)):
        raise ValueError("Valore non valido per %s." % tipi[k][0])
    v = str(v)
    if len(v) > 20000:
        raise ValueError("%s e' troppo lungo." % tipi[k][0])
    ammessi = "\n\t" if k in TESTI_LUNGHI else ""
    if any(ord(c) < 32 and c not in ammessi for c in v) or "\x7f" in v:
        raise ValueError("%s contiene caratteri non ammessi." % tipi[k][0])
    try:
        v.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("%s contiene caratteri non validi." % tipi[k][0]) from None
    v = v if k in TESTI_LUNGHI else v.strip()
    if tipi[k][1] == "number":
        v = v.replace(",", ".")
    if tipi[k][1] == "select" and v not in tipi[k][2]:
        raise ValueError("%s: valore non previsto (%s)." % (tipi[k][0], ", ".join(o or "automatico" for o in tipi[k][2])))
    errore = impostazioni.errore_valore(k, v)
    if errore:
        raise ValueError(errore)
    return v


@bp.post("/admin/api/impostazioni")
def salva_impostazioni():
    if not impostazioni.scrivibile():
        return jsonify(errore="La cartella %s non e' scrivibile: monta il volume dei dati (vedi docs/admin.md)." % impostazioni.DATA_DIR), 409
    d = request.get_json(silent=True)
    cambi = d.get("valori") if isinstance(d, dict) else None
    if not isinstance(cambi, dict):
        return jsonify(errore="Richiesta non valida."), 400
    tipi = {c[0]: (c[2], c[3], c[4]) for c in impostazioni.CAMPI}
    with _lock_salva:
        nuovi = impostazioni.leggi()            # the file, not what was loaded at start: two saves in a row both count
        for k, v in cambi.items():
            if k not in impostazioni.NOMI:
                return jsonify(errore="Impostazione sconosciuta: %s" % k), 400
            if v is None:
                nuovi.pop(k, None)              # back to the value from .env
                continue
            try:
                nuovi[k] = _pulisci_valore(k, v, tipi)
            except ValueError as e:
                return jsonify(errore=str(e)), 400
        for url, segreto in SEGRETO_DI.items():
            nuovo_url = nuovi.get(url, impostazioni.BASE.get(url) if url in impostazioni.OVERRIDE else os.environ.get(url, ""))
            if url in cambi and (nuovo_url or "") != os.environ.get(url, "") and segreto not in cambi:
                return jsonify(errore="Hai cambiato %s: inserisci di nuovo %s (anche vuoto, se non serve) nello stesso salvataggio."
                               % (tipi[url][0], tipi[segreto][0])), 400
        # the new settings must start the service: same checks as at startup, in a separate process
        env = dict(impostazioni.ambiente_con(nuovi), DATA_DIR=os.path.join(impostazioni.DATA_DIR, "nessun-file"))  # not the old file
        try:
            prova = subprocess.run([sys.executable, "-c", "import app"], cwd=os.path.dirname(os.path.abspath(__file__)),
                                   env=env, capture_output=True, text=True, timeout=60)
        except (OSError, ValueError) as e:
            return jsonify(errore="Impostazioni non valide: %s" % str(e)[:200]), 400
        if prova.returncode != 0:
            righe = [r for r in prova.stderr.strip().splitlines() if r.strip()]
            return jsonify(errore="Impostazioni non valide: " + (righe[-1] if righe else "errore all'avvio")[:300]), 400
        impostazioni.salva(nuovi)
    log.info("admin: settings saved (%s)", ", ".join(sorted(cambi)) or "none")
    return jsonify(ok=True, riavvio=_riavvia(request.environ.get("SERVER_SOFTWARE", "")))


class _Sessione(SecureCookieSessionInterface):
    def get_cookie_secure(self, app):
        # Secure when the page is reached over HTTPS (directly or through the proxy); plain http on the home network still works
        return request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"


def configura(flask_app):
    flask_app.session_interface = _Sessione()
    flask_app.secret_key = SEGRETO
    flask_app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict", SESSION_COOKIE_NAME="aab_admin",
                            PERMANENT_SESSION_LIFETIME=DURATA, SESSION_REFRESH_EACH_REQUEST=False)
    flask_app.register_blueprint(bp)
