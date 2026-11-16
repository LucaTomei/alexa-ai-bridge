"""Notifications: which events send one, every channel with its format, never from the test chat, no repeats, a
limit per hour, failing channels logged without their secrets, and the admin page that configures it all."""
import importlib, json, threading
import pytest
import conftest
from conftest import tool_use, final
APP, ADMIN, HOME, NOTIF, IMP = conftest.APP, conftest.ADMIN, conftest.HOME, conftest.NOTIF, conftest.IMPOSTAZIONI
WEB = "http://127.0.0.1:%d" % conftest.WEB_PORT
SEGRETI = ("tg-token", "ntfy-token", "gotify-token", "hook-token", "/ntfy/casa-segreta", "/hook/segreto")
PORTA = {"dominio": "lock", "servizio": "unlock", "entita": ["lock.front_door"]}


@pytest.fixture
def canali(monkeypatch):
    for k, v in dict(HA_SERVIZI=["mobile_app_telefono"], TELEGRAM_URL=WEB + "/telegram", TELEGRAM_TOKEN="tg-token",
                     TELEGRAM_CHAT="42", NTFY_URL=WEB + "/ntfy/casa-segreta", NTFY_TOKEN="ntfy-token", GOTIFY_URL=WEB + "/gotify",
                     GOTIFY_TOKEN="gotify-token", WEBHOOK_URL=WEB + "/hook/segreto", WEBHOOK_TOKEN="hook-token").items():
        monkeypatch.setattr(NOTIF, k, v)


@pytest.fixture
def client():
    c = APP.app.test_client()
    c.csrf = c.post("/admin/api/login", json={"password": "test-admin-password"}).json["csrf"]
    NOTIF.attendi()
    return c


def post(c, path, body=None):
    return c.post("/admin/api/" + path, json=body, headers={"X-CSRF": c.csrf})


def inviate(ha, web):
    """What reached each channel: HA notify calls and the other channels' requests."""
    assert NOTIF.attendi(5)
    return [c for c in ha.calls if c[0].startswith("/api/services/notify/")], [c for c in web.calls if c[0].startswith(conftest.NOTIFICHE)]


def chiedi(alexa, llm, *passi):
    llm.queue = list(passi) + [final("Ok.")]
    return alexa.ask("x")


# ---------- events and channels
def test_nothing_is_sent_without_a_channel(alexa, llm, ha, web):
    chiedi(alexa, llm, tool_use("t", "esegui_azione", PORTA))
    assert inviate(ha, web) == ([], []) and not NOTIF.ULTIME and not any(NOTIF.configurati().values())


def test_a_blocked_attempt_reaches_every_channel(alexa, llm, ha, web, canali):
    chiedi(alexa, llm, tool_use("t", "esegui_azione", PORTA))
    ha_calls, altre = inviate(ha, web)
    testo = "Bloccato: il modello ha chiesto lock.unlock lock.front_door, non è permesso."
    assert ha_calls == [("/api/services/notify/mobile_app_telefono", {"title": "Alexa AI Bridge", "message": testo})]
    per = {p.split("/")[1]: (p, b, h) for (p, b), h in zip(altre, web.headers, strict=True)}
    assert per["telegram"][:2] == ("/telegram/bottg-token/sendMessage", {"chat_id": "42", "text": "Alexa AI Bridge\n" + testo})
    assert per["ntfy"][1] == testo and per["ntfy"][2]["Priority"] == "4" and per["ntfy"][2]["Authorization"] == "Bearer ntfy-token"
    assert per["ntfy"][2]["Title"] == "Alexa AI Bridge" and per["ntfy"][0] == "/ntfy/casa-segreta"
    assert per["gotify"][:2] == ("/gotify/message", {"title": "Alexa AI Bridge", "message": testo, "priority": 8})
    assert per["hook"][1]["content"] == "Alexa AI Bridge: " + testo and per["hook"][1]["text"] == per["hook"][1]["content"]
    assert per["hook"][1]["message"] == testo and per["hook"][1]["urgente"] is True
    assert per["hook"][2]["Authorization"] == "Bearer hook-token"
    assert NOTIF.ULTIME[-1]["esiti"] == {c: "ok" for c in NOTIF.CANALI} and NOTIF.ULTIME[-1]["evento"] == "bloccate"


