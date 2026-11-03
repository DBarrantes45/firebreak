# Back up and restore

Most of Firebreak already lives in Git: rules, SLOs, dashboards, runbooks and
the n8n workflows. A backup saves the state that doesn't.

| Volume | What it holds |
| :--- | :--- |
| `promdata` | Metric history |
| `grafanadata` | Users, preferences, annotations |
| `lokidata`, `tempodata` | Logs and traces |
| `alertmanagerdata` | Silences |
| `pgdata` | The test bed's orders |
| `n8n-data` | n8n's credentials, such as the Telegram token |

The Ollama model (about 5 GB) is left out on purpose: `ollama pull` gets it
back.

## Back up

```bash
scripts/backup.sh
```

It stops the stateful services, copies each volume into
`backups/<timestamp>/` and brings them back: about 30 seconds of downtime.
Stopping keeps every file consistent without Prometheus's admin API, which can
also delete series. A `MANIFEST` records the Git version, the image tags and a
SHA-256 for each archive.

Backups contain credentials and the database, so `backups/` is owner-only
and ignored by Git. Copy it somewhere else; a backup on the same disk doesn't
survive that disk.

## Restore

```bash
scripts/restore.sh backups/<timestamp>
```

It checks every archive against the manifest before touching anything,
replaces each volume's contents and starts the stack again.

## Drill results

A backup you never restored is a hope. Tested on 2026-11-02: back up, delete
every volume above, restore, and check.

| Check | Result |
| :--- | :--- |
| A Grafana annotation made before the backup | Back |
| Metric history | Back, oldest sample unchanged |
| n8n credentials | Back; an alert sent through n8n reached Telegram |
| **Recovery time (RTO)** | **30 s**, twice |
