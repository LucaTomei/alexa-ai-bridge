"""Admin page: access control, status and checks, history, test chat, settings."""
import json, os, subprocess, sys
import pytest
import conftest
from conftest import tool_use, final, oa_tool_call, oa_final
APP, ADMIN, IMP, HOME = conftest.APP, conftest.ADMIN, conftest.IMPOSTAZIONI, conftest.HOME
SRC = os.path.join(os.path.dirname(__file__), "..", "src")


@pytest.fixture
def anon():
    return APP.app.test_client()


@pytest.fixture
def client(anon):
    r = anon.post("/admin/api/login", json={"password": "test-admin-password"})
    assert r.status_code == 200
    anon.csrf = r.json["csrf"]
    return anon


def post(c, path, body=None, method="POST"):
    return c.open("/admin/api/" + path, method=method, json=body, headers={"X-CSRF": c.csrf})


@pytest.fixture
def dati(tmp_path, monkeypatch):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    return tmp_path


# ---------- access
def test_page_and_assets_are_served_with_strict_headers(anon):
    r = anon.get("/admin")
    assert r.status_code == 200 and b"Alexa AI Bridge" in r.data
    assert "default-src 'self'" in r.headers["Content-Security-Policy"] and r.headers["X-Content-Type-Options"] == "nosniff"
    for f in ("app.js", "app.css", "icon.svg"):
        assert anon.get("/admin/" + f).status_code == 200
    assert anon.get("/admin/admin.py").status_code == 404 and anon.get("/admin/../app.py").status_code == 404


def test_off_without_a_strong_password(anon, monkeypatch):
    monkeypatch.setattr(ADMIN, "ATTIVO", False)
    assert anon.get("/admin").status_code == 404 and anon.post("/admin/api/login", json={"password": "x"}).status_code == 404
    assert anon.get("/health").status_code == 200


def test_api_needs_login_and_csrf(anon, client):
    fresh = APP.app.test_client()
    assert fresh.get("/admin/api/stato").status_code == 401
    assert fresh.get("/admin/api/sessione").json == {"autenticato": False, "csrf": None, "lingua": "it"}
    assert client.get("/admin/api/stato").status_code == 200
    assert client.post("/admin/api/prova/casa").status_code == 403                    # no CSRF header
    assert client.post("/admin/api/prova/casa", headers={"X-CSRF": "wrong"}).status_code == 403
    assert post(client, "logout").status_code == 200 and client.get("/admin/api/stato").status_code == 401


def login_da(ip, password="test-admin-password", **kw):
    return APP.app.test_client().post("/admin/api/login", json={"password": password}, environ_base={"REMOTE_ADDR": ip}, **kw)


def test_wrong_passwords_are_limited_per_client_without_locking_the_owner_out():
    for _ in range(5):
        assert login_da("10.0.0.66", "nope").status_code == 401
    assert login_da("10.0.0.66").status_code == 429            # this client waits, even with the right password
    for i in range(40):                                          # many clients guessing: no global lock-out
        login_da("10.1.%d.1" % i, "nope")
    assert login_da("127.0.0.1").status_code == 200


