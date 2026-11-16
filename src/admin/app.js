"use strict";
// Admin page of Alexa AI Bridge, in Italian or English. No framework, no external resources.
// Server data is only ever placed in the page with textContent (never innerHTML).

const $ = (sel) => document.querySelector(sel);

// ---------- texts
const TESTI = {
  it: {
    "login.sub": "Pannello di gestione", "login.password": "Password", "login.entra": "Entra",
    "tab.panoramica": "Panoramica", "tab.conversazioni": "Conversazioni", "tab.chat": "Chat di prova", "tab.casa": "Casa",
    "tab.impostazioni": "Configurazione", "tab.sistema": "Sistema", "tab.registro": "Registro", "esci": "Esci",
    "btn.prova": "Prova", "btn.in_corso": "In corso…", "btn.aggiorna": "Aggiorna", "btn.svuota": "Svuota", "btn.annulla": "Annulla",
    "btn.salva": "Salva e riavvia", "btn.verifica": "Verifica…", "btn.riavvio": "Riavvio…",
    "pan.dallavvio": "Nello storico", "pan.prove": "Prove",
    "pan.prove_desc": "Ogni prova usa la configurazione attuale, come farebbe una domanda ad Alexa.",
    "prova.modello": "Modello", "prova.modello_desc": "Una domanda breve al modello.",
    "prova.web": "Ricerca web", "prova.web_desc": "Il meteo di oggi nella tua città.",
    "prova.casa": "Home Assistant", "prova.casa_desc": "Il riepilogo della casa, in sola lettura.",
    "card.servizio": "Servizio", "card.modello": "Modello", "card.web": "Ricerca web", "card.casa": "Home Assistant",
    "card.attivo_da": "Attivo da %s", "card.sospese": "%s risposte in sospeso", "card.avvisi": "%s avvisi nel registro",
    "card.nessun_avviso": "Nessun avviso", "card.compatibile": "OpenAI-compatibile",
    "web.native": "Nativa del modello", "web.spenta": "Spenta", "web.rifiutata": "Rifiutata dal modello", "web.ok": "Disponibile",
    "web.niente": "Le domande sull'attualità non avranno dati freschi",
    "casa.collegato": "Collegato", "casa.no_strumenti": "Strumenti non accettati dal modello", "casa.non_configurato": "Non configurato",
    "casa.imposta": "Imposta URL e token nella Configurazione",
    "adatt.titolo": "Adattamenti automatici: ", "adatt.strumenti": "il modello non accetta strumenti: niente comandi alla casa né ricerca web lato servizio",
    "adatt.web": "la ricerca web nativa è stata rifiutata dall'endpoint", "adatt.max": "l'endpoint usa max_completion_tokens",
    "adatt.thinking": "l'endpoint non accetta il parametro thinking",
    "stat.domande": "domande", "stat.storico_spento": "domande (storico spento)", "stat.medio": "tempo medio",
    "stat.lente": "oltre %s s (\"ci sto pensando\")", "stat.errori": "errori", "stat.azioni": "azioni sulla casa",
    "durata.giorni": "giorni",
    "conv.cerca": "Cerca nelle domande e nelle risposte", "conv.tutte": "Tutte",
    "conv.nota": "Salvate nel volume dati del servizio, restano dopo riavvii e aggiornamenti. Gli utenti sono anonimizzati.",
    "conv.nessuna": "Ancora nessuna domanda. Prova a parlare con Alexa o usa la chat di prova.",
    "conv.nessuna_filtro": "Nessuna conversazione corrisponde al filtro.", "conv.allora": "consegnata con \"allora?\"",
    "conv.errore": "Errore: ", "conv.svuota_conferma": "Svuotare lo storico delle conversazioni?",
    "chat.simula": "Simula le azioni sulla casa", "chat.nuova": "Nuova conversazione", "chat.invia": "Invia",
    "chat.placeholder": "Fai una domanda…",
    "chat.vuoto": "Scrivi come parleresti ad Alexa, per esempio \"che tempo fa domani\" o \"accendi la luce del salone\".",
    "chat.nuova_fatta": "Nuova conversazione. Il modello non ricorda più le domande precedenti.",
    "chat.fallita": "Alexa direbbe: \"Non sono riuscito a rispondere.\" (%s)", "chat.lenta": "su Alexa: \"Ci sto pensando\", poi \"allora?\"",
    "casa.intro": "Le entità di Home Assistant che l'assistente vede, con le regole che le proteggono. Puoi vietarne altre o chiedere sempre un sì a voce prima di comandarle.",
    "casa.cerca": "Cerca per nome o entity_id", "casa.vista_tutte": "Tutte", "casa.vista_comandabili": "Comandabili",
    "casa.vista_bloccate": "Mai comandabili", "casa.vista_conferma": "Chiedono conferma",
    "casa.blocco.dominio": "Mai comandabile (tipo di entità)", "casa.blocco.regole": "Bloccata dalle regole di sicurezza incluse",
    "casa.blocco.regex": "Bloccata dalla tua regola HA_VIETATO", "casa.blocco.pagina": "Vietata da te",
    "casa.comandabile": "Comandabile", "casa.vieta": "Vieta", "casa.conferma": "Chiedi sempre un sì",
    "casa.scena": "Una scena esegue tutto ciò che contiene: tienici fuori serrature e allarmi.",
    "casa.non_configurata": "Home Assistant non è configurato: imposta URL e token nella Configurazione.",
    "casa.nessuna": "Nessuna entità corrisponde.", "casa.errore": "Home Assistant non risponde: %s",
    "casa.nota_conferma": "Le azioni su più di %s entità chiedono comunque conferma.",
    "modifiche.una": "1 modifica non salvata", "modifiche.tante": "%s modifiche non salvate",
    "imp.sola_lettura": "Sola lettura. ", "imp.sola_lettura_desc": "Per salvare dalla pagina serve una cartella dati scrivibile (%s): con il compose incluso è già montata; altrimenti vedi docs/admin.md.",
    "imp.salvata": "salvata qui", "imp.env": "da .env", "imp.predefinita": "predefinita", "imp.torna_env": "Torna al valore del .env", "imp.torna_predefinito": "Torna al predefinito",
    "imp.valore_env": "valore del .env",
    "imp.cancella": "Cancella", "imp.cancellata": "verrà cancellata al salvataggio", "imp.segreta": "•••••••• impostata: scrivi per cambiarla",
    "imp.non_impostata": "non impostata", "imp.credenziali": "  (contiene credenziali: scrivi per cambiarlo)",
    "imp.predefinito": "predefinito: %s", "imp.automatico": "(automatico)", "imp.non_impostato": "(non impostato)",
    "imp.istruzioni_incluse": "vuoto: le istruzioni incluse",
    "imp.applicata": "Configurazione applicata.", "imp.salvate_riavvia": "Salvate. Riavvia il servizio per applicarle.",
    "sis.alexa": "Alexa", "sis.skill_id": "Skill ID", "sis.endpoint": "Endpoint da inserire nella console Alexa",
    "sis.endpoint_mancante": "Imposta PUBLIC_HOST nel .env per vederlo qui.", "sis.lingua": "Lingua dell'assistente",
    "sis.modello_desc": "Incollalo nel JSON Editor della console Alexa, nella lingua corrispondente. Con la lingua automatica la stessa skill può avere entrambi: italiano in Italian (IT), inglese in English (US).",
    "sis.scarica": "Scarica %s", "sis.copia": "Copia", "sis.copiato": "Copiato.",
    "sis.servizio": "Servizio", "sis.versione": "Versione", "sis.attivo_da": "Attivo da", "sis.aggiornamenti": "Controlla aggiornamenti",
    "sis.aggiornato": "Hai l'ultima versione (%s).", "sis.nuova": "È disponibile la versione %s.", "sis.vedi": "Vedi la release",
    "sis.sviluppo": "Versione di sviluppo: l'ultima release è %s.",
    "sis.riavvia": "Riavvia il servizio", "sis.riavvia_conferma": "Riavviare il servizio? Le risposte in sospeso andranno perse.",
    "sis.riavviato": "Servizio riavviato.", "sis.non_riavviabile": "Riavvio automatico non disponibile: riavvia il container.",
    "sis.scarta": "Scarta le risposte in sospeso", "sis.scartate": "Scartate.",
    "sis.sicurezza": "Accesso", "sis.password": "Cambia la password del pannello", "sis.attuale": "Password attuale",
    "sis.nuova_pw": "Nuova password (almeno 12 caratteri)", "sis.ripeti_pw": "Ripeti la nuova password", "sis.cambia": "Cambia password",
    "sis.pw_diverse": "Le due password non coincidono.", "sis.pw_cambiata": "Password cambiata: le altre sessioni sono state chiuse.",
    "sis.pw_da_pagina": "La password è stata cambiata da questa pagina e vale al posto di ADMIN_PASSWORD.",
    "sis.pw_da_env": "Vale la password ADMIN_PASSWORD del .env.", "sis.pw_ripristina": "Torna alla password del .env",
    "sis.pw_ripristinata": "Ora vale di nuovo la password del .env.",
    "sis.pw_serve_attuale": "Scrivi la password attuale nel primo campo, poi riprova.",
    "sis.esci_ovunque": "Esci da tutti i dispositivi", "sis.esci_conferma": "Chiudere tutte le sessioni, compresa questa?",
    "sis.backup": "Backup delle impostazioni", "sis.backup_desc": "Esporta tutte le impostazioni senza chiavi, token e indirizzi con credenziali; importandole vengono controllate come un salvataggio normale.",
    "sis.esporta": "Esporta", "sis.importa": "Importa", "sis.importa_conferma": "Importare %s impostazioni e riavviare?",
    "sis.importa_errore": "Il file non è un backup valido.", "sis.importate": "Impostazioni importate.",
    "sis.importa_saltati": "Da reimpostare in Configurazione insieme alla loro chiave: %s.",
    "sis.importa_solo_url": "Nel backup ci sono solo indirizzi senza chiave (%s): impostali in Configurazione insieme alla chiave.",
    "sis.rete": "Rete e pubblicazione", "sis.rete_desc": "Queste si cambiano nel .env sul server, poi docker compose up -d: decidono dove il servizio è raggiungibile.",
    "sis.pubblico_on": "Il pannello può essere raggiunto attraverso il reverse proxy.", "sis.pubblico_off": "Il pannello non è pubblicato attraverso il reverse proxy.",
    "sis.non_impostato": "non impostato",
    "reg.tutti": "Tutti i livelli", "reg.avvisi": "Solo avvisi ed errori", "reg.auto": "Aggiornamento automatico", "reg.vuoto": "Nessuna riga.",
    "err.sessione": "Sessione scaduta",
    "sub.panoramica": "Lo stato del servizio e una prova rapida di ogni sua parte.",
    "sub.conversazioni": "Le ultime domande ad Alexa, alla chat di prova e ai test, con le azioni eseguite sulla casa.",
    "sub.chat": "Parla con l'assistente per iscritto: stesso modello, stessi strumenti e stesse regole dell'Echo.",
    "sub.casa": "Le entità di Home Assistant che l'assistente può vedere e le regole che le proteggono. Puoi vietarne altre o chiedere sempre un sì a voce.",
    "sub.impostazioni": "Ogni impostazione con la sua spiegazione. Al salvataggio i valori vengono controllati e il servizio si riavvia da solo.",
    "sub.sistema": "Quello che serve alla console Alexa, la versione, l'accesso al pannello e il backup.",
    "sub.registro": "Le ultime righe scritte dal servizio.",
    "conv.e2e": "Test e2e",
    "imp.predefinita_valore": "valore predefinito: %s", "imp.vale": "valore predefinito: %s", "imp.vuota": "vuota",
    "imp.altro_modello": "Altro… (scrivilo a mano)", "imp.modelli_n": "Elenco dal fornitore: %s modelli.",
    "imp.modelli_errore": "Elenco dei modelli non disponibile (%s): scrivi il nome a mano.",
    "imp.non_impostata_c": "non impostata",
    "opt.LANGUAGE.auto": "Automatica: la lingua in cui parla l'Echo", "opt.LANGUAGE.it": "Italiano", "opt.LANGUAGE.en": "Inglese",
    "opt.LLM_API.": "Automatico (dall'URL)", "opt.LLM_API.anthropic": "Anthropic (Claude)", "opt.LLM_API.openai": "Compatibile OpenAI",
    "opt.WEB_SEARCH.auto": "Automatica", "opt.WEB_SEARCH.native": "Nativa di Claude", "opt.WEB_SEARCH.searxng": "SearXNG",
    "opt.WEB_SEARCH.brave": "Brave Search", "opt.WEB_SEARCH.tavily": "Tavily", "opt.WEB_SEARCH.off": "Spenta",
    "opt.HA_TOOLS.1": "Attivi", "opt.HA_TOOLS.0": "Spenti", "opt.NOTIFY_ATTIVE.1": "Attive", "opt.NOTIFY_ATTIVE.0": "Sospese",
    "sis.lingua_auto": "Automatica: italiano o inglese, come parla l'Echo",
    "tab.automazioni": "Automazioni",
    "sub.automazioni": "Le automazioni di Home Assistant create a voce: chiedi ad Alexa \"ogni sera al tramonto accendi la luce del salone\", lei te le rilegge e le crea solo dopo il tuo sì.",
    "auto.cerca": "Cerca per nome o descrizione",
    "auto.titolo_on": "Automazioni a voce attive", "auto.titolo_off": "Automazioni a voce spente",
    "auto.desc_on": "L'assistente può creare automazioni (a un orario, all'alba o al tramonto, quando cambia uno stato o un sensore supera una soglia) e attivarle, disattivarle o eliminarle. Le azioni seguono le regole della scheda Casa; creare ed eliminare chiedono sempre un sì a voce; vede e cambia solo quelle create da lui.",
    "auto.desc_off": "Accendile per chiedere ad Alexa di creare automazioni di Home Assistant. Serve il token di un utente amministratore (Configurazione → Token per le automazioni): Home Assistant fa scrivere automazioni solo agli amministratori.",
    "auto.attiva": "Attiva", "auto.disattiva": "Disattiva",
    "auto.senza_strumenti": "Gli strumenti casa sono spenti (Configurazione → Strumenti casa): finché restano spenti l'assistente non vede né crea automazioni.",
    "auto.no_permessi": "Il token usato non è di un amministratore: Home Assistant rifiuterà di creare ed eliminare automazioni. Imposta Token per le automazioni nella Configurazione.",
    "auto.permessi_ok": "Il token può creare ed eliminare automazioni.",
    "auto.limite": "Al massimo %s automazioni create a voce (%s ora).",
    "auto.nessuna": "Ancora nessuna automazione creata a voce. Prova: \"Alexa, apri cervellone\", poi \"ogni giorno alle sette accendi la luce della cucina\".",
    "auto.nessuna_filtro": "Nessuna automazione corrisponde.",
    "auto.non_configurata": "Home Assistant non è configurato: imposta URL e token nella Configurazione.",
    "auto.errore": "Home Assistant non risponde: %s",
    "auto.accesa": "Attiva", "auto.spenta": "Disattivata", "auto.sparita": "Non più in Home Assistant",
    "auto.ultima": "ultima esecuzione %s", "auto.mai": "mai eseguita", "auto.creata": "creata %s",
    "auto.elimina": "Elimina", "auto.elimina_conferma": "Eliminare l'automazione \"%s\" da Home Assistant?", "auto.dimentica": "Togli dall'elenco",
    "auto.eliminata": "Automazione eliminata.", "auto.attivata": "Automazione attivata.", "auto.disattivata": "Automazione disattivata.",
    "opt.HA_AUTOMAZIONI.1": "Attive", "opt.HA_AUTOMAZIONI.0": "Spente",
    "tab.notifiche": "Notifiche",
    "sub.notifiche": "Un messaggio sul telefono quando succede qualcosa che vale la pena sapere: un'azione confermata a voce, un tentativo bloccato su porte o allarmi, un'automazione creata.",
    "not.generale": "Notifiche", "not.attive": "Invia notifiche", "not.max": "Al massimo all'ora",
    "not.max_desc": "Oltre questo numero le successive non partono; lo stesso messaggio non si ripete entro due minuti.",
    "not.eventi": "Quando avvisarti",
    "nev.confermate": "Azioni confermate a voce", "nevd.confermate": "Azioni su più stanze o su entità che chiedono sempre un sì, eseguite dopo il tuo sì.",
    "nev.bloccate": "Tentativi bloccati", "nevd.bloccate": "Il modello ha chiesto qualcosa di vietato: aprire una serratura o una porta, l'antifurto, un'entità che hai vietato.",
    "nev.automazioni": "Automazioni", "nevd.automazioni": "Create, attivate, disattivate o eliminate, a voce o da questa pagina.",
    "nev.azioni": "Ogni azione sulla casa", "nevd.azioni": "Ogni comando inviato a Home Assistant, anche accendere una luce: possono essere tante.",
    "nev.errori": "Errori", "nevd.errori": "Alexa non è riuscita a rispondere (modello irraggiungibile, chiave sbagliata…).",
    "nev.pannello": "Pannello di gestione", "nevd.pannello": "Accessi, troppe password sbagliate, password cambiata, impostazioni salvate.",
    "not.canali": "Canali", "not.canali_desc": "Ogni canale configurato riceve tutte le notifiche. Token e indirizzi si impostano nella Configurazione, gruppo Notifiche.",
    "can.ha": "App Home Assistant", "can.telegram": "Telegram", "can.ntfy": "ntfy", "can.gotify": "Gotify", "can.webhook": "Webhook",
    "not.configurato": "Configurato", "not.non_configurato": "Non configurato", "not.configura": "Configura",
    "not.servizi": "Servizi notify di Home Assistant: scegli dove mandarle (l'app sul telefono si chiama mobile_app_…).",
    "not.servizi_nessuno": "Home Assistant non ha servizi notify: installa l'app Home Assistant sul telefono e accedi.",
    "not.servizi_errore": "Elenco dei servizi non disponibile (%s).", "not.ha_non_configurato": "Serve Home Assistant (URL e token) nella Configurazione.",
    "not.prova": "Invia una notifica di prova", "not.prova_nessuno": "Configura prima almeno un canale.",
    "not.ultime": "Ultime notifiche", "not.ultime_vuoto": "Ancora nessuna notifica da quando il servizio è partito.",
    "nev.prova": "Prova",
    "nev.modelli": "Modelli che non rispondono", "nevd.modelli": "Un modello non è raggiungibile, è scollegato o ha finito il credito e risponde il successivo; quando torna disponibile.",
    "nev.memoria": "Cose imparate", "nevd.memoria": "L'assistente ha salvato in memoria qualcosa di nuovo su chi abita in casa.",
    "tab.modelli": "Modelli",
    "sub.modelli": "Il modello principale e quelli di riserva, provati in ordine: se uno non risponde, è scollegato o ha finito i token, risponde il successivo.",
    "mod.ordine": "In ordine di prova", "mod.ordine_desc": "Un modello che non risponde viene messo in pausa e si passa al successivo; finita la pausa si riprova il principale. Dopo un'azione sulla casa non si cambia mai modello a metà (potrebbe ripeterla).",
    "mod.principale": "Principale", "mod.riserva": "Riserva · %s", "mod.saltato": "Non usato", "mod.giu": "Non disponibile: %s",
    "mod.fino": "in pausa fino alle %s", "mod.in_uso": "Sta rispondendo", "mod.disponibile": "Disponibile", "mod.non_provato": "Non ancora usato",
    "mod.senza_chiave": "senza chiave", "mod.usa": "Usa", "mod.prova": "Prova", "mod.modifica": "Modifica", "mod.ultimo_ok": "ultima risposta %s",
    "mod.ultimo_errore": "ultimo errore %s", "mod.aggiungi": "Aggiungi un modello di riserva",
    "mod.aggiungi_desc": "Per esempio un altro CLIProxyAPI con un altro account, o un fornitore diverso: si configura nella Configurazione, gruppo Modello %s (di riserva).",
    "mod.pieno": "Hai configurato tutti i %s modelli possibili.",
    "mod.comportamento": "Comportamento", "mod.pausa": "Pausa di un modello che non risponde (secondi)",
    "mod.pausa_desc": "Per questo tempo viene saltato; 0 lo riprova a ogni domanda.",
    "mod.controllo": "Controllo in background (minuti)",
    "mod.controllo_desc": "Ogni quanto verificare che ogni modello sia raggiungibile e la chiave valida: usa l'elenco dei modelli, non consuma token. 0 mai.",
    "mod.notifica": "Avvisami quando un modello non risponde o torna disponibile",
    "mod.notifica_desc": "Con i canali della scheda Notifiche.", "mod.nessun_canale": "Nessun canale di notifica configurato: impostalo nella scheda Notifiche.",
    "mod.notifiche_sospese": "Le notifiche sono sospese nella scheda Notifiche.",
    "mod.prova_desc": "Prova fa una domanda breve solo a quel modello (pochi token): mostra se è collegato e ha credito.",
    "card.riserve": "+%s di riserva", "card.riserva_in_uso": "Sta rispondendo il modello di riserva %s",
    "imp.gruppo_chiuso": "non configurato: apri per aggiungerlo",
    "opt.SI.1": "Sì", "opt.SI.0": "No", "opt.MEMORIA.1": "Attiva", "opt.MEMORIA.0": "Spenta",
    "tab.memoria": "Memoria",
    "sub.memoria": "Quello che l'assistente sa di te e di chi abita con te, imparato dalle conversazioni: lo usa per risponderti meglio. Puoi correggerlo, aggiungere o cancellare qualsiasi cosa.",
    "mem.generale": "Memoria", "mem.attiva": "Ricorda da una conversazione all'altra",
    "mem.auto": "Impara da solo dopo ogni risposta",
    "mem.auto_desc": "Una breve richiesta in background, dopo che Alexa ha già risposto, cerca fatti nuovi (qualche token in più per domanda). Spento: impara solo quando glielo chiedi (\"ricordati che…\") o quando lo decide il modello.",
    "mem.max": "Fatti ricordati al massimo", "mem.recenti": "Scambi delle conversazioni precedenti da rileggere",
    "mem.giorni": "Per quanti giorni", "mem.recenti_desc": "Così \"come ti dicevo ieri\" ha senso. 0: nessuno.",
    "mem.istruzioni": "Cosa ricordare", "mem.istruzioni_ph": "vuoto: fatti duraturi su chi abita in casa (nomi, parentele, gusti, abitudini, orari, compleanni, animali)",
    "mem.mai": "Password, codici e dati riservati non vengono mai salvati.",
    "mem.fatti": "Cosa sa (%s)", "mem.nuovo": "Un fatto da ricordare, es. Anna è vegetariana", "mem.persona": "Persona (facoltativo)",
    "mem.aggiungi": "Aggiungi", "mem.cerca": "Cerca nei ricordi", "mem.nessuno": "Ancora niente. Prova a dire ad Alexa: \"ricordati che il sabato andiamo in piscina\".",
    "mem.nessuno_filtro": "Nessun ricordo corrisponde.", "mem.modifica": "Modifica", "mem.elimina": "Dimentica", "mem.salva": "Salva", "mem.annulla": "Annulla",
    "mem.elimina_conferma": "Dimenticare \"%s\"?", "mem.svuota": "Dimentica tutto", "mem.svuota_conferma": "Dimenticare tutto quello che l'assistente sa?",
    "mem.fonte.voce": "a voce", "mem.fonte.auto": "imparato", "mem.fonte.pannello": "da qui",
    "mem.voci": "Voci riconosciute",
    "mem.voci_desc": "Se nell'app Alexa ognuno ha il suo profilo vocale e nella console Alexa la skill ha attiva Skill Personalization (Build → Permissions), l'assistente sa chi sta parlando: chi dice \"sono Anna\" viene ricordato.",
    "mem.voci_nessuna": "Nessuna voce riconosciuta finora.", "mem.voce_dimentica": "Dimentica",
    "mem.scambi": "Conversazioni recenti", "mem.scambi_desc": "Le ultime domande e risposte che l'assistente rilegge.",
    "mem.scambi_nessuno": "Nessuna conversazione salvata.", "mem.scambi_svuota": "Cancella",
    "mem.salvato": "Salvato.", "mem.dimenticato": "Dimenticato.",
  },
  en: {
    "login.sub": "Admin page", "login.password": "Password", "login.entra": "Log in",
    "tab.panoramica": "Overview", "tab.conversazioni": "Conversations", "tab.chat": "Test chat", "tab.casa": "Home",
    "tab.impostazioni": "Settings", "tab.sistema": "System", "tab.registro": "Log", "esci": "Log out",
    "btn.prova": "Run", "btn.in_corso": "Running…", "btn.aggiorna": "Refresh", "btn.svuota": "Clear", "btn.annulla": "Cancel",
    "btn.salva": "Save and restart", "btn.verifica": "Checking…", "btn.riavvio": "Restarting…",
    "pan.dallavvio": "In the history", "pan.prove": "Checks",
    "pan.prove_desc": "Every check uses the current settings, just like a question to Alexa.",
    "prova.modello": "Model", "prova.modello_desc": "A short question to the model.",
    "prova.web": "Web search", "prova.web_desc": "Today's weather in your city.",
    "prova.casa": "Home Assistant", "prova.casa_desc": "The home summary, read only.",
    "card.servizio": "Service", "card.modello": "Model", "card.web": "Web search", "card.casa": "Home Assistant",
    "card.attivo_da": "Up for %s", "card.sospese": "%s answers waiting", "card.avvisi": "%s warnings in the log",
    "card.nessun_avviso": "No warnings", "card.compatibile": "OpenAI-compatible",
    "web.native": "Model's native search", "web.spenta": "Off", "web.rifiutata": "Rejected by the model", "web.ok": "Available",
    "web.niente": "Questions about current events won't get fresh data",
    "casa.collegato": "Connected", "casa.no_strumenti": "Tools not accepted by the model", "casa.non_configurato": "Not configured",
    "casa.imposta": "Set the URL and token in Settings",
    "adatt.titolo": "Automatic adjustments: ", "adatt.strumenti": "the model does not accept tools: no home control and no service-side web search",
    "adatt.web": "native web search was rejected by the endpoint", "adatt.max": "the endpoint uses max_completion_tokens",
    "adatt.thinking": "the endpoint does not accept the thinking parameter",
    "stat.domande": "questions", "stat.storico_spento": "questions (history off)", "stat.medio": "average time",
    "stat.lente": "over %s s (\"let me think\")", "stat.errori": "errors", "stat.azioni": "home actions",
    "durata.giorni": "days",
    "conv.cerca": "Search questions and answers", "conv.tutte": "All",
    "conv.nota": "Kept in the service's data volume: they survive restarts and updates. Users are anonymised.",
    "conv.nessuna": "No questions yet. Talk to Alexa or use the test chat.",
    "conv.nessuna_filtro": "No conversation matches the filter.", "conv.allora": "delivered on \"so?\"",
    "conv.errore": "Error: ", "conv.svuota_conferma": "Clear the conversation history?",
    "chat.simula": "Simulate home actions", "chat.nuova": "New conversation", "chat.invia": "Send",
    "chat.placeholder": "Ask a question…",
    "chat.vuoto": "Write as you would speak to Alexa, for example \"what's the weather tomorrow\" or \"turn on the living room light\".",
    "chat.nuova_fatta": "New conversation. The model no longer remembers the previous questions.",
    "chat.fallita": "Alexa would say: \"I couldn't answer that.\" (%s)", "chat.lenta": "on Alexa: \"Let me think\", then \"so?\"",
    "casa.intro": "The Home Assistant entities the assistant can see, with the rules that protect them. You can forbid more of them, or always require a spoken yes before controlling them.",
    "casa.cerca": "Search by name or entity_id", "casa.vista_tutte": "All", "casa.vista_comandabili": "Controllable",
    "casa.vista_bloccate": "Never controllable", "casa.vista_conferma": "Ask for a yes",
    "casa.blocco.dominio": "Never controllable (entity type)", "casa.blocco.regole": "Blocked by the built-in safety rules",
    "casa.blocco.regex": "Blocked by your HA_VIETATO rule", "casa.blocco.pagina": "Forbidden by you",
    "casa.comandabile": "Controllable", "casa.vieta": "Forbid", "casa.conferma": "Always ask for a yes",
    "casa.scena": "A scene runs whatever it contains: keep locks and alarms out of it.",
    "casa.non_configurata": "Home Assistant is not configured: set the URL and token in Settings.",
    "casa.nessuna": "No entity matches.", "casa.errore": "Home Assistant does not answer: %s",
    "casa.nota_conferma": "Actions on more than %s entities always ask for a yes anyway.",
    "modifiche.una": "1 unsaved change", "modifiche.tante": "%s unsaved changes",
    "imp.sola_lettura": "Read only. ", "imp.sola_lettura_desc": "Saving from the page needs a writable data folder (%s): the bundled compose file mounts it; otherwise see docs/admin.md.",
    "imp.salvata": "saved here", "imp.env": "from .env", "imp.predefinita": "default", "imp.torna_env": "Back to the .env value", "imp.torna_predefinito": "Back to the default",
    "imp.valore_env": "value from .env",
    "imp.cancella": "Clear", "imp.cancellata": "will be cleared on save", "imp.segreta": "•••••••• set: type to change it",
    "imp.non_impostata": "not set", "imp.credenziali": "  (contains credentials: type to change it)",
    "imp.predefinito": "default: %s", "imp.automatico": "(automatic)", "imp.non_impostato": "(not set)",
    "imp.istruzioni_incluse": "empty: the built-in instructions",
    "imp.applicata": "Settings applied.", "imp.salvate_riavvia": "Saved. Restart the service to apply them.",
    "sis.alexa": "Alexa", "sis.skill_id": "Skill ID", "sis.endpoint": "Endpoint to enter in the Alexa console",
    "sis.endpoint_mancante": "Set PUBLIC_HOST in .env to see it here.", "sis.lingua": "Assistant language",
    "sis.modello_desc": "Paste it in the JSON Editor of the Alexa console, in the matching language. With the automatic language one skill can have both: Italian in Italian (IT), English in English (US).",
    "sis.scarica": "Download %s", "sis.copia": "Copy", "sis.copiato": "Copied.",
    "sis.servizio": "Service", "sis.versione": "Version", "sis.attivo_da": "Up for", "sis.aggiornamenti": "Check for updates",
    "sis.aggiornato": "You have the latest version (%s).", "sis.nuova": "Version %s is available.", "sis.vedi": "See the release",
    "sis.sviluppo": "Development version: the latest release is %s.",
    "sis.riavvia": "Restart the service", "sis.riavvia_conferma": "Restart the service? Answers still waiting will be lost.",
    "sis.riavviato": "Service restarted.", "sis.non_riavviabile": "Automatic restart is not available: restart the container.",
    "sis.scarta": "Discard answers waiting", "sis.scartate": "Discarded.",
    "sis.sicurezza": "Access", "sis.password": "Change the admin page password", "sis.attuale": "Current password",
    "sis.nuova_pw": "New password (at least 12 characters)", "sis.ripeti_pw": "Repeat the new password", "sis.cambia": "Change password",
    "sis.pw_diverse": "The two passwords do not match.", "sis.pw_cambiata": "Password changed: every other session was logged out.",
    "sis.pw_da_pagina": "The password was changed from this page and replaces ADMIN_PASSWORD.",
    "sis.pw_da_env": "ADMIN_PASSWORD from .env is in use.", "sis.pw_ripristina": "Go back to the .env password",
    "sis.pw_ripristinata": "The .env password is in use again.",
    "sis.pw_serve_attuale": "Type the current password in the first box, then try again.",
    "sis.esci_ovunque": "Log out everywhere", "sis.esci_conferma": "Log out every session, this one included?",
    "sis.backup": "Settings backup", "sis.backup_desc": "Exports every setting except keys, tokens and addresses with credentials; importing checks them like a normal save.",
    "sis.esporta": "Export", "sis.importa": "Import", "sis.importa_conferma": "Import %s settings and restart?",
    "sis.importa_errore": "The file is not a valid backup.", "sis.importate": "Settings imported.",
    "sis.importa_saltati": "Set these again in Settings, together with their key: %s.",
    "sis.importa_solo_url": "The backup only holds addresses without their key (%s): set them in Settings together with the key.",
    "sis.rete": "Network and publishing", "sis.rete_desc": "These are changed in .env on the server, then docker compose up -d: they decide where the service can be reached.",
    "sis.pubblico_on": "The page can be reached through the reverse proxy.", "sis.pubblico_off": "The page is not published through the reverse proxy.",
    "sis.non_impostato": "not set",
    "reg.tutti": "All levels", "reg.avvisi": "Warnings and errors only", "reg.auto": "Auto refresh", "reg.vuoto": "No lines.",
    "err.sessione": "Session expired",
    "sub.panoramica": "The state of the service, and a quick check of each part of it.",
    "sub.conversazioni": "The latest questions to Alexa, the test chat and the checks, with the home actions they ran.",
    "sub.chat": "Talk to the assistant in writing: same model, same tools and same rules as on the Echo.",
    "sub.casa": "The Home Assistant entities the assistant can see and the rules that protect them. Forbid more of them, or always require a spoken yes.",
    "sub.impostazioni": "Every setting with its explanation. Saving checks the values and restarts the service by itself.",
    "sub.sistema": "What the Alexa console needs, the version, access to this page and backup.",
    "sub.registro": "The latest lines written by the service.",
    "conv.e2e": "E2E test",
    "imp.predefinita_valore": "default: %s", "imp.vale": "default: %s", "imp.vuota": "empty",
    "imp.altro_modello": "Other… (type it)", "imp.modelli_n": "List from the provider: %s models.",
    "imp.modelli_errore": "Model list not available (%s): type the name.",
    "imp.non_impostata_c": "not set",
    "opt.LANGUAGE.auto": "Automatic: the language the Echo speaks", "opt.LANGUAGE.it": "Italian", "opt.LANGUAGE.en": "English",
    "opt.LLM_API.": "Automatic (from the URL)", "opt.LLM_API.anthropic": "Anthropic (Claude)", "opt.LLM_API.openai": "OpenAI-compatible",
    "opt.WEB_SEARCH.auto": "Automatic", "opt.WEB_SEARCH.native": "Claude's native search", "opt.WEB_SEARCH.searxng": "SearXNG",
    "opt.WEB_SEARCH.brave": "Brave Search", "opt.WEB_SEARCH.tavily": "Tavily", "opt.WEB_SEARCH.off": "Off",
    "opt.HA_TOOLS.1": "On", "opt.HA_TOOLS.0": "Off", "opt.NOTIFY_ATTIVE.1": "On", "opt.NOTIFY_ATTIVE.0": "Paused",
    "sis.lingua_auto": "Automatic: Italian or English, as the Echo speaks",
    "tab.automazioni": "Automations",
    "sub.automazioni": "The Home Assistant automations created by voice: ask Alexa \"every evening at sunset turn on the living room light\", she reads it back and creates it only after your yes.",
    "auto.cerca": "Search by name or description",
    "auto.titolo_on": "Automations by voice are on", "auto.titolo_off": "Automations by voice are off",
    "auto.desc_on": "The assistant can create automations (at a time, at sunrise or sunset, when a state changes or a sensor crosses a threshold) and enable, disable or delete them. Their actions follow the rules of the Home tab; creating and deleting always need a spoken yes; it only sees and changes the ones it created.",
    "auto.desc_off": "Switch them on to ask Alexa to create Home Assistant automations. An administrator's token is needed (Settings → Token for automations): Home Assistant lets only administrators write automations.",
    "auto.attiva": "Switch on", "auto.disattiva": "Switch off",
    "auto.senza_strumenti": "Home tools are off (Settings → Home tools): while they stay off the assistant neither sees nor creates automations.",
    "auto.no_permessi": "The token in use is not an administrator's: Home Assistant will refuse to create and delete automations. Set Token for automations in Settings.",
    "auto.permessi_ok": "The token can create and delete automations.",
    "auto.limite": "At most %s automations created by voice (%s now).",
    "auto.nessuna": "No automation created by voice yet. Try: \"Alexa, open big brain\", then \"every day at seven turn on the kitchen light\".",
    "auto.nessuna_filtro": "No automation matches.",
    "auto.non_configurata": "Home Assistant is not configured: set the URL and token in Settings.",
    "auto.errore": "Home Assistant does not answer: %s",
    "auto.accesa": "On", "auto.spenta": "Off", "auto.sparita": "No longer in Home Assistant",
    "auto.ultima": "last run %s", "auto.mai": "never run", "auto.creata": "created %s",
    "auto.elimina": "Delete", "auto.elimina_conferma": "Delete the automation \"%s\" from Home Assistant?", "auto.dimentica": "Remove from the list",
    "auto.eliminata": "Automation deleted.", "auto.attivata": "Automation switched on.", "auto.disattivata": "Automation switched off.",
    "opt.HA_AUTOMAZIONI.1": "On", "opt.HA_AUTOMAZIONI.0": "Off",
    "tab.notifiche": "Notifications",
    "sub.notifiche": "A message on your phone when something worth knowing happens: an action confirmed by voice, a blocked attempt on doors or alarms, an automation created.",
    "not.generale": "Notifications", "not.attive": "Send notifications", "not.max": "At most per hour",
    "not.max_desc": "Beyond this number the next ones are not sent; the same message is not repeated within two minutes.",
    "not.eventi": "When to tell you",
    "nev.confermate": "Actions confirmed by voice", "nevd.confermate": "Actions on several rooms or on entities that always ask for a yes, run after your yes.",
    "nev.bloccate": "Blocked attempts", "nevd.bloccate": "The model asked for something forbidden: opening a lock or a door, the alarm, an entity you forbade.",
    "nev.automazioni": "Automations", "nevd.automazioni": "Created, enabled, disabled or deleted, by voice or from this page.",
    "nev.azioni": "Every home action", "nevd.azioni": "Every command sent to Home Assistant, even turning on a light: they can be many.",
    "nev.errori": "Errors", "nevd.errori": "Alexa could not answer (model unreachable, wrong key…).",
    "nev.pannello": "Admin page", "nevd.pannello": "Logins, too many wrong passwords, password changed, settings saved.",
    "not.canali": "Channels", "not.canali_desc": "Every configured channel gets every notification. Tokens and addresses are set in Settings, Notifications group.",
    "can.ha": "Home Assistant app", "can.telegram": "Telegram", "can.ntfy": "ntfy", "can.gotify": "Gotify", "can.webhook": "Webhook",
    "not.configurato": "Configured", "not.non_configurato": "Not configured", "not.configura": "Configure",
    "not.servizi": "Home Assistant notify services: choose where to send them (the phone app is called mobile_app_…).",
    "not.servizi_nessuno": "Home Assistant has no notify service: install the Home Assistant app on your phone and log in.",
    "not.servizi_errore": "Service list not available (%s).", "not.ha_non_configurato": "Home Assistant (URL and token) is needed in Settings.",
    "not.prova": "Send a test notification", "not.prova_nessuno": "Configure at least one channel first.",
    "not.ultime": "Latest notifications", "not.ultime_vuoto": "No notification yet since the service started.",
    "nev.prova": "Test",
    "nev.modelli": "Models not answering", "nevd.modelli": "A model is unreachable, logged out or out of credit and the next one answers; when it is back.",
    "nev.memoria": "Things learned", "nevd.memoria": "The assistant saved something new about the people at home.",
    "tab.modelli": "Models",
    "sub.modelli": "The main model and the fallback ones, tried in order: when one does not answer, is logged out or out of tokens, the next one answers.",
    "mod.ordine": "In the order they are tried", "mod.ordine_desc": "A model that does not answer is paused and the next one is used; after the pause the main one is tried again. After a home action the model is never switched halfway (it could repeat it).",
    "mod.principale": "Main", "mod.riserva": "Fallback · %s", "mod.saltato": "Not used", "mod.giu": "Not available: %s",
    "mod.fino": "paused until %s", "mod.in_uso": "Answering", "mod.disponibile": "Available", "mod.non_provato": "Not used yet",
    "mod.senza_chiave": "no key", "mod.usa": "Use", "mod.prova": "Check", "mod.modifica": "Edit", "mod.ultimo_ok": "last answer %s",
    "mod.ultimo_errore": "last error %s", "mod.aggiungi": "Add a fallback model",
    "mod.aggiungi_desc": "For example another CLIProxyAPI with another account, or another provider: it is set in Settings, group Model %s (fallback).",
    "mod.pieno": "All %s possible models are configured.",
    "mod.comportamento": "Behaviour", "mod.pausa": "Pause of a model that does not answer (seconds)",
    "mod.pausa_desc": "It is skipped for this long; 0 tries it again at every question.",
    "mod.controllo": "Background check (minutes)",
    "mod.controllo_desc": "How often to check that every model is reachable and its key valid: it uses the model list, no tokens. 0 never.",
    "mod.notifica": "Tell me when a model stops answering or is back",
    "mod.notifica_desc": "With the channels of the Notifications tab.", "mod.nessun_canale": "No notification channel is configured: set one in the Notifications tab.",
    "mod.notifiche_sospese": "Notifications are paused in the Notifications tab.",
    "mod.prova_desc": "Check asks that model only a short question (a few tokens): it shows whether it is logged in and has credit.",
    "card.riserve": "+%s fallback", "card.riserva_in_uso": "Fallback model %s is answering",
    "imp.gruppo_chiuso": "not configured: open to add it",
    "opt.SI.1": "Yes", "opt.SI.0": "No", "opt.MEMORIA.1": "On", "opt.MEMORIA.0": "Off",
    "tab.memoria": "Memory",
    "sub.memoria": "What the assistant knows about you and the people you live with, learned from the conversations: it uses it to answer you better. You can correct, add or delete anything.",
    "mem.generale": "Memory", "mem.attiva": "Remember from one conversation to the next",
    "mem.auto": "Learn by itself after every answer",
    "mem.auto_desc": "A short background request, after Alexa has already answered, looks for new facts (a few more tokens per question). Off: it learns only when you ask (\"remember that…\") or when the model decides.",
    "mem.max": "Maximum facts remembered", "mem.recenti": "Exchanges from earlier conversations to read again",
    "mem.giorni": "For how many days", "mem.recenti_desc": "So that \"as I told you yesterday\" makes sense. 0: none.",
    "mem.istruzioni": "What to remember", "mem.istruzioni_ph": "empty: lasting facts about the people at home (names, relationships, tastes, habits, schedules, birthdays, pets)",
    "mem.mai": "Passwords, codes and confidential data are never saved.",
    "mem.fatti": "What it knows (%s)", "mem.nuovo": "A fact to remember, e.g. Anna is vegetarian", "mem.persona": "Person (optional)",
    "mem.aggiungi": "Add", "mem.cerca": "Search the memory", "mem.nessuno": "Nothing yet. Try telling Alexa: \"remember that on Saturdays we go swimming\".",
    "mem.nessuno_filtro": "Nothing matches.", "mem.modifica": "Edit", "mem.elimina": "Forget", "mem.salva": "Save", "mem.annulla": "Cancel",
    "mem.elimina_conferma": "Forget \"%s\"?", "mem.svuota": "Forget everything", "mem.svuota_conferma": "Forget everything the assistant knows?",
    "mem.fonte.voce": "by voice", "mem.fonte.auto": "learned", "mem.fonte.pannello": "from here",
    "mem.voci": "Recognised voices",
    "mem.voci_desc": "If everyone has a voice profile in the Alexa app and the skill has Skill Personalization on in the Alexa console (Build → Permissions), the assistant knows who is speaking: whoever says \"I'm Anna\" is remembered.",
    "mem.voci_nessuna": "No voice recognised so far.", "mem.voce_dimentica": "Forget",
    "mem.scambi": "Recent conversations", "mem.scambi_desc": "The last questions and answers the assistant reads again.",
    "mem.scambi_nessuno": "No conversation saved.", "mem.scambi_svuota": "Clear",
    "mem.salvato": "Saved.", "mem.dimenticato": "Forgotten.",
  },
};

