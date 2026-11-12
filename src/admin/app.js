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
    "pan.dallavvio": "Dall'ultimo avvio", "pan.prove": "Prove",
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
    "conv.nota": "Tenute solo in memoria: si azzerano al riavvio. Gli utenti sono anonimizzati.",
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
    "imp.salvata": "salvata qui", "imp.env": "da .env", "imp.predefinita": "predefinita", "imp.torna_env": "Torna al valore del .env",
    "imp.cancella": "Cancella", "imp.cancellata": "verrà cancellata al salvataggio", "imp.segreta": "•••••••• impostata: scrivi per cambiarla",
    "imp.non_impostata": "non impostata", "imp.credenziali": "  (contiene credenziali: scrivi per cambiarlo)",
    "imp.predefinito": "predefinito: %s", "imp.automatico": "(automatico)", "imp.non_impostato": "(non impostato)",
    "imp.istruzioni_incluse": "vuoto: le istruzioni incluse",
    "imp.applicata": "Configurazione applicata.", "imp.salvate_riavvia": "Salvate. Riavvia il servizio per applicarle.",
    "sis.alexa": "Alexa", "sis.skill_id": "Skill ID", "sis.endpoint": "Endpoint da inserire nella console Alexa",
    "sis.endpoint_mancante": "Imposta PUBLIC_HOST nel .env per vederlo qui.", "sis.lingua": "Lingua dell'assistente",
    "sis.modello_desc": "Incollalo nel JSON Editor della console Alexa. Usa quello della stessa lingua dell'assistente e crea la skill in quella lingua.",
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
    "sis.esci_ovunque": "Esci da tutti i dispositivi", "sis.esci_conferma": "Chiudere tutte le sessioni, compresa questa?",
    "sis.backup": "Backup delle impostazioni", "sis.backup_desc": "Esporta tutte le impostazioni senza chiavi, token e indirizzi con credenziali; importandole vengono controllate come un salvataggio normale.",
    "sis.esporta": "Esporta", "sis.importa": "Importa", "sis.importa_conferma": "Importare %s impostazioni e riavviare?",
    "sis.importa_errore": "Il file non è un backup valido.", "sis.importate": "Impostazioni importate.",
    "sis.rete": "Rete e pubblicazione", "sis.rete_desc": "Queste si cambiano nel .env sul server, poi docker compose up -d: decidono dove il servizio è raggiungibile.",
    "sis.pubblico_on": "Il pannello può essere raggiunto attraverso il reverse proxy.", "sis.pubblico_off": "Il pannello non è pubblicato attraverso il reverse proxy.",
    "sis.non_impostato": "non impostato",
    "reg.tutti": "Tutti i livelli", "reg.avvisi": "Solo avvisi ed errori", "reg.auto": "Aggiornamento automatico", "reg.vuoto": "Nessuna riga.",
    "err.sessione": "Sessione scaduta",
  },
  en: {
    "login.sub": "Admin page", "login.password": "Password", "login.entra": "Log in",
    "tab.panoramica": "Overview", "tab.conversazioni": "Conversations", "tab.chat": "Test chat", "tab.casa": "Home",
    "tab.impostazioni": "Settings", "tab.sistema": "System", "tab.registro": "Log", "esci": "Log out",
    "btn.prova": "Run", "btn.in_corso": "Running…", "btn.aggiorna": "Refresh", "btn.svuota": "Clear", "btn.annulla": "Cancel",
    "btn.salva": "Save and restart", "btn.verifica": "Checking…", "btn.riavvio": "Restarting…",
    "pan.dallavvio": "Since the last start", "pan.prove": "Checks",
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
    "conv.nota": "Kept in memory only: cleared at every restart. Users are anonymised.",
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
    "imp.salvata": "saved here", "imp.env": "from .env", "imp.predefinita": "default", "imp.torna_env": "Back to the .env value",
    "imp.cancella": "Clear", "imp.cancellata": "will be cleared on save", "imp.segreta": "•••••••• set: type to change it",
    "imp.non_impostata": "not set", "imp.credenziali": "  (contains credentials: type to change it)",
    "imp.predefinito": "default: %s", "imp.automatico": "(automatic)", "imp.non_impostato": "(not set)",
    "imp.istruzioni_incluse": "empty: the built-in instructions",
    "imp.applicata": "Settings applied.", "imp.salvate_riavvia": "Saved. Restart the service to apply them.",
    "sis.alexa": "Alexa", "sis.skill_id": "Skill ID", "sis.endpoint": "Endpoint to enter in the Alexa console",
    "sis.endpoint_mancante": "Set PUBLIC_HOST in .env to see it here.", "sis.lingua": "Assistant language",
    "sis.modello_desc": "Paste it in the JSON Editor of the Alexa console. Use the one in the assistant's language and create the skill in that language.",
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
    "sis.esci_ovunque": "Log out everywhere", "sis.esci_conferma": "Log out every session, this one included?",
    "sis.backup": "Settings backup", "sis.backup_desc": "Exports every setting except keys, tokens and addresses with credentials; importing checks them like a normal save.",
    "sis.esporta": "Export", "sis.importa": "Import", "sis.importa_conferma": "Import %s settings and restart?",
    "sis.importa_errore": "The file is not a valid backup.", "sis.importate": "Settings imported.",
    "sis.rete": "Network and publishing", "sis.rete_desc": "These are changed in .env on the server, then docker compose up -d: they decide where the service can be reached.",
    "sis.pubblico_on": "The page can be reached through the reverse proxy.", "sis.pubblico_off": "The page is not published through the reverse proxy.",
    "sis.non_impostato": "not set",
    "reg.tutti": "All levels", "reg.avvisi": "Warnings and errors only", "reg.auto": "Auto refresh", "reg.vuoto": "No lines.",
    "err.sessione": "Session expired",
  },
};

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
  const tab = location.hash.slice(1) || "panoramica";
  if (tab === "conversazioni") disegnaStorico();
  if (tab === "impostazioni") caricaImpostazioni();
  if (tab === "casa") disegnaCasa();
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
  if (location.hash !== "#" + tab) history.replaceState(null, "", "#" + tab);
  clearInterval(timerRegistro);
  if (tab === "conversazioni") caricaStorico();
  if (tab === "impostazioni") caricaImpostazioni();
  if (tab === "casa") caricaCasa();
  if (tab === "sistema") caricaSistema();
  if (tab === "registro") { caricaRegistro(); timerRegistro = setInterval(() => { if ($("#auto-registro").checked) caricaRegistro(); }, 5000); }
  if (tab === "chat") {
    if (!conversazione.length && !$("#messaggi").children.length) messaggioVuoto(t("chat.vuoto"));
    setTimeout(() => $("#chat-testo").focus(), 50);
  }
}