def test_forbidden_entities_and_automations_are_blocked_attempts(alexa, llm, ha, web, canali, monkeypatch):
    monkeypatch.setattr(HOME, "AUTOMAZIONI", True)
    chiedi(alexa, llm, tool_use("t", "esegui_azione", {"dominio": "switch", "servizio": "turn_off", "entita": ["switch.docker_zigbee2mqtt"]}))
    chiedi(alexa, llm, tool_use("t", "crea_automazione", {"nome": "x", "quando": {"tipo": "orario", "ora": "8:00"},
                                                          "azioni": [{"dominio": "switch", "servizio": "turn_off", "entita": ["switch.docker_zigbee2mqtt"]}]}))
    # a harmless mistake of the model (a service that does not exist) is not worth a notification
    chiedi(alexa, llm, tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "blink", "entita": ["light.kitchen"]}))
    testi = [v["testo"] for v in NOTIF.ULTIME] if NOTIF.attendi() else []
    assert testi == ["Bloccato: il modello ha chiesto switch.turn_off Zigbee2MQTT (switch.docker_zigbee2mqtt), non è permesso.",
                     "Bloccato: il modello ha chiesto switch.turn_off su Zigbee2MQTT (switch.docker_zigbee2mqtt) dentro "
                     "un'automazione, non è permesso."]


def test_which_actions_are_notified(alexa, llm, ha, web, canali, monkeypatch):
    luce = {"dominio": "light", "servizio": "turn_off", "entita": ["light.living_room"]}
    chiedi(alexa, llm, tool_use("t", "esegui_azione", luce))
    assert not NOTIF.ULTIME and NOTIF.attendi()                     # by default: only confirmed ones
    tutte = {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}
    r = chiedi(alexa, llm, tool_use("t1", "esegui_azione", tutte))
    llm.queue = [tool_use("t2", "esegui_azione", tutte), final("Chiuse.")]
    alexa.intent("AMAZON.YesIntent", {"h": r["sessionAttributes"]["h"][:-1] + [{"role": "assistant", "content": "Le chiudo?"}]})
    NOTIF.attendi()
    assert [v["testo"] for v in NOTIF.ULTIME] == ["Eseguito dopo il tuo sì: cover.close_cover su Tutte le tapparelle."]
    monkeypatch.setattr(NOTIF, "SCELTI", {"azioni"})               # every action: the confirmed ones too
    chiedi(alexa, llm, tool_use("t", "esegui_azione", luce))
    NOTIF.attendi()
    assert NOTIF.ULTIME[-1]["testo"] == "Eseguito: light.turn_off su Luce salone." and NOTIF.ULTIME[-1]["evento"] == "azioni"


def test_the_test_chat_never_notifies(client, llm, ha, web, canali):
    llm.queue = [tool_use("t", "esegui_azione", PORTA), final("No.")]
    post(client, "chat", {"testo": "apri la porta"})
    assert inviate(ha, web) == ([], [])


