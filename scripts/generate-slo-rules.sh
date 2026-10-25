#!/usr/bin/env bash
# Validates slos/ and regenerates the Prometheus rules from it.
# Run it after every change to slos/orders-api.yml; CI fails if you forget.

set -euo pipefail

SLOTH_IMAGE="ghcr.io/slok/sloth:v0.16.0"

sloth() {
    docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$SLOTH_IMAGE" "$@"
}

sloth validate -i slos/
sloth generate -i slos/orders-api.yml -o platform/prometheus/rules/slo-orders-api.yml
echo "Rules written to platform/prometheus/rules/slo-orders-api.yml"
