"""Admin page: status and checks, conversation history, a test chat, the home's safety rules, settings, system
actions and recent log, in Italian or English.

Off unless ADMIN_PASSWORD is set (12 characters or more). Reachable directly (the server itself, or the home network
with BRIDGE_BIND) and, only with ADMIN_PUBLIC=on, through a reverse proxy: a request that carries proxy headers is
refused otherwise, whatever the proxy is. See docs/admin.md."""
import collections, fcntl, hashlib, hmac, json, logging, os, re, signal, subprocess, sys, threading, time, urllib.request
from flask import Blueprint, Response, abort, current_app, jsonify, request, send_from_directory, session
from flask.sessions import SecureCookieSessionInterface
import impostazioni
import lingua as L
import notifiche

log = logging.getLogger("alexa-ai-bridge")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ATTIVO = len(PASSWORD) >= 12
if PASSWORD and not ATTIVO:
    log.warning("ADMIN_PASSWORD is shorter than 12 characters: the admin page is off")
PUBBLICO = os.environ.get("ADMIN_PUBLIC", "off").strip().lower() == "on"
VERSIONE = os.environ.get("APP_VERSION", "dev")
REPO = "LucaTomei/alexa-ai-bridge"
AVVIO = time.time()
QUI = os.path.dirname(os.path.abspath(__file__))
CARTELLA = os.path.join(QUI, "admin")
CARTELLA_SKILL = next((d for d in (os.path.join(QUI, "skill"), os.path.join(QUI, "..", "skill")) if os.path.isdir(d)), None)
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
ENTITA = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
_lock, _lock_registro, _lock_login, _lock_salva = threading.Lock(), threading.Lock(), threading.Lock(), threading.Lock()

bp = Blueprint("admin", __name__)


def _lingua():
    """Language of the page that made the request (X-Lang), else the assistant's."""
    h = request.headers.get("X-Lang", "").strip().lower()
    return h if h in L.LINGUE else L.LINGUA


def _m(it, en):
    return en if _lingua() == "en" else it


def _errore(it, en, codice=400):
    return jsonify(errore=_m(it, en)), codice


# ---------- what the page shows: history and log
class _Cattura(logging.Handler):
    def emit(self, r):
        with _lock_registro:
            REGISTRO.append({"t": r.created, "livello": r.levelname, "testo": r.getMessage()[:1000]})


def righe_registro():
    with _lock_registro:
        return list(REGISTRO)


logging.getLogger("alexa-ai-bridge").addHandler(_Cattura(logging.INFO))


# The history is kept in DATA_DIR (it survives restarts, settings saves and updates, and every process writes to the
# same place, scripts/e2e.py included); in memory only when there is no writable data folder.
FILE_STORICO = os.path.join(impostazioni.DATA_DIR, "history.json")


def _su_disco():
    return impostazioni.scrivibile()


def _modifica_storico(cambia):
    """Read, change and rewrite the history file under an exclusive lock (several processes may write)."""
    with open(FILE_STORICO + ".lock", "a") as blocco:
        fcntl.flock(blocco, fcntl.LOCK_EX)
        try:
            with open(FILE_STORICO, encoding="utf-8") as f:
                voci = json.load(f)
            voci = voci if isinstance(voci, list) else []
        except (OSError, ValueError):
            voci = []
        voci = cambia(voci)[-STORICO.maxlen:]
        tmp = FILE_STORICO + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(voci, f)          # ASCII escapes: any text (even a broken surrogate) can be stored
        os.replace(tmp, FILE_STORICO)
        return voci


def voci_storico():
    if not STORIA_ATTIVA:
        return []
    if _su_disco():
        try:
            with open(FILE_STORICO, encoding="utf-8") as f:
                voci = json.load(f)
            return voci[-STORICO.maxlen:] if isinstance(voci, list) else []
        except (OSError, ValueError):
            return []
    with _lock:
        return list(STORICO)


def aggiungi_voce(voce):
    if not STORIA_ATTIVA:
        return
    if _su_disco():
        try:
            _modifica_storico(lambda voci: voci + [voce])
            return
        except OSError as e:
            log.warning("admin: history not saved (%s)", e)
    with _lock:
        STORICO.append(voce)


def svuota():
    with _lock:
        STORICO.clear()
    if _su_disco():
        try:
            _modifica_storico(lambda voci: [])
        except OSError:
            pass


def registra(lav, uid, origine):
    """Called by the service when a question is answered (or fails)."""
    if not STORIA_ATTIVA:
        return
    domanda = lav["hist"][-1]["content"] if lav.get("hist") else ""
    aggiungi_voce({"t": lav["t"], "utente": hashlib.sha256(uid.encode()).hexdigest()[:8],
                   "origine": "e2e" if uid == "e2e-test" else origine,
                   "domanda": domanda, "risposta": lav.get("risposta"), "errore": lav.get("errore"),
                   "durata": round(lav.get("durata") or 0, 1), "azioni": lav.get("azioni") or []})


# ---------- authentication
SEGRETO = impostazioni.segreto()          # random, never derived from the password
_FILE_REVOCATE = os.path.join(impostazioni.DATA_DIR, "admin-sessions-revoked.json")


def _materiale_password():
    return impostazioni.password_salvata() or PASSWORD


def _impronta():
    """Ties a session to the current password: changing it (in .env or from the page) logs everyone out."""
    return hmac.new(SEGRETO, _materiale_password().encode(), hashlib.sha256).hexdigest()[:16]


