"use strict";
// Admin page of Alexa AI Bridge. No framework, no external resources. The DOM is built with textContent only.

const $ = (sel) => document.querySelector(sel);
let csrf = null;
let stato = null;
let timerStato = null;
let timerRegistro = null;

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

function toast(testo, ms = 3000) {
  const t = $("#toast");
  t.textContent = testo;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, ms);
}

async function api(metodo, percorso, corpo) {
  const opzioni = { method: metodo, headers: {}, credentials: "same-origin" };
  if (metodo !== "GET") opzioni.headers["X-CSRF"] = csrf || "";
  if (corpo !== undefined) {
    opzioni.headers["Content-Type"] = "application/json";
    opzioni.body = JSON.stringify(corpo);
  }
  const r = await fetch("/admin/api/" + percorso, opzioni);
  let dati = {};
  try { dati = await r.json(); } catch (e) { /* empty body */ }
  if (r.status === 401 && percorso !== "login") { mostraLogin(); throw new Error("Sessione scaduta"); }
  if (!r.ok) throw new Error(dati.errore || ("Errore " + r.status));
  return dati;
}

function quando(t) {
  const d = new Date(t * 1000);
  const oggi = new Date();
  const ora = d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return d.toDateString() === oggi.toDateString() ? ora : d.toLocaleDateString("it-IT", { day: "numeric", month: "short" }) + " " + ora;
}

function durataLeggibile(s) {
  if (s < 60) return Math.round(s) + " s";
  if (s < 3600) return Math.round(s / 60) + " min";
  if (s < 86400) return Math.round(s / 3600) + " h";
  return Math.round(s / 86400) + " giorni";
}

// ---------- login
function mostraLogin() {
  $("#shell").hidden = true;
  $("#login").hidden = false;
  clearInterval(timerStato); clearInterval(timerRegistro);
  setTimeout(() => $("#password").focus(), 50);
}

async function entra(ev) {
  ev.preventDefault();
  const bottone = ev.target.querySelector("button");
  bottone.disabled = true;
  $("#login-errore").textContent = "";
  try {
    const d = await api("POST", "login", { password: $("#password").value });
    csrf = d.csrf;
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
  if (tab === "registro") { caricaRegistro(); timerRegistro = setInterval(() => { if ($("#auto-registro").checked) caricaRegistro(); }, 5000); }
  if (tab === "chat") setTimeout(() => $("#chat-testo").focus(), 50);
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
  const webTesto = { native: "Nativa del modello", searxng: "SearXNG", brave: "Brave Search", tavily: "Tavily" }[w.backend] || "Spenta";
  $("#stato-cards").replaceChildren(
    card("Servizio", stato.avvisi ? "warn" : "ok", "Attivo da " + durataLeggibile(stato.ora - stato.avvio),
      stato.in_sospeso ? stato.in_sospeso + " risposte in sospeso" : (stato.avvisi ? stato.avvisi + " avvisi nel registro" : "Nessun avviso")),
    card("Modello", m.chiave || !m.url.startsWith("https") ? "ok" : "warn", m.nome, (m.api === "anthropic" ? "Anthropic" : "OpenAI-compatibile") + " · " + m.url),
    card("Ricerca web", w.attiva ? "ok" : (w.backend ? "warn" : ""), webTesto, w.backend && !w.attiva ? "Rifiutata dal modello" : (w.attiva ? "Disponibile" : "Le domande sull'attualità non avranno dati freschi")),
    card("Home Assistant", c.attiva ? "ok" : (c.configurata ? "warn" : ""), c.attiva ? "Collegato" : (c.configurata ? "Strumenti non accettati dal modello" : "Non configurato"), c.url || "Imposta HA_URL e HA_TOKEN"),
  );
  const a = stato.adattamenti, note = [];
  if (!a.strumenti) note.push("il modello non accetta strumenti: niente comandi alla casa né ricerca web lato servizio");
  if (!a.web_nativo) note.push("la ricerca web nativa è stata rifiutata dall'endpoint");
  if (a.max_completion) note.push("l'endpoint usa max_completion_tokens");
  if (!a.thinking) note.push("l'endpoint non accetta il parametro thinking");
  $("#adattamenti").replaceChildren(...(note.length ? [el("div", { class: "notice" }, el("strong", { text: "Adattamenti automatici: " }), note.join("; ") + ".")] : []));
  const s = stato.statistiche;
  const stat = (n, l) => el("div", { class: "stat" }, el("b", { text: n }), el("span", { text: l }));
  $("#stats").replaceChildren(
    stat(s.domande, stato.storico_attivo ? "domande" : "domande (storico spento)"),
    stat(s.durata_media === null ? "–" : s.durata_media + " s", "tempo medio"),
    stat(s.lente, "oltre " + stato.attesa + " s (\"ci sto pensando\")"),
    stat(s.errori, "errori"),
    stat(s.azioni, "azioni sulla casa"),
  );
}

async function prova(box) {
  const bottone = box.querySelector("button"), esito = box.querySelector(".esito");
  bottone.disabled = true;
  bottone.textContent = "In corso…";
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
    bottone.textContent = "Prova";
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
    $("#storico").replaceChildren(el("p", { class: "vuoto", text: storico.length ? "Nessuna conversazione corrisponde al filtro." : "Ancora nessuna domanda. Prova a parlare con Alexa o usa la chat di prova." }));
    return;
  }
  const lenta = stato ? stato.attesa : 6;
  $("#storico").replaceChildren(...voci.map((v) => el("article", { class: "voce" },
    el("div", { class: "voce-meta" },
      el("time", { text: quando(v.t) }),
      el("span", { class: "chip " + (v.origine === "chat" ? "accent" : ""), text: v.origine === "chat" ? "Chat di prova" : "Alexa · " + v.utente }),
      el("span", { class: "chip " + (v.errore ? "bad" : v.durata > lenta ? "warn" : "ok"), text: v.durata + " s" }),
      v.durata > lenta && !v.errore ? el("span", { class: "chip warn", text: "consegnata con \"allora?\"" }) : null),
    el("div", { class: "q", text: v.domanda }),
    el("div", { class: "a" + (v.errore ? " err" : ""), text: v.risposta || ("Errore: " + v.errore) }),
    v.azioni.length ? el("div", { class: "azioni" }, v.azioni.map(chipAzione)) : null)));
}

