"""The admin page in a real browser (headless Chrome): every tab renders, with no JavaScript error and no secret in the
page. Skipped when no Chrome/Chromium is installed (CI has one)."""
import os, re, shutil, socket, subprocess, sys, time, urllib.request
import pytest

CANDIDATI = [os.environ.get("CHROME", ""), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
CHROME = next((c for c in CANDIDATI if c and (shutil.which(c) or os.path.exists(c))), None)
if not CHROME and os.environ.get("REQUIRE_BROWSER"):      # CI sets it: a missing browser must fail, not skip
    raise RuntimeError("REQUIRE_BROWSER is set but no Chrome or Chromium was found")
pytestmark = pytest.mark.skipif(not CHROME, reason="no Chrome or Chromium installed")


@pytest.fixture(scope="module")
def url(tmp_path_factory):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    server = os.path.join(os.path.dirname(__file__), "ui_server.py")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LLM_", "HA_", "ADMIN_", "SKILL_", "HOME_", "WEB_"))}
    p = subprocess.Popen([sys.executable, server, str(porta), str(tmp_path_factory.mktemp("dati"))], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % porta
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/admin/api/sessione", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield base
    p.terminate()
    p.wait(10)


def apri(url, tab, lingua="it-IT"):
    # the page picks its language from the browser's: Italian unless asked otherwise
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--enable-logging=stderr",
                        "--v=0", "--window-size=1280,900", "--virtual-time-budget=6000", "--lang=" + lingua,
                        "--accept-lang=" + lingua, "--dump-dom", "%s/admin#%s" % (url, tab)], capture_output=True, text=True, timeout=90)
    errori = [r for r in r.stderr.splitlines() if "CONSOLE" in r and re.search(r"Uncaught|Error", r)]
    assert not errori, errori
    return r.stdout


def visibile(dom, id_):
    tag = re.search(r'<[^>]+id="%s"[^>]*>' % id_, dom)
    return bool(tag) and " hidden" not in tag.group(0)


def test_overview(url):
    dom = apri(url, "panoramica")
    assert visibile(dom, "shell") and not visibile(dom, "login") and visibile(dom, "tab-panoramica")
    assert len(re.findall(r'class="card(?: cliccabile)?"', dom)) == 4 and dom.count('class="stat"') == 5
    assert "gpt-5-mini" in dom and "v1.0.0" in dom and "Attivo da 2 giorni" in dom


def test_conversations(url):
    dom = apri(url, "conversazioni")
    assert visibile(dom, "tab-conversazioni") and dom.count('class="voce"') == 8
    assert "come si cucina il risotto alla milanese" in dom and "light.turn_on light.studio" in dom
    assert "consegnata con" in dom          # the 9.8 s answer went through "allora?"


def test_settings_without_secrets(url):
    dom = apri(url, "impostazioni")
    assert visibile(dom, "tab-impostazioni") and 'data-campo="LLM_MODEL"' in dom and 'data-campo="HA_VIETATO"' in dom
    assert dom.count('class="gruppo"') == 11 and dom.count('class="gruppo chiuso"') == 3 and "Lingua dell'assistente" in dom and 'data-campo="NOTIFY_WEBHOOK_URL"' in dom
    assert "demo-secret-key" not in dom and "demo-secret-token" not in dom and "demo-password-123" not in dom
    assert "demo-secret-telegram" not in dom and "demo-secret-cliproxy" not in dom
    assert 'id="f-LLM_2_MODEL"' in dom and "gemini-3-flash" in dom and "Modello 3 (di riserva)" in dom


@pytest.mark.parametrize("scheda", ["panoramica", "conversazioni", "chat", "modelli", "casa", "automazioni", "notifiche", "memoria",
                                    "impostazioni", "sistema", "registro"])
def test_phone_width_has_no_sideways_scroll(url, scheda):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--window-size=500,900",
                        "--virtual-time-budget=8000", "--dump-dom", "%s/demo-frame/360/%s" % (url, scheda)],
                       capture_output=True, text=True, timeout=90)
    assert "OVERFLOW=0" in r.stdout, re.findall(r"OVERFLOW=-?\d+", r.stdout) or r.stdout[-500:]


def test_chat_and_log(url):
    dom = apri(url, "chat")
    assert visibile(dom, "tab-chat") and 'id="chat-form"' in dom
    dom = apri(url, "registro")
    assert visibile(dom, "tab-registro") and "demo: admin page ready" in dom


