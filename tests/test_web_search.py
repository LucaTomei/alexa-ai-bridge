"""Native web search (Anthropic server tool): sent with the home location, only the final text is spoken."""
import conftest
from conftest import final
APP = conftest.APP


def test_web_tool_sent_with_location(alexa, llm):
    alexa.ask("che tempo fa domani")
    web = [t for t in llm.requests[-1]["tools"] if t.get("name") == "web_search"][0]
    assert web["type"] == "web_search_20250305" and web["user_location"]["city"] == "Testville" and web["user_location"]["country"] == "IT"


def test_only_text_after_search_is_spoken(alexa, llm):
    llm.queue = [{"stop_reason": "end_turn", "content": [
        {"type": "text", "text": "Cerco. "}, {"type": "server_tool_use", "name": "web_search", "input": {"query": "meteo"}},
        {"type": "web_search_tool_result", "content": []}, {"type": "text", "text": "Domani pioggia "}, {"type": "text", "text": "leggera."}]}]
    assert alexa.said(alexa.ask("meteo")) == "Domani pioggia leggera."


def test_pause_turn_is_continued(alexa, llm):
    llm.queue = [{"stop_reason": "pause_turn", "content": [{"type": "server_tool_use", "name": "web_search", "input": {}}]}, final("Fatto.")]
    assert alexa.said(alexa.ask("x")) == "Fatto." and llm.requests[-1]["messages"][-1]["role"] == "assistant"


def test_rejected_web_search_is_switched_off_but_home_tools_stay(alexa, llm):
    llm.reject_tools = {"web_search"}
    assert alexa.said(alexa.ask("x")).startswith("R1 su") and conftest.LLM_MOD.STATO["web_nativo"] is False
    assert [t["name"] for t in llm.requests[-1]["tools"]] == ["riepilogo_casa", "cerca_in_casa", "esegui_azione"]
    alexa.ask("y")
    assert "web_search" not in [t.get("name") for t in llm.requests[-1]["tools"]]


def test_rejected_tools_fall_back_to_plain_answer(alexa, llm):
    llm.reject_tools = {"web_search", "riepilogo_casa"}
    assert alexa.said(alexa.ask("x")).startswith("R1 su") and "tools" not in llm.requests[-1] and conftest.LLM_MOD.STATO["strumenti"] is False
    alexa.ask("y")   # from now on: no tools, and the instructions no longer mention them
    assert "tools" not in llm.requests[-1] and "riepilogo_casa" not in llm.requests[-1]["messages"][-1]["content"]
