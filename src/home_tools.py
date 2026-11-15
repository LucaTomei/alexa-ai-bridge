"""Home Assistant tools for Alexa AI Bridge: read the state of the home and control it, within strict limits.

Never: locks, doors/gates, alarms, scripts, automations, technical services. Actions on several rooms need
the user's spoken "yes" (checked by the service, not by the model). Tool descriptions are Italian (it-IT skill)."""
import json, os, re, threading, time, urllib.error, urllib.request, logging
import lingua as L
import notifiche

HA = os.environ.get("HA_URL", "").rstrip("/")
TOKEN = os.environ.get("HA_TOKEN", "")
UA = os.environ.get("HA_UA") or os.environ.get("HTTP_USER_AGENT", "alexa-ai-bridge/1.0")   # Cloudflare blocks the default "Python-urllib" user agent
_SI_ENV = ("1", "true", "yes", "on")
ATTIVO = bool(HA and TOKEN) and os.environ.get("HA_TOOLS", "1").strip().lower() in _SI_ENV
# automations created by voice: off unless HA_AUTOMAZIONI=1. Home Assistant lets only administrators write automations,
# so they can use their own token, kept apart from the everyday one
AUTOMAZIONI = os.environ.get("HA_AUTOMAZIONI", "0").strip().lower() in _SI_ENV
TOKEN_AUTOMAZIONI = os.environ.get("HA_AUTOMAZIONI_TOKEN", "").strip() or TOKEN
MAX_AUTOMAZIONI = int(os.environ.get("HA_AUTOMAZIONI_MAX", "").strip() or "20")
log = logging.getLogger("alexa-ai-bridge")

LEGGIBILI = ("light", "cover", "climate", "switch", "fan", "humidifier", "scene", "sensor", "binary_sensor", "person", "lock", "weather", "media_player")
COMANDI = {  # domain -> allowed services
    "light": {"turn_on", "turn_off", "toggle"},
    "cover": {"open_cover", "close_cover", "stop_cover", "set_cover_position"},
    "climate": {"turn_on", "turn_off", "set_temperature", "set_hvac_mode"},
    "switch": {"turn_on", "turn_off", "toggle"},
    "fan": {"turn_on", "turn_off"},
    "humidifier": {"turn_on", "turn_off", "set_humidity"},
    "scene": {"turn_on"},
}
DATI_AMMESSI = ("brightness_pct", "position", "temperature", "hvac_mode", "humidity", "color_temp_kelvin", "rgb_color")
VIETATO_BASE = (r"^lock\.|^alarm_control_panel\.|^script\.|^automation\.|porta|portone|serratura|cancello|antifurto|allarme|"
                r"(?:^|[._\s])(?:door|doors|gate|gates|garage_door|garage door|alarm|siren|unlock)(?:$|[._\s])|"
                r"docker|power_control|zigbee|mosquitto|frigate|arcane|nodered|node_red|adguard|backup|proxmox|kuma|_restart|riavvia")


class _Vietato:
    """The built-in forbidden list plus HA_VIETATO (added, never a replacement), each compiled on its own so that a
    custom regex with inline flags such as (?i) works."""
    def __init__(self, extra):
        self.regole = [re.compile(VIETATO_BASE, re.I)]
        if extra:
            try:
                self.regole.append(re.compile(extra, re.I))
            except re.error as e:
                raise SystemExit("HA_VIETATO is not a valid regular expression: %s" % e) from None

    def search(self, testo):
        return next((m for r in self.regole for m in [r.search(testo)] if m), None)


VIETATO = _Vietato(os.environ.get("HA_VIETATO", "").strip())


def _lista(nome_env):
    return [x.strip() for x in os.environ.get(nome_env, "").split(",") if x.strip()]


# entities that act on several rooms (e.g. a cover group): always need a spoken confirmation
GRUPPI = set(_lista("HA_GRUPPI"))
MAX_SENZA_CONFERMA = int(os.environ.get("HA_MAX_SENZA_CONFERMA", "3"))
# summary: temperature sensors (regex on entity_id; empty = every sensor with device_class temperature)
TEMP_PATTERN = os.environ.get("HA_TEMP_PATTERN", "")
# summary: extra entities as "entity_id=Label,entity_id=Label" (power meter, front door, rain sensor...)
EXTRA = [tuple(p.strip() for p in x.split("=", 1)) for x in _lista("HA_SUMMARY_EXTRA") if "=" in x]
ATTRIBUTI = ("current_position", "current_temperature", "temperature", "hvac_action", "brightness", "unit_of_measurement", "current_humidity", "humidity")

