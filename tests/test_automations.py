"""Automations created by voice: off by default, a spoken yes before creating or deleting, the same rules as
esegui_azione for what they do, and only the automations made by the service can be seen or changed."""
import json
import pytest
import conftest
from conftest import tool_use, final, last_tool_result, oa_tool_call, oa_final
APP, ADMIN, HOME = conftest.APP, conftest.ADMIN, conftest.HOME
CONFIG = "/api/config/automation/config/"

LUCE = {"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"], "dati": {"brightness_pct": 40}}
SVEGLIA = {"nome": "Luce cucina al mattino", "quando": {"tipo": "orario", "ora": "7:05"}, "giorni": ["mon", "wed", "fri"],
           "azioni": [LUCE]}


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(HOME, "AUTOMAZIONI", True)


@pytest.fixture
def client():
    c = APP.app.test_client()
    c.csrf = c.post("/admin/api/login", json={"password": "test-admin-password"}).json["csrf"]
    return c


def post(c, path, body=None):
    return c.post("/admin/api/" + path, json=body, headers={"X-CSRF": c.csrf})


def creazioni(ha):
    return [(p, b) for p, b in ha.calls if p.startswith(CONFIG) and b != "DELETE"]


def crea(alexa, llm, args, risposta="Fatto."):
    """Ask, then confirm with a yes: the conversation a real user has."""
    llm.queue = [tool_use("t1", "crea_automazione", args), final("Creo questa automazione, va bene?")]
    r = alexa.ask("ogni mattina accendi la luce della cucina")
    llm.queue = [tool_use("t2", "crea_automazione", dict(args, confermato=True)), final(risposta)]
    return alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])


# ---------- off by default
def test_off_by_default(alexa, llm, ha):
    alexa.ask("x")
    nomi = [t["name"] for t in llm.requests[-1]["tools"]]
    assert "crea_automazione" not in nomi and "crea_automazione" not in llm.requests[-1]["messages"][-1]["content"]
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato=True)), final("No.")]
    alexa.ask("crea un'automazione")
    assert "spente" in last_tool_result(llm) and not ha.calls


def test_tools_and_instructions_when_on(alexa, llm, on):
    alexa.ask("x")
    body = llm.requests[-1]
    nomi = [t["name"] for t in body["tools"]]
    assert [n for n in nomi if "automazion" in n] == ["crea_automazione", "elenca_automazioni", "gestisci_automazione"]
    assert "crea_automazione" in body["messages"][-1]["content"] and "confermato=true" in body["messages"][-1]["content"]


def test_tools_need_home_assistant(alexa, llm, on, monkeypatch):
    monkeypatch.setattr(HOME, "ATTIVO", False)
    assert not HOME.automazioni_attive()
    alexa.ask("x")
    assert [t.get("name") for t in llm.requests[-1]["tools"]] == ["web_search", "ricorda", "dimentica"]


# ---------- creating
def test_create_after_a_spoken_yes(alexa, llm, ha, on):
    llm.queue = [tool_use("t1", "crea_automazione", SVEGLIA), final("Ogni lunedì, mercoledì e venerdì alle 7:05 accendo la cucina. Va bene?")]
    r = alexa.ask("ogni mattina accendi la luce della cucina")
    riepilogo = last_tool_result(llm)
    assert not ha.calls and riepilogo.startswith("SERVE CONFERMA")
    assert "alle 07:05, solo lun, mer, ven: light.turn_on Luce cucina" in riepilogo
    llm.queue = [tool_use("t2", "crea_automazione", dict(SVEGLIA, confermato=True)), final("Fatto, l'ho creata.")]
    r = alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert alexa.said(r) == "Fatto, l'ho creata." and "creata e attiva" in last_tool_result(llm)
    [(percorso, config)] = creazioni(ha)
    aid = percorso[len(CONFIG):]
    assert aid.startswith("aab_") and config == {
        "alias": "Alexa: Luce cucina al mattino",
        "description": "Creata a voce con Alexa AI Bridge. alle 07:05, solo lun, mer, ven: light.turn_on Luce cucina {\"brightness_pct\": 40}",
        "mode": "single", "triggers": [{"trigger": "time", "at": "07:05:00"}],
        "conditions": [{"condition": "time", "weekday": ["mon", "wed", "fri"]}],
        "actions": [{"action": "light.turn_on", "target": {"entity_id": ["light.kitchen"]}, "data": {"brightness_pct": 40}}]}
    assert "[azioni eseguite: automation.create %s (Luce cucina al mattino)]" % aid in r["sessionAttributes"]["h"][-1]["content"]
    registro = json.loads(open(HOME.FILE_AUTOMAZIONI).read())
    assert registro[aid]["nome"] == "Luce cucina al mattino" and registro[aid]["riassunto"].startswith("alle 07:05")


