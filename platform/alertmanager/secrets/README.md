# Secrets

Everything in this folder except this file is ignored by Git. Alertmanager
expects two files here:

- `telegram_bot_token`: the token BotFather gave you, and nothing else.
- `telegram_chat_id`: the numeric id of the chat that receives the alerts.

Alertmanager runs as an unprivileged user inside its container, so both
files need to be readable by others (`chmod 644`). Fine on a single-user
lab machine; use a real secret store anywhere else.