_cache = {"t": 0, "s": []}
_tl = threading.local()
SI = L.SI        # a "yes" in Italian or English

def azzera_azioni():
    _tl.azioni = []
    _tl.entita_fatte = set()     # every entity acted on in this turn: the confirmation limit counts them all

def azioni_fatte():
    return list(getattr(_tl, "azioni", []))

def imposta_simulazione(attiva):
    """Test chat of the admin page: every check runs, but no command is sent to Home Assistant."""
    _tl.simula = bool(attiva)

def imposta_domanda(testo, chiesto=True, turno=None):
    """Called before every model request: a confirmation counts only if the user's last sentence is a short yes
    and (chiesto) the assistant's previous turn was a question. turno identifies this turn of the conversation (the
    same for a retry of the same question): what is proposed in a turn can only be confirmed in a later one."""
    _tl.consenso = bool(chiesto) and L.e_un_si(testo)
    _tl.turno = turno if turno is not None else os.urandom(8).hex()

def _req(method, path, body=None, timeout=10, token=None):
    req = urllib.request.Request(HA + "/api/" + path, None if body is None else json.dumps(body).encode(), method=method,
                                 headers={"Authorization": "Bearer " + (token or TOKEN), "Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else None

def stati():
    if time.time() - _cache["t"] > 5:
        _cache["s"] = _req("GET", "states"); _cache["t"] = time.time()
    return _cache["s"]

def nome(s):
    return s.get("attributes", {}).get("friendly_name") or s["entity_id"]

def riga(s):
    a = s.get("attributes", {})
    ex = []
    for k in ATTRIBUTI:
        if k in a and a[k] not in (None, ""):
            v = a[k]
            if k == "brightness":
                v = "%d%%" % round(int(v) * 100 / 255)
            ex.append("%s=%s" % (k, v))
    st = s["state"] + ((" " + a["unit_of_measurement"]) if a.get("unit_of_measurement") else "")
    return "%s | %s | %s%s" % (s["entity_id"], nome(s), st, (" | " + ", ".join(e for e in ex if not e.startswith("unit_of"))) if ex else "")

COPERTURE_VIETATE = {"garage", "gate", "door"}     # device_class of covers that open a way into the home


def vietata(s, tutti=None):
    """True if this entity can never be controlled: forbidden name or ID, a garage/gate/door cover, or a scene that
    sets a forbidden entity (a scene could unlock a door). tutti: entity_id -> state, to check scene members."""
    if VIETATO.search(s["entity_id"] + " " + nome(s)):
        return True
    a = s.get("attributes") or {}
    if s["entity_id"].startswith("cover.") and str(a.get("device_class") or "").lower() in COPERTURE_VIETATE:
        return True
    if s["entity_id"].startswith("scene."):
        membri = a.get("entity_id") if isinstance(a.get("entity_id"), list) else []
        tutti = tutti or {}
        return any(isinstance(e, str) and e != s["entity_id"] and vietata(tutti.get(e) or {"entity_id": e}, None) for e in membri)
    return False

def leggibile(s):
    return s["entity_id"].split(".")[0] in LEGGIBILI and s["state"] not in ("unavailable",)

def _pick(ids):
    m = {s["entity_id"]: s for s in stati()}
    return [m[i] for i in ids if i in m]

def riepilogo():
    S = stati(); m = {s["entity_id"]: s for s in S}
    out = []
    pp = [s for s in S if s["entity_id"].startswith("person.")]
    out.append(L.t("persone") + ": " + "; ".join("%s=%s" % (nome(s), {"home": L.t("a_casa"), "not_home": L.t("fuori")}.get(s["state"], s["state"])) for s in pp))
    luci = [nome(s) for s in S if s["entity_id"].startswith("light.") and s["state"] == "on" and not re.search(r"channel", s["entity_id"])]
    out.append(L.t("luci_accese") + ": " + (", ".join(luci) if luci else L.t("nessuna")))
    tp = [s for s in S if s["entity_id"].startswith("cover.") and not s["entity_id"].endswith("_alexa")]
    out.append(L.t("tapparelle") + ": " + "; ".join("%s %s" % (nome(s), s["attributes"].get("current_position", s["state"])) for s in tp))
    temps = [s for s in S if re.match(TEMP_PATTERN, s["entity_id"])] if TEMP_PATTERN else \
            [s for s in S if s["entity_id"].startswith("sensor.") and s.get("attributes", {}).get("device_class") == "temperature"][:12]
    if temps:
        out.append(L.t("temperature") + ": " + "; ".join("%s %s°" % (nome(s), s["state"]) for s in temps))
    cl = [s for s in S if s["entity_id"].startswith("climate.")]
    out.append(L.t("clima") + ": " + "; ".join(L.t("clima_riga") % (nome(s), s["state"], s["attributes"].get("current_temperature"), s["attributes"].get("temperature")) for s in cl))
    for e, n in EXTRA:
        if e in m:
            out.append("%s: %s%s" % (n, m[e]["state"], (" " + m[e]["attributes"]["unit_of_measurement"]) if m[e]["attributes"].get("unit_of_measurement") else ""))
    return "\n".join(out)

def cerca(testo):
    parole = [p for p in re.split(r"\W+", (testo or "").lower()) if len(p) > 1]
    S = [s for s in stati() if leggibile(s)]
    hit = [s for s in S if all(p in (s["entity_id"] + " " + nome(s)).lower() for p in parole)] if parole else []
    if not hit and parole:   # fall back to any single word
        hit = [s for s in S if any(p in (s["entity_id"] + " " + nome(s)).lower() for p in parole)]
    hit = hit[:40]
    if not hit:
        return L.t("nessuna_entita") % testo
    tutti = {s["entity_id"]: s for s in stati()}
    return "\n".join((L.t("non_comandabile") if vietata(s, tutti) else "") + riga(s) for s in hit)

DOMINI_SENSIBILI = ("lock", "alarm_control_panel", "script", "automation", "button", "siren")


def avvisa(evento, testo, urgente=False):
    """A notification about what the assistant did or was refused: never for the test chat (simulated)."""
    if not getattr(_tl, "simula", False):
        notifiche.notifica(evento, testo, urgente)


def _bloccata(descrizione):
    avvisa("bloccate", L.t("n_bloccata") % descrizione, True)


def esegui(dominio, servizio, entita, dati=None, confermato=False):
    if isinstance(entita, str):   # some models send one entity as a plain string
        entita = [x.strip() for x in entita.split(",")]
    entita = [e.strip() for e in (entita or []) if isinstance(e, str) and e.strip()]
    if dominio not in COMANDI or servizio not in COMANDI[dominio]:
        if dominio in DOMINI_SENSIBILI or any(VIETATO.search(e) for e in entita):     # a lock, the alarm...: worth knowing
            _bloccata("%s.%s %s" % (dominio, servizio, ", ".join(entita)))
        return L.t("non_permessa") % (dominio, servizio, ", ".join("%s(%s)" % (d, "/".join(sorted(v))) for d, v in COMANDI.items()))
    if not entita or "all" in entita:
        return L.t("niente_all")
    S = {s["entity_id"]: s for s in stati()}
    for e in entita:
        if not e.startswith(dominio + "."):
            return L.t("altro_dominio") % (e, dominio)
        if e not in S:
            return L.t("non_esiste") % e
        if vietata(S[e], S):
            _bloccata("%s.%s %s (%s)" % (dominio, servizio, nome(S[e]), e))
            return L.t("vietata") % (nome(S[e]), e)
    dati = {k: v for k, v in (dati if isinstance(dati, dict) else {}).items() if k in DATI_AMMESSI}
    fatte = getattr(_tl, "entita_fatte", set())   # split calls in one turn count together
    multi = max(len(entita), len(fatte | set(entita))) > MAX_SENZA_CONFERMA or any(e in GRUPPI for e in entita)
    if multi and not (confermato and getattr(_tl, "consenso", False)):
        return L.t("serve_conferma") % ", ".join(nome(S[e]) for e in entita)
    simulata = getattr(_tl, "simula", False)
    if not simulata:
        _req("POST", "services/%s/%s" % (dominio, servizio), dict(dati, entity_id=entita), timeout=15)
        _cache["t"] = 0
    log.info("azione HA%s: %s.%s %s %s", " (simulata)" if simulata else "", dominio, servizio, ",".join(entita), json.dumps(dati) if dati else "")
    _tl.entita_fatte = fatte | set(entita)
    _tl.azioni = getattr(_tl, "azioni", []) + ["%s%s.%s %s%s" % ("[simulata] " if simulata else "", dominio, servizio, ",".join(entita), (" " + json.dumps(dati)) if dati else "")]
    avvisa(("confermate", "azioni") if multi else ("azioni",),
           L.t("n_confermata" if multi else "n_azione") % ("%s.%s" % (dominio, servizio), ", ".join(nome(S[e]) for e in entita)))
    return L.t("fatto_su") % (dominio, servizio, ", ".join(nome(S[e]) for e in entita))

# ---------- automations created by voice
# Same rules as esegui_azione for what they do (allowed services, explicit entities, never a forbidden one), a spoken yes
# before creating or deleting one, and the assistant only ever sees and changes the automations it created (their
# Home Assistant id starts with PREFISSO): never the ones made by hand.
PREFISSO = "aab_"
GIORNI = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_NOMI_GIORNI = {"lun": "mon", "mar": "tue", "mer": "wed", "gio": "thu", "ven": "fri", "sab": "sat", "dom": "sun",
                "mo": "mon", "tu": "tue", "we": "wed", "th": "thu", "fr": "fri", "sa": "sat", "su": "sun"}
MAX_AZIONI = 5
FILE_AUTOMAZIONI = os.path.join(os.environ.get("DATA_DIR", "/data"), "automations.json")
_lock_registro = threading.Lock()
# what was put to the user: a yes creates exactly the automation that was read back, never something the model changed
# after the question, nor something proposed and "confirmed" in the same turn (key -> (when, turn))
_proposte, _lock_proposte = {}, threading.Lock()
VALIDITA_PROPOSTA = 900


class _NonValida(Exception):
    """A request the service will not turn into an automation: the message is for the model."""


def automazioni_attive():
    return ATTIVO and AUTOMAZIONI


def _confermata(chiave, confermato):
    """True if this proposal (an automation to create, one to delete) was put to the user in an earlier turn and the
    user has now said yes to it. Otherwise it is recorded as proposed in this turn, and the caller asks."""
    turno = getattr(_tl, "turno", None)
    with _lock_proposte:
        ora = time.time()
        for k in [k for k, (t, _) in _proposte.items() if ora - t > VALIDITA_PROPOSTA]:
            del _proposte[k]
        prima = _proposte.get(chiave)
        if confermato and getattr(_tl, "consenso", False) and prima and turno is not None and prima[1] != turno:
            del _proposte[chiave]
            return True
        _proposte[chiave] = (ora, turno)
        return False


def _registro():
    """What the service remembers about the automations it created (summary, creation time), by Home Assistant id."""
    try:
        with open(FILE_AUTOMAZIONI, encoding="utf-8") as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, dict)} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _registro_cambia(cambia):
    with _lock_registro:
        d = _registro()
        cambia(d)
        try:
            tmp = FILE_AUTOMAZIONI + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, FILE_AUTOMAZIONI)
        except OSError as e:          # no data volume: the automation exists anyway, only its summary is not kept
            log.warning("automations: list not saved (%s)", e)


