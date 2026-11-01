# Database outage went unnoticed postmortem

**Date:** 2026-10-25 · **Authors:** Douglas Barrantes · **Status:** final · **Game day:** GD-04 (run informally, before the catalog existed)

Blameless: this is about how the system let it happen, not about who did what.

## Summary

During a manual game day, PostgreSQL was stopped on purpose for about six
minutes. Every request to `/products` failed with a 500, but no alert fired
and nobody was paged. The availability SLO couldn't see the outage, because
requests that failed with an exception were never counted.

## Impact

Lab only, no real users. About six minutes of a full outage of
`/products` and `/orders`. On a real service this would have burned a large
share of the monthly error budget with no one aware of it.

## Root causes

1. When the database is down, taking a connection from the pool raises
   `PoolTimeout`. FastAPI turns the unhandled exception into a 500 for the
   client.
2. Inside the metrics middleware, `call_next` doesn't return that 500: it
   re-raises the exception. The middleware stopped right there, before
   recording anything.
3. So `http_requests_total` never saw those errors. The availability SLI was
   computed from incomplete data and stayed green.
4. Why didn't any test catch it? Every earlier failure test used the chaos
   middleware, which returns a 500 response instead of raising. The one real
   failure mode was never exercised.

## Trigger

`docker compose stop db`, run on purpose as part of the exercise.

## Resolution

Bringing the database back up restored the service. The detection gap was
fixed in v0.5.1: the middleware now records a 500 when the request raises,
then re-raises.

## Detection

The system did not detect it. It was found by a human: the expected Telegram
message never arrived, and digging in showed the 500 counter frozen in
Prometheus while the API kept answering 500.

A second, smaller problem made it look worse: an earlier page from a chaos
experiment was still firing (its 30-minute window hadn't cleared), so even a
correctly counted outage would have been folded into an alert Alertmanager
had already sent, and not repeated for an hour.

## Action items

| Action item | Type | Owner | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| Count unhandled exceptions as 500 in the metrics middleware | detect | Douglas | P0 | done (v0.5.1) |
| Regression test that simulates the database being down | detect | Douglas | P0 | done (v0.5.1) |
| Automate GD-04 in CI: stop the database, expect the availability alert | detect | Douglas | P1 | planned (phase 7) |
| Return 503 fast when the pool is exhausted instead of letting requests queue | mitigate | Douglas | P2 | idea |

## Lessons learned

### What went well

- Once traced, the cause was clear in minutes: the counter frozen while the
  API kept answering 500 pointed straight at the middleware.
- The fix was small, and a regression test proves it (it fails without the
  fix).

### What went wrong

- Dashboards, SLOs, alerts, tests and CI were all green, and the most likely
  real outage was still invisible.
- All failure testing went through the chaos middleware, which takes a
  different code path from a real failure.

### Where we got lucky

- It happened in a game day, not in production.
- Someone was waiting for the alert and noticed it didn't come.

## Timeline

All times local (UTC−6).

| Time | Event |
| :--- | :--- |
| 14:16 | A chaos experiment starts the availability page that later lingers |
| ~14:41 | Database stopped on purpose (first run) |
| 14:47 | No alert received; investigation starts. The 500 counter is frozen at 220 |
| ~14:52 | Root cause found: `call_next` re-raises, the request is never counted |
| 14:58 | Fix released as v0.5.1, with a regression test |
| 15:01 | Second run: database stopped again |
| 15:03 | Availability page reaches Telegram (MTTD 2 min) |
| 15:07 | Database back, service healthy (recovery in 6 min) |
| ~15:40 | Page resolves once the outage leaves the 30-minute window |

## Supporting information

- Fix: pull request #7, release v0.5.1.
- Query that showed the gap: `increase(http_requests_total{route="/products",status="500"}[5m])` returned 0 while every request was failing.
