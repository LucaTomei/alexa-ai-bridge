"""scripts/e2e.py runs its checks inside the container. Here the same checks run in a subprocess against the fake
model and the fake Home Assistant, with a scripted conversation: the script must report ALL OK and exit 0, and must
fail when the home does not do what the model says."""
import importlib.util, os, subprocess, sys
import pytest
from conftest import tool_use, final

ROOT = os.path.join(os.path.dirname(__file__), "..")
spec = importlib.util.spec_from_file_location("e2e", os.path.join(ROOT, "scripts", "e2e.py"))
E2E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E2E)


def _conversation():
    luce = {"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}
    return [
        final("Sono le dieci."),                                                              # ore sono
        {"stop_reason": "end_turn", "content": [                                              # tempo fa domani
            {"type": "server_tool_use", "name": "web_search", "input": {"query": "meteo"}},
            {"type": "web_search_tool_result", "content": []}, {"type": "text", "text": "Domani sole."}]},
        tool_use("t1", "riepilogo_casa", {}), final("In casa c'e' Alice."),                   # e la casa adesso
        tool_use("t2", "esegui_azione", luce), final("Accesa."),                              # accendi ...
        tool_use("t3", "esegui_azione", dict(luce, servizio="turn_off")), final("Spenta."),   # spegnila
        tool_use("t4", "esegui_azione", {"dominio": "cover", "servizio": "close_cover",       # chiudi tutte
                                         "entita": ["cover.all_covers"], "confermato": True}), final("Le chiudo tutte?"),
        final("Va bene, le lascio cosi'."),                                                   # no
        tool_use("t5", "esegui_azione", {"dominio": "lock", "servizio": "unlock", "entita": ["lock.front_door"]}),
        final("Non posso aprire la porta."),                                                  # apri la porta
    ]


def _run(tmp_path, lingua="it", **extra):
    script = tmp_path / "inner.py"
    script.write_text(E2E.INNER)
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), E2E_LIGHT="light.kitchen", LANGUAGE=lingua, **extra,
               E2E_LIGHT_NAME="la luce della cucina" if lingua == "it" else "the kitchen light", E2E_LOCK="lock.front_door")
    return subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("lingua", ["it", "en"])
def test_e2e_checks_pass_on_a_working_setup(llm, ha, tmp_path, lingua):
    llm.queue = _conversation()
    r = _run(tmp_path, lingua)
    assert r.returncode == 0 and "RESULT: ALL OK" in r.stdout, r.stdout + r.stderr
    assert "ERR" not in r.stdout and not llm.queue and ("language: %s" % lingua) in r.stdout
    assert [c[0] for c in ha.calls] == ["/api/services/light/turn_on", "/api/services/light/turn_off"]
    assert next(s for s in ha.states if s["entity_id"] == "lock.front_door")["state"] == "locked"


@pytest.mark.parametrize("crea", [False, True])
def test_e2e_automation_by_voice_must_not_be_created_after_no(llm, ha, tmp_path, crea):
    proposta = {"nome": "Cucina alle sette", "quando": {"tipo": "orario", "ora": "07:00"},
                "azioni": [{"dominio": "light", "servizio": "turn_on", "entita": ["light.kitchen"]}]}
    llm.queue = _conversation()[:-2] + [
        tool_use("t5", "esegui_azione", {"dominio": "lock", "servizio": "unlock", "entita": ["lock.front_door"]}),
        final("Non posso aprire la porta."),
        tool_use("t6", "crea_automazione", proposta), final("La creo, va bene?"),
        # after the "no" the model tries to confirm by itself: the service must refuse
        tool_use("t7", "crea_automazione", dict(proposta, confermato=True)) if crea else final("Va bene, niente."),
    ] + ([final("Creata.")] if crea else [])
    r = _run(tmp_path, HA_AUTOMAZIONI="1")
    assert "OK  automations: the token can write them" in r.stdout, r.stdout + r.stderr
    if not crea:
        assert r.returncode == 0 and "OK  automation by voice: read back, not created after 'no'" in r.stdout, r.stdout + r.stderr
        assert not ha.automations
    else:
        assert r.returncode == 0 and not ha.automations, r.stdout + r.stderr


def test_e2e_checks_fail_when_the_light_does_not_turn_on(llm, ha, tmp_path):
    conv = _conversation()
    conv[4] = final("Accesa.")                       # the model says so, but never calls the tool
    conv.pop(5)
    llm.queue = conv
    r = _run(tmp_path)
    assert r.returncode == 1 and "SOME CHECKS FAILED" in r.stdout
    assert "ERR turn the light on" in r.stdout


def test_runner_needs_docker(monkeypatch, capsys):
    monkeypatch.setattr(E2E.shutil, "which", lambda name: None)
    try:
        E2E.main()
        raise AssertionError("no exit")
    except SystemExit as e:
        assert "docker not found" in str(e)
