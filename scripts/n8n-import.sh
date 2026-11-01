#!/usr/bin/env bash
# Loads the workflows in automation/n8n/ into the running n8n.
#
#   docker compose --profile automation up -d --wait
#   scripts/n8n-import.sh                                   remediation in dry run
#   FIREBREAK_REMEDIATION_DRY_RUN=false scripts/n8n-import.sh   remediation for real
#
# Nothing private is in the repo. On import, three placeholders are filled in:
# the Telegram chat id (from the same secret file Alertmanager uses), the id of
# the Telegram credential (create it once in the n8n editor, named anything)
# and the dry-run switch. Imported workflows are left unpublished.

set -euo pipefail

chat_id=$(tr -d '[:space:]' < platform/alertmanager/secrets/telegram_chat_id)
if ! [[ "$chat_id" =~ ^-?[0-9]+$ ]]; then
    echo "platform/alertmanager/secrets/telegram_chat_id must hold a numeric chat id"
    exit 1
fi

dry_run="${FIREBREAK_REMEDIATION_DRY_RUN:-true}"
if [[ "$dry_run" != true && "$dry_run" != false ]]; then
    echo "FIREBREAK_REMEDIATION_DRY_RUN must be true or false"
    exit 1
fi

# The export keeps credential data encrypted; only the id is read here.
credential_id=$(docker compose exec -T n8n n8n export:credentials --all 2> /dev/null | python3 -c '
import json, sys
ids = [c["id"] for c in json.load(sys.stdin) if c["type"] == "telegramApi"]
print(ids[0] if ids else "")')
if [ -z "$credential_id" ]; then
    echo "No Telegram credential in n8n yet: create one in the editor (Credentials > Telegram API) and run this again."
    exit 1
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

for file in automation/n8n/*.json; do
    sed -e "s/__TELEGRAM_CHAT_ID__/$chat_id/g" \
        -e "s/__TELEGRAM_CREDENTIAL_ID__/$credential_id/g" \
        -e "s/__REMEDIATION_DRY_RUN__/$dry_run/g" \
        "$file" > "$tmp"
    docker compose cp "$tmp" n8n:/tmp/workflow.json > /dev/null 2>&1
    # Importing over an existing id replaces that workflow and unpublishes it.
    docker compose exec -T n8n n8n import:workflow --input=/tmp/workflow.json > /dev/null 2>&1
    docker compose exec -T n8n rm -f /tmp/workflow.json
    echo "Imported $file"
done
echo "Remediation dry run: $dry_run. Publish both workflows in the editor."