def test_home_tab(url):
    dom = apri(url, "casa")
    assert visibile(dom, "tab-casa") and len(re.findall(r'class="entita(?: bloccata)?"', dom)) == 13   # automations included
    for testo in ("Mai comandabile (tipo di entità)", "Bloccata dalle regole di sicurezza incluse", "Vietata da te", "Comandabile",
                  "Chiedi sempre un sì", "light.studio"):
        assert testo in dom, testo


def test_automations_tab(url):
    dom = apri(url, "automazioni")
    assert visibile(dom, "tab-automazioni") and len(re.findall(r'class="entita(?: bloccata)?"', dom)) == 3
    for testo in ("Automazioni a voce attive", "Luce cucina al mattino", "alle 07:05, solo lun, mer, ven", "Disattivata",
                  "Non più in Home Assistant", "Togli dall'elenco", "Il token può creare ed eliminare automazioni",
                  "automation.alexa_tapparelle_al_tramonto", "mai eseguita"):
        assert testo in dom, testo
    assert "Irrigazione notte" not in dom and "demo-secret-token" not in dom


def test_notifications_tab(url):
    dom = apri(url, "notifiche")
    assert visibile(dom, "tab-notifiche") and dom.count('class="scelta"') == 8 + 4       # eight events, four notify services
    # the phone apps in sight, the other services folded (none of them is chosen)
    piega = re.search(r'<details class="altri-servizi"[^>]*>', dom)
    assert piega and "open" not in piega.group(0) and "Altri servizi notify (2)" in dom
    assert dom.index("notify.mobile_app_tablet") < piega.start() < dom.index("notify.persistent_notification")
    for testo in ("Quando avvisarti", "Tentativi bloccati", "notify.mobile_app_tablet", "chat 123456", "Non configurato",
                  "Invia una notifica di prova", "Telegram · HTTP 401", "Eseguito dopo il tuo sì"):
        assert testo in dom, testo
    assert "demo-secret-telegram" not in dom and "demo-secret-token" not in dom


def test_models_tab(url):
    dom = apri(url, "modelli")
    assert visibile(dom, "tab-modelli") and dom.count('class="canale"') == 2
    for testo in ("Principale · claude-haiku-5-5", "Riserva · 2 · gpt-5-mini", "Non disponibile: HTTP 429: Quota exhausted",
                  "Sta rispondendo", "cliproxyapi:8317", "Aggiungi un modello di riserva", "Avvisami quando un modello"):
        assert testo in dom, testo
    assert "demo-secret" not in dom
    dom = apri(url, "panoramica")
    assert "Sta rispondendo il modello di riserva 2" in dom and "gpt-5-mini" in dom


def test_memory_tab(url):
    dom = apri(url, "memoria")
    assert visibile(dom, "tab-memoria") and dom.count('class="voce"') == 4 + 1      # four facts, one exchange
    for testo in ("Cosa sa (4)", "prende il caffè senza zucchero", "Anna è la sorella di Luca", "imparato", "a voce",
                  "Voci riconosciute", 'value="Luca"', "che tempo fa domani", "Impara da solo"):
        assert testo in dom, testo


def test_system_tab(url):
    dom = apri(url, "sistema")
    assert visibile(dom, "tab-sistema") and "amzn1.ask.skill.demo" in dom and "https://alexa.example.org/alexa" in dom
    assert "Scarica it-IT" in dom and "Scarica en-US" in dom and "Cambia la password del pannello" in dom
    assert "demo-password-123" not in dom


@pytest.mark.parametrize("scheda, testi", [
    ("panoramica", ("Overview", "Up for 2 days", "Checks", "In the history")),
    ("casa", ("Never controllable (entity type)", "Forbidden by you", "Always ask for a yes")),
    ("automazioni", ("Automations by voice are on", "No longer in Home Assistant", "never run", "Delete")),
    ("notifiche", ("When to tell you", "Blocked attempts", "Home Assistant app", "Send a test notification", "Models not answering")),
    ("modelli", ("In the order they are tried", "Fallback · 2", "Answering", "Add a fallback model")),
    ("memoria", ("What it knows (4)", "Recognised voices", "Learn by itself", "by voice")),
    ("impostazioni", ("Assistant language", "API key", "Admin page")),
    ("sistema", ("Download en-US", "Change the admin page password", "Network and publishing")),
])
def test_english(url, scheda, testi):
    dom = apri(url, scheda, "en-US")
    assert '<html lang="en"' in dom
    for testo in testi:
        assert testo in dom, testo
    assert "Panoramica" not in dom
