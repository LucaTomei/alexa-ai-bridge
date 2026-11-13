"""Fixes from the 1.1.1 review: spoken consent, home safety, settings that redirect keys, odd requests."""
import json, os, subprocess, sys
import pytest
import conftest
from conftest import tool_use, final
from test_admin import client, anon, dati, post  # noqa: F401  (fixtures)
APP, ADMIN, IMP, HOME, L = conftest.APP, conftest.ADMIN, conftest.IMPOSTAZIONI, conftest.HOME, conftest.APP.L
SRC = os.path.join(os.path.dirname(__file__), "..", "src")


# ---------- a "yes" is a short answer, never a question that starts with "si"
@pytest.mark.parametrize("testo,ok", [
    ("sì", True), ("si'", True), ("certo, chiudile", True), ("va bene", True), ("sì, chiudile tutte", True), ("yes, go ahead", True),
    ("si possono chiudere tutte le tapparelle", False), ("vai a chiudere tutto quanto adesso", False), ("certo che no", False),
    ("sure, how is the weather today", False), ("ok?", False), ("no", False), ("sì ma non adesso", False)])
def test_short_yes_only(testo, ok):
    assert L.e_un_si(testo) is ok


def test_yes_counts_only_after_a_question(alexa, llm, ha):
    args = {"dominio": "cover", "servizio": "close_cover", "entita": ["cover.all_covers"], "confermato": True}
    llm.queue = [tool_use("t1", "esegui_azione", args), final("Fatto.")]
    alexa.ask("si possono chiudere tutte le tapparelle")            # first turn: nobody asked anything
    assert not ha.calls
    llm.queue = [tool_use("t2", "esegui_azione", args), final("Ok.")]
    alexa.ask("sì", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Fatto."}]})   # not after a question
    assert not ha.calls
    llm.queue = [tool_use("t3", "esegui_azione", args), final("Chiuse.")]
    alexa.ask("sì", {"h": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Le chiudo tutte?\n[azioni eseguite: y]"}]})
    assert ha.calls == [("/api/services/cover/close_cover", {"entity_id": ["cover.all_covers"]})]


# ---------- the confirmation limit counts every entity of the turn
def test_split_calls_still_need_a_yes(alexa, llm, ha, monkeypatch):
    monkeypatch.setattr(HOME, "MAX_SENZA_CONFERMA", 1)
    call = lambda i, e: tool_use(i, "esegui_azione", {"dominio": "light", "servizio": "turn_off", "entita": [e]})
    llm.queue = [call("a", "light.living_room"), call("b", "light.kitchen"), final("Spente.")]
    alexa.ask("spegni tutte le luci")
    assert ha.calls == [("/api/services/light/turn_off", {"entity_id": ["light.living_room"]})]


# ---------- garage and gate covers, scenes that would unlock a door
def test_garage_cover_and_unsafe_scene_are_forbidden(alexa, llm, ha):
    ha.states += [{"entity_id": "cover.box", "state": "closed", "attributes": {"friendly_name": "Basculante", "device_class": "garage"}},
                  {"entity_id": "scene.arrivo", "state": "scening", "attributes": {"friendly_name": "Arrivo", "entity_id": ["light.kitchen", "lock.front_door"]}},
                  {"entity_id": "scene.sera", "state": "scening", "attributes": {"friendly_name": "Sera", "entity_id": ["light.kitchen"]}}]
    for dom, srv, ent in (("cover", "open_cover", "cover.box"), ("scene", "turn_on", "scene.arrivo")):
        llm.queue = [tool_use("t", "esegui_azione", {"dominio": dom, "servizio": srv, "entita": [ent]}), final("No.")]
        alexa.ask("x")
        assert not ha.calls, ent
    assert "[NON COMANDABILE]" in HOME.cerca("basculante") and "[NON COMANDABILE]" in HOME.cerca("arrivo")
    llm.queue = [tool_use("t", "esegui_azione", {"dominio": "scene", "servizio": "turn_on", "entita": ["scene.sera"]}), final("Ok.")]
    alexa.ask("x")
    assert ha.calls == [("/api/services/scene/turn_on", {"entity_id": ["scene.sera"]})]


# ---------- a stolen session cannot send a stored key somewhere else
@pytest.mark.parametrize("valori", [
    {"LLM_BASE_URL": "https://attacker.example/v1", "LLM_API_KEY": None},
    {"HA_URL": "https://attacker.example", "HA_TOKEN": None},
    {"BRAVE_URL": "https://attacker.example/search"},
    {"TAVILY_URL": "https://attacker.example/search"},
])
def test_keys_never_follow_a_new_address(client, dati, valori):  # noqa: F811
    r = post(client, "impostazioni", {"valori": valori})
    assert r.status_code == 400 and "scrivi di nuovo" in r.json["errore"], r.json


def test_key_back_to_env_while_address_is_from_the_page(client, dati, monkeypatch):  # noqa: F811
    monkeypatch.setattr(IMP, "OVERRIDE", {"LLM_BASE_URL": "https://other.example/v1", "LLM_API_KEY": ""})
    monkeypatch.setattr(IMP, "BASE", {"LLM_BASE_URL": os.environ.get("LLM_BASE_URL"), "LLM_API_KEY": os.environ.get("LLM_API_KEY")})
    (dati / "settings.json").write_text(json.dumps({"LLM_BASE_URL": "https://other.example/v1", "LLM_API_KEY": ""}))
    r = post(client, "impostazioni", {"valori": {"LLM_API_KEY": None}})
    assert r.status_code == 400 and "scrivi di nuovo" in r.json["errore"], r.json


def test_password_reset_is_locked_out_too(client):  # noqa: F811
    for _ in range(6):
        post(client, "password", {"attuale": "sbagliata"}, method="DELETE")
    assert post(client, "password", {"attuale": "test-admin-password"}, method="DELETE").status_code == 429


@pytest.mark.parametrize("valore", ["3.0", "1e2", "+"])
def test_whole_numbers_are_digits(client, dati, valore):  # noqa: F811
    r = post(client, "impostazioni", {"valori": {"WEB_RESULTS": valore}})
    assert r.status_code == 400


# ---------- odd requests never hurt the service
def test_huge_body_is_refused_before_reading(anon):  # noqa: F811
    r = anon.post("/alexa", data=b"{" + b" " * (600 * 1024) + b"}", headers={"Signature-256": "x",
                  "SignatureCertChainUrl": "https://s3.amazonaws.com/echo.api/echo-api-cert.pem"})
    assert r.status_code == 413
    assert anon.post("/alexa", data=b"{}").status_code == 400


def test_history_failure_never_blocks_the_answer(alexa, llm, monkeypatch):
    def rotto(*a, **k):
        raise UnicodeEncodeError("utf-8", "x", 0, 1, "surrogates not allowed")
    monkeypatch.setattr(ADMIN, "registra", rotto)
    llm.queue = [final("Ecco.")]
    assert alexa.said(alexa.ask("domanda")) == "Ecco."


def test_broken_surrogate_is_stored(dati, monkeypatch):  # noqa: F811
    monkeypatch.setattr(ADMIN, "FILE_STORICO", str(dati / "history.json"))
    ADMIN.aggiungi_voce({"t": 1, "domanda": "\ud83d ciao", "risposta": "ok"})
    assert ADMIN.voci_storico()[-1]["domanda"] == "\ud83d ciao"


def test_control_characters_never_reach_the_speech():
    assert APP.pulisci("ciao\x00 a\x07 te\x1b") == "ciao a te"


def test_checks_speak_the_language_of_the_page(client, llm):  # noqa: F811
    llm.queue = [final("All good.")]
    client.post("/admin/api/prova/modello", headers={"X-CSRF": client.csrf, "X-Lang": "en"})
    assert llm.requests[-1]["system"].startswith("You are")


# ---------- settings from older versions keep working
def _avvia(**env):
    e = dict(os.environ, **env)
    return subprocess.run([sys.executable, "-c", "import lingua, llm; print(lingua.SCELTA, llm.API)"], cwd=SRC, env=e,
                          capture_output=True, text=True, timeout=60)


def test_language_as_locale_is_accepted():
    r = _avvia(LANGUAGE="en-US")
    assert r.returncode == 0 and r.stdout.split()[0] == "en", r.stderr


def test_empty_api_format_guesses_even_with_the_old_name():
    r = _avvia(LLM_API="", LLM_FORMAT="openai", LLM_BASE_URL="https://api.anthropic.com/v1")
    assert r.returncode == 0 and r.stdout.split()[1] == "anthropic", r.stderr
    env = dict(os.environ); env.pop("LLM_API", None)
    r = subprocess.run([sys.executable, "-c", "import llm; print(llm.API)"], cwd=SRC, capture_output=True, text=True, timeout=60,
                       env=dict(env, LLM_FORMAT="openai", LLM_BASE_URL="https://api.anthropic.com/v1"))
    assert r.stdout.strip() == "openai", r.stderr
