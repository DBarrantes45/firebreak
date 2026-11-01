# GD-06: the network to the database gets slow

**Date:** 2026-10-25 · **Incident commander:** Douglas Barrantes · **Scribe:** Douglas Barrantes

## Scenario

Every packet the database sends is delayed by 300 ms.

## Steady-state hypothesis

The latency page reaches Telegram within 3 minutes, and traces show the
time going into `db.pool.acquire` and `SELECT`, not into the API.

## Injection

```bash
scripts/gameday.sh GD-06
```

Under the hood:

```bash
docker run --rm --cap-add NET_ADMIN --network container:firebreak-db-1 alpine:3 \n  sh -c 'apk add -q iproute2 && tc qdisc add dev eth0 root netem delay 300ms'
```

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

The delay can't be removed.

## Rollback

```bash
docker run --rm --cap-add NET_ADMIN --network container:firebreak-db-1 alpine:3 \n  sh -c 'apk add -q iproute2 && tc qdisc del dev eth0 root'
```

## Expected alert and runbook

`OrdersApiHighLatency` (page) → [orders-api-high-latency.md](../runbooks/orders-api-high-latency.md)

## Results

| Mark | Time |
| :--- | :--- |
| Injection started | 16:51:02 |
| Alert received (detection) | 16:52:51 |
| Mitigation applied | 16:52:51 |
| Service healthy again (recovery) | 16:53:02 |

**MTTD:** 109 s · **MTTR:** 120 s · **Hypothesis held:** no, see below

## Findings

The first run (16:43) failed: no alert after 5 minutes, even though
`/products` went from about 5 ms to 0.59 s and 85% of requests were over
250 ms. Two things stacked up:

- The fast page needs both the 5-minute **and** the 1-hour windows above
  14.4% bad. Coming from a healthy hour, the 1-hour window needs roughly 10
  minutes of slowness before it crosses. That's the design working: five slow
  minutes don't threaten a monthly SLO.
- The traffic generator was a closed loop (send, wait for the answer, send
  again). When the API slowed down, it dropped from 5 to 2 requests per
  second, so the slow requests weighed less than they would with real users,
  who keep arriving regardless. Game days now use k6 with an open model.

The second run alerted in 109 seconds, but that number is flattering: the
1-hour window still remembered the slowness of the first run. From a clean
hour, expect about 10 minutes. The hypothesis ("within 3 minutes") was wrong,
and that's the useful result: latency incidents that start from a healthy
state take around 10 minutes to page.

Recovery was quick: 11 seconds after removing the delay, `/readyz` and
`/products` were healthy again.
