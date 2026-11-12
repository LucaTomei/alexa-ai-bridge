"""Home Assistant tools: read, control within limits, spoken confirmation for multi-room actions."""
import conftest
from conftest import tool_use, final, last_tool_result
HOME = conftest.HOME


def test_summary(alexa, llm):
    llm.queue = [tool_use("t1", "riepilogo_casa", {}), final("In casa c'e' Alice.")]
    assert alexa.said(alexa.ask("com'e' la casa")) == "In casa c'e' Alice."
    res = last_tool_result(llm)
    for part in ("Persone: Alice=a casa", "Luci accese: Luce salone", "Temperatura camera 18.9", "Consumo ora: 640 W", "Porta di casa: locked"):
        assert part in res


def test_find_and_switch_off_a_light(alexa, llm, ha):
    llm.queue = [tool_use("t1", "cerca_in_casa", {"testo": "salone"}),
                 tool_use("t2", "esegui_azione", {"dominio": "light", "servizio": "turn_off", "entita": ["light.living_room"]}), final("Spenta.")]
    r = alexa.ask("spegni la luce del salone")
    assert ha.calls == [("/api/services/light/turn_off", {"entity_id": ["light.living_room"]})]
    assert alexa.said(r) == "Spenta."   # the "Un attimo." before the tool call is not spoken
    assert r["sessionAttributes"]["h"][-1]["content"] == "Spenta.\n[azioni eseguite: light.turn_off light.living_room]"


def test_action_note_is_never_spoken(alexa, llm):
    llm.queue = [final("Ok. [azioni eseguite: x] Fatto.")]
    assert alexa.said(alexa.ask("x")) == "Ok. Fatto."


def test_forbidden_targets_are_refused(alexa, llm, ha):
    for dom, srv, ent in (("lock", "unlock", "lock.front_door"), ("switch", "turn_off", "switch.docker_zigbee2mqtt"),
                          ("script", "turn_on", "script.open"), ("light", "turn_off", "all"), ("light", "turn_off", "light.missing"),
                          ("light", "turn_off", "switch.docker_zigbee2mqtt")):
        llm.queue = [tool_use("t", "esegui_azione", {"dominio": dom, "servizio": srv, "entita": [ent]}), final("No.")]
        alexa.ask("x")
        assert not ha.calls, (dom, ent)
    assert "[NON COMANDABILE]" in HOME.cerca("porta") and "[NON COMANDABILE]" in HOME.cerca("zigbee")


def test_multi_room_needs_spoken_yes(alexa, llm, ha):
    llm.queue = [tool_use("t1", "esegui_azione", {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}),
                 final("Le chiudo tutte?")]
    r = alexa.ask("chiudi tutte le tapparelle")
    assert not ha.calls and "SERVE CONFERMA" in last_tool_result(llm)        # the model cannot confirm by itself
    llm.queue = [tool_use("t2", "esegui_azione", {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}),
                 final("Chiuse.")]
    r = alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert ha.calls == [("/api/services/cover/close_cover", {"entity_id": ["cover.all_covers"]})] and alexa.said(r) == "Chiuse."


def test_many_entities_need_confirmation_and_no_stops(alexa, llm, ha):
    ents = ["light.living_room", "light.kitchen", "light.living_room", "light.kitchen"]
    llm.queue = [tool_use("t1", "esegui_azione", {"dominio": "light", "servizio": "turn_off", "entita": ents, "confermato": True}), final("Confermi?")]
    r = alexa.ask("spegni tutto")
    llm.queue = [final("Va bene.")]
    alexa.intent("AMAZON.NoIntent", r["sessionAttributes"])
    assert not ha.calls


def test_yes_phrases(alexa):
    for text, ok in (("sì", True), ("si'", True), ("certo, chiudile", True), ("va bene", True), ("chiudi tutto", False), ("sicuro?", False), ("no", False)):
        HOME.imposta_domanda(text)
        assert HOME._tl.consenso is ok, text


def test_only_allowed_data_is_forwarded(alexa, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "cover", "servizio": "set_cover_position", "entita": ["cover.bedroom"],
                                                 "dati": {"position": 50, "entity_id": "lock.front_door"}}), final("Ok.")]
    alexa.ask("camera a meta'")
    assert ha.calls == [("/api/services/cover/set_cover_position", {"position": 50, "entity_id": ["cover.bedroom"]})]


def test_home_assistant_down(alexa, llm, monkeypatch):
    monkeypatch.setattr(HOME, "HA", "http://127.0.0.1:1")
    llm.queue = [tool_use("t", "riepilogo_casa", {}), final("Non riesco.")]
    assert alexa.said(alexa.ask("x")) == "Non riesco." and "Errore nel contattare Home Assistant" in last_tool_result(llm)


def test_user_agent_is_not_python_urllib(ha):
    assert HOME.UA != "" and not HOME.UA.startswith("Python-urllib")
    assert HOME.riepilogo().startswith("Persone:")   # the fake HA blocks Python-urllib like Cloudflare does


def test_tools_off_without_token(monkeypatch, alexa, llm):
    monkeypatch.setattr(HOME, "ATTIVO", False)
    alexa.ask("x")
    assert [t.get("name") for t in llm.requests[-1]["tools"]] == ["web_search"]


def test_empty_answer_after_an_action_is_not_retried(alexa, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "toggle", "entita": ["light.kitchen"]}),
                 {"stop_reason": "end_turn", "content": []}]
    assert alexa.said(alexa.ask("cambia la cucina")) == "Fatto."
    assert len(ha.calls) == 1 and len(llm.requests) == 2      # a retry would toggle the light back


def test_entity_as_string_and_bad_data(alexa, llm, ha):
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "light", "servizio": "turn_on", "entita": "light.kitchen", "dati": "50%"}),
                 final("Accesa.")]
    assert alexa.said(alexa.ask("accendi la cucina")) == "Accesa."
    assert ha.calls == [("/api/services/light/turn_on", {"entity_id": ["light.kitchen"]})]


def test_custom_forbidden_list_extends_the_default(monkeypatch):
    import importlib
    monkeypatch.setenv("HA_VIETATO", "cucina")
    monkeypatch.setenv("HA_GRUPPI", " cover.all_covers , cover.bedroom ")
    try:
        mod = importlib.reload(HOME)
        assert mod.VIETATO.search("light.kitchen Luce cucina") and mod.VIETATO.search("lock.front_door Porta di casa")
        assert mod.GRUPPI == {"cover.all_covers", "cover.bedroom"}
    finally:
        monkeypatch.undo()
        importlib.reload(HOME)