def test_proxied_requests_are_refused_unless_published(anon, monkeypatch):
    for h in ("X-Forwarded-For", "X-Forwarded-Proto", "Forwarded", "X-Real-IP", "X-Forwarded-Host"):
        assert anon.get("/admin", headers={h: "x"}).status_code == 404, h
        assert anon.post("/admin/api/login", json={"password": "test-admin-password"}, headers={h: "x"}).status_code == 404, h
    assert anon.get("/health", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200     # the rest is untouched
    monkeypatch.setattr(ADMIN, "PUBBLICO", True)
    assert anon.get("/admin", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200


def test_spoofed_forwarded_for_does_not_dodge_the_limit(monkeypatch):
    monkeypatch.setattr(ADMIN, "PUBBLICO", True)
    for i in range(5):     # the proxy appends the real client last: whatever the client wrote before stays ignored
        login_da("172.18.0.2", "nope", headers={"X-Forwarded-For": "6.6.6.%d, 203.0.113.7" % i})
    assert login_da("172.18.0.2", headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.7"}).status_code == 429
    assert login_da("172.18.0.2", headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 200


def test_logout_revokes_the_cookie_and_sessions_expire(client, monkeypatch):
    cookie = client.get_cookie("aab_admin").value
    assert post(client, "logout").status_code == 200
    replay = APP.app.test_client()
    replay.set_cookie("aab_admin", cookie)
    assert replay.get("/admin/api/stato").status_code == 401    # a copied cookie dies with the logout
    c = APP.app.test_client()
    c.post("/admin/api/login", json={"password": "test-admin-password"})
    assert c.get("/admin/api/stato").status_code == 200
    monkeypatch.setattr(ADMIN, "DURATA", 0)
    assert c.get("/admin/api/stato").status_code == 401         # absolute lifetime, not renewed by use
    monkeypatch.undo()
    monkeypatch.setattr(ADMIN, "PASSWORD", "a-new-password-for-admin")
    assert c.get("/admin/api/stato").status_code == 401         # a new password logs everyone out


def test_session_key_is_random_and_not_derived_from_the_password():
    import hashlib
    assert len(ADMIN.SEGRETO) >= 32 and ADMIN.SEGRETO != hashlib.sha256(b"alexa-ai-bridge-admin:test-admin-password").digest()
    assert IMP.segreto() == ADMIN.SEGRETO                       # kept in DATA_DIR, stable across restarts
    assert oct(os.stat(os.path.join(IMP.DATA_DIR, "admin-secret")).st_mode & 0o777) == "0o600"


def test_session_cookie_flags(anon, monkeypatch):
    monkeypatch.setattr(ADMIN, "PUBBLICO", True)
    r = anon.post("/admin/api/login", json={"password": "test-admin-password"}, headers={"X-Forwarded-Proto": "https"})
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Secure" in cookie
    r = APP.app.test_client().post("/admin/api/login", json={"password": "test-admin-password"})
    assert "Secure" not in r.headers["Set-Cookie"]     # plain http on the home network still works


# ---------- status and checks
def test_status(client, alexa, llm):
    alexa.ask("ciao")
    s = client.get("/admin/api/stato").json
    assert s["modello"] == {"api": "anthropic", "url": APP.llm.BASE, "nome": "model-test", "chiave": True}
    assert s["web"]["backend"] == "native" and s["casa"]["attiva"] is True and s["statistiche"]["domande"] == 1
    assert "test-key" not in json.dumps(s) and "ha-token" not in json.dumps(s)


def test_checks(client, llm, openai, web):
    r = post(client, "prova/modello").json
    assert r["ok"] and r["esito"].startswith("R1 su")
    r = post(client, "prova/web").json                  # SearXNG with the openai fixture
    assert r["ok"] and "Meteo Testville" in r["esito"]
    r = post(client, "prova/casa").json
    assert r["ok"] and r["esito"].startswith("Persone:")


def test_checks_report_problems(client, monkeypatch):
    monkeypatch.setattr(APP, "WEB", None)
    assert post(client, "prova/web").json == {"ok": False, "esito": "Ricerca web spenta o non configurata.", "durata": 0}
    monkeypatch.setattr(HOME, "HA", "http://127.0.0.1:1")
    r = post(client, "prova/casa").json
    assert r["ok"] is False and r["esito"]
    monkeypatch.setattr(HOME, "ATTIVO", False)
    assert post(client, "prova/casa").json["ok"] is False
    assert post(client, "prova/altro").status_code == 404


# ---------- history
def test_history_records_alexa_and_clears(client, alexa, llm):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}), final("Accesa.")]
    alexa.ask("accendi la cucina")
    v = client.get("/admin/api/storico").json["voci"]
    assert len(v) == 1 and v[0]["domanda"] == "accendi la cucina" and v[0]["risposta"] == "Accesa."
    assert v[0]["origine"] == "alexa" and v[0]["azioni"] == ["light.turn_on light.kitchen"] and v[0]["utente"] != "user-1"
    assert post(client, "storico", method="DELETE").status_code == 200 and client.get("/admin/api/storico").json["voci"] == []


def test_history_records_failures(client, alexa, llm, monkeypatch):
    monkeypatch.setattr(llm, "handle", lambda *a: (401, {"error": "bad key"}))
    alexa.ask("x")
    v = client.get("/admin/api/storico").json["voci"][0]
    assert v["risposta"] is None and "401" in v["errore"]


def test_history_can_be_off(alexa, llm, monkeypatch):
    monkeypatch.setattr(ADMIN, "STORIA_ATTIVA", False)
    alexa.ask("privata")
    monkeypatch.undo()
    assert not ADMIN.voci_storico()


# ---------- test chat
def test_chat_simulates_home_actions_by_default(client, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "turn_off", "entita": ["light.living_room"]}), final("Spenta.")]
    r = post(client, "chat", {"testo": "spegni il salone"}).json
    assert r["risposta"] == "Spenta." and r["azioni"] == ["[simulata] light.turn_off light.living_room"] and not ha.calls
    assert r["storia"][-1]["content"].startswith("Spenta.\n[azioni eseguite: [simulata]")
    assert HOME._tl.simula is False                     # the simulation never leaks to the next request


