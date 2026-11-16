"""Settings changed from the admin page.

They are stored as JSON in DATA_DIR/settings.json (a Docker volume) and override the values from .env. This module is
imported before every other one, so the overrides are in os.environ when the other modules read their settings.
Saving restarts the gunicorn worker, which imports everything again with the new values."""
import json, math, os, re, tempfile
from urllib.parse import urlsplit

DATA_DIR = os.environ.get("DATA_DIR", "/data")
FILE = os.path.join(DATA_DIR, "settings.json")

# name, group, kind (text | secret | select | number | textarea), options, (label, help) in Italian, (label, help) in English
CAMPI = [
    ("SKILL_ID", "alexa", "text", None,
     ("Skill ID", "amzn1.ask.skill.… dalla console Alexa: le richieste per altre skill sono rifiutate."),
     ("Skill ID", "amzn1.ask.skill.… from the Alexa console: requests for other skills are refused.")),
    ("LANGUAGE", "alexa", "select", ["auto", "it", "en"],
     ("Lingua dell'assistente", "auto risponde nella lingua in cui parla l'Echo: una sola skill con modello italiano e inglese parla entrambe (scheda Sistema)."),
     ("Assistant language", "auto answers in the language the Echo speaks: one skill with an Italian and an English model speaks both (System tab).")),
    ("LLM_API", "modello", "select", ["", "anthropic", "openai"],
     ("Formato API", "anthropic (Claude) oppure openai (qualsiasi endpoint compatibile). Vuoto: dedotto dall'URL."),
     ("API format", "anthropic (Claude) or openai (any compatible endpoint). Empty: guessed from the URL.")),
    ("LLM_BASE_URL", "modello", "text", None,
     ("URL base", "Es. https://api.anthropic.com/v1 oppure http://host.docker.internal:11434/v1. Cambiandolo va reinserita la chiave."),
     ("Base URL", "E.g. https://api.anthropic.com/v1 or http://host.docker.internal:11434/v1. Changing it requires the key again.")),
    ("LLM_API_KEY", "modello", "secret", None, ("Chiave API", "Vuota per i modelli locali."), ("API key", "Empty for local models.")),
    ("LLM_MODEL", "modello", "text", None,
     ("Modello", "Nome del modello dal listino del fornitore. I modelli veloci suonano meglio."),
     ("Model", "Model name from the provider's list. Fast models sound best.")),
    ("LLM_MAX_TOKENS", "modello", "number", None, ("Token massimi per risposta", ""), ("Max tokens per answer", "")),
    ("LLM_EXTRA_JSON", "modello", "text", None,
     ("Campi extra (JSON)", "Aggiunti a ogni richiesta, es. {\"reasoning_effort\": \"low\"}"),
     ("Extra fields (JSON)", "Added to every request, e.g. {\"reasoning_effort\": \"low\"}")),
    ("LLM_PAUSA", "modello", "number", None,
     ("Pausa di un modello che non risponde (s)", "Un modello non raggiungibile, scollegato o senza credito viene saltato per questo tempo e risponde il successivo; 0 lo riprova a ogni domanda. Più comodo dalla scheda Modelli."),
     ("Pause of a model that does not answer (s)", "A model that is unreachable, logged out or out of credit is skipped for this long and the next one answers; 0 tries it again at every question. Easier from the Models tab.")),
    ("LLM_CONTROLLO", "modello", "number", None,
     ("Controllo dei modelli (minuti)", "Ogni quanto verificare in background che ogni modello risponda (non consuma token); 0 mai."),
     ("Model check (minutes)", "How often to check in the background that every model answers (uses no tokens); 0 never.")),
    ("LLM_2_ATTIVO", "riserva2", "select", ["1", "0"], ("Usa questo modello", "0 lo salta senza cancellarlo."), ("Use this model", "0 skips it without removing it.")),
    ("LLM_2_API", "riserva2", "select", ["", "anthropic", "openai"],
     ("Formato API", "anthropic oppure openai (qualsiasi endpoint compatibile, anche CLIProxyAPI). Vuoto: dedotto dall'URL."),
     ("API format", "anthropic or openai (any compatible endpoint, CLIProxyAPI too). Empty: guessed from the URL.")),
    ("LLM_2_BASE_URL", "riserva2", "text", None,
     ("URL base", "Es. http://cliproxyapi:8317/v1. Vuoto: modello non usato. Cambiandolo va reinserita la chiave."),
     ("Base URL", "E.g. http://cliproxyapi:8317/v1. Empty: model not used. Changing it requires the key again.")),
    ("LLM_2_API_KEY", "riserva2", "secret", None, ("Chiave API", "Vuota per i modelli locali."), ("API key", "Empty for local models.")),
    ("LLM_2_MODEL", "riserva2", "text", None, ("Modello", "Nome del modello."), ("Model", "Model name.")),
    ("LLM_2_EXTRA_JSON", "riserva2", "text", None,
     ("Campi extra (JSON)", "Aggiunti a ogni richiesta a questo modello."), ("Extra fields (JSON)", "Added to every request to this model.")),
    ("LLM_3_ATTIVO", "riserva3", "select", ["1", "0"], ("Usa questo modello", "0 lo salta senza cancellarlo."), ("Use this model", "0 skips it without removing it.")),
    ("LLM_3_API", "riserva3", "select", ["", "anthropic", "openai"],
     ("Formato API", "anthropic oppure openai (qualsiasi endpoint compatibile, anche CLIProxyAPI). Vuoto: dedotto dall'URL."),
     ("API format", "anthropic or openai (any compatible endpoint, CLIProxyAPI too). Empty: guessed from the URL.")),
    ("LLM_3_BASE_URL", "riserva3", "text", None,
     ("URL base", "Es. http://cliproxyapi:8317/v1. Vuoto: modello non usato. Cambiandolo va reinserita la chiave."),
     ("Base URL", "E.g. http://cliproxyapi:8317/v1. Empty: model not used. Changing it requires the key again.")),
    ("LLM_3_API_KEY", "riserva3", "secret", None, ("Chiave API", "Vuota per i modelli locali."), ("API key", "Empty for local models.")),
    ("LLM_3_MODEL", "riserva3", "text", None, ("Modello", "Nome del modello."), ("Model", "Model name.")),
    ("LLM_3_EXTRA_JSON", "riserva3", "text", None,
     ("Campi extra (JSON)", "Aggiunti a ogni richiesta a questo modello."), ("Extra fields (JSON)", "Added to every request to this model.")),
    ("LLM_4_ATTIVO", "riserva4", "select", ["1", "0"], ("Usa questo modello", "0 lo salta senza cancellarlo."), ("Use this model", "0 skips it without removing it.")),
    ("LLM_4_API", "riserva4", "select", ["", "anthropic", "openai"],
     ("Formato API", "anthropic oppure openai (qualsiasi endpoint compatibile, anche CLIProxyAPI). Vuoto: dedotto dall'URL."),
     ("API format", "anthropic or openai (any compatible endpoint, CLIProxyAPI too). Empty: guessed from the URL.")),
    ("LLM_4_BASE_URL", "riserva4", "text", None,
     ("URL base", "Es. http://cliproxyapi:8317/v1. Vuoto: modello non usato. Cambiandolo va reinserita la chiave."),
     ("Base URL", "E.g. http://cliproxyapi:8317/v1. Empty: model not used. Changing it requires the key again.")),
    ("LLM_4_API_KEY", "riserva4", "secret", None, ("Chiave API", "Vuota per i modelli locali."), ("API key", "Empty for local models.")),
    ("LLM_4_MODEL", "riserva4", "text", None, ("Modello", "Nome del modello."), ("Model", "Model name.")),
    ("LLM_4_EXTRA_JSON", "riserva4", "text", None,
     ("Campi extra (JSON)", "Aggiunti a ogni richiesta a questo modello."), ("Extra fields (JSON)", "Added to every request to this model.")),
    ("LLM_5_ATTIVO", "riserva5", "select", ["1", "0"], ("Usa questo modello", "0 lo salta senza cancellarlo."), ("Use this model", "0 skips it without removing it.")),
    ("LLM_5_API", "riserva5", "select", ["", "anthropic", "openai"],
     ("Formato API", "anthropic oppure openai (qualsiasi endpoint compatibile, anche CLIProxyAPI). Vuoto: dedotto dall'URL."),
     ("API format", "anthropic or openai (any compatible endpoint, CLIProxyAPI too). Empty: guessed from the URL.")),
    ("LLM_5_BASE_URL", "riserva5", "text", None,
     ("URL base", "Es. http://cliproxyapi:8317/v1. Vuoto: modello non usato. Cambiandolo va reinserita la chiave."),
     ("Base URL", "E.g. http://cliproxyapi:8317/v1. Empty: model not used. Changing it requires the key again.")),
    ("LLM_5_API_KEY", "riserva5", "secret", None, ("Chiave API", "Vuota per i modelli locali."), ("API key", "Empty for local models.")),
    ("LLM_5_MODEL", "riserva5", "text", None, ("Modello", "Nome del modello."), ("Model", "Model name.")),
    ("LLM_5_EXTRA_JSON", "riserva5", "text", None,
     ("Campi extra (JSON)", "Aggiunti a ogni richiesta a questo modello."), ("Extra fields (JSON)", "Added to every request to this model.")),
    ("ATTESA_MAX", "tempi", "number", None,
     ("Attesa massima (s)", "Oltre questo tempo Alexa dice \"Ci sto pensando\". Da 1 a 7.5."),
     ("Maximum wait (s)", "Beyond this Alexa says \"Let me think\". From 1 to 7.5.")),
    ("LLM_TIMEOUT_LUNGO", "tempi", "number", None, ("Tempo massimo in background (s)", ""), ("Maximum background time (s)", "")),
    ("WEB_SEARCH", "web", "select", ["auto", "native", "searxng", "brave", "tavily", "off"],
     ("Ricerca web", "auto: Claude usa la ricerca nativa, gli altri modelli il primo servizio configurato."),
     ("Web search", "auto: Claude uses its native search, other models the first configured service.")),
    ("SEARXNG_URL", "web", "text", None, ("URL SearXNG", "Con il container incluso: http://searxng:8080"),
     ("SearXNG URL", "With the bundled container: http://searxng:8080")),
    ("BRAVE_API_KEY", "web", "secret", None, ("Chiave Brave Search", ""), ("Brave Search key", "")),
    ("TAVILY_API_KEY", "web", "secret", None, ("Chiave Tavily", ""), ("Tavily key", "")),
    ("WEB_RESULTS", "web", "number", None, ("Risultati per ricerca", ""), ("Results per search", "")),
    ("WEB_LANGUAGE", "web", "text", None, ("Lingua di ricerca", "Vuoto: la lingua dell'assistente."),
     ("Search language", "Empty: the assistant's language.")),
    ("WEB_MAX", "web", "number", None, ("Ricerche native per domanda", "Solo Claude."), ("Native searches per question", "Claude only.")),
    ("HOME_CITY", "luogo", "text", None, ("Città", "Per meteo e ricerche locali."), ("City", "For weather and local searches.")),
    ("HOME_REGION", "luogo", "text", None, ("Regione", ""), ("Region", "")),
    ("HOME_COUNTRY", "luogo", "text", None, ("Paese (codice)", "Es. IT"), ("Country (code)", "E.g. GB")),
    ("HOME_TIMEZONE", "luogo", "text", None, ("Fuso orario", "Es. Europe/Rome"), ("Time zone", "E.g. Europe/London")),
    ("HA_URL", "casa", "text", None,
     ("URL", "Es. https://homeassistant.example.com. Cambiandolo va reinserito il token."),
     ("URL", "E.g. https://homeassistant.example.com. Changing it requires the token again.")),
    ("HA_TOKEN", "casa", "secret", None,
     ("Token", "Token di un utente dedicato non amministratore. Vuoto: strumenti casa spenti."),
     ("Token", "Token of a dedicated non-admin user. Empty: home tools off.")),
    ("HA_TOOLS", "casa", "select", ["1", "0"], ("Strumenti casa", "1 attivi, 0 spenti."), ("Home tools", "1 on, 0 off.")),
    ("HA_GRUPPI", "casa", "text", None,
     ("Entità su più stanze", "Separate da virgole: chiedono sempre conferma. Più comodo dalla scheda Casa."),
     ("Entities for several rooms", "Comma separated: they always need a yes. Easier from the Home tab.")),
    ("HA_MAX_SENZA_CONFERMA", "casa", "number", None, ("Entità senza conferma", "Oltre questo numero serve un sì."),
     ("Entities without confirmation", "Above this number a yes is needed.")),
    ("HA_SUMMARY_EXTRA", "casa", "text", None, ("Righe extra nel riepilogo", "entity_id=Etichetta,entity_id=Etichetta"),
     ("Extra summary lines", "entity_id=Label,entity_id=Label")),
    ("HA_TEMP_PATTERN", "casa", "text", None, ("Sensori di temperatura (regex)", "Vuoto: tutti i sensori di temperatura (max 12)."),
     ("Temperature sensors (regex)", "Empty: every temperature sensor (max 12).")),
    ("HA_VIETATO", "casa", "text", None,
     ("Altre entità vietate (regex)", "Si aggiunge alla lista di sicurezza incorporata. Più comodo dalla scheda Casa."),
     ("Other forbidden entities (regex)", "Added to the built-in safety list. Easier from the Home tab.")),
    ("HA_AUTOMAZIONI", "casa", "select", ["0", "1"],
     ("Automazioni a voce", "1: l'assistente può creare, attivare, disattivare ed eliminare automazioni di Home Assistant, sempre con un sì a voce. Più comodo dalla scheda Automazioni."),
     ("Automations by voice", "1: the assistant can create, enable, disable and delete Home Assistant automations, always after a spoken yes. Easier from the Automations tab.")),
    ("HA_AUTOMAZIONI_TOKEN", "casa", "secret", None,
     ("Token per le automazioni", "Home Assistant fa creare ed eliminare automazioni solo agli amministratori: token di un utente amministratore, usato solo per questo. Vuoto: il token sopra."),
     ("Token for automations", "Home Assistant lets only administrators create and delete automations: an administrator's token, used only for that. Empty: the token above.")),
    ("HA_AUTOMAZIONI_MAX", "casa", "number", None, ("Automazioni a voce al massimo", ""), ("Maximum automations by voice", "")),
    ("NOTIFY_ATTIVE", "notifiche", "select", ["1", "0"],
     ("Notifiche", "0 le sospende tutte senza cancellare i canali. Più comodo dalla scheda Notifiche."),
     ("Notifications", "0 pauses them all without removing the channels. Easier from the Notifications tab.")),
    ("NOTIFY_EVENTI", "notifiche", "text", None,
     ("Eventi", "Separati da virgole: confermate, bloccate, automazioni, modelli, azioni, errori, memoria, pannello; none per nessuno. Più comodo dalla scheda Notifiche."),
     ("Events", "Comma separated: confermate, bloccate, automazioni, modelli, azioni, errori, memoria, pannello; none for none. Easier from the Notifications tab.")),
    ("NOTIFY_MAX_ORA", "notifiche", "number", None, ("Notifiche all'ora al massimo", "Oltre, le successive non partono (contro le raffiche)."),
     ("Maximum notifications per hour", "Beyond this the next ones are not sent (against bursts).")),
    ("NOTIFY_HA", "notifiche", "text", None,
     ("App Home Assistant: servizi notify", "Es. mobile_app_iphone_di_luca, separati da virgole: usa il token di Home Assistant sopra. Più comodo dalla scheda Notifiche."),
     ("Home Assistant app: notify services", "E.g. mobile_app_my_phone, comma separated: uses the Home Assistant token above. Easier from the Notifications tab.")),
    ("NOTIFY_TELEGRAM_TOKEN", "notifiche", "secret", None, ("Telegram: token del bot", "Da @BotFather."), ("Telegram: bot token", "From @BotFather.")),
    ("NOTIFY_TELEGRAM_CHAT", "notifiche", "text", None,
     ("Telegram: chat ID", "La tua chat con il bot (scrivigli /start, poi leggi l'ID con @userinfobot) o un gruppo."),
     ("Telegram: chat ID", "Your chat with the bot (send it /start, then get the ID from @userinfobot) or a group.")),
    ("NOTIFY_NTFY_URL", "notifiche", "secret", None,
     ("ntfy: indirizzo del topic", "Es. https://ntfy.sh/un-nome-difficile-da-indovinare: chi conosce il topic legge le notifiche."),
     ("ntfy: topic address", "E.g. https://ntfy.sh/a-name-hard-to-guess: whoever knows the topic reads the notifications.")),
    ("NOTIFY_NTFY_TOKEN", "notifiche", "secret", None, ("ntfy: token", "Solo per un server con accesso protetto."),
     ("ntfy: token", "Only for a server with access control.")),
    ("NOTIFY_GOTIFY_URL", "notifiche", "text", None, ("Gotify: indirizzo del server", "Es. https://gotify.example.com"),
     ("Gotify: server address", "E.g. https://gotify.example.com")),
    ("NOTIFY_GOTIFY_TOKEN", "notifiche", "secret", None, ("Gotify: token dell'applicazione", ""), ("Gotify: application token", "")),
    ("NOTIFY_WEBHOOK_URL", "notifiche", "secret", None,
     ("Webhook: indirizzo", "Riceve un POST JSON (title, text, content, message): va bene per Discord, Slack, n8n, Node-RED."),
     ("Webhook: address", "Receives a JSON POST (title, text, content, message): works with Discord, Slack, n8n, Node-RED.")),
    ("NOTIFY_WEBHOOK_TOKEN", "notifiche", "secret", None, ("Webhook: token", "Facoltativo, inviato come Authorization: Bearer."),
     ("Webhook: token", "Optional, sent as Authorization: Bearer.")),
    ("MEMORIA", "memoria", "select", ["1", "0"],
     ("Memoria", "1: l'assistente ricorda chi abita in casa da una conversazione all'altra. Più comodo dalla scheda Memoria."),
     ("Memory", "1: the assistant remembers the people at home from one conversation to the next. Easier from the Memory tab.")),
    ("MEMORIA_AUTO", "memoria", "select", ["1", "0"],
     ("Impara da solo", "1: dopo ogni risposta una breve richiesta in background cerca fatti nuovi da ricordare (qualche token in più); 0: solo quando glielo chiedi o lo decide il modello."),
     ("Learn by itself", "1: after every answer a short background request looks for new facts to remember (a few more tokens); 0: only when you ask or the model decides.")),
    ("MEMORIA_MAX", "memoria", "number", None, ("Fatti ricordati al massimo", "Oltre, si dimenticano i più vecchi."),
     ("Maximum facts remembered", "Beyond this the oldest are forgotten.")),
    ("MEMORIA_RECENTI", "memoria", "number", None,
     ("Scambi delle conversazioni precedenti", "Quante domande e risposte delle volte prima il modello rilegge; 0 nessuna."),
     ("Exchanges from earlier conversations", "How many questions and answers from earlier times the model reads again; 0 none.")),
    ("MEMORIA_GIORNI", "memoria", "number", None, ("Per quanti giorni", "Gli scambi più vecchi non si rileggono."),
     ("For how many days", "Older exchanges are not read again.")),
    ("MEMORIA_ISTRUZIONI", "memoria", "textarea", None,
     ("Cosa ricordare", "Vuoto: fatti duraturi su chi abita in casa (nomi, parentele, gusti, abitudini, orari, compleanni, animali)."),
     ("What to remember", "Empty: lasting facts about the people at home (names, relationships, tastes, habits, schedules, birthdays, pets).")),
    ("ADMIN_HISTORY", "pannello", "number", None, ("Domande nello storico", "0 spegne lo storico."),
     ("Questions in the history", "0 turns the history off.")),
    ("SYSTEM_PROMPT", "avanzate", "textarea", None, ("Prompt di sistema", "Vuoto: le regole vocali incluse, nella lingua scelta."),
     ("System prompt", "Empty: the built-in voice rules, in the chosen language.")),
    ("ISTRUZIONI_TURNO", "avanzate", "textarea", None, ("Istruzioni a ogni domanda", "Vuoto: quelle incluse."),
     ("Instructions with every question", "Empty: the built-in ones.")),
    ("HTTP_USER_AGENT", "avanzate", "text", None, ("User agent", ""), ("User agent", "")),
    ("HA_UA", "avanzate", "text", None, ("User agent per Home Assistant", "Vuoto: lo user agent sopra."),
     ("User agent for Home Assistant", "Empty: the user agent above.")),
    ("BRAVE_URL", "avanzate", "text", None, ("Endpoint Brave", "Vuoto: l'API ufficiale."), ("Brave endpoint", "Empty: the official API.")),
    ("TAVILY_URL", "avanzate", "text", None, ("Endpoint Tavily", "Vuoto: l'API ufficiale."), ("Tavily endpoint", "Empty: the official API.")),
    ("NOTIFY_TELEGRAM_URL", "avanzate", "text", None, ("Endpoint Telegram", "Vuoto: l'API ufficiale."), ("Telegram endpoint", "Empty: the official API.")),
]
GRUPPI = {"alexa": ("Alexa", "Alexa"), "modello": ("Modello", "Model"),
          **{"riserva%d" % n: ("Modello %d (di riserva)" % n, "Model %d (fallback)" % n) for n in range(2, 6)},
          "tempi": ("Tempi", "Timing"),
          "web": ("Ricerca web", "Web search"), "luogo": ("Luogo", "Location"), "casa": ("Home Assistant", "Home Assistant"),
          "notifiche": ("Notifiche", "Notifications"), "memoria": ("Memoria", "Memory"), "pannello": ("Pannello", "Admin page"), "avanzate": ("Avanzate", "Advanced")}
