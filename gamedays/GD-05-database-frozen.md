# GD-05: the database freezes

**Date:** 2026-10-25 · **Incident commander:** `scripts/gameday.sh --silence` · **Scribe:** rebuilt from Prometheus and Loki

## Scenario

PostgreSQL is paused: it keeps its connections open but stops answering.

## Steady-state hypothesis

The availability page reaches Telegram within 3 minutes, and the API
recovers on its own within 1 minute of unpausing, without a restart.

## Injection

```bash
scripts/gameday.sh GD-05
```

Under the hood:

```bash
docker compose pause db
```

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

The API doesn't recover after `unpause`.

## Rollback

```bash
docker compose unpause db
```

## Expected alert and runbook

`OrdersApiHighErrorRate` (page) → [orders-api-high-error-rate.md](../runbooks/orders-api-high-error-rate.md)

## Results

> The run's own output was lost (it lived in `/tmp` and the machine
> rebooted). These marks come from the `ALERTS` series in Prometheus and the
> API logs in Loki, so they're accurate to about 15 seconds. The alert was
> silenced: "received" means it reached Alertmanager, not Telegram.

| Mark | Time |
| :--- | :--- |
| Injection started | ~19:57:58 |
| Alert received (detection) | ~19:58:45 |
| Mitigation applied | ~19:58:47 |
| Service healthy again (recovery) | ~19:58:49 |

**MTTD:** ~47 s · **MTTR:** ~51 s · **Hypothesis held:** yes

## Findings

- Freezing the database is worse than stopping it: almost every request
  failed (99%), because each one waited 2 seconds for a connection and then
  gave up. The pool logged `connection timeout expired` from 19:58:00 on.
- That error rate burns the budget so fast that the page fired in under a
  minute, much quicker than GD-04.
- After unpausing, the first orders went through within 2 seconds, with no
  restart. The 2-second pool timeout is what keeps a frozen database from
  freezing the API too: requests fail fast instead of piling up.
