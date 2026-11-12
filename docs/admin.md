# Admin page

A web page to look after the bridge without a terminal: see whether everything works, read what was asked, try the
assistant by text, and change the settings.

<p align="center"><img src="images/admin-overview.png" width="85%" alt="Admin page: overview"></p>

| Tab | What it does |
|---|---|
| **Panoramica** | Service, model, web search and Home Assistant at a glance; questions, average time, slow answers, errors and home actions since the last start; one-click checks of the model, the web search and Home Assistant. |
| **Conversazioni** | The latest questions and answers with their time, the home actions they ran and any error. Searchable. Users are anonymised. |
| **Chat di prova** | Talk to the assistant by text, with the same model, tools and rules as on the Echo. Home actions are **simulated** by default: every safety check runs, but nothing is sent to Home Assistant. |
| **Configurazione** | Every setting with its explanation. Saving checks the new values, then restarts the service in a few seconds. Keys and tokens are never shown, only whether they are set. |
| **Registro** | The latest log lines, with a filter for warnings and errors. |

<p align="center">
  <img src="images/admin-conversations.png" width="49%" alt="Admin page: conversations">
  <img src="images/admin-settings.png" width="49%" alt="Admin page: settings">
</p>

## Turn it on

The page is **off** until you set a password of at least 12 characters in `.env`:

```bash
ADMIN_PASSWORD=a-long-password-only-you-know
```

Then `docker compose up -d`. Where you can open it is up to you, and you can combine the options:

| From | Settings in `.env` | Address |
|---|---|---|
| **The server itself** (default) | nothing else | `http://127.0.0.1:8090/admin` on the server, or from your computer through an SSH tunnel: `ssh -L 8090:127.0.0.1:8090 user@server`, then `http://127.0.0.1:8090/admin` |
| **Your home network** | `BRIDGE_BIND=0.0.0.0` | `http://<server-ip>:8090/admin` from any device at home |
| **Anywhere** | `ADMIN_PUBLIC=on` (bundled Caddy) | `https://<PUBLIC_HOST>/admin` |
| **Your own reverse proxy** | – | publish `/admin` on the site that already serves `/alexa`, or on a separate host name |

With `BRIDGE_BIND=0.0.0.0` the page travels over plain HTTP on your home network: fine for a trusted network, use the
SSH tunnel or HTTPS otherwise. `/alexa` is published too, but it only accepts requests signed by Amazon.

A VPN to your home (WireGuard, Tailscale…) gives you the home-network option from anywhere, without publishing the
page on the internet.

## Security

- Off without `ADMIN_PASSWORD`; a password shorter than 12 characters keeps it off (the log says so).
- After 5 wrong passwords from the same address, or 30 in total, logins are refused for 15 minutes. Every wrong
  password costs one second.
- The session cookie is `HttpOnly` and `SameSite=Strict`, and `Secure` when the page is reached over HTTPS. Every
  change needs a CSRF token. Sessions last 12 hours; changing the password logs everyone out.
- Strict `Content-Security-Policy`, no external resources, the page cannot be framed.
- Keys and tokens never leave the server: the page only shows whether they are set.
- With `ADMIN_PUBLIC` unset or `off`, the bundled Caddy answers 404 on `/admin`, whatever the service does.

## Conversation history

Kept **in memory only**: it is lost at every restart and never written to disk. `ADMIN_HISTORY` sets how many
questions are kept (default `100`); `ADMIN_HISTORY=0` turns the history off. Amazon user IDs are replaced by a
short anonymous code.

## How saved settings work

- Settings saved from the page are stored in `/data/settings.json`, in the `bridge_data` Docker volume, and take
  precedence over `.env`. *"Torna al valore del .env"* removes the override.
- Before saving, the new values are loaded in a separate process with the same checks as at startup: a wrong value
  (a model block without URL, invalid JSON, an invalid regular expression…) is refused and nothing changes.
- After saving, the service restarts its worker in a few seconds. A slow answer still pending is lost.
- `SKILL_ID` can be changed here; `ADMIN_PASSWORD` cannot (change it in `.env`).
- Without a writable `/data` (for example running the image without the compose file), the settings are read-only:
  mount a volume on `/data`.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `ADMIN_PASSWORD` | – | Turns the page on (12 characters or more) |
| `ADMIN_HISTORY` | `100` | Questions kept in the history; `0` turns it off |
| `BRIDGE_BIND` | `127.0.0.1` | Address the service port is published on (`0.0.0.0` = home network too) |
| `ADMIN_PUBLIC` | `off` | `on` publishes `/admin` through the bundled Caddy |