// ---------- test chat
let conversazione = [];

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
  const attesa = aggiungi(el("div", { class: "typing", "aria-label": "Sto pensando" }, el("i"), el("i"), el("i")));
  try {
    const r = await api("POST", "chat", { testo, storia: conversazione, simula: $("#simula").checked });
    attesa.remove();
    if (r.risposta) {
      conversazione = r.storia;
      aggiungi(el("div", { class: "msg bot", text: r.risposta }));
    } else {
      aggiungi(el("div", { class: "msg bot err", text: "Alexa direbbe: \"Non sono riuscito a rispondere.\" (" + r.errore + ")" }));
    }
    aggiungi(el("div", { class: "msg-meta" },
      el("span", { class: "chip " + (r.lenta ? "warn" : "ok"), text: r.durata + " s" }),
      r.lenta ? el("span", { class: "chip warn", text: "su Alexa: \"Ci sto pensando\", poi \"allora?\"" }) : null,
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
  $("#messaggi").replaceChildren(el("p", { class: "vuoto", text: "Nuova conversazione. Il modello non ricorda più le domande precedenti." }));
  $("#chat-testo").focus();
}

// ---------- settings
let campi = [], modifiche = {}, configurabile = false;

async function caricaImpostazioni() {
  let d;
  try { d = await api("GET", "impostazioni"); } catch (e) { toast(e.message); return; }
  campi = d.campi; configurabile = d.configurabile; modifiche = {};
  $("#impostazioni-avviso").replaceChildren(...(configurabile ? [] : [el("div", { class: "notice" },
    el("strong", { text: "Sola lettura. " }),
    "Per salvare dalla pagina serve una cartella dati scrivibile (" + d.cartella + "): con il compose incluso è già montata; altrimenti vedi docs/admin.md.")]));
  disegnaImpostazioni();
}

function origineChip(c) {
  const t = { pagina: ["accent", "salvata qui"], env: ["", "da .env"], default: ["", "predefinita"] }[c.origine];
  return el("span", { class: "chip " + t[0], text: t[1] });
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
  $("#savebar-testo").textContent = n === 1 ? "1 modifica non salvata" : n + " modifiche non salvate";
}

function controllo(c) {
  const id = "f-" + c.nome;
  const dis = !configurabile;
  if (c.tipo === "select") {
    const s = el("select", { id, disabled: dis, onchange: (e) => segnaModifica(c.nome, e.target.value) },
      c.opzioni.map((o) => el("option", { value: o, text: o === "" ? "(automatico)" : o })));
    if (!c.opzioni.includes(c.valore)) s.prepend(el("option", { value: c.valore, text: c.valore || "(non impostato)" }));
    s.value = c.valore;
    return s;
  }
  if (c.tipo === "textarea") {
    const t = el("textarea", { id, disabled: dis, placeholder: "vuoto: le istruzioni incluse", oninput: (e) => segnaModifica(c.nome, e.target.value) });
    t.value = c.valore;
    return t;
  }
  if (c.tipo === "secret") {
    return el("input", { id, type: "password", autocomplete: "new-password", disabled: dis,
      placeholder: c.impostato ? "•••••••• impostata: scrivi per cambiarla" : "non impostata",
      oninput: (e) => segnaModifica(c.nome, e.target.value === "" ? undefined : e.target.value) });
  }
  if (c.mascherato) {
    return el("input", { id, type: "text", disabled: dis, spellcheck: "false", autocomplete: "off",
      placeholder: c.mascherato + "  (contiene credenziali: scrivi per cambiarlo)",
      oninput: (e) => segnaModifica(c.nome, e.target.value === "" ? undefined : e.target.value) });
  }
  const i = el("input", { id, type: c.tipo === "number" ? "number" : "text", step: "any", disabled: dis, spellcheck: "false",
    placeholder: c.predefinito ? "predefinito: " + c.predefinito : "",
    oninput: (e) => segnaModifica(c.nome, e.target.value) });
  i.value = c.valore;
  return i;
}

function disegnaImpostazioni() {
  const gruppi = [];
  for (const c of campi) {
    let g = gruppi.find((x) => x.nome === c.gruppo);
    if (!g) gruppi.push(g = { nome: c.gruppo, campi: [] });
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
          c.origine === "pagina" && configurabile ? el("button", { type: "button", class: "link", text: "Torna al valore del .env",
            onclick: () => segnaModifica(c.nome, null) }) : null,
          c.tipo === "secret" && c.impostato && configurabile ? el("button", { type: "button", class: "link", text: "Cancella",
            onclick: () => { document.getElementById("f-" + c.nome).placeholder = "verrà cancellata al salvataggio"; segnaModifica(c.nome, ""); } }) : null)))))));
  $("#savebar").hidden = true;
}

