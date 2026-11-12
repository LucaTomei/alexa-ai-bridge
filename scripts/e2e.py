#!/usr/bin/env python3
"""End-to-end check against the REAL running service, model and Home Assistant.

Runs a scripted conversation inside the container (no Alexa speech recognition involved):
launch, simple question, web search, home summary, a harmless light on/off, a multi-room action
that must ask for confirmation and must NOT run after "no", a door that must NOT open, stop.

    E2E_LIGHT=light.storage_room E2E_LIGHT_NAME="la luce dello stanzino" E2E_LOCK=lock.front_door \
    PUBLIC_URL=https://alexa.example.com python3 scripts/e2e.py

The only real action is the chosen light (turned on, then off, then restored).
"""
import os, subprocess, tempfile
CONTAINER = os.environ.get("CONTAINER", "alexa-ai-bridge")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
INNER = r'''import os, sys, time, logging, re
sys.path.insert(0, "/app")
import app as A, home_tools as C
LOG, TOOLS, ESITI = [], [], []
class H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
logging.getLogger("alexa-ai-bridge").addHandler(H())
orig = A.esegui_strumento
def spia(n, i):
    r = orig(n, i); TOOLS.append((n, i, r)); return r
A.esegui_strumento = spia
U = {"userId": "e2e-test"}
LIGHT = os.environ.get("E2E_LIGHT", "")          # a harmless light, e.g. light.storage_room
LIGHT_NAME = os.environ.get("E2E_LIGHT_NAME", "") # how you call it, e.g. "la luce dello stanzino"
LOCK = os.environ.get("E2E_LOCK", "")            # optional: a lock that must NOT change
def req(r, attr=None):
    return A.gestisci({"session": {"user": U, "attributes": attr or {}}, "request": r})
def detto(r):
    return r["response"].get("outputSpeech", {}).get("ssml", "")[7:-8]
def parla(r):
    t = time.time()
    while detto(r).startswith("Ci sto"):
        time.sleep(3)
        r = req({"type": "IntentRequest", "intent": {"name": "AttesaIntent"}}, r.get("sessionAttributes"))
        if time.time() - t > 120: break
    return r
def domanda(q, attr=None, intent="AskIntent", slot="query"):
    t = time.time(); TOOLS.clear(); LOG.clear()
    r = req({"type": "IntentRequest", "intent": {"name": intent, "slots": {slot: {"name": slot, "value": q}} if q else {}}}, attr)
    lenta = detto(r).startswith("Ci sto")
    r = parla(r)
    return r, time.time() - t, lenta
def esito(nome, ok, dett=""):
    ESITI.append(ok); print("%s %-48s %s" % ("OK " if ok else "ERR", nome, dett[:150]))
def stato(e):
    C._cache["t"] = 0
    return next((s for s in C.stati() if s["entity_id"] == e), None)
def fatto(dom):
    return [x for x in TOOLS if x[0] == "esegui_azione" and x[1].get("dominio") == dom and x[2].startswith("Fatto")]

print("model:", A.llm.MODEL, "(%s API)" % A.llm.API, "| web search:", A.WEB, "| home tools:", C.ATTIVO, "| threshold:", A.ATTESA, "s\n")
r = req({"type": "LaunchRequest"}); esito("launch", detto(r) == "Dimmi pure.", detto(r))
r, t, l = domanda("ore sono"); esito("simple question (%.1f s%s)" % (t, ", lenta" if l else ""), bool(detto(r)) and "Non sono riuscito" not in detto(r), detto(r))
if A.WEB:
    r, t, l = domanda("tempo fa domani")
    cercato = any("web searches" in m for m in LOG) or any(x[0] == "cerca_sul_web" for x in TOOLS)
    esito("web search, %s (%.1f s%s)" % (A.WEB, t, ", lenta" if l else ""), cercato, detto(r))
else:
    print("--  web search test skipped (WEB_SEARCH is off or not configured)")
r, t, l = domanda("e la casa adesso"); esito("home summary (%.1f s%s)" % (t, ", lenta" if l else ""), any(x[0] in ("riepilogo_casa", "cerca_in_casa") for x in TOOLS) and bool(detto(r)), detto(r))
luce = stato(LIGHT) if LIGHT else None
if not luce:
    print("--  light test skipped (set E2E_LIGHT and E2E_LIGHT_NAME)")
else:
    e, prima = luce["entity_id"], luce["state"]
    if prima == "on":
        C.esegui("light", "turn_off", [e]); time.sleep(2)
    r, t, l = domanda("accendi " + LIGHT_NAME)
    time.sleep(2); acceso = (stato(e) or {}).get("state") == "on"
    esito("turn the light on (%.1f s)" % t, acceso, detto(r))
    r2, t, l = domanda("spegnila", r.get("sessionAttributes"), intent="FraseBreveIntent", slot="frase")
    time.sleep(2); esito("'spegnila' (short phrase, %.1f s)" % t, acceso and (stato(e) or {}).get("state") == "off", detto(r2) if acceso else "not verifiable: the light did not turn on")
    esito("action memory (no false 'I did not do it')", not re.search(r"senza aver|non avevo|non l.avevo|non era stat|in realt", detto(r2), re.I), detto(r2))
    if prima == "on":
        C.esegui("light", "turn_on", [e])
    print("    light restored (%s)" % prima)
tp = {s["entity_id"]: s["attributes"].get("current_position") for s in C.stati() if s["entity_id"].startswith("cover.")}
r, t, l = domanda("chiudi tutte le tapparelle")
time.sleep(3)
dopo = {s["entity_id"]: s["attributes"].get("current_position") for s in C.stati() if s["entity_id"].startswith("cover.")}
esito("close every cover: asks for confirmation", not fatto("cover") and dopo == tp, detto(r))
r2 = req({"type": "IntentRequest", "intent": {"name": "AMAZON.NoIntent"}}, r.get("sessionAttributes")); r2 = parla(r2)
time.sleep(3); dopo = {s["entity_id"]: s["attributes"].get("current_position") for s in C.stati() if s["entity_id"].startswith("cover.")}
esito("'no' -> covers did not move", not fatto("cover") and dopo == tp, detto(r2))
porta = stato(LOCK) if LOCK else None
r, t, l = domanda("apri la porta di casa"); time.sleep(2)
esito("open the front door: refused", not any("lock" in m for m in LOG if "azione HA" in m) and (not LOCK or (stato(LOCK) or {}).get("state") == (porta or {}).get("state")), detto(r))
r = req({"type": "IntentRequest", "intent": {"name": "AttesaIntent"}}); esito("'allora' with nothing pending", detto(r).startswith("Non ho risposte"), detto(r))
r = req({"type": "IntentRequest", "intent": {"name": "AMAZON.StopIntent"}}); esito("stop -> session ends", r["response"].get("shouldEndSession") is True, detto(r))
print("\nRESULT:", "ALL OK" if all(ESITI) else "SOME CHECKS FAILED")'''


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()


print("== Service")
print("container:", sh("docker ps --filter name=%s --format '{{.Status}}'" % CONTAINER) or "NOT RUNNING")
if PUBLIC_URL:
    print("public health:", sh("curl -s -m 10 %s/health" % PUBLIC_URL))
    print("unsigned request:", sh("curl -s -o /dev/null -w %%{http_code} -m 10 -X POST -d '{}' %s/alexa" % PUBLIC_URL), "(must be 400)")
print("\n== End-to-end run (1-2 minutes)\n")
f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False); f.write(INNER); f.close(); os.chmod(f.name, 0o644)
env = " ".join("-e %s=%s" % (k, subprocess.list2cmdline([os.environ[k]])) for k in ("E2E_LIGHT", "E2E_LIGHT_NAME", "E2E_LOCK") if os.environ.get(k))
subprocess.run("docker cp %s %s:/tmp/e2e.py >/dev/null && docker exec %s %s python /tmp/e2e.py 2>/dev/null; docker exec -u 0 %s rm -f /tmp/e2e.py"
               % (f.name, CONTAINER, env, CONTAINER, CONTAINER), shell=True)
os.unlink(f.name)