def test_chat_can_run_real_actions_and_keeps_memory(client, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}), final("Accesa.")]
    r = post(client, "chat", {"testo": "accendi la cucina", "simula": False}).json
    assert ha.calls == [("/api/services/light/turn_on", {"entity_id": ["light.kitchen"]})]
    r = post(client, "chat", {"testo": "e adesso?", "storia": r["storia"]}).json
    assert r["risposta"] == "R3 su: e adesso?" and len(r["storia"]) == 4
    v = client.get("/admin/api/storico").json["voci"]
    assert [x["origine"] for x in v] == ["chat", "chat"]


def test_chat_safety_rules_still_apply(client, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "lock", "servizio": "unlock", "entita": ["lock.front_door"]}), final("No.")]
    r = post(client, "chat", {"testo": "apri la porta", "simula": False}).json
    assert r["azioni"] == [] and not ha.calls


def test_chat_input_validation_and_errors(client, llm, monkeypatch):
    assert post(client, "chat", {"testo": "  "}).status_code == 400
    r = post(client, "chat", {"testo": "x", "storia": [{"role": "assistant", "content": "a"}, {"role": "system", "content": "evil"}, "junk"]}).json
    assert r["storia"][0] == {"role": "user", "content": "x"}
    monkeypatch.setattr(llm, "handle", lambda *a: (401, {"error": "bad key"}))
    r = post(client, "chat", {"testo": "y"}).json
    assert r["risposta"] is None and "401" in r["errore"]


def test_chat_with_openai_models(client, openai, ha):
    openai.queue = [oa_tool_call("c", "cerca_in_casa", {"testo": "cucina"}), oa_final("La cucina e' spenta.")]
    assert post(client, "chat", {"testo": "com'e' la cucina"}).json["risposta"] == "La cucina e' spenta."


# ---------- settings
def test_settings_never_expose_secrets(client, dati):
    d = client.get("/admin/api/impostazioni").json
    campi = {c["nome"]: c for c in d["campi"]}
    assert campi["LLM_API_KEY"]["valore"] is None and campi["LLM_API_KEY"]["impostato"] is True
    assert campi["HA_TOKEN"]["valore"] is None and campi["LLM_MODEL"]["valore"] == "model-test"
    assert campi["LLM_MODEL"]["origine"] == "env" and d["configurabile"] is True
    assert "test-key" not in json.dumps(d) and "ha-token" not in json.dumps(d) and "ADMIN_PASSWORD" not in json.dumps(d)


