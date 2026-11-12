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
   garage door, siren…*), and technical services (containers, Zigbee, MQTT broker, NVR, backups…).
   `HA_VIETATO` **adds** your own regex to this list, e.g. `HA_VIETATO=garage|irrigazione`; it can never remove
   a built-in rule. The check is on names: a switch that opens the gate but is called *"relay 3"* is not caught,
   so give such entities a descriptive name or list them in `HA_VIETATO`.
3. **Explicit targets**: every entity must exist and belong to the requested domain; `all` is refused.
4. **Allowed data keys only**: `brightness_pct`, `position`, `temperature`, `hvac_mode`, `humidity`,
   `color_temp_kelvin`, `rgb_color`. Anything else (e.g. an `entity_id` smuggled into `dati`) is dropped.
5. **Spoken confirmation for multi-room actions**: more than `HA_MAX_SENZA_CONFERMA` entities, or any entity in
   `HA_GRUPPI`, runs only if `confermato=true` **and the user's last sentence is a yes** (*sì, certo, va bene,
   procedi…*). The model cannot confirm on its own.
6. **Every executed action is logged** (`azione HA: …`) and recorded in the conversation memory.

> ⚠️ **Scenes** run whatever they contain. `scene.turn_on` needs no confirmation, so a scene that unlocks a door or
> changes several rooms bypasses rules 2 and 5. Keep locks and alarms out of scenes, or forbid those scenes with
> `HA_VIETATO`.

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
