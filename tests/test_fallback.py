"""Fallback models: a main model that is unreachable, logged out, out of credit or over its limit is paused and the
next one answers; it comes back after the pause; never a second model after a home action; notifications on every
change; the background check; the Models tab of the admin page."""
import os, subprocess, sys, time
import pytest
import conftest
from conftest import tool_use, oa_final
APP, LLM, NOTIF, ADMIN = conftest.APP, conftest.LLM_MOD, conftest.NOTIF, conftest.ADMIN
BASE = "http://127.0.0.1:%d" % conftest.LLM_PORT
SPENTO = "http://127.0.0.1:1/v1"                 # nothing listens there: connection refused at once
SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def riserva(n, base=None, api="openai", attivo=True, key="k2"):
    f = LLM.Fornitore(n, base or "%s/v%d" % (BASE, n), key, "riserva-%d" % n, api, {}, LLM._stato_nuovo(), attivo)
    LLM.RISERVE.append(f)
    return f


@pytest.fixture
def avvisi(monkeypatch):
    out = []
    monkeypatch.setattr(NOTIF, "notifica", lambda evento, testo, urgente=False: out.append((evento, testo, urgente)) or True)
    return out


def percorsi(llm):
    return [p.split("/")[1] for p in llm.paths]


def test_out_of_credit_the_next_model_answers_then_the_main_one_comes_back(alexa, llm, avvisi):
    riserva(2)
    llm.fail = {"/v1/": (429, {"error": {"type": "rate_limit_error", "message": "Quota exhausted for this account"}})}
    assert alexa.said(alexa.ask("che ore sono")).startswith("R1 su: che ore sono")
    assert percorsi(llm) == ["v1", "v2"]                      # no retry on the main one: another model is ready
    s = LLM.salute(1)
    assert s["giu"] and s["fino"] > time.time() + 250 and "429" in s["errore"] and "Quota exhausted" in s["errore"]
    assert avvisi == [("modelli", "Modello non disponibile: model-test (127.0.0.1:%d): HTTP 429: Quota exhausted for this "
                       "account. Ora risponde riserva-2 (127.0.0.1:%d)." % (conftest.LLM_PORT, conftest.LLM_PORT), True)]
    # paused: the next question goes straight to the fallback model, and nothing more is sent
    llm.paths.clear(); avvisi.clear()
    alexa.ask("e domani")
    assert percorsi(llm) == ["v2"] and avvisi == [] and LLM.ULTIMO["n"] == 2
    # after the pause the main model is tried first again; it answers: notified once
    llm.fail = {}; s["fino"] = 0; llm.paths.clear()
    alexa.ask("e dopodomani")
    assert percorsi(llm) == ["v1"] and not LLM.salute(1)["giu"] and LLM.ULTIMO["n"] == 1
    assert avvisi == [("modelli", "Modello di nuovo disponibile: model-test (127.0.0.1:%d)." % conftest.LLM_PORT, False)]


@pytest.mark.parametrize("guasto,motivo", [
    ((401, {"error": {"message": "auth_unavailable: no auth available"}}), "HTTP 401: auth_unavailable: no auth available"),
    ((403, {"error": "forbidden"}), "HTTP 403: forbidden"),
    ((500, {"error": {"message": "upstream down"}}), "HTTP 500: upstream down"),
    ((400, {"error": {"message": "Your credit balance is too low to access the API"}}), "HTTP 400: Your credit balance"),
    ((404, {"error": {"message": "model_not_found"}}), "HTTP 404: model_not_found"),
])
def test_logged_out_or_broken_models_are_paused(alexa, llm, avvisi, guasto, motivo):
    riserva(2)
    llm.fail = {"/v1/": guasto}
    assert alexa.said(alexa.ask("ciao come va")).startswith("R1 su:")
    assert LLM.salute(1)["giu"] and LLM.salute(1)["errore"].startswith(motivo) and avvisi[0][0] == "modelli"


