#!/usr/bin/env bash
# Sends a steady mix of requests to orders-api so the dashboards have data.
# Usage: scripts/generate-traffic.sh [requests_per_second]   (default: 5)
# Stop it with Ctrl+C.

set -u

API_URL="http://localhost:8000"
REQUESTS_PER_SECOND="${1:-5}"
PAUSE_SECONDS=$(awk "BEGIN { print 1 / $REQUESTS_PER_SECOND }")

echo "Sending about $REQUESTS_PER_SECOND requests per second to $API_URL (Ctrl+C to stop)"

count=0
while true; do
    count=$((count + 1))

    # 4 out of 5 requests read products, 1 out of 5 creates an order.
    if [ $((count % 5)) -eq 0 ]; then
        status=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API_URL/orders" \
            -H 'content-type: application/json' \
            -d '{"product_id": 1, "quantity": 1}')
        echo "POST /orders    -> $status"
    else
        status=$(curl -s -o /dev/null -w '%{http_code}' "$API_URL/products")
        echo "GET  /products  -> $status"
    fi

    sleep "$PAUSE_SECONDS"
done