// the fallback models have the same menus as the main one
for (const l of ["it", "en"]) {
  for (let n = 2; n <= 5; n++) {
    for (const o of ["", "anthropic", "openai"]) TESTI[l]["opt.LLM_" + n + "_API." + o] = TESTI[l]["opt.LLM_API." + o];
    for (const o of ["1", "0"]) TESTI[l]["opt.LLM_" + n + "_ATTIVO." + o] = TESTI[l]["opt.SI." + o];
  }
  for (const o of ["1", "0"]) TESTI[l]["opt.MEMORIA_AUTO." + o] = TESTI[l]["opt.SI." + o];
}

let lingua = (() => {
  try { const l = localStorage.getItem("aab-lingua"); if (l === "it" || l === "en") return l; } catch (e) { /* no storage */ }
  return (navigator.language || "").toLowerCase().startsWith("it") ? "it" : "en";
})();

function t(chiave, ...valori) {
  let s = (TESTI[lingua] && TESTI[lingua][chiave]) || TESTI.it[chiave] || chiave;
  for (const v of valori) s = s.replace("%s", v);
  return s;
}

function traduciPagina() {
  document.documentElement.lang = lingua;
  document.querySelectorAll("[data-t]").forEach((n) => { n.textContent = t(n.dataset.t); });
  document.querySelectorAll("[data-tp]").forEach((n) => { n.placeholder = t(n.dataset.tp); });
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lingua)));
}