def _testo(v, massimo):
    v = re.sub(r"[\x00-\x1f\x7f]+", " ", str(v if v is not None else "")).strip()
    return v[:massimo].strip()


def _ora(v):
    m = re.fullmatch(r"\s*([01]?\d|2[0-3])\s*[:.]\s*([0-5]\d)(?:\s*[:.]\s*([0-5]\d))?\s*", str(v or ""))
    if not m:
        raise _NonValida(L.t("auto_ora"))
    return "%02d:%02d:%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def _intero(v, minimo, massimo, chiave):
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise _NonValida(L.t(chiave)) from None
    if n != n or not minimo <= n <= massimo or n != int(n):
        raise _NonValida(L.t(chiave))
    return int(n)


def _numero(v):
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise _NonValida(L.t("auto_soglia")) from None
    if n != n or abs(n) == float("inf"):
        raise _NonValida(L.t("auto_soglia"))
    return int(n) if n == int(n) else n


def _durata(minuti):
    return "%02d:%02d:00" % divmod(minuti, 60)


def _giorni(v):
    if v in (None, "", []):
        return []
    v = v if isinstance(v, list) else re.split(r"[,\s]+", str(v))
    out = []
    for g in v:
        g = str(g).strip().lower()
        if not g:
            continue
        g = _NOMI_GIORNI.get(g[:3], _NOMI_GIORNI.get(g[:2], g[:3]))
        if g not in GIORNI:
            raise _NonValida(L.t("auto_giorni"))
        if g not in out:
            out.append(g)
    return sorted(out, key=GIORNI.index) if len(out) < 7 else []


