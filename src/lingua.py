"""Language of the assistant: Italian (it) or English (en), set with LANGUAGE.

Every text the user hears, every instruction to the model and every tool description lives here. The Alexa skill must
use the interaction model of the same language (skill/interaction-model.it-IT.json or .en-US.json)."""
import os
import re

LINGUE = ("it", "en")
LINGUA = (os.environ.get("LANGUAGE") or "it").strip().lower()[:2]
if LINGUA not in LINGUE:
    raise SystemExit("LANGUAGE must be 'it' (Italian) or 'en' (English), not %r" % os.environ.get("LANGUAGE"))

TESTI = {
    # ---- spoken by Alexa
    "benvenuto": ("Dimmi pure.", "Go ahead."),
    "cosa_vuoi": ("Cosa vuoi sapere?", "What would you like to know?"),
    "cosa_fare": ("Cosa vuoi fare?", "What would you like to do?"),
    "altro": ("Altro?", "Anything else?"),
    "ciao": ("Ciao!", "Bye!"),
    "aiuto": ("Fammi una domanda, per esempio: come si cucina il risotto. Se ci metto un po', dimmi allora per sentire "
              "la risposta. Per uscire di' basta.",
              "Ask me anything, for example: how do I make a risotto. If I take a while, say so to hear the answer. "
              "To finish, say stop."),
    "non_capito": ("Non ho capito. ", "Sorry, I didn't get that. "),
    "ripeti": ("Non ho capito, puoi ripetere?", "Sorry, could you say that again?"),
    "ripeti_breve": ("Puoi ripetere?", "Could you say that again?"),
    "va_bene": ("Va bene. Altro?", "Okay. Anything else?"),
    "fallita": ("Non sono riuscito a rispondere. Riprova a farmi la domanda.", "I couldn't answer that. Please ask me again."),
    "penso": ("Ci sto pensando. Dimmi allora tra qualche secondo.", "Let me think. Say so in a few seconds."),
    "penso_ancora": ("Ci sto ancora pensando. Dimmi allora tra qualche secondo.", "Still thinking. Say so in a few seconds."),
    "vuoi_risposta": ("Vuoi la risposta? Dimmi allora.", "Want the answer? Just say so."),
    "nessuna_attesa": ("Non ho risposte in sospeso. Cosa vuoi sapere?", "I have no answers waiting. What would you like to know?"),
    "risposta_prima": ("Ho la risposta alla domanda di prima. ", "I have the answer to your earlier question. "),
    "penso_prima": ("Sto ancora pensando alla domanda di prima. Dimmi allora tra poco, oppure fammi un'altra domanda.",
                    "I'm still thinking about your earlier question. Say so in a moment, or ask me something else."),
    "fatto": ("Fatto.", "Done."),
    "si": ("si'", "yes"),
    "no": ("no", "no"),
    # ---- instructions to the model
    "system": ("Sei un assistente vocale in italiano. Rispondi in modo naturale e breve, al massimo 2-3 frasi, senza elenchi, "
               "senza markdown, senza emoji: la risposta viene letta ad alta voce.",
               "You are a voice assistant speaking English. Answer naturally and briefly, at most 2-3 sentences, with no "
               "lists, no markdown and no emoji: the answer is read aloud."),
    "turno": ("[Sei l'assistente vocale di casa su Alexa, non un assistente di programmazione: non parlare di codice o di file. "
              "Rispondi in italiano parlato, in modo naturale, al massimo 3-4 frasi, senza elenchi, senza markdown e senza emoji: "
              "la risposta viene letta ad alta voce. Rispondi direttamente, senza premesse. La frase arriva dal riconoscimento "
              "vocale e spesso manca la parola iniziale (perché, come, cosa, quanto, quando, dove, chi): trattala sempre come "
              "una domanda o una richiesta, mai come un'affermazione da confermare.]",
              "[You are the home voice assistant on Alexa, not a coding assistant: do not talk about code or files. "
              "Answer in natural spoken English, at most 3-4 sentences, with no lists, no markdown and no emoji: the answer is "
              "read aloud. Answer directly, without preambles. The sentence comes from speech recognition and often lacks its "
              "first word (why, how, what, how much, when, where, who): always treat it as a question or a request, never as "
              "a statement to confirm.]"),
    "oggi": ("[Oggi e' %s; ", "[Today is %s; "),
    "casa_a": ("casa e' a %s. ", "home is in %s. "),
    "usa_web": ("Se serve un'informazione aggiornata (meteo, notizie, risultati, orari, prezzi, eventi) cercala sul web; "
                "non dire che stai cercando e non leggere indirizzi web.",
                "If you need up-to-date information (weather, news, scores, opening hours, prices, events) search the web; "
                "do not say that you are searching and never read web addresses."),
    "usa_casa": (" Puoi leggere e comandare la casa con gli strumenti riepilogo_casa, cerca_in_casa ed esegui_azione: "
                 "per comandare trova prima l'entity_id con cerca_in_casa; dopo un'azione di' in poche parole cosa hai fatto; "
                 "porta, portone e antifurto non si possono comandare da qui.",
                 " You can read and control the home with the tools riepilogo_casa, cerca_in_casa and esegui_azione: "
                 "to control something, first find its entity_id with cerca_in_casa; after an action say briefly what you "
                 "did; doors, gates and the alarm cannot be controlled from here."),
    "azioni": ("azioni eseguite", "actions done"),
    "prova_modello": ("Rispondi solo con: tutto funziona.", "Reply only with: everything works."),
    "prova_web": ("che tempo fa oggi a %s? cercalo sul web", "what's the weather today in %s? search the web"),
    "citta_prova": ("Roma", "London"),
    # ---- tools
    "web_desc": ("Cerca informazioni aggiornate sul web: meteo, notizie, risultati sportivi, orari, prezzi, eventi, "
                 "qualsiasi fatto che puo' essere cambiato di recente. Restituisce titolo ed estratto dei primi risultati.",
                 "Search the web for up-to-date information: weather, news, sports results, opening hours, prices, events, "
                 "any fact that may have changed recently. Returns the title and an excerpt of the top results."),
    "web_query": ("cosa cercare, con luogo e data quando servono (es. 'meteo Roma domani')",
                  "what to search for, with place and date when they matter (e.g. 'weather London tomorrow')"),
    "web_vuota": ("Specifica cosa cercare.", "Say what to search for."),
    "web_niente": ("Nessun risultato.", "No results."),
    "web_errore": ("Ricerca web non disponibile in questo momento (%s).", "Web search is not available right now (%s)."),
    "web_diretta": ("Risposta diretta: ", "Direct answer: "),
    "riepilogo_desc": ("Stato generale della casa: chi e' a casa, luci accese, tapparelle, temperature, clima, consumo, porta, "
                       "rifiuti, pioggia. Usalo per domande generiche sulla casa.",
                       "General state of the home: who is home, lights on, shutters, temperatures, climate, power, door, "
                       "rubbish collection, rain. Use it for general questions about the home."),
    "cerca_desc": ("Cerca dispositivi e sensori di casa per nome o stanza (es. 'luci salone', 'tapparella camera', "
                   "'temperatura bagno', 'lavatrice'). Restituisce entity_id, nome e stato. Usalo prima di comandare per "
                   "trovare l'entity_id giusto.",
                   "Find devices and sensors of the home by name or room (e.g. 'living room lights', 'bedroom shutter', "
                   "'bathroom temperature', 'washing machine'). Returns entity_id, name and state. Use it before controlling "
                   "something, to find the right entity_id."),
    "esegui_desc": ("Comanda dispositivi di casa. Domini e servizi permessi: light(turn_on,turn_off,toggle; dati: brightness_pct), "
                    "cover(open_cover,close_cover,stop_cover,set_cover_position; dati: position 0=chiusa 100=aperta), "
                    "climate(turn_on,turn_off,set_temperature,set_hvac_mode; dati: temperature, hvac_mode), "
                    "switch(turn_on,turn_off,toggle), fan, humidifier(set_humidity), scene(turn_on). Serrature, portone e "
                    "antifurto NON sono comandabili. Per azioni su piu' stanze serve confermato=true dopo il si' dell'utente.",
                    "Control devices of the home. Allowed domains and services: light(turn_on,turn_off,toggle; data: "
                    "brightness_pct), cover(open_cover,close_cover,stop_cover,set_cover_position; data: position 0=closed "
                    "100=open), climate(turn_on,turn_off,set_temperature,set_hvac_mode; data: temperature, hvac_mode), "
                    "switch(turn_on,turn_off,toggle), fan, humidifier(set_humidity), scene(turn_on). Locks, doors and the "
                    "alarm can NOT be controlled. Actions on several rooms need confermato=true after the user's yes."),
    "entita_desc": ("entity_id esatti", "exact entity_ids"),
    "persone": ("Persone", "People"),
    "a_casa": ("a casa", "home"),
    "fuori": ("fuori", "away"),
    "luci_accese": ("Luci accese", "Lights on"),
    "nessuna": ("nessuna", "none"),
    "tapparelle": ("Tapparelle (100=aperta)", "Shutters (100=open)"),
    "temperature": ("Temperature", "Temperatures"),
    "clima": ("Clima", "Climate"),
    "clima_riga": ("%s %s (stanza %s°, impostata %s°)", "%s %s (room %s°, set to %s°)"),
    "nessuna_entita": ("Nessuna entita' trovata per '%s'.", "No entity found for '%s'."),
    "non_comandabile": ("[NON COMANDABILE] ", "[CANNOT BE CONTROLLED] "),
    "non_permessa": ("Azione non permessa: %s.%s. Permesse: %s", "Action not allowed: %s.%s. Allowed: %s"),
    "niente_all": ("Indica le entita' una per una (niente 'all').", "List the entities one by one (no 'all')."),
    "altro_dominio": ("L'entita' %s non e' del dominio %s.", "The entity %s is not in the %s domain."),
    "non_esiste": ("L'entita' %s non esiste: usa cerca_in_casa.", "The entity %s does not exist: use cerca_in_casa."),
    "vietata": ("Per sicurezza non posso comandare %s (%s): serrature, portone, antifurto e servizi tecnici sono esclusi.",
                "For safety I cannot control %s (%s): locks, doors, the alarm and technical services are excluded."),
    "serve_conferma": ("SERVE CONFERMA: l'azione riguarda piu' stanze (%s). Chiedi all'utente una conferma breve e non eseguire: "
                       "solo quando l'utente avra' risposto si', richiama esegui_azione con confermato=true.",
                       "CONFIRMATION NEEDED: the action involves several rooms (%s). Ask the user for a short confirmation and do "
                       "not run it: only after the user has said yes, call esegui_azione again with confermato=true."),
    "fatto_su": ("Fatto: %s.%s su %s.", "Done: %s.%s on %s."),
    "strumento_ignoto": ("Strumento sconosciuto.", "Unknown tool."),
    "errore_ha": ("Errore nel contattare Home Assistant: %s", "Could not reach Home Assistant: %s"),
}

