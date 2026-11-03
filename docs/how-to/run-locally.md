# Run it locally

You need Docker with Compose v2 and around 4 GB of free memory.

The first time, create `.env` with a random password for every service:

```bash
scripts/init-env.sh
```

It never overwrites an existing `.env`. Grafana's login is `admin` and the
`GRAFANA_ADMIN_PASSWORD` it wrote there.

Start everything and wait until the healthchecks pass:

```bash
docker compose up -d --build --wait
```

Dashboards are empty without traffic, so feed them a few requests per second
(Ctrl+C stops it):

```bash
scripts/generate-traffic.sh 5
```

After changing the API code, rebuilding just that service is enough:

```bash
docker compose up -d --build --wait api
```

`docker compose down` stops the stack and keeps your data. Add `-v` to wipe
it all: database, metrics, logs and traces.

## Chaos and game days

`/admin/chaos` is off by default and answers 404. Game days need it, so set
`FIREBREAK_CHAOS_ENABLED=true` in `.env` and recreate the API:

```bash
docker compose up -d --wait api
```
