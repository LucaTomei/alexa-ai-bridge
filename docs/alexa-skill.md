# The Alexa skill

The skill comes in two languages. With `LANGUAGE=auto` (the default) one skill can have both, see
[below](#one-skill-both-languages); `LANGUAGE=it` or `en` answers in that language only.

| `LANGUAGE` | Skill locale | Interaction model | Invocation |
|---|---|---|---|
| `it` | Italian (IT) | [`skill/interaction-model.it-IT.json`](../skill/interaction-model.it-IT.json) | *"Alexa, apri cervellone"* |
| `en` | English (US), or any English locale | [`skill/interaction-model.en-US.json`](../skill/interaction-model.en-US.json) | *"Alexa, open big brain"* |

Paste it into **Build → Interaction Model → JSON Editor**, then **Save** and **Build skill**. The admin page offers
both files for download (**Sistema**). For English locales other than US (UK, Canada, Australia, India), add the
locale in the console and paste the same English model.

## One skill, both languages

With `LANGUAGE=auto` (the default) the service answers in the language of each request: Alexa tells it which locale
the Echo speaks. To make one skill speak Italian and English:

1. In the console, **Language Settings** (left menu of the **Build** tab, at the bottom) → add **English (US)** (and
   any other English locale) → **Save**.
2. Switch the language selector at the top of the console to English (US) → **Interaction Model → JSON Editor** →
   paste [`skill/interaction-model.en-US.json`](../skill/interaction-model.en-US.json) → **Save** → **Build skill**.
3. The endpoint is shared by every language: nothing else to set.

An Italian Echo opens it with *"Alexa, apri cervellone"*, an English one with *"Alexa, open big brain"*. Test the
English side in the simulator by choosing **English (US)** next to the text box.

## Keeping the interaction model up to date

The models in [`skill/`](../skill/) are versioned with the service. Every release in the
[changelog](../CHANGELOG.md) says whether they changed. Only then download the new file (admin page → **Sistema**, or
from the repository), paste it in the JSON Editor of each language, **Save** and **Build skill**.

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

## Translating the skill to another language

1. Copy the interaction model to your locale and translate invocation name, carrier phrases, short phrases and
   the Attesa/Stop samples.
2. Everything the service says or tells the model is in [`src/lingua.py`](../src/lingua.py): add your language to
   `LINGUE`, a column to `TESTI`, the words of `PAROLE_ATTESA`, `SI` (a *yes*) and `_NEGA` (a *no*), day and month
   names, and map your locale in `da_locale`.