def _password_giusta(pw):
    if not isinstance(pw, str):
        return False
    registrata = impostazioni.password_salvata()
    if registrata:
        return impostazioni.verifica_password_salvata(pw, registrata)
    return hmac.compare_digest(pw.encode("utf-8", "replace"), PASSWORD.encode())


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


def _nuova_sessione():
    session.clear()
    session.permanent = True
    session.update(admin=True, csrf=os.urandom(16).hex(), sid=os.urandom(16).hex(), login=time.time(), pw=_impronta())


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


def _sbagliata(chi):
    """Records a wrong password and waits (inside the login lock: one wrong password per RITARDO from everyone)."""
    with _lock:
        _tentativi[chi].append(time.time())
        bloccato = len(_tentativi[chi]) == 5
    log.warning("admin: wrong password (%s)", chi)
    if bloccato:
        notifiche.notifica("pannello", L.t("n_tentativi") % chi, True)
    time.sleep(RITARDO)


@bp.before_request
def _controlli():
    if not ATTIVO:
        abort(404)
    if not PUBBLICO and any(h in request.headers for h in INTESTAZIONI_PROXY):
        abort(404)               # reached through a reverse proxy, but the page is not meant to be published
    if request.path.startswith("/admin/api/") and request.endpoint not in ("admin.login", "admin.sessione"):
        if not autenticato():
            return _errore("Sessione scaduta: entra di nuovo.", "Session expired: please log in again.", 401)
        if request.method != "GET" and not hmac.compare_digest(request.headers.get("X-CSRF", ""), session.get("csrf", "")):
            return _errore("Token CSRF non valido: ricarica la pagina.", "Invalid CSRF token: reload the page.", 403)


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
    return jsonify(autenticato=ok, csrf=session.get("csrf") if ok else None, lingua=L.LINGUA)


