"""Admin page with demo data and login bypassed, for the browser tests (tests/test_admin_ui.py) and for screenshots.

    python tests/ui_server.py <port> <empty data folder>

Never used by the service. Model, search and Home Assistant are not contacted."""
import os, sys, time

os.environ.update(SKILL_ID="amzn1.ask.skill.demo", LLM_BASE_URL="https://api.anthropic.com/v1", LLM_API_KEY="demo-secret-key",
                  LLM_MODEL="claude-haiku-5-5", HOME_CITY="Roma", HA_URL="https://homeassistant.local:8123",
                  HA_TOKEN="demo-secret-token", ADMIN_PASSWORD="demo-password-123", DATA_DIR=sys.argv[2], APP_VERSION="1.0.0",
                  PUBLIC_HOST="alexa.example.org", HA_GRUPPI="cover.tutte", HA_VIETATO=r"^switch\.irrigazione(?:\s|$)")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import app as A  # noqa: E402
import admin  # noqa: E402
import home_tools  # noqa: E402
from flask import session  # noqa: E402


@A.app.before_request
def _accesso_demo():
    if not admin.autenticato():
        session.update(admin=True, csrf="demo", sid="demo", login=time.time(), pw=admin._impronta())


@A.app.after_request
def _incorniciabile(r):
    # the demo page may be framed by /demo-frame (same origin): headless Chrome cannot open a window narrower than 500 px
    r.headers["Content-Security-Policy"] = r.headers.get("Content-Security-Policy", "").replace("frame-ancestors 'none'", "frame-ancestors 'self'")
    return r


@A.app.get("/demo-frame/<int:larghezza>/<scheda>")
def _cornice(larghezza, scheda):
    """The admin page at phone width; after loading, reports how far it scrolls sideways (0 = it fits)."""
    return ("<!doctype html><body style='margin:0'><iframe id=f src='/admin#%s' width=%d height=844 style='border:0'></iframe>"
            "<p id=esito></p><script>setTimeout(function(){var d=document.getElementById('f').contentDocument.documentElement;"
            "document.getElementById('esito').textContent='OVERFLOW='+(d.scrollWidth-d.clientWidth)},2500)</script>"
            % (scheda, larghezza))


ora = time.time()
for fa, origine, domanda, risposta, durata, azioni in [
    (3400, "alexa", "che tempo fa domani", "Domani a Roma sole al mattino e qualche nuvola dal pomeriggio, massima di 21 gradi.", 4.2, []),
    (3100, "alexa", "accendi la luce dello studio", "Fatto, ho acceso la luce dello studio.", 3.1, ["light.turn_on light.studio"]),
    (3050, "alexa", "spegnila", "Spenta.", 2.4, ["light.turn_off light.studio"]),
    (2400, "alexa", "chi ha vinto la partita ieri sera", "La Roma ha vinto due a uno in casa, con il gol decisivo nel finale.", 9.8, []),
    (1800, "alexa", "chiudi tutte le tapparelle", "Vuoi che chiuda tutte le tapparelle di casa?", 3.6, []),
    (1790, "alexa", "si'", "Fatto, ho chiuso tutte le tapparelle.", 2.9, ["cover.close_cover cover.tutte"]),
    (900, "chat", "apri la porta di casa", "Per sicurezza non posso aprire la porta di casa da qui.", 2.2, []),
    (300, "alexa", "come si cucina il risotto alla milanese", "Fai tostare il riso nel burro con la cipolla, sfuma col vino "
     "bianco, poi aggiungi il brodo un mestolo alla volta e lo zafferano a metà cottura. Manteca con burro e parmigiano.", 3.8, []),
]:
    admin.aggiungi_voce({"t": ora - fa, "utente": "4f2a9c1e" if origine == "alexa" else "chat", "origine": origine,
                          "domanda": domanda, "risposta": risposta, "errore": None, "durata": durata, "azioni": azioni})
admin.AVVIO = ora - 2 * 86400 - 3600
_stati = [{"entity_id": e, "state": st, "attributes": {"friendly_name": n}} for e, st, n in [
    ("light.studio", "on", "Luce studio"), ("light.salone", "off", "Luce salone"), ("cover.tutte", "open", "Tutte le tapparelle"),
    ("cover.camera", "open", "Tapparella camera"), ("climate.salone", "heat", "Clima salone"), ("switch.irrigazione", "off", "Irrigazione"),
    ("switch.cancello", "off", "Cancello"), ("lock.porta", "locked", "Porta di casa"), ("scene.notte", "scening", "Scena notte"),
    ("script.allarme", "off", "Attiva allarme")]]
home_tools.stati = lambda: _stati
A.llm.modelli = lambda timeout=8: [{"id": "claude-haiku-5-5", "nome": "Claude Haiku 5.5"},
                                   {"id": "claude-sonnet-5-5", "nome": "Claude Sonnet 5.5"}]
A.log.info("demo: admin page ready")
A.app.run(host="127.0.0.1", port=int(sys.argv[1]), threaded=True)
