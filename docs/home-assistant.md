# Home Assistant tools

Optional. Without `HA_TOKEN` the tools are simply not offered to the model.

## The three tools

| Tool | What the model gets |
|---|---|
| `riepilogo_casa` | people home/away, lights on, covers with position, temperatures, climate, plus your `HA_SUMMARY_EXTRA` lines (power meter, front door, rain…) |
| `cerca_in_casa(testo)` | matching entities: `entity_id | name | state | key attributes`; forbidden ones are marked `[NON COMANDABILE]` |
| `esegui_azione(dominio, servizio, entita, dati, confermato)` | runs one service call, after every check below |

## Rules enforced by the service (not by the prompt)

1. **Allowed services only**: `light` on/off/toggle, `cover` open/close/stop/position, `climate` on/off/temperature/mode,
   `switch`, `fan`, `humidifier`, `scene.turn_on`.
2. **Forbidden entities** (regex on entity ID *and* friendly name): locks, alarms, scripts, automations,
   anything named like a door, gate or alarm in Italian or English (*porta, portone, cancello, allarme, door, gate,
   garage door, siren…*), covers whose device class is *garage*, *gate* or *door* whatever their name, scenes that
   include a forbidden entity, and technical services (containers, Zigbee, MQTT broker, NVR, backups…).
   `HA_VIETATO` **adds** your own regex to this list, e.g. `HA_VIETATO=garage|irrigazione`; it can never remove
   a built-in rule. The check is on names: a switch that opens the gate but is called *"relay 3"* is not caught,
   so give such entities a descriptive name or list them in `HA_VIETATO`.
3. **Explicit targets**: every entity must exist and belong to the requested domain; `all` is refused.
4. **Allowed data keys only**: `brightness_pct`, `position`, `temperature`, `hvac_mode`, `humidity`,
   `color_temp_kelvin`, `rgb_color`. Anything else (e.g. an `entity_id` smuggled into `dati`) is dropped.
5. **Spoken confirmation for multi-room actions**: more than `HA_MAX_SENZA_CONFERMA` entities in one answer (split
   calls count together), or any entity in `HA_GRUPPI`, runs only if `confermato=true` **and the user's last
   sentence is a short yes** (*sì, certo, va bene, procedi…*, at most four words, no *no/non*) **answering a question
   of the assistant**. The model cannot confirm on its own, and *"si possono chiudere le tapparelle?"* is not a yes.
6. **Every executed action is logged** (`azione HA: …`) and recorded in the conversation memory.