@bp.post("/admin/api/login")
def login():
    chi = _client()
    if _bloccato(chi):
        log.warning("admin: too many failed logins (%s)", chi)
        return _errore("Troppi tentativi: riprova tra 15 minuti.", "Too many attempts: try again in 15 minutes.", 429)
    d = request.get_json(silent=True)
    pw = d.get("password", "") if isinstance(d, dict) else ""
    with _lock_login:
        if not _password_giusta(pw):
            _sbagliata(chi)
            return _errore("Password errata.", "Wrong password.", 401)
    _nuova_sessione()
    log.info("admin: login (%s)", chi)
    notifiche.notifica("pannello", L.t("n_accesso") % chi)
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
    voci = voci_storico()
    durate = [v["durata"] for v in voci if v.get("risposta")]
    return jsonify(
        versione=VERSIONE, avvio=AVVIO, ora=time.time(), lingua=L.LINGUA,
        modello={"api": A.llm.API, "url": impostazioni.mascherato(A.llm.BASE) or A.llm.BASE, "nome": A.llm.MODEL, "chiave": bool(A.llm.KEY)},
        web={"backend": A.WEB, "attiva": A.web_attivo()},
        casa={"configurata": bool(A.casa.HA and A.casa.TOKEN), "attiva": A.casa_attiva(), "url": impostazioni.mascherato(A.casa.HA) or A.casa.HA,
              "automazioni": A.casa.automazioni_attive()},
        adattamenti={k: v for k, v in A.llm.STATO.items()},
        fornitori=A.llm.descrivi(), memoria={"attiva": A.memoria.ATTIVA, "fatti": len(A.memoria.fatti())},
        attesa=A.ATTESA, in_sospeso=len(A._lavori),
        statistiche={"domande": len(voci), "errori": sum(1 for v in voci if v.get("errore")),
                     "lente": sum(1 for v in voci if (v.get("durata") or 0) > A.ATTESA),
                     "durata_media": round(sum(durate) / len(durate), 1) if durate else None,
                     "azioni": sum(len(v.get("azioni") or []) for v in voci)},
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
    L.imposta(_lingua())        # the checks speak the language of the page
    if cosa == "modello":
        r = _cronometra(lambda: A.ask_llm([{"role": "user", "content": L.t("prova_modello")}], timeout=30)
                        or _m("(risposta vuota)", "(empty answer)"))
    elif cosa == "web":
        if not A.WEB:
            return jsonify(ok=False, esito=_m("Ricerca web spenta o non configurata.", "Web search is off or not configured."), durata=0)
        citta = A.web.HOME_CITY or L.t("citta_prova")
        if A.WEB == "native":
            r = _cronometra(lambda: A.ask_llm([{"role": "user", "content": L.t("prova_web") % citta}], timeout=60))
        else:
            r = _cronometra(lambda: A.web.cerca(("meteo %s oggi" if L.attuale() == "it" else "weather %s today") % citta, A.WEB))
            r["ok"] = r["ok"] and not r["esito"].startswith(L.t("web_errore").split("(")[0].strip())
    else:
        if not A.casa.ATTIVO:
            return jsonify(ok=False, esito=_m("Home Assistant non configurato (HA_URL e HA_TOKEN).",
                                              "Home Assistant is not configured (HA_URL and HA_TOKEN)."), durata=0)
        A.casa._cache["t"] = 0
        r = _cronometra(A.casa.riepilogo)
    log.info("admin: check %s -> %s", cosa, "ok" if r["ok"] else "error")
    return jsonify(r)


@bp.get("/admin/api/storico")
def storico():
    return jsonify(voci=list(reversed(voci_storico())), attivo=STORIA_ATTIVA)


@bp.delete("/admin/api/storico")
def svuota_storico():
    svuota()
    return jsonify(ok=True)


@bp.get("/admin/api/registro")
def registro():
    return jsonify(voci=list(reversed(righe_registro())))


# ---------- test chat: the same pipeline as Alexa, home actions simulated unless asked otherwise
@bp.post("/admin/api/chat")
def chat():
    A = _a()
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return _errore("Richiesta non valida.", "Invalid request.")
    testo = str(d.get("testo") or "").strip()[:1000]
    if not testo:
        return _errore("Scrivi una domanda.", "Type a question.")
    storia = d.get("storia") if isinstance(d.get("storia"), list) else []
    storia = [{"role": m["role"], "content": m["content"][:4000]} for m in storia if isinstance(m, dict)
              and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-A.MAXH:]
    if storia and storia[0]["role"] != "user":
        storia = storia[1:]
    lav = {"hist": storia + [{"role": "user", "content": testo}], "t": time.time(), "risposta": None, "errore": None}
    L.imposta(d.get("lingua") if d.get("lingua") in L.LINGUE else None)   # the test chat can try either language
    A.casa.azzera_azioni()
    A.memoria.imposta_persona(None)
    A.memoria.imposta_prova(False)
    A.casa.imposta_simulazione(d.get("simula", True) is not False)
    try:
        r = A.pulisci(A.ask_llm(lav["hist"], timeout=A.TIMEOUT_LUNGO))
        lav["risposta"] = r or None
        lav["errore"] = None if r else _m("risposta vuota", "empty answer")
    except Exception as e:
        lav["errore"] = str(e)[:300]
    finally:
        A.casa.imposta_simulazione(False)
    lav["durata"] = time.time() - lav["t"]
    lav["azioni"] = A.casa.azioni_fatte()
    registra(lav, "admin-chat", "chat")
    if lav["risposta"]:                    # like Alexa: the memory learns from the test chat too, in the background
        lingua = L.attuale()
        threading.Thread(target=lambda: (L.imposta(lingua), A.impara(testo, lav["risposta"])), daemon=True).start()
    nota = ("\n[%s: %s]" % (L.t("azioni"), "; ".join(lav["azioni"]))) if lav["azioni"] else ""
    return jsonify(risposta=lav["risposta"], errore=lav["errore"], durata=round(lav["durata"], 1), azioni=lav["azioni"],
                   lenta=lav["durata"] > A.ATTESA,
                   storia=(lav["hist"] + ([{"role": "assistant", "content": lav["risposta"] + nota}] if lav["risposta"] else []))[-A.MAXH:])


# ---------- settings
@bp.get("/admin/api/modelli")
def modelli():
    """Models offered by the configured endpoint (?n=2..5: a fallback one), for the model picker of the settings page."""
    A = _a()
    n = request.args.get("n", "1")
    f = A.llm.fornitore(int(n)) if n.isdigit() else None
    if not f:
        return jsonify(modelli=[], attuale="", errore=_m("non configurato", "not configured"))
    try:
        return jsonify(modelli=A.llm.modelli(f=f), attuale=f.model)
    except Exception as e:
        return jsonify(modelli=[], attuale=f.model, errore=str(e).split(":")[0][:60])   # e.g. "HTTP 401"


# ---------- the models, in the order they are tried
@bp.get("/admin/api/fornitori")
def fornitori():
    A = _a()
    return jsonify(fornitori=A.llm.descrivi(), pausa=A.llm.PAUSA, controllo=A.llm.CONTROLLO, max=A.llm.RISERVE_MAX,
                   liberi=[n for n in range(2, A.llm.RISERVE_MAX + 1) if not A.llm.fornitore(n)],
                   notifica="modelli" in notifiche.SCELTI, notifiche_attive=notifiche.ATTIVE,
                   canali=any(notifiche.configurati().values()), configurabile=impostazioni.scrivibile())


@bp.post("/admin/api/fornitori")
def fornitori_salva():
    A = _a()
    d = request.get_json(silent=True)
    numero = lambda v: not isinstance(v, bool) and isinstance(v, (int, str))
    if not isinstance(d, dict) or not numero(d.get("pausa")) or not numero(d.get("controllo")) \
            or not isinstance(d.get("notifica"), bool) or not isinstance(d.get("attivi"), dict):
        return _errore("Richiesta non valida.", "Invalid request.")
    cambi = {"LLM_PAUSA": str(d["pausa"]), "LLM_CONTROLLO": str(d["controllo"])}
    for n, on in d["attivi"].items():
        if not (isinstance(n, str) and n.isdigit() and 2 <= int(n) <= A.llm.RISERVE_MAX and isinstance(on, bool)):
            return _errore("Richiesta non valida.", "Invalid request.")
        cambi["LLM_%s_ATTIVO" % n] = "1" if on else "0"
    eventi = [e for e in notifiche.EVENTI if e in notifiche.SCELTI and e != "modelli"] + (["modelli"] if d["notifica"] else [])
    if set(eventi) != set(notifiche.SCELTI):
        cambi["NOTIFY_EVENTI"] = ",".join(e for e in notifiche.EVENTI if e in eventi) or "none"
    corpo, codice = _salva(cambi)
    return jsonify(corpo), codice


@bp.post("/admin/api/fornitori/prova")
def fornitori_prova():
    """A short question to this model only: it shows whether it is logged in and has credit (it uses a few tokens)."""
    A = _a()
    d = request.get_json(silent=True)
    n = d.get("n") if isinstance(d, dict) else None
    f = A.llm.fornitore(n) if isinstance(n, int) and not isinstance(n, bool) else None
    if not f:
        return _errore("Modello non configurato.", "Model not configured.", 404)
    L.imposta(_lingua())
    t = time.time()
    try:
        r = A.llm.chiedi(A.sistema(), [{"role": "user", "content": L.t("prova_modello")}], [], None, timeout=30, solo=f)
        ok, esito = True, r or _m("(risposta vuota)", "(empty answer)")
    except Exception as e:
        ok, esito = False, A.llm.motivo(e)
    log.info("admin: check of model %d -> %s", f.n, "ok" if ok else "error")
    return jsonify(ok=ok, esito=esito[:500], durata=round(time.time() - t, 1), fornitori=A.llm.descrivi())


# ---------- memory
def _fatto_pagina(f):
    return {"id": f["id"], "testo": f["testo"], "persona": f.get("persona", ""), "t": f.get("t"), "fonte": f.get("fonte", "")}


@bp.get("/admin/api/memoria")
def memoria():
    M = _a().memoria
    d = M.leggi()
    return jsonify(attiva=M.ATTIVA, auto=M.AUTO, max=M.MAX, recenti=M.RECENTI, giorni=M.GIORNI, istruzioni=M.ISTRUZIONI,
                   fatti=[_fatto_pagina(f) for f in reversed(d["fatti"])],
                   voci=[{"id": k, "nome": v} for k, v in sorted(d["voci"].items(), key=lambda kv: kv[1].lower())],
                   scambi=[{"t": x.get("t"), "domanda": x["d"], "risposta": x.get("r", ""), "chi": d["voci"].get(x.get("v"), "")}
                           for x in reversed(d["scambi"])],
                   configurabile=impostazioni.scrivibile())


@bp.post("/admin/api/memoria")
def memoria_salva():
    d = request.get_json(silent=True)
    numero = lambda v: not isinstance(v, bool) and isinstance(v, (int, str))
    if not isinstance(d, dict) or not isinstance(d.get("attiva"), bool) or not isinstance(d.get("auto"), bool) \
            or not all(numero(d.get(k)) for k in ("max", "recenti", "giorni")) or not isinstance(d.get("istruzioni"), str):
        return _errore("Richiesta non valida.", "Invalid request.")
    corpo, codice = _salva({"MEMORIA": "1" if d["attiva"] else "0", "MEMORIA_AUTO": "1" if d["auto"] else "0",
                            "MEMORIA_MAX": str(d["max"]), "MEMORIA_RECENTI": str(d["recenti"]), "MEMORIA_GIORNI": str(d["giorni"]),
                            "MEMORIA_ISTRUZIONI": d["istruzioni"]})
    return jsonify(corpo), codice


def _memoria_scrivibile():
    if not impostazioni.scrivibile():
        return _errore("La cartella dei dati non è scrivibile.", "The data folder is not writable.", 409)
    return None


@bp.post("/admin/api/memoria/fatto")
def memoria_fatto():
    """Add a fact (without id) or change one."""
    M = _a().memoria
    errore = _memoria_scrivibile()
    if errore:
        return errore
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("testo"), str) or not isinstance(d.get("persona", ""), str) \
            or not isinstance(d.get("id", ""), str):
        return _errore("Richiesta non valida.", "Invalid request.")
    if M.SEGRETO.search(d["testo"]):
        return _errore("Password, codici e dati riservati non si salvano in memoria.",
                       "Passwords, codes and confidential data are not saved in the memory.")
    if d.get("id"):
        if not M.modifica(d["id"], d["testo"], d.get("persona", "")):
            return _errore("Ricordo non trovato o vuoto.", "Fact not found or empty.", 404)
    else:
        esito, _ = M.aggiungi(d["testo"], d.get("persona", ""), "pannello")
        if esito == "vuoto":
            return _errore("Scrivi il fatto da ricordare.", "Type the fact to remember.")
    log.info("admin: memory fact %s", "changed" if d.get("id") else "added")
    return jsonify(ok=True)


