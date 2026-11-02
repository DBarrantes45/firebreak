#!/usr/bin/env bash
# Copies the alerting and recording rules into the Helm chart, so the cluster
# runs exactly what Compose runs. platform/prometheus/rules/ is the source;
# edit there and run this. CI fails if the copies drift.

set -euo pipefail

dest=deploy/k8s/charts/orders-api/files/rules
mkdir -p "$dest"
rm -f "$dest"/*.yml
cp platform/prometheus/rules/*.yml "$dest"/
echo "Rules copied to $dest"