NOMI = {c[0] for c in CAMPI}
TIPO = {c[0]: c[2] for c in CAMPI}
OPZIONI = {c[0]: c[3] for c in CAMPI}
# what the service uses when a setting is empty (shown as placeholder on the page)
PREDEFINITI = {"LLM_MAX_TOKENS": "1024", "ATTESA_MAX": "6", "LLM_TIMEOUT_LUNGO": "120", "WEB_RESULTS": "5",
               "WEB_MAX": "3", "HOME_TIMEZONE": "Europe/Rome", "HA_MAX_SENZA_CONFERMA": "3", "HTTP_USER_AGENT": "alexa-ai-bridge/1.0",
               "LLM_EXTRA_JSON": "{}", "WEB_SEARCH": "auto", "HA_TOOLS": "1", "LANGUAGE": "auto", "ADMIN_HISTORY": "100",
               "HA_AUTOMAZIONI": "0", "HA_AUTOMAZIONI_MAX": "20", "NOTIFY_ATTIVE": "1", "NOTIFY_MAX_ORA": "30",
               "NOTIFY_EVENTI": "confermate,bloccate,automazioni,modelli", "NOTIFY_TELEGRAM_URL": "https://api.telegram.org",
               "BRAVE_URL": "https://api.search.brave.com/res/v1/web/search", "TAVILY_URL": "https://api.tavily.com/search",
               "LLM_PAUSA": "300", "LLM_CONTROLLO": "10", "MEMORIA": "1", "MEMORIA_AUTO": "1", "MEMORIA_MAX": "100",
               "MEMORIA_RECENTI": "4", "MEMORIA_GIORNI": "7",
               **{"LLM_%d_%s" % (n, k): v for n in range(2, 6) for k, v in (("ATTIVO", "1"), ("EXTRA_JSON", "{}"))}}
