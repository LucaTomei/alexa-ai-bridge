"""Test fixtures: a fake model endpoint (Anthropic and OpenAI-compatible), a fake Home Assistant and fake web
search backends (SearXNG, Brave, Tavily), all in-process HTTP servers.
Environment variables are set before the service module is imported."""
import json, os, sys, threading, time, http.server
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class FakeLLM:
    """Scripted model endpoint. Speaks the Anthropic format on /messages and the OpenAI format on /chat/completions.
    queue: list of responses; empty queue -> echo "R<n> su: <last user text>" (n = messages without the system one)."""
    def __init__(self):
        self.queue, self.requests, self.paths, self.headers = [], [], [], []
        self.delay, self.reject_tools, self.require_max_completion = 0.0, set(), False

    def reset(self):
        self.__init__()

    def handle(self, body, path="/v1/messages", headers=None):
        self.requests.append(body); self.paths.append(path); self.headers.append(dict(headers or {}))
        time.sleep(self.delay)
        openai = path.endswith("/chat/completions")
        names = {(t.get("function") or {}).get("name") if openai else t.get("name") for t in body.get("tools", [])}
        if names & self.reject_tools:
            return 400, {"error": "tool not allowed"}
        if openai and self.require_max_completion and "max_tokens" in body:
            return 400, {"error": {"message": "Unsupported parameter: 'max_tokens'. Use 'max_completion_tokens' instead."}}
        if self.queue:
            return 200, self.queue.pop(0)
        msgs = [m for m in body["messages"] if m["role"] != "system"]
        last = msgs[-1]["content"]
        text = "R%d su: %s" % (len(msgs), last.split("\n\n")[-1] if isinstance(last, str) else "ok")
        if openai:
            return 200, {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
        return 200, {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


class FakeWeb:
    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = []


class FakeHA:
    def __init__(self):
        self.reset()

    def reset(self):
        self.calls, self.blocked_agents = [], ["Python-urllib"]
        self.states = [
            {"entity_id": "person.alice", "state": "home", "attributes": {"friendly_name": "Alice"}},
            {"entity_id": "light.living_room", "state": "on", "attributes": {"friendly_name": "Luce salone", "brightness": 128}},
            {"entity_id": "light.kitchen", "state": "off", "attributes": {"friendly_name": "Luce cucina"}},
            {"entity_id": "cover.bedroom", "state": "open", "attributes": {"friendly_name": "Tapparella camera", "current_position": 90}},
            {"entity_id": "cover.all_covers", "state": "open", "attributes": {"friendly_name": "Tutte le tapparelle", "current_position": 90}},
            {"entity_id": "lock.front_door", "state": "locked", "attributes": {"friendly_name": "Porta di casa"}},
            {"entity_id": "switch.docker_zigbee2mqtt", "state": "on", "attributes": {"friendly_name": "Zigbee2MQTT"}},
            {"entity_id": "climate.bedroom", "state": "off", "attributes": {"friendly_name": "Clima camera", "current_temperature": 19, "temperature": 20}},
            {"entity_id": "sensor.bedroom_temperature", "state": "18.9", "attributes": {"friendly_name": "Temperatura camera", "unit_of_measurement": "°C", "device_class": "temperature"}},
            {"entity_id": "sensor.power", "state": "640", "attributes": {"unit_of_measurement": "W"}},
        ]


LLM, HA, WEB = FakeLLM(), FakeHA(), FakeWeb()


def _server(get=None, post=None):
    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code, obj):
            d = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(d)))
            self.end_headers(); self.wfile.write(d)

        def do_GET(self):
            self._send(*get(self))

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            self._send(*post(self, body))

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)   # a free port: parallel test runs do not collide
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def _ha_auth(h):
    if any(h.headers.get("User-Agent", "").startswith(b) for b in HA.blocked_agents):
        return 403, {"message": "blocked"}
    if h.headers.get("Authorization") != "Bearer ha-token":
        return 401, {"message": "unauthorized"}


def _ha_get(h):
    err = _ha_auth(h)
    return err or (200, {"message": "API running."} if h.path == "/api/" else HA.states)


def _ha_post(h, body):
    err = _ha_auth(h)
    if err:
        return err
    HA.calls.append((h.path, body))
    servizio = h.path.rsplit("/", 1)[-1]          # apply the call, like Home Assistant would
    nuovo = {"turn_on": "on", "turn_off": "off", "open_cover": "open", "close_cover": "closed"}.get(servizio)
    for s in HA.states:
        if nuovo and s["entity_id"] in (body.get("entity_id") or []):
            s["state"] = nuovo
    return 200, []


