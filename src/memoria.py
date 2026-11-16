"""Memory: what the assistant learns about the people at home, across conversations.

- Facts ("Luca prende il caffè senza zucchero", "Anna è la sorella di Luca e vive con lui", "il gatto si chiama Miro"),
  saved by the model with the ricorda tool when someone says something worth remembering, and, with MEMORIA_AUTO,
  learned by a short background request after every answer (it never slows an answer down).
- Voices: when Alexa recognises who is speaking (voice profiles, skill personalization) the assistant can learn the
  name that goes with each voice, and knows who it is talking to.
- The last exchanges of earlier conversations (MEMORIA_RECENTI), so "come ti dicevo ieri" makes sense.

Everything is kept in DATA_DIR/memory.json (readable by the service only) and can be read, changed and deleted from
the admin page, Memoria tab. Passwords, codes and similar secrets are never saved."""
import hashlib, json, logging, os, re, tempfile, threading, time
import impostazioni
import lingua as L
import notifiche

log = logging.getLogger("alexa-ai-bridge")


def _env(nome, predefinito=""):
    return (os.environ.get(nome) or predefinito).strip()


ATTIVA = _env("MEMORIA", "1").lower() not in ("0", "false", "no", "off")
AUTO = _env("MEMORIA_AUTO", "1").lower() not in ("0", "false", "no", "off")
MAX = int(_env("MEMORIA_MAX", "100"))
RECENTI = int(_env("MEMORIA_RECENTI", "4"))
GIORNI = int(_env("MEMORIA_GIORNI", "7"))
ISTRUZIONI = os.environ.get("MEMORIA_ISTRUZIONI", "").strip()
FILE = os.path.join(impostazioni.DATA_DIR, "memory.json")
SCAMBI_TENUTI = 20                    # exchanges kept for MEMORIA_RECENTI (at most 20 are ever used)
LUNGHEZZA = 300                       # characters of a fact
NOMI_STRUMENTI = ("ricorda", "dimentica", "chi_parla")
# never kept, whoever asks: secrets would end up in every request to the model
SEGRETO = re.compile(r"passw|parola d'ordine|\bpin\b|\biban\b|carta di credito|credit card|\bcvv\b|\btoken\b|api.?key|"
                     r"chiave api|codice fiscale|social security|combinazion|combination|"
                     r"\b(?:codice|code|codes|chiave|key)\b[^.;]*\d{3,}|\d{3,}[^.;]*\b(?:codice|code|chiave|key)\b|"
                     r"wi-?fi[^.;]*\b(?:chiave|key|password|codice|code)\b|\b(?:chiave|key|password|codice|code)\b[^.;]*wi-?fi|"
                     r"codice (?:d'accesso|di accesso|segreto|dell'allarme|del l?allarme|pin)|security code|access code|"
                     r"alarm code|passcode|\bpuk\b|\bseed\b", re.I)
_lock = threading.Lock()
_tl = threading.local()
_stato = {"rotto": False}            # memory.json could not be read: it is put aside before the next write


# ---------- the file
def _vuota():
    return {"fatti": [], "voci": {}, "scambi": []}


def _testo(v):
    return v if isinstance(v, str) else ""