# what an empty setting means, when it is not a plain value (Italian, English)
PREDEFINITI_TESTO = {
    "LLM_API": ("dedotto dall'URL", "guessed from the URL"),
    "WEB_LANGUAGE": ("la lingua dell'assistente", "the assistant's language"),
    "HA_GRUPPI": ("nessuna", "none"), "HA_SUMMARY_EXTRA": ("nessuna", "none"),
    "HA_TEMP_PATTERN": ("tutti i sensori di temperatura", "every temperature sensor"),
    "HA_VIETATO": ("solo la lista incorporata", "the built-in list only"),
    "SYSTEM_PROMPT": ("le regole incluse", "the built-in rules"), "ISTRUZIONI_TURNO": ("quelle incluse", "the built-in ones"),
    "HA_UA": ("lo user agent generale", "the general user agent"),
    "SEARXNG_URL": ("nessuno", "none"), "HOME_CITY": ("nessuna", "none"), "HOME_REGION": ("nessuna", "none"),
    "HOME_COUNTRY": ("nessuno", "none"), "HA_URL": ("nessuno: strumenti casa spenti", "none: home tools off"),
    "LLM_API_KEY": ("nessuna", "none"), "BRAVE_API_KEY": ("nessuna", "none"), "TAVILY_API_KEY": ("nessuna", "none"),
    "HA_TOKEN": ("nessuno: strumenti casa spenti", "none: home tools off"),
    "HA_AUTOMAZIONI_TOKEN": ("il token sopra", "the token above"),
    "NOTIFY_HA": ("nessuno", "none"), "NOTIFY_TELEGRAM_TOKEN": ("nessuno", "none"), "NOTIFY_TELEGRAM_CHAT": ("nessuna", "none"),
    "NOTIFY_NTFY_URL": ("nessuno", "none"), "NOTIFY_NTFY_TOKEN": ("nessuno", "none"), "NOTIFY_GOTIFY_URL": ("nessuno", "none"),
    "NOTIFY_GOTIFY_TOKEN": ("nessuno", "none"), "NOTIFY_WEBHOOK_URL": ("nessuno", "none"), "NOTIFY_WEBHOOK_TOKEN": ("nessuno", "none"),
    "MEMORIA_ISTRUZIONI": ("fatti duraturi su chi abita in casa", "lasting facts about the people at home"),
    **{"LLM_%d_%s" % (n, k): v for n in range(2, 6) for k, v in (
        ("API", ("dedotto dall'URL", "guessed from the URL")), ("BASE_URL", ("nessuno: non usato", "none: not used")),
        ("API_KEY", ("nessuna", "none")), ("MODEL", ("nessuno", "none")))},
}
SEGRETI = {c[0] for c in CAMPI if c[2] == "secret"}

