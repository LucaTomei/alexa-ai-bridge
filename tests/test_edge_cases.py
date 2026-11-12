"""Edge cases: configuration errors, Amazon's real certificate chain, limits of the tool loops, rare requests."""
import datetime as dt, json, os, subprocess, sys
import pytest
from cryptography import x509
from cryptography.x509.verification import VerificationError
import conftest
from conftest import tool_use, final, oa_tool_call, oa_final, last_tool_result
APP, HOME, LLM_MOD, WEB_MOD = conftest.APP, conftest.HOME, conftest.LLM_MOD, conftest.WEB_MOD
SRC = os.path.join(os.path.dirname(__file__), "..", "src")
DATA = os.path.join(os.path.dirname(__file__), "data")


# ---------- configuration errors are explained at startup
def _start(**env):
    base = {k: v for k, v in os.environ.items() if not k.startswith(("LLM_", "SKILL_", "HOME_", "HA_", "ADMIN_", "LANGUAGE"))}
    base.update(SKILL_ID="amzn1.ask.skill.x", LLM_BASE_URL="http://127.0.0.1:9/v1", LLM_MODEL="m")
    base.update({k: v for k, v in env.items() if v is not None})
    for k, v in env.items():
        if v is None:
            base.pop(k, None)
    return subprocess.run([sys.executable, "-c", "import app"], cwd=SRC, env=base, capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("env, message", [
    ({"SKILL_ID": None}, "SKILL_ID is not set"),
    ({"SKILL_ID": "  "}, "SKILL_ID is not set"),
    ({"LLM_BASE_URL": None}, "LLM_BASE_URL is not set"),
    ({"LLM_MODEL": ""}, "LLM_MODEL is not set"),
    ({"LLM_API": "gemini"}, "LLM_API must be"),
    ({"LLM_EXTRA_JSON": "[1, 2]"}, "LLM_EXTRA_JSON must be a JSON object"),
    ({"LLM_EXTRA_JSON": "{not json"}, "LLM_EXTRA_JSON must be a JSON object"),
    ({"HA_VIETATO": "garage("}, "HA_VIETATO is not a valid regular expression"),
    ({"LLM_BASE_URL": "file:///etc/passwd#"}, "LLM_BASE_URL) deve essere un indirizzo http"),
    ({"HA_URL": "ftp://ha"}, "HA_URL) deve essere un indirizzo http"),
    ({"ATTESA_MAX": "inf"}, "ATTESA_MAX) deve essere un numero tra 1 e 7.5"),
    ({"ADMIN_HISTORY": "molti"}, "ADMIN_HISTORY must be a number"),
    ({"LANGUAGE": "fr"}, "LANGUAGE must be 'it' (Italian) or 'en' (English)"),
])
def test_configuration_errors_are_clear(env, message):
    r = _start(**env)
    assert r.returncode != 0 and message in r.stderr and "Traceback" not in r.stderr


def test_valid_configuration_starts_and_warns_about_a_bad_timezone():
    assert _start().returncode == 0
    assert _start(ADMIN_HISTORY="", ATTESA_MAX="7").returncode == 0      # empty = default
    assert _start(LANGUAGE="en").returncode == 0 and _start(LANGUAGE="EN").returncode == 0
    r = _start(HOME_TIMEZONE="Europe/Atlantide")
    assert r.returncode == 0 and "unknown HOME_TIMEZONE" in r.stderr


# ---------- Amazon's real certificate chain, with the real public roots
def test_real_amazon_certificate_chain_is_accepted():
    with open(os.path.join(DATA, "echo-api-cert-12.pem"), "rb") as f:
        certs = x509.load_pem_x509_certificates(f.read())
    quando = certs[0].not_valid_before_utc + dt.timedelta(days=30)        # inside its validity period
    assert APP.verifica_catena(certs, quando) is certs[0]
    with pytest.raises(VerificationError):
        APP.verifica_catena(certs, certs[0].not_valid_after_utc + dt.timedelta(days=1))   # expired
    with pytest.raises(VerificationError):
        APP.verifica_catena(certs[:1], quando)                             # intermediates missing


def test_certificate_is_downloaded_once(monkeypatch):
    scaricati = []
    monkeypatch.setattr(APP, "scarica", lambda u: scaricati.append(u) or b"")
    monkeypatch.setattr(APP, "verifica_catena", lambda certs: "leaf")
    monkeypatch.setattr(APP.x509, "load_pem_x509_certificates", lambda b: ["leaf"])
    APP._cache.clear()
    assert APP.cert_amazon("https://s3.amazonaws.com/echo.api/a.pem") == "leaf"
    assert APP.cert_amazon("https://s3.amazonaws.com/echo.api/a.pem") == "leaf" and len(scaricati) == 1
    APP._cache.clear()


def test_timestamp_checks(monkeypatch):
    class Cert:
        def public_key(self):
            class K:
                def verify(self, *a):
                    return None
            return K()
    monkeypatch.setattr(APP, "cert_amazon", lambda u: Cert())
    h = {"SignatureCertChainUrl": "https://s3.amazonaws.com/echo.api/a.pem", "Signature-256": "AA=="}
    now = dt.datetime.now(dt.timezone.utc)
    ok = {"session": {"application": {"applicationId": APP.SKILL_ID}}, "request": {"timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}
    assert APP.richiesta_valida(b"", h, ok) is None
    naive = json.loads(json.dumps(ok)); naive["request"]["timestamp"] = now.strftime("%Y-%m-%dT%H:%M:%S")
    assert APP.richiesta_valida(b"", h, naive) is None
    assert APP.richiesta_valida(b"", h, {"request": {}}) == "timestamp mancante"
    ctx = {"context": {"System": {"application": {"applicationId": APP.SKILL_ID}}}, "request": ok["request"]}
    assert APP.richiesta_valida(b"", h, ctx) is None                    # skill ID from context (no session)


def test_http_edge_cases():
    c = APP.app.test_client()
    assert c.post("/alexa", data=b"{not json").status_code == 400
    assert c.get("/alexa").status_code == 405 and c.get("/").status_code == 404


# ---------- conversation edge cases
def test_unknown_request_types_end_politely(alexa):
    r = alexa.req({"type": "Connections.Response"})
    assert alexa.said(r) == "Ciao!" and r["response"]["shouldEndSession"] is True


def test_user_id_from_context(alexa, llm):
    d = {"context": {"System": {"user": {"userId": "ctx-user"}}}, "request": {"type": "LaunchRequest"}}
    assert APP.utente(d) == "ctx-user" and APP.utente({}) == "anonimo"


def test_long_answers_are_cut_at_a_word(alexa, llm):
    llm.queue = [final("parola " * 200)]
    said = alexa.said(alexa.ask("raccontami tutto"))
    assert len(said) <= 701 and said.endswith("parola.")


def test_two_empty_answers(alexa, llm):
    empty = {"stop_reason": "end_turn", "content": []}
    llm.queue = [empty, empty]
    assert alexa.said(alexa.ask("x")).startswith("Non sono riuscito")


def test_old_jobs_are_cleaned_up(alexa, llm, monkeypatch):
    llm.delay = 1.2
    alexa.ask("prima")
    alexa.user = {"userId": "user-2"}
    monkeypatch.setattr(APP, "CONSERVA", 0)
    llm.delay = 0
    alexa.ask("seconda")
    assert "user-1" not in APP._lavori


def test_new_question_replaces_a_pending_one(alexa, llm):
    llm.delay = 1.3
    alexa.ask("prima domanda")
    vecchio = APP._lavori["user-1"]
    llm.delay = 0
    alexa.ask("seconda domanda")
    APP.consegna("user-1", vecchio, {})              # delivering the old one must not drop the new one
    assert "user-1" not in APP._lavori or APP._lavori["user-1"] is not vecchio


# ---------- model adapters: limits and rejections
def test_rejected_thinking_parameter_is_dropped_and_remembered(alexa, llm, monkeypatch):
    bodies = []
    def handle(body, path, headers):
        bodies.append(dict(body))
        if "thinking" in body:
            return 400, {"error": {"message": "thinking: unknown parameter"}}
        return 200, final("Ok.")
    monkeypatch.setattr(llm, "handle", handle)
    assert alexa.said(alexa.ask("x")) == "Ok." and "tools" in bodies[-1]
    assert LLM_MOD.STATO["strumenti"] is True and LLM_MOD.STATO["web_nativo"] is True and LLM_MOD.STATO["thinking"] is False
    n = len(bodies)
    alexa.ask("y")
    assert len(bodies) == n + 1 and "thinking" not in bodies[-1]       # no failed request first


def test_thinking_from_extra_json_is_respected(alexa, llm, monkeypatch):
    monkeypatch.setattr(LLM_MOD, "EXTRA", {"thinking": {"type": "enabled", "budget_tokens": 1024}})
    alexa.ask("x")
    assert llm.requests[-1]["thinking"] == {"type": "enabled", "budget_tokens": 1024}


def test_failure_reports_the_original_rejection(openai, monkeypatch):
    def handle(body, path, headers):
        return 400, {"error": "messages too long" if "tools" in body else "something else"}
    monkeypatch.setattr(openai, "handle", handle)
    tools = [{"name": "t", "description": "d", "parameters": {"type": "object", "properties": {}}}]
    with pytest.raises(LLM_MOD.Rifiutata, match="messages too long.*after adapting the request.*something else"):
        LLM_MOD.chiedi("s", [{"role": "user", "content": "x"}], tools, None, timeout=30)
    assert LLM_MOD.STATO["strumenti"] is True


def test_anthropic_tool_loop_is_bounded(alexa, llm):
    llm.queue = [tool_use("t%d" % i, "cerca_in_casa", {"testo": "luce"}) for i in range(LLM_MOD.MAX_ROUNDS + 1)]
    assert alexa.said(alexa.ask("x")) == "Un attimo." and len(llm.requests) == LLM_MOD.MAX_ROUNDS + 1


def test_anthropic_tool_use_without_tool_blocks(alexa, llm):
    llm.queue = [{"stop_reason": "tool_use", "content": [{"type": "text", "text": "Ecco."}]}]
    assert alexa.said(alexa.ask("x")) == "Ecco." and len(llm.requests) == 1


def test_openai_tool_loop_is_bounded(alexa, openai):
    openai.queue = [oa_tool_call("c%d" % i, "cerca_in_casa", {"testo": "luce"}) for i in range(LLM_MOD.MAX_ROUNDS + 1)]
    alexa.ask("x")       # 8 rounds, then no text: one more try (the echo answers)
    assert len(openai.requests) == LLM_MOD.MAX_ROUNDS + 2


def test_openai_empty_answer_is_retried(alexa, openai):
    openai.queue = [oa_final(""), oa_final("Seconda.")]
    assert alexa.said(alexa.ask("x")) == "Seconda."


# ---------- home tools: rare paths
def test_search_details_and_fallbacks():
    out = HOME.cerca("luce salone")
    assert "light.living_room | Luce salone | on | brightness=50%" in out
    assert "light.kitchen" in HOME.cerca("cucina inesistente")           # no entity has both words: any word
    assert HOME.cerca("zzz").startswith("Nessuna entita'")
    assert HOME._pick(["light.kitchen", "light.missing"])[0]["entity_id"] == "light.kitchen"


def test_unknown_tool(alexa, llm):
    llm.queue = [tool_use("t", "apri_tutto", {}), final("No.")]
    alexa.ask("x")
    assert last_tool_result(llm) == "Strumento sconosciuto."


def test_summary_with_a_temperature_pattern(monkeypatch):
    monkeypatch.setattr(HOME, "TEMP_PATTERN", r"sensor\.bedroom")
    assert "Temperature: Temperatura camera 18.9" in HOME.riepilogo()
    monkeypatch.setattr(HOME, "TEMP_PATTERN", r"sensor\.nothing")
    assert "Temperature:" not in HOME.riepilogo()


def test_forced_native_search_with_claude():
    assert WEB_MOD.backend("anthropic", "native") == "native"


def test_forbidden_list_covers_english_names_without_false_positives():
    for testo in ("cover.garage_door Garage door", "switch.gate_opener Gate", "switch.front_door Front Door",
                  "switch.alarm_siren Siren", "lock.x", "script.notte Notte", "switch.cancello Cancello"):
        assert HOME.VIETATO.search(testo), testo
    for testo in ("light.indoor Indoor lamp", "light.outdoor_garden Outdoor", "switch.gateway_lamp Lampada", "light.salone Salone"):
        assert not HOME.VIETATO.search(testo), testo


def test_custom_forbidden_regex_with_inline_flags():
    v = HOME._Vietato("(?i)Irrigazione")
    assert v.search("switch.irrigazione_orto Orto") and v.search("lock.front_door")


def test_discarding_keeps_a_newer_question(alexa, llm):
    llm.delay = 1.3
    alexa.ask("dal primo Echo")
    vecchio = APP._lavori["user-1"]
    alexa.ask("dal secondo Echo")
    APP.scarta("user-1", vecchio)                     # stale reference: the new question must survive
    assert APP._lavori["user-1"] is not vecchio
