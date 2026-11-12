"""Admin page: status and checks, conversation history, a test chat, settings and recent log.

Off unless ADMIN_PASSWORD is set (12 characters or more). Where it can be reached is decided outside the service:
the published port (BRIDGE_BIND) and the reverse proxy (ADMIN_PUBLIC for the bundled Caddy). See docs/admin.md."""
import collections, hashlib, hmac, logging, os, signal, subprocess, sys, threading, time
from flask import Blueprint, abort, jsonify, request, send_from_directory, session
from flask.sessions import SecureCookieSessionInterface
import impostazioni

log = logging.getLogger("alexa-ai-bridge")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ATTIVO = len(PASSWORD) >= 12
if PASSWORD and not ATTIVO:
    log.warning("ADMIN_PASSWORD is shorter than 12 characters: the admin page is off")
VERSIONE = os.environ.get("APP_VERSION", "dev")
AVVIO = time.time()
CARTELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin")
try:
    _N = int(os.environ.get("ADMIN_HISTORY", "100"))
except ValueError:
    raise SystemExit("ADMIN_HISTORY must be a number (0 turns the history off)") from None
STORICO = collections.deque(maxlen=max(_N, 1))
STORIA_ATTIVA = _N > 0
REGISTRO = collections.deque(maxlen=300)
RITARDO = 1.0            # seconds added to every wrong password
_lock = threading.Lock()

bp = Blueprint("admin", __name__)


# ---------- what the page shows: history and log
class _Cattura(logging.Handler):
    def emit(self, r):
        REGISTRO.append({"t": r.created, "livello": r.levelname, "testo": r.getMessage()[:1000]})


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
def _chiave():
    return hashlib.sha256(("alexa-ai-bridge-admin:" + PASSWORD).encode()).digest()


_tentativi = collections.defaultdict(list)


def _client():
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[0].strip() if xff else "") or request.remote_addr or "?"


def _bloccato(chi):
    ora = time.time()
    for k in list(_tentativi):
        _tentativi[k] = [t for t in _tentativi[k] if ora - t < 900]
        if not _tentativi[k]:
            del _tentativi[k]
    return len(_tentativi.get(chi, [])) >= 5 or sum(len(v) for v in _tentativi.values()) >= 30


@bp.before_request
def _controlli():
    if not ATTIVO:
        abort(404)
    if request.path.startswith("/admin/api/") and request.endpoint not in ("admin.login", "admin.sessione"):
        if not session.get("admin"):
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
    return jsonify(autenticato=bool(session.get("admin")), csrf=session.get("csrf") if session.get("admin") else None)


@bp.post("/admin/api/login")
def login():
    chi = _client()
    if _bloccato(chi):
        log.warning("admin: too many failed logins (%s)", chi)
        return jsonify(errore="Troppi tentativi: riprova tra 15 minuti."), 429
    pw = (request.get_json(silent=True) or {}).get("password", "")
    if not isinstance(pw, str) or not hmac.compare_digest(pw.encode(), PASSWORD.encode()):
        _tentativi[chi].append(time.time())
        log.warning("admin: wrong password (%s)", chi)
        time.sleep(RITARDO)
        return jsonify(errore="Password errata."), 401
    session.clear()
    session.permanent = True
    session["admin"] = True
    session["csrf"] = os.urandom(16).hex()
    log.info("admin: login (%s)", chi)
    return jsonify(csrf=session["csrf"])


@bp.post("/admin/api/logout")
def logout():
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
        modello={"api": A.llm.API, "url": A.llm.BASE, "nome": A.llm.MODEL, "chiave": bool(A.llm.KEY)},
        web={"backend": A.WEB, "attiva": A.web_attivo()},
        casa={"configurata": bool(A.casa.HA and A.casa.TOKEN), "attiva": A.casa_attiva(), "url": A.casa.HA},
        adattamenti={k: v for k, v in A.llm.STATO.items()},
        attesa=A.ATTESA, in_sospeso=len(A._lavori),
        statistiche={"domande": len(voci), "errori": sum(1 for v in voci if v["errore"]),
                     "lente": sum(1 for v in voci if v["durata"] > A.ATTESA),
                     "durata_media": round(sum(durate) / len(durate), 1) if durate else None,
                     "azioni": sum(len(v["azioni"]) for v in voci)},
        avvisi=sum(1 for r in REGISTRO if r["livello"] in ("WARNING", "ERROR", "CRITICAL")),
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
    return jsonify(voci=list(reversed(REGISTRO)))


# ---------- test chat: the same pipeline as Alexa, home actions simulated unless asked otherwise
@bp.post("/admin/api/chat")
def chat():
    A = _a()
    d = request.get_json(silent=True) or {}
    testo = str(d.get("testo") or "").strip()[:1000]
    if not testo:
        return jsonify(errore="Scrivi una domanda."), 400
    storia = [m for m in d.get("storia") or [] if isinstance(m, dict) and m.get("role") in ("user", "assistant")
              and isinstance(m.get("content"), str)][-A.MAXH:]
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


@bp.post("/admin/api/impostazioni")
def salva_impostazioni():
    if not impostazioni.scrivibile():
        return jsonify(errore="La cartella %s non e' scrivibile: monta il volume dei dati (vedi docs/admin.md)." % impostazioni.DATA_DIR), 409
    cambi = (request.get_json(silent=True) or {}).get("valori") or {}
    nuovi = dict(impostazioni.OVERRIDE)
    tipi = {c[0]: (c[2], c[3]) for c in impostazioni.CAMPI}
    for k, v in cambi.items():
        if k not in impostazioni.NOMI:
            return jsonify(errore="Impostazione sconosciuta: %s" % k), 400
        if v not in (None, "") and tipi[k][1] == "number":
            try:
                float(str(v).replace(",", "."))
            except ValueError:
                return jsonify(errore="%s deve essere un numero." % tipi[k][0]), 400
            v = str(v).replace(",", ".")
        if v is None:
            nuovi.pop(k, None)              # back to the value from .env
        else:
            nuovi[k] = str(v).strip() if k not in ("SYSTEM_PROMPT", "ISTRUZIONI_TURNO") else str(v)
    # the new settings must start the service: same checks as at startup, in a separate process
    env = dict(impostazioni.ambiente_con(nuovi), DATA_DIR=os.path.join(impostazioni.DATA_DIR, "nessun-file"))  # not the old file
    prova = subprocess.run([sys.executable, "-c", "import app"], cwd=os.path.dirname(os.path.abspath(__file__)),
                           env=env, capture_output=True, text=True, timeout=60)
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
    flask_app.secret_key = _chiave()
    flask_app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict", SESSION_COOKIE_NAME="aab_admin",
                            PERMANENT_SESSION_LIFETIME=12 * 3600)
    flask_app.register_blueprint(bp)