def _trigger(q, S):
    """The trigger for Home Assistant and its description, from what the model sent."""
    q = q if isinstance(q, dict) else {}
    tipo = str(q.get("tipo") or "").strip().lower()
    if tipo in ("orario", "time", "ora"):
        ora = _ora(q.get("ora"))
        return {"trigger": "time", "at": ora}, L.t("auto_d_orario") % ora[:5]
    if tipo in ("sole", "sun"):
        ev = {"alba": "sunrise", "sunrise": "sunrise", "tramonto": "sunset", "sunset": "sunset"}.get(str(q.get("evento") or "").strip().lower())
        if not ev:
            raise _NonValida(L.t("auto_sole"))
        scarto = _intero(q.get("scarto_minuti") or 0, -180, 180, "auto_scarto")
        t = {"trigger": "sun", "event": ev}
        if scarto:
            t["offset"] = ("-" if scarto < 0 else "") + _durata(abs(scarto))
            return t, L.t(("auto_d_prima_" if scarto < 0 else "auto_d_dopo_") + ev) % abs(scarto)
        return t, L.t("auto_d_" + ev)
    if tipo in ("stato", "state", "soglia", "numeric_state"):
        e = _testo(q.get("entita"), 255)
        if not e or e not in S:
            raise _NonValida(L.t("non_esiste") % (e or "?"))
        n = nome(S[e])
        if tipo in ("stato", "state"):
            a, da = _testo(q.get("a"), 64), _testo(q.get("da"), 64)
            if not a and not da:
                raise _NonValida(L.t("auto_stato"))
            t = {"trigger": "state", "entity_id": e}
            if a:
                t["to"] = a
            if da:
                t["from"] = da
            descr = (L.t("auto_d_da_a") % (n, da, a)) if a and da else (L.t("auto_d_a") % (n, a)) if a else (L.t("auto_d_da") % (n, da))
        else:
            sopra, sotto = _numero(q.get("sopra")), _numero(q.get("sotto"))
            if sopra is None and sotto is None:
                raise _NonValida(L.t("auto_soglia"))
            if sopra is not None and sotto is not None and sopra >= sotto:
                raise _NonValida(L.t("auto_soglia"))
            t = {"trigger": "numeric_state", "entity_id": e}
            if sopra is not None:
                t["above"] = sopra
            if sotto is not None:
                t["below"] = sotto
            descr = (L.t("auto_d_tra") % (n, sopra, sotto)) if sopra is not None and sotto is not None else \
                (L.t("auto_d_sopra") % (n, sopra)) if sopra is not None else (L.t("auto_d_sotto") % (n, sotto))
        if q.get("per_minuti"):
            minuti = _intero(q.get("per_minuti"), 1, 1440, "auto_per")
            t["for"] = _durata(minuti)
            descr += L.t("auto_d_per") % minuti
        return t, descr
    raise _NonValida(L.t("auto_tipo"))