def test_the_model_cannot_confirm_by_itself(alexa, llm, ha, on):
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato=True)), final("Va bene?")]
    alexa.ask("ogni mattina accendi la luce della cucina")
    assert last_tool_result(llm).startswith("SERVE CONFERMA") and not ha.calls
    # a question that starts like a yes is not a yes
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato=True)), final("Ok.")]
    alexa.ask("si può creare un'automazione?", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Va bene?"}]})
    assert not ha.calls
    # confermato must be a real true, not a string
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato="true")), final("Ok.")]
    alexa.intent("AMAZON.YesIntent", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Va bene?"}]})
    assert not ha.calls


def test_a_yes_creates_only_what_was_read_to_the_user(alexa, llm, ha, on, monkeypatch):
    llm.queue = [tool_use("t1", "crea_automazione", SVEGLIA), final("Va bene?")]
    r = alexa.ask("ogni mattina accendi la luce della cucina")
    altra = dict(SVEGLIA, azioni=[dict(LUCE, entita=["light.living_room"])], confermato=True)
    llm.queue = [tool_use("t2", "crea_automazione", altra), final("Prima ti chiedo: va bene il salone?")]
    r = alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert last_tool_result(llm).startswith("SERVE CONFERMA") and "Luce salone" in last_tool_result(llm) and not ha.calls
    llm.queue = [tool_use("t3", "crea_automazione", altra), final("Creata.")]
    alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])           # now the user did hear it
    [(_, config)] = creazioni(ha)
    assert config["actions"][0]["target"] == {"entity_id": ["light.living_room"]}
    # a proposal is valid for 15 minutes, and only once
    monkeypatch.setattr(HOME, "VALIDITA_PROPOSTA", -1)
    llm.queue = [tool_use("t4", "crea_automazione", dict(SVEGLIA, nome="altra")), final("Va bene?")]
    r = alexa.ask("x")
    llm.queue = [tool_use("t5", "crea_automazione", dict(SVEGLIA, nome="altra", confermato=True)), final("Va bene?")]
    alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert last_tool_result(llm).startswith("SERVE CONFERMA") and len(creazioni(ha)) == 1