def test_unreachable_main_model(alexa, llm, avvisi, monkeypatch):
    monkeypatch.setattr(LLM, "BASE", SPENTO)
    riserva(2)
    assert alexa.said(alexa.ask("ciao")).startswith("R1 su: ciao")
    assert LLM.salute(1)["errore"] == "Connection refused" and "127.0.0.1:1" in avvisi[0][1]


def test_a_bad_request_tries_the_next_model_without_pausing_the_main_one(alexa, llm, avvisi):
    riserva(2)
    llm.fail = {"/v1/": (400, {"error": {"message": "messages: roles must alternate"}})}
    assert alexa.said(alexa.ask("ciao")).startswith("R1 su:")
    assert not LLM.salute(1)["giu"] and avvisi == []


def test_fallback_models_in_order_inactive_ones_skipped(alexa, llm, avvisi):
    riserva(2, attivo=False); riserva(3, base=SPENTO); riserva(4)
    llm.fail = {"/v1/": (503, {"error": "overloaded"})}
    assert alexa.said(alexa.ask("ciao")).startswith("R1 su:")
    assert percorsi(llm) == ["v1", "v4"] and LLM.salute(3)["giu"] and 2 not in LLM.SALUTE
    assert "riserva-3" in avvisi[0][1] and "model-test" in avvisi[0][1] and avvisi[0][1].endswith("riserva-4 (127.0.0.1:%d)." % conftest.LLM_PORT)


def test_every_model_failing(alexa, llm, avvisi):
    riserva(2)
    llm.fail = {"/v1/": (500, {}), "/v2/": (401, {})}
    r = alexa.ask("ciao")
    assert "Ci sto pensando" in alexa.said(r) or "Non sono riuscito" in alexa.said(r)
    conftest.APP._lavori.clear()
    for t in __import__("threading").enumerate():
        if getattr(t, "_target", None) is APP.calcola:
            t.join(5)
    eventi = [a[0] for a in avvisi]
    assert "modelli" in eventi and any(a[1].startswith("Nessun modello ha risposto") for a in avvisi)
    # both paused: the next question still tries them (better than not answering), main one first
    llm.fail = {}; llm.paths.clear()
    assert alexa.said(alexa.ask("riprova")).startswith("R1 su:") and percorsi(llm) == ["v1"]


def test_never_another_model_after_a_home_action(alexa, llm, ha, avvisi):
    """The action ran on the main model, then it failed: another model could run it again (a toggle undoes itself)."""
    riserva(2)
    llm.queue = [tool_use("t1", "esegui_azione", {"dominio": "light", "servizio": "toggle", "entita": ["light.kitchen"]})]
    llm.fail = {}
    orig = llm.handle

    def dopo_la_prima(body, path="/v1/messages", headers=None):
        if len(llm.requests) >= 1 and path.startswith("/v1/"):
            llm.requests.append(body); llm.paths.append(path)
            return 500, {"error": "down"}
        return orig(body, path, headers)
    llm.handle = dopo_la_prima
    try:
        alexa.ask("inverti la luce della cucina")
        for t in __import__("threading").enumerate():
            if getattr(t, "_target", None) is APP.calcola:
                t.join(5)
    finally:
        llm.handle = orig
    assert len([c for c in ha.calls if c[0].endswith("/toggle")]) == 1
    assert "v2" not in percorsi(llm) and LLM.salute(1)["giu"]