function cambiaLingua(l) {
  lingua = l;
  try { localStorage.setItem("aab-lingua", l); } catch (e) { /* no storage */ }
  traduciPagina();
  if ($("#shell").hidden) return;
  caricaStato();
  const tab = document.getElementById("tab-" + location.hash.slice(1)) ? location.hash.slice(1) : "panoramica";
  intestazione(tab);
  if (tab === "conversazioni") disegnaStorico();
  if (tab === "impostazioni") caricaImpostazioni(true);
  if (tab === "casa") disegnaCasa();
  if (tab === "automazioni") disegnaAutomazioni();
  if (tab === "notifiche") disegnaNotifiche();
  if (tab === "modelli") disegnaModelli();
  if (tab === "memoria") disegnaMemoria();
  if (tab === "sistema") caricaSistema();
  if (tab === "chat" && !conversazione.length) messaggioVuoto(t("chat.vuoto"));
}

// ---------- helpers
let csrf = null, stato = null, timerStato = null, timerRegistro = null;

function el(tag, attrs, ...figli) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of figli.flat()) if (f !== null && f !== undefined && f !== false) n.append(f instanceof Node ? f : String(f));
  return n;
}

function toast(testo, ms = 3500) {
  const n = $("#toast");
  n.textContent = testo;
  n.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { n.hidden = true; }, ms);
}