@pytest.mark.parametrize("valori, messaggio", [
    ({"LLM_BASE_URL": "file:///data/settings.json#", "LLM_API_KEY": ""}, "http:// o https://"),
    ({"HA_URL": "gopher://x", "HA_TOKEN": ""}, "http:// o https://"),
    ({"SEARXNG_URL": "javascript:alert(1)"}, "http:// o https://"),
    ({"ATTESA_MAX": "inf"}, "tra 1 e 7.5"),
    ({"ATTESA_MAX": "nan"}, "tra 1 e 7.5"),
    ({"ATTESA_MAX": "8"}, "tra 1 e 7.5"),
    ({"LLM_MAX_TOKENS": "1e12"}, "intero tra 1 e 200000"),
    ({"WEB_RESULTS": "2.5"}, "intero"),
    ({"HA_TOOLS": "maybe"}, "valore non previsto"),
    ({"HOME_CITY": "Roma\x00"}, "caratteri non ammessi"),
    ({"HOME_CITY": "Roma\nRIGA"}, "caratteri non ammessi"),
    ({"HOME_CITY": "\udc80"}, "caratteri non validi"),
    ({"SYSTEM_PROMPT": "x" * 20001}, "troppo lungo"),
    ({"HOME_CITY": True}, "Valore non valido"),
    ({"LLM_BASE_URL": "https://attacker.example/v1"}, "scrivi di nuovo Modello: Chiave API"),
    ({"HA_URL": "https://attacker.example"}, "scrivi di nuovo Home Assistant: Token"),
])
def test_dangerous_or_broken_values_are_refused(client, dati, valori, messaggio):
    r = post(client, "impostazioni", {"valori": valori})
    assert r.status_code == 400 and messaggio in r.json["errore"], r.json
    assert not (dati / "settings.json").exists() and not list(dati.glob(".settings-*"))


def test_malformed_requests_are_400_not_500(client, dati):
    for corpo in ({"valori": ["LLM_MODEL"]}, {"valori": "x"}, [], "x"):
        assert post(client, "impostazioni", corpo).status_code == 400
    assert post(client, "chat", ["x"]).status_code == 400
    assert post(client, "chat", {"testo": "ciao", "storia": "non una lista"}).status_code == 200


def test_new_endpoint_with_its_key_is_accepted(client, dati):
    r = post(client, "impostazioni", {"valori": {"LLM_BASE_URL": "http://127.0.0.1:11434/v1", "LLM_API_KEY": ""}})
    assert r.status_code == 200
    assert json.loads((dati / "settings.json").read_text()) == {"LLM_BASE_URL": "http://127.0.0.1:11434/v1", "LLM_API_KEY": ""}


def test_two_saves_before_the_restart_both_count(client, dati):
    assert post(client, "impostazioni", {"valori": {"HOME_CITY": "Roma"}}).status_code == 200
    assert post(client, "impostazioni", {"valori": {"WEB_RESULTS": "7"}}).status_code == 200
    assert json.loads((dati / "settings.json").read_text()) == {"HOME_CITY": "Roma", "WEB_RESULTS": "7"}


def test_urls_with_credentials_are_masked(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "https://user:pass@search.example/?token=abc")
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["SEARXNG_URL"]["valore"] is None and campi["SEARXNG_URL"]["mascherato"] == "https://•••@search.example/?•••"
    monkeypatch.setattr(APP.casa, "HA", "https://u:p@ha.example")
    assert client.get("/admin/api/stato").json["casa"]["url"] == "https://•••@ha.example"


def test_empty_answers_never_put_the_response_body_in_the_log(client, llm):
    llm.queue = [{"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": "LLM_API_KEY=sk-secret"}], "leak": "sk-secret"}] * 2
    post(client, "prova/modello")
    righe = " ".join(v["testo"] for v in client.get("/admin/api/registro").json["voci"])
    assert "sk-secret" not in righe and "stop_reason=end_turn, blocks=thinking" in righe


