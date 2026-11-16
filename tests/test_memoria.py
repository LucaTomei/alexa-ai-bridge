"""Memory: facts saved by voice and learned by itself, never secrets, used in the next conversations; recognised voices;
the earlier exchanges; everything off with MEMORIA=0; the Memory tab of the admin page."""
import json, os, threading, time
import pytest
import conftest
from conftest import tool_use, final
APP, M, ADMIN = conftest.APP, conftest.MEMORIA, conftest.ADMIN


def istruzioni(llm):
    """The instructions of the last question (they lead the last user turn that is text)."""
    testo = [m["content"] for m in llm.requests[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], str)][-1]
    return testo.split("\n\n")[0]


def aspetta():
    for t in threading.enumerate():
        if getattr(t, "_target", None) is APP.calcola:
            t.join(5)


def test_saved_by_voice_and_used_in_the_next_conversation(alexa, llm):
    llm.queue = [tool_use("t1", "ricorda", {"fatto": "prende il caffè senza zucchero", "persona": "Luca"}), final("Me lo ricordo.")]
    assert alexa.said(alexa.ask("ricordati che prendo il caffè senza zucchero")) == "Me lo ricordo."
    assert conftest.last_tool_result(llm) == "Salvato in memoria."
    f = M.fatti()
    assert [(x["testo"], x["persona"], x["fonte"]) for x in f] == [("prende il caffè senza zucchero", "Luca", "voce")]
    assert oct(os.stat(M.FILE).st_mode & 0o777) == "0o600"
    alexa.ask("fammi un caffè")                               # a new conversation, no history
    t = istruzioni(llm)
    assert "Cosa sai di chi abita in casa: Luca: prende il caffè senza zucchero." in t and "Hai una memoria" in t
    assert [x["name"] for x in llm.requests[-1]["tools"]][-2:] == ["ricorda", "dimentica"]


def test_never_secrets(alexa, llm):
    for fatto in ("il codice dell'allarme è 1234", "la password del wifi è pippo", "il PIN del bancomat è 5555"):
        llm.queue = [tool_use("t", "ricorda", {"fatto": fatto}), final("No.")]
        alexa.ask("ricordatelo")
        assert conftest.last_tool_result(llm).startswith("Non salvato")
    assert M.fatti() == []


def test_duplicates_forgetting_and_the_limit(alexa, llm, monkeypatch):
    assert M.aggiungi("Anna è la sorella di Luca")[0] == "nuovo"
    assert M.aggiungi("anna è la sorella di luca")[0] == "gia"
    llm.queue = [tool_use("t", "dimentica", {"fatto": "sorella Anna"}), final("Dimenticato.")]
    alexa.ask("dimentica quello che sai di Anna")
    assert conftest.last_tool_result(llm) == "Dimenticato: Anna è la sorella di Luca." and M.fatti() == []
    llm.queue = [tool_use("t", "dimentica", {"fatto": "il cane"}), final("Non c'è.")]
    alexa.ask("dimentica il cane")
    assert conftest.last_tool_result(llm) == "Niente del genere in memoria."
    monkeypatch.setattr(M, "MAX", 3)
    for i in range(5):
        M.aggiungi("fatto numero %d" % i)
    assert [f["testo"] for f in M.fatti()] == ["fatto numero 2", "fatto numero 3", "fatto numero 4"]


def test_earlier_exchanges(alexa, llm, monkeypatch):
    alexa.ask("quanto dista Roma da Milano")
    aspetta()
    alexa.ask("e in treno?")                                  # a new conversation: the earlier exchange is read again
    t = istruzioni(llm)
    assert "Conversazioni precedenti" in t and "quanto dista Roma da Milano -> R1 su: quanto dista Roma da Milano" in t
    aspetta()
    # not twice: what is already in this conversation is not repeated
    h = [{"role": "user", "content": "quanto dista Roma da Milano"}, {"role": "assistant", "content": "500 km"}]
    alexa.ask("e in treno?", {"h": h})
    assert "quanto dista Roma da Milano ->" not in istruzioni(llm) and "e in treno? -> R1" in istruzioni(llm)
    aspetta()
    d = M.leggi()
    for s in d["scambi"]:
        s["t"] = time.time() - 8 * 86400                      # older than MEMORIA_GIORNI
    M._scrivi(d)
    alexa.ask("ciao")
    assert "quanto dista" not in istruzioni(llm)
    monkeypatch.setattr(M, "RECENTI", 0)
    M.svuota("scambi")
    alexa.ask("una domanda qualsiasi")
    aspetta()
    assert M.leggi()["scambi"] == []