def test_proposing_and_confirming_in_the_same_turn_does_not_count(alexa, llm, ha, on):
    # the user said yes to something else; the model proposes and "confirms" at once: nothing is created
    attr = {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Vuoi sapere altro?"}]}
    llm.queue = [tool_use("t1", "crea_automazione", dict(SVEGLIA, confermato=True)),
                 tool_use("t2", "crea_automazione", dict(SVEGLIA, confermato=True)), final("Fatto.")]
    alexa.intent("AMAZON.YesIntent", attr)
    assert last_tool_result(llm).startswith("SERVE CONFERMA") and not ha.calls
    # nor when the model retries the same question after an empty answer
    llm.queue = [tool_use("t3", "crea_automazione", dict(SVEGLIA, nome="b", confermato=True)), {"stop_reason": "end_turn", "content": []},
                 tool_use("t4", "crea_automazione", dict(SVEGLIA, nome="b", confermato=True)), final("Fatto.")]
    alexa.intent("AMAZON.YesIntent", attr)
    assert not ha.calls
    # the same for deleting
    crea(alexa, llm, SVEGLIA)
    aid = next(iter(ha.automations))
    llm.queue = [tool_use("t5", "gestisci_automazione", {"automazione": aid, "operazione": "elimina", "confermato": True}),
                 tool_use("t6", "gestisci_automazione", {"automazione": aid, "operazione": "elimina", "confermato": True}), final("Ok.")]
    alexa.intent("AMAZON.YesIntent", attr)
    assert aid in ha.automations and last_tool_result(llm).startswith("SERVE CONFERMA")


@pytest.mark.parametrize("quando, giorni, trigger, testo", [
    ({"tipo": "sole", "evento": "tramonto", "scarto_minuti": -30}, None,
     {"trigger": "sun", "event": "sunset", "offset": "-00:30:00"}, "30 minuti prima del tramonto"),
    ({"tipo": "sole", "evento": "alba"}, [], {"trigger": "sun", "event": "sunrise"}, "all'alba"),
    ({"tipo": "sole", "evento": "sunrise", "scarto_minuti": 90}, None,
     {"trigger": "sun", "event": "sunrise", "offset": "01:30:00"}, "90 minuti dopo l'alba"),
    ({"tipo": "stato", "entita": "lock.front_door", "a": "unlocked", "per_minuti": 5}, None,
     {"trigger": "state", "entity_id": "lock.front_door", "to": "unlocked", "for": "00:05:00"},
     "quando Porta di casa diventa unlocked per 5 minuti"),
    ({"tipo": "stato", "entita": "person.alice", "da": "home", "a": "not_home"}, None,
     {"trigger": "state", "entity_id": "person.alice", "to": "not_home", "from": "home"}, "quando Alice passa da home a not_home"),
    ({"tipo": "soglia", "entita": "sensor.bedroom_temperature", "sotto": "18.5"}, "sab, domenica",
     {"trigger": "numeric_state", "entity_id": "sensor.bedroom_temperature", "below": 18.5},
     "quando Temperatura camera scende sotto 18.5, solo sab, dom"),
    ({"tipo": "soglia", "entita": "sensor.power", "sopra": 3000}, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     {"trigger": "numeric_state", "entity_id": "sensor.power", "above": 3000}, "quando sensor.power sale sopra 3000:"),
    ({"tipo": "soglia", "entita": "sensor.power", "sopra": 100, "sotto": 200}, None,
     {"trigger": "numeric_state", "entity_id": "sensor.power", "above": 100, "below": 200}, "quando sensor.power e' tra 100 e 200"),
])
def test_triggers(alexa, llm, ha, on, quando, giorni, trigger, testo):
    crea(alexa, llm, {"nome": "prova", "quando": quando, "giorni": giorni, "azioni": [LUCE]})
    [(_, config)] = creazioni(ha)
    assert config["triggers"] == [trigger] and testo in config["description"], config["description"]
    assert config["conditions"] == ([{"condition": "time", "weekday": ["sat", "sun"]}] if giorni == "sab, domenica" else [])


@pytest.mark.parametrize("args, errore", [
    ({"quando": {"tipo": "orario", "ora": "25:00"}}, "Ora non valida"),
    ({"quando": {"tipo": "orario"}}, "Ora non valida"),
    ({"quando": {"tipo": "ogni tanto"}}, "orario, sole, stato o soglia"),
    ({"quando": "alle 7"}, "orario, sole, stato o soglia"),
    ({"quando": {"tipo": "sole", "evento": "mezzogiorno"}}, "alba o tramonto"),
    ({"quando": {"tipo": "sole", "evento": "alba", "scarto_minuti": 500}}, "tra -180 e 180"),
    ({"quando": {"tipo": "sole", "evento": "alba", "scarto_minuti": 1.5}}, "tra -180 e 180"),
    ({"quando": {"tipo": "stato", "entita": "light.kitchen"}}, "stato di arrivo"),
    ({"quando": {"tipo": "stato", "entita": "light.nowhere", "a": "on"}}, "non esiste"),
    ({"quando": {"tipo": "stato", "entita": "light.kitchen", "a": "on", "per_minuti": 5000}}, "per_minuti"),
    ({"quando": {"tipo": "soglia", "entita": "sensor.power"}}, "sopra e/o sotto"),
    ({"quando": {"tipo": "soglia", "entita": "sensor.power", "sopra": 5, "sotto": 1}}, "sopra e/o sotto"),
    ({"quando": {"tipo": "soglia", "entita": "sensor.power", "sopra": "molto"}}, "sopra e/o sotto"),
    ({"quando": {"tipo": "soglia", "entita": "sensor.power", "sopra": "inf"}}, "sopra e/o sotto"),
    ({"giorni": ["mon", "funday"]}, "giorni"),
    ({"azioni": []}, "da 1 a 5 azioni"),
    ({"azioni": [LUCE] * 6}, "da 1 a 5 azioni"),
    ({"azioni": [{"dominio": "lock", "servizio": "unlock", "entita": ["lock.front_door"]}]}, "Azione non permessa"),
    ({"azioni": [{"dominio": "script", "servizio": "turn_on", "entita": ["script.x"]}]}, "Azione non permessa"),
    ({"azioni": [{"dominio": "automation", "servizio": "turn_off", "entita": ["automation.x"]}]}, "Azione non permessa"),
    ({"azioni": [{"dominio": "switch", "servizio": "turn_off", "entita": ["switch.docker_zigbee2mqtt"]}]}, "Per sicurezza"),
    ({"azioni": [{"dominio": "light", "servizio": "turn_on", "entita": ["all"]}]}, "niente 'all'"),
    ({"azioni": [{"dominio": "light", "servizio": "turn_on", "entita": ["switch.docker_zigbee2mqtt"]}]}, "non e' del dominio"),
    ({"azioni": [{"dominio": "light", "servizio": "turn_on", "entita": ["light.missing"]}]}, "non esiste"),
])
def test_what_is_refused(alexa, llm, ha, on, args, errore):
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato=True, **args)), final("No.")]
    alexa.intent("AMAZON.YesIntent", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Va bene?"}]})
    assert errore in last_tool_result(llm), last_tool_result(llm)
    assert not ha.calls


def test_doors_by_device_class_and_dangerous_scenes_are_refused(alexa, llm, ha, on):
    ha.states += [{"entity_id": "cover.box", "state": "closed", "attributes": {"friendly_name": "Box", "device_class": "garage"}},
                  {"entity_id": "scene.esco", "state": "x", "attributes": {"friendly_name": "Esco", "entity_id": ["lock.front_door"]}}]
    for azione in ({"dominio": "cover", "servizio": "open_cover", "entita": ["cover.box"]},
                   {"dominio": "scene", "servizio": "turn_on", "entita": "scene.esco"}):
        llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, azioni=[azione], confermato=True)), final("No.")]
        alexa.intent("AMAZON.YesIntent", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Va bene?"}]})
        assert "Per sicurezza" in last_tool_result(llm)
    assert not ha.calls


def test_only_allowed_data_and_a_single_action_object(alexa, llm, ha, on):
    azione = {"dominio": "cover", "servizio": "set_cover_position", "entita": "cover.bedroom",
              "dati": {"position": 0, "entity_id": "lock.front_door"}}
    crea(alexa, llm, {"nome": "", "quando": {"tipo": "orario", "ora": "22.30"}, "azioni": azione})
    [(_, config)] = creazioni(ha)
    assert config["actions"] == [{"action": "cover.set_cover_position", "target": {"entity_id": ["cover.bedroom"]}, "data": {"position": 0}}]
    assert config["alias"].startswith("Alexa: alle 22:30: cover.set_cover_position")      # no name: the summary


def test_same_name_and_maximum(alexa, llm, ha, on, monkeypatch):
    crea(alexa, llm, SVEGLIA)
    llm.queue = [tool_use("t", "crea_automazione", SVEGLIA), final("No.")]
    alexa.ask("x")
    assert "Esiste gia'" in last_tool_result(llm)
    monkeypatch.setattr(HOME, "MAX_AUTOMAZIONI", 1)
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, nome="altra")), final("No.")]
    alexa.ask("x")
    assert "il massimo" in last_tool_result(llm) and len(creazioni(ha)) == 1


