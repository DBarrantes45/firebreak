# Incident automation

An optional layer that takes the first minutes of an incident: n8n asks a
local LLM (Ollama, on the GPU) for a plain-language summary of each alert,
and restarts the API on its own when it dies, behind fixed guardrails.

It needs an NVIDIA GPU, so it sits behind a Compose profile and the default
`up` (and CI) never starts it.

## Set it up

```bash
docker compose --profile automation up -d --wait
docker compose exec ollama ollama pull qwen3:8b
```

Open n8n at <http://localhost:5678>, create the owner account, and add one
credential: **Telegram API**, with the same bot token Alertmanager uses.
Then load the workflows and publish both in the editor:

```bash
scripts/n8n-import.sh                                       # remediation in dry run
FIREBREAK_REMEDIATION_DRY_RUN=false scripts/n8n-import.sh   # restarts for real
```

## The two workflows

Both live in [`automation/n8n/`](../../automation/n8n).

- **Alert summary:** every alert gets a short summary from the LLM and its
  runbook link. If Ollama doesn't answer within 30 seconds, the raw alert
  goes out instead.
- **Alert remediation:** restarts `orders-api` when `OrdersApiDown` fires.
  Only that alert, at most twice an hour, through a socket proxy that allows
  nothing but restarts. A new crash right after a restart is a crash loop
  and goes to a human. The LLM never decides anything here.

Alertmanager keeps sending to Telegram directly as well, so an alert never
depends on n8n being up. The trade-off is two messages per alert.

In the GD-03 game day, the bot restarted the API 7 seconds after the alert
(MTTR 115 s).