async function api(metodo, percorso, corpo) {
  const opzioni = { method: metodo, headers: { "X-Lang": lingua }, credentials: "same-origin" };
  if (metodo !== "GET") opzioni.headers["X-CSRF"] = csrf || "";
  if (corpo !== undefined) {
    opzioni.headers["Content-Type"] = "application/json";
    opzioni.body = JSON.stringify(corpo);
  }
  const r = await fetch("/admin/api/" + percorso, opzioni);
  let dati = {};
  try { dati = await r.json(); } catch (e) { /* empty body */ }
  if (r.status === 401 && percorso !== "login" && percorso !== "password") { mostraLogin(); throw new Error(dati.errore || t("err.sessione")); }
  if (!r.ok) throw new Error(dati.errore || ("HTTP " + r.status));
  return dati;
}

function scarica(percorso) {
  // a plain link: the browser sends the session cookie and saves the attachment
  const a = el("a", { href: "/admin/api/" + percorso, download: "" });
  document.body.append(a);
  a.click();
  a.remove();
}

function quando(ts) {
  const d = new Date(ts * 1000), oggi = new Date(), loc = lingua === "it" ? "it-IT" : "en-GB";
  const ora = d.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return d.toDateString() === oggi.toDateString() ? ora : d.toLocaleDateString(loc, { day: "numeric", month: "short" }) + " " + ora;
}

function durataLeggibile(s) {
  if (s < 60) return Math.round(s) + " s";
  if (s < 3600) return Math.round(s / 60) + " min";
  if (s < 86400) return Math.round(s / 3600) + " h";
  return Math.round(s / 86400) + " " + t("durata.giorni");
}

function testoModifiche(n) { return n === 1 ? t("modifiche.una") : t("modifiche.tante", n); }

// ---------- login
function mostraLogin() {
  $("#shell").hidden = true;
  $("#login").hidden = false;
  clearInterval(timerStato); clearInterval(timerRegistro);
  setTimeout(() => $("#password").focus(), 50);
}

async function entra(ev) {
  ev.preventDefault();
  const bottone = ev.target.querySelector("button[type=submit]");
  bottone.disabled = true;
  $("#login-errore").textContent = "";
  try {
    csrf = (await api("POST", "login", { password: $("#password").value })).csrf;
    $("#password").value = "";
    avvia();
  } catch (e) {
    $("#login-errore").textContent = e.message;
  } finally {
    bottone.disabled = false;
  }
}

// ---------- tabs
function vaiA(tab) {
  if (!document.getElementById("tab-" + tab)) tab = "panoramica";
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  document.querySelectorAll(".tab").forEach((s) => { s.hidden = s.id !== "tab-" + tab; });
  intestazione(tab);
  if (location.hash !== "#" + tab) history.replaceState(null, "", "#" + tab);
  document.querySelector('.tabs button[aria-selected="true"]')?.scrollIntoView({ block: "nearest", inline: "nearest" });
  clearInterval(timerRegistro);
  if (tab === "conversazioni") caricaStorico();
  if (tab === "impostazioni") caricaImpostazioni(true);
  if (tab === "casa" && !modificheCasa()) caricaCasa();
  if (tab === "automazioni") caricaAutomazioni();
  if (tab === "notifiche" && !modificheNotifiche()) caricaNotifiche();
  if (tab === "modelli" && !modificheModelli()) caricaModelli();
  if (tab === "memoria") caricaMemoria(modificheMemoria() > 0);
  if (tab === "sistema") caricaSistema();
  if (tab === "registro") { caricaRegistro(); timerRegistro = setInterval(() => { if ($("#auto-registro").checked) caricaRegistro(); }, 5000); }
  if (tab === "chat") {
    if (!conversazione.length && !$("#messaggi").children.length) messaggioVuoto(t("chat.vuoto"));
    setTimeout(() => $("#chat-testo").focus(), 50);
  }
}

function intestazione(tab) {
  $("#titolo-pagina").textContent = t("tab." + tab);
  $("#sottotitolo-pagina").textContent = t("sub." + tab);
}

// ---------- overview
function card(titolo, livello, valore, sotto) {
  return el("div", { class: "card" },
    el("div", { class: "card-head" }, el("span", { class: "dot " + livello }), titolo),
    el("div", { class: "card-value", text: valore }),
    sotto ? el("div", { class: "card-sub", text: sotto }) : null);
}

function cardModello(m, fornitori) {
  const riserve = fornitori.filter((f) => f.n > 1 && f.attivo), uso = fornitori.find((f) => f.in_uso && f.n > 1);
  const giu = fornitori.some((f) => f.attivo && f.giu);
  const sotto = uso ? t("card.riserva_in_uso", uso.n) + " · " + uso.host
    : (m.api === "anthropic" ? "Anthropic" : t("card.compatibile")) + " · " + m.url + (riserve.length ? " · " + t("card.riserve", riserve.length) : "");
  const c = card(t("card.modello"), giu || uso || !(m.chiave || !m.url.startsWith("https")) ? "warn" : "ok", uso ? uso.modello : m.nome, sotto);
  c.classList.add("cliccabile");
  c.addEventListener("click", () => vaiA("modelli"));
  return c;
}

async function caricaStato() {
  try { stato = await api("GET", "stato"); } catch (e) { return; }
  $("#versione").textContent = "v" + stato.versione.replace(/^v/, "");
  const m = stato.modello, w = stato.web, c = stato.casa;
  const webTesto = { native: t("web.native"), searxng: "SearXNG", brave: "Brave Search", tavily: "Tavily" }[w.backend] || t("web.spenta");
  $("#stato-cards").replaceChildren(
    card(t("card.servizio"), stato.avvisi ? "warn" : "ok", t("card.attivo_da", durataLeggibile(stato.ora - stato.avvio)),
      stato.in_sospeso ? t("card.sospese", stato.in_sospeso) : (stato.avvisi ? t("card.avvisi", stato.avvisi) : t("card.nessun_avviso"))),
    cardModello(m, stato.fornitori || []),
    card(t("card.web"), w.attiva ? "ok" : (w.backend ? "warn" : ""), webTesto, w.backend && !w.attiva ? t("web.rifiutata") : (w.attiva ? t("web.ok") : t("web.niente"))),
    card(t("card.casa"), c.attiva ? "ok" : (c.configurata ? "warn" : ""), c.attiva ? t("casa.collegato") : (c.configurata ? t("casa.no_strumenti") : t("casa.non_configurato")), c.url || t("casa.imposta")),
  );
  const a = stato.adattamenti, note = [];
  if (!a.strumenti) note.push(t("adatt.strumenti"));
  if (!a.web_nativo) note.push(t("adatt.web"));
  if (a.max_completion) note.push(t("adatt.max"));
  if (a.thinking === false) note.push(t("adatt.thinking"));
  $("#adattamenti").replaceChildren(...(note.length ? [el("div", { class: "notice" }, el("strong", { text: t("adatt.titolo") }), note.join("; ") + ".")] : []));
  const s = stato.statistiche;
  const stat = (n, l) => el("div", { class: "stat" }, el("b", { text: n }), el("span", { text: l }));
  $("#stats").replaceChildren(
    stat(s.domande, stato.storico_attivo ? t("stat.domande") : t("stat.storico_spento")),
    stat(s.durata_media === null ? "–" : s.durata_media + " s", t("stat.medio")),
    stat(s.lente, t("stat.lente", stato.attesa)),
    stat(s.errori, t("stat.errori")),
    stat(s.azioni, t("stat.azioni")),
  );
}

async function prova(box) {
  const bottone = box.querySelector("button"), esito = box.querySelector(".esito");
  bottone.disabled = true;
  bottone.textContent = t("btn.in_corso");
  esito.hidden = false;
  esito.className = "esito";
  esito.textContent = "…";
  try {
    const r = await api("POST", "prova/" + box.dataset.prova);
    esito.className = "esito " + (r.ok ? "ok" : "bad");
    esito.textContent = (r.ok ? "✓ " : "✗ ") + (r.durata ? r.durata + " s\n" : "") + r.esito;
  } catch (e) {
    esito.className = "esito bad";
    esito.textContent = "✗ " + e.message;
  } finally {
    bottone.disabled = false;
    bottone.textContent = t("btn.prova");
  }
}

// ---------- history
let storico = [];

async function caricaStorico() {
  try { storico = (await api("GET", "storico")).voci; } catch (e) { return; }
  disegnaStorico();
}

function chipAzione(a) {
  return el("span", { class: "chip " + (a.startsWith("[simulata]") ? "" : "accent"), text: a });
}