@bp.post("/admin/api/memoria/elimina")
def memoria_elimina():
    M = _a().memoria
    errore = _memoria_scrivibile()
    if errore:
        return errore
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("id"), str):
        return _errore("Richiesta non valida.", "Invalid request.")
    if not M.elimina(d["id"]):
        return _errore("Ricordo non trovato.", "Fact not found.", 404)
    log.info("admin: memory fact deleted")
    return jsonify(ok=True)


@bp.post("/admin/api/memoria/svuota")
def memoria_svuota():
    M = _a().memoria
    errore = _memoria_scrivibile()
    if errore:
        return errore
    d = request.get_json(silent=True)
    cosa = d.get("cosa") if isinstance(d, dict) else None
    if cosa not in ("fatti", "scambi", "voci", "tutto"):
        return _errore("Richiesta non valida.", "Invalid request.")
    M.svuota(cosa)
    log.info("admin: memory cleared (%s)", cosa)
    return jsonify(ok=True)


@bp.post("/admin/api/memoria/voce")
def memoria_voce():
    """Rename a recognised voice, or forget it (empty name)."""
    M = _a().memoria
    errore = _memoria_scrivibile()
    if errore:
        return errore
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("id"), str) or not isinstance(d.get("nome"), str) \
            or d["id"] not in M.leggi()["voci"]:
        return _errore("Voce non trovata.", "Voice not found.", 404)
    M.imposta_voce(d["id"], d["nome"])
    return jsonify(ok=True)


@bp.get("/admin/api/impostazioni")
def leggi_impostazioni():
    return jsonify(campi=impostazioni.valori(_lingua()), configurabile=impostazioni.scrivibile(), cartella=impostazioni.DATA_DIR)


