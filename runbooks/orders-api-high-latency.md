# OrdersApiHighLatency

**What it means:** too many successful requests are taking longer than
250 ms. The latency SLO allows 1% of them over 30 days.

## First five minutes

1. On the **Golden signals** dashboard, check whether only p95/p99 went up
   (some users affected) or p50 too (everyone affected).
2. Check chaos: `curl -s localhost:8000/admin/chaos`. A non-zero
   `latency_rate` is the answer; switch it off with an empty `{}`.
3. Hover a high diamond on the *Latency p95 with exemplars* panel and open
   the trace. Find the longest span:
   - `db.pool.acquire` is long: every connection in the pool is busy, so
     requests queue for one. Look for traffic spikes or slow queries.
   - `SELECT` is long: the database itself is slow.
   - Neither, but the root span is long: the time went somewhere that has
     no span yet, in the app before the endpoint ran.

## Common causes

| Trace shows | Likely cause | Next step |
| :--- | :--- | :--- |
| Gap before any child span | Chaos latency, or CPU starvation | Check chaos, then `docker stats` |
| Long `db.pool.acquire` | Pool exhausted | Compare traffic with the pool size (10) |
| Long `SELECT` | Slow or locked database | `docker compose logs db` |