def _con_voce(q, person="amzn1.ask.person.ABC"):
    return APP.gestisci({"session": {"user": {"userId": "u"}, "attributes": {}},
                         "context": {"System": {"person": {"personId": person}}},
                         "request": {"type": "IntentRequest", "intent": {"name": "AskIntent", "slots": {"query": {"value": q}}}}})


def test_recognised_voices(llm):
    llm.queue = [tool_use("t", "chi_parla", {"nome": "Luca"}), final("Piacere Luca.")]
    _con_voce("sono Luca")
    assert "non sai ancora chi e'" in istruzioni(llm) and "chi_parla" in [x["name"] for x in llm.requests[0]["tools"]]
    assert conftest.last_tool_result(llm) == "Ora la voce di chi parla e' associata a Luca."
    _con_voce("che ore sono")
    assert "Sta parlando Luca." in istruzioni(llm)
    assert "amzn1.ask.person" not in open(M.FILE, encoding="utf-8").read()   # only a hash of Alexa's id is kept
    _con_voce("e tu chi sei", "amzn1.ask.person.ALTRO")
    assert "Sta parlando" not in istruzioni(llm)
    # a request without a recognised voice never inherits the previous one (threads are reused)
    APP.gestisci({"session": {"user": {"userId": "u"}, "attributes": {}},
                  "request": {"type": "IntentRequest", "intent": {"name": "AskIntent", "slots": {"query": {"value": "ciao"}}}}})
    assert "Sta parlando" not in istruzioni(llm) and "chi_parla" not in [x["name"] for x in llm.requests[-1]["tools"]]


def test_learns_by_itself_after_the_answer(alexa, llm, monkeypatch):
    monkeypatch.setattr(M, "AUTO", True)
    M.aggiungi("Luca abita a Torino")
    vecchio = M.fatti()[0]["id"]
    llm.queue = [final("Ottima scelta."),
                 final('Ecco: [{"fatto": "Luca ha un gatto di nome Miro", "persona": "Luca"}, '
                       '{"fatto": "Luca abita a Milano", "persona": "Luca", "sostituisce": "%s"}, '
                       '{"fatto": "la password del wifi è x"}, {"nonsense": 1}, "x"]' % vecchio)]
    assert alexa.said(alexa.ask("ho appena adottato un gatto che si chiama Miro e mi sono trasferito a Milano")) == "Ottima scelta."
    aspetta()
    estrazione = llm.requests[-1]
    assert "Gia' in memoria" in estrazione["messages"][0]["content"] and vecchio in estrazione["messages"][0]["content"]
    assert "tools" not in estrazione and estrazione["system"].startswith("Estrai fatti")
    assert sorted(f["testo"] for f in M.fatti()) == ["Luca abita a Milano", "Luca ha un gatto di nome Miro"]
    assert {f["fonte"] for f in M.fatti()} == {"auto"}
    # short answers ("sì", "allora?") never cost a request
    n = len(llm.requests)
    alexa.ask("sì grazie")
    aspetta()
    assert len(llm.requests) == n + 1
    # a broken answer from the model teaches nothing and breaks nothing
    llm.queue = [final("Ok."), final("non è JSON")]
    alexa.ask("mi piace molto il jazz degli anni cinquanta")
    aspetta()
    assert len(M.fatti()) == 2


