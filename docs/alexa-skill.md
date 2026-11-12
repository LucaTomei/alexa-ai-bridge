# The Alexa skill

The whole interaction model is in [`skill/interaction-model.it-IT.json`](../skill/interaction-model.it-IT.json).
Paste it into **Build → Interaction Model → JSON Editor**, then **Save** and **Build skill**.

## Intents

| Intent | Samples | What the service does |
|---|---|---|
| `AskIntent` | `{query}` after one of **154 carrier phrases** | sends the question to the model |
| `FraseBreveIntent` | `{frase}`, a custom type with **71 short phrases** | sends the phrase to the model, with the conversation |
| `AttesaIntent` | *allora, hai finito, sei pronto, quindi…* | delivers a pending slow answer |
| `AMAZON.YesIntent` | built-in | delivers a pending answer, otherwise sends *"sì"* to the model (confirmations) |
| `AMAZON.NoIntent` | built-in | discards a pending answer, otherwise sends *"no"* to the model |
| `AMAZON.StopIntent` | built-in + *ciao, grazie, ho finito, a posto così, buonanotte…* | ends the session |
| `AMAZON.Help/Cancel/Fallback/NavigateHome` | built-in | help, end, "non ho capito" |

## Carrier phrases

`AMAZON.SearchQuery` is the only way to get free text from Alexa, and it has a hard rule: **a sample cannot be
just `{query}`**. There must be at least one word before it, and the user's sentence must start with one of those
words. Alexa then removes that word from the slot value.

The skill therefore lists 154 openings that cover how people actually start sentences in Italian:

- questions: *che, chi, come, cosa, perché, quanto, quando, dove, quale, a che ora, c'è, è…*
- requests: *dimmi, spiegami, raccontami, cerca, consigliami, vorrei, dammi, puoi, per favore…*
- commands: *accendi, spegni, apri, chiudi, alza, abbassa, metti, imposta, attiva, regola, ferma…*
- follow-ups: *e, e se, ma, anche, allora dimmi…*
- articles and time words: *il, la, un, una, oggi, domani, stasera, ieri…*

Because Alexa drops the opening word (*"perché il cielo è blu"* arrives as *"il cielo è blu"*), every request
tells the model to treat the sentence as a question, never as a statement to confirm.

## Short phrases

One-word follow-ups (*"spegnila"*) cannot match `{query}`: there is nothing after the carrier. They are handled by
`FraseBreveIntent`, whose only sample is `{frase}` with a custom slot type listing pronoun forms and common short
replies:

> spegnila · accendile · alzala · abbassale · di più · di meno · a metà · anche quella · più caldo · ripeti ·
> spiegati meglio · in breve · va bene · buongiorno …

The service passes the phrase to the model together with the conversation, so *"spegnila"* turns off the light that
was just turned on.

## Invocation name

`cervellone` (*"big brain"*). Lessons:

- Test the name **by voice**. A brand-like name worked when typed in the simulator, but the Echo answered
  *"Purtroppo non so come aiutarti"* because speech recognition never produced it.
- If the simulator answers *"Non posso raggiungere la Skill richiesta"* and the **JSON Input** panel is filled,
  Alexa matched your skill but your endpoint did not answer: look at the network path (see
  [lessons learned](lessons-learned.md)).
- If the **JSON Input** panel is empty, Alexa did not match the skill at all: invocation name or build.

## Translating the skill

1. Copy the interaction model to your locale and translate invocation name, carrier phrases, short phrases and
   the Attesa/Stop samples.
2. Translate the spoken strings in `src/app.py` (`risposta(...)` calls, `AIUTO`, `PAROLE_ATTESA`) and the voice
   rules (`SYSTEM_PROMPT`, `ISTRUZIONI_TURNO`, overridable from `.env`).
3. Adjust the "yes" regular expression (`SI`) in `src/home_tools.py`.
