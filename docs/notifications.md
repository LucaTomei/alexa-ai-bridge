# Notifications

Optional. A short message on your phone (or wherever you like) when something worth knowing happens at home:

> 🔔 *Bloccato: il modello ha chiesto lock.unlock lock.front_door, non è permesso.*<br>
> 🔔 *Eseguito dopo il tuo sì: cover.close_cover su Tutte le tapparelle.*<br>
> 🔔 *Automazione creata a voce: 'Luce cucina al mattino' (alle 07:05, solo lun, mer, ven: light.turn_on Luce cucina).*

Everything is set from the admin page: the **Notifiche** tab chooses the events and the Home Assistant app, sends a
test notification and shows the latest ones with their result; tokens and addresses are in **Configurazione**, group
**Notifiche**. Each setting can also go in `.env` ([reference](setup.md#configuration-reference)).

## Events

| Event (`NOTIFY_EVENTI`) | When | Default |
|---|---|:---:|
| `confermate` | an action on several rooms, or on an entity that always asks for a *yes*, ran after your *yes* | ✓ |
| `bloccate` | the model asked for something forbidden: a lock, a door or gate, the alarm, a script, a technical service, an entity you forbade, also inside an automation | ✓ |
| `automazioni` | an automation [created by voice](home-assistant.md#automations-by-voice) was created, enabled, disabled or deleted (by voice or from the admin page) | ✓ |
| `modelli` | a model is unreachable, logged out or out of credit and a [fallback model](providers.md#fallback-models) answers (or none does); a model is back | ✓ |
| `azioni` | every command sent to Home Assistant, even one light (they can be many) | |
| `errori` | Alexa could not answer: the model is unreachable, the key is wrong… | |
| `memoria` | the assistant [learned](memory.md) something new about the people at home | |
| `pannello` | admin page: a login, too many wrong passwords (the client is blocked), the password changed, settings saved, *log out everywhere* | |

Nothing about home actions is ever sent for the **test chat** of the admin page, whose home actions are only
simulated.
`NOTIFY_ATTIVE=0` (*Invia notifiche* off) pauses everything without removing the channels.

## Channels

Every configured channel gets every notification.

| Channel | Settings | Notes |
|---|---|---|
| **Home Assistant app** | `NOTIFY_HA` | The `notify` services of Home Assistant, e.g. `mobile_app_my_phone` (the companion app on your phone). Uses the Home Assistant URL and token already set: the **Notifiche** tab lists the services Home Assistant offers, tick the ones you want. |
| **Telegram** | `NOTIFY_TELEGRAM_TOKEN`, `NOTIFY_TELEGRAM_CHAT` | Create a bot with [@BotFather](https://t.me/BotFather), send it `/start`, get your chat ID (for example from [@userinfobot](https://t.me/userinfobot)); a group works too. |
| **ntfy** | `NOTIFY_NTFY_URL`, `NOTIFY_NTFY_TOKEN` | The topic address, e.g. `https://ntfy.sh/a-long-random-name`: on the public server whoever knows the topic reads it, so keep it hard to guess. The token is for a server with access control. Blocked attempts are sent with high priority. |
| **Gotify** | `NOTIFY_GOTIFY_URL`, `NOTIFY_GOTIFY_TOKEN` | The server address and an *application* token. |
| **Webhook** | `NOTIFY_WEBHOOK_URL`, `NOTIFY_WEBHOOK_TOKEN` | A JSON `POST` with `title`, `text`, `content`, `message`, `urgente` and `t`: Slack reads `text`, Discord reads `content`; n8n, Node-RED and Home Assistant webhooks get every field. The optional token goes in `Authorization: Bearer`. |

Addresses that hold a secret (the ntfy topic, the webhook URL) are treated like keys: never shown on the page and
never in the settings backup. As for the other services, changing a channel's address asks for its token again.

## Limits

- Notifications are sent in the background: an answer from Alexa is never slowed down.
- The same message is not repeated within two minutes (a model that retries a forbidden action sends one).
- At most `NOTIFY_MAX_ORA` (30) notifications per hour; beyond that the next ones are not sent and the log says so once.
- A channel that fails is logged (*notification on telegram not sent: HTTP 401*) without its address or token, and
  never stops the others.