def _azione(a, S):
    """One action of the automation, checked like esegui_azione: same services, same forbidden entities."""
    a = a if isinstance(a, dict) else {}
    dominio, servizio = str(a.get("dominio") or "").strip(), str(a.get("servizio") or "").strip()
    entita = a.get("entita")
    if isinstance(entita, str):
        entita = [x.strip() for x in entita.split(",")]
    entita = list(dict.fromkeys(e.strip() for e in (entita or []) if isinstance(e, str) and e.strip()))
    if dominio not in COMANDI or servizio not in COMANDI[dominio]:
        raise _NonValida(L.t("non_permessa") % (dominio, servizio, ", ".join("%s(%s)" % (d, "/".join(sorted(v))) for d, v in COMANDI.items())))
    if not entita or "all" in entita:
        raise _NonValida(L.t("niente_all"))
    for e in entita:
        if not e.startswith(dominio + "."):
            raise _NonValida(L.t("altro_dominio") % (e, dominio))
        if e not in S:
            raise _NonValida(L.t("non_esiste") % e)
        if vietata(S[e], S):
            _bloccata(L.t("n_in_automazione") % ("%s.%s" % (dominio, servizio), "%s (%s)" % (nome(S[e]), e)))
            raise _NonValida(L.t("vietata") % (nome(S[e]), e))
    dati = {k: v for k, v in (a.get("dati") if isinstance(a.get("dati"), dict) else {}).items() if k in DATI_AMMESSI}
    passo = {"action": "%s.%s" % (dominio, servizio), "target": {"entity_id": entita}}
    if dati:
        passo["data"] = dati
    return passo, "%s.%s %s%s" % (dominio, servizio, ", ".join(nome(S[e]) for e in entita), (" " + json.dumps(dati)) if dati else "")


