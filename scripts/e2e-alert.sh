#!/usr/bin/env bash
# Stops the API on purpose and checks that OrdersApiDown reaches Alertmanager.
# Prints the time to detect (MTTD). Runs locally and in CI.
#
# The alert is silenced for the duration of the test, so running it locally
# doesn't ping your phone. A silenced alert still reaches Alertmanager; it
# just isn't sent anywhere.

set -euo pipefail

TIMEOUT_SECONDS=180

amtool() {
    docker compose exec -T alertmanager amtool --alertmanager.url=http://localhost:9093 "$@"
}

alert_reached_alertmanager() {
    curl -fsS localhost:9093/api/v2/alerts | python3 -c '
import json, sys
alerts = json.load(sys.stdin)
found = [a for a in alerts
         if a["labels"]["alertname"] == "OrdersApiDown"
         and a["status"]["state"] in ("active", "suppressed")]
sys.exit(0 if found else 1)'
}

silence_id=$(amtool silence add alertname=OrdersApiDown \
    --duration=10m --author=e2e-alert --comment="Planned outage from scripts/e2e-alert.sh")
trap 'amtool silence expire "$silence_id" > /dev/null' EXIT

echo "Stopping the API"
docker compose stop api > /dev/null
start=$SECONDS

until alert_reached_alertmanager; do
    elapsed=$((SECONDS - start))
    if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
        echo "FAILED: OrdersApiDown did not reach Alertmanager within ${TIMEOUT_SECONDS}s"
        docker compose start api > /dev/null
        exit 1
    fi
    echo "waiting for OrdersApiDown (${elapsed}s)"
    sleep 5
done

mttd=$((SECONDS - start))
echo "ok: OrdersApiDown reached Alertmanager after ${mttd}s"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "OrdersApiDown time to detect: ${mttd}s" >> "$GITHUB_STEP_SUMMARY"
fi

echo "Starting the API again"
docker compose up -d --wait api > /dev/null

# Keep the silence until the alert has resolved, or the trap would unmute
# a still-firing alert and send a message after all.
until ! alert_reached_alertmanager; do
    sleep 5
done
echo "ok: alert resolved"