@bp.get("/admin/api/impostazioni/esporta")
def esporta_impostazioni():
    """Every setting that is set, without keys, tokens and URLs with credentials: a backup that is safe to keep."""
    valori = {}
    for c in impostazioni.CAMPI:
        v = os.environ.get(c[0], "")
        if c[0] == "LLM_API" and "LLM_API" not in os.environ:
            v = os.environ.get("LLM_FORMAT", "")       # the old name of the same setting
        if v and c[0] not in impostazioni.SEGRETI and not (c[0] in impostazioni.URL and impostazioni.mascherato(v)):
            valori[c[0]] = v
    corpo = json.dumps({"app": "alexa-ai-bridge", "versione": VERSIONE, "impostazioni": valori}, indent=2, ensure_ascii=False)
    return Response(corpo, mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=alexa-ai-bridge-settings.json"})


def _riavvia(server):
    """Ask gunicorn for a graceful reload: a new worker imports the service again with the new settings."""
    if server.startswith("gunicorn"):
        threading.Timer(0.5, os.kill, (os.getppid(), signal.SIGHUP)).start()
        return True
    return False


TESTI_LUNGHI = ("SYSTEM_PROMPT", "ISTRUZIONI_TURNO", "MEMORIA_ISTRUZIONI")
# changing where requests go means re-entering the secret sent there: a stolen session cannot redirect a stored key
SEGRETO_DI = {"LLM_BASE_URL": "LLM_API_KEY", "HA_URL": "HA_TOKEN", "BRAVE_URL": "BRAVE_API_KEY", "TAVILY_URL": "TAVILY_API_KEY"}
# optional secrets sent to the same address: when they are set, they follow the same rule
SEGRETI_OPZIONALI_DI = {"HA_URL": ("HA_AUTOMAZIONI_TOKEN",), "NOTIFY_TELEGRAM_URL": ("NOTIFY_TELEGRAM_TOKEN",),
                        "NOTIFY_NTFY_URL": ("NOTIFY_NTFY_TOKEN",), "NOTIFY_GOTIFY_URL": ("NOTIFY_GOTIFY_TOKEN",),
                        "NOTIFY_WEBHOOK_URL": ("NOTIFY_WEBHOOK_TOKEN",),
                        **{"LLM_%d_BASE_URL" % n: ("LLM_%d_API_KEY" % n,) for n in range(2, 6)}}


def _pulisci_valore(k, v):
    """The value to store, or raises ValueError with a message for the page."""
    lingua = _lingua()
    nome = impostazioni.etichetta(k, lingua)
    if isinstance(v, bool) or not isinstance(v, (str, int, float)):
        raise ValueError(_m("Valore non valido per %s.", "Invalid value for %s.") % nome)
    v = str(v)
    if len(v) > 20000:
        raise ValueError(_m("%s è troppo lungo.", "%s is too long.") % nome)
    ammessi = "\n\t" if k in TESTI_LUNGHI else ""
    if any(ord(c) < 32 and c not in ammessi for c in v) or "\x7f" in v:
        raise ValueError(_m("%s contiene caratteri non ammessi.", "%s contains characters that are not allowed.") % nome)
    try:
        v.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(_m("%s contiene caratteri non validi.", "%s contains invalid characters.") % nome) from None
    v = v if k in TESTI_LUNGHI else v.strip()
    if impostazioni.TIPO[k] == "number":
        v = v.replace(",", ".")
    if impostazioni.TIPO[k] == "select" and v not in impostazioni.OPZIONI[k]:
        scelte = ", ".join(o or _m("automatico", "automatic") for o in impostazioni.OPZIONI[k])
        raise ValueError(_m("%s: valore non previsto (%s).", "%s: unexpected value (%s).") % (nome, scelte))
    errore = impostazioni.errore_valore(k, v, lingua)
    if errore:
        raise ValueError(errore)
    return v


def _salva(cambi):
    """Validate, test-load and store changes ({name: value, or None to go back to .env}). Returns (body, status)."""
    if not impostazioni.scrivibile():
        return {"errore": _m("La cartella %s non è scrivibile: monta il volume dei dati (vedi docs/admin.md).",
                             "The folder %s is not writable: mount the data volume (see docs/admin.md).") % impostazioni.DATA_DIR}, 409
    if not isinstance(cambi, dict):
        return {"errore": _m("Richiesta non valida.", "Invalid request.")}, 400
    with _lock_salva:
        nuovi = impostazioni.leggi()            # the file, not what was loaded at start: two saves in a row both count
        for k, v in cambi.items():
            if k not in impostazioni.NOMI:
                return {"errore": _m("Impostazione sconosciuta: %s", "Unknown setting: %s") % k}, 400
            if v is None:
                nuovi.pop(k, None)              # back to the value from .env
                continue
            try:
                nuovi[k] = _pulisci_valore(k, v)
            except ValueError as e:
                return {"errore": str(e)}, 400
        coppie = [(u, k) for u, k in SEGRETO_DI.items()] + \
            [(u, k) for u, ks in SEGRETI_OPZIONALI_DI.items() for k in ks if os.environ.get(k) or nuovi.get(k)]
        for url, segreto in coppie:
            url_env = (impostazioni.BASE.get(url) if url in impostazioni.OVERRIDE else os.environ.get(url)) or ""
            nuovo_url = nuovi.get(url, url_env) or ""
            # typed again in this very save when the address changes, and a key from .env only ever goes to the .env address
            if (url in cambi and nuovo_url != os.environ.get(url, "") and not isinstance(cambi.get(segreto), str)) \
                    or (nuovo_url != url_env and segreto not in nuovi):
                lingua = _lingua()
                return {"errore": _m("%s è cambiato: scrivi di nuovo %s (anche vuoto, se non serve) e salva tutto insieme.",
                                     "%s changed: type %s again (even empty, if not needed) and save both together.")
                        % (impostazioni.etichetta_piena(url, lingua), impostazioni.etichetta_piena(segreto, lingua))}, 400
        # the new settings must start the service: same checks as at startup, in a separate process
        env = dict(impostazioni.ambiente_con(nuovi), DATA_DIR=os.path.join(impostazioni.DATA_DIR, "nessun-file"))  # not the old file
        try:
            prova = subprocess.run([sys.executable, "-c", "import app"], cwd=QUI, env=env, capture_output=True, text=True, timeout=60)
        except (OSError, ValueError) as e:
            return {"errore": _m("Impostazioni non valide: %s", "Invalid settings: %s") % str(e)[:200]}, 400
        if prova.returncode != 0:
            righe = [r for r in prova.stderr.strip().splitlines() if r.strip()]
            return {"errore": _m("Impostazioni non valide: ", "Invalid settings: ") + (righe[-1] if righe else "?")[:300]}, 400
        impostazioni.salva(nuovi)
    log.info("admin: settings saved (%s)", ", ".join(sorted(cambi)) or "none")
    if notifiche.notifica("pannello", L.t("n_impostazioni") % (", ".join(sorted(cambi)) or "-")):
        notifiche.attendi(4)                # sent before the restart
    return {"ok": True, "riavvio": _riavvia(request.environ.get("SERVER_SOFTWARE", ""))}, 200


@bp.post("/admin/api/impostazioni")
def salva_impostazioni():
    d = request.get_json(silent=True)
    corpo, codice = _salva(d.get("valori") if isinstance(d, dict) else None)
    return jsonify(corpo), codice


# ---------- the home's safety rules, entity by entity
# an entity forbidden from the page is stored in HA_VIETATO as  ^light\.name(?:\s|$)
_TOKEN = re.compile(r"\^([a-z_]+)\\\.([a-z0-9_]+)\(\?:\\s\|\$\)")
DOMINI_MOSTRATI = ("lock", "alarm_control_panel", "script", "automation")


def _vietate_da_pagina(regex):
    return ["%s.%s" % m.groups() for m in _TOKEN.finditer(regex or "")]


def _componi_vietato(regex, entita):
    altro = re.sub(r"\|{2,}", "|", _TOKEN.sub("", regex or "")).strip("|")
    token = [r"^%s(?:\s|$)" % re.escape(e) for e in entita]
    return "|".join(([altro] if altro else []) + token)


@bp.get("/admin/api/casa")
def casa():
    A = _a()
    C = A.casa
    if not (C.HA and C.TOKEN):
        return jsonify(configurata=False, entita=[], gruppi=sorted(C.GRUPPI))
    try:
        C._cache["t"] = 0
        stati = C.stati()
    except Exception as e:
        return jsonify(configurata=True, errore=str(e)[:300], entita=[], gruppi=sorted(C.GRUPPI))
    da_pagina = set(_vietate_da_pagina(os.environ.get("HA_VIETATO", "")))
    base = C.VIETATO.regole[0]
    altre = C.VIETATO.regole[1:]
    out = []
    for s in stati:
        eid = s.get("entity_id", "")
        dominio = eid.split(".")[0]
        if dominio not in C.COMANDI and dominio not in DOMINI_MOSTRATI:
            continue
        testo = eid + " " + C.nome(s)
        if dominio not in C.COMANDI:
            blocco = "dominio"
        elif base.search(testo):
            blocco = "regole"
        elif eid in da_pagina:
            blocco = "pagina"
        elif any(r.search(testo) for r in altre):
            blocco = "regex"
        else:
            blocco = None
        out.append({"id": eid, "nome": C.nome(s), "stato": s.get("state"), "dominio": dominio, "blocco": blocco,
                    "gruppo": eid in C.GRUPPI})
    out.sort(key=lambda x: (x["dominio"], x["nome"].lower()))
    return jsonify(configurata=True, entita=out, gruppi=sorted(C.GRUPPI), vietate=sorted(da_pagina),
                   max_senza_conferma=C.MAX_SENZA_CONFERMA)


@bp.post("/admin/api/casa")
def salva_casa():
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("gruppi"), list) or not isinstance(d.get("vietate"), list):
        return _errore("Richiesta non valida.", "Invalid request.")
    gruppi, vietate = d["gruppi"], d["vietate"]
    if not all(isinstance(e, str) and ENTITA.match(e) for e in gruppi + vietate):
        return _errore("Entity ID non valido.", "Invalid entity ID.")
    corpo, codice = _salva({"HA_GRUPPI": ",".join(dict.fromkeys(gruppi)),
                            "HA_VIETATO": _componi_vietato(os.environ.get("HA_VIETATO", ""), list(dict.fromkeys(vietate)))})
    return jsonify(corpo), codice