def _mie(S=None):
    """The automations this service created, as Home Assistant reports them."""
    S = stati() if S is None else S
    return [s for s in S if s.get("entity_id", "").startswith("automation.")
            and str((s.get("attributes") or {}).get("id") or "").startswith(PREFISSO)]


def _prepara(nome_a, quando, azioni, giorni):
    """The automation as Home Assistant wants it, and its summary; raises _NonValida."""
    S = {s["entity_id"]: s for s in stati()}
    trigger, d_trigger = _trigger(quando, S)
    giorni = _giorni(giorni)
    if not isinstance(azioni, list) or not azioni:
        azioni = [azioni] if isinstance(azioni, dict) else []
    if not azioni:
        raise _NonValida(L.t("auto_azioni") % MAX_AZIONI)
    if len(azioni) > MAX_AZIONI:
        raise _NonValida(L.t("auto_azioni") % MAX_AZIONI)
    passi, d_azioni = zip(*[_azione(a, S) for a in azioni], strict=True)
    riassunto = d_trigger + ((L.t("auto_d_giorni") % ", ".join(L.t("auto_g_" + g) for g in giorni)) if giorni else "") + \
        ": " + "; ".join(d_azioni)
    nome_a = _testo(nome_a, 60) or _testo(riassunto, 60)
    mie = _mie(list(S.values()))
    if any(str((s.get("attributes") or {}).get("friendly_name") or "").lower() == ("alexa: " + nome_a).lower() for s in mie):
        raise _NonValida(L.t("auto_esiste") % nome_a)
    if len(mie) >= MAX_AUTOMAZIONI:
        raise _NonValida(L.t("auto_troppe") % MAX_AUTOMAZIONI)
    config = {"alias": "Alexa: " + nome_a, "description": L.t("auto_descrizione") + riassunto, "mode": "single",
              "triggers": [trigger], "conditions": [{"condition": "time", "weekday": giorni}] if giorni else [],
              "actions": list(passi)}
    return config, nome_a, riassunto


def _errore_http(e):
    if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403):
        return L.t("auto_permessi")
    return L.t("errore_ha") % str(e)[:150]


def crea_automazione(nome_a, quando, azioni, giorni=None, confermato=False):
    try:
        config, nome_a, riassunto = _prepara(nome_a, quando, azioni, giorni)
    except _NonValida as e:
        return str(e)
    if not _confermata("crea:" + json.dumps(config, sort_keys=True), confermato):
        return L.t("auto_conferma") % (nome_a, riassunto)
    simulata = getattr(_tl, "simula", False)
    aid = "%s%d" % (PREFISSO, int(time.time() * 1000))
    if not simulata:
        try:
            _req("POST", "config/automation/config/" + aid, config, timeout=15, token=TOKEN_AUTOMAZIONI)
        except urllib.error.HTTPError as e:
            log.warning("automation not created: HTTP %s", e.code)
            return _errore_http(e)
        _cache["t"] = 0
        _registro_cambia(lambda d: d.update({aid: {"nome": nome_a, "riassunto": riassunto, "creata": time.time()}}))
    log.info("automazione HA%s creata: %s (%s) %s", " (simulata)" if simulata else "", aid, nome_a, riassunto)
    avvisa("automazioni", L.t("n_auto_creata") % (nome_a, riassunto))
    _tl.azioni = getattr(_tl, "azioni", []) + ["%sautomation.create %s (%s)" % ("[simulata] " if simulata else "", aid, nome_a)]
    return L.t("auto_creata") % (nome_a, riassunto)


