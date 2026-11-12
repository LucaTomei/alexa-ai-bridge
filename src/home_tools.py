"""Home Assistant tools for Alexa AI Bridge: read the state of the home and control it, within strict limits.

Never: locks, doors/gates, alarms, scripts, automations, technical services. Actions on several rooms need
the user's spoken "yes" (checked by the service, not by the model). Tool descriptions are Italian (it-IT skill)."""
import json, os, re, threading, time, urllib.request, logging

HA = os.environ.get("HA_URL", "").rstrip("/")
TOKEN = os.environ.get("HA_TOKEN", "")
UA = os.environ.get("HA_UA") or os.environ.get("HTTP_USER_AGENT", "alexa-ai-bridge/1.0")   # Cloudflare blocks the default "Python-urllib" user agent
ATTIVO = bool(HA and TOKEN) and os.environ.get("HA_TOOLS", "1").strip().lower() in ("1", "true", "yes", "on")
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
SI = re.compile(r"^\s*(s[ii\u00ec]'?|si'|certo|confermo|conferma|ok|okay|va bene|procedi|vai|fallo|esatto|d'accordo|perfetto)\b", re.I)

def azzera_azioni():
    _tl.azioni = []

def azioni_fatte():
    return list(getattr(_tl, "azioni", []))

def imposta_simulazione(attiva):
    """Test chat of the admin page: every check runs, but no command is sent to Home Assistant."""
    _tl.simula = bool(attiva)

def imposta_domanda(testo):
    """Called before every model request: a confirmation counts only if the user's last sentence is a yes."""
    _tl.consenso = bool(SI.match(testo or ""))

