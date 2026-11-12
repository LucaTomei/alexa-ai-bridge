"""Conversation flow: memory, slow answers ("allora?"), yes/no, short phrases, stop."""
import time
from conftest import final


def test_fast_answer_and_follow_up_memory(alexa, llm):
    r = alexa.ask("come si cucina il risotto")
    assert alexa.said(r) == "R1 su: come si cucina il risotto" and r["response"]["shouldEndSession"] is False
    r = alexa.ask("e se non ho il parmigiano", r["sessionAttributes"])
    assert alexa.said(r) == "R3 su: e se non ho il parmigiano" and len(r["sessionAttributes"]["h"]) == 4


def test_voice_instructions_and_date_are_added_but_not_stored(alexa, llm):
    r = alexa.ask("ciao")
    sent = llm.requests[-1]["messages"][-1]["content"]
    assert "assistente vocale" in sent and "Testville" in sent and "Oggi e'" in sent
    assert r["sessionAttributes"]["h"][0]["content"] == "ciao"


def test_slow_answer_then_allora(alexa, llm):
    llm.delay = 3.0
    r = alexa.ask("domanda lunga")
    assert alexa.said(r).startswith("Ci sto pensando")
    r2 = alexa.intent("AttesaIntent", r["sessionAttributes"])          # waits ATTESA_MAX (1 s): still running
    assert alexa.said(r2).startswith("Ci sto ancora pensando")
    time.sleep(1.2)
    r3 = alexa.intent("AttesaIntent", r["sessionAttributes"])
    assert alexa.said(r3) == "R1 su: domanda lunga" and len(r3["sessionAttributes"]["h"]) == 2
    assert alexa.said(alexa.intent("AttesaIntent")).startswith("Non ho risposte in sospeso")


def test_allora_said_as_free_text(alexa, llm):
    llm.delay = 1.4
    alexa.ask("domanda due"); time.sleep(1.2); llm.delay = 0
    assert alexa.said(alexa.ask("allora?")) == "R1 su: domanda due"


def test_reopen_skill_delivers_pending_answer(alexa, llm):
    llm.delay = 1.5
    alexa.ask("domanda tre")
    assert alexa.said(alexa.req({"type": "LaunchRequest"})).startswith("Sto ancora pensando")
    time.sleep(1.5)
    assert alexa.said(alexa.req({"type": "LaunchRequest"})) == "Ho la risposta alla domanda di prima. R1 su: domanda tre"
    assert alexa.said(alexa.req({"type": "LaunchRequest"})) == "Dimmi pure."


def test_no_discards_pending_answer(alexa, llm):
    llm.delay = 1.5
    alexa.ask("domanda quattro")
    assert alexa.said(alexa.intent("AMAZON.NoIntent")) == "Va bene. Altro?"
    time.sleep(1.5); llm.delay = 0
    assert alexa.said(alexa.intent("AMAZON.YesIntent")) == "R1 su: si'"   # nothing pending: "yes" goes to the model


def test_empty_model_answer_is_retried(alexa, llm):
    llm.queue = [{"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": ""}]}, final("Seconda volta.")]
    assert alexa.said(alexa.ask("vuota")) == "Seconda volta." and len(llm.requests) == 2


def test_model_error_is_spoken(alexa, llm, monkeypatch):
    monkeypatch.setattr(llm, "handle", lambda body: (500, {"error": "boom"}))
    assert alexa.said(alexa.ask("errore")).startswith("Non sono riuscito")


def test_users_are_separated(alexa, llm):
    llm.delay = 1.5
    alexa.ask("di Alice")
    alexa.user = {"userId": "user-2"}
    assert alexa.said(alexa.intent("AttesaIntent")).startswith("Non ho risposte in sospeso")


def test_short_phrase_goes_to_model(alexa, llm):
    assert alexa.said(alexa.short("spegnila")) == "R1 su: spegnila"
    assert alexa.said(alexa.req({"type": "IntentRequest", "intent": {"name": "FraseBreveIntent", "slots": {"frase": {}}}})).startswith("Non ho capito")


def test_stop_help_fallback(alexa):
    assert alexa.intent("AMAZON.StopIntent")["response"]["shouldEndSession"] is True
    assert "domanda" in alexa.said(alexa.intent("AMAZON.HelpIntent"))
    assert alexa.said(alexa.intent("AMAZON.FallbackIntent")).startswith("Non ho capito")
    assert alexa.req({"type": "SessionEndedRequest"}) == {"version": "1.0", "response": {}}


def test_speech_is_cleaned_and_escaped(alexa, llm):
    llm.queue = [final("**Grassetto** & <tag> # titolo")]
    assert alexa.said(alexa.ask("x")) == "Grassetto &amp; &lt;tag titolo"