# ---------- automations created by voice
@bp.get("/admin/api/automazioni")
def automazioni():
    C = _a().casa
    out = {"configurata": bool(C.HA and C.TOKEN), "attiva": C.automazioni_attive(), "abilitata": C.AUTOMAZIONI,
           "strumenti": C.ATTIVO, "max": C.MAX_AUTOMAZIONI, "token_dedicato": C.TOKEN_AUTOMAZIONI != C.TOKEN,
           "voci": [], "permessi": None, "configurabile": impostazioni.scrivibile()}
    if not out["configurata"]:
        return jsonify(out)
    try:
        C._cache["t"] = 0
        out["voci"] = C.elenco_automazioni()
    except Exception as e:
        out["errore"] = str(e)[:300]
        return jsonify(out)
    try:
        out["permessi"] = C.permessi_automazioni()
    except Exception:
        out["permessi"] = None              # Home Assistant did not say: the page shows nothing about it
    return jsonify(out)


def _automazione_richiesta():
    """The automation created by voice that the request names, or an error response."""
    C = _a().casa
    if not (C.HA and C.TOKEN):
        return None, _errore("Home Assistant non configurato.", "Home Assistant is not configured.", 409)
    d = request.get_json(silent=True)
    aid = d.get("id") if isinstance(d, dict) else None
    if not isinstance(aid, str) or not aid.startswith(C.PREFISSO) or not re.fullmatch(r"[A-Za-z0-9_]{1,64}", aid):
        return None, _errore("Automazione non valida.", "Invalid automation.")
    C.imposta_simulazione(False)
    L.imposta(_lingua())
    try:
        C._cache["t"] = 0
        v = next((x for x in C.elenco_automazioni() if x["id"] == aid), None)
    except Exception as e:
        return None, _errore_ha(e)
    if not v:
        return None, _errore("Non è tra le automazioni create a voce.", "It is not one of the automations created by voice.", 404)
    return (d, v), None


