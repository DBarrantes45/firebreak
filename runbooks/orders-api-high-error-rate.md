# OrdersApiHighErrorRate

**What it means:** more `/products` or `/orders` requests are failing with
5xx than the availability SLO (99.9%) can afford. A page means the monthly
budget would be gone in days at this pace; a ticket means weeks.

## First five minutes

1. Open the **SLOs and error budget** dashboard and confirm the burn rate is
   still high. If it already dropped, the cause may be gone; keep reading
   anyway, the budget was spent.
2. Check whether someone turned chaos on: `curl -s localhost:8000/admin/chaos`.
   A non-zero `error_rate` explains everything. Turn it off with
   `curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{}'`.
3. In Grafana Explore → Loki, run
   `{service_name="orders-api"} | severity_text="ERROR"` and read the most
   frequent message.

## Common causes

| What the logs say | Likely cause | Next step |
| :--- | :--- | :--- |
| `chaos: injected error` | Chaos is on | Turn it off (step 2) |
| `database not reachable` | Postgres is down or saturated | `docker compose ps db`, then `docker compose logs db` |
| Nothing obvious | A bug in a recent change | Open a failing trace from a log line and look for the red span |

## Afterwards

If this incident spent more than 20% of the monthly budget, write a
postmortem (see the [error budget policy](../docs/error-budget-policy.md)).