def test_settings_are_validated_saved_and_reverted(client, dati):
    r = post(client, "impostazioni", {"valori": {"LLM_EXTRA_JSON": "[1, 2]"}})
    assert r.status_code == 400 and "LLM_EXTRA_JSON must be a JSON object" in r.json["errore"]
    r = post(client, "impostazioni", {"valori": {"HA_VIETATO": "garage("}})
    assert r.status_code == 400 and "HA_VIETATO" in r.json["errore"]
    assert post(client, "impostazioni", {"valori": {"PASSWORD": "x"}}).status_code == 400
    r = post(client, "impostazioni", {"valori": {"ATTESA_MAX": "sei"}})
    assert r.status_code == 400 and r.json["errore"] == "Attesa massima (s) (ATTESA_MAX) deve essere un numero."
    assert not (dati / "settings.json").exists()
    r = post(client, "impostazioni", {"valori": {"LLM_MODEL": "  modello-nuovo ", "HOME_CITY": "Roma"}})
    assert r.status_code == 200 and r.json == {"ok": True, "riavvio": False}       # not under gunicorn: no reload
    assert json.loads((dati / "settings.json").read_text()) == {"LLM_MODEL": "modello-nuovo", "HOME_CITY": "Roma"}
    assert oct((dati / "settings.json").stat().st_mode & 0o777) == "0o600"


def test_saved_settings_override_env_at_startup(dati):
    (dati / "settings.json").write_text(json.dumps({"LLM_MODEL": "dal-pannello", "NON_GESTITA": "x"}))
    env = dict(os.environ, DATA_DIR=str(dati))
    r = subprocess.run([sys.executable, "-c", "import app, os; print(app.llm.MODEL, os.environ.get('NON_GESTITA'))"],
                       cwd=SRC, env=env, capture_output=True, text=True, timeout=60)
    assert r.stdout.split() == ["dal-pannello", "None"], r.stderr


def test_validation_ignores_the_previously_saved_file(client, dati, monkeypatch):
    (dati / "settings.json").write_text(json.dumps({"LLM_EXTRA_JSON": "[broken]"}))     # a bad file must not block a fix
    monkeypatch.setattr(IMP, "OVERRIDE", {"LLM_EXTRA_JSON": "[broken]"})
    monkeypatch.setattr(IMP, "BASE", {"LLM_EXTRA_JSON": None})
    r = post(client, "impostazioni", {"valori": {"LLM_EXTRA_JSON": None}})
    assert r.status_code == 200 and json.loads((dati / "settings.json").read_text()) == {}


def test_settings_read_only_without_data_folder(client, monkeypatch):
    monkeypatch.setattr(IMP, "DATA_DIR", "/nonexistent/aab")
    assert client.get("/admin/api/impostazioni").json["configurabile"] is False
    assert post(client, "impostazioni", {"valori": {"HOME_CITY": "Roma"}}).status_code == 409


def test_reload_asks_gunicorn(monkeypatch):
    chiamate = []
    monkeypatch.setattr(ADMIN.threading, "Timer", lambda t, f, args: type("T", (), {"start": lambda self: chiamate.append(args)})())
    assert ADMIN._riavvia("gunicorn/26.2.0") is True and chiamate and chiamate[0][1] == ADMIN.signal.SIGHUP
    assert ADMIN._riavvia("Werkzeug/3.1") is False


# ---------- log
def test_log_captures_service_messages(client, alexa, llm):
    alexa.ask("x")
    voci = client.get("/admin/api/registro").json["voci"]
    assert any("domanda risposta" in v["testo"] for v in voci) and any(v["testo"].startswith("admin: login") for v in voci)


# ---------- language of the page
def test_messages_follow_the_page_language(anon, client, dati):
    r = anon.post("/admin/api/login", json={"password": "nope"}, headers={"X-Lang": "en"})
    assert r.json["errore"] == "Wrong password."
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni", headers={"X-Lang": "en"}).json["campi"]}
    assert campi["LLM_API_KEY"]["etichetta"] == "API key" and campi["LLM_API_KEY"]["nome_gruppo"] == "Model"
    r = client.post("/admin/api/impostazioni", json={"valori": {"ATTESA_MAX": "99"}}, headers={"X-CSRF": client.csrf, "X-Lang": "en"})
    assert r.json["errore"] == "Maximum wait (s) (ATTESA_MAX) must be a number between 1 and 7.5."
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["LLM_API_KEY"]["etichetta"] == "Chiave API"