def _web_get(h):
    WEB.calls.append((h.path, dict(h.headers)))
    if h.path.startswith("/search?"):
        return 200, {"answers": ["Domani sole"], "results": [{"title": "Meteo <b>Testville</b>", "content": "Sole, 21 gradi", "url": "https://www.meteo.example/t"}]}
    if h.path.startswith("/brave?"):
        if h.headers.get("X-Subscription-Token") != "brave-key":
            return 401, {}
        return 200, {"web": {"results": [{"title": "Notizia", "description": "Il <strong>fatto</strong> del giorno", "url": "https://news.example/a"}]}}
    return 404, {}


def _web_post(h, body):
    WEB.calls.append((h.path, body))
    if h.path == "/tavily" and h.headers.get("Authorization") == "Bearer tvly-key":
        return 200, {"answer": "Risposta Tavily", "results": [{"title": "Orari", "content": "Aperto fino alle 20", "url": "https://shop.example"}]}
    return 401, {}


LLM_PORT = _server(post=lambda h, b: LLM.handle(b, h.path, h.headers))
WEB_PORT = _server(get=_web_get, post=_web_post)
HA_PORT = _server(get=_ha_get, post=_ha_post)
os.environ.update(
    LLM_BASE_URL="http://127.0.0.1:%d/v1" % LLM_PORT, LLM_API_KEY="test-key", LLM_MODEL="model-test", LLM_API="anthropic",
    SKILL_ID="amzn1.ask.skill.test", ATTESA_MAX="1.0", HA_URL="http://127.0.0.1:%d" % HA_PORT, HA_TOKEN="ha-token",
    HA_GRUPPI="cover.all_covers", HA_SUMMARY_EXTRA="sensor.power=Consumo ora,lock.front_door=Porta di casa",
    HOME_CITY="Testville", HOME_COUNTRY="IT",
    SEARXNG_URL="http://127.0.0.1:%d" % WEB_PORT, BRAVE_URL="http://127.0.0.1:%d/brave" % WEB_PORT, BRAVE_API_KEY="brave-key",
    TAVILY_URL="http://127.0.0.1:%d/tavily" % WEB_PORT, TAVILY_API_KEY="tvly-key")

import app as APP  # noqa: E402  (after the environment is ready)
import home_tools as HOME  # noqa: E402
import llm as LLM_MOD  # noqa: E402
import web_search as WEB_MOD  # noqa: E402,F401  (used by the tests through conftest)
WEB_DEFAULT = APP.WEB


@pytest.fixture(autouse=True)
def clean():
    LLM.reset(); HA.reset(); WEB.reset()
    APP._lavori.clear(); APP.WEB = WEB_DEFAULT
    LLM_MOD.API = "anthropic"; LLM_MOD.STATO.update(web_nativo=True, strumenti=True, max_completion=False, thinking=True)
    HOME.ATTIVO = True; HOME._cache["t"] = 0
    yield


@pytest.fixture
def llm():
    return LLM


@pytest.fixture
def ha():
    return HA


@pytest.fixture
def web():
    return WEB


@pytest.fixture
def openai(monkeypatch):
    """Switch the service to the OpenAI-compatible format with SearXNG as web search."""
    monkeypatch.setattr(LLM_MOD, "API", "openai")
    monkeypatch.setattr(APP, "WEB", "searxng")
    return LLM


@pytest.fixture
def alexa():
    """Helpers that build Alexa requests (signature checks are covered in test_signature.py)."""
    class Alexa:
        user = {"userId": "user-1"}

        def req(self, r, attr=None):
            return APP.gestisci({"session": {"user": self.user, "attributes": attr or {}}, "request": r})

        def ask(self, q, attr=None):
            return self.req({"type": "IntentRequest", "intent": {"name": "AskIntent", "slots": {"query": {"value": q}}}}, attr)

        def short(self, q, attr=None):
            return self.req({"type": "IntentRequest", "intent": {"name": "FraseBreveIntent", "slots": {"frase": {"value": q}}}}, attr)

        def intent(self, name, attr=None):
            return self.req({"type": "IntentRequest", "intent": {"name": name}}, attr)

        @staticmethod
        def said(r):
            return r["response"].get("outputSpeech", {}).get("ssml", "")[7:-8]
    return Alexa()


def tool_use(i, name, inp):
    return {"stop_reason": "tool_use", "content": [{"type": "text", "text": "Un attimo."}, {"type": "tool_use", "id": i, "name": name, "input": inp}]}


def final(text):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


def last_tool_result(llm):
    for m in reversed(llm.requests[-1]["messages"]):
        if m["role"] == "user" and isinstance(m["content"], list):
            return m["content"][0]["content"]
        if m["role"] == "tool":
            return m["content"]


def oa_tool_call(i, name, args, as_text=True):
    """OpenAI-format response asking for one tool call (arguments as a JSON string, or as an object)."""
    return {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
        {"id": i, "type": "function", "function": {"name": name, "arguments": json.dumps(args) if as_text else args}}]}}]}


def oa_final(text):
    return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}