function disegnaStorico() {
  const testo = $("#filtro").value.trim().toLowerCase(), origine = $("#filtro-origine").value;
  const voci = storico.filter((v) => (!origine || v.origine === origine) &&
    (!testo || (v.domanda + " " + (v.risposta || "") + " " + (v.errore || "")).toLowerCase().includes(testo)));
  if (!voci.length) {
    $("#storico").replaceChildren(el("p", { class: "vuoto", text: storico.length ? t("conv.nessuna_filtro") : t("conv.nessuna") }));
    return;
  }
  const lenta = stato ? stato.attesa : 6;
  $("#storico").replaceChildren(...voci.map((v) => el("article", { class: "voce" },
    el("div", { class: "voce-meta" },
      el("time", { text: quando(v.t) }),
      el("span", { class: "chip " + (v.origine === "alexa" ? "" : "accent"),
        text: v.origine === "chat" ? t("tab.chat") : v.origine === "e2e" ? t("conv.e2e") : "Alexa · " + v.utente }),
      el("span", { class: "chip " + (v.errore ? "bad" : v.durata > lenta ? "warn" : "ok"), text: v.durata + " s" }),
      v.durata > lenta && !v.errore ? el("span", { class: "chip warn", text: t("conv.allora") }) : null),
    el("div", { class: "q", text: v.domanda }),
    el("div", { class: "a" + (v.errore ? " err" : ""), text: v.risposta || (t("conv.errore") + v.errore) }),
    v.azioni.length ? el("div", { class: "azioni" }, v.azioni.map(chipAzione)) : null)));
}

// ---------- test chat
let conversazione = [];

function messaggioVuoto(testo) {
  $("#messaggi").replaceChildren(el("p", { class: "vuoto", text: testo }));
}

function aggiungi(nodo) {
  const box = $("#messaggi");
  box.querySelector(".vuoto")?.remove();
  box.append(nodo);
  box.scrollTop = box.scrollHeight;
  return nodo;
}

async function invia(ev) {
  ev.preventDefault();
  const campo = $("#chat-testo"), testo = campo.value.trim();
  if (!testo) return;
  campo.value = "";
  campo.disabled = true;
  aggiungi(el("div", { class: "msg user", text: testo }));
  const attesa = aggiungi(el("div", { class: "typing", "aria-label": "…" }, el("i"), el("i"), el("i")));
  try {
    const r = await api("POST", "chat", { testo, storia: conversazione, simula: $("#simula").checked, lingua });
    attesa.remove();
    if (r.risposta) {
      conversazione = r.storia;
      aggiungi(el("div", { class: "msg bot", text: r.risposta }));
    } else {
      aggiungi(el("div", { class: "msg bot err", text: t("chat.fallita", r.errore) }));
    }
    aggiungi(el("div", { class: "msg-meta" },
      el("span", { class: "chip " + (r.lenta ? "warn" : "ok"), text: r.durata + " s" }),
      r.lenta ? el("span", { class: "chip warn", text: t("chat.lenta") }) : null,
      r.azioni.map(chipAzione)));
  } catch (e) {
    attesa.remove();
    aggiungi(el("div", { class: "msg bot err", text: e.message }));
  } finally {
    campo.disabled = false;
    campo.focus();
  }
}

function nuovaChat() {
  conversazione = [];
  messaggioVuoto(t("chat.nuova_fatta"));
  $("#chat-testo").focus();
}

// ---------- home: safety rules per entity
let casa = null, casaGruppi = new Set(), casaVietate = new Set();

async function caricaCasa() {
  try { casa = await api("GET", "casa"); } catch (e) { toast(e.message); return; }
  casaGruppi = new Set(casa.gruppi || []);
  casaVietate = new Set(casa.vietate || []);
  disegnaCasa();
}

function modificheCasa() {
  if (!casa) return 0;
  const g0 = new Set(casa.gruppi || []), v0 = new Set(casa.vietate || []);
  let n = 0;
  for (const x of new Set([...g0, ...casaGruppi])) if (g0.has(x) !== casaGruppi.has(x)) n++;
  for (const x of new Set([...v0, ...casaVietate])) if (v0.has(x) !== casaVietate.has(x)) n++;
  return n;
}

function aggiornaBarraCasa() {
  const n = modificheCasa();
  $("#casa-savebar").hidden = n === 0;
  $("#casa-savebar-testo").textContent = testoModifiche(n);
}

function interruttore(etichetta, acceso, cambia) {
  const input = el("input", { type: "checkbox", onchange: (e) => cambia(e.target.checked) });
  input.checked = acceso;
  return el("label", { class: "switch small" }, input, el("span"), " " + etichetta);
}

function disegnaCasa() {
  const box = $("#casa");
  if (!casa) return;
  if (!casa.configurata) { box.replaceChildren(el("p", { class: "vuoto", text: t("casa.non_configurata") })); return; }
  if (casa.errore) { box.replaceChildren(el("p", { class: "vuoto", text: t("casa.errore", casa.errore) })); return; }
  const testo = $("#casa-filtro").value.trim().toLowerCase(), vista = $("#casa-vista").value;
  const voci = casa.entita.map((e) => Object.assign({}, e, {
    fissa: Boolean(e.blocco && e.blocco !== "pagina"),   // decided by the built-in rules or by a hand-written regex
    vietataOra: casaVietate.has(e.id),
    gruppoOra: casaGruppi.has(e.id),
  })).filter((e) => {
    if (testo && !(e.id + " " + e.nome).toLowerCase().includes(testo)) return false;
    const bloccata = e.fissa || e.vietataOra;
    if (vista === "comandabili") return !bloccata;
    if (vista === "bloccate") return bloccata;
    if (vista === "conferma") return e.gruppoOra;
    return true;
  });
  const righe = voci.map((e) => {
    const bloccata = e.fissa || e.vietataOra;
    const etichetta = e.fissa ? el("span", { class: "stato-testo bad", text: t("casa.blocco." + e.blocco) })
      : e.vietataOra ? el("span", { class: "stato-testo bad", text: t("casa.blocco.pagina") })
      : el("span", { class: "stato-testo ok", text: t("casa.comandabile") });
    return el("div", { class: "entita" + (bloccata ? " bloccata" : "") },
      el("div", { class: "entita-info" },
        el("div", { class: "entita-nome", text: e.nome }),
        el("div", { class: "entita-id" }, el("code", { text: e.id }), e.stato == null ? "" : " · " + String(e.stato)),
        e.dominio === "scene" && !bloccata ? el("div", { class: "entita-nota", text: t("casa.scena") }) : null),
      el("div", { class: "entita-azioni" },
        etichetta,
        e.fissa ? null : interruttore(t("casa.vieta"), e.vietataOra, (on) => {
          if (on) casaVietate.add(e.id); else casaVietate.delete(e.id);
          disegnaCasa();
        }),
        bloccata ? null : interruttore(t("casa.conferma"), e.gruppoOra, (on) => {
          if (on) casaGruppi.add(e.id); else casaGruppi.delete(e.id);
          aggiornaBarraCasa();
        })));
  });
  box.replaceChildren(
    el("p", { class: "muted small", text: t("casa.nota_conferma", casa.max_senza_conferma) }),
    ...(righe.length ? righe : [el("p", { class: "vuoto", text: t("casa.nessuna") })]));
  aggiornaBarraCasa();
}

async function salvaCasa() {
  await salvaERiavvia($("#casa-salva"), () => api("POST", "casa", { gruppi: [...casaGruppi], vietate: [...casaVietate] }), caricaCasa);
}

// ---------- automations created by voice
let automazioni = null;

async function caricaAutomazioni() {
  try { automazioni = await api("GET", "automazioni"); } catch (e) { toast(e.message); return; }
  disegnaAutomazioni();
}

function quandoIso(v) {
  const ms = Date.parse(v);
  return Number.isNaN(ms) ? String(v) : quando(ms / 1000);
}

function statoAutomazioni(a) {
  const box = $("#auto-stato");
  if (!a.configurata) { box.replaceChildren(); return; }
  const bott = el("button", { class: "btn small " + (a.abilitata ? "" : "primary"), type: "button",
    text: a.abilitata ? t("auto.disattiva") : t("auto.attiva"), disabled: !a.configurabile || null,
    onclick: async (ev) => {
      await salvaERiavvia(ev.target, () => api("POST", "impostazioni", { valori: { HA_AUTOMAZIONI: a.abilitata ? "0" : "1" } }),
        caricaAutomazioni);
      disegnaAutomazioni();        // the button gets its own label back, also when saving failed
    } });
  const note = [];
  if (a.abilitata && !a.strumenti) note.push(el("div", { class: "notice" }, t("auto.senza_strumenti")));
  if (a.permessi === false) note.push(el("div", { class: "notice" }, t("auto.no_permessi")));
  box.replaceChildren(
    el("div", { class: "notice " + (a.attiva ? "ok" : "info") },
      el("div", { class: "auto-testa" },
        el("div", {}, el("strong", { text: a.attiva ? t("auto.titolo_on") : t("auto.titolo_off") }),
          el("p", { text: a.abilitata ? t("auto.desc_on") : t("auto.desc_off") })),
        bott)),
    ...note,
    el("p", { class: "muted small", text: t("auto.limite", a.max, a.voci.length) + (a.permessi === true ? " " + t("auto.permessi_ok") : "") }));
}

function disegnaAutomazioni() {
  const box = $("#automazioni"), a = automazioni;
  if (!a) return;
  statoAutomazioni(a);
  if (!a.configurata) { box.replaceChildren(el("p", { class: "vuoto", text: t("auto.non_configurata") })); return; }
  if (a.errore) { box.replaceChildren(el("p", { class: "vuoto", text: t("auto.errore", a.errore) })); return; }
  const testo = $("#auto-filtro").value.trim().toLowerCase();
  const voci = a.voci.filter((v) => !testo || (v.nome + " " + v.riassunto + " " + (v.entity_id || "")).toLowerCase().includes(testo));
  if (!voci.length) {
    box.replaceChildren(el("p", { class: "vuoto", text: a.voci.length ? t("auto.nessuna_filtro") : t("auto.nessuna") }));
    return;
  }
  box.replaceChildren(...voci.map((v) => {
    const sparita = v.stato === null, accesa = v.stato === "on";
    const meta = [v.entity_id ? el("code", { text: v.entity_id }) : el("code", { text: v.id }),
      " · " + (v.ultima ? t("auto.ultima", quandoIso(v.ultima)) : t("auto.mai")),
      v.creata ? " · " + t("auto.creata", quando(v.creata)) : ""];
    const elimina = el("button", { class: "btn small danger", type: "button", text: sparita ? t("auto.dimentica") : t("auto.elimina"),
      onclick: async (ev) => {
        if (!sparita && !confirm(t("auto.elimina_conferma", v.nome))) return;
        ev.target.disabled = true;
        try { await api("POST", "automazioni/elimina", { id: v.id }); toast(t("auto.eliminata")); } catch (e) { toast(e.message, 6000); }
        caricaAutomazioni();
      } });
    return el("div", { class: "entita" + (accesa ? "" : " bloccata") },
      el("div", { class: "entita-info" },
        el("div", { class: "entita-nome", text: v.nome }),
        v.riassunto ? el("div", { class: "entita-descr", text: v.riassunto }) : null,
        el("div", { class: "entita-id" }, ...meta)),
      el("div", { class: "entita-azioni" },
        sparita ? el("span", { class: "stato-testo bad", text: t("auto.sparita") }) : interruttore(accesa ? t("auto.accesa") : t("auto.spenta"), accesa, async (on) => {
          try {
            await api("POST", "automazioni/stato", { id: v.id, attiva: on });
            toast(on ? t("auto.attivata") : t("auto.disattivata"));
          } catch (e) { toast(e.message, 6000); }
          caricaAutomazioni();
        }),
        elimina));
  }));
}

// ---------- notifications
let notif = null, notifScelte = null;

function scelteDa(n) {
  return { attive: n.attive, eventi: new Set(n.eventi), ha: new Set(n.ha_scelti), max_ora: String(n.max_ora) };
}

async function caricaNotifiche() {
  try { notif = await api("GET", "notifiche"); } catch (e) { toast(e.message); return; }
  notifScelte = scelteDa(notif);
  disegnaNotifiche();
}

function modificheNotifiche() {
  if (!notif || !notifScelte) return 0;
  const p = scelteDa(notif), diversi = (a, b) => [...new Set([...a, ...b])].filter((x) => a.has(x) !== b.has(x)).length;
  return (p.attive !== notifScelte.attive) + (p.max_ora !== notifScelte.max_ora) + diversi(p.eventi, notifScelte.eventi) + diversi(p.ha, notifScelte.ha);
}

function aggiornaBarraNotifiche() {
  const n = modificheNotifiche();
  $("#notif-savebar").hidden = n === 0;
  $("#notif-savebar-testo").textContent = testoModifiche(n);
}

function casella(etichetta, descrizione, acceso, cambia, disabilitata) {
  const i = el("input", { type: "checkbox", disabled: disabilitata || null, onchange: (e) => { cambia(e.target.checked); aggiornaBarraNotifiche(); } });
  i.checked = acceso;
  return el("label", { class: "scelta" }, i, el("div", {}, el("b", { text: etichetta }), descrizione ? el("span", { text: descrizione }) : null));
}