# ---------- home tab
def test_home_tab_lists_entities_with_their_protection(client, ha, monkeypatch):
    ha.states.append({"entity_id": "switch.irrigazione", "state": "off", "attributes": {"friendly_name": "Irrigazione"}})
    monkeypatch.setattr(HOME, "VIETATO", HOME._Vietato(r"^switch\.irrigazione(?:\s|$)|garage"))
    monkeypatch.setenv("HA_VIETATO", r"^switch\.irrigazione(?:\s|$)|garage")
    d = client.get("/admin/api/casa").json
    e = {x["id"]: x for x in d["entita"]}
    assert e["lock.front_door"]["blocco"] == "dominio" and e["switch.docker_zigbee2mqtt"]["blocco"] == "regole"
    assert e["switch.irrigazione"]["blocco"] == "pagina" and e["light.kitchen"]["blocco"] is None
    assert e["cover.all_covers"]["gruppo"] is True and d["vietate"] == ["switch.irrigazione"]
    assert "sensor.power" not in e and "person.alice" not in e      # only what could ever be controlled


def test_home_tab_saves_groups_and_forbidden_entities(client, dati, monkeypatch):
    monkeypatch.setenv("HA_VIETATO", r"garage|^switch\.old(?:\s|$)")
    r = post(client, "casa", {"gruppi": ["cover.all_covers", "light.kitchen"], "vietate": ["light.living_room"]})
    assert r.status_code == 200, r.json
    salvato = json.loads((dati / "settings.json").read_text())
    assert salvato["HA_GRUPPI"] == "cover.all_covers,light.kitchen"
    assert salvato["HA_VIETATO"] == r"garage|^light\.living_room(?:\s|$)"           # your own regex stays
    assert HOME._Vietato(salvato["HA_VIETATO"]).search("light.living_room Luce salone")
    assert not HOME._Vietato(salvato["HA_VIETATO"]).search("light.living_room_2 Altra")
    for corpo in ({"gruppi": ["light.x; rm"], "vietate": []}, {"gruppi": "x", "vietate": []}, {}):
        assert post(client, "casa", corpo).status_code == 400


def test_home_tab_without_home_assistant(client, monkeypatch):
    monkeypatch.setattr(HOME, "TOKEN", "")
    assert client.get("/admin/api/casa").json["configurata"] is False
    monkeypatch.undo()
    monkeypatch.setattr(HOME, "HA", "http://127.0.0.1:1")
    assert client.get("/admin/api/casa").json["errore"]