def test_a_fallback_model_in_the_other_format_gets_client_web_search(alexa, llm, monkeypatch):
    monkeypatch.setattr(APP, "WEB", "native")
    monkeypatch.setattr(APP, "WEB_CLIENT", "searxng")
    riserva(2)
    llm.fail = {"/v1/": (529, {"error": "overloaded"})}
    alexa.ask("che tempo fa domani")
    corpo = llm.requests[-1]
    nomi = [(t.get("function") or {}).get("name") for t in corpo["tools"]]
    assert llm.paths[-1] == "/v2/chat/completions" and nomi[0] == "cerca_sul_web" and "web_search_20250305" not in str(corpo)
    llm.fail = {"/v1/": (529, {})}
    llm.queue = [conftest.oa_tool_call("c1", "cerca_sul_web", {"query": "meteo Testville"}), oa_final("Sole.")]
    LLM.SALUTE.clear()
    assert alexa.said(alexa.ask("che tempo fa domani")) == "Sole." and any(c[0].startswith("/search?") for c in conftest.WEB.calls)


def test_each_model_learns_what_its_endpoint_accepts(alexa, llm):
    f = riserva(2)
    llm.fail = {"/v1/": (500, {})}
    llm.require_max_completion = True
    alexa.ask("ciao")
    assert f.stato["max_completion"] is True and LLM.STATO["max_completion"] is False


def test_the_wait_is_shared_between_models(monkeypatch):
    """A main model that hangs never takes all the time: the next one still has its turn."""
    riserva(2)
    tempi = []

    def domanda(f, *a, **k):
        tempi.append((f.n, round(a[5] - time.time())))
        if f.n == 1:
            raise TimeoutError("timed out")
        return "ok"
    monkeypatch.setattr(LLM, "_domanda", domanda)
    assert LLM.chiedi("s", [{"role": "user", "content": "x"}], [], None, timeout=120) == "ok"
    assert tempi[0] == (1, 60) and tempi[1][0] == 2 and tempi[1][1] >= 115
    assert LLM.salute(1)["errore"] == "timeout"


def test_background_check(llm, avvisi):
    f = riserva(2, base=SPENTO)
    LLM.controlla_tutti()
    assert LLM.salute(2)["giu"] and LLM.salute(2)["controllo"] and not LLM.salute(1)["giu"]
    assert avvisi == [("modelli", "Modello non raggiungibile: riserva-2 (127.0.0.1:1) (Connection refused).", True)]
    LLM.controlla_tutti()
    assert len(avvisi) == 1                                   # still down: nothing new
    f.base = BASE + "/v2"
    LLM.controlla_tutti()
    assert not LLM.salute(2)["giu"] and avvisi[-1] == ("modelli", "Modello di nuovo disponibile: riserva-2 (127.0.0.1:%d)." % conftest.LLM_PORT, False)
    assert llm.requests == []                                 # the check costs no tokens


def test_background_check_does_not_clear_a_model_out_of_credit(alexa, llm, avvisi):
    riserva(2)
    llm.fail = {"/v1/messages": (429, {"error": {"message": "quota exceeded"}})}
    alexa.ask("ciao")
    LLM.controlla_tutti()                                     # its /models list works, but it still has no credit
    assert LLM.salute(1)["giu"] and len(avvisi) == 1


def test_background_check_trusts_recent_answers(llm, avvisi):
    """An endpoint that answers but refuses its model list (HTTP 401 there) is not paused while it answers."""
    f = riserva(2, base=BASE + "/v2", api="anthropic", key="bad")
    LLM.salute(2)["t_ok"] = time.time() - 60
    LLM.controlla_tutti()
    assert not LLM.salute(2)["giu"] and avvisi == []
    LLM.salute(2)["t_ok"] = time.time() - 3 * 3600
    LLM.controlla_tutti()
    assert LLM.salute(2)["giu"] and "HTTP 401" in avvisi[0][1] and f.n == 2


def test_check_results():
    f = riserva(2)
    assert LLM.controlla(f) == (True, "2")
    conftest.LLM.fail = {}
    assert LLM.controlla(riserva(3, base=SPENTO))[0] is False
    assert LLM.controlla(riserva(4, base=BASE + "/nessuno", api="anthropic", key="bad"))[0] is False   # 401
    vuoto = riserva(5)
    orig = LLM.modelli
    LLM.modelli = lambda timeout=8, f=None: []
    try:
        assert LLM.controlla(vuoto) == (False, "nessun modello nell'elenco (account non collegato?)")
    finally:
        LLM.modelli = orig