def test_a_token_without_admin_rights_gets_a_clear_message(alexa, llm, ha, on, monkeypatch):
    monkeypatch.setattr(HOME, "TOKEN_AUTOMAZIONI", "ha-token")
    r = crea(alexa, llm, SVEGLIA, "Non ci riesco.")
    assert "serve il token di un amministratore" in last_tool_result(llm) and alexa.said(r) == "Non ci riesco."
    assert not ha.automations and not HOME._registro()


def test_home_assistant_down(alexa, llm, on, monkeypatch):
    monkeypatch.setattr(HOME, "HA", "http://127.0.0.1:1")
    llm.queue = [tool_use("t", "crea_automazione", SVEGLIA), final("Non riesco.")]
    alexa.ask("x")
    assert "Errore nel contattare Home Assistant" in last_tool_result(llm)


def test_english_and_openai_format(alexa, llm, ha, on, openai):
    alexa.user = {"userId": "user-en"}
    r = alexa.req({"type": "IntentRequest", "locale": "en-US", "intent": {"name": "AskIntent", "slots": {"query": {"value": "x"}}}})
    assert "crea_automazione" in [t["function"]["name"] for t in openai.requests[-1]["tools"]]
    openai.queue = [oa_tool_call("c1", "crea_automazione", {"nome": "Night", "quando": {"tipo": "sole", "evento": "tramonto"},
                                                            "azioni": [LUCE]}), oa_final("Shall I?")]
    r = alexa.req({"type": "IntentRequest", "locale": "en-US", "intent": {"name": "AskIntent", "slots": {"query": {"value": "every evening"}}}})
    assert last_tool_result(openai).startswith("CONFIRMATION NEEDED. Automation 'Night': at sunset: light.turn_on Luce cucina")
    openai.queue = [oa_tool_call("c2", "crea_automazione", {"nome": "Night", "quando": {"tipo": "sole", "evento": "tramonto"},
                                                            "azioni": [LUCE], "confermato": True}), oa_final("Done.")]
    alexa.req({"type": "IntentRequest", "locale": "en-US", "intent": {"name": "AMAZON.YesIntent"}}, r["sessionAttributes"])
    [(_, config)] = creazioni(ha)
    assert config["description"].startswith("Created by voice with Alexa AI Bridge. at sunset")


