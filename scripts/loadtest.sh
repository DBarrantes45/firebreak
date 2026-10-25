#!/usr/bin/env bash
# Runs one k6 scenario from loadtests/ against the running stack.
# Usage: scripts/loadtest.sh smoke | average-load | breakpoint | spike | soak
# Exits with k6's own code, so a broken threshold fails whatever called it.

set -euo pipefail

scenario="${1:?usage: scripts/loadtest.sh <scenario>}"

if [ ! -f "loadtests/${scenario}.js" ]; then
    echo "No such scenario: loadtests/${scenario}.js"
    exit 2
fi

docker compose --profile loadtest run --rm k6 run "/scripts/${scenario}.js"