def _numero(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def leggi():
    """The memory, always well formed: a hand-edited or damaged file never breaks an answer."""
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return _vuota()
    except (OSError, ValueError) as e:
        if not _stato["rotto"]:
            log.warning("memory: %s cannot be read (%s): it will be kept aside as memory.json.broken", FILE, type(e).__name__)
        _stato["rotto"] = True
        return _vuota()
    if not isinstance(d, dict):
        _stato["rotto"] = True
        return _vuota()
    lista = lambda k: d.get(k) if isinstance(d.get(k), list) else []
    out = _vuota()
    out["fatti"] = [{"id": x["id"], "testo": x["testo"], "persona": _testo(x.get("persona")), "t": _numero(x.get("t")),
                     "fonte": _testo(x.get("fonte"))}
                    for x in lista("fatti") if isinstance(x, dict) and isinstance(x.get("testo"), str) and isinstance(x.get("id"), str)]
    voci = d.get("voci") if isinstance(d.get("voci"), dict) else {}
    out["voci"] = {k: v for k, v in voci.items() if isinstance(k, str) and isinstance(v, str)}
    out["scambi"] = [{"t": _numero(x.get("t")), "d": x["d"], "r": _testo(x.get("r")), "v": _testo(x.get("v"))}
                     for x in lista("scambi") if isinstance(x, dict) and isinstance(x.get("d"), str)]
    return out


def _scrivi(d):
    if not impostazioni.scrivibile():
        return False
    if _stato["rotto"]:                   # never overwrite what could not be read: keep it for the owner
        try:
            os.replace(FILE, FILE + ".broken")
        except OSError:
            pass
        _stato["rotto"] = False
    fd, tmp = tempfile.mkstemp(dir=impostazioni.DATA_DIR, prefix=".memory-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.chmod(tmp, 0o600)
        os.replace(tmp, FILE)
        return True
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _pulito(testo, n=LUNGHEZZA):
    t = " ".join(re.sub(r"[\x00-\x1f\x7f\[\]]", " ", str(testo or "")).split())
    return t[:n].strip()


def _parole(t):
    return set(re.findall(r"[^\W_]{3,}", t.lower()))


def _simile(a, b):
    """How much two facts are the same (0..1): shared words over all their words, so "Anna non è più vegetariana" is
    not "Anna è vegetariana"."""
    pa, pb = _parole(a), _parole(b)
    return len(pa & pb) / len(pa | pb) if pa and pb else float(a.lower() == b.lower())


def _copre(fatto, richiesta):
    """How much of what is asked a fact contains (0..1)."""
    pf, pr = _parole(fatto), _parole(richiesta)
    return len(pf & pr) / len(pr) if pr else 0.0


# ---------- facts
def fatti():
    return leggi()["fatti"]


def aggiungi(testo, persona="", fonte="voce", sostituisce=None):
    """Save a fact. Returns (outcome, fact): outcome is nuovo, gia (already known), vietato (a secret) or vuoto."""
    testo, persona = _pulito(testo), _pulito(persona, 60)
    if not testo:
        return "vuoto", None
    if SEGRETO.search(testo):
        return "vietato", None
    with _lock:
        d = leggi()
        if sostituisce:
            d["fatti"] = [f for f in d["fatti"] if f["id"] != sostituisce]
        for f in d["fatti"]:
            if f["testo"].lower() == testo.lower() or (_simile(f["testo"], testo) >= 0.9 and len(_parole(testo)) >= 3):
                if sostituisce:
                    _scrivi(d)
                return "gia", f
        nuovo = {"id": os.urandom(5).hex(), "testo": testo, "persona": persona, "t": time.time(), "fonte": fonte}
        d["fatti"].append(nuovo)
        tolti = len(d["fatti"]) - MAX
        if tolti > 0:                       # full: the oldest go
            d["fatti"] = d["fatti"][tolti:]
        _scrivi(d)
    return "nuovo", nuovo


def modifica(fid, testo, persona=""):
    testo, persona = _pulito(testo), _pulito(persona, 60)
    if not testo or SEGRETO.search(testo):
        return False
    with _lock:
        d = leggi()
        for f in d["fatti"]:
            if f["id"] == fid:
                f.update(testo=testo, persona=persona, t=time.time())
                return _scrivi(d)
    return False


def elimina(fid):
    with _lock:
        d = leggi()
        prima = len(d["fatti"])
        d["fatti"] = [f for f in d["fatti"] if f["id"] != fid]
        return len(d["fatti"]) < prima and _scrivi(d)


def dimentica(testo):
    """Forget the one fact that matches these words best (the model can ask again for the next one); returns it."""
    testo = _pulito(testo)
    with _lock:
        d = leggi()
        punti = [((_copre(f["testo"] + " " + f.get("persona", ""), testo), _simile(f["testo"], testo)), f) for f in d["fatti"]]
        punti = [(p, f) for p, f in punti if p[0] >= 0.5]
        if not punti:
            return []
        via = max(punti, key=lambda pf: pf[0])[1]
        d["fatti"] = [f for f in d["fatti"] if f is not via]
        _scrivi(d)
    return [via["testo"]]


def svuota(cosa="tutto"):
    with _lock:
        d = leggi()
        if cosa in ("fatti", "tutto"):
            d["fatti"] = []
        if cosa in ("scambi", "tutto"):
            d["scambi"] = []
        if cosa in ("voci", "tutto"):
            d["voci"] = {}
        return _scrivi(d)


# ---------- voices: Alexa's personId of a recognised voice, never stored as it is
def _chiave_voce(person_id):
    return hashlib.sha256(("alexa-ai-bridge:" + person_id).encode()).hexdigest()[:16] if person_id else None


def imposta_persona(person_id):
    """Called before every model request with the personId Alexa sent (None if it did not recognise the voice)."""
    _tl.voce = _chiave_voce(person_id)


def imposta_prova(attiva):
    """scripts/e2e.py: the memory is read but never changed."""
    _tl.prova = bool(attiva)


def voce_attuale():
    return getattr(_tl, "voce", None)


def nome_voce(chiave):
    return leggi()["voci"].get(chiave or "", "") if chiave else ""


def imposta_voce(chiave, nome):
    nome = _pulito(nome, 40)
    with _lock:
        d = leggi()
        if nome:
            d["voci"][chiave] = nome
        else:
            d["voci"].pop(chiave, None)
        return _scrivi(d)


# ---------- earlier conversations
def registra_scambio(domanda, risposta):
    if getattr(_tl, "prova", False) or not (ATTIVA and RECENTI and isinstance(domanda, str) and risposta):
        return
    if SEGRETO.search(domanda) or SEGRETO.search(risposta):
        return                            # a password said aloud is never kept, not even as an earlier exchange
    with _lock:
        d = leggi()
        d["scambi"] = (d["scambi"] + [{"t": time.time(), "d": _pulito(domanda, 400), "r": _pulito(risposta, 600),
                                       "v": voce_attuale() or ""}])[-SCAMBI_TENUTI:]
        _scrivi(d)


def contesto(storia):
    """What the model is told, with every question: the facts, who is speaking, the last earlier exchanges."""
    if not ATTIVA:
        return ""
    d = leggi()
    out = ""
    if d["fatti"]:
        out += L.t("mem_blocco") % "; ".join((f["persona"] + ": " if f.get("persona") else "") + f["testo"] for f in d["fatti"])
    voce = voce_attuale()
    if voce:
        nome = d["voci"].get(voce)
        out += (L.t("mem_parla") % nome) if nome else L.t("mem_sconosciuto")
    if RECENTI:
        gia = {m["content"] for m in storia if m.get("role") == "user" and isinstance(m.get("content"), str)}
        limite = time.time() - GIORNI * 86400
        scambi = [s for s in d["scambi"] if s.get("t", 0) >= limite and s["d"] not in gia][-RECENTI:]
        if scambi:
            out += L.t("mem_recenti") % " | ".join(
                "%s%s -> %s" % ((d["voci"].get(s.get("v")) + ": ") if d["voci"].get(s.get("v")) else "", s["d"], s["r"]) for s in scambi)
    return out


# ---------- tools for the model
def strumenti():
    if not ATTIVA:
        return []
    out = [
        {"name": "ricorda", "description": L.t("ricorda_desc"),
         "parameters": {"type": "object", "properties": {
             "fatto": {"type": "string", "description": L.t("ricorda_fatto_desc")},
             "persona": {"type": "string", "description": L.t("ricorda_persona_desc")}}, "required": ["fatto"]}},
        {"name": "dimentica", "description": L.t("dimentica_desc"),
         "parameters": {"type": "object", "properties": {"fatto": {"type": "string"}}, "required": ["fatto"]}},
    ]
    if voce_attuale():
        out.append({"name": "chi_parla", "description": L.t("chi_parla_desc"),
                    "parameters": {"type": "object", "properties": {"nome": {"type": "string"}}, "required": ["nome"]}})
    return out


def esegui(nome, a):
    if not ATTIVA:
        return L.t("mem_spenta")
    if getattr(_tl, "prova", False):
        return L.t("mem_prova")
    if nome == "ricorda":
        esito, f = aggiungi(a.get("fatto"), a.get("persona") or "", "voce")
        if esito == "nuovo":
            log.info("memory: a new fact")
            notifiche.notifica("memoria", L.t("n_memoria") % f["testo"])
        return L.t({"nuovo": "mem_salvato", "gia": "mem_gia", "vietato": "mem_vietato", "vuoto": "mem_non_trovato"}[esito])
    if nome == "dimentica":
        via = dimentica(a.get("fatto"))
        return (L.t("mem_dimenticato") % "; ".join(via)) if via else L.t("mem_non_trovato")
    if nome == "chi_parla":
        voce, n = voce_attuale(), _pulito(a.get("nome"), 40)
        if not voce or not n:
            return L.t("mem_non_trovato")
        imposta_voce(voce, n)
        return L.t("mem_voce") % n
    return L.t("strumento_ignoto")


# ---------- learning by itself, after an answer
def _json_lista(testo):
    m = re.search(r"\[.*\]", testo or "", re.S)
    if not m:
        return []
    try:
        v = json.loads(m.group(0))
    except ValueError:
        return []
    return v if isinstance(v, list) else []


def da_imparare(domanda):
    """Worth a background request? Not a yes, a no, "allora?" or a two-word command."""
    return bool(ATTIVA and AUTO and isinstance(domanda, str) and len(re.findall(r"[^\W_]+", domanda)) >= 4)


def impara(domanda, risposta, chiedi):
    """Ask the model which facts this exchange teaches (chiedi(system, messages) -> text). Returns the new facts."""
    if not (da_imparare(domanda) and risposta):
        return []
    d = leggi()
    noti = "\n".join("%s: %s%s" % (f["id"], (f["persona"] + ": ") if f.get("persona") else "", f["testo"]) for f in d["fatti"]) or "-"
    chi = nome_voce(voce_attuale())
    testo = L.t("mem_estrai") % (ISTRUZIONI or L.t("mem_cosa"), noti, (chi + ": ") if chi else "", _pulito(domanda, 600), _pulito(risposta, 800))
    try:
        uscita = chiedi(L.t("mem_estrai_system"), [{"role": "user", "content": testo}])
    except Exception as e:
        log.info("memory: nothing learned (%s)", str(e)[:80])
        return []
    nuovi = []
    for v in _json_lista(uscita)[:5]:
        if not isinstance(v, dict) or not isinstance(v.get("fatto"), str):
            continue
        sost = v.get("sostituisce") if isinstance(v.get("sostituisce"), str) and any(f["id"] == v["sostituisce"] for f in d["fatti"]) else None
        esito, f = aggiungi(v["fatto"], v.get("persona") if isinstance(v.get("persona"), str) else "", "auto", sost)
        if esito == "nuovo":
            nuovi.append(f["testo"])
    if nuovi:
        log.info("memory: %d new facts learned", len(nuovi))
        notifiche.notifica("memoria", L.t("n_memoria") % "; ".join(nuovi))
    return nuovi