# ---------- listing, enabling, disabling, deleting
def test_only_own_automations_are_listed_and_changed(alexa, llm, ha, on):
    ha.states.append({"entity_id": "automation.allarme_notte", "state": "on",
                      "attributes": {"id": "1690000000", "friendly_name": "Allarme notte"}})
    crea(alexa, llm, SVEGLIA)
    llm.queue = [tool_use("t", "elenca_automazioni", {}), final("Una.")]
    alexa.ask("quali automazioni hai creato")
    elenco = last_tool_result(llm)
    assert "automation.alexa_luce_cucina_al_mattino | Luce cucina al mattino | on | alle 07:05" in elenco
    assert "allarme" not in elenco.lower()
    for chi in ("automation.allarme_notte", "Allarme notte", "1690000000", ""):
        llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": chi, "operazione": "disattiva"}), final("No.")]
        alexa.ask("x")
        assert "non e' tra le automazioni create a voce" in last_tool_result(llm)
    assert not [c for c in ha.calls if c[0].startswith("/api/services/automation/")]


def test_disable_enable_and_delete_with_a_yes(alexa, llm, ha, on):
    crea(alexa, llm, SVEGLIA)
    aid = next(iter(ha.automations))
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": "luce cucina al mattino", "operazione": "disattiva"}), final("Ok.")]
    alexa.ask("disattiva la sveglia della cucina")
    assert ha.calls[-1] == ("/api/services/automation/turn_off", {"entity_id": "automation.alexa_luce_cucina_al_mattino"})
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": "automation.alexa_luce_cucina_al_mattino", "operazione": "enable"}), final("Ok.")]
    alexa.ask("riattivala")
    assert ha.calls[-1] == ("/api/services/automation/turn_on", {"entity_id": "automation.alexa_luce_cucina_al_mattino"})
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": aid, "operazione": "elimina", "confermato": True}), final("Sicuro?")]
    r = alexa.ask("elimina la sveglia della cucina")
    assert last_tool_result(llm).startswith("SERVE CONFERMA") and aid in ha.automations
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": aid, "operazione": "elimina", "confermato": True}), final("Eliminata.")]
    r = alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert alexa.said(r) == "Eliminata." and not ha.automations and aid not in HOME._registro()
    assert "automation.delete automation.alexa_luce_cucina_al_mattino" in r["sessionAttributes"]["h"][-1]["content"]
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": aid, "operazione": "rinomina"}), final("No.")]
    alexa.ask("x")
    assert "attiva, disattiva o elimina" in last_tool_result(llm)


