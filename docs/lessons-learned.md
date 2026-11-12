# Lessons learned

Fifteen problems we hit while building this, in the order you are likely to meet them, with the fix that is now
in the code.

## 1. The 8-second limit

**Symptom:** *"Non posso raggiungere la Skill richiesta"* on slow questions.

**Cause:** Alexa gives a skill about 8 seconds to answer; there is no setting to extend it.

**Fix:** each question runs in a background thread; the request waits `ATTESA_MAX` (≤ 7 s). If the answer is not
ready, Alexa says *"Ci sto pensando, dimmi allora"*; the answer is delivered on *"allora?"*, *"sì"*, or when the
skill is reopened within 15 minutes.

## 2. Free text needs a carrier phrase

**Symptom:** *"che tempo fa domani"* and *"accendi la luce"* end in *"non ho capito"*, while
*"domanda come si cucina il risotto"* works.

**Cause:** `AMAZON.SearchQuery` slots only match after a fixed word; a sample cannot be `{query}` alone.

**Fix:** 154 carrier phrases covering questions, requests, commands, follow-ups, articles and time words.

## 3. One-word follow-ups

**Symptom:** *"spegnila"* is not understood.

**Cause:** after removing a carrier there is nothing left for `{query}`.

**Fix:** `FraseBreveIntent` with a custom slot type listing 71 short phrases, passed to the model with the conversation.

## 4. The missing first word

**Symptom:** *"perché il cielo è blu"* → *"Sì, hai ragione, il cielo è blu!"*

**Cause:** Alexa removes the carrier from the slot; the model receives a statement.

**Fix:** every request reminds the model that the first word may be missing and that the sentence is a question.

## 5. Invocation names must survive speech recognition

**Symptom:** the skill opens in the simulator (typed) but the Echo says *"Purtroppo non so come aiutarti"*.

**Fix:** a plain word in the skill's language (`cervellone`). Always test the invocation by voice.

## 6. The interaction model was never saved

**Symptom:** every question is a fallback. **Check:** *Build → Intents* still lists `HelloWorldIntent`.

**Fix:** paste the JSON again, **Save**, then **Build skill**.

## 7. Reading the simulator

*JSON Input* empty → Alexa did not match the skill (invocation, build). *JSON Input* filled and *JSON Output* empty
→ Alexa matched the skill but your endpoint did not answer: check the network path and the service logs.

## 8. Cloudflare Bot Fight Mode blocks Alexa

**Symptom:** the endpoint answers `curl`, the health check is fine, but Alexa's requests never reach the reverse
proxy. A WAF *Skip* rule for the path records **0 events**: the block happens earlier.

**Fix:** a DNS-only record for the skill hostname (on paid plans, a Super Bot Fight Mode exception may work).

## 9. Cloudflare blocks Python's default user agent

**Symptom:** `curl` to Home Assistant gets 401 (reachable), Python gets **403**.

**Fix:** send an explicit user agent (`HTTP_USER_AGENT=alexa-ai-bridge/1.0`).

## 10. The official request-verification library would not load

**Symptom:** `LibraryNotFoundError: Error detecting the version of libcrypto` from `oscrypto` (pulled in by
`flask-ask-sdk` / `ask-sdk-webservice-support`) with recent OpenSSL 3 builds.

**Fix:** a 60-line verification with `cryptography`'s X.509 path validation, covered by tests.

## 11. Reasoning can leave nothing to say

**Symptom:** sometimes the answer is empty, or Alexa reads the model's reasoning aloud.

**Cause:**

- With Claude's extended thinking on and a small `max_tokens`, the thinking uses up the whole budget, so the
  response holds only a `thinking` block.
- Open reasoning models (DeepSeek R1, Qwen…) put their reasoning inside `<think>` tags.

**Fix:**

- `"thinking": {"type": "disabled"}` for Claude.
- `<think>…</think>` is removed before speaking.
- `reasoning_effort` can be set through `LLM_EXTRA_JSON`.
- `max_tokens` is 1024, and an empty answer gets one automatic retry (not after a home action: a second run could
  repeat it, and a `toggle` would undo itself).

## 12. A gateway's own system prompt wins

**Symptom:** *"I'm not a voice assistant, I'm a coding assistant…"* when you call a model through a gateway that
adds its own system prompt.

**Fix:** the voice rules are repeated inside each user turn, not only in `system`. Use the provider's official
API when you can.

## 13. Memory must include actions, not only words

**Symptom:** after *"accendi la luce"* (which worked), *"spegnila"* got *"earlier I said I turned it on without
actually sending the command"* — false.

**Cause:** the history stored only spoken text, so on the next turn there was no trace of the tool call.

**Fix:** assistant messages that ran actions carry `[azioni eseguite: …]` in the history; it is never spoken.

## 14. Confirmations must be enforced by the service

**Risk:** the model could set `confermato=true` on its own and close every shutter in the house.

**Fix:** a multi-room action runs only if the user's **last sentence** is a yes (*sì, certo, va bene, procedi…*).
*"Sì"* with nothing pending is passed to the model so it can complete the confirmation.

## 15. One `template:` key, not two

**Symptom:** after a Home Assistant restart, presence sensors and the "house empty" sensor are *unavailable* (and
the alarm automation that uses them silently stops working).

**Cause:** template covers for Alexa were added under a second `template:` key in `configuration.yaml`; YAML keeps
only the last one. The log says *"contains duplicate key"*, as a warning.

**Fix:** `template: !include_dir_merge_list templates`, one file per topic.
