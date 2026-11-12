"""Settings changed from the admin page.

They are stored as JSON in DATA_DIR/settings.json (a Docker volume) and override the values from .env. This module is
imported before every other one, so the overrides are in os.environ when the other modules read their settings.
Saving restarts the gunicorn worker, which imports everything again with the new values."""
import json, os, tempfile

DATA_DIR = os.environ.get("DATA_DIR", "/data")
FILE = os.path.join(DATA_DIR, "settings.json")

# name, group, label, kind (text | secret | select | number | textarea), options, help
CAMPI = [
    ("SKILL_ID", "Alexa", "Skill ID", "text", None, "amzn1.ask.skill.… dalla console Alexa: le richieste per altre skill sono rifiutate."),
    ("LLM_API", "Modello", "Formato API", "select", ["", "anthropic", "openai"],
     "anthropic (Claude) oppure openai (qualsiasi endpoint compatibile). Vuoto: dedotto dall'URL."),
    ("LLM_BASE_URL", "Modello", "URL base", "text", None, "Es. https://api.anthropic.com/v1 oppure http://host.docker.internal:11434/v1"),
    ("LLM_API_KEY", "Modello", "Chiave API", "secret", None, "Vuota per i modelli locali."),
    ("LLM_MODEL", "Modello", "Modello", "text", None, "Nome del modello dal listino del fornitore. I modelli veloci suonano meglio."),
    ("LLM_MAX_TOKENS", "Modello", "Token massimi per risposta", "number", None, "Default 1024."),
    ("LLM_EXTRA_JSON", "Modello", "Campi extra (JSON)", "text", None, "Aggiunti a ogni richiesta, es. {\"reasoning_effort\": \"low\"}"),
    ("ATTESA_MAX", "Tempi", "Attesa massima (s)", "number", None, "Oltre questo tempo Alexa dice \"Ci sto pensando\". Al massimo 7."),
    ("LLM_TIMEOUT_LUNGO", "Tempi", "Tempo massimo in background (s)", "number", None, "Default 120."),
    ("WEB_SEARCH", "Ricerca web", "Ricerca web", "select", ["auto", "native", "searxng", "brave", "tavily", "off"],
     "auto: Claude usa la ricerca nativa, gli altri modelli il primo servizio configurato."),
    ("SEARXNG_URL", "Ricerca web", "URL SearXNG", "text", None, "Con il container incluso: http://searxng:8080"),
    ("BRAVE_API_KEY", "Ricerca web", "Chiave Brave Search", "secret", None, ""),
    ("TAVILY_API_KEY", "Ricerca web", "Chiave Tavily", "secret", None, ""),
    ("WEB_RESULTS", "Ricerca web", "Risultati per ricerca", "number", None, "Default 5."),
    ("WEB_LANGUAGE", "Ricerca web", "Lingua di ricerca", "text", None, "Default it."),
    ("WEB_MAX", "Ricerca web", "Ricerche native per domanda", "number", None, "Solo Claude. Default 3."),
    ("HOME_CITY", "Luogo", "Città", "text", None, "Per meteo e ricerche locali."),
    ("HOME_REGION", "Luogo", "Regione", "text", None, ""),
    ("HOME_COUNTRY", "Luogo", "Paese (codice)", "text", None, "Es. IT"),
    ("HOME_TIMEZONE", "Luogo", "Fuso orario", "text", None, "Es. Europe/Rome"),
    ("HA_URL", "Home Assistant", "URL", "text", None, "Es. https://homeassistant.example.com"),
    ("HA_TOKEN", "Home Assistant", "Token", "secret", None, "Token di un utente dedicato non amministratore. Vuoto: strumenti casa spenti."),
    ("HA_TOOLS", "Home Assistant", "Strumenti casa", "select", ["1", "0"], "1 attivi, 0 spenti."),
    ("HA_GRUPPI", "Home Assistant", "Entità su più stanze", "text", None, "Separate da virgole: chiedono sempre conferma."),
    ("HA_MAX_SENZA_CONFERMA", "Home Assistant", "Entità senza conferma", "number", None, "Oltre questo numero serve un sì. Default 3."),
    ("HA_SUMMARY_EXTRA", "Home Assistant", "Righe extra nel riepilogo", "text", None, "entity_id=Etichetta,entity_id=Etichetta"),
    ("HA_TEMP_PATTERN", "Home Assistant", "Sensori di temperatura (regex)", "text", None, "Vuoto: tutti i sensori di temperatura (max 12)."),
    ("HA_VIETATO", "Home Assistant", "Altre entità vietate (regex)", "text", None,
     "Si aggiunge alla lista di sicurezza incorporata, non la sostituisce. Es. garage|irrigazione"),
    ("SYSTEM_PROMPT", "Avanzate", "Prompt di sistema", "textarea", None, "Vuoto: le regole vocali italiane incluse."),
    ("ISTRUZIONI_TURNO", "Avanzate", "Istruzioni a ogni domanda", "textarea", None, "Vuoto: quelle incluse."),
    ("HTTP_USER_AGENT", "Avanzate", "User agent", "text", None, "Default alexa-ai-bridge/1.0"),
]
NOMI = {c[0] for c in CAMPI}
# what the service uses when a setting is empty (shown as placeholder on the page)
PREDEFINITI = {"LLM_MAX_TOKENS": "1024", "ATTESA_MAX": "6", "LLM_TIMEOUT_LUNGO": "120", "WEB_RESULTS": "5", "WEB_LANGUAGE": "it",
               "WEB_MAX": "3", "HOME_TIMEZONE": "Europe/Rome", "HA_MAX_SENZA_CONFERMA": "3", "HTTP_USER_AGENT": "alexa-ai-bridge/1.0",
               "LLM_EXTRA_JSON": "{}", "WEB_SEARCH": "auto", "HA_TOOLS": "1"}
SEGRETI = {c[0] for c in CAMPI if c[3] == "secret"}

BASE = {}        # value from the environment (.env) of every overridden setting, before the override
OVERRIDE = {}    # settings saved from the admin page


def leggi():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return {k: str(v) for k, v in d.items() if k in NOMI} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def carica():
    """Apply the saved settings to os.environ (called once, at import)."""
    OVERRIDE.clear(); BASE.clear()
    for k, v in leggi().items():
        BASE[k] = os.environ.get(k)
        OVERRIDE[k] = v
        os.environ[k] = v


def scrivibile():
    return os.path.isdir(DATA_DIR) and os.access(DATA_DIR, os.W_OK)


def ambiente_con(nuovi):
    """The environment the service would have with these overrides instead of the current ones."""
    env = dict(os.environ)
    for k in OVERRIDE:
        if BASE.get(k) is None:
            env.pop(k, None)
        else:
            env[k] = BASE[k]
    env.update(nuovi)
    return env


def salva(nuovi):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix=".settings-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(nuovi, f, indent=2, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, FILE)


def valori():
    """Current settings for the page; secrets are never sent, only whether they are set."""
    out = []
    for nome, gruppo, etichetta, tipo, opzioni, aiuto in CAMPI:
        v = os.environ.get(nome, "")
        out.append({"nome": nome, "gruppo": gruppo, "etichetta": etichetta, "tipo": tipo, "opzioni": opzioni, "aiuto": aiuto,
                    "predefinito": PREDEFINITI.get(nome, ""),
                    "valore": None if nome in SEGRETI else v, "impostato": bool(v),
                    "origine": "pagina" if nome in OVERRIDE else ("env" if nome in os.environ else "default")})
    return out


carica()