def elenco_automazioni():
    """The automations created by voice: state from Home Assistant, summary from the service's own list. One that
    Home Assistant does not report (deleted by hand, or not loaded yet) is listed with stato None."""
    reg = _registro()
    out, visti = [], set()
    for s in _mie():
        a = s.get("attributes") or {}
        aid = str(a.get("id"))
        visti.add(aid)
        r = reg.get(aid, {})
        out.append({"id": aid, "entity_id": s["entity_id"], "nome": r.get("nome") or re.sub(r"^Alexa: ", "", nome(s)),
                    "stato": s.get("state"), "ultima": a.get("last_triggered"), "riassunto": r.get("riassunto") or "",
                    "creata": r.get("creata")})
    for aid, r in reg.items():
        if aid not in visti:
            out.append({"id": aid, "entity_id": None, "nome": r.get("nome") or aid, "stato": None, "ultima": None,
                        "riassunto": r.get("riassunto") or "", "creata": r.get("creata")})
    return sorted(out, key=lambda v: -(v.get("creata") or 0))


def elenca_automazioni():
    voci = elenco_automazioni()
    if not voci:
        return L.t("auto_nessuna")
    return "\n".join("%s | %s | %s | %s%s" % (v["entity_id"] or v["id"], v["nome"], v["stato"] or L.t("auto_non_trovata"),
                                              v["riassunto"], (" | " + L.t("auto_ultima") % v["ultima"]) if v["ultima"] else "")
                     for v in voci)


def trova_automazione(chi):
    """One of the automations created by voice, by entity_id, Home Assistant id or name; None if it is not one of them."""
    chi = _testo(chi, 255).lower()
    if not chi:
        return None
    voci = elenco_automazioni()
    for v in voci:
        if chi in ((v["entity_id"] or "").lower(), v["id"].lower()):
            return v
    trovate = [v for v in voci if chi in (v["nome"].lower(), "alexa: " + v["nome"].lower())]
    return trovate[0] if len(trovate) == 1 else None


def imposta_automazione(v, accesa):
    """Switch one automation created by voice on or off (automation.turn_on/turn_off, the everyday token is enough)."""
    if not v.get("entity_id"):
        raise _NonValida(L.t("auto_non_trovata_ha") % v["nome"])
    servizio = "turn_on" if accesa else "turn_off"
    if not getattr(_tl, "simula", False):
        _req("POST", "services/automation/" + servizio, {"entity_id": v["entity_id"]}, timeout=15)
        _cache["t"] = 0
    return servizio


def elimina_automazione(v):
    """Delete one automation created by voice (needs an administrator token). One Home Assistant no longer has is
    only forgotten."""
    if not getattr(_tl, "simula", False):
        try:
            _req("DELETE", "config/automation/config/" + v["id"], timeout=15, token=TOKEN_AUTOMAZIONI)
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404):
                raise
        _cache["t"] = 0
        _registro_cambia(lambda d: d.pop(v["id"], None))


def permessi_automazioni():
    """True if the token can write automations (Home Assistant answers 404 for a missing one, 401 to non-admins)."""
    try:
        _req("GET", "config/automation/config/%sverifica" % PREFISSO, timeout=8, token=TOKEN_AUTOMAZIONI)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False
        if e.code in (400, 404):
            return True
        raise


def gestisci_automazione(chi, operazione, confermato=False):
    operazione = str(operazione or "").strip().lower()
    operazione = {"enable": "attiva", "on": "attiva", "disable": "disattiva", "off": "disattiva", "delete": "elimina"}.get(operazione, operazione)
    if operazione not in ("attiva", "disattiva", "elimina"):
        return L.t("auto_operazione")
    v = trova_automazione(chi)
    if not v:
        return L.t("auto_sconosciuta") % _testo(chi, 80)
    simulata = getattr(_tl, "simula", False)
    pre = "[simulata] " if simulata else ""
    try:
        if operazione == "elimina":
            if not _confermata("elimina:" + v["id"], confermato):
                return L.t("auto_conferma_elimina") % v["nome"]
            elimina_automazione(v)
            fatto = "automation.delete %s (%s)" % (v["entity_id"] or v["id"], v["nome"])
        else:
            servizio = imposta_automazione(v, operazione == "attiva")
            fatto = "automation.%s %s" % (servizio, v["entity_id"])
    except _NonValida as e:
        return str(e)
    except urllib.error.HTTPError as e:
        return _errore_http(e)
    log.info("automazione HA%s: %s", " (simulata)" if simulata else "", fatto)
    _tl.azioni = getattr(_tl, "azioni", []) + [pre + fatto]
    avvisa("automazioni", L.t("n_auto_op") % (v["nome"], L.t("auto_op_" + operazione)))
    return L.t("auto_fatto") % (L.t("auto_op_" + operazione), v["nome"])