def _errore_ha(e):
    if getattr(e, "code", None) in (401, 403):
        return _errore("Home Assistant ha rifiutato: serve il token di un amministratore (Token per le automazioni).",
                       "Home Assistant refused: an administrator's token is needed (Token for automations).", 502)
    return jsonify(errore=_m("Home Assistant non risponde: %s", "Home Assistant does not answer: %s") % str(e)[:200]), 502


@bp.post("/admin/api/automazioni/stato")
def stato_automazione():
    trovata, errore = _automazione_richiesta()
    if errore:
        return errore
    d, v = trovata
    if not isinstance(d.get("attiva"), bool):
        return _errore("Richiesta non valida.", "Invalid request.")
    C = _a().casa
    try:
        servizio = C.imposta_automazione(v, d["attiva"])
    except C._NonValida as e:
        return jsonify(errore=str(e)), 409
    except Exception as e:
        return _errore_ha(e)
    log.info("admin: automation.%s %s", servizio, v["entity_id"])
    notifiche.notifica("automazioni", L.t("n_auto_pannello") % (v["nome"], L.t("auto_op_attiva" if d["attiva"] else "auto_op_disattiva")))
    return jsonify(ok=True)


@bp.post("/admin/api/automazioni/elimina")
def elimina_automazione():
    trovata, errore = _automazione_richiesta()
    if errore:
        return errore
    _, v = trovata
    try:
        _a().casa.elimina_automazione(v)
    except Exception as e:
        return _errore_ha(e)
    log.info("admin: automation deleted %s (%s)", v["id"], v["nome"])
    notifiche.notifica("automazioni", L.t("n_auto_pannello") % (v["nome"], L.t("auto_op_elimina")))
    return jsonify(ok=True)


# ---------- notifications
@bp.get("/admin/api/notifiche")
def notifiche_stato():
    N = notifiche
    out = {"attive": N.ATTIVE, "eventi": [e for e in N.EVENTI if e in N.SCELTI], "tutti": list(N.EVENTI), "max_ora": N.MAX_ORA,
           "canali": {c: {"configurato": ok, "dettaglio": N.dettagli()[c]} for c, ok in N.configurati().items()},
           "ha_configurato": bool(N.HA_URL and N.HA_TOKEN), "ha_scelti": list(N.HA_SERVIZI), "servizi_ha": None,
           "ultime": list(reversed(N.ULTIME)), "configurabile": impostazioni.scrivibile()}
    if out["ha_configurato"]:
        try:
            out["servizi_ha"] = N.servizi_ha()
        except Exception as e:
            out["errore_ha"] = N._errore(e)
    return jsonify(out)


@bp.post("/admin/api/notifiche")
def notifiche_salva():
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("attive"), bool) or not isinstance(d.get("eventi"), list) \
            or not isinstance(d.get("ha"), list) or isinstance(d.get("max_ora"), bool) or not isinstance(d.get("max_ora"), (int, str)):
        return _errore("Richiesta non valida.", "Invalid request.")
    eventi = [e for e in notifiche.EVENTI if e in d["eventi"]]
    if len(eventi) != len(set(d["eventi"])) or not all(isinstance(s, str) and re.fullmatch(r"[a-z0-9_]{1,100}", s) for s in d["ha"]):
        return _errore("Evento o servizio non valido.", "Invalid event or service.")
    corpo, codice = _salva({"NOTIFY_ATTIVE": "1" if d["attive"] else "0", "NOTIFY_EVENTI": ",".join(eventi) or "none",
                            "NOTIFY_HA": ",".join(dict.fromkeys(d["ha"])), "NOTIFY_MAX_ORA": str(d["max_ora"])})
    return jsonify(corpo), codice


@bp.post("/admin/api/notifiche/prova")
def notifiche_prova():
    L.imposta(_lingua())
    if not any(notifiche.configurati().values()):
        return _errore("Nessun canale configurato: impostalo nella Configurazione, gruppo Notifiche.",
                       "No channel is configured: set one in Settings, Notifications group.", 409)
    esiti = notifiche.prova()
    log.info("admin: test notification (%s)", ", ".join("%s %s" % kv for kv in esiti.items()))
    return jsonify(esiti=esiti, ok=all(v == "ok" for v in esiti.values()))


