"""LANGUAGE=en: everything Alexa says, the instructions to the model, the tools and the home summary are English."""
import time
import pytest
import conftest
from conftest import tool_use, final, last_tool_result
APP, HOME, WEB_MOD = conftest.APP, conftest.HOME, conftest.WEB_MOD
L = APP.L


@pytest.fixture(autouse=True)
def inglese(monkeypatch):
    monkeypatch.setattr(L, "LINGUA", "en")


def test_spoken_texts(alexa, llm):
    assert alexa.said(alexa.req({"type": "LaunchRequest"})) == "Go ahead."
    assert alexa.said(alexa.intent("AMAZON.HelpIntent")).startswith("Ask me anything")
    assert alexa.said(alexa.intent("AMAZON.StopIntent")) == "Bye!"
    assert alexa.said(alexa.intent("AMAZON.FallbackIntent")).startswith("Sorry, I didn't get that.")
    assert alexa.said(alexa.intent("AttesaIntent")).startswith("I have no answers waiting")
    r = alexa.ask("how do I make a risotto")
    assert r["response"]["reprompt"]["outputSpeech"]["ssml"] == "<speak>Anything else?</speak>"


def test_slow_answer_and_so(alexa, llm):
    llm.delay = 1.3
    assert alexa.said(alexa.ask("long question")) == "Let me think. Say so in a few seconds."
    time.sleep(1.4); llm.delay = 0
    assert alexa.said(alexa.short("so")) == "R1 su: long question"


def test_instructions_and_tools_are_english(alexa, llm):
    alexa.ask("hello")
    body = llm.requests[-1]
    assert body["system"].startswith("You are a voice assistant speaking English")
    sent = body["messages"][-1]["content"]
    assert sent.startswith("[You are the home voice assistant") and "[Today is " in sent and "home is in Testville" in sent
    assert "You can read and control the home" in sent
    tools = {t["name"]: t for t in body["tools"]}
    assert tools["esegui_azione"]["description"].startswith("Control devices of the home")


def test_home_summary_confirmation_and_yes(alexa, llm, ha):
    llm.queue = [tool_use("t1", "riepilogo_casa", {}), final("Alice is home.")]
    alexa.ask("how is the house")
    assert last_tool_result(llm).startswith("People: Alice=home") and "Lights on: Luce salone" in last_tool_result(llm)
    args = {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}
    llm.queue = [tool_use("t2", "esegui_azione", args), final("Close them all?")]
    r = alexa.ask("close every shutter")
    assert "CONFIRMATION NEEDED" in last_tool_result(llm) and not ha.calls
    llm.queue = [tool_use("t3", "esegui_azione", args), final("Done.")]
    r = alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])
    assert ha.calls and llm.requests[-1]["messages"][-3]["content"].endswith("yes")
    assert r["sessionAttributes"]["h"][-1]["content"].endswith("[actions done: cover.close_cover cover.all_covers]")


def test_english_yes_words():
    for text, ok in (("yes", True), ("sure, close them", True), ("go ahead", True), ("of course", True), ("yesterday", False),
                     ("right shutter down", False), ("close everything", False), ("sì", True)):
        HOME.imposta_domanda(text)
        assert HOME._tl.consenso is ok, text


def test_action_notes_in_both_languages_are_never_spoken(alexa, llm):
    llm.queue = [final("Ok [actions done: x] then [azioni eseguite: y] done.")]
    assert alexa.said(alexa.ask("x")) == "Ok then done."


def test_web_results_in_english(web):
    assert WEB_MOD.cerca("weather", "searxng").startswith("Direct answer: Domani sole")
    assert WEB_MOD.cerca(" ", "searxng") == "Say what to search for."
    assert WEB_MOD.strumento()["description"].startswith("Search the web")