def test_automations_errors_and_admin_events(client, alexa, llm, ha, web, canali, monkeypatch):
    monkeypatch.setattr(HOME, "AUTOMAZIONI", True)
    monkeypatch.setattr(NOTIF, "SCELTI", set(NOTIF.EVENTI))
    args = {"nome": "Sveglia", "quando": {"tipo": "orario", "ora": "7:00"}, "azioni": [{"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}]}
    r = chiedi(alexa, llm, tool_use("t", "crea_automazione", args))
    llm.queue = [tool_use("t", "crea_automazione", dict(args, confermato=True)), final("Fatto.")]
    alexa.intent("AMAZON.YesIntent", {"h": r["sessionAttributes"]["h"][:-1] + [{"role": "assistant", "content": "Va bene?"}]})
    aid = next(iter(ha.automations))
    assert post(client, "automazioni/stato", {"id": aid, "attiva": False}).status_code == 200
    monkeypatch.setattr(APP.llm, "BASE", "http://127.0.0.1:1/v1")      # the model is down
    alexa.ask("che ore sono")
    for t in threading.enumerate():
        if getattr(t, "_target", None) is APP.calcola:
            t.join(10)
    for _ in range(5):                                              # the fifth wrong password locks the client out
        APP.app.test_client().post("/admin/api/login", json={"password": "no"})
    NOTIF.attendi()
    testi = [v["testo"] for v in NOTIF.ULTIME]
    assert "Automazione creata a voce: 'Sveglia' (alle 07:00: light.turn_on Luce cucina)." in testi
    assert "Automazione 'Sveglia' disattivata dal pannello." in testi
    assert any(x.startswith("Alexa non è riuscita a rispondere: ") for x in testi)
    assert "Troppe password sbagliate per il pannello da 127.0.0.1: bloccato per 15 minuti." in testi
    APP.app.test_client().post("/admin/api/login", json={"password": "test-admin-password"}, environ_base={"REMOTE_ADDR": "10.9.9.9"})
    NOTIF.attendi()
    assert NOTIF.ULTIME[-1]["testo"] == "Accesso al pannello di gestione da 10.9.9.9."


def test_admin_events_settings_and_password(client, canali, monkeypatch, tmp_path):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(IMP, "FILE_PASSWORD", str(tmp_path / "admin-password"))
    monkeypatch.setattr(NOTIF, "SCELTI", {"pannello"})
    assert post(client, "impostazioni", {"valori": {"HOME_CITY": "Roma"}}).status_code == 200
    assert NOTIF.ULTIME[-1]["testo"] == "Impostazioni salvate dal pannello: HOME_CITY."      # sent before the restart
    r = post(client, "password", {"attuale": "test-admin-password", "nuova": "una-password-nuova"})
    client.csrf = r.json["csrf"]
    r = client.delete("/admin/api/password", json={"attuale": "una-password-nuova"}, headers={"X-CSRF": client.csrf})
    client.csrf = r.json["csrf"]
    post(client, "sistema/esci-ovunque")
    NOTIF.attendi()
    testi = [v["testo"] for v in NOTIF.ULTIME]
    assert testi.count("La password del pannello è stata cambiata.") == 1         # the same text is not repeated
    assert "Tutte le sessioni del pannello sono state chiuse." in testi


def test_paused_no_repeats_and_a_limit_per_hour(alexa, llm, ha, web, canali, monkeypatch, caplog):
    monkeypatch.setattr(NOTIF, "ATTIVE", False)
    assert NOTIF.notifica("bloccate", "uno") is False
    monkeypatch.setattr(NOTIF, "ATTIVE", True)
    monkeypatch.setattr(NOTIF, "MAX_ORA", 2)
    assert NOTIF.notifica("bloccate", "uno") and not NOTIF.notifica("bloccate", "uno")       # repeated: not sent
    assert NOTIF.notifica("bloccate", "due") and not NOTIF.notifica("bloccate", "tre")       # third in an hour: not sent
    assert not NOTIF.notifica("bloccate", "quattro") and not NOTIF.notifica("azioni", "non scelto")
    NOTIF.attendi()
    assert [v["testo"] for v in NOTIF.ULTIME] == ["uno", "due"]
    assert sum("more than 2 in an hour" in r.getMessage() for r in caplog.records) == 1


def test_a_failing_channel_never_shows_its_secrets(alexa, llm, ha, web, canali, monkeypatch, caplog):
    web.fail = {"/telegram/", "/hook"}
    monkeypatch.setattr(NOTIF, "NTFY_URL", "http://127.0.0.1:1/ntfy/casa-segreta")
    monkeypatch.setattr(NOTIF, "GOTIFY_TOKEN", "sbagliato")
    chiedi(alexa, llm, tool_use("t", "esegui_azione", PORTA))
    NOTIF.attendi()
    esiti = NOTIF.ULTIME[-1]["esiti"]
    assert esiti["ha"] == "ok" and esiti["telegram"] == esiti["webhook"] == "HTTP 500" and esiti["gotify"] == "HTTP 401"
    assert "refused" in esiti["ntfy"].lower()
    righe = " ".join(r.getMessage() for r in caplog.records)
    assert "notification on telegram not sent: HTTP 500" in righe and not any(s in righe for s in SEGRETI)
    monkeypatch.setattr(NOTIF, "_consegna", lambda *a: 1 / 0)      # an unexpected error never stops the thread
    assert NOTIF.notifica("bloccate", "nuova") and NOTIF.attendi()
    monkeypatch.setattr(NOTIF, "SCELTI", None)          # and a broken state never reaches the caller
    assert NOTIF.notifica("bloccate", "x") is False


# ---------- admin page
def test_admin_tab(client, ha, web, canali):
    d = client.get("/admin/api/notifiche").json
    assert d["attive"] is True and d["eventi"] == ["confermate", "bloccate", "automazioni", "modelli"] and d["max_ora"] == 30
    assert d["tutti"] == list(NOTIF.EVENTI) and d["servizi_ha"] == ["mobile_app_telefono", "persistent_notification"]
    assert all(c["configurato"] for c in d["canali"].values()) and d["ha_scelti"] == ["mobile_app_telefono"]
    assert d["canali"]["ntfy"]["dettaglio"] == "http://127.0.0.1" and d["canali"]["telegram"]["dettaglio"] == "chat 42"
    assert d["canali"]["ha"]["dettaglio"] == "notify.mobile_app_telefono"
    assert not any(s in json.dumps(d) for s in SEGRETI)
    r = post(client, "notifiche/prova")
    assert r.json == {"esiti": {c: "ok" for c in NOTIF.CANALI}, "ok": True}
    assert ("/api/services/notify/mobile_app_telefono", {"title": "Alexa AI Bridge", "message": "Notifica di prova: questo canale funziona."}) in ha.calls
    assert client.get("/admin/api/notifiche").json["ultime"][0]["evento"] == "prova"
    r = client.post("/admin/api/notifiche/prova", headers={"X-CSRF": client.csrf, "X-Lang": "en"})
    assert web.calls[-1][1]["message"] == "Test notification: this channel works."


def test_admin_tab_without_channels_or_home_assistant(client, monkeypatch):
    r = post(client, "notifiche/prova")
    assert r.status_code == 409 and "Nessun canale" in r.json["errore"]
    monkeypatch.setattr(NOTIF, "HA_URL", "http://127.0.0.1:1")
    d = client.get("/admin/api/notifiche").json
    assert d["servizi_ha"] is None and d["errore_ha"] and not any(c["configurato"] for c in d["canali"].values())
    monkeypatch.setattr(NOTIF, "HA_TOKEN", "")
    assert "errore_ha" not in client.get("/admin/api/notifiche").json


def test_admin_tab_saves_the_choices(client, monkeypatch, tmp_path):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    r = post(client, "notifiche", {"attive": False, "eventi": ["errori", "bloccate"], "ha": ["mobile_app_a", "mobile_app_a"], "max_ora": 12})
    assert r.status_code == 200, r.json
    assert json.loads((tmp_path / "settings.json").read_text()) == {"NOTIFY_ATTIVE": "0", "NOTIFY_EVENTI": "bloccate,errori",
                                                                     "NOTIFY_HA": "mobile_app_a", "NOTIFY_MAX_ORA": "12"}
    assert post(client, "notifiche", {"attive": True, "eventi": [], "ha": [], "max_ora": "30"}).status_code == 200
    assert json.loads((tmp_path / "settings.json").read_text())["NOTIFY_EVENTI"] == "none"
    for corpo in ({"attive": "si", "eventi": [], "ha": [], "max_ora": 1}, {"attive": True, "eventi": ["pippo"], "ha": [], "max_ora": 1},
                  {"attive": True, "eventi": [], "ha": ["Bad Name"], "max_ora": 1}, {"attive": True, "eventi": [], "ha": [], "max_ora": True},
                  {"attive": True, "eventi": [], "ha": [], "max_ora": 0}, {"attive": True, "eventi": "x", "ha": [], "max_ora": 1}, []):
        assert post(client, "notifiche", corpo).status_code == 400, corpo


@pytest.mark.parametrize("valori, messaggio", [
    ({"NOTIFY_EVENTI": "bloccate,pippo"}, "eventi sconosciuti (pippo)"),
    ({"NOTIFY_HA": "mobile app"}, "servizi notify"),
    ({"NOTIFY_NTFY_URL": "ftp://ntfy.example/x"}, "http:// o https://"),
    ({"NOTIFY_WEBHOOK_URL": "javascript:alert(1)"}, "http:// o https://"),
    ({"NOTIFY_MAX_ORA": "0"}, "intero tra 1 e 1000"),
])
def test_settings_are_checked(client, monkeypatch, tmp_path, valori, messaggio):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    r = post(client, "impostazioni", {"valori": valori})
    assert r.status_code == 400 and messaggio in r.json["errore"], r.json


def test_a_token_follows_its_address(client, monkeypatch, tmp_path):
    monkeypatch.setattr(IMP, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(IMP, "FILE", str(tmp_path / "settings.json"))
    monkeypatch.setenv("NOTIFY_WEBHOOK_TOKEN", "hook-token")
    r = post(client, "impostazioni", {"valori": {"NOTIFY_WEBHOOK_URL": "https://altro.example/hook"}})
    assert r.status_code == 400 and "Notifiche: Webhook: token" in r.json["errore"]
    r = post(client, "impostazioni", {"valori": {"NOTIFY_WEBHOOK_URL": "https://altro.example/hook", "NOTIFY_WEBHOOK_TOKEN": "nuovo"}})
    assert r.status_code == 200, r.json
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["NOTIFY_WEBHOOK_URL"]["valore"] is None and campi["NOTIFY_NTFY_URL"]["tipo"] == "secret"


def test_settings_at_startup(monkeypatch):
    for k, v in dict(NOTIFY_ATTIVE="0", NOTIFY_EVENTI="azioni, errori,pippo", NOTIFY_MAX_ORA="5",
                     NOTIFY_HA="notify.mobile_app_a, mobile_app_b", NOTIFY_GOTIFY_URL="https://g.example/").items():
        monkeypatch.setenv(k, v)
    try:
        mod = importlib.reload(NOTIF)
        assert mod.ATTIVE is False and mod.SCELTI == {"azioni", "errori"} and mod.MAX_ORA == 5
        assert mod.HA_SERVIZI == ["mobile_app_a", "mobile_app_b"] and mod.GOTIFY_URL == "https://g.example"
        assert IMP.eventi_notifiche("") == {"confermate", "bloccate", "automazioni", "modelli"} and IMP.eventi_notifiche("None") == set()
    finally:
        monkeypatch.undo()
        importlib.reload(NOTIF)
