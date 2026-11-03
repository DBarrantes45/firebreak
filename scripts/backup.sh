#!/usr/bin/env bash
# Backs up everything Firebreak keeps outside Git into backups/<timestamp>/.
#
#   scripts/backup.sh
#
# Rules, SLOs, dashboards, runbooks and n8n workflows already live in Git;
# this saves the state that doesn't: metric history, logs, traces, Grafana's
# annotations and users, Alertmanager silences, the test bed's orders, and
# n8n's credentials. The Ollama model is left out: it's 5 GB and
# `ollama pull` gets it back.
#
# The stateful services stop for the few seconds the copy takes, so every
# file is consistent. That avoids Prometheus's admin API, which can also
# delete series.

set -euo pipefail

volumes=(promdata grafanadata lokidata tempodata alertmanagerdata pgdata n8n-data)
services=(prometheus grafana loki tempo alertmanager db n8n)
project=firebreak

dest="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$dest"
# Backups hold n8n credentials and the database: owner-only.
chmod 700 backups "$dest"

running=$(docker compose --profile automation ps --services --status running)
stop=()
for service in "${services[@]}"; do
    if grep -qx "$service" <<< "$running"; then stop+=("$service"); fi
done

echo "Stopping ${stop[*]}"
docker compose --profile automation stop "${stop[@]}" > /dev/null 2>&1
started=$SECONDS

for volume in "${volumes[@]}"; do
    full="${project}_${volume}"
    if ! docker volume inspect "$full" > /dev/null 2>&1; then
        echo "skip $volume (doesn't exist)"
        continue
    fi
    # Root, to read every file in the volume; the archive is then handed to
    # you and made owner-only, since it can hold credentials.
    docker run --rm -v "$full":/source:ro -v "$PWD/$dest":/backup alpine:3 sh -c \
        "tar --numeric-owner -czf /backup/$volume.tar.gz -C /source . \
         && chown $(id -u):$(id -g) /backup/$volume.tar.gz && chmod 600 /backup/$volume.tar.gz"
    echo "saved $volume"
done

echo "Starting ${stop[*]} again ($((SECONDS - started)) s stopped)"
# Recreated rather than restarted: a config file edited in place by a tool
# that swaps the file (sed -i does) leaves a plain restart pointing at the
# old one, and the container won't start.
docker compose --profile automation up -d --force-recreate --wait "${stop[@]}" > /dev/null 2>&1

{
    echo "created: $(date -Iseconds)"
    echo "git: $(git describe --tags --always --dirty)"
    echo "images:"
    docker compose --profile automation config --images | sed 's/^/  /'
    echo "sha256:"
    (cd "$dest" && sha256sum ./*.tar.gz | sed 's/^/  /')
} > "$dest/MANIFEST"
chmod 600 "$dest/MANIFEST"

echo "Backup in $dest ($(du -sh "$dest" | cut -f1))"