> ⚠️ **Scenes** run whatever they contain. A scene whose members include a forbidden entity is refused, but only if
> Home Assistant lists its members (scenes made in the UI do). A scene that changes several rooms still needs no
> confirmation: list it in `HA_GRUPPI` (or set *always ask* in the admin page's **Casa** tab).

## Automations by voice

Optional, **off by default**. With it on, you can ask for automations the way you would describe them:

> 🗣️ *"Ogni sera al tramonto chiudi la tapparella della camera."*<br>
> 🔊 *"Creo un'automazione che al tramonto chiude la tapparella della camera, tutti i giorni. Va bene?"*<br>
> 🗣️ *"Sì."* — 🔊 *"Fatto, l'ho creata."*<br>
> 🗣️ *"Quali automazioni hai creato?"* · *"Disattiva quella della camera."* · *"Eliminala."* (asks first)

Three more tools are offered to the model:

| Tool | What it does |
|---|---|
| `crea_automazione(nome, quando, giorni, azioni, confermato)` | creates an automation, after the summary was read to you and you said *yes* |
| `elenca_automazioni` | lists the automations created by voice, with state, last run and summary |
| `gestisci_automazione(automazione, operazione, confermato)` | enables, disables or deletes one of them (deleting asks first) |

What can start an automation (`quando`):

| `tipo` | Example | In Home Assistant |
|---|---|---|
| `orario` | *"ogni giorno alle 7"*, *"il sabato alle 9"* (`giorni`) | time trigger, optional weekday condition |
| `sole` | *"al tramonto"*, *"mezz'ora prima dell'alba"* | sun trigger with offset (up to 3 hours) |
| `stato` | *"quando la porta di casa si apre"*, *"quando esco"*, *"se la lavatrice resta spenta per 5 minuti"* | state trigger (`to`, `from`, `for`) |
| `soglia` | *"quando la temperatura della camera scende sotto 18"* | numeric state trigger (`above`, `below`) |

Up to five actions, each **checked exactly like `esegui_azione`**: allowed services only, explicit entities that
exist, no forbidden entity (locks, doors, alarms, scripts, automations, technical services, `HA_VIETATO`, the
entities forbidden from the **Casa** tab), allowed data keys only. Any entity can be the *trigger* (reading the
front door is fine), never the *action*.

Rules enforced by the service:

1. **Always a spoken yes.** The first call only returns a summary, which the model reads to you. The automation is
   created only when the same call comes back with `confermato=true` **after your short yes** to that question, and
   only if it is **exactly** the automation summarised, in an earlier turn of the conversation (a proposal is valid
   for 15 minutes): the model cannot change it after asking, nor propose and confirm it in one go. Deleting works
   the same way.
2. **Only its own automations.** Each one gets an id starting with `aab_`, an alias starting with `Alexa: ` and a
   description saying it was created by voice. The assistant lists, enables, disables and deletes only those;
   the automations you made by hand are invisible to it.
3. **A limit**: at most `HA_AUTOMAZIONI_MAX` (20) automations by voice; names must be unique.
4. The test chat of the admin page only **simulates** them, like the other home actions.
5. Every one is logged and recorded in the conversation history.

### Switching it on

Home Assistant lets only **administrators** create and delete automations (its configuration API). Keep the
everyday token non-admin and give the service a second one, used only for that:

1. In Home Assistant create a second user, *Alexa AI automations*, **administrator**, and a long-lived token for it
   (or use your own admin token).
2. Admin page → **Configurazione** → *Home Assistant* → **Token per le automazioni** (or `HA_AUTOMAZIONI_TOKEN` in
   `.env`).
3. **Automazioni** tab → **Attiva** (or `HA_AUTOMAZIONI=1`). The tab says whether the token has the rights it needs,
   lists the automations created by voice and lets you switch them on and off or delete them.

The automations are written to `automations.yaml` by Home Assistant itself: your `configuration.yaml` needs the
default `automation: !include automations.yaml` line (it is there unless you removed it). They show up in
*Settings → Automations* like any other, and keep working if the bridge is down.

> ⚠️ An automation runs later, on its own, with nobody there to say *no*. It is checked once, when it is created:
> if you later rename a device so that it would be forbidden, the automation keeps controlling it. Review the
> **Automazioni** tab from time to time.

## Dedicated Home Assistant user

1. *Settings → People → Users → Add user*: name *Alexa AI*, **not administrator**, **not** "local access only"
   (the service calls from outside your network).
2. Log in as that user in a private window and create a **long-lived access token** (*Profile → Security*).
   If your Home Assistant is behind Cloudflare and the private window stays on *"Unable to connect"*, use the local
   address of Home Assistant for this step.
3. Put it in `.env` as `HA_TOKEN`, set `HA_URL`, `docker compose up -d`.

Check reachability from the host, with a fake token — **401** means reachable:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer test" https://homeassistant.example.com/api/
```

If Python gets **403** while curl gets 401, a WAF is blocking Python's default user agent: the service already
sends `HTTP_USER_AGENT` (`alexa-ai-bridge/1.0`, or `HA_UA` if set).

## Bonus: covers that show inverted positions on Alexa

If your shutters are exposed to Alexa through Matter and Alexa shows the position inverted, a pair of
*template covers* that invert the position is a reliable fix:

```yaml
# templates/covers_alexa.yaml  (loaded with  template: !include_dir_merge_list templates)
- cover:
    - name: "Night shutters Alexa"
      unique_id: night_shutters_alexa
      position: >-
        {% set p = state_attr('cover.night_shutters', 'current_position') %}
        {{ (100 - p | int) if p is not none else none }}
      open_cover:  [{action: cover.open_cover,  target: {entity_id: cover.night_shutters}}]
      close_cover: [{action: cover.close_cover, target: {entity_id: cover.night_shutters}}]
      stop_cover:  [{action: cover.stop_cover,  target: {entity_id: cover.night_shutters}}]
      set_cover_position:
        - action: cover.set_cover_position
          target: {entity_id: cover.night_shutters}
          data: {position: "{{ 100 - position }}"}
```

Expose the inverted cover to Alexa and hide the original from the bridge.

> ⚠️ **Never add a second `template:` key** to `configuration.yaml`. YAML keeps only the last one: every template
> entity defined under the first key (presence sensors, for example) silently becomes *unavailable* at the next
> restart. Use `template: !include_dir_merge_list templates` and one file per topic.