# ---------- system tab
def test_system_info_and_interaction_models(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_HOST", "alexa.casa.example")
    s = client.get("/admin/api/sistema").json
    assert s["skill_id"] == "amzn1.ask.skill.test" and s["endpoint"] == "https://alexa.casa.example/alexa"
    assert s["modelli_skill"] == ["en-US", "it-IT"] and s["lingua"] == "it" and s["infrastruttura"]["PUBLIC_HOST"] == "alexa.casa.example"
    for locale, invocazione in (("it-IT", "cervellone"), ("en-US", "big brain")):
        r = client.get("/admin/api/sistema/modello-skill/" + locale)
        assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
        assert json.loads(r.data)["interactionModel"]["languageModel"]["invocationName"] == invocazione
    assert client.get("/admin/api/sistema/modello-skill/../app.py").status_code == 404


def test_restart_and_pending_answers(client, alexa, llm):
    assert post(client, "sistema/riavvia").json == {"riavvio": False}     # not under gunicorn in the tests
    llm.delay = 1.2
    alexa.ask("lenta")
    assert post(client, "sistema/scarta-sospese").json == {"scartate": 1} and not APP._lavori


def test_log_out_everywhere(client):
    altro = APP.app.test_client()
    altro.post("/admin/api/login", json={"password": "test-admin-password"})
    assert post(client, "sistema/esci-ovunque").status_code == 200
    assert client.get("/admin/api/stato").status_code == 401 and altro.get("/admin/api/stato").status_code == 401
    assert APP.app.test_client().post("/admin/api/login", json={"password": "test-admin-password"}).status_code == 200


@pytest.mark.parametrize("ultima, nuova, sconosciuta", [("v1.2.0", True, False), ("v1.0.0", False, False)])
def test_update_check(client, monkeypatch, ultima, nuova, sconosciuta):
    monkeypatch.setattr(ADMIN, "VERSIONE", "1.0.0")
    monkeypatch.setattr(ADMIN, "_scarica_json", lambda url: {"tag_name": ultima, "html_url": "https://github.com/x/releases/" + ultima})
    r = client.get("/admin/api/sistema/aggiornamenti").json
    assert r["nuova"] is nuova and r["sconosciuta"] is sconosciuta and r["ultima"] == ultima.lstrip("v")


def test_update_check_offline_and_dev_build(client, monkeypatch):
    def giu(url):
        raise OSError("no network")
    monkeypatch.setattr(ADMIN, "_scarica_json", giu)
    assert "no network" in client.get("/admin/api/sistema/aggiornamenti").json["errore"]
    monkeypatch.setattr(ADMIN, "_scarica_json", lambda url: {"tag_name": "v1.0.0"})
    assert client.get("/admin/api/sistema/aggiornamenti").json["sconosciuta"] is True     # "dev"


@pytest.fixture
def password_pulita():
    yield
    IMP.cancella_password()


def test_change_the_password_from_the_page(client, password_pulita):
    altro = APP.app.test_client()
    altro.post("/admin/api/login", json={"password": "test-admin-password"})
    assert post(client, "password", {"attuale": "sbagliata", "nuova": "una-nuova-password"}).status_code == 401
    assert post(client, "password", {"attuale": "test-admin-password", "nuova": "corta"}).status_code == 400
    r = post(client, "password", {"attuale": "test-admin-password", "nuova": "una-nuova-password"})
    assert r.status_code == 200
    client.csrf = r.json["csrf"]
    assert client.get("/admin/api/stato").status_code == 200          # this browser stays in
    assert altro.get("/admin/api/stato").status_code == 401            # the others are logged out
    assert IMP.password_salvata().startswith("scrypt$") and "una-nuova-password" not in IMP.password_salvata()
    assert login_da("10.9.9.1", "test-admin-password").status_code == 401
    assert login_da("10.9.9.2", "una-nuova-password").status_code == 200
    r = client.delete("/admin/api/password", json={"attuale": "una-nuova-password"}, headers={"X-CSRF": client.csrf})
    assert r.status_code == 200 and IMP.password_salvata() is None
    assert login_da("10.9.9.3", "test-admin-password").status_code == 200


# ---------- backup
def test_export_never_contains_secrets(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "https://u:p@search.example")
    r = client.get("/admin/api/impostazioni/esporta")
    d = json.loads(r.data)
    assert "attachment" in r.headers["Content-Disposition"] and d["app"] == "alexa-ai-bridge"
    assert d["impostazioni"]["LLM_MODEL"] == "model-test" and d["impostazioni"]["HOME_CITY"] == "Testville"
    testo = r.data.decode()
    for segreto in ("test-key", "ha-token", "brave-key", "tvly-key", "u:p@", "test-admin-password"):
        assert segreto not in testo


# ---------- rare paths
def test_revoked_sessions_survive_a_restart(client):
    sid = None
    with client.session_transaction() as s:
        sid = s["sid"]
    post(client, "logout")
    assert sid in ADMIN._leggi_revocate()            # what a new worker loads at start


def test_native_web_check_and_hand_written_rule(client, llm, ha, monkeypatch):
    monkeypatch.setattr(APP, "WEB", "native")
    llm.queue = [final("Sole a Testville.")]
    assert post(client, "prova/web").json["esito"] == "Sole a Testville."
    monkeypatch.setattr(HOME, "VIETATO", HOME._Vietato("cucina"))
    e = {x["id"]: x for x in client.get("/admin/api/casa").json["entita"]}
    assert e["light.kitchen"]["blocco"] == "regex"


def test_password_endpoints_refuse_bad_requests(client, monkeypatch, password_pulita):
    r = client.delete("/admin/api/password", json={"attuale": "sbagliata"}, headers={"X-CSRF": client.csrf})
    assert r.status_code == 401
    monkeypatch.setattr(IMP, "DATA_DIR", "/nonexistent/aab")
    assert post(client, "password", {"attuale": "test-admin-password", "nuova": "x" * 20}).status_code == 409
    monkeypatch.undo()
    for _ in range(5):
        login_da("127.0.0.1", "nope")
    assert post(client, "password", {"attuale": "test-admin-password", "nuova": "x" * 20}).status_code == 429


def test_skill_models_missing_from_the_image(client, monkeypatch):
    monkeypatch.setattr(ADMIN, "CARTELLA_SKILL", None)
    assert client.get("/admin/api/sistema/modello-skill/it-IT").status_code == 404
    assert client.get("/admin/api/sistema").json["modelli_skill"] == []


def test_settings_helpers(tmp_path, monkeypatch):
    assert IMP.mascherato("https://u:p@ha.example:8123/x?k=1") == "https://•••@ha.example:8123/x?•••"
    assert IMP.mascherato("https://ha.example") is None and IMP.etichetta("NON_ESISTE") == "NON_ESISTE"
    assert IMP.verifica_password_salvata("x", "scrypt$rotto") is False
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    (tmp_path / "admin-secret").write_bytes(b"corto")
    k = IMP.segreto()                                   # a short or broken key is replaced
    assert len(k) == 32 and (tmp_path / "admin-secret").read_bytes() == k and IMP.segreto() == k
    monkeypatch.setattr(IMP, "OVERRIDE", {"HOME_CITY": "Roma"})
    monkeypatch.setattr(IMP, "BASE", {"HOME_CITY": "Testville"})
    assert IMP.ambiente_con({})["HOME_CITY"] == "Testville"


def test_failed_write_leaves_no_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    with pytest.raises(TypeError):
        IMP.salva({"X": object()})
    assert list(tmp_path.iterdir()) == []


def test_old_llm_format_name_is_shown_as_the_api_format(client, monkeypatch):
    monkeypatch.delenv("LLM_API", raising=False)
    monkeypatch.setenv("LLM_FORMAT", "anthropic")
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["LLM_API"]["valore"] == "anthropic"
    assert campi["WEB_SEARCH"]["predefinito"] == "auto"       # an empty select shows its default


def test_model_list_from_the_endpoint(client, openai, monkeypatch):
    r = client.get("/admin/api/modelli").json
    assert r["modelli"] == [{"id": "model-test", "nome": "Model Test"}, {"id": "model-fast", "nome": ""}] and r["attuale"] == "model-test"
    monkeypatch.setattr(conftest.LLM_MOD, "API", "anthropic")
    assert [m["id"] for m in client.get("/admin/api/modelli").json["modelli"]] == ["model-test", "model-fast"]
    monkeypatch.setattr(conftest.LLM_MOD, "KEY", "wrong")
    r = client.get("/admin/api/modelli").json
    assert r["modelli"] == [] and r["errore"] == "HTTP 401"


def test_defaults_are_described(client):
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["LLM_MAX_TOKENS"]["predefinito"] == "1024" and campi["HA_VIETATO"]["predefinito_testo"] == "solo la lista incorporata"
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni", headers={"X-Lang": "en"}).json["campi"]}
    assert campi["HA_VIETATO"]["predefinito_testo"] == "the built-in list only"


def test_history_is_shared_and_survives_a_restart(client, alexa, llm):
    alexa.ask("prima della riavvio")
    APP.admin.STORICO.clear()                  # what a new worker has in memory: nothing
    assert client.get("/admin/api/storico").json["voci"][0]["domanda"] == "prima della riavvio"
    ADMIN.registra({"hist": [{"role": "user", "content": "dal test e2e"}], "t": 1.0, "durata": 2}, "e2e-test", "alexa")
    assert client.get("/admin/api/storico").json["voci"][0]["origine"] == "e2e"
