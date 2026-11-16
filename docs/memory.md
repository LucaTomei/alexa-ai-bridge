# Memory

On by default. The assistant remembers the people at home from one conversation to the next, and gets to know you
better over time:

> *"Ricordati che il sabato mattina andiamo in piscina."* … days later … *"Che faccio sabato?"*<br>
> *"Mi chiamo Anna."* (with voice profiles, see below) … *"Cosa mi consigli per cena?"* → it knows Anna is vegetarian.

Everything is in the admin page, **Memoria** tab: what it knows, fact by fact (edit, add, forget), the recognised
voices, the last exchanges it reads again, and every setting. Each setting can also go in `.env`
([reference](setup.md#configuration-reference)).

## What it remembers

| | How | Setting |
|---|---|---|
| **Facts** | One short sentence each, with the person it is about: *"Luca: takes his coffee without sugar"*, *"the cat is called Miro"*. The model saves one when you say something worth remembering or ask it to (*"ricordati che…"*), and forgets on request (*"dimentica…"*). | `MEMORIA_MAX` (100): beyond it the oldest go |
| **Learning by itself** | After every answer (never before: Alexa is not slowed down), a short background request asks the model which new facts the exchange teaches, or which older ones it replaces. It costs a few tokens per question; yes/no answers and short commands are skipped. | `MEMORIA_AUTO` (1) |
| **What to remember** | By default lasting facts about the people at home: names, relationships, tastes, habits, schedules, birthdays, pets, how they like answers. Never passing facts (the weather, a light that is on). | `MEMORIA_ISTRUZIONI` |
| **Earlier conversations** | The last exchanges of earlier conversations are read again, so *"come ti dicevo ieri"* makes sense. | `MEMORIA_RECENTI` (4), `MEMORIA_GIORNI` (7) |
| **Who is speaking** | When Alexa recognises the voice (below), the assistant learns the name that goes with it (*"mi chiamo Anna"*) and knows whom it is talking to. | – |

Every question carries what it knows, so the model uses it naturally, without listing it. `MEMORIA=0` switches
everything off (nothing is read, saved or sent) without deleting what was saved.

## Recognising voices

Alexa tells a skill who is speaking only when:

1. everyone at home has a **voice profile** in the Alexa app (*More → Settings → Your Profile → Voice ID*);
2. the skill has **personalization** on: Alexa developer console, your skill → **Build** → **Permissions** →
   switch on **Skill Personalization** (or add the permission `alexa::person_id:read` to the manifest).

Alexa then sends an anonymous ID for each recognised voice; the service keeps only a hash of it, with the name you
say. Without voice profiles, or for a voice it does not recognise, the memory still works for the whole household.
Recognising a voice is not authentication: it only personalises answers and never unlocks anything.

## Privacy

- Saved only in the data volume (`memory.json`, readable by the service only), never in the settings backup.
- **Passwords, PINs, codes, IBANs and similar are never saved**, whoever asks: those sentences are refused, and are
  not kept among the earlier exchanges either.
- It learns only from what you say, never from the assistant's answers (which may quote web pages), and the model
  gets what it knows as information, never as instructions.
- *"Dimentica…"* forgets the one fact that matches best: say it again for the next one. A damaged `memory.json` is
  kept aside as `memory.json.broken`, never overwritten.
- What it knows is sent to your model provider with every question, like the conversation itself: choose your
  provider accordingly, or switch learning off and keep only what you add from the page.
- Forget a single fact, a voice, the earlier exchanges or everything from the **Memoria** tab.
- The test chat of the admin page uses the memory and feeds it like the Echo; `scripts/e2e.py` never does.
