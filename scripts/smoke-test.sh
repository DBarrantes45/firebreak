#!/usr/bin/env bash
# End-to-end smoke test against a running stack (docker compose up -d --wait).
# The same script runs on your machine and in CI.

set -euo pipefail

set -a
# shellcheck disable=SC1091
source .env
set +a

GRAFANA_AUTH="admin:${GRAFANA_ADMIN_PASSWORD}"

# retry <attempts> <description> <command...>: runs the command every 5 s.
retry() {
    local attempts=$1 description=$2
    shift 2
    for attempt in $(seq 1 "$attempts"); do
        if "$@" > /dev/null 2>&1; then
            echo "ok: $description"
            return 0
        fi
        echo "waiting ($attempt/$attempts): $description"
        sleep 5
    done
    echo "FAILED: $description"
    return 1
}

prometheus_target_is_up() {
    curl -fsS localhost:9090/api/v1/targets | python3 -c '
import json, sys
targets = json.load(sys.stdin)["data"]["activeTargets"]
health = [t["health"] for t in targets if t["labels"]["job"] == "orders-api"]
sys.exit(0 if health == ["up"] else 1)'
}

trace_is_in_tempo() {
    curl -fsS "localhost:3200/api/traces/$1"
}

log_is_in_loki() {
    curl -fsS --get localhost:3100/loki/api/v1/query_range \
        --data-urlencode "query={service_name=\"orders-api\"} | trace_id=\"$1\"" \
        | python3 -c 'import json, sys; sys.exit(0 if json.load(sys.stdin)["data"]["result"] else 1)'
}

echo "== API"
curl -fsS localhost:8000/healthz > /dev/null && echo "ok: /healthz"
curl -fsS localhost:8000/readyz > /dev/null && echo "ok: /readyz"
curl -fsS localhost:8000/products > /dev/null && echo "ok: /products"
curl -fsS localhost:8000/metrics | grep -q http_requests_total && echo "ok: /metrics"

echo "== Backends"
retry 12 "Prometheus scrapes orders-api" prometheus_target_is_up
retry 12 "Loki is ready" curl -fsS localhost:3100/ready
retry 12 "Tempo is ready" curl -fsS localhost:3200/ready

echo "== Grafana"
for uid in prometheus tempo loki; do
    curl -fsS -u "$GRAFANA_AUTH" "localhost:3000/api/datasources/uid/$uid" > /dev/null
    echo "ok: data source $uid"
done
curl -fsS -u "$GRAFANA_AUTH" localhost:3000/api/dashboards/uid/golden-signals > /dev/null
echo "ok: dashboard golden-signals"

echo "== Telemetry end to end"
# Send one order with a known trace id, then expect its trace in Tempo
# and its "order created" log line in Loki. This catches a broken exporter
# that every other check would let through silently.
trace_id=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
curl -fsS -X POST localhost:8000/orders \
    -H 'content-type: application/json' \
    -H "traceparent: 00-${trace_id}-$(python3 -c 'import secrets; print(secrets.token_hex(8))')-01" \
    -d '{"product_id": 1, "quantity": 1}' > /dev/null
echo "sent an order with trace_id $trace_id"
retry 12 "trace reached Tempo" trace_is_in_tempo "$trace_id"
retry 12 "log line reached Loki" log_is_in_loki "$trace_id"

echo "== All smoke checks passed"