def test_custom_instructions_for_learning(alexa, llm, monkeypatch):
    monkeypatch.setattr(M, "AUTO", True)
    monkeypatch.setattr(M, "ISTRUZIONI", "solo i compleanni")
    llm.queue = [final("Ok."), final("[]")]
    alexa.ask("domani è il compleanno di mia madre Rosa")
    aspetta()
    assert llm.requests[-1]["messages"][0]["content"].startswith("Cosa ricordare: solo i compleanni.") and M.fatti() == []


def test_memory_off(alexa, llm, monkeypatch):
    M.aggiungi("Luca ama il jazz")
    monkeypatch.setattr(M, "ATTIVA", False)
    monkeypatch.setattr(M, "AUTO", True)
    alexa.ask("che musica mi piace di solito")
    aspetta()
    assert "jazz" not in istruzioni(llm) and "ricorda" not in [x["name"] for x in llm.requests[-1]["tools"]]
    assert len(llm.requests) == 1 and M.leggi()["scambi"] == []
    assert M.esegui("ricorda", {"fatto": "x"}) == "La memoria e' spenta."


def test_english(alexa, llm, monkeypatch):
    conftest.APP.L.imposta("en")
    M.aggiungi("Luca loves jazz", "Luca")
    try:
        assert "What you know about the people at home: Luca: Luca loves jazz." in M.contesto([])
    finally:
        conftest.APP.L.imposta(None)


# ---------- admin page
@pytest.fixture
def client():
    c = APP.app.test_client()
    c.csrf = c.post("/admin/api/login", json={"password": "test-admin-password"}).json["csrf"]
    return c


def post(c, path, body=None):
    return c.post("/admin/api/" + path, json=body, headers={"X-CSRF": c.csrf})


def test_memory_tab(client, llm):
    assert post(client, "memoria/fatto", {"testo": "Anna è vegetariana", "persona": "Anna"}).status_code == 200
    assert post(client, "memoria/fatto", {"testo": "il codice dell'allarme è 1"}).status_code == 400
    assert post(client, "memoria/fatto", {"testo": "   "}).status_code == 400
    d = client.get("/admin/api/memoria").json
    assert d["attiva"] and d["auto"] is False and d["max"] == 100 and d["recenti"] == 4 and d["giorni"] == 7
    f = d["fatti"][0]
    assert (f["testo"], f["persona"], f["fonte"]) == ("Anna è vegetariana", "Anna", "pannello")
    assert post(client, "memoria/fatto", {"id": f["id"], "testo": "Anna è vegana", "persona": "Anna"}).status_code == 200
    assert M.fatti()[0]["testo"] == "Anna è vegana"
    assert post(client, "memoria/fatto", {"id": "nessuno", "testo": "x"}).status_code == 404
    assert post(client, "memoria/elimina", {"id": f["id"]}).status_code == 200 and M.fatti() == []
    assert post(client, "memoria/elimina", {"id": f["id"]}).status_code == 404
    # voices
    M.imposta_voce("abc", "Luca")
    assert client.get("/admin/api/memoria").json["voci"] == [{"id": "abc", "nome": "Luca"}]
    assert post(client, "memoria/voce", {"id": "abc", "nome": "Luca T."}).status_code == 200 and M.nome_voce("abc") == "Luca T."
    assert post(client, "memoria/voce", {"id": "abc", "nome": ""}).status_code == 200 and M.leggi()["voci"] == {}
    assert post(client, "memoria/voce", {"id": "zzz", "nome": "x"}).status_code == 404
    # clearing
    M.aggiungi("uno"); M.registra_scambio("domanda", "risposta")
    assert post(client, "memoria/svuota", {"cosa": "fatti"}).status_code == 200 and M.fatti() == [] and M.leggi()["scambi"]
    assert client.get("/admin/api/memoria").json["scambi"][0]["domanda"] == "domanda"
    assert post(client, "memoria/svuota", {"cosa": "tutto"}).status_code == 200 and M.leggi() == M._vuota()
    assert post(client, "memoria/svuota", {"cosa": "x"}).status_code == 400
    for corpo in (None, [], {"testo": 1}, {"testo": "x", "persona": 2}):
        assert post(client, "memoria/fatto", corpo).status_code == 400


