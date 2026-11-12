"""OpenAI-compatible providers (OpenAI, Gemini, Mistral, Groq, OpenRouter, Ollama, LM Studio...) and the
client-side web search backends (SearXNG, Brave, Tavily)."""
import conftest
from conftest import oa_tool_call, oa_final, last_tool_result
APP, LLM_MOD, WEB_MOD = conftest.APP, conftest.LLM_MOD, conftest.WEB_MOD


def test_plain_answer_and_request_shape(alexa, openai):
    r = alexa.ask("come si cucina il risotto")
    assert alexa.said(r) == "R1 su: come si cucina il risotto"
    body, path, hdr = openai.requests[-1], openai.paths[-1], openai.headers[-1]
    assert path == "/v1/chat/completions" and hdr["Authorization"] == "Bearer test-key"
    assert body["messages"][0] == {"role": "system", "content": APP.SYSTEM} and body["max_tokens"] == LLM_MOD.MAX_TOKENS
    assert "thinking" not in body
    names = [t["function"]["name"] for t in body["tools"]]
    assert names == ["cerca_sul_web", "riepilogo_casa", "cerca_in_casa", "esegui_azione"]
    assert all(t["type"] == "function" and t["function"]["parameters"]["type"] == "object" for t in body["tools"])


def test_follow_up_memory(alexa, openai):
    r = alexa.ask("chi ha scritto i promessi sposi")
    r = alexa.ask("e quando", r["sessionAttributes"])
    assert alexa.said(r) == "R3 su: e quando"
    assert [m["role"] for m in openai.requests[-1]["messages"]] == ["system", "user", "assistant", "user"]


def test_home_action_with_tool_calls(alexa, openai, ha):
    openai.queue = [oa_tool_call("c1", "cerca_in_casa", {"testo": "salone"}),
                    oa_tool_call("c2", "esegui_azione", {"dominio": "light", "servizio": "turn_off", "entita": ["light.living_room"]}),
                    oa_final("Ho spento la luce del salone.")]
    r = alexa.ask("spegni la luce del salone")
    assert alexa.said(r) == "Ho spento la luce del salone."
    assert ha.calls == [("/api/services/light/turn_off", {"entity_id": ["light.living_room"]})]
    msgs = openai.requests[-1]["messages"]
    assert msgs[-1]["role"] == "tool" and msgs[-1]["tool_call_id"] == "c2" and msgs[-1]["content"].startswith("Fatto")
    assert msgs[-2]["role"] == "assistant" and msgs[-2]["content"] == "" and msgs[-2]["tool_calls"][0]["id"] == "c2"
    assert r["sessionAttributes"]["h"][-1]["content"].endswith("[azioni eseguite: light.turn_off light.living_room]")


