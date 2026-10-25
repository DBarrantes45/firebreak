# Endpoints and ports

Everything listens on `127.0.0.1` only, so nothing is reachable from the
rest of your network.

| Service | Where | Notes |
| :--- | :--- | :--- |
| orders-api | <http://localhost:8000/docs> | Interactive API docs |
| Grafana | <http://localhost:3000> | User `admin`, password from `GRAFANA_ADMIN_PASSWORD` in `.env` |
| Prometheus | <http://localhost:9090> | Query console; *Status → Target health* shows what it scrapes |
| Tempo | <http://localhost:3200/ready> | `/api/traces/<trace_id>` returns a single trace |
| Loki | <http://localhost:3100/ready> | LogQL over HTTP |
| PostgreSQL | `localhost:5432` | Credentials in `.env` |

## orders-api

| Method | Path | What it does |
| :--- | :--- | :--- |
| GET | `/healthz` | Liveness. Never touches the database |
| GET | `/readyz` | Readiness. Returns 503 when the database can't be reached |
| GET | `/products` | Lists products |
| POST | `/orders` | Takes `{"product_id": 1, "quantity": 2}`; answers 201, 400 or 404 |
| GET | `/metrics` | Prometheus metrics |
| GET, POST | `/admin/chaos` | Only exists when `FIREBREAK_CHAOS_ENABLED=true` |

## Chaos settings

```json
{ "error_rate": 0.2, "latency_ms": 300, "latency_rate": 0.1, "leak_mb_per_request": 0 }
```

`error_rate` is the share of requests that get a 500. `latency_ms` is added
to a share of requests set by `latency_rate`. `leak_mb_per_request` keeps that
many megabytes in memory for good on every request. An empty object, `{}`,
switches everything off.
