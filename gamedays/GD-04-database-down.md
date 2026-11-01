# GD-04: the database goes down

**Date:** 2026-10-25 · **Incident commander:** Douglas Barrantes · **Scribe:** Douglas Barrantes

## Scenario

PostgreSQL stops while users keep shopping.

## Steady-state hypothesis

The availability page (`OrdersApiHighErrorRate`, severity page) reaches
Telegram within 3 minutes of the database stopping, and `/readyz` reports
healthy within 1 minute of the database coming back, without restarting the
API.

## Injection

```bash
docker compose stop db
```

With `scripts/generate-traffic.sh 5` running the whole time.

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

The database doesn't come back with `docker compose start db`, or any
service other than `api` and `db` stops responding.

## Rollback

```bash
docker compose start db
```

## Expected alert and runbook

`OrdersApiHighErrorRate` (page) →
[orders-api-high-error-rate.md](../runbooks/orders-api-high-error-rate.md).
The runbook's table points to `database not reachable` in the logs.

## Results

First run (about 14:41): **no alert at all.** That run led to the
[postmortem](../postmortems/2026-10-25-database-outage-went-unnoticed.md)
and the fix in v0.5.1. The table below is the second run.

| Mark | Time |
| :--- | :--- |
| Injection started | 15:01 |
| Alert received (detection) | 15:03 |
| Mitigation applied | 15:07 |
| Service healthy again (recovery) | 15:07 |

**MTTD:** 2 min · **MTTR:** 6 min · **Hypothesis held:** yes, on the second run

## Findings

- The SLO alert resolves about 30 minutes after the service recovers, not
  right away: the 30-minute window keeps remembering the outage. Measure
  recovery on the service (`/readyz`, the errors panel), not on the
  "resolved" message.
- The API recovered on its own: the connection pool checks connections
  before lending them, so no restart was needed.