def test_tool_arguments_as_object_and_broken_json(alexa, openai, ha):
    openai.queue = [oa_tool_call("c1", "esegui_azione", {"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}, as_text=False),
                    oa_final("Accesa.")]
    assert alexa.said(alexa.ask("accendi la cucina")) == "Accesa." and ha.calls[0][0] == "/api/services/light/turn_on"
    broken = oa_tool_call("c2", "esegui_azione", {}); broken["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{not json"
    openai.queue = [broken, oa_final("Non ci sono riuscito.")]
    assert alexa.said(alexa.ask("x")) == "Non ci sono riuscito." and len(ha.calls) == 1


def test_multi_room_confirmation_also_with_openai(alexa, openai, ha):
    args = {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}
    openai.queue = [oa_tool_call("c1", "esegui_azione", args), oa_final("Le chiudo tutte?")]
    r = alexa.ask("chiudi tutte le tapparelle")
    assert not ha.calls and "SERVE CONFERMA" in last_tool_result(openai)
    openai.queue = [oa_tool_call("c2", "esegui_azione", args), oa_final("Chiuse.")]
    assert alexa.said(alexa.intent("AMAZON.YesIntent", r["sessionAttributes"])) == "Chiuse." and len(ha.calls) == 1


def test_model_without_tool_support(alexa, openai):
    openai.reject_tools = {"riepilogo_casa"}
    assert alexa.said(alexa.ask("x")) == "R1 su: x" and "tools" not in openai.requests[-1] and LLM_MOD.STATO["strumenti"] is False
    alexa.ask("y")
    assert "tools" not in openai.requests[-1] and "cerca_in_casa" not in openai.requests[-1]["messages"][-1]["content"]


def test_max_completion_tokens_is_learned(alexa, openai):
    openai.require_max_completion = True
    assert alexa.said(alexa.ask("x")) == "R1 su: x"
    assert "max_tokens" not in openai.requests[-1] and openai.requests[-1]["max_completion_tokens"] == LLM_MOD.MAX_TOKENS
    n = len(openai.requests)
    alexa.ask("y")
    assert len(openai.requests) == n + 1      # no second rejection


def test_reasoning_in_think_tags_is_not_spoken(alexa, openai):
    openai.queue = [oa_final("<think>L'utente chiede...\nragiono</think>\nSono le otto.")]
    assert alexa.said(alexa.ask("che ore sono")) == "Sono le otto."
    assert LLM_MOD.senza_pensieri("ragiono a lungo</think>Ok") == "Ok"


def test_content_parts_and_extra_fields(alexa, openai, monkeypatch):
    monkeypatch.setattr(LLM_MOD, "EXTRA", {"reasoning_effort": "low"})
    openai.queue = [{"choices": [{"message": {"role": "assistant", "content": [{"type": "text", "text": "Ciao "}, {"type": "text", "text": "a te."}]}}]}]
    assert alexa.said(alexa.ask("ciao")) == "Ciao a te." and openai.requests[-1]["reasoning_effort"] == "low"


def test_no_api_key_for_local_models(alexa, openai, monkeypatch):
    monkeypatch.setattr(LLM_MOD, "KEY", "")
    alexa.ask("x")
    assert "Authorization" not in openai.headers[-1]


# ---------- web search backends
def test_searxng(alexa, openai, web):
    openai.queue = [oa_tool_call("c1", "cerca_sul_web", {"query": "meteo Testville domani"}), oa_final("Domani sole e 21 gradi.")]
    assert alexa.said(alexa.ask("che tempo fa domani")) == "Domani sole e 21 gradi."
    path, _ = web.calls[-1]
    assert path.startswith("/search?") and "format=json" in path and "language=it" in path and "meteo+Testville" in path
    res = last_tool_result(openai)
    assert "Risposta diretta: Domani sole" in res and "1. Meteo Testville - Sole, 21 gradi (meteo.example)" in res
    assert "cercala sul web" in openai.requests[0]["messages"][-1]["content"]


def test_brave(monkeypatch, web):
    assert WEB_MOD.cerca("notizie", "brave") == "1. Notizia - Il fatto del giorno (news.example)"
    path, hdr = web.calls[-1]
    assert path.startswith("/brave?q=notizie") and hdr["X-Subscription-Token"] == "brave-key"
    monkeypatch.setattr(WEB_MOD, "BRAVE_API_KEY", "wrong")
    assert WEB_MOD.cerca("notizie", "brave").startswith("Ricerca web non disponibile")


def test_tavily(web):
    out = WEB_MOD.cerca("orari negozio", "tavily")
    assert out == "Risposta diretta: Risposta Tavily\n1. Orari - Aperto fino alle 20 (shop.example)"
    assert web.calls[-1] == ("/tavily", {"query": "orari negozio", "max_results": 5, "search_depth": "basic", "include_answer": True})


def test_search_backend_down_is_reported_to_the_model(monkeypatch):
    monkeypatch.setattr(WEB_MOD, "SEARXNG_URL", "http://127.0.0.1:1")
    assert WEB_MOD.cerca("x", "searxng").startswith("Ricerca web non disponibile")
    assert WEB_MOD.cerca("  ", "searxng") == "Specifica cosa cercare."


def test_backend_selection(monkeypatch):
    b = WEB_MOD.backend
    assert b("anthropic", "auto") == "native" and b("openai", "auto") == "searxng"
    assert b("anthropic", "searxng") == "searxng" and b("openai", "native") is None
    assert b("openai", "off") is None and b("openai", "0") is None and b("anthropic", "1") == "native"
    assert b("openai", "bing") is None
    monkeypatch.setitem(WEB_MOD._CONFIGURATO, "searxng", "")
    assert b("openai", "auto") == "brave" and b("openai", "searxng") is None
    for k in ("brave", "tavily"):
        monkeypatch.setitem(WEB_MOD._CONFIGURATO, k, "")
    assert b("openai", "auto") is None


def test_no_web_search_configured(alexa, openai, monkeypatch):
    monkeypatch.setattr(APP, "WEB", None)
    alexa.ask("x")
    assert "cerca_sul_web" not in [t["function"]["name"] for t in openai.requests[-1]["tools"]]
    assert "cercala sul web" not in openai.requests[-1]["messages"][-1]["content"]


def test_claude_with_client_side_search(alexa, llm, web, monkeypatch):
    monkeypatch.setattr(APP, "WEB", "searxng")
    alexa.ask("x")
    names = [t["name"] for t in llm.requests[-1]["tools"]]
    assert names[0] == "cerca_sul_web" and "web_search" not in names and "input_schema" in llm.requests[-1]["tools"][0]


def test_unrelated_rejection_does_not_switch_tools_off(alexa, openai, monkeypatch):
    monkeypatch.setattr(openai, "handle", lambda *a: (400, {"error": {"message": "context length exceeded"}}))
    assert alexa.said(alexa.ask("x")).startswith("Non sono riuscito")
    assert LLM_MOD.STATO["strumenti"] is True        # a 400 that tools did not cause must not disable home control


def test_overloaded_endpoint_is_retried_once(openai, monkeypatch):
    calls = []
    def flaky(body, path, headers):
        calls.append(path)
        return (503, {"error": "overloaded"}) if len(calls) == 1 else (200, oa_final("Eccomi."))
    monkeypatch.setattr(openai, "handle", flaky)
    assert LLM_MOD.chiedi("s", [{"role": "user", "content": "x"}], [], None, timeout=30) == "Eccomi." and len(calls) == 2


def test_wrong_key_is_reported_with_the_body(openai, monkeypatch):
    monkeypatch.setattr(openai, "handle", lambda *a: (401, {"error": "invalid api key"}))
    try:
        LLM_MOD.chiedi("s", [{"role": "user", "content": "x"}], [], None, timeout=30)
        raise AssertionError("no error")
    except LLM_MOD.ErroreModello as e:
        assert "401" in str(e) and "invalid api key" in str(e)