def strumenti():
    """The home tools, described in the assistant's language (names and parameters never change)."""
    base = [
        {"name": "riepilogo_casa", "description": L.t("riepilogo_desc"), "parameters": {"type": "object", "properties": {}}},
        {"name": "cerca_in_casa", "description": L.t("cerca_desc"),
         "parameters": {"type": "object", "properties": {"testo": {"type": "string"}}, "required": ["testo"]}},
        {"name": "esegui_azione", "description": L.t("esegui_desc"),
         "parameters": {"type": "object", "properties": {
             "dominio": {"type": "string"}, "servizio": {"type": "string"},
             "entita": {"type": "array", "items": {"type": "string"}, "description": L.t("entita_desc")},
             "dati": {"type": "object"}, "confermato": {"type": "boolean"}}, "required": ["dominio", "servizio", "entita"]}},
    ]
    if not automazioni_attive():
        return base
    azione = {"type": "object", "properties": {
        "dominio": {"type": "string"}, "servizio": {"type": "string"},
        "entita": {"type": "array", "items": {"type": "string"}, "description": L.t("entita_desc")},
        "dati": {"type": "object"}}, "required": ["dominio", "servizio", "entita"]}
    return base + [
        {"name": "crea_automazione", "description": L.t("crea_auto_desc"),
         "parameters": {"type": "object", "properties": {
             "nome": {"type": "string", "description": L.t("auto_nome_desc")},
             "quando": {"type": "object", "description": L.t("auto_quando_desc"), "properties": {
                 "tipo": {"type": "string", "enum": ["orario", "sole", "stato", "soglia"]},
                 "ora": {"type": "string", "description": "HH:MM"},
                 "evento": {"type": "string", "enum": ["alba", "tramonto"]},
                 "scarto_minuti": {"type": "integer"},
                 "entita": {"type": "string"}, "a": {"type": "string"}, "da": {"type": "string"},
                 "sopra": {"type": "number"}, "sotto": {"type": "number"}, "per_minuti": {"type": "integer"}},
                 "required": ["tipo"]},
             "giorni": {"type": "array", "items": {"type": "string", "enum": list(GIORNI)}, "description": L.t("auto_giorni_desc")},
             "azioni": {"type": "array", "items": azione},
             "confermato": {"type": "boolean"}}, "required": ["nome", "quando", "azioni"]}},
        {"name": "elenca_automazioni", "description": L.t("elenca_auto_desc"), "parameters": {"type": "object", "properties": {}}},
        {"name": "gestisci_automazione", "description": L.t("gestisci_auto_desc"),
         "parameters": {"type": "object", "properties": {
             "automazione": {"type": "string", "description": L.t("auto_chi_desc")},
             "operazione": {"type": "string", "enum": ["attiva", "disattiva", "elimina"]},
             "confermato": {"type": "boolean"}}, "required": ["automazione", "operazione"]}},
    ]


AUTOMAZIONI_STRUMENTI = ("crea_automazione", "elenca_automazioni", "gestisci_automazione")


def esegui_strumento(nome_s, inp):
    try:
        if nome_s == "riepilogo_casa":
            return riepilogo()
        if nome_s == "cerca_in_casa":
            return cerca(inp.get("testo", ""))
        if nome_s == "esegui_azione":
            return esegui(inp.get("dominio", ""), inp.get("servizio", ""), inp.get("entita") or [], inp.get("dati") or {}, bool(inp.get("confermato")))
        if nome_s in AUTOMAZIONI_STRUMENTI and not automazioni_attive():
            return L.t("auto_spente")
        if nome_s == "crea_automazione":
            return crea_automazione(inp.get("nome"), inp.get("quando"), inp.get("azioni"), inp.get("giorni"), inp.get("confermato") is True)
        if nome_s == "elenca_automazioni":
            return elenca_automazioni()
        if nome_s == "gestisci_automazione":
            return gestisci_automazione(inp.get("automazione"), inp.get("operazione"), inp.get("confermato") is True)
        return L.t("strumento_ignoto")
    except Exception as e:
        log.warning("strumento %s: %s", nome_s, e)
        return L.t("errore_ha") % str(e)[:150]