# numbers: (minimum, maximum, integer only)
LIMITI = {"LLM_MAX_TOKENS": (1, 200000, True), "ATTESA_MAX": (1, 7.5, False), "LLM_TIMEOUT_LUNGO": (5, 900, False),
          "WEB_RESULTS": (1, 20, True), "WEB_MAX": (1, 20, True), "HA_MAX_SENZA_CONFERMA": (0, 100, True),
          "ADMIN_HISTORY": (0, 1000, True), "HA_AUTOMAZIONI_MAX": (1, 200, True), "NOTIFY_MAX_ORA": (1, 1000, True),
          "LLM_PAUSA": (0, 86400, True), "LLM_CONTROLLO": (0, 1440, True), "MEMORIA_MAX": (1, 1000, True),
          "MEMORIA_RECENTI": (0, 20, True), "MEMORIA_GIORNI": (1, 365, True)}
# endpoints the service sends keys and tokens to: only http(s), never file:// or other schemes
URL = ("LLM_BASE_URL", "HA_URL", "SEARXNG_URL", "BRAVE_URL", "TAVILY_URL", "NOTIFY_TELEGRAM_URL", "NOTIFY_NTFY_URL",
       "NOTIFY_GOTIFY_URL", "NOTIFY_WEBHOOK_URL") + tuple("LLM_%d_BASE_URL" % n for n in range(2, 6))