def test_memory_tab_saves(client, monkeypatch):
    salvati = []
    monkeypatch.setattr(ADMIN, "_salva", lambda cambi: (salvati.append(cambi), ({"ok": True, "riavvio": False}, 200))[1])
    r = post(client, "memoria", {"attiva": True, "auto": False, "max": 50, "recenti": "0", "giorni": 3, "istruzioni": "i gusti"})
    assert r.status_code == 200 and salvati[-1] == {"MEMORIA": "1", "MEMORIA_AUTO": "0", "MEMORIA_MAX": "50", "MEMORIA_RECENTI": "0",
                                                    "MEMORIA_GIORNI": "3", "MEMORIA_ISTRUZIONI": "i gusti"}
    for corpo in ({"attiva": 1, "auto": False, "max": 1, "recenti": 1, "giorni": 1, "istruzioni": ""},
                  {"attiva": True, "auto": False, "max": True, "recenti": 1, "giorni": 1, "istruzioni": ""},
                  {"attiva": True, "auto": False, "max": 1, "recenti": 1, "giorni": 1}, []):
        assert post(client, "memoria", corpo).status_code == 400


def test_the_test_chat_uses_and_feeds_the_memory(client, llm, monkeypatch):
    monkeypatch.setattr(M, "AUTO", True)
    M.aggiungi("Luca ama il jazz")
    llm.queue = [final("Jazz, direi."), final('[{"fatto": "Luca suona il sassofono"}]')]
    r = post(client, "chat", {"testo": "che musica potrei ascoltare stasera", "storia": []}).json
    assert r["risposta"] == "Jazz, direi." and "Luca ama il jazz" in llm.requests[0]["messages"][-1]["content"]
    for _ in range(100):
        if len(M.fatti()) == 2:
            break
        time.sleep(0.05)
    assert [f["testo"] for f in M.fatti()] == ["Luca ama il jazz", "Luca suona il sassofono"]


def test_a_broken_file_is_an_empty_memory():
    with open(M.FILE, "w") as f:
        f.write("{broken")
    assert M.leggi() == M._vuota()
    with open(M.FILE, "w") as f:
        json.dump({"fatti": [{"id": "a", "testo": "ok"}, {"testo": 3}, "x"], "voci": {"a": 1}, "scambi": [{"d": "q"}, 5]}, f)
    d = M.leggi()
    assert [x["id"] for x in d["fatti"]] == ["a"] and d["voci"] == {} and len(d["scambi"]) == 1


@pytest.mark.parametrize("intento,valore,inviato", [
    ("RicordaIntent", "che il sabato andiamo in piscina", "ricordati che il sabato andiamo in piscina"),
    ("TiRicordiIntent", "come si chiama il gatto", "ti ricordi come si chiama il gatto"),
    ("DimenticaIntent", "la piscina", "dimentica la piscina"),
    ("PresentaIntent", "Anna", "mi chiamo Anna"),
])
def test_memory_intents_put_the_opening_word_back(alexa, llm, intento, valore, inviato):
    r = alexa.req({"type": "IntentRequest", "intent": {"name": intento, "slots": {"query": {"value": valore}}}})
    assert alexa.said(r).startswith("R1 su: " + inviato)
    assert alexa.said(alexa.req({"type": "IntentRequest", "intent": {"name": intento, "slots": {}}})) == "Non ho capito, puoi ripetere?"


def test_memory_intents_in_english(alexa, llm):
    r = APP.gestisci({"session": {"user": {"userId": "u"}, "attributes": {}},
                      "request": {"type": "IntentRequest", "locale": "en-US",
                                  "intent": {"name": "RicordaIntent", "slots": {"query": {"value": "that I like jazz"}}}}})
    assert alexa.said(r).startswith("R1 su: remember that I like jazz")