async function salva() {
  const bottone = $("#salva");
  bottone.disabled = true;
  bottone.textContent = "Verifica…";
  const avvioPrima = stato ? stato.avvio : 0;
  try {
    const r = await api("POST", "impostazioni", { valori: modifiche });
    if (!r.riavvio) {
      toast("Salvate. Riavvia il servizio per applicarle.", 5000);
    } else {
      bottone.textContent = "Riavvio…";
      for (let i = 0; i < 40; i++) {
        await new Promise((ok) => setTimeout(ok, 750));
        try {
          const s = await api("GET", "stato");
          if (s.avvio !== avvioPrima) { stato = s; break; }
        } catch (e) { /* the worker is restarting */ }
      }
      toast("Configurazione applicata.");
      caricaStato();
    }
    await caricaImpostazioni();
  } catch (e) {
    toast(e.message, 8000);
  } finally {
    bottone.disabled = false;
    bottone.textContent = "Salva e riavvia";
  }
}

// ---------- log
async function caricaRegistro() {
  let voci;
  try { voci = (await api("GET", "registro")).voci; } catch (e) { return; }
  const solo = $("#livello").value;
  voci = voci.filter((v) => !solo || v.livello !== "INFO");
  $("#registro").replaceChildren(...(voci.length ? voci.map((v) => el("div", { class: "riga " + v.livello },
    el("span", { text: quando(v.t) }), el("span", { text: v.livello }), el("span", { class: "testo", text: v.testo })))
    : [el("p", { class: "vuoto", text: "Nessuna riga." })]));
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
  $("#login-form").addEventListener("submit", entra);
  document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => vaiA(b.dataset.tab)));
  window.addEventListener("hashchange", () => vaiA(location.hash.slice(1)));
  $("#esci").addEventListener("click", async () => { try { await api("POST", "logout"); } catch (e) { /* ignore */ } csrf = null; mostraLogin(); });
  document.querySelectorAll(".check").forEach((b) => b.querySelector("button").addEventListener("click", () => prova(b)));
  $("#filtro").addEventListener("input", disegnaStorico);
  $("#filtro-origine").addEventListener("change", disegnaStorico);
  $("#aggiorna-storico").addEventListener("click", caricaStorico);
  $("#svuota-storico").addEventListener("click", async () => {
    if (!confirm("Svuotare lo storico delle conversazioni?")) return;
    try { await api("DELETE", "storico"); caricaStorico(); caricaStato(); } catch (e) { toast(e.message); }
  });
  $("#chat-form").addEventListener("submit", invia);
  $("#nuova-chat").addEventListener("click", nuovaChat);
  $("#salva").addEventListener("click", salva);
  $("#annulla").addEventListener("click", () => { modifiche = {}; disegnaImpostazioni(); });
  $("#livello").addEventListener("change", caricaRegistro);
  window.addEventListener("beforeunload", (e) => { if (Object.keys(modifiche).length) e.preventDefault(); });
  try {
    const s = await api("GET", "sessione");
    if (s.autenticato) { csrf = s.csrf; avvia(); } else mostraLogin();
  } catch (e) { mostraLogin(); }
});