def test_one_deleted_by_hand_is_listed_and_can_be_forgotten(alexa, llm, ha, on):
    crea(alexa, llm, SVEGLIA)
    aid = next(iter(ha.automations))
    ha.automations.clear()
    ha.states = [s for s in ha.states if not s["entity_id"].startswith("automation.")]
    HOME._cache["t"] = 0
    assert "non trovata in Home Assistant" in HOME.elenca_automazioni()
    llm.queue = [tool_use("t", "gestisci_automazione", {"automazione": aid, "operazione": "disattiva"}), final("No.")]
    alexa.ask("x")
    assert "non c'e' piu'" in last_tool_result(llm)
    HOME.imposta_domanda("si'")
    assert HOME.gestisci_automazione(aid, "elimina", True).startswith("SERVE CONFERMA")      # asked in this turn
    HOME.imposta_domanda("si'")                                                              # the next one: yes
    assert HOME.gestisci_automazione(aid, "elimina", True).startswith("Fatto") and not HOME._registro()


def test_the_test_chat_only_simulates(client, llm, ha, on):
    llm.queue = [tool_use("t", "crea_automazione", SVEGLIA), final("La creo, va bene?")]
    r = post(client, "chat", {"testo": "ogni mattina accendi la cucina"}).json
    llm.queue = [tool_use("t", "crea_automazione", dict(SVEGLIA, confermato=True)), final("Creata.")]
    r = post(client, "chat", {"testo": "sì", "storia": r["storia"]}).json
    assert r["risposta"] == "Creata." and r["azioni"][0].startswith("[simulata] automation.create aab_")
    assert not ha.calls and not HOME._registro()


# ---------- admin page
def test_admin_lists_and_changes_them(client, alexa, llm, ha, on):
    assert client.get("/admin/api/stato").json["casa"]["automazioni"] is True
    ha.states.append({"entity_id": "automation.a_mano", "state": "on", "attributes": {"id": "123", "friendly_name": "A mano"}})
    crea(alexa, llm, SVEGLIA)
    d = client.get("/admin/api/automazioni").json
    assert d["attiva"] is True and d["permessi"] is True and d["max"] == 20 and d["token_dedicato"] is True
    [v] = d["voci"]
    assert v["entity_id"] == "automation.alexa_luce_cucina_al_mattino" and v["stato"] == "on" and v["riassunto"].startswith("alle 07:05")
    assert post(client, "automazioni/stato", {"id": v["id"], "attiva": False}).json == {"ok": True}
    assert ha.calls[-1] == ("/api/services/automation/turn_off", {"entity_id": v["entity_id"]})
    for corpo, codice in (({"id": "123", "attiva": False}, 400), ({"id": "aab_nope", "attiva": False}, 404),
                          ({"id": v["id"], "attiva": "no"}, 400), ({"id": "aab_x/../y"}, 400), ([], 400)):
        assert post(client, "automazioni/stato", corpo).status_code == codice, corpo
    assert client.post("/admin/api/automazioni/elimina", json={"id": v["id"]}).status_code == 403      # no CSRF
    assert post(client, "automazioni/elimina", {"id": v["id"]}).json == {"ok": True}
    assert not ha.automations and client.get("/admin/api/automazioni").json["voci"] == []
    assert any("automation deleted" in r["testo"] for r in client.get("/admin/api/registro").json["voci"])