def _req(method, path, body=None, timeout=10):
    req = urllib.request.Request(HA + "/api/" + path, None if body is None else json.dumps(body).encode(), method=method,
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": UA})
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

def leggibile(s):
    return s["entity_id"].split(".")[0] in LEGGIBILI and s["state"] not in ("unavailable",)

def _pick(ids):
    m = {s["entity_id"]: s for s in stati()}
    return [m[i] for i in ids if i in m]

def riepilogo():
    S = stati(); m = {s["entity_id"]: s for s in S}
    out = []
    pp = [s for s in S if s["entity_id"].startswith("person.")]
    out.append("Persone: " + "; ".join("%s=%s" % (nome(s), {"home": "a casa", "not_home": "fuori"}.get(s["state"], s["state"])) for s in pp))
    luci = [nome(s) for s in S if s["entity_id"].startswith("light.") and s["state"] == "on" and not re.search(r"channel", s["entity_id"])]
    out.append("Luci accese: " + (", ".join(luci) if luci else "nessuna"))
    tp = [s for s in S if s["entity_id"].startswith("cover.") and not s["entity_id"].endswith("_alexa")]
    out.append("Tapparelle (100=aperta): " + "; ".join("%s %s" % (nome(s), s["attributes"].get("current_position", s["state"])) for s in tp))
    temps = [s for s in S if re.match(TEMP_PATTERN, s["entity_id"])] if TEMP_PATTERN else \
            [s for s in S if s["entity_id"].startswith("sensor.") and s.get("attributes", {}).get("device_class") == "temperature"][:12]
    if temps:
        out.append("Temperature: " + "; ".join("%s %s°" % (nome(s), s["state"]) for s in temps))
    cl = [s for s in S if s["entity_id"].startswith("climate.")]
    out.append("Clima: " + "; ".join("%s %s (stanza %s°, impostata %s°)" % (nome(s), s["state"], s["attributes"].get("current_temperature"), s["attributes"].get("temperature")) for s in cl))
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
        return "Nessuna entita' trovata per '%s'." % testo
    return "\n".join(("[NON COMANDABILE] " if VIETATO.search(s["entity_id"] + " " + nome(s)) else "") + riga(s) for s in hit)

def esegui(dominio, servizio, entita, dati=None, confermato=False):
    if isinstance(entita, str):   # some models send one entity as a plain string
        entita = [x.strip() for x in entita.split(",")]
    entita = [e.strip() for e in (entita or []) if isinstance(e, str) and e.strip()]
    if dominio not in COMANDI or servizio not in COMANDI[dominio]:
        return "Azione non permessa: %s.%s. Permesse: %s" % (dominio, servizio, ", ".join("%s(%s)" % (d, "/".join(sorted(v))) for d, v in COMANDI.items()))
    if not entita or "all" in entita:
        return "Indica le entita' una per una (niente 'all')."
    S = {s["entity_id"]: s for s in stati()}
    for e in entita:
        if not e.startswith(dominio + "."):
            return "L'entita' %s non e' del dominio %s." % (e, dominio)
        if e not in S:
            return "L'entita' %s non esiste: usa cerca_in_casa." % e
        if VIETATO.search(e + " " + nome(S[e])):
            return "Per sicurezza non posso comandare %s (%s): serrature, portone, antifurto e servizi tecnici sono esclusi." % (nome(S[e]), e)
    dati = {k: v for k, v in (dati if isinstance(dati, dict) else {}).items() if k in ("brightness_pct", "position", "temperature", "hvac_mode", "humidity", "color_temp_kelvin", "rgb_color")}
    multi = len(entita) > MAX_SENZA_CONFERMA or any(e in GRUPPI for e in entita)
    if multi and not (confermato and getattr(_tl, "consenso", False)):
        return ("SERVE CONFERMA: l'azione riguarda piu' stanze (%s). Chiedi all'utente una conferma breve e non eseguire: "
                "solo quando l'utente avra' risposto si', richiama esegui_azione con confermato=true.") % ", ".join(nome(S[e]) for e in entita)
    simulata = getattr(_tl, "simula", False)
    if not simulata:
        _req("POST", "services/%s/%s" % (dominio, servizio), dict(dati, entity_id=entita), timeout=15)
        _cache["t"] = 0
    log.info("azione HA%s: %s.%s %s %s", " (simulata)" if simulata else "", dominio, servizio, ",".join(entita), json.dumps(dati) if dati else "")
    _tl.azioni = getattr(_tl, "azioni", []) + ["%s%s.%s %s%s" % ("[simulata] " if simulata else "", dominio, servizio, ",".join(entita), (" " + json.dumps(dati)) if dati else "")]
    return "Fatto: %s.%s su %s." % (dominio, servizio, ", ".join(nome(S[e]) for e in entita))

STRUMENTI = [
    {"name": "riepilogo_casa", "description": "Stato generale della casa: chi e' a casa, luci accese, tapparelle, temperature, clima, consumo, porta, rifiuti, pioggia. Usalo per domande generiche sulla casa.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "cerca_in_casa", "description": "Cerca dispositivi e sensori di casa per nome o stanza (es. 'luci salone', 'tapparella camera', 'temperatura bagno', 'lavatrice'). Restituisce entity_id, nome e stato. Usalo prima di comandare per trovare l'entity_id giusto.",
     "parameters": {"type": "object", "properties": {"testo": {"type": "string"}}, "required": ["testo"]}},
    {"name": "esegui_azione", "description": "Comanda dispositivi di casa. Domini e servizi permessi: light(turn_on,turn_off,toggle; dati: brightness_pct), cover(open_cover,close_cover,stop_cover,set_cover_position; dati: position 0=chiusa 100=aperta), climate(turn_on,turn_off,set_temperature,set_hvac_mode; dati: temperature, hvac_mode), switch(turn_on,turn_off,toggle), fan, humidifier(set_humidity), scene(turn_on). Serrature, portone e antifurto NON sono comandabili. Per azioni su piu' stanze serve confermato=true dopo il si' dell'utente.",
     "parameters": {"type": "object", "properties": {
         "dominio": {"type": "string"}, "servizio": {"type": "string"},
         "entita": {"type": "array", "items": {"type": "string"}, "description": "entity_id esatti"},
         "dati": {"type": "object"}, "confermato": {"type": "boolean"}}, "required": ["dominio", "servizio", "entita"]}},
]

def esegui_strumento(nome_s, inp):
    try:
        if nome_s == "riepilogo_casa":
            return riepilogo()
        if nome_s == "cerca_in_casa":
            return cerca(inp.get("testo", ""))
        if nome_s == "esegui_azione":
            return esegui(inp.get("dominio", ""), inp.get("servizio", ""), inp.get("entita") or [], inp.get("dati") or {}, bool(inp.get("confermato")))
        return "Strumento sconosciuto."
    except Exception as e:
        log.warning("strumento %s: %s", nome_s, e)
        return "Errore nel contattare Home Assistant: %s" % str(e)[:150]
