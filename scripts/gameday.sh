#!/usr/bin/env bash
# Runs one game day from gamedays/ and measures it.
#
#   scripts/gameday.sh GD-01            alert reaches Telegram, like a real incident
#   scripts/gameday.sh GD-01 --silence  alert only reaches Alertmanager
#   WARMUP_SECONDS=1200 scripts/gameday.sh GD-01   healthy traffic first
#   HANDS_OFF=1 scripts/gameday.sh GD-03   no rollback: wait for the automation
#
# Steps: start traffic, inject the failure, wait for the expected alert,
# roll back (playing the responder), wait until the service is healthy,
# then print the four marks for the game day file.

set -euo pipefail

id="${1:?usage: scripts/gameday.sh GD-0N [--silence]}"

# Keep a copy of everything this run prints in the repo, not in /tmp:
# a reboot in the middle of a long batch must not lose the results.
mkdir -p gamedays/runs
log="gamedays/runs/$(date +%F-%H%M)-${id}.log"
exec > >(tee -a "$log") 2>&1
silence="${2:-}"
# Latency alerts need the 1h window to fill up; see GD-06 findings.
alert_timeout=1200
health_timeout=180
hands_off="${HANDS_OFF:-0}"
if [ "$hands_off" = 1 ]; then
    # The automation needs time to notice, retry and cool down.
    health_timeout=600
fi
# Healthy traffic before the injection. SLO alerts compare against the last
# hour, so a run straight after another one alerts unrealistically fast.
warmup_seconds="${WARMUP_SECONDS:-30}"

chaos() {
    curl -fsS -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d "$1" > /dev/null
}

db_network() {
    docker run --rm --cap-add NET_ADMIN --network container:firebreak-db-1 alpine:3 \
        sh -c "apk add -q iproute2 && tc qdisc $1 dev eth0 root ${2:-}"
}

case "$id" in
    GD-01) expected=OrdersApiHighErrorRate
           inject() { chaos '{"error_rate": 0.2}'; }
           rollback() { chaos '{}'; } ;;
    GD-02) expected=OrdersApiHighLatency
           inject() { chaos '{"latency_ms": 800, "latency_rate": 0.3}'; }
           rollback() { chaos '{}'; } ;;
    GD-03) expected=OrdersApiDown
           inject() { chaos '{"leak_mb_per_request": 5}'; }
           rollback() { docker compose up -d --wait api > /dev/null; } ;;
    GD-04) expected=OrdersApiHighErrorRate
           inject() { docker compose stop db > /dev/null; }
           rollback() { docker compose start db > /dev/null; } ;;
    GD-05) expected=OrdersApiHighErrorRate
           inject() { docker compose pause db > /dev/null; }
           rollback() { docker compose unpause db > /dev/null; } ;;
    GD-06) expected=OrdersApiHighLatency
           inject() { db_network add "netem delay 300ms"; }
           rollback() { db_network del; } ;;
    *) echo "Unknown game day: $id"; exit 2 ;;
esac

if [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/admin/chaos)" = 404 ]; then
    echo "Chaos is off. Set FIREBREAK_CHAOS_ENABLED=true in .env, then: docker compose up -d --wait api"
    exit 1
fi

alert_fired() {
    curl -fsS localhost:9093/api/v2/alerts | python3 -c '
import json, sys
name = sys.argv[1]
alerts = json.load(sys.stdin)
hit = [a for a in alerts if a["labels"]["alertname"] == name
       and a["labels"].get("severity") == "page"
       and a["status"]["state"] in ("active", "suppressed")]
sys.exit(0 if hit else 1)' "$expected"
}

service_healthy() {
    [ "$(curl -s -o /dev/null -m 3 -w '%{http_code}' localhost:8000/readyz)" = 200 ] &&
        [ "$(curl -s -o /dev/null -m 3 -w '%{http_code}' localhost:8000/products)" = 200 ]
}

if alert_fired; then
    echo "$expected is already firing from an earlier run. Wait for it to resolve first."
    exit 1
fi

silence_id=""
traffic_pid=""
cleanup() {
    [ -n "$traffic_pid" ] && kill "$traffic_pid" 2> /dev/null || true
    docker ps -q --filter "label=com.docker.compose.service=k6" | xargs -r docker stop > /dev/null 2>&1 || true
    if [ -n "$silence_id" ]; then
        docker compose exec -T alertmanager amtool --alertmanager.url=http://localhost:9093 \
            silence expire "$silence_id" || true
    fi
}
trap cleanup EXIT

if [ "$silence" = "--silence" ]; then
    silence_id=$(docker compose exec -T alertmanager amtool --alertmanager.url=http://localhost:9093 \
        silence add "alertname=$expected" --duration=1h --author=gameday --comment="$id")
fi

echo "Starting background traffic (k6, 10 rps, counted as user traffic)"
docker compose --profile loadtest run --rm -e COUNT_AS_USER=true k6 run --quiet /scripts/gameday-traffic.js > /dev/null 2>&1 &
traffic_pid=$!
echo "Warming up for ${warmup_seconds}s"
sleep "$warmup_seconds"

t_inject=$(date +%T); s_inject=$SECONDS
echo "$t_inject  injecting $id"
inject

until alert_fired; do
    if [ $((SECONDS - s_inject)) -ge "$alert_timeout" ]; then
        echo "FAILED: $expected did not fire within ${alert_timeout}s. Rolling back."
        rollback
        exit 1
    fi
    sleep 5
done
t_alert=$(date +%T); s_alert=$SECONDS
echo "$t_alert  $expected fired"

echo "api container: $(docker inspect firebreak-api-1 -f '{{.State.Status}}, OOMKilled={{.State.OOMKilled}}')"
if [ "$hands_off" = 1 ]; then
    t_rollback="by the automation"
    echo "$(date +%T)  hands off: waiting for the automation to fix it"
else
    t_rollback=$(date +%T)
    echo "$t_rollback  rolling back"
    rollback
fi

until service_healthy; do
    if [ $((SECONDS - s_alert)) -ge "$health_timeout" ]; then
        echo "FAILED: service not healthy ${health_timeout}s after the rollback"
        exit 1
    fi
    sleep 2
done
t_healthy=$(date +%T); s_healthy=$SECONDS
echo "$t_healthy  service healthy"

echo
echo "| Mark | Time |"
echo "| :--- | :--- |"
echo "| Injection started | $t_inject |"
echo "| Alert received (detection) | $t_alert |"
echo "| Mitigation applied | $t_rollback |"
echo "| Service healthy again (recovery) | $t_healthy |"
echo
echo "MTTD: $((s_alert - s_inject))s · MTTR: $((s_healthy - s_inject))s"