def test_reasons_never_hold_an_address():
    e = LLM.ErroreModello('HTTP 502: {"error": {"message": "bad gateway at https://secret.example/x?key=1"}}', 502)
    assert LLM.motivo(e) == "HTTP 502: bad gateway at"
    assert LLM.motivo(LLM.Rifiutata("plain text")) == "HTTP 400: plain text"


@pytest.mark.parametrize("env,errore", [
    ({"LLM_2_BASE_URL": "http://x/v1"}, "LLM_2_MODEL is not set"),
    ({"LLM_3_MODEL": "m"}, "LLM_3_BASE_URL is not set"),
    ({"LLM_2_BASE_URL": "http://x/v1", "LLM_2_MODEL": "m", "LLM_2_API": "gemini"}, "LLM_2_API must be"),
    ({"LLM_4_BASE_URL": "http://x/v1", "LLM_4_MODEL": "m", "LLM_4_EXTRA_JSON": "[1]"}, "LLM_4_EXTRA_JSON must be a JSON object"),
    ({"LLM_2_BASE_URL": "ftp://x", "LLM_2_MODEL": "m"}, "http:// o https://"),
    ({"LLM_PAUSA": "-1"}, "between 0 and 86400"),
])
def test_settings_checked_at_startup(env, errore):
    r = subprocess.run([sys.executable, "-c", "import impostazioni, llm"], cwd=SRC, capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, DATA_DIR="/nonexistent", **env))
    assert r.returncode != 0 and errore in r.stderr.replace("must be an http:// or https:// address", "http:// o https://")


def test_settings_load_fallback_models():
    r = subprocess.run([sys.executable, "-c", "import impostazioni, llm; print([(f.n, f.api, f.model, f.attivo, f.extra) for f in llm.RISERVE], llm.PAUSA, llm.CONTROLLO)"],
                       cwd=SRC, capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, DATA_DIR="/nonexistent", LLM_2_BASE_URL="https://api.anthropic.com/v1", LLM_2_MODEL="claude",
                                LLM_3_BASE_URL="http://cliproxy:8317/v1/", LLM_3_MODEL="gpt", LLM_3_ATTIVO="0",
                                LLM_3_EXTRA_JSON='{"a": 1}', LLM_PAUSA="60", LLM_CONTROLLO="0"))
    assert r.stdout.strip() == "[(2, 'anthropic', 'claude', True, {}), (3, 'openai', 'gpt', False, {'a': 1})] 60 0", r.stderr


# ---------- admin page
@pytest.fixture
def client():
    c = APP.app.test_client()
    c.csrf = c.post("/admin/api/login", json={"password": "test-admin-password"}).json["csrf"]
    return c


def post(c, path, body=None):
    return c.post("/admin/api/" + path, json=body, headers={"X-CSRF": c.csrf})


def test_models_tab(client, llm, avvisi):
    riserva(2, key=""); riserva(3, attivo=False)
    llm.fail = {"/v1/": (429, {"error": {"message": "quota"}})}
    APP.ask_llm([{"role": "user", "content": "ciao"}])
    d = client.get("/admin/api/fornitori").json
    assert [f["n"] for f in d["fornitori"]] == [1, 2, 3] and d["liberi"] == [4, 5] and d["pausa"] == 300 and d["notifica"] is True
    uno, due, tre = d["fornitori"]
    assert uno["giu"] and uno["in_pausa"] and uno["errore"] == "HTTP 429: quota" and uno["chiave"] and not uno["in_uso"]
    assert due["in_uso"] and not due["chiave"] and due["host"] == "127.0.0.1:%d" % conftest.LLM_PORT and not tre["attivo"]
    assert "k2" not in str(d) and "test-key" not in str(d) and "/v2" not in str(d)
    assert client.get("/admin/api/stato").json["fornitori"][1]["in_uso"] is True
    # the check asks that one model only, and updates its state
    llm.fail = {}; llm.paths.clear()
    r = post(client, "fornitori/prova", {"n": 1}).json
    assert r["ok"] and percorsi(llm) == ["v1"] and not r["fornitori"][0]["giu"]
    llm.fail = {"/v3/": (401, {"error": {"message": "not logged in"}})}
    r = post(client, "fornitori/prova", {"n": 3}).json
    assert not r["ok"] and r["esito"] == "HTTP 401: not logged in"
    assert post(client, "fornitori/prova", {"n": 5}).status_code == 404 and post(client, "fornitori/prova", {"n": True}).status_code == 404
    # the model list of a fallback model, for the model picker
    assert client.get("/admin/api/modelli?n=2").json["attuale"] == "riserva-2"
    assert client.get("/admin/api/modelli?n=4").json["errore"] == "non configurato"


