# Capacity report: orders-api

Measured on 2026-10-25 against `v0.5.1` plus the phase 6 changes.

## Setup

- `orders-api` limited to **1 CPU and 512 MB**; PostgreSQL to the same.
  Without a ceiling the API would borrow the whole machine and the numbers
  would mean nothing.
- k6 2.3.0, running inside the Compose network.
- Traffic mix: 80% `GET /products`, 20% `POST /orders`.
- Open model (`*-arrival-rate` executors): k6 keeps the rate even when the
  API slows down, the way real users do.
- Load test requests carry `X-Load-Test`, so they don't count against the SLOs.

## Results

| Test | Load | p99 (successful) | Errors | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| Smoke | 1 VU, no pauses, 30 s | 2.8 ms (p95) | 0% | ✅ |
| Average load | 20 rps for 3 min | 5.9 ms | 0% | ✅ within SLO |
| Breakpoint | +50 rps every 30 s | 250 ms crossed at ~365 rps | 0% | stopped at 3 min 18 s |
| Spike | 20 → 450 rps for 1 min → 20 | up to ~8 s during the burst | 0% | ✅ recovered |
| Soak | 30 rps for 1 h | _pending_ | _pending_ | _pending_ |

## Breaking point

The API stays comfortable up to about **300 rps** (p99 under 40 ms). Past
that, latency doesn't climb gently, it bends: 78 ms at 320 rps, 220 ms at
365 rps. That is where its single CPU hits 100%.

**The limiting resource is the API's CPU.** PostgreSQL never went above 8%
CPU and memory stayed flat at about 70 MB of 512. More capacity means more
CPU for the API (cores or replicas), not a bigger database.

Nothing failed outright. The service didn't return errors when saturated;
requests queued up and got slow. That is exactly why there is a latency SLO
next to the availability one: with availability alone, this would have looked
healthy.

## Spike

A burst of 450 rps, roughly 1.5 times capacity, held for a minute:

- The API served about 330 rps, its ceiling, at 100% CPU. k6 couldn't send
  the rest (7,648 dropped iterations).
- Requests waited in line for up to **8 seconds**, but none failed.
- About a minute after the burst ended, p99 was back to 5 ms. No lingering
  slowness, no restart needed.

An 8-second wait is a failure from a user's point of view, even if the status
code is 200. A request timeout or load shedding (answering 503 right away
once the queue is too long) would trade those long waits for fast, honest
errors. Worth considering before this runs in front of real users.

## Soak

_Pending: one hour at 30 rps, watching memory._

## Headroom

Normal traffic in this lab is around 5 to 20 rps, against a capacity of about
300. Capacity planning usually keeps a service under 70% of its breaking
point, so the practical ceiling is **about 200 rps**. Above that, add CPU
before the users notice.

## How to rerun

```bash
scripts/loadtest.sh smoke
scripts/loadtest.sh average-load
scripts/loadtest.sh breakpoint
scripts/loadtest.sh spike
scripts/loadtest.sh soak        # one hour; SOAK_DURATION=10m to shorten
```