# notifications: the events that can send one (the first four are the default)
EVENTI_NOTIFICHE = ("confermate", "bloccate", "automazioni", "modelli", "azioni", "errori", "memoria", "pannello")
EVENTI_PREDEFINITI = 4


def eventi_notifiche(valore):
    """The chosen events: empty means the default, none (or nessuno) means no event."""
    v = (valore or "").strip().lower()
    if not v:
        return set(EVENTI_NOTIFICHE[:EVENTI_PREDEFINITI])
    if v in ("none", "nessuno"):
        return set()
    return {x.strip() for x in v.split(",") if x.strip() in EVENTI_NOTIFICHE}


def etichetta(nome, lingua="en"):
    for c in CAMPI:
        if c[0] == nome:
            return (c[5] if lingua == "en" else c[4])[0]
    return nome


def etichetta_piena(nome, lingua="en"):
    """The label with its group, e.g. "Home Assistant: URL", for messages about a field."""
    for c in CAMPI:
        if c[0] == nome:
            return "%s: %s" % (GRUPPI[c[1]][1 if lingua == "en" else 0], etichetta(nome, lingua))
    return nome


def m(lingua, it, en):
    return en if lingua == "en" else it


BASE = {}        # value from the environment (.env) of every overridden setting, before the override
OVERRIDE = {}    # settings saved from the admin page


