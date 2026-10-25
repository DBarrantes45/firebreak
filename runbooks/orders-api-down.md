# OrdersApiDown

**What it means:** Prometheus has not been able to scrape `orders-api` for
a minute. Either the process is gone or nothing can reach it. The SLO alerts
are muted while this one fires, because without data they can't tell you
anything.

## First five minutes

1. `docker compose ps api`: is the container running, restarting or exited?
2. `docker compose logs --tail 50 api`: look for a crash at startup. The most
   common one is the database not being ready when the pool opens.
3. `curl -i localhost:8000/healthz`: if this answers but Prometheus still
   can't scrape, the problem is between them (network, port, target config
   in `platform/prometheus/prometheus.yml`).

## Getting it back

`docker compose up -d --wait api` restarts it. If it keeps dying, read the
logs before restarting again: a crash loop hides the first, useful error.