// ---------- overview
function card(titolo, livello, valore, sotto) {
  return el("div", { class: "card" },
    el("div", { class: "card-head" }, el("span", { class: "dot " + livello }), titolo),
    el("div", { class: "card-value", text: valore }),
    sotto ? el("div", { class: "card-sub", text: sotto }) : null);
}

async function caricaStato() {
  try { stato = await api("GET", "stato"); } catch (e) { return; }
  $("#versione").textContent = "v" + stato.versione.replace(/^v/, "");
  const m = stato.modello, w = stato.web, c = stato.casa;
  const webTesto = { native: t("web.native"), searxng: "SearXNG", brave: "Brave Search", tavily: "Tavily" }[w.backend] || t("web.spenta");
  $("#stato-cards").replaceChildren(
    card(t("card.servizio"), stato.avvisi ? "warn" : "ok", t("card.attivo_da", durataLeggibile(stato.ora - stato.avvio)),
      stato.in_sospeso ? t("card.sospese", stato.in_sospeso) : (stato.avvisi ? t("card.avvisi", stato.avvisi) : t("card.nessun_avviso"))),
    card(t("card.modello"), m.chiave || !m.url.startsWith("https") ? "ok" : "warn", m.nome, (m.api === "anthropic" ? "Anthropic" : t("card.compatibile")) + " · " + m.url),
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
      el("span", { class: "chip " + (v.origine === "chat" ? "accent" : ""), text: v.origine === "chat" ? t("tab.chat") : "Alexa · " + v.utente }),
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
    const r = await api("POST", "chat", { testo, storia: conversazione, simula: $("#simula").checked });
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
    const etichetta = e.fissa ? el("span", { class: "chip bad", text: t("casa.blocco." + e.blocco) })
      : e.vietataOra ? el("span", { class: "chip bad", text: t("casa.blocco.pagina") })
      : el("span", { class: "chip ok", text: t("casa.comandabile") });
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

// ---------- settings
let campi = [], modifiche = {}, configurabile = false;

async function caricaImpostazioni() {
  let d;
  try { d = await api("GET", "impostazioni"); } catch (e) { toast(e.message); return; }
  campi = d.campi; configurabile = d.configurabile; modifiche = {};
  $("#impostazioni-avviso").replaceChildren(...(configurabile ? [] : [el("div", { class: "notice" },
    el("strong", { text: t("imp.sola_lettura") }), t("imp.sola_lettura_desc", d.cartella))]));
  disegnaImpostazioni();
}

function origineChip(c) {
  const v = { pagina: ["accent", t("imp.salvata")], env: ["", t("imp.env")], default: ["", t("imp.predefinita")] }[c.origine];
  return el("span", { class: "chip " + v[0], text: v[1] });
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

function controllo(c) {
  const id = "f-" + c.nome, dis = !configurabile;
  if (c.tipo === "select") {
    const s = el("select", { id, disabled: dis, onchange: (e) => segnaModifica(c.nome, e.target.value) },
      c.opzioni.map((o) => el("option", { value: o, text: o === "" ? t("imp.automatico") : o })));
    if (!c.opzioni.includes(c.valore)) s.prepend(el("option", { value: c.valore, text: c.valore || t("imp.non_impostato") }));
    s.value = c.valore;
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
  $("#impostazioni-form").replaceChildren(...gruppi.map((g) => el("fieldset", { class: "gruppo" },
    el("h3", { text: g.nome }),
    g.campi.map((c) => el("div", { class: "campo", "data-campo": c.nome },
      el("div", { class: "campo-info" },
        el("label", { for: "f-" + c.nome, text: c.etichetta }),
        el("p", { class: "muted" }, el("code", { text: c.nome }), c.aiuto ? " · " + c.aiuto : "")),
      el("div", { class: "campo-edit" },
        controllo(c),
        el("div", { class: "campo-azioni" },
          origineChip(c),
          c.origine === "pagina" && configurabile ? el("button", { type: "button", class: "link", text: t("imp.torna_env"),
            onclick: () => segnaModifica(c.nome, null) }) : null,
          c.tipo === "secret" && c.impostato && configurabile ? el("button", { type: "button", class: "link", text: t("imp.cancella"),
            onclick: () => { document.getElementById("f-" + c.nome).placeholder = t("imp.cancellata"); segnaModifica(c.nome, ""); } }) : null)))))));
  $("#savebar").hidden = true;
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
      rigaSis(t("sis.lingua"), s.lingua === "en" ? "English (en-US)" : "Italiano (it-IT)"),
      el("p", { class: "muted small", text: t("sis.modello_desc") }),
      el("div", { class: "azioni-sis" }, s.modelli_skill.map((l) =>
        bottone(t("sis.scarica", l), () => scarica("sistema/modello-skill/" + l), l.startsWith(s.lingua) ? "primary" : "")))),
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
      ...["PUBLIC_HOST", "BRIDGE_BIND", "ADMIN_PUBLIC", "BRIDGE_VERSION", "COMPOSE_PROFILES"].map((k) => rigaVariabile(k, infra[k])),
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
  if (!confirm(t("sis.importa_conferma", Object.keys(valori).length))) return;
  const avvioPrima = stato ? stato.avvio : 0;
  try {
    const r = await api("POST", "impostazioni", { valori });
    if (r.riavvio) await attendiRiavvio(avvioPrima);
    toast(t("sis.importate"));
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
  $("#salva").addEventListener("click", salva);
  $("#annulla").addEventListener("click", () => { modifiche = {}; disegnaImpostazioni(); });
  $("#livello").addEventListener("change", caricaRegistro);
  $("#importa-file").addEventListener("change", importa);
  window.addEventListener("beforeunload", (e) => { if (Object.keys(modifiche).length || modificheCasa()) e.preventDefault(); });
  try {
    const s = await api("GET", "sessione");
    if (s.autenticato) { csrf = s.csrf; avvia(); } else mostraLogin();
  } catch (e) { mostraLogin(); }
});
