#!/usr/bin/env bash
# Restores a backup made by scripts/backup.sh, replacing the current data.
#
#   scripts/restore.sh backups/20261102-193000
#
# Checks every archive against the manifest before touching anything, then
# replaces each volume's contents and brings the stack back up.

set -euo pipefail

src="${1:?usage: scripts/restore.sh backups/<timestamp>}"
project=firebreak
[ -f "$src/MANIFEST" ] || { echo "$src has no MANIFEST: not a backup made by backup.sh"; exit 1; }

echo "Verifying checksums"
(cd "$src" && sed -n 's/^  \([0-9a-f]\{64\}  .*\)$/\1/p' MANIFEST | sha256sum -c --quiet)

started=$SECONDS
docker compose --profile automation stop > /dev/null 2>&1

for archive in "$src"/*.tar.gz; do
    volume=$(basename "$archive" .tar.gz)
    full="${project}_${volume}"
    # Compose's own labels, so a volume recreated here still counts as one of
    # the project's (without them Compose warns on every up).
    docker volume create --label com.docker.compose.project="$project" \
        --label com.docker.compose.volume="$volume" "$full" > /dev/null
    # Empty the volume first, dotfiles included, so nothing newer survives.
    docker run --rm -v "$full":/target -v "$PWD/$src":/backup:ro alpine:3 \
        sh -c "find /target -mindepth 1 -delete && tar --numeric-owner -xzf /backup/$volume.tar.gz -C /target"
    echo "restored $volume"
done

docker compose up -d --wait > /dev/null 2>&1 || { echo "the stack didn't come back up: docker compose ps"; exit 1; }
# n8n's data came along, so bring the automation profile back too. It needs a
# GPU; without one the core stack is still fully restored.
if [ -f "$src/n8n-data.tar.gz" ]; then
    docker compose --profile automation up -d --wait > /dev/null 2>&1 \
        || echo "warning: the automation profile didn't start (no GPU?); core stack is up"
fi
echo "Restored $src in $((SECONDS - started)) s"