def test_admin_reports_missing_rights_and_errors(client, alexa, llm, ha, on, monkeypatch):
    crea(alexa, llm, SVEGLIA)
    aid = next(iter(ha.automations))
    monkeypatch.setattr(HOME, "TOKEN_AUTOMAZIONI", "ha-token")
    d = client.get("/admin/api/automazioni").json
    assert d["permessi"] is False and d["token_dedicato"] is False
    r = post(client, "automazioni/elimina", {"id": aid})
    assert r.status_code == 502 and "amministratore" in r.json["errore"] and aid in ha.automations
    monkeypatch.setattr(HOME, "HA", "http://127.0.0.1:1")
    assert client.get("/admin/api/automazioni").json["errore"]
    assert post(client, "automazioni/stato", {"id": aid, "attiva": True}).status_code == 502
    monkeypatch.setattr(HOME, "TOKEN", "")
    assert client.get("/admin/api/automazioni").json["configurata"] is False
    assert post(client, "automazioni/elimina", {"id": aid}).status_code == 409


def test_admin_state_of_an_automation_gone_from_home_assistant(client, ha, on):
    HOME._registro_cambia(lambda d: d.update({"aab_1": {"nome": "Vecchia", "riassunto": "alle 07:00: x", "creata": 1}}))
    [v] = client.get("/admin/api/automazioni").json["voci"]
    assert v["stato"] is None and v["entity_id"] is None
    r = post(client, "automazioni/stato", {"id": "aab_1", "attiva": True})
    assert r.status_code == 409 and "Vecchia" in r.json["errore"]
    assert post(client, "automazioni/elimina", {"id": "aab_1"}).json == {"ok": True} and not HOME._registro()


def test_settings(client, monkeypatch, tmp_path):
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "FILE", str(tmp_path / "settings.json"))
    campi = {c["nome"]: c for c in client.get("/admin/api/impostazioni").json["campi"]}
    assert campi["HA_AUTOMAZIONI"]["opzioni"] == ["0", "1"] and campi["HA_AUTOMAZIONI"]["predefinito"] == "0"
    assert campi["HA_AUTOMAZIONI_TOKEN"]["valore"] is None and campi["HA_AUTOMAZIONI_TOKEN"]["impostato"] is True
    assert "ha-admin-token" not in json.dumps(campi)
    for valori, messaggio in (({"HA_AUTOMAZIONI_MAX": "0"}, "intero tra 1 e 200"), ({"HA_AUTOMAZIONI": "si"}, "valore non previsto"),
                              ({"HA_URL": "https://altro.example", "HA_TOKEN": "t"}, "scrivi di nuovo Home Assistant: Token per le automazioni")):
        r = post(client, "impostazioni", {"valori": valori})
        assert r.status_code == 400 and messaggio in r.json["errore"], r.json
    r = post(client, "impostazioni", {"valori": {"HA_URL": "https://altro.example", "HA_TOKEN": "t", "HA_AUTOMAZIONI_TOKEN": ""}})
    assert r.status_code == 200, r.json
    assert post(client, "impostazioni", {"valori": {"HA_AUTOMAZIONI": "1", "HA_AUTOMAZIONI_MAX": "5"}}).status_code == 200
    salvate = json.loads((tmp_path / "settings.json").read_text())
    assert salvate["HA_AUTOMAZIONI"] == "1" and salvate["HA_AUTOMAZIONI_MAX"] == "5"


def test_an_unset_automation_token_does_not_have_to_be_typed(client, monkeypatch, tmp_path):
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(conftest.IMPOSTAZIONI, "FILE", str(tmp_path / "settings.json"))
    monkeypatch.delenv("HA_AUTOMAZIONI_TOKEN")
    assert post(client, "impostazioni", {"valori": {"HA_URL": "https://altro.example", "HA_TOKEN": "t"}}).status_code == 200


def test_settings_load_at_startup(monkeypatch):
    import importlib
    monkeypatch.setenv("HA_AUTOMAZIONI", "1")
    monkeypatch.setenv("HA_AUTOMAZIONI_MAX", "7")
    monkeypatch.delenv("HA_AUTOMAZIONI_TOKEN")
    try:
        mod = importlib.reload(HOME)
        assert mod.AUTOMAZIONI is True and mod.MAX_AUTOMAZIONI == 7 and mod.TOKEN_AUTOMAZIONI == "ha-token"
    finally:
        monkeypatch.undo()
        importlib.reload(HOME)


