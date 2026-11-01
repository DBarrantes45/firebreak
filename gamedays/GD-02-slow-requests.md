# GD-02: 30% of requests are slow

**Date:** 2026-10-25 · **Incident commander:** `scripts/gameday.sh --silence` · **Scribe:** rebuilt from Prometheus and Loki

## Scenario

Almost a third of the requests wait an extra 800 ms.

## Steady-state hypothesis

The latency page (`OrdersApiHighLatency`) reaches Telegram within 3 minutes,
and p99 is back under 250 ms within 1 minute of the rollback.

## Injection

```bash
scripts/gameday.sh GD-02
```

Under the hood:

```bash
curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{"latency_ms": 800, "latency_rate": 0.3}'
```

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

p99 stays high after the rollback.

## Rollback

```bash
curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{}'
```

## Expected alert and runbook

`OrdersApiHighLatency` (page) → [orders-api-high-latency.md](../runbooks/orders-api-high-latency.md)

## Results

> The run's own output was lost (it lived in `/tmp` and the machine
> rebooted). These marks come from the `ALERTS` series in Prometheus and the
> API logs in Loki, so they're accurate to about 15 seconds. The alert was
> silenced: "received" means it reached Alertmanager, not Telegram.

| Mark | Time |
| :--- | :--- |
| Injection started | 18:36:15 |
| Alert received (detection) | ~18:44:50 |
| Mitigation applied | 18:44:57 |
| Service healthy again (recovery) | ~18:45:00 |

**MTTD:** ~515 s · **MTTR:** ~525 s · **Hypothesis held:** no, see below

## Findings

- The latency page took about 8.5 minutes, not 3. Same cause as
  [GD-06](GD-06-slow-network.md): the long burn-rate window has to fill up
  with slow requests before the page fires, and this run started after 20
  minutes of healthy traffic. That's the SLO doing its job, and the
  hypothesis was the thing that was wrong. Latency incidents page in
  minutes, not seconds.
- Recovery was immediate after clearing the delay; p99 doesn't need the
  window to drain, only the alert does.