def test_models_tab_saves(client, monkeypatch):
    riserva(2)
    salvati = []
    monkeypatch.setattr(ADMIN, "_salva", lambda cambi: (salvati.append(cambi), ({"ok": True, "riavvio": False}, 200))[1])
    assert post(client, "fornitori", {"pausa": 60, "controllo": "0", "notifica": False, "attivi": {"2": False}}).status_code == 200
    assert salvati[-1] == {"LLM_PAUSA": "60", "LLM_CONTROLLO": "0", "LLM_2_ATTIVO": "0", "NOTIFY_EVENTI": "confermate,bloccate,automazioni"}
    post(client, "fornitori", {"pausa": 60, "controllo": 5, "notifica": True, "attivi": {}})
    assert "NOTIFY_EVENTI" not in salvati[-1]                 # already on: the events are not touched
    for corpo in ({"pausa": True, "controllo": 1, "notifica": True, "attivi": {}}, {"pausa": 1, "controllo": 1, "notifica": "si", "attivi": {}},
                  {"pausa": 1, "controllo": 1, "notifica": True, "attivi": {"1": False}}, {"pausa": 1, "controllo": 1, "notifica": True, "attivi": {"9": True}},
                  {"pausa": 1, "controllo": 1, "notifica": True, "attivi": {"2": "0"}}, []):
        assert post(client, "fornitori", corpo).status_code == 400


def test_saving_a_fallback_model_from_the_page(client, tmp_path, monkeypatch):
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "FILE", str(tmp_path / "settings.json"))
    r = post(client, "impostazioni", {"valori": {"LLM_2_BASE_URL": "http://cliproxy:8317/v1", "LLM_2_MODEL": "gpt-5"}})
    assert r.status_code == 200, r.json
    r = post(client, "impostazioni", {"valori": {"LLM_2_MODEL": None}})      # an address without a model: refused
    assert r.status_code == 400 and "LLM_2_MODEL is not set" in r.json["errore"]
    r = post(client, "impostazioni", {"valori": {"LLM_2_BASE_URL": "http://a/v1", "LLM_2_MODEL": "m", "LLM_2_API_KEY": "k"}})
    assert r.status_code == 200
    os.environ.update(LLM_2_BASE_URL="http://a/v1", LLM_2_MODEL="m", LLM_2_API_KEY="k")
    try:
        # its key is set: moving it to another address needs the key again
        r = post(client, "impostazioni", {"valori": {"LLM_2_BASE_URL": "http://other/v1"}})
        assert r.status_code == 400 and "Modello 2 (di riserva): Chiave API" in r.json["errore"]
    finally:
        for k in ("LLM_2_BASE_URL", "LLM_2_MODEL", "LLM_2_API_KEY"):
            os.environ.pop(k)
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["LLM_2_BASE_URL"]["nome_gruppo"] == "Modello 2 (di riserva)" and campi["LLM_5_API_KEY"]["tipo"] == "secret"
    assert campi["LLM_PAUSA"]["predefinito"] == "300"