# ---------- corner cases
def test_corner_cases(alexa, llm, ha, on, monkeypatch, tmp_path):
    assert HOME.elenca_automazioni() == "Nessuna automazione creata a voce."
    assert HOME._giorni("lun,, mer lun") == ["mon", "wed"] and HOME._giorni(None) == []
    with pytest.raises(HOME._NonValida):
        HOME._intero(None, 1, 5, "auto_per")
    assert HOME._trigger({"tipo": "stato", "entita": "light.kitchen", "da": "on"}, {"light.kitchen": ha.states[2]})[0] == \
        {"trigger": "state", "entity_id": "light.kitchen", "from": "on"}
    # the same automation proposed twice and an automation with a name but no data
    HOME.imposta_domanda("si'")
    assert HOME.crea_automazione("x", {"tipo": "orario", "ora": "8:00"}, [{"dominio": "light", "servizio": "turn_off",
                                                                          "entita": ["light.kitchen"]}]).startswith("SERVE CONFERMA")
    HOME.imposta_domanda("si'")
    # no data volume: the automation is created anyway, its summary is not kept
    monkeypatch.setattr(HOME, "FILE_AUTOMAZIONI", str(tmp_path / "manca" / "automations.json"))
    assert HOME.crea_automazione("x", {"tipo": "orario", "ora": "8:00"}, [{"dominio": "light", "servizio": "turn_off",
                                                                          "entita": ["light.kitchen"]}], None, True).startswith("Fatto")
    assert len(ha.automations) == 1 and HOME._registro() == {}
    # other Home Assistant errors are reported, not hidden
    monkeypatch.setattr(HOME, "_req", lambda *a, **k: (_ for _ in ()).throw(
        HOME.urllib.error.HTTPError("u", 500, "boom", {}, None)))
    assert "Errore nel contattare Home Assistant" in HOME._errore_http(HOME.urllib.error.HTTPError("u", 500, "boom", {}, None))
    with pytest.raises(HOME.urllib.error.HTTPError):
        HOME.permessi_automazioni()
    v = {"id": "aab_9", "entity_id": "automation.x", "nome": "x"}
    with pytest.raises(HOME.urllib.error.HTTPError):
        HOME.elimina_automazione(v)
    monkeypatch.setattr(HOME, "trova_automazione", lambda chi: v)
    assert "Errore nel contattare Home Assistant" in HOME.gestisci_automazione("x", "disattiva")


def test_simulated_enable_and_delete_send_nothing(ha, on):
    HOME._registro_cambia(lambda d: d.update({"aab_5": {"nome": "Prova", "riassunto": "", "creata": 1}}))
    ha.states.append({"entity_id": "automation.alexa_prova", "state": "on", "attributes": {"id": "aab_5", "friendly_name": "Alexa: Prova"}})
    HOME.imposta_simulazione(True)
    HOME.azzera_azioni()
    HOME.imposta_domanda("si'")
    assert HOME.gestisci_automazione("Prova", "off").startswith("Fatto")
    assert HOME.gestisci_automazione("alexa: prova", "delete", True).startswith("SERVE CONFERMA")
    HOME.imposta_domanda("si'")
    assert HOME.gestisci_automazione("alexa: prova", "delete", True).startswith("Fatto")
    assert not ha.calls and "aab_5" in HOME._registro()
    assert HOME.azioni_fatte() == ["[simulata] automation.turn_off automation.alexa_prova",
                                   "[simulata] automation.delete automation.alexa_prova (Prova)"]


def test_admin_when_home_assistant_does_not_answer_the_rights_check(client, on, monkeypatch):
    monkeypatch.setattr(HOME, "permessi_automazioni", lambda: (_ for _ in ()).throw(OSError("timeout")))
    d = client.get("/admin/api/automazioni").json
    assert d["permessi"] is None and d["voci"] == [] and d["configurabile"] is True
