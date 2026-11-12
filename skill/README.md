# Interaction models

| File | Console language | Invocation |
|---|---|---|
| `interaction-model.it-IT.json` | Italian (IT) | *"Alexa, apri cervellone"* |
| `interaction-model.en-US.json` | English (US), or any English locale | *"Alexa, open big brain"* |

Paste each one in **Build → Interaction Model → JSON Editor** of the matching language, then **Save** and
**Build skill**. With `LANGUAGE=auto` one skill can have both. The admin page offers them for download (**Sistema**).

They are versioned with the service: each release in [`CHANGELOG.md`](../CHANGELOG.md) says whether they changed
(*Interaction model: unchanged* means there is nothing to do in the Alexa console). Guide:
[`docs/alexa-skill.md`](../docs/alexa-skill.md).
