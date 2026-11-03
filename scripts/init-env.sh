#!/usr/bin/env bash
# Creates .env from .env.example with a random value for every password, so
# no install ever runs with a password someone else knows. Never overwrites an
# existing .env.

set -euo pipefail

if [ -e .env ]; then
    echo ".env already exists; leaving it alone."
    exit 0
fi

# Hex keeps the passwords free of characters sed or a URL would trip on.
while IFS= read -r line; do
    if [[ "$line" == *=change-me ]]; then
        echo "${line%=change-me}=$(openssl rand -hex 24)"
    else
        echo "$line"
    fi
done < .env.example > .env
chmod 600 .env

echo ".env created with random passwords (only you can read it)."
echo "Grafana login: admin / the GRAFANA_ADMIN_PASSWORD in .env"