function disegnaNotifiche() {
  const n = notif, sc = notifScelte;
  if (!n || !sc) return;
  const dis = !n.configurabile;
  const attive = interruttore(t("not.attive"), sc.attive, (on) => { sc.attive = on; aggiornaBarraNotifiche(); });
  if (dis) attive.querySelector("input").disabled = true;
  const max = el("input", { type: "number", class: "numero", min: "1", max: "1000", step: "1", disabled: dis || null,
    oninput: (e) => { sc.max_ora = e.target.value; aggiornaBarraNotifiche(); } });
  max.value = sc.max_ora;
  const esito = el("pre", { class: "esito", hidden: true });
  const provaBtn = bottone(t("not.prova"), async (ev) => {
    ev.target.disabled = true;
    esito.hidden = false; esito.className = "esito"; esito.textContent = "…";
    try {
      const r = await api("POST", "notifiche/prova");
      esito.className = "esito " + (r.ok ? "ok" : "bad");
      esito.textContent = Object.entries(r.esiti).map(([c, v]) => (v === "ok" ? "✓ " : "✗ ") + t("can." + c) + (v === "ok" ? "" : ": " + v)).join("\n");
    } catch (e) { esito.className = "esito bad"; esito.textContent = "✗ " + e.message; }
    ev.target.disabled = false;
    caricaNotifiche();
  }, "primary");
  const configurati = Object.values(n.canali).some((c) => c.configurato);
  if (!configurati) provaBtn.disabled = true;

  let servizi;
  if (!n.ha_configurato) servizi = el("p", { class: "muted small", text: t("not.ha_non_configurato") });
  else if (n.servizi_ha === null) servizi = el("p", { class: "muted small", text: t("not.servizi_errore", n.errore_ha || "?") });
  else {
    const nomi = [...new Set([...n.servizi_ha, ...sc.ha])].sort();
    servizi = el("div", {}, el("p", { class: "muted small", text: nomi.length ? t("not.servizi") : t("not.servizi_nessuno") }),
      el("div", { class: "scelte" }, nomi.map((s) => casella("notify." + s, null, sc.ha.has(s), (on) => { if (on) sc.ha.add(s); else sc.ha.delete(s); }, dis))));
  }
  const canale = (c) => {
    const k = n.canali[c];
    return el("div", { class: "canale" },
      el("div", { class: "canale-info" }, el("b", { text: t("can." + c) }), k.dettaglio ? el("div", { text: k.dettaglio }) : null),
      el("span", { class: "stato-testo " + (k.configurato ? "ok" : ""), text: k.configurato ? t("not.configurato") : t("not.non_configurato") }),
      c === "ha" ? null : el("button", { class: "link", type: "button", text: t("not.configura"), onclick: () => vaiA("impostazioni") }));
  };
  const ultime = n.ultime.length ? n.ultime.map((u) => el("div", { class: "voce" },
    el("div", { class: "voce-meta" }, el("time", { text: quando(u.t) }), el("span", { class: "chip", text: t("nev." + u.evento) })),
    el("div", { class: "a", text: u.testo }),
    el("div", { class: "azioni" }, Object.entries(u.esiti).map(([c, v]) => el("span", { class: "chip " + (v === "ok" ? "ok" : "bad"),
      text: t("can." + c) + (v === "ok" ? "" : " · " + v) })))))
    : [el("p", { class: "muted small", text: t("not.ultime_vuoto") })];

  $("#notifiche").replaceChildren(
    sezione(t("not.generale"), attive,
      rigaSis(t("not.max"), max), el("p", { class: "muted small", text: t("not.max_desc") })),
    sezione(t("not.eventi"), el("div", { class: "scelte" }, n.tutti.map((e) =>
      casella(t("nev." + e), t("nevd." + e), sc.eventi.has(e), (on) => { if (on) sc.eventi.add(e); else sc.eventi.delete(e); }, dis)))),
    sezione(t("not.canali"), el("p", { class: "muted small", text: t("not.canali_desc") }),
      ...["ha", "telegram", "ntfy", "gotify", "webhook"].map(canale), servizi,
      el("div", { class: "azioni-sis" }, provaBtn), configurati ? null : el("p", { class: "muted small", text: t("not.prova_nessuno") }), esito),
    sezione(t("not.ultime"), el("div", { class: "lista" }, ...ultime)));
  aggiornaBarraNotifiche();
}

async function salvaNotifiche() {
  const sc = notifScelte;
  await salvaERiavvia($("#notif-salva"), () => api("POST", "notifiche",
    { attive: sc.attive, eventi: [...sc.eventi], ha: [...sc.ha], max_ora: sc.max_ora }), caricaNotifiche);
}

// ---------- models: the main one and the fallback ones
let fornDati = null, fornScelte = null;

function scelteFornitori(d) {
  return { pausa: String(d.pausa), controllo: String(d.controllo), notifica: d.notifica,
    attivi: Object.fromEntries(d.fornitori.filter((f) => f.n > 1).map((f) => [String(f.n), f.attivo])) };
}

async function caricaModelli() {
  try { fornDati = await api("GET", "fornitori"); } catch (e) { toast(e.message); return; }
  fornScelte = scelteFornitori(fornDati);
  disegnaModelli();
}

function modificheModelli() {
  if (!fornDati || !fornScelte) return 0;
  const p = scelteFornitori(fornDati);
  return (p.pausa !== fornScelte.pausa) + (p.controllo !== fornScelte.controllo) + (p.notifica !== fornScelte.notifica) +
    Object.keys(p.attivi).filter((k) => p.attivi[k] !== fornScelte.attivi[k]).length;
}

function aggiornaBarraModelli() {
  const n = modificheModelli();
  $("#mod-savebar").hidden = n === 0;
  $("#mod-savebar-testo").textContent = testoModifiche(n);
}

function statoFornitore(f) {
  if (!f.attivo) return ["", t("mod.saltato")];
  if (f.giu) return ["bad", t("mod.giu", f.errore || "?") + (f.in_pausa ? " · " + t("mod.fino", quando(f.fino)) : "")];
  if (f.in_uso) return ["ok", t("mod.in_uso")];
  if (f.t_ok) return ["ok", t("mod.disponibile")];
  return ["", t("mod.non_provato")];
}

function apriGruppo(chiave) {
  gruppoDaAprire = chiave;
  vaiA("impostazioni");
}

function disegnaModelli() {
  const d = fornDati, sc = fornScelte;
  if (!d || !sc) return;
  const dis = !d.configurabile;
  const riga = (f) => {
    const [classe, testo] = statoFornitore(f);
    const esito = el("pre", { class: "esito", hidden: true });
    const prova = bottone(t("mod.prova"), async (ev) => {
      ev.target.disabled = true;
      esito.hidden = false; esito.className = "esito"; esito.textContent = "…";
      try {
        const r = await api("POST", "fornitori/prova", { n: f.n });
        esito.className = "esito " + (r.ok ? "ok" : "bad");
        esito.textContent = (r.ok ? "✓ " : "✗ ") + r.durata + " s\n" + r.esito;
        fornDati.fornitori = r.fornitori;
        setTimeout(disegnaModelli, 4000);
      } catch (e) { esito.className = "esito bad"; esito.textContent = "✗ " + e.message; }
      ev.target.disabled = false;
    });
    const usa = f.n > 1 ? interruttore(t("mod.usa"), sc.attivi[String(f.n)], (on) => { sc.attivi[String(f.n)] = on; aggiornaBarraModelli(); }) : null;
    if (usa && dis) usa.querySelector("input").disabled = true;
    const sotto = [(f.api === "anthropic" ? "Anthropic" : t("card.compatibile")) + " · " + f.host + (f.chiave ? "" : " · " + t("mod.senza_chiave"))];
    if (f.t_ok) sotto.push(t("mod.ultimo_ok", quando(f.t_ok)));
    if (f.t_errore && !f.giu) sotto.push(t("mod.ultimo_errore", quando(f.t_errore)) + (f.errore ? ": " + f.errore : ""));
    return el("div", {},
      el("div", { class: "canale" },
        el("div", { class: "canale-info" }, el("b", { text: (f.n === 1 ? t("mod.principale") : t("mod.riserva", f.n)) + " · " + f.modello }),
          el("div", { text: sotto.join(" · ") })),
        el("span", { class: "stato-testo " + classe, text: testo }),
        usa, prova,
        el("button", { class: "link", type: "button", text: t("mod.modifica"), onclick: () => apriGruppo(f.n === 1 ? "modello" : "riserva" + f.n) })),
      esito);
  };
  const pausa = el("input", { type: "number", class: "numero", min: "0", max: "86400", step: "1", disabled: dis || null,
    oninput: (e) => { sc.pausa = e.target.value; aggiornaBarraModelli(); } });
  pausa.value = sc.pausa;
  const controllo = el("input", { type: "number", class: "numero", min: "0", max: "1440", step: "1", disabled: dis || null,
    oninput: (e) => { sc.controllo = e.target.value; aggiornaBarraModelli(); } });
  controllo.value = sc.controllo;
  const avviso = !d.canali ? t("mod.nessun_canale") : (!d.notifiche_attive ? t("mod.notifiche_sospese") : null);
  const nota = (chiave) => el("p", { class: "muted small", text: t(chiave) });
  $("#modelli").replaceChildren(
    sezione(t("mod.ordine"), nota("mod.ordine_desc"), ...d.fornitori.map(riga), nota("mod.prova_desc"),
      d.liberi.length
        ? el("div", {}, el("div", { class: "azioni-sis" }, bottone(t("mod.aggiungi"), () => apriGruppo("riserva" + d.liberi[0]), "primary")),
          el("p", { class: "muted small", text: t("mod.aggiungi_desc", d.liberi[0]) }))
        : el("p", { class: "muted small", text: t("mod.pieno", d.max) })),
    sezione(t("mod.comportamento"),
      rigaSis(t("mod.pausa"), pausa), nota("mod.pausa_desc"),
      rigaSis(t("mod.controllo"), controllo), nota("mod.controllo_desc"),
      el("div", { class: "scelte" }, casella(t("mod.notifica"), t("mod.notifica_desc"), sc.notifica,
        (on) => { sc.notifica = on; aggiornaBarraModelli(); }, dis)),
      avviso ? el("p", {}, el("button", { class: "link", type: "button", text: avviso, onclick: () => vaiA("notifiche") })) : null));
  aggiornaBarraModelli();
}

async function salvaModelli() {
  const sc = fornScelte;
  const attivi = Object.fromEntries(Object.entries(sc.attivi).map(([k, v]) => [k, v]));
  await salvaERiavvia($("#mod-salva"), () => api("POST", "fornitori",
    { pausa: sc.pausa, controllo: sc.controllo, notifica: sc.notifica, attivi }), caricaModelli);
}

// ---------- memory
let mem = null, memScelte = null, memModifica = null;

function scelteMemoria(d) {
  return { attiva: d.attiva, auto: d.auto, max: String(d.max), recenti: String(d.recenti), giorni: String(d.giorni), istruzioni: d.istruzioni };
}

async function caricaMemoria(conserva) {
  try { mem = await api("GET", "memoria"); } catch (e) { toast(e.message); return; }
  if (!conserva || !memScelte) memScelte = scelteMemoria(mem);
  disegnaMemoria();
}

function modificheMemoria() {
  if (!mem || !memScelte) return 0;
  const p = scelteMemoria(mem);
  return Object.keys(p).filter((k) => p[k] !== memScelte[k]).length;
}

function aggiornaBarraMemoria() {
  const n = modificheMemoria();
  $("#mem-savebar").hidden = n === 0;
  $("#mem-savebar-testo").textContent = testoModifiche(n);
}

async function azioneMemoria(percorso, corpo, messaggio) {
  try { await api("POST", percorso, corpo); if (messaggio) toast(t(messaggio)); } catch (e) { toast(e.message, 6000); return false; }
  await caricaMemoria(true);
  return true;
}