def leggi():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        # a hand-edited file must never crash the service: unknown names and NUL characters are skipped
        return {k: str(v) for k, v in d.items() if k in NOMI and "\x00" not in str(v)} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def carica():
    """Apply the saved settings to os.environ (called once, at import)."""
    OVERRIDE.clear(); BASE.clear()
    for k, v in leggi().items():
        BASE[k] = os.environ.get(k)
        OVERRIDE[k] = v
        os.environ[k] = v


def errore_valore(nome, valore, lingua="en"):
    """Why a value is not acceptable, or None. Used at startup (in English) and by the admin page."""
    valore = (valore or "").strip()
    if not valore:
        return None
    nome_campo = "%s (%s)" % (etichetta(nome, lingua), nome)
    if nome in LIMITI:
        minimo, massimo, intero = LIMITI[nome]
        try:
            n = float(valore)
        except ValueError:
            return m(lingua, "%s deve essere un numero.", "%s must be a number.") % nome_campo
        if not math.isfinite(n) or not minimo <= n <= massimo or (intero and not re.fullmatch(r"[+-]?\d+", valore)):
            if intero:
                return m(lingua, "%s deve essere un numero intero tra %g e %g.", "%s must be a whole number between %g and %g.") \
                    % (nome_campo, minimo, massimo)
            return m(lingua, "%s deve essere un numero tra %g e %g.", "%s must be a number between %g and %g.") % (nome_campo, minimo, massimo)
    if nome in URL:
        p = urlsplit(valore)
        if p.scheme not in ("http", "https") or not p.hostname:
            return m(lingua, "%s deve essere un indirizzo http:// o https://.", "%s must be an http:// or https:// address.") % nome_campo
    if nome == "NOTIFY_EVENTI" and valore.lower() not in ("none", "nessuno"):
        sbagliati = [x.strip() for x in valore.split(",") if x.strip() and x.strip().lower() not in EVENTI_NOTIFICHE]
        if sbagliati:
            return m(lingua, "%s: eventi sconosciuti (%s). Ammessi: %s.", "%s: unknown events (%s). Allowed: %s.") \
                % (nome_campo, ", ".join(sbagliati), ", ".join(EVENTI_NOTIFICHE))
    if nome == "NOTIFY_HA" and not re.fullmatch(r"\s*(?:notify\.)?[a-z0-9_]+\s*(?:,\s*(?:notify\.)?[a-z0-9_]+\s*)*,?\s*", valore):
        return m(lingua, "%s: nomi di servizi notify separati da virgole, es. mobile_app_telefono.",
                 "%s: names of notify services, comma separated, e.g. mobile_app_phone.") % nome_campo
    return None


