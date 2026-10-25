# Run it locally

You need Docker with Compose v2 and around 4 GB of free memory.

The first time, copy the example environment file and put real passwords in it:

```bash
cp .env.example .env
```

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