function disegnaMemoria() {
  const d = mem, sc = memScelte;
  if (!d || !sc) return;
  const dis = !d.configurabile;
  const numero = (chiave, min, max) => {
    const i = el("input", { type: "number", class: "numero", min, max, step: "1", disabled: dis || null,
      oninput: (e) => { sc[chiave] = e.target.value; aggiornaBarraMemoria(); } });
    i.value = sc[chiave];
    return i;
  };
  const sw = (chiave, testo) => {
    const s = interruttore(testo, sc[chiave], (on) => { sc[chiave] = on; aggiornaBarraMemoria(); });
    if (dis) s.querySelector("input").disabled = true;
    return s;
  };
  const istruzioni = el("textarea", { class: "mem-istruzioni", disabled: dis || null, placeholder: t("mem.istruzioni_ph"),
    oninput: (e) => { sc.istruzioni = e.target.value; aggiornaBarraMemoria(); } });
  istruzioni.value = sc.istruzioni;

  // facts
  const testo = el("input", { type: "text", maxlength: "300", placeholder: t("mem.nuovo"), disabled: dis || null });
  const persona = el("input", { type: "text", maxlength: "60", placeholder: t("mem.persona"), class: "mem-persona", disabled: dis || null });
  const aggiungi = el("form", { class: "mem-nuovo", onsubmit: async (ev) => {
    ev.preventDefault();
    if (!testo.value.trim()) return;
    if (await azioneMemoria("memoria/fatto", { testo: testo.value, persona: persona.value }, "mem.salvato")) { testo.value = ""; persona.value = ""; }
  } }, testo, persona, el("button", { class: "btn small primary", type: "submit", text: t("mem.aggiungi"), disabled: dis || null }));
  const filtro = el("input", { type: "search", placeholder: t("mem.cerca"), value: disegnaMemoria.filtro || "",
    oninput: (e) => { disegnaMemoria.filtro = e.target.value; disegnaFatti(); } });
  const lista = el("div", { class: "lista" });
  const disegnaFatti = () => {
    const q = (disegnaMemoria.filtro || "").trim().toLowerCase();
    const fatti = d.fatti.filter((f) => !q || (f.testo + " " + f.persona).toLowerCase().includes(q));
    if (!fatti.length) { lista.replaceChildren(el("p", { class: "vuoto", text: d.fatti.length ? t("mem.nessuno_filtro") : t("mem.nessuno") })); return; }
    lista.replaceChildren(...fatti.map((f) => {
      if (memModifica === f.id) {
        const tx = el("input", { type: "text", maxlength: "300" }), pe = el("input", { type: "text", maxlength: "60", class: "mem-persona", placeholder: t("mem.persona") });
        tx.value = f.testo; pe.value = f.persona;
        setTimeout(() => tx.focus(), 0);
        return el("form", { class: "voce mem-nuovo", onsubmit: async (ev) => {
          ev.preventDefault();
          if (await azioneMemoria("memoria/fatto", { id: f.id, testo: tx.value, persona: pe.value }, "mem.salvato")) { memModifica = null; disegnaMemoria(); }
        } }, tx, pe, el("button", { class: "btn small primary", type: "submit", text: t("mem.salva") }),
        bottone(t("mem.annulla"), () => { memModifica = null; disegnaFatti(); }, "ghost"));
      }
      return el("div", { class: "voce" },
        el("div", { class: "voce-meta" }, f.persona ? el("span", { class: "chip accent", text: f.persona }) : null,
          el("span", { class: "chip", text: t("mem.fonte." + f.fonte) }), f.t ? el("time", { text: quando(f.t) }) : null),
        el("div", { class: "a", text: f.testo }),
        dis ? null : el("div", { class: "azioni" },
          el("button", { class: "link", type: "button", text: t("mem.modifica"), onclick: () => { memModifica = f.id; disegnaFatti(); } }),
          el("button", { class: "link danger", type: "button", text: t("mem.elimina"), onclick: () => {
            if (confirm(t("mem.elimina_conferma", f.testo))) azioneMemoria("memoria/elimina", { id: f.id }, "mem.dimenticato");
          } })));
    }));
  };
  disegnaFatti();

  const voci = d.voci.length ? d.voci.map((v) => {
    const nome = el("input", { type: "text", maxlength: "40", disabled: dis || null, value: v.nome, "aria-label": t("mem.voci") });
    return el("div", { class: "canale" }, el("div", { class: "canale-info" }, nome),
      dis ? null : bottone(t("mem.salva"), () => azioneMemoria("memoria/voce", { id: v.id, nome: nome.value }, "mem.salvato")),
      dis ? null : el("button", { class: "link danger", type: "button", text: t("mem.voce_dimentica"),
        onclick: () => azioneMemoria("memoria/voce", { id: v.id, nome: "" }, "mem.dimenticato") }));
  }) : [el("p", { class: "muted small", text: t("mem.voci_nessuna") })];

  const scambi = d.scambi.length ? d.scambi.map((x) => el("div", { class: "voce" },
    el("div", { class: "voce-meta" }, x.t ? el("time", { text: quando(x.t) }) : null, x.chi ? el("span", { class: "chip accent", text: x.chi }) : null),
    el("div", { class: "q", text: x.domanda }), el("div", { class: "a", text: x.risposta })))
    : [el("p", { class: "muted small", text: t("mem.scambi_nessuno") })];

  $("#memoria").replaceChildren(
    sezione(t("mem.generale"), sw("attiva", t("mem.attiva")), sw("auto", t("mem.auto")), el("p", { class: "muted small", text: t("mem.auto_desc") }),
      rigaSis(t("mem.max"), numero("max", "1", "1000")),
      rigaSis(t("mem.recenti"), numero("recenti", "0", "20")), rigaSis(t("mem.giorni"), numero("giorni", "1", "365")),
      el("p", { class: "muted small", text: t("mem.recenti_desc") }),
      el("label", { class: "mem-etichetta", text: t("mem.istruzioni") }), istruzioni,
      el("p", { class: "muted small", text: t("mem.mai") })),
    sezione(t("mem.fatti", d.fatti.length), aggiungi, filtro, lista,
      d.fatti.length && !dis ? el("div", { class: "azioni-sis" }, bottone(t("mem.svuota"), () => {
        if (confirm(t("mem.svuota_conferma"))) azioneMemoria("memoria/svuota", { cosa: "fatti" }, "mem.dimenticato");
      }, "danger")) : null),
    sezione(t("mem.voci"), el("p", { class: "muted small", text: t("mem.voci_desc") }), ...voci),
    sezione(t("mem.scambi"), el("p", { class: "muted small", text: t("mem.scambi_desc") }), el("div", { class: "lista" }, ...scambi),
      d.scambi.length && !dis ? el("div", { class: "azioni-sis" }, bottone(t("mem.scambi_svuota"),
        () => azioneMemoria("memoria/svuota", { cosa: "scambi" }, "mem.dimenticato"), "danger")) : null));
  aggiornaBarraMemoria();
}

async function salvaMemoria() {
  const sc = memScelte;
  await salvaERiavvia($("#mem-salva"), () => api("POST", "memoria", sc), () => { memScelte = null; caricaMemoria(); });
}

// ---------- settings
let campi = [], modifiche = {}, configurabile = false, elenchiModelli = {}, gruppoDaAprire = null;

// conserva: keep what was changed and not saved yet (switching tab or language must never lose it)
async function caricaImpostazioni(conserva) {
  const prima = conserva ? { ...modifiche } : {};
  let d;
  const elenco = (n) => api("GET", "modelli?n=" + n).catch((e) => ({ modelli: [], errore: e.message }));
  const principale = elenco(1);
  try { d = await api("GET", "impostazioni"); } catch (e) { toast(e.message); return; }
  campi = d.campi; configurabile = d.configurabile; modifiche = {}; elenchiModelli = {};
  $("#impostazioni-avviso").replaceChildren(...(configurabile ? [] : [el("div", { class: "notice" },
    el("strong", { text: t("imp.sola_lettura") }), t("imp.sola_lettura_desc", d.cartella))]));
  disegnaImpostazioni();
  ripristinaModifiche(prima);
  const riserve = [2, 3, 4, 5].filter((n) => campi.some((c) => c.nome === "LLM_" + n + "_BASE_URL" && c.impostato));
  const elenchi = await Promise.all([principale, ...riserve.map(elenco)]);
  [1, ...riserve].forEach((n, i) => {
    const nome = n === 1 ? "LLM_MODEL" : "LLM_" + n + "_MODEL";
    elenchiModelli[nome] = elenchi[i];
    sceltaModello(elenchi[i], nome);
  });
  ripristinaModifiche(prima);
}

function ripristinaModifiche(prima) {
  for (const [nome, valore] of Object.entries(prima)) {
    if (!campi.some((c) => c.nome === nome)) continue;
    const f = document.getElementById("f-" + nome);
    if (f && valore !== null) {
      if (f.tagName === "SELECT" && ![...f.options].some((o) => o.value === valore)) f.append(el("option", { value: valore, text: valore }));
      f.value = valore;
    }
    segnaModifica(nome, valore);
  }
}

// the model field becomes the list of what the provider offers, with "Other…" to type any name
function sceltaModello(r, nome = "LLM_MODEL") {
  const riga = document.querySelector('[data-campo="' + nome + '"] .campo-edit');
  const c = campi.find((x) => x.nome === nome);
  if (!riga || !c || riga.querySelector(".nota-modelli")) return;
  const elenco = r.modelli || [];
  const nota = el("p", { class: "muted small nota-modelli",
    text: elenco.length ? t("imp.modelli_n", elenco.length) : t("imp.modelli_errore", r.errore || "0") });
  if (!elenco.length || !configurabile) { riga.append(nota); return; }
  const ids = elenco.map((m) => m.id);
  const s = el("select", { id: "f-" + nome, onchange: (e) => {
    if (e.target.value !== "__altro__") { segnaModifica(nome, e.target.value); return; }
    const i = el("input", { id: "f-" + nome, type: "text", spellcheck: "false", placeholder: c.valore,
      oninput: (ev) => segnaModifica(nome, ev.target.value || undefined) });
    segnaModifica(nome, undefined);      // the menu choice no longer counts: what is typed does
    e.target.replaceWith(i);
    i.focus();
  } },
  ids.includes(c.valore) || !c.valore ? [] : [el("option", { value: c.valore, text: c.valore })],
  elenco.map((m) => el("option", { value: m.id, text: m.nome && m.nome !== m.id ? m.nome + " — " + m.id : m.id })),
  el("option", { value: "__altro__", text: t("imp.altro_modello") }));
  const inSospeso = modifiche[nome];          // typed before the list arrived: keep it
  if (typeof inSospeso === "string" && inSospeso && !ids.includes(inSospeso)) s.prepend(el("option", { value: inSospeso, text: inSospeso }));
  s.value = typeof inSospeso === "string" && inSospeso ? inSospeso : c.valore || ids[0];
  riga.querySelector("#f-" + nome).replaceWith(s);
  riga.append(nota);
}

function valorePredefinito(c) {
  if (c.tipo === "select" && c.predefinito) return etichettaOpzione(c, c.predefinito);
  return c.predefinito || c.predefinito_testo || null;
}

function origineChip(c) {
  const p = valorePredefinito(c);
  if (c.origine === "default") {
    // a menu already shows the default it is on: just say so
    const testo = c.tipo === "select" ? t("imp.predefinita") : p ? t("imp.predefinita_valore", p) : t("imp.non_impostata_c");
    return el("span", { class: "chip", text: testo });
  }
  const v = { pagina: ["accent", t("imp.salvata")], env: ["", t("imp.env")] }[c.origine];
  return el("span", {}, el("span", { class: "chip " + v[0], text: v[1] }), p ? " " + t("imp.vale", p) : "");
}

function segnaModifica(nome, valore) {
  const c = campi.find((x) => x.nome === nome);
  const nascosto = c.tipo === "secret" || c.mascherato;
  const iniziale = nascosto ? undefined : c.valore;
  if (valore === undefined || (valore === iniziale && !nascosto)) delete modifiche[nome];
  else modifiche[nome] = valore;
  document.querySelector('[data-campo="' + nome + '"]')?.classList.toggle("modificato", nome in modifiche);
  const n = Object.keys(modifiche).length;
  $("#savebar").hidden = n === 0;
  $("#savebar-testo").textContent = testoModifiche(n);
}

function etichettaOpzione(c, o) {
  const k = "opt." + c.nome + "." + o;
  const v = t(k);
  return v === k ? (o === "" ? t("imp.automatico") : o) : v;
}

function controllo(c) {
  const id = "f-" + c.nome, dis = !configurabile;
  if (c.tipo === "select") {
    const s = el("select", { id, disabled: dis, onchange: (e) => segnaModifica(c.nome, e.target.value) },
      c.opzioni.map((o) => el("option", { value: o, text: etichettaOpzione(c, o) })));
    // empty means "the default": show it, instead of a blank choice
    const mostrato = c.valore === "" && c.predefinito && c.opzioni.includes(c.predefinito) ? c.predefinito : c.valore;
    if (!c.opzioni.includes(mostrato)) s.prepend(el("option", { value: mostrato, text: mostrato || t("imp.non_impostato") }));
    s.value = mostrato;
    return s;
  }
  if (c.tipo === "textarea") {
    const a = el("textarea", { id, disabled: dis, placeholder: t("imp.istruzioni_incluse"), oninput: (e) => segnaModifica(c.nome, e.target.value) });
    a.value = c.valore;
    return a;
  }
  if (c.tipo === "secret" || c.mascherato) {
    return el("input", { id, type: c.tipo === "secret" ? "password" : "text", autocomplete: "new-password", disabled: dis, spellcheck: "false",
      placeholder: c.mascherato ? c.mascherato + t("imp.credenziali") : (c.impostato ? t("imp.segreta") : t("imp.non_impostata")),
      oninput: (e) => segnaModifica(c.nome, e.target.value === "" ? undefined : e.target.value) });
  }
  const i = el("input", { id, type: c.tipo === "number" ? "number" : "text", step: "any", disabled: dis, spellcheck: "false",
    placeholder: c.predefinito ? t("imp.predefinito", c.predefinito) : "", oninput: (e) => segnaModifica(c.nome, e.target.value) });
  i.value = c.valore;
  return i;
}

function disegnaImpostazioni() {
  const gruppi = [];
  for (const c of campi) {
    let g = gruppi.find((x) => x.chiave === c.gruppo);
    if (!g) gruppi.push(g = { chiave: c.gruppo, nome: c.nome_gruppo, campi: [] });
    g.campi.push(c);
  }
  // a fallback model that is not configured stays closed: one click opens it
  const chiuso = (g) => g.chiave.startsWith("riserva") && g.chiave !== gruppoDaAprire && !g.campi.some((c) => c.impostato && c.tipo !== "select");
  $("#impostazioni-form").replaceChildren(...gruppi.map((g) => el("fieldset", { class: "gruppo" + (chiuso(g) ? " chiuso" : ""), id: "gruppo-" + g.chiave },
    chiuso(g) ? el("h3", {}, el("button", { type: "button", class: "apri-gruppo", "aria-expanded": "false",
      onclick: (e) => { const f = e.target.closest("fieldset"); f.classList.remove("chiuso"); e.currentTarget.setAttribute("aria-expanded", "true"); } },
      g.nome, el("span", { class: "muted small", text: " · " + t("imp.gruppo_chiuso") }))) : el("h3", { text: g.nome }),
    g.campi.map((c) => el("div", { class: "campo", "data-campo": c.nome },
      el("div", { class: "campo-info" },
        el("label", { for: "f-" + c.nome, text: c.etichetta }),
        el("p", { class: "muted" }, el("code", { text: c.nome }), c.aiuto ? " · " + c.aiuto : "")),
      el("div", { class: "campo-edit" },
        controllo(c),
        el("div", { class: "campo-azioni" },
          origineChip(c),
          c.origine === "pagina" && configurabile ? el("button", { type: "button", class: "link",
            text: c.base ? t("imp.torna_env") : t("imp.torna_predefinito"), onclick: () => {
              const f = document.getElementById("f-" + c.nome);
              if (f && f.tagName !== "SELECT" && c.tipo !== "secret") { f.value = ""; f.placeholder = c.base ? t("imp.valore_env") : (valorePredefinito(c) || ""); }
              segnaModifica(c.nome, null);
            } }) : null,
          c.tipo === "secret" && c.impostato && configurabile ? el("button", { type: "button", class: "link", text: t("imp.cancella"),
            onclick: () => { document.getElementById("f-" + c.nome).placeholder = t("imp.cancellata"); segnaModifica(c.nome, ""); } }) : null)))))));
  $("#savebar").hidden = true;
  for (const [nome, r] of Object.entries(elenchiModelli)) sceltaModello(r, nome);
  if (gruppoDaAprire) {
    const g = document.getElementById("gruppo-" + gruppoDaAprire);
    gruppoDaAprire = null;
    if (g) setTimeout(() => g.scrollIntoView({ block: "start", behavior: "smooth" }), 50);
  }
}

