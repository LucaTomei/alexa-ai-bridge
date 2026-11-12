"""The admin page in a real browser (headless Chrome): every tab renders, with no JavaScript error and no secret in the
page. Skipped when no Chrome/Chromium is installed (CI has one)."""
import os, re, shutil, socket, subprocess, sys, time, urllib.request
import pytest

CANDIDATI = [os.environ.get("CHROME", ""), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
CHROME = next((c for c in CANDIDATI if c and (shutil.which(c) or os.path.exists(c))), None)
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


def apri(url, tab, larghezza=1280):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--enable-logging=stderr",
                        "--v=0", "--window-size=%d,900" % larghezza, "--virtual-time-budget=6000", "--dump-dom",
                        "%s/admin#%s" % (url, tab)], capture_output=True, text=True, timeout=90)
    errori = [r for r in r.stderr.splitlines() if "CONSOLE" in r and re.search(r"Uncaught|Error", r)]
    assert not errori, errori
    return r.stdout


def visibile(dom, id_):
    tag = re.search(r'<[^>]+id="%s"[^>]*>' % id_, dom)
    return bool(tag) and " hidden" not in tag.group(0)


def test_overview(url):
    dom = apri(url, "panoramica")
    assert visibile(dom, "shell") and not visibile(dom, "login") and visibile(dom, "tab-panoramica")
    assert dom.count('class="card"') == 4 and dom.count('class="stat"') == 5
    assert "claude-haiku-5-5" in dom and "v1.0.0" in dom and "Attivo da 2 giorni" in dom


def test_conversations(url):
    dom = apri(url, "conversazioni")
    assert visibile(dom, "tab-conversazioni") and dom.count('class="voce"') == 8
    assert "come si cucina il risotto alla milanese" in dom and "light.turn_on light.studio" in dom
    assert "consegnata con" in dom          # the 9.8 s answer went through "allora?"


def test_settings_without_secrets(url):
    dom = apri(url, "impostazioni")
    assert visibile(dom, "tab-impostazioni") and 'data-campo="LLM_MODEL"' in dom and 'data-campo="HA_VIETATO"' in dom
    assert dom.count('class="gruppo"') == 7
    assert "demo-secret-key" not in dom and "demo-secret-token" not in dom and "demo-password-123" not in dom


@pytest.mark.parametrize("scheda", ["panoramica", "conversazioni", "chat", "impostazioni", "registro"])
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
