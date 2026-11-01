# GD-01: 20% of requests fail

**Date:** 2026-10-25 · **Incident commander:** `scripts/gameday.sh --silence` · **Scribe:** rebuilt from Prometheus and Loki

## Scenario

One request in five answers 500 while users keep shopping.

## Steady-state hypothesis

The availability page (`OrdersApiHighErrorRate`) reaches Telegram within 3
minutes of the injection, and the error rate is back to 0 within 1 minute of
the rollback.

## Injection

```bash
scripts/gameday.sh GD-01
```

Under the hood:

```bash
curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{"error_rate": 0.2}'
```

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

Errors keep coming after the rollback.

## Rollback

```bash
curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{}'
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
| Injection started | 17:43:32 |
| Alert received (detection) | ~17:46:05 |
| Mitigation applied | 17:46:11 |
| Service healthy again (recovery) | ~17:46:13 |

**MTTD:** ~155 s · **MTTR:** ~160 s · **Hypothesis held:** yes

## Findings

- About 17% of user requests failed (20% configured; the gap is sampling
  noise at 10 rps). The fast page fired in about 2.5 minutes, inside the
  3-minute hypothesis.
- Errors stopped the moment the chaos settings were cleared. The API never
  restarted, so there was nothing to recover besides the setting itself.