async function attendiRiavvio(avvioPrima) {
  for (let i = 0; i < 40; i++) {
    await new Promise((ok) => setTimeout(ok, 750));
    try {
      const s = await api("GET", "stato");
      if (s.avvio !== avvioPrima) { stato = s; break; }
    } catch (e) { /* the worker is restarting */ }
  }
  caricaStato();
}

async function salvaERiavvia(bottone, invio, dopo) {
  bottone.disabled = true;
  bottone.textContent = t("btn.verifica");
  const avvioPrima = stato ? stato.avvio : 0;
  try {
    const r = await invio();
    if (!r.riavvio) {
      toast(t("imp.salvate_riavvia"), 5000);
    } else {
      bottone.textContent = t("btn.riavvio");
      await attendiRiavvio(avvioPrima);
      toast(t("imp.applicata"));
    }
    await dopo();
  } catch (e) {
    toast(e.message, 8000);
  } finally {
    bottone.disabled = false;
    bottone.textContent = t("btn.salva");
  }
}

async function salva() {
  await salvaERiavvia($("#salva"), () => api("POST", "impostazioni", { valori: modifiche }), caricaImpostazioni);
}

// ---------- system
function rigaSis(etichetta, ...valore) {
  return el("div", { class: "riga-sis" }, el("span", { class: "muted", text: etichetta }), el("span", { class: "valore" }, ...valore));
}

function rigaVariabile(nome, valore) {
  return el("div", { class: "riga-sis pila" }, el("code", { class: "muted", text: nome }),
    el("span", { class: "valore" }, valore ? el("code", { text: valore }) : el("span", { class: "muted", text: t("sis.non_impostato") })));
}

function sezione(titolo, ...figli) {
  return el("section", { class: "card sezione" }, el("h3", { text: titolo }), ...figli);
}

function copia(testo) {
  if (navigator.clipboard) navigator.clipboard.writeText(testo).then(() => toast(t("sis.copiato")), () => {});
}

function bottone(testo, onclick, classe) {
  return el("button", { class: "btn small" + (classe ? " " + classe : ""), type: "button", text: testo, onclick });
}

async function caricaSistema() {
  let s;
  try { s = await api("GET", "sistema"); } catch (e) { toast(e.message); return; }
  const esitoAgg = el("p", { class: "muted small" });
  const attuale = el("input", { type: "password", autocomplete: "current-password", placeholder: t("sis.attuale") });
  const nuova = el("input", { type: "password", autocomplete: "new-password", placeholder: t("sis.nuova_pw") });
  const ripeti = el("input", { type: "password", autocomplete: "new-password", placeholder: t("sis.ripeti_pw") });
  const infra = s.infrastruttura;

  const controllaAggiornamenti = async () => {
    esitoAgg.textContent = "…";
    try {
      const r = await api("GET", "sistema/aggiornamenti");
      const testo = r.errore ? r.errore : r.nuova ? t("sis.nuova", r.ultima) : r.sconosciuta ? t("sis.sviluppo", r.ultima) : t("sis.aggiornato", r.ultima);
      const link = r.url && (r.nuova || r.sconosciuta) ? el("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", text: t("sis.vedi") }) : null;
      esitoAgg.replaceChildren(testo, link ? " " : "", link || "");
    } catch (e) { esitoAgg.textContent = e.message; }
  };
  const riavvia = async (ev) => {
    if (!confirm(t("sis.riavvia_conferma"))) return;
    const avvioPrima = stato ? stato.avvio : 0;
    ev.target.disabled = true;
    try {
      const r = await api("POST", "sistema/riavvia");
      if (r.riavvio) { await attendiRiavvio(avvioPrima); toast(t("sis.riavviato")); caricaSistema(); } else toast(t("sis.non_riavviabile"), 6000);
    } catch (e) { toast(e.message); } finally { ev.target.disabled = false; }
  };
  const scarta = async () => {
    try { await api("POST", "sistema/scarta-sospese"); toast(t("sis.scartate")); caricaSistema(); caricaStato(); } catch (e) { toast(e.message); }
  };
  const cambiaPw = async (ev) => {
    ev.preventDefault();
    if (nuova.value !== ripeti.value) { toast(t("sis.pw_diverse")); return; }
    try {
      csrf = (await api("POST", "password", { attuale: attuale.value, nuova: nuova.value })).csrf;
      toast(t("sis.pw_cambiata"), 5000);
      caricaSistema();
    } catch (e) { toast(e.message, 6000); }
  };
  const ripristinaPw = async () => {
    if (!attuale.value) { toast(t("sis.pw_serve_attuale"), 5000); attuale.focus(); return; }
    try {
      csrf = (await api("DELETE", "password", { attuale: attuale.value })).csrf;
      toast(t("sis.pw_ripristinata"), 5000);
      caricaSistema();
    } catch (e) { toast(e.message, 6000); }
  };
  const esciOvunque = async () => {
    if (!confirm(t("sis.esci_conferma"))) return;
    try { await api("POST", "sistema/esci-ovunque"); } catch (e) { /* already logged out */ }
    csrf = null;
    mostraLogin();
  };

  $("#sistema").replaceChildren(
    sezione(t("sis.alexa"),
      rigaSis(t("sis.skill_id"), el("code", { text: s.skill_id }), el("button", { class: "link", type: "button", text: t("sis.copia"), onclick: () => copia(s.skill_id) })),
      rigaSis(t("sis.endpoint"), s.endpoint ? el("code", { text: s.endpoint }) : el("span", { class: "muted", text: t("sis.endpoint_mancante") }),
        s.endpoint ? el("button", { class: "link", type: "button", text: t("sis.copia"), onclick: () => copia(s.endpoint) }) : null),
      rigaSis(t("sis.lingua"), s.lingua_scelta === "auto" ? t("sis.lingua_auto") : s.lingua === "en" ? "English (en-US)" : "Italiano (it-IT)"),
      el("p", { class: "muted small", text: t("sis.modello_desc") }),
      el("div", { class: "azioni-sis" }, s.modelli_skill.map((l) =>
        bottone(t("sis.scarica", l), () => scarica("sistema/modello-skill/" + l),
          s.lingua_scelta === "auto" || l.startsWith(s.lingua) ? "primary" : "")))),
    sezione(t("sis.servizio"),
      rigaSis(t("sis.versione"), "v" + s.versione.replace(/^v/, "")),
      rigaSis(t("sis.attivo_da"), durataLeggibile(Date.now() / 1000 - s.avvio)),
      el("div", { class: "azioni-sis" },
        bottone(t("sis.aggiornamenti"), controllaAggiornamenti),
        bottone(t("sis.riavvia"), riavvia),
        s.in_sospeso ? bottone(t("sis.scarta") + " (" + s.in_sospeso + ")", scarta) : null),
      esitoAgg),
    sezione(t("sis.sicurezza"),
      el("p", { class: "muted small", text: s.password_da_pagina ? t("sis.pw_da_pagina") : t("sis.pw_da_env") }),
      el("form", { class: "form-pw", onsubmit: cambiaPw },
        el("strong", { text: t("sis.password") }), attuale, nuova, ripeti,
        el("div", { class: "azioni-sis" },
          el("button", { class: "btn small primary", type: "submit", text: t("sis.cambia") }),
          s.password_da_pagina ? bottone(t("sis.pw_ripristina"), ripristinaPw) : null)),
      el("div", { class: "azioni-sis" }, bottone(t("sis.esci_ovunque"), esciOvunque, "danger"))),
    sezione(t("sis.backup"),
      el("p", { class: "muted small", text: t("sis.backup_desc") }),
      el("div", { class: "azioni-sis" },
        bottone(t("sis.esporta"), () => scarica("impostazioni/esporta")),
        s.dati_persistenti ? bottone(t("sis.importa"), () => $("#importa-file").click()) : null)),
    sezione(t("sis.rete"),
      el("p", { class: "muted small", text: t("sis.rete_desc") }),
      ...["PUBLIC_HOST", "BRIDGE_BIND", "BRIDGE_PORT", "ADMIN_PUBLIC", "BRIDGE_VERSION", "COMPOSE_PROFILES"].map((k) => rigaVariabile(k, infra[k])),
      el("p", { class: "muted small", text: s.pubblico ? t("sis.pubblico_on") : t("sis.pubblico_off") })),
  );
}

async function importa(ev) {
  const file = ev.target.files[0];
  ev.target.value = "";
  if (!file) return;
  let valori = null;
  try {
    const d = JSON.parse(await file.text());
    if (d && d.app === "alexa-ai-bridge" && d.impostazioni && typeof d.impostazioni === "object" && !Array.isArray(d.impostazioni)) valori = d.impostazioni;
  } catch (e) { valori = null; }
  if (!valori) { toast(t("sis.importa_errore"), 6000); return; }
  // a backup never holds keys: an address whose key is missing is left out, to be set again with its key
  const coppie = { LLM_BASE_URL: "LLM_API_KEY", HA_URL: "HA_TOKEN", BRAVE_URL: "BRAVE_API_KEY", TAVILY_URL: "TAVILY_API_KEY" };
  const saltati = Object.keys(coppie).filter((u) => u in valori && !(coppie[u] in valori));
  saltati.forEach((u) => delete valori[u]);
  if (!Object.keys(valori).length) { toast(t("sis.importa_solo_url", saltati.join(", ")), 9000); return; }
  if (!confirm(t("sis.importa_conferma", Object.keys(valori).length))) return;
  const avvioPrima = stato ? stato.avvio : 0;
  try {
    const r = await api("POST", "impostazioni", { valori });
    if (r.riavvio) await attendiRiavvio(avvioPrima);
    campi = null;
    toast((r.riavvio ? t("sis.importate") : t("imp.salvate_riavvia")) + (saltati.length ? " " + t("sis.importa_saltati", saltati.join(", ")) : ""), 9000);
  } catch (e) { toast(e.message, 8000); }
}

// ---------- log
async function caricaRegistro() {
  let voci;
  try { voci = (await api("GET", "registro")).voci; } catch (e) { return; }
  const solo = $("#livello").value;
  voci = voci.filter((v) => !solo || v.livello !== "INFO");
  $("#registro").replaceChildren(...(voci.length ? voci.map((v) => el("div", { class: "riga " + v.livello },
    el("span", { text: quando(v.t) }), el("span", { text: v.livello }), el("span", { class: "testo", text: v.testo })))
    : [el("p", { class: "vuoto", text: t("reg.vuoto") })]));
}

// ---------- start
function avvia() {
  $("#login").hidden = true;
  $("#shell").hidden = false;
  caricaStato();
  clearInterval(timerStato);
  timerStato = setInterval(() => { if (!document.hidden) caricaStato(); }, 10000);
  vaiA(location.hash.slice(1) || "panoramica");
}

document.addEventListener("DOMContentLoaded", async () => {
  traduciPagina();
  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => cambiaLingua(b.dataset.lang)));
  $("#login-form").addEventListener("submit", entra);
  document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => vaiA(b.dataset.tab)));
  window.addEventListener("hashchange", () => vaiA(location.hash.slice(1)));
  $("#esci").addEventListener("click", async () => { try { await api("POST", "logout"); } catch (e) { /* ignore */ } csrf = null; mostraLogin(); });
  document.querySelectorAll(".check").forEach((b) => b.querySelector("button").addEventListener("click", () => prova(b)));
  $("#filtro").addEventListener("input", disegnaStorico);
  $("#filtro-origine").addEventListener("change", disegnaStorico);
  $("#aggiorna-storico").addEventListener("click", caricaStorico);
  $("#svuota-storico").addEventListener("click", async () => {
    if (!confirm(t("conv.svuota_conferma"))) return;
    try { await api("DELETE", "storico"); caricaStorico(); caricaStato(); } catch (e) { toast(e.message); }
  });
  $("#chat-form").addEventListener("submit", invia);
  $("#nuova-chat").addEventListener("click", nuovaChat);
  $("#casa-filtro").addEventListener("input", disegnaCasa);
  $("#casa-vista").addEventListener("change", disegnaCasa);
  $("#casa-aggiorna").addEventListener("click", caricaCasa);
  $("#casa-annulla").addEventListener("click", () => { casaGruppi = new Set(casa.gruppi || []); casaVietate = new Set(casa.vietate || []); disegnaCasa(); });
  $("#casa-salva").addEventListener("click", salvaCasa);
  $("#auto-filtro").addEventListener("input", disegnaAutomazioni);
  $("#notif-salva").addEventListener("click", salvaNotifiche);
  $("#notif-annulla").addEventListener("click", () => { notifScelte = scelteDa(notif); disegnaNotifiche(); });
  $("#mod-salva").addEventListener("click", salvaModelli);
  $("#mod-annulla").addEventListener("click", () => { fornScelte = scelteFornitori(fornDati); disegnaModelli(); });
  $("#mem-salva").addEventListener("click", salvaMemoria);
  $("#mem-annulla").addEventListener("click", () => { memScelte = scelteMemoria(mem); disegnaMemoria(); });
  $("#auto-aggiorna").addEventListener("click", caricaAutomazioni);
  $("#salva").addEventListener("click", salva);
  $("#annulla").addEventListener("click", () => { modifiche = {}; disegnaImpostazioni(); });
  $("#livello").addEventListener("change", caricaRegistro);
  $("#importa-file").addEventListener("change", importa);
  window.addEventListener("beforeunload", (e) => { if (Object.keys(modifiche).length || modificheCasa() || modificheNotifiche() || modificheModelli() || modificheMemoria()) e.preventDefault(); });
  try {
    const s = await api("GET", "sessione");
    if (s.autenticato) { csrf = s.csrf; avvia(); } else mostraLogin();
  } catch (e) { mostraLogin(); }
});