# ---------- system
def _infrastruttura():
    return {k: os.environ.get(k, "") for k in ("PUBLIC_HOST", "BRIDGE_BIND", "BRIDGE_PORT", "ADMIN_PUBLIC", "BRIDGE_VERSION", "COMPOSE_PROFILES")}


@bp.get("/admin/api/sistema")
def sistema():
    A = _a()
    host = os.environ.get("PUBLIC_HOST", "").strip()
    return jsonify(versione=VERSIONE, avvio=AVVIO, lingua=L.LINGUA, lingua_scelta=L.SCELTA, skill_id=A.SKILL_ID,
                   endpoint=("https://%s/alexa" % host) if host and host != "alexa.example.com" and not host.startswith(":") else None,
                   modelli_skill=sorted(f.split(".")[1] for f in os.listdir(CARTELLA_SKILL) if f.endswith(".json")) if CARTELLA_SKILL else [],
                   in_sospeso=len(A._lavori), password_da_pagina=bool(impostazioni.password_salvata()),
                   dati_persistenti=impostazioni.scrivibile(), infrastruttura=_infrastruttura(), pubblico=PUBBLICO)


@bp.get("/admin/api/sistema/modello-skill/<any('it-IT','en-US'):locale>")
def modello_skill(locale):
    if not CARTELLA_SKILL:
        abort(404)
    return send_from_directory(CARTELLA_SKILL, "interaction-model.%s.json" % locale, as_attachment=True)


@bp.post("/admin/api/sistema/riavvia")
def riavvia():
    log.info("admin: restart requested")
    return jsonify(riavvio=_riavvia(request.environ.get("SERVER_SOFTWARE", "")))


@bp.post("/admin/api/sistema/scarta-sospese")
def scarta_sospese():
    A = _a()
    with A._lock:
        n = len(A._lavori)
        A._lavori.clear()
    log.info("admin: %d pending answers discarded", n)
    return jsonify(scartate=n)


@bp.post("/admin/api/sistema/esci-ovunque")
def esci_ovunque():
    """A new signing key: every session cookie, on every device, stops working at once."""
    global SEGRETO
    SEGRETO = impostazioni.segreto(nuovo=True)
    current_app.secret_key = SEGRETO
    REVOCATE.clear()
    log.warning("admin: every session logged out")
    notifiche.notifica("pannello", L.t("n_esci_ovunque"), True)
    return jsonify(ok=True)


def _scarica_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "alexa-ai-bridge/%s" % VERSIONE, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.load(r)


def _versione(v):
    try:
        return tuple(int(x) for x in str(v).lstrip("v").split(".")[:3])
    except ValueError:
        return None


@bp.get("/admin/api/sistema/aggiornamenti")
def aggiornamenti():
    try:
        d = _scarica_json("https://api.github.com/repos/%s/releases/latest" % REPO)
    except Exception as e:
        return jsonify(errore=_m("Impossibile controllare: %s", "Could not check: %s") % str(e)[:150], attuale=VERSIONE)
    ultima = str(d.get("tag_name") or "").lstrip("v")
    a, u = _versione(VERSIONE), _versione(ultima)
    return jsonify(attuale=VERSIONE, ultima=ultima, url=d.get("html_url"), nuova=bool(a and u and u > a), sconosciuta=a is None)


@bp.post("/admin/api/password")
def cambia_password():
    d = request.get_json(silent=True)
    d = d if isinstance(d, dict) else {}
    attuale, nuova = d.get("attuale"), d.get("nuova")
    chi = _client()
    if _bloccato(chi):
        return _errore("Troppi tentativi: riprova tra 15 minuti.", "Too many attempts: try again in 15 minutes.", 429)
    if not impostazioni.scrivibile():
        return _errore("Serve la cartella dati scrivibile.", "A writable data folder is needed.", 409)
    with _lock_login:
        if not _password_giusta(attuale):
            _sbagliata(chi)
            return _errore("La password attuale non è giusta.", "The current password is wrong.", 401)
    if not isinstance(nuova, str) or not 12 <= len(nuova) <= 200 or any(ord(c) < 32 for c in nuova):
        return _errore("La nuova password deve avere da 12 a 200 caratteri.", "The new password must be 12 to 200 characters long.")
    impostazioni.salva_password(nuova)
    _nuova_sessione()                    # this browser stays in, every other session is logged out
    log.warning("admin: password changed from the page")
    notifiche.notifica("pannello", L.t("n_password"), True)
    return jsonify(csrf=session["csrf"])


@bp.delete("/admin/api/password")
def ripristina_password():
    d = request.get_json(silent=True)
    attuale = d.get("attuale") if isinstance(d, dict) else None
    chi = _client()
    if _bloccato(chi):
        return _errore("Troppi tentativi: riprova tra 15 minuti.", "Too many attempts: try again in 15 minutes.", 429)
    with _lock_login:
        if not _password_giusta(attuale):
            _sbagliata(chi)
            return _errore("La password attuale non è giusta.", "The current password is wrong.", 401)
    impostazioni.cancella_password()
    _nuova_sessione()
    log.warning("admin: password set back to ADMIN_PASSWORD from .env")
    notifiche.notifica("pannello", L.t("n_password"), True)
    return jsonify(csrf=session["csrf"])


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