def controlla(env):
    for nome in list(LIMITI) + list(URL) + ["NOTIFY_EVENTI", "NOTIFY_HA"]:
        e = errore_valore(nome, env.get(nome))
        if e:
            return e
    return None


def mascherato(url):
    """An URL without its credentials (user:password@ and the query string), for display."""
    p = urlsplit(url or "")
    if not p.username and not p.password and not p.query:
        return None
    host = p.hostname or ""
    if p.port:
        host += ":%d" % p.port
    return "%s://%s%s%s" % (p.scheme, "•••@" if p.username or p.password else "", host, p.path) + ("?•••" if p.query else "")


def _scrivi_privato(percorso, dati):
    fd = os.open(percorso, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as h:
        h.write(dati)


def segreto(nuovo=False):
    """Random key that signs the admin session cookie, kept in DATA_DIR (a new one per process without it).
    nuovo=True replaces it: every session, everywhere, is logged out."""
    f = os.path.join(DATA_DIR, "admin-secret")
    if not nuovo:
        try:
            with open(f, "rb") as h:
                k = h.read()
            if len(k) >= 32:
                return k
        except OSError:
            pass
    k = os.urandom(32)
    if scrivibile():
        try:
            _scrivi_privato(f, k)
        except OSError:
            pass
    return k


# ---- admin password changed from the page (scrypt hash in DATA_DIR); without it, ADMIN_PASSWORD from .env is used
FILE_PASSWORD = os.path.join(DATA_DIR, "admin-password")


def password_salvata():
    try:
        with open(FILE_PASSWORD, encoding="ascii") as f:
            v = f.read().strip()
        return v if v.startswith("scrypt$") else None
    except (OSError, ValueError):
        return None


def _scrypt(pw, sale, n=2 ** 14, r=8, p=1):
    import hashlib
    return hashlib.scrypt(pw.encode("utf-8", "replace"), salt=sale, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)


def salva_password(pw):
    sale = os.urandom(16)
    _scrivi_privato(FILE_PASSWORD, ("scrypt$16384$8$1$%s$%s" % (sale.hex(), _scrypt(pw, sale).hex())).encode("ascii"))


def verifica_password_salvata(pw, registrata):
    import hmac
    try:
        _, n, r, p, sale, hashato = registrata.split("$")
        return hmac.compare_digest(_scrypt(pw, bytes.fromhex(sale), int(n), int(r), int(p)).hex(), hashato)
    except (ValueError, TypeError):
        return False


def cancella_password():
    try:
        os.unlink(FILE_PASSWORD)
    except FileNotFoundError:
        pass


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
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(nuovi, f, indent=2, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def valori(lingua="it"):
    """Current settings for the page; secrets are never sent, only whether they are set."""
    out = []
    for nome, gruppo, tipo, opzioni, testi_it, testi_en in CAMPI:
        v = os.environ.get(nome, "")
        vecchio = nome == "LLM_API" and nome not in os.environ and bool(os.environ.get("LLM_FORMAT"))
        if vecchio:
            v = os.environ["LLM_FORMAT"]              # the old name of the same setting, still accepted
        nascosto = mascherato(v) if nome in URL else None
        nome_campo, aiuto = testi_en if lingua == "en" else testi_it
        out.append({"nome": nome, "gruppo": gruppo, "nome_gruppo": GRUPPI[gruppo][1 if lingua == "en" else 0],
                    "etichetta": nome_campo, "tipo": tipo, "opzioni": opzioni, "aiuto": aiuto,
                    "predefinito": PREDEFINITI.get(nome, ""), "mascherato": nascosto,
                    "predefinito_testo": PREDEFINITI_TESTO.get(nome, ("", ""))[1 if lingua == "en" else 0],
                    "valore": None if nome in SEGRETI or nascosto else v, "impostato": bool(v),
                    "base": BASE.get(nome) is not None if nome in OVERRIDE else nome in os.environ,   # has a .env value
                    "origine": "pagina" if nome in OVERRIDE else ("env" if nome in os.environ or vecchio else "default")})
    return out


carica()
_errore = controlla(os.environ)
if _errore:
    raise SystemExit(_errore)