GIORNI = {"it": ["lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato", "domenica"],
          "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
MESI = {"it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
               "novembre", "dicembre"],
        "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]}

# both languages are always accepted: harmless, and it keeps working while a skill is being switched over
PAROLE_ATTESA = {"allora", "e allora", "allora che mi dici", "hai finito", "sei pronto", "quindi", "pronto", "fatto", "vai",
                 "ci sei", "eccomi", "si", "sì", "la risposta", "dimmi la risposta", "dammi la risposta",
                 "so", "well", "so what", "and so", "are you done", "are you ready", "is it ready", "ready", "done", "go on",
                 "i'm here", "yes", "the answer", "give me the answer", "tell me the answer", "what's the answer"}
SI = re.compile(r"^\s*(s[iì]'?|certo|confermo|conferma|ok|okay|va bene|procedi|vai|fallo|esatto|d'accordo|perfetto|"
                r"yes|yeah|yep|sure|of course|confirm|go ahead|do it|correct|alright|all right)\b", re.I)
NOTA_AZIONI = re.compile(r"\[(?:azioni eseguite|actions done):[^\]]*\]")


def t(chiave, lingua=None):
    it, en = TESTI[chiave]
    return en if (lingua or LINGUA) == "en" else it


def data(n, lingua=None):
    lingua = lingua or LINGUA
    if lingua == "en":
        return "%s %d %s %d, %02d:%02d" % (GIORNI["en"][n.weekday()], n.day, MESI["en"][n.month - 1], n.year, n.hour, n.minute)
    return "%s %d %s %d, ore %02d:%02d" % (GIORNI["it"][n.weekday()], n.day, MESI["it"][n.month - 1], n.year, n.hour, n.minute)
